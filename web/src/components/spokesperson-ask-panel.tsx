/**
 * SpokespersonAskPanel — Chapter 6 slices 1 + 2 (SESSIONs 234, 235).
 *
 * Beats covered:
 *  • Beat 1 (Return)      — portrait + "Ask {name} something" hero.
 *  • Beat 2 (Ask)         — inline exchange + first-class receipt.
 *  • Beat 3 (Fix source)  — click-receipt → inline doc editor;
 *                            honest-fallback → "Teach {name}
 *                            about this" inline compose.
 *
 * Design lock: docs/design/CUSTOMER_JOURNEY_V1.md §"Chapter 6 —
 * Ongoing training".
 *
 * Two visual states composed on the same slot:
 *
 *  • **Portrait state (default)** — hero portrait with an
 *    "Ask {name} something" input directly under it. Operator
 *    sees Oliver present; the affordance to engage is one field
 *    away.
 *  • **Chat state (engaged)** — portrait area collapses to a
 *    compact thumbnail; the answer + receipt take the space.
 *    A "Back to portrait" affordance dismisses back to default.
 *
 * The swap is the design-lock's Beat 5 grammar applied to Ask:
 * "portrait becomes something when engaged, portrait returns on
 * end/error." Talk (R8) will share this pattern in a later
 * slice, but for now Ask is the only surface that swaps.
 *
 * Ship bar (design lock, non-negotiable):
 *  • Receipt is visually first-class — not a footnote. Design
 *    lock: "the operator's eyes go to the receipt because that
 *    is what 'prove it' actually means."
 *  • Honest fallback ("answered from what he already knows") is
 *    rendered as a receipt shape, not hidden — the operator
 *    needs to see that Oliver had nothing to draw on so Beat 3
 *    (later slice) can suggest teaching him.
 *  • Name interpolation everywhere — no hardcoded "Oliver."
 */
import { useState } from "react";
import { ArrowLeft, MessageCircleQuestion, PencilLine, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useAskSpokesperson,
  type AskCitation,
  type AskResponse,
  type Spokesperson,
} from "@/lib/api/spokespeople";
import {
  useCreateKnowledge,
  useKnowledgeDocument,
  useUpdateKnowledge,
} from "@/lib/api/knowledge";

interface SpokespersonAskPanelProps {
  spokesperson: Spokesperson;
}

// Beat 3 — which secondary surface (if any) is open inside the
// chat state. Chat state itself is implied by ``lastExchange`` or
// a pending ask; ``fix`` layers on top and replaces the follow-up
// input while the operator repairs the source (cited-doc edit or
// teach-me compose).
type FixMode =
  | { kind: "none" }
  | { kind: "edit"; citation: AskCitation }
  | { kind: "compose"; question: string };

