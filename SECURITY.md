# Security

NERV runs entirely on localhost with no authentication. This section documents the trust model and risks.

## Trust Model

NERV assumes a **trusted local environment**. All network interfaces bind to `127.0.0.1` only. Any process running as the same user can access NERV services without credentials.

## Services and Attack Surface

### A2A Hub Server (port 19820)

| Aspect | Value |
|--------|-------|
| Bind address | `127.0.0.1` (loopback only) |
| Authentication | None |
| Protocol | JSON-RPC 2.0 over HTTP |
| Exposure | Local processes only |

**Risks:**
- Any local process can delegate tasks, read task state, or cancel tasks
- No rate limiting or request validation beyond schema checks
- `tasks/sendSubscribe` exposes SSE streams without authentication

**Mitigations:**
- Binds to `127.0.0.1` by default — not reachable from the network
- Port is configurable via `.nerv/a2a-config.yaml` or `NERV_HUB_URL`
- Do not change the bind address to `0.0.0.0` in shared environments

### Memory MCP Server

| Aspect | Value |
|--------|-------|
| Transport | stdio (MCP protocol) |
| Authentication | Process-level (must be launched by host) |
| Data | ChromaDB + SQLite in `.nerv/memory/` |

**Risks:**
- Memory content may contain sensitive project information (architecture decisions, bug details)
- No encryption at rest for `.nerv/memory/` directory

**Mitigations:**
- stdio transport means only the spawning process can communicate with it
- `NERV_MEMORY_PROFILE=safe` disables write-capable tools

### CLI (`nerv`)

| Aspect | Value |
|--------|-------|
| Transport | Local filesystem operations |
| Permissions | Same as invoking user |

**Risks:**
- `nerv init --force` overwrites existing files without confirmation
- Templates are rendered from local files — no remote code execution

## Recommendations

1. **Never expose port 19820 externally** — do not use `0.0.0.0` as `a2a_host` on multi-user systems
2. **Use `NERV_MEMORY_PROFILE=safe`** in untrusted or read-only contexts
3. **Treat `.nerv/memory/` as sensitive** — it contains project knowledge base
4. **Audit agent cards** in `.nerv/a2a-config.yaml` — agents can execute MCP tools via subprocess
5. **Use filesystem permissions** to restrict access to `.nerv/` directory on shared machines

## No Sandbox

NERV does not sandbox agent execution. Agents delegated via A2A hub run as the same user with the same filesystem access. This is by design — NERV is infrastructure, not a sandbox. Use OS-level isolation (containers, VMs, separate user accounts) if you need execution boundaries.
