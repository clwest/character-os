/**
 * Image generation form — W11.6.3.
 *
 * Hosts the model + aspect-ratio + purpose + style-preset
 * selectors with hover-text per Contract rule 9, plus the
 * subject textarea + optional advanced negative-prompt
 * override. Fires ``useGenerateImage`` and surfaces the
 * result inline.
 *
 * Defaults per scope-lock §"Operator journeys":
 *   - model: sd3-large (recommended default for final use)
 *   - aspect_ratio: 16:9 (web/banner)
 *   - purpose: scene (most generic)
 *
 * Contract rule 2 — ``avatar`` purpose is omitted from the
 * SPA picker; operators who want avatar bake go through the
 * spokesperson wizard.
 */
import { useState, type FormEvent } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { StylePresetPicker } from "@/components/style-preset-picker";
import {
  IMAGE_ASPECT_RATIOS,
  IMAGE_ASPECT_RATIO_HINTS,
  IMAGE_PURPOSES,
  IMAGE_PURPOSE_HINTS,
  IMAGE_PURPOSE_LABELS,
  STABILITY_MODELS,
  STABILITY_MODEL_CREDITS,
  STABILITY_MODEL_HINTS,
  STABILITY_MODEL_LABELS,
  useGenerateImage,
  type ImageAspectRatio,
  type ImagePurpose,
  type StabilityModel,
} from "@/lib/api/images";

interface ImageGenerationFormProps {
  workspace: string;
  onGenerated?: (assetId: string) => void;
}

interface FormState {
  purpose: ImagePurpose;
  subject: string;
  model: StabilityModel;
  aspectRatio: ImageAspectRatio;
  stylePreset: string | undefined;
  showAdvanced: boolean;
  negativePromptOverride: string;
}

const INITIAL_STATE: FormState = {
  purpose: "scene",
  subject: "",
  model: "sd3-large",
  aspectRatio: "16:9",
  stylePreset: undefined,
  showAdvanced: false,
  negativePromptOverride: "",
};

