import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Flame, Mic, MessageCircle, Pencil, Plus, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useCloneVoice,
  useRefreshPortrait,
  useSpokesperson,
  type Spokesperson,
} from "@/lib/api/spokespeople";
import { useVideos, type Video } from "@/lib/api/videos";
import { VideoRow } from "@/components/video-row";
import { VoiceCapture, type VoiceCaptureValue } from "@/components/voice-capture";
import { KnowledgePanel } from "@/components/knowledge-panel";
import { SpokespersonEditModal } from "@/components/spokesperson-edit-modal";
import { SpokespersonRebakeModal } from "@/components/spokesperson-rebake-modal";
import {
  useThreads,
  useCreateThread,
  type ConversationThread,
} from "@/lib/api/conversations";
import { cn } from "@/lib/utils";

/**
 * Spokesperson detail (S-10 of UI_REDESIGN_V2.md). The first
 * surface where avatar + voice setup state matters — both fields
 * surface as pills, and missing values get inline setup callouts
 * pointing at future slices (create-flow S-06, voice-clone UI).
 *
 * Layout mirrors the dashboard: editorial masthead → primary panel
 * (identity) → secondary panels (setup status + videos library).
 */
export function SpokespersonDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const sp = useSpokesperson(id);
  const videos = useVideos({ spokesperson: id });
  // W11.1 — edit-spokesperson modal. Opens via the Edit pencil
  // on the IdentityPanel header; closes on cancel or save.
  // MUST live above the early returns or React's hook-order check
  // throws "Rendered more hooks than during the previous render"
  // when sp.isLoading flips from true → false.
  const [editing, setEditing] = useState(false);
  // W11.2 — re-bake avatar confirm modal. Real Runway spend so
  // gets a dedicated affordance instead of inline-on-edit.
  const [rebaking, setRebaking] = useState(false);

  if (sp.isLoading) return <DetailSkeleton />;
  if (sp.isError) return <DetailError message={extractMessage(sp.error)} />;
  if (!sp.data) return <DetailError message="Spokesperson not found." />;

  const s = sp.data;
  // Hoisted from SetupPanel in SESSION 134 (slice 11). The layout
  // diverges by completion state — fully configured spokespeople
  // skip the setup column entirely; partial ones show only the
  // unfinished rows.
  const setupItems = buildSetupItems(s);
  const allDone = setupItems.every((it) => it.done);
  const pendingItems = setupItems.filter((it) => !it.done);

  return (
    <div
      className="flex flex-col gap-12"
      data-testid="spokesperson-detail"
      data-configured={allDone ? "full" : "partial"}
    >
      <Masthead
        spokesperson={s}
        ready={allDone}
        onRebake={() => setRebaking(true)}
      />
      <IdentityPanel spokesperson={s} onEdit={() => setEditing(true)} />
      {editing && (
        <SpokespersonEditModal
          spokesperson={s}
          onClose={() => setEditing(false)}
        />
      )}
      {rebaking && (
        <SpokespersonRebakeModal
          spokesperson={s}
          onClose={() => setRebaking(false)}
        />
      )}
      {allDone && <TalkCta spokesperson={s} />}

      {allDone ? (
        <section
          className="reveal"
          style={{ "--reveal-delay": "0.04s" } as React.CSSProperties}
          data-testid="ready-state"
        >
          <VideosPanel
            videos={videos.data}
            loading={videos.isLoading}
            error={videos.error}
            spokespersonId={s.id}
          />
        </section>
      ) : (
        <section
          className="reveal grid grid-cols-1 gap-6 lg:grid-cols-[2fr,1fr]"
          style={{ "--reveal-delay": "0.04s" } as React.CSSProperties}
        >
          <VideosPanel
            videos={videos.data}
            loading={videos.isLoading}
            error={videos.error}
            spokespersonId={s.id}
          />
          <SetupPanel spokesperson={s} pendingItems={pendingItems} />
        </section>
      )}

      {/* SESSION 138 / K5 — Knowledge panel.
          Filtered view of workspace knowledge visible to this
          spokesperson (empty M2M OR M2M-attached). Per-row
          attach/detach toggles flip the visibility scope. */}
      <section
        className="reveal"
        style={{ "--reveal-delay": "0.06s" } as React.CSSProperties}
      >
        <KnowledgePanel
          workspaceId={s.workspace}
          spokespersonId={s.id}
          spokespersonName={s.name}
        />
      </section>

      {/* SESSION 145 / K9 — Conversations panel.
          Lists threads with this spokesperson + a CTA to
          start a new one. Empty state for fresh spokespeople
          encourages picking the conversational surface. */}
      <section
        className="reveal"
        style={{ "--reveal-delay": "0.07s" } as React.CSSProperties}
      >
        <ConversationsPanel
          spokespersonId={s.id}
          spokespersonName={s.name}
        />
      </section>
    </div>
  );
}

