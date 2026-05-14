import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSpokesperson } from "@/lib/api/spokespeople";
import { useCreateVideo } from "@/lib/api/videos";
import { ApiError } from "@/lib/api/client";

/**
 * Make-a-video form (S-12 of UI_REDESIGN_V2.md).
 *
 * Routes from the spokesperson detail page's "Make a video"
 * CTA. Fires POST /api/videos/ which:
 *   1. Validates the spokesperson belongs to the user's workspace.
 *   2. Persists the Video row with status="rendering" +
 *      media_engine_task_id.
 *   3. Enqueues the SESSION 109 Celery polling task.
 *
 * On success: redirect to /videos/{id} (the canonical async
 * polling surface). Failures stay on this page so the operator
 * can amend the brief.
 *
 * The kind picker is hidden for v1 — locked to `spokesperson_ad`
 * (the only kind backend ships in SESSION 109). Other kinds land
 * in subsequent slices and grow this form into a kind-discriminated
 * tabbed layout.
 */
const renderSchema = z.object({
  title: z
    .string()
    .max(200, "Title is too long. Keep it under 200 chars.")
    .optional(),
  brief: z
    .string()
    .min(8, "Give the spokesperson at least a sentence to work with.")
    .max(4000, "Brief is too long. Keep it to a paragraph or two."),
});

type RenderForm = z.infer<typeof renderSchema>;

interface TierLimitPayload {
  code: string;
  message: string;
  current_tier?: string;
  suggested_tier?: string | null;
  videos_used?: number;
  videos_limit?: number;
}

export function MakeVideoRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const spokesperson = useSpokesperson(id);
  const create = useCreateVideo();

  const form = useForm<RenderForm>({
    resolver: zodResolver(renderSchema),
    defaultValues: { title: "", brief: "" },
  });

  // Pre-fill the brief from the spokesperson's business_brief once
  // the data lands. We don't lock the field — operators often want
  // to riff per-video off the base brief.
  useEffect(() => {
    if (spokesperson.data && !form.getValues("brief")) {
      form.setValue("brief", spokesperson.data.business_brief);
    }
  }, [spokesperson.data, form]);

  if (spokesperson.isLoading) {
    return <FormSkeleton />;
  }
  if (spokesperson.isError || !spokesperson.data) {
    return (
      <div className="flex flex-col gap-6 py-12 text-center">
        <p className="font-display text-3xl tracking-tight">
          Spokesperson not found.
        </p>
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

  const sp = spokesperson.data;

  const onSubmit = form.handleSubmit(async (input) => {
    try {
      const video = await create.mutateAsync({
        spokesperson: sp.id,
        title: input.title?.trim() || undefined,
        brief: input.brief.trim(),
        kind: "spokesperson_ad",
      });
      navigate(`/videos/${video.id}`, { replace: true });
    } catch {
      // surfaces via create.error
    }
  });

  const tierLimit = extractTierLimit(create.error);
  const generalError = !tierLimit ? extractMessage(create.error) : null;
  const submitting = create.isPending;
  const avatarReady = sp.runway_avatar_id !== "";

  return (
    <div className="reveal flex flex-col gap-10">
      <Masthead spokespersonName={sp.name} spokespersonId={sp.id} />

      {!avatarReady && <AvatarNotReadyCallout spokespersonId={sp.id} />}

      <form onSubmit={onSubmit} className="flex flex-col gap-8">
        <FieldGroup
          label="Title"
          id="title"
          hint="Optional. A short name to find this video later — defaults to the brief if empty."
          error={form.formState.errors.title?.message}
        >
          <Input
            id="title"
            type="text"
            autoComplete="off"
            placeholder="Black Friday sale, Spring launch, ..."
            {...form.register("title")}
          />
        </FieldGroup>

        <FieldGroup
          label="Brief"
          id="brief"
          hint="What this spokesperson says. Pre-filled from their default brief — edit per video."
          error={form.formState.errors.brief?.message}
        >
          <textarea
            id="brief"
            rows={6}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            {...form.register("brief")}
          />
        </FieldGroup>

        {tierLimit && <TierLimitCallout payload={tierLimit} />}
        {generalError && (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            {generalError}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-6">
          <Link
            to={`/spokespeople/${sp.id}`}
            className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          >
            Cancel
          </Link>
          <Button
            type="submit"
            size="lg"
            disabled={submitting || !avatarReady}
            data-testid="render-submit"
          >
            {submitting ? "Firing render…" : "Make a video"}
          </Button>
        </div>
      </form>
    </div>
  );
}

// ---- Sections ------------------------------------------------------

function Masthead({
  spokespersonName,
  spokespersonId,
}: {
  spokespersonName: string;
  spokespersonId: string;
}) {
  return (
    <header className="flex flex-col gap-3 border-b border-border pb-8">
      <Link
        to={`/spokespeople/${spokespersonId}`}
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="back-to-spokesperson"
      >
        <ArrowLeft className="h-3 w-3" />
        {spokespersonName}
      </Link>
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        Render
      </span>
      <h1
        className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
        style={
          {
            fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
          } as React.CSSProperties
        }
      >
        Make a video
        <br />
        <span className="text-muted-foreground">with {spokespersonName}.</span>
      </h1>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
        Type the brief; the spokesperson says it. Mock mode renders in
        ~13 s; real-mode Runway calls run 60–120 s. You'll watch the
        status on the next page.
      </p>
    </header>
  );
}

function AvatarNotReadyCallout({ spokespersonId }: { spokespersonId: string }) {
  return (
    <div
      className="rounded-md border border-primary/40 bg-primary/5 p-5"
      data-testid="avatar-not-ready"
    >
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
          Avatar not bound
        </span>
        <p className="font-display text-xl leading-snug tracking-tight">
          This spokesperson doesn't have an avatar yet.
        </p>
        <p className="text-sm text-muted-foreground">
          Add a portrait on the{" "}
          <Link
            to={`/spokespeople/${spokespersonId}`}
            className="underline underline-offset-2 hover:text-foreground"
          >
            spokesperson page
          </Link>{" "}
          first — the video render needs a Runway avatar to drive.
        </p>
      </div>
    </div>
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
          Upgrade to <strong className="capitalize">{payload.suggested_tier}</strong> for
          more renders this period.
        </p>
      )}
    </div>
  );
}

function FormSkeleton() {
  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-3 border-b border-border pb-8">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-14 w-2/3 rounded bg-muted" />
      </div>
      {Array.from({ length: 2 }).map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-3 w-32 rounded bg-muted" />
          <div className="h-10 w-full rounded bg-muted" />
        </div>
      ))}
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
