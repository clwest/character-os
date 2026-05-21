/**
 * /workspace/bundles/:id — Publish Bundle detail.
 *
 * SESSION B14.4. Shows different affordances based on bundle.status:
 *   DRAFT — metadata panel + forecast + launch button + variant preview.
 *   LAUNCHING / IN_FLIGHT — progress summary + variant progress grid (polling).
 *   COMPLETED / PARTIAL / FAILED — terminal banner + variant grid with retry.
 *
 * Scope: docs/design/PUBLISH_BUNDLE_V1.md §B14.4.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  Trash2,
  X,
  RefreshCw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  useBundle,
  useBundleVariants,
  useBundleForecast,
  useLaunchBundle,
  useRetryVariant,
  useDeleteBundle,
  bundleStatusTone,
  bundleStatusLabel,
  variantStatusTone,
  blockingReasonMessage,
  platformDisplay,
  formatDurationS,
  type PublishBundle,
  type PublishVariant,
  type BundleForecast,
  type BundleStatus,
} from "@/lib/api/bundles";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- Grid-visible statuses ----------------------------------

const GRID_STATUSES = new Set<BundleStatus>([
  "launching",
  "in_flight",
  "completed",
  "partial",
  "failed",
]);

// ---- Page component -----------------------------------------

export function BundleDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const bundle = useBundle(id);

  if (bundle.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <LoadingSkeleton />
      </div>
    );
  }

  if (bundle.isError) {
    const err = bundle.error as { status?: number; message?: string } | null;
    const is404 = err?.status === 404;
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        {is404 ? (
          <NotFound />
        ) : (
          <ErrorPanel
            message={err?.message ?? "Failed to load bundle."}
            onRetry={() => bundle.refetch()}
          />
        )}
      </div>
    );
  }

  if (!bundle.data) return null;

  const b = bundle.data;
  const isDraft = b.status === "draft";
  const showGrid = GRID_STATUSES.has(b.status);
  const isTerminal =
    b.status === "completed" || b.status === "partial" || b.status === "failed";

  return (
    <div
      data-testid="bundle-detail"
      className="flex flex-col gap-8 max-w-3xl"
    >
      <BackLink />
      <BundleMetadataPanel bundle={b} />

      {/* Terminal status banner */}
      {isTerminal && <TerminalBanner bundle={b} />}

      {/* DRAFT: forecast + launch */}
      {isDraft && id && (
        <ForecastPanel bundleId={id} bundle={b} />
      )}

      {/* Active + terminal: variant progress grid */}
      {showGrid && id && (
        <VariantGrid
          bundleId={id}
          bundle={b}
          refetchBundle={() => void bundle.refetch()}
        />
      )}
    </div>
  );
}

// ---- BundleMetadataPanel ------------------------------------

