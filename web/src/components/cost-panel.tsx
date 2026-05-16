/**
 * Workspace cost telemetry panel — K7.1 (SESSION 174).
 *
 * Surfaces the per-surface + month-to-date cost rollup the F3
 * workspace overview endpoint added. Three surfaces split out
 * (compositions / images / realtime), plus an MTD-vs-all-time
 * pivot so the operator can see this-month spend at a glance.
 *
 * No tier limits or alerts in v1 — purely informational. Tier
 * caps already exist on the billing surface (videos /
 * spokespeople / realtime sessions / realtime minutes); this
 * panel is the dollar-cost lens, not the tier-quota lens.
 *
 * The micros-to-display conversion follows the platform's
 * convention: 1 USD = 1_000_000 micros. Stability credits are
 * priced ≈ $0.001 / credit so an image asset cost like 6_500
 * micros displays as $0.0065 — operators see real spend, not
 * raw credits.
 */
import { Film, Image as ImageIcon, MessageCircle, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OverviewCostBreakdown } from "@/lib/api/overview";

interface CostPanelProps {
  loading: boolean;
  error: unknown;
  data: OverviewCostBreakdown | undefined;
}

export function CostPanel({ loading, error, data }: CostPanelProps) {
  return (
    <section
      data-testid="cost-panel"
      className="flex flex-col gap-4 rounded-md border border-border bg-card p-5"
    >
      <header className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Spend
          </span>
          <h2 className="font-display text-2xl leading-tight">
            Workspace costs
          </h2>
        </div>
        <Wallet className="h-5 w-5 text-muted-foreground" aria-hidden />
      </header>

      {loading && <SkeletonRows />}
      {!loading && Boolean(error) && (
        <p
          data-testid="cost-panel-error"
          className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive"
        >
          Couldn't load cost data. The dashboard auto-retries.
        </p>
      )}
      {!loading && !error && !data && (
        <p
          data-testid="cost-panel-unavailable"
          className="text-xs text-muted-foreground"
        >
          Cost telemetry not available from this backend (pre-K7.1).
        </p>
      )}
      {!loading && !error && data && <CostBody data={data} />}
    </section>
  );
}

function CostBody({ data }: { data: OverviewCostBreakdown }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <TotalCard
          label="This month"
          micros={data.mtd_micros}
          emphasis="primary"
          testid="cost-total-mtd"
        />
        <TotalCard
          label="All time"
          micros={data.total_micros}
          emphasis="muted"
          testid="cost-total-alltime"
        />
        <div className="hidden flex-col justify-center text-xs text-muted-foreground sm:flex">
          <span>
            Since{" "}
            <strong className="text-foreground">
              {formatMonthStart(data.month_start)}
            </strong>
          </span>
          <span className="opacity-70">
            Cumulative dollar spend across all surfaces.
          </span>
        </div>
      </div>

      <ul className="flex flex-col gap-1" data-testid="cost-breakdown-list">
        <SurfaceRow
          icon={Film}
          label="Videos (compositions)"
          mtdMicros={data.mtd_compositions_micros}
          totalMicros={data.compositions_micros}
          testid="cost-row-compositions"
        />
        <SurfaceRow
          icon={ImageIcon}
          label="Images"
          mtdMicros={data.mtd_images_micros}
          totalMicros={data.images_micros}
          testid="cost-row-images"
        />
        <SurfaceRow
          icon={MessageCircle}
          label="Realtime sessions"
          mtdMicros={data.mtd_realtime_micros}
          totalMicros={data.realtime_micros}
          testid="cost-row-realtime"
        />
      </ul>
    </div>
  );
}

function TotalCard({
  label,
  micros,
  emphasis,
  testid,
}: {
  label: string;
  micros: number;
  emphasis: "primary" | "muted";
  testid: string;
}) {
  return (
    <div
      data-testid={testid}
      className={cn(
        "flex flex-col gap-1 rounded-md border p-3",
        emphasis === "primary"
          ? "border-foreground/30 bg-foreground/5"
          : "border-border bg-muted/30",
      )}
    >
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </span>
      <span className="font-display text-2xl leading-tight tabular-nums">
        {formatDollars(micros)}
      </span>
    </div>
  );
}

function SurfaceRow({
  icon: Icon,
  label,
  mtdMicros,
  totalMicros,
  testid,
}: {
  icon: LucideIcon;
  label: string;
  mtdMicros: number;
  totalMicros: number;
  testid: string;
}) {
  return (
    <li
      data-testid={testid}
      className="flex items-center justify-between gap-3 border-b border-border/60 py-2 last:border-b-0"
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
        <span className="text-sm">{label}</span>
      </div>
      <div className="flex flex-col items-end gap-0 text-xs">
        <span className="font-mono tabular-nums">
          {formatDollars(mtdMicros)}{" "}
          <span className="text-muted-foreground">MTD</span>
        </span>
        <span className="font-mono tabular-nums text-muted-foreground">
          {formatDollars(totalMicros)} all-time
        </span>
      </div>
    </li>
  );
}

function SkeletonRows() {
  return (
    <div className="flex flex-col gap-2" data-testid="cost-panel-skeleton">
      <div className="h-16 animate-pulse rounded-md bg-muted/40" />
      <div className="h-10 animate-pulse rounded-md bg-muted/30" />
      <div className="h-10 animate-pulse rounded-md bg-muted/30" />
      <div className="h-10 animate-pulse rounded-md bg-muted/30" />
    </div>
  );
}

// ---- formatting helpers ------------------------------------------

export function formatDollars(micros: number): string {
  // micros → dollars. The minimum unit we want visible is the
  // tenth of a cent ($0.001) because Stability credits sit at
  // ≈ $0.001/credit and a single core image is ~$0.003. Truncate
  // anything sub-fractional to four decimals so $0.0065 shows
  // exactly, and switch to $0.00 / $0.0X precision on bigger
  // numbers so a $42.50 spend doesn't read as $42.5000.
  if (micros === 0) return "$0.00";
  const dollars = micros / 1_000_000;
  if (dollars < 0.01) return `$${dollars.toFixed(4)}`;
  if (dollars < 1) return `$${dollars.toFixed(3)}`;
  return `$${dollars.toFixed(2)}`;
}

function formatMonthStart(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
