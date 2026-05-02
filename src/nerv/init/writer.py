"""File writing with conflict resolution."""

from __future__ import annotations

import os
import subprocess
from enum import StrEnum
from pathlib import Path

MARKER_START = "<!-- NERV:START -->"
MARKER_END = "<!-- NERV:END -->"


def validate_markers(content: str) -> list[str]:
    """Return list of warning strings for malformed markers. Empty = clean."""
    warnings = []
    start_count = content.count(MARKER_START)
    end_count = content.count(MARKER_END)
    if start_count != end_count:
        warnings.append(
            f"Mismatched markers: {start_count} START, {end_count} END. "
            "Only the first balanced pair will be updated."
        )
    elif start_count > 1:
        warnings.append(
            f"Multiple marker pairs ({start_count}) detected. "
            "Only the first pair will be updated."
        )
    return warnings


class WriteResult(StrEnum):
    """Result of file write operation."""

    CREATED = "created"
    SKIPPED = "skipped"
    OVERWRITTEN = "overwritten"
    UPDATED = "updated"


def _strip_markers(content: str) -> str:
    """Extract inner content if markers are present, otherwise return as-is."""
    if MARKER_START not in content or MARKER_END not in content:
        return content
    start_idx = content.find(MARKER_START)
    end_idx = content.find(MARKER_END)
    start_line_end = content.find("\n", start_idx)
    if start_line_end == -1 or end_idx <= start_line_end:
        return content
    return content[start_line_end + 1 : end_idx].rstrip()


def write_file(
    path: Path,
    content: str,
    force: bool = False,
    use_markers: bool = False,
    make_executable: bool = False,
) -> WriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)

    if use_markers:
        content = _strip_markers(content)

    if not path.exists():
        if use_markers:
            final_content = f"{MARKER_START}\n{content}\n{MARKER_END}\n"
        else:
            final_content = content
        path.write_text(final_content, encoding="utf-8")
        if make_executable:
            os.chmod(path, 0o755)
        return WriteResult.CREATED

    existing_content = path.read_text(encoding="utf-8")

    if use_markers:
        if MARKER_START in existing_content and MARKER_END in existing_content:
            updated_content = _replace_between_markers(existing_content, content)
            path.write_text(updated_content, encoding="utf-8")
            if make_executable:
                os.chmod(path, 0o755)
            return WriteResult.UPDATED
        elif force:
            final_content = f"{MARKER_START}\n{content}\n{MARKER_END}\n"
            path.write_text(final_content, encoding="utf-8")
            if make_executable:
                os.chmod(path, 0o755)
            return WriteResult.OVERWRITTEN
        else:
            return WriteResult.SKIPPED
    else:
        if force:
            path.write_text(content, encoding="utf-8")
            if make_executable:
                os.chmod(path, 0o755)
            return WriteResult.OVERWRITTEN
        else:
            return WriteResult.SKIPPED


def _replace_between_markers(text: str, new_content: str) -> str:
    """Replace content between MARKER_START and MARKER_END."""
    start_pos = text.find(MARKER_START)
    end_pos = text.find(MARKER_END)

    if start_pos == -1 or end_pos == -1:
        return text

    start_line_end = text.find("\n", start_pos)
    if start_line_end == -1:
        start_line_end = len(text)

    before = text[: start_line_end + 1]
    after = text[end_pos:]

    return f"{before}{new_content}\n{after}"


def configure_git_hooks(root: Path) -> bool:
    git_dir = root / ".git"
    if not git_dir.exists():
        return False

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
