/**
 * Per-recipe form — drives ``POST /api/compositions/``.
 *
 * V15.1 handles five field types (text / textarea / checkbox /
 * select / number) + spokesperson_picker, which covers the three
 * recipes in ``LIVE_RECIPE_KINDS``. asset_picker (V15.2-V15.3)
 * and dialogue_lines (V15.4) come later — coming-soon recipes
 * short-circuit with a placeholder.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
import { ApiError } from "@/lib/api/client";

type FormState = Record<string, unknown>;

export function RecipeFormRoute() {
  const { kind } = useParams<{ kind: string }>();
  const recipe = useRecipe(kind);
  const me = useMe();
  const spokespeople = useSpokespeople();
  const create = useCreateComposition();
  const navigate = useNavigate();

  const [form, setForm] = useState<FormState>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (recipe.isLoading || me.isLoading) {
    return <FormSkeleton />;
  }
  if (recipe.isError || !recipe.data) {
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

  const r = recipe.data;
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

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const params: Record<string, unknown> = {};
    for (const field of r.fields) {
      const v = form[field.name];
      if (v === undefined || v === "" || v === null) {
        if (field.required && field.default === undefined) {
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
      });
      navigate(`/compositions/${comp.id}`, { replace: true });
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-8 py-10">
      <Header recipe={r} />
      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-6"
        data-testid={`recipe-form-${r.kind}`}
      >
        {r.fields.map((field) => (
          <FieldRenderer
            key={field.name}
            field={field}
            value={form[field.name]}
            onChange={(value) => handleChange(field.name, value)}
            spokespeople={workspaceSpokespeople}
            workspaceId={workspaceId}
          />
        ))}
        {assetTypesNeeded.length > 0 && (
          <AssetHint types={assetTypesNeeded} workspaceId={workspaceId} />
        )}

        {submitError && (
          <div
            className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
            data-testid="recipe-submit-error"
          >
            {submitError}
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-6">
          <Link
            to="/recipes"
            className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          >
            Cancel
          </Link>
          <Button
            type="submit"
            size="lg"
            disabled={create.isPending}
            data-testid="recipe-submit"
          >
            {create.isPending ? "Starting render…" : "Run composition"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function Header({ recipe }: { recipe: Recipe }) {
  return (
    <header className="flex flex-col gap-3 border-b pb-6">
      <Link
        to="/recipes"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        All recipes
      </Link>
      <h1 className="font-display text-3xl leading-tight tracking-tight md:text-4xl">
        {recipe.display_name}
      </h1>
      <p className="max-w-2xl text-muted-foreground">{recipe.description}</p>
    </header>
  );
}

function FieldRenderer({
  field,
  value,
  onChange,
  spokespeople,
  workspaceId,
}: {
  field: RecipeField;
  value: unknown;
  onChange: (value: unknown) => void;
  spokespeople: Spokesperson[];
  workspaceId: string;
}) {
  const id = `field-${field.name}`;

  return (
    <div className="flex flex-col gap-2" data-testid={`recipe-field-${field.name}`}>
      <div className="flex flex-col gap-1">
        <Label
          htmlFor={id}
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          {field.label}
          {!field.required && <span className="ml-2 normal-case tracking-normal text-muted-foreground/60">(optional)</span>}
        </Label>
        {field.help_text && (
          <p className="text-xs text-muted-foreground">{field.help_text}</p>
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
    </div>
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
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
          <span className="text-muted-foreground">Enable</span>
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
    default:
      return <UnsupportedField message={`Unknown field type`} />;
  }
}

function AssetPicker({
  id,
  assetType,
  workspaceId,
  value,
  onChange,
  required,
}: {
  id: string;
  assetType: AssetListItem["asset_type"];
  workspaceId: string;
  value: string | undefined;
  onChange: (value: string) => void;
  required: boolean;
}) {
  const assets = useAssets({ workspace: workspaceId, assetType });

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
      <div className="flex flex-col gap-1 rounded-md border border-dashed bg-muted/20 p-4 text-xs text-muted-foreground">
        <p className="font-mono uppercase tracking-[0.22em]">
          No {assetType} assets yet
        </p>
        <p className="normal-case tracking-normal">
          Run a recipe that produces a {assetType} first (e.g. a
          {assetType === "clip" ? " talking head or cinematic visual" : ""}
          {assetType === "audio" ? " voice design" : ""}), then come back here
          to use it as input.
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

function assetLabel(a: AssetListItem): string {
  const seconds = a.duration_ms != null ? ` · ${(a.duration_ms / 1000).toFixed(1)}s` : "";
  const filename = a.file_path.split("/").pop() || a.file_path;
  const trimmedName = filename.length > 40 ? `${filename.slice(0, 37)}…` : filename;
  return `${trimmedName}${seconds}`;
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
    <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-4 text-xs text-amber-800 dark:text-amber-300">
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
      <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-4 text-xs text-amber-800 dark:text-amber-300">
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
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Line {idx + 1}
            </span>
            <button
              type="button"
              onClick={() => removeLine(idx)}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-destructive"
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
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            data-testid={`dialogue-line-text-${idx}`}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={addLine}
        className="inline-flex w-fit items-center gap-1.5 rounded-md border border-dashed px-3 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:border-foreground hover:text-foreground"
        data-testid="dialogue-line-add"
      >
        <Plus className="h-3 w-3" />
        Add line
      </button>
    </div>
  );
}

function UnsupportedField({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-dashed bg-muted/30 p-4 text-xs text-muted-foreground">
      {message}
    </div>
  );
}

function ComingSoon({ recipe }: { recipe: Recipe }) {
  return (
    <div className="flex flex-col gap-6 py-10">
      <Link
        to="/recipes"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        All recipes
      </Link>
      <div className="flex flex-col gap-3 rounded-md border bg-card p-8 shadow-paper">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Coming soon
        </span>
        <h1 className="font-display text-3xl leading-tight tracking-tight">
          {recipe.display_name}
        </h1>
        <p className="text-muted-foreground">{recipe.description}</p>
        <p className="text-sm text-muted-foreground">
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
      <p className="text-sm text-muted-foreground">{message}</p>
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
      <p className="text-sm text-muted-foreground">
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
