/**
 * Bridge-tool catalog for the /workspace/tools UI (C5).
 *
 * Client-side metadata mirror of the engine-bridge tools registered
 * on the Django side under shell/apps/realtime/tools/. Kept as a static
 * constant instead of a live API fetch because:
 *
 *   - v1 tool set is stable (no per-workspace overrides).
 *   - The picker needs synchronous label + hint access during render.
 *   - A dedicated tool-catalog endpoint is queued as follow-on work
 *     alongside P3 4.4's full catalog list-view (candidate C6).
 *
 * v1 ships `consult_engine` only. `query_spider_data` and
 * `agent_consult` are backend-registered but intentionally excluded
 * from the SPA picker per SESSION 226 F-10-C ratification: both
 * require args (`topic`, `agent_name`) the C5.1 single-question
 * form does not send. The C5 arc closed with a one-tool SPA
 * surface; a follow-on slice (candidate C6) ships a per-tool
 * fields renderer (F-10-B pattern) and re-enables the other two.
 *
 * When re-enabling: update this list AND `tools.test.tsx`'s option-
 * count assertions AND `docs/design/BRIDGE_TOOLS_UI_V1.md` contract
 * rule 4 in the same commit; without the paired doc change the
 * SPA drifts from the scope-lock.
 *
 * Cost note: value is authoritative from the Python decorator as of
 * SESSION 225. `consult_engine` = $0.005 — under the R7.0 $0.05
 * approval threshold, so C5 forms submit inline without triggering
 * the R8.1 approval modal.
 *
 * Tier note: EB rule 8 puts the load-bearing tier gate in the
 * `resolve_engine_connection` resolver, not on the tool spec. The Python
 * tool spec's `tier_required="starter"` is misleading — a Starter
 * workspace's dispatch fails at the resolver (returns None → tool
 * executor returns "engine not configured" error). SPA presents Pro+
 * as the effective tier.
 */

export interface BridgeToolMeta {
  /** Backend tool name, must match `@register_tool(name=...)`. */
  name: string;
  /** Short label shown in the picker. */
  label: string;
  /** One-line hint shown below the picker or as an option subtitle. */
  hint: string;
  /** Cost per invocation in micros (1 dollar = 1_000_000 micros). */
  cost_micros: number;
  /** Effective tier the operator's workspace needs. Pro+ across the board. */
  effective_tier: "pro";
}

export const BRIDGE_TOOLS: BridgeToolMeta[] = [
  {
    name: "consult_engine",
    label: "Consult engine",
    hint: "Ask your configured engine a direct question. Best for one-shot lookups.",
    cost_micros: 5_000,
    effective_tier: "pro",
  },
  // query_spider_data + agent_consult intentionally excluded — see
  // module-level comment for v1-scope rationale (F-10-C).
];

/**
 * Format a per-tool cost for inline display in the picker.
 * `5_000` → "$0.005"; `7_500` → "$0.0075".
 */
export function formatToolCost(costMicros: number): string {
  const dollars = costMicros / 1_000_000;
  // Keep enough precision to distinguish 5k from 7.5k without trailing zeros.
  return `$${dollars.toFixed(4).replace(/0+$/, "").replace(/\.$/, ".0")}`;
}

/**
 * Format a picker option label with inline tier + cost hints (partial P3 4.4).
 * "Consult engine — Pro · $0.005"
 */
export function formatToolOptionLabel(tool: BridgeToolMeta): string {
  const tierLabel = tool.effective_tier === "pro" ? "Pro" : tool.effective_tier;
  return `${tool.label} — ${tierLabel} · ${formatToolCost(tool.cost_micros)}`;
}
