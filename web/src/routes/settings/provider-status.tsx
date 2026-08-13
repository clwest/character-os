/**
 * /settings/provider-status — P1 slice 2.3 (SESSION 220).
 *
 * Operator-facing surface for the provider-status endpoint
 * shipped in SESSION 219. Renders configuration + selected mode +
 * (v1: null) reachability for nine provider surfaces, preserving
 * the server-side truthfulness invariants. Never implies:
 *
 *   * mode="real" means a provider call succeeded,
 *   * configured=true means credentials are valid,
 *   * reachable=null means provider failure,
 *   * media-engine reachability proves provider reachability,
 *   * or a provider is production-ready because its row is green.
 *
 * Not a customer configuration panel; not provider enablement UI.
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  MinusCircle,
  RefreshCw,
  ServerCog,
  XCircle,
} from "lucide-react";
import { useMe } from "@/lib/api/workspaces";
import { PROVIDER_NAMES, useProviderReport } from "@/lib/api/provider-health";
import type {
  ProviderMode,
  ProviderName,
  ProviderRow,
  ProviderSource,
  TopStatus,
} from "@/lib/api/provider-health";
import { ApiError } from "@/lib/api/client";

// -------------------- copy tables --------------------

const PROVIDER_LABELS: Record<ProviderName, string> = {
  runway: "Runway",
  image_gen: "Image generation",
  llm_provider: "LLM provider",
  realtime: "Realtime avatar",
  openai_shell: "OpenAI (shell services)",
  stability: "Stability AI",
  elevenlabs: "ElevenLabs",
  serper: "Serper",
  engine_bridge: "the sibling project engine bridge",
  celery_worker: "Celery worker (task queue)",
};

const MODE_LABELS: Record<ProviderMode, string> = {
  mock: "Mock mode selected",
  real: "Real mode selected",
  unavailable: "Would fail — configuration incomplete",
  unknown: "Mode unknown — media engine unreachable",
};

const SOURCE_LABELS: Record<ProviderSource, string> = {
  media_engine_health: "Read from media-engine /health",
  shell_env: "Read from Django-side environment",
  engine_connection_row: "Per-workspace EngineConnection row",
  env_fallback: "Environment fallback",
  none: "No configuration source resolved",
};

const TOP_STATUS_LABELS: Record<TopStatus, string> = {
  ok: "All checks green — no issues observed",
  degraded: "Partial status — some providers need attention",
  unavailable: "Provider report could not be constructed",
};

const REACHABLE_NULL_HINT =
  "No provider-specific probe was attempted. Media-engine reachability does not prove this provider is reachable.";

// -------------------- helpers --------------------

function ModeIcon({ mode }: { mode: ProviderMode }) {
  const cls = "h-3.5 w-3.5";
  if (mode === "real") return <CheckCircle2 className={`${cls} text-emerald-500`} aria-hidden="true" />;
  if (mode === "mock") return <MinusCircle className={`${cls} text-slate-400`} aria-hidden="true" />;
  if (mode === "unavailable") return <XCircle className={`${cls} text-rose-500`} aria-hidden="true" />;
  return <CircleHelp className={`${cls} text-amber-500`} aria-hidden="true" />;
}

function ReachableBadge({ reachable }: { reachable: boolean | null }) {
  if (reachable === null) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-md border border-fog/30 bg-fog/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-fog"
        data-testid="reachable-null"
      >
        <CircleHelp className="h-3 w-3" aria-hidden="true" />
        Not probed
      </span>
    );
  }
  if (reachable === true) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-500"
        data-testid="reachable-true">
        <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
        Probe succeeded
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-rose-500"
      data-testid="reachable-false">
      <XCircle className="h-3 w-3" aria-hidden="true" />
      Probe failed
    </span>
  );
}

// -------------------- route component --------------------

export function ProviderStatusRoute() {
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const scoped = Boolean(workspaceId);

  const report = useProviderReport(workspaceId);

  const authError = useMemo(() => {
    if (report.error instanceof ApiError) {
      if (report.error.status === 401) return "auth_required";
      if (report.error.status === 403) return "forbidden";
    }
    return null;
  }, [report.error]);

  return (
    <div className="max-w-3xl space-y-8" data-testid="provider-status-page">
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <ServerCog className="h-4 w-4 text-gold" aria-hidden="true" />
          <h1
            className="font-display text-xl italic text-cream"
            data-testid="provider-status-title"
          >
            Provider status
          </h1>
        </div>
        <p className="max-w-2xl text-sm text-fog">
          Operator-only view of provider configuration. This page describes
          what would be selected in each provider adapter — it does not
          prove that any provider is actually reachable, and it does not
          claim that any customer workflow has succeeded. Real-mode
          verification lives in{" "}
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-gold/80">
            DOGFOOD_MATRIX
          </span>
          .
        </p>
      </header>

      {authError === "auth_required" ? (
        <AuthGate reason="Sign in required to view provider status." />
      ) : authError === "forbidden" ? (
        <AuthGate reason="Your account does not have access to provider status." />
      ) : report.isPending ? (
        <LoadingBlock />
      ) : report.error ? (
        <GenericError
          detail={String(report.error?.message ?? "Unknown error")}
          onRetry={() => report.refetch()}
        />
      ) : report.data ? (
        <ReportView
          data={report.data}
          scoped={scoped}
          workspaceLabel={me.data?.default_workspace?.name ?? null}
          onRefresh={() => report.refetch()}
          fetching={report.isFetching}
        />
      ) : null}
    </div>
  );
}

// -------------------- sub-views --------------------

function LoadingBlock() {
  return (
    <div
      className="rounded-md border border-fog/20 bg-ink/40 p-6"
      role="status"
      aria-live="polite"
      data-testid="provider-status-loading"
    >
      <div className="flex items-center gap-2 text-sm text-fog">
        <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
        Checking providers…
      </div>
    </div>
  );
}

function AuthGate({ reason }: { reason: string }) {
  return (
    <div
      className="rounded-md border border-amber-500/40 bg-amber-500/5 p-6"
      role="alert"
      data-testid="provider-status-auth-gate"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" aria-hidden="true" />
        <div className="space-y-1">
          <p className="text-sm text-cream">{reason}</p>
          <Link
            to="/sign-in"
            className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.18em] text-gold hover:underline"
          >
            Go to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}

function GenericError({ detail, onRetry }: { detail: string; onRetry: () => void }) {
  return (
    <div
      className="rounded-md border border-rose-500/40 bg-rose-500/5 p-6"
      role="alert"
      data-testid="provider-status-error"
    >
      <div className="flex items-start gap-2">
        <XCircle className="mt-0.5 h-4 w-4 text-rose-500" aria-hidden="true" />
        <div className="space-y-2">
          <p className="text-sm text-cream">
            The provider-status endpoint could not be read. This does not
            mean any provider is down — the endpoint itself is unreachable
            or returned a shape the SPA cannot parse.
          </p>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-fog">
            {detail}
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 rounded-md border border-gold/40 bg-gold/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-gold hover:bg-gold/10"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Refresh status
          </button>
        </div>
      </div>
    </div>
  );
}

function ReportView({
  data,
  scoped,
  workspaceLabel,
  onRefresh,
  fetching,
}: {
  data: import("@/lib/api/provider-health").ProviderReport;
  scoped: boolean;
  workspaceLabel: string | null;
  onRefresh: () => void;
  fetching: boolean;
}) {
  const topLabel = TOP_STATUS_LABELS[data.status];
  const topClass =
    data.status === "ok"
      ? "border-emerald-500/40 bg-emerald-500/5 text-cream"
      : "border-amber-500/40 bg-amber-500/5 text-cream";

  return (
    <section className="space-y-6" data-testid="provider-status-report">
      {/* Top status */}
      <div
        className={`rounded-md border p-4 ${topClass}`}
        role="status"
        aria-live="polite"
        data-testid={`top-status-${data.status}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {data.status === "ok" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />
            )}
            <span className="text-sm">{topLabel}</span>
          </div>
          <div className="flex items-center gap-3">
            <span
              className="font-mono text-[10px] uppercase tracking-[0.24em] text-fog"
              data-testid="generated-at"
            >
              Generated {data.generated_at}
            </span>
            <button
              type="button"
              onClick={onRefresh}
              disabled={fetching}
              data-testid="refresh-button"
              className="inline-flex items-center gap-1 rounded-md border border-gold/40 bg-gold/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-gold hover:bg-gold/10 disabled:opacity-40"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${fetching ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              {fetching ? "Refreshing…" : "Refresh status"}
            </button>
          </div>
        </div>
      </div>

      {/* Media-engine sub-object */}
      <div
        className={`rounded-md border p-4 ${
          data.media_engine.reachable
            ? "border-emerald-500/30 bg-ink/40"
            : "border-amber-500/40 bg-amber-500/5"
        }`}
        data-testid="media-engine-block"
      >
        <div className="flex items-center gap-2">
          {data.media_engine.reachable ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />
          )}
          <p className="text-sm text-cream">
            {data.media_engine.reachable
              ? "Media engine reachable"
              : "Media engine unavailable — showing partial status"}
          </p>
        </div>
        {data.media_engine.detail ? (
          <p
            className="mt-1 pl-6 font-mono text-[11px] uppercase tracking-[0.18em] text-fog"
            data-testid="media-engine-detail"
          >
            {data.media_engine.detail}
          </p>
        ) : null}
        <p className="mt-1 pl-6 text-xs text-fog">
          Media-engine process reachability does not prove that any
          upstream provider is reachable.
        </p>
      </div>

      {/* Workspace context */}
      <div
        className="rounded-md border border-fog/20 bg-ink/30 p-3 text-xs text-fog"
        data-testid="workspace-context"
      >
        {scoped
          ? `Engine-bridge row scoped to workspace: ${workspaceLabel ?? "(default)"}.`
          : "No workspace context available. Engine-bridge row reflects environment fallback only — per-workspace EngineConnection rows are not considered."}
      </div>

      {/* Provider grid */}
      <ul className="space-y-3" data-testid="provider-list">
        {PROVIDER_NAMES.map((name) => (
          <li key={name}>
            <ProviderRowCard name={name} row={data.providers[name]} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProviderRowCard({ name, row }: { name: ProviderName; row: ProviderRow }) {
  const label = PROVIDER_LABELS[name];
  return (
    <section
      className="rounded-md border border-fog/20 bg-ink/30 p-4"
      aria-label={`${label} — ${MODE_LABELS[row.mode]}`}
      data-testid={`provider-row-${name}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="font-display text-base italic text-cream">{label}</h2>
          <p
            className="font-mono text-[10px] uppercase tracking-[0.24em] text-fog"
            data-testid={`provider-name-${name}`}
          >
            {name}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center gap-1 rounded-md border border-fog/30 bg-fog/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-fog"
            data-testid={`configured-${name}`}
          >
            {row.configured ? "Configured" : "Not configured"}
          </span>
          <span
            className="inline-flex items-center gap-1 rounded-md border border-fog/30 bg-fog/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-fog"
            data-testid={`mode-${name}`}
          >
            <ModeIcon mode={row.mode} />
            {MODE_LABELS[row.mode]}
          </span>
          <ReachableBadge reachable={row.reachable} />
        </div>
      </div>

      <p
        className="mt-2 font-mono text-[10px] uppercase tracking-[0.24em] text-fog"
        data-testid={`source-${name}`}
      >
        Source · {SOURCE_LABELS[row.source]}
      </p>
      {row.detail ? (
        <p
          className="mt-1 text-xs text-fog"
          data-testid={`detail-${name}`}
        >
          {row.detail}
        </p>
      ) : null}
      {row.reachable === null ? (
        <p
          className="mt-1 text-xs italic text-fog"
          data-testid={`reachable-null-hint-${name}`}
        >
          {REACHABLE_NULL_HINT}
        </p>
      ) : null}
    </section>
  );
}
