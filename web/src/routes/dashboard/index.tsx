import { Link, useNavigate } from "react-router-dom";
import { Plus, Loader2, CheckCircle2, XCircle, MinusCircle, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSession, useSignout } from "@/lib/auth/use-session";
import { useMe, useSubscription } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { SpokespersonCard } from "@/components/spokesperson-card";
import { UsageMeter } from "@/components/usage-meter";
import { CostPanel } from "@/components/cost-panel";
import {
  useWorkspaceOverview,
  type OverviewComposition,
  type OverviewSpokesperson,
  type WorkspaceOverview,
} from "@/lib/api/overview";
import { OnboardingTour } from "@/components/onboarding-tour";
import { SectionHeader } from "@/components/editorial";
import { cn } from "@/lib/utils";

/**
 * Workspace dashboard (S-09 of UI_REDESIGN_V2.md). The first
 * screen returning users see.
 *
 * Editorial-warm layout per BRAND_IDENTITY_V1.md — flush-left
 * masthead, generous negative space, staggered card reveals.
 */
export function DashboardRoute() {
  const navigate = useNavigate();
  const session = useSession();
  const signout = useSignout();
  const me = useMe();
  const sub = useSubscription();
  const spokespeople = useSpokespeople();
  const workspaceId = me.data?.default_workspace?.id;
  const overview = useWorkspaceOverview(workspaceId);
  const overviewByName = new Map<string, OverviewSpokesperson>(
    overview.data?.spokespeople.map((s) => [s.id, s]) ?? [],
  );

  async function handleSignOut() {
    await signout.mutateAsync();
    navigate("/sign-in", { replace: true });
  }

  const workspaceName =
    me.data?.default_workspace?.name ??
    sub.data?.workspace_name ??
    session.data?.user?.email ??
    "Your workspace";

  // F8 — derive onboarding tour state from actual workspace
  // data. Banner self-hides once all three milestones land,
  // and the operator can dismiss it any time (persists in
  // localStorage).
  const tourLoading =
    overview.isLoading || me.isLoading || spokespeople.isLoading;
  const hasSpokesperson = (spokespeople.data?.length ?? 0) > 0;
  const hasKnowledge = (overview.data?.knowledge.doc_count ?? 0) > 0;
  const hasComposition = (overview.data?.compositions.total_count ?? 0) > 0;

  return (
    <div className="flex flex-col gap-12">
      <Masthead
        workspaceName={workspaceName}
        userEmail={session.data?.user?.email ?? me.data?.email}
        onSignOut={handleSignOut}
        signingOut={signout.isPending}
      />

      <OnboardingTour
        loading={tourLoading}
        hasSpokesperson={hasSpokesperson}
        hasKnowledge={hasKnowledge}
        hasComposition={hasComposition}
      />

      <PrimaryAction />

      <section
        className="reveal grid grid-cols-1 gap-6 md:grid-cols-[1fr,18rem]"
        style={{ "--reveal-delay": "0.04s" } as React.CSSProperties}
      >
        <SpokespeoplePanel
          loading={spokespeople.isLoading}
          error={spokespeople.error}
          data={spokespeople.data}
          overviewByName={overviewByName}
        />
        <UsagePanel
          loading={sub.isLoading}
          error={sub.error}
          data={sub.data}
        />
      </section>

      <section
        className="reveal grid grid-cols-1 gap-6 md:grid-cols-[1fr,18rem]"
        style={{ "--reveal-delay": "0.06s" } as React.CSSProperties}
      >
        <ActivityFeedPanel
          loading={overview.isLoading}
          error={overview.error}
          data={overview.data}
        />
        <KnowledgeCorpusPanel
          loading={overview.isLoading}
          error={overview.error}
          data={overview.data}
        />
      </section>

      <section
        className="reveal"
        style={{ "--reveal-delay": "0.08s" } as React.CSSProperties}
      >
        <CostPanel
          loading={overview.isLoading}
          error={overview.error}
          data={overview.data?.cost_breakdown}
        />
      </section>
    </div>
  );
}

