from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nerv.platform import project_relative_path, resolve_project_root


class RuntimePaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_root: Path
    memory_dir: Path
    nerv_dir: Path
    hub_state_dir: Path
    logs_dir: Path

    @property
    def pid_file(self) -> Path:
        return self.nerv_dir / "hub.pid"

    @property
    def log_file(self) -> Path:
        return self.logs_dir / "hub.log"

    @classmethod
    def from_project_root(cls, project_root: Path) -> RuntimePaths:
        return cls(
            project_root=project_root,
            memory_dir=project_relative_path(project_root, ".nerv", "memory"),
            nerv_dir=project_relative_path(project_root, ".nerv"),
            hub_state_dir=project_relative_path(project_root, ".nerv", "hub-state"),
            logs_dir=project_relative_path(project_root, ".nerv", "logs"),
        )


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_name: str = "nerv"
    a2a_host: str = "127.0.0.1"
    a2a_port: int = Field(default=19820, ge=1, le=65535)
    paths: RuntimePaths

    @property
    def a2a_base_url(self) -> str:
        return f"http://{self.a2a_host}:{self.a2a_port}"


def load_runtime_settings(project_root: Path | None = None) -> RuntimeSettings:
    root = project_root or resolve_project_root()
    paths = RuntimePaths.from_project_root(root)
    settings = RuntimeSettings(project_name=root.name or "nerv", paths=paths)

    config_path = paths.nerv_dir / "a2a-config.yaml"
    if not config_path.exists():
        return settings

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    hub_section = raw.get("hub") or {}

    settings_data = settings.model_dump()
    if isinstance(raw.get("project"), str) and raw["project"].strip():
        settings_data["project_name"] = raw["project"].strip()
    if "host" in hub_section:
        settings_data["a2a_host"] = hub_section["host"]
    if "port" in hub_section:
        settings_data["a2a_port"] = hub_section["port"]
    return RuntimeSettings.model_validate(settings_data)
