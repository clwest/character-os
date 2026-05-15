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
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  LIVE_RECIPE_KINDS,
  type Recipe,
  type RecipeField,
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
          />
        ))}

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
}: {
  field: RecipeField;
  value: unknown;
  onChange: (value: unknown) => void;
  spokespeople: Spokesperson[];
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
}: {
  id: string;
  field: RecipeField;
  value: unknown;
  onChange: (value: unknown) => void;
  spokespeople: Spokesperson[];
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
        <UnsupportedField
          message={`Asset picker (${field.asset_type}) ships in V15.2.`}
        />
      );
    case "dialogue_lines":
      return (
        <UnsupportedField message="Dialogue line builder ships in V15.4." />
      );
    default:
      return <UnsupportedField message={`Unknown field type`} />;
  }
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
