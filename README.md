# NERV

> *"God's in his heaven. All's right with the world."*

Invisible engineering infrastructure for AI agents. Named after the clandestine organization from *Neon Genesis Evangelion*, nerv provides the hidden machinery that powers agent-native development: project scaffolding (the **Geofront**), persistent semantic memory (the **MAGI**), and A2A task delegation (the **Command Center**). Integrates natively with opencode via MCP servers, agent skills, slash commands, and sub-agents.

[Architecture](docs/ARCHITECTURE.md) • [SDD Workflow](docs/SDD-WORKFLOW.md) • [MCP Tools](docs/MCP-TOOLS.md) • [Deployment](docs/DEPLOYMENT.md) • [Evangelion](EVANGELION.md) • [Security](SECURITY.md) • [Contributing](CONTRIBUTING.md)

## Why NERV?

Like its anime namesake, nerv operates from beneath the surface. While you write code in the light of your editor (Tokyo-3), nerv's infrastructure runs in the hidden Geofront (`nerv/`) below — the MAGI supercomputer stores and recalls engineering memories across sessions, the Command Center dispatches EVAs (agents) to execute missions (tasks), and the Human Instrumentality Project (SDD workflow) orchestrates the entire development lifecycle.

Every nerv concept maps to an Evangelion analog. See [EVANGELION.md](EVANGELION.md) for the full concept map.

## Quick Start

```bash
# Install nerv as a global tool (once, runs everywhere):
uv tool install git+https://github.com/juanmanueldaza/nerv.git

# Initialize in your project:
nerv init
```

Or without installing:

```bash
uvx --from git+https://github.com/juanmanueldaza/nerv.git nerv init
```

`nerv init` detects your project stack (python/node/go/generic) and scaffolds 45+ files:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Coding standards with **LCL injection** — auto-detected frameworks, tools, project structure, and framework-specific guidance |
| `opencode.json` | opencode config: MCP servers, instructions, disables built-in agents, sets `nerv` as default |
| `.opencode/skills/` | Agent skills — code, testing, commits, SDD, git-ops, github-ops (14 skills). Code and testing skills get framework-specific snippets injected. |
| `.opencode/commands/` | Slash commands — `/sdd-new`, `/judgment-day`, `/review`, `/handoff` plus auto-generated `/test`, `/lint`, `/typecheck` (when tools detected) |
| `.opencode/agents/` | Sub-agents — 7 SDD phase agents + 2 operations agents (git-ops, github-ops) + **nerv** primary orchestrator agent |
| `.nerv/a2a-config.yaml` | A2A hub configuration |
| `.nerv/skill-registry.md` | Auto-generated skill index for hub |
| `.githooks/pre-push` | Git pre-push hook |

**LCL Injection**: `nerv init` parses your `pyproject.toml` / `package.json` / `go.mod` dependencies and auto-detects frameworks (FastAPI, Flask, Django, SQLAlchemy, React, Express, etc.), tooling (pytest, ruff, mypy, jest, etc.), and project structure. This context is injected into `AGENTS.md`, skill files, and slash commands — so the AI agent "breathes" your project from the first session.

## OpenCode Integration

NERV generates files in opencode's native discovery paths. When you run opencode in your project:

- **Nerv is the only primary agent** — `opencode.json` disables built-in `build` and `plan`, sets `default_agent: "nerv"`. Only the NERV orchestrator appears in the agent picker.
- **Skills** in `.opencode/skills/` are auto-discovered via the `skill` tool — loaded on demand with full context
- **Commands** in `.opencode/commands/` appear as slash commands in the TUI — type `/sdd-new` to start a workflow
- **Agents** in `.opencode/agents/` are available as sub-agents — invoked by the orchestrator via `Task` tool
- **Instructions** via `opencode.json` ensure `AGENTS.md` is loaded as context

## Components

### CLI

```bash
nerv init [--stack python|node|go|generic] [--force]
nerv update [--dry-run] [--force-commands] [--only <strategy>]
nerv hub start                    # foreground (development)
nerv daemon install|start|stop|status|enable|logs  # background service (recommended)
nerv memory list|search|prune|stats
```

`--only` strategies: `overwrite`, `json-merge`, `create-if-missing`. Use `--force-commands` to overwrite commands and skills on update.

After `git pull`, reinstall from source to pick up changes:

```bash
uv tool install --reinstall .
```

### MCP Servers

Run as subprocesses by opencode, configured in `opencode.json`:

| Command | Purpose |
|---------|---------|
| `nerv-memory` | Memory server — save, search, recall, context management |
| `nerv-hub` | A2A hub — delegate tasks to agents, poll work, complete tasks |

### A2A Hub

JSON-RPC 2.0 server on `127.0.0.1:19820` for task delegation between agents. Supports `tasks/send`, `tasks/get`, `tasks/list`, `tasks/complete`, and SSE subscriptions.

See [Architecture](docs/ARCHITECTURE.md) for system design.

## Memory System

Dual-store persistent memory:

- **ChromaDB** — Vector embeddings for semantic search
- **SQLite** — Relations between memories (judgments, revisions)

Memory types: `architecture`, `bugfix`, `config`, `decision`, `discovery`, `learning`, `pattern`, `context`, `summary`, `note`.

Scopes: `project` (shared), `session` (current), `personal` (agent-specific).

## SDD Workflow

8-phase Spec-Driven Development pipeline, started via `/sdd-new <change>`:

```
explore → propose → spec → design → tasks → apply → verify → archive
```

Each phase is an agent skill (loaded via opencode's `skill` tool) with a dedicated sub-agent for delegation. Phases write to and read from persistent memory with `topic_key: sdd-<change_id>-<phase>`. See [SDD Workflow](docs/SDD-WORKFLOW.md) for phase details.

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NERV_LOG_LEVEL` | `INFO` | Logging level |
| `NERV_AGENT_SOURCE` | `unknown` | Agent identifier |
| `NERV_HUB_URL` | `http://127.0.0.1:19820` | A2A hub URL |
| `NERV_MEMORY_PROFILE` | `full` | `full` or `safe` (read-only tools) |

### Hub Config

`.nerv/a2a-config.yaml`:

```yaml
hub:
  host: 127.0.0.1
  port: 19820
project: your-project-name
```

## Development

```bash
# Install dev dependencies:
uv sync --dev

# Run tests:
uv run pytest

# Optional: install nerv globally in editable mode (source changes reflect immediately):
uv tool install --editable .
```

## Security

NERV runs on localhost with no authentication. See [SECURITY.md](SECURITY.md) for the trust model and recommendations.

## Requirements

- Python >= 3.14
- [uv](https://github.com/astral-sh/uv)
