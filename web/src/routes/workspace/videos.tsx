/**
 * /workspace/videos — Videos library.
 *
 * SESSION 209 / Path A. Paginated browse over every composition
 * (video) the workspace has produced. Click a row → existing
 * /compositions/:id detail page. Filter by spokesperson + status.
 *
 * Out of scope (Path B, queued):
 *   - Soft-delete (archived_at + DELETE endpoint)
 *   - Storage-purge background job
 */
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  MinusCircle,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  COMPOSITION_STATUSES,
  useCompositions,
  type CompositionListItem,
  type CompositionStatus,
} from "@/lib/api/compositions";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useMe } from "@/lib/api/workspaces";

const PAGE_SIZES = [25, 50, 100] as const;

export function WorkspaceVideosRoute() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  const spokesperson = searchParams.get("spokesperson") ?? "";
  const statusFilter =
    (searchParams.get("status") as CompositionStatus | null) ?? "";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const pageSizeRaw = Number(searchParams.get("page_size") ?? "25");
  const pageSize = (PAGE_SIZES as readonly number[]).includes(pageSizeRaw)
    ? pageSizeRaw
    : 25;

  const spokespeople = useSpokespeople();
  const compositions = useCompositions({
    workspace: workspaceId,
    spokesperson: spokesperson || undefined,
    status: (statusFilter || undefined) as CompositionStatus | undefined,
    page,
    page_size: pageSize,
  });

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      if (key !== "page") next.delete("page");
      return next;
    });
  }

  function clearAllFilters() {
    setSearchParams({});
  }

  const totalCount = compositions.data?.count ?? 0;
  const results = compositions.data?.results ?? [];
  const hasNext = !!compositions.data?.next;
  const hasPrev = !!compositions.data?.previous;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const hasAnyFilter = spokesperson || statusFilter;

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Header --------------------------------------------- */}
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <h1
          data-testid="videos-title"
          className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
        >
          Videos
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Every composition rendered in this workspace — talking heads,
          backdrops, polished outputs, layouts. Click any row for the
          full pipeline view.
        </p>
      </header>

      {/* ---- Filter bar ----------------------------------------- */}
      <section
        data-testid="videos-filters"
        className="rounded-md border border-border bg-card p-5 flex flex-wrap items-end gap-6"
      >
        <div className="flex flex-col gap-1.5 min-w-[200px]">
          <label
            htmlFor="filter-spokesperson"
            className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground"
          >
            Spokesperson
          </label>
          <select
            id="filter-spokesperson"
            data-testid="filter-spokesperson"
            value={spokesperson}
            onChange={(e) => setParam("spokesperson", e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All spokespeople</option>
            {(spokespeople.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5 min-w-[180px]">
          <label
            htmlFor="filter-status"
            className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground"
          >
            Status
          </label>
          <select
            id="filter-status"
            data-testid="filter-status"
            value={statusFilter}
            onChange={(e) => setParam("status", e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">Any status</option>
            {COMPOSITION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5 min-w-[160px]">
          <label
            htmlFor="filter-page-size"
            className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground"
          >
            Per page
          </label>
          <select
            id="filter-page-size"
            data-testid="filter-page-size"
            value={pageSize}
            onChange={(e) => setParam("page_size", e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n} per page
              </option>
            ))}
          </select>
        </div>

        {hasAnyFilter && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            data-testid="clear-filters"
            onClick={clearAllFilters}
            className="self-end"
          >
            Clear filters
          </Button>
        )}
      </section>

      {/* ---- Results body --------------------------------------- */}
      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between border-b border-border/60 pb-2">
          <h2 className="font-display text-xl tracking-tight">
            Results{" "}
            <span
              data-testid="results-count"
              className="font-mono text-xs text-muted-foreground"
            >
              {compositions.isLoading ? "…" : totalCount}
            </span>
          </h2>
          {totalPages > 1 && (
            <span className="font-mono text-xs text-muted-foreground">
              Page {page} of {totalPages}
            </span>
          )}
        </div>

        {compositions.isLoading && <ResultsSkeleton />}

        {compositions.error && (
          <p
            data-testid="videos-error"
            className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
          >
            Couldn't load videos: {String(compositions.error)}
          </p>
        )}

        {!compositions.isLoading && !compositions.error && totalCount === 0 && (
          <div
            data-testid="videos-empty"
            className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border bg-card/50 p-12 text-center"
          >
            <p className="font-display text-xl tracking-tight">
              {hasAnyFilter ? "No videos match these filters" : "No videos yet"}
            </p>
            <p className="max-w-md text-sm text-muted-foreground">
              {hasAnyFilter
                ? "Clear the filters above to see all workspace videos."
                : "Fire a composition from any recipe and it'll appear here with status and cost."}
            </p>
            {!hasAnyFilter && (
              <Link to="/recipes">
                <Button size="sm">Open recipe gallery</Button>
              </Link>
            )}
          </div>
        )}

        {results.length > 0 && (
          <ol data-testid="videos-list" className="flex flex-col">
            {results.map((row) => (
              <VideoRow key={row.id} row={row} />
            ))}
          </ol>
        )}
      </section>

      {/* ---- Pagination ----------------------------------------- */}
      {totalCount > 0 && (
        <nav
          data-testid="videos-pagination"
          className="flex items-center justify-between gap-3 pt-2"
        >
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="pagination-prev"
            disabled={!hasPrev || compositions.isFetching}
            onClick={() => setParam("page", String(Math.max(1, page - 1)))}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="font-mono text-xs text-muted-foreground">
            {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalCount)}{" "}
            of {totalCount}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="pagination-next"
            disabled={!hasNext || compositions.isFetching}
            onClick={() => setParam("page", String(page + 1))}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </nav>
      )}
    </div>
  );
}

// ---- Atoms --------------------------------------------------------

function VideoRow({ row }: { row: CompositionListItem }) {
  const cost = row.cost_actual_micros / 1_000_000;
  return (
    <Link
      to={`/compositions/${row.id}`}
      className="flex items-center gap-4 border-b border-border/60 py-3 transition-colors last:border-b-0 hover:bg-muted/40"
      data-testid="video-row"
    >
      <StatusIcon status={row.status} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-medium">{row.name}</span>
          {row.mock_mode && (
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-warning">
              mock
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <span data-testid="row-template">{row.template_kind}</span>
          <span data-testid="row-spokesperson">{row.spokesperson_name}</span>
          <span>{new Date(row.created_at).toLocaleDateString()}</span>
        </div>
      </div>
      <div className="flex flex-col items-end gap-1 text-xs text-muted-foreground">
        <span data-testid="row-status" className="font-mono">
          {row.status}
        </span>
        {row.cost_actual_micros > 0 && (
          <span className="font-mono">${cost.toFixed(4)}</span>
        )}
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: CompositionListItem["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" />;
    case "running":
    case "draft":
    case "planning":
      return (
        <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-accent" />
      );
    case "failed":
      return <XCircle className="h-4 w-4 flex-shrink-0 text-destructive" />;
    case "partial":
      return <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-warning" />;
    default:
      return (
        <MinusCircle className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
      );
  }
}

function ResultsSkeleton() {
  return (
    <div className="flex flex-col">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="grid grid-cols-[2.5rem,1fr,auto] items-baseline gap-4 border-b border-border/60 py-4"
        >
          <div className="h-7 w-8 rounded bg-muted" />
          <div className="flex flex-col gap-2">
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-3 w-1/3 rounded bg-muted/70" />
          </div>
          <div className="h-3 w-12 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
