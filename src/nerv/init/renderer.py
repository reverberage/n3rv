"""Jinja2 template rendering engine."""

from __future__ import annotations

from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    UndefinedError,
)


class TemplateRenderError(Exception):
    """Error during template rendering."""


class TemplateEngine:
    """Jinja2-based template rendering engine."""

    def __init__(self, templates_dir: Path) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
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
