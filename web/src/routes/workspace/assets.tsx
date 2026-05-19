/**
 * /workspace/assets — Asset Library v1 list view.
 *
 * SESSION 189 / A5. Paginated browse over all workspace assets
 * (clips, images, audio, transcripts). Filter by role, asset_type,
 * storage health, and more.
 *
 * Scope: docs/design/ASSET_LIBRARY_V1.md §A5.
 * Out of scope: per-asset detail (A6), asset picker (A7).
 *
 * Q-a-6 deferral: Avatars, voices, and portraits live on the
 * Spokesperson page; they are NOT shown here in v1. The disclosure
 * note in the page header communicates this to the operator.
 */
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  ChevronLeft as PrevIcon,
  Film,
  FileText,
  Music,
  Mic,
  Image as ImageIcon,
  X,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMe } from "@/lib/api/workspaces";
import {
  useWorkspaceAssets,
  assetRoleLabel,
  assetTypeLabel,
  storageHealthLabel,
  storageHealthTone,
  relativeTime,
  ASSET_ROLES,
  ASSET_TYPES,
  STORAGE_HEALTH_VALUES,
  type WorkspaceAsset,
  type AssetType,
  type AssetRole,
  type StorageHealth,
} from "@/lib/api/workspace-assets";
import { cn } from "@/lib/utils";

// ---- Constants ------------------------------------------------

const PAGE_SIZES = [25, 50, 100] as const;

// ---- URL search param helpers ---------------------------------

function toArray(raw: string | null): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function fromArray(arr: string[]): string {
  return arr.join(",");
}

// ---- Page component ------------------------------------------

