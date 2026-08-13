/**
 * /workspace/transcripts — Transcript Miner v1 list view.
 *
 * SESSION 202 / B1.5. Lists all transcript assets in the workspace.
 * Each row is clickable → /workspace/transcripts/:id for mining.
 *
 * Q-b-6 resolution: standalone route (not an extension of /workspace/assets).
 * The miner workflow is transcript-centric; the asset list is workspace-wide.
 *
 * Scope: docs/design/TRANSCRIPT_MINER_V1.md §B1.5.
 */
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, FileText, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMe } from "@/lib/api/workspaces";
import { useTranscripts, useHighlightsForTranscript } from "@/lib/api/transcripts";
import { relativeTime, type WorkspaceAsset } from "@/lib/api/workspace-assets";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/editorial";

// ---- Page component ------------------------------------------

export function WorkspaceTranscriptsRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  const transcripts = useTranscripts({ workspace: workspaceId });

  const results = transcripts.data?.results ?? [];

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Page header ---------------------------------------- */}
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <SectionHeader number={8} title="Transcripts" />
        <div className="flex items-center gap-3">
          <Sparkles className="h-7 w-7 text-gold/60" />
          <h1
            data-testid="transcripts-title"
            className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
          >
            Transcript <span className="italic gold-text">miner.</span>
          </h1>
        </div>
        <p className="max-w-2xl text-base text-mist">
          Every live session produces a transcript. Pick one, mine it for
          shareable highlights, then approve the clips you want rendered.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      {/* ---- List ---------------------------------------------- */}
      <section className="flex flex-col gap-4">
        <h2 className="font-display text-2xl tracking-tight">
          Transcripts
          {results.length > 0 ? (
            <span className="ml-2 text-xl text-fog/70 font-sans font-normal">
              ({results.length})
            </span>
          ) : null}
        </h2>

        {/* Loading skeleton */}
        {transcripts.isLoading && (
          <ul
            data-testid="transcripts-skeleton"
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
          >
            {Array.from({ length: 4 }).map((_, i) => (
              <li
                key={i}
                className="flex items-start gap-4 px-5 py-4 animate-pulse"
              >
                <div className="h-10 w-10 shrink-0 rounded bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/5 rounded bg-muted" />
                  <div className="h-3 w-3/5 rounded bg-muted" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Error state */}
        {transcripts.isError && (
          <div
            data-testid="transcripts-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load transcripts:{" "}
              {(transcripts.error as Error).message}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="transcripts-retry"
              className="mt-3"
              onClick={() => transcripts.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!transcripts.isLoading && !transcripts.isError && results.length === 0 && (
          <div
            data-testid="transcripts-empty"
            className="rounded-md border border-dashed border-luxe bg-card/40 p-12 text-center"
          >
            <FileText className="mx-auto h-10 w-10 text-fog" />
            <p className="mt-4 font-display text-xl tracking-tight text-cream">No transcripts yet</p>
            <p className="mt-1 text-sm text-mist max-w-md mx-auto">
              Transcripts are created automatically at the end of a live
              realtime session.{" "}
              <Link
                to="/spokespeople"
                className="text-primary underline-offset-4 hover:underline"
              >
                Start a live session
              </Link>{" "}
              to produce your first transcript.
            </p>
          </div>
        )}

        {/* Transcript rows */}
        {results.length > 0 && (
          <ul
            data-testid="transcripts-list"
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
          >
            {results.map((transcript) => (
              <TranscriptRow key={transcript.id} transcript={transcript} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---- TranscriptRow -------------------------------------------

function TranscriptRow({ transcript }: { transcript: WorkspaceAsset }) {
  const highlights = useHighlightsForTranscript(transcript.id);
  const highlightCount = highlights.data?.length ?? 0;

  // Title: use asset title if present, otherwise fall back to mined_at date.
  const displayTitle =
    transcript.title ||
    `Untitled transcript · ${relativeTime(transcript.created_at)}`;

  // Content preview: subject field holds a short summary when set.
  const preview = transcript.subject || null;

  // Char count comes from size_bytes for inline content (backend stores char
  // count there for TRANSCRIPT assets — no separate field in the list
  // serializer). Fall back gracefully.
  const charCount = transcript.size_bytes ?? null;

  return (
    <li
      data-testid={`transcript-row-${transcript.id}`}
      className="hover:bg-gold/5 transition-colors"
    >
      <Link
        to={`/workspace/transcripts/${transcript.id}`}
        data-testid={`transcript-link-${transcript.id}`}
        className="flex items-start gap-4 px-5 py-4"
      >
        {/* Icon */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-luxe bg-muted">
          <FileText className="h-5 w-5 text-fog" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <p
            data-testid={`transcript-title-${transcript.id}`}
            className="truncate text-sm font-medium"
            title={displayTitle}
          >
            {displayTitle}
          </p>

          {/* Preview */}
          {preview && (
            <p className="mt-0.5 line-clamp-2 text-xs text-fog max-w-xl">
              {preview.length > 120 ? `${preview.slice(0, 120)}…` : preview}
            </p>
          )}

          {/* Meta row: char count + highlight badge + time */}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {charCount != null && charCount > 0 && (
              <span className="inline-flex items-center rounded-sm border border-luxe bg-muted px-1.5 py-0.5 font-mono text-[10px] text-fog">
                {charCount.toLocaleString()} chars
              </span>
            )}

            {/* Highlight count badge — eager from the pre-fetched list */}
            <HighlightCountBadge count={highlightCount} isLoading={highlights.isLoading} />

            <span className="ml-auto shrink-0 text-xs text-fog/60">
              {relativeTime(transcript.created_at)}
            </span>
          </div>
        </div>
      </Link>
    </li>
  );
}

// ---- HighlightCountBadge ------------------------------------

function HighlightCountBadge({
  count,
  isLoading,
}: {
  count: number;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <span className="inline-block h-4 w-10 animate-pulse rounded bg-muted" />
    );
  }

  if (count === 0) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] font-medium",
          "border-luxe bg-muted/50 text-fog",
        )}
      >
        <Sparkles className="h-2.5 w-2.5" />
        Not mined
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] font-medium",
        "border-amber-500/40 bg-amber-500/10 text-amber-400",
      )}
    >
      <Sparkles className="h-2.5 w-2.5" />
      {count} {count === 1 ? "highlight" : "highlights"}
    </span>
  );
}
