/**
 * Composition status page — drives the polling shape parallel to
 * /videos/:id. Renders the step-by-step plan + final asset URL
 * when the composition reaches a terminal status.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, CornerDownRight, CornerUpRight, Download, Library, Loader2, MinusCircle, ShieldAlert, XCircle } from "lucide-react";
import { VerificationStatusBadge } from "@/components/verification-status-badge";
import { Button } from "@/components/ui/button";
import {
  type Composition,
  type CompositionStep,
  type KnowledgeDocCitation,
  type LineageRef,
  type LineageDerivedFromEntry,
  type ProducedAsset,
  isTerminalStatus,
  useComposition,
  useCompositionLineage,
} from "@/lib/api/recipes";

export function CompositionStatusRoute() {
  const { id } = useParams<{ id: string }>();
  const composition = useComposition(id);
  const lineage = useCompositionLineage(id);

  if (composition.isLoading) {
    return <StatusSkeleton />;
  }
  if (composition.isError || !composition.data) {
    return (
      <NotFound
        message={
          composition.error instanceof Error
            ? composition.error.message
            : "Composition not found"
        }
      />
    );
  }

  const c = composition.data;
  const terminal = isTerminalStatus(c.status);

  return (
    <div className="flex flex-col gap-8 py-10">
      <Header composition={c} />
      <ProgressSummary composition={c} />
      {lineage.data && lineage.data.derived_from.length > 0 && (
        <DerivedFromPanel entries={lineage.data.derived_from} />
      )}
      <StepList steps={c.steps} />
      {terminal && c.final_asset && <FinalAsset composition={c} />}
      {c.produced_assets.length > 0 && (
        <ProducedAssetsPanel assets={c.produced_assets} />
      )}
      {terminal && !c.final_asset && c.status === "failed" && (
        <FailedCallout composition={c} />
      )}
      {(c.verification_warnings.length > 0 || c.rejected_synthesis) && (
        <VerifierPanel composition={c} />
      )}
      {c.synthesized_brief && <SynthesizedBriefPanel composition={c} />}
      {c.knowledge_docs_used.length > 0 && (
        <CitationsPanel docs={c.knowledge_docs_used} />
      )}
      {lineage.data && lineage.data.used_by.length > 0 && (
        <UsedByPanel entries={lineage.data.used_by} />
      )}
    </div>
  );
}

function Header({ composition }: { composition: Composition }) {
  return (
    <header className="flex flex-col gap-3 border-b pb-6">
      <Link
        to="/recipes"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        All recipes
      </Link>
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        {composition.template_kind}
      </span>
      <h1 className="font-display text-3xl leading-tight tracking-tight md:text-4xl">
        {composition.name}
      </h1>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm text-muted-foreground">
          Composition <span className="font-mono">{composition.id.slice(0, 8)}</span>
          {composition.mock_mode && (
            <>
              {" • "}
              <span className="font-mono text-warning">
                mock mode
              </span>
            </>
          )}
        </p>
        {composition.verification_status && (
          <VerificationStatusBadge status={composition.verification_status} />
        )}
      </div>
    </header>
  );
}

// SESSION 251 redesign — replaces the old full-width StatusBadge +
// card-per-step list. Operator feedback while dogfooding
// talking_head_with_backdrop (9 steps): the previous layout meant
// scrolling through 9 large cards to see "how far along am I."
// This condenses the header into one row of status + segmented
// tick bar + counts, and the step list into one line per step.
// Detail (error message, output asset tag) still surfaces inline
// on the matching row.
function ProgressSummary({ composition }: { composition: Composition }) {
  const statusStyle: Record<Composition["status"], string> = {
    draft: "border-muted-foreground/30 text-muted-foreground",
    planning: "border-muted-foreground/30 text-muted-foreground",
    running: "border-accent/40 bg-accent/10 text-accent",
    partial: "border-warning/40 bg-warning/10 text-warning",
    completed: "border-success/40 bg-success/10 text-success",
    failed: "border-destructive/40 bg-destructive/5 text-destructive",
  };

  const steps = composition.steps
    .slice()
    .sort((a, b) => a.position - b.position);
  const total = steps.length;
  const done = steps.filter(
    (s) => s.status === "succeeded" || s.status === "skipped",
  ).length;
  const runningStep = steps.find((s) => s.status === "running");
  const failedStep = steps.find((s) => s.status === "failed");

  const dollars = (composition.cost_actual_micros / 1_000_000).toFixed(2);
  const elapsedLabel = useElapsedLabel(
    composition.created_at,
    composition.updated_at,
    isTerminalStatus(composition.status),
  );

  // One-line status summary — mirrors the shape the operator asked
  // for: "3/9 · step 4 running · elapsed · $ spent" without needing
  // to scroll.
  const progressText = total > 0 ? `${done} / ${total}` : composition.status;
  const detailBits: string[] = [];
  if (runningStep) {
    detailBits.push(`step ${runningStep.position + 1} running`);
  } else if (failedStep) {
    detailBits.push(`step ${failedStep.position + 1} failed`);
  }
  if (elapsedLabel) detailBits.push(elapsedLabel);
  if (composition.cost_actual_micros > 0) detailBits.push(`$${dollars}`);

  return (
    <section
      className={
        "flex flex-col gap-3 rounded-md border p-4 " +
        statusStyle[composition.status]
      }
      data-testid="composition-status"
    >
      <div className="flex flex-wrap items-center gap-3">
        <StatusIcon status={composition.status} />
        <span className="font-mono text-[11px] uppercase tracking-[0.22em]">
          Status: {composition.status}
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-current/70">
          {progressText}
        </span>
        {detailBits.length > 0 && (
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-current/70">
            · {detailBits.join(" · ")}
          </span>
        )}
      </div>
      {total > 0 && <TickBar steps={steps} />}
      {composition.error_message && (
        <p className="text-sm">{composition.error_message}</p>
      )}
    </section>
  );
}

// Segmented tick bar — one tick per step, colored by state. Reads
// left-to-right in step order. Kept intentionally simple (no
// animations beyond the running-tick pulse) so a wide composition
// still reads at a glance.
function TickBar({ steps }: { steps: CompositionStep[] }) {
  return (
    <div
      className="flex flex-wrap gap-1"
      data-testid="composition-tick-bar"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={steps.length}
      aria-valuenow={
        steps.filter((s) => s.status === "succeeded" || s.status === "skipped").length
      }
    >
      {steps.map((step) => (
        <span
          key={step.id}
          data-testid={`composition-tick-${step.position}`}
          data-status={step.status}
          title={`#${step.position + 1} ${step.primitive} — ${step.status}`}
          className={
            "h-1.5 min-w-6 flex-1 rounded-sm " + tickTone(step.status)
          }
        />
      ))}
    </div>
  );
}

function tickTone(status: CompositionStep["status"]): string {
  switch (status) {
    case "succeeded":
      return "bg-success/80";
    case "running":
      return "bg-accent animate-pulse";
    case "failed":
      return "bg-destructive/80";
    case "skipped":
      return "bg-muted-foreground/30";
    default:
      return "bg-muted-foreground/15";
  }
}

// Composition-level elapsed. Uses ``created_at`` → ``updated_at``
// for terminal compositions; live-ticks (1 Hz) against ``now`` for
// running ones so operators see a moving clock instead of stale
// "0 min" until the next poll. Poll cadence itself is separate
// (recipes.ts refetchInterval).
function useElapsedLabel(
  createdAt: string,
  updatedAt: string,
  isTerminal: boolean,
): string | null {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (isTerminal) return;
    const t = setInterval(() => setNowMs(Date.now()), 1_000);
    return () => clearInterval(t);
  }, [isTerminal]);

  const startMs = Date.parse(createdAt);
  const endMs = isTerminal ? Date.parse(updatedAt) : nowMs;
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return null;
  const seconds = Math.max(0, Math.round((endMs - startMs) / 1_000));
  return formatElapsed(seconds);
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return s === 0 ? `${m}m` : `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return mm === 0 ? `${h}h` : `${h}h ${mm}m`;
}

function StepList({ steps }: { steps: CompositionStep[] }) {
  if (steps.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="font-display text-xl tracking-tight">Steps</h2>
      <ol className="flex flex-col divide-y overflow-hidden rounded-md border bg-card">
        {steps
          .slice()
          .sort((a, b) => a.position - b.position)
          .map((step) => (
            <StepRow key={step.id} step={step} />
          ))}
      </ol>
    </section>
  );
}

// Collapsed one-liner. Row itself is a single line; error text and
// output-asset tag land on secondary lines inside the same row so
// the row still gives up its info without expanding into a card.
function StepRow({ step }: { step: CompositionStep }) {
  return (
    <li
      className="flex flex-col gap-1 px-3 py-2 text-sm"
      data-testid={`composition-step-${step.position}`}
    >
      <div className="flex items-center gap-3">
        <span className="shrink-0" aria-hidden>
          <StatusIcon status={step.status} small />
        </span>
        <span className="w-8 shrink-0 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          #{step.position + 1}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium">
          {step.primitive}
        </span>
        <StepTrailingTag step={step} />
      </div>
      {step.error_message && (
        <p className="pl-14 text-xs text-destructive">{step.error_message}</p>
      )}
    </li>
  );
}

function StepTrailingTag({ step }: { step: CompositionStep }) {
  // Right-side tag: output_asset shape for succeeded steps, plain
  // status word otherwise. Kept small + monospace so it doesn't
  // fight the primitive name for attention.
  if (step.output_asset) {
    const durationMs = step.output_asset.duration_ms;
    return (
      <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {step.output_asset.asset_type}
        {durationMs != null && ` · ${(durationMs / 1000).toFixed(1)}s`}
      </span>
    );
  }
  if (step.status === "pending") return null;
  return (
    <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
      {step.status}
    </span>
  );
}

function StatusIcon({
  status,
  small = false,
}: {
  status: Composition["status"] | CompositionStep["status"];
  small?: boolean;
}) {
  const size = small ? "h-3.5 w-3.5" : "h-5 w-5";
  switch (status) {
    case "completed":
    case "succeeded":
      return <CheckCircle2 className={`${size} text-success`} />;
    case "running":
      return <Loader2 className={`${size} animate-spin text-accent`} />;
    case "failed":
      return <XCircle className={`${size} text-destructive`} />;
    case "skipped":
      return <MinusCircle className={`${size} text-muted-foreground`} />;
    case "partial":
      return <CheckCircle2 className={`${size} text-warning`} />;
    default:
      return <Circle className={`${size} text-muted-foreground`} />;
  }
}

function SynthesizedBriefPanel({ composition }: { composition: Composition }) {
  // K6.6 — what K6 actually said. Renders only on successful
  // renders where the LLM synthesized (verified / skipped
  // statuses). Strict-mode rejections show their text in the
  // VerifierPanel above; this panel covers the "render
  // shipped — what did it say?" audit case.
  return (
    <section
      className="flex flex-col gap-2 rounded-md border bg-card p-5 text-sm shadow-paper"
      data-testid="composition-synthesized-brief"
    >
      <div className="flex items-center justify-between border-b pb-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          K6 synthesized brief
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {composition.synthesized_brief.split(/\s+/).length} words
        </span>
      </div>
      <p className="whitespace-pre-wrap text-foreground">
        {composition.synthesized_brief}
      </p>
    </section>
  );
}


function VerifierPanel({ composition }: { composition: Composition }) {
  const warnings = composition.verification_warnings ?? [];
  const rejected = composition.rejected_synthesis ?? "";
  const isStrictReject = rejected.length > 0;
  return (
    <section
      className="flex flex-col gap-3 rounded-md border border-warning/40 bg-warning/10 p-5 text-sm"
      data-testid="composition-verifier-panel"
    >
      <div className="flex items-center justify-between border-b border-warning/30 pb-2">
        <div className="flex items-center gap-2">
          {isStrictReject ? (
            <ShieldAlert className="h-4 w-4 text-warning" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-warning" />
          )}
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-warning">
            K6.4 claim verifier
          </span>
        </div>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-warning">
          {isStrictReject
            ? "Strict — render blocked"
            : `Warn — ${warnings.length} flag${warnings.length === 1 ? "" : "s"}`}
        </span>
      </div>
      {warnings.length > 0 && (
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-warning mb-1">
            Unsupported claims
          </div>
          <ul className="list-disc space-y-0.5 pl-5 text-foreground">
            {warnings.map((w, i) => (
              <li key={`${w.claim}-${i}`}>
                <span className="font-mono">"{w.claim}"</span>{" "}
                <span className="text-muted-foreground">({w.kind})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {rejected && (
        <details>
          <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.18em] text-warning">
            Show what the LLM almost said
          </summary>
          <p className="mt-1 whitespace-pre-wrap rounded-md bg-background/60 p-2 text-xs text-muted-foreground">
            {rejected}
          </p>
        </details>
      )}
    </section>
  );
}

function CitationsPanel({ docs }: { docs: KnowledgeDocCitation[] }) {
  const totalChunks = docs.reduce((sum, d) => sum + d.chunk_count, 0);
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-card p-5 shadow-paper"
      data-testid="composition-citations"
    >
      <div className="flex items-center justify-between border-b pb-2">
        <div className="flex items-center gap-2">
          <Library className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-base tracking-tight">Knowledge used</h2>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {docs.length} doc{docs.length === 1 ? "" : "s"} · {totalChunks} chunk
          {totalChunks === 1 ? "" : "s"}
        </span>
      </div>
      <ul className="flex flex-col gap-1.5">
        {docs.map((doc) => (
          <li key={doc.id}>
            <Link
              to={`/workspace/knowledge/${doc.id}`}
              className="flex items-baseline justify-between gap-3 rounded-sm border bg-muted/30 px-3 py-2 transition-colors hover:border-foreground"
              data-testid={`citation-${doc.id}`}
            >
              <span className="truncate text-sm">{doc.title}</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {doc.chunk_count} chunk{doc.chunk_count === 1 ? "" : "s"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DerivedFromPanel({ entries }: { entries: LineageDerivedFromEntry[] }) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-muted/30 p-4"
      data-testid="lineage-derived-from"
    >
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        <CornerDownRight className="h-3.5 w-3.5" />
        Derived from
      </div>
      <ul className="flex flex-col gap-2">
        {entries.map((entry) => (
          <li key={`${entry.composition_id}-${entry.asset_id}`}>
            <Link
              to={`/compositions/${entry.composition_id}`}
              className="flex items-baseline justify-between gap-3 rounded-sm border bg-card px-3 py-2 transition-colors hover:border-foreground"
              data-testid={`derived-from-${entry.composition_id}`}
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-sm">{entry.composition_name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {entry.template_kind} · {entry.asset_type}
                </span>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {entry.status}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function UsedByPanel({ entries }: { entries: LineageRef[] }) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-muted/30 p-4"
      data-testid="lineage-used-by"
    >
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        <CornerUpRight className="h-3.5 w-3.5" />
        Used by {entries.length} composition{entries.length === 1 ? "" : "s"}
      </div>
      <ul className="flex flex-col gap-2">
        {entries.map((entry) => (
          <li key={entry.composition_id}>
            <Link
              to={`/compositions/${entry.composition_id}`}
              className="flex items-baseline justify-between gap-3 rounded-sm border bg-card px-3 py-2 transition-colors hover:border-foreground"
              data-testid={`used-by-${entry.composition_id}`}
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-sm">{entry.composition_name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {entry.template_kind}
                </span>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {entry.status}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

// A8 (SESSION 192) — Asset Library v1 cross-link. Lists every Asset
// the composition's pipeline produced, with role badge + storage-health
// tone + link to the A6 detail view at /workspace/assets/<id>. is_final
// gets a "Final" pill so the operator can scan the pipeline output and
// spot the deliverable at a glance.
function ProducedAssetsPanel({ assets }: { assets: ProducedAsset[] }) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-muted/30 p-4"
      data-testid="produced-assets-panel"
    >
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        <Library className="h-3.5 w-3.5" />
        Produced {assets.length} asset{assets.length === 1 ? "" : "s"}
      </div>
      <ul className="flex flex-col gap-2">
        {assets.map((a) => (
          <li key={a.id}>
            <Link
              to={`/workspace/assets/${a.id}`}
              className="flex items-baseline justify-between gap-3 rounded-sm border bg-card px-3 py-2 transition-colors hover:border-foreground"
              data-testid={`produced-asset-${a.id}`}
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-sm">
                  {a.title || a.file_path || "Untitled asset"}
                </span>
                <span className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  <span>{a.asset_type}</span>
                  {a.role && (
                    <span className="rounded-sm border px-1.5 py-0.5">
                      {a.role.replace(/_/g, " ")}
                    </span>
                  )}
                  <span className={producedStorageTone(a.storage_health)}>
                    {a.storage_health.replace(/_/g, " ")}
                  </span>
                </span>
              </div>
              {a.is_final && (
                <span className="rounded-sm border border-foreground/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-foreground">
                  Final
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function producedStorageTone(storage: string): string {
  // Match A5's storageHealthTone palette without importing the
  // workspace-assets module (avoids a cross-route coupling).
  if (storage === "https_live" || storage === "local_present") {
    return "text-emerald-500";
  }
  if (storage === "https_expiring_soon") {
    return "text-amber-500";
  }
  if (storage === "https_expired" || storage === "local_missing") {
    return "text-destructive";
  }
  return "text-muted-foreground";
}

function FinalAsset({ composition }: { composition: Composition }) {
  const a = composition.final_asset!;
  const hasPlayableSrc =
    !composition.mock_mode &&
    (a.file_path.startsWith("/") || a.file_path.startsWith("http"));
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-card p-5 shadow-paper"
      data-testid="composition-final-asset"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Final output
        </span>
        {hasPlayableSrc && (
          <Button asChild size="sm" variant="outline" data-testid="composition-download">
            <a
              href={a.file_path}
              download={downloadFilename(composition, a.file_path)}
            >
              <Download className="h-3.5 w-3.5" />
              Download
            </a>
          </Button>
        )}
      </div>
      <p className="font-mono text-sm break-all">{a.file_path}</p>
      {composition.mock_mode ? (
        <p className="text-xs text-muted-foreground">
          Mock-mode output — no playable video. Disable mock mode to render
          for real.
        </p>
      ) : (
        hasPlayableSrc ? (
          <video
            controls
            className="w-full rounded border"
            src={a.file_path}
          />
        ) : null
      )}
    </section>
  );
}

// Suggest a friendly download name. Priority:
//   1. Composition name (slugified) + inferred extension
//   2. The URL's basename (whatever the server serves)
// Browsers respect ``download`` on same-origin URLs (the /data
// proxy makes media-engine files same-origin); cross-origin
// URLs fall back to opening in a new tab, which is still a
// one-right-click save.
function downloadFilename(composition: Composition, filePath: string): string {
  const extMatch = filePath.match(/\.(mp4|mov|webm|mp3|wav|png|jpg|jpeg)(?:\?|$)/i);
  const ext = extMatch?.[1]?.toLowerCase() ?? "mp4";
  const raw = (composition.name || "video").trim();
  const slug = raw
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || "video";
  return `${slug}.${ext}`;
}

function FailedCallout({ composition }: { composition: Composition }) {
  return (
    <section className="rounded-md border border-destructive/40 bg-destructive/5 p-5 text-sm">
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-destructive">
        Failed
      </p>
      <p className="mt-2">
        {composition.error_message || "The composition reported failed status without a message."}
      </p>
    </section>
  );
}

function NotFound({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-3 py-10">
      <p className="font-display text-2xl">Composition not found</p>
      <p className="text-sm text-muted-foreground">{message}</p>
      <Button asChild variant="outline" size="sm">
        <Link to="/recipes">Back to gallery</Link>
      </Button>
    </div>
  );
}

function StatusSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6 py-10">
      <div className="h-10 w-1/2 rounded bg-muted" />
      <div className="h-16 rounded bg-muted" />
      <div className="h-32 rounded bg-muted" />
    </div>
  );
}
