/**
 * /workspace/scripts/:id — Script detail view.
 *
 * SESSION B2.5. Layout:
 *   - Header: name + status pill + verification badge
 *   - Draft panel: draft_text + token counts + model
 *   - Citations panel: cited_documents list → /workspace/knowledge/<id>
 *   - Verifier panel: warnings (warned/blocked)
 *   - Action toolbar: status-dependent (DRAFT / READY / RENDERED)
 *   - Revision history panel: collapsed by default
 *   - Post-render section: composition link when render fires
 *
 * Scope: docs/design/AUTO_SCRIPT_V1.md §B2.5.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  Trash2,
  RefreshCw,
  Copy,
  Play,
  ChevronDown,
  ChevronUp,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useScript,
  useRegenerateScript,
  useApproveScript,
  useRenderScript,
  useCloneScript,
  useDeleteScript,
  useDerivedCampaigns,
  scriptStatusTone,
  scriptStatusLabel,
  verificationStatusTone,
  verificationStatusLabel,
  type ScriptDetail,
  type RegenerateScriptInput,
  type VerifierMode,
  type DerivedCampaignRow,
} from "@/lib/api/scripts";
import {
  campaignStatusTone,
  campaignStatusLabel,
} from "@/lib/api/campaigns";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { StatusBadge, VerificationBadge } from "./scripts";

// ---- Page component ---------------------------------------------

export function ScriptDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const script = useScript(id);

  if (script.isLoading) {
    return (
      <div className="flex flex-col gap-4 max-w-3xl">
        <BackLink />
        <LoadingSkeleton />
      </div>
    );
  }

  if (script.isError) {
    const err = script.error as { status?: number; message?: string } | null;
    const is404 = err?.status === 404;
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        {is404 ? (
          <NotFound />
        ) : (
          <ErrorPanel
            message={err?.message ?? "Failed to load script."}
            onRetry={() => script.refetch()}
          />
        )}
      </div>
    );
  }

  if (!script.data) return null;

  return <ScriptDetailView script={script.data} refetch={() => script.refetch()} />;
}

// ---- ScriptDetailView -------------------------------------------

function ScriptDetailView({
  script,
  refetch,
}: {
  script: ScriptDetail;
  refetch: () => void;
}) {
  const navigate = useNavigate();
  const statusTone = scriptStatusTone(script.status);
  const statusLabel = scriptStatusLabel(script.status);
  const vTone = verificationStatusTone(script.verification_status);
  const vLabel = verificationStatusLabel(script.verification_status);

  const [renderedCompositionId, setRenderedCompositionId] = useState<
    string | null
  >(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  const renderMutation = useRenderScript(script.id);

  async function handleRender() {
    setRenderError(null);
    try {
      const result = await renderMutation.mutateAsync(undefined);
      setRenderedCompositionId(result.composition_id);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? String(
              (err.body as Record<string, unknown> | null)?.detail ??
                err.message,
            )
          : err instanceof Error
            ? err.message
            : "Render failed.";
      setRenderError(msg);
    }
  }

  return (
    <div
      data-testid="script-detail"
      className="flex flex-col gap-8 max-w-3xl"
    >
      <BackLink />

      {/* ---- Header -------------------------------------------- */}
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex flex-col gap-1">
            <h1
              data-testid="script-detail-name"
              className="font-display text-3xl leading-tight tracking-tight"
            >
              {script.name || "Untitled script"}
            </h1>
            <p className="text-sm text-fog">
              {script.spokesperson_name} ·{" "}
              <span className="font-mono text-xs">
                {script.id.slice(0, 8)}…
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge tone={statusTone} label={statusLabel} />
            {script.verification_status !== "" && (
              <VerificationBadge tone={vTone} label={vLabel} />
            )}
          </div>
        </div>

        {/* Action toolbar */}
        <ActionToolbar
          script={script}
          refetch={refetch}
          navigate={navigate}
          onRender={() => void handleRender()}
          isRendering={renderMutation.isPending}
        />
      </header>

      {/* ---- Draft panel --------------------------------------- */}
      <DraftPanel script={script} />

      {/* ---- Citations panel ---------------------------------- */}
      <CitationsPanel script={script} />

      {/* ---- Verifier panel ----------------------------------- */}
      {/* Render whenever the verifier produced flags. K6 produces
          informational warnings on `verified` (below the `warned`
          threshold) — the V-arc has rendered against this shape
          for months. Gating on status alone hid them.            */}
      {(script.verification_warnings.length > 0 ||
        script.verification_status === "blocked") && (
        <VerifierPanel script={script} />
      )}

      {/* ---- Post-render panel -------------------------------- */}
      {(renderedCompositionId || renderError) && (
        <RenderResultPanel
          compositionId={renderedCompositionId}
          error={renderError}
        />
      )}

      {/* ---- Derived campaigns (BC4) -------------------------- */}
      <DerivedCampaignsPanel scriptId={script.id} />

      {/* ---- Revision history --------------------------------- */}
      {script.revision_history.length > 0 && (
        <RevisionHistoryPanel script={script} />
      )}
    </div>
  );
}

