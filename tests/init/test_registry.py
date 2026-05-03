"""Tests for the skill registry module."""

from __future__ import annotations

from pathlib import Path


from nerv.init.registry import (
    SkillEntry,
    SkillRegistry,
    _parse_frontmatter,
    write_registry,
)


# --------------------------------------------------------------------------- #
# _parse_frontmatter
# --------------------------------------------------------------------------- #


def test_parse_frontmatter_with_valid_yaml():
    content = "---\nname: my-skill\ndescription: Does things\n---\n\n## Body"
    fm, body = _parse_frontmatter(content)
    assert fm["name"] == "my-skill"
    assert fm["description"] == "Does things"
    assert body.startswith("## Body")


def test_parse_frontmatter_no_frontmatter():
    content = "## Just a body"
    fm, body = _parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_parse_frontmatter_malformed_yaml():
    content = "---\n: bad: yaml: :\n---\n\nbody"
    fm, body = _parse_frontmatter(content)
    assert fm == {}


def test_parse_frontmatter_hub_skill_ids_list():
    content = "---\nname: sdd-apply\ndescription: Apply task\nhub-skill-ids: [implementation, plan-execution]\n---\n"
    fm, _ = _parse_frontmatter(content)
    assert fm["hub-skill-ids"] == ["implementation", "plan-execution"]


# --------------------------------------------------------------------------- #
# SkillRegistry.scan
# --------------------------------------------------------------------------- #

SKILL_CONTENT = """\
---
name: test-skill
description: A test skill
when_to_use: When you want to test things
model: low
hub-skill-ids: [review, reasoning]
---

## Goal

Do the thing.
"""

SKILL_NO_FRONTMATTER = "## Just a plain markdown skill\n\nNo YAML here."

SKILL_MISSING_DESCRIPTION = "---\nname: no-desc\n---\n\n## Body"


def _make_skill_dir(tmp_path: Path, subpath: str, content: str) -> Path:
    skill_dir = tmp_path / subpath
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def test_scan_finds_valid_skills(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 1
    entry = registry.entries[0]
    assert entry.name == "test-skill"
    assert entry.description == "A test skill"
    assert entry.model == "low"
    assert entry.hub_skill_ids == ["review", "reasoning"]


def test_scan_skips_no_frontmatter(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/plain-skill", SKILL_NO_FRONTMATTER)
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 0


def test_scan_skips_missing_description(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/no-desc", SKILL_MISSING_DESCRIPTION)
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 0


def test_scan_empty_dir(tmp_path: Path):
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 0


def test_scan_multiple_skills(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/skill-a", SKILL_CONTENT)
    content_b = SKILL_CONTENT.replace("test-skill", "skill-b").replace(
        "A test skill", "Skill B"
    )
    _make_skill_dir(tmp_path, ".opencode/skills/skill-b", content_b)
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 2


def test_scan_deduplicates_symlinks(tmp_path: Path):
    original = _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    link_dir = tmp_path / ".github" / "skills" / "test-skill"
    link_dir.mkdir(parents=True)
    link = link_dir / "SKILL.md"
    link.symlink_to(original)
    registry = SkillRegistry.scan(tmp_path)
    assert len(registry.entries) == 1


# --------------------------------------------------------------------------- #
# SkillRegistry.find_by_skill_id
# --------------------------------------------------------------------------- #


def test_find_by_skill_id_match(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    registry = SkillRegistry.scan(tmp_path)
    results = registry.find_by_skill_id("review")
    assert len(results) == 1
    assert results[0].name == "test-skill"


def test_find_by_skill_id_no_match(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    registry = SkillRegistry.scan(tmp_path)
    results = registry.find_by_skill_id("implementation")
    assert results == []


def test_find_by_skill_id_empty_registry(tmp_path: Path):
    registry = SkillRegistry.scan(tmp_path)
    assert registry.find_by_skill_id("anything") == []


# --------------------------------------------------------------------------- #
# SkillEntry.as_context_item
# --------------------------------------------------------------------------- #


def test_as_context_item_structure(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    registry = SkillRegistry.scan(tmp_path)
    item = registry.entries[0].as_context_item()
    assert item["content"] == SKILL_CONTENT
    assert item["metadata"]["source"] == "skill"
    assert item["metadata"]["skill_name"] == "test-skill"
    assert "skill_path" in item["metadata"]


# --------------------------------------------------------------------------- #
# SkillRegistry.to_markdown
# --------------------------------------------------------------------------- #


def test_to_markdown_empty():
    registry = SkillRegistry([])
    md = registry.to_markdown()
    assert "_No agentskills.io skills found._" in md


def test_to_markdown_with_entries(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    registry = SkillRegistry.scan(tmp_path)
    md = registry.to_markdown()
    assert "test-skill" in md
    assert "review, reasoning" in md
    assert "| Name |" in md


def test_to_markdown_truncates_long_descriptions():
    long_desc = "x" * 100
    entry = SkillEntry(
        name="long-skill",
        description=long_desc,
        path=Path("/fake/SKILL.md"),
        raw_content="",
    )
    registry = SkillRegistry([entry])
    md = registry.to_markdown()
    assert "…" in md


# --------------------------------------------------------------------------- #
# write_registry
# --------------------------------------------------------------------------- #


def test_write_registry_creates_file(tmp_path: Path):
    _make_skill_dir(tmp_path, ".opencode/skills/test-skill", SKILL_CONTENT)
    out = write_registry(tmp_path)
    assert out.exists()
    assert out.name == "skill-registry.md"
    assert out.parent.name == ".nerv"
    content = out.read_text()
    assert "test-skill" in content


def test_write_registry_empty_project(tmp_path: Path):
    out = write_registry(tmp_path)
    assert out.exists()
    content = out.read_text()
    assert "_No agentskills.io skills found._" in content
