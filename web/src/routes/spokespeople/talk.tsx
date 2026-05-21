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
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { AvatarCall, AvatarVideo } from "@runwayml/avatars-react";
import { ArrowLeft, Headphones, Loader2, Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSpokesperson } from "@/lib/api/spokespeople";
import {
  useCreateRealtimeSession,
  useEndRealtimeSession,
  useInvokeTool,
  useRealtimeCostEstimate,
  useRealtimeSession,
  type DispatchResult,
  type RealtimeSession,
} from "@/lib/api/realtime";
import { ApiError } from "@/lib/api/client";
import {
  ToolApprovalModal,
  type PendingInvocation,
} from "@/components/tool-approval-modal";
import { AvatarSessionInner } from "@/components/avatar-session-inner";
import { CostTicker } from "@/components/cost-ticker";

// Fallback constants used when the cost-estimate hook
// (R9 /api/realtime_sessions/cost_estimate/) hasn't
// responded yet OR returns an error. Conservative
// placeholders that match the backend's
// DEFAULT_RATE_MICROS_PER_MINUTE +
// PROVIDER_MAX_SESSION_MINUTES.
const FALLBACK_COST_PER_MINUTE_MICROS = 80_000; // ~$0.08/min
const FALLBACK_MAX_SESSION_MINUTES = 5;

type Lifecycle =
  | { kind: "idle" }
  | { kind: "creating" }
  | { kind: "ready"; session: RealtimeSession; sessionKey: string }
  // `ending` unmounts <AvatarCall> so the SDK can run its WebRTC
  // cleanup BEFORE we call the broker. Runway interprets DELETE
  // arriving while the peer is still active as "operator
  // cancelled" → conversation marked failed → no transcript
  // persists. Hackathon parity (their `onEnd` callback fires
  // after SDK cleanup, then triggers backend close).
  | { kind: "ending"; session: RealtimeSession }
  | { kind: "ended"; session: RealtimeSession }
  | { kind: "error"; message: string };

