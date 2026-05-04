/**
 * nerv-shell-env plugin for OpenCode.
 *
 * shell.env hook: injects NERV_AGENT_SOURCE based on the active OpenCode
 * agent name. Preserves existing value if already set.
 *
 * Agent name → source mapping:
 *   "nerv"          → "opencode:nerv"
 *   "sdd-*"         → "opencode:sdd-<phase>"
 *   "git-ops"       → "opencode:git-ops"
 *   "github-ops"    → "opencode:github-ops"
 *   everything else → "opencode:unknown"
 */

const AGENT_SOURCE_MAP = {
  nerv: "opencode:nerv",
  "git-ops": "opencode:git-ops",
  "github-ops": "opencode:github-ops",
};

function deriveSource(agentName) {
  if (!agentName || typeof agentName !== "string") return "opencode:unknown";
  if (AGENT_SOURCE_MAP[agentName]) return AGENT_SOURCE_MAP[agentName];
  if (agentName.startsWith("sdd-")) return `opencode:sdd-${agentName.replace("sdd-", "")}`;
  return "opencode:unknown";
}

/** shell.env hook — runs before each shell subprocess. */
export function onShellEnv(env, agentName) {
  try {
    // Never overwrite an already-set value
    if (env.NERV_AGENT_SOURCE) return env;

    const source = deriveSource(agentName);
    return { ...env, NERV_AGENT_SOURCE: source };
  } catch (err) {
    // Degrade silently — never block OpenCode
    return env;
  }
}
