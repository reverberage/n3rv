from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from chromadb import PersistentClient
from chromadb.api.types import EmbeddingFunction, Embeddings, Documents

from nerv.config import RuntimeSettings
from nerv.models.memory import (
    ConflictCandidate,
    ContextEntry,
    ContextResult,
    JudgeResult,
    MemoryScope,
    MemoryType,
    PruneResult,
    RecallResult,
    RelationVerdict,
    SaveResult,
    SearchResponse,
    SearchResult,
    SessionStartResult,
    TimelineEntry,
    TimelineResult,
)
from nerv.mcp.shared import detect_agent_source, ensure_runtime_directories

logger = logging.getLogger("nerv.mcp.memory")


class _SimpleHashEmbeddingFunction(EmbeddingFunction):
    """Deterministic hash-based embeddings — no ML deps required.

    Used as a fallback when onnxruntime is unavailable (e.g. Python 3.14 on Windows).
    Semantic similarity is approximate (character-level), but the store remains functional.
    """
    DIM = 384

    def name(self) -> str:
        return "nerv-hash"

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        import hashlib
        import math
        embeddings: Embeddings = []
        for text in input:
            vec = [0.0] * self.DIM
            for i, ch in enumerate(text[:2048]):
                digest = int(hashlib.md5(f"{i}:{ch}".encode()).hexdigest(), 16)
                vec[digest % self.DIM] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings


def _make_embedding_function() -> EmbeddingFunction | None:
    """Return the default ChromaDB embedding function, or a hash fallback."""
    try:
        import onnxruntime  # noqa: F401 — probe only
        return None  # let chromadb use its default
    except (ImportError, Exception):
        return _SimpleHashEmbeddingFunction()


TOPIC_KEY_PATTERN = re.compile(r"^[a-z0-9-]+$")

_SESSION_CONTEXT_TYPES = [MemoryType.DECISION, MemoryType.ARCHITECTURE, MemoryType.PATTERN, MemoryType.CONFIG]
_SESSION_CONTEXT_LIMIT = 5

_CONFLICT_CANDIDATES_LIMIT = 3


class RelationsStore:
    """Lightweight sqlite3-backed store for memory verdict relations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    reason TEXT,
                    agent_source TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, target_id)
                )
            """)
            conn.commit()

    def upsert(
        self,
        *,
        source_id: str,
        target_id: str,
        verdict: str,
        reason: str,
        agent_source: str,
    ) -> tuple[str, bool]:
        """Insert or update a relation. Returns (relation_id, is_new)."""
        relation_id = str(uuid5(NAMESPACE_URL, f"{source_id}:{target_id}"))
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM memory_relations WHERE source_id=? AND target_id=?",
                (source_id, target_id),
            ).fetchone()
            is_new = existing is None
            conn.execute(
                """
                INSERT INTO memory_relations (id, source_id, target_id, verdict, reason, agent_source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id) DO UPDATE SET
                    id=excluded.id,
                    verdict=excluded.verdict,
                    reason=excluded.reason,
                    agent_source=excluded.agent_source,
                    created_at=excluded.created_at
                """,
                (relation_id, source_id, target_id, verdict, reason, agent_source, now),
            )
            conn.commit()
        return relation_id, is_new


