#!/usr/bin/env bash
# NERV GitHub MCP wrapper — auto-detects GitHub token from gh CLI or env vars.
# Falls back in order: gh auth token → GITHUB_PERSONAL_ACCESS_TOKEN → GITHUB_TOKEN
set -euo pipefail

TOKEN=""

# 1. Try gh CLI (keyring-based, no env var needed)
if command -v gh &>/dev/null && gh auth token &>/dev/null; then
    TOKEN="$(gh auth token)"
fi

# 2. Fall back to explicit env vars
if [[ -z "${TOKEN:-}" ]]; then
    TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN:-}"
fi
if [[ -z "${TOKEN:-}" ]]; then
    TOKEN="${GITHUB_TOKEN:-}"
fi

if [[ -z "${TOKEN:-}" ]]; then
    echo "[nerv:github-mcp] No GitHub token found — run 'gh auth login' or set GITHUB_PERSONAL_ACCESS_TOKEN" >&2
    exit 1
fi

export GITHUB_PERSONAL_ACCESS_TOKEN="${TOKEN}"
exec npx -y @modelcontextprotocol/server-github "$@"
