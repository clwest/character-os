/**
 * Per-recipe form — drives ``POST /api/compositions/``.
 *
 * V15.1 handles five field types (text / textarea / checkbox /
 * select / number) + spokesperson_picker, which covers the three
 * recipes in ``LIVE_RECIPE_KINDS``. asset_picker (V15.2-V15.3)
 * and dialogue_lines (V15.4) come later — coming-soon recipes
 * short-circuit with a placeholder.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  LIVE_RECIPE_KINDS,
  type AssetListItem,
  type Recipe,
  type RecipeField,
  useAssets,
  useCreateComposition,
  useRecipe,
} from "@/lib/api/recipes";
import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople, type Spokesperson } from "@/lib/api/spokespeople";
import { useKnowledgePreview } from "@/lib/api/knowledge-preview";
import { ApiError } from "@/lib/api/client";
// B2.5 — script_picker field type
import { useScripts } from "@/lib/api/scripts";
// SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — episode-driven
// pre-fill + cast-only performer restriction.
import { useEpisode } from "@/lib/api/episodes";

type FormState = Record<string, unknown>;

export function RecipeFormRoute() {
  const { kind } = useParams<{ kind: string }>();
  const recipe = useRecipe(kind);
  const me = useMe();
  const spokespeople = useSpokespeople();
  const create = useCreateComposition();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // F1 (workspace fabric) — when the gallery passes a
  // `?spokesperson=<id>` hint we pre-bind the recipe's
  // spokesperson_picker field. The operator can still
  // change it; the hint just sets the initial value
  // (F0 contract rule 2).
  const spokespersonHint = searchParams.get("spokesperson") ?? undefined;
  // SESSION 262 / EPISODE_SCHEMA_V1 — when the Episode detail
  // page's "New render under this Episode" CTA passes
  // `?episode=<uuid>`, we attach the resulting Composition to
  // that Episode on submit. There's no user-visible form field
  // for it — the FK is set silently and the operator sees the
  // attachment on the Composition detail page.
  const episodeHint = searchParams.get("episode") ?? undefined;
  // SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — when launched
  // from Episode context, fetch the Episode so we can:
  //   1. pre-fill the topic/cast/mode fields from Episode data;
  //   2. restrict spokesperson-picker options to Episode.cast
  //      (Episode.cast is authoritative for performers per the
  //      SESSION 262 operator brief correction #1);
  //   3. surface the "Episode: <title>" chip in the header;
  //   4. block submit with a clear insufficient-cast prompt
  //      rather than silently permitting Universe fallback.
  // `useEpisode(undefined)` is a no-op (query disabled) so this
  // is free for standalone/legacy launches.
  const episodeQuery = useEpisode(episodeHint);
  const episode = episodeQuery.data;

  const [form, setForm] = useState<FormState>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Track whether the operator has explicitly overridden any
  // Episode-pre-filled field so we don't clobber their edits on
  // re-render when the Episode query settles.
  const [prefilledFromEpisode, setPrefilledFromEpisode] = useState(false);

  // Pre-bind the spokesperson_picker fields from the URL hint
  // once the recipe metadata lands. The operator can still
  // change the selection — the hint is the initial value
  // only (F0 contract rule 2). Re-runs only when the hint
  // or recipe identity changes; doesn't clobber subsequent
  // operator edits.
  useEffect(() => {
    if (!spokespersonHint || !recipe.data) return;
    setForm((prev) => {
      const next = { ...prev };
      let touched = false;
      for (const field of recipe.data!.fields) {
        if (field.type === "spokesperson_picker" && !prev[field.name]) {
          next[field.name] = spokespersonHint;
          touched = true;
        }
      }
      return touched ? next : prev;
    });
  }, [spokespersonHint, recipe.data]);

  // SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — one-shot
  // pre-fill from Episode when both the Episode + the recipe
  // metadata are loaded. Runs once (guarded by
  // prefilledFromEpisode); subsequent operator edits are never
  // clobbered. Cast ordering uses Episode.cast[] which the
  // backend serializes by EpisodeCast.added_at (UI convention
  // only — NOT a protagonist/lead role designation per
  // the audit doc §Q10).
  useEffect(() => {
    if (prefilledFromEpisode) return;
    if (!episode || !recipe.data) return;
    setForm((prev) => {
      const next = { ...prev };
      let touched = false;
      const seedIfEmpty = (name: string, value: unknown) => {
        if (value === undefined || value === null || value === "") return;
        if (prev[name] === undefined || prev[name] === "") {
          next[name] = value;
          touched = true;
        }
      };
      for (const field of recipe.data!.fields) {
        // Topic textarea — seed from Episode.operator_topic on any
        // recipe whose primary textarea is named `topic`
        // (dialogue_scene, long_form_ad, talking_head AI-topic).
        if (field.type === "textarea" && field.name === "topic") {
          seedIfEmpty(field.name, episode.operator_topic);
        }
        // Single-primary recipes (talking_head, long_form_ad) —
        // seed with cast[0].
        if (
          field.type === "spokesperson_picker" &&
          (field.name === "spokesperson_id"
            || field.name === "primary_spokesperson_id")
        ) {
          seedIfEmpty(field.name, episode.cast[0]?.id);
        }
        // Dialogue secondary — seed with cast[1] (added_at order).
        if (
          field.type === "spokesperson_picker" &&
          field.name === "secondary_spokesperson_id"
        ) {
          seedIfEmpty(field.name, episode.cast[1]?.id);
        }
        // Dialogue mode — Episode implies AI-Topic (topic + cast
        // declared upstream). Operator can flip in the field.
        if (
          field.type === "select" &&
          field.name === "dialogue_mode"
        ) {
          seedIfEmpty(field.name, "ai_topic");
        }
      }
      if (touched) {
        setPrefilledFromEpisode(true);
        return next;
      }
      return prev;
    });
  }, [episode, recipe.data, prefilledFromEpisode]);

  // Rules of Hooks — every hook call has to fire on every
  // render in the same order. The early returns below for
  // loading / error / coming-soon / no-workspace states must
  // come AFTER all hook calls; we compute F4's preview inputs
  // here so useDebounced + useKnowledgePreview are called
  // unconditionally and gated by their `enabled` flags
  // instead of by component-level returns.
  const r = recipe.data;
  const useKnowledgeField = r?.fields.find(
    (f) => f.name === "use_knowledge" && f.type === "checkbox",
  );
  const hasUseKnowledge = Boolean(useKnowledgeField);
  const useKnowledgeChecked = hasUseKnowledge
    ? Boolean(
        (form.use_knowledge as boolean | undefined) ??
          useKnowledgeField?.default ??
          false,
      )
    : false;
  // SESSION 257 / AI-D4 — dialogue_scene has a mode field that
  // flips which OTHER fields render. Kind check keeps this scoped
  // to dialogue_scene so no other recipe's fields see the filter.
  const isDialogueScene = r?.kind === "dialogue_scene";
  const dialogueModeField = r?.fields.find(
    (f) => f.name === "dialogue_mode" && f.type === "select",
  );
  const dialogueMode = isDialogueScene
    ? ((form.dialogue_mode as string | undefined) ??
       (dialogueModeField?.default as string | undefined) ??
       "manual")
    : null;

  const primaryTextareaField = r?.fields.find((f) => f.type === "textarea");
  const queryValue =
    typeof form[primaryTextareaField?.name ?? ""] === "string"
      ? (form[primaryTextareaField?.name ?? ""] as string)
      : "";
  const spokespersonValue = (form.spokesperson_id ??
    form.primary_spokesperson_id ?? "") as string;
  const debouncedQuery = useDebounced(queryValue, 500);
  const previewEnabled =
    hasUseKnowledge &&
    useKnowledgeChecked &&
    Boolean(spokespersonValue) &&
    debouncedQuery.trim().length >= 8;
  const preview = useKnowledgePreview(
    previewEnabled
      ? { spokesperson: spokespersonValue, query: debouncedQuery.trim() }
      : null,
  );

  if (recipe.isLoading || me.isLoading) {
    return <FormSkeleton />;
  }
  if (recipe.isError || !r) {
    return (
      <NotFound
        message={
          recipe.error instanceof Error
            ? recipe.error.message
            : "Recipe not found"
        }
      />
    );
  }

  const isLive = LIVE_RECIPE_KINDS.has(r.kind);

  if (!isLive) {
    return <ComingSoon recipe={r} />;
  }

  const workspaceId = me.data?.default_workspace?.id;
  if (!workspaceId) {
    return <NoWorkspace />;
  }

  const workspaceSpokespeople = (spokespeople.data ?? []).filter(
    (s) => s.workspace === workspaceId,
  );

  // SESSION 262 — Episode.cast is authoritative for performers
  // when the recipe launched from Episode context (correction #1
  // in the SESSION 262 operator brief). Filter the picker option
  // set to Episode.cast members only; do NOT silently fall back
  // to the Universe/workspace roster. When no Episode context,
  // preserve the pre-Episode workspace-roster behavior.
  const castOnlySpokespeople = episode
    ? workspaceSpokespeople.filter((s) =>
        episode.cast.some((c) => c.id === s.id),
      )
    : workspaceSpokespeople;

  // Compute how many performer slots this recipe needs so we can
  // detect insufficient-cast Episode launches. The three live
  // dialogue-family fields we care about:
  const performerFieldNames = new Set([
    "spokesperson_id",
    "primary_spokesperson_id",
    "secondary_spokesperson_id",
  ]);
  const performerSlotCount = r.fields.filter(
    (f) =>
      f.type === "spokesperson_picker" &&
      performerFieldNames.has(f.name),
  ).length;
  const insufficientCast = Boolean(
    episode && performerSlotCount > episode.cast.length,
  );

  // Determine which asset types this recipe needs. Each
  // asset_picker field declares its asset_type; we fetch one
  // query per distinct type so the picker dropdowns are ready
  // when the field renders.
  const assetTypesNeeded = Array.from(
    new Set(
      r.fields
        .filter((f) => f.type === "asset_picker" && f.asset_type)
        .map((f) => f.asset_type as AssetListItem["asset_type"]),
    ),
  );

  const handleChange = (name: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  // SESSION 257 / AI-D4 — per-mode field visibility for
  // dialogue_scene. Manual mode hides AI-only fields; AI Topic
  // mode hides the manual dialogue_lines editor. Non-dialogue
  // recipes are unaffected. Kept as a pure function of
  // (field.name, dialogueMode) so the render loop and submit
  // filter agree on the same set. Mode-switch preserves local
  // form state — switching back restores previous inputs.
  const isFieldVisible = (fieldName: string): boolean => {
    if (!isDialogueScene) return true;
    if (dialogueMode === "ai_topic") {
      return fieldName !== "lines";
    }
    // manual mode (default; also selected on omitted dialogue_mode)
    return ![
      "secondary_spokesperson_id",
      "topic",
      "target_duration_seconds",
      "use_knowledge",
      "verifier_mode",
      "opener",
    ].includes(fieldName);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const params: Record<string, unknown> = {};
    for (const field of r.fields) {
      // AI-D4 — only submit values for fields visible in the
      // active mode. Filter keeps stale hidden values from
      // reaching the backend (e.g. abandoned manual lines
      // shouldn't drive an AI Topic request).
      if (!isFieldVisible(field.name)) continue;

      const touched = form[field.name];
      // When the operator never touched the field, fall back to the
      // schema's default for submission. This matches the render-side
      // `defaultedValue = value ?? field.default` pattern — without
      // this fallback, a required field with a non-null default
      // (e.g. V17.2's `target_duration`) silently drops on submit
      // and the backend starter explodes with a missing-kwarg 500.
      const v =
        touched === undefined || touched === "" || touched === null
          ? field.default
          : touched;
      if (v === undefined || v === "" || v === null) {
        if (field.required) {
          setSubmitError(`Missing required field: ${field.label}`);
          return;
        }
        continue;
      }
      params[field.name] = v;
    }

    try {
      const comp = await create.mutateAsync({
        kind: r.kind,
        workspace: workspaceId,
        params,
        // SESSION 262 — attach to the Episode context when the
        // operator entered this form via "New render under this
        // Episode." Omitted otherwise (standalone Composition).
        ...(episodeHint ? { episode: episodeHint } : {}),
      });
      navigate(`/compositions/${comp.id}`, { replace: true });
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    }
  };

  const galleryHref = spokespersonHint
    ? `/recipes?spokesperson=${spokespersonHint}`
    : "/recipes";

  return (
    <div className="flex flex-col gap-8 py-10">
      <Header recipe={r} galleryHref={galleryHref} />
      {/* SESSION 262 — Episode context chip. Renders only when
          launched from Episode; standalone recipe workflow shows
          nothing here (byte-for-byte pre-Episode header). */}
      {episode && (
        <div
          data-testid="episode-context-chip"
          className="flex flex-wrap items-baseline gap-2 rounded-md border border-luxe bg-card/60 px-4 py-2 text-sm"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
            Rendering under episode
          </span>
          <Link
            to={`/workspace/episodes/${episode.id}`}
            className="font-display italic text-gold hover:underline"
            data-testid="episode-context-title-link"
          >
            {episode.title}
          </Link>
          <span className="text-mist">·</span>
          <span className="text-mist">
            cast: {episode.cast.map((c) => c.name).join(", ") || "(empty)"}
          </span>
        </div>
      )}
      {/* SESSION 262 — insufficient-cast block. Recipe needs more
          performer slots than Episode.cast can supply. Per operator
          brief correction #1, do NOT silently fall back to the
          Universe roster; require an explicit cast-add action on
          the Episode first. */}
      {episode && insufficientCast && (
        <div
          data-testid="episode-insufficient-cast"
          className="flex flex-col gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm"
        >
          <p className="text-cream">
            This recipe needs {performerSlotCount} performer
            {performerSlotCount === 1 ? "" : "s"} but
            {" "}<em>{episode.title}</em> currently has only{" "}
            {episode.cast.length} in its cast. Add the missing
            performer{performerSlotCount - episode.cast.length === 1 ? "" : "s"}
            {" "}to the Episode first — this preserves the story-level
            statement of "who's in this story."
          </p>
          <div>
            <Button asChild variant="secondary">
              <Link to={`/workspace/episodes/${episode.id}`}>
                Add cast to Episode
              </Link>
            </Button>
          </div>
        </div>
      )}
      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-6"
        data-testid={`recipe-form-${r.kind}`}
      >
        {r.fields.filter((field) => isFieldVisible(field.name)).map((field) => (
          <FieldRenderer
            key={field.name}
            field={field}
            value={form[field.name]}
            onChange={(value) => handleChange(field.name, value)}
            // AI-D4 — filter primary out of the secondary picker
            // so operators can't accidentally pick the same person
            // twice. Backend still validates authoritatively; this
            // is UX only.
            spokespeople={
              // SESSION 262 — Episode.cast is the authoritative
              // performer set when launched from Episode context;
              // pre-Episode behavior (workspace roster) otherwise.
              // Dialogue secondary picker still filters out the
              // currently-selected primary to avoid
              // same-person-both-roles selection.
              isDialogueScene &&
              field.name === "secondary_spokesperson_id" &&
              form.primary_spokesperson_id
                ? castOnlySpokespeople.filter(
                    (s) => s.id !== form.primary_spokesperson_id,
                  )
                : castOnlySpokespeople
            }
            workspaceId={workspaceId}
            briefModeHelper={
              field.name === primaryTextareaField?.name && useKnowledgeChecked
            }
            // SESSION 251 — knowledge-off long-form: show a live
            // "~Ns estimated" hint beside the primary script textarea
            // derived from the current input length. Hidden when
            // knowledge is on (duration then comes from the select).
            speakingRateCharsPerSecond={
              field.name === primaryTextareaField?.name && !useKnowledgeChecked
                ? r.speaking_rate_chars_per_second
                : undefined
            }
          />
        ))}
        {assetTypesNeeded.length > 0 && (
          <AssetHint types={assetTypesNeeded} workspaceId={workspaceId} />
        )}
        {hasUseKnowledge && useKnowledgeChecked && (
          <KnowledgePreviewPanel
            enabled={previewEnabled}
            spokespersonPicked={Boolean(spokespersonValue)}
            queryReady={debouncedQuery.trim().length >= 8}
            isLoading={preview.isFetching}
            data={preview.data}
            error={preview.error}
          />
        )}

        {submitError && (
          <div
            className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
            data-testid="recipe-submit-error"
          >
            {submitError}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-luxe pt-6">
          <Link
            to={galleryHref}
            className="font-mono text-xs uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
          >
            Cancel
          </Link>
          <Button
            type="submit"
            size="lg"
            // SESSION 262 — block submit when Episode has too few
            // cast members for the recipe. Operator must add cast
            // on the Episode first (correction #1 in operator brief).
            disabled={create.isPending || insufficientCast}
            data-testid="recipe-submit"
            title={
              insufficientCast
                ? "Add cast to the Episode before rendering."
                : undefined
            }
          >
            {create.isPending ? "Starting render…" : "Run composition"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function Header({
  recipe,
  galleryHref,
}: {
  recipe: Recipe;
  galleryHref: string;
}) {
  return (
    <header className="relative flex flex-col gap-3 border-b border-luxe pb-6">
      <Link
        to={galleryHref}
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
      >
        <ArrowLeft className="h-3 w-3" />
        All recipes
      </Link>
      <h1 className="font-display text-3xl leading-tight tracking-tight text-cream md:text-4xl">
        {recipe.display_name}
      </h1>
      <p className="max-w-2xl text-mist">{recipe.description}</p>
    </header>
  );
}

function FieldRenderer({
  field,
  value,
  onChange,
  spokespeople,
  workspaceId,
  briefModeHelper = false,
  speakingRateCharsPerSecond,
}: {
  field: RecipeField;
  value: unknown;
  onChange: (value: unknown) => void;
  spokespeople: Spokesperson[];
  workspaceId: string;
  /** When true (F4), append a "this is a brief — the LLM
   *  expands it" hint to the field's help_text. Only the
   *  primary textarea of a use_knowledge-enabled recipe sets
   *  this. */
  briefModeHelper?: boolean;
  /** SESSION 251 — when set, render a live "estimated duration"
   *  chip beside the field. Caller sets this only on the primary
   *  textarea of a knowledge-OFF long-form recipe, using the
   *  canonical constant from the recipe metadata (no client
   *  hardcoding). */
  speakingRateCharsPerSecond?: number;
}) {
  const id = `field-${field.name}`;

  // SESSION 210 — when `briefModeHelper` is on (the primary
  // textarea of a use_knowledge=true recipe), the field is a
  // TOPIC, not a literal script. Per the SESSION 209 calibration
  // finding: K6's build_render_brief replaces the operator's
  // script with a brand-voiced expansion from workspace
  // knowledge. The displayed label reflects this so operators
  // don't write 120-char lines expecting them to be spoken.
  const displayLabel = briefModeHelper ? "Topic" : field.label;

  return (
    <div className="flex flex-col gap-2" data-testid={`recipe-field-${field.name}`}>
      <div className="flex flex-col gap-1">
        <Label
          htmlFor={id}
          className="text-[11px] uppercase tracking-[0.22em] text-fog"
        >
          {displayLabel}
          {briefModeHelper && (
            <span className="ml-2 normal-case tracking-normal italic text-gold/80">
              — knowledge mode
            </span>
          )}
          {!field.required && <span className="ml-2 normal-case tracking-normal text-fog/60">(optional)</span>}
        </Label>
        {field.help_text && !briefModeHelper && (
          <p className="text-xs text-fog">{field.help_text}</p>
        )}
        {briefModeHelper && (
          <p
            className="text-xs text-mist"
            data-testid="brief-mode-helper"
          >
            <strong className="text-cream">This is a topic, not a
            script.</strong> When knowledge mode is on, the writer
            reads your workspace docs and drafts the spoken lines
            for you — one or two sentences here is plenty (e.g. <em
            className="italic">"60-second spot about our spring launch,
            focused on the early-bird discount"</em>). Final render
            length depends on the drafted script, not on this
            input's character count.
          </p>
        )}
      </div>
      <FieldInput
        id={id}
        field={field}
        value={value}
        onChange={onChange}
        spokespeople={spokespeople}
        workspaceId={workspaceId}
      />
      {speakingRateCharsPerSecond && (
        <ScriptDurationHint
          text={typeof value === "string" ? value : ""}
          charsPerSecond={speakingRateCharsPerSecond}
        />
      )}
    </div>
  );
}

// SESSION 251 — live estimated-duration chip under the primary
// long-form textarea when knowledge mode is OFF. Uses the
// speaking-rate constant surfaced by the recipe metadata (single
// source of truth with the server-side word-budget math). Kept
// tiny + monospace so it doesn't compete with the field label
// for attention.
function ScriptDurationHint({
  text,
  charsPerSecond,
}: {
  text: string;
  charsPerSecond: number;
}) {
  const seconds = Math.max(
    0,
    Math.round(text.trim().length / charsPerSecond),
  );
  const label =
    seconds < 60
      ? `~${seconds}s`
      : `~${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return (
    <p
      className="text-[11px] font-mono uppercase tracking-[0.18em] text-fog"
      data-testid="script-duration-hint"
    >
      Estimated spoken duration: {label}
      {text.trim().length === 0 && " (type your script to see the estimate)"}
    </p>
  );
}

function FieldInput({
  id,
  field,
  value,
  onChange,
  spokespeople,
  workspaceId,
}: {
  id: string;
  field: RecipeField;
  value: unknown;
  onChange: (value: unknown) => void;
  spokespeople: Spokesperson[];
  workspaceId: string;
}) {
  const defaultedValue = value ?? field.default;

  switch (field.type) {
    case "text":
      return (
        <Input
          id={id}
          type="text"
          maxLength={field.max_chars}
          value={(defaultedValue as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "textarea":
      return (
        <textarea
          id={id}
          rows={6}
          maxLength={field.max_chars}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-fog focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          value={(defaultedValue as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "checkbox": {
      const checked = (defaultedValue as boolean) ?? false;
      return (
        <label className="flex items-center gap-2 text-sm">
          <input
            id={id}
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className="h-4 w-4 rounded border-input"
          />
          <span className="text-fog">Enable</span>
        </label>
      );
    }
    case "number":
      return (
        <Input
          id={id}
          type="number"
          min={field.min_value}
          max={field.max_value}
          value={
            defaultedValue === undefined || defaultedValue === null
              ? ""
              : String(defaultedValue)
          }
          onChange={(e) => {
            const next = e.target.value;
            if (next === "") {
              onChange(undefined);
            } else {
              const parsed = Number(next);
              onChange(Number.isFinite(parsed) ? parsed : undefined);
            }
          }}
        />
      );
    case "select":
      return (
        <select
          id={id}
          value={(defaultedValue as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {!field.required && <option value="">— select —</option>}
          {(field.choices ?? []).map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      );
    case "spokesperson_picker":
      return (
        <select
          id={id}
          value={(defaultedValue as string) ?? ""}
          onChange={(e) => onChange(e.target.value || undefined)}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <option value="">— select spokesperson —</option>
          {spokespeople.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
              {s.runway_avatar_id === "" ? " (no avatar)" : ""}
            </option>
          ))}
        </select>
      );
    case "asset_picker":
      return (
        <AssetPicker
          id={id}
          assetType={field.asset_type as AssetListItem["asset_type"]}
          workspaceId={workspaceId}
          roleFilter={field.role_filter}
          value={defaultedValue as string | undefined}
          onChange={(v) => onChange(v || undefined)}
          required={field.required}
        />
      );
    case "dialogue_lines":
      return (
        <DialogueLinesEditor
          value={(defaultedValue as DialogueLine[] | undefined) ?? []}
          onChange={(v) => onChange(v)}
          spokespeople={spokespeople}
        />
      );
    case "script_picker":
      return (
        <ScriptPicker
          id={id}
          workspaceId={workspaceId}
          value={defaultedValue as string | undefined}
          onChange={(v) => onChange(v || undefined)}
          required={field.required}
        />
      );
    default:
      return <UnsupportedField message={`Unknown field type`} />;
  }
}

function AssetPicker({
  id,
  assetType,
  workspaceId,
  roleFilter,
  value,
  onChange,
  required,
}: {
  id: string;
  assetType: AssetListItem["asset_type"];
  workspaceId: string;
  // A7 (SESSION 190) — optional AssetRole that narrows the
  // picker dropdown. Forwarded as ``?role=<value>`` to the
  // backend AssetViewSet.
  roleFilter?: string;
  value: string | undefined;
  onChange: (value: string) => void;
  required: boolean;
}) {
  const assets = useAssets({
    workspace: workspaceId,
    assetType,
    role: roleFilter,
  });

  if (assets.isLoading) {
    return (
      <div className="h-10 animate-pulse rounded-md border bg-muted/30" />
    );
  }
  if (assets.isError) {
    return (
      <UnsupportedField
        message={`Couldn't load ${assetType} assets: ${
          assets.error instanceof Error ? assets.error.message : "unknown error"
        }`}
      />
    );
  }

  const list = assets.data ?? [];
  if (list.length === 0) {
    return (
      <div className="flex flex-col gap-1 rounded-md border border-dashed bg-muted/20 p-4 text-xs text-fog">
        <p className="font-mono uppercase tracking-[0.22em]">
          No {assetType} assets yet
        </p>
        <p className="normal-case tracking-normal">
          {assetType === "image" ? (
            <>
              Generate one from the{" "}
              <Link to="/images" className="underline">
                Images tab
              </Link>{" "}
              first, then come back here to use it as a reference frame.
            </>
          ) : (
            <>
              Run a recipe that produces a {assetType} first (e.g. a
              {assetType === "clip" ? " talking head or cinematic visual" : ""}
              {assetType === "audio" ? " voice design" : ""}), then come back
              here to use it as input.
            </>
          )}
        </p>
      </div>
    );
  }

  return (
    <select
      id={id}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      {!required && <option value="">— none —</option>}
      {required && !value && (
        <option value="" disabled>
          — select a {assetType} —
        </option>
      )}
      {list.map((a) => (
        <option key={a.id} value={a.id}>
          {assetLabel(a)}
        </option>
      ))}
    </select>
  );
}

// ---- ScriptPicker (B2.5 — script_picker field type) ---------------

/**
 * Renders a dropdown of READY (approved) scripts for the auto_script recipe.
 * Called by FieldInput when field.type === "script_picker".
 *
 * When no approved scripts exist, renders an empty-state hint that links
 * the operator to /workspace/scripts so they can draft + approve one.
 * Mirrors the AssetPicker empty-state UX pattern.
 */
function ScriptPicker({
  id,
  workspaceId,
  value,
  onChange,
  required,
}: {
  id: string;
  workspaceId: string;
  value: string | undefined;
  onChange: (value: string) => void;
  required: boolean;
}) {
  // SESSION 251 — widened to include RENDERED scripts. The prior
  // ``status: "ready"`` filter hid every script the operator had
  // ever actually fired a composition from, forcing a clone-then-
  // re-approve loop just to reuse a known-good script. RENDERED
  // scripts are approved AND proven to run to completion; they're
  // exactly the ones an operator wants to reuse. See finding-f-*
  // notes / SESSION 251 handoff.
  const scripts = useScripts(workspaceId, {});

  if (scripts.isLoading) {
    return (
      <div className="h-10 animate-pulse rounded-md border bg-muted/30" />
    );
  }

  if (scripts.isError) {
    return (
      <UnsupportedField
        message={`Couldn't load approved scripts: ${
          scripts.error instanceof Error ? scripts.error.message : "unknown error"
        }`}
      />
    );
  }

  // Client-side filter to the two "approved" states. DRAFT is not
  // yet approved; ARCHIVED is intentionally hidden.
  const list = (scripts.data ?? []).filter(
    (s) => s.status === "ready" || s.status === "rendered",
  );

  if (list.length === 0) {
    return (
      <div
        data-testid="script-picker-empty"
        className="flex flex-col gap-1 rounded-md border border-dashed bg-muted/20 p-4 text-xs text-fog"
      >
        <p className="font-mono uppercase tracking-[0.22em]">
          No approved scripts yet
        </p>
        <p className="normal-case tracking-normal">
          Draft a script at{" "}
          <Link
            to="/workspace/scripts/new"
            className="underline text-primary"
          >
            /workspace/scripts
          </Link>
          , then approve it before running this recipe.
        </p>
      </div>
    );
  }

  return (
    <select
      id={id}
      data-testid="script-picker-select"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      {!required && <option value="">— none —</option>}
      {required && !value && (
        <option value="" disabled>
          — select an approved script —
        </option>
      )}
      {list.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name || "Untitled script"} · {s.spokesperson_name}
          {s.status === "rendered" && " · previously rendered"}
        </option>
      ))}
    </select>
  );
}

function assetLabel(a: AssetListItem): string {
  // W11.6.5.1 — operator-facing label cascade:
  //   1. ``title`` (auto-populated on /api/images/ create from
  //      subject; operator can override).
  //   2. ``subject`` (image rows from W11.6.4+ when title is
  //      empty — typically a pre-W11.6.5.1 row).
  //   3. ``file_path``-tail filename + duration (the legacy
  //      shape used for clip/audio assets that don't have
  //      titles yet).
  //
  // Pre-W11.6.5.1 image rows expose data URIs in file_path
  // which split-tail to garbage like "data:image/png;base64,
  // iVBORw0KGgo…" — actively misleading. Subject is the
  // far better fallback for those.
  if (a.title && a.title.trim()) {
    return _trim(a.title);
  }
  if (a.asset_type === "image" && a.subject && a.subject.trim()) {
    return _trim(a.subject);
  }
  const seconds =
    a.duration_ms != null ? ` · ${(a.duration_ms / 1000).toFixed(1)}s` : "";
  const filename = a.file_path.split("/").pop() || a.file_path;
  const trimmedName = _trim(filename);
  return `${trimmedName}${seconds}`;
}

function _trim(s: string): string {
  return s.length > 60 ? `${s.slice(0, 57)}…` : s;
}

function AssetHint({
  types,
  workspaceId,
}: {
  types: AssetListItem["asset_type"][];
  workspaceId: string;
}) {
  // Surface a single hint row when any picker has zero options —
  // operators new to the gallery want a quick "what do I do now?"
  // signal.
  const clipsQuery = useAssets(
    types.includes("clip") ? { workspace: workspaceId, assetType: "clip" } : undefined,
  );
  const audioQuery = useAssets(
    types.includes("audio") ? { workspace: workspaceId, assetType: "audio" } : undefined,
  );
  const anyMissing =
    (types.includes("clip") && clipsQuery.data?.length === 0) ||
    (types.includes("audio") && audioQuery.data?.length === 0);
  if (!anyMissing) return null;
  return (
    <div className="rounded-md border border-warning/40 bg-warning/10 p-4 text-xs text-warning">
      <p className="font-mono uppercase tracking-[0.22em]">Tip</p>
      <p className="mt-1 normal-case tracking-normal">
        This recipe needs existing workspace assets as input. Run a producing
        recipe first (Talking head or Cinematic visual produce clips; Voice
        design produces audio in V15.3), then come back here.
      </p>
    </div>
  );
}

interface DialogueLine {
  spokesperson_id: string;
  text: string;
}

function DialogueLinesEditor({
  value,
  onChange,
  spokespeople,
}: {
  value: DialogueLine[];
  onChange: (lines: DialogueLine[]) => void;
  spokespeople: Spokesperson[];
}) {
  const lines = value.length === 0 ? [{ spokesperson_id: "", text: "" }] : value;

  const updateLine = (idx: number, patch: Partial<DialogueLine>) => {
    const next = lines.map((l, i) => (i === idx ? { ...l, ...patch } : l));
    onChange(next);
  };

  const addLine = () => {
    onChange([...lines, { spokesperson_id: "", text: "" }]);
  };

  const removeLine = (idx: number) => {
    if (lines.length === 1) {
      onChange([{ spokesperson_id: "", text: "" }]);
      return;
    }
    onChange(lines.filter((_, i) => i !== idx));
  };

  if (spokespeople.length < 2) {
    return (
      <div className="rounded-md border border-warning/40 bg-warning/10 p-4 text-xs text-warning">
        <p className="font-mono uppercase tracking-[0.22em]">Need 2+ spokespeople</p>
        <p className="mt-1 normal-case tracking-normal">
          Dialogue scenes work best with at least two characters. Create another
          spokesperson first, then come back.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3" data-testid="dialogue-lines-editor">
      {lines.map((line, idx) => (
        <div
          key={idx}
          className="flex flex-col gap-2 rounded-md border bg-card p-3"
          data-testid={`dialogue-line-${idx}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
              Line {idx + 1}
            </span>
            <button
              type="button"
              onClick={() => removeLine(idx)}
              className="inline-flex items-center gap-1 text-xs text-fog transition-colors hover:text-destructive"
              data-testid={`dialogue-line-remove-${idx}`}
              aria-label={`Remove line ${idx + 1}`}
            >
              <Trash2 className="h-3 w-3" />
              Remove
            </button>
          </div>
          <select
            value={line.spokesperson_id}
            onChange={(e) => updateLine(idx, { spokesperson_id: e.target.value })}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            data-testid={`dialogue-line-speaker-${idx}`}
          >
            <option value="">— who speaks? —</option>
            {spokespeople.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
                {s.runway_avatar_id === "" ? " (no avatar)" : ""}
              </option>
            ))}
          </select>
          <textarea
            rows={2}
            value={line.text}
            onChange={(e) => updateLine(idx, { text: e.target.value })}
            placeholder="What this character says…"
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-fog focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            data-testid={`dialogue-line-text-${idx}`}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={addLine}
        className="inline-flex w-fit items-center gap-1.5 rounded-md border border-dashed px-3 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:border-gold/40 hover:text-gold"
        data-testid="dialogue-line-add"
      >
        <Plus className="h-3 w-3" />
        Add line
      </button>
    </div>
  );
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

