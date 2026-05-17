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
import { AlertCircle, CheckCircle2, Info, Loader2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  TONE_ARCHETYPES,
  type ChangeVoiceResponse,
  type Spokesperson,
  type ToneArchetype,
  useChangeVoice,
  useUpdateSpokesperson,
  useVoicePresets,
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
  // W11.y (SESSION 175) — personality / business_brief split.
  // Pre-W11.y rows had personality backfilled from business_brief
  // server-side; operator can split per-spokesperson here.
  const [personality, setPersonality] = useState(
    spokesperson.personality ?? "",
  );
  const [visualSubject, setVisualSubject] = useState(
    spokesperson.visual_subject ?? "",
  );
  const [toneArchetype, setToneArchetype] = useState<ToneArchetype>(
    spokesperson.tone_archetype,
  );
  // W11.2 — voice preset swap. Only the value changes; the live
  // PATCH against Runway fires via a separate action because the
  // PATCH endpoint isn't part of the ModelViewSet.
  const [voicePreset, setVoicePreset] = useState(
    spokesperson.voice_id ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  // SESSION 174 — surface the voice_patch envelope returned by
  // the change-voice action so the operator can tell whether the
  // live Runway PATCH actually succeeded. SESSION 171 dogfood
  // discovered that the modal previously closed silently
  // regardless of patch outcome.
  const [voicePatch, setVoicePatch] = useState<
    ChangeVoiceResponse["voice_patch"] | null
  >(null);
  const update = useUpdateSpokesperson();
  const changeVoice = useChangeVoice();
  const voicePresets = useVoicePresets();
  const isPending = update.isPending || changeVoice.isPending;
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  // Esc / backdrop dismiss — only when no save is in flight.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !isPending) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, isPending]);

  function _hasChanges(): boolean {
    return (
      name.trim() !== spokesperson.name ||
      businessBrief !== (spokesperson.business_brief ?? "") ||
      personality !== (spokesperson.personality ?? "") ||
      visualSubject !== (spokesperson.visual_subject ?? "") ||
      toneArchetype !== spokesperson.tone_archetype ||
      voicePreset !== (spokesperson.voice_id ?? "")
    );
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setVoicePatch(null);
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
      if (personality !== (spokesperson.personality ?? "")) {
        payload.personality = personality;
      }
      if (visualSubject !== (spokesperson.visual_subject ?? "")) {
        payload.visual_subject = visualSubject;
      }
      if (toneArchetype !== spokesperson.tone_archetype) {
        payload.tone_archetype = toneArchetype;
      }
      // PATCH for the simple fields first.
      const hasPatchFields =
        payload.name !== undefined ||
        payload.business_brief !== undefined ||
        payload.personality !== undefined ||
        payload.visual_subject !== undefined ||
        payload.tone_archetype !== undefined;
      if (hasPatchFields) {
        await update.mutateAsync(payload);
      }
      // W11.2 — voice change is a separate action (PATCH on the
      // Runway avatar via the change-voice endpoint). Fire only
      // when the voice preset actually changed.
      if (voicePreset && voicePreset !== (spokesperson.voice_id ?? "")) {
        const result = await changeVoice.mutateAsync({
          id: spokesperson.id,
          preset: voicePreset,
        });
        setVoicePatch(result.voice_patch);
        // W11.x.1 (SESSION 175) — never auto-close after a voice
        // change. SESSION 174 dogfood: the success/skipped
        // banners flashed for ~10ms then unmounted because
        // ``onClose()`` fired in the same React tick that set
        // the banner state, leaving operators with zero visible
        // confirmation. Operator clicks Close themselves
        // (button relabels via the voicePatch-aware footer).
        // Persona-only edits (no voice change) still auto-close
        // — they don't carry telemetry to surface.
        return;
      }
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
              Voice changes are live — they PATCH the Runway avatar. To change
              the visual (re-bake the avatar) use the dedicated button on the
              detail page.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
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
            disabled={isPending}
            data-testid="edit-name"
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-tone">Tone archetype</Label>
          <select
            id="edit-tone"
            value={toneArchetype}
            onChange={(e) => setToneArchetype(e.target.value as ToneArchetype)}
            disabled={isPending}
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
          <Label htmlFor="edit-voice">Voice preset</Label>
          <select
            id="edit-voice"
            value={voicePreset}
            onChange={(e) => setVoicePreset(e.target.value)}
            disabled={isPending || voicePresets.isLoading}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="edit-voice"
          >
            {voicePresets.isLoading && <option value="">Loading…</option>}
            {voicePresets.data?.map((preset) => (
              <option key={preset} value={preset}>
                {preset}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            Live PATCH on Runway. Takes effect on the next render. Failed
            patches keep the new value in the DB so the next avatar bake
            picks it up.
          </p>
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
            disabled={isPending}
            placeholder="e.g. battle unicorn in Roman legionary armor"
            data-testid="edit-visual"
          />
          <p className="text-xs text-muted-foreground">
            Changes here don't re-bake the avatar — they're recorded on the
            row and picked up the next time you re-bake.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-brief">
            Business brief{" "}
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              WHAT
            </span>
          </Label>
          <textarea
            id="edit-brief"
            value={businessBrief}
            onChange={(e) => setBusinessBrief(e.target.value)}
            rows={5}
            disabled={isPending}
            placeholder="The product, the audience, pricing, key policies. Facts the spokesperson grounds in."
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="edit-brief"
          />
          <p className="text-xs text-muted-foreground">
            Facts about the business. Treated as authoritative alongside the
            knowledge corpus.
          </p>
        </div>

        {/* W11.y (SESSION 175) — personality split from business_brief.
            Pre-W11.y rows have personality backfilled from
            business_brief so this defaults to a copy of the brief
            until the operator splits them. */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="edit-personality">
            Personality{" "}
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              HOW
            </span>
          </Label>
          <textarea
            id="edit-personality"
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            rows={4}
            disabled={isPending}
            placeholder="Voice, character, mannerisms. How the spokesperson speaks. Distinct from the business brief above."
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="edit-personality"
          />
          <p className="text-xs text-muted-foreground">
            Drives K6's tone fence + the realtime avatar's
            personality on Runway's side. Empty falls back to business
            brief.
          </p>
        </div>

        {voicePatch && <VoicePatchBanner voicePatch={voicePatch} />}

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
            disabled={isPending}
            data-testid="edit-cancel"
          >
            {voicePatch ? "Close" : "Cancel"}
          </Button>
          <Button
            type="submit"
            disabled={isPending || !_hasChanges() || !name.trim()}
            data-testid="edit-save"
          >
            {isPending ? (
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

/**
 * SESSION 174 — telemetry banner for the change-voice action's
 * `voice_patch` envelope. Renders one of three states:
 *
 *   - `ok` (green) — live Runway PATCH succeeded; the new voice
 *     is active immediately on the existing avatar.
 *   - `skipped` (muted) — there was no live Runway avatar to
 *     PATCH (avatar wasn't baked yet). The DB row carries the
 *     new voice; the next bake picks it up.
 *   - `failed` (destructive) — the live PATCH was rejected. The
 *     DB row still carries the new voice (so the next bake uses
 *     it), but the existing avatar still has the old voice.
 *     Error message surfaces verbatim.
 *
 * Any other status (`unknown`, server contract drift) renders as
 * a muted info banner with the raw status string.
 */
function VoicePatchBanner({
  voicePatch,
}: {
  voicePatch: ChangeVoiceResponse["voice_patch"];
}) {
  if (voicePatch.status === "ok") {
    return (
      <div
        data-testid="voice-patch-banner"
        data-status="ok"
        className="flex items-start gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3 text-xs text-emerald-700 dark:text-emerald-300"
      >
        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <span>
          Voice updated on the live avatar. The new preset takes effect
          on the next render.
        </span>
      </div>
    );
  }
  if (voicePatch.status === "skipped") {
    return (
      <div
        data-testid="voice-patch-banner"
        data-status="skipped"
        className="flex items-start gap-2 rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground"
      >
        <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <span>
          Voice saved to the row. No live avatar exists yet — the next
          bake will use the new preset.
        </span>
      </div>
    );
  }
  if (voicePatch.status === "failed") {
    return (
      <div
        data-testid="voice-patch-banner"
        data-status="failed"
        className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive"
      >
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <div className="flex flex-col gap-1">
          <strong>Runway rejected the voice change.</strong>
          <span>
            The new preset is saved on the row (the next avatar bake
            will pick it up) but the live avatar still has the previous
            voice.
          </span>
          {voicePatch.error && (
            <span className="opacity-80">Details: {voicePatch.error}</span>
          )}
        </div>
      </div>
    );
  }
  return (
    <div
      data-testid="voice-patch-banner"
      data-status={voicePatch.status}
      className="flex items-start gap-2 rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground"
    >
      <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
      <span>Voice update status: {voicePatch.status}</span>
    </div>
  );
}
