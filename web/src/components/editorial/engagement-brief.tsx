/**
 * EngagementBrief — V3 editorial dossier-style key/value card.
 *
 * Mirrors the parent site's § 06 "Engagement Brief" aside
 * (page.tsx lines 469-493): gold-bordered left edge, microtype
 * gold title, definition-list rows of microtype label →
 * italic display value, with the last row optionally
 * emphasized (gold-bright "Reply · By morning"-style hook).
 *
 * Surfaces this lands on:
 * - Public marketing / landing pages
 * - Sign-in / sign-up engagement frame
 * - The spokesperson "Talk" CTA lead-capture (if it ever opens
 *   publicly)
 * - Any contact / inquiry block
 *
 * Don't put one on every page — the editorial weight depends
 * on selective placement.
 */
import { cn } from "@/lib/utils";

export interface EngagementBriefEntry {
  /** Microtype label (e.g. "Cadence", "Format"). */
  label: string;
  /** Italic display value. */
  value: string;
  /** Render the value in gold-bright (the brief's signature emphasis). */
  emphasis?: boolean;
}

interface EngagementBriefProps {
  /** Title above the list. Default "Engagement Brief". */
  title?: string;
  /** Definition rows in display order. */
  entries: EngagementBriefEntry[];
  /** Append extra classes. */
  className?: string;
}

export function EngagementBrief({
  title = "Engagement Brief",
  entries,
  className,
}: EngagementBriefProps) {
  return (
    <aside data-testid="engagement-brief" className={className}>
      <div className="border-l border-gold/30 pl-8">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-gold/80">
          {title}
        </div>
        <dl className="mt-6 space-y-5 text-sm">
          {entries.map((entry, index) => {
            const isLast = index === entries.length - 1;
            return (
              <div
                key={`${entry.label}-${index}`}
                data-testid="engagement-brief-row"
                className={cn(
                  "flex justify-between gap-4",
                  !isLast && "border-b border-luxe/60 pb-3",
                )}
              >
                <dt className="font-mono text-[10.5px] uppercase tracking-[0.26em] text-fog">
                  {entry.label}
                </dt>
                <dd
                  className={cn(
                    "font-display italic",
                    entry.emphasis ? "text-gold-bright" : "text-cream/90",
                  )}
                >
                  {entry.value}
                </dd>
              </div>
            );
          })}
        </dl>
      </div>
    </aside>
  );
}