function KnowledgePreviewPanel({
  enabled,
  spokespersonPicked,
  queryReady,
  isLoading,
  data,
  error,
}: {
  enabled: boolean;
  spokespersonPicked: boolean;
  queryReady: boolean;
  isLoading: boolean;
  data: import("@/lib/api/knowledge-preview").KnowledgePreview | undefined;
  error: unknown;
}) {
  let body: React.ReactNode;
  if (!spokespersonPicked) {
    body = (
      <p className="text-xs text-fog">
        Pick a spokesperson above to preview what knowledge would inform this
        render.
      </p>
    );
  } else if (!queryReady) {
    body = (
      <p className="text-xs text-fog">
        Type a brief above (at least 8 characters) to preview the knowledge
        that would feed the LLM-synthesized script.
      </p>
    );
  } else if (isLoading && !data) {
    body = (
      <p className="text-xs text-fog">
        Checking what knowledge applies…
      </p>
    );
  } else if (error || data?.preview_failed) {
    body = (
      <p className="text-xs text-fog">
        Preview unavailable. The render will still pull knowledge at submit time.
      </p>
    );
  } else if (data && data.total_chunks === 0) {
    body = (
      <p className="text-xs text-fog">
        No matching knowledge for this brief. The render will use just your
        prompt + the spokesperson's business brief.
      </p>
    );
  } else if (data) {
    body = (
      <>
        <p className="text-xs text-fog">
          The LLM would draw from{" "}
          <strong>
            {data.docs_used.length} doc{data.docs_used.length === 1 ? "" : "s"}
          </strong>{" "}
          (<strong>{data.total_chunks} chunks</strong>):
        </p>
        <ul className="flex flex-col gap-1 text-xs">
          {data.docs_used.map((d) => (
            <li
              key={d.id}
              className="flex items-baseline justify-between"
            >
              <span className="line-clamp-1">{d.title}</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
                {d.chunk_count} chunk{d.chunk_count === 1 ? "" : "s"}
              </span>
            </li>
          ))}
        </ul>
      </>
    );
  } else {
    body = null;
  }

  return (
    <div
      className="flex flex-col gap-2 rounded-md border border-dashed bg-muted/30 p-4"
      data-testid="knowledge-preview-panel"
      aria-busy={isLoading || undefined}
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
        Knowledge preview
      </p>
      {body}
      {!enabled && spokespersonPicked && queryReady && (
        // Defensive — should not normally render; covers a
        // theoretical state where enabled is false despite
        // the prerequisites being met (e.g. mid-debounce).
        <p className="text-xs text-fog">Updating preview…</p>
      )}
    </div>
  );
}

