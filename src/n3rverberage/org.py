"""Org-level configuration for reverberage multi-project workspaces."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from n3rverberage.models.a2a import AgentCapabilities, AgentSkill, NervAgentCard

logger = logging.getLogger("n3rverberage.org")

ORG_CONFIG_FILENAME = "org-config.yaml"


class OrgNotFoundError(Exception):
    """Raised when no .n3rverberage/org-config.yaml is found."""


class OrgProject(BaseModel):
    """A single project registered in the org."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path
    description: str = ""
    type: Literal["hub", "satellite", "tool"] = "satellite"
    repo_url: str | None = None


class OrgConfig(BaseModel):
    """Org-level configuration for a multi-project workspace."""

    org_name: str = "reverberage"
    projects: list[OrgProject] = []
    config: dict[str, Any] = Field(
        default_factory=lambda: {
            "shared_skills_dir": ".opencode/shared/skills",
            "satellites_dir": ".",
        }
    )

    @field_validator("projects")
    @classmethod
    def _no_duplicate_names(cls, v: list[OrgProject]) -> list[OrgProject]:
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate project names: {names}")
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> OrgConfig:
        """Load org config from a YAML file."""
        if not path.exists():
            raise OrgNotFoundError(f"Org config not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid org config in {path}: expected a mapping")
        return cls.model_validate(raw)

    def to_yaml(self, path: Path) -> None:
        """Write org config to a YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="python")
        # Convert Path objects to strings for YAML serialization
        for p in data.get("projects", []):
            p["path"] = str(p["path"])
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

    def discover_satellite_cards(
        self, config_dir: Path | None = None
    ) -> list[NervAgentCard]:
        """Discover agent cards for all satellite projects."""
        cards: list[NervAgentCard] = []
        base = config_dir or Path.cwd()
        for project in self.projects:
            if project.type != "satellite":
                continue
            project_path = (base / project.path).resolve()
            a2a_config = project_path / ".n3rverberage" / "a2a-config.yaml"
            if not a2a_config.exists():
                logger.debug("No a2a-config.yaml for %s at %s", project.name, a2a_config)
                continue
            try:
                raw = yaml.safe_load(a2a_config.read_text(encoding="utf-8")) or {}
                hub = raw.get("hub", {})
                host = hub.get("host", "127.0.0.1")
                port = hub.get("port", 19820)
                card = NervAgentCard(
                    name=f"n3rverberage-{project.name}",
                    description=project.description or f"{project.name} satellite agent",
                    url=f"http://{host}:{port}",
                    version="0.1.0",
                    capabilities=AgentCapabilities(streaming=False),
                    skills=[
                        AgentSkill(
                            id=f"satellite-{project.name}",
                            name=project.name,
                            description=project.description or f"{project.name} operations",
                        ),
                    ],
                )
                cards.append(card)
            except Exception as exc:
                logger.warning("Failed to load agent card for %s: %s", project.name, exc)
                continue
        return cards


def resolve_org_root(start: Path | None = None) -> Path:
    """Walk up from *start* looking for .n3rverberage/org-config.yaml.

    Raises OrgNotFoundError if no config is found.
    """
    current = (start or Path.cwd()).resolve()
    for ancestor in [current] + list(current.parents):
        config_path = ancestor / ".n3rverberage" / ORG_CONFIG_FILENAME
        if config_path.exists():
            return ancestor
    raise OrgNotFoundError(
        f"No .n3rverberage/{ORG_CONFIG_FILENAME} found from {start or Path.cwd()}. "
        "Run 'n3rverberage org init' first."
    )
