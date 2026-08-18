/**
 * /workspace/universes/:id — Universe detail page.
 *
 * SESSION 261 / Phase 4. Shows member teammates + docs +
 * edit/archive/unarchive/hard-delete affordances.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Globe2, Trash2, ArchiveRestore } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/api/workspaces";
import {
  useUniverse,
  useUpdateUniverse,
  useArchiveUniverse,
  useUnarchiveUniverse,
  useHardDeleteUniverse,
} from "@/lib/api/universes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useKnowledgeList } from "@/lib/api/knowledge";
import { ApiError } from "@/lib/api/client";
import { SectionHeader } from "@/components/editorial";


export function UniverseDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const universe = useUniverse(id);
  const spokespeople = useSpokespeople();
  const knowledge = useKnowledgeList(workspaceId);

  const update = useUpdateUniverse(workspaceId);
  const archive = useArchiveUniverse(workspaceId);
  const unarchive = useUnarchiveUniverse(workspaceId);
  const hardDelete = useHardDeleteUniverse(workspaceId);

  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [dirty, setDirty] = useState(false);

  const u = universe.data;
  const memberTeammates = (spokespeople.data ?? []).filter(
    (sp) => sp.universe === id,
  );
  const memberDocs = (knowledge.data ?? []).filter((d) => d.universe === id);

  async function handleSave() {
    if (!u) return;
    try {
      await update.mutateAsync({
        id: u.id,
        payload: {
          name: name.trim() || u.name,
          description: description,
        },
      });
      setDirty(false);
    } catch (err) {
      console.error("universe update failed", err);
    }
  }

  async function handleArchive() {
    if (!u) return;
    if (!confirm(`Archive "${u.name}"?`)) return;
    await archive.mutateAsync(u.id);
    navigate("/workspace/universes");
  }

  async function handleUnarchive() {
    if (!u) return;
    await unarchive.mutateAsync(u.id);
  }

  async function handleHardDelete() {
    if (!u) return;
    if (
      !confirm(
        `PERMANENTLY delete "${u.name}"? This requires the world be empty (no teammates, no docs).`,
      )
    )
      return;
    try {
      await hardDelete.mutateAsync(u.id);
      navigate("/workspace/universes");
    } catch (err) {
      // Backend returns 409 with blocking counts.
      console.error("hard-delete rejected", err);
    }
  }

  if (universe.isLoading) return <p className="text-sm text-fog">Loading…</p>;
  if (universe.error || !u) {
    return (
      <p className="text-sm text-destructive">
        Could not load universe: {String(universe.error)}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/workspace/universes")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to worlds
        </button>
        <SectionHeader number={2} title="World detail" />
        <div className="flex items-center gap-3">
          <Globe2 className="h-8 w-8 text-gold" />
          <h1
            data-testid="universe-detail-name"
            className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
          >
            {u.name}
          </h1>
        </div>
        <p className="text-sm text-fog">
          Slug: <code className="font-mono">{u.slug}</code>
          {u.archived_at && (
            <span className="ml-3 rounded-sm border border-luxe bg-muted px-2 py-0.5 text-xs uppercase text-fog">
              archived
            </span>
          )}
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      <section className="rounded-md border border-luxe bg-card/60 p-6">
        <h2 className="font-display text-2xl tracking-tight text-cream">Edit</h2>
        <div className="mt-4 flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="universe-name">Name</Label>
            <Input
              id="universe-name"
              data-testid="universe-name"
              value={dirty ? name : u.name}
              onChange={(e) => {
                setDirty(true);
                setName(e.target.value);
              }}
              maxLength={120}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="universe-description">Description</Label>
            <textarea
              id="universe-description"
              data-testid="universe-description"
              className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              value={dirty ? description : u.description}
              onChange={(e) => {
                setDirty(true);
                setDescription(e.target.value);
              }}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              data-testid="universe-save"
              onClick={handleSave}
              disabled={!dirty || update.isPending}
            >
              {update.isPending ? "Saving…" : "Save"}
            </Button>
            {u.archived_at ? (
              <Button
                type="button"
                variant="outline"
                data-testid="universe-unarchive"
                onClick={handleUnarchive}
              >
                <ArchiveRestore className="mr-2 h-4 w-4" />
                Unarchive
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                data-testid="universe-archive"
                onClick={handleArchive}
              >
                Archive
              </Button>
            )}
            <Button
              type="button"
              variant="destructive"
              data-testid="universe-hard-delete"
              onClick={handleHardDelete}
              disabled={
                memberTeammates.length > 0 || memberDocs.length > 0
              }
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete permanently
            </Button>
          </div>
          {(memberTeammates.length > 0 || memberDocs.length > 0) && (
            <p className="text-xs text-fog">
              Delete permanently is blocked while this world has members.
              Reassign every teammate and doc first.
            </p>
          )}
          {update.error && (
            <p className="text-sm text-destructive">
              {readableError(update.error)}
            </p>
          )}
        </div>
      </section>

      {/* SESSION 262 — Episodes list link. Explicit-only Episode
          workflow lives at /workspace/universes/:id/episodes. */}
      <section className="rounded-md border border-luxe bg-card/60 p-6">
        <h2 className="mb-2 font-display text-2xl tracking-tight text-cream">
          Episodes{" "}
          <span className="text-fog text-sm">({u.episode_count ?? 0})</span>
        </h2>
        <p className="mb-3 text-sm text-mist">
          Stories your cast lives through. Renders may attach to an Episode
          or remain standalone.
        </p>
        <Link
          to={`/workspace/universes/${u.id}/episodes`}
          className="inline-block text-sm text-gold hover:underline"
          data-testid="universe-episodes-link"
        >
          Manage episodes →
        </Link>
      </section>

      <section>
        <h2 className="mb-3 border-b border-luxe pb-2 font-display text-2xl tracking-tight text-cream">
          Teammates <span className="text-fog text-sm">({memberTeammates.length})</span>
        </h2>
        {memberTeammates.length === 0 && (
          <p className="text-sm text-fog">No teammates yet.</p>
        )}
        <ul className="divide-y divide-luxe rounded-md border border-luxe bg-card">
          {memberTeammates.map((sp) => (
            <li
              key={sp.id}
              data-testid={`member-teammate-${sp.id}`}
              className="flex items-center gap-4 px-5 py-3"
            >
              <Link
                to={`/spokespeople/${sp.id}`}
                className="truncate font-medium underline-offset-4 hover:underline"
              >
                {sp.name}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 border-b border-luxe pb-2 font-display text-2xl tracking-tight text-cream">
          Docs <span className="text-fog text-sm">({memberDocs.length})</span>
        </h2>
        {memberDocs.length === 0 && (
          <p className="text-sm text-fog">No docs yet.</p>
        )}
        <ul className="divide-y divide-luxe rounded-md border border-luxe bg-card">
          {memberDocs.map((d) => (
            <li
              key={d.id}
              data-testid={`member-doc-${d.id}`}
              className="flex items-center gap-4 px-5 py-3"
            >
              <Link
                to={`/workspace/knowledge/${d.id}`}
                className="truncate font-medium underline-offset-4 hover:underline"
              >
                {d.title}
              </Link>
            </li>
          ))}
        </ul>
      </section>
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
