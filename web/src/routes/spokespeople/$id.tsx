import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSpokesperson, type Spokesperson } from "@/lib/api/spokespeople";
import { useVideos, type Video } from "@/lib/api/videos";
import { VideoRow } from "@/components/video-row";
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

  if (sp.isLoading) return <DetailSkeleton />;
  if (sp.isError) return <DetailError message={extractMessage(sp.error)} />;
  if (!sp.data) return <DetailError message="Spokesperson not found." />;

  const s = sp.data;

  return (
    <div className="flex flex-col gap-12">
      <Masthead spokesperson={s} />
      <IdentityPanel spokesperson={s} />

      <section
        className="reveal grid grid-cols-1 gap-6 lg:grid-cols-[2fr,1fr]"
        style={{ "--reveal-delay": "0.04s" } as React.CSSProperties}
      >
        <VideosPanel
          videos={videos.data}
          loading={videos.isLoading}
          error={videos.error}
        />
        <SetupPanel spokesperson={s} />
      </section>
    </div>
  );
}

// ---- Sections -------------------------------------------------------

function Masthead({ spokesperson }: { spokesperson: Spokesperson }) {
  return (
    <header
      className="reveal flex flex-col gap-3 border-b border-border pb-8"
      data-testid="spokesperson-masthead"
    >
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="back-to-dashboard"
      >
        <ArrowLeft className="h-3 w-3" />
        Workspace
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex flex-col gap-3">
          <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Spokesperson
          </span>
          <h1
            className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
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
        <div className="flex flex-wrap items-center gap-2">
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
    </header>
  );
}

function IdentityPanel({ spokesperson }: { spokesperson: Spokesperson }) {
  return (
    <section
      className="reveal grid grid-cols-1 gap-6 rounded-md border bg-card p-8 shadow-paper md:grid-cols-[14rem,1fr]"
      style={{ "--reveal-delay": "0.02s" } as React.CSSProperties}
      data-testid="identity-panel"
    >
      <Portrait
        portraitPath={spokesperson.portrait_path}
        name={spokesperson.name}
      />
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Business brief
          </span>
          {spokesperson.business_brief.trim() ? (
            <p className="font-display text-xl leading-snug tracking-tight">
              {spokesperson.business_brief}
            </p>
          ) : (
            <p className="font-display text-xl leading-snug tracking-tight text-muted-foreground">
              No brief yet. The brief is what the spokesperson speaks
              about across every render — usually one paragraph
              describing what the business does and who it's for.
            </p>
          )}
        </div>
        <MetadataGrid spokesperson={spokesperson} />
      </div>
    </section>
  );
}

function Portrait({
  portraitPath,
  name,
}: {
  portraitPath: string;
  name: string;
}) {
  if (portraitPath) {
    return (
      <div className="aspect-square w-full overflow-hidden rounded border border-border bg-muted">
        <img src={portraitPath} alt="" className="h-full w-full object-cover" />
      </div>
    );
  }
  const initials = deriveInitials(name);
  return (
    <div className="flex aspect-square w-full items-center justify-center rounded border border-border bg-gradient-to-br from-muted via-card to-muted/70">
      <span
        className="font-display text-7xl font-light text-foreground/70"
        style={{ fontVariationSettings: '"opsz" 144, "SOFT" 50' } as React.CSSProperties}
        aria-hidden
      >
        {initials}
      </span>
    </div>
  );
}

function MetadataGrid({ spokesperson }: { spokesperson: Spokesperson }) {
  const rows: Array<[string, string]> = [
    ["Avatar id", spokesperson.runway_avatar_id || "—"],
    ["Voice id", spokesperson.voice_id || "—"],
    ["Created", formatDate(spokesperson.created_at)],
    ["Updated", formatDate(spokesperson.updated_at)],
  ];
  return (
    <dl className="grid grid-cols-1 gap-x-8 gap-y-2 border-t border-border/60 pt-4 sm:grid-cols-2">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-baseline justify-between gap-4">
          <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">
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

function SetupPanel({ spokesperson }: { spokesperson: Spokesperson }) {
  const items = buildSetupItems(spokesperson);
  const allDone = items.every((it) => it.done);

  return (
    <aside
      className="flex flex-col gap-5"
      aria-label="Setup checklist"
      data-testid="setup-panel"
    >
      <PanelHeader title="Setup" />
      <div className="rounded-md border bg-card p-6 shadow-paper">
        {allDone ? (
          <p className="font-display text-lg tracking-tight">
            Ready to render. Everything this spokesperson needs is in place.
          </p>
        ) : (
          <ol className="flex flex-col gap-4">
            {items.map((it, i) => (
              <li
                key={it.label}
                className="grid grid-cols-[2rem,1fr] items-baseline gap-4"
              >
                <span
                  className={cn(
                    "font-display text-2xl leading-none tabular-nums",
                    it.done ? "text-primary" : "text-muted-foreground",
                  )}
                >
                  {it.done ? "✓" : String(i + 1).padStart(2, "0")}
                </span>
                <div className="flex flex-col gap-1">
                  <span
                    className={cn(
                      "font-display text-lg leading-snug tracking-tight",
                      it.done && "text-muted-foreground line-through decoration-1",
                    )}
                  >
                    {it.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{it.body}</span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </aside>
  );
}

function VideosPanel({
  videos,
  loading,
  error,
}: {
  videos: Video[] | undefined;
  loading: boolean;
  error: unknown;
}) {
  return (
    <section className="flex flex-col gap-5">
      <PanelHeader title="Renders" count={videos?.length} />
      {loading ? <VideosSkeleton /> : null}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {videos && videos.length === 0 && (
        <div
          className="reveal flex flex-col gap-2 rounded-md border border-dashed border-border bg-card/50 p-8 text-center"
          data-testid="videos-empty"
        >
          <p className="font-display text-xl tracking-tight">
            No renders yet
          </p>
          <p className="mx-auto max-w-md text-sm text-muted-foreground">
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
    <div className="flex items-baseline justify-between border-b border-border/60 pb-3">
      <h2 className="font-display text-xl tracking-tight">{title}</h2>
      {typeof count === "number" && (
        <span className="font-mono text-xs text-muted-foreground">{count}</span>
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
    muted: "border-border bg-muted text-muted-foreground",
  }[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-sm border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
        toneClass,
      )}
      data-testid={`status-pill-${label.toLowerCase()}`}
    >
      <span className="text-muted-foreground/70">{label}</span>
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
      <div className="flex flex-col gap-3 border-b border-border pb-8">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-14 w-2/3 rounded bg-muted" />
      </div>
      <div className="grid grid-cols-1 gap-6 rounded-md border bg-card p-8 shadow-paper md:grid-cols-[14rem,1fr]">
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
          className="grid grid-cols-[2.5rem,1fr,auto] items-baseline gap-4 border-b border-border/60 py-4"
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
      <p className="text-sm text-muted-foreground">
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
  label: string;
  body: string;
  done: boolean;
}

function buildSetupItems(s: Spokesperson): SetupItem[] {
  return [
    {
      label: "Business brief",
      body: "One paragraph describing what this spokesperson speaks about.",
      done: Boolean(s.business_brief.trim()),
    },
    {
      label: "Runway avatar",
      body: "Portrait + Runway avatar id bound. Ships with create-spokesperson (S-06).",
      done: Boolean(s.runway_avatar_id) && s.runway_avatar_status !== "failed",
    },
    {
      label: "Voice",
      body: "Either a Runway preset or a custom clone. Voice clone UI ships in a later slice.",
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
