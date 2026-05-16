/**
 * SpokespersonRebakeModal — W11.2 (SESSION 170).
 *
 * Operator-mediated re-bake flow for an existing spokesperson's
 * avatar. The cost + wait are real enough that this gets a
 * dedicated confirm modal rather than a one-click button:
 *
 *   - Cost: ~$5-10 Runway credits per bake (portrait + avatar
 *           Runway calls combined).
 *   - Wait: 30-180s synchronous; the modal blocks until ready.
 *   - Side effect: replaces ``runway_avatar_id`` + ``portrait_path``
 *           on the row. Previous renders keep their final_asset URLs
 *           — they're unaffected — but new renders use the new
 *           avatar.
 *
 * The modal shows the operator the current visual_subject + voice
 * (read-only here; edit them in the SpokespersonEditModal first if
 * needed) and a Confirm button. On click, fires the rebake-avatar
 * action and stays open with a "Re-baking…" spinner until the row
 * updates.
 */
import { useEffect, useState } from "react";
import { Flame, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useRebakeAvatar,
  type Spokesperson,
} from "@/lib/api/spokespeople";
import { ApiError } from "@/lib/api/client";

export interface SpokespersonRebakeModalProps {
  spokesperson: Spokesperson;
  onClose: () => void;
}

export function SpokespersonRebakeModal({
  spokesperson,
  onClose,
}: SpokespersonRebakeModalProps) {
  const rebake = useRebakeAvatar();
  const [error, setError] = useState<string | null>(null);

  // Esc dismisses unless a bake is in flight (the bake is real
  // Runway spend — don't let an accidental Esc abandon the
  // operator's spinner mid-bake).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !rebake.isPending) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, rebake.isPending]);

  async function handleConfirm() {
    setError(null);
    try {
      await rebake.mutateAsync({ id: spokesperson.id });
      onClose();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? typeof err.body === "object" && err.body !== null
            ? JSON.stringify(err.body)
            : err.message
          : err instanceof Error
            ? err.message
            : "Re-bake failed.";
      setError(message);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !rebake.isPending) onClose();
      }}
      data-testid="spokesperson-rebake-modal"
      role="dialog"
      aria-modal="true"
      aria-label={`Re-bake ${spokesperson.name}'s avatar`}
    >
      <div className="flex w-full max-w-lg flex-col gap-4 rounded-md border bg-card p-6 shadow-paper">
        <header className="flex items-start justify-between gap-3 border-b pb-3">
          <div className="flex items-start gap-2">
            <Flame className="mt-0.5 h-5 w-5 text-amber-700" />
            <div>
              <h2 className="font-display text-2xl leading-tight tracking-tight">
                Re-bake {spokesperson.name}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Generates a fresh portrait + bakes a new Runway avatar from
                the current visual subject + voice.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={rebake.isPending}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Close"
            data-testid="rebake-modal-close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div className="flex flex-col gap-0.5">
            <dt className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Visual subject
            </dt>
            <dd
              className="font-mono text-xs"
              data-testid="rebake-visual-subject"
            >
              {spokesperson.visual_subject || "—"}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Voice
            </dt>
            <dd className="font-mono text-xs" data-testid="rebake-voice">
              {spokesperson.voice_id || "—"}
            </dd>
          </div>
        </dl>

        <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-xs">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-800">
            What this costs
          </p>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
            <li>
              ~$5-10 in Runway credits (portrait gen + avatar bake combined).
            </li>
            <li>30-180 seconds wall-clock — the request blocks until ready.</li>
            <li>
              Replaces this spokesperson's avatar id + portrait. Past renders
              keep their existing asset URLs.
            </li>
            <li>
              Re-bake won't reach into the prompt — if you want a different
              look or voice, edit the spokesperson first, then re-bake.
            </li>
          </ul>
        </div>

        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 border-t pt-3">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={rebake.isPending}
            data-testid="rebake-cancel"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={rebake.isPending}
            data-testid="rebake-confirm"
          >
            {rebake.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Re-baking… (30-180s)
              </>
            ) : (
              <>
                <Flame className="mr-1 h-4 w-4" />
                Confirm + spend
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
