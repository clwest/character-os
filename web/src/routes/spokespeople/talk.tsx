/**
 * Realtime "Talk to spokesperson" route — R8.0 (SESSION 153).
 *
 * Minimum viable demo of the realtime arc. Lifecycle:
 *
 *    idle → creating → ready → live → ended
 *      ↑                ↓ (failure path)
 *      └─────────── error
 *
 * Operator clicks Start → broker creates the session (R3)
 * with the composed knowledge document (R4) + memory
 * projection (R6) → SPA mounts `<AvatarCall>` from the
 * Runway SDK with the issued ``(sessionId, sessionKey)``
 * pair → live audio session → operator clicks End → broker
 * fires R5's transcript capture.
 *
 * Mock-mode UX (when ``mock_mode=true`` on the session):
 * skip the SDK mount entirely. Show a "Demo mode" pill and
 * a stub panel that walks the operator through the same
 * lifecycle without a real WebRTC connection. Tests run
 * against this branch.
 *
 * R8.1 adds the tool-approval modal + cost forecasting UI.
 * R8.2 adds the live cost ticker + error paths +
 * rejection narration.
 */
import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { AvatarCall } from "@runwayml/avatars-react";
import { ArrowLeft, Loader2, Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSpokesperson } from "@/lib/api/spokespeople";
import {
  useCreateRealtimeSession,
  useEndRealtimeSession,
  useRealtimeSession,
  type RealtimeSession,
} from "@/lib/api/realtime";
import { ApiError } from "@/lib/api/client";

type Lifecycle =
  | { kind: "idle" }
  | { kind: "creating" }
  | { kind: "ready"; session: RealtimeSession; sessionKey: string }
  | { kind: "ended"; session: RealtimeSession }
  | { kind: "error"; message: string };

export function TalkRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const sp = useSpokesperson(id);
  const [lifecycle, setLifecycle] = useState<Lifecycle>({ kind: "idle" });
  const createSession = useCreateRealtimeSession();
  const endSession = useEndRealtimeSession();

  // Poll once the session is mid-creation so the UI advances
  // from CREATING → READY without operator action.
  const sessionId = lifecycle.kind === "ready" ? lifecycle.session.id : undefined;
  const polled = useRealtimeSession(sessionId);

  // Sync polled status changes into local lifecycle. The
  // poll hook handles its own refetch interval; this hook
  // mirrors terminal state changes back into lifecycle.
  useEffect(() => {
    if (lifecycle.kind !== "ready" || !polled.data) return;
    if (polled.data.status === "ended" || polled.data.status === "failed") {
      setLifecycle({ kind: "ended", session: polled.data });
    } else if (polled.data.status === "ready") {
      // Keep the existing key — only the status changed.
      setLifecycle((prev) =>
        prev.kind === "ready"
          ? { ...prev, session: polled.data! }
          : prev,
      );
    }
  }, [polled.data, lifecycle.kind]);

  async function handleStart() {
    if (!id) return;
    setLifecycle({ kind: "creating" });
    try {
      const session = await createSession.mutateAsync({
        spokesperson: id,
      });
      setLifecycle({
        kind: "ready",
        session,
        sessionKey: session.provider_session_key,
      });
    } catch (err) {
      setLifecycle({
        kind: "error",
        message: extractMessage(err),
      });
    }
  }

  async function handleEnd() {
    if (lifecycle.kind !== "ready") return;
    const sid = lifecycle.session.id;
    try {
      const ended = await endSession.mutateAsync(sid);
      setLifecycle({ kind: "ended", session: ended });
    } catch (err) {
      setLifecycle({
        kind: "error",
        message: extractMessage(err),
      });
    }
  }

  if (sp.isLoading) return <TalkSkeleton />;
  if (sp.isError || !sp.data) {
    return (
      <TalkError
        message={
          sp.error instanceof Error ? sp.error.message : "Spokesperson not found."
        }
        backHref={id ? `/spokespeople/${id}` : "/dashboard"}
      />
    );
  }

  const spokesperson = sp.data;

  return (
    <div
      className="flex flex-col gap-8 py-6"
      data-testid="talk-route"
      data-lifecycle={lifecycle.kind}
    >
      <BackLink href={`/spokespeople/${spokesperson.id}`} />

      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Talk to {spokesperson.name}
        </h1>
        <p className="text-sm text-muted-foreground">
          Live two-way conversation grounded in your workspace knowledge.
          {spokesperson.business_brief && (
            <>
              {" "}
              Brief: <span className="italic">{spokesperson.business_brief}</span>
            </>
          )}
        </p>
      </header>

      {lifecycle.kind === "idle" && (
        <IdlePanel
          onStart={handleStart}
          starting={createSession.isPending}
          spokespersonName={spokesperson.name}
        />
      )}

      {lifecycle.kind === "creating" && <CreatingPanel />}

      {lifecycle.kind === "ready" && (
        <LivePanel
          session={lifecycle.session}
          sessionKey={lifecycle.sessionKey}
          spokespersonName={spokesperson.name}
          avatarId={spokesperson.runway_avatar_id ?? ""}
          onEnd={handleEnd}
          ending={endSession.isPending}
        />
      )}

      {lifecycle.kind === "ended" && (
        <EndedPanel
          session={lifecycle.session}
          onStartAnother={() => setLifecycle({ kind: "idle" })}
          onBackToDetail={() =>
            navigate(`/spokespeople/${spokesperson.id}`)
          }
        />
      )}

      {lifecycle.kind === "error" && (
        <ErrorPanel
          message={lifecycle.message}
          onRetry={() => setLifecycle({ kind: "idle" })}
        />
      )}
    </div>
  );
}

