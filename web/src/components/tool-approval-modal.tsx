/**
 * ToolApprovalModal — R8.1 (SESSION 154).
 *
 * Renders when a tool invocation lands ``awaiting_approval``
 * (today: ``render_video``, $0.08 > $0.05 threshold). The
 * operator either approves the invocation (POST
 * ``/api/realtime_tool_invocations/<id>/approve/``) or rejects
 * with an optional reason (POST ``.../reject/``).
 *
 * Q-r-2 (rejection narration via ``sendClientEvent``) is
 * deferred to R8.2 — this modal records the rejection
 * server-side via ``error_message``; the SPA → avatar data
 * channel piece lands once the AvatarCall inner-component
 * surfaces are wired in R8.2.
 *
 * Minimal inline modal — no Radix dependency. Fixed
 * positioned with backdrop, focus trap via tabindex.
 * shadcn-style visual but lighter touch matching the
 * SPA's existing palette of UI primitives.
 */
import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useApproveInvocation,
  useRejectInvocation,
  type DispatchResult,
} from "@/lib/api/realtime";

export interface PendingInvocation {
  invocation_id: string;
  tool_name: string;
  cost_micros: number;
  reason: string;
  args?: Record<string, unknown>;
}

export interface ToolApprovalModalProps {
  invocation: PendingInvocation;
  spokespersonName: string;
  /** Fires when the modal completes (approve OR reject succeeded). */
  onResolved: (result: DispatchResult) => void;
  /** Fires when the operator dismisses the modal without acting
   *  (Esc / backdrop). Server-side state is unchanged. */
  onDismiss: () => void;
}

export function ToolApprovalModal({
  invocation,
  spokespersonName,
  onResolved,
  onDismiss,
}: ToolApprovalModalProps) {
  const [reason, setReason] = useState("");
  const [pendingMode, setPendingMode] = useState<
    "idle" | "approving" | "rejecting"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const approve = useApproveInvocation();
  const reject = useRejectInvocation();

  // Dismiss on Esc.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && pendingMode === "idle") onDismiss();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onDismiss, pendingMode]);

  async function handleApprove() {
    setError(null);
    setPendingMode("approving");
    try {
      const result = await approve.mutateAsync(invocation.invocation_id);
      onResolved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed.");
      setPendingMode("idle");
    }
  }

  async function handleReject() {
    setError(null);
    setPendingMode("rejecting");
    try {
      const result = await reject.mutateAsync({
        invocationId: invocation.invocation_id,
        reason: reason.trim() || undefined,
      });
      onResolved(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed.");
      setPendingMode("idle");
    }
  }

  const dollars = (invocation.cost_micros / 1_000_000).toFixed(2);
  const toolLabel = formatToolLabel(invocation.tool_name);
  const busy = pendingMode !== "idle";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      data-testid="tool-approval-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tool-approval-title"
      onClick={(e) => {
        // Dismiss on backdrop click — but only when no async
        // op is in flight (don't strand the operator if the
        // server is processing their decision).
        if (e.target === e.currentTarget && !busy) onDismiss();
      }}
    >
      <div className="relative flex max-w-md flex-col gap-4 rounded-lg border bg-card p-6 shadow-lg">
        <button
          type="button"
          onClick={onDismiss}
          disabled={busy}
          aria-label="Dismiss"
          className="absolute right-3 top-3 inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          data-testid="tool-approval-dismiss"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex flex-col gap-1">
          <p
            id="tool-approval-title"
            className="text-base font-semibold tracking-tight"
          >
            {spokespersonName} wants to {toolLabel}.
          </p>
          <p className="text-sm text-muted-foreground">
            Estimated cost: <span className="font-mono">${dollars}</span>.
            Approve to let {spokespersonName} run this, or reject to
            keep the conversation going without it.
          </p>
        </div>

        {invocation.args && Object.keys(invocation.args).length > 0 && (
          <dl
            className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 rounded border border-dashed bg-muted/40 p-3 text-xs"
            data-testid="tool-approval-args"
          >
            {Object.entries(invocation.args).map(([k, v]) => (
              <ArgRow key={k} name={k} value={v} />
            ))}
          </dl>
        )}

        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-muted-foreground">
            Reason (shown to {spokespersonName} on reject — optional)
          </span>
          <textarea
            className="rounded border bg-background px-2 py-1.5 text-sm"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={busy}
            placeholder="Not now, let's talk about the script first."
            data-testid="tool-approval-reason"
          />
        </label>

        {error && (
          <p
            className="rounded border border-destructive bg-destructive/10 px-3 py-2 text-xs text-destructive"
            data-testid="tool-approval-error"
          >
            {error}
          </p>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={handleReject}
            disabled={busy}
            data-testid="tool-approval-reject"
          >
            {pendingMode === "rejecting" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Rejecting…
              </>
            ) : (
              "Reject"
            )}
          </Button>
          <Button
            onClick={handleApprove}
            disabled={busy}
            data-testid="tool-approval-approve"
          >
            {pendingMode === "approving" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Approving…
              </>
            ) : (
              "Approve"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ArgRow({ name, value }: { name: string; value: unknown }) {
  const display =
    typeof value === "string"
      ? value
      : typeof value === "number" || typeof value === "boolean"
        ? String(value)
        : JSON.stringify(value);
  return (
    <>
      <dt className="text-muted-foreground">{name}</dt>
      <dd className="break-words font-mono text-foreground/80">
        {display.length > 80 ? display.slice(0, 80) + "…" : display}
      </dd>
    </>
  );
}

// Human-readable tool label for the prompt copy. Keeps the
// modal's voice in the spokesperson's first person rather
// than exposing tool names.
function formatToolLabel(toolName: string): string {
  switch (toolName) {
    case "render_video":
      return "render a video for you";
    case "attach_memory":
      return "save this conversation to memory";
    default:
      return `run the ${toolName.replace(/_/g, " ")} action`;
  }
}
