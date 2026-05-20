/**
 * /workspace/transcripts/:id — Transcript detail + mining trigger.
 *
 * SESSION 202 / B1.5. Shows the full transcript body, "Mine highlights"
 * button with knobs, and the existing highlights for this transcript.
 *
 * B1.6 will add approve/reject buttons per highlight — NOT in this slice.
 *
 * Scope: docs/design/TRANSCRIPT_MINER_V1.md §B1.5.
 */
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ChevronLeft,
  Loader2,
  Sparkles,
  AlertCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTranscript } from "@/lib/api/transcripts";
import {
  useHighlightsForTranscript,
  useMineTranscript,
  highlightStatusLabel,
  highlightStatusTone,
  type TranscriptHighlight,
} from "@/lib/api/transcripts";
import { relativeTime } from "@/lib/api/workspace-assets";
import { cn } from "@/lib/utils";

// ---- Constants -----------------------------------------------

const DEFAULT_TARGET_COUNT = 5;
const DEFAULT_MAX_CHARS = 280;

// ---- Page component ------------------------------------------

export function WorkspaceTranscriptDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const asset = useTranscript(id);

  if (asset.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <LoadingSkeleton />
      </div>
    );
  }

  if (asset.isError) {
    const err = asset.error as { status?: number; message?: string } | null;
    const is404 = err?.status === 404;
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        {is404 ? (
          <NotFound />
        ) : (
          <ErrorPanel
            message={err?.message ?? "Failed to load transcript."}
            onRetry={() => asset.refetch()}
          />
        )}
      </div>
    );
  }

  if (!asset.data) return null;

  const data = asset.data;
  const displayTitle =
    data.title ||
    `Untitled transcript · ${relativeTime(data.created_at)}`;

  return (
    <div
      data-testid="transcript-detail"
      className="flex flex-col gap-10"
    >
      <BackLink />

      {/* ---- Page header ----------------------------------------- */}
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1
            data-testid="transcript-detail-title"
            className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
          >
            {displayTitle}
          </h1>
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-sm border border-border bg-muted/50 px-2.5 py-1 text-[11px] text-muted-foreground">
            Transcript
          </span>
        </div>

        {/* Metadata row */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span>Created {new Date(data.created_at).toLocaleString()}</span>
          {data.size_bytes != null && data.size_bytes > 0 && (
            <span className="font-mono">{data.size_bytes.toLocaleString()} chars</span>
          )}
          {data.primitive_kind && (
            <code className="rounded-sm border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
              {data.primitive_kind}
            </code>
          )}
        </div>
      </header>

      {/* ---- Transcript body ------------------------------------ */}
      <section
        data-testid="transcript-body-section"
        className="rounded-md border border-border bg-card p-5"
      >
        <h2 className="mb-3 font-display text-lg tracking-tight text-muted-foreground">
          Transcript
        </h2>
        {data.inline_content ? (
          <pre
            data-testid="transcript-body"
            className="whitespace-pre-wrap text-sm leading-relaxed font-mono max-h-[480px] overflow-y-auto"
          >
            {data.inline_content}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">
            No transcript body available.
          </p>
        )}
      </section>

      {/* ---- Mining panel --------------------------------------- */}
      {id && <MiningPanel transcriptId={id} inlineContent={data.inline_content} />}
    </div>
  );
}

// ---- MiningPanel ---------------------------------------------

