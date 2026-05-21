/**
 * /workspace/bundles/new — Create a new publish bundle.
 *
 * SESSION B14.4. Three-field form:
 *   1. Source CLIP picker (searchable asset list)
 *   2. Name (max 120 chars)
 *   3. Platform checkboxes (from PLATFORM_CATALOG)
 *
 * Prefills source clip when ?source_clip_id=<id> is present in the URL
 * (Q-d-8: the Asset-detail "Publish bundle" CTA links here with the clip
 * pre-selected).
 *
 * On success → navigate to /workspace/bundles/<id>.
 *
 * Scope: docs/design/PUBLISH_BUNDLE_V1.md §B14.4.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, Loader2, AlertCircle, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkspaceAssets } from "@/lib/api/workspace-assets";
import {
  useCreateBundle,
  PLATFORM_CATALOG,
  formatDurationS,
} from "@/lib/api/bundles";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- Page component -----------------------------------------

export function BundleNewRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ---- CLIP asset list for the picker
  const clips = useWorkspaceAssets({ asset_type: ["clip"] });
  const clipList = clips.data?.results ?? [];

  const create = useCreateBundle();

  // ---- Form state
  const [selectedClipId, setSelectedClipId] = useState<string>("");
  const [name, setName] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(
    new Set(),
  );
  const [clipSearch, setClipSearch] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Prefill from ?source_clip_id= query param (Q-d-8).
  useEffect(() => {
    const prefill = searchParams.get("source_clip_id");
    if (prefill && !selectedClipId) {
      setSelectedClipId(prefill);
    }
  }, [searchParams, selectedClipId]);

  // ---- Validation
  const clipError =
    selectedClipId.trim() === "" ? "Source clip is required." : null;
  const nameError = name.trim().length === 0 ? "Name is required." : null;
  const platformError =
    selectedPlatforms.size === 0 ? "Select at least one platform." : null;

  function togglePlatform(key: string) {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  // Filtered clip list for the searchable picker.
  const filteredClips = clipSearch.trim()
    ? clipList.filter((c) => {
        const q = clipSearch.toLowerCase();
        return (
          (c.title || "").toLowerCase().includes(q) ||
          (c.subject || "").toLowerCase().includes(q)
        );
      })
    : clipList;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setShowErrors(true);
    if (clipError || nameError || platformError) return;

    setSubmitError(null);
    try {
      const bundle = await create.mutateAsync({
        source_clip_id: selectedClipId,
        name: name.trim(),
        selected_platforms: [...selectedPlatforms],
      });
      navigate(`/workspace/bundles/${bundle.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        const body = err.body as Record<string, unknown> | null;
        const detailMsg = body?.detail != null ? String(body.detail) : null;
        const platformMsg =
          body?.selected_platforms != null
            ? String(
                Array.isArray(body.selected_platforms)
                  ? body.selected_platforms[0]
                  : body.selected_platforms,
              )
            : null;
        setSubmitError(
          platformMsg ??
            detailMsg ??
            "Submission failed — check your inputs.",
        );
      } else {
        setSubmitError(
          err instanceof Error ? err.message : "An unexpected error occurred.",
        );
      }
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      {/* ---- Back link ----------------------------------------- */}
      <Link
        to="/workspace/bundles"
        data-testid="back-to-bundles"
        className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Bundles
      </Link>

      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-2">
        <h1
          data-testid="bundle-new-title"
          className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
        >
          New bundle
        </h1>
        <p className="text-base text-mist">
          Pick a source clip, give the bundle a name, and select which
          platforms to reformat it for. Each platform generates one
          variant at the right aspect ratio and duration cap — all ffmpeg,
          $0 cost.
        </p>
      </header>

      {/* ---- Form ---------------------------------------------- */}
      <form
        data-testid="bundle-create-form"
        onSubmit={(e) => void handleSubmit(e)}
        className="flex flex-col gap-6 rounded-md border border-luxe bg-card p-6"
        noValidate
      >
        {/* Source clip picker */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">
            Source clip <span className="text-destructive">*</span>
          </label>
          <p className="text-xs text-fog">
            The CLIP asset to reformat for each platform.
          </p>

          {clips.isLoading ? (
            <div
              data-testid="clip-picker-loading"
              className="h-9 rounded-md bg-muted animate-pulse"
            />
          ) : clipList.length === 0 ? (
            <div className="rounded-md border border-dashed border-luxe p-4 text-sm text-fog">
              No CLIP assets in this workspace. Render a video first, then
              publish it here.
            </div>
          ) : (
            <>
              {/* Search */}
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-fog" />
                <Input
                  data-testid="clip-search-input"
                  type="text"
                  value={clipSearch}
                  onChange={(e) => setClipSearch(e.target.value)}
                  placeholder="Search clips…"
                  className="pl-8 h-8 text-xs"
                  disabled={create.isPending}
                />
              </div>

              {/* Clip list */}
              <div
                data-testid="clip-picker-list"
                className={cn(
                  "max-h-52 overflow-y-auto rounded-md border border-input bg-background",
                  showErrors && clipError && "border-destructive",
                )}
              >
                {filteredClips.length === 0 ? (
                  <p className="px-3 py-2 text-xs text-fog">
                    No clips match your search.
                  </p>
                ) : (
                  filteredClips.map((clip) => {
                    const isSelected = selectedClipId === clip.id;
                    const title = clip.title || clip.subject || "Untitled clip";
                    const durationLabel =
                      clip.duration_ms != null
                        ? ` · ${formatDurationS(clip.duration_ms)}`
                        : "";
                    return (
                      <button
                        key={clip.id}
                        type="button"
                        data-testid={`clip-option-${clip.id}`}
                        onClick={() => setSelectedClipId(clip.id)}
                        disabled={create.isPending}
                        className={cn(
                          "w-full px-3 py-2 text-left text-sm flex flex-col gap-0.5 transition-colors",
                          isSelected
                            ? "bg-primary/10 text-primary"
                            : "hover:bg-gold/10 text-cream",
                        )}
                      >
                        <span className="font-medium truncate">{title}</span>
                        <span className="text-[11px] text-fog font-mono">
                          {clip.id.slice(0, 8)}…{durationLabel}
                        </span>
                      </button>
                    );
                  })
                )}
              </div>
            </>
          )}

          {showErrors && clipError && (
            <p
              data-testid="bundle-clip-error"
              className="text-xs text-destructive"
            >
              {clipError}
            </p>
          )}

          {/* Show selected clip name for confirmation */}
          {selectedClipId && (
            <p
              data-testid="selected-clip-display"
              className="text-xs text-fog"
            >
              Selected:{" "}
              <span className="font-mono">
                {(() => {
                  const found = clipList.find((c) => c.id === selectedClipId);
                  return found
                    ? found.title || found.subject || selectedClipId.slice(0, 8) + "…"
                    : selectedClipId.slice(0, 8) + "…";
                })()}
              </span>
            </p>
          )}
        </div>

        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="bundle-name"
            className="text-sm font-medium"
          >
            Bundle name <span className="text-destructive">*</span>
          </label>
          <Input
            id="bundle-name"
            data-testid="bundle-name-input"
            type="text"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Q3 product launch"
            disabled={create.isPending}
            className={cn(
              showErrors && nameError && "border-destructive ring-destructive",
            )}
          />
          {showErrors && nameError && (
            <p
              data-testid="bundle-name-error"
              className="text-xs text-destructive"
            >
              {nameError}
            </p>
          )}
          <p className="text-[11px] text-fog">
            {name.length} / 120 — variants will be named "{name || "…"} —{" "}
            Platform"
          </p>
        </div>

        {/* Platform checkboxes */}
        <div className="flex flex-col gap-1.5">
          <fieldset>
            <legend className="text-sm font-medium mb-2">
              Platforms <span className="text-destructive">*</span>
            </legend>
            <p className="text-xs text-fog mb-3">
              Each selected platform creates one variant at the right ratio
              and duration cap.
            </p>
            <div className="flex flex-col gap-2">
              {PLATFORM_CATALOG.map((platform) => {
                const checked = selectedPlatforms.has(platform.key);
                return (
                  <label
                    key={platform.key}
                    data-testid={`platform-checkbox-label-${platform.key}`}
                    className={cn(
                      "flex items-center gap-3 rounded-md border p-3 cursor-pointer transition-colors",
                      checked
                        ? "border-primary/40 bg-primary/5"
                        : "border-luxe hover:bg-muted/30",
                      create.isPending && "cursor-not-allowed opacity-50",
                    )}
                  >
                    <input
                      type="checkbox"
                      data-testid={`platform-checkbox-${platform.key}`}
                      checked={checked}
                      onChange={() => togglePlatform(platform.key)}
                      disabled={create.isPending}
                      className="h-4 w-4 rounded border-input accent-primary"
                    />
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium">
                        {platform.display}
                      </span>
                      <span className="text-[11px] text-fog font-mono">
                        {platform.target_ratio} ·{" "}
                        {formatDurationS(platform.max_duration_ms)} max
                      </span>
                    </div>
                  </label>
                );
              })}
            </div>
          </fieldset>
          {showErrors && platformError && (
            <p
              data-testid="bundle-platform-error"
              className="text-xs text-destructive"
            >
              {platformError}
            </p>
          )}
          {selectedPlatforms.size > 0 && (
            <p className="text-[11px] text-fog">
              {selectedPlatforms.size} platform
              {selectedPlatforms.size !== 1 ? "s" : ""} selected ·{" "}
              {selectedPlatforms.size} variant
              {selectedPlatforms.size !== 1 ? "s" : ""} will be created at
              launch · $0 cost
            </p>
          )}
        </div>

        {/* Submission error */}
        {submitError && (
          <div
            data-testid="bundle-submit-error"
            className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
            <p className="text-sm text-destructive">{submitError}</p>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center gap-3 pt-2">
          <Button
            type="submit"
            data-testid="bundle-create-submit"
            disabled={create.isPending}
          >
            {create.isPending ? (
              <>
                <Loader2
                  data-testid="bundle-create-spinner"
                  className="mr-2 h-4 w-4 animate-spin"
                />
                Creating…
              </>
            ) : (
              "Create bundle"
            )}
          </Button>
          <Button
            asChild
            type="button"
            variant="ghost"
            disabled={create.isPending}
          >
            <Link to="/workspace/bundles">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