// ---- Sections -------------------------------------------------------

function Masthead({
  workspaceName,
  userEmail,
  onSignOut,
  signingOut,
}: {
  workspaceName: string;
  userEmail: string | undefined;
  onSignOut: () => void;
  signingOut: boolean;
}) {
  return (
    <header
      className="reveal relative flex flex-col gap-4 pb-10"
      data-testid="dashboard-masthead"
    >
      {/* V3.4 — `§ 01 — Workspace` editorial label per BRAND
       * IDENTITY V3 contract rule 4. */}
      <SectionHeader number={1} title="Workspace" />
      <div className="flex flex-wrap items-end justify-between gap-6">
        <h1
          className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl text-cream"
          style={{ fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1' } as React.CSSProperties}
          data-testid="workspace-name"
        >
          {workspaceName}
        </h1>
        <div className="flex items-center gap-4">
          {/* The "Knowledge" link previously here retired into
              the NavRail (F2). Keeping the masthead lean. */}
          {userEmail && (
            <span className="hidden font-mono text-xs text-fog sm:inline">
              {userEmail}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={onSignOut}
            disabled={signingOut}
            data-testid="sign-out"
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>
      </div>
      {/* V3.4 — hairline-gold gradient replaces the generic
       * masthead border. Fades in/out at both ends. */}
      <div
        className="hairline-gold absolute inset-x-0 bottom-0 h-px"
        aria-hidden="true"
      />
    </header>
  );
}

function PrimaryAction() {
  return (
    <section
      className="reveal luxe-shadow flex flex-col gap-4 rounded-md border border-luxe bg-card p-8 md:flex-row md:items-center md:justify-between"
      style={{ "--reveal-delay": "0.02s" } as React.CSSProperties}
      data-testid="primary-action"
    >
      <div className="flex flex-col gap-2">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
          § 02 — Render queue
        </span>
        <p className="font-display text-3xl leading-tight tracking-tight text-cream md:text-4xl">
          Compose a render.
          <span className="italic text-mist"> Ground in workspace knowledge. </span>
          <span className="italic gold-text">Ship.</span>
        </p>
      </div>
      <Button asChild size="lg" className="self-start md:self-auto">
        <Link to="/recipes" data-testid="make-video-cta">
          Open recipe gallery →
        </Link>
      </Button>
    </section>
  );
}

function SpokespeoplePanel({
  loading,
  error,
  data,
  overviewByName,
}: {
  loading: boolean;
  error: unknown;
  data: Awaited<ReturnType<typeof import("@/lib/api/spokespeople").listSpokespeople>> | undefined;
  overviewByName: Map<string, OverviewSpokesperson>;
}) {
  return (
    <section className="flex flex-col gap-5">
      <PanelHeader
        title="Spokespeople"
        count={data?.length}
        action={
          <Link
            to="/spokespeople/new"
            className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
            data-testid="new-spokesperson-link"
          >
            <Plus className="h-3 w-3" />
            New
          </Link>
        }
      />
      {loading && <SpokespeopleSkeleton />}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {data && data.length === 0 && (
        <EmptyState
          headline="No spokespeople yet."
          body="A spokesperson is the on-camera identity your workspace renders against — portrait, voice, and grounding brief. Commission one to begin."
          testId="spokespeople-empty"
          action={
            <Link to="/spokespeople/new" data-testid="empty-create-cta">
              <Button size="lg">Commission a spokesperson →</Button>
            </Link>
          }
        />
      )}
      {data && data.length > 0 && (
        <div
          className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
          data-testid="spokespeople-grid"
        >
          {data.map((s, i) => {
            const o = overviewByName.get(s.id);
            return (
              <div key={s.id} className="flex flex-col gap-2">
                <SpokespersonCard
                  spokesperson={s}
                  revealDelay={`${0.04 + i * 0.06}s`}
                />
                {o && (o.composition_count > 0 || o.attached_docs_count > 0) && (
                  <div
                    className="flex gap-3 px-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
                    data-testid={`spokesperson-badges-${s.id}`}
                  >
                    {o.composition_count > 0 && (
                      <span>{o.composition_count} comp{o.composition_count === 1 ? "" : "s"}</span>
                    )}
                    {o.attached_docs_count > 0 && (
                      <span>{o.attached_docs_count} doc{o.attached_docs_count === 1 ? "" : "s"}</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function UsagePanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: unknown;
  data: Awaited<ReturnType<typeof import("@/lib/api/workspaces").getSubscription>> | undefined;
}) {
  if (loading) {
    return <UsageMeterSkeleton />;
  }
  if (error) {
    return <ErrorRow message={extractMessage(error)} />;
  }
  if (!data) return null;
  return (
    <UsageMeter
      used={data.videos_used}
      limit={data.videos_limit}
      tier={data.tier}
      status={data.status}
    />
  );
}

function ActivityFeedPanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: unknown;
  data: WorkspaceOverview | undefined;
}) {
  const recent = data?.compositions.recent ?? [];
  return (
    <section className="flex flex-col gap-5" data-testid="activity-feed">
      <PanelHeader
        title="Recent activity"
        count={data?.compositions.total_count}
        action={
          data && data.compositions.running_count > 0 ? (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
              <Loader2 className="h-3 w-3 animate-spin" />
              {data.compositions.running_count} running
            </span>
          ) : null
        }
      />
      {loading && <VideoListSkeleton />}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {data && recent.length === 0 && (
        <EmptyState
          headline="No renders yet."
          body="Compositions fired from any recipe surface in this workspace land here — status, cost, produced assets. Open the gallery to begin."
          testId="activity-empty"
          action={
            <Link to="/recipes">
              <Button size="lg">Open recipe gallery →</Button>
            </Link>
          }
        />
      )}
      {recent.length > 0 && (
        <ol className="flex flex-col" data-testid="activity-list">
          {recent.map((c) => (
            <ActivityRow key={c.id} composition={c} />
          ))}
        </ol>
      )}
    </section>
  );
}

function ActivityRow({ composition }: { composition: OverviewComposition }) {
  const cost = composition.cost_actual_micros / 1_000_000;
  return (
    <Link
      to={`/compositions/${composition.id}`}
      className="flex items-center gap-4 border-b py-3 transition-colors last:border-b-0 hover:bg-muted/40"
      data-testid="activity-row"
    >
      <StatusIcon status={composition.status} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-medium">{composition.name}</span>
          {composition.mock_mode && (
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-warning">
              mock
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <span>{composition.template_kind}</span>
          <span>{composition.spokesperson_name}</span>
        </div>
      </div>
      <div className="flex flex-col items-end gap-1 text-xs text-muted-foreground">
        <span className="font-mono">{composition.status}</span>
        {composition.cost_actual_micros > 0 && (
          <span className="font-mono">${cost.toFixed(4)}</span>
        )}
      </div>
    </Link>
  );
}

function StatusIcon({ status }: { status: OverviewComposition["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" />;
    case "running":
    case "draft":
    case "planning":
      return <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-accent" />;
    case "failed":
      return <XCircle className="h-4 w-4 flex-shrink-0 text-destructive" />;
    case "partial":
      return <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-warning" />;
    default:
      return <MinusCircle className="h-4 w-4 flex-shrink-0 text-muted-foreground" />;
  }
}

function KnowledgeCorpusPanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: unknown;
  data: WorkspaceOverview | undefined;
}) {
  if (loading) {
    return (
      <div className="h-48 animate-pulse rounded-md border bg-card" />
    );
  }
  if (error) {
    return <ErrorRow message={extractMessage(error)} />;
  }
  if (!data) return null;
  const k = data.knowledge;
  const nonZeroSources = Object.entries(k.source_mix).filter(([_, n]) => n > 0);
  return (
    <section
      className="flex flex-col gap-4 rounded-md border bg-card p-5 shadow-paper"
      data-testid="knowledge-corpus"
    >
      <div className="flex items-baseline justify-between border-b pb-2">
        <div className="flex items-center gap-2">
          <Library className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-base tracking-tight">Knowledge</h2>
        </div>
        <Link
          to="/workspace/knowledge"
          className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          data-testid="knowledge-corpus-link"
        >
          View all
        </Link>
      </div>
      <div className="flex items-baseline gap-4">
        <div className="flex flex-col">
          <span
            className="font-display text-3xl leading-none tracking-tight"
            data-testid="knowledge-doc-count"
          >
            {k.doc_count}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            doc{k.doc_count === 1 ? "" : "s"}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="font-display text-3xl leading-none tracking-tight">
            {k.chunk_count}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            chunks
          </span>
        </div>
      </div>
      {nonZeroSources.length > 0 && (
        <ul className="flex flex-col gap-1 text-xs">
          {nonZeroSources.map(([src, n]) => (
            <li
              key={src}
              className="flex items-baseline justify-between font-mono uppercase tracking-[0.22em] text-muted-foreground"
            >
              <span>{src}</span>
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}
      {k.most_recent && (
        <div className="border-t pt-2 text-xs">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Most recent
          </p>
          <Link
            to={`/workspace/knowledge/${k.most_recent.id}`}
            className="mt-1 line-clamp-2 hover:underline"
          >
            {k.most_recent.title}
          </Link>
        </div>
      )}
      {k.doc_count === 0 && (
        <p className="text-xs text-muted-foreground">
          No docs yet. Add some from the Knowledge tab so renders can draw on them.
        </p>
      )}
    </section>
  );
}

// ---- Atoms ---------------------------------------------------------

function PanelHeader({
  title,
  count,
  action,
}: {
  title: string;
  count: number | undefined;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-luxe pb-3">
      <div className="flex items-baseline gap-3">
        <h2 className="font-display text-xl tracking-tight text-cream">
          {title}
        </h2>
        {typeof count === "number" && (
          <span className="font-mono text-xs text-gold/70">{count}</span>
        )}
      </div>
      {action}
    </div>
  );
}

function EmptyState({
  headline,
  body,
  testId,
  action,
}: {
  headline: string;
  body: string;
  testId?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="reveal flex flex-col items-center gap-4 rounded-md border border-dashed border-luxe bg-card/40 p-10 text-center"
      data-testid={testId}
    >
      <p className="font-display text-xl italic tracking-tight text-cream">{headline}</p>
      <p className="mx-auto max-w-md text-sm text-mist">{body}</p>
      {action}
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
      {message}
    </div>
  );
}

function SpokespeopleSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex h-72 flex-col gap-4 rounded-md border bg-card p-6 shadow-paper",
          )}
        >
          <div className="aspect-square w-full rounded bg-muted" />
          <div className="h-4 w-2/3 rounded bg-muted" />
          <div className="h-3 w-full rounded bg-muted/70" />
          <div className="h-3 w-1/2 rounded bg-muted/70" />
        </div>
      ))}
    </div>
  );
}

function UsageMeterSkeleton() {
  return (
    <div className="flex h-40 flex-col gap-4 rounded-md border bg-card p-6 shadow-paper">
      <div className="h-3 w-1/3 rounded bg-muted" />
      <div className="h-8 w-1/2 rounded bg-muted" />
      <div className="h-px w-full bg-border" />
    </div>
  );
}

function VideoListSkeleton() {
  return (
    <div className="flex flex-col">
      {Array.from({ length: 3 }).map((_, i) => (
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

function extractMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Something went wrong fetching workspace data.";
}
