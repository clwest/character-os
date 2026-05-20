/**
 * /workspace/campaigns/new — Create a new personalized campaign.
 *
 * SESSION B3.7. Two-field form: metadata (name + spokesperson +
 * template). On success → navigate to the campaign detail page
 * where the operator pastes their CSV.
 *
 * Scope: docs/design/PERSONALIZED_VIDEO_V1.md §B3.7.
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, Loader2, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useCreateCampaign, parsePlaceholders } from "@/lib/api/campaigns";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

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

  // Pick the first spokesperson by default when the list loads.
  useEffect(() => {
    if (!spokespersonId && spList.length > 0) {
      setSpokespersonId(spList[0]!.id);
    }
  }, [spList, spokespersonId]);

  // Client-side placeholder preview — purely advisory.
  const detectedVars = parsePlaceholders(template);

  const [submitError, setSubmitError] = useState<string | null>(null);

  // ---- Validation
  const nameError = name.trim().length === 0 ? "Name is required." : null;
  const spError = spokespersonId.trim() === "" ? "Spokesperson is required." : null;
  const templateError =
    template.trim().length === 0 ? "Template is required." : null;

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
        template,
      });
      navigate(`/workspace/campaigns/${campaign.id}`);
    } catch (err) {
      // Surface backend 400 (e.g. template syntax error) inline.
      if (err instanceof ApiError && err.status === 400) {
        const body = err.body as Record<string, unknown> | null;
        const templateMsg =
          body?.template != null
            ? String(Array.isArray(body.template) ? body.template[0] : body.template)
            : null;
        const detailMsg = body?.detail != null ? String(body.detail) : null;
        setSubmitError(templateMsg ?? detailMsg ?? "Submission failed — check your inputs.");
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
        className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Campaigns
      </Link>

      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-2">
        <h1
          data-testid="campaign-new-title"
          className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
        >
          New campaign
        </h1>
        <p className="text-base text-muted-foreground">
          Define the campaign name, pick a spokesperson, and write your script
          template. Use <code className="rounded-sm border border-border bg-muted px-1 py-0.5 font-mono text-[11px]">{"{first_name}"}</code>-style
          placeholders — you&apos;ll paste your CSV next.
        </p>
      </header>

      {/* ---- Form ----------------------------------------------- */}
      <form
        data-testid="campaign-create-form"
        onSubmit={(e) => void handleSubmit(e)}
        className="flex flex-col gap-6 rounded-md border border-border bg-card p-6"
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
          <p className="text-[11px] text-muted-foreground">
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
              onChange={(e) => setSpokespersonId(e.target.value)}
              disabled={create.isPending || spList.length === 0}
              className={cn(
                "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors",
                "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
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
            <p className="text-xs text-muted-foreground">
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

        {/* Template */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="campaign-template"
            className="text-sm font-medium"
          >
            Script template <span className="text-destructive">*</span>
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
              "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
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
          <p className="text-[11px] text-muted-foreground">
            {template.length} / 4000
          </p>

          {/* Detected variables preview */}
          {detectedVars.length > 0 && (
            <div
              data-testid="detected-vars"
              className="flex flex-wrap gap-1.5 mt-1"
            >
              <span className="text-[11px] text-muted-foreground">
                Detected variables:
              </span>
              {detectedVars.map((v) => (
                <span
                  key={v}
                  data-testid={`detected-var-${v}`}
                  className="inline-flex items-center rounded-sm border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
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
