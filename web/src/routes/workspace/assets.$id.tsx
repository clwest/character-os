/**
 * /workspace/assets/:id — Asset Library v1 per-asset detail view.
 *
 * SESSION 191 / A6. Renders the full detail for a single workspace asset:
 * media preview, metadata table, producing step, and downstream consumers.
 *
 * Scope: docs/design/ASSET_LIBRARY_V1.md §A6.
 * Out of scope: edit/rename/delete actions (v1 is read-only), avatar/voice
 * previews (live on Spokesperson — Q-a-6 deferral).
 *
 * Back-link pattern: plain link to /workspace/assets (no search-param
 * preservation). knowledge.$id.tsx uses the same convention — we match it.
 * Filter state is URL-encoded on the list view, so the browser Back button
 * restores it anyway when operator clicks back.
 */
import { Link, useParams } from "react-router-dom";
import {
  ChevronLeft,
  Copy,
  Check,
  Film,
  FileText,
  Music,
  Mic,
  Image as ImageIcon,
  ExternalLink,
  Layers,
  ArrowRight,
} from "lucide-react";
import { useState, useCallback } from "react";

import { Button } from "@/components/ui/button";
import {
  useWorkspaceAsset,
  assetRoleLabel,
  assetTypeLabel,
  storageHealthLabel,
  storageHealthTone,
  type WorkspaceAssetDetail,
  type AssetType,
  type ProducingStep,
  type DownstreamComposition,
} from "@/lib/api/workspace-assets";
import { cn } from "@/lib/utils";

// ---- Page -------------------------------------------------------

export function WorkspaceAssetDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const asset = useWorkspaceAsset(id);

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
            message={err?.message ?? "Failed to load asset."}
            onRetry={() => asset.refetch()}
          />
        )}
      </div>
    );
  }

  if (!asset.data) return null;

  const data = asset.data;
  const displayTitle = data.title || data.subject || "Untitled asset";

  return (
    <div
      className="flex flex-col gap-10"
      data-testid="asset-detail"
    >
      <BackLink />

      {/* ---- Page header ----------------------------------------- */}
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1
            data-testid="asset-detail-title"
            className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
          >
            {displayTitle}
          </h1>
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            <RolePill role={data.role} />
            <StorageHealthPill health={data.storage_health} />
            <TypeChip type={data.asset_type} />
          </div>
        </div>
        {data.producing_prompt && (
          <p
            data-testid="asset-detail-prompt"
            className="max-w-2xl text-sm text-muted-foreground"
          >
            {data.producing_prompt}
          </p>
        )}
      </header>

      {/* ---- Media preview --------------------------------------- */}
      <MediaPreviewPanel asset={data} />

      {/* ---- Metadata table ------------------------------------- */}
      <MetadataTable asset={data} />

      {/* ---- Lineage -------------------------------------------- */}
      <LineageSection asset={data} />

      {/* ---- Publish bundle CTA (CLIP assets only — Q-d-8) ------- */}
      {data.asset_type === "clip" && (
        <section
          data-testid="publish-bundle-section"
          className="rounded-md border border-border bg-card p-5 flex flex-col gap-3"
        >
          <h2 className="font-display text-lg tracking-tight">
            Publish to social platforms
          </h2>
          <p className="text-sm text-muted-foreground">
            Fan this clip out to Instagram Reels, YouTube Shorts, TikTok, X,
            and LinkedIn — each at the right aspect ratio and duration cap.
            All ffmpeg, $0 incremental cost.
          </p>
          <a
            data-testid="publish-bundle-cta"
            href={`/workspace/bundles/new?source_clip_id=${data.id}`}
            className="inline-flex w-fit items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            Publish bundle
          </a>
        </section>
      )}
    </div>
  );
}

// ---- Back link --------------------------------------------------

function BackLink() {
  return (
    <Link
      to="/workspace/assets"
      data-testid="back-to-assets"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to Asset Library
    </Link>
  );
}

// ---- Media preview panel ----------------------------------------