// ---- DraftPanel ------------------------------------------------

function DraftPanel({ script }: { script: ScriptDetail }) {
  return (
    <section
      data-testid="draft-panel"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-4"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl tracking-tight">Draft</h2>
        <div className="flex items-center gap-3 text-xs text-fog">
          {script.model && (
            <span className="font-mono">{script.model}</span>
          )}
          {(script.tokens_input > 0 || script.tokens_output > 0) && (
            <span>
              {script.tokens_input.toLocaleString()} in /{" "}
              {script.tokens_output.toLocaleString()} out
            </span>
          )}
        </div>
      </div>

      {script.draft_text ? (
        <pre
          data-testid="draft-text"
          className="whitespace-pre-wrap rounded-md bg-muted/40 border border-luxe p-4 font-mono text-sm leading-relaxed overflow-x-auto"
        >
          {script.draft_text}
        </pre>
      ) : (
        <p className="text-sm text-fog italic">
          No draft text yet.
        </p>
      )}

      {script.opener && (
        <div className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-wider text-fog font-medium">
            Pinned opener
          </span>
          <p
            data-testid="draft-opener"
            className="text-sm italic text-fog border-l-2 border-luxe pl-3"
          >
            "{script.opener}"
          </p>
        </div>
      )}
    </section>
  );
}

// ---- CitationsPanel --------------------------------------------

