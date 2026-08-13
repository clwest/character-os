/**
 * /workspace/tools — non-realtime bridge invocation UI (C5).
 *
 * First-customer surface for the three engine-bridge tools
 * (consult_engine / query_spider_data / agent_consult) without ever
 * starting a live WebRTC realtime session. C5.1 ships the route + form
 * + dispatch wiring; C5.2 polishes the result panel; C5.3 hardens the
 * tier gate; C5.4 dogfoods against real the sibling project.
 *
 * Scope: docs/design/BRIDGE_TOOLS_UI_V1.md §"SPA surface".
 *
 * Contract rules honored here (see scope doc §"Contract rules"):
 *   - Rule 2: never start a live realtime session. The DRAFT container
 *     is created via POST /api/realtime_sessions/ and NEVER followed up
 *     with a media-engine start_session call. Status stays DRAFT for
 *     the entire page lifecycle.
 *   - Rule 3: DRAFT sessions are page-scoped, not persistent. We hold
 *     the session id in local React state — a page reload creates a
 *     fresh DRAFT on next dispatch.
 *   - Rule 5: auto-create DRAFT session one-click. Operator never sees
 *     a "create session first" step.
 *   - Rule 7: the SAME `POST .../invoke_tool/` endpoint R7.0 uses.
 *     No non-realtime-dispatch flag, no divergent code path.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ChevronLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useMe, useSubscription } from "@/lib/api/workspaces";
import { useSpokespeople, type Spokesperson } from "@/lib/api/spokespeople";
import {
  useCreateRealtimeSession,
  useInvokeTool,
  type DispatchResult,
} from "@/lib/api/realtime";
import {
  BRIDGE_TOOLS,
  formatToolOptionLabel,
  type BridgeToolMeta,
} from "@/lib/api/tools";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/editorial";
import { BridgeResultPanel } from "@/components/bridge-result-panel";
import { BridgeUpgradeNudge } from "@/components/bridge-upgrade-nudge";

// ---- Page component ---------------------------------------------

export function WorkspaceToolsRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const subscription = useSubscription();
  const spokespeople = useSpokespeople();

  const workspaceId = me.data?.default_workspace?.id;
  const tier = subscription.data?.tier;

  // Filter to spokespeople in the active workspace only. `spokespeople.ts`
  // returns the full user-scoped list; the picker restricts to the
  // current workspace for consistency with /workspace/scripts.new.
  const workspaceSpokespeople = useMemo<Spokesperson[]>(
    () =>
      (spokespeople.data ?? []).filter(
        (s) => !workspaceId || s.workspace === workspaceId,
      ),
    [spokespeople.data, workspaceId],
  );

  const readyForForm =
    !me.isLoading &&
    !subscription.isLoading &&
    !spokespeople.isLoading;

  // Rule 8 (EB) tier gate. Starter workspaces see the placeholder — full
  // upgrade nudge lands in C5.3.
  const isStarter = tier === "starter";

  return (
    <div className="flex flex-col gap-10">
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <SectionHeader number={1} title="Tools" />
        <h1
          data-testid="tools-title"
          className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
        >
          Ask your{" "}
          <span className="italic gold-text">engine</span> directly.
        </h1>
        <p className="max-w-2xl text-base text-mist">
          Fire a bridge tool against your configured engine without starting a
          live conversation. Answers persist to your workspace asset library.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      {!readyForForm && (
        <p className="text-sm text-fog" data-testid="tools-loading">
          Loading…
        </p>
      )}

      {/*
       * Rule 8 (EB) tier gate — Starter workspaces never mount the form.
       * `resolve_engine_connection` on the backend returns None for
       * Starter, so a Starter dispatch would fail server-side anyway;
       * this branch is the operator-facing upsell surface for that
       * server-side reality (Q-eb-2 resolution: better upsell discovery).
       */}
      {readyForForm && isStarter && <BridgeUpgradeNudge />}

      {readyForForm && !isStarter && (
        <BridgeToolForm
          spokespeople={workspaceSpokespeople}
          tools={BRIDGE_TOOLS}
        />
      )}
    </div>
  );
}

// ---- Form -------------------------------------------------------

interface BridgeToolFormProps {
  spokespeople: Spokesperson[];
  tools: BridgeToolMeta[];
}

