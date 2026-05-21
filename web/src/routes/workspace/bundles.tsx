/**
 * /workspace/bundles — Publish Bundle list view.
 *
 * SESSION B14.4. Lists all publish bundles in the workspace.
 * Each row: name, status badge, source_clip_id hint, variant total, created_at.
 * Status filter chips at the top. "New bundle" primary CTA top-right.
 *
 * Scope: docs/design/PUBLISH_BUNDLE_V1.md §B14.4.
 */
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, Share2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMe } from "@/lib/api/workspaces";
import {
  useBundles,
  bundleStatusTone,
  bundleStatusLabel,
  type BundleStatus,
  type PublishBundle,
  BUNDLE_STATUSES,
} from "@/lib/api/bundles";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/editorial";

// ---- Status filter chips labels ------------------------------

const FILTER_OPTIONS: Array<{ value: BundleStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "in_flight", label: "In Flight" },
  { value: "completed", label: "Completed" },
  { value: "partial", label: "Partial" },
  { value: "failed", label: "Failed" },
];

// ---- Page component -----------------------------------------

export function WorkspaceBundlesRoute() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  const rawStatus = searchParams.get("status") ?? "all";
  const activeStatus: BundleStatus | undefined =
    rawStatus !== "all" && (BUNDLE_STATUSES as readonly string[]).includes(rawStatus)
      ? (rawStatus as BundleStatus)
      : undefined;

  const bundles = useBundles(workspaceId, { status: activeStatus });
  const results = bundles.data ?? [];

  function handleFilterClick(value: BundleStatus | "all") {
    if (value === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ status: value });
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Page header --------------------------------------- */}
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <SectionHeader number={5} title="Bundles" />
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Share2 className="h-7 w-7 text-fog" />
            <h1
              data-testid="bundles-title"
              className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
            >
              Publish <span className="italic gold-text">bundles.</span>
            </h1>
          </div>
          <Button
            asChild
            data-testid="new-bundle-btn"
          >
            <Link to="/workspace/bundles/new">
              <Plus className="mr-2 h-4 w-4" />
              New bundle →
            </Link>
          </Button>
        </div>
        <p className="max-w-2xl text-base text-mist">
          Publish bundles fan a source clip out to 5+ social platforms in one
          click. All ffmpeg — $0 incremental cost.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      {/* ---- Status filter chips ------------------------------- */}
      <div
        data-testid="status-filter-chips"
        className="flex flex-wrap gap-2"
      >
        {FILTER_OPTIONS.map((opt) => {
          const isActive = opt.value === (activeStatus ?? "all");
          return (
            <button
              key={opt.value}
              type="button"
              data-testid={`filter-chip-${opt.value}`}
              onClick={() => handleFilterClick(opt.value)}
              className={cn(
                "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                isActive
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-luxe bg-muted/40 text-fog hover:bg-gold/10 hover:text-cream",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* ---- List ---------------------------------------------- */}
      <section className="flex flex-col gap-4">
        <h2 className="font-display text-2xl tracking-tight text-cream">
          {activeStatus ? bundleStatusLabel(activeStatus) : "All"} bundles
          {results.length > 0 && (
            <span className="ml-2 text-xl text-fog/70 font-sans font-normal">
              ({results.length})
            </span>
          )}
        </h2>

        {/* Loading skeleton */}
        {bundles.isLoading && (
          <ul
            data-testid="bundles-skeleton"
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
          >
            {Array.from({ length: 4 }).map((_, i) => (
              <li
                key={i}
                className="flex items-start gap-4 px-5 py-4 animate-pulse"
              >
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/5 rounded bg-muted" />
                  <div className="h-3 w-3/5 rounded bg-muted" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Error state */}
        {bundles.isError && (
          <div
            data-testid="bundles-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load bundles:{" "}
              {(bundles.error as Error).message}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="bundles-retry"
              className="mt-3"
              onClick={() => bundles.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!bundles.isLoading && !bundles.isError && results.length === 0 && (
          <div
            data-testid="bundles-empty"
            className="rounded-md border border-dashed border-luxe bg-card/40 p-12 text-center"
          >
            <Share2 className="mx-auto h-10 w-10 text-fog" />
            <p className="mt-4 font-display text-xl tracking-tight text-cream">No publish bundles yet</p>
            <p className="mt-1 text-sm text-mist max-w-md mx-auto">
              Publish bundles fan a source clip out to 5+ social platforms in
              one click. All ffmpeg — $0 incremental cost.
            </p>
            <Button
              asChild
              size="sm"
              className="mt-4"
              data-testid="bundles-empty-cta"
            >
              <Link to="/workspace/bundles/new">Create your first bundle</Link>
            </Button>
          </div>
        )}

        {/* Bundle rows */}
        {results.length > 0 && (
          <ul
            data-testid="bundles-list"
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
          >
            {results.map((bundle) => (
              <BundleRow key={bundle.id} bundle={bundle} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---- BundleRow ----------------------------------------------

function BundleRow({ bundle }: { bundle: PublishBundle }) {
  const tone = bundleStatusTone(bundle.status);
  const label = bundleStatusLabel(bundle.status);
  const total = bundle.variant_counts.total;

  return (
    <li
      data-testid={`bundle-row-${bundle.id}`}
      className="hover:bg-gold/5 transition-colors"
    >
      <Link
        to={`/workspace/bundles/${bundle.id}`}
        data-testid={`bundle-link-${bundle.id}`}
        className="flex items-center gap-4 px-5 py-4"
      >
        {/* Name + source clip hint */}
        <div className="flex-1 min-w-0">
          <p
            data-testid={`bundle-name-${bundle.id}`}
            className="truncate text-sm font-medium"
            title={bundle.name}
          >
            {bundle.name}
          </p>
          <p className="mt-0.5 text-xs text-fog font-mono">
            clip: {bundle.source_clip_id.slice(0, 8)}…
          </p>
        </div>

        {/* Meta row: status badge + variant count + date */}
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge tone={tone} label={label} />
          <span className="text-xs text-fog">
            {total === 1 ? "1 variant" : `${total} variants`}
          </span>
          <span className="text-xs text-fog/60">
            {relativeTime(bundle.created_at)}
          </span>
        </div>
      </Link>
    </li>
  );
}

// ---- StatusBadge helper --------------------------------------

export function StatusBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
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
          "border-luxe bg-muted text-fog",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- relativeTime helper ------------------------------------

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
