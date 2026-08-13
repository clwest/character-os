/**
 * Identity surface — SESSION 232.
 *
 * Route: /spokespeople/:id/identity
 *
 * The dedicated form for defining a spokesperson's operating rules
 * (contract rule 10; three-layer sequence body → identity →
 * knowledge). Six slots: business focus / audience / offering /
 * always-emphasize / never-say / desired felt outcome. Slot 1
 * carries over from the wizard's ``business_brief``; the other
 * five are new SESSION 232.
 *
 * Full design lock at
 * ``docs/design/CUSTOMER_JOURNEY_V1.md`` §"The spokesperson detail
 * page — where identity gets defined".
 *
 * Copy interpolates the actual spokesperson name via
 * ``interpolateSpokespersonName`` — no hardcoded "Oliver".
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  IDENTITY_FIELDS,
  interpolateSpokespersonName,
  useSpokesperson,
  useUpdateSpokesperson,
  type IdentityFieldName,
  type Spokesperson,
  type UpdateSpokespersonInput,
} from "@/lib/api/spokespeople";
import { ApiError } from "@/lib/api/client";

export function SpokespersonIdentityRoute() {
  const { id } = useParams<{ id: string }>();
  const sp = useSpokesperson(id);
  const navigate = useNavigate();

  if (sp.isLoading) return <IdentitySkeleton />;
  if (sp.isError) return <IdentityError message={extractMessage(sp.error)} />;
  if (!sp.data) return <IdentityError message="Spokesperson not found." />;

  return (
    <IdentityForm
      spokesperson={sp.data}
      onDone={() => navigate(`/spokespeople/${sp.data!.id}`)}
    />
  );
}

interface IdentityFormProps {
  spokesperson: Spokesperson;
  onDone: () => void;
}

function IdentityForm({ spokesperson, onDone }: IdentityFormProps) {
  const update = useUpdateSpokesperson();
  const [values, setValues] = useState<Record<IdentityFieldName, string>>({
    business_brief: spokesperson.business_brief ?? "",
    who_you_help: spokesperson.who_you_help ?? "",
    what_you_sell: spokesperson.what_you_sell ?? "",
    always_emphasize: spokesperson.always_emphasize ?? "",
    never_say: spokesperson.never_say ?? "",
    desired_feeling: spokesperson.desired_feeling ?? "",
  });
  const [error, setError] = useState<string | null>(null);

  const filledCount = IDENTITY_FIELDS.reduce(
    (n, f) => (values[f.name].trim().length > 0 ? n + 1 : n),
    0,
  );

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    // Send only fields that changed from the loaded row.
    const payload: UpdateSpokespersonInput = { id: spokesperson.id };
    let changed = false;
    for (const f of IDENTITY_FIELDS) {
      const current = values[f.name];
      const original = (spokesperson[f.name] ?? "") as string;
      if (current !== original) {
        payload[f.name] = current;
        changed = true;
      }
    }
    if (!changed) {
      onDone();
      return;
    }
    try {
      await update.mutateAsync(payload);
      onDone();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.body === "object" && err.body !== null
            ? JSON.stringify(err.body)
            : err.message
          : err instanceof Error
            ? err.message
            : "Save failed.",
      );
    }
  }

  const name = spokesperson.name;
  const isPending = update.isPending;

  return (
    <div className="flex flex-col gap-8" data-testid="identity-page">
      <header className="flex flex-col gap-3">
        <Link
          to={`/spokespeople/${spokesperson.id}`}
          className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
          data-testid="identity-back"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to {name}
        </Link>
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <div className="flex flex-col gap-2">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
              § — Identity
            </span>
            <h1
              className="font-display text-4xl leading-[0.95] tracking-tight text-cream md:text-5xl"
              data-testid="identity-heading"
            >
              Define {name}
            </h1>
          </div>
          <span
            className="inline-flex items-center gap-2 rounded-sm border border-border bg-muted px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-fog"
            data-testid="identity-progress"
          >
            <span className="text-fog/70">Filled</span>
            <span className="text-foreground">
              {filledCount} of {IDENTITY_FIELDS.length}
            </span>
          </span>
        </div>
        <p className="max-w-2xl text-sm text-fog">
          This is who {name} is — what shapes everything they say and
          do. You can update it any time.
        </p>
      </header>

      <form onSubmit={handleSave} className="flex flex-col gap-8">
        {IDENTITY_FIELDS.map((f) => {
          const label = interpolateSpokespersonName(f.label, name);
          const help = interpolateSpokespersonName(f.help, name);
          return (
            <div
              key={f.name}
              className="flex flex-col gap-2"
              data-testid={`identity-field-${f.name}`}
            >
              <Label htmlFor={`identity-${f.name}`} className="text-base">
                {label}
              </Label>
              <p className="text-xs text-fog">{help}</p>
              <textarea
                id={`identity-${f.name}`}
                value={values[f.name]}
                onChange={(e) =>
                  setValues((v) => ({ ...v, [f.name]: e.target.value }))
                }
                rows={4}
                disabled={isPending}
                placeholder={f.placeholder}
                maxLength={2000}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                data-testid={`identity-input-${f.name}`}
              />
            </div>
          );
        })}

        {error && (
          <div
            className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive"
            data-testid="identity-error"
          >
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 border-t border-luxe pt-4">
          <Link to={`/spokespeople/${spokesperson.id}`}>
            <Button
              type="button"
              variant="ghost"
              disabled={isPending}
              data-testid="identity-cancel"
            >
              Cancel
            </Button>
          </Link>
          <Button
            type="submit"
            disabled={isPending}
            data-testid="identity-save"
          >
            {isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <Save className="mr-1 h-4 w-4" />
                Save
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

function IdentitySkeleton() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3 border-b border-luxe pb-6">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-10 w-64 rounded bg-muted" />
      </div>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-4 w-40 rounded bg-muted" />
          <div className="h-3 w-64 rounded bg-muted/70" />
          <div className="h-24 w-full rounded bg-muted/50" />
        </div>
      ))}
    </div>
  );
}

function IdentityError({ message }: { message: string }) {
  return (
    <div className="flex flex-col gap-6 py-12 text-center">
      <p className="font-display text-3xl tracking-tight">{message}</p>
      <div className="mx-auto">
        <Link to="/dashboard">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-1 h-3 w-3" /> Back to workspace
          </Button>
        </Link>
      </div>
    </div>
  );
}

function extractMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Something went wrong loading this spokesperson.";
}