function UnsupportedField({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed bg-muted/30 p-4 text-xs text-fog">
      {message}
    </div>
  );
}

function ComingSoon({ recipe }: { recipe: Recipe }) {
  return (
    <div className="flex flex-col gap-6 py-10">
      <Link
        to="/recipes"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
      >
        <ArrowLeft className="h-3 w-3" />
        All recipes
      </Link>
      <div className="luxe-shadow flex flex-col gap-3 rounded-md border border-luxe bg-card p-8">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
          Coming soon
        </span>
        <h1 className="font-display text-3xl leading-tight tracking-tight">
          {recipe.display_name}
        </h1>
        <p className="text-fog">{recipe.description}</p>
        <p className="text-sm text-fog">
          The backend supports this recipe (you can drive it via REST or the
          admin) — the SPA form lands in a later V15.x slice.
        </p>
      </div>
    </div>
  );
}

function NotFound({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-3 py-10">
      <p className="font-display text-2xl">Recipe not found</p>
      <p className="text-sm text-fog">{message}</p>
      <Button asChild variant="outline" size="sm">
        <Link to="/recipes">Back to gallery</Link>
      </Button>
    </div>
  );
}

function NoWorkspace() {
  return (
    <div className="flex flex-col items-start gap-3 py-10">
      <p className="font-display text-2xl">No workspace yet</p>
      <p className="text-sm text-fog">
        Finish account setup before creating compositions.
      </p>
    </div>
  );
}

function FormSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6 py-10">
      <div className="h-10 w-1/2 rounded bg-muted" />
      <div className="h-32 rounded bg-muted" />
      <div className="h-32 rounded bg-muted" />
    </div>
  );
}

function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const body = err.body as Record<string, unknown> | null;
    if (body) {
      // DRF returns {field: ["msg"]} or {detail: "msg"}
      if (typeof body.detail === "string") return body.detail;
      const fields = Object.entries(body).map(([k, v]) => {
        const msg = Array.isArray(v) ? v.join("; ") : String(v);
        return `${k}: ${msg}`;
      });
      if (fields.length > 0) return fields.join(" • ");
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Unknown error";
}
