/**
 * CostTicker — R8.2 (SESSION 155).
 *
 * Renders the elapsed time + running cost estimate during
 * a live realtime session. Drives operator awareness as the
 * session approaches its provider-defined cap (5 minutes
 * for Runway today).
 *
 * Cost is purely client-side estimation against
 * ``ESTIMATED_COST_PER_MINUTE_MICROS`` (the same hardcoded
 * constant the IdlePanel forecast uses). R9 (cost
 * governance backend) ships per-provider micros-per-second
 * lookups; the ticker upgrades cleanly when those land.
 *
 * Color-shifts as the session approaches the cap:
 *   - 0-3 min   → muted
 *   - 3-4 min   → amber (heads-up)
 *   - 4-5 min   → destructive (last minute)
 */
import { useEffect, useState } from "react";

export interface CostTickerProps {
  /** ISO timestamp the session became READY. Counting
   *  starts here. */
  startedAt: string | null;
  /** Per-minute cost estimate in micros ($1 = 1_000_000). */
  costPerMinuteMicros: number;
  /** Provider cap in minutes (5 for Runway). */
  maxMinutes: number;
  /** Demo-mode marker — appended to the label so
   *  operators don't conflate mock cost with real spend. */
  mockMode: boolean;
}

export function CostTicker({
  startedAt,
  costPerMinuteMicros,
  maxMinutes,
  mockMode,
}: CostTickerProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(() =>
    computeElapsedSeconds(startedAt),
  );

  useEffect(() => {
    if (!startedAt) return;
    // Recompute immediately on mount so the first frame
    // doesn't show 0:00.
    setElapsedSeconds(computeElapsedSeconds(startedAt));
    const handle = setInterval(() => {
      setElapsedSeconds(computeElapsedSeconds(startedAt));
    }, 1000);
    return () => clearInterval(handle);
  }, [startedAt]);

  const capSeconds = maxMinutes * 60;
  const clampedElapsed = Math.min(elapsedSeconds, capSeconds);
  const cents = (clampedElapsed * costPerMinuteMicros) / 60 / 10_000;
  const dollars = (cents / 100).toFixed(2);

  // Color thresholds: muted < 3 min, amber 3-4, destructive
  // 4-5. Last 60s reads as a hard warning the operator
  // should wrap up.
  const minutesIn = clampedElapsed / 60;
  const tone =
    minutesIn >= maxMinutes - 1
      ? "destructive"
      : minutesIn >= maxMinutes - 2
        ? "amber"
        : "muted";

  return (
    <div
      className={
        "inline-flex flex-col gap-0.5 rounded border px-3 py-1.5 text-xs " +
        toneClasses(tone)
      }
      data-testid="cost-ticker"
      data-tone={tone}
      data-elapsed-seconds={elapsedSeconds}
    >
      <div className="flex items-baseline gap-2 font-mono">
        <span>{formatTime(clampedElapsed)}</span>
        <span>·</span>
        <span>${dollars}</span>
        {mockMode && <span className="text-[10px] uppercase">(demo)</span>}
      </div>
      <div className="text-[10px] text-muted-foreground">
        {capSeconds - clampedElapsed > 0
          ? `${formatTime(capSeconds - clampedElapsed)} remaining`
          : "session cap reached"}
      </div>
    </div>
  );
}

function computeElapsedSeconds(startedAt: string | null): number {
  if (!startedAt) return 0;
  const start = new Date(startedAt).getTime();
  if (Number.isNaN(start)) return 0;
  return Math.max(0, Math.floor((Date.now() - start) / 1000));
}

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function toneClasses(tone: "muted" | "amber" | "destructive"): string {
  switch (tone) {
    case "destructive":
      return "border-destructive bg-destructive/10 text-destructive";
    case "amber":
      return "border-yellow-400 bg-yellow-50 text-yellow-900";
    default:
      return "border-border bg-muted/40 text-foreground";
  }
}