export function TalkRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const sp = useSpokesperson(id);
  const [lifecycle, setLifecycle] = useState<Lifecycle>({ kind: "idle" });
  const [pendingInvocation, setPendingInvocation] =
    useState<PendingInvocation | null>(null);
  const [lastToolResult, setLastToolResult] =
    useState<DispatchResult | null>(null);
  const createSession = useCreateRealtimeSession();
  const endSession = useEndRealtimeSession();
  const invokeTool = useInvokeTool();
  // R9 — backend-fetched cost forecast. Fallback to the
  // hardcoded constants when the hook hasn't resolved or
  // errors (don't block the UX on a transient billing
  // endpoint failure).
  const costEstimate = useRealtimeCostEstimate({
    workspaceId: sp.data?.workspace,
  });
  const costPerMinuteMicros =
    costEstimate.data?.cost_per_minute_micros ??
    FALLBACK_COST_PER_MINUTE_MICROS;
  const maxSessionMinutes =
    costEstimate.data?.max_session_minutes ??
    FALLBACK_MAX_SESSION_MINUTES;
  const minutesRemaining =
    costEstimate.data?.monthly_minutes_remaining ?? null;
  const minutesLimit = costEstimate.data?.monthly_minutes_limit ?? null;

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

  // The SDK's end() function — assigned by AvatarSessionInner
  // while a real session is mounted. Calling this publishes an
  // `END_CALL` data-channel message that Runway needs to flip
  // the conversation to `ended` (and produce a transcript)
  // before LiveKit disconnects. Without it Runway marks the
  // conversation `failed` with no transcript.
  const sdkEndRef = useRef<(() => Promise<void>) | null>(null);

  function handleEnd() {
    if (lifecycle.kind !== "ready") return;
    // Mock sessions skip the intermediate `ending` state — there's
    // no SDK / WebRTC peer to drain, so the broker call can fire
    // immediately and the test stays deterministic.
    if (lifecycle.session.mock_mode) {
      void finalizeEnd(lifecycle.session);
      return;
    }
    // Real sessions: fire the SDK's END_CALL message + LiveKit
    // disconnect FIRST. The SDK's onEnd callback (wired below)
    // resolves the broker call. Transitioning to `ending` shows
    // the operator a "Closing…" panel during the handshake.
    setLifecycle({ kind: "ending", session: lifecycle.session });
    const sdkEnd = sdkEndRef.current;
    if (sdkEnd) {
      void sdkEnd().catch((err) => {
        // SDK end can fail (already disconnected, etc.) — that's
        // fine, the defensive timer below still fires finalizeEnd.
        // eslint-disable-next-line no-console
        console.warn("SDK end() failed; defensive timer will finalize", err);
      });
    }
  }

  async function finalizeEnd(session: RealtimeSession) {
    try {
      const ended = await endSession.mutateAsync(session.id);
      setLifecycle({ kind: "ended", session: ended });
    } catch (err) {
      setLifecycle({
        kind: "error",
        message: extractMessage(err),
      });
    }
  }

  // When entering `ending`, the SDK's onEnd should fire after
  // its cleanup. If it doesn't (some SDK paths skip the callback
  // when the unmount is operator-initiated), this defensive
  // 2.5s timer calls finalizeEnd anyway. finalizeEnd is
  // idempotent — the broker tolerates double-end calls.
  useEffect(() => {
    if (lifecycle.kind !== "ending") return;
    const session = lifecycle.session;
    const timer = setTimeout(() => finalizeEnd(session), 2500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lifecycle.kind]);

  // R8.1 — operator-triggered tool invocation. In real-mode
  // (R8.2) this will be wired to the SDK's `useClientEvent`
  // hook inside <AvatarCall> so the avatar's LLM can fire
  // tools natively. R8.1 ships the dispatch + approval
  // surface; the mock-mode debug button exercises it
  // end-to-end without a real avatar.
  async function handleInvokeTool(
    toolName: string,
    args: Record<string, unknown>,
  ) {
    if (lifecycle.kind !== "ready") return;
    setLastToolResult(null);
    try {
      const result = await invokeTool.mutateAsync({
        sessionId: lifecycle.session.id,
        tool_name: toolName,
        args,
      });
      if (result.state === "awaiting_approval") {
        setPendingInvocation({
          invocation_id: result.invocation_id,
          tool_name: result.tool_name,
          cost_micros: result.cost_micros,
          reason: result.reason ?? "",
          args,
        });
      } else {
        setLastToolResult(result);
      }
    } catch (err) {
      setLastToolResult({
        state: "failed",
        invocation_id: "",
        tool_name: toolName,
        cost_micros: 0,
        error_message: extractMessage(err),
      });
    }
  }

  function handleApprovalResolved(result: DispatchResult) {
    setPendingInvocation(null);
    setLastToolResult(result);
  }

  function handleApprovalDismiss() {
    setPendingInvocation(null);
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
        <p className="text-sm text-fog">
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
          voiceId={spokesperson.voice_id}
          costPerMinuteMicros={costPerMinuteMicros}
          maxSessionMinutes={maxSessionMinutes}
          minutesRemaining={minutesRemaining}
          minutesLimit={minutesLimit}
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
          onInvokeTool={handleInvokeTool}
          invokingTool={invokeTool.isPending}
          lastToolResult={lastToolResult}
          costPerMinuteMicros={costPerMinuteMicros}
          maxSessionMinutes={maxSessionMinutes}
          onSdkError={(err) =>
            setLifecycle({
              kind: "error",
              message: extractMessage(err),
            })
          }
          onSdkEnd={() => {
            // Fires after the SDK's END_CALL + LiveKit
            // disconnect resolve. Works for both
            // operator-initiated end (handleEnd called
            // sdkEnd) and provider-initiated end (Runway
            // closed the room because of expiry / fault).
            void finalizeEnd(lifecycle.session);
          }}
          sdkEndRef={sdkEndRef}
        />
      )}

      {lifecycle.kind === "ending" && <EndingPanel />}

      {pendingInvocation && (
        <ToolApprovalModal
          invocation={pendingInvocation}
          spokespersonName={spokesperson.name}
          onResolved={handleApprovalResolved}
          onDismiss={handleApprovalDismiss}
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
  voiceId,
  costPerMinuteMicros,
  maxSessionMinutes,
  minutesRemaining,
  minutesLimit,
}: {
  onStart: () => void;
  starting: boolean;
  spokespersonName: string;
  voiceId: string;
  costPerMinuteMicros: number;
  maxSessionMinutes: number;
  minutesRemaining: number | null;
  minutesLimit: number | null;
}) {
  const fullSessionCostMicros = costPerMinuteMicros * maxSessionMinutes;
  const fullSessionDollars = (fullSessionCostMicros / 1_000_000).toFixed(2);
  // R9 — operator-facing minutes-remaining hint. Only
  // shows when the tier has a budget (Agency is null →
  // skip the hint).
  const showMinutesHint =
    minutesRemaining !== null && minutesLimit !== null;
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
        <p className="text-xs text-fog">
          Sessions last up to {maxSessionMinutes} minutes
          (Runway's per-session cap). You can end early or
          reconnect afterward.
        </p>
        <div
          className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-foreground"
          data-testid="talk-headphones-tip"
        >
          <Headphones className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>Wear headphones.</strong> Speaker audio leaks
            back into your microphone otherwise — {spokespersonName} hears
            themselves and can derail mid-thought. Also make sure
            your browser has microphone permission granted before
            you click Start.
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
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
          <span
            className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-fog"
            data-testid="cost-forecast"
            title="Estimated session cost at the provider's per-minute rate."
          >
            <span>~${fullSessionDollars}</span>
            <span className="text-[10px] uppercase tracking-wide">
              for {maxSessionMinutes} min
            </span>
          </span>
          {showMinutesHint && (
            <span
              className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-fog"
              data-testid="minutes-remaining"
              title="Your remaining realtime minutes this month."
            >
              <span>{minutesRemaining}</span>
              <span className="text-[10px] uppercase tracking-wide">
                of {minutesLimit} min left this month
              </span>
            </span>
          )}
          {voiceId && (
            <span
              className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-fog"
              data-testid="talk-voice-pill"
              title={
                `${spokespersonName} will speak with the '${voiceId}' voice. ` +
                `Change it from the spokesperson edit modal.`
              }
            >
              <span className="text-[10px] uppercase tracking-wide">
                Voice
              </span>
              <span className="font-mono">{voiceId}</span>
            </span>
          )}
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
        <Loader2 className="h-5 w-5 animate-spin text-fog" />
        <p className="text-sm text-fog">
          Composing the document + connecting to Runway…
        </p>
      </div>
    </section>
  );
}

