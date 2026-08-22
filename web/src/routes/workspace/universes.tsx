/**
 * /workspace/universes — Universe list + create form.
 *
 * SESSION 261 / Phase 4. Backend surface:
 * shell/apps/universe/views.py::UniverseViewSet.
 *
 * The load-bearing SPA affordance for the Universe substrate:
 * operators create/archive Universes here, then assign teammates
 * and scope knowledge uploads to them.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, Globe2, Archive } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/api/workspaces";
import {
  useUniverses,
  useCreateUniverse,
  useArchiveUniverse,
  type Universe,
} from "@/lib/api/universes";
import { ApiError } from "@/lib/api/client";
import { SectionHeader } from "@/components/editorial";


export function WorkspaceUniversesRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const list = useUniverses(workspaceId);

  const universes = list.data ?? [];

  return (
    <div className="flex flex-col gap-10">
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <SectionHeader number={1} title="Universes" />
        <h1
          data-testid="universes-title"
          className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
        >
          Your <span className="italic gold-text">worlds</span>.
        </h1>
        <p className="max-w-2xl text-base text-mist">
          A Universe scopes teammates and knowledge to one world. A workspace
          can hold multiple Universes; cross-Universe leak is impossible by
          construction. Legacy teammates and docs stay Universe-less.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      <CreatePanel workspaceId={workspaceId} />

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between border-b border-luxe pb-3">
          <h2 className="font-display text-2xl tracking-tight text-cream">
            Worlds
          </h2>
          {universes.length > 0 && (
            <span className="font-mono text-xs text-fog">{universes.length}</span>
          )}
        </div>

        {list.isLoading && <p className="text-sm text-fog">Loading…</p>}
        {list.error && (
          <p className="text-sm text-destructive">
            Failed to load: {list.error.message}
          </p>
        )}
        {!list.isLoading && universes.length === 0 && <EmptyState />}
        {universes.length > 0 && (
          <ul
            data-testid="universes-list"
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
          >
            {universes.map((u) => (
              <UniverseRow key={u.id} universe={u} workspaceId={workspaceId} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}


function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-luxe bg-card/40 p-12 text-center">
      <Globe2 className="mx-auto h-10 w-10 text-fog" />
      <p className="mt-4 font-display text-xl tracking-tight text-cream">
        No worlds yet
      </p>
      <p className="mt-1 text-sm text-mist max-w-md mx-auto">
        Create a world above to scope teammates and knowledge to one
        universe. Existing teammates + docs stay legacy until you
        explicitly assign them.
      </p>
    </div>
  );
}


function CreatePanel({ workspaceId }: { workspaceId: string | undefined }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  // SESSION 277 Slice 8 (Q-277-8) — compact World identity.
  // Optional (blank is valid), but exposed here on the dedicated
  // create surface so operators can populate it at Universe-create
  // time. The Slice-5 inline "+ Create new World" flow in the
  // spokesperson wizard remains name-only per Slice 8 scope-lock.
  const [brief, setBrief] = useState("");
  const create = useCreateUniverse(workspaceId);

  const disabled = !workspaceId || !name.trim() || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        name: name.trim(),
        description: description.trim() || undefined,
        brief: brief.trim() || undefined,
      });
      setName("");
      setDescription("");
      setBrief("");
    } catch (err) {
      console.error("universe create failed", err);
    }
  }

  return (
    <section
      data-testid="universe-create-panel"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <h2 className="font-display text-2xl tracking-tight text-cream">
        Create a world
      </h2>
      <p className="mt-1 text-sm text-mist">
        Pick a name; describe it in a sentence. Slug is auto-derived.
      </p>

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-name">Name</Label>
          <Input
            id="universe-name"
            data-testid="universe-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Workshop, Bakery, Riverstone"
            maxLength={120}
            required
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-brief">What is this World? (optional)</Label>
          <textarea
            id="universe-brief"
            data-testid="universe-brief"
            className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="A warm neighborhood artisan bakery built around small-batch baking, naturally leavened sourdough, handcrafted pastries..."
            maxLength={2000}
          />
          <p className="text-xs text-muted-foreground">
            Describe the enduring shared context every character in this
            World should understand — its kind, purpose, audience, and
            atmosphere. Keep detailed facts, pricing, policies, menus,
            and procedures in Knowledge. Aim for 1–3 short paragraphs.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-description">Description (optional)</Label>
          <textarea
            id="universe-description"
            data-testid="universe-description"
            className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Internal note about this world — not consumed by synthesis."
          />
        </div>

        {create.error && (
          <p
            data-testid="universe-create-error"
            className="text-sm text-destructive"
          >
            {readableError(create.error)}
          </p>
        )}

        <Button type="submit" data-testid="universe-create-submit" disabled={disabled}>
          {create.isPending ? "Creating…" : "Create world"}
        </Button>
      </form>
    </section>
  );
}


function UniverseRow({
  universe,
  workspaceId,
}: {
  universe: Universe;
  workspaceId: string | undefined;
}) {
  const archive = useArchiveUniverse(workspaceId);

  async function handleArchive() {
    if (!confirm(`Archive "${universe.name}"? Members stay attached to the universe; you can unarchive later.`)) {
      return;
    }
    await archive.mutateAsync(universe.id);
  }

  return (
    <li
      data-testid={`universe-row-${universe.id}`}
      className="flex items-center gap-4 px-5 py-4"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Globe2 className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Link
            to={`/workspace/universes/${universe.id}`}
            data-testid={`universe-row-link-${universe.id}`}
            className="truncate font-medium underline-offset-4 hover:underline"
            title={universe.name}
          >
            {universe.name}
          </Link>
        </div>
        <p className="mt-1 text-xs text-fog">
          {universe.teammate_count} teammate
          {universe.teammate_count === 1 ? "" : "s"} ·{" "}
          {universe.knowledge_document_count} doc
          {universe.knowledge_document_count === 1 ? "" : "s"} · slug{" "}
          <code className="font-mono">{universe.slug}</code>
        </p>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-testid={`universe-archive-${universe.id}`}
        onClick={handleArchive}
        disabled={archive.isPending}
        aria-label={`Archive ${universe.name}`}
      >
        <Archive className="h-4 w-4" />
      </Button>
    </li>
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
