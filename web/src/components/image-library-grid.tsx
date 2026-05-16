/**
 * Image library grid — W11.6.4.
 *
 * Workspace image browse + filter surface. Renders the
 * caller's workspace images via ``useImages`` with filter
 * controls (purpose / model / style preset). Clicking a card
 * raises ``onSelect(asset)`` so the parent can mount the
 * detail modal.
 *
 * Filters re-trigger the query — TanStack invalidation is
 * automatic via the queryKey changing. The backend caps the
 * response at 200 newest; until pagination ships (W11.7+) we
 * surface a hint when the cap is hit.
 *
 * Loading + error + empty states have their own renders so
 * each test scenario can be asserted independently.
 */
import { useMemo, useState } from "react";
import { Filter, Image as ImageIcon, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  IMAGE_PURPOSES,
  IMAGE_PURPOSE_LABELS,
  STABILITY_MODELS,
  STABILITY_MODEL_LABELS,
  useImages,
  type ImageAsset,
  type ImagePurpose,
  type StabilityModel,
} from "@/lib/api/images";

interface ImageLibraryGridProps {
  workspace: string;
  onSelect: (asset: ImageAsset) => void;
}

interface Filters {
  purpose?: ImagePurpose;
  model?: StabilityModel;
  stylePreset?: string;
}

const RESULT_CAP = 200;

export function ImageLibraryGrid({ workspace, onSelect }: ImageLibraryGridProps) {
  const [filters, setFilters] = useState<Filters>({});
  const images = useImages({
    workspace,
    purpose: filters.purpose,
    model: filters.model,
    stylePreset: filters.stylePreset,
  });

  const stylePresetOptions = useMemo(
    () => collectStylePresets(images.data ?? []),
    [images.data],
  );

  const hasActiveFilters =
    Boolean(filters.purpose) ||
    Boolean(filters.model) ||
    Boolean(filters.stylePreset);

  return (
    <div className="flex flex-col gap-4" data-testid="image-library-grid">
      <FilterBar
        filters={filters}
        onChange={setFilters}
        stylePresetOptions={stylePresetOptions}
        hasActiveFilters={hasActiveFilters}
      />

      {images.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading images…
        </div>
      )}

      {images.isError && (
        <div
          data-testid="image-library-error"
          className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
        >
          Couldn't load your image library. Try again in a moment.
        </div>
      )}

      {images.data && images.data.length === 0 && (
        <EmptyState hasActiveFilters={hasActiveFilters} />
      )}

      {images.data && images.data.length > 0 && (
        <>
          <div
            data-testid="image-library-cards"
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {images.data.map((asset) => (
              <ImageCard
                key={asset.id}
                asset={asset}
                onClick={() => onSelect(asset)}
              />
            ))}
          </div>
          {images.data.length === RESULT_CAP && (
            <p
              data-testid="image-library-cap"
              className="text-xs text-muted-foreground"
            >
              Showing the {RESULT_CAP} most recent images. Use filters
              to narrow further; full pagination ships in a later slice.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function FilterBar({
  filters,
  onChange,
  stylePresetOptions,
  hasActiveFilters,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  stylePresetOptions: string[];
  hasActiveFilters: boolean;
}) {
  return (
    <div
      data-testid="image-library-filters"
      className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-card p-3"
    >
      <Filter className="h-4 w-4 text-muted-foreground" aria-hidden />
      <div className="flex flex-col gap-1">
        <Label
          htmlFor="filter-purpose"
          className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Purpose
        </Label>
        <select
          id="filter-purpose"
          data-testid="filter-purpose"
          value={filters.purpose ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              purpose: e.target.value
                ? (e.target.value as ImagePurpose)
                : undefined,
            })
          }
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option value="">All purposes</option>
          {IMAGE_PURPOSES.map((p) => (
            <option key={p} value={p}>
              {IMAGE_PURPOSE_LABELS[p]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <Label
          htmlFor="filter-model"
          className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Model
        </Label>
        <select
          id="filter-model"
          data-testid="filter-model"
          value={filters.model ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              model: e.target.value
                ? (e.target.value as StabilityModel)
                : undefined,
            })
          }
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        >
          <option value="">All models</option>
          {STABILITY_MODELS.map((m) => (
            <option key={m} value={m}>
              {STABILITY_MODEL_LABELS[m]}
            </option>
          ))}
        </select>
      </div>
      {stylePresetOptions.length > 0 && (
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="filter-style"
            className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            Style preset
          </Label>
          <select
            id="filter-style"
            data-testid="filter-style"
            value={filters.stylePreset ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                stylePreset: e.target.value || undefined,
              })
            }
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          >
            <option value="">All styles</option>
            {stylePresetOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}
      {hasActiveFilters && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onChange({})}
          data-testid="filter-clear"
        >
          <X className="mr-1 h-3 w-3" />
          Clear filters
        </Button>
      )}
    </div>
  );
}

function ImageCard({
  asset,
  onClick,
}: {
  asset: ImageAsset;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`image-card-${asset.id}`}
      className={cn(
        "flex flex-col gap-2 rounded-md border border-border bg-card p-3 text-left transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "hover:border-foreground/30",
      )}
    >
      <img
        src={asset.file_path}
        alt={asset.subject || asset.prompt.slice(0, 120)}
        className="w-full rounded-sm border border-border"
      />
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
        <span>{asset.purpose}</span>
        <span>
          {asset.model} · {asset.aspect_ratio}
        </span>
      </div>
      {asset.style_preset && (
        <span className="text-xs text-muted-foreground">
          Style: {asset.style_preset}
        </span>
      )}
    </button>
  );
}

function EmptyState({ hasActiveFilters }: { hasActiveFilters: boolean }) {
  return (
    <div
      data-testid="image-library-empty"
      className="flex flex-col items-start gap-2 rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground"
    >
      <ImageIcon className="h-5 w-5" />
      <p>
        {hasActiveFilters
          ? "No images match the active filters. Adjust or clear filters above."
          : "No images in this workspace yet. Switch to the Generate tab to create your first one."}
      </p>
    </div>
  );
}

function collectStylePresets(assets: ImageAsset[]): string[] {
  const presets = new Set<string>();
  for (const asset of assets) {
    if (asset.style_preset) presets.add(asset.style_preset);
  }
  return Array.from(presets).sort();
}
