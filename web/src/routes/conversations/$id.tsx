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
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  type ConversationMessage,
  useMessages,
  useSendMessage,
  useThread,
} from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/client";

export function ConversationChatRoute() {
  const { id } = useParams<{ id: string }>();
  const thread = useThread(id);
  const messages = useMessages(id);
  const send = useSendMessage(id);
  const [draft, setDraft] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
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
    const trimmed = draft.trim();
    if (!trimmed) return;
    setDraft("");
    try {
      await send.mutateAsync(trimmed);
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
      // Restore the draft so the operator can edit + retry.
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
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            ⌘ / Ctrl + Enter to send
          </span>
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
  return (
    <div
      className={
        "flex flex-col gap-1 " +
        (isUser ? "items-end" : "items-start")
      }
      data-testid={`message-${message.role}`}
    >
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {isUser ? "You" : spokespersonName}
      </span>
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
    </div>
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
