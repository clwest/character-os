/**
 * /workspace/universes/:id/episodes — Episode list + create.
 *
 * SESSION 262 / EPISODE_SCHEMA_V1. Backend surface:
 * shell/apps/universe/views.py::EpisodeViewSet (list + create).
 *
 * SESSION 269 §12 — Create form now offers an inline cast picker
 * so a solo Episode can be assembled on ONE screen. Backend
 * accepts ``cast_ids`` in the create payload and attaches
 * atomically. Zero-cast draft creation remains allowed but the
 * scene CTAs on the Episode detail page block silent fall-through
 * (existing insufficientCast guard).
 *
 * Load-bearing:
 * - Episode creation is explicit-only.
 * - Standalone Composition workflow (no Episode) remains available
 *   from the recipe form elsewhere in the SPA.
 */
import { useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionHeader } from "@/components/editorial";
import { PossibleNextEpisodes } from "@/components/possible-next-episodes";
import { useUniverse } from "@/lib/api/universes";
import { useEpisodes, useCreateEpisode } from "@/lib/api/episodes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { ApiError } from "@/lib/api/client";


export function UniverseEpisodesRoute() {
  const { id: universeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const universe = useUniverse(universeId);
  const episodes = useEpisodes(universeId);
  const create = useCreateEpisode(universeId);
  // SESSION 269 §12 — cast picker options. Filter to teammates
  // whose ``universe`` matches this Universe (only same-Universe
  // teammates are legal cast; the same filter the Episode detail
  // page's cast-add dropdown uses).
  const spokespeople = useSpokespeople();
  const eligibleTeammates = useMemo(
    () => (spokespeople.data ?? []).filter((s) => s.universe === universeId),
    [spokespeople.data, universeId],
  );

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [operatorTopic, setOperatorTopic] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Selected cast set — Set<UUID>. Empty = zero-cast draft
  // (allowed but the scene CTAs on the Episode detail page will
  // block a downstream render until at least one member is added).
  const [selectedCastIds, setSelectedCastIds] = useState<Set<string>>(
    new Set(),
  );
  // SESSION 280 v1 — chip appears above the topic field when the
  // operator arrived here by picking a "where could this story go
  // next?" suggestion. UI-only state; the suggestion text is a
  // pre-fill, never a commitment, and the operator can edit or
  // discard freely.
  const [suggestionChipVisible, setSuggestionChipVisible] = useState(false);
  const topicRef = useRef<HTMLTextAreaElement | null>(null);

  const toggleCast = (teammateId: string) => {
    setSelectedCastIds((prev) => {
      const next = new Set(prev);
      if (next.has(teammateId)) {
        next.delete(teammateId);
      } else {
        next.add(teammateId);
      }
      return next;
    });
  };

  async function handleCreate(ev: React.FormEvent) {
    ev.preventDefault();
    setSubmitError(null);
    if (!universeId) return;
    const cleanedTopic = operatorTopic.trim();
    if (!cleanedTopic) {
      setSubmitError("Story topic is required.");
      return;
    }
    const cleanedTitle =
      title.trim() ||
      cleanedTopic.slice(0, 60) + (cleanedTopic.length > 60 ? "…" : "");
    // Preserve insertion order — the SPA's recipe-form pre-fill
    // uses ``Episode.cast[0]`` as the default primary spokesperson.
    // Iterating eligibleTeammates keeps the picker order (which
    // matches the API's spokespeople list order) authoritative.
    const cast_ids = eligibleTeammates
      .filter((s) => selectedCastIds.has(s.id))
      .map((s) => s.id);
    try {
      const ep = await create.mutateAsync({
        universe: universeId,
        title: cleanedTitle,
        operator_topic: cleanedTopic,
        ...(cast_ids.length > 0 ? { cast_ids } : {}),
      });
      setCreating(false);
      setTitle("");
      setOperatorTopic("");
      setSelectedCastIds(new Set());
      setSuggestionChipVisible(false);
      navigate(`/workspace/episodes/${ep.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError(String(err));
      }
    }
  }

  const rows = episodes.data ?? [];
  // SESSION 280 v1 — gate the "where could this story go next?"
  // section on there being ≥ 1 non-archived Episode in this
  // Universe. Zero episodes = no story substrate to suggest from;
  // the section hides silently rather than nagging the operator.
  const activeEpisodeCount = rows.filter((r) => !r.archived_at).length;
  const suggestionsEnabled = activeEpisodeCount >= 1;

  // SESSION 280 v1 — handler passed into <PossibleNextEpisodes>.
  // Picking a suggestion OPENS the existing create form with the
  // topic pre-filled. Nothing is created until the operator
  // submits. Cast stays unset — the operator decides who's in
  // this Episode. Title stays blank — will derive from the topic
  // on submit unless the operator supplies one.
  function handleUseSuggestion(text: string) {
    setCreating(true);
    setTitle("");
    setOperatorTopic(text);
    setSelectedCastIds(new Set());
    setSubmitError(null);
    setSuggestionChipVisible(true);
    // Focus the topic textarea after the form mounts so the
    // operator immediately sees the pre-fill is theirs to edit.
    setTimeout(() => {
      topicRef.current?.focus();
      topicRef.current?.setSelectionRange(text.length, text.length);
    }, 0);
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate(`/workspace/universes/${universeId}`)}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to universe
        </button>
        <SectionHeader number={1} title="Episodes" />
        <h1 className="font-display text-3xl leading-tight tracking-tight text-cream md:text-4xl">
          Stories in <span className="italic gold-text">{universe.data?.name ?? "…"}</span>
        </h1>
        <p className="max-w-2xl text-sm text-mist">
          An Episode is an explicit story your cast lives through. Renders
          created under an Episode share its intent; standalone Compositions
          remain fully supported and never wrap into an Episode by
          accident.
        </p>
        {!creating && (
          <div>
            <Button type="button" onClick={() => setCreating(true)}>
              <Sparkles className="mr-2 h-4 w-4" /> New Episode
            </Button>
          </div>
        )}
      </header>

      {/* SESSION 280 v1 — "Where could this story go next?"
          surface. Hidden entirely when the Universe has zero
          active Episodes; the existing empty-state copy below
          still fires in that case. Renders above the existing
          episodes list so the operator sees possibilities
          adjacent to (not instead of) their own choice. */}
      {universeId && !creating && (
        <PossibleNextEpisodes
          universeId={universeId}
          enabled={suggestionsEnabled}
          onUseSuggestion={handleUseSuggestion}
        />
      )}

      {creating && (
        <form
          onSubmit={handleCreate}
          className="flex flex-col gap-3 rounded-lg border border-fog/30 bg-black/20 p-6"
        >
          {/* SESSION 280 v1 — appears only when the operator
              arrived at this form by picking a "where could this
              story go next?" suggestion. Never persisted; the
              [×] dismisses the chip only (textarea contents are
              the operator's to edit or discard). */}
          {suggestionChipVisible && (
            <div
              className="flex items-center justify-between gap-2 rounded-md border border-gold/40 bg-gold/5 px-3 py-2 text-xs text-gold"
              data-testid="episode-create-suggestion-chip"
              role="status"
            >
              <span>
                Started from an idea. Edit anything freely — nothing is
                saved yet.
              </span>
              <button
                type="button"
                onClick={() => setSuggestionChipVisible(false)}
                className="text-gold/70 transition-colors hover:text-gold"
                aria-label="Dismiss the suggested-start note"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          <Label htmlFor="new-ep-title">Title (optional; derived from topic if blank)</Label>
          <Input
            id="new-ep-title"
            value={title}
            onChange={(ev) => setTitle(ev.target.value)}
            placeholder="AI took over the lab"
          />
          <Label htmlFor="new-ep-topic">Operator topic (story-authoritative)</Label>
          <textarea
            id="new-ep-topic"
            ref={topicRef}
            className="min-h-[120px] rounded-md border border-fog/30 bg-black/30 px-3 py-2 text-cream"
            value={operatorTopic}
            onChange={(ev) => setOperatorTopic(ev.target.value)}
            placeholder="Rivet warns Patch the AI will fire the humans; Patch is skeptical."
            required
          />
          <p className="text-xs text-fog">
            The topic drives every Composition under this Episode. You can
            edit it later without disturbing per-attempt provenance.
          </p>

          {/*
            SESSION 269 §12 — inline cast picker. Selecting one
            character makes this a solo Episode (Episode detail
            offers a solo-scene action); selecting two or more
            keeps the existing dialogue-scene action. Zero cast
            is a valid draft — the scene actions on the Episode
            detail page block silent fall-through via the existing
            insufficientCast guard on the recipe form. Cast can
            still be added or removed on the Episode detail page
            after creation.
          */}
          <div className="flex flex-col gap-2 rounded-md border border-fog/30 bg-black/20 p-4">
            <Label>Cast (optional; add now or later)</Label>
            {spokespeople.isLoading && (
              <p className="text-xs italic text-fog">
                Loading available characters…
              </p>
            )}
            {!spokespeople.isLoading && eligibleTeammates.length === 0 && (
              <p className="text-xs italic text-fog">
                No characters in this Universe yet. Add teammates to this
                Universe from the Universe detail page, then come back
                — or create the Episode now and attach cast later.
              </p>
            )}
            {eligibleTeammates.length > 0 && (
              <div
                className="flex flex-wrap gap-2"
                data-testid="episode-create-cast-picker"
              >
                {eligibleTeammates.map((tm) => {
                  const checked = selectedCastIds.has(tm.id);
                  return (
                    <button
                      key={tm.id}
                      type="button"
                      aria-pressed={checked}
                      data-testid={`episode-create-cast-toggle-${tm.id}`}
                      onClick={() => toggleCast(tm.id)}
                      className={
                        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm transition-colors " +
                        (checked
                          ? "border-gold bg-gold/10 text-gold"
                          : "border-fog/40 text-cream hover:border-gold/60")
                      }
                    >
                      <span
                        aria-hidden="true"
                        className={
                          "inline-block h-2 w-2 rounded-full " +
                          (checked ? "bg-gold" : "bg-fog/40")
                        }
                      />
                      {tm.name}
                    </button>
                  );
                })}
              </div>
            )}
            <p className="text-xs text-fog">
              {selectedCastIds.size === 0 && (
                <>
                  No cast selected — this will save as a draft Episode.
                  The scene action on the Episode page will remind you
                  to add at least one character before rendering.
                </>
              )}
              {selectedCastIds.size === 1 && (
                <>
                  One character selected — the Episode will offer a
                  solo-scene action.
                </>
              )}
              {selectedCastIds.size >= 2 && (
                <>
                  {selectedCastIds.size} characters selected — the
                  Episode will offer a dialogue-scene action.
                </>
              )}
            </p>
          </div>

          {submitError && (
            <p className="text-sm text-red-400" role="alert">
              {submitError}
            </p>
          )}
          <div className="flex items-center gap-2">
            <Button type="submit" disabled={create.isPending}>
              Create Episode
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setCreating(false);
                setSubmitError(null);
                setSelectedCastIds(new Set());
                setSuggestionChipVisible(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      {rows.length === 0 && !creating && (
        <p className="text-sm italic text-fog">
          No Episodes in this Universe yet.
        </p>
      )}

      <ul className="flex flex-col gap-3">
        {rows.map((ep) => (
          <li
            key={ep.id}
            className="rounded-lg border border-fog/30 bg-black/20 p-4"
          >
            <Link
              to={`/workspace/episodes/${ep.id}`}
              className="block text-cream hover:text-gold"
            >
              <div className="font-display text-lg">{ep.title}</div>
              <div className="mt-1 text-xs text-fog">
                {ep.composition_count} composition
                {ep.composition_count === 1 ? "" : "s"} · {ep.cast.length}{" "}
                cast member{ep.cast.length === 1 ? "" : "s"}
                {ep.archived_at ? " · archived" : ""}
              </div>
              <div className="mt-2 line-clamp-2 text-sm text-mist">
                {ep.operator_topic}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