export function SpokespersonAskPanel({
  spokesperson,
}: SpokespersonAskPanelProps) {
  // Locally-held exchange state. Slice-1 shows the single most
  // recent exchange; a follow-up-history slice (queued) will
  // append. Local state (not react-query) because the exchange
  // is ephemeral — no server-side history model yet, and the
  // asks themselves are $0.001/call so re-mounting the panel
  // does not need to preserve them.
  const [question, setQuestion] = useState("");
  const [lastExchange, setLastExchange] = useState<{
    question: string;
    response: AskResponse;
  } | null>(null);
  const [fix, setFix] = useState<FixMode>({ kind: "none" });
  // Beat 3 saved-notice — dismissed on next ask, explicit close,
  // or opening another fix surface. NOT gated on re-embed
  // completion (Beat 4 owns that gate); slice-2 shows the honest
  // "re-reading" copy as a soft acknowledgment.
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const ask = useAskSpokesperson();

  const engaged = lastExchange !== null || ask.isPending;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const q = question.trim();
    if (!q || ask.isPending) return;
    // A new question clears any open fix surface + prior saved
    // notice so the exchange area is clean for the incoming answer.
    setFix({ kind: "none" });
    setSavedNotice(null);
    try {
      const response = await ask.mutateAsync({
        id: spokesperson.id,
        question: q,
      });
      setLastExchange({ question: q, response });
      setQuestion("");
    } catch {
      // ask.error surfaces in the render path below.
    }
  }

  function handleDismiss() {
    setLastExchange(null);
    setFix({ kind: "none" });
    setSavedNotice(null);
    ask.reset();
  }

  function handleCitationClick(citation: AskCitation) {
    setFix({ kind: "edit", citation });
    setSavedNotice(null);
  }

  function handleTeachClick() {
    if (!lastExchange) return;
    setFix({ kind: "compose", question: lastExchange.question });
    setSavedNotice(null);
  }

  function handleFixCancel() {
    setFix({ kind: "none" });
  }

  function handleFixSaved() {
    setFix({ kind: "none" });
    setSavedNotice(
      `${spokesperson.name} is re-reading your updated notes…`,
    );
  }

  return (
    <section
      className="reveal luxe-shadow flex flex-col gap-6 rounded-md border border-luxe bg-card p-8"
      style={{ "--reveal-delay": "0.02s" } as React.CSSProperties}
      data-testid="spokesperson-ask-panel"
      data-engaged={engaged ? "true" : "false"}
    >
      <header className="flex items-center justify-between border-b border-luxe/60 pb-3">
        <div className="flex items-center gap-2">
          <MessageCircleQuestion className="h-4 w-4 text-gold" />
          <h2 className="font-display text-base tracking-tight">
            Ask {spokesperson.name}
          </h2>
        </div>
        {engaged && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            data-testid="ask-dismiss"
            disabled={ask.isPending}
          >
            <ArrowLeft className="mr-1 h-3.5 w-3.5" />
            Back to portrait
          </Button>
        )}
      </header>

      {!engaged ? (
        <PortraitState
          spokesperson={spokesperson}
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
          submitting={ask.isPending}
        />
      ) : (
        <ChatState
          spokesperson={spokesperson}
          lastExchange={lastExchange}
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
          submitting={ask.isPending}
          error={ask.error}
          fix={fix}
          savedNotice={savedNotice}
          onCitationClick={handleCitationClick}
          onTeachClick={handleTeachClick}
          onFixCancel={handleFixCancel}
          onFixSaved={handleFixSaved}
        />
      )}
    </section>
  );
}

// ---- portrait state (default) --------------------------------------

function PortraitState({
  spokesperson,
  question,
  onQuestionChange,
  onSubmit,
  submitting,
}: {
  spokesperson: Spokesperson;
  question: string;
  onQuestionChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  submitting: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-6" data-testid="ask-portrait-state">
      <AskHeroPortrait
        portraitPath={spokesperson.portrait_path}
        name={spokesperson.name}
      />
      <AskForm
        spokespersonName={spokesperson.name}
        question={question}
        onQuestionChange={onQuestionChange}
        onSubmit={onSubmit}
        submitting={submitting}
        variant="hero"
      />
    </div>
  );
}

// ---- chat state (engaged) ------------------------------------------

function ChatState({
  spokesperson,
  lastExchange,
  question,
  onQuestionChange,
  onSubmit,
  submitting,
  error,
  fix,
  savedNotice,
  onCitationClick,
  onTeachClick,
  onFixCancel,
  onFixSaved,
}: {
  spokesperson: Spokesperson;
  lastExchange: { question: string; response: AskResponse } | null;
  question: string;
  onQuestionChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  submitting: boolean;
  error: unknown;
  fix: FixMode;
  savedNotice: string | null;
  onCitationClick: (citation: AskCitation) => void;
  onTeachClick: () => void;
  onFixCancel: () => void;
  onFixSaved: () => void;
}) {
  const fixOpen = fix.kind !== "none";
  return (
    <div className="flex flex-col gap-5" data-testid="ask-chat-state">
      <div className="flex items-start gap-4">
        <AskThumbnail
          portraitPath={spokesperson.portrait_path}
          name={spokesperson.name}
        />
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {lastExchange && (
            <ExchangePanel
              question={lastExchange.question}
              response={lastExchange.response}
              spokespersonName={spokesperson.name}
              onCitationClick={onCitationClick}
              onTeachClick={onTeachClick}
            />
          )}
          {submitting && !lastExchange && (
            <p
              className="text-sm text-fog italic"
              data-testid="ask-loading"
            >
              {spokesperson.name} is thinking…
            </p>
          )}
          {error instanceof Error && (
            <p
              className="text-sm text-destructive"
              data-testid="ask-error"
            >
              Couldn't reach {spokesperson.name} — {error.message}
            </p>
          )}
          {savedNotice && !fixOpen && (
            <p
              className="rounded-sm border border-gold/30 bg-gold/5 px-3 py-2 text-sm text-foreground/90"
              data-testid="ask-saved-notice"
            >
              {savedNotice}
            </p>
          )}
        </div>
      </div>
      {fix.kind === "edit" ? (
        <EditDocSurface
          spokespersonName={spokesperson.name}
          citation={fix.citation}
          onCancel={onFixCancel}
          onSaved={onFixSaved}
        />
      ) : fix.kind === "compose" ? (
        <ComposeDocSurface
          spokesperson={spokesperson}
          question={fix.question}
          onCancel={onFixCancel}
          onSaved={onFixSaved}
        />
      ) : (
        <AskForm
          spokespersonName={spokesperson.name}
          question={question}
          onQuestionChange={onQuestionChange}
          onSubmit={onSubmit}
          submitting={submitting}
          variant="followup"
        />
      )}
    </div>
  );
}

