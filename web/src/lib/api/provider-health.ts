/**
 * /api/health/providers/ wrapper — P1 slice 2.3 (SESSION 220).
 *
 * SPA-side client for the provider-status endpoint shipped in
 * SESSION 219 (P1 2.2, backend commit 4f09a62). Preserves the
 * server-side truthfulness invariants — see
 * `docs/production-readiness/REAL_MODE_PROVIDER_RUNBOOK.md` §2.4
 * for the full contract.
 *
 * Distinctions this schema preserves (any UI that consumes the
 * hook MUST keep these separate):
 *
 *   media-engine process reachability
 *     ≠ provider configuration
 *       ≠ provider adapter selected
 *         ≠ provider endpoint actually probed
 *           ≠ completed product journey
 *
 * In v1 every provider row's `reachable` is `null` because no
 * provider-specific safe probes are wired. Only
 * `media_engine.reachable` flips true/false today.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Enums that mirror provider_status.py ---------------------------

export const providerModeSchema = z.enum([
  "mock",
  "real",
  "unavailable",
  "unknown",
]);
export type ProviderMode = z.infer<typeof providerModeSchema>;

export const providerSourceSchema = z.enum([
  "media_engine_health",
  "shell_env",
  "engine_connection_row",
  "env_fallback",
  "none",
]);
export type ProviderSource = z.infer<typeof providerSourceSchema>;

export const topStatusSchema = z.enum([
  "ok",
  "degraded",
  "unavailable",  // reserved for future; not reachable in v1
]);
export type TopStatus = z.infer<typeof topStatusSchema>;

// ---- Per-provider row ----------------------------------------------

export const providerRowSchema = z.object({
  configured: z.boolean(),
  mode: providerModeSchema,
  // tri-state: true / false / null. Null is the truthful value when
  // no provider-specific probe was attempted.
  reachable: z.boolean().nullable(),
  source: providerSourceSchema,
  detail: z.string().nullable(),
});
export type ProviderRow = z.infer<typeof providerRowSchema>;

// ---- Media-engine sub-object ----------------------------------------
// Note: server-side response deliberately omits base_url. The SPA
// does not need internal service topology.

export const mediaEngineStatusSchema = z.object({
  reachable: z.boolean(),
  detail: z.string().nullable(),
});
export type MediaEngineStatus = z.infer<typeof mediaEngineStatusSchema>;

// ---- Full report shape ---------------------------------------------

export const PROVIDER_NAMES = [
  "runway",
  "image_gen",
  "llm_provider",
  "realtime",
  "openai_shell",
  "stability",
  "elevenlabs",
  "serper",
  "engine_bridge",
  // SESSION 224 F-07 — celery worker liveness. A dead worker
  // makes compositions spin forever with no user-visible signal;
  // this row surfaces the difference between "generating" and
  // "silently queued to a dead consumer."
  "celery_worker",
] as const;
export type ProviderName = (typeof PROVIDER_NAMES)[number];

const providersMapSchema = z.object({
  runway: providerRowSchema,
  image_gen: providerRowSchema,
  llm_provider: providerRowSchema,
  realtime: providerRowSchema,
  openai_shell: providerRowSchema,
  stability: providerRowSchema,
  elevenlabs: providerRowSchema,
  serper: providerRowSchema,
  engine_bridge: providerRowSchema,
  celery_worker: providerRowSchema,
});
export type ProvidersMap = z.infer<typeof providersMapSchema>;

const providerReportSchema = z.object({
  status: topStatusSchema,
  generated_at: z.string(),
  media_engine: mediaEngineStatusSchema,
  providers: providersMapSchema,
});
export type ProviderReport = z.infer<typeof providerReportSchema>;

// ---- Fetcher + hook -------------------------------------------------

export async function getProviderReport(
  workspaceId?: string,
): Promise<ProviderReport> {
  const path = workspaceId
    ? `/api/health/providers/?workspace=${encodeURIComponent(workspaceId)}`
    : "/api/health/providers/";
  return apiJson(path, {}, (json) => providerReportSchema.parse(json));
}

/**
 * Manual-refresh only: no polling. Callers use the returned
 * `refetch` to fire a fresh request when the operator clicks
 * "Refresh status". The endpoint's server-side media-engine
 * probe has a 3-second timeout — expect up to that latency
 * per call.
 */
export function useProviderReport(workspaceId?: string) {
  return useQuery({
    queryKey: ["provider-health", workspaceId ?? "unscoped"],
    queryFn: () => getProviderReport(workspaceId),
    staleTime: 0,
    // No refetchInterval on purpose — this is a diagnostics
    // surface, not a live-updating dashboard tile. Manual
    // refresh only, per SESSION 220 UI contract.
    refetchOnWindowFocus: false,
    retry: false,
  });
}
