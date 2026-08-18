/**
 * /workspace/episodes/:id — Episode detail.
 *
 * SESSION 262 / EPISODE_SCHEMA_V1. Backend surface:
 * shell/apps/universe/views.py::EpisodeViewSet.
 *
 * Load-bearing:
 * - Editing Episode.operator_topic here does NOT propagate to attached
 *   Compositions (their SESSION 262 observability is immutable-once-set).
 * - Cast is operator-authoritative; the SPA never auto-populates.
 * - Composition creation from this page pre-fills `episode` on the
 *   recipe form.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft, Trash2, ArchiveRestore, Film, Play, Loader2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionHeader } from "@/components/editorial";
import {
  useEpisode,
  useUpdateEpisode,
  useArchiveEpisode,
  useUnarchiveEpisode,
  useHardDeleteEpisode,
  useAddCastMember,
  useRemoveCastMember,
} from "@/lib/api/episodes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import {
  useCompositionsForEpisode,
  type CompositionRow,
} from "@/lib/api/recipes";
import { ApiError } from "@/lib/api/client";


export function EpisodeDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const episode = useEpisode(id);
  const spokespeople = useSpokespeople();

  const universeId = episode.data?.universe;
  const update = useUpdateEpisode(universeId);
  const archive = useArchiveEpisode(universeId);
  const unarchive = useUnarchiveEpisode(universeId);
  const hardDelete = useHardDeleteEpisode(universeId);
  const addCast = useAddCastMember(id);
  const removeCast = useRemoveCastMember(id);
  // SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — attached
  // Compositions list. Backend ?episode= filter returns only the
  // renders that FK'd this Episode.
  const compositions = useCompositionsForEpisode(id);

  const [title, setTitle] = useState("");
  const [operatorTopic, setOperatorTopic] = useState("");
  const [dirty, setDirty] = useState(false);
  const [castPick, setCastPick] = useState("");

  const e = episode.data;
  useEffect(() => {
    if (e && !dirty) {
      setTitle(e.title);
      setOperatorTopic(e.operator_topic);
    }
  }, [e?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Only Teammates in this Episode's Universe can be added as cast.
  const eligibleTeammates = (spokespeople.data ?? []).filter(
    (sp) => sp.universe === universeId,
  );
  const castIds = new Set((e?.cast ?? []).map((c) => c.id));
  const pickable = eligibleTeammates.filter((t) => !castIds.has(t.id));

  async function handleSave() {
    if (!e) return;
    try {
      await update.mutateAsync({
        id: e.id,
        payload: {
          title: title.trim() || e.title,
          operator_topic: operatorTopic,
        },
      });
      setDirty(false);
    } catch (err) {
      console.error("episode update failed", err);
    }
  }

  async function handleArchive() {
    if (!e) return;
    if (!confirm(`Archive "${e.title}"?`)) return;
    await archive.mutateAsync(e.id);
    navigate(`/workspace/universes/${universeId}/episodes`);
  }

  async function handleUnarchive() {
    if (!e) return;
    await unarchive.mutateAsync(e.id);
  }

  async function handleHardDelete() {
    if (!e) return;
    if (!confirm(`Hard-delete "${e.title}"? This cannot be undone.`)) return;
    try {
      await hardDelete.mutateAsync(e.id);
      navigate(`/workspace/universes/${universeId}/episodes`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        alert(
          "This Episode has attached Compositions. Detach them (or " +
            "archive instead) before hard-deleting."
        );
        return;
      }
      throw err;
    }
  }

  async function handleAddCast() {
    if (!castPick) return;
    try {
      await addCast.mutateAsync(castPick);
      setCastPick("");
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
        return;
      }
      throw err;
    }
  }

  async function handleRemoveCast(teammateId: string) {
    await removeCast.mutateAsync(teammateId);
  }

  if (episode.isLoading) {
    return <div className="p-8 text-mist">Loading…</div>;
  }
  if (!e) {
    return <div className="p-8 text-mist">Episode not found.</div>;
  }

  const isArchived = !!e.archived_at;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() =>
            navigate(`/workspace/universes/${universeId}/episodes`)
          }
        >
          <ChevronLeft className="h-4 w-4" />
          Back to episodes
        </button>
        <SectionHeader number={1} title="Episode" />
        <h1
          data-testid="episode-title"
          className="font-display text-3xl leading-tight tracking-tight text-cream md:text-4xl"
        >
          {e.title}
          {isArchived && (
            <span className="ml-3 text-sm text-fog italic">(archived)</span>
          )}
        </h1>
        <p className="text-sm text-mist">
          in Universe{" "}
          <Link
            to={`/workspace/universes/${universeId}`}
            className="italic text-gold hover:underline"
          >
            {e.universe_name ?? universeId}
          </Link>{" "}
          · {e.composition_count} composition
          {e.composition_count === 1 ? "" : "s"}
        </p>
      </header>

      <section className="flex flex-col gap-4">
        <Label htmlFor="ep-title">Title</Label>
        <Input
          id="ep-title"
          value={title}
          onChange={(ev) => {
            setTitle(ev.target.value);
            setDirty(true);
          }}
        />
        <Label htmlFor="ep-topic">Operator topic (story-authoritative)</Label>
        <textarea
          id="ep-topic"
          className="min-h-[120px] rounded-md border border-fog/30 bg-black/30 px-3 py-2 text-cream"
          value={operatorTopic}
          onChange={(ev) => {
            setOperatorTopic(ev.target.value);
            setDirty(true);
          }}
        />
        <p className="text-xs text-fog">
          Editing story intent here does <strong>not</strong> mutate the
          verbatim topic on any already-rendered Composition — that
          per-attempt copy is immutable (SESSION 262).
        </p>
        {dirty && (
          <div>
            <Button type="button" onClick={handleSave}>
              Save story metadata
            </Button>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <SectionHeader number={2} title="Cast" />
        <p className="text-sm text-mist">
          Operator-declared characters in this story. Only Teammates in this
          Universe may join.
        </p>
        {e.cast.length === 0 && (
          <p className="text-sm italic text-fog">Cast is empty.</p>
        )}
        <ul className="flex flex-wrap gap-2">
          {e.cast.map((c) => (
            <li
              key={c.id}
              className="inline-flex items-center gap-2 rounded-full border border-fog/40 px-3 py-1 text-sm text-cream"
            >
              {c.name}
              <button
                type="button"
                aria-label={`remove ${c.name}`}
                onClick={() => handleRemoveCast(c.id)}
                className="text-fog hover:text-gold"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
        {pickable.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={castPick}
              onChange={(ev) => setCastPick(ev.target.value)}
              className="rounded-md border border-fog/30 bg-black/30 px-3 py-2 text-cream"
            >
              <option value="">Pick a Teammate…</option>
              {pickable.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <Button
              type="button"
              onClick={handleAddCast}
              disabled={!castPick || addCast.isPending}
            >
              Add to cast
            </Button>
          </div>
        )}
      </section>

      {/* SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — versions
          list. Attached Compositions rendered inline so the
          operator sees this Episode's history at a glance instead
          of a bare count. Each row: name + kind + duration + status
          + created-at + Open + Make-another-version. */}
      <EpisodeVersionsSection
        episodeId={e.id}
        episodeCastCount={e.cast.length}
        loading={compositions.isLoading}
        error={compositions.error}
        rows={compositions.data ?? []}
      />

      {/* SESSION 262 — primary "render under this Episode" CTA.
          Suggests dialogue_scene when the cast has ≥2 members
          (matches the recipe's cast contract), otherwise routes
          to the recipe gallery so the operator picks. The
          `?episode=<id>` query param propagates through the
          recipe form and lands on the Composition's episode FK
          at create. */}
      {!isArchived && (
        <section className="rounded-md border border-luxe bg-card/60 p-6">
          <h2 className="mb-2 font-display text-2xl tracking-tight text-cream">
            Render under this Episode
          </h2>
          <p className="mb-3 text-sm text-mist">
            The story intent and cast above pre-scope every render
            you create from here. The resulting Composition attaches
            to this Episode automatically.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            {e.cast.length >= 2 ? (
              <Button asChild data-testid="episode-render-dialogue-cta">
                <Link to={`/recipes/dialogue_scene?episode=${e.id}`}>
                  <Film className="mr-2 h-4 w-4" />
                  New dialogue scene
                </Link>
              </Button>
            ) : (
              <Button asChild data-testid="episode-render-talking-cta">
                <Link to={`/recipes/talking_head?episode=${e.id}`}>
                  <Film className="mr-2 h-4 w-4" />
                  New talking head
                </Link>
              </Button>
            )}
            <Button
              asChild
              variant="secondary"
              data-testid="episode-render-any-cta"
            >
              <Link to={`/recipes?episode=${e.id}`}>Choose another recipe</Link>
            </Button>
          </div>
          {e.cast.length < 2 && (
            <p className="mt-2 text-xs text-fog">
              Add a second cast member above to enable dialogue-scene
              renders.
            </p>
          )}
        </section>
      )}

      <section className="flex items-center gap-3">
        {!isArchived ? (
          <>
            <Button
              type="button"
              variant="secondary"
              onClick={handleArchive}
            >
              Archive
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleHardDelete}
              disabled={e.composition_count > 0}
              title={
                e.composition_count > 0
                  ? "Detach every Composition before hard-deleting."
                  : "Permanently delete this empty Episode."
              }
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Hard-delete
            </Button>
          </>
        ) : (
          <Button type="button" onClick={handleUnarchive}>
            <ArchiveRestore className="mr-2 h-4 w-4" />
            Unarchive
          </Button>
        )}
      </section>
    </div>
  );
}


// SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — versions section.
// Renders each Composition attached to the Episode as a compact
// row with the fields SESSION 262 CompositionListSerializer
// surfaces (name, template_kind, status, target_duration_seconds,
// created_at). "Open" navigates to the Composition detail;
// "Make another version" relaunches the same recipe with
// `?episode=<id>` so the Episode-driven recipe form re-applies
// its prefills. Empty state teaches the operator that the
// section will populate as they render.
function EpisodeVersionsSection({
  episodeId,
  episodeCastCount,
  loading,
  error,
  rows,
}: {
  episodeId: string;
  episodeCastCount: number;
  loading: boolean;
  error: unknown;
  rows: CompositionRow[];
}) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border border-luxe bg-card/60 p-6"
      data-testid="episode-versions-section"
    >
      <div className="flex items-baseline justify-between">
        <h2 className="font-display text-2xl tracking-tight text-cream">
          Renders{" "}
          <span className="text-fog text-sm">({rows.length})</span>
        </h2>
      </div>
      <p className="text-sm text-mist">
        Every render created under this Episode appears here. Retry,
        cutdown, aspect variant, or backdrop swap — all versions
        share this story's intent + cast.
      </p>

      {loading && (
        <p className="flex items-center gap-2 text-sm text-fog">
          <Loader2 className="h-3 w-3 animate-spin" /> Loading…
        </p>
      )}
      {!loading && error !== null && error !== undefined && (
        <p className="text-sm text-destructive">
          Could not load renders: {String(error)}
        </p>
      )}
      {!loading && !error && rows.length === 0 && (
        <p className="text-sm italic text-fog">
          No renders yet. Use the CTA below to create the first one.
        </p>
      )}
      {rows.length > 0 && (
        <ul
          className="flex flex-col divide-y divide-luxe rounded-md border border-luxe bg-card"
          data-testid="episode-versions-list"
        >
          {rows.map((row) => (
            <EpisodeVersionRow
              key={row.id}
              row={row}
              episodeId={episodeId}
              episodeCastCount={episodeCastCount}
            />
          ))}
        </ul>
      )}
    </section>
  );
}


