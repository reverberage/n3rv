"""Integration tests for SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import pytest
from aiohttp.test_utils import TestClient, TestServer

from nerv.a2a.hub import A2AHub


async def build_client(runtime_settings) -> TestClient:
    """Build test client for hub."""
    hub = A2AHub(runtime_settings)
    client = TestClient(TestServer(hub.create_app()))
    await client.start_server()
    return client


@pytest.mark.asyncio
async def test_sse_response_headers(runtime_settings) -> None:
    """Test SSE endpoint returns correct headers."""
    client = await build_client(runtime_settings)
    try:
        # Create a task first
        sent = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tasks/send",
                "params": {
                    "requesting_agent": "test",
                    "skill_id": "implementation",
                    "description": "Test task",
                },
            },
        )
        task_id = (await sent.json())["result"]["id"]
        
        # Subscribe to task
        response = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tasks/sendSubscribe",
                "params": {"task_id": task_id},
            },
        )
        
        assert response.status == 200
        assert response.headers["Content-Type"] == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sse_streams_task_events(runtime_settings) -> None:
    """Test SSE endpoint streams task-status events."""
    client = await build_client(runtime_settings)
    try:
        # Create a task (will auto-complete)
        sent = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tasks/send",
                "params": {
                    "requesting_agent": "test",
                    "skill_id": "implementation",
                    "description": "Test task",
                },
            },
        )
        task_id = (await sent.json())["result"]["id"]
        
        # Subscribe to task (already completed)
        response = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tasks/sendSubscribe",
                "params": {"task_id": task_id},
            },
        )
        
        # Read stream
        chunks = []
        async for chunk in response.content.iter_any():
            chunks.append(chunk.decode())
            # Break after a short period (task is terminal)
            if len(chunks) >= 3:
                break
        
        stream_data = "".join(chunks)
        
        # Should contain at least one event: task-status
        assert "event: task-status" in stream_data
        assert f'"id":"{task_id}"' in stream_data
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sse_terminal_task_closes_stream(runtime_settings) -> None:
    """Test SSE stream closes after terminal state event."""
    client = await build_client(runtime_settings)
    try:
        # Create a completed task
        sent = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tasks/send",
                "params": {
                    "requesting_agent": "test",
                    "skill_id": "implementation",
                    "description": "Test task",
                },
            },
        )
        task_id = (await sent.json())["result"]["id"]
        
        # Task is already completed, subscribe should send one event and close
        response = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tasks/sendSubscribe",
                "params": {"task_id": task_id},
            },
        )
        
        # Collect all chunks (should be limited since stream closes)
        chunks = []
        async for chunk in response.content.iter_any():
            chunks.append(chunk.decode())
        
        stream_data = "".join(chunks)
        
        # Should have at least one event
        assert "event: task-status" in stream_data
        # Should contain completed state
        assert '"state":"completed"' in stream_data
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_sse_unknown_task_returns_empty_stream(runtime_settings) -> None:
    """Test SSE endpoint handles unknown task_id gracefully."""
    client = await build_client(runtime_settings)
    try:
        # Subscribe to non-existent task
        response = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tasks/sendSubscribe",
                "params": {"task_id": "task-00000000000000000000000000000000"},
            },
        )
        
        # Should still return SSE headers
        assert response.status == 200
        assert response.headers["Content-Type"] == "text/event-stream"
        
        # Stream should close quickly with no events
        chunks = []
        async for chunk in response.content.iter_any():
            chunks.append(chunk)
            if len(chunks) > 10:  # Safety limit
                break
        
        # Should be empty or very minimal
        stream_data = b"".join(chunks).decode()
        # Should not have any task-status events
        assert stream_data == "" or "event: task-status" not in stream_data
    finally:
        await client.close()
