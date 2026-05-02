from __future__ import annotations

import os
from pathlib import Path

from nerv.config import RuntimeSettings
from nerv.models.memory import MemoryScope, MemoryType, RelationVerdict
from nerv.mcp.memory_store import MemoryStore
from nerv.mcp.shared import build_mcp_server, detect_agent_source, resolve_runtime_settings, result_payload


class MemoryService:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.store = MemoryStore(settings)

    def memory_save(
        self,
        *,
        content: str,
        title: str,
        type: str,
        topic_key: str | None = None,
        scope: str = "project",
    ) -> dict:
        return result_payload(
            self.store.save_memory(
                content=content,
                title=title,
                memory_type=MemoryType(type),
                topic_key=topic_key,
                scope=MemoryScope(scope),
                agent_source=detect_agent_source(),
            )
        )

    def memory_get(self, *, id: str) -> dict:
        return result_payload(self.store.get_memory(id))

    def memory_search(
        self,
        *,
        query: str,
        limit: int = 5,
        type_filter: str | None = None,
        keyword: str | None = None,
        snippet_only: bool = False,
        include_personal: bool = False,
    ) -> dict:
        return result_payload(
            self.store.search_memories(
                query=query,
                limit=limit,
                type_filter=MemoryType(type_filter) if type_filter else None,
                keyword=keyword,
                snippet_only=snippet_only,
                include_personal=include_personal,
            )
        )

    def memory_recall(self, *, topic_key: str) -> dict:
        return result_payload(self.store.recall_memory(topic_key))

    def memory_context(self, *, n: int = 10) -> dict:
        return result_payload(self.store.recent_context(n=n))

    def memory_session_summary(self, *, summary: str) -> dict:
        return result_payload(self.store.save_session_summary(summary=summary, agent_source=detect_agent_source()))

    def memory_session_start(self) -> dict:
        return result_payload(self.store.start_session(agent_source=detect_agent_source()))

    def memory_delete(self, *, id: str, hard_delete: bool = False) -> dict:
        return result_payload(self.store.delete_memory(id=id, hard_delete=hard_delete))

    def memory_stats(self) -> dict:
        return result_payload(self.store.memory_stats())

    def memory_timeline(self, *, id: str, before: int = 5, after: int = 5) -> dict:
        return result_payload(self.store.memory_timeline(id=id, before=before, after=after))

    def memory_judge(self, *, source_id: str, target_id: str, verdict: str, reason: str | None = None) -> dict:
        return result_payload(
            self.store.judge_memory(
                source_id=source_id,
                target_id=target_id,
                verdict=RelationVerdict(verdict),
                reason=reason,
            )
        )

    def memory_prune(self, *, scope: str, older_than_days: int) -> dict:
        return result_payload(
            self.store.prune_memories(
                scope=MemoryScope(scope),
                older_than_days=older_than_days,
            )
        )


def build_memory_server(project_root: Path | None = None):
    settings = resolve_runtime_settings(project_root)
    service = MemoryService(settings)
    server = build_mcp_server(
        "nerv-memory",
        "Shared persistent memory for agent interactions.",
        settings,
    )
    profile = os.environ.get("NERV_MEMORY_PROFILE", "full")

    @server.tool(description="Persist a memory observation to project-local ChromaDB.")
    async def memory_save(
        content: str,
        title: str,
        type: str,
        topic_key: str | None = None,
        scope: str = "project",
    ) -> dict:
        return service.memory_save(content=content, title=title, type=type, topic_key=topic_key, scope=scope)

    @server.tool(description="Fetch full content of a single active memory by ID.")
    async def memory_get(id: str) -> dict:
        return service.memory_get(id=id)

    @server.tool(description="Semantic search across stored engineering memories.")
    async def memory_search(
        query: str,
        limit: int = 5,
        type_filter: str | None = None,
        keyword: str | None = None,
        snippet_only: bool = False,
        include_personal: bool = False,
    ) -> dict:
        return service.memory_search(
            query=query,
            limit=limit,
            type_filter=type_filter,
            keyword=keyword,
            snippet_only=snippet_only,
            include_personal=include_personal,
        )

    @server.tool(description="Recall a single memory by topic key.")
    async def memory_recall(topic_key: str) -> dict:
        return service.memory_recall(topic_key=topic_key)

    @server.tool(description="Return recent memories in reverse chronological order.")
    async def memory_context(n: int = 10) -> dict:
        return service.memory_context(n=n)

    @server.tool(description="Persist a session summary as a memory of type summary.")
    async def memory_session_summary(summary: str) -> dict:
        return service.memory_session_summary(summary=summary)

    @server.tool(description="Persist a session-start context entry and return the new session id.")
    async def memory_session_start() -> dict:
        return service.memory_session_start()

    @server.tool(description="Return aggregate counts for active memories.")
    async def memory_stats() -> dict:
        return service.memory_stats()

    @server.tool(description="Return active memories surrounding a focus memory id.")
    async def memory_timeline(id: str, before: int = 5, after: int = 5) -> dict:
        return service.memory_timeline(id=id, before=before, after=after)

    @server.tool(description="Record an agent verdict on the relationship between two memories.")
    async def memory_judge(source_id: str, target_id: str, verdict: str, reason: str | None = None) -> dict:
        return service.memory_judge(source_id=source_id, target_id=target_id, verdict=verdict, reason=reason)

    @server.tool(description="Soft-delete memories of a given scope older than N days.")
    async def memory_prune(scope: str, older_than_days: int) -> dict:
        return service.memory_prune(scope=scope, older_than_days=older_than_days)

    if profile != "safe":
        @server.tool(description="Delete a stored memory by id, optionally removing it permanently.")
        async def memory_delete(id: str, hard_delete: bool = False) -> dict:
            return service.memory_delete(id=id, hard_delete=hard_delete)

    return server


def run_memory_server() -> None:
    build_memory_server().run()


def main() -> None:
    run_memory_server()