// ---- the exchange (answer + first-class receipt) -------------------

function ExchangePanel({
  question,
  response,
  spokespersonName,
  onCitationClick,
  onTeachClick,
}: {
  question: string;
  response: AskResponse;
  spokespersonName: string;
  onCitationClick: (citation: AskCitation) => void;
  onTeachClick: () => void;
}) {
  return (
    <div className="flex flex-col gap-4" data-testid="ask-exchange">
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-fog">
          You asked
        </span>
        <p className="text-sm text-foreground/80" data-testid="ask-question-echo">
          {question}
        </p>
      </div>
      <div className="flex flex-col gap-3 rounded-sm border border-luxe/60 bg-background/60 p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-gold" />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-gold">
            {spokespersonName} says
          </span>
        </div>
        <p
          className="whitespace-pre-wrap text-base leading-relaxed text-cream"
          data-testid="ask-answer"
        >
          {response.answer}
        </p>
      </div>
      <Receipt
        response={response}
        spokespersonName={spokespersonName}
        onCitationClick={onCitationClick}
        onTeachClick={onTeachClick}
      />
    </div>
  );
}

/**
 * The receipt is the load-bearing element per the design lock —
 * "not a footnote." Given equal visual weight to the answer via
 * its own bordered card + strong label. Two shapes:
 *  - grounded: "From your notes on X (3 chunks), Y (1 chunk)." Each
 *    citation row is a button (Beat 3) → opens the inline doc
 *    editor keyed by ``document_id``.
 *  - honest fallback: "{name} answered from what {name} already
 *    knows." A "Teach {name} about this" button (Beat 3) opens
 *    the inline compose surface pre-scoped to the question.
 */