function EpisodeVersionRow({
  row,
  episodeId,
  episodeCastCount,
}: {
  row: CompositionRow;
  episodeId: string;
  episodeCastCount: number;
}) {
  // Same-recipe "make another version" — routes into the recipe
  // form with the Episode context preserved so topic + cast pre-
  // fill and the FK attaches on submit.
  const relaunchHref = `/recipes/${row.template_kind}?episode=${episodeId}`;
  const requestedDurationLabel = row.target_duration_seconds
    ? `${row.target_duration_seconds}s`
    : null;
  const statusClass = statusColorClass(row.status);
  // Talking-head-family recipes need only 1 cast; dialogue-family
  // needs 2. When the Episode's cast dropped below the recipe's
  // requirement (rare — operator removed a member post-render),
  // the "make another version" link is presented as an
  // insufficient-cast hint rather than a live link.
  const dialogueFamily = row.template_kind === "dialogue_scene";
  const hasSufficientCastForRelaunch = dialogueFamily
    ? episodeCastCount >= 2
    : episodeCastCount >= 1;

  return (
    <li
      className="flex items-baseline justify-between gap-4 px-4 py-3 text-sm"
      data-testid={`episode-version-row-${row.id}`}
    >
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span
            className={
              "inline-block rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] " +
              statusClass
            }
            data-testid={`episode-version-status-${row.id}`}
          >
            {row.status}
          </span>
          <span className="truncate font-medium text-cream">{row.name}</span>
        </div>
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
          <span>{row.template_kind}</span>
          {requestedDurationLabel && <span>· {requestedDurationLabel} target</span>}
          <span>· {formatShortDate(row.created_at)}</span>
          {row.mock_mode && <span>· mock</span>}
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-3">
        <Link
          to={`/compositions/${row.id}`}
          className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.22em] text-fog hover:text-gold"
          data-testid={`episode-version-open-${row.id}`}
        >
          <Play className="h-3 w-3" /> Open
        </Link>
        {hasSufficientCastForRelaunch ? (
          <Link
            to={relaunchHref}
            className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.22em] text-fog hover:text-gold"
            data-testid={`episode-version-relaunch-${row.id}`}
          >
            <Film className="h-3 w-3" /> Make another version
          </Link>
        ) : (
          <span
            className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog/50"
            title="Add cast to Episode to relaunch this recipe."
          >
            (add cast to relaunch)
          </span>
        )}
      </div>
    </li>
  );
}

function statusColorClass(status: string): string {
  switch (status) {
    case "completed":
      return "border-success/40 bg-success/5 text-success";
    case "failed":
      return "border-destructive/40 bg-destructive/5 text-destructive";
    case "partial":
      return "border-warning/40 bg-warning/5 text-warning";
    case "running":
      return "border-accent/40 bg-accent/10 text-accent";
    default:
      return "border-fog/30 text-fog";
  }
}

function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