export function ImageGenerationForm({
  workspace,
  onGenerated,
}: ImageGenerationFormProps) {
  const [state, setState] = useState<FormState>(INITIAL_STATE);
  const generate = useGenerateImage();

  function handleChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((s) => ({ ...s, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const subject = state.subject.trim();
    if (!subject) return;
    generate.mutate(
      {
        workspace,
        purpose: state.purpose,
        subject,
        model: state.model,
        aspect_ratio: state.aspectRatio,
        style_preset: state.stylePreset,
        negative_prompt_override:
          state.showAdvanced && state.negativePromptOverride.trim()
            ? state.negativePromptOverride.trim()
            : undefined,
      },
      {
        onSuccess: (asset) => {
          onGenerated?.(asset.id);
        },
      },
    );
  }

  const submitting = generate.isPending;
  const result = generate.data;
  const submitDisabled = submitting || !state.subject.trim();

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-6"
      data-testid="image-generation-form"
    >
      {/* Purpose */}
      <section className="flex flex-col gap-2">
        <Label className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Purpose
        </Label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {IMAGE_PURPOSES.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => handleChange("purpose", p)}
              data-testid={`image-purpose-${p}`}
              data-selected={state.purpose === p ? "true" : "false"}
              title={IMAGE_PURPOSE_HINTS[p]}
              className={cn(
                "flex flex-col items-start gap-1 rounded-md border p-3 text-left text-sm transition-colors",
                state.purpose === p
                  ? "border-foreground bg-foreground/5"
                  : "border-border hover:border-foreground/30",
              )}
            >
              <span className="font-medium">{IMAGE_PURPOSE_LABELS[p]}</span>
              <span className="text-xs text-muted-foreground">
                {IMAGE_PURPOSE_HINTS[p]}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* Subject */}
      <section className="flex flex-col gap-2">
        <Label
          htmlFor="image-subject"
          className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Subject
        </Label>
        <textarea
          id="image-subject"
          data-testid="image-subject"
          value={state.subject}
          onChange={(e) => handleChange("subject", e.target.value)}
          placeholder="Describe what the image should show."
          rows={3}
          required
          disabled={submitting}
          className="min-h-[88px] rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
        />
      </section>

      {/* Model */}
      <section className="flex flex-col gap-2">
        <Label className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Model
        </Label>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
          {STABILITY_MODELS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => handleChange("model", m)}
              data-testid={`image-model-${m}`}
              data-selected={state.model === m ? "true" : "false"}
              title={STABILITY_MODEL_HINTS[m]}
              className={cn(
                "flex flex-col items-start gap-1 rounded-md border p-3 text-left text-sm transition-colors",
                state.model === m
                  ? "border-foreground bg-foreground/5"
                  : "border-border hover:border-foreground/30",
              )}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="font-medium">{STABILITY_MODEL_LABELS[m]}</span>
                <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  {STABILITY_MODEL_CREDITS[m]} credits
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {STABILITY_MODEL_HINTS[m]}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* Aspect ratio */}
      <section className="flex flex-col gap-2">
        <Label className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Aspect ratio
        </Label>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
          {IMAGE_ASPECT_RATIOS.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => handleChange("aspectRatio", r)}
              data-testid={`image-ratio-${r}`}
              data-selected={state.aspectRatio === r ? "true" : "false"}
              title={IMAGE_ASPECT_RATIO_HINTS[r]}
              className={cn(
                "rounded-md border px-3 py-2 text-sm transition-colors",
                state.aspectRatio === r
                  ? "border-foreground bg-foreground/5 font-medium"
                  : "border-border hover:border-foreground/30",
              )}
            >
              {r}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {IMAGE_ASPECT_RATIO_HINTS[state.aspectRatio]}
        </p>
      </section>

      {/* Style preset */}
      <section className="flex flex-col gap-2">
        <Label className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Style preset (optional)
        </Label>
        <StylePresetPicker
          value={state.stylePreset}
          onChange={(p) => handleChange("stylePreset", p)}
          disabled={submitting}
        />
      </section>

      {/* Advanced */}
      <section className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => handleChange("showAdvanced", !state.showAdvanced)}
          data-testid="image-advanced-toggle"
          className="self-start font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground hover:text-foreground"
        >
          {state.showAdvanced ? "Hide" : "Show"} advanced
        </button>
        {state.showAdvanced && (
          <div className="flex flex-col gap-2 rounded-md border border-border p-3">
            <Label
              htmlFor="image-neg-prompt"
              className="text-xs text-muted-foreground"
            >
              Negative prompt override
            </Label>
            <textarea
              id="image-neg-prompt"
              data-testid="image-negative-prompt"
              value={state.negativePromptOverride}
              onChange={(e) =>
                handleChange("negativePromptOverride", e.target.value)
              }
              placeholder="Leave blank to use the default for this purpose."
              rows={2}
              disabled={submitting}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
            />
          </div>
        )}
      </section>

      {/* Submit */}
      <div className="flex items-center justify-end gap-3">
        {submitting && (
          <span
            data-testid="image-submitting"
            className="flex items-center gap-2 text-xs text-muted-foreground"
          >
            <Loader2 className="h-3 w-3 animate-spin" />
            Generating ({STABILITY_MODEL_CREDITS[state.model]} credits)…
          </span>
        )}
        <Button
          type="submit"
          disabled={submitDisabled}
          data-testid="image-submit"
        >
          Generate image
        </Button>
      </div>

      {/* Error */}
      {generate.isError && (
        <div
          data-testid="image-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <strong>Generation failed.</strong>{" "}
            {extractErrorMessage(generate.error) ?? "Try again in a moment."}
          </div>
        </div>
      )}

      {/* Result */}
      {result && !generate.isError && (
        <GeneratedImageCard asset={result} />
      )}
    </form>
  );
}

function GeneratedImageCard({
  asset,
}: {
  asset: ReturnType<typeof useGenerateImage>["data"];
}) {
  if (!asset) return null;
  return (
    <article
      data-testid="image-result"
      className="flex flex-col gap-3 rounded-md border border-border p-4"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Generated
        </span>
        <span className="text-xs text-muted-foreground">
          {asset.model} · {asset.aspect_ratio} · {asset.purpose}
          {asset.style_preset ? ` · ${asset.style_preset}` : ""}
        </span>
      </header>
      <img
        src={asset.file_path}
        alt={asset.prompt.slice(0, 120)}
        className="w-full rounded-md border border-border"
      />
      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">Prompt</summary>
        <p className="mt-2 whitespace-pre-wrap">{asset.prompt}</p>
      </details>
    </article>
  );
}

function extractErrorMessage(err: unknown): string | undefined {
  if (!err) return undefined;
  if (err instanceof Error) return err.message;
  return undefined;
}