function Receipt({
  response,
  spokespersonName,
  onCitationClick,
  onTeachClick,
}: {
  response: AskResponse;
  spokespersonName: string;
  onCitationClick: (citation: AskCitation) => void;
  onTeachClick: () => void;
}) {
  if (!response.used_knowledge || response.citations.length === 0) {
    return (
      <div
        className="flex flex-col gap-3 rounded-sm border border-amber-500/30 bg-amber-500/5 p-4"
        data-testid="ask-receipt"
        data-shape="honest-fallback"
      >
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-amber-500/90">
            Where this came from
          </span>
          <p className="text-sm text-foreground/90">
            {spokespersonName} answered from what {spokespersonName} already
            knows — nothing specific in what you've taught them yet.
          </p>
        </div>
        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onTeachClick}
            data-testid="ask-teach-cta"
            className="border-amber-500/40 text-amber-100 hover:bg-amber-500/10"
          >
            <PencilLine className="mr-1 h-3.5 w-3.5" />
            Teach {spokespersonName} about this
          </Button>
        </div>
      </div>
    );
  }
  // Sort most-cited-first per design lock: "receipt names each,
  // comma-separated, most-cited first."
  const sorted = [...response.citations].sort(
    (a, b) => b.chunk_count - a.chunk_count,
  );
  return (
    <div
      className="rounded-sm border border-gold/30 bg-gold/5 p-4"
      data-testid="ask-receipt"
      data-shape="grounded"
    >
      <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-gold">
        From your notes
      </span>
      <ul className="mt-2 flex flex-col gap-1">
        {sorted.map((c) => (
          <li key={c.document_id}>
            <button
              type="button"
              onClick={() => onCitationClick(c)}
              className="group flex w-full items-baseline justify-between gap-3 rounded-sm px-1 py-1 text-left text-sm transition-colors hover:bg-gold/10 focus:bg-gold/10 focus:outline-none focus:ring-1 focus:ring-gold/40"
              data-testid={`ask-citation-${c.document_id}`}
              aria-label={`Edit ${c.title}`}
            >
              <span className="truncate text-foreground/90 group-hover:text-gold group-focus:text-gold">
                {c.title}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-fog">
                {c.chunk_count} {c.chunk_count === 1 ? "excerpt" : "excerpts"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---- Beat 3 — edit cited doc surface -------------------------------
//
// Renders inside the chat state in place of the follow-up input when
// the operator clicks a citation. Fetches the doc, prefills a
// textarea from ``processed_content``, PATCHes on Save. The backend
// re-ingest (SESSION 235 serializer change) preserves the doc id +
// workspace + M2M so the receipt's chunk_count refreshes when the
// operator asks again — no separate reconciliation needed.

function EditDocSurface({
  spokespersonName,
  citation,
  onCancel,
  onSaved,
}: {
  spokespersonName: string;
  citation: AskCitation;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const docQuery = useKnowledgeDocument(citation.document_id);
  const update = useUpdateKnowledge(docQuery.data?.workspace);
  const [text, setText] = useState<string | null>(null);
  // Prefill once the fetch resolves; ignore subsequent refetches so
  // the operator's in-progress edits are not clobbered.
  if (docQuery.data && text === null) {
    setText(docQuery.data.processed_content ?? "");
  }

  const dirty = text !== null && text.trim().length > 0;
  async function handleSave() {
    if (text === null || !dirty || update.isPending) return;
    try {
      await update.mutateAsync({
        id: citation.document_id,
        payload: { text_content: text },
      });
      onSaved();
    } catch {
      // update.error surfaces in the panel below.
    }
  }

  return (
    <div
      className="flex flex-col gap-3 rounded-sm border border-gold/40 bg-background/60 p-4"
      data-testid="ask-edit-surface"
    >
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-gold">
          Fixing
        </span>
        <p className="font-display text-sm text-cream" data-testid="ask-edit-title">
          {citation.title}
        </p>
      </div>
      {docQuery.isLoading && (
        <p className="text-sm text-fog italic" data-testid="ask-edit-loading">
          Opening this note…
        </p>
      )}
      {docQuery.error instanceof Error && (
        <p className="text-sm text-destructive" data-testid="ask-edit-fetch-error">
          Couldn't open this note — {docQuery.error.message}
        </p>
      )}
      {text !== null && (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="min-h-40 w-full rounded-sm border border-luxe bg-background px-3 py-2 text-sm text-cream focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold/40"
          data-testid="ask-edit-textarea"
          aria-label={`Edit ${citation.title}`}
          disabled={update.isPending}
        />
      )}
      {update.error instanceof Error && (
        <p className="text-sm text-destructive" data-testid="ask-edit-save-error">
          Couldn't save — {update.error.message}
        </p>
      )}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-fog">
          {spokespersonName} will re-read this after you save.
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancel}
            data-testid="ask-edit-cancel"
            disabled={update.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={!dirty || update.isPending}
            data-testid="ask-edit-save"
          >
            {update.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---- Beat 3 — teach-me compose surface -----------------------------
//
// Rendered when the honest-fallback teach-me CTA is clicked. Title
// is pre-scoped to the question so the operator's eyeline lands on
// the body field. POSTs with ``spokesperson_ids=[<this>]`` so the
// new note is immediately visible to this spokesperson (empty M2M
// would visible-to-all, which is broader than the operator asked
// for on a teach-this-one moment).

function ComposeDocSurface({
  spokesperson,
  question,
  onCancel,
  onSaved,
}: {
  spokesperson: Spokesperson;
  question: string;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const create = useCreateKnowledge(spokesperson.workspace);
  const [title, setTitle] = useState(suggestedTitleFromQuestion(question));
  const [text, setText] = useState("");

  const dirty = title.trim().length > 0 && text.trim().length > 0;

  async function handleSave() {
    if (!dirty || create.isPending) return;
    try {
      await create.mutateAsync({
        workspace: spokesperson.workspace,
        title: title.trim(),
        text_content: text,
        spokesperson_ids: [spokesperson.id],
      });
      onSaved();
    } catch {
      // create.error surfaces in the panel below.
    }
  }

  return (
    <div
      className="flex flex-col gap-3 rounded-sm border border-amber-500/40 bg-background/60 p-4"
      data-testid="ask-compose-surface"
    >
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-amber-500/90">
          Teaching {spokesperson.name}
        </span>
        <p className="text-sm text-foreground/80">
          You asked: <span className="text-cream">{question}</span>
        </p>
      </div>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-fog">
          Title
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-sm border border-luxe bg-background px-3 py-2 text-sm text-cream focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold/40"
          data-testid="ask-compose-title"
          disabled={create.isPending}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-fog">
          What should {spokesperson.name} know?
        </span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="min-h-40 w-full rounded-sm border border-luxe bg-background px-3 py-2 text-sm text-cream focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold/40"
          data-testid="ask-compose-textarea"
          aria-label={`Teach ${spokesperson.name} about ${question}`}
          disabled={create.isPending}
        />
      </label>
      {create.error instanceof Error && (
        <p className="text-sm text-destructive" data-testid="ask-compose-save-error">
          Couldn't save — {create.error.message}
        </p>
      )}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-fog">
          Saved as a note attached to {spokesperson.name}.
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancel}
            data-testid="ask-compose-cancel"
            disabled={create.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={!dirty || create.isPending}
            data-testid="ask-compose-save"
          >
            {create.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Turn a question into a short "About: ..." title, capped so it
 * doesn't sprawl past the input width. Trailing punctuation gets
 * stripped — a title doesn't need the question mark. */
function suggestedTitleFromQuestion(question: string): string {
  const cleaned = question.trim().replace(/[?.!]+$/, "").trim();
  if (!cleaned) return "New note";
  const capped = cleaned.length > 60 ? cleaned.slice(0, 57) + "…" : cleaned;
  return `About: ${capped}`;
}

// ---- form (shared between portrait + chat states) ------------------

function AskForm({
  spokespersonName,
  question,
  onQuestionChange,
  onSubmit,
  submitting,
  variant,
}: {
  spokespersonName: string;
  question: string;
  onQuestionChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  submitting: boolean;
  variant: "hero" | "followup";
}) {
  const placeholder = `Ask ${spokespersonName} something.`;
  return (
    <form
      onSubmit={onSubmit}
      className={
        variant === "hero"
          ? "flex w-full max-w-xl flex-col gap-2"
          : "flex w-full flex-col gap-2"
      }
      data-testid={`ask-form-${variant}`}
    >
      <div className="flex items-stretch gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder={placeholder}
          disabled={submitting}
          data-testid="ask-input"
          className="flex-1 rounded-sm border border-luxe bg-background px-3 py-2 text-sm placeholder:text-fog focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold/40 disabled:opacity-60"
          aria-label={placeholder}
        />
        <Button
          type="submit"
          disabled={submitting || question.trim().length === 0}
          data-testid="ask-submit"
        >
          {submitting ? "Asking…" : "Ask"}
        </Button>
      </div>
    </form>
  );
}

// ---- portrait renderers --------------------------------------------
//
// Lightweight — no orbital treatment, no CloudFront JWT refresh
// (the identity panel below still has the fully-decorated
// Portrait; this hero is the coaching-context portrait).

function AskHeroPortrait({
  portraitPath,
  name,
}: {
  portraitPath: string;
  name: string;
}) {
  if (portraitPath) {
    return (
      <div
        className="luxe-shadow relative h-52 w-52 overflow-hidden rounded-full ring-1 ring-gold/40"
        data-testid="ask-hero-portrait"
      >
        <img
          src={portraitPath}
          alt={name}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className="luxe-shadow flex h-52 w-52 items-center justify-center rounded-full ring-1 ring-gold/40 bg-gradient-to-br from-midnight via-ink to-midnight/70"
      data-testid="ask-hero-portrait"
    >
      <span
        className="font-display text-5xl font-light text-cream/70"
        aria-hidden
      >
        {deriveInitials(name)}
      </span>
    </div>
  );
}

function AskThumbnail({
  portraitPath,
  name,
}: {
  portraitPath: string;
  name: string;
}) {
  if (portraitPath) {
    return (
      <div
        className="luxe-shadow relative h-16 w-16 shrink-0 overflow-hidden rounded-full ring-1 ring-gold/40"
        data-testid="ask-thumbnail"
      >
        <img
          src={portraitPath}
          alt={name}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className="luxe-shadow flex h-16 w-16 shrink-0 items-center justify-center rounded-full ring-1 ring-gold/40 bg-gradient-to-br from-midnight via-ink to-midnight/70"
      data-testid="ask-thumbnail"
    >
      <span className="font-display text-xl font-light text-cream/70" aria-hidden>
        {deriveInitials(name)}
      </span>
    </div>
  );
}

function deriveInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  const last = parts[parts.length - 1];
  if (!first) return "?";
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  return ((first[0] ?? "") + (last?.[0] ?? "")).toUpperCase() || "?";
}