function ConversationsPanel({
  spokespersonId,
  spokespersonName,
}: {
  spokespersonId: string;
  spokespersonName: string;
}) {
  const threads = useThreads({ spokesperson: spokespersonId });
  const createThread = useCreateThread();
  const navigate = useNavigate();

  async function handleNewThread() {
    try {
      const t = await createThread.mutateAsync({
        spokesperson: spokespersonId,
      });
      navigate(`/conversations/${t.id}`);
    } catch {
      // surfaces via createThread.error below
    }
  }

  return (
    <div
      className="flex flex-col gap-4 rounded-md border bg-card p-5 luxe-shadow"
      data-testid="spokesperson-conversations-panel"
    >
      <div className="flex items-baseline justify-between border-b pb-2">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-fog" />
          <h2 className="font-display text-base tracking-tight">Conversations</h2>
          {threads.data && (
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
              {threads.data.length}
            </span>
          )}
        </div>
        <Button
          size="sm"
          onClick={handleNewThread}
          disabled={createThread.isPending}
          data-testid="conversation-new"
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          {createThread.isPending ? "Starting…" : "Start a chat"}
        </Button>
      </div>

      {createThread.error instanceof Error && (
        <p className="text-sm text-destructive">{createThread.error.message}</p>
      )}

      {threads.isLoading && (
        <div className="h-20 animate-pulse rounded bg-muted/40" />
      )}

      {threads.data && threads.data.length === 0 && (
        <p className="text-sm text-fog">
          No chats yet. Start one to talk to {spokespersonName} — they'll draw
          on the workspace knowledge attached above.
        </p>
      )}

      {threads.data && threads.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {threads.data.map((t) => (
            <ConversationRow key={t.id} thread={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ConversationRow({ thread }: { thread: ConversationThread }) {
  const preview = thread.last_message_preview || "(no messages yet)";
  return (
    <li>
      <Link
        to={`/conversations/${thread.id}`}
        data-testid={`conversation-row-${thread.id}`}
        className="flex items-baseline justify-between gap-3 rounded-sm border bg-muted/30 px-3 py-2 transition-colors hover:border-foreground"
      >
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-sm">
            {thread.title || `Chat ${thread.id.slice(0, 8)}`}
          </span>
          <span className="line-clamp-1 text-xs text-fog">{preview}</span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
          {thread.message_count} msg{thread.message_count === 1 ? "" : "s"}
        </span>
      </Link>
    </li>
  );
}

// ---- Sections -------------------------------------------------------

function Masthead({
  spokesperson,
  ready,
  onRebake,
}: {
  spokesperson: Spokesperson;
  ready: boolean;
  onRebake?: () => void;
}) {
  return (
    <header
      className="reveal relative flex flex-col gap-4 pb-10"
      data-testid="spokesperson-masthead"
    >
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
        data-testid="back-to-dashboard"
      >
        <ArrowLeft className="h-3 w-3" />
        Workspace
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
              § — Spokesperson
            </span>
            {ready && (
              <span
                className="inline-flex items-center gap-1.5 rounded-sm border border-gold/40 bg-gold/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-gold"
                data-testid="ready-badge"
              >
                Ready to render
              </span>
            )}
          </div>
          <h1
            className="font-display text-5xl leading-[0.95] tracking-tight text-cream md:text-6xl"
            style={
              {
                fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
              } as React.CSSProperties
            }
            data-testid="spokesperson-name"
          >
            {spokesperson.name}
          </h1>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-2">
            {onRebake && spokesperson.runway_avatar_id && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onRebake}
                data-testid="rebake-trigger"
                title="Re-bake avatar (real Runway spend, 30-180s)"
              >
                <Flame className="mr-1 h-3.5 w-3.5" />
                Re-bake
              </Button>
            )}
            <Link
              to={`/recipes?spokesperson=${spokesperson.id}`}
              data-testid="make-video-link"
            >
              <Button
                size="lg"
                disabled={!spokesperson.runway_avatar_id}
                title={
                  spokesperson.runway_avatar_id
                    ? undefined
                    : "Bind a portrait first — the render pipeline needs an attached avatar."
                }
              >
                <Wand2 className="mr-1.5 h-4 w-4" />
                New render
              </Button>
            </Link>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <StatusPill
              label="Status"
              value={prettyStatus(spokesperson.status)}
              tone={statusTone(spokesperson.status)}
            />
            <StatusPill
              label="Avatar"
              value={prettyAvatarStatus(spokesperson.runway_avatar_status)}
              tone={avatarTone(spokesperson.runway_avatar_status)}
            />
            <StatusPill
              label="Voice"
              value={spokesperson.voice_id ? "Bound" : "Not set"}
              tone={spokesperson.voice_id ? "ready" : "muted"}
            />
          </div>
        </div>
      </div>
      {/* V3.6 — hairline-gold gradient under masthead per
       * BRAND_IDENTITY_V3 §editorial patterns. */}
      <div
        className="hairline-gold absolute inset-x-0 bottom-0 h-px"
        aria-hidden="true"
      />
    </header>
  );
}

function IdentityPanel({
  spokesperson,
  onEdit,
}: {
  spokesperson: Spokesperson;
  onEdit?: () => void;
}) {
  return (
    <section
      className="reveal luxe-shadow grid grid-cols-1 gap-6 rounded-md border border-luxe bg-card p-8 md:grid-cols-[14rem,1fr]"
      style={{ "--reveal-delay": "0.02s" } as React.CSSProperties}
      data-testid="identity-panel"
    >
      <Portrait
        spokespersonId={spokesperson.id}
        portraitPath={spokesperson.portrait_path}
        name={spokesperson.name}
      />
      <div className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-1 flex-col gap-2">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
              Business brief
            </span>
            {spokesperson.business_brief.trim() ? (
              <p className="font-display text-xl leading-snug tracking-tight text-cream">
                {spokesperson.business_brief}
              </p>
            ) : (
              <p className="font-display text-xl leading-snug tracking-tight text-mist italic">
                No brief yet. The brief is what the spokesperson speaks
                about across every render — usually one paragraph
                describing what the business does and who it's for.
              </p>
            )}
          </div>
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onEdit}
              data-testid="identity-edit"
              aria-label={`Edit ${spokesperson.name}`}
              className="shrink-0"
            >
              <Pencil className="mr-1 h-3.5 w-3.5" />
              Edit
            </Button>
          )}
        </div>
        <MetadataGrid spokesperson={spokesperson} />
      </div>
    </section>
  );
}

function Portrait({
  spokespersonId,
  portraitPath,
  name,
}: {
  spokespersonId?: string;
  portraitPath: string;
  name: string;
}) {
  // SESSION 169 follow-up — Runway's CloudFront JWTs expire ~30
  // days after avatar create. The <img onError> handler fires a
  // refresh-portrait action which returns a fresh signed URL; we
  // swap the src and retry once. ``retried`` blocks the second
  // attempt so a permanently-broken URL can't loop forever.
  const refresh = useRefreshPortrait();
  const [retried, setRetried] = useState(false);
  const [src, setSrc] = useState(portraitPath);

  // Keep src in sync if the parent re-renders with a different
  // portrait_path (e.g. after the edit modal save).
  if (src !== portraitPath && !retried) {
    setSrc(portraitPath);
  }

  async function handleError() {
    if (retried || !spokespersonId) return;
    setRetried(true);
    try {
      const fresh = await refresh.mutateAsync(spokespersonId);
      if (fresh.portrait_path && fresh.portrait_path !== src) {
        setSrc(fresh.portrait_path);
      }
    } catch {
      // Swallow — the initials fallback will render via the
      // empty src guard below.
    }
  }

  // V3.6 — orbital portrait treatment per BRAND_IDENTITY_V3
  // §editorial patterns. Three concentric gold rings + an
  // orbiting dot at outer + a counter-orbiting dot at inner.
  // Mirrors the parent site's hero portrait
  // (`/24-7-ai-global/src/app/page.tsx` lines 77-107).
  if (src) {
    return (
      <div className="relative aspect-square w-full">
        {/* Decorative rings */}
        <div className="absolute inset-0 rounded-full border border-gold/15" aria-hidden="true" />
        <div className="absolute inset-3 rounded-full border border-gold/10" aria-hidden="true" />
        <div className="absolute inset-6 rounded-full border border-gold/[0.06]" aria-hidden="true" />
        {/* Outer orbiting dot — clockwise, 28s */}
        <div className="animate-orbit-slow absolute inset-0" aria-hidden="true">
          <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
            <div className="h-2 w-2 rounded-full bg-gold shadow-[0_0_24px_4px_rgba(201,169,97,0.6)]" />
          </div>
        </div>
        {/* Inner orbit — slower (just slower; the parent site
         * reverses direction but we don't have a reverse helper) */}
        <div className="animate-orbit absolute inset-4" aria-hidden="true">
          <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
            <div className="h-1.5 w-1.5 rounded-full bg-gold/80" />
          </div>
        </div>
        {/* Portrait */}
        <div className="luxe-shadow absolute inset-3 overflow-hidden rounded-full ring-1 ring-gold/40">
          <img
            src={src}
            alt=""
            className="h-full w-full object-cover"
            onError={handleError}
            data-testid="spokesperson-portrait-img"
          />
          <div
            className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-ink/40 via-transparent to-gold/5"
            aria-hidden="true"
          />
        </div>
      </div>
    );
  }
  // Initials fallback — same orbital frame, no portrait inside.
  const initials = deriveInitials(name);
  return (
    <div className="relative aspect-square w-full">
      <div className="absolute inset-0 rounded-full border border-gold/15" aria-hidden="true" />
      <div className="absolute inset-3 rounded-full border border-gold/10" aria-hidden="true" />
      <div className="absolute inset-6 rounded-full border border-gold/[0.06]" aria-hidden="true" />
      <div className="luxe-shadow absolute inset-3 flex items-center justify-center rounded-full ring-1 ring-gold/40 bg-gradient-to-br from-midnight via-ink to-midnight/70">
        <span
          className="font-display text-7xl font-light text-cream/70"
          style={{ fontVariationSettings: '"opsz" 144, "SOFT" 50' } as React.CSSProperties}
          aria-hidden
        >
          {initials}
        </span>
      </div>
    </div>
  );
}

function MetadataGrid({ spokesperson }: { spokesperson: Spokesperson }) {
  const rows: Array<[string, string]> = [
    ["Tone", spokesperson.tone_archetype],
    ["Visual subject", spokesperson.visual_subject || "—"],
    ["Avatar id", spokesperson.runway_avatar_id || "—"],
    ["Voice id", spokesperson.voice_id || "—"],
    ["Created", formatDate(spokesperson.created_at)],
    ["Updated", formatDate(spokesperson.updated_at)],
  ];
  return (
    <dl className="grid grid-cols-1 gap-x-8 gap-y-2 border-t border-luxe pt-4 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-baseline justify-between gap-4">
          <dt className="text-[11px] uppercase tracking-wider text-fog">
            {label}
          </dt>
          <dd className="truncate font-mono text-xs text-foreground/80">
            {value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function SetupPanel({
  spokesperson,
  pendingItems,
}: {
  spokesperson: Spokesperson;
  pendingItems: SetupItem[];
}) {
  // Hide-on-completion (SESSION 134 — slice 11): the panel only
  // renders when there are pending items. Fully configured rows
  // skip this whole column up in the parent. We still defensively
  // guard here in case a caller forgets to filter.
  if (pendingItems.length === 0) return null;

  return (
    <aside
      className="flex flex-col gap-5"
      aria-label="Setup checklist"
      data-testid="setup-panel"
    >
      <PanelHeader title="Set up" count={pendingItems.length} />
      <div className="rounded-md border bg-card p-6 luxe-shadow">
        <ol className="flex flex-col gap-6">
          {pendingItems.map((it, i) => (
            <li
              key={it.kind}
              className="grid grid-cols-[2rem,1fr] items-baseline gap-4"
              data-testid={`setup-item-${it.kind}`}
            >
              <span className="font-display text-2xl leading-none tabular-nums text-fog">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="flex flex-col gap-2">
                <span className="font-display text-lg leading-snug tracking-tight">
                  {it.label}
                </span>
                <span className="text-xs text-fog">{it.body}</span>
                {it.kind === "voice" && (
                  <VoiceSetupAffordance spokespersonId={spokesperson.id} />
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </aside>
  );
}

function VoiceSetupAffordance({ spokespersonId }: { spokespersonId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [value, setValue] = useState<VoiceCaptureValue | null>(null);
  const clone = useCloneVoice();

  if (!expanded) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-1 self-start"
        onClick={() => setExpanded(true)}
        data-testid="voice-setup-open"
      >
        <Mic className="mr-1 h-3 w-3" />
        Set up voice
      </Button>
    );
  }

  const submit = () => {
    if (!value) return;
    const payload = (() => {
      if (value.mode === "preset") {
        return { id: spokespersonId, preset: value.preset };
      }
      return { id: spokespersonId, audio_data_uri: value.dataUri };
    })();
    clone.mutate(payload, {
      onSuccess: () => {
        setValue(null);
        setExpanded(false);
      },
    });
  };

  return (
    <div className="mt-2 flex flex-col gap-3" data-testid="voice-setup-panel">
      <VoiceCapture value={value} onChange={setValue} />
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setValue(null);
            setExpanded(false);
            clone.reset();
          }}
          disabled={clone.isPending}
          data-testid="voice-setup-cancel"
        >
          Cancel
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={submit}
          disabled={!value || clone.isPending}
          data-testid="voice-setup-submit"
        >
          {clone.isPending ? "Saving…" : "Save voice"}
        </Button>
      </div>
      {clone.isError && (
        <p className="text-xs text-destructive" data-testid="voice-setup-error">
          Couldn't save the voice. Try again, or pick a different mode.
        </p>
      )}
    </div>
  );
}

function VideosPanel({
  videos,
  loading,
  error,
  spokespersonId,
}: {
  videos: Video[] | undefined;
  loading: boolean;
  error: unknown;
  spokespersonId: string;
}) {
  const hasVideos = !!videos && videos.length > 0;
  return (
    <section className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between border-b border-luxe pb-3">
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-xl tracking-tight">Renders</h2>
          {typeof videos?.length === "number" && (
            <span className="font-mono text-xs text-fog">
              {videos.length}
            </span>
          )}
        </div>
        {hasVideos && (
          <Link
            to={`/workspace/videos?spokesperson=${spokespersonId}`}
            data-testid="videos-library-link"
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-foreground"
          >
            View all in library →
          </Link>
        )}
      </div>
      {loading ? <VideosSkeleton /> : null}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {videos && videos.length === 0 && (
        <div
          className="reveal flex flex-col gap-2 rounded-md border border-dashed border-luxe bg-card/50 p-8 text-center"
          data-testid="videos-empty"
        >
          <p className="font-display text-xl tracking-tight">
            No renders yet
          </p>
          <p className="mx-auto max-w-md text-sm text-fog">
            Once this spokesperson is set up, every video you make with
            them lands here, newest first.
          </p>
        </div>
      )}
      {videos && videos.length > 0 && (
        <ol className="flex flex-col" data-testid="videos-list">
          {videos.map((v, i) => (
            <VideoRow
              key={v.id}
              video={v}
              index={i}
              revealDelay={`${0.06 + i * 0.05}s`}
            />
          ))}
        </ol>
      )}
    </section>
  );
}

// ---- Atoms ---------------------------------------------------------

function PanelHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-baseline justify-between border-b border-luxe pb-3">
      <h2 className="font-display text-xl tracking-tight">{title}</h2>
      {typeof count === "number" && (
        <span className="font-mono text-xs text-fog">{count}</span>
      )}
    </div>
  );
}

type PillTone = "ready" | "rendering" | "failed" | "muted";

function StatusPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: PillTone;
}) {
  const toneClass = {
    ready: "border-primary/40 bg-primary/10 text-primary",
    rendering: "border-primary/30 bg-primary/5 text-primary",
    failed: "border-destructive/40 bg-destructive/10 text-destructive",
    muted: "border-border bg-muted text-fog",
  }[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-sm border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
        toneClass,
      )}
      data-testid={`status-pill-${label.toLowerCase()}`}
    >
      <span className="text-fog/70">{label}</span>
      <span className="text-current">{value}</span>
    </span>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
      {message}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-3 border-b border-luxe pb-8">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-14 w-2/3 rounded bg-muted" />
      </div>
      <div className="grid grid-cols-1 gap-6 rounded-md border bg-card p-8 luxe-shadow md:grid-cols-[14rem,1fr]">
        <div className="aspect-square w-full rounded bg-muted" />
        <div className="flex flex-col gap-3">
          <div className="h-3 w-24 rounded bg-muted" />
          <div className="h-5 w-full rounded bg-muted" />
          <div className="h-5 w-3/4 rounded bg-muted" />
        </div>
      </div>
    </div>
  );
}

function VideosSkeleton() {
  return (
    <div className="flex flex-col">
      {Array.from({ length: 2 }).map((_, i) => (
        <div
          key={i}
          className="grid grid-cols-[2.5rem,1fr,auto] items-baseline gap-4 border-b border-luxe py-4"
        >
          <div className="h-7 w-8 rounded bg-muted" />
          <div className="flex flex-col gap-2">
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-3 w-1/3 rounded bg-muted/70" />
          </div>
          <div className="h-3 w-12 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}

function DetailError({ message }: { message: string }) {
  return (
    <div className="flex flex-col gap-6 py-12 text-center">
      <p className="font-display text-3xl tracking-tight">{message}</p>
      <p className="text-sm text-fog">
        The spokesperson may have been archived, or this link is stale.
      </p>
      <div className="mx-auto">
        <Link to="/dashboard">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-1 h-3 w-3" /> Back to workspace
          </Button>
        </Link>
      </div>
    </div>
  );
}

// ---- Helpers -------------------------------------------------------

interface SetupItem {
  kind: "brief" | "avatar" | "voice";
  label: string;
  body: string;
  done: boolean;
}

function buildSetupItems(s: Spokesperson): SetupItem[] {
  return [
    {
      kind: "brief",
      label: "Business brief",
      body: "One paragraph describing what this spokesperson speaks about.",
      done: Boolean(s.business_brief.trim()),
    },
    {
      kind: "avatar",
      label: "Runway avatar",
      body: "Portrait + Runway avatar id bound. Ships with create-spokesperson (S-06).",
      done: Boolean(s.runway_avatar_id) && s.runway_avatar_status !== "failed",
    },
    {
      kind: "voice",
      label: "Voice",
      body: "Either a Runway preset or a custom clone — pick one and you're done.",
      done: Boolean(s.voice_id),
    },
  ];
}

function prettyStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function statusTone(status: string): PillTone {
  if (status === "ready") return "ready";
  if (status === "archived") return "muted";
  return "muted";
}

function prettyAvatarStatus(status: string): string {
  if (!status) return "Not set";
  return status.replace(/_/g, " ");
}

function avatarTone(status: string): PillTone {
  if (!status) return "muted";
  if (status === "ready" || status === "mock") return "ready";
  if (status === "rendering" || status === "pending") return "rendering";
  if (status === "failed") return "failed";
  return "muted";
}

function deriveInitials(name: string): string {
  const cleaned = (name || "").trim();
  if (!cleaned) return "?";
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0]!.slice(0, 2).toUpperCase();
  return (words[0]![0]! + words[words.length - 1]![0]!).toUpperCase();
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function extractMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Something went wrong fetching this spokesperson.";
}

// SESSION 153 / R8.0 — "Talk to {name}" CTA. Renders only
// for fully-configured spokespeople (allDone) so we don't
// route operators into a session that can't actually start
// (the broker rejects creates without runway_avatar_id).
function TalkCta({ spokesperson }: { spokesperson: Spokesperson }) {
  return (
    <section
      className="reveal flex flex-col gap-3 rounded-md border bg-card p-6 sm:flex-row sm:items-center sm:justify-between"
      style={{ "--reveal-delay": "0.03s" } as React.CSSProperties}
      data-testid="talk-cta"
    >
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold tracking-tight">
          Talk live with {spokesperson.name}
        </h2>
        <p className="text-sm text-fog">
          Start a real-time audio session grounded in your
          workspace knowledge.
        </p>
      </div>
      <Button asChild>
        <Link
          to={`/spokespeople/${spokesperson.id}/talk`}
          data-testid="talk-cta-link"
        >
          <Mic className="mr-2 h-4 w-4" />
          Talk to {spokesperson.name}
        </Link>
      </Button>
    </section>
  );
}
