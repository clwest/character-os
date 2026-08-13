/**
 * /workspace/campaigns/new — Create a new personalized campaign.
 *
 * SESSION B3.7. Two-field form: metadata (name + spokesperson +
 * template). On success → navigate to the campaign detail page
 * where the operator pastes their CSV.
 *
 * SESSION BC4. Added "Start from an approved script (optional)"
 * Script picker section above the template textarea. Resolves
 * Q-bc-4, Q-bc-5, Q-bc-8 as-proposed.
 *
 * Scope: docs/design/PERSONALIZED_VIDEO_V1.md §B3.7.
 *       docs/design/B2_B3_COMPOSITION_V1.md §BC4.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, Loader2, AlertCircle, X, Link2Off } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useCreateCampaign, parsePlaceholders } from "@/lib/api/campaigns";
import { useScripts, verificationStatusTone, verificationStatusLabel, type ScriptListItem } from "@/lib/api/scripts";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- VerificationBadge (inline — mirrors scripts.tsx) --------

function VerificationBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  label: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-luxe bg-muted text-fog",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- ScriptPickerSection ------------------------------------

/**
 * Optional Script picker shown above the template textarea.
 *
 * Q-bc-4: filters by spokesperson by default; "Show all workspace
 * scripts" toggle drops the spokesperson filter.
 * Q-bc-5: no warning when operator edits the copied template.
 * Q-bc-8: "Use this draft as starting template" copies draft_text
 *         verbatim into the textarea (no placeholder injection).
 * Q-bc-3: annotated inline — source_script link is fixed post-create.
 */
function ScriptPickerSection({
  workspaceId,
  spokespersonId,
  pickedScript,
  onPick,
  onUnlink,
  onUseAsTemplate,
  disabled,
}: {
  workspaceId: string;
  spokespersonId: string;
  pickedScript: ScriptListItem | null;
  onPick: (script: ScriptListItem) => void;
  onUnlink: () => void;
  onUseAsTemplate: (draftText: string) => void;
  disabled: boolean;
}) {
  const [showAll, setShowAll] = useState(false);

  // Filter: spokesperson + ready by default; all-workspace toggle drops the sp filter.
  const filters = {
    status: "ready" as const,
    ...(showAll ? {} : { spokesperson: spokespersonId }),
  };

  const scripts = useScripts(workspaceId || undefined, filters);
  const scriptList = scripts.data ?? [];

  return (
    <div
      data-testid="script-picker-section"
      className="flex flex-col gap-3 rounded-md border border-luxe bg-muted/20 p-4"
    >
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex flex-col gap-0.5">
          <p className="text-sm font-medium">
            Start from an approved script{" "}
            <span className="text-fog font-normal">(optional)</span>
          </p>
          <p className="text-[11px] text-fog">
            Picks an approved Script as the starting template + links knowledge
            lineage to every per-recipient render.
          </p>
        </div>
      </div>

      {/* Spokesperson-filter toggle */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="script-picker-show-all-toggle"
          onClick={() => setShowAll((v) => !v)}
          disabled={disabled}
          className={cn(
            "text-[11px] underline underline-offset-2 text-fog hover:text-gold",
            showAll && "text-primary",
          )}
        >
          {showAll
            ? "Show only this spokesperson's scripts"
            : "Show all workspace scripts"}
        </button>
      </div>

      {/* Script select */}
      {scripts.isLoading ? (
        <div className="h-9 rounded-md bg-muted animate-pulse" data-testid="script-picker-loading" />
      ) : scriptList.length === 0 ? (
        <div
          data-testid="script-picker-empty"
          className="rounded-md border border-dashed border-luxe p-3 text-center"
        >
          <p className="text-xs text-fog">
            No approved scripts yet —{" "}
            <Link
              to="/workspace/scripts/new"
              className="text-primary underline-offset-2 hover:underline"
            >
              draft one at /workspace/scripts/new
            </Link>
          </p>
        </div>
      ) : (
        <select
          data-testid="script-picker-select"
          value={pickedScript?.id ?? ""}
          onChange={(e) => {
            const found = scriptList.find((s) => s.id === e.target.value);
            if (found) onPick(found);
          }}
          disabled={disabled}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors",
            "placeholder:text-fog focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          <option value="">— Pick a script —</option>
          {scriptList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name || "Untitled script"} ({s.spokesperson_name})
            </option>
          ))}
        </select>
      )}

      {/* Picked script preview card */}
      {pickedScript && (
        <ScriptPreviewCard
          script={pickedScript}
          onUnlink={onUnlink}
          onUseAsTemplate={onUseAsTemplate}
          disabled={disabled}
        />
      )}

      {/* Q-bc-3 immutability hint */}
      <p className="text-[11px] text-fog">
        Once you create the campaign, the Script link is fixed. To change it,
        create a new campaign.
      </p>
    </div>
  );
}

