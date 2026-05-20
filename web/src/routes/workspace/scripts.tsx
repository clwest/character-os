/**
 * /workspace/scripts — Script list view.
 *
 * SESSION B2.5. Lists all auto-scripts in the workspace.
 * Columns: status pill, name, spokesperson, prompt (truncated),
 * verification badge, model, tokens, revision count, date, actions.
 * Filter dropdowns for status + verification_status.
 * "New script" CTA top-right.
 *
 * Scope: docs/design/AUTO_SCRIPT_V1.md §B2.5.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, FileText, Plus, Trash2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMe } from "@/lib/api/workspaces";
import {
  useScripts,
  useDeleteScript,
  scriptStatusTone,
  scriptStatusLabel,
  verificationStatusTone,
  verificationStatusLabel,
  type ScriptStatus,
  type VerificationStatus,
  type ScriptListItem,
  SCRIPT_STATUSES,
  VERIFICATION_STATUSES,
} from "@/lib/api/scripts";
import { cn } from "@/lib/utils";

// ---- Filter option shapes ---------------------------------------

const STATUS_FILTER_OPTIONS: Array<{ value: ScriptStatus | "all"; label: string }> =
  [
    { value: "all", label: "All" },
    { value: "draft", label: "Draft" },
    { value: "ready", label: "Approved" },
    { value: "rendered", label: "Rendered" },
    { value: "archived", label: "Archived" },
  ];

const VERIFICATION_FILTER_OPTIONS: Array<{
  value: VerificationStatus | "all";
  label: string;
}> = [
  { value: "all", label: "Any" },
  { value: "verified", label: "Verified" },
  { value: "warned", label: "Warned" },
  { value: "blocked", label: "Blocked" },
  { value: "skipped", label: "Skipped" },
];

// ---- Page component ---------------------------------------------

export function WorkspaceScriptsRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  const [activeStatus, setActiveStatus] = useState<ScriptStatus | undefined>(
    undefined,
  );
  const [activeVerification, setActiveVerification] = useState<
    VerificationStatus | undefined
  >(undefined);

  const scripts = useScripts(workspaceId, {
    status: activeStatus,
    verification_status: activeVerification,
  });
  const results = scripts.data ?? [];

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <FileText className="h-7 w-7 text-muted-foreground" />
            <h1
              data-testid="scripts-title"
              className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
            >
              Auto Scripts
            </h1>
          </div>
          <Button asChild data-testid="new-script-btn">
            <Link to="/workspace/scripts/new">
              <Plus className="mr-2 h-4 w-4" />
              New script
            </Link>
          </Button>
        </div>
        <p className="max-w-2xl text-base text-muted-foreground">
          Draft a script with K2 knowledge retrieval and K6 verifier, approve
          it, then fire a render — all without leaving your workspace.
        </p>
      </header>

      {/* ---- Filters ------------------------------------------ */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Status filter */}
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Status
          </span>
          <div
            data-testid="status-filter-chips"
            className="flex flex-wrap gap-1.5"
          >
            {STATUS_FILTER_OPTIONS.map((opt) => {
              const isActive = opt.value === (activeStatus ?? "all");
              return (
                <button
                  key={opt.value}
                  type="button"
                  data-testid={`status-chip-${opt.value}`}
                  onClick={() =>
                    setActiveStatus(
                      opt.value === "all"
                        ? undefined
                        : (opt.value as ScriptStatus),
                    )
                  }
                  className={cn(
                    "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    isActive
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Verification filter */}
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Verifier
          </span>
          <div
            data-testid="verification-filter-chips"
            className="flex flex-wrap gap-1.5"
          >
            {VERIFICATION_FILTER_OPTIONS.map((opt) => {
              const isActive = opt.value === (activeVerification ?? "all");
              return (
                <button
                  key={opt.value}
                  type="button"
                  data-testid={`verification-chip-${opt.value}`}
                  onClick={() =>
                    setActiveVerification(
                      opt.value === "all"
                        ? undefined
                        : (opt.value as VerificationStatus),
                    )
                  }
                  className={cn(
                    "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    isActive
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ---- List --------------------------------------------- */}
      <section className="flex flex-col gap-4">
        <h2 className="font-display text-2xl tracking-tight">
          {activeStatus ? scriptStatusLabel(activeStatus) : "All"} scripts
          {results.length > 0 && (
            <span className="ml-2 text-xl text-muted-foreground font-sans font-normal">
              ({results.length})
            </span>
          )}
        </h2>

        {/* Loading skeleton */}
        {scripts.isLoading && (
          <ul
            data-testid="scripts-skeleton"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {Array.from({ length: 4 }).map((_, i) => (
              <li
                key={i}
                className="flex items-start gap-4 px-5 py-4 animate-pulse"
              >
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/5 rounded bg-muted" />
                  <div className="h-3 w-3/5 rounded bg-muted" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Error state */}
        {scripts.isError && (
          <div
            data-testid="scripts-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load scripts: {(scripts.error as Error).message}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="scripts-retry"
              className="mt-3"
              onClick={() => scripts.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!scripts.isLoading && !scripts.isError && results.length === 0 && (
          <div
            data-testid="scripts-empty"
            className="rounded-md border border-dashed border-border p-12 text-center"
          >
            <FileText className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-base font-medium">No scripts yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Draft a script from your workspace knowledge, review + approve it,
              then fire a render — all with full K6 verification.
            </p>
            <Button
              asChild
              size="sm"
              className="mt-4"
              data-testid="scripts-empty-cta"
            >
              <Link to="/workspace/scripts/new">
                Draft your first script
              </Link>
            </Button>
          </div>
        )}

        {/* Script rows */}
        {results.length > 0 && (
          <ul
            data-testid="scripts-list"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {results.map((script) => (
              <ScriptRow key={script.id} script={script} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---- ScriptRow --------------------------------------------------

function ScriptRow({ script }: { script: ScriptListItem }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const deleteMutation = useDeleteScript(script.id);

  const statusTone = scriptStatusTone(script.status);
  const statusLabel = scriptStatusLabel(script.status);
  const vTone = verificationStatusTone(script.verification_status);
  const vLabel = verificationStatusLabel(script.verification_status);

  const canDelete = script.status !== "rendered";

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    await deleteMutation.mutateAsync();
    setConfirmDelete(false);
  }

  return (
    <li
      data-testid={`script-row-${script.id}`}
      className="hover:bg-muted/30 transition-colors"
    >
      <Link
        to={`/workspace/scripts/${script.id}`}
        data-testid={`script-link-${script.id}`}
        className="flex items-start gap-4 px-5 py-4"
      >
        {/* Main content */}
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge tone={statusTone} label={statusLabel} />
            <p
              data-testid={`script-name-${script.id}`}
              className="truncate text-sm font-medium"
              title={script.name}
            >
              {script.name || "Untitled script"}
            </p>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            <span className="font-medium">{script.spokesperson_name}</span>
            {" · "}
            <span className="opacity-80">{truncate(script.prompt, 80)}</span>
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-0.5">
            {/* Verification badge — only when notable */}
            {(script.verification_status === "warned" ||
              script.verification_status === "blocked") && (
              <VerificationBadge tone={vTone} label={vLabel} />
            )}
            {script.model && (
              <span className="text-[10px] text-muted-foreground font-mono">
                {script.model}
              </span>
            )}
            {(script.tokens_input > 0 || script.tokens_output > 0) && (
              <span className="text-[10px] text-muted-foreground">
                {script.tokens_input + script.tokens_output} tok
              </span>
            )}
            {script.revision_count > 0 && (
              <span className="text-[10px] text-muted-foreground">
                {script.revision_count} rev{script.revision_count !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Right column: date + delete */}
        <div
          className="flex shrink-0 flex-col items-end gap-2"
          onClick={(e) => e.preventDefault()}
        >
          <span className="text-xs text-muted-foreground/60">
            {relativeTime(script.created_at)}
          </span>
          {canDelete && (
            <div className="flex items-center gap-1.5">
              {confirmDelete && (
                <>
                  <span className="text-[10px] text-muted-foreground">
                    Confirm?
                  </span>
                  <button
                    type="button"
                    data-testid={`script-cancel-delete-${script.id}`}
                    className="text-[10px] text-muted-foreground hover:text-foreground"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setConfirmDelete(false);
                    }}
                  >
                    Cancel
                  </button>
                </>
              )}
              <button
                type="button"
                data-testid={`script-delete-btn-${script.id}`}
                disabled={deleteMutation.isPending}
                onClick={(e) => void handleDelete(e)}
                className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                title={confirmDelete ? "Click to confirm delete" : "Delete script"}
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Trash2 className="h-3 w-3" />
                )}
                {confirmDelete ? "Yes, delete" : "Delete"}
              </button>
            </div>
          )}
          {!canDelete && (
            <span
              data-testid={`script-rendered-tag-${script.id}`}
              className="text-[10px] text-muted-foreground/60"
              title="Rendered scripts cannot be deleted. Clone first."
            >
              rendered
            </span>
          )}
        </div>
      </Link>
    </li>
  );
}

// ---- StatusBadge ------------------------------------------------

export function StatusBadge({
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
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- VerificationBadge ------------------------------------------

export function VerificationBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  label: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium",
        tone === "amber" &&
          "border-amber-500/30 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/30 bg-destructive/10 text-destructive",
      )}
    >
      K6.4: {label}
    </span>
  );
}

// ---- Utility helpers --------------------------------------------

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max - 1) + "…" : str;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// Re-export for use in detail view
export { SCRIPT_STATUSES, VERIFICATION_STATUSES };
