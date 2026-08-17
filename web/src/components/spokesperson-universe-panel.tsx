/**
 * SpokespersonUniversePanel — SESSION 261 SPA slice.
 *
 * Assign a teammate to a Universe (or detach to legacy). Load-
 * bearing UX: before PATCHing, the SPA queries
 * ``universe-move-preview`` to surface any KnowledgeDocument M2M
 * attach rows that would become cross-Universe. If non-empty, the
 * confirm modal enumerates the offending rows and the operator
 * must ack before the PATCH proceeds — otherwise the PATCH would
 * reject at the serializer layer.
 */
import { useEffect, useState } from "react";
import { Globe2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/api/workspaces";
import {
  UNIVERSE_LEGACY_SENTINEL,
  useUniverses,
} from "@/lib/api/universes";
import {
  fetchUniverseMovePreview,
  updateSpokesperson,
  type Spokesperson,
  type UniverseMovePreview,
} from "@/lib/api/spokespeople";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/client";


export interface SpokespersonUniversePanelProps {
  spokesperson: Spokesperson;
}

/** Convert the SPA select value to the payload universe field. */
function toPayload(value: string): string | null {
  return value === UNIVERSE_LEGACY_SENTINEL ? null : value;
}

/** Inverse: payload universe -> select value for controlled inputs. */
function fromPayload(v: string | null): string {
  return v === null ? UNIVERSE_LEGACY_SENTINEL : v;
}


export function SpokespersonUniversePanel({
  spokesperson,
}: SpokespersonUniversePanelProps) {
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const universes = useUniverses(workspaceId);
  const qc = useQueryClient();

  const currentValue = fromPayload(spokesperson.universe);
  const [pendingValue, setPendingValue] = useState<string>(currentValue);
  const [preview, setPreview] = useState<UniverseMovePreview | null>(null);
  const [isSaving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPendingValue(currentValue);
  }, [currentValue]);

  const dirty = pendingValue !== currentValue;
  const options = universes.data ?? [];

  async function handleSave() {
    setError(null);
    const targetPayload = toPayload(pendingValue);
    // Pre-flight universe-move-preview. If offending rows, the
    // preview modal below intercepts submit.
    try {
      const p = await fetchUniverseMovePreview(spokesperson.id, targetPayload);
      if (p.offending_documents.length > 0) {
        setPreview(p);
        return;
      }
    } catch (err) {
      // If preview fails, still let the operator try — the PATCH
      // will surface a clean 400 with the offending rows.
      console.warn("universe-move-preview failed; proceeding to PATCH", err);
    }
    await performPatch(targetPayload);
  }

  async function performPatch(target: string | null) {
    setSaving(true);
    try {
      await updateSpokesperson({ id: spokesperson.id, universe: target });
      qc.invalidateQueries({ queryKey: ["spokesperson", spokesperson.id] });
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
      qc.invalidateQueries({ queryKey: ["universes", "list"] });
      setPreview(null);
    } catch (err) {
      setError(readableError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      data-testid="spokesperson-universe-panel"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <div className="mb-4 flex items-center gap-2">
        <Globe2 className="h-5 w-5 text-gold" />
        <h2 className="font-display text-2xl tracking-tight text-cream">
          Universe
        </h2>
      </div>
      <p className="mb-4 text-sm text-mist">
        Scope this teammate to a world so their knowledge stays inside it.
        Pick "None (legacy)" to keep pre-Universe workspace-wide behavior.
      </p>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="teammate-universe">World / Universe</Label>
          <select
            id="teammate-universe"
            data-testid="teammate-universe-select"
            value={pendingValue}
            onChange={(e) => setPendingValue(e.target.value)}
            disabled={universes.isLoading || isSaving}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value={UNIVERSE_LEGACY_SENTINEL}>None (legacy)</option>
            {options.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <p className="text-sm text-destructive" data-testid="teammate-universe-error">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          <Button
            type="button"
            data-testid="teammate-universe-save"
            onClick={handleSave}
            disabled={!dirty || isSaving}
          >
            {isSaving ? "Saving…" : "Save"}
          </Button>
          {dirty && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => setPendingValue(currentValue)}
              disabled={isSaving}
            >
              Reset
            </Button>
          )}
        </div>
      </div>

      {preview && (
        <UniverseMovePreviewModal
          preview={preview}
          onCancel={() => setPreview(null)}
          onConfirm={() => performPatch(toPayload(pendingValue))}
          working={isSaving}
        />
      )}
    </section>
  );
}


function UniverseMovePreviewModal({
  preview,
  onCancel,
  onConfirm,
  working,
}: {
  preview: UniverseMovePreview;
  onCancel: () => void;
  onConfirm: () => void;
  working: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      data-testid="universe-move-preview-modal"
    >
      <div className="w-full max-w-lg rounded-lg border border-luxe bg-background p-6 shadow-xl">
        <h3 className="font-display text-2xl tracking-tight text-cream">
          Reassigning would orphan {preview.offending_documents.length} doc attachment
          {preview.offending_documents.length === 1 ? "" : "s"}
        </h3>
        <p className="mt-2 text-sm text-mist">
          The following documents are attached to this teammate but belong to
          a different world. If you proceed, this teammate will no longer see
          those docs in retrieval. You can reassign the docs first if you
          want to keep them accessible.
        </p>
        <ul
          data-testid="universe-move-offending"
          className="mt-4 max-h-56 divide-y divide-luxe overflow-y-auto rounded-md border border-luxe bg-card"
        >
          {preview.offending_documents.map((d) => (
            <li key={d.id} className="px-4 py-2 text-sm text-cream">
              {d.title}
            </li>
          ))}
        </ul>
        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={working}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={working}
            data-testid="universe-move-confirm"
          >
            {working ? "Saving…" : "Reassign anyway"}
          </Button>
        </div>
      </div>
    </div>
  );
}


function readableError(err: unknown): string {
  if (err instanceof ApiError) {
    const body = err.body;
    if (typeof body === "object" && body !== null) {
      const messages: string[] = [];
      for (const [k, v] of Object.entries(body)) {
        if (Array.isArray(v)) {
          messages.push(...v.map((m) => `${k}: ${String(m)}`));
        } else if (typeof v === "string") {
          messages.push(`${k}: ${v}`);
        }
      }
      if (messages.length > 0) return messages.join("\n");
    }
    return err.message;
  }
  return String(err);
}
