"""Jinja2 template rendering engine."""

from __future__ import annotations

from pathlib import Path

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    UndefinedError,
)


class TemplateRenderError(Exception):
    """Error during template rendering."""


class TemplateEngine:
    """Jinja2-based template rendering engine.

    Supports template resolution with the following priority chain:
        project_overrides > shared > bundled

    When *shared_templates_dir* is provided, shared templates override bundled
    (template name collision => shared wins). Project-level overrides are added
    by the caller prepending another FileSystemLoader to the ChoiceLoader list.
    """

    def __init__(self, templates_dir: Path, shared_templates_dir: Path | None = None) -> None:
        loaders = []
        if shared_templates_dir is not None:
            loaders.append(FileSystemLoader(str(shared_templates_dir)))
        loaders.append(FileSystemLoader(str(templates_dir)))
        loader = ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]
        self.env = Environment(
            loader=loader,
            autoescape=False,
            undefined=StrictUndefined,
        )

    def render(self, template_name: str, context: dict) -> str:
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except TemplateNotFound as exc:
            raise TemplateRenderError(f"Template not found: {template_name}") from exc
        except UndefinedError as exc:
            raise TemplateRenderError(f"Undefined variable in template {template_name}: {exc}") from exc