function EndingPanel() {
  return (
    <section
      className="rounded-lg border bg-card p-6"
      data-testid="talk-ending"
    >
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-fog" />
        <p className="text-sm text-fog">
          Closing the session and capturing the transcript…
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
  onInvokeTool,
  invokingTool,
  lastToolResult,
  costPerMinuteMicros,
  maxSessionMinutes,
  onSdkError,
  onSdkEnd,
  sdkEndRef,
}: {
  session: RealtimeSession;
  sessionKey: string;
  spokespersonName: string;
  avatarId: string;
  onEnd: () => void;
  ending: boolean;
  onInvokeTool: (toolName: string, args: Record<string, unknown>) => void;
  invokingTool: boolean;
  lastToolResult: DispatchResult | null;
  costPerMinuteMicros: number;
  maxSessionMinutes: number;
  onSdkError: (err: Error) => void;
  onSdkEnd: () => void;
  sdkEndRef: React.MutableRefObject<(() => Promise<void>) | null>;
}) {
  // Counting basis for the cost ticker. ``ready_at`` lands
  // once the broker's state machine flips READY; in mock
  // mode it's set in the create response. Fall back to
  // ``started_at`` then ``created_at`` so the ticker
  // always has SOMETHING to count from.
  const tickerStart =
    session.ready_at ?? session.started_at ?? session.created_at;

  return (
    <section
      className="flex flex-col gap-4"
      data-testid="talk-live"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <LiveIndicator mock={session.mock_mode} />
          <p className="text-sm">
            Live with{" "}
            <span className="font-medium">{spokespersonName}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <CostTicker
            startedAt={tickerStart}
            costPerMinuteMicros={costPerMinuteMicros}
            maxMinutes={maxSessionMinutes}
            mockMode={session.mock_mode}
          />
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
      </div>

      {session.mock_mode ? (
        <MockSessionPanel
          session={session}
          onInvokeTool={onInvokeTool}
          invokingTool={invokingTool}
        />
      ) : (
        <AvatarCall
          avatarId={avatarId}
          sessionId={session.provider_session_id}
          sessionKey={sessionKey}
          audio
          video={false}
          onEnd={onSdkEnd}
          onError={onSdkError}
          className="w-full max-w-3xl self-center overflow-hidden rounded-xl border border-luxe bg-card shadow-md"
          data-testid="avatar-call"
        >
          {/* `video` is the LOCAL-media flag (operator's
              webcam). The avatar's video output renders via
              <AvatarVideo /> regardless. With `video={true}`
              the SDK requests webcam access; if the operator
              has no webcam or denies the prompt the WebRTC
              handshake negotiated tracks mismatch and Runway
              marks the session FAILED with no transcript
              (verified on two failed sessions May 18 2026).
              Hackathon parity — set false, render avatar via
              the dedicated child below. */}
          <AvatarVideo className="aspect-video w-full" />
          {/* R8.2 — inside-AvatarCall hook consumer.
              Receives tool-invocation events from the
              avatar's data channel + dispatches via the
              parent's onInvokeTool callback. */}
          <AvatarSessionInner
            onToolInvocation={onInvokeTool}
            endRef={sdkEndRef}
          />
        </AvatarCall>
      )}

      {lastToolResult && (
        <ToolResultPanel result={lastToolResult} />
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
          ? " bg-muted text-fog"
          : " bg-success/15 text-success")
      }
      data-testid={mock ? "live-pill-mock" : "live-pill-real"}
    >
      <span
        className={
          "h-2 w-2 rounded-full" +
          (mock ? " bg-muted-foreground" : " animate-pulse bg-success")
        }
      />
      {mock ? "Live (demo mode)" : "Live"}
    </span>
  );
}

