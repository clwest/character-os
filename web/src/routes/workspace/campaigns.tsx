/**
 * /workspace/campaigns — Personalized Video Campaign list view.
 *
 * SESSION B3.7. Lists all campaigns in the workspace.
 * Each row: name, status badge, spokesperson, recipient count, created_at.
 * Status filter chips at the top. "New campaign" CTA top-right.
 *
 * Scope: docs/design/PERSONALIZED_VIDEO_V1.md §B3.7.
 */
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, Video, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMe } from "@/lib/api/workspaces";
import {
  useCampaigns,
  campaignStatusTone,
  campaignStatusLabel,
  type CampaignStatus,
  type PersonalizedCampaign,
  CAMPAIGN_STATUSES,
} from "@/lib/api/campaigns";
import { cn } from "@/lib/utils";

// ---- Status filter chips labels ------------------------------

const FILTER_OPTIONS: Array<{ value: CampaignStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "in_flight", label: "In Flight" },
  { value: "completed", label: "Completed" },
  { value: "partial", label: "Partial" },
  { value: "failed", label: "Failed" },
];

// ---- Page component -----------------------------------------

export function WorkspaceCampaignsRoute() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  // ?status= filter. Empty string / "all" → no filter.
  const rawStatus = searchParams.get("status") ?? "all";
  const activeStatus: CampaignStatus | undefined =
    rawStatus !== "all" && (CAMPAIGN_STATUSES as readonly string[]).includes(rawStatus)
      ? (rawStatus as CampaignStatus)
      : undefined;

  const campaigns = useCampaigns(workspaceId, {
    status: activeStatus,
  });

  const results = campaigns.data ?? [];

  function handleFilterClick(value: CampaignStatus | "all") {
    if (value === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ status: value });
    }
  }

  return (
    <div className="flex flex-col gap-8">
      {/* ---- Page header --------------------------------------- */}
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Video className="h-7 w-7 text-muted-foreground" />
            <h1
              data-testid="campaigns-title"
              className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
            >
              Campaigns
            </h1>
          </div>
          <Button
            asChild
            data-testid="new-campaign-btn"
          >
            <Link to="/workspace/campaigns/new">
              <Plus className="mr-2 h-4 w-4" />
              New campaign
            </Link>
          </Button>
        </div>
        <p className="max-w-2xl text-base text-muted-foreground">
          Write one script template, paste a CSV of recipients, and launch —
          the system renders a personalized talking-head video for each row.
        </p>
      </header>

      {/* ---- Status filter chips ------------------------------- */}
      <div
        data-testid="status-filter-chips"
        className="flex flex-wrap gap-2"
      >
        {FILTER_OPTIONS.map((opt) => {
          const isActive = opt.value === (activeStatus ?? "all");
          return (
            <button
              key={opt.value}
              type="button"
              data-testid={`filter-chip-${opt.value}`}
              onClick={() => handleFilterClick(opt.value)}
              className={cn(
                "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                isActive
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* ---- List ---------------------------------------------- */}
      <section className="flex flex-col gap-4">
        <h2 className="font-display text-2xl tracking-tight">
          {activeStatus ? campaignStatusLabel(activeStatus) : "All"} campaigns
          {results.length > 0 && (
            <span className="ml-2 text-xl text-muted-foreground font-sans font-normal">
              ({results.length})
            </span>
          )}
        </h2>

        {/* Loading skeleton */}
        {campaigns.isLoading && (
          <ul
            data-testid="campaigns-skeleton"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {Array.from({ length: 4 }).map((_, i) => (
              <li
                key={i}
                className="flex items-start gap-4 px-5 py-4 animate-pulse"
              >
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/5 rounded bg-muted" />
                  <div className="h-3 w-3/5 rounded bg-muted" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Error state */}
        {campaigns.isError && (
          <div
            data-testid="campaigns-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
          >
            <p className="text-sm text-destructive">
              Failed to load campaigns:{" "}
              {(campaigns.error as Error).message}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="campaigns-retry"
              className="mt-3"
              onClick={() => campaigns.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!campaigns.isLoading && !campaigns.isError && results.length === 0 && (
          <div
            data-testid="campaigns-empty"
            className="rounded-md border border-dashed border-border p-12 text-center"
          >
            <Video className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-base font-medium">No campaigns yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Campaigns let you send personalized talking-head videos to a
              whole list of recipients at once.
            </p>
            <Button
              asChild
              size="sm"
              className="mt-4"
              data-testid="campaigns-empty-cta"
            >
              <Link to="/workspace/campaigns/new">Create your first campaign</Link>
            </Button>
          </div>
        )}

        {/* Campaign rows */}
        {results.length > 0 && (
          <ul
            data-testid="campaigns-list"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {results.map((campaign) => (
              <CampaignRow key={campaign.id} campaign={campaign} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---- CampaignRow ---------------------------------------------

function CampaignRow({ campaign }: { campaign: PersonalizedCampaign }) {
  const tone = campaignStatusTone(campaign.status);
  const label = campaignStatusLabel(campaign.status);
  const total = campaign.recipient_counts.total;

  return (
    <li
      data-testid={`campaign-row-${campaign.id}`}
      className="hover:bg-muted/30 transition-colors"
    >
      <Link
        to={`/workspace/campaigns/${campaign.id}`}
        data-testid={`campaign-link-${campaign.id}`}
        className="flex items-center gap-4 px-5 py-4"
      >
        {/* Name + spokesperson */}
        <div className="flex-1 min-w-0">
          <p
            data-testid={`campaign-name-${campaign.id}`}
            className="truncate text-sm font-medium"
            title={campaign.name}
          >
            {campaign.name}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {campaign.spokesperson_name}
          </p>
        </div>

        {/* Meta row: status badge + recipient count + date */}
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge tone={tone} label={label} />
          <span className="text-xs text-muted-foreground">
            {total === 1 ? "1 recipient" : `${total} recipients`}
          </span>
          <span className="text-xs text-muted-foreground/60">
            {relativeTime(campaign.created_at)}
          </span>
        </div>
      </Link>
    </li>
  );
}

// ---- StatusBadge helper --------------------------------------

export function StatusBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  label: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" &&
          "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- relativeTime helper (mirrors the workspace-assets pattern) -

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
