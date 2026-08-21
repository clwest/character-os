/**
 * Knowledge panel for the spokesperson detail page.
 *
 * SESSION 138 / K5. Filtered view of K4's workspace
 * knowledge — shows docs visible to this spokesperson (empty
 * M2M OR M2M includes them) with per-row attach/detach
 * controls.
 *
 * "Visible to all" badge appears when the doc has no M2M
 * attachments (workspace-wide). "Restricted" badge appears
 * when the M2M is non-empty AND includes this spokesperson.
 *
 * Upload happens at the workspace level — the panel sends the
 * operator there via the "Manage workspace knowledge" link.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  statusTone,
  useSpokespersonKnowledge,
  useToggleSpokespersonAttachment,
  type KnowledgeDocument,
  type DocumentStatus,
} from "@/lib/api/knowledge";
import { cn } from "@/lib/utils";

/**
 * SESSION 276 Slice 13 / Delta Stage 3C-1 (refined Q-276-27) —
 * machine-readable error code the backend returns when a detach
 * would remove the last remaining spokesperson from an active
 * ``audience_scope=CHARACTER`` KD. See
 * ``shell/apps/embeddings/views.py`` ``_toggle_spokesperson``.
 */
const FINAL_DETACH_ERROR_CODE =
  "final_character_detach_requires_audience_decision";

/** Extract the backend's ``detail`` string from a rejected detach.
 * Returns the exact backend copy if this is the Slice 13 final-
 * detach case; ``null`` otherwise (caller falls back to whatever
 * generic error handling exists). Kept as a pure helper so the
 * SPA test can assert the discrimination without a full mock. */
export function finalDetachErrorMessage(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  const body = err.body as
    | { code?: string; detail?: string; [k: string]: unknown }
    | null;
  if (body?.code !== FINAL_DETACH_ERROR_CODE) return null;
  return typeof body.detail === "string" ? body.detail : null;
}


interface KnowledgePanelProps {
  workspaceId: string;
  spokespersonId: string;
  spokespersonName: string;
}


