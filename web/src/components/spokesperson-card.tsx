import { cn } from "@/lib/utils";
import type { Spokesperson } from "@/lib/api/spokespeople";

interface SpokespersonCardProps {
  spokesperson: Spokesperson;
  className?: string;
  /** Inline animation delay, e.g. "0.08s" — for staggered reveals. */
  revealDelay?: string;
}

/**
 * Editorial-warm tile. Initials-in-serif portrait until real
 * portraits land (`portrait_path` will become a real image URL when
 * the SESSION 108 avatar flow runs against real Runway credits).
 *
 * Status pill: ready=oxblood, setup_needed=muted, archived=hidden.
 */
export function SpokespersonCard({
  spokesperson,
  className,
  revealDelay,
}: SpokespersonCardProps) {
  const initials = deriveInitials(spokesperson.name);
  const brief = spokesperson.business_brief.trim() || "No brief yet.";
  const briefSnippet = brief.length > 140 ? brief.slice(0, 137) + "…" : brief;

  return (
    <article
      className={cn(
        "reveal group relative flex flex-col gap-5 rounded-md border bg-card p-6 shadow-paper",
        "transition-shadow duration-150 ease-out hover:shadow-paper-hover",
        className,
      )}
      style={revealDelay ? ({ "--reveal-delay": revealDelay } as React.CSSProperties) : undefined}
    >
      <Portrait
        initials={initials}
        portraitPath={spokesperson.portrait_path}
      />
      <div className="flex flex-col gap-2">
        <h3 className="font-display text-2xl leading-tight tracking-tight">
          {spokesperson.name}
        </h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {briefSnippet}
        </p>
      </div>
      <div className="mt-auto flex items-center justify-between border-t border-border pt-4 text-xs">
        <StatusBadge status={spokesperson.status} />
        <span className="font-mono text-muted-foreground">
          {spokesperson.video_count ?? 0} video
          {spokesperson.video_count === 1 ? "" : "s"}
        </span>
      </div>
    </article>
  );
}

function Portrait({
  initials,
  portraitPath,
}: {
  initials: string;
  portraitPath: string;
}) {
  if (portraitPath) {
    return (
      <div className="aspect-square w-full overflow-hidden rounded border border-border bg-muted">
        <img
          src={portraitPath}
          alt=""
          className="h-full w-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className={cn(
        "flex aspect-square w-full items-center justify-center rounded border border-border",
        "bg-gradient-to-br from-muted via-card to-muted/70",
      )}
      aria-hidden
    >
      <span
        className="font-display text-5xl font-light text-foreground/70"
        style={{ fontVariationSettings: '"opsz" 144, "SOFT" 50' }}
      >
        {initials}
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    ready: {
      label: "Ready",
      className: "border-primary/40 bg-primary/10 text-primary",
    },
    setup_needed: {
      label: "Setup needed",
      className: "border-border bg-muted text-muted-foreground",
    },
    archived: {
      label: "Archived",
      className: "border-border bg-muted/60 text-muted-foreground",
    },
  };
  const meta = map[status] ?? {
    label: status,
    className: "border-border bg-muted text-muted-foreground",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
        meta.className,
      )}
    >
      {meta.label}
    </span>
  );
}

function deriveInitials(name: string): string {
  const cleaned = (name || "").trim();
  if (!cleaned) return "?";
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0]!.slice(0, 2).toUpperCase();
  return (words[0]![0]! + words[words.length - 1]![0]!).toUpperCase();
}
