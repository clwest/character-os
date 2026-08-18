/**
 * Narrative memory panels — SESSION 264 Slice 1.
 *
 * Three exports:
 *
 *   * NarrativeMemoryPromotePanel({composition, episode})
 *       Rendered on the Composition detail page. Lets the operator
 *       promote turns/facts from an accepted Composition into
 *       durable NarrativeMemory rows. Only rendered when the
 *       Composition is Episode-attached (episode !== null).
 *
 *   * NarrativeMemoryList({filter, showSource})
 *       Rendered as a tab on Episode and Universe detail pages.
 *       Lists memories with per-row archive action. `filter`
 *       accepts either {episodeId} or {universeId}. `showSource`
 *       renders the source-composition link + kind badges (for
 *       Universe view which spans Episodes).
 *
 * Load-bearing rules mirrored from the audit (SESSION 264):
 *
 * - Promotion is EXPLICIT. Nothing auto-promotes.
 * - Never mutates canon (KnowledgeDocument). The panel talks only
 *   to /api/narrative-memories/ and the composition promote action.
 * - Retrieval integration is Slice 2; this panel is a write +
 *   inspect surface only.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Trash2, ArchiveRestore, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import type { EpisodeCastMember } from "@/lib/api/episodes";
import { useEpisode } from "@/lib/api/episodes";
import {
  NARRATIVE_MEMORY_KINDS,
  NARRATIVE_MEMORY_WEIGHTS,
  usePromoteMemories,
  useNarrativeMemoriesByComposition,
  useNarrativeMemoriesByEpisode,
  useNarrativeMemoriesByUniverse,
  useArchiveMemory,
  useUnarchiveMemory,
  type NarrativeMemory,
  type NarrativeMemoryKind,
  type NarrativeMemoryWeight,
} from "@/lib/api/narrative-memories";


// ============================================================
// Promote panel — for Composition detail page.
// ============================================================

interface NarrativeMemoryPromotePanelProps {
  compositionId: string;
  episodeId: string;
}

export function NarrativeMemoryPromotePanel({
  compositionId,
  episodeId,
}: NarrativeMemoryPromotePanelProps) {
  const episodeQ = useEpisode(episodeId);
  const memoriesQ = useNarrativeMemoriesByComposition(compositionId);
  const cast = episodeQ.data?.cast ?? [];
  const promote = usePromoteMemories(compositionId);
  const archive = useArchiveMemory();

  const [body, setBody] = useState("");
  const [kind, setKind] = useState<NarrativeMemoryKind>("event");
  const [weight, setWeight] = useState<NarrativeMemoryWeight>("peripheral");
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
      setError("Memory body cannot be blank.");
      return;
    }
    try {
      await promote.mutateAsync({
        episode: episodeId,
        memories: [
          {
            body: stripped,
            kind,
            weight,
            witnessed_by: witnesses,
          },
        ],
      });
      setBody("");
      setKind("event");
      setWeight("peripheral");
      setWitnesses([]);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        return;
      }
      throw err;
    }
  }

  return (
    <section
      className="flex flex-col gap-4 rounded-md border bg-card p-5 text-sm shadow-paper"
      data-testid="composition-promote-narrative-memory"
    >
      <header className="flex items-baseline justify-between border-b pb-2">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Narrative memory
          </span>
          <h3 className="font-display text-lg text-foreground">
            Promote to durable story history
          </h3>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {memoriesQ.data?.length ?? 0} promoted from this render
        </span>
      </header>
      <p className="text-xs text-muted-foreground">
        Explicit-only. Promotions never mutate Universe canon. Rows land
        on this Episode and are retrievable in Slice 2. Wide default is{" "}
        <em>whole cast witnessed</em>; narrow by picking specific witnesses.
      </p>

      <div className="flex flex-col gap-3">
        <label htmlFor="nm-body" className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Body
        </label>
        <textarea
          id="nm-body"
          className="min-h-[80px] rounded-md border border-fog/30 bg-black/20 px-3 py-2 text-foreground"
          value={body}
          onChange={(ev) => setBody(ev.target.value)}
          placeholder="e.g. Patch connected an AI agent to workshop tools and the printer started a job he did not queue."
          data-testid="nm-body"
        />

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="nm-kind" className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Kind
            </label>
            <select
              id="nm-kind"
              value={kind}
              onChange={(ev) => setKind(ev.target.value as NarrativeMemoryKind)}
              className="rounded-md border border-fog/30 bg-black/20 px-2 py-1.5 text-foreground"
              data-testid="nm-kind"
            >
              {NARRATIVE_MEMORY_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="nm-weight" className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Weight
            </label>
            <select
              id="nm-weight"
              value={weight}
              onChange={(ev) =>
                setWeight(ev.target.value as NarrativeMemoryWeight)
              }
              className="rounded-md border border-fog/30 bg-black/20 px-2 py-1.5 text-foreground"
              data-testid="nm-weight"
            >
              {NARRATIVE_MEMORY_WEIGHTS.map((w) => (
                <option key={w} value={w}>
                  {w}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2 md:col-span-2 flex flex-col gap-1">
            <label className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Witnessed by
            </label>
            <div className="flex flex-wrap gap-1">
              {cast.length === 0 && (
                <span className="text-xs italic text-muted-foreground">
                  Episode has no cast yet.
                </span>
              )}
              {cast.map((tm: EpisodeCastMember) => {
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
                    data-testid={`nm-witness-toggle-${tm.id}`}
                  >
                    {tm.name}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-muted-foreground italic">
              Empty = whole cast. Only Episode cast members are eligible.
            </p>
          </div>
        </div>

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
          Promoted from this render
        </span>
        <ul className="mt-2 flex flex-col gap-2">
          {(memoriesQ.data ?? []).length === 0 && (
            <li className="text-xs italic text-muted-foreground">
              Nothing promoted yet.
            </li>
          )}
          {(memoriesQ.data ?? []).map((m) => (
            <li
              key={m.id}
              className="flex items-start justify-between gap-3 rounded border border-fog/20 bg-black/10 px-3 py-2"
              data-testid={`nm-row-${m.id}`}
            >
              <div className="flex flex-col gap-1">
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {m.kind.replace("_", " ")} · {m.weight}
                </span>
                <span className="text-sm text-foreground">{m.body}</span>
                {m.witnessed_by.length > 0 && (
                  <span className="text-[10px] italic text-muted-foreground">
                    witnessed by:{" "}
                    {m.witnessed_by.map((w) => w.name).join(", ")}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => archive.mutateAsync(m.id)}
                aria-label="archive memory"
                className="text-fog transition-colors hover:text-destructive"
                data-testid={`nm-archive-${m.id}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}


// ============================================================
// List — for Episode and Universe detail pages.
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
  title = "Memories",
  emptyLabel = "No memories promoted yet.",
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

  const archive = useArchiveMemory();
  const unarchive = useUnarchiveMemory();

  const rows = q.data ?? [];

  return (
    <section
      className="flex flex-col gap-4 rounded-md border bg-card p-5 text-sm shadow-paper"
      data-testid="narrative-memory-list"
    >
      <header className="flex items-baseline justify-between border-b pb-2">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Narrative memory
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
            archived
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
          Failed to load memories.
        </p>
      )}
      {!q.isLoading && rows.length === 0 && (
        <p className="text-xs italic text-muted-foreground">{emptyLabel}</p>
      )}
      <ul className="flex flex-col gap-2">
        {rows.map((m) => (
          <MemoryRow
            key={m.id}
            memory={m}
            showSource={showSource}
            onArchive={() => archive.mutateAsync(m.id)}
            onUnarchive={() => unarchive.mutateAsync(m.id)}
          />
        ))}
      </ul>
    </section>
  );
}


function MemoryRow({
  memory,
  showSource,
  onArchive,
  onUnarchive,
}: {
  memory: NarrativeMemory;
  showSource: boolean;
  onArchive: () => Promise<unknown>;
  onUnarchive: () => Promise<unknown>;
}) {
  const isArchived = memory.status === "archived" || !!memory.archived_at;
  const isSuperseded = memory.status === "superseded";
  return (
    <li
      className={
        "flex items-start justify-between gap-3 rounded border border-fog/20 bg-black/10 px-3 py-2 " +
        (isArchived || isSuperseded ? "opacity-60" : "")
      }
      data-testid={`nm-row-${memory.id}`}
    >
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          <span>{memory.kind.replace("_", " ")}</span>
          <span>·</span>
          <span>{memory.weight}</span>
          {isArchived && (
            <span className="rounded bg-fog/20 px-1.5 py-0.5 text-destructive">
              archived
            </span>
          )}
          {isSuperseded && (
            <span className="rounded bg-fog/20 px-1.5 py-0.5">
              superseded
            </span>
          )}
        </div>
        <span className="text-sm text-foreground">{memory.body}</span>
        {memory.witnessed_by.length > 0 && (
          <span className="text-[10px] italic text-muted-foreground">
            witnessed by: {memory.witnessed_by.map((w) => w.name).join(", ")}
          </span>
        )}
        {showSource && (
          <span className="text-[10px] italic text-muted-foreground">
            from Episode{" "}
            <Link
              to={`/workspace/episodes/${memory.episode}`}
              className="text-gold hover:underline"
            >
              {memory.episode_title || memory.episode.slice(0, 8)}
            </Link>{" "}
            · Composition{" "}
            <Link
              to={`/compositions/${memory.source_composition}`}
              className="text-gold hover:underline"
            >
              {memory.source_composition_name ||
                memory.source_composition.slice(0, 8)}
            </Link>
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {isArchived ? (
          <button
            type="button"
            onClick={() => onUnarchive()}
            aria-label="unarchive memory"
            className="text-fog transition-colors hover:text-gold"
            data-testid={`nm-unarchive-${memory.id}`}
          >
            <ArchiveRestore className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onArchive()}
            aria-label="archive memory"
            className="text-fog transition-colors hover:text-destructive"
            data-testid={`nm-archive-${memory.id}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </li>
  );
}
