/**
 * Composition status page — drives the polling shape parallel to
 * /videos/:id. Renders the step-by-step plan + final asset URL
 * when the composition reaches a terminal status.
 */
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, Circle, CornerDownRight, CornerUpRight, Library, Loader2, MinusCircle, ShieldAlert, XCircle } from "lucide-react";
import { VerificationStatusBadge } from "@/components/verification-status-badge";
import { Button } from "@/components/ui/button";
import {
  type Composition,
  type CompositionStep,
  type KnowledgeDocCitation,
  type LineageRef,
  type LineageDerivedFromEntry,
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
      <StatusBadge composition={c} />
      {lineage.data && lineage.data.derived_from.length > 0 && (
        <DerivedFromPanel entries={lineage.data.derived_from} />
      )}
      <StepList steps={c.steps} />
      {terminal && c.final_asset && <FinalAsset composition={c} />}
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
              <span className="font-mono text-amber-700 dark:text-amber-300">
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

function StatusBadge({ composition }: { composition: Composition }) {
  const statusStyle: Record<Composition["status"], string> = {
    draft: "border-muted-foreground/30 text-muted-foreground",
    planning: "border-muted-foreground/30 text-muted-foreground",
    running: "border-blue-500/40 bg-blue-500/5 text-blue-700 dark:text-blue-300",
    partial: "border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-300",
    completed: "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
    failed: "border-destructive/40 bg-destructive/5 text-destructive",
  };
  return (
    <div
      className={
        "flex items-center gap-3 rounded-md border p-4 " + statusStyle[composition.status]
      }
      data-testid="composition-status"
    >
      <StatusIcon status={composition.status} />
      <div className="flex flex-col">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em]">
          Status: {composition.status}
        </span>
        {composition.error_message && (
          <span className="text-sm">{composition.error_message}</span>
        )}
      </div>
    </div>
  );
}

function StepList({ steps }: { steps: CompositionStep[] }) {
  if (steps.length === 0) return null;
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-xl tracking-tight">Steps</h2>
      <ol className="flex flex-col gap-2">
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

function StepRow({ step }: { step: CompositionStep }) {
  return (
    <li
      className="flex items-start gap-3 rounded-md border bg-card p-4"
      data-testid={`composition-step-${step.position}`}
    >
      <StatusIcon status={step.status} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            #{step.position + 1}
          </span>
          <span className="font-medium">{step.primitive}</span>
        </div>
        {step.error_message && (
          <p className="text-sm text-destructive">{step.error_message}</p>
        )}
        {step.output_asset && (
          <p className="text-xs text-muted-foreground">
            <span className="font-mono">{step.output_asset.asset_type}</span>
            {step.output_asset.duration_ms != null && (
              <> · {(step.output_asset.duration_ms / 1000).toFixed(1)}s</>
            )}
          </p>
        )}
      </div>
    </li>
  );
}

function StatusIcon({
  status,
}: {
  status: Composition["status"] | CompositionStep["status"];
}) {
  switch (status) {
    case "completed":
    case "succeeded":
      return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
    case "running":
      return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-destructive" />;
    case "skipped":
      return <MinusCircle className="h-5 w-5 text-muted-foreground" />;
    case "partial":
      return <CheckCircle2 className="h-5 w-5 text-amber-600" />;
    default:
      return <Circle className="h-5 w-5 text-muted-foreground" />;
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
      className="flex flex-col gap-3 rounded-md border border-amber-500/50 bg-amber-500/5 p-5 text-sm"
      data-testid="composition-verifier-panel"
    >
      <div className="flex items-center justify-between border-b border-amber-500/30 pb-2">
        <div className="flex items-center gap-2">
          {isStrictReject ? (
            <ShieldAlert className="h-4 w-4 text-amber-700" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-amber-700" />
          )}
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-amber-800">
            K6.4 claim verifier
          </span>
        </div>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-amber-700">
          {isStrictReject
            ? "Strict — render blocked"
            : `Warn — ${warnings.length} flag${warnings.length === 1 ? "" : "s"}`}
        </span>
      </div>
      {warnings.length > 0 && (
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-800 mb-1">
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
          <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.18em] text-amber-800">
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

function FinalAsset({ composition }: { composition: Composition }) {
  const a = composition.final_asset!;
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-card p-5 shadow-paper"
      data-testid="composition-final-asset"
    >
      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        Final output
      </span>
      <p className="font-mono text-sm break-all">{a.file_path}</p>
      {composition.mock_mode ? (
        <p className="text-xs text-muted-foreground">
          Mock-mode output — no playable video. Disable mock mode to render
          for real.
        </p>
      ) : (
        a.file_path.startsWith("/") || a.file_path.startsWith("http") ? (
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