class MemoryStore:
    """Dual-store memory system: ChromaDB (vector search) + SQLite (relations).

    Provides persistent semantic memory for agents with conflict detection,
    revision tracking, and soft-delete support.
    """

    SEARCH_NUDGE_THRESHOLD = 3
    SEARCH_NUDGE_MESSAGE = (
        "You've searched memory several times without saving new context. "
        "Consider using memory_save or memory_session_summary."
    )

    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._searches_since_write = 0
        ensure_runtime_directories(settings.paths)
        self.client = PersistentClient(path=str(settings.paths.memory_dir))
        ef = _make_embedding_function()
        if ef is not None:
            logger.warning("onnxruntime unavailable — using hash embedding fallback (semantic search degraded)")
        collection_name = self._collection_name(settings.paths.project_root)
        try:
            self.collection = self.client.get_or_create_collection(
                collection_name,
                embedding_function=ef,
            )
        except Exception:
            self.client.delete_collection(collection_name)
            self.collection = self.client.get_or_create_collection(
                collection_name,
                embedding_function=ef,
            )
        self.relations = RelationsStore(settings.paths.memory_dir / "relations.db")
        self._ensure_metadata_defaults()

    def save_memory(
        self,
        *,
        content: str,
        title: str,
        memory_type: MemoryType,
        topic_key: str | None = None,
        scope: MemoryScope = MemoryScope.PROJECT,
        agent_source: str | None = None,
    ) -> SaveResult:
        """Persist a memory observation.

        Handles creation, updates (by topic_key), duplicate detection (by content hash),
        and conflict detection (BM25 on existing memories).
        """
        self._validate_content(content)
        self._validate_title(title)
        validated_topic_key = self._validate_topic_key(topic_key)
        now = self._now()
        content_hash = self._content_hash(content)
        document_id = str(uuid5(NAMESPACE_URL, validated_topic_key)) if validated_topic_key else str(uuid4())
        status = "created"
        revision_count = 1
        original_timestamp = now.isoformat()
        original_last_accessed = now.isoformat()
        self._reset_search_nudge()

        if validated_topic_key:
            existing = self.collection.get(
                where=self._active_where({"topic_key": validated_topic_key}),
                limit=1,
                include=["metadatas"],
            )
            if existing["ids"]:
                document_id = existing["ids"][0]
                existing_meta = dict(existing["metadatas"][0])
                if existing_meta.get("content_hash") == content_hash:
                    existing_meta["duplicate_count"] = int(existing_meta.get("duplicate_count", 1)) + 1
                    existing_meta["last_seen_at"] = now.isoformat()
                    self.collection.update(ids=[document_id], metadatas=[existing_meta])
                    logger.debug("memory_save topic-duplicate id=%s", document_id)
                    return SaveResult(id=document_id, topic_key=validated_topic_key, status="duplicate", timestamp=now, revision_count=int(existing_meta.get("revision_count", 1)))
                else:
                    status = "updated"
                    revision_count = int(existing_meta.get("revision_count", 1)) + 1
                    original_timestamp = str(existing_meta.get("timestamp", now.isoformat()))
                    original_last_accessed = str(existing_meta.get("last_accessed_at", now.isoformat()))

        if status == "created":
            duplicate = self.collection.get(
                where=self._active_where({"content_hash": content_hash}),
                include=["metadatas"],
                limit=1,
            )
            if duplicate["ids"]:
                dup_id = duplicate["ids"][0]
                dup_meta = dict(duplicate["metadatas"][0])
                dup_meta["duplicate_count"] = int(dup_meta.get("duplicate_count", 1)) + 1
                dup_meta["last_seen_at"] = now.isoformat()
                self.collection.update(ids=[dup_id], metadatas=[dup_meta])
                logger.debug("memory_save global-duplicate id=%s hash=%s", dup_id, content_hash)
                return SaveResult(
                    id=dup_id,
                    topic_key=dup_meta.get("topic_key"),
                    status="duplicate",
                    timestamp=now,
                )

        metadata: dict[str, object] = {
            "title": title,
            "type": memory_type.value,
            "topic_key": validated_topic_key,
            "scope": scope.value,
            "timestamp": original_timestamp,
            "agent_source": agent_source or detect_agent_source(),
            "deleted_at": "",
            "content_hash": content_hash,
            "duplicate_count": 1,
            "last_seen_at": now.isoformat(),
            "revision_count": revision_count,
            "updated_at": now.isoformat(),
            "last_accessed_at": original_last_accessed,
        }
        self.collection.upsert(ids=[document_id], documents=[content], metadatas=[metadata])

        conflicts = self._bm25_candidates(content, exclude_id=document_id)

        logger.debug(
            "memory_save id=%s topic=%s status=%s conflicts=%d",
            document_id, validated_topic_key, status, len(conflicts),
        )
        return SaveResult(id=document_id, topic_key=validated_topic_key, status=status, timestamp=now, revision_count=revision_count, conflicts=conflicts)

    def get_memory(self, id: str) -> ContextEntry:
        """Fetch full content of a single active (non-deleted) memory by ID.

        Raises KeyError if not found or soft-deleted.
        """
        result = self.collection.get(ids=[id], include=["documents", "metadatas"])
        if not result["ids"]:
            raise KeyError(id)
        metadata = result["metadatas"][0]
        if str(metadata.get("deleted_at", "")):
            raise KeyError(id)
        return self._build_memory_entry(item_id=id, document=result["documents"][0], metadata=metadata)

    def search_memories(
        self,
        *,
        query: str,
        limit: int = 5,
        type_filter: MemoryType | None = None,
        keyword: str | None = None,
        snippet_only: bool = False,
        include_personal: bool = False,
    ) -> SearchResponse:
        """Semantic search across stored memories.

        Uses ChromaDB vector similarity. Returns optional nudge when search
        is called repeatedly without writing.
        """
        if not query or len(query) > 1_000:
            raise ValueError("query must be non-empty and at most 1000 characters")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if keyword is not None and (not keyword or len(keyword) > 1_000):
            raise ValueError("keyword must be non-empty and at most 1000 characters")

        filters: list[dict[str, object]] = []
        if type_filter:
            filters.append({"type": type_filter.value})
        if not include_personal:
            filters.append({"scope": {"$ne": "personal"}})
        where = self._active_where(*filters)

        result = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
            where_document={"$contains": keyword} if keyword else None,
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        items: list[SearchResult] = []
        for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            entry = self._build_memory_entry(item_id=item_id, document=document, metadata=metadata)
            content_out = document[:200] if snippet_only and len(document) > 200 else document
            items.append(
                SearchResult(
                    id=entry.id,
                    title=entry.title,
                    content=content_out,
                    type=entry.type,
                    topic_key=entry.topic_key,
                    score=self._distance_to_score(float(distance)),
                    timestamp=entry.timestamp,
                    agent_source=entry.agent_source,
                )
            )
        logger.debug("memory_search query=%r limit=%d results=%d", query[:60], limit, len(items))
        self._searches_since_write += 1
        nudge = self.SEARCH_NUDGE_MESSAGE if self._searches_since_write > self.SEARCH_NUDGE_THRESHOLD else None
        return SearchResponse(results=items, nudge=nudge)

    def recall_memory(self, topic_key: str) -> RecallResult:
        """Recall the most recent active memory for a topic_key.

        Updates last_accessed_at. Returns found=False if no active memory exists.
        """
        validated_topic_key = self._validate_topic_key(topic_key)
        result = self.collection.get(where=self._active_where({"topic_key": validated_topic_key}), limit=1, include=["documents", "metadatas"])
        if not result["ids"]:
            return RecallResult(found=False, topic_key=validated_topic_key)

        item_id = result["ids"][0]
        metadata = dict(result["metadatas"][0])

        metadata["last_accessed_at"] = self._now().isoformat()
        self.collection.update(ids=[item_id], metadatas=[metadata])

        entry = self._build_memory_entry(item_id=item_id, document=result["documents"][0], metadata=metadata)
        return RecallResult(
            found=True,
            topic_key=validated_topic_key,
            id=entry.id,
            title=entry.title,
            content=entry.content,
            type=entry.type,
            timestamp=entry.timestamp,
            agent_source=entry.agent_source,
        )

    def recent_context(self, *, n: int = 10) -> ContextResult:
        """Return up to n most recent active memories (reverse chronological)."""
        if not 1 <= n <= 50:
            raise ValueError("n must be between 1 and 50")

        result = self.collection.get(where=self._active_where(), include=["documents", "metadatas"])
        entries: list[ContextEntry] = []
        for item_id, document, metadata in zip(
            result["ids"],
            result["documents"],
            result["metadatas"],
            strict=False,
        ):
            entries.append(self._build_memory_entry(item_id=item_id, document=document, metadata=metadata))
        entries.sort(key=lambda item: item.timestamp, reverse=True)
        return ContextResult(count=min(n, len(entries)), memories=entries[:n])

    def delete_memory(self, *, id: str, hard_delete: bool = False) -> dict[str, str | bool]:
        """Delete a memory by ID.

        Soft delete (default): sets deleted_at timestamp, memory remains queryable by ID.
        Hard delete: permanently removes from ChromaDB.
        """
        result = self.collection.get(ids=[id], include=["metadatas"])
        if not result["ids"]:
            raise KeyError(id)

        if hard_delete:
            self.collection.delete(ids=[id])
        else:
            metadata = dict(result["metadatas"][0])
            metadata["deleted_at"] = self._now().isoformat()
            self.collection.update(ids=[id], metadatas=[metadata])

        logger.debug("memory_delete id=%s hard_delete=%s", id, hard_delete)
        return {"id": id, "status": "deleted", "hard_delete": hard_delete}

    def memory_stats(self) -> dict[str, object]:
        """Return aggregate counts: total, by_type, by_scope, by_agent."""
        result = self.collection.get(where=self._active_where(), include=["metadatas"])
        by_type: Counter[str] = Counter({t.value: 0 for t in MemoryType})
        by_scope: Counter[str] = Counter({s.value: 0 for s in MemoryScope})
        by_agent: Counter[str] = Counter()

        for metadata in result["metadatas"]:
            by_type[str(metadata["type"])] += 1
            by_scope[str(metadata["scope"])] += 1
            by_agent[str(metadata["agent_source"])] += 1

        return {
            "total": len(result["ids"]),
            "by_type": dict(by_type),
            "by_scope": dict(by_scope),
            "by_agent": dict(by_agent),
        }

    def memory_timeline(self, *, id: str, before: int = 5, after: int = 5) -> TimelineResult:
        """Return memories surrounding a focus memory (before + after).

        Sorted chronologically. Raises KeyError if focus ID not found.
        """
        if not 0 <= before <= 20:
            raise ValueError("before must be between 0 and 20")
        if not 0 <= after <= 20:
            raise ValueError("after must be between 0 and 20")

        result = self.collection.get(where=self._active_where(), include=["documents", "metadatas"])
        entries = [
            self._build_memory_entry(item_id=item_id, document=document, metadata=metadata)
            for item_id, document, metadata in zip(
                result["ids"],
                result["documents"],
                result["metadatas"],
                strict=False,
            )
        ]
        entries.sort(key=lambda item: item.timestamp)

        for index, entry in enumerate(entries):
            if entry.id != id:
                continue
            return TimelineResult(
                focus=self._build_timeline_entry(entry, is_focus=True),
                before=[self._build_timeline_entry(item, is_focus=False) for item in entries[max(0, index - before) : index]],
                after=[
                    self._build_timeline_entry(item, is_focus=False)
                    for item in reversed(entries[index + 1 : index + 1 + after])
                ],
            )

        raise KeyError(id)

    def save_session_summary(self, *, summary: str, agent_source: str | None = None) -> SaveResult:
        """Persist a session summary as type=summary, scope=session."""
        timestamp = self._now()
        title = f"Session summary - {timestamp.isoformat()}"
        return self.save_memory(
            content=summary,
            title=title,
            memory_type=MemoryType.SUMMARY,
            topic_key=None,
            scope=MemoryScope.SESSION,
            agent_source=agent_source,
        )

    def start_session(self, *, agent_source: str | None = None) -> SessionStartResult:
        """Start a new session: saves context entry and returns recent project memories.

        Returns session_id and up to _SESSION_CONTEXT_LIMIT high-value memories.
        """
        started_at = self._now()
        session_id = uuid4().hex
        self.save_memory(
            content=f"Session started at {started_at.isoformat()}",
            title=f"Session start - {session_id[:8]}",
            memory_type=MemoryType.CONTEXT,
            topic_key=f"session-start-{session_id[:8]}",
            scope=MemoryScope.SESSION,
            agent_source=agent_source,
        )
        context = self._load_session_context(types=_SESSION_CONTEXT_TYPES, limit=_SESSION_CONTEXT_LIMIT)
        return SessionStartResult(session_id=session_id, started_at=started_at, context=context)

    def judge_memory(
        self,
        *,
        source_id: str,
        target_id: str,
        verdict: RelationVerdict,
        reason: str | None = None,
    ) -> JudgeResult:
        """Record an agent verdict on the relationship between two memories.

        Validates both IDs exist. Upserts into SQLite relations store.
        """
        self.get_memory(source_id)
        self.get_memory(target_id)

        relation_id, is_new = self.relations.upsert(
            source_id=source_id,
            target_id=target_id,
            verdict=verdict.value,
            reason=reason or "",
            agent_source=detect_agent_source(),
        )
        logger.debug("memory_judge %s->%s verdict=%s new=%s", source_id, target_id, verdict, is_new)
        return JudgeResult(
            source_id=source_id,
            target_id=target_id,
            verdict=verdict,
            status="created" if is_new else "updated",
            is_new=is_new,
        )

    def prune_memories(self, *, scope: MemoryScope, older_than_days: int) -> PruneResult:
        """Soft-delete active memories of the given scope older than N days.

        Sets deleted_at timestamp on matching memories.
        """
        if not 1 <= older_than_days <= 3650:
            raise ValueError("older_than_days must be between 1 and 3650")

        cutoff = self._now() - timedelta(days=older_than_days)
        result = self.collection.get(
            where=self._active_where({"scope": scope.value}),
            include=["metadatas"],
        )

        ids_to_prune: list[str] = []
        metas_to_update: list[dict] = []
        now_iso = self._now().isoformat()

        for item_id, metadata in zip(result["ids"], result["metadatas"], strict=False):
            ts_str = str(metadata.get("updated_at") or metadata.get("timestamp", ""))
            if not ts_str:
                continue
            try:
                ts = self._parse_timestamp(ts_str)
            except ValueError:
                continue
            if ts < cutoff:
                updated_meta = dict(metadata)
                updated_meta["deleted_at"] = now_iso
                ids_to_prune.append(item_id)
                metas_to_update.append(updated_meta)

        if ids_to_prune:
            self.collection.update(ids=ids_to_prune, metadatas=metas_to_update)

        logger.debug("memory_prune scope=%s older_than=%d pruned=%d", scope, older_than_days, len(ids_to_prune))
        return PruneResult(pruned=len(ids_to_prune), scope=scope, older_than_days=older_than_days)

    def _load_session_context(self, *, types: list[MemoryType], limit: int) -> list[ContextEntry]:
        """Return recent project-scoped memories of high-value types for session injection."""
        type_values = [t.value for t in types]
        result = self.collection.get(
            where=self._active_where(
                {"scope": "project"},
                {"type": {"$in": type_values}},
            ),
            include=["documents", "metadatas"],
        )
        entries = [
            self._build_memory_entry(item_id=item_id, document=doc, metadata=meta)
            for item_id, doc, meta in zip(result["ids"], result["documents"], result["metadatas"], strict=False)
        ]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def _bm25_candidates(self, content: str, *, exclude_id: str) -> list[ConflictCandidate]:
        """Return up to _CONFLICT_CANDIDATES_LIMIT existing memories most similar to content (BM25)."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.debug("rank_bm25 not available; skipping conflict detection")
            return []

        result = self.collection.get(where=self._active_where(), include=["documents", "metadatas"])
        candidates = [
            (item_id, doc, meta)
            for item_id, doc, meta in zip(result["ids"], result["documents"], result["metadatas"], strict=False)
            if item_id != exclude_id
        ]
        if not candidates:
            return []

        cand_ids, cand_docs, cand_metas = zip(*candidates, strict=False)
        corpus_texts = [f"{m['title']} {d}" for d, m in zip(cand_docs, cand_metas)]
        tokenized = [text.lower().split() for text in corpus_texts]
        bm25 = BM25Okapi(tokenized)

        query_tokens = content.lower().split()
        scores = bm25.get_scores(query_tokens)

        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[ConflictCandidate] = []
        for idx, score in indexed[:_CONFLICT_CANDIDATES_LIMIT]:
            if score <= 0.0:
                break
            results.append(ConflictCandidate(
                id=cand_ids[idx],
                title=str(cand_metas[idx]["title"]),
                score=round(float(score), 4),
            ))
        return results

    @staticmethod
    def _collection_name(project_root: Path) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", project_root.name.lower()).strip("-") or "project"
        return f"{slug}_memories"

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        return 1.0 / (1.0 + max(distance, 0.0))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _build_memory_entry(*, item_id: str, document: str, metadata: dict) -> ContextEntry:
        updated_at_str = str(metadata.get("updated_at", ""))
        last_accessed_str = str(metadata.get("last_accessed_at", ""))
        return ContextEntry(
            id=item_id,
            title=str(metadata["title"]),
            content=document,
            type=MemoryType(str(metadata["type"])),
            scope=MemoryScope(str(metadata["scope"])),
            topic_key=metadata.get("topic_key"),
            timestamp=MemoryStore._parse_timestamp(str(metadata["timestamp"])),
            agent_source=str(metadata["agent_source"]),
            revision_count=int(metadata.get("revision_count", 1)),
            updated_at=MemoryStore._parse_timestamp(updated_at_str) if updated_at_str else None,
            last_accessed_at=MemoryStore._parse_timestamp(last_accessed_str) if last_accessed_str else None,
        )

    @staticmethod
    def _build_timeline_entry(entry: ContextEntry, *, is_focus: bool) -> TimelineEntry:
        return TimelineEntry(**entry.model_dump(), is_focus=is_focus)

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content or len(content) > 10_000:
            raise ValueError("content must be non-empty and at most 10000 characters")

    @staticmethod
    def _validate_title(title: str) -> None:
        if not title or len(title) > 200:
            raise ValueError("title must be non-empty and at most 200 characters")

    @staticmethod
    def _validate_topic_key(topic_key: str | None) -> str | None:
        if topic_key is None:
            return None
        if len(topic_key) > 100 or not TOPIC_KEY_PATTERN.fullmatch(topic_key):
            raise ValueError("topic_key must match [a-z0-9-]+ and be at most 100 characters")
        return topic_key

    def _ensure_metadata_defaults(self) -> None:
        result = self.collection.get(include=["documents", "metadatas"])
        ids_to_update: list[str] = []
        metadatas_to_update: list[dict] = []
        for item_id, document, metadata in zip(
            result["ids"],
            result["documents"],
            result["metadatas"],
            strict=False,
        ):
            updated_metadata = dict(metadata)
            changed = False
            if "deleted_at" not in updated_metadata:
                updated_metadata["deleted_at"] = ""
                changed = True
            if updated_metadata.get("scope") == "global":
                updated_metadata["scope"] = MemoryScope.PERSONAL.value
                changed = True
            if "content_hash" not in updated_metadata:
                updated_metadata["content_hash"] = self._content_hash(document)
                changed = True
            if "duplicate_count" not in updated_metadata:
                updated_metadata["duplicate_count"] = 1
                changed = True
            if "last_seen_at" not in updated_metadata:
                updated_metadata["last_seen_at"] = str(updated_metadata["timestamp"])
                changed = True
            if "revision_count" not in updated_metadata:
                updated_metadata["revision_count"] = 1
                changed = True
            if "updated_at" not in updated_metadata:
                updated_metadata["updated_at"] = str(updated_metadata["timestamp"])
                changed = True
            if "last_accessed_at" not in updated_metadata:
                updated_metadata["last_accessed_at"] = str(updated_metadata["timestamp"])
                changed = True
            if changed:
                ids_to_update.append(item_id)
                metadatas_to_update.append(updated_metadata)

        if ids_to_update:
            self.collection.update(ids=ids_to_update, metadatas=metadatas_to_update)

    @staticmethod
    def _content_hash(content: str) -> str:
        normalized = content.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _reset_search_nudge(self) -> None:
        self._searches_since_write = 0

    @staticmethod
    def _active_where(*filters: dict[str, object]) -> dict[str, object]:
        """Build a ChromaDB where clause combining all filters with active (non-deleted) guard."""
        all_filters: list[dict[str, object]] = [*filters, {"deleted_at": ""}]
        if len(all_filters) == 1:
            return all_filters[0]
        return {"$and": list(all_filters)}
