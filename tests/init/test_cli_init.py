"""Integration tests for CLI."""

from __future__ import annotations

import json
import shutil
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


def test_init_creates_opencode_json_with_env(tmp_path: Path):
    """Test opencode.json has NERV_AGENT_SOURCE env after init."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0

    ocode = json.loads((tmp_path / "opencode.json").read_text())
    memory_cfg = ocode["mcp"]["nerv-memory"]
    hub_cfg = ocode["mcp"]["nerv-hub"]

    assert memory_cfg["environment"] == {"NERV_AGENT_SOURCE": "opencode"}
    assert hub_cfg["environment"] == {"NERV_AGENT_SOURCE": "opencode"}


def test_init_creates_systemd_unit(tmp_path: Path):
    """Test init creates systemd unit file."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0

    unit_path = tmp_path / ".nerv" / "systemd" / "nerv-hub.service"
    assert unit_path.exists()
    content = unit_path.read_text()
    assert "NERV A2A Hub for" in content
    nerv_binary = shutil.which("nerv")
    assert nerv_binary is not None, "nerv binary not found in PATH"
    assert f"ExecStart={nerv_binary} hub start" in content
    assert "Restart=on-failure" in content


def test_init_mentions_daemon_setup(tmp_path: Path):
    """Test init output references daemon setup."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "clitest"')

    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert "nerv daemon install" in result.stdout


def test_daemon_help_works():
    """Test daemon commands are registered."""
    result = runner.invoke(app, ["daemon", "--help"])
    assert result.exit_code == 0
    assert "Manage nerv hub daemon" in result.stdout
    assert "install" in result.stdout
    assert "start" in result.stdout
    assert "stop" in result.stdout
    assert "status" in result.stdout
    assert "enable" in result.stdout
    assert "logs" in result.stdout
