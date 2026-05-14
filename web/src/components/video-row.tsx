import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import type { Video } from "@/lib/api/videos";

interface VideoRowProps {
  video: Video;
  index: number;
  className?: string;
  revealDelay?: string;
}

/**
 * Editorial-styled row for the dashboard's recent-videos list. Hits
 * the magazine "numbered article list" form — leading roman-style
 * index, title, kicker with spokesperson + relative time.
 */
export function VideoRow({ video, index, className, revealDelay }: VideoRowProps) {
  const title =
    video.title.trim() ||
    (video.brief.trim() ? truncate(video.brief, 80) : "Untitled video");
  const kicker = [
    video.spokesperson_name,
    formatKind(video.kind),
    formatRelativeTime(video.created_at),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <li
      className={cn(
        "reveal group relative grid grid-cols-[2.5rem,1fr,auto] items-baseline gap-4 border-b border-border/60 py-4 transition-colors last:border-b-0 hover:bg-card/40",
        className,
      )}
      style={revealDelay ? ({ "--reveal-delay": revealDelay } as React.CSSProperties) : undefined}
      data-testid="video-row"
    >
      <span className="font-display text-3xl font-light leading-none text-muted-foreground tabular-nums">
        {String(index + 1).padStart(2, "0")}
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate font-display text-lg leading-snug tracking-tight">
          {/* Stretched-link: same pattern SESSION 118 introduced on
            * SpokespersonCard. ::after covers the row so the entire
            * surface is clickable but child semantics stay intact. */}
          <Link
            to={`/videos/${video.id}`}
            className="outline-none after:absolute after:inset-0"
          >
            {title}
          </Link>
        </span>
        <span className="truncate text-xs uppercase tracking-wider text-muted-foreground">
          {kicker}
        </span>
      </div>
      <StatusDot status={video.status} />
    </li>
  );
}

function StatusDot({ status }: { status: Video["status"] }) {
  const map: Record<Video["status"], { color: string; label: string }> = {
    pending: { color: "bg-muted-foreground/40", label: "Pending" },
    rendering: { color: "bg-primary/70 animate-pulse", label: "Rendering" },
    ready: { color: "bg-primary", label: "Ready" },
    failed: { color: "bg-destructive", label: "Failed" },
    archived: { color: "bg-muted-foreground/30", label: "Archived" },
  };
  const meta = map[status];
  return (
    <span className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
      <span className={cn("inline-block h-2 w-2 rounded-full", meta.color)} />
      {meta.label}
    </span>
  );
}

function formatKind(kind: string): string {
  return kind.replace(/_/g, " ");
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
