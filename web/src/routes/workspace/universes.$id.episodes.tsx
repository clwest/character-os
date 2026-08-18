/**
 * /workspace/universes/:id/episodes — Episode list + create.
 *
 * SESSION 262 / EPISODE_SCHEMA_V1. Backend surface:
 * shell/apps/universe/views.py::EpisodeViewSet (list + create).
 *
 * Load-bearing:
 * - Episode creation is explicit-only.
 * - Standalone Composition workflow (no Episode) remains available
 *   from the recipe form elsewhere in the SPA.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionHeader } from "@/components/editorial";
import { useUniverse } from "@/lib/api/universes";
import { useEpisodes, useCreateEpisode } from "@/lib/api/episodes";
import { ApiError } from "@/lib/api/client";


export function UniverseEpisodesRoute() {
  const { id: universeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const universe = useUniverse(universeId);
  const episodes = useEpisodes(universeId);
  const create = useCreateEpisode(universeId);

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [operatorTopic, setOperatorTopic] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

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
    try {
      const ep = await create.mutateAsync({
        universe: universeId,
        title: cleanedTitle,
        operator_topic: cleanedTopic,
      });
      setCreating(false);
      setTitle("");
      setOperatorTopic("");
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

      {creating && (
        <form
          onSubmit={handleCreate}
          className="flex flex-col gap-3 rounded-lg border border-fog/30 bg-black/20 p-6"
        >
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