export function WorkspaceAssetsRoute() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  // Parse filter state from URL search params.
  const roles = toArray(searchParams.get("role"));
  const assetTypes = toArray(searchParams.get("asset_type"));
  const storages = toArray(searchParams.get("storage"));
  const primitiveKinds = toArray(searchParams.get("primitive_kind"));
  const q = searchParams.get("q") ?? "";
  const createdAfter = searchParams.get("created_after") ?? "";
  const createdBefore = searchParams.get("created_before") ?? "";
  const page = Number(searchParams.get("page") ?? "1");
  const pageSize = Number(searchParams.get("page_size") ?? "25");

  // Local state for "more filters" disclosure.
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);

  const assets = useWorkspaceAssets({
    role: roles,
    asset_type: assetTypes,
    storage: storages,
    primitive_kind: primitiveKinds,
    q: q || undefined,
    created_after: createdAfter || undefined,
    created_before: createdBefore || undefined,
    page,
    page_size: pageSize,
    workspace: workspaceId,
  });

  // ---- Param setters ------------------------------------------

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      // Reset to page 1 whenever filters change.
      if (key !== "page") next.delete("page");
      return next;
    });
  }

  function toggleMulti(key: string, current: string[], value: string) {
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    setParam(key, fromArray(next));
  }

  function clearAllFilters() {
    setSearchParams({});
  }

  const hasAnyFilter =
    roles.length > 0 ||
    assetTypes.length > 0 ||
    storages.length > 0 ||
    primitiveKinds.length > 0 ||
    q ||
    createdAfter ||
    createdBefore;

  const totalCount = assets.data?.count ?? 0;
  const results = assets.data?.results ?? [];
  const hasNext = !!assets.data?.next;
  const hasPrev = !!assets.data?.previous;

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Page header ---------------------------------------- */}
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
          data-testid="assets-title"
          className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
        >
          Asset Library
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Every clip, image, audio track, and transcript produced by your
          workspace. Filter by role or type to find what you need.
        </p>
        {/* Q-a-6 deferral notice */}
        <p className="max-w-2xl text-sm text-muted-foreground/70">
          Avatars, voices, and portraits live on the Spokesperson page — not
          shown here in v1.
        </p>
      </header>

      {/* ---- Filter bar ----------------------------------------- */}
      <section
        data-testid="assets-filters"
        className="rounded-md border border-border bg-card p-5 flex flex-col gap-4"
      >
        {/* Primary filter row: role + asset_type + storage */}
        <div className="flex flex-wrap gap-6">
          <FilterGroup
            label="Role"
            options={ASSET_ROLES.map((r) => ({
              value: r,
              label: assetRoleLabel(r as AssetRole),
            }))}
            selected={roles}
            onToggle={(v) => toggleMulti("role", roles, v)}
            testIdPrefix="filter-role"
          />
          <FilterGroup
            label="Type"
            options={ASSET_TYPES.map((t) => ({
              value: t,
              label: assetTypeLabel(t as AssetType),
            }))}
            selected={assetTypes}
            onToggle={(v) => toggleMulti("asset_type", assetTypes, v)}
            testIdPrefix="filter-type"
          />
          <FilterGroup
            label="Storage"
            options={STORAGE_HEALTH_VALUES.map((s) => ({
              value: s,
              label: storageHealthLabel(s as StorageHealth),
            }))}
            selected={storages}
            onToggle={(v) => toggleMulti("storage", storages, v)}
            testIdPrefix="filter-storage"
          />
        </div>

        {/* "More filters" disclosure toggle */}
        <button
          type="button"
          data-testid="more-filters-toggle"
          className="inline-flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => setMoreFiltersOpen((o) => !o)}
          aria-expanded={moreFiltersOpen}
        >
          {moreFiltersOpen ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
          {moreFiltersOpen ? "Fewer filters" : "More filters"}
        </button>

        {/* Expanded filters: q, dates, primitive_kind */}
        {moreFiltersOpen && (
          <div
            data-testid="more-filters-panel"
            className="flex flex-wrap gap-4"
          >
            <div className="flex flex-col gap-1.5 min-w-[220px]">
              <label className="text-xs font-medium text-muted-foreground">
                Search
              </label>
              <Input
                data-testid="filter-q"
                value={q}
                onChange={(e) => setParam("q", e.target.value)}
                placeholder="Title, subject, prompt…"
                className="h-8 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Created after
              </label>
              <Input
                data-testid="filter-created-after"
                type="date"
                value={createdAfter}
                onChange={(e) => setParam("created_after", e.target.value)}
                className="h-8 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Created before
              </label>
              <Input
                data-testid="filter-created-before"
                type="date"
                value={createdBefore}
                onChange={(e) => setParam("created_before", e.target.value)}
                className="h-8 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5 min-w-[220px]">
              <label className="text-xs font-medium text-muted-foreground">
                Primitive kind
              </label>
              <Input
                data-testid="filter-primitive-kind"
                value={primitiveKinds.join(",")}
                onChange={(e) =>
                  setParam("primitive_kind", e.target.value)
                }
                placeholder="e.g. generate_avatar_speech"
                className="h-8 text-sm"
              />
            </div>
          </div>
        )}

        {/* Active filter pills + clear button */}
        {hasAnyFilter && (
          <div className="flex flex-wrap items-center gap-2">
            {[
              ...roles.map((r) => ({
                key: `role:${r}`,
                label: `Role: ${assetRoleLabel(r as AssetRole)}`,
                onRemove: () => toggleMulti("role", roles, r),
              })),
              ...assetTypes.map((t) => ({
                key: `type:${t}`,
                label: `Type: ${assetTypeLabel(t as AssetType)}`,
                onRemove: () => toggleMulti("asset_type", assetTypes, t),
              })),
              ...storages.map((s) => ({
                key: `storage:${s}`,
                label: `Storage: ${storageHealthLabel(s as StorageHealth)}`,
                onRemove: () => toggleMulti("storage", storages, s),
              })),
              ...(q
                ? [
                    {
                      key: "q",
                      label: `Search: ${q}`,
                      onRemove: () => setParam("q", ""),
                    },
                  ]
                : []),
              ...(createdAfter
                ? [
                    {
                      key: "after",
                      label: `After: ${createdAfter}`,
                      onRemove: () => setParam("created_after", ""),
                    },
                  ]
                : []),
              ...(createdBefore
                ? [
                    {
                      key: "before",
                      label: `Before: ${createdBefore}`,
                      onRemove: () => setParam("created_before", ""),
                    },
                  ]
                : []),
              ...primitiveKinds.map((pk) => ({
                key: `pk:${pk}`,
                label: `Primitive: ${pk}`,
                onRemove: () => toggleMulti("primitive_kind", primitiveKinds, pk),
              })),
            ].map(({ key, label, onRemove }) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded-sm border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                {label}
                <button
                  type="button"
                  onClick={onRemove}
                  aria-label={`Remove filter ${label}`}
                  className="hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid="clear-filters"
              onClick={clearAllFilters}
              className="h-6 px-2 text-xs"
            >
              Clear all
            </Button>
          </div>
        )}
      </section>

      {/* ---- List ---------------------------------------------- */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl tracking-tight">
            Assets
            {totalCount > 0 ? (
              <span className="ml-2 text-xl text-muted-foreground font-sans font-normal">
                ({totalCount.toLocaleString()})
              </span>
            ) : null}
          </h2>
          {/* Page size selector */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Show</span>
            {PAGE_SIZES.map((ps) => (
              <button
                key={ps}
                type="button"
                data-testid={`page-size-${ps}`}
                onClick={() => {
                  setSearchParams((prev) => {
                    const next = new URLSearchParams(prev);
                    next.set("page_size", String(ps));
                    next.delete("page");
                    return next;
                  });
                }}
                className={cn(
                  "rounded px-2 py-0.5 text-xs",
                  pageSize === ps
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent",
                )}
              >
                {ps}
              </button>
            ))}
          </div>
        </div>

        {/* Loading skeleton */}
        {assets.isLoading && (
          <ul
            data-testid="assets-skeleton"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {Array.from({ length: 5 }).map((_, i) => (
              <li
                key={i}
                className="flex items-start gap-4 px-5 py-4 animate-pulse"
              >
                <div className="h-14 w-14 shrink-0 rounded bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/5 rounded bg-muted" />
                  <div className="h-3 w-3/5 rounded bg-muted" />
                  <div className="h-3 w-1/4 rounded bg-muted" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Error state */}
        {assets.isError && (
          <div
            data-testid="assets-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load assets: {(assets.error as Error).message}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="assets-retry"
              className="mt-3"
              onClick={() => assets.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!assets.isLoading && !assets.isError && results.length === 0 && (
          <div
            data-testid="assets-empty"
            className="rounded-md border border-dashed border-border p-12 text-center"
          >
            <Film className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-base font-medium">No assets found</p>
            {hasAnyFilter ? (
              <>
                <p className="mt-1 text-sm text-muted-foreground">
                  No assets match these filters. Clear filters to see
                  everything.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="empty-clear-filters"
                  className="mt-4"
                  onClick={clearAllFilters}
                >
                  Clear filters
                </Button>
              </>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                No assets have been generated in this workspace yet. Run a
                recipe to produce your first asset.
              </p>
            )}
          </div>
        )}

        {/* Asset rows */}
        {results.length > 0 && (
          <ul
            data-testid="assets-list"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {results.map((asset) => (
              <AssetRow key={asset.id} asset={asset} />
            ))}
          </ul>
        )}

        {/* Pagination controls */}
        {(hasPrev || hasNext) && (
          <div
            data-testid="pagination-controls"
            className="flex items-center justify-between"
          >
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="pagination-prev"
              disabled={!hasPrev}
              onClick={() => setParam("page", String(Math.max(1, page - 1)))}
            >
              <PrevIcon className="mr-1.5 h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="pagination-next"
              disabled={!hasNext}
              onClick={() => setParam("page", String(page + 1))}
            >
              Next
              <ChevronRight className="ml-1.5 h-4 w-4" />
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}

// ---- AssetRow -------------------------------------------------

function AssetRow({ asset }: { asset: WorkspaceAsset }) {
  const displayTitle =
    asset.title || asset.subject || "Untitled";

  const healthTone = storageHealthTone(asset.storage_health);

  return (
    <li
      data-testid={`asset-row-${asset.id}`}
      className="flex items-start gap-4 px-5 py-4"
    >
      {/* Thumbnail / icon */}
      <AssetThumbnail asset={asset} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Primary line */}
        <p
          className="truncate text-sm font-medium"
          title={displayTitle}
        >
          {displayTitle}
        </p>

        {/* Secondary line: badges */}
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {/* Role badge */}
          <span
            data-testid={`asset-role-badge-${asset.id}`}
            className="inline-flex items-center rounded-sm border border-border bg-muted px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
          >
            {assetRoleLabel(asset.role)}
          </span>

          {/* Storage health badge */}
          <span
            data-testid={`asset-storage-badge-${asset.id}`}
            className={cn(
              "inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
              healthTone === "success" &&
                "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
              healthTone === "warning" &&
                "border-amber-500/40 bg-amber-500/10 text-amber-400",
              healthTone === "danger" &&
                "border-destructive/40 bg-destructive/10 text-destructive",
              healthTone === "neutral" &&
                "border-border bg-muted text-muted-foreground",
            )}
          >
            {storageHealthLabel(asset.storage_health)}
          </span>

          {/* primitive_kind chip */}
          {asset.primitive_kind && (
            <span
              data-testid={`asset-primitive-badge-${asset.id}`}
              className="inline-flex items-center rounded-sm border border-border bg-muted/50 px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {asset.primitive_kind}
            </span>
          )}

          {/* Composition link */}
          {asset.composition && (
            <Link
              to={`/compositions/${asset.composition.id}`}
              data-testid={`asset-composition-link-${asset.id}`}
              className="text-[11px] text-primary underline-offset-4 hover:underline"
            >
              {asset.composition.name}
            </Link>
          )}
        </div>

        {/* Tertiary: prompt preview + relative time */}
        <div className="mt-1 flex items-start gap-3">
          {asset.producing_prompt && (
            <p
              className="line-clamp-1 max-w-md text-xs text-muted-foreground"
              title={asset.producing_prompt}
            >
              {asset.producing_prompt.length > 120
                ? `${asset.producing_prompt.slice(0, 120)}…`
                : asset.producing_prompt}
            </p>
          )}
          <span className="ml-auto shrink-0 text-xs text-muted-foreground/60">
            {relativeTime(asset.created_at)}
          </span>
        </div>
      </div>
    </li>
  );
}

// ---- AssetThumbnail ------------------------------------------

function AssetThumbnail({ asset }: { asset: WorkspaceAsset }) {
  if (asset.asset_type === "image" && asset.file_path) {
    return (
      <img
        src={asset.file_path}
        alt={asset.title || asset.subject || "Asset image"}
        data-testid={`asset-thumb-${asset.id}`}
        className="h-14 w-14 shrink-0 rounded object-cover bg-muted"
        loading="lazy"
        onError={(e) => {
          // On load failure, hide the broken img and show the fallback icon.
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }}
      />
    );
  }

  const iconClass = "h-6 w-6 text-muted-foreground";
  let Icon: React.FC<{ className?: string }>;
  switch (asset.asset_type as AssetType) {
    case "clip":
      Icon = ({ className }) => <Film className={className} />;
      break;
    case "audio":
      Icon = ({ className }) => <Music className={className} />;
      break;
    case "transcript":
      Icon = ({ className }) => <FileText className={className} />;
      break;
    case "voice":
      Icon = ({ className }) => <Mic className={className} />;
      break;
    default:
      Icon = ({ className }) => <ImageIcon className={className} />;
  }

  return (
    <div
      data-testid={`asset-icon-${asset.id}`}
      className="flex h-14 w-14 shrink-0 items-center justify-center rounded border border-border bg-muted"
    >
      <Icon className={iconClass} />
    </div>
  );
}

// ---- FilterGroup ---------------------------------------------

interface FilterGroupOption {
  value: string;
  label: string;
}

function FilterGroup({
  label,
  options,
  selected,
  onToggle,
  testIdPrefix,
}: {
  label: string;
  options: FilterGroupOption[];
  selected: string[];
  onToggle: (value: string) => void;
  testIdPrefix: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              data-testid={`${testIdPrefix}-${opt.value}`}
              onClick={() => onToggle(opt.value)}
              aria-pressed={active}
              className={cn(
                "rounded-sm border px-2.5 py-1 text-xs transition-colors",
                active
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted/50 text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
