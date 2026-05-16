/**
 * Image detail modal — W11.6.4.
 *
 * Opens when an operator clicks an image card in the library
 * grid. Shows the full image, composed prompt, and metadata;
 * offers two actions:
 *
 *   - **Regenerate** — re-fires ``useGenerateImage`` with the
 *     same workspace + purpose + model + style_preset +
 *     aspect_ratio + subject. The backend re-composes from the
 *     subject (not the prompt) so framing isn't double-applied.
 *     Falls back to "Adjust on Generate tab" for pre-W11.6.4
 *     rows where subject is empty.
 *
 *   - **Delete** — confirms then fires ``useDeleteImage``.
 *     Closes the modal on success.
 *
 * Esc / backdrop / X all dismiss when no async op is in
 * flight. Same minimal inline-modal pattern as
 * ``tool-approval-modal.tsx`` (no Radix dependency).
 */
import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useDeleteImage,
  useGenerateImage,
  type ImageAsset,
} from "@/lib/api/images";

export interface ImageDetailModalProps {
  asset: ImageAsset;
  /** Fires after a successful regenerate; the parent typically
   *  updates the selected asset so the modal swaps to the new
   *  result. */
  onRegenerated?: (newAsset: ImageAsset) => void;
  /** Fires after a successful delete. Parent should close. */
  onDeleted?: () => void;
  /** Fires when the operator dismisses without acting. */
  onDismiss: () => void;
}

export function ImageDetailModal({
  asset,
  onRegenerated,
  onDeleted,
  onDismiss,
}: ImageDetailModalProps) {
  const generate = useGenerateImage();
  const del = useDeleteImage();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const busy = generate.isPending || del.isPending;
  const canRegenerate = Boolean(asset.subject);

  useEffect(() => {
    if (!busy) {
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape") onDismiss();
      };
      window.addEventListener("keydown", handler);
      return () => window.removeEventListener("keydown", handler);
    }
    return undefined;
  }, [busy, onDismiss]);

  function handleRegenerate() {
    if (!canRegenerate) return;
    setActionError(null);
    generate.mutate(
      {
        workspace: asset.workspace,
        purpose: asset.purpose as never,
        subject: asset.subject,
        model: asset.model as never,
        aspect_ratio: asset.aspect_ratio as never,
        style_preset: asset.style_preset || undefined,
        negative_prompt_override: asset.negative_prompt || undefined,
        spokesperson: asset.spokesperson ?? undefined,
      },
      {
        onSuccess: (created) => {
          onRegenerated?.(created);
        },
        onError: (err) => {
          setActionError(extractMessage(err) ?? "Regenerate failed.");
        },
      },
    );
  }

  function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setActionError(null);
    del.mutate(asset.id, {
      onSuccess: () => {
        onDeleted?.();
      },
      onError: (err) => {
        setActionError(extractMessage(err) ?? "Delete failed.");
      },
    });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="image-detail-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onDismiss();
      }}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-4xl flex-col gap-4 overflow-y-auto rounded-lg border border-border bg-card p-6 shadow-lg"
      >
        <header className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {asset.purpose} · {asset.aspect_ratio}
            </span>
            <h2 className="font-display text-2xl leading-tight">
              {asset.subject || asset.prompt.slice(0, 80) + "…"}
            </h2>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onDismiss}
            disabled={busy}
            data-testid="image-detail-dismiss"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        </header>

        <img
          src={asset.file_path}
          alt={asset.subject || asset.prompt.slice(0, 120)}
          className="w-full rounded-md border border-border"
          data-testid="image-detail-image"
        />

        <section className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Metadata label="Model" value={asset.model} />
          <Metadata
            label="Style preset"
            value={asset.style_preset || "—"}
          />
          <Metadata
            label="Cost"
            value={`${(asset.cost_micros / 1000).toFixed(1)} credits`}
          />
          <Metadata
            label="Created"
            value={new Date(asset.created_at).toLocaleString()}
          />
        </section>

        {asset.subject && (
          <section className="flex flex-col gap-1">
            <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Subject
            </h3>
            <p className="text-sm">{asset.subject}</p>
          </section>
        )}

        <details className="text-sm">
          <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Composed prompt
          </summary>
          <p
            className="mt-2 whitespace-pre-wrap text-muted-foreground"
            data-testid="image-detail-prompt"
          >
            {asset.prompt}
          </p>
        </details>

        {asset.negative_prompt && (
          <details className="text-sm">
            <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Negative prompt
            </summary>
            <p className="mt-2 whitespace-pre-wrap text-muted-foreground">
              {asset.negative_prompt}
            </p>
          </details>
        )}

        {actionError && (
          <div
            data-testid="image-detail-error"
            className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
          >
            {actionError}
          </div>
        )}

        <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
          {confirmDelete && (
            <span
              data-testid="image-detail-confirm-text"
              className="mr-auto text-sm text-destructive"
            >
              Delete this image permanently?
            </span>
          )}
          <Button
            type="button"
            variant={confirmDelete ? "destructive" : "outline"}
            onClick={handleDelete}
            disabled={busy}
            data-testid="image-detail-delete"
          >
            {del.isPending ? (
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-3 w-3" />
            )}
            {confirmDelete ? "Confirm delete" : "Delete"}
          </Button>
          <Button
            type="button"
            onClick={handleRegenerate}
            disabled={busy || !canRegenerate}
            title={
              canRegenerate
                ? "Re-fire with the same subject + parameters"
                : "Subject not available on pre-W11.6.4 images. Use the Generate tab to start fresh."
            }
            data-testid="image-detail-regenerate"
          >
            {generate.isPending ? (
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-3 w-3" />
            )}
            Regenerate
          </Button>
        </footer>
      </div>
    </div>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </span>
      <span className="text-sm">{value}</span>
    </div>
  );
}

function extractMessage(err: unknown): string | undefined {
  if (!err) return undefined;
  if (err instanceof Error) return err.message;
  return undefined;
}
