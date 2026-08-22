/**
 * /workspace/universes/:id — Universe detail page.
 *
 * SESSION 261 / Phase 4 — original CRUD scaffold.
 * SESSION 262 — Episodes link.
 * SESSION 264 — inline NarrativeMemoryList.
 * SESSION 277 Slice 8 — Universe.brief exposed as an editable field.
 * SESSION 277 Slice 10 (Q-277-10) — page now defaults to a readable
 *   World overview. Explicit "Edit" affordance toggles into a form
 *   containing Name + What is this World? + Operator notes (optional).
 *   Save/Cancel return to the overview. Archive + Delete permanently
 *   move into a distinct "Lifecycle" region below the primary
 *   content sections (Characters / Episodes / Docs / Memories) so
 *   destructive actions no longer share a button row with Save.
 *   `Universe.description` remains the existing DB field; its
 *   operator-visible label becomes "Operator notes (optional)" per
 *   the accepted product decision — the model column is NOT renamed.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft,
  Globe2,
  Pencil,
  Trash2,
  ArchiveRestore,
  X,
} from "lucide-react";

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
  type Universe,
} from "@/lib/api/universes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useKnowledgeList } from "@/lib/api/knowledge";
import { ApiError } from "@/lib/api/client";
import { SectionHeader } from "@/components/editorial";
import { NarrativeMemoryList } from "@/components/narrative-memory-panels";


export function UniverseDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const universe = useUniverse(id);
  const spokespeople = useSpokespeople();
  const knowledge = useKnowledgeList(workspaceId);

  const archive = useArchiveUniverse(workspaceId);
  const unarchive = useUnarchiveUniverse(workspaceId);
  const hardDelete = useHardDeleteUniverse(workspaceId);

  // SESSION 277 Slice 10 (Q-277-10) — view/edit toggle. Default is
  // Overview (read-only prose); Edit reveals the form.
  const [mode, setMode] = useState<"view" | "edit">("view");

  const u = universe.data;
  const memberTeammates = (spokespeople.data ?? []).filter(
    (sp) => sp.universe === id,
  );
  const memberDocs = (knowledge.data ?? []).filter((d) => d.universe === id);

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
        <div className="flex flex-wrap items-center gap-3">
          <Globe2 className="h-8 w-8 text-gold" />
          <h1
            data-testid="universe-detail-name"
            className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
          >
            {u.name}
          </h1>
          {mode === "view" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="universe-edit-toggle"
              onClick={() => setMode("edit")}
              className="ml-auto"
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </Button>
          )}
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

      {mode === "view" ? (
        <OverviewPanel universe={u} />
      ) : (
        <EditPanel
          universe={u}
          workspaceId={workspaceId}
          onSaved={() => setMode("view")}
          onCancel={() => setMode("view")}
        />
      )}

      {/* SESSION 262 — Episodes list link. Explicit-only Episode
          workflow lives at /workspace/universes/:id/episodes. */}
      <section
        className="rounded-md border border-luxe bg-card/60 p-6"
        data-testid="universe-episodes-section"
      >
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

      <section data-testid="universe-teammates-section">
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

      {/* SESSION 264 Slice 1 — Universe-wide narrative memory
          list (spans every Episode in the world). Sourced from
          /api/narrative-memories/?universe=<id>. `showSource`
          reveals which Episode + Composition each memory came
          from since this view crosses Episodes. */}
      <NarrativeMemoryList
        filter={{ universeId: u.id }}
        showSource
        title="World memories"
        emptyLabel="No memories promoted in this world yet."
      />

      <section data-testid="universe-docs-section">
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

      {/* SESSION 277 Slice 10 (Q-277-10) — destructive lifecycle
          actions live in their own bordered region at the bottom of
          the page so they no longer share a button row with Save.
          Explicit "Lifecycle" heading + explanatory copy on the
          blocked hard-delete state. */}
      <DangerRegion
        universe={u}
        memberTeammatesCount={memberTeammates.length}
        memberDocsCount={memberDocs.length}
        onArchive={handleArchive}
        onUnarchive={handleUnarchive}
        onHardDelete={handleHardDelete}
      />
    </div>
  );
}


// ---- SESSION 277 Slice 10 — Overview panel (default view) ----

