"""Update orchestrator for nerv update command."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from nerv.init.context import ProjectContext
from nerv.init.detector import detect_stack
from nerv.init.registry import write_registry
from nerv.init.renderer import TemplateEngine
from nerv.init.writer import validate_markers, write_file, MARKER_START, MARKER_END


class UpdateStrategy(StrEnum):
    """Strategy for updating files."""

    MARKER_MERGE = "marker_merge"
    JSON_MERGE = "json_merge"
    OVERWRITE = "overwrite"
    SKIP_DEFAULT = "skip_default"
    CREATE_IF_MISSING = "create_if_missing"


_ONLY_CATEGORY_ALIASES: dict[str, UpdateStrategy] = {
    "marker-merge": UpdateStrategy.MARKER_MERGE,
    "marker_merge": UpdateStrategy.MARKER_MERGE,
    "json-merge": UpdateStrategy.JSON_MERGE,
    "json_merge": UpdateStrategy.JSON_MERGE,
    "overwrite": UpdateStrategy.OVERWRITE,
    "skip-default": UpdateStrategy.SKIP_DEFAULT,
    "skip_default": UpdateStrategy.SKIP_DEFAULT,
    "create-if-missing": UpdateStrategy.CREATE_IF_MISSING,
    "create_if_missing": UpdateStrategy.CREATE_IF_MISSING,
}


@dataclass(frozen=True)
class UpdateEntry:
    """Entry in the file update manifest."""

    template_name: str
    output_path: str
    strategy: UpdateStrategy
    make_executable: bool = False


@dataclass
class UpdateResult:
    """Result of updating a single file."""

    path: str
    strategy: UpdateStrategy
    result: str
    warning: str | None = None


@dataclass
class UpdateSummary:
    """Summary of update operation."""

    results: list[UpdateResult] = field(default_factory=list)

    @property
    def updated_count(self) -> int:
        return sum(1 for r in self.results if r.result in ("CREATED", "UPDATED", "OVERWRITTEN"))

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.result == "SKIPPED")

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.result == "ERROR")


FILE_UPDATE_MANIFEST: list[UpdateEntry] = [
    UpdateEntry("nerv/a2a-config.yaml.j2", ".nerv/a2a-config.yaml", UpdateStrategy.OVERWRITE),
    UpdateEntry("opencode/AGENTS.md.j2", "AGENTS.md", UpdateStrategy.CREATE_IF_MISSING),
    UpdateEntry("opencode/skills/code/SKILL.md.j2", ".nerv/skills/code/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/testing/SKILL.md.j2", ".nerv/skills/testing/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/commits/SKILL.md.j2", ".nerv/skills/commits/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("mcp.json.j2", "mcp.json", UpdateStrategy.JSON_MERGE),
    UpdateEntry("githooks/pre-push.py.j2", ".githooks/pre-push", UpdateStrategy.OVERWRITE, make_executable=True),
    UpdateEntry("opencode/skills/sdd-explore/SKILL.md.j2", ".nerv/skills/sdd-explore/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-propose/SKILL.md.j2", ".nerv/skills/sdd-propose/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-spec/SKILL.md.j2", ".nerv/skills/sdd-spec/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-design/SKILL.md.j2", ".nerv/skills/sdd-design/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-tasks/SKILL.md.j2", ".nerv/skills/sdd-tasks/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-apply/SKILL.md.j2", ".nerv/skills/sdd-apply/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-verify/SKILL.md.j2", ".nerv/skills/sdd-verify/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/sdd-archive/SKILL.md.j2", ".nerv/skills/sdd-archive/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
    UpdateEntry("opencode/skills/judgment-day/SKILL.md.j2", ".nerv/skills/judgment-day/SKILL.md", UpdateStrategy.SKIP_DEFAULT),
]


def deep_merge_json(base: dict, overlay: dict) -> dict:
    """Merge overlay into base. overlay wins on key conflicts. Recursive for nested dicts."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_json(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_only_category(only: str) -> UpdateStrategy:
    normalized = only.strip().lower().replace(" ", "-")
    normalized = normalized.replace("_", "-")
    if normalized == "all":
        raise ValueError("Internal error: 'all' is not a selectable category")
    try:
        return _ONLY_CATEGORY_ALIASES[normalized]
    except KeyError as exc:
        allowed = ", ".join(["all", "marker-merge", "json-merge", "overwrite", "skip-default", "create-if-missing"])
        raise ValueError(f"Unknown update category: {only}. Allowed values: {allowed}") from exc


