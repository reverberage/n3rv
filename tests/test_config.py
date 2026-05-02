from __future__ import annotations

from nerv.config import load_runtime_settings


def test_load_runtime_settings_defaults_project_name_to_root_name(tmp_path) -> None:
    settings = load_runtime_settings(tmp_path)

    assert settings.project_name == tmp_path.name
    assert settings.a2a_host == "127.0.0.1"
    assert settings.a2a_port == 19820


def test_load_runtime_settings_reads_project_and_hub_config(tmp_path) -> None:
    nerv_dir = tmp_path / ".nerv"
    nerv_dir.mkdir()
    (nerv_dir / "a2a-config.yaml").write_text(
        "project: demo-app\nhub:\n  host: 0.0.0.0\n  port: 9009\n",
        encoding="utf-8",
    )

    settings = load_runtime_settings(tmp_path)

    assert settings.project_name == "demo-app"
    assert settings.a2a_host == "0.0.0.0"
    assert settings.a2a_port == 9009
