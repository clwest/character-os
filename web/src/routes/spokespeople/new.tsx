import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  PortraitUpload,
  type PortraitUploadResult,
} from "@/components/portrait-upload";
import { SpokespersonWizard } from "@/components/spokesperson-wizard";
import { useMe } from "@/lib/api/workspaces";
import { useCreateSpokesperson } from "@/lib/api/spokespeople";
import { ApiError } from "@/lib/api/client";

/**
 * Create-spokesperson flow (S-06 of UI_REDESIGN_V2.md).
 *
 * Flow:
 *   1. Operator lands here from the dashboard's empty-state CTA or
 *      from the masthead "+ New" button.
 *   2. Form: name (required) + business_brief (required) + portrait
 *      (optional file upload, converted to data URI client-side).
 *   3. Submit → POST /api/spokespeople/ with the locked schema.
 *   4. Backend's SESSION 116 perform_create fires the media-engine
 *      avatar create if a portrait was supplied (synchronous in
 *      mock mode; ~20 s in real mode).
 *   5. On success: redirect to /spokespeople/{id} (SESSION 118 detail
 *      route). The mutation hook also invalidates the dashboard's
 *      spokespeople + subscription caches.
 *
 * Tier-limit (HTTP 402) shows a structured upgrade callout —
 * different from generic validation errors.
 */
const createSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required.")
    .max(120, "Name must be 120 characters or fewer."),
  business_brief: z
    .string()
    .min(8, "Give the spokesperson at least a sentence of context.")
    .max(4000, "Brief is too long. Keep it to a paragraph or two."),
});

type CreateForm = z.infer<typeof createSchema>;

interface TierLimitPayload {
  code: string;
  message: string;
  current_tier?: string;
  suggested_tier?: string | null;
  spokespeople_used?: number;
  spokespeople_limit?: number;
}

export function CreateSpokespersonRoute() {
  // SESSION 128 — wizard scaffold (slice 5) lands behind ?wizard=1.
  // Default route serves the legacy single-form so the 12 existing
  // Playwright specs stay green. Slices 6-9 fill in the wizard's
  // step bodies; when slice 9 ships, we flip the default + retire
  // the legacy form in a separate slice.
  const [searchParams] = useSearchParams();
  if (searchParams.get("wizard") === "1") {
    return <SpokespersonWizard />;
  }

  return <LegacyCreateForm />;
}

function LegacyCreateForm() {
  const navigate = useNavigate();
  const me = useMe();
  const create = useCreateSpokesperson();
  const [portrait, setPortrait] = useState<PortraitUploadResult | null>(null);

  const form = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: "", business_brief: "" },
  });

  const workspaceId = me.data?.default_workspace?.id;

  const onSubmit = form.handleSubmit(async (input) => {
    if (!workspaceId) return;
    try {
      const sp = await create.mutateAsync({
        workspace: workspaceId,
        name: input.name.trim(),
        business_brief: input.business_brief.trim(),
        portrait_data_uri: portrait?.dataUri,
      });
      navigate(`/spokespeople/${sp.id}`, { replace: true });
    } catch {
      // mutation error surfaces via create.error
    }
  });

  const tierLimit = extractTierLimit(create.error);
  const generalError = !tierLimit ? extractMessage(create.error) : null;
  const submitting = create.isPending;

  return (
    <div className="reveal flex flex-col gap-10">
      <Masthead />
      <form onSubmit={onSubmit} className="flex flex-col gap-8">
        <FieldGroup
          label="Name"
          id="name"
          hint="What this spokesperson is called inside the workspace."
          error={form.formState.errors.name?.message}
        >
          <Input
            id="name"
            type="text"
            autoComplete="off"
            placeholder="Casey, Coach Ben, The Bell Curve…"
            {...form.register("name")}
          />
        </FieldGroup>

        <FieldGroup
          label="Business brief"
          id="business_brief"
          hint="One paragraph the spokesperson speaks from. The business, the product, the audience, the tone."
          error={form.formState.errors.business_brief?.message}
        >
          <textarea
            id="business_brief"
            rows={5}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Sells artisan bicycle bells to small bike shops. Tone: warm, opinionated, just-the-facts. Audience: shop owners under 45 who care about hand-built parts."
            {...form.register("business_brief")}
          />
        </FieldGroup>

        <FieldGroup
          label="Portrait"
          id="portrait"
          hint="Optional. If supplied, a Runway avatar binds during create. Otherwise add one later from the spokesperson page."
        >
          <PortraitUpload value={portrait} onChange={setPortrait} />
        </FieldGroup>

        {tierLimit && <TierLimitCallout payload={tierLimit} />}
        {generalError && (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            {generalError}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-6">
          <Link
            to="/dashboard"
            className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          >
            Cancel
          </Link>
          <Button
            type="submit"
            size="lg"
            disabled={submitting || !workspaceId}
            data-testid="create-submit"
          >
            {submitting ? "Creating…" : "Create spokesperson"}
          </Button>
        </div>
      </form>
    </div>
  );
}

// ---- Masthead -------------------------------------------------------

function Masthead() {
  return (
    <header className="flex flex-col gap-3 border-b border-border pb-8">
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="back-to-dashboard"
      >
        <ArrowLeft className="h-3 w-3" />
        Workspace
      </Link>
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        New spokesperson
      </span>
      <h1
        className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
        style={
          {
            fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
          } as React.CSSProperties
        }
      >
        Define
        <br />
        the spokesperson.
      </h1>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
        A spokesperson is the on-camera identity the workspace renders
        videos against. Set the name + brief now; you can refine the
        portrait, voice, and other details after the row lands.
      </p>
    </header>
  );
}

// ---- Atoms ---------------------------------------------------------

function FieldGroup({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-col gap-1">
        <Label
          htmlFor={id}
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          {label}
        </Label>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function TierLimitCallout({ payload }: { payload: TierLimitPayload }) {
  return (
    <div
      className="flex flex-col gap-3 rounded-md border border-primary/40 bg-primary/5 p-5"
      data-testid="tier-limit-callout"
    >
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
          {payload.current_tier ?? "your plan"} · cap reached
        </span>
        <p className="font-display text-xl leading-snug tracking-tight">
          {payload.message}
        </p>
      </div>
      {payload.suggested_tier && (
        <p className="text-sm text-muted-foreground">
          Upgrade to <strong className="capitalize">{payload.suggested_tier}</strong> to
          add more. (Stripe wiring lands when credentials arrive.)
        </p>
      )}
    </div>
  );
}

// ---- Helpers -------------------------------------------------------

function extractTierLimit(error: unknown): TierLimitPayload | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status !== 402) return null;
  const body = error.body;
  if (
    body &&
    typeof body === "object" &&
    "code" in body &&
    typeof (body as { code: unknown }).code === "string"
  ) {
    return body as TierLimitPayload;
  }
  return null;
}

function extractMessage(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    const body = error.body as
      | { detail?: string; errors?: Array<{ message?: string }> }
      | null;
    if (body?.errors?.[0]?.message) return body.errors[0]!.message!;
    if (body?.detail) return body.detail;
    return `Request failed (${error.status}).`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Try again.";
}
