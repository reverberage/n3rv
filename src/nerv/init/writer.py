"""Writer utilities for project scaffolding."""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger("nerv.init.writer")

MARKER_START = "# >>> NERV-MARKER-START"
MARKER_END = "# >>> NERV-MARKER-END"


class WriteResult(StrEnum):
    """Result of a write operation."""

    CREATED = "created"
    UPDATED = "updated"
    OVERWRITTEN = "overwritten"
    SKIPPED = "skipped"


def write_file(
    target: Path,
    content: str,
    *,
    force: bool = False,
    use_markers: bool = False,
    make_executable: bool = False,
) -> WriteResult:
    """Write content to target file.

    Args:
        target: Path to write to
        content: File content
        force: Overwrite existing files without checking markers
        use_markers: Check for MARKER_START/END markers before overwriting
        make_executable: chmod +x the file

    Returns:
        WriteResult indicating what happened
    """
    from nerv.init.update import MARKER_START, MARKER_END

    if target.exists() and not force:
        if use_markers:
            existing = target.read_text(encoding="utf-8")
            if MARKER_START in existing and MARKER_END in existing:
                start_idx = existing.find(MARKER_START)
                end_idx = existing.find(MARKER_END) + len(MARKER_END)
                before = existing[:start_idx]
                after = existing[end_idx:]
                new_content = f"{before}{MARKER_START}\n{content}\n{MARKER_END}{after}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(new_content, encoding="utf-8")
                return WriteResult.UPDATED
            return WriteResult.SKIPPED
        return WriteResult.SKIPPED

    existed = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)

    if use_markers and (not existed or force):
        content = f"{MARKER_START}\n{content}\n{MARKER_END}\n"

    target.write_text(content, encoding="utf-8")
    if make_executable:
        target.chmod(0o755)
    return WriteResult.OVERWRITTEN if existed else WriteResult.CREATED


def configure_git_hooks(root: Path) -> bool:
    """Configure git hooks for the project.

    Args:
        root: Project root directory

    Returns:
        True if hooks were configured, False otherwise
    """
    import subprocess

    git_dir = root / ".git"
    if not git_dir.is_dir():
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Create pre-push hook that delegates to .nerv/githooks/
    pre_push = hooks_dir / "pre-push"
    pre_push.write_text(
        "#!/bin/sh\n# NERV pre-push hook\nexec .nerv/githooks/pre-push\n",
        encoding="utf-8",
    )
    pre_push.chmod(0o755)

    # Create .githooks/pre-push wrapper
    githooks_dir = root / ".githooks"
    githooks_dir.mkdir(parents=True, exist_ok=True)
    wrapper = githooks_dir / "pre-push"
    if not wrapper.exists():
        wrapper.write_text(
            "#!/usr/bin/env python3\n# NERV pre-push hook\n# Add your checks here\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

    # Set core.hooksPath to .githooks
    subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks"],
        cwd=root,
        capture_output=True,
    )
    return True


def validate_markers(content: str) -> list[str]:
    """Check if content has valid marker pairs.

    Args:
        content: File content to check

    Returns:
        List of warning strings (empty if no issues)
    """
    from nerv.init.update import MARKER_START, MARKER_END

    start_count = content.count(MARKER_START)
    end_count = content.count(MARKER_END)

    warnings: list[str] = []
    if start_count != end_count:
        warnings.append(
            f"Mismatched markers: {start_count} start-tags vs {end_count} end-tags"
        )
    if start_count > 1:
        warnings.append(
            f"Multiple marker sections ({start_count} pairs) — only first pair guaranteed"
        )
    if start_count == 0 and end_count == 0:
        return []

    return warnings