// ---- ScriptPreviewCard --------------------------------------

function ScriptPreviewCard({
  script,
  onUnlink,
  onUseAsTemplate,
  disabled,
}: {
  script: ScriptListItem;
  onUnlink: () => void;
  onUseAsTemplate: (draftText: string) => void;
  disabled: boolean;
}) {
  const vTone = verificationStatusTone(script.verification_status);
  const vLabel = verificationStatusLabel(script.verification_status);
  const preview = script.draft_text
    ? script.draft_text.slice(0, 200) + (script.draft_text.length > 200 ? "…" : "")
    : "";

  return (
    <div
      data-testid={`script-preview-card-${script.id}`}
      className="rounded-md border border-luxe bg-card p-4 flex flex-col gap-3"
    >
      {/* Header row: name + badges + unlink */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex flex-col gap-1 min-w-0">
          <p
            data-testid="script-preview-name"
            className="text-sm font-medium truncate"
          >
            {script.name || "Untitled script"}
          </p>
          <div className="flex items-center gap-1.5 flex-wrap">
            {script.verification_status !== "" && (
              <VerificationBadge tone={vTone} label={vLabel} />
            )}
            <span className="text-[10px] text-fog">
              {script.knowledge_chunk_count} chunk
              {script.knowledge_chunk_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
        <button
          type="button"
          data-testid="script-picker-unlink"
          onClick={onUnlink}
          disabled={disabled}
          title="Unlink script — author template free-form instead"
          className="text-fog hover:text-gold shrink-0"
        >
          <Link2Off className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Draft preview */}
      {preview && (
        <pre
          data-testid="script-preview-draft"
          className="whitespace-pre-wrap font-mono text-[11px] text-fog bg-muted/30 rounded-md p-2 max-h-28 overflow-y-auto border border-luxe"
        >
          {preview}
        </pre>
      )}

      {/* "Use this draft as starting template" — Q-bc-8: copies verbatim */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        data-testid="script-use-as-template-btn"
        disabled={disabled || !script.draft_text}
        onClick={() => onUseAsTemplate(script.draft_text)}
        className="w-fit text-xs gap-1.5"
      >
        Use this draft as starting template
      </Button>

      {/* Derived-from annotation — shown after "Use" was clicked (handled by parent) */}
    </div>
  );
}

// ---- Page component -----------------------------------------

export function CampaignNewRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id ?? "";

  const spokespeople = useSpokespeople();
  const spList = spokespeople.data ?? [];

  const create = useCreateCampaign();

  // ---- Form state
  const [name, setName] = useState("");
  const [spokespersonId, setSpokespersonId] = useState("");
  const [template, setTemplate] = useState("");

  // BC4: Script picker state
  const [pickedScript, setPickedScript] = useState<ScriptListItem | null>(null);
  const [sourceScriptId, setSourceScriptId] = useState<string | undefined>(undefined);

  // Pick the first spokesperson by default when the list loads.
  useEffect(() => {
    if (!spokespersonId && spList.length > 0) {
      setSpokespersonId(spList[0]!.id);
    }
  }, [spList, spokespersonId]);

  // When spokesperson changes, clear the picked script to avoid cross-sp confusion
  // (the picker will re-filter by default; operator can toggle "show all" again).
  function handleSpokespersonChange(newId: string) {
    setSpokespersonId(newId);
    setPickedScript(null);
    setSourceScriptId(undefined);
  }

  // BC4: "Use this draft as starting template" — Q-bc-8: verbatim copy
  function handleUseAsTemplate(draftText: string) {
    setTemplate(draftText);
    // sourceScriptId stays set — this is the FK kept in the create payload
  }

  // BC4: unlink clears the source script state; operator can author free-form
  function handleUnlinkScript() {
    setPickedScript(null);
    setSourceScriptId(undefined);
  }

  // BC4: picking a script sets the preview card + FK; does NOT auto-copy template
  function handlePickScript(script: ScriptListItem) {
    setPickedScript(script);
    setSourceScriptId(script.id);
  }

  // Client-side placeholder preview — purely advisory.
  const detectedVars = parsePlaceholders(template);

  const [submitError, setSubmitError] = useState<string | null>(null);

  // ---- Validation
  // BC4: template is now optional when source_script_id is set. If neither
  // is set, the backend will 400 — surface that inline via submitError.
  const nameError = name.trim().length === 0 ? "Name is required." : null;
  const spError = spokespersonId.trim() === "" ? "Spokesperson is required." : null;
  // Only require template in the UI if no script is linked.
  const templateRequired = !sourceScriptId && template.trim().length === 0;
  const templateError = templateRequired ? "Template is required (or pick an approved script above)." : null;

  const [showErrors, setShowErrors] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setShowErrors(true);
    if (nameError || spError || templateError) return;

    setSubmitError(null);
    try {
      const campaign = await create.mutateAsync({
        workspace_id: workspaceId,
        spokesperson_id: spokespersonId,
        name: name.trim(),
        template: template || undefined,
        source_script_id: sourceScriptId,
      });
      navigate(`/workspace/campaigns/${campaign.id}`);
    } catch (err) {
      // Surface backend 400 inline.
      if (err instanceof ApiError && err.status === 400) {
        const body = err.body as Record<string, unknown> | null;
        const templateMsg =
          body?.template != null
            ? String(Array.isArray(body.template) ? body.template[0] : body.template)
            : null;
        const detailMsg = body?.detail != null ? String(body.detail) : null;

        // BC4: source_script_not_ready — defensive (picker only shows READY scripts,
        // but server could reject if the Script was just archived in another tab).
        const code = typeof body?.code === "string" ? body.code : null;
        if (code === "source_script_not_ready") {
          setSubmitError(
            "This script isn't approved — only READY or RENDERED scripts can ground a campaign.",
          );
        } else if (detailMsg?.includes("not found")) {
          setSubmitError("Script not available in this workspace.");
        } else {
          setSubmitError(
            templateMsg ?? detailMsg ?? "Submission failed — check your inputs.",
          );
        }
      } else if (err instanceof ApiError && err.status === 404) {
        setSubmitError("Script not available in this workspace.");
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
        to="/workspace/campaigns"
        data-testid="back-to-campaigns"
        className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Campaigns
      </Link>

      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-2">
        <h1
          data-testid="campaign-new-title"
          className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
        >
          New campaign
        </h1>
        <p className="text-base text-mist">
          Define the campaign name, pick a spokesperson, and write your script
          template. Use <code className="rounded-sm border border-luxe bg-muted px-1 py-0.5 font-mono text-[11px]">{"{first_name}"}</code>-style
          placeholders — you&apos;ll paste your CSV next.
        </p>
      </header>

      {/* ---- Form ----------------------------------------------- */}
      <form
        data-testid="campaign-create-form"
        onSubmit={(e) => void handleSubmit(e)}
        className="flex flex-col gap-6 rounded-md border border-luxe bg-card p-6"
        noValidate
      >
        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="campaign-name"
            className="text-sm font-medium"
          >
            Campaign name <span className="text-destructive">*</span>
          </label>
          <Input
            id="campaign-name"
            data-testid="campaign-name-input"
            type="text"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Q3 outreach — enterprise prospects"
            disabled={create.isPending}
            className={cn(
              showErrors && nameError && "border-destructive ring-destructive",
            )}
          />
          {showErrors && nameError && (
            <p
              data-testid="campaign-name-error"
              className="text-xs text-destructive"
            >
              {nameError}
            </p>
          )}
          <p className="text-[11px] text-fog">
            {name.length} / 120
          </p>
        </div>

        {/* Spokesperson picker */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="campaign-spokesperson"
            className="text-sm font-medium"
          >
            Spokesperson <span className="text-destructive">*</span>
          </label>
          {spokespeople.isLoading ? (
            <div
              data-testid="spokesperson-loading"
              className="h-9 rounded-md bg-muted animate-pulse"
            />
          ) : (
            <select
              id="campaign-spokesperson"
              data-testid="campaign-spokesperson-select"
              value={spokespersonId}
              onChange={(e) => handleSpokespersonChange(e.target.value)}
              disabled={create.isPending || spList.length === 0}
              className={cn(
                "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors",
                "placeholder:text-fog focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                "disabled:cursor-not-allowed disabled:opacity-50",
                showErrors && spError && "border-destructive ring-destructive",
              )}
            >
              {spList.length === 0 ? (
                <option value="">No spokespeople found</option>
              ) : (
                spList.map((sp) => (
                  <option key={sp.id} value={sp.id}>
                    {sp.name}
                  </option>
                ))
              )}
            </select>
          )}
          {spList.length === 0 && !spokespeople.isLoading && (
            <p className="text-xs text-fog">
              You need at least one spokesperson.{" "}
              <Link
                to="/spokespeople/new"
                className="text-primary underline-offset-4 hover:underline"
              >
                Create one
              </Link>
              .
            </p>
          )}
          {showErrors && spError && (
            <p
              data-testid="campaign-spokesperson-error"
              className="text-xs text-destructive"
            >
              {spError}
            </p>
          )}
        </div>

        {/* BC4: Script picker section — above the template textarea */}
        {workspaceId && (
          <ScriptPickerSection
            workspaceId={workspaceId}
            spokespersonId={spokespersonId}
            pickedScript={pickedScript}
            onPick={handlePickScript}
            onUnlink={handleUnlinkScript}
            onUseAsTemplate={handleUseAsTemplate}
            disabled={create.isPending}
          />
        )}

        {/* Derived-from banner when script is linked */}
        {sourceScriptId && pickedScript && (
          <div
            data-testid="derived-from-banner"
            className="flex items-center gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400"
          >
            <X
              className="h-3 w-3 cursor-pointer shrink-0"
              onClick={handleUnlinkScript}
              aria-label="Unlink script"
            />
            <span>
              Derived from:{" "}
              <strong>{pickedScript.name || "Untitled script"}</strong>
              {" "}— template editable, FK is audit trail
            </span>
          </div>
        )}

        {/* Template */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="campaign-template"
            className="text-sm font-medium"
          >
            Script template{" "}
            {!sourceScriptId && <span className="text-destructive">*</span>}
            {sourceScriptId && (
              <span className="ml-1 text-[10px] font-normal text-fog">
                (pre-filled from script — edit freely)
              </span>
            )}
          </label>
          <textarea
            id="campaign-template"
            data-testid="campaign-template-input"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            maxLength={4000}
            rows={6}
            placeholder={`Hi {first_name},\n\nI noticed that {company} just hit {milestone}...`}
            disabled={create.isPending}
            className={cn(
              "w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm",
              "placeholder:text-fog focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              "resize-y disabled:cursor-not-allowed disabled:opacity-50",
              showErrors && templateError && "border-destructive ring-destructive",
            )}
          />
          {showErrors && templateError && (
            <p
              data-testid="campaign-template-error"
              className="text-xs text-destructive"
            >
              {templateError}
            </p>
          )}
          <p className="text-[11px] text-fog">
            {template.length} / 4000
          </p>

          {/* Detected variables preview */}
          {detectedVars.length > 0 && (
            <div
              data-testid="detected-vars"
              className="flex flex-wrap gap-1.5 mt-1"
            >
              <span className="text-[11px] text-fog">
                Detected variables:
              </span>
              {detectedVars.map((v) => (
                <span
                  key={v}
                  data-testid={`detected-var-${v}`}
                  className="inline-flex items-center rounded-sm border border-luxe bg-muted px-1.5 py-0.5 font-mono text-[10px] text-fog"
                >
                  {"{"}
                  {v}
                  {"}"}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Submission error */}
        {submitError && (
          <div
            data-testid="campaign-submit-error"
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
            data-testid="campaign-create-submit"
            disabled={create.isPending}
          >
            {create.isPending ? (
              <>
                <Loader2
                  data-testid="campaign-create-spinner"
                  className="mr-2 h-4 w-4 animate-spin"
                />
                Creating…
              </>
            ) : (
              "Create campaign"
            )}
          </Button>
          <Button
            asChild
            type="button"
            variant="ghost"
            disabled={create.isPending}
          >
            <Link to="/workspace/campaigns">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
