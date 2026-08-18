/**
 * Narrative memory panels — SESSION 264 Slice 1
 * (dogfood UX correction: creator language over data-model language).
 *
 * Three exports:
 *
 *   * NarrativeMemoryPromotePanel({compositionId, episodeId})
 *       Rendered on the Composition detail page. Creator-facing
 *       "Remember this" form + "Story history" recap. Only
 *       rendered when the Composition is Episode-attached.
 *
 *   * NarrativeMemoryList({filter, showSource})
 *       Rendered as a section on Episode and Universe detail
 *       pages. `filter` accepts either {episodeId} or {universeId}.
 *       `showSource` renders the source-composition link for the
 *       Universe view which spans Episodes. Uses "Forget" instead
 *       of "archive" as the creator-facing action.
 *
 * Backend invariants preserved by this UX (audit §16):
 *
 * - Generated != remembered. Nothing lands until the creator
 *   presses "Remember this".
 * - Remembered != canon. This panel never touches
 *   KnowledgeDocument.
 * - Provenance intact. The composition/episode FKs on the
 *   POST body come from props.
 * - Witness semantics intact. "Everyone in this episode" ↔
 *   empty witnessed_by (whole-cast convention); "Choose
 *   characters..." ↔ explicit teammate ids.
 *
 * Internal-only concepts kept out of the creator UI (per SESSION
 * 264 dogfood correction): "promotion", "durable", "row",
 * "retrieval", "Slice 2", "kind", "weight", "peripheral", "M2M",
 * "synthesis artifact". Those remain in the backend, the audit
 * doc, and the admin surface — not in the creator flow.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Trash2, ArchiveRestore, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { useEpisode } from "@/lib/api/episodes";
import {
  usePromoteMemories,
  useNarrativeMemoriesByComposition,
  useNarrativeMemoriesByEpisode,
  useNarrativeMemoriesByUniverse,
  useArchiveMemory,
  useUnarchiveMemory,
  type NarrativeMemory,
} from "@/lib/api/narrative-memories";


// ============================================================
// "Remember this" — Composition detail promote panel.
// ============================================================

interface NarrativeMemoryPromotePanelProps {
  compositionId: string;
  episodeId: string;
}

type WitnessMode = "everyone" | "some";

export function NarrativeMemoryPromotePanel({
  compositionId,
  episodeId,
}: NarrativeMemoryPromotePanelProps) {
  const episodeQ = useEpisode(episodeId);
  const memoriesQ = useNarrativeMemoriesByComposition(compositionId);
  const cast = episodeQ.data?.cast ?? [];
  const promote = usePromoteMemories(compositionId);

  const [body, setBody] = useState("");
  // "everyone" (default) maps to empty witnessed_by → whole-cast
  // convention on the backend. "some" reveals the cast toggles
  // and only sends explicit ids.
  const [witnessMode, setWitnessMode] = useState<WitnessMode>("everyone");
  const [witnesses, setWitnesses] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function toggleWitness(id: string) {
    setWitnesses((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  async function handleSubmit() {
    setError(null);
    const stripped = body.trim();
    if (!stripped) {
      setError("Tell us what happened first.");
      return;
    }
    if (witnessMode === "some" && witnesses.length === 0) {
      setError(
        "Pick at least one character, or switch to Everyone in this episode.",
      );
      return;
    }
    try {
      await promote.mutateAsync({
        episode: episodeId,
        memories: [
          {
            body: stripped,
            // Kind and weight are internal defaults for the
            // creator flow (see SESSION 264 dogfood correction).
            // Omitting them here lets the backend serializer
            // apply kind=event / weight=peripheral defaults,
            // which is the whole-cast v1 shape.
            witnessed_by: witnessMode === "everyone" ? [] : witnesses,
          },
        ],
      });
      setBody("");
      setWitnessMode("everyone");
      setWitnesses([]);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        return;
      }
      throw err;
    }
  }

  const remembered = memoriesQ.data ?? [];

  return (
    <section
      className="flex flex-col gap-4 rounded-md border bg-card p-5 text-sm shadow-paper"
      data-testid="composition-remember-this"
    >
      <header className="flex flex-col gap-1 border-b pb-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Story history
        </span>
        <h3 className="font-display text-lg text-foreground">Remember this</h3>
        <p className="text-xs text-muted-foreground">
          Save something that happened in this episode so the characters can
          remember it later.
        </p>
      </header>

      <div className="flex flex-col gap-3">
        <label
          htmlFor="nm-body"
          className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          What happened?
        </label>
        <textarea
          id="nm-body"
          className="min-h-[80px] rounded-md border border-fog/30 bg-black/20 px-3 py-2 text-foreground"
          value={body}
          onChange={(ev) => setBody(ev.target.value)}
          placeholder="e.g. Patch connected an AI agent to the workshop tools and the printer started a job he did not queue."
          data-testid="nm-body"
        />

        <fieldset className="flex flex-col gap-2">
          <legend className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Who remembers this?
          </legend>
          <label
            className="flex items-center gap-2 text-foreground"
            data-testid="nm-witness-mode-everyone"
          >
            <input
              type="radio"
              name="nm-witness-mode"
              value="everyone"
              checked={witnessMode === "everyone"}
              onChange={() => {
                setWitnessMode("everyone");
                setWitnesses([]);
              }}
            />
            <span>Everyone in this episode</span>
          </label>
          <label
            className="flex items-center gap-2 text-foreground"
            data-testid="nm-witness-mode-some"
          >
            <input
              type="radio"
              name="nm-witness-mode"
              value="some"
              checked={witnessMode === "some"}
              onChange={() => setWitnessMode("some")}
            />
            <span>Choose characters&hellip;</span>
          </label>

          {witnessMode === "some" && (
            <div
              className="mt-1 flex flex-wrap gap-1 pl-6"
              data-testid="nm-witness-picker"
            >
              {cast.length === 0 && (
                <span className="text-xs italic text-muted-foreground">
                  This episode has no cast yet. Add characters to the episode
                  first.
                </span>
              )}
              {cast.map((tm) => {
                const active = witnesses.includes(tm.id);
                return (
                  <button
                    key={tm.id}
                    type="button"
                    onClick={() => toggleWitness(tm.id)}
                    className={
                      "rounded-full border px-2.5 py-0.5 text-xs transition-colors " +
                      (active
                        ? "border-gold bg-gold/10 text-gold"
                        : "border-fog/30 text-muted-foreground hover:border-fog")
                    }
                    aria-pressed={active}
                    data-testid={`nm-witness-toggle-${tm.id}`}
                  >
                    {tm.name}
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>

        {error && (
          <p className="text-xs text-destructive" data-testid="nm-error">
            {error}
          </p>
        )}
        <div>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={promote.isPending || !body.trim()}
            data-testid="nm-submit"
          >
            {promote.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Plus className="mr-2 h-4 w-4" />
            )}
            Remember this
          </Button>
        </div>
      </div>

      <div className="border-t pt-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          What we remember from this render
        </span>
        <ul className="mt-2 flex flex-col gap-2" data-testid="nm-recap-list">
          {remembered.length === 0 && (
            <li
              className="text-xs italic text-muted-foreground"
              data-testid="nm-recap-empty"
            >
              Nothing remembered from this render yet.
            </li>
          )}
          {remembered.map((m) => (
            <MemoryRow
              key={m.id}
              memory={m}
              showSource={false}
              variant="compact"
            />
          ))}
        </ul>
      </div>
    </section>
  );
}


// ============================================================
// "Story history" list — Episode + Universe detail pages.
// ============================================================

type MemoryListFilter =
  | { episodeId: string; universeId?: never }
  | { universeId: string; episodeId?: never };

interface NarrativeMemoryListProps {
  filter: MemoryListFilter;
  /** When true, show the source-composition link + episode title
   *  (useful for Universe view which spans Episodes). */
  showSource?: boolean;
  title?: string;
  emptyLabel?: string;
}