function CitationsPanel({ script }: { script: ScriptDetail }) {
  return (
    <section
      data-testid="citations-panel"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-3"
    >
      <h2 className="font-display text-xl tracking-tight">Knowledge citations</h2>
      {script.cited_documents.length === 0 ? (
        <p
          data-testid="citations-empty"
          className="text-sm text-fog"
        >
          No knowledge attached — draft was synthesized from the prompt and
          spokesperson brief alone.
        </p>
      ) : (
        <ul
          data-testid="citations-list"
          className="flex flex-col divide-y divide-luxe"
        >
          {script.cited_documents.map((doc) => (
            <li
              key={doc.id}
              data-testid={`citation-${doc.id}`}
              className="flex items-center justify-between gap-3 py-2 text-sm"
            >
              <Link
                to={`/workspace/knowledge/${doc.id}`}
                className="text-primary hover:underline underline-offset-2 truncate"
              >
                {doc.title}
              </Link>
              <span className="shrink-0 text-xs text-fog">
                {doc.chunk_count}{" "}
                {doc.chunk_count === 1 ? "chunk" : "chunks"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---- VerifierPanel ---------------------------------------------

function VerifierPanel({ script }: { script: ScriptDetail }) {
  const isBlocked = script.verification_status === "blocked";
  const isWarned = script.verification_status === "warned";
  // Anything else carrying flags (verified / skipped / trusted_passthrough)
  // is informational — show the panel without amber/destructive framing
  // so the operator can still approve cleanly.
  const isInfo = !isBlocked && !isWarned;

  const n = script.verification_warnings.length;
  const plural = n !== 1 ? "s" : "";

  const heading = isBlocked
    ? "K6.4 verification blocked"
    : isWarned
      ? `K6.4 flagged ${n} unsupported claim${plural}`
      : `Verifier noted ${n} informational flag${plural}`;

  return (
    <section
      data-testid="verifier-panel"
      data-tone={isBlocked ? "blocked" : isWarned ? "warned" : "info"}
      className={cn(
        "rounded-md border p-6 flex flex-col gap-4",
        isBlocked && "border-destructive/40 bg-destructive/5",
        isWarned && "border-amber-500/40 bg-amber-500/5",
        isInfo && "border-luxe bg-muted/20",
      )}
    >
      <div className="flex items-start gap-2">
        <AlertCircle
          className={cn(
            "h-5 w-5 shrink-0 mt-0.5",
            isBlocked && "text-destructive",
            isWarned && "text-amber-400",
            isInfo && "text-fog",
          )}
        />
        <div className="flex flex-col gap-1">
          <h2
            className={cn(
              "font-display text-xl tracking-tight",
              isBlocked && "text-destructive",
              isWarned && "text-amber-400",
              isInfo && "text-foreground",
            )}
          >
            {heading}
          </h2>
          {isBlocked && (
            <p
              data-testid="blocked-hint"
              className="text-sm text-destructive/80"
            >
              This script cannot be approved until you regenerate and resolve
              the flagged claims. Click Regenerate to draft a new version.
            </p>
          )}
          {isInfo && (
            <p
              data-testid="info-hint"
              className="text-sm text-fog"
            >
              These are advisory — the draft is approved-ready. Review the
              flagged spans below if you want to tighten grounding before
              rendering.
            </p>
          )}
        </div>
      </div>

      {script.verification_warnings.length > 0 && (
        <ul
          data-testid="verification-warnings-list"
          className="flex flex-col gap-2"
        >
          {script.verification_warnings.map((w, i) => (
            <li
              key={i}
              data-testid={`warning-${i}`}
              className="flex flex-col gap-0.5 rounded-md border border-luxe bg-card p-3"
            >
              <p className="text-sm text-foreground">{w.claim}</p>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-fog">
                  {w.kind}
                </span>
                <span className="text-[10px] text-fog">
                  pos. {w.position}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---- ActionToolbar ---------------------------------------------

function ActionToolbar({
  script,
  refetch,
  navigate,
  onRender,
  isRendering,
}: {
  script: ScriptDetail;
  refetch: () => void;
  navigate: ReturnType<typeof useNavigate>;
  onRender: () => void;
  isRendering: boolean;
}) {
  const [showRegenerateModal, setShowRegenerateModal] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const approveMutation = useApproveScript(script.id);
  const cloneMutation = useCloneScript(script.id);
  const deleteMutation = useDeleteScript(script.id);

  const isBlocked = script.verification_status === "blocked";
  const isDraft = script.status === "draft";
  const isReady = script.status === "ready";
  const isRendered = script.status === "rendered";

  async function handleApprove() {
    setApproveError(null);
    try {
      await approveMutation.mutateAsync();
      refetch();
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as Record<string, unknown> | null;
        const detail =
          typeof body?.detail === "string" ? body.detail : null;
        const code =
          typeof body?.code === "string" ? body.code : null;
        if (code === "verification_blocked") {
          setApproveError(
            detail ??
              "Cannot approve a script with blocked verification claims. Regenerate first.",
          );
        } else {
          setApproveError(detail ?? err.message);
        }
      } else {
        setApproveError(
          err instanceof Error ? err.message : "Approve failed.",
        );
      }
    }
  }

  async function handleClone() {
    try {
      const clone = await cloneMutation.mutateAsync();
      navigate(`/workspace/scripts/${clone.id}`);
    } catch {
      // Swallow — cloneMutation.error holds the error state
    }
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleteError(null);
    try {
      await deleteMutation.mutateAsync();
      navigate("/workspace/scripts");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? String(
              (err.body as Record<string, unknown> | null)?.detail ??
                err.message,
            )
          : err instanceof Error
            ? err.message
            : "Delete failed.";
      setDeleteError(msg);
      setConfirmDelete(false);
    }
  }

  return (
    <div
      data-testid="action-toolbar"
      className="flex flex-col gap-3"
    >
      {/* Error banners */}
      {approveError && (
        <div
          data-testid="approve-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{approveError}</p>
        </div>
      )}
      {deleteError && (
        <p data-testid="delete-error" className="text-xs text-destructive">
          {deleteError}
        </p>
      )}
      {cloneMutation.isError && (
        <p data-testid="clone-error" className="text-xs text-destructive">
          Clone failed:{" "}
          {cloneMutation.error instanceof Error
            ? cloneMutation.error.message
            : "Unknown error."}
        </p>
      )}

      {/* Toolbar row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* DRAFT actions */}
        {isDraft && (
          <>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="regenerate-btn"
              onClick={() => setShowRegenerateModal(true)}
              className="gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Regenerate
            </Button>
            <Button
              type="button"
              size="sm"
              data-testid="approve-btn"
              disabled={isBlocked || approveMutation.isPending}
              onClick={() => void handleApprove()}
              title={
                isBlocked
                  ? "Cannot approve: verification is blocked. Regenerate first."
                  : undefined
              }
              className="gap-1.5"
            >
              {approveMutation.isPending ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Approving…
                </>
              ) : (
                "Approve"
              )}
            </Button>
          </>
        )}

        {/* READY actions */}
        {isReady && (
          <>
            <Button
              type="button"
              size="sm"
              data-testid="render-btn"
              disabled={isRendering || renderNotPossible(script)}
              onClick={onRender}
              className="gap-1.5"
            >
              {isRendering ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Rendering…
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" />
                  Render now
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="regenerate-from-ready-btn"
              onClick={() => setShowRegenerateModal(true)}
              className="gap-1.5"
              title="Regenerating will step the script back to DRAFT"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Regenerate
            </Button>
          </>
        )}

        {/* RENDERED — regenerate and delete are refused server-side */}
        {isRendered && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="regenerate-disabled-btn"
            disabled
            title="Rendered scripts cannot be regenerated. Clone first."
            className="gap-1.5 opacity-50 cursor-not-allowed"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Regenerate
          </Button>
        )}

        {/* Clone — available in all statuses */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="clone-btn"
          disabled={cloneMutation.isPending}
          onClick={() => void handleClone()}
          className="gap-1.5"
        >
          {cloneMutation.isPending ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Cloning…
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Clone
            </>
          )}
        </Button>

        {/* Delete — disabled for RENDERED */}
        {!isRendered ? (
          <div className="flex items-center gap-1.5 ml-auto">
            {confirmDelete && !deleteMutation.isPending && (
              <span className="text-xs text-fog">
                This permanently deletes the script.
              </span>
            )}
            <Button
              type="button"
              variant={confirmDelete ? "destructive" : "outline"}
              size="sm"
              data-testid="delete-btn"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
              className="gap-1.5"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  {confirmDelete ? "Confirm delete" : "Delete"}
                </>
              )}
            </Button>
            {confirmDelete && !deleteMutation.isPending && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-3 text-xs"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            )}
          </div>
        ) : (
          <div
            className="ml-auto flex items-center"
            title="Rendered scripts cannot be deleted. Clone first, then archive."
          >
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="delete-disabled-btn"
              disabled
              className="gap-1.5 opacity-50 cursor-not-allowed ml-auto"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </Button>
          </div>
        )}
      </div>

      {/* Warned approval hint */}
      {isDraft && script.verification_status === "warned" && (
        <p
          data-testid="warned-approve-hint"
          className="text-xs text-amber-400"
        >
          K6.4 flagged {script.verification_warnings.length} unsupported claim
          {script.verification_warnings.length !== 1 ? "s" : ""} — review above
          before approving.
        </p>
      )}

      {/* Regenerate modal */}
      {showRegenerateModal && (
        <RegenerateModal
          script={script}
          onClose={() => setShowRegenerateModal(false)}
          onSuccess={refetch}
        />
      )}
    </div>
  );
}

function renderNotPossible(_script: ScriptDetail): boolean {
  // status=READY is the only guard — already checked upstream.
  return false;
}

// ---- RegenerateModal -------------------------------------------

function RegenerateModal({
  script,
  onClose,
  onSuccess,
}: {
  script: ScriptDetail;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [prompt, setPrompt] = useState(script.prompt);
  const [opener, setOpener] = useState(script.opener);
  const [verifierMode, setVerifierMode] = useState<VerifierMode>(
    script.verifier_mode,
  );
  const [error, setError] = useState<string | null>(null);

  const regenerate = useRegenerateScript(script.id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const input: RegenerateScriptInput = {};
      if (prompt !== script.prompt) input.prompt = prompt;
      if (opener !== script.opener) input.opener = opener;
      if (verifierMode !== script.verifier_mode)
        input.verifier_mode = verifierMode;
      await regenerate.mutateAsync(input);
      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        const body = err.body as Record<string, unknown> | null;
        setError(
          typeof body?.detail === "string"
            ? body.detail
            : "Draft quota exhausted — upgrade to regenerate.",
        );
      } else if (err instanceof ApiError && err.status === 409) {
        setError("Cannot regenerate a rendered or archived script.");
      } else {
        setError(
          err instanceof Error ? err.message : "Regenerate failed.",
        );
      }
    }
  }

  return (
    <div
      data-testid="regenerate-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !regenerate.isPending) onClose();
      }}
    >
      <div
        data-testid="regenerate-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="regenerate-modal-heading"
        className="relative w-full max-w-lg rounded-lg border border-luxe bg-card shadow-xl p-6 flex flex-col gap-5"
        onClick={(e) => e.stopPropagation()}
      >
        {!regenerate.isPending && (
          <button
            type="button"
            aria-label="Close"
            data-testid="regenerate-modal-close"
            onClick={onClose}
            className="absolute top-4 right-4 text-fog hover:text-gold"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        <h2
          id="regenerate-modal-heading"
          data-testid="regenerate-modal-heading"
          className="font-display text-xl tracking-tight"
        >
          Regenerate script
        </h2>

        <p className="text-sm text-fog">
          Each regenerate snapshots the current draft to revision history and
          counts against your monthly quota.
        </p>

        <form
          onSubmit={(e) => void handleSubmit(e)}
          className="flex flex-col gap-4"
        >
          {/* Prompt */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="regen-prompt" className="text-sm font-medium">
              Prompt
            </label>
            <textarea
              id="regen-prompt"
              data-testid="regen-prompt-textarea"
              rows={4}
              maxLength={4000}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={regenerate.isPending}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
            />
          </div>

          {/* Opener */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="regen-opener" className="text-sm font-medium">
              Opening line{" "}
              <span className="text-fog font-normal">
                (optional)
              </span>
            </label>
            <Input
              id="regen-opener"
              data-testid="regen-opener-input"
              type="text"
              maxLength={280}
              value={opener}
              onChange={(e) => setOpener(e.target.value)}
              disabled={regenerate.isPending}
            />
          </div>

          {/* Verifier mode */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="regen-verifier-mode"
              className="text-sm font-medium"
            >
              Verifier mode
            </label>
            <select
              id="regen-verifier-mode"
              data-testid="regen-verifier-mode-select"
              value={verifierMode}
              onChange={(e) =>
                setVerifierMode(e.target.value as VerifierMode)
              }
              disabled={regenerate.isPending}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
            >
              <option value="">Default (warn)</option>
              <option value="strict">Strict</option>
              <option value="warn">Warn</option>
              <option value="off">Off</option>
            </select>
          </div>

          {error && (
            <div
              data-testid="regen-error"
              className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <Button
              type="submit"
              data-testid="regen-submit"
              disabled={regenerate.isPending}
            >
              {regenerate.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Regenerating…
                </>
              ) : (
                "Regenerate"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              data-testid="regen-cancel"
              disabled={regenerate.isPending}
              onClick={onClose}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---- RenderResultPanel -----------------------------------------

function RenderResultPanel({
  compositionId,
  error,
}: {
  compositionId: string | null;
  error: string | null;
}) {
  if (error) {
    return (
      <div
        data-testid="render-result-error"
        className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4"
      >
        <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!compositionId) return null;

  return (
    <div
      data-testid="render-result-success"
      className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-4 flex flex-col gap-2"
    >
      <p className="text-sm text-emerald-400 font-medium">
        Render kicked off — composition{" "}
        <span className="font-mono text-xs">{compositionId.slice(0, 8)}…</span>
      </p>
      <div className="flex items-center gap-3">
        <Link
          to={`/compositions/${compositionId}`}
          data-testid="render-composition-link"
          className="text-xs text-emerald-400 hover:underline underline-offset-2"
        >
          Track composition →
        </Link>
        <Link
          to="/workspace/assets"
          data-testid="render-assets-link"
          className="text-xs text-emerald-400/70 hover:underline underline-offset-2"
        >
          Browse assets
        </Link>
      </div>
    </div>
  );
}

// ---- DerivedCampaignsPanel (BC4) --------------------------------

/**
 * Collapsible panel showing all Campaigns derived from this Script via
 * the source_script FK. Fetches GET /api/scripts/<id>/derived_campaigns/.
 *
 * BC4 / Contract rule 1 — Script doesn't have a back-reference on its
 * model; this panel queries Campaign's FK in reverse via the new endpoint.
 * N=0 → collapsed by default with a muted hint.
 * N>0 → expanded by default.
 * Backend caps at 100 rows (Q-bc-9). Hint shown when at cap.
 */
function DerivedCampaignsPanel({ scriptId }: { scriptId: string }) {
  const derived = useDerivedCampaigns(scriptId);
  const rows = derived.data ?? [];
  const n = rows.length;
  const atCap = n >= 100;

  // N=0 → default collapsed; N>0 → default expanded.
  const [expanded, setExpanded] = useState(n > 0);

  // Re-initialize expanded state when data loads (only on first load).
  const [initialized, setInitialized] = useState(false);
  if (!initialized && derived.data !== undefined) {
    setExpanded(n > 0);
    setInitialized(true);
  }

  return (
    <section
      data-testid="derived-campaigns-panel"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-3"
    >
      <button
        type="button"
        data-testid="derived-campaigns-toggle"
        className="flex items-center justify-between w-full"
        onClick={() => setExpanded((v) => !v)}
      >
        <h2 className="font-display text-xl tracking-tight">
          Derived campaigns ({derived.isLoading ? "…" : n})
        </h2>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-fog" />
        ) : (
          <ChevronDown className="h-4 w-4 text-fog" />
        )}
      </button>

      {expanded && (
        <div data-testid="derived-campaigns-content" className="flex flex-col gap-3">
          {derived.isLoading && (
            <div className="flex items-center gap-2 text-sm text-fog">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading derived campaigns…
            </div>
          )}

          {!derived.isLoading && n === 0 && (
            <p
              data-testid="derived-campaigns-empty"
              className="text-sm text-fog italic"
            >
              Not yet used in any campaign.
            </p>
          )}

          {n > 0 && (
            <ul
              data-testid="derived-campaigns-list"
              className="flex flex-col divide-y divide-luxe"
            >
              {rows.map((row) => (
                <DerivedCampaignRow key={row.id} row={row} />
              ))}
            </ul>
          )}

          {atCap && (
            <p className="text-[11px] text-fog">
              Showing first 100 — refine via campaign status filter if needed.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function DerivedCampaignRow({ row }: { row: DerivedCampaignRow }) {
  const tone = campaignStatusTone(row.status);
  const label = campaignStatusLabel(row.status);

  // Simple relative time helper — avoids a date-fns dep.
  function relativeTime(isoString: string): string {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "today";
    if (diffDays === 1) return "1 day ago";
    if (diffDays < 30) return `${diffDays} days ago`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths === 1) return "1 month ago";
    return `${diffMonths} months ago`;
  }

  return (
    <li
      data-testid={`derived-campaign-row-${row.id}`}
      className="py-3 flex items-center gap-3 flex-wrap text-sm"
    >
      {/* Status badge */}
      <span
        className={cn(
          "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
          tone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-400",
          tone === "success" && "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
          tone === "muted" && "border-luxe bg-muted text-fog",
          tone === "danger" && "border-destructive/40 bg-destructive/10 text-destructive",
        )}
      >
        {label}
      </span>

      {/* Name link */}
      <Link
        to={`/workspace/campaigns/${row.id}`}
        data-testid={`derived-campaign-link-${row.id}`}
        className="font-medium text-foreground hover:text-primary hover:underline underline-offset-2 flex-1 min-w-0 truncate"
      >
        {row.name}
      </Link>

      {/* Recipient count */}
      <span className="text-xs text-fog shrink-0">
        {row.recipient_count} recipient{row.recipient_count !== 1 ? "s" : ""}
      </span>

      {/* Relative timestamp */}
      <span className="text-xs text-fog shrink-0">
        {relativeTime(row.created_at)}
      </span>
    </li>
  );
}

// ---- RevisionHistoryPanel --------------------------------------

function RevisionHistoryPanel({ script }: { script: ScriptDetail }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section
      data-testid="revision-history-panel"
      className="rounded-md border border-luxe bg-card p-6 flex flex-col gap-3"
    >
      <button
        type="button"
        data-testid="revision-history-toggle"
        className="flex items-center justify-between w-full"
        onClick={() => setExpanded((v) => !v)}
      >
        <h2 className="font-display text-xl tracking-tight">
          Revision history ({script.revision_history.length})
        </h2>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-fog" />
        ) : (
          <ChevronDown className="h-4 w-4 text-fog" />
        )}
      </button>

      {expanded && (
        <div
          data-testid="revision-history-list"
          className="flex flex-col gap-4"
        >
          {[...script.revision_history].reverse().map((rev, i) => (
            <div
              key={i}
              data-testid={`revision-${i}`}
              className="rounded-md border border-luxe p-4 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between text-xs text-fog">
                <span>{new Date(rev.ts).toLocaleString()}</span>
                <div className="flex items-center gap-2">
                  {rev.model && (
                    <span className="font-mono">{rev.model}</span>
                  )}
                  {rev.verification_status && (
                    <span className="uppercase">{rev.verification_status}</span>
                  )}
                  <span>
                    {rev.tokens_input + rev.tokens_output} tok
                  </span>
                </div>
              </div>
              {rev.prompt !== script.prompt && (
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] uppercase tracking-wider text-fog">
                    Prompt then
                  </span>
                  <p className="text-xs text-fog italic truncate">
                    {rev.prompt}
                  </p>
                </div>
              )}
              <pre className="whitespace-pre-wrap text-xs font-mono bg-muted/30 rounded-md p-3 leading-relaxed overflow-x-auto max-h-40">
                {rev.draft_text}
              </pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---- Loading / error / not-found helpers -----------------------

function BackLink() {
  return (
    <Link
      to="/workspace/scripts"
      data-testid="back-to-scripts"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to Scripts
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div
      data-testid="script-detail-skeleton"
      className="flex flex-col gap-6 animate-pulse"
    >
      <div className="h-10 w-64 rounded bg-muted" />
      <div className="h-48 w-full rounded-md bg-muted" />
      <div className="h-32 w-full rounded-md bg-muted" />
    </div>
  );
}

function NotFound() {
  return (
    <div
      data-testid="script-not-found"
      className="rounded-md border border-dashed border-luxe p-12 text-center"
    >
      <p className="text-base font-medium">Script not found</p>
      <p className="mt-1 text-sm text-fog">
        This script may have been deleted or belongs to a different workspace.
      </p>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="mt-4"
        data-testid="not-found-back"
      >
        <Link to="/workspace/scripts">Back to Scripts</Link>
      </Button>
    </div>
  );
}

function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      data-testid="script-detail-error"
      className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
    >
      <p className="text-sm text-destructive">{message}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        data-testid="script-detail-retry"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}