function BridgeToolForm({ spokespeople, tools }: BridgeToolFormProps) {
  const [toolName, setToolName] = useState<string>(tools[0]?.name ?? "");
  const [spokespersonId, setSpokespersonId] = useState<string>(
    spokespeople[0]?.id ?? "",
  );
  const [question, setQuestion] = useState<string>("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<DispatchResult | null>(null);

  // Contract rule 3 — DRAFT session id is page-scoped React state.
  // First dispatch creates one; subsequent dispatches on the same
  // spokesperson reuse it. Switching spokespeople invalidates.
  const [draftSessionId, setDraftSessionId] = useState<string | null>(null);
  const [draftSessionSpokespersonId, setDraftSessionSpokespersonId] =
    useState<string | null>(null);

  useEffect(() => {
    // Reset the cached DRAFT if the operator swaps spokespeople —
    // a DRAFT is tied to its spokesperson (its knowledge scope).
    if (
      draftSessionSpokespersonId &&
      spokespersonId !== draftSessionSpokespersonId
    ) {
      setDraftSessionId(null);
      setDraftSessionSpokespersonId(null);
    }
  }, [spokespersonId, draftSessionSpokespersonId]);

  const createSession = useCreateRealtimeSession();
  const invoke = useInvokeTool();

  const isPending = createSession.isPending || invoke.isPending;
  const canSubmit =
    !isPending &&
    toolName.trim() !== "" &&
    spokespersonId.trim() !== "" &&
    question.trim() !== "";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitError(null);
    setLastResult(null);

    try {
      // Contract rule 5 — auto-create + reuse DRAFT container.
      // Contract rule 2 — `draft_only: true` keeps the row in DRAFT
      // and skips the media-engine calls; without this flag the
      // create endpoint would start a real Runway session, breaking
      // C5's "never starts a live realtime session" contract and
      // burning ~$0.14 per form submit (F-09 fix).
      let sessionId = draftSessionId;
      if (!sessionId) {
        const session = await createSession.mutateAsync({
          spokesperson: spokespersonId,
          title: "Bridge tool session",
          draft_only: true,
        });
        sessionId = session.id;
        setDraftSessionId(session.id);
        setDraftSessionSpokespersonId(spokespersonId);
      }

      const result = await invoke.mutateAsync({
        sessionId,
        tool_name: toolName,
        args: { question: question.trim() },
      });

      setLastResult(result);

      if (result.state === "failed" || result.state === "rejected") {
        setSubmitError(
          result.error_message?.trim() || "Dispatch did not succeed.",
        );
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      setSubmitError(message);
    }
  }

  if (spokespeople.length === 0) {
    return (
      <div
        data-testid="tools-no-spokespeople"
        className="rounded-md border border-luxe bg-card p-6 text-sm text-mist"
      >
        Create a spokesperson before invoking a bridge tool — the DRAFT session
        needs one to scope its knowledge.
        <Link
          to="/spokespeople/new"
          className="ml-1 text-gold hover:underline"
        >
          Create one →
        </Link>
      </div>
    );
  }

  return (
    <form
      data-testid="tools-form"
      onSubmit={handleSubmit}
      className="flex flex-col gap-6 rounded-md border border-luxe bg-card p-6"
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="tools-tool-picker">Tool</Label>
        <select
          id="tools-tool-picker"
          data-testid="tools-tool-picker"
          value={toolName}
          onChange={(e) => setToolName(e.target.value)}
          className="rounded-md border border-luxe bg-background px-3 py-2 text-sm text-cream focus:outline-none focus:ring-2 focus:ring-gold"
        >
          {tools.map((t) => (
            <option key={t.name} value={t.name}>
              {formatToolOptionLabel(t)}
            </option>
          ))}
        </select>
        <p className="text-xs text-fog">
          {tools.find((t) => t.name === toolName)?.hint ?? ""}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="tools-spokesperson-picker">Spokesperson</Label>
        <select
          id="tools-spokesperson-picker"
          data-testid="tools-spokesperson-picker"
          value={spokespersonId}
          onChange={(e) => setSpokespersonId(e.target.value)}
          className="rounded-md border border-luxe bg-background px-3 py-2 text-sm text-cream focus:outline-none focus:ring-2 focus:ring-gold"
        >
          {spokespeople.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="tools-question">Question</Label>
        <textarea
          id="tools-question"
          data-testid="tools-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={4}
          placeholder="What would you like to ask the engine?"
          className="rounded-md border border-luxe bg-background px-3 py-2 text-sm text-cream focus:outline-none focus:ring-2 focus:ring-gold"
        />
      </div>

      {submitError && (
        <div
          data-testid="tools-submit-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 flex-none" />
          <span>{submitError}</span>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          type="submit"
          data-testid="tools-submit"
          disabled={!canSubmit}
          className={cn(isPending && "opacity-70")}
        >
          {isPending && (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          )}
          {isPending ? "Dispatching…" : "Ask"}
        </Button>
        {draftSessionId && (
          <span
            data-testid="tools-session-reuse-badge"
            className="text-xs text-fog"
          >
            Reusing session {draftSessionId.slice(0, 8)}…
          </span>
        )}
      </div>

      {lastResult && lastResult.state === "succeeded" && (
        <BridgeResultPanel result={lastResult} />
      )}
    </form>
  );
}
