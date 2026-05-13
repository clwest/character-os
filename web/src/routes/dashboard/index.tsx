import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useSession, useSignout } from "@/lib/auth/use-session";
import { useMe, useSubscription } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useVideos } from "@/lib/api/videos";
import { SpokespersonCard } from "@/components/spokesperson-card";
import { VideoRow } from "@/components/video-row";
import { UsageMeter } from "@/components/usage-meter";
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
  const videos = useVideos({ limit: 6 });

  async function handleSignOut() {
    await signout.mutateAsync();
    navigate("/sign-in", { replace: true });
  }

  const workspaceName =
    me.data?.default_workspace?.name ??
    sub.data?.workspace_name ??
    session.data?.user?.email ??
    "Your workspace";

  return (
    <div className="flex flex-col gap-12">
      <Masthead
        workspaceName={workspaceName}
        userEmail={session.data?.user?.email ?? me.data?.email}
        onSignOut={handleSignOut}
        signingOut={signout.isPending}
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
        />
        <UsagePanel
          loading={sub.isLoading}
          error={sub.error}
          data={sub.data}
        />
      </section>

      <RecentVideosPanel
        loading={videos.isLoading}
        error={videos.error}
        data={videos.data}
      />
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
      className="reveal flex flex-col gap-3 border-b border-border pb-8"
      data-testid="dashboard-masthead"
    >
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        Workspace
      </span>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <h1
          className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
          style={{ fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1' } as React.CSSProperties}
          data-testid="workspace-name"
        >
          {workspaceName}
        </h1>
        <div className="flex items-center gap-4">
          {userEmail && (
            <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
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
    </header>
  );
}

function PrimaryAction() {
  return (
    <section
      className="reveal flex flex-col gap-4 rounded-md border bg-card p-8 shadow-paper md:flex-row md:items-center md:justify-between"
      style={{ "--reveal-delay": "0.02s" } as React.CSSProperties}
      data-testid="primary-action"
    >
      <div className="flex flex-col gap-2">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Make today's video
        </span>
        <p className="font-display text-3xl leading-tight tracking-tight">
          Type your business.
          <span className="text-muted-foreground"> Click. </span>
          Get a video ad.
        </p>
      </div>
      <Button
        size="lg"
        disabled
        title="Coming in the next slice (S-12)"
        className="self-start md:self-auto"
      >
        Make a video
      </Button>
    </section>
  );
}

function SpokespeoplePanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: unknown;
  data: Awaited<ReturnType<typeof import("@/lib/api/spokespeople").listSpokespeople>> | undefined;
}) {
  return (
    <section className="flex flex-col gap-5">
      <PanelHeader title="Spokespeople" count={data?.length} />
      {loading && <SpokespeopleSkeleton />}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {data && data.length === 0 && (
        <EmptyState
          headline="No spokespeople yet"
          body="A spokesperson is the on-camera identity behind every video — a portrait, a voice, a one-paragraph business brief. You'll set up the first one in the next slice."
          testId="spokespeople-empty"
        />
      )}
      {data && data.length > 0 && (
        <div
          className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3"
          data-testid="spokespeople-grid"
        >
          {data.map((s, i) => (
            <SpokespersonCard
              key={s.id}
              spokesperson={s}
              revealDelay={`${0.04 + i * 0.06}s`}
            />
          ))}
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

function RecentVideosPanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: unknown;
  data: Awaited<ReturnType<typeof import("@/lib/api/videos").listVideos>> | undefined;
}) {
  return (
    <section className="flex flex-col gap-5">
      <PanelHeader title="Recent renders" count={data?.length} />
      {loading && <VideoListSkeleton />}
      {error ? <ErrorRow message={extractMessage(error)} /> : null}
      {data && data.length === 0 && (
        <EmptyState
          headline="No renders yet"
          body="Your videos will appear here once you've made one. Renders take about 60–120 seconds in real mode; the SPA polls the status automatically."
          testId="videos-empty"
        />
      )}
      {data && data.length > 0 && (
        <ol className="flex flex-col" data-testid="videos-list">
          {data.map((v, i) => (
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

function PanelHeader({ title, count }: { title: string; count: number | undefined }) {
  return (
    <div className="flex items-baseline justify-between border-b border-border/60 pb-3">
      <h2 className="font-display text-xl tracking-tight">{title}</h2>
      {typeof count === "number" && (
        <span className="font-mono text-xs text-muted-foreground">
          {count}
        </span>
      )}
    </div>
  );
}

function EmptyState({
  headline,
  body,
  testId,
}: {
  headline: string;
  body: string;
  testId?: string;
}) {
  return (
    <div
      className="reveal flex flex-col gap-2 rounded-md border border-dashed border-border bg-card/50 p-8 text-center"
      data-testid={testId}
    >
      <p className="font-display text-xl tracking-tight">{headline}</p>
      <p className="mx-auto max-w-md text-sm text-muted-foreground">{body}</p>
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