function MockSessionPanel({
  session,
  onInvokeTool,
  invokingTool,
}: {
  session: RealtimeSession;
  onInvokeTool: (toolName: string, args: Record<string, unknown>) => void;
  invokingTool: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-4 rounded-lg border-2 border-dashed bg-muted/50 p-6"
      data-testid="mock-session-panel"
    >
      <div className="text-center">
        <p className="text-sm font-medium">Demo mode</p>
        <p className="mt-2 text-xs text-fog">
          Mock-mode session — no real WebRTC handshake. The
          backend composed the document + memory loop
          end-to-end; click End to fire the transcript
          capture flow.
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <dt className="text-fog">Provider session</dt>
        <dd className="font-mono">{session.provider_session_id || "—"}</dd>
        <dt className="text-fog">Document</dt>
        <dd className="font-mono">{session.provider_document_id || "—"}</dd>
      </dl>

      {/* R8.1 — operator-triggered tool dispatch. R8.2 wires
          these to the SDK's `useClientEvent` so the avatar
          can fire them natively; for now the demo path
          exercises the dispatch → modal → approve/reject
          flow end-to-end. */}
      <div
        className="flex flex-col gap-2 border-t pt-4"
        data-testid="mock-tool-buttons"
      >
        <p className="text-xs font-medium uppercase tracking-wider text-fog">
          Test tool dispatch
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={invokingTool}
            onClick={() =>
              onInvokeTool("render_video", {
                script: "Pitch the spring sale to my audience.",
              })
            }
            data-testid="mock-fire-render-video"
          >
            Fire <span className="ml-1 font-mono text-xs">render_video</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={invokingTool}
            onClick={() => onInvokeTool("show_videos_tab", {})}
            data-testid="mock-fire-show-videos-tab"
          >
            Fire <span className="ml-1 font-mono text-xs">show_videos_tab</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

function ToolResultPanel({ result }: { result: DispatchResult }) {
  const ok = result.state === "succeeded";
  const queued = result.state === "queued";
  const failed = result.state === "failed";
  const rejected = result.state === "rejected";
  const resultObj = isResultObject(result.result) ? result.result : null;
  const isRecallSessions =
    ok &&
    result.tool_name === "recall_recent_conversations" &&
    resultObj !== null &&
    Array.isArray(resultObj.sessions);
  const isRecallKnowledge =
    ok &&
    result.tool_name === "recall_knowledge" &&
    resultObj !== null &&
    Array.isArray(resultObj.matches);
  return (
    <div
      className={
        "flex flex-col gap-2 rounded border px-4 py-3 text-xs text-foreground " +
        (ok
          ? "border-success/40 bg-success/10"
          : queued
            ? "border-accent/40 bg-accent/10"
            : rejected
              ? "border-warning/40 bg-warning/10"
              : failed
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : "border-border bg-muted")
      }
      data-testid="tool-result-panel"
      data-state={result.state}
    >
      <div className="flex items-baseline gap-2">
        <span className="font-mono font-semibold">{result.tool_name}</span>
        <span className="text-[10px] uppercase tracking-wide">
          {result.state}
        </span>
      </div>
      {result.error_message && <p>{result.error_message}</p>}
      {result.reason && <p className="italic">{result.reason}</p>}
      {isRecallSessions && (
        <RecallSessionsList
          sessions={resultObj.sessions as RecallSession[]}
        />
      )}
      {isRecallKnowledge && (
        <RecallKnowledgeList
          query={typeof resultObj.query === "string" ? resultObj.query : ""}
          matches={resultObj.matches as KnowledgeMatch[]}
        />
      )}
      {ok && resultObj !== null && !isRecallSessions && !isRecallKnowledge && (
        <p className="font-mono text-foreground/80">
          {summariseResultObject(resultObj)}
        </p>
      )}
    </div>
  );
}

interface RecallSession {
  session_id: string;
  ended_at: string | null;
  duration_seconds?: number | null;
  preview: string;
}

function RecallSessionsList({ sessions }: { sessions: RecallSession[] }) {
  if (sessions.length === 0) {
    return (
      <p className="italic text-foreground/70">
        No prior conversations to recall yet.
      </p>
    );
  }
  return (
    <ul
      className="flex flex-col gap-2"
      data-testid="recall-sessions-list"
    >
      {sessions.map((s) => (
        <li
          key={s.session_id}
          className="rounded border border-luxe bg-card/80 px-3 py-2"
        >
          <div className="flex items-baseline justify-between gap-2 text-[11px] uppercase tracking-wide text-foreground/60">
            <span>{formatRecallTimestamp(s.ended_at)}</span>
            {typeof s.duration_seconds === "number" && (
              <span>{Math.max(1, Math.round(s.duration_seconds))}s</span>
            )}
          </div>
          <p className="mt-1 whitespace-pre-wrap text-foreground/90">
            {s.preview}
          </p>
        </li>
      ))}
    </ul>
  );
}

interface KnowledgeMatch {
  chunk_id: string;
  document_title?: string | null;
  text: string;
}

function RecallKnowledgeList({
  query,
  matches,
}: {
  query: string;
  matches: KnowledgeMatch[];
}) {
  if (matches.length === 0) {
    return (
      <p className="italic text-foreground/70">
        No knowledge matches{query ? ` for "${query}"` : ""}.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2" data-testid="recall-knowledge-list">
      {query && (
        <p className="text-[11px] uppercase tracking-wide text-foreground/60">
          Query: <span className="normal-case italic">{query}</span>
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {matches.map((m) => (
          <li
            key={m.chunk_id}
            className="rounded border border-luxe bg-card/80 px-3 py-2"
          >
            {m.document_title && (
              <p className="text-[11px] font-medium uppercase tracking-wide text-foreground/60">
                {m.document_title}
              </p>
            )}
            <p className="mt-1 whitespace-pre-wrap text-foreground/90">
              {m.text}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatRecallTimestamp(iso: string | null): string {
  if (!iso) return "Earlier session";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isResultObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function summariseResultObject(obj: Record<string, unknown>): string {
  // Common ids the dispatcher might surface — show the most
  // useful one without overwhelming the panel.
  if (typeof obj.composition_id === "string") {
    return `composition: ${obj.composition_id}`;
  }
  if (typeof obj.asset_id === "string") {
    return `asset: ${obj.asset_id}`;
  }
  if (typeof obj.event === "string") {
    return `event: ${obj.event}`;
  }
  return "(succeeded)";
}

function SessionMeta({ session }: { session: RealtimeSession }) {
  return (
    <dl
      className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-fog sm:grid-cols-4"
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
      <p className="mt-2 text-sm text-fog">
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
      className="flex flex-col gap-4 rounded-lg border border-destructive bg-destructive/5 p-6"
      data-testid="talk-error"
    >
      <div>
        <h2 className="text-base font-semibold text-destructive">
          Couldn't keep the live session going
        </h2>
        <p className="mt-2 text-sm">{message}</p>
        <p className="mt-3 text-xs text-fog">
          Real-time sessions can fail to connect under
          restrictive network conditions (firewalls, VPNs)
          or when the device's microphone isn't accessible.
          You can retry below, or switch to a recorded
          video — same spokesperson, same knowledge, no
          WebRTC.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={onRetry} data-testid="talk-retry">
          Try again
        </Button>
        <Button asChild variant="outline" data-testid="talk-fallback">
          <Link to="/recipes">Make a recorded video instead</Link>
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
      className="inline-flex items-center gap-1 text-sm text-fog hover:text-foreground"
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
        className="inline-flex items-center gap-1 text-sm text-fog"
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