// ---- Lifecycle panels --------------------------------------------

function IdlePanel({
  onStart,
  starting,
  spokespersonName,
}: {
  onStart: () => void;
  starting: boolean;
  spokespersonName: string;
}) {
  return (
    <section
      className="rounded-lg border bg-card p-6"
      data-testid="talk-idle"
    >
      <div className="flex flex-col gap-4">
        <p className="text-sm">
          When you click Start, {spokespersonName} will pull in
          your attached workspace knowledge and any prior
          conversations you've had with them, then open a
          live audio session.
        </p>
        <p className="text-xs text-muted-foreground">
          Sessions last up to 5 minutes (Runway's per-session
          cap). You can end early or reconnect afterward.
        </p>
        <div>
          <Button
            onClick={onStart}
            disabled={starting}
            data-testid="talk-start"
            size="lg"
          >
            {starting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting…
              </>
            ) : (
              <>
                <Mic className="mr-2 h-4 w-4" />
                Start session
              </>
            )}
          </Button>
        </div>
      </div>
    </section>
  );
}

function CreatingPanel() {
  return (
    <section
      className="rounded-lg border bg-card p-6"
      data-testid="talk-creating"
    >
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Composing the document + connecting to Runway…
        </p>
      </div>
    </section>
  );
}

function LivePanel({
  session,
  sessionKey,
  spokespersonName,
  avatarId,
  onEnd,
  ending,
}: {
  session: RealtimeSession;
  sessionKey: string;
  spokespersonName: string;
  avatarId: string;
  onEnd: () => void;
  ending: boolean;
}) {
  return (
    <section
      className="flex flex-col gap-4"
      data-testid="talk-live"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LiveIndicator mock={session.mock_mode} />
          <p className="text-sm">
            Live with{" "}
            <span className="font-medium">{spokespersonName}</span>
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={onEnd}
          disabled={ending}
          data-testid="talk-end"
        >
          {ending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Ending…
            </>
          ) : (
            <>
              <MicOff className="mr-2 h-4 w-4" />
              End session
            </>
          )}
        </Button>
      </div>

      {session.mock_mode ? (
        <MockSessionPanel session={session} />
      ) : (
        <AvatarCall
          avatarId={avatarId}
          sessionId={session.provider_session_id}
          sessionKey={sessionKey}
          audio
          data-testid="avatar-call"
        />
      )}

      <SessionMeta session={session} />
    </section>
  );
}

