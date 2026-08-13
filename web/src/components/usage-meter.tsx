import { cn } from "@/lib/utils";

interface UsageMeterProps {
  used: number;
  limit: number | null;
  tier: string;
  status: string;
  className?: string;
}

/**
 * Thin editorial meter. Display-font usage count + sans-serif tier
 * line + a hairline progress rule. No fat progress bar — the meter
 * is informational, not the focal point.
 */
export function UsageMeter({
  used,
  limit,
  tier,
  status,
  className,
}: UsageMeterProps) {
  const isUnlimited = limit === null;
  const pct = isUnlimited ? 0 : Math.min(100, (used / Math.max(limit, 1)) * 100);
  const display = isUnlimited ? `${used}` : `${used} / ${limit}`;
  const isOver = !isUnlimited && used >= limit;
  const isWarning = !isUnlimited && !isOver && pct >= 80;

  return (
    <section
      className={cn(
        "reveal flex flex-col gap-3 rounded-md border bg-card p-6 shadow-paper",
        className,
      )}
      aria-label="Plan usage"
    >
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Videos this period
          </span>
          <span
            className={cn(
              "font-display text-4xl leading-none tracking-tight",
              isOver && "text-destructive",
            )}
          >
            {display}
          </span>
        </div>
        <div className="text-right text-xs">
          <div className="font-display text-base capitalize tracking-tight text-foreground">
            {tier}
          </div>
          <div className="uppercase tracking-wider text-muted-foreground">
            {status}
          </div>
        </div>
      </div>
      {!isUnlimited && (
        <div className="relative h-px w-full overflow-hidden bg-border" aria-hidden>
          <div
            className={cn(
              "absolute inset-y-0 left-0 transition-[width] duration-500 ease-out",
              isOver ? "bg-destructive" : isWarning ? "bg-primary" : "bg-foreground/60",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {isUnlimited && (
        <div className="text-xs text-muted-foreground">Unlimited on {tier}</div>
      )}
    </section>
  );
}
