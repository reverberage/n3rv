"""Init module for project scaffolding."""

from __future__ import annotations

from pathlib import Path

from nerv.init.context import ProjectContext
from nerv.init.detector import detect_stack
from nerv.init.registry import write_registry
from nerv.init.renderer import TemplateEngine
from nerv.init.writer import (
    WriteResult,
    configure_git_hooks,
    scaffold_agents_md,
    write_file,
)

FILE_MANIFEST = [
    ("nerv/a2a-config.yaml.j2", ".nerv/a2a-config.yaml", False, False),
    ("opencode.json.j2", "opencode.json", False, False),
    ("githooks/pre-push.py.j2", ".githooks/pre-push", False, True),
    # Skills (opencode-native path)
    (
        "opencode/skills/code/SKILL.md.j2",
        ".opencode/skills/code/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/testing/SKILL.md.j2",
        ".opencode/skills/testing/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/commits/SKILL.md.j2",
        ".opencode/skills/commits/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-explore/SKILL.md.j2",
        ".opencode/skills/sdd-explore/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-propose/SKILL.md.j2",
        ".opencode/skills/sdd-propose/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-spec/SKILL.md.j2",
        ".opencode/skills/sdd-spec/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-design/SKILL.md.j2",
        ".opencode/skills/sdd-design/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-tasks/SKILL.md.j2",
        ".opencode/skills/sdd-tasks/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-apply/SKILL.md.j2",
        ".opencode/skills/sdd-apply/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-verify/SKILL.md.j2",
        ".opencode/skills/sdd-verify/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/sdd-archive/SKILL.md.j2",
        ".opencode/skills/sdd-archive/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/judgment-day/SKILL.md.j2",
        ".opencode/skills/judgment-day/SKILL.md",
        False,
        False,
    ),
    # Slash commands
    ("opencode/commands/sdd-new.md.j2", ".opencode/commands/sdd-new.md", False, False),
    (
        "opencode/commands/judgment-day.md.j2",
        ".opencode/commands/judgment-day.md",
        False,
        False,
    ),
    ("opencode/commands/review.md.j2", ".opencode/commands/review.md", False, False),
    ("opencode/commands/handoff.md.j2", ".opencode/commands/handoff.md", False, False),
    # SDD phase sub-agents
    (
        "opencode/agents/sdd-explorer.md.j2",
        ".opencode/agents/sdd-explorer.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-proposer.md.j2",
        ".opencode/agents/sdd-proposer.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-speccer.md.j2",
        ".opencode/agents/sdd-speccer.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-designer.md.j2",
        ".opencode/agents/sdd-designer.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-task-planner.md.j2",
        ".opencode/agents/sdd-task-planner.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-verifier.md.j2",
        ".opencode/agents/sdd-verifier.md",
        False,
        False,
    ),
    (
        "opencode/agents/sdd-archiver.md.j2",
        ".opencode/agents/sdd-archiver.md",
        False,
        False,
    ),
    # Git & GitHub sub-agents
    ("opencode/agents/git-ops.md.j2", ".opencode/agents/git-ops.md", False, False),
    (
        "opencode/agents/github-ops.md.j2",
        ".opencode/agents/github-ops.md",
        False,
        False,
    ),
    # Git & GitHub skills
    (
        "opencode/skills/git-ops/SKILL.md.j2",
        ".opencode/skills/git-ops/SKILL.md",
        False,
        False,
    ),
    (
        "opencode/skills/github-ops/SKILL.md.j2",
        ".opencode/skills/github-ops/SKILL.md",
        False,
        False,
    ),
]


def run_init(
    root: Path,
    project_name: str | None,
    stack_override: str | None,
    force: bool,
) -> int:
    try:
        stack_info = detect_stack(root, stack_override=stack_override)
        final_project_name = project_name or stack_info.project_name

        context = ProjectContext.build(
            project_name=final_project_name,
            stack=stack_info.stack,
        )

        print(f"Detected: {stack_info.stack.value} ({stack_info.project_name})")

        templates_dir = Path(__file__).parent / "templates"
        engine = TemplateEngine(templates_dir)

        created_count = 0
        skipped_count = 0
        error_count = 0

        # Scaffold AGENTS.md (replaces template rendering)
        try:
            agents_md = root / "AGENTS.md"
            existed = agents_md.exists()
            result_path = scaffold_agents_md(
                root, context.stack.value, final_project_name, force=force
            )
            if existed and not force:
                print(f"⊘ Skipped {result_path.relative_to(root)} (already exists)")
                skipped_count += 1
            else:
                print(f"✓ Created {result_path.relative_to(root)}")
                created_count += 1
        except Exception as exc:
            print(f"✗ Error scaffolding AGENTS.md: {exc}")
            error_count += 1

        for template_name, output_path, use_markers, make_executable in FILE_MANIFEST:
            try:
                content = engine.render(template_name, context.to_dict())
                target = root / output_path
                result = write_file(
                    target,
                    content,
                    force=force,
                    use_markers=use_markers,
                    make_executable=make_executable,
                )

                if result == WriteResult.CREATED:
                    print(f"✓ Created {output_path}")
                    created_count += 1
                elif result == WriteResult.UPDATED:
                    print(f"✓ Updated {output_path}")
                    created_count += 1
                elif result == WriteResult.OVERWRITTEN:
                    print(f"✓ Overwritten {output_path}")
                    created_count += 1
                elif result == WriteResult.SKIPPED:
                    print(f"⊘ Skipped {output_path} (already exists)")
                    skipped_count += 1

            except Exception as exc:
                print(f"✗ Error {output_path}: {exc}")
                error_count += 1

        if configure_git_hooks(root):
            print("✓ Configured git hooks")
        else:
            print("⚠ Warning: No .git directory found, skipping git hooks config")

        try:
            registry_path = write_registry(root)
            print(f"✓ Updated {registry_path.relative_to(root)}")
        except Exception as exc:
            print(f"⚠ Skill registry not written: {exc}")

        print(
            f"\nDone. {created_count} files created/updated, {skipped_count} skipped."
        )
        if error_count > 0:
            print(f"⚠ {error_count} errors occurred")
            return 1

        print("NERV is configured. Work inside opencode.")
        return 0

    except Exception as exc:
        print(f"✗ Fatal error: {exc}")
        return 1