function MiningPanel({
  transcriptId,
  inlineContent,
}: {
  transcriptId: string;
  inlineContent: string;
}) {
  const [targetCount, setTargetCount] = useState(DEFAULT_TARGET_COUNT);
  const [maxChars, setMaxChars] = useState(DEFAULT_MAX_CHARS);
  const [mineError, setMineError] = useState<string | null>(null);

  const highlights = useHighlightsForTranscript(transcriptId);
  const mine = useMineTranscript();

  const hasContent = Boolean(inlineContent?.trim());

  async function handleMine() {
    setMineError(null);
    try {
      await mine.mutateAsync({
        transcript_asset_id: transcriptId,
        target_count: targetCount,
        max_chars: maxChars,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Mining failed. Please try again.";
      setMineError(message);
    }
  }

  return (
    <section
      data-testid="mining-panel"
      className="flex flex-col gap-6 rounded-md border border-border bg-card p-5"
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-xl tracking-tight">
            Mine highlights
          </h2>
          <p className="text-sm text-muted-foreground">
            The LLM will find the most shareable moments and save them as
            highlights for your review.
          </p>
        </div>
      </div>

      {/* Knobs */}
      <div className="flex flex-wrap gap-6">
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="target-count"
            className="text-xs font-medium text-muted-foreground"
          >
            Number of highlights
          </label>
          <Input
            id="target-count"
            data-testid="target-count-input"
            type="number"
            min={1}
            max={10}
            value={targetCount}
            onChange={(e) => setTargetCount(Number(e.target.value))}
            className="h-8 w-24 text-sm"
            disabled={mine.isPending}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="max-chars"
            className="text-xs font-medium text-muted-foreground"
          >
            Max chars per highlight
          </label>
          <Input
            id="max-chars"
            data-testid="max-chars-input"
            type="number"
            min={50}
            max={280}
            value={maxChars}
            onChange={(e) => setMaxChars(Number(e.target.value))}
            className="h-8 w-28 text-sm"
            disabled={mine.isPending}
          />
        </div>
      </div>

      {/* Mine button */}
      <div className="flex items-center gap-3">
        <Button
          type="button"
          data-testid="mine-highlights-btn"
          disabled={mine.isPending || !hasContent}
          onClick={() => void handleMine()}
        >
          {mine.isPending ? (
            <>
              <Loader2
                data-testid="mine-spinner"
                className="mr-2 h-4 w-4 animate-spin"
              />
              Mining…
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Mine highlights
            </>
          )}
        </Button>
        {!hasContent && (
          <p className="text-xs text-muted-foreground">
            No transcript body to mine.
          </p>
        )}
      </div>

      {/* Inline error */}
      {mineError && (
        <div
          data-testid="mine-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{mineError}</p>
        </div>
      )}

      {/* Mining returned empty (no LLM synthesis) */}
      {mine.isSuccess && mine.data.highlights.length === 0 && (
        <div
          data-testid="mine-empty-result"
          className="rounded-md border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-400"
        >
          {mine.data.used_synthesis
            ? "The model ran but found no shareable highlights. Try adjusting the knobs or check the transcript content."
            : "Mining did not run — the LLM helper was not available (check server configuration)."}
        </div>
      )}

      {/* Highlights list */}
      <HighlightsList
        transcriptId={transcriptId}
        highlights={highlights.data ?? []}
        isLoading={highlights.isLoading}
        isError={highlights.isError}
        onRetry={() => highlights.refetch()}
      />
    </section>
  );
}

// ---- HighlightsList ------------------------------------------

function HighlightsList({
  transcriptId: _transcriptId,
  highlights,
  isLoading,
  isError,
  onRetry,
}: {
  transcriptId: string;
  highlights: TranscriptHighlight[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  if (isLoading) {
    return (
      <div
        data-testid="highlights-loading"
        className="space-y-2 animate-pulse"
      >
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded-md bg-muted" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div
        data-testid="highlights-error"
        className="rounded-md border border-destructive/40 bg-destructive/10 p-4 text-center"
      >
        <p className="text-sm text-destructive">Failed to load highlights.</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-2"
          data-testid="highlights-retry"
          onClick={onRetry}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (highlights.length === 0) {
    return (
      <p
        data-testid="highlights-empty"
        className="text-sm text-muted-foreground"
      >
        Click &quot;Mine highlights&quot; to find shareable moments.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-display text-base text-muted-foreground tracking-tight">
        Highlights ({highlights.length})
      </h3>
      <ul
        data-testid="highlights-list"
        className="divide-y divide-border rounded-md border border-border bg-card/50"
      >
        {highlights.map((h) => (
          <HighlightRow key={h.id} highlight={h} />
        ))}
      </ul>
    </div>
  );
}

// ---- HighlightRow --------------------------------------------

function HighlightRow({ highlight: h }: { highlight: TranscriptHighlight }) {
  const tone = highlightStatusTone(h.status);
  const label = highlightStatusLabel(h.status);

  return (
    <li
      data-testid={`highlight-row-${h.id}`}
      className="flex flex-col gap-2 px-4 py-3"
    >
      {/* Top row: status badge + char range + mined-at */}
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone={tone} label={label} />
        <span className="font-mono text-[10px] text-muted-foreground">
          [{h.char_start}, {h.char_end}]
        </span>
        <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60">
          {relativeTime(h.mined_at)}
        </span>
      </div>

      {/* Highlight text */}
      <p
        data-testid={`highlight-text-${h.id}`}
        className="text-sm leading-relaxed"
      >
        {h.text.length > 200 ? `${h.text.slice(0, 200)}…` : h.text}
      </p>

      {/* Composition link (rendered only when produced_composition_id is set) */}
      {h.produced_composition_id && (
        <Link
          to={`/compositions/${h.produced_composition_id}`}
          data-testid={`highlight-composition-link-${h.id}`}
          className="text-xs text-primary underline-offset-4 hover:underline"
        >
          View composition
        </Link>
      )}

      {/* Rejection reason (rendered only when rejected + reason is set) */}
      {h.status === "rejected" && h.rejection_reason && (
        <p className="text-xs text-muted-foreground italic">
          Reason: {h.rejection_reason}
        </p>
      )}
    </li>
  );
}

// ---- StatusBadge helper --------------------------------------

function StatusBadge({
  tone,
  label,
}: {
  tone: "amber" | "success" | "muted" | "danger";
  label: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" &&
          "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- Loading / error / not-found states ----------------------

function BackLink() {
  return (
    <Link
      to="/workspace/transcripts"
      data-testid="back-to-transcripts"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to Transcript Miner
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div
      data-testid="transcript-detail-skeleton"
      className="flex flex-col gap-6 animate-pulse"
    >
      <div className="flex items-start gap-4">
        <div className="h-10 w-64 rounded bg-muted" />
        <div className="h-7 w-24 rounded bg-muted" />
      </div>
      <div className="h-48 w-full rounded-md bg-muted" />
      <div className="h-40 w-full rounded-md bg-muted" />
    </div>
  );
}

function NotFound() {
  return (
    <div
      data-testid="transcript-not-found"
      className="rounded-md border border-dashed border-border p-12 text-center"
    >
      <p className="text-base font-medium">Transcript not found</p>
      <p className="mt-1 text-sm text-muted-foreground">
        This transcript may have been deleted or belongs to a different
        workspace.
      </p>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="mt-4"
        data-testid="not-found-back"
      >
        <Link to="/workspace/transcripts">Back to Transcript Miner</Link>
      </Button>
    </div>
  );
}

function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      data-testid="transcript-detail-error"
      className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
    >
      <p className="text-sm text-destructive">{message}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        data-testid="transcript-detail-retry"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}