function LiveIndicator({ mock }: { mock: boolean }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium" +
        (mock
          ? " bg-yellow-100 text-yellow-800"
          : " bg-emerald-100 text-emerald-800")
      }
      data-testid={mock ? "live-pill-mock" : "live-pill-real"}
    >
      <span
        className={
          "h-2 w-2 rounded-full" +
          (mock ? " bg-yellow-500" : " animate-pulse bg-emerald-500")
        }
      />
      {mock ? "Live (demo mode)" : "Live"}
    </span>
  );
}

function MockSessionPanel({ session }: { session: RealtimeSession }) {
  return (
    <div
      className="rounded-lg border-2 border-dashed bg-muted/50 p-6 text-center"
      data-testid="mock-session-panel"
    >
      <p className="text-sm font-medium">Demo mode</p>
      <p className="mt-2 text-xs text-muted-foreground">
        Mock-mode session — no real WebRTC handshake. The
        backend composed the document + memory loop end-to-
        end; click End to fire the transcript capture flow.
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <dt className="text-muted-foreground">Provider session</dt>
        <dd className="font-mono">{session.provider_session_id || "—"}</dd>
        <dt className="text-muted-foreground">Document</dt>
        <dd className="font-mono">{session.provider_document_id || "—"}</dd>
      </dl>
    </div>
  );
}

function SessionMeta({ session }: { session: RealtimeSession }) {
  return (
    <dl
      className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-4"
      data-testid="talk-session-meta"
    >
      <dt>Knowledge chunks</dt>
      <dd className="font-mono text-foreground">
        {session.knowledge_chunk_ids.length}
      </dd>
      <dt>Status</dt>
      <dd className="font-mono text-foreground">{session.status}</dd>
    </dl>
  );
}

function EndedPanel({
  session,
  onStartAnother,
  onBackToDetail,
}: {
  session: RealtimeSession;
  onStartAnother: () => void;
  onBackToDetail: () => void;
}) {
  return (
    <section
      className="rounded-lg border bg-card p-6"
      data-testid="talk-ended"
    >
      <h2 className="text-base font-semibold">Session ended</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Duration:{" "}
        <span className="font-mono text-foreground">
          {session.duration_seconds}s
        </span>
        . The transcript is being captured in the background — it
        will appear in this spokesperson's recent conversations
        shortly.
      </p>
      <div className="mt-4 flex gap-2">
        <Button onClick={onStartAnother} data-testid="talk-restart">
          Start another session
        </Button>
        <Button
          variant="secondary"
          onClick={onBackToDetail}
          data-testid="talk-back"
        >
          Back to spokesperson
        </Button>
      </div>
    </section>
  );
}

function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <section
      className="rounded-lg border border-destructive bg-destructive/5 p-6"
      data-testid="talk-error"
    >
      <h2 className="text-base font-semibold text-destructive">
        Couldn't start the session
      </h2>
      <p className="mt-2 text-sm">{message}</p>
      <div className="mt-4">
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      </div>
    </section>
  );
}

// ---- Boilerplate -------------------------------------------------

function BackLink({ href }: { href: string }) {
  return (
    <Link
      to={href}
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to spokesperson
    </Link>
  );
}

function TalkSkeleton() {
  return (
    <div className="flex flex-col gap-6 py-6" data-testid="talk-skeleton">
      <div className="h-4 w-24 rounded bg-muted" />
      <div className="h-8 w-64 rounded bg-muted" />
      <div className="h-32 rounded-lg border bg-card" />
    </div>
  );
}

function TalkError({
  message,
  backHref,
}: {
  message: string;
  backHref: string;
}) {
  return (
    <div className="flex flex-col gap-4 py-10" data-testid="talk-fatal-error">
      <Link
        to={backHref}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>
      <p className="text-sm text-destructive">{message}</p>
    </div>
  );
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const body = err.body;
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
    return `Request failed (${err.status}).`;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}