function MediaPreviewPanel({ asset }: { asset: WorkspaceAssetDetail }) {
  const isExpired = asset.storage_health === "https_expired";
  const isDataUri = asset.storage_health === "data_uri";

  // TRANSCRIPT: render inline_content body.
  if (asset.asset_type === "transcript") {
    return (
      <section
        data-testid="asset-preview-transcript"
        className="rounded-md border border-border bg-card p-5"
      >
        <h2 className="mb-3 font-display text-lg tracking-tight text-muted-foreground">
          Transcript content
        </h2>
        {asset.inline_content ? (
          <pre className="whitespace-pre-wrap text-sm leading-relaxed font-mono max-h-96 overflow-y-auto">
            {asset.inline_content}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">
            No transcript body available.
          </p>
        )}
      </section>
    );
  }

  // VOICE: Runway voice id — no player, hint only.
  if (asset.asset_type === "voice") {
    return (
      <section
        data-testid="asset-preview-voice"
        className="rounded-md border border-border bg-card p-5 flex flex-col gap-2"
      >
        <h2 className="font-display text-lg tracking-tight text-muted-foreground">
          Voice asset
        </h2>
        <p className="text-sm">
          <span className="font-mono text-muted-foreground mr-2">
            Voice id:
          </span>
          <code className="text-foreground">{asset.file_path || "—"}</code>
        </p>
        <p className="text-xs text-muted-foreground">
          Voice previews live on the spokesperson edit modal — not available
          here in v1.
        </p>
      </section>
    );
  }

  // IMAGE
  if (asset.asset_type === "image") {
    if (isExpired) {
      return <ExpiredMediaPanel />;
    }
    if (asset.file_path) {
      return (
        <section
          data-testid="asset-preview-image"
          className="rounded-md border border-border bg-card overflow-hidden"
        >
          <img
            src={asset.file_path}
            alt={asset.title || asset.subject || "Asset image"}
            className={cn(
              "w-full max-h-[520px] object-contain",
              isDataUri ? "bg-transparent" : "bg-muted",
            )}
          />
        </section>
      );
    }
  }

  // CLIP
  if (asset.asset_type === "clip") {
    if (isExpired) {
      return <ExpiredMediaPanel />;
    }
    if (asset.file_path) {
      return (
        <section
          data-testid="asset-preview-clip"
          className="rounded-md border border-border bg-card overflow-hidden"
        >
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            controls
            src={asset.file_path}
            className="w-full max-h-[520px] bg-muted"
          />
        </section>
      );
    }
  }

  // AUDIO
  if (asset.asset_type === "audio") {
    if (isExpired) {
      return <ExpiredMediaPanel />;
    }
    if (asset.file_path) {
      return (
        <section
          data-testid="asset-preview-audio"
          className="rounded-md border border-border bg-card p-5"
        >
          <h2 className="mb-3 font-display text-lg tracking-tight text-muted-foreground">
            Audio
          </h2>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio controls src={asset.file_path} className="w-full" />
        </section>
      );
    }
  }

  // Fallback: no preview available.
  return (
    <section
      data-testid="asset-preview-none"
      className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-muted/30 p-12"
    >
      <AssetTypeIcon type={asset.asset_type} className="h-10 w-10 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">No preview available.</p>
    </section>
  );
}

function ExpiredMediaPanel() {
  return (
    <section
      data-testid="asset-preview-expired"
      className="flex flex-col items-center justify-center gap-3 rounded-md border border-amber-500/30 bg-amber-500/5 p-12"
    >
      <p className="text-sm text-amber-400 font-medium">
        URL expired — this asset is no longer accessible via its stored link.
      </p>
      <p className="text-xs text-muted-foreground">
        Re-run the composition step to regenerate this asset.
      </p>
    </section>
  );
}

// ---- Metadata table ---------------------------------------------