export function NarrativeMemoryList({
  filter,
  showSource = false,
  title = "Story history",
  emptyLabel = "Nothing remembered yet.",
}: NarrativeMemoryListProps) {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [includeSuperseded, setIncludeSuperseded] = useState(false);

  // Two queries live under one component so callers don't have to
  // pick — but only one runs at a time (React Query's `enabled`
  // gate matches the filter shape).
  const byEpisode = useNarrativeMemoriesByEpisode(
    filter.episodeId,
    { includeArchived, includeSuperseded },
  );
  const byUniverse = useNarrativeMemoriesByUniverse(
    filter.universeId,
    { includeArchived, includeSuperseded },
  );
  const q = filter.episodeId ? byEpisode : byUniverse;

  const rows = q.data ?? [];

  return (
    <section
      className="flex flex-col gap-4 rounded-md border bg-card p-5 text-sm shadow-paper"
      data-testid="narrative-memory-list"
    >
      <header className="flex items-baseline justify-between border-b pb-2">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Story history
          </span>
          <h3 className="font-display text-lg text-foreground">{title}</h3>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(ev) => setIncludeArchived(ev.target.checked)}
              data-testid="nm-toggle-archived"
            />
            forgotten
          </label>
          <label className="inline-flex items-center gap-1">
            <input
              type="checkbox"
              checked={includeSuperseded}
              onChange={(ev) => setIncludeSuperseded(ev.target.checked)}
              data-testid="nm-toggle-superseded"
            />
            superseded
          </label>
        </div>
      </header>

      {q.isLoading && (
        <p className="text-xs italic text-muted-foreground">Loading…</p>
      )}
      {q.isError && (
        <p className="text-xs text-destructive">
          Couldn&rsquo;t load story history.
        </p>
      )}
      {!q.isLoading && rows.length === 0 && (
        <p className="text-xs italic text-muted-foreground">{emptyLabel}</p>
      )}
      <ul className="flex flex-col gap-2">
        {rows.map((m) => (
          <MemoryRow key={m.id} memory={m} showSource={showSource} />
        ))}
      </ul>
    </section>
  );
}


