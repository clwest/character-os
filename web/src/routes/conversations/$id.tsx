/**
 * Conversation chat view — K9 (knowledge arc).
 *
 * One thread. Message list + composer. Submits to
 * `POST /api/conversations/<id>/messages/` which returns
 * both the user message and the synthesized spokesperson
 * reply in one round trip.
 *
 * The K9 endpoint runs synthesis server-side, so the
 * spokesperson reply lands the moment the request resolves.
 * No polling needed for v1; SSE / streaming is a v1.1
 * concern (Q-k-3 resolved).
 */
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Loader2, Send, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VerificationStatusBadge } from "@/components/verification-status-badge";
import {
  type ConversationMessage,
  type VerifierMode,
  type VerifierRejection,
  useMessages,
  useSendMessage,
  useThread,
  verifierRejectionSchema,
} from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/client";

export function ConversationChatRoute() {
  const { id } = useParams<{ id: string }>();
  const thread = useThread(id);
  const messages = useMessages(id);
  const send = useSendMessage(id);
  const [draft, setDraft] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  // K6.4 v1.1 — per-request verifier mode override. Default
  // "warn" so the SPA's selection always wins (warns are
  // visible, strict requires an explicit flip).
  const [verifierMode, setVerifierMode] = useState<VerifierMode>("warn");
  // K6.4 v1.1 — when strict mode rejects (422), we don't show
  // a one-liner submit error; we render a full rejection panel
  // so the operator can review what the LLM almost said.
  const [verifierRejection, setVerifierRejection] = useState<VerifierRejection | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when a new message lands.
  useEffect(() => {
    if (!messages.data) return;
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.data?.length]);

  if (thread.isLoading) {
    return <ChatSkeleton />;
  }
  if (thread.isError || !thread.data) {
    return (
      <div className="flex flex-col gap-4 py-10">
        <BackLink />
        <p className="text-sm text-destructive">
          {thread.error instanceof Error
            ? thread.error.message
            : "Conversation not found"}
        </p>
      </div>
    );
  }

  const data = thread.data;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setVerifierRejection(null);
    const trimmed = draft.trim();
    if (!trimmed) return;
    setDraft("");
    try {
      await send.mutateAsync({ content: trimmed, verifierMode });
    } catch (err) {
      // K6.4 v1.1 — strict-mode rejection comes back as 422
      // with a `verifier_rejection` body. Surface that as a
      // structured panel, not a one-liner.
      if (err instanceof ApiError && err.status === 422) {
        const body = err.body as { verifier_rejection?: unknown } | null;
        const parsed = body?.verifier_rejection
          ? verifierRejectionSchema.safeParse(body.verifier_rejection)
          : null;
        if (parsed?.success) {
          setVerifierRejection(parsed.data);
          // Restore draft so operator can edit + retry; the
          // placeholder spokesperson message is already in
          // the thread's message list via the next refetch.
          setDraft(trimmed);
          return;
        }
      }
      setSubmitError(extractErrorMessage(err));
      setDraft(trimmed);
    }
  }

  return (
    <div className="flex flex-col gap-6 py-10" data-testid="conversation-chat">
      <Header thread={data} />
      <div
        ref={scrollRef}
        className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto rounded-md border bg-card p-5 shadow-paper"
        data-testid="conversation-messages"
      >
        {messages.isLoading && <ListSkeleton />}
        {messages.isError && (
          <p className="text-sm text-destructive">Couldn't load messages.</p>
        )}
        {messages.data?.length === 0 && (
          <EmptyState spokespersonName={data.spokesperson_name} />
        )}
        {messages.data?.map((m) => (
          <MessageBubble key={m.id} message={m} spokespersonName={data.spokesperson_name} />
        ))}
        {send.isPending && <PendingBubble />}
      </div>

      {submitError && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {submitError}
        </div>
      )}

      {verifierRejection && (
        <VerifierRejectionPanel
          rejection={verifierRejection}
          onDismiss={() => setVerifierRejection(null)}
        />
      )}

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-2"
        data-testid="conversation-composer"
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          maxLength={4000}
          placeholder={`Message ${data.spokesperson_name}…`}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={send.isPending}
          onKeyDown={(e) => {
            // Cmd/Ctrl + Enter submits — matches chat-UX conventions.
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              handleSubmit(e as unknown as React.FormEvent);
            }
          }}
          data-testid="conversation-input"
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              ⌘ / Ctrl + Enter to send
            </span>
            <VerifierModeSelect
              value={verifierMode}
              onChange={setVerifierMode}
              disabled={send.isPending}
            />
          </div>
          <Button
            type="submit"
            disabled={send.isPending || !draft.trim()}
            data-testid="conversation-send"
          >
            {send.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Thinking…
              </>
            ) : (
              <>
                <Send className="mr-1 h-4 w-4" />
                Send
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

function Header({ thread }: { thread: ReturnType<typeof useThread>["data"] }) {
  if (!thread) return null;
  return (
    <header className="flex flex-col gap-3 border-b pb-6">
      <Link
        to={`/spokespeople/${thread.spokesperson}`}
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="conversation-back"
      >
        <ArrowLeft className="h-3 w-3" />
        {thread.spokesperson_name}
      </Link>
      <h1 className="font-display text-3xl leading-tight tracking-tight md:text-4xl">
        {thread.title || `Chat with ${thread.spokesperson_name}`}
      </h1>
      <p className="text-sm text-muted-foreground">
        {thread.message_count} message
        {thread.message_count === 1 ? "" : "s"}
      </p>
    </header>
  );
}

function MessageBubble({
  message,
  spokespersonName,
}: {
  message: ConversationMessage;
  spokespersonName: string;
}) {
  const isUser = message.role === "user";
  const warnings = message.verification_warnings ?? [];
  const rejected = message.rejected_synthesis ?? "";
  const hasVerifierSurface = warnings.length > 0 || rejected.length > 0;
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={
        "flex flex-col gap-1 " +
        (isUser ? "items-end" : "items-start")
      }
      data-testid={`message-${message.role}`}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {isUser ? "You" : spokespersonName}
        </span>
        {!isUser && message.verification_status && (
          <VerificationStatusBadge status={message.verification_status} />
        )}
      </div>
      <div
        className={
          "max-w-[80%] whitespace-pre-wrap rounded-md border px-4 py-2 text-sm " +
          (isUser
            ? "border-foreground/20 bg-foreground/5"
            : "border-muted bg-muted/30")
        }
      >
        {message.content}
      </div>
      {!isUser && hasVerifierSurface && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 inline-flex items-center gap-1 self-start rounded-md border border-warning/40 bg-warning/10 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-warning transition-colors hover:bg-warning/20"
          data-testid={`message-verifier-toggle-${message.id}`}
        >
          <AlertTriangle className="h-3 w-3" />
          {rejected
            ? "K6.4 strict — reply withheld"
            : `K6.4 flagged ${warnings.length} claim${warnings.length === 1 ? "" : "s"}`}
          <span className="text-warning/60">{expanded ? "▲" : "▼"}</span>
        </button>
      )}
      {!isUser && hasVerifierSurface && expanded && (
        <VerifierInlineDetail warnings={warnings} rejected={rejected} />
      )}
    </div>
  );
}

