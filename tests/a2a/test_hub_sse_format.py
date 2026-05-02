"""Tests for SSE event formatting helpers."""

from __future__ import annotations

from nerv.a2a.hub import _format_sse_event


def test_sse_event_has_event_line():
    """SSE event must start with event: task-status line."""
    result = _format_sse_event({"id": "task-1", "status": {"state": "working"}})
    assert b"event: task-status\n" in result


def test_sse_event_has_data_line():
    """SSE event must contain data line with JSON payload."""
    result = _format_sse_event({"id": "task-1"})
    assert b'data: {"id":"task-1"}' in result


def test_sse_event_ends_with_double_newline():
    """SSE event must end with double newline."""
    result = _format_sse_event({"id": "task-1"})
    assert result.endswith(b"\n\n")


def test_sse_event_minified_json():
    """SSE event should use minified JSON (no extra spaces)."""
    result = _format_sse_event({"id": "task-1", "nested": {"key": "value"}})
    # Should not have spaces after colons or commas
    assert b'{"id":"task-1","nested":{"key":"value"}}' in result
