import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVideo, type Video } from "@/lib/api/videos";
import { cn } from "@/lib/utils";

/**
 * Video status + playback (S-11 of UI_REDESIGN_V2.md).
 *
 * The canonical fire-then-poll consumer for the entire SPA. Every
 * future async surface (voice clone status, spider dashboards,
 * batch operations) should pattern-match against this route's
 * shape:
 *
 *   - useVideo's refetchInterval is a function of current data,
 *     returns false on terminal states.
 *   - Status pill + elapsed-time + live progress copy while non-
 *     terminal.
 *   - On `ready`: <video controls> with output_path. Skeleton
 *     during initial load.
 *   - On `failed`: destructive callout with error_message + a
 *     "Try again" CTA back to the render form.
 *
 * The Celery worker (SESSION 109) writes terminal state in
 * ~13 s (mock) / 60-120 s (real). The page assumes Redis +
 * Celery worker are up.
 */
export function VideoStatusRoute() {
  const { id } = useParams<{ id: string }>();
  const query = useVideo(id);

  if (query.isLoading) return <StatusSkeleton />;
  if (query.isError || !query.data) {
    return <NotFound />;
  }

  const video = query.data;
  return (
    <div className="flex flex-col gap-12">
      <Masthead video={video} />
      <PrimaryPanel video={video} />
      <DetailGrid video={video} />
    </div>
  );
}

// ---- Sections ------------------------------------------------------

function Masthead({ video }: { video: Video }) {
  const backTo = `/spokespeople/${video.spokesperson}`;
  return (
    <header
      className="reveal flex flex-col gap-3 border-b border-border pb-8"
      data-testid="video-masthead"
    >
      <Link
        to={backTo}
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="back-to-spokesperson"
      >
        <ArrowLeft className="h-3 w-3" />
        {video.spokesperson_name ?? "Spokesperson"}
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex flex-col gap-3">
          <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Render · {video.kind.replace(/_/g, " ")}
          </span>
          <h1
            className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
            style={
              {
                fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
              } as React.CSSProperties
            }
            data-testid="video-title"
          >
            {video.title.trim() || "Untitled render"}
          </h1>
        </div>
        <StatusPill status={video.status} />
      </div>
    </header>
  );
}

function PrimaryPanel({ video }: { video: Video }) {
  if (video.status === "ready") {
    return <Playback video={video} />;
  }
  if (video.status === "failed") {
    return <FailedCallout video={video} />;
  }
  return <RenderingPanel video={video} />;
}

function Playback({ video }: { video: Video }) {
  return (
    <section
      className="reveal flex flex-col gap-4 rounded-md border bg-card p-6 shadow-paper"
      data-testid="playback-panel"
    >
      <div className="overflow-hidden rounded border border-border bg-muted">
        <video
          src={video.output_path}
          controls
          className="aspect-video w-full bg-black"
          data-testid="video-player"
        />
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-4 border-t border-border/60 pt-4 text-xs text-muted-foreground">
        <span className="font-mono uppercase tracking-wider">
          Ready
          {video.duration_seconds !== null
            ? ` · ${video.duration_seconds.toFixed(1)}s`
            : ""}
          {video.completed_at ? ` · ${formatRelativeTime(video.completed_at)}` : ""}
        </span>
        <a
          href={video.output_path}
          target="_blank"
          rel="noreferrer"
          className="font-mono uppercase tracking-wider underline-offset-4 hover:underline hover:text-foreground"
          data-testid="open-source"
        >
          Open original ↗
        </a>
      </div>
    </section>
  );
}

function RenderingPanel({ video }: { video: Video }) {
  const elapsed = useElapsed(video.created_at);
  const headline =
    video.status === "pending" ? "Queued." : "Rendering.";
  const body =
    video.status === "pending"
      ? "Sitting in the queue. The Celery worker picks it up next."
      : "Runway is processing. Mock mode lands in ~13s; real mode takes 60–120s.";

  return (
    <section
      className="reveal flex flex-col gap-5 rounded-md border bg-card p-8 shadow-paper"
      data-testid="rendering-panel"
    >
      <div className="flex flex-col gap-3">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          In flight
        </span>
        <p
          className="font-display text-4xl leading-tight tracking-tight"
          style={
            {
              fontVariationSettings: '"opsz" 72, "SOFT" 25' ,
            } as React.CSSProperties
          }
        >
          {headline}
        </p>
        <p className="max-w-2xl text-sm text-muted-foreground">{body}</p>
      </div>
      <div className="flex items-baseline justify-between border-t border-border/60 pt-4">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Elapsed
        </span>
        <span
          className="font-display text-2xl leading-none tabular-nums"
          data-testid="elapsed"
        >
          {formatElapsed(elapsed)}
        </span>
      </div>
      <div className="relative h-px w-full overflow-hidden bg-border" aria-hidden>
        <div className="absolute inset-y-0 left-0 w-1/2 animate-pulse bg-primary/60" />
      </div>
    </section>
  );
}