function OverviewPanel({ universe: u }: { universe: Universe }) {
  const briefTrimmed = (u.brief ?? "").trim();
  const notesTrimmed = (u.description ?? "").trim();
  return (
    <section
      data-testid="universe-overview"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <h2 className="mb-4 font-display text-2xl tracking-tight text-cream">
        Overview
      </h2>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            What is this World?
          </span>
          {briefTrimmed ? (
            <p
              data-testid="universe-brief-view"
              className="whitespace-pre-wrap text-base leading-relaxed text-cream"
            >
              {briefTrimmed}
            </p>
          ) : (
            <p
              data-testid="universe-brief-empty"
              className="text-sm italic text-muted-foreground"
            >
              No World brief yet. Click <strong>Edit</strong> to describe
              what this World is — its kind, purpose, audience, and
              atmosphere. Every character in this World inherits this
              during synthesis.
            </p>
          )}
        </div>

        {notesTrimmed && (
          <div className="flex flex-col gap-2 border-t border-luxe pt-4">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Operator notes
            </span>
            <p
              data-testid="universe-notes-view"
              className="whitespace-pre-wrap text-sm text-mist"
            >
              {notesTrimmed}
            </p>
            <p className="text-xs text-muted-foreground">
              Private operator reference — not used by characters or
              synthesis.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}


// ---- SESSION 277 Slice 10 — Edit panel (revealed by Edit) ----

function EditPanel({
  universe: u,
  workspaceId,
  onSaved,
  onCancel,
}: {
  universe: Universe;
  workspaceId: string | undefined;
  onSaved: () => void;
  onCancel: () => void;
}) {
  // Staged inputs seed from the server-truth values so opening Edit
  // shows the existing content — Cancel discards without hitting the
  // API; Save persists and returns to Overview.
  const [name, setName] = useState<string>(u.name);
  const [brief, setBrief] = useState<string>(u.brief ?? "");
  const [notes, setNotes] = useState<string>(u.description ?? "");
  const update = useUpdateUniverse(workspaceId);

  const dirty =
    name.trim() !== u.name ||
    brief !== (u.brief ?? "") ||
    notes !== (u.description ?? "");

  async function handleSave() {
    try {
      await update.mutateAsync({
        id: u.id,
        payload: {
          name: name.trim() || u.name,
          brief: brief,
          description: notes,
        },
      });
      onSaved();
    } catch (err) {
      console.error("universe update failed", err);
    }
  }

  return (
    <section
      data-testid="universe-edit"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <h2 className="mb-4 font-display text-2xl tracking-tight text-cream">
        Edit
      </h2>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-name">Name</Label>
          <Input
            id="universe-name"
            data-testid="universe-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-brief">What is this World?</Label>
          <textarea
            id="universe-brief"
            data-testid="universe-brief"
            className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            maxLength={2000}
            placeholder="A warm neighborhood artisan bakery built around small-batch baking..."
          />
          <p className="text-xs text-muted-foreground">
            Shared identity every character in this World inherits and
            uses during synthesis. Keep detailed facts, pricing,
            policies, menus, and procedures in Knowledge. Aim for 1–3
            short paragraphs.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="universe-description">
            Operator notes (optional)
          </Label>
          <textarea
            id="universe-description"
            data-testid="universe-description"
            className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Private reminder to yourself. Not shown to characters."
          />
          <p className="text-xs text-muted-foreground">
            Private operator reference — characters do not use this and
            it is not consumed by synthesis. Use it for audit notes,
            reminders, or context you want to keep on the World row.
          </p>
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
          <Button
            type="button"
            variant="ghost"
            data-testid="universe-cancel"
            onClick={onCancel}
            disabled={update.isPending}
          >
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
        </div>
        {update.error && (
          <p className="text-sm text-destructive">
            {readableError(update.error)}
          </p>
        )}
      </div>
    </section>
  );
}


// ---- SESSION 277 Slice 10 — Danger / Lifecycle region ----

function DangerRegion({
  universe: u,
  memberTeammatesCount,
  memberDocsCount,
  onArchive,
  onUnarchive,
  onHardDelete,
}: {
  universe: Universe;
  memberTeammatesCount: number;
  memberDocsCount: number;
  onArchive: () => void;
  onUnarchive: () => void;
  onHardDelete: () => void;
}) {
  const hardDeleteBlocked = memberTeammatesCount > 0 || memberDocsCount > 0;
  return (
    <section
      data-testid="universe-danger"
      className="rounded-md border border-destructive/40 bg-destructive/5 p-6"
    >
      <h2 className="mb-2 font-display text-2xl tracking-tight text-destructive">
        Lifecycle
      </h2>
      <p className="mb-4 text-xs text-muted-foreground">
        Archive hides this World and its members from ordinary views
        without deleting anything. Delete permanently is irreversible
        and only allowed on an empty World.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        {u.archived_at ? (
          <Button
            type="button"
            variant="outline"
            data-testid="universe-unarchive"
            onClick={onUnarchive}
          >
            <ArchiveRestore className="mr-2 h-4 w-4" />
            Unarchive
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            data-testid="universe-archive"
            onClick={onArchive}
          >
            Archive
          </Button>
        )}
        <Button
          type="button"
          variant="destructive"
          data-testid="universe-hard-delete"
          onClick={onHardDelete}
          disabled={hardDeleteBlocked}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete permanently
        </Button>
      </div>
      {hardDeleteBlocked && (
        <p className="mt-3 text-xs text-fog">
          Delete permanently is blocked while this world has members.
          Reassign every teammate and doc first.
        </p>
      )}
    </section>
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