// ============================================================
// Shared memory row — used by promote-panel recap AND list views.
// Handles Forget / Restore actions inline.
// ============================================================

function MemoryRow({
  memory,
  showSource,
  variant = "full",
}: {
  memory: NarrativeMemory;
  showSource: boolean;
  variant?: "full" | "compact";
}) {
  const archive = useArchiveMemory();
  const unarchive = useUnarchiveMemory();

  const isArchived = memory.status === "archived" || !!memory.archived_at;
  const isSuperseded = memory.status === "superseded";
  const busy = archive.isPending || unarchive.isPending;

  async function handleForget() {
    if (busy) return;
    const confirmed =
      typeof window === "undefined"
        ? true
        : window.confirm(
            "Forget this memory? Characters will stop remembering it. " +
              "You can bring it back from the forgotten filter.",
          );
    if (!confirmed) return;
    try {
      await archive.mutateAsync(memory.id);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
        return;
      }
      throw err;
    }
  }

  async function handleRestore() {
    if (busy) return;
    try {
      await unarchive.mutateAsync(memory.id);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
        return;
      }
      throw err;
    }
  }

  const witnessLabel =
    memory.witnessed_by.length === 0
      ? "Everyone in the episode"
      : memory.witnessed_by.map((w) => w.name).join(", ");

  return (
    <li
      className={
        "flex items-start justify-between gap-3 rounded border border-fog/20 bg-black/10 px-3 py-2 " +
        (isArchived || isSuperseded ? "opacity-60" : "")
      }
      data-testid={`nm-row-${memory.id}`}
    >
      <div className="flex flex-col gap-1">
        <span className="text-sm text-foreground">{memory.body}</span>
        <span className="text-[10px] italic text-muted-foreground">
          Remembered by: {witnessLabel}
        </span>
        {isArchived && (
          <span className="text-[10px] italic text-destructive">
            Forgotten. Toggle the &ldquo;forgotten&rdquo; filter to bring it back.
          </span>
        )}
        {isSuperseded && (
          <span className="text-[10px] italic text-muted-foreground">
            Replaced by a later memory.
          </span>
        )}
        {showSource && variant === "full" && (
          <span className="text-[10px] italic text-muted-foreground">
            From episode{" "}
            <Link
              to={`/workspace/episodes/${memory.episode}`}
              className="text-gold hover:underline"
            >
              {memory.episode_title || memory.episode.slice(0, 8)}
            </Link>
            {memory.source_composition_name ? (
              <>
                {" "}· render{" "}
                <Link
                  to={`/compositions/${memory.source_composition}`}
                  className="text-gold hover:underline"
                >
                  {memory.source_composition_name}
                </Link>
              </>
            ) : null}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {isArchived ? (
          <button
            type="button"
            onClick={handleRestore}
            disabled={busy}
            aria-label="restore memory"
            title="Bring back"
            className="text-fog transition-colors hover:text-gold disabled:opacity-40"
            data-testid={`nm-restore-${memory.id}`}
          >
            <ArchiveRestore className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleForget}
            disabled={busy}
            aria-label="forget memory"
            title="Forget"
            className="text-fog transition-colors hover:text-destructive disabled:opacity-40"
            data-testid={`nm-forget-${memory.id}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </li>
  );
}