def _select_manifest_entries(only: str | None) -> list[UpdateEntry]:
    if only is None or only.strip().lower() == "all":
        return FILE_UPDATE_MANIFEST
    strategy = _resolve_only_category(only)
    return [entry for entry in FILE_UPDATE_MANIFEST if entry.strategy == strategy]


def run_update(
    root: Path,
    dry_run: bool = False,
    force_commands: bool = False,
    only: str | None = None,
) -> int:
    try:
        stack_info = detect_stack(root, stack_override=None)
        context = ProjectContext.build(
            project_name=stack_info.project_name,
            stack=stack_info.stack,
        )

        templates_dir = Path(__file__).parent / "templates"
        engine = TemplateEngine(templates_dir)

        summary = UpdateSummary()
        entries = _select_manifest_entries(only)

        for entry in entries:
            result = _process_entry(entry, root, engine, context, dry_run, force_commands)
            summary.results.append(result)
            _print_result(result, dry_run)

        _print_summary(summary, dry_run)

        if not dry_run:
            try:
                registry_path = write_registry(root)
                print(f"✓ Updated {registry_path.relative_to(root)}")
            except Exception as exc:
                print(f"⚠ Skill registry not written: {exc}")

        return 1 if summary.error_count > 0 else 0

    except Exception as exc:
        print(f"✗ Fatal error: {exc}")
        return 1


def _process_entry(
    entry: UpdateEntry,
    root: Path,
    engine: TemplateEngine,
    context: ProjectContext,
    dry_run: bool,
    force_commands: bool,
) -> UpdateResult:
    try:
        content = engine.render(entry.template_name, context.to_dict())
        target = root / entry.output_path

        if entry.strategy == UpdateStrategy.MARKER_MERGE:
            return _handle_marker_merge(entry, target, content, dry_run)
        elif entry.strategy == UpdateStrategy.JSON_MERGE:
            return _handle_json_merge(entry, target, content, dry_run)
        elif entry.strategy == UpdateStrategy.OVERWRITE:
            return _handle_overwrite(entry, target, content, dry_run)
        elif entry.strategy == UpdateStrategy.SKIP_DEFAULT:
            return _handle_skip_default(entry, target, content, dry_run, force_commands)
        elif entry.strategy == UpdateStrategy.CREATE_IF_MISSING:
            return _handle_create_if_missing(entry, target, content, dry_run)
        else:
            return UpdateResult(entry.output_path, entry.strategy, "ERROR", warning=f"Unknown strategy: {entry.strategy}")

    except Exception as exc:
        return UpdateResult(entry.output_path, entry.strategy, "ERROR", warning=str(exc))


def _handle_marker_merge(entry: UpdateEntry, target: Path, content: str, dry_run: bool) -> UpdateResult:
    content_clean = content
    if MARKER_START in content and MARKER_END in content:
        start_idx = content.find(MARKER_START)
        end_idx = content.find(MARKER_END)
        if start_idx != -1 and end_idx != -1:
            start_line_end = content.find("\n", start_idx)
            if start_line_end != -1:
                content_clean = content[start_line_end + 1 : end_idx].rstrip()

    if not target.exists():
        if not dry_run:
            result = write_file(target, content_clean, force=False, use_markers=True, make_executable=entry.make_executable)
            return UpdateResult(entry.output_path, entry.strategy, result.upper())
        else:
            return UpdateResult(entry.output_path, entry.strategy, "CREATED")

    existing_content = target.read_text(encoding="utf-8")
    warnings = validate_markers(existing_content)

    for warning in warnings:
        print(f"⚠ {entry.output_path}: {warning}", flush=True)

    if MARKER_START in existing_content and MARKER_END in existing_content:
        if not dry_run:
            result = write_file(target, content_clean, force=False, use_markers=True, make_executable=entry.make_executable)
            return UpdateResult(entry.output_path, entry.strategy, result.upper(), warning=warnings[0] if warnings else None)
        else:
            return UpdateResult(entry.output_path, entry.strategy, "UPDATED", warning=warnings[0] if warnings else None)
    else:
        return UpdateResult(entry.output_path, entry.strategy, "SKIPPED", warning="No markers found")


