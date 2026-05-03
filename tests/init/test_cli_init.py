"""Integration tests for CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from nerv.cli import app

runner = CliRunner()


def test_init_command_creates_files(tmp_path: Path):
    """Test nerv init creates files in temporary directory."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    result = runner.invoke(app, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".nerv/a2a-config.yaml").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "opencode.json").exists()
    assert (tmp_path / ".githooks/pre-push").exists()


def test_init_with_explicit_stack_and_name(tmp_path: Path):
    """Test init with explicit --stack and --project-name."""
    result = runner.invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--stack",
            "python",
            "--project-name",
            "myapp",
        ],
    )

    assert result.exit_code == 0

    config = tmp_path / ".nerv/a2a-config.yaml"
    content = config.read_text()
    assert "project: myapp" in content
    assert "port: 19820" in content

    agents_md = tmp_path / "AGENTS.md"
    assert "**Stack**: python" in agents_md.read_text()


def test_init_double_invocation_skips_files(tmp_path: Path):
    """Test running init twice skips existing files on second run."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    result1 = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result1.exit_code == 0

    config = tmp_path / ".nerv/a2a-config.yaml"
    config.write_text("# Modified\n" + config.read_text())

    result2 = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result2.exit_code == 0
    assert "Skipped" in result2.stdout

    assert "# Modified" in config.read_text()


def test_init_with_force_overwrites(tmp_path: Path):
    """Test init --force overwrites existing files."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    runner.invoke(app, ["init", "--root", str(tmp_path)])

    ocode = tmp_path / "opencode.json"
    ocode.write_text('{"modified": true}')

    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--force"])

    assert result.exit_code == 0
    assert '"modified"' not in ocode.read_text()


def test_hub_start_help_works():
    """Test that hub start --help works (backward compatibility)."""
    result = runner.invoke(app, ["hub", "start", "--help"])
    assert result.exit_code == 0
    assert "Start the A2A hub server" in result.stdout


def test_init_help_works():
    """Test that init --help works."""
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "Initialize agent-native integration" in result.stdout
    assert "--stack" in result.stdout
    assert "--project-name" in result.stdout
    assert "--force" in result.stdout
