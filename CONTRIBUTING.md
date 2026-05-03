# Contributing to NERV

## Dev Setup

Requires Python >=3.14 and [uv](https://github.com/astral-sh/uv).

```bash
# Clone and sync dependencies
uv sync

# Or install in development mode
uv pip install -e .
```

## Running Tests

```bash
pytest
```

Test files are in `tests/` — ~2900 lines across 20 test files.

## Code Style

Rules are enforced via `AGENTS.md` (loaded automatically by opencode agent):

**REJECT if:**
- Hardcoded secrets or credentials
- Silent error handling (empty `except: pass`, empty `catch {}` blocks)
- `TODO` or `FIXME` without a linked issue number

**REQUIRE:**
- Descriptive variable and function names
- Error messages that help debugging

## Project Structure

```
src/nerv/
├── cli.py              # Typer CLI entry point
├── cli_memory.py       # Memory CLI subcommands
├── config.py           # RuntimeSettings, RuntimePaths
├── platform.py         # Project root detection
├── util.py             # Helpers
├── a2a/               # A2A hub server
│   ├── hub.py          # A2AHub: aiohttp web app, RPC handler
│   ├── router.py       # TaskRouter: routes tasks to agents
│   ├── state.py        # HubStateStore: task persistence (JSON)
│   └── agent_cards.py  # Load agent cards from YAML
├── init/               # Project scaffolding
│   ├── run_init.py     # Init orchestration
│   ├── detector.py     # Stack detection (python/node/go/generic)
│   ├── renderer.py     # Jinja2 template engine
│   ├── registry.py     # SkillRegistry: scans SKILL.md files
│   └── templates/      # Jinja2 templates
├── mcp/                # MCP servers
│   ├── memory_server.py # Memory MCP server (12 tools)
│   ├── hub_server.py   # Hub MCP server (5 tools)
│   ├── memory_store.py # MemoryStore: ChromaDB + SQLite
│   ├── client.py       # HubMCPBridge: subprocess MCP clients
│   └── shared.py       # Shared MCP utilities
└── models/             # Pydantic models
    ├── a2a.py          # AgentCard, TaskState, etc.
    └── memory.py       # MemoryType, SearchResult, etc.
```

## Adding a New Skill

1. Create directory: `.nerv/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter:

```yaml
---
name: <skill-name>
description: "One-line description"
when_to_use: "When to trigger this skill"
allowed-tools:
  - Read
  - Write
  - mcp__nerv-memory__memory_save
model: haiku|sonnet
effort: low|medium|high
user-invocable: false
hub-skill-ids: [<optional, for A2A delegation>]
---
```

3. Add skill reference to `AGENTS.md` Skill Index table
4. If the skill should be delegable via A2A hub, add `hub-skill-ids` to frontmatter

## Adding a New MCP Tool

### Memory Tool

1. Add method to `MemoryService` class in `src/nerv/mcp/memory_server.py`
2. Add corresponding `@server.tool()` decorator with description
3. Update `docs/MCP-TOOLS.md` with tool documentation
4. Add docstring to `MemoryStore` method if implementing new storage logic

### Hub Tool

1. Add method to `src/nerv/mcp/hub_server.py` with `@server.tool()` decorator
2. Use `_rpc(hub_url, "tasks/...", {...})` to call A2A hub RPC methods
3. Update `docs/MCP-TOOLS.md` with tool documentation

## Entry Points

| Command | Entry Function |
|---------|----------------|
| `nerv` | `src/nerv/cli.py:main()` |
| `nerv-memory` | `src/nerv/mcp/memory_server.py:main()` |
| `nerv-hub` | `src/nerv/mcp/hub_server.py:main()` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NERV_LOG_LEVEL` | `INFO` | Logging level |
| `NERV_AGENT_SOURCE` | `unknown` | Agent identifier |
| `NERV_HUB_URL` | `http://127.0.0.1:19820` | A2A hub URL |
| `NERV_MEMORY_PROFILE` | `full` | Memory profile (`full` or `safe`) |

## Documentation

- `README.md` — User-facing overview
- `AGENTS.md` — Coding standards and skill index
- `docs/ARCHITECTURE.md` — System architecture
- `docs/SDD-WORKFLOW.md` — SDD phase guide
- `docs/MCP-TOOLS.md` — MCP tool reference
- `.nerv/skills/*/SKILL.md` — Agent skill instructions