def _handle_json_merge(entry: UpdateEntry, target: Path, content: str, dry_run: bool) -> UpdateResult:
    try:
        try:
            template_data = json.loads(content)
        except json.JSONDecodeError as e:
            return UpdateResult(entry.output_path, entry.strategy, "ERROR", warning=f"Invalid JSON in template: {e}")

        if not target.exists():
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(template_data, indent=4) + "\n", encoding="utf-8")
            return UpdateResult(entry.output_path, entry.strategy, "CREATED")

        try:
            existing_data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return UpdateResult(entry.output_path, entry.strategy, "ERROR", warning=f"Invalid JSON in existing file: {e}")

        merged = deep_merge_json(existing_data, template_data)

        if not dry_run:
            target.write_text(json.dumps(merged, indent=4) + "\n", encoding="utf-8")

        return UpdateResult(entry.output_path, entry.strategy, "UPDATED")

    except Exception as exc:
        return UpdateResult(entry.output_path, entry.strategy, "ERROR", warning=str(exc))


def _handle_overwrite(entry: UpdateEntry, target: Path, content: str, dry_run: bool) -> UpdateResult:
    if not dry_run:
        result = write_file(target, content, force=True, use_markers=False, make_executable=entry.make_executable)
        return UpdateResult(entry.output_path, entry.strategy, result.upper())
    else:
        if target.exists():
            return UpdateResult(entry.output_path, entry.strategy, "OVERWRITTEN")
        else:
            return UpdateResult(entry.output_path, entry.strategy, "CREATED")


def _handle_skip_default(entry: UpdateEntry, target: Path, content: str, dry_run: bool, force_commands: bool) -> UpdateResult:
    if not force_commands:
        return UpdateResult(entry.output_path, entry.strategy, "SKIPPED", warning="use --force-commands to update")
    else:
        return _handle_overwrite(entry, target, content, dry_run)


def _handle_create_if_missing(entry: UpdateEntry, target: Path, content: str, dry_run: bool) -> UpdateResult:
    if target.exists():
        return UpdateResult(entry.output_path, entry.strategy, "SKIPPED")

    if not dry_run:
        result = write_file(target, content, force=False, use_markers=False, make_executable=entry.make_executable)
        return UpdateResult(entry.output_path, entry.strategy, result.upper())

    return UpdateResult(entry.output_path, entry.strategy, "CREATED")


def _print_result(result: UpdateResult, dry_run: bool):
    prefix = "[DRY RUN] " if dry_run else ""
    if result.result == "CREATED":
        print(f"{prefix}✓ Created {result.path}")
    elif result.result == "UPDATED":
        print(f"{prefix}✓ Updated {result.path}")
    elif result.result == "OVERWRITTEN":
        print(f"{prefix}✓ Overwritten {result.path}")
    elif result.result == "SKIPPED":
        print(f"{prefix}⊘ Skipped {result.path}")
    elif result.result == "ERROR":
        print(f"{prefix}✗ Error {result.path}: {result.warning}")


def _print_summary(summary: UpdateSummary, dry_run: bool):
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Done. ✓ {summary.updated_count} updated / ⊘ {summary.skipped_count} skipped", end="")
    if summary.error_count > 0:
        print(f" / ✗ {summary.error_count} errors")
    else:
        print()
