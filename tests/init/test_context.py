"""Tests for ProjectContext model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nerv.init.context import ProjectContext, Stack


def test_stack_enum_values():
    """Test Stack enum has required values."""
    assert Stack.PYTHON == "python"
    assert Stack.NODE == "node"
    assert Stack.GO == "go"
    assert Stack.GENERIC == "generic"


def test_project_context_build():
    """Test ProjectContext.build() creates valid context with auto-populated fields."""
    ctx = ProjectContext.build(project_name="myapp", stack=Stack.PYTHON)
    
    assert ctx.project_name == "myapp"
    assert ctx.stack == Stack.PYTHON
    assert isinstance(ctx.nerv_version, str)
    assert len(ctx.nerv_version) > 0
    assert isinstance(ctx.timestamp, str)
    assert "T" in ctx.timestamp  # ISO 8601 format


def test_project_context_to_dict():
    """Test to_dict() returns correct structure for Jinja2 rendering."""
    ctx = ProjectContext.build(project_name="testproject", stack=Stack.NODE)
    result = ctx.to_dict()
    
    assert result["project_name"] == "testproject"
    assert result["stack"] == "node"  # Stack enum converted to string
    assert "nerv_version" in result
    assert "timestamp" in result


def test_project_context_validates_project_name():
    """Test that empty or invalid project names raise ValidationError."""
    with pytest.raises(ValidationError):
        ProjectContext.build(project_name="", stack=Stack.PYTHON)


def test_stack_validation():
    """Test that invalid stack values raise ValidationError."""
    # Direct construction with invalid stack should fail
    with pytest.raises(ValidationError):
        ProjectContext(
            project_name="test",
            stack="invalid",  # type: ignore
            nerv_version="0.1.0",
            timestamp="2025-01-15T00:00:00Z",
        )