function FailedCallout({ video }: { video: Video }) {
  return (
    <section
      className="reveal flex flex-col gap-4 rounded-md border border-destructive/40 bg-destructive/5 p-8"
      data-testid="failed-panel"
    >
      <div className="flex flex-col gap-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-destructive">
          Failed
        </span>
        <p className="font-display text-3xl leading-tight tracking-tight">
          Runway couldn't finish this render.
        </p>
        {video.error_message && (
          <p className="font-mono text-sm text-destructive">
            {video.error_message}
          </p>
        )}
      </div>
      <Link to={`/spokespeople/${video.spokesperson}/render`}>
        <Button variant="outline" size="sm">
          Try again
        </Button>
      </Link>
    </section>
  );
}

function DetailGrid({ video }: { video: Video }) {
  const rows: Array<[string, string]> = [
    ["Brief", video.brief],
    ["Spokesperson", video.spokesperson_name ?? video.spokesperson],
    ["Kind", video.kind.replace(/_/g, " ")],
    ["Task id", video.media_engine_task_id || "—"],
    ["Created", formatRelativeTime(video.created_at)],
    [
      "Completed",
      video.completed_at ? formatRelativeTime(video.completed_at) : "—",
    ],
  ];

  return (
    <section
      className="reveal flex flex-col gap-5"
      style={{ "--reveal-delay": "0.04s" } as React.CSSProperties}
    >
      <h2 className="font-display text-xl tracking-tight border-b border-border/60 pb-3">
        Detail
      </h2>
      <dl
        className="grid grid-cols-1 gap-x-12 gap-y-4 sm:grid-cols-[10rem,1fr]"
        data-testid="video-detail-grid"
      >
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex flex-col gap-1 border-b border-border/40 pb-3 sm:contents sm:border-b-0 sm:pb-0"
          >
            <dt className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {label}
            </dt>
            <dd
              className={cn(
                label === "Brief"
                  ? "font-display text-base leading-snug"
                  : "text-sm",
                label === "Task id" && "font-mono",
                "text-foreground",
              )}
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ---- Atoms ---------------------------------------------------------

function StatusPill({ status }: { status: Video["status"] }) {
  const map: Record<Video["status"], { label: string; className: string }> = {
    pending: {
      label: "Pending",
      className: "border-border bg-muted text-muted-foreground",
    },
    rendering: {
      label: "Rendering",
      className: "border-primary/40 bg-primary/10 text-primary",
    },
    ready: {
      label: "Ready",
      className: "border-primary/40 bg-primary/10 text-primary",
    },
    failed: {
      label: "Failed",
      className: "border-destructive/40 bg-destructive/10 text-destructive",
    },
    archived: {
      label: "Archived",
      className: "border-border bg-muted/60 text-muted-foreground",
    },
  };
  const meta = map[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
        meta.className,
      )}
      data-testid="status-pill"
    >
      {meta.label}
    </span>
  );
}

function StatusSkeleton() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-3 border-b border-border pb-8">
        <div className="h-3 w-32 rounded bg-muted" />
        <div className="h-14 w-2/3 rounded bg-muted" />
      </div>
      <div className="h-40 rounded-md border bg-card shadow-paper" />
    </div>
  );
}

function NotFound() {
  return (
    <div className="flex flex-col gap-6 py-12 text-center">
      <p className="font-display text-3xl tracking-tight">Video not found.</p>
      <p className="text-sm text-muted-foreground">
        The link may be stale or the row was archived.
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

/** Tracks wall-clock elapsed since `created_at`, ticking every
 *  second. Halts on unmount. */
function useElapsed(createdAt: string): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = () => setNow(Date.now());
    const interval = window.setInterval(tick, 1_000);
    return () => window.clearInterval(interval);
  }, []);
  const then = new Date(createdAt).getTime();
  if (Number.isNaN(then)) return 0;
  return Math.max(0, Math.floor((now - then) / 1000));
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${mins}m ${String(rest).padStart(2, "0")}s`;
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffMs = Date.now() - then;
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
