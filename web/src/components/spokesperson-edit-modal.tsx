/**
 * SpokespersonEditModal — W11.1 (SESSION 169).
 *
 * Edit the persona-axis fields of a Spokesperson:
 * - name
 * - business_brief
 * - visual_subject
 * - tone_archetype
 *
 * Voice + avatar are read-only here — changing them requires
 * a Runway-side re-bind (W11.2 work). The Edit button on the
 * detail page opens this modal; Save fires a PATCH that
 * partial-updates the row and seeds the cache so the detail
 * page reflects the new values instantly.
 *
 * Minimal inline modal — same pattern as ToolApprovalModal
 * (R8.1). No Radix dependency. Esc / backdrop dismisses when
 * no save is in flight.
 */
import { useEffect, useRef, useState } from "react";
import { Loader2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  TONE_ARCHETYPES,
  type Spokesperson,
  type ToneArchetype,
  useUpdateSpokesperson,
} from "@/lib/api/spokespeople";
import { ApiError } from "@/lib/api/client";

const TONE_LABEL: Record<ToneArchetype, string> = {
  tutor: "Tutor — patient teacher",
  authority: "Authority — confident expert",
  friend: "Friend — warm and approachable",
  expert: "Expert — neutral and direct",
  performer: "Performer — energetic and dramatic",
};

export interface SpokespersonEditModalProps {
  spokesperson: Spokesperson;
  onClose: () => void;
}

export function SpokespersonEditModal({
  spokesperson,
  onClose,
}: SpokespersonEditModalProps) {
  const [name, setName] = useState(spokesperson.name);
  const [businessBrief, setBusinessBrief] = useState(
    spokesperson.business_brief ?? "",
  );
  const [visualSubject, setVisualSubject] = useState(
    spokesperson.visual_subject ?? "",
  );
  const [toneArchetype, setToneArchetype] = useState<ToneArchetype>(
    spokesperson.tone_archetype,
  );
  const [error, setError] = useState<string | null>(null);
  const update = useUpdateSpokesperson();
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  // Esc / backdrop dismiss — only when no save is in flight.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !update.isPending) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, update.isPending]);

  function _hasChanges(): boolean {
    return (
      name.trim() !== spokesperson.name ||
      businessBrief !== (spokesperson.business_brief ?? "") ||
      visualSubject !== (spokesperson.visual_subject ?? "") ||
      toneArchetype !== spokesperson.tone_archetype
    );
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!_hasChanges()) {
      onClose();
      return;
    }
    if (!name.trim()) {
      setError("Name cannot be blank.");
      return;
    }
    if (visualSubject.length > 200) {
      setError("Visual subject must be 200 characters or fewer.");
      return;
    }
    try {
      // Send only the changed fields so the PATCH is minimal.
      const payload: Parameters<typeof update.mutateAsync>[0] = {
        id: spokesperson.id,
      };
      if (name.trim() !== spokesperson.name) payload.name = name.trim();
      if (businessBrief !== (spokesperson.business_brief ?? "")) {
        payload.business_brief = businessBrief;
      }
      if (visualSubject !== (spokesperson.visual_subject ?? "")) {
        payload.visual_subject = visualSubject;
      }
      if (toneArchetype !== spokesperson.tone_archetype) {
        payload.tone_archetype = toneArchetype;
      }
      await update.mutateAsync(payload);
      onClose();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? typeof err.body === "object" && err.body !== null
            ? JSON.stringify(err.body)
            : err.message
          : err instanceof Error
            ? err.message
            : "Save failed.";
      setError(message);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !update.isPending) onClose();
      }}
      data-testid="spokesperson-edit-modal"
      role="dialog"
      aria-modal="true"
      aria-label={`Edit ${spokesperson.name}`}
    >
      <form
        onSubmit={handleSave}
        className="flex w-full max-w-lg flex-col gap-4 rounded-md border bg-card p-6 shadow-paper"
      >
        <header className="flex items-start justify-between gap-3 border-b pb-3">
          <div>
            <h2 className="font-display text-2xl leading-tight tracking-tight">
              Edit {spokesperson.name}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Voice and avatar can't be changed here — they're bound at avatar
              creation. Use the detail page setup row to re-bake the avatar.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={update.isPending}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Close"
            data-testid="edit-modal-close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-name">Name</Label>
          <Input
            id="edit-name"
            ref={firstInputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            disabled={update.isPending}
            data-testid="edit-name"
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-tone">Tone archetype</Label>
          <select
            id="edit-tone"
            value={toneArchetype}
            onChange={(e) => setToneArchetype(e.target.value as ToneArchetype)}
            disabled={update.isPending}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="edit-tone"
          >
            {TONE_ARCHETYPES.map((t) => (
              <option key={t} value={t}>
                {TONE_LABEL[t]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-visual">
            Visual subject{" "}
            <span className="text-muted-foreground">
              ({visualSubject.length}/200)
            </span>
          </Label>
          <Input
            id="edit-visual"
            value={visualSubject}
            onChange={(e) => setVisualSubject(e.target.value)}
            maxLength={200}
            disabled={update.isPending}
            placeholder="e.g. battle unicorn in Roman legionary armor"
            data-testid="edit-visual"
          />
          <p className="text-xs text-muted-foreground">
            Changes here don't re-bake the avatar — they're recorded for the
            next portrait regen.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-brief">Business brief</Label>
          <textarea
            id="edit-brief"
            value={businessBrief}
            onChange={(e) => setBusinessBrief(e.target.value)}
            rows={5}
            disabled={update.isPending}
            placeholder="What does this spokesperson sound like, and what business do they represent?"
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="edit-brief"
          />
          <p className="text-xs text-muted-foreground">
            Drives K6's render-time script voice. Changes apply to the next
            video you create.
          </p>
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
            disabled={update.isPending}
            data-testid="edit-cancel"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={update.isPending || !_hasChanges() || !name.trim()}
            data-testid="edit-save"
          >
            {update.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <Save className="mr-1 h-4 w-4" />
                Save changes
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
