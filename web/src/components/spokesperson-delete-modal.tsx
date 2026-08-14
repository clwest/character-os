/**
 * SpokespersonDeleteModal — SESSION 251.
 *
 * Customer-facing delete confirmation for a Teammate. Fires
 * ``DELETE /api/spokespeople/<id>/`` on confirm; on success the
 * parent redirects and React Query caches are invalidated.
 *
 * Historical outputs (compositions, assets, transcripts, scripts,
 * campaigns, threads) survive the delete via the SESSION 251
 * SET_NULL migrations. The copy states this explicitly so the
 * customer knows what they are and are not signing up for.
 *
 * Mirrors the visual + interaction shape of
 * ``ToolApprovalModal`` (Esc dismiss, backdrop dismiss when idle,
 * spinner on the destructive button). No typed-confirm ("DELETE")
 * per scope; the risk is bounded because historical work is
 * preserved server-side.
 */
import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDeleteSpokesperson } from "@/lib/api/spokespeople";

export interface SpokespersonDeleteModalProps {
  spokespersonId: string;
  spokespersonName: string;
  /** Fires after DELETE returns 204 — parent should redirect. */
  onDeleted: () => void;
  /** Fires when the operator dismisses without deleting. */
  onDismiss: () => void;
}

export function SpokespersonDeleteModal({
  spokespersonId,
  spokespersonName,
  onDeleted,
  onDismiss,
}: SpokespersonDeleteModalProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const del = useDeleteSpokesperson();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onDismiss();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onDismiss, busy]);

  async function handleDelete() {
    setError(null);
    setBusy(true);
    try {
      await del.mutateAsync(spokespersonId);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      data-testid="spokesperson-delete-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="spokesperson-delete-title"
      onClick={(e) => {
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
          data-testid="spokesperson-delete-dismiss"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex flex-col gap-2">
          <p
            id="spokesperson-delete-title"
            className="text-base font-semibold tracking-tight"
            data-testid="spokesperson-delete-title"
          >
            Delete {spokespersonName}?
          </p>
          <p className="text-sm text-muted-foreground">
            {spokespersonName} will be removed from your team and can no
            longer be used to create new content. Existing generated
            videos and assets will remain in your library.
          </p>
        </div>

        {error && (
          <p
            className="rounded border border-destructive bg-destructive/10 px-3 py-2 text-xs text-destructive"
            data-testid="spokesperson-delete-error"
          >
            {error}
          </p>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={onDismiss}
            disabled={busy}
            data-testid="spokesperson-delete-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={busy}
            data-testid="spokesperson-delete-confirm"
          >
            {busy ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting…
              </>
            ) : (
              `Delete ${spokespersonName}`
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