function VerifierInlineDetail({
  warnings,
  rejected,
}: {
  warnings: ConversationMessage["verification_warnings"];
  rejected: string;
}) {
  return (
    <div
      className="max-w-[80%] rounded-md border border-warning/30 bg-warning/5 p-3 text-xs"
      data-testid="message-verifier-detail"
    >
      {warnings.length > 0 && (
        <div className="mb-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-warning mb-1">
            Unsupported terms
          </div>
          <ul className="list-disc space-y-0.5 pl-5">
            {warnings.map((w, i) => (
              <li key={`${w.claim}-${i}`}>
                <span className="font-mono">"{w.claim}"</span>{" "}
                <span className="text-muted-foreground">— {w.kind}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {rejected && (
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-warning mb-1">
            What the LLM almost said (withheld)
          </div>
          <p className="whitespace-pre-wrap text-muted-foreground">{rejected}</p>
        </div>
      )}
    </div>
  );
}

function VerifierRejectionPanel({
  rejection,
  onDismiss,
}: {
  rejection: VerifierRejection;
  onDismiss: () => void;
}) {
  return (
    <div
      className="rounded-md border border-warning/40 bg-warning/10 p-4 text-sm"
      data-testid="verifier-rejection-panel"
      role="alert"
    >
      <div className="mb-2 flex items-start gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-warning">
        <ShieldAlert className="h-4 w-4" />
        Strict mode held the reply
      </div>
      <p className="mb-2 text-foreground">
        K6.4 flagged {rejection.unsupported_claims.length} unsupported claim
        {rejection.unsupported_claims.length === 1 ? "" : "s"} in the synthesized
        reply. The user message was recorded; the reply was withheld.
      </p>
      <ul className="mb-3 list-disc space-y-0.5 pl-5 text-xs">
        {rejection.unsupported_claims.map((c, i) => (
          <li key={`${c.claim}-${i}`}>
            <span className="font-mono">"{c.claim}"</span>{" "}
            <span className="text-muted-foreground">({c.kind})</span>
          </li>
        ))}
      </ul>
      <details className="mb-3 text-xs">
        <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.18em] text-warning">
          Show what the LLM almost said
        </summary>
        <p className="mt-1 whitespace-pre-wrap rounded-md bg-background/60 p-2 text-muted-foreground">
          {rejection.rejected_synthesis || "(empty)"}
        </p>
      </details>
      <button
        type="button"
        onClick={onDismiss}
        className="inline-flex items-center font-mono text-[10px] uppercase tracking-[0.22em] text-warning/80 underline-offset-2 hover:text-warning hover:underline"
      >
        Dismiss
      </button>
    </div>
  );
}

function VerifierModeSelect({
  value,
  onChange,
  disabled,
}: {
  value: VerifierMode;
  onChange: (v: VerifierMode) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
      Verifier:
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as VerifierMode)}
        disabled={disabled}
        className="rounded border border-input bg-background px-1.5 py-0.5 text-[10px] uppercase tracking-[0.18em] disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="conversation-verifier-mode"
      >
        <option value="warn">Warn</option>
        <option value="strict">Strict</option>
        <option value="off">Off</option>
      </select>
    </label>
  );
}

function PendingBubble() {
  return (
    <div className="flex flex-col gap-1 items-start" data-testid="message-pending">
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        Thinking…
      </span>
      <div className="max-w-[80%] rounded-md border border-muted bg-muted/30 px-4 py-2 text-sm text-muted-foreground">
        <Loader2 className="inline h-3 w-3 animate-spin" />
        <span className="ml-2">Generating reply…</span>
      </div>
    </div>
  );
}

function EmptyState({ spokespersonName }: { spokespersonName: string }) {
  return (
    <div
      className="flex flex-col items-center gap-2 py-10 text-center"
      data-testid="conversation-empty"
    >
      <p className="font-display text-xl tracking-tight">
        No messages yet
      </p>
      <p className="max-w-md text-sm text-muted-foreground">
        Say hi to {spokespersonName} — they'll draw on the workspace knowledge
        to answer. Try "what is your business about?" or "what makes you
        different from competitors?"
      </p>
    </div>
  );
}

function ChatSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6 py-10">
      <div className="h-10 w-1/2 rounded bg-muted" />
      <div className="h-64 rounded bg-muted" />
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={
            "h-12 max-w-[80%] animate-pulse rounded-md bg-muted/40 " +
            (i % 2 === 0 ? "self-end" : "self-start")
          }
        />
      ))}
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/dashboard"
      className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="h-3 w-3" />
      Dashboard
    </Link>
  );
}

function extractErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const body = err.body as Record<string, unknown> | null;
    if (body) {
      if (typeof body.detail === "string") return body.detail;
      const fields = Object.entries(body).map(([k, v]) => {
        const msg = Array.isArray(v) ? v.join("; ") : String(v);
        return `${k}: ${msg}`;
      });
      if (fields.length > 0) return fields.join(" • ");
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Unknown error";
}
