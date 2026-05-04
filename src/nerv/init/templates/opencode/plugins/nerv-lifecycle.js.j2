/**
 * nerv-lifecycle plugin for OpenCode.
 *
 * Two hooks:
 * 1. experimental.session.compacting — injects SDD pipeline state into
 *    compaction prompts so SDD state survives context overflow.
 * 2. session.idle — auto-archives session summaries after 300s idle
 *    if SDD activity was detected.
 */

// ──────────────────────────────────────────────
// Internal: best-effort memory MCP read
// ──────────────────────────────────────────────

const MEMORY_MCP_URL = "http://127.0.0.1:19821";

async function memoryRecall(topicKey) {
  try {
    const res = await fetch(`${MEMORY_MCP_URL}/rpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: "memory_recall",
        params: { topic_key: topicKey },
      }),
      signal: AbortSignal.timeout(2000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.error) return null;
    return data.result;
  } catch {
    return null;
  }
}

async function memorySearch(query, limit = 10) {
  try {
    const res = await fetch(`${MEMORY_MCP_URL}/rpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: "memory_search",
        params: { query, limit },
      }),
      signal: AbortSignal.timeout(2000),
    });
    if (!res.ok) return [];
    const data = await res.json();
    if (data.error) return [];
    return data.result ?? [];
  } catch {
    return [];
  }
}

async function memorySessionSummary(summaryText) {
  try {
    const res = await fetch(`${MEMORY_MCP_URL}/rpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: "memory_session_summary",
        params: { summary: summaryText },
      }),
      signal: AbortSignal.timeout(2000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ──────────────────────────────────────────────
// Compaction hook
// ──────────────────────────────────────────────

const SDD_PHASES = [
  "context",
  "proposal",
  "spec",
  "design",
  "tasks",
  "impl",
  "verify",
];

/**
 * Reads SDD pipeline state from memory and embeds a compact summary
 * into the compaction context so SDD state survives context compaction.
 */
export async function onSessionCompacting(ctx) {
  try {
    // Search for active SDD topic keys
    const hits = await memorySearch("sdd-", 20);
    if (!hits || hits.length === 0) return ctx; // no SDD activity

    // Group by change_id (extract from topic_key pattern: sdd-<change_id>-<phase>)
    const byChange = {};
    for (const hit of hits) {
      const key = hit.topic_key || hit.id || "";
      const match = key.match(/^sdd-(.+)-(.+)$/);
      if (!match) continue;
      const [, changeId, phase] = match;
      if (!byChange[changeId]) byChange[changeId] = {};
      byChange[changeId][phase] = hit;
    }

    // Build summary for the 3 most recent change_ids
    const sorted = Object.entries(byChange)
      .map(([changeId, phases]) => {
        const completedPhases = SDD_PHASES.filter((p) => phases[p]);
        const currentPhase = SDD_PHASES.find((p) => !phases[p]) ?? "done";
        return { changeId, completedPhases, currentPhase, phases };
      })
      .sort((a, b) => b.completedPhases.length - a.completedPhases.length)
      .slice(0, 3);

    const lines = ["## SDD Pipeline State (survives compaction)"];
    for (const entry of sorted) {
      lines.push(`- **${entry.changeId}**: ${entry.completedPhases.length}/${SDD_PHASES.length} phases complete`);
      lines.push(`  Next: \`${entry.currentPhase}\``);
      lines.push(`  Completed: ${entry.completedPhases.join(", ") || "none"}`);
      lines.push(`  Memory keys: ${entry.completedPhases.map((p) => `\`sdd-${entry.changeId}-${p}\``).join(", ")}`);
    }

    const summary = lines.join("\n");

    // Inject into compaction context
    return {
      ...ctx,
      injectedContext: (ctx.injectedContext ?? "") + "\n\n" + summary,
    };
  } catch {
    // Degrade silently
    return ctx;
  }
}

// ──────────────────────────────────────────────
// Idle hook — auto-archive session summary
// ──────────────────────────────────────────────

const IDLE_THRESHOLD_MS = 300_000; // 5 minutes

export async function onSessionIdle(ctx) {
  try {
    // Only archive if we have a reasonable idle duration
    const idleMs = ctx.idleDurationMs ?? ctx.idleDuration ?? 0;
    if (idleMs < IDLE_THRESHOLD_MS) return;

    // Check for SDD activity before archiving (avoid noise)
    const hits = await memorySearch("sdd-", 3);
    if (!hits || hits.length === 0) return;

    const summary = `Session idle after ${Math.round(idleMs / 1000)}s. SDD activity detected (${hits.length} memory keys).`;
    await memorySessionSummary(summary);
  } catch {
    // Degrade silently — never block
  }
}