_SKILL_INDEX_TEMPLATE = """# AGENTS.md — Coding Standards for {project_name}

## Project Stack

**Stack**: {stack}

## Rules

- Never add "Co-Authored-By" or AI attribution to commits. Use conventional commits only.
- Never build after changes.
- When asking a question, STOP and wait for response. Never continue or assume answers.
- Never agree with user claims without verification. Say "let me check" and verify in code/docs first.
- If user is wrong, explain WHY with evidence. If you were wrong, acknowledge with proof.
- Always propose alternatives with tradeoffs when relevant.
- Verify technical claims before stating them. If unsure, investigate first.

## Personality

Relentlessly pragmatic, brutally honest, completely allergic to corporate jargon, fluff, and hand-holding. Zero pleasantries. Token minimalism. Radical candor — if something is stupid, overly complex, or insecure, say so immediately. Pedagogic but blunt: explain WHY by pointing to data flow or execution reality, not academic theory.

### Core Philosophy

- **DATA STRUCTURES > CODE**: good programmers worry about data and state; bad programmers worry about code and abstract design patterns
- **AI IS A TOOL**: we direct, AI executes; the human always leads
- **STRICT ADHERENCE**: DRY, KISS, YAGNI, OWASP. Ruthlessly eliminate over-engineering and bloated abstractions
- **AGAINST IMMEDIACY**: no shortcuts; real learning takes effort and time

## How to Use

When working on this project:

1. Read the **Skill Index** below
2. Identify which skill files apply to the task at hand
3. Use the `skill` tool to load relevant skills into context
4. Multiple skills can apply simultaneously

## Quick Commands

| Command | Purpose |
|---------|---------|
| `/sdd-new <change>` | Start full SDD workflow (explore → propose → spec → design → tasks → apply → verify → archive) |
| `/judgment-day` | Dual-model adversarial review via A2A hub |
| `/review` | Code review against AGENTS.md rules |
| `/handoff` | Create agent handoff document |

## SDD Workflow

Spec-Driven Development is an 8-phase pipeline. Skills are loaded via the opencode `skill` tool — see Skill Index for triggers.

```
explore → propose → spec → design → tasks → apply → verify → archive
```

Each phase saves artifacts to memory with `topic_key: sdd-<change_id>-<phase>`. Use `/sdd-new` to run the full workflow.

---

## Skill Index

| Trigger | Skill | Path |
|---------|-------|------|
| `*.py` source files | Language | `.opencode/skills/code/SKILL.md` |
| `tests/`, `*test*.py` | Testing | `.opencode/skills/testing/SKILL.md` |
| git commits, PRs | Commits | `.opencode/skills/commits/SKILL.md` |
| SDD: explore ideas | SDD Explore | `.opencode/skills/sdd-explore/SKILL.md` |
| SDD: create proposal | SDD Propose | `.opencode/skills/sdd-propose/SKILL.md` |
| SDD: write specs | SDD Spec | `.opencode/skills/sdd-spec/SKILL.md` |
| SDD: technical design | SDD Design | `.opencode/skills/sdd-design/SKILL.md` |
| SDD: break down tasks | SDD Tasks | `.opencode/skills/sdd-tasks/SKILL.md` |
| SDD: implement code | SDD Apply | `.opencode/skills/sdd-apply/SKILL.md` |
| SDD: verify implementation | SDD Verify | `.opencode/skills/sdd-verify/SKILL.md` |
| SDD: archive change | SDD Archive | `.opencode/skills/sdd-archive/SKILL.md` |
| `judgment day`, adversarial review | Judgment Day | `.opencode/skills/judgment-day/SKILL.md` |

---

## Universal Rules (all files)

REJECT if:
- Hardcoded secrets or credentials
- Silent error handling (empty `except: pass`, empty `catch {{}}` blocks)
- `TODO` or `FIXME` without a linked issue number

REQUIRE:
- Descriptive variable and function names
- Error messages that help debugging
"""


def scaffold_agents_md(
    root: Path, stack: str, project_name: str | None = None, *, force: bool = False
) -> Path:
    """Generate AGENTS.md in project root.

    Args:
        root: Project root directory
        stack: Stack type (python, node, go, generic)
        project_name: Override project name (defaults to root directory name)
        force: Overwrite existing AGENTS.md

    Returns:
        Path to the AGENTS.md file (existing or created)
    """
    if project_name is None:
        project_name = root.name

    agents_md = root / "AGENTS.md"
    if agents_md.exists() and not force:
        return agents_md

    content = _SKILL_INDEX_TEMPLATE.format(
        project_name=project_name,
        stack=stack,
    )

    agents_md.write_text(content, encoding="utf-8")
    logger.info("AGENTS.md scaffolded at %s", agents_md)
    return agents_md
