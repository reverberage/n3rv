from __future__ import annotations

from pathlib import Path


def _tools_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".opencode" / "tools" / "nerv-stats.ts"


class TestNervStatsTools:
    def test_file_exists(self) -> None:
        assert _tools_path().is_file()

    def test_imports_tool(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "@opencode-ai/plugin" in content

    def test_exports_memory_stats(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "export const nerv_memory_stats" in content

    def test_exports_task_status(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "export const nerv_task_status" in content

    def test_exports_hub_health(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "export const nerv_hub_health" in content

    def test_exports_check_pending_tasks(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "export const nerv_check_pending_tasks" in content

    def test_hub_health_returns_false_on_failure(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        # Should return {connected: false} on failure, never throw
        assert "connected: false" in content or '"connected": false' in content

    def test_task_status_accepts_task_id_param(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "task_id" in content

    def test_check_pending_tasks_falls_back_to_env(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "NERV_AGENT_SOURCE" in content or "agent_id" in content

    def test_all_tools_use_tool_helper(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "tool({" in content

    def test_timeout_handling_present(self) -> None:
        content = _tools_path().read_text(encoding="utf-8")
        assert "AbortController" in content or "timeout" in content.lower()