export function KnowledgePanel({
  workspaceId,
  spokespersonId,
  spokespersonName,
}: KnowledgePanelProps) {
  const list = useSpokespersonKnowledge(workspaceId, spokespersonId, {
    refetchInterval: (query) => {
      const docs = query.state.data ?? [];
      const inFlight = docs.some(
        (d) => d.status === "pending" || d.status === "processing",
      );
      return inFlight ? 3000 : false;
    },
  });

  const docs = list.data ?? [];

  return (
    <section
      className="flex flex-col gap-5"
      data-testid="spokesperson-knowledge-panel"
    >
      <PanelHeader
        title="Knowledge"
        count={docs.length}
        action={
          <Link
            to="/workspace/knowledge"
            data-testid="manage-knowledge-link"
            className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          >
            <ExternalLink className="h-3 w-3" />
            Manage workspace knowledge
          </Link>
        }
      />

      {list.isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {list.error && (
        <p className="text-sm text-destructive">
          Failed to load knowledge: {list.error.message}
        </p>
      )}

      {!list.isLoading && docs.length === 0 && (
        <EmptyState spokespersonName={spokespersonName} />
      )}

      {docs.length > 0 && (
        <ul
          data-testid="spokesperson-knowledge-list"
          className="divide-y divide-border rounded-md border border-border bg-card"
        >
          {docs.map((doc) => (
            <KnowledgePanelRow
              key={doc.id}
              doc={doc}
              workspaceId={workspaceId}
              spokespersonId={spokespersonId}
              spokespersonName={spokespersonName}
            />
          ))}
        </ul>
      )}
    </section>
  );
}


function EmptyState({ spokespersonName }: { spokespersonName: string }) {
  return (
    <div
      className="rounded-md border border-dashed border-border p-8 text-center"
      data-testid="spokesperson-knowledge-empty"
    >
      <FileText className="mx-auto h-8 w-8 text-muted-foreground" />
      <p className="mt-3 text-sm font-medium">
        {spokespersonName} doesn't know anything yet
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Add documents in workspace knowledge — they'll appear here once
        they apply to this spokesperson.
      </p>
      <Link
        to="/workspace/knowledge"
        className="mt-4 inline-block text-sm font-medium underline-offset-4 hover:underline"
        data-testid="empty-add-knowledge"
      >
        Open workspace knowledge →
      </Link>
    </div>
  );
}


function KnowledgePanelRow({
  doc,
  workspaceId,
  spokespersonId,
  spokespersonName,
}: {
  doc: KnowledgeDocument;
  workspaceId: string;
  spokespersonId: string;
  spokespersonName: string;
}) {
  const toggle = useToggleSpokespersonAttachment(workspaceId, spokespersonId);
  // SESSION 276 Slice 13 — surfaces the backend's structured
  // final-detach error inline so the operator sees a clear,
  // non-technical explanation instead of a generic failure.
  const [finalDetachMessage, setFinalDetachMessage] = useState<string | null>(
    null,
  );

  const isAttached = doc.spokespeople.includes(spokespersonId);
  const visibility = doc.spokespeople.length === 0
    ? "workspace-wide"
    : isAttached
      ? "restricted-includes-me"
      : // Shouldn't appear in this filtered list, but defensively handle it.
        "restricted-excludes-me";

  async function handleAttach() {
    await toggle.mutateAsync({ documentId: doc.id, attach: true });
  }
  async function handleDetach() {
    setFinalDetachMessage(null);
    try {
      await toggle.mutateAsync({ documentId: doc.id, attach: false });
    } catch (err) {
      // SESSION 276 Slice 13 — the backend rejects a detach that
      // would leave a CHARACTER KD with an empty M2M. Surface the
      // structured message inline; other errors bubble up.
      const message = finalDetachErrorMessage(err);
      if (message) {
        setFinalDetachMessage(message);
        return;
      }
      throw err;
    }
  }

  return (
    <li
      data-testid={`spokesperson-knowledge-row-${doc.id}`}
      data-visibility={visibility}
      className="flex flex-col gap-2 px-5 py-4"
    >
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <p className="truncate text-sm font-medium" title={doc.title}>
              {doc.title}
            </p>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {visibility === "workspace-wide" ? (
              <>Visible to every spokesperson in the workspace · {doc.chunk_count} chunk{doc.chunk_count === 1 ? "" : "s"}</>
            ) : (
              <>Attached to {doc.spokespeople.length} spokespe{doc.spokespeople.length === 1 ? "rson" : "ople"} · {doc.chunk_count} chunk{doc.chunk_count === 1 ? "" : "s"}</>
            )}
          </p>
        </div>

        <StatusPill status={doc.status} />

        {visibility === "workspace-wide" ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid={`attach-button-${doc.id}`}
            onClick={handleAttach}
            disabled={toggle.isPending}
            title={`Restrict to ${spokespersonName} only`}
          >
            {toggle.isPending ? "…" : `Make ${spokespersonName}-only`}
          </Button>
        ) : (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            data-testid={`detach-button-${doc.id}`}
            onClick={handleDetach}
            disabled={toggle.isPending}
            title={`Remove ${spokespersonName} from this doc's visibility`}
          >
            {toggle.isPending ? "…" : "Detach"}
          </Button>
        )}
      </div>

      {finalDetachMessage && (
        <div
          role="alert"
          data-testid={`final-detach-blocked-${doc.id}`}
          className="rounded-sm border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100"
        >
          <p>{finalDetachMessage}</p>
          <button
            type="button"
            onClick={() => setFinalDetachMessage(null)}
            className="mt-1 text-[11px] uppercase tracking-wider text-amber-200/80 underline-offset-2 hover:text-amber-100 hover:underline"
            data-testid={`final-detach-dismiss-${doc.id}`}
          >
            Dismiss
          </button>
        </div>
      )}
    </li>
  );
}


function StatusPill({ status }: { status: DocumentStatus }) {
  const tone = statusTone(status);
  return (
    <span
      data-testid="knowledge-row-status"
      data-status={status}
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider",
        tone === "neutral" && "border-border bg-muted text-muted-foreground",
        tone === "info" && "border-primary/40 bg-primary/10 text-primary",
        tone === "success" && "border-success/40 bg-success/10 text-success",
        tone === "danger" && "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {status}
    </span>
  );
}


function PanelHeader({
  title,
  count,
  action,
}: {
  title: string;
  count?: number;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-border/60 pb-3">
      <h2 className="font-display text-xl tracking-tight">
        {title}
        {typeof count === "number" && (
          <span className="ml-2 font-mono text-xs text-muted-foreground">
            {count}
          </span>
        )}
      </h2>
      {action}
    </div>
  );
}
