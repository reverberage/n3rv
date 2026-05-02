# NERV

Invisible engineering infrastructure for opencode agents.

Provides agent-native project scaffolding, persistent semantic memory (ChromaDB), and A2A task delegation for AI-assisted development workflows.

[Architecture](docs/ARCHITECTURE.md) • [SDD Workflow](docs/SDD-WORKFLOW.md) • [MCP Tools](docs/MCP-TOOLS.md) • [Contributing](CONTRIBUTING.md)

## Install

Requires Python >=3.14 and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

Or install in development mode:

```bash
uv pip install -e .
```

Entry points: `nerv` (CLI), `nerv-memory` (MCP server), `nerv-hub` (A2A hub server).

## Quick Start

Initialize NERV in your project:

```bash
cd /path/to/your/project
nerv init
```

`nerv init` detects your project stack (python/node/go/generic) and scaffolds:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Coding standards with skill index |
| `.nerv/a2a-config.yaml` | A2A hub configuration |
| `.nerv/skills/` | Agent skills (code, testing, commits, SDD workflow) |
| `mcp.json` | MCP server configuration |
| `.githooks/pre-push` | Git pre-push hook |

Options:

```bash
nerv init [--root .] [--project-name X] [--stack python|node|go|generic] [--force]
```

Update existing scaffold:

```bash
nerv update [--dry-run] [--force-commands] [--only <files>]
```

## Commands

### Hub

Start the A2A hub server (default port 19820):

```bash
nerv hub start
```

### Memory

Inspect persistent engineering memories:

```bash
nerv memory list [--type bugfix|decision|...] [--scope project|personal] [--limit N]
nerv memory search <query> [--type ...] [--keyword ...] [--limit N]
nerv memory prune [--scope ...] [--older-than N]
nerv memory stats
```

### MCP Servers

For agent integration (opencode):

```bash
nerv-memory   # Memory MCP server (save, search, recall, context, session management)
nerv-hub      # A2A hub MCP server (delegate tasks, poll work, complete tasks)
```

## Configuration

Environment variables (`.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `NERV_LOG_LEVEL` | `INFO` | Logging level |
| `NERV_AGENT_SOURCE` | `unknown` | Agent identifier (e.g., `opencode`) |
| `NERV_HUB_URL` | `http://127.0.0.1:19820` | A2A hub URL |
| `NERV_MEMORY_PROFILE` | `full` | Memory profile mode |

A2A hub config (`.nerv/a2a-config.yaml`, created by `nerv init`):

```yaml
hub:
  host: 127.0.0.1
  port: 19820
project: <project-name>
```

## SDD Workflow

NERV includes 8 Spec-Driven Development phases as skills:

explore → propose → spec → design → tasks → apply → verify → archive

Triggered by the opencode agent during development sessions.

## Judgment Day

Adversarial review skill that launches two independent blind judge sub-agents to review code, synthesizes findings, applies fixes, and re-judges.

Trigger: `judgment day`, `judgment-day`, `review adversarial`, `dual review`

## Troubleshooting

### Hub won't start

- Check if port 19820 is already in use: `lsof -i :19820`
- Verify `.nerv/a2a-config.yaml` exists (run `nerv init` to create)
- Check `NERV_LOG_LEVEL=DEBUG` for details

### Memory store issues

- ChromaDB corruption: delete `.nerv/memory/chroma/` and restart
- ONNXRuntime unavailable: normal on Python 3.14/Windows, falls back to hash embeddings
- Search returns no results: verify memories were saved (check `nerv memory list`)

### A2A delegation fails

- `SKILL_NOT_FOUND`: skill_id doesn't match any agent in `.nerv/a2a-config.yaml`
- `MCP_TOOL_ERROR`: agent's MCP tool call failed — check agent logs
- `RESTART_RECOVERY`: hub restarted while task was in progress — retry the task