function MetadataTable({ asset }: { asset: WorkspaceAssetDetail }) {
  const rows: { label: string; value: React.ReactNode; testId?: string }[] = [
    {
      label: "ID",
      testId: "meta-id",
      value: (
        <span className="inline-flex items-center gap-2">
          <code className="font-mono text-xs break-all">{asset.id}</code>
          <CopyButton value={asset.id} ariaLabel="Copy asset ID" />
        </span>
      ),
    },
    { label: "Type", value: assetTypeLabel(asset.asset_type) },
    {
      label: "Role",
      value: assetRoleLabel(asset.role),
    },
  ];

  if (asset.file_path && asset.asset_type !== "transcript") {
    rows.push({
      label: "File path",
      value: (
        <span className="inline-flex items-center gap-2 min-w-0">
          <code
            className="font-mono text-xs break-all line-clamp-2"
            title={asset.file_path}
          >
            {asset.file_path}
          </code>
          <CopyButton value={asset.file_path} ariaLabel="Copy file path" />
          {asset.file_path.startsWith("http") && (
            <a
              href={asset.file_path}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open file in new tab"
              className="shrink-0 text-muted-foreground hover:text-foreground"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </span>
      ),
    });
  }

  if (asset.primitive_kind) {
    rows.push({
      label: "Primitive",
      value: (
        <code className="font-mono text-xs">{asset.primitive_kind}</code>
      ),
    });
  }

  if (asset.width != null && asset.height != null) {
    rows.push({
      label: "Dimensions",
      value: `${asset.width} × ${asset.height} px`,
    });
  }

  if (asset.duration_ms != null) {
    rows.push({
      label: "Duration",
      value: formatDuration(asset.duration_ms),
    });
  }

  if (asset.size_bytes != null) {
    rows.push({
      label: "Size",
      value: formatBytes(asset.size_bytes),
    });
  }

  rows.push({
    label: "Cost",
    value: formatCost(asset.cost_micros),
  });

  rows.push({
    label: "Created",
    value: new Date(asset.created_at).toLocaleString(),
  });

  if (asset.composition) {
    rows.push({
      label: "Composition",
      value: (
        <Link
          to={`/compositions/${asset.composition.id}`}
          className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
        >
          {asset.composition.name}
          <ExternalLink className="h-3 w-3" />
        </Link>
      ),
    });
  }

  return (
    <section>
      <h2 className="mb-3 font-display text-2xl tracking-tight">Metadata</h2>
      <dl
        data-testid="asset-metadata"
        className="grid grid-cols-1 gap-x-8 gap-y-2 rounded-md border border-border bg-card p-5 text-sm md:grid-cols-[10rem_1fr]"
      >
        {rows.map((row) => (
          <div key={row.label} className="contents">
            <dt
              data-testid={row.testId}
              className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground"
            >
              {row.label}
            </dt>
            <dd className="break-words min-w-0">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ---- Lineage section --------------------------------------------

function LineageSection({ asset }: { asset: WorkspaceAssetDetail }) {
  return (
    <section className="flex flex-col gap-6">
      <h2 className="font-display text-2xl tracking-tight">Lineage</h2>

      {/* Produced by */}
      <div className="flex flex-col gap-3">
        <h3 className="font-display text-base text-muted-foreground tracking-tight">
          Produced by
        </h3>
        {asset.composition ? (
          <ProducedByPanel
            composition={asset.composition}
            producingStep={asset.producing_step}
          />
        ) : (
          <p
            data-testid="produced-by-none"
            className="text-sm text-muted-foreground"
          >
            No producing composition linked.
          </p>
        )}
      </div>

      {/* Used downstream by */}
      <div className="flex flex-col gap-3">
        <h3 className="font-display text-base text-muted-foreground tracking-tight">
          Used downstream by
        </h3>
        {asset.downstream_compositions.length > 0 ? (
          <DownstreamCompositionsPanel
            items={asset.downstream_compositions}
          />
        ) : (
          <p
            data-testid="downstream-empty"
            className="text-sm text-muted-foreground"
          >
            Not yet used in another composition.
          </p>
        )}
      </div>
    </section>
  );
}

function ProducedByPanel({
  composition,
  producingStep,
}: {
  composition: WorkspaceAssetDetail["composition"];
  producingStep: ProducingStep | null;
}) {
  if (!composition) return null;
  return (
    <div
      data-testid="produced-by-panel"
      className="flex flex-col gap-3"
    >
      {/* Composition card */}
      <Link
        to={`/compositions/${composition.id}`}
        data-testid="producing-composition-link"
        className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-4 py-3 transition-colors hover:border-foreground"
      >
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium">{composition.name}</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            {composition.template_kind} · {composition.status}
          </span>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </Link>

      {/* Step card */}
      {producingStep && (
        <div
          data-testid="producing-step-panel"
          className="rounded-md border border-border bg-card p-5 flex flex-col gap-3"
        >
          <div className="flex items-center gap-3">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <span className="font-display text-base tracking-tight">
              Step {producingStep.position}
            </span>
            <code className="rounded-sm border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">
              {producingStep.primitive}
            </code>
          </div>

          {Object.keys(producingStep.params).length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Params
              </span>
              <pre
                data-testid="producing-step-params"
                className="max-h-48 overflow-auto rounded-sm border border-border bg-muted/50 p-3 font-mono text-xs leading-relaxed"
              >
                {JSON.stringify(producingStep.params, null, 2)}
              </pre>
            </div>
          )}

          {producingStep.inputs.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Inputs
              </span>
              <pre
                data-testid="producing-step-inputs"
                className="max-h-48 overflow-auto rounded-sm border border-border bg-muted/50 p-3 font-mono text-xs leading-relaxed"
              >
                {JSON.stringify(producingStep.inputs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DownstreamCompositionsPanel({
  items,
}: {
  items: DownstreamComposition[];
}) {
  return (
    <ul
      data-testid="downstream-compositions"
      className="flex flex-col gap-1.5"
    >
      {items.map((item) => (
        <li key={item.id}>
          <Link
            to={`/compositions/${item.id}`}
            data-testid={`downstream-comp-${item.id}`}
            className="flex items-center justify-between gap-3 rounded-sm border border-border bg-card px-3 py-2.5 transition-colors hover:border-foreground"
          >
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="truncate text-sm">{item.name}</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {item.template_kind} · {item.status}
              </span>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </Link>
        </li>
      ))}
    </ul>
  );
}

// ---- Badge helpers ----------------------------------------------

function RolePill({ role }: { role: WorkspaceAssetDetail["role"] }) {
  return (
    <span
      data-testid="asset-detail-role"
      className="inline-flex shrink-0 items-center rounded-sm border border-border bg-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
    >
      {assetRoleLabel(role)}
    </span>
  );
}

function StorageHealthPill({
  health,
}: {
  health: WorkspaceAssetDetail["storage_health"];
}) {
  const tone = storageHealthTone(health);
  return (
    <span
      data-testid="asset-detail-health"
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "warning" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
        tone === "neutral" &&
          "border-border bg-muted text-muted-foreground",
      )}
    >
      {storageHealthLabel(health)}
    </span>
  );
}

function TypeChip({ type }: { type: AssetType }) {
  return (
    <span
      data-testid="asset-detail-type"
      className="inline-flex shrink-0 items-center gap-1.5 rounded-sm border border-border bg-muted/50 px-2.5 py-1 text-[11px] text-muted-foreground"
    >
      <AssetTypeIcon type={type} className="h-3 w-3" />
      {assetTypeLabel(type)}
    </span>
  );
}

function AssetTypeIcon({
  type,
  className,
}: {
  type: AssetType;
  className?: string;
}) {
  switch (type) {
    case "clip":
      return <Film className={className} />;
    case "audio":
      return <Music className={className} />;
    case "transcript":
      return <FileText className={className} />;
    case "voice":
      return <Mic className={className} />;
    case "image":
    default:
      return <ImageIcon className={className} />;
  }
}

// ---- Loading / error / not-found states -------------------------

function LoadingSkeleton() {
  return (
    <div
      data-testid="asset-detail-skeleton"
      className="flex flex-col gap-6 animate-pulse"
    >
      {/* Header skeleton */}
      <div className="flex items-start gap-4">
        <div className="h-10 w-64 rounded bg-muted" />
        <div className="h-7 w-24 rounded bg-muted" />
      </div>
      {/* Preview skeleton */}
      <div className="h-48 w-full rounded-md bg-muted" />
      {/* Metadata skeleton */}
      <div className="h-40 w-full rounded-md bg-muted" />
    </div>
  );
}

function NotFound() {
  return (
    <div
      data-testid="asset-not-found"
      className="rounded-md border border-dashed border-border p-12 text-center"
    >
      <p className="text-base font-medium">Asset not found</p>
      <p className="mt-1 text-sm text-muted-foreground">
        This asset may have been deleted or belongs to a different workspace.
      </p>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="mt-4"
        data-testid="not-found-back"
      >
        <Link to="/workspace/assets">Back to Asset Library</Link>
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
      data-testid="asset-detail-error"
      className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
    >
      <p className="text-sm text-destructive">{message}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        data-testid="asset-detail-retry"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}

// ---- CopyButton helper ------------------------------------------

function CopyButton({
  value,
  ariaLabel,
}: {
  value: string;
  ariaLabel: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [value]);

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={handleCopy}
      className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-400" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

// ---- Formatting helpers -----------------------------------------

/** Format duration from milliseconds. */
function formatDuration(ms: number): string {
  const totalSeconds = Math.round(ms / 1_000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
}

/** Format bytes to KB / MB with 1 decimal place. */
function formatBytes(bytes: number): string {
  if (bytes < 1_024) return `${bytes} B`;
  if (bytes < 1_024 * 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / (1_024 * 1_024)).toFixed(1)} MB`;
}

/** Format cost_micros as a dollar string, e.g. "$0.001". */
function formatCost(micros: number): string {
  if (micros === 0) return "$0";
  const dollars = micros / 1_000_000;
  // Show at least 3 decimal places for sub-cent values.
  if (dollars < 0.01) return `$${dollars.toFixed(4)}`;
  if (dollars < 1) return `$${dollars.toFixed(3)}`;
  return `$${dollars.toFixed(2)}`;
}
