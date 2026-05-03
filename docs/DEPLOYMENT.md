# Deployment

NERV is a local-only tool that runs as part of your development workflow. It is not designed for production server deployment. This guide covers setup for development machines and CI/CD environments.

## Development Machine

### Prerequisites

- Python >= 3.14
- [uv](https://github.com/astral-sh/uv) package manager

### Install

```bash
git clone https://github.com/your-org/nerv.git
cd nerv
uv sync
```

This installs NERV in a virtual environment managed by uv. Entry points `nerv`, `nerv-memory`, and `nerv-hub` become available.

### Verify Installation

```bash
nerv --help
nerv-memory --help
nerv-hub --help
```

## Using NERV in a Project

### 1. Initialize

```bash
cd /path/to/your/project
nerv init
```

This scaffolds:
- `AGENTS.md` — Coding standards
- `.nerv/a2a-config.yaml` — Hub configuration
- `.nerv/skills/` — Agent skills directory
- `mcp.json` — MCP server configuration for opencode

### 2. Configure MCP Servers

Add to your opencode `mcp.json` (or equivalent):

```json
{
  "mcpServers": {
    "nerv-memory": {
      "command": "nerv-memory"
    },
    "nerv-hub": {
      "command": "nerv-hub"
    }
  }
}
```

### 3. Start the Hub

```bash
nerv hub start
```

The hub binds to `127.0.0.1:19820` by default. Change in `.nerv/a2a-config.yaml`:

```yaml
hub:
  host: 127.0.0.1
  port: 19820
```

## CI/CD Integration

NERV's memory and hub components are local-only and not suitable for CI/CD. However, the CLI can be used for scaffolding:

```yaml
# Example: GitHub Actions step for scaffolding
- name: Setup NERV
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv sync
    nerv init --stack python --force
```

### Testing in CI

```bash
uv run pytest
```

NERV's test suite uses `pytest` with `pytest-asyncio`. Tests are in `tests/`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NERV_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `NERV_AGENT_SOURCE` | `unknown` | Agent identifier for memory scope |
| `NERV_HUB_URL` | `http://127.0.0.1:19820` | Hub URL for MCP delegation |
| `NERV_MEMORY_PROFILE` | `full` | Memory tool availability (`full` or `safe`) |

## Updating NERV

```bash
cd /path/to/nerv
git pull
uv sync
```

To update scaffolding in existing projects:

```bash
cd /path/to/your/project
nerv update [--dry-run] [--force-commands] [--only <files>]
```

## Troubleshooting

### Port Already in Use

```bash
lsof -i :19820
# or
ss -tlnp | grep 19820
```

Kill the process or change the port in `.nerv/a2a-config.yaml`.

### ChromaDB Corruption

Delete the ChromaDB directory and restart:

```bash
rm -rf .nerv/memory/chroma/
```

### ONNXRuntime Unavailable

On Python 3.14 or Windows, ONNXRuntime may not have a compatible wheel. NERV falls back to hash embeddings automatically. Search quality degrades to exact keyword matching.

### Hub Connection Refused

1. Verify hub is running: `curl http://127.0.0.1:19820`
2. Check `NERV_HUB_URL` matches your hub address
3. Verify `.nerv/a2a-config.yaml` exists
