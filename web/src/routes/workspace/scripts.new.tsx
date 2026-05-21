/**
 * /workspace/scripts/new — Draft a new auto-script.
 *
 * SESSION B2.5. Form fields:
 *   1. Spokesperson picker (useSpokespeople)
 *   2. Name (text, optional — backend defaults to "Untitled script")
 *   3. Prompt (textarea, required, 1-4000 chars)
 *   4. Opener pin (text, optional, ≤280 chars)
 *   5. Verifier mode (select)
 *
 * On success → navigate to /workspace/scripts/<id>.
 * 402 → tier exhaustion inline error with detail from server payload.
 *
 * Scope: docs/design/AUTO_SCRIPT_V1.md §B2.5.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  FileText,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useCreateScript, type VerifierMode } from "@/lib/api/scripts";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- Verifier mode options --------------------------------------

const VERIFIER_MODE_OPTIONS: Array<{ value: VerifierMode; label: string; hint: string }> = [
  { value: "", label: "Default (warn)", hint: "K6.4 flags unsupported claims but doesn't block." },
  { value: "strict", label: "Strict", hint: "K6.4 blocks the draft if any claim is unsupported." },
  { value: "warn", label: "Warn", hint: "K6.4 flags claims with inline warnings only." },
  { value: "off", label: "Off", hint: "Skip K6.4 verification entirely." },
];

// ---- Page component ---------------------------------------------

export function ScriptNewRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const spokespeople = useSpokespeople();
  const workspaceSpokespeople = (spokespeople.data ?? []).filter(
    (s) => !workspaceId || s.workspace === workspaceId,
  );

  const create = useCreateScript();

  // ---- Form state
  const [spokespersonId, setSpokespersonId] = useState("");
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [opener, setOpener] = useState("");
  const [verifierMode, setVerifierMode] = useState<VerifierMode>("");
  const [showErrors, setShowErrors] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ---- Validation
  const spokespersonError =
    spokespersonId.trim() === "" ? "Select a spokesperson." : null;
  const promptError =
    prompt.trim() === ""
      ? "Prompt is required."
      : prompt.length > 4000
        ? "Prompt must be 4000 characters or fewer."
        : null;
  const openerError =
    opener.length > 280 ? "Opening line must be 280 characters or fewer." : null;

  const hasErrors = Boolean(spokespersonError || promptError || openerError);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setShowErrors(true);
    if (hasErrors) return;

    setSubmitError(null);
    try {
      const script = await create.mutateAsync({
        spokesperson_id: spokespersonId,
        name: name.trim() || undefined,
        prompt: prompt.trim(),
        opener: opener.trim() || undefined,
        verifier_mode: verifierMode || undefined,
      });
      navigate(`/workspace/scripts/${script.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as Record<string, unknown> | null;

        // 402 = tier exhaustion — show actionable message
        if (err.status === 402) {
          const detail =
            typeof body?.detail === "string"
              ? body.detail
              : "You've reached your monthly script drafts limit. Upgrade your plan to draft more.";
          setSubmitError(detail);
          return;
        }

        // 404 = cross-workspace or unknown spokesperson
        if (err.status === 404) {
          setSubmitError(
            "Spokesperson not found in this workspace. Refresh and try again.",
          );
          return;
        }

        const detailMsg =
          typeof body?.detail === "string" ? body.detail : null;
        setSubmitError(
          detailMsg ?? err.message ?? "Submission failed — check your inputs.",
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
        to="/workspace/scripts"
        data-testid="back-to-scripts"
        className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Scripts
      </Link>

      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-fog" />
          <h1
            data-testid="script-new-title"
            className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
          >
            New script
          </h1>
        </div>
        <p className="text-base text-mist">
          Describe what your spokesperson should say. K2 retrieves relevant
          knowledge, gpt-5 drafts the script, and K6.4 verifies every claim
          before you approve.
        </p>
      </header>

      {/* ---- Form ---------------------------------------------- */}
      <form
        data-testid="script-create-form"
        onSubmit={(e) => void handleSubmit(e)}
        className="flex flex-col gap-6 rounded-md border border-luxe bg-card p-6"
        noValidate
      >
        {/* Spokesperson picker */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="script-spokesperson" className="text-sm font-medium">
            Spokesperson <span className="text-destructive">*</span>
          </label>
          <p className="text-xs text-fog">
            Who will deliver this script? K2 retrieves knowledge scoped to
            this spokesperson's workspace.
          </p>
          {spokespeople.isLoading ? (
            <div
              data-testid="spokesperson-picker-loading"
              className="h-10 rounded-md bg-muted animate-pulse"
            />
          ) : workspaceSpokespeople.length === 0 ? (
            <div className="rounded-md border border-dashed border-luxe p-4 text-sm text-fog">
              No spokespeople in this workspace.{" "}
              <Link
                to="/spokespeople/new"
                className="text-primary underline underline-offset-2"
              >
                Create one first
              </Link>
              .
            </div>
          ) : (
            <select
              id="script-spokesperson"
              data-testid="script-spokesperson-select"
              value={spokespersonId}
              onChange={(e) => setSpokespersonId(e.target.value)}
              disabled={create.isPending}
              className={cn(
                "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50",
                showErrors && spokespersonError && "border-destructive",
              )}
            >
              <option value="">— select spokesperson —</option>
              {workspaceSpokespeople.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.runway_avatar_id === "" ? " (no avatar)" : ""}
                </option>
              ))}
            </select>
          )}
          {showErrors && spokespersonError && (
            <p
              data-testid="script-spokesperson-error"
              className="text-xs text-destructive"
            >
              {spokespersonError}
            </p>
          )}
        </div>

        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="script-name" className="text-sm font-medium">
            Script name{" "}
            <span className="text-fog font-normal">(optional)</span>
          </label>
          <Input
            id="script-name"
            data-testid="script-name-input"
            type="text"
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Spring launch — product benefits"
            disabled={create.isPending}
          />
          <p className="text-[11px] text-fog">
            Leave blank for "Untitled script". {name.length} / 200
          </p>
        </div>

        {/* Prompt */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="script-prompt" className="text-sm font-medium">
            What should the avatar talk about?{" "}
            <span className="text-destructive">*</span>
          </label>
          <p className="text-xs text-fog">
            This is your brief to the LLM. K2 retrieves matching knowledge
            chunks; gpt-5 synthesizes them into a full script. 1–4000 chars.
          </p>
          <textarea
            id="script-prompt"
            data-testid="script-prompt-textarea"
            rows={5}
            maxLength={4000}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="60-second product demo covering the three core features, focused on ease of use for small teams…"
            disabled={create.isPending}
            className={cn(
              "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-fog focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50",
              showErrors && promptError && "border-destructive",
            )}
          />
          {showErrors && promptError && (
            <p
              data-testid="script-prompt-error"
              className="text-xs text-destructive"
            >
              {promptError}
            </p>
          )}
          <p className="text-[11px] text-fog">
            {prompt.length} / 4000
          </p>
        </div>

        {/* Opener pin */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="script-opener" className="text-sm font-medium">
            Pin the opening line{" "}
            <span className="text-fog font-normal">(optional)</span>
          </label>
          <p className="text-xs text-fog">
            K6.6: verbatim first line for the avatar to say. Leave blank and
            gpt-5 will open naturally from the brief.
          </p>
          <Input
            id="script-opener"
            data-testid="script-opener-input"
            type="text"
            maxLength={280}
            value={opener}
            onChange={(e) => setOpener(e.target.value)}
            placeholder="Hey, I'm Sasha — and today I want to talk about something big…"
            disabled={create.isPending}
            className={cn(
              showErrors && openerError && "border-destructive",
            )}
          />
          {showErrors && openerError && (
            <p
              data-testid="script-opener-error"
              className="text-xs text-destructive"
            >
              {openerError}
            </p>
          )}
          <p className="text-[11px] text-fog">
            {opener.length} / 280
          </p>
        </div>

        {/* Verifier mode */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="script-verifier-mode"
            className="text-sm font-medium"
          >
            K6.4 verifier mode{" "}
            <span className="text-fog font-normal">(optional)</span>
          </label>
          <p className="text-xs text-fog">
            Controls how the K6.4 fact-verifier handles unsupported claims in
            the draft.
          </p>
          <select
            id="script-verifier-mode"
            data-testid="script-verifier-mode-select"
            value={verifierMode}
            onChange={(e) => setVerifierMode(e.target.value as VerifierMode)}
            disabled={create.isPending}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
          >
            {VERIFIER_MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {/* Mode hint */}
          {verifierMode !== undefined && (
            <p className="text-[11px] text-fog">
              {
                VERIFIER_MODE_OPTIONS.find((o) => o.value === verifierMode)
                  ?.hint
              }
            </p>
          )}
        </div>

        {/* Submission error */}
        {submitError && (
          <div
            data-testid="script-submit-error"
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
            data-testid="script-create-submit"
            disabled={
              create.isPending ||
              spokespeople.isLoading ||
              workspaceSpokespeople.length === 0
            }
          >
            {create.isPending ? (
              <>
                <Loader2
                  data-testid="script-create-spinner"
                  className="mr-2 h-4 w-4 animate-spin"
                />
                Drafting…
              </>
            ) : (
              "Draft script"
            )}
          </Button>
          <Button
            asChild
            type="button"
            variant="ghost"
            disabled={create.isPending}
          >
            <Link to="/workspace/scripts">Cancel</Link>
          </Button>
        </div>

        {/* Processing hint */}
        {create.isPending && (
          <p
            data-testid="script-drafting-hint"
            className="text-xs text-fog"
          >
            K2 is retrieving knowledge and gpt-5 is synthesizing your script.
            This usually takes 5–15 seconds.
          </p>
        )}
      </form>
    </div>
  );
}