function BundleMetadataPanel({ bundle }: { bundle: PublishBundle }) {
  const navigate = useNavigate();
  const deleteMutation = useDeleteBundle();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const tone = bundleStatusTone(bundle.status);
  const label = bundleStatusLabel(bundle.status);
  const isDraft = bundle.status === "draft";
  const isTerminal =
    bundle.status === "completed" ||
    bundle.status === "partial" ||
    bundle.status === "failed";
  const canDelete = isDraft || isTerminal;

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleteError(null);
    try {
      await deleteMutation.mutateAsync(bundle.id);
      navigate("/workspace/bundles");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? String(
              (err.body as Record<string, unknown> | null)?.detail ??
                err.message,
            )
          : err instanceof Error
            ? err.message
            : "Delete failed.";
      setDeleteError(msg);
      setConfirmDelete(false);
    }
  }

  return (
    <section
      data-testid="bundle-metadata"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-5"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h1
            data-testid="bundle-detail-name"
            className="font-display text-3xl leading-tight tracking-tight text-cream"
          >
            {bundle.name}
          </h1>
          <p className="text-sm text-fog">
            Source clip:{" "}
            <Link
              to={`/workspace/assets/${bundle.source_clip_id}`}
              className="font-mono text-primary hover:underline text-xs"
            >
              {bundle.source_clip_id.slice(0, 8)}…
            </Link>
          </p>
        </div>
        <StatusBadge tone={tone} label={label} />
      </div>

      {/* Variant count summary */}
      <div className="flex flex-wrap gap-3 text-sm text-fog">
        <span>
          <strong className="text-cream">
            {bundle.variant_counts.total}
          </strong>{" "}
          variant{bundle.variant_counts.total !== 1 ? "s" : ""}
        </span>
        {bundle.variant_counts.completed > 0 && (
          <span className="text-emerald-400">
            {bundle.variant_counts.completed} completed
          </span>
        )}
        {bundle.variant_counts.failed > 0 && (
          <span className="text-destructive">
            {bundle.variant_counts.failed} failed
          </span>
        )}
        {bundle.launched_at && (
          <span>Launched {relativeTime(bundle.launched_at)}</span>
        )}
      </div>

      {/* Selected platforms chips */}
      {bundle.selected_platforms.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-fog uppercase tracking-wider">
            Platforms
          </p>
          <div className="flex flex-wrap gap-1.5">
            {bundle.selected_platforms.map((key) => (
              <span
                key={key}
                data-testid={`platform-chip-${key}`}
                className="inline-flex items-center rounded-sm border border-luxe bg-muted px-1.5 py-0.5 text-[11px] text-fog"
              >
                {platformDisplay(key)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Delete bundle — DRAFT or terminal only */}
      {canDelete && (
        <div className="flex flex-col gap-2 pt-2 border-t border-luxe">
          {deleteError && (
            <p
              data-testid="delete-bundle-error"
              className="text-xs text-destructive"
            >
              {deleteError}
            </p>
          )}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              data-testid="delete-bundle-btn"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
              className="h-8 px-3 text-xs gap-1.5"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="h-3 w-3" />
                  {confirmDelete ? "Confirm delete" : "Delete bundle"}
                </>
              )}
            </Button>
            {confirmDelete && !deleteMutation.isPending && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-3 text-xs"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            )}
            {confirmDelete && (
              <p className="text-xs text-fog">
                This will permanently delete the bundle and all variants.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ---- ForecastPanel -------------------------------------------

function ForecastPanel({
  bundleId,
  bundle,
}: {
  bundleId: string;
  bundle: PublishBundle;
}) {
  const forecast = useBundleForecast(bundleId);
  const launch = useLaunchBundle(bundleId);
  const [modalOpen, setModalOpen] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launched, setLaunched] = useState(false);
  const [launchResult, setLaunchResult] = useState<{
    queued_count: number;
    failed_at_start_count: number;
  } | null>(null);

  const f = forecast.data;

  async function handleLaunchConfirm() {
    setLaunchError(null);
    try {
      const result = await launch.mutateAsync();
      setLaunchResult({
        queued_count: result.queued_count,
        failed_at_start_count: result.failed_at_start_count,
      });
      setLaunched(true);
      setModalOpen(false);
    } catch (err) {
      if (
        err instanceof ApiError &&
        (err.status === 409 || err.status === 400)
      ) {
        const body = err.body as Record<string, unknown> | null;
        const msg =
          typeof body?.detail === "string"
            ? body.detail
            : "Launch failed — check the bundle status and try again.";
        setLaunchError(msg);
      } else {
        setLaunchError(
          err instanceof Error ? err.message : "An unexpected error occurred.",
        );
      }
      setModalOpen(false);
    }
  }

  return (
    <section
      data-testid="forecast-panel"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-4"
    >
      <h2 className="font-display text-xl tracking-tight">Launch</h2>

      {/* Cost + time preview */}
      {forecast.isLoading && (
        <div className="flex items-center gap-2 text-sm text-fog">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Calculating…
        </div>
      )}
      {f && (
        <div
          data-testid="forecast-summary"
          className="flex flex-col gap-2 text-sm"
        >
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-fog">
            <span>
              <strong className="text-cream">{f.variant_count}</strong>{" "}
              variant{f.variant_count !== 1 ? "s" : ""}
            </span>
            <span>
              Cost:{" "}
              <strong className="text-emerald-400">$0.00</strong> (ffmpeg only)
            </span>
            <span>
              Est. time:{" "}
              <strong className="text-cream">
                ~{f.estimated_wall_time_s}s
              </strong>
            </span>
            <span
              data-testid="batch-cap-badge"
              className="inline-flex items-center rounded-sm border border-luxe bg-muted px-1.5 py-0.5 text-[10px] font-medium text-fog"
            >
              batch cap: 10
            </span>
          </div>

          {/* Blocking reason */}
          {!f.ready_to_launch && f.blocking_reason && (
            <div
              data-testid="blocking-reason"
              className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
              <p className="text-sm text-amber-300">
                {blockingReasonMessage(f.blocking_reason.code)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Variant preview list (DRAFT: shows what will fire) */}
      {bundle.selected_platforms.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium text-fog uppercase tracking-wider">
            Variant preview
          </p>
          <div className="rounded-md border border-luxe bg-muted/20 divide-y divide-luxe">
            {bundle.selected_platforms.map((key) => {
              const cat = [
                { key: "reels", target_ratio: "720:1280", max_duration_ms: 60000 },
                { key: "shorts", target_ratio: "720:1280", max_duration_ms: 60000 },
                { key: "tiktok", target_ratio: "720:1280", max_duration_ms: 90000 },
                { key: "x_twitter", target_ratio: "1280:720", max_duration_ms: 140000 },
                { key: "linkedin", target_ratio: "1280:720", max_duration_ms: 30000 },
              ].find((p) => p.key === key);
              return (
                <div
                  key={key}
                  data-testid={`variant-preview-row-${key}`}
                  className="px-3 py-2 flex items-center gap-3 text-sm"
                >
                  <span className="font-medium">{platformDisplay(key)}</span>
                  {cat && (
                    <span className="text-xs text-fog font-mono">
                      {cat.target_ratio} · {formatDurationS(cat.max_duration_ms)} max
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Launch error */}
      {launchError && (
        <div
          data-testid="launch-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{launchError}</p>
        </div>
      )}

      {/* Post-launch success notice */}
      {launched && launchResult && (
        <div
          data-testid="launch-success-banner"
          className="flex items-start gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3"
        >
          <p className="text-sm text-emerald-400">
            {launchResult.queued_count} variant
            {launchResult.queued_count !== 1 ? "s" : ""} queued.
            {launchResult.failed_at_start_count > 0 &&
              ` ${launchResult.failed_at_start_count} failed at start — see grid.`}
          </p>
        </div>
      )}

      {/* Launch button */}
      <Button
        type="button"
        data-testid="launch-btn"
        disabled={
          !f?.ready_to_launch ||
          launch.isPending ||
          forecast.isLoading ||
          launched
        }
        onClick={() => setModalOpen(true)}
        className="w-fit"
      >
        {launch.isPending ? (
          <>
            <Loader2
              data-testid="launch-spinner"
              className="mr-2 h-4 w-4 animate-spin"
            />
            Launching…
          </>
        ) : (
          `Launch ${bundle.selected_platforms.length} variant${bundle.selected_platforms.length !== 1 ? "s" : ""}`
        )}
      </Button>

      {/* Launch confirmation modal */}
      {modalOpen && f && (
        <LaunchModal
          bundle={bundle}
          forecast={f}
          isPending={launch.isPending}
          onConfirm={() => void handleLaunchConfirm()}
          onCancel={() => setModalOpen(false)}
        />
      )}
    </section>
  );
}

// ---- LaunchModal — inline, no Radix dep ----------------------

function LaunchModal({
  bundle,
  forecast,
  isPending,
  onConfirm,
  onCancel,
}: {
  bundle: PublishBundle;
  forecast: BundleForecast;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      data-testid="launch-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isPending) onCancel();
      }}
    >
      <div
        data-testid="launch-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="launch-modal-heading"
        className="relative w-full max-w-md rounded-lg border border-luxe bg-card shadow-xl p-6 flex flex-col gap-5"
        onClick={(e) => e.stopPropagation()}
      >
        {!isPending && (
          <button
            type="button"
            aria-label="Close"
            data-testid="launch-modal-close"
            onClick={onCancel}
            className="absolute top-4 right-4 text-fog hover:text-gold"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        <h2
          id="launch-modal-heading"
          data-testid="launch-modal-heading"
          className="font-display text-xl tracking-tight"
        >
          Launch {forecast.variant_count} variant
          {forecast.variant_count !== 1 ? "s" : ""}?
        </h2>

        <div className="flex flex-col gap-2 text-sm text-fog">
          <p>
            Bundle:{" "}
            <strong className="text-cream">{bundle.name}</strong>
          </p>
          <p>
            Platforms:{" "}
            <strong className="text-cream">
              {bundle.selected_platforms.map((k) => platformDisplay(k)).join(", ")}
            </strong>
          </p>
          <p>
            Estimated cost:{" "}
            <strong className="text-emerald-400">$0.00</strong> (all ffmpeg)
          </p>
          <p>
            Estimated wall-time:{" "}
            <strong className="text-cream">
              ~{forecast.estimated_wall_time_s}s
            </strong>
          </p>
          <p className="text-xs text-fog/80 mt-1">
            Each variant reformats the source clip to the platform&apos;s
            aspect ratio and trims to its maximum duration. Platform clips
            are not counted against your monthly video allowance.
          </p>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <Button
            type="button"
            data-testid="launch-modal-confirm"
            disabled={isPending}
            onClick={onConfirm}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Launching…
              </>
            ) : (
              "Yes, launch"
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            data-testid="launch-modal-cancel"
            disabled={isPending}
            onClick={onCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---- TerminalBanner ------------------------------------------

function TerminalBanner({ bundle }: { bundle: PublishBundle }) {
  const { completed, failed, total } = bundle.variant_counts;
  const status = bundle.status;

  const text =
    status === "completed"
      ? `Completed — ${completed} of ${total} rendered successfully.`
      : status === "partial"
        ? `Partial — ${completed} succeeded, ${failed} failed.`
        : `Failed — all ${total} variant${total !== 1 ? "s" : ""} failed to render.`;

  const tone =
    status === "completed"
      ? "success"
      : status === "partial"
        ? "amber"
        : "danger";

  return (
    <div
      data-testid="terminal-banner"
      className={cn(
        "rounded-md border p-4 text-sm font-medium",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <span data-testid="terminal-banner-text">{text}</span>
        <a
          data-testid="browse-assets-link"
          href="/workspace/assets"
          className="text-xs font-normal underline underline-offset-2 opacity-80 hover:opacity-100"
        >
          Browse produced assets
        </a>
      </div>
    </div>
  );
}

// ---- VariantGrid ---------------------------------------------

function VariantGrid({
  bundleId,
  bundle,
  refetchBundle,
}: {
  bundleId: string;
  bundle: PublishBundle;
  refetchBundle: () => void;
}) {
  const variants = useBundleVariants(bundleId);
  const rows = variants.data ?? [];
  const counts = bundle.variant_counts;
  const activeCount = counts.queued + counts.running;
  const isActive =
    bundle.status === "launching" || bundle.status === "in_flight";
  const completedPlusFailed = counts.completed + counts.failed;

  return (
    <section
      data-testid="variant-grid"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-5"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-xl tracking-tight">Variants</h2>

        {/* Progress summary (active only) */}
        {isActive && (
          <div
            data-testid="progress-summary"
            className="flex flex-col gap-2"
          >
            <p className="text-sm text-fog">
              <span className="text-foreground font-medium">
                {completedPlusFailed} of {counts.total}
              </span>{" "}
              done
              {activeCount > 0 && ` · ${activeCount} in progress`}
            </p>
            {counts.total > 0 && (
              <div
                data-testid="progress-bar"
                className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
              >
                <div
                  className="h-full rounded-full bg-amber-400 transition-all"
                  style={{
                    width: `${Math.round((completedPlusFailed / counts.total) * 100)}%`,
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {variants.isLoading && (
        <div className="flex items-center gap-2 text-sm text-fog">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading variants…
        </div>
      )}

      {rows.length > 0 && (
        <div className="flex flex-col divide-y divide-luxe">
          {rows.map((v) => (
            <VariantRow
              key={v.id}
              variant={v}
              bundleId={bundleId}
              bundle={bundle}
              refetchBundle={refetchBundle}
            />
          ))}
        </div>
      )}

      {!variants.isLoading && rows.length === 0 && (
        <p className="text-sm text-fog">No variants found.</p>
      )}
    </section>
  );
}

// ---- VariantRow ---------------------------------------------

function VariantRow({
  variant,
  bundleId,
  bundle,
  refetchBundle,
}: {
  variant: PublishVariant;
  bundleId: string;
  bundle: PublishBundle;
  refetchBundle: () => void;
}) {
  const [confirmRetry, setConfirmRetry] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const retry = useRetryVariant(bundleId);

  const tone = variantStatusTone(variant.status);
  const isTerminal =
    bundle.status === "completed" ||
    bundle.status === "partial" ||
    bundle.status === "failed";
  const canRetry = isTerminal && variant.status === "failed";

  async function handleRetry() {
    if (!confirmRetry) {
      setConfirmRetry(true);
      return;
    }
    setRetryError(null);
    try {
      await retry.mutateAsync(variant.id);
      setConfirmRetry(false);
      refetchBundle();
    } catch (err) {
      setRetryError(
        err instanceof Error ? err.message : "Retry failed.",
      );
      setConfirmRetry(false);
    }
  }

  return (
    <div
      data-testid={`variant-row-${variant.id}`}
      className="py-4 flex flex-col gap-2"
    >
      <div className="flex items-center gap-3 flex-wrap">
        {/* Status badge */}
        <VariantStatusBadge tone={tone} status={variant.status} />

        {/* Platform display */}
        <span
          data-testid={`variant-platform-${variant.id}`}
          className="font-medium text-sm"
        >
          {platformDisplay(variant.platform_key)}
        </span>

        {/* Ratio + duration */}
        <span
          data-testid={`variant-specs-${variant.id}`}
          className="text-xs text-fog font-mono"
        >
          {variant.target_ratio} · {formatDurationS(variant.max_duration_ms)} max
        </span>

        {/* Composition link for completed variants */}
        {variant.produced_composition_id && variant.status === "completed" && (
          <a
            data-testid={`variant-composition-link-${variant.id}`}
            href={`/compositions/${variant.produced_composition_id}`}
            className="ml-auto text-xs text-primary hover:underline whitespace-nowrap"
          >
            View composition →
          </a>
        )}
      </div>

      {/* Error message */}
      {variant.status === "failed" && variant.error_message && (
        <p
          data-testid={`variant-error-${variant.id}`}
          className="text-xs text-destructive pl-1"
        >
          {variant.error_message}
        </p>
      )}

      {/* Retry affordance (terminal bundles only, failed variants) */}
      {canRetry && (
        <div className="flex items-center gap-3 pl-1">
          {retryError && (
            <p
              data-testid={`variant-retry-error-${variant.id}`}
              className="text-xs text-destructive"
            >
              {retryError}
            </p>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid={`retry-btn-${variant.id}`}
            disabled={retry.isPending}
            onClick={() => void handleRetry()}
            className="h-7 px-2.5 text-xs gap-1.5"
          >
            {retry.isPending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Retrying…
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3" />
                {confirmRetry ? "Confirm retry" : "Retry"}
              </>
            )}
          </Button>
          {confirmRetry && !retry.isPending && (
            <>
              <p className="text-xs text-fog">
                A new variant render will fire for this platform.
              </p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2.5 text-xs"
                onClick={() => setConfirmRetry(false)}
              >
                Cancel
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ---- VariantStatusBadge -------------------------------------

function VariantStatusBadge({
  tone,
  status,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  status: string;
}) {
  return (
    <span
      data-testid={`variant-status-badge-${status}`}
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-luxe bg-muted text-fog",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {status}
    </span>
  );
}

// ---- StatusBadge (bundle-level) -----------------------------

function StatusBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  label: string;
}) {
  return (
    <span
      data-testid="bundle-status-badge"
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-luxe bg-muted text-fog",
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
      to="/workspace/bundles"
      data-testid="back-to-bundles"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to Bundles
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div
      data-testid="bundle-detail-skeleton"
      className="flex flex-col gap-6 animate-pulse"
    >
      <div className="h-10 w-64 rounded bg-muted" />
      <div className="h-48 w-full rounded-md bg-muted" />
      <div className="h-40 w-full rounded-md bg-muted" />
    </div>
  );
}

function NotFound() {
  return (
    <div
      data-testid="bundle-not-found"
      className="rounded-md border border-dashed border-luxe bg-card/40 p-12 text-center"
    >
      <p className="text-base font-medium">Bundle not found</p>
      <p className="mt-1 text-sm text-fog">
        This bundle may have been deleted or belongs to a different workspace.
      </p>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="mt-4"
        data-testid="not-found-back"
      >
        <Link to="/workspace/bundles">Back to Bundles</Link>
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
      data-testid="bundle-detail-error"
      className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
    >
      <p className="text-sm text-destructive">{message}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        data-testid="bundle-detail-retry"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
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
