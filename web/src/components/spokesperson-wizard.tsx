import { useCallback, useReducer } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/api/workspaces";
import { useSuggestTone } from "@/lib/api/prompts";
import { TONE_ARCHETYPES, type ToneArchetype } from "@/lib/api/spokespeople";
import { cn } from "@/lib/utils";

/**
 * Create-spokesperson wizard scaffold (SESSION 128 — wizard slice 5).
 *
 * Pure structural shell: 4 numbered steps (Identity / Portrait /
 * Voice / Confirm) with forward/back navigation and shared state via
 * useReducer. Slices 6-9 (SESSION 129+) fill each step's body in;
 * what ships today is the step indicator, the reducer shape, the
 * navigation primitives, and minimal placeholder bodies so the
 * scaffold is exercise-able + the e2e suite has surfaces to drive.
 *
 * State shape matches the eventual create-spokesperson payload
 * (`CreateSpokespersonInput` in `lib/api/spokespeople.ts`). Each
 * step's body will commit to its slice of the payload via the
 * `SET_FIELD` action; the Confirm step reads the assembled payload
 * and fires the existing `useCreateSpokesperson` mutation.
 *
 * Per `docs/design/CREATE_SPOKESPERSON_WIZARD.md` §"Wizard scope" and
 * `00-START-NEXT-SESSION.md`'s SESSION 128 recommendation.
 */

// ---- State ---------------------------------------------------------

interface WizardState {
  step: 1 | 2 | 3 | 4;
  // Each step commits its data here. Empty / null when not yet
  // touched. The Confirm step reads the whole bag.
  identity: {
    name: string;
    business_brief: string;
    visual_subject: string;
    tone_archetype: string;
  };
  portrait: {
    // SESSION 124 PortraitUploadResult shape — kept loose here so
    // slice 7 (Step 2 body) can plug it in without circular import
    // gymnastics.
    dataUri: string | null;
    fileName: string | null;
    mime: string | null;
    bytes: number | null;
  };
  voice: {
    // SESSION 126 VoiceCaptureValue shape, similarly loose.
    mode: "preset" | "upload" | "record" | null;
    preset: string | null;
    dataUri: string | null;
  };
}

type WizardAction =
  | { type: "SET_STEP"; step: WizardState["step"] }
  | { type: "NEXT" }
  | { type: "PREV" }
  | { type: "SET_IDENTITY"; patch: Partial<WizardState["identity"]> }
  | { type: "SET_PORTRAIT"; patch: Partial<WizardState["portrait"]> }
  | { type: "SET_VOICE"; patch: Partial<WizardState["voice"]> }
  | { type: "RESET" };

const INITIAL_STATE: WizardState = {
  step: 1,
  identity: {
    name: "",
    business_brief: "",
    visual_subject: "",
    tone_archetype: "expert", // matches model default
  },
  portrait: {
    dataUri: null,
    fileName: null,
    mime: null,
    bytes: null,
  },
  voice: {
    mode: null,
    preset: null,
    dataUri: null,
  },
};

function reducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
    case "NEXT":
      return state.step < 4
        ? { ...state, step: (state.step + 1) as WizardState["step"] }
        : state;
    case "PREV":
      return state.step > 1
        ? { ...state, step: (state.step - 1) as WizardState["step"] }
        : state;
    case "SET_IDENTITY":
      return { ...state, identity: { ...state.identity, ...action.patch } };
    case "SET_PORTRAIT":
      return { ...state, portrait: { ...state.portrait, ...action.patch } };
    case "SET_VOICE":
      return { ...state, voice: { ...state.voice, ...action.patch } };
    case "RESET":
      return INITIAL_STATE;
  }
}

// ---- Per-step gating ------------------------------------------------
//
// Returns true when the current step has enough data to advance. The
// reducer doesn't gate — the parent decides. Slices 6-9 tighten each
// rule as they wire the real bodies; today the rules are loose
// placeholders that match the scaffold's minimal inputs.

// Min business_brief length — matches the legacy form's createSchema
// (`min(8, "Give the spokesperson at least a sentence of context.")`).
const MIN_BRIEF_CHARS = 8;

function canAdvance(state: WizardState): boolean {
  switch (state.step) {
    case 1:
      // Step 1 (slice 6): name AND brief required. tone_archetype
      // has a sane default (`expert`) so we don't gate on it.
      return (
        state.identity.name.trim().length > 0 &&
        state.identity.business_brief.trim().length >= MIN_BRIEF_CHARS
      );
    case 2:
    case 3:
      // Slices 7 + 8 wire the real gates; placeholder always advances.
      return true;
    case 4:
      // Confirm: scaffolded today as a stub. Slice 9 wires the
      // actual create-spokesperson submit.
      return false;
  }
}

// ---- Wizard --------------------------------------------------------

const STEP_LABELS: Record<WizardState["step"], string> = {
  1: "Identity",
  2: "Portrait",
  3: "Voice",
  4: "Confirm",
};

export function SpokespersonWizard() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;

  const onNext = useCallback(() => dispatch({ type: "NEXT" }), []);
  const onPrev = useCallback(() => dispatch({ type: "PREV" }), []);
  const onCancel = useCallback(() => navigate("/dashboard"), [navigate]);

  return (
    <div className="reveal flex flex-col gap-10" data-testid="wizard">
      <Masthead />
      <StepIndicator current={state.step} />

      <div
        className="flex min-h-[20rem] flex-col gap-6 rounded-md border bg-card p-8 shadow-paper"
        data-testid={`wizard-step-${state.step}`}
      >
        {state.step === 1 && <Step1Identity state={state} dispatch={dispatch} />}
        {state.step === 2 && <Step2Portrait state={state} />}
        {state.step === 3 && <Step3Voice state={state} />}
        {state.step === 4 && <Step4Confirm state={state} workspaceId={workspaceId} />}
      </div>

      <Navigation
        step={state.step}
        canAdvance={canAdvance(state)}
        onNext={onNext}
        onPrev={onPrev}
        onCancel={onCancel}
      />
    </div>
  );
}

// ---- Masthead + step indicator -------------------------------------

function Masthead() {
  return (
    <header className="flex flex-col gap-3 border-b border-border pb-8">
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        Workspace
      </Link>
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        New spokesperson · wizard
      </span>
      <h1
        className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
        style={
          {
            fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
          } as React.CSSProperties
        }
      >
        Compose
        <br />
        the spokesperson.
      </h1>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
        Four steps: identity, portrait, voice, confirm. Move forward
        and back freely — your work is preserved across steps.
      </p>
    </header>
  );
}

function StepIndicator({ current }: { current: WizardState["step"] }) {
  return (
    <ol
      className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4"
      aria-label="Wizard progress"
      data-testid="wizard-step-indicator"
    >
      {([1, 2, 3, 4] as const).map((n, i) => {
        const isCurrent = n === current;
        const isDone = n < current;
        return (
          <li
            key={n}
            className={cn(
              "flex flex-1 items-center gap-3",
              i > 0 && "sm:before:mr-2 sm:before:h-px sm:before:flex-1 sm:before:bg-border",
            )}
          >
            <span
              className={cn(
                "grid h-8 w-8 place-items-center rounded-full border font-mono text-xs tabular-nums",
                isCurrent && "border-primary bg-primary text-primary-foreground",
                isDone && "border-primary bg-primary/10 text-primary",
                !isCurrent && !isDone && "border-border bg-muted text-muted-foreground",
              )}
              data-testid={`step-pill-${n}`}
              aria-current={isCurrent ? "step" : undefined}
            >
              {isDone ? <Check className="h-3 w-3" aria-hidden /> : n}
            </span>
            <span
              className={cn(
                "font-mono text-[11px] uppercase tracking-[0.22em]",
                isCurrent ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {STEP_LABELS[n]}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

// ---- Step bodies (scaffold stubs) ----------------------------------
//
// Each step renders a placeholder block + a hint of what slice will
// fill it in. Step 1 carries the one real input (name) so navigation
// state preservation is observable in the e2e suite.

function Step1Identity({
  state,
  dispatch,
}: {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
}) {
  const briefTrimmed = state.identity.business_brief.trim();
  const briefTooShort =
    briefTrimmed.length > 0 && briefTrimmed.length < MIN_BRIEF_CHARS;

  // Reactive tone suggestion — fires only when the brief is long
  // enough that the keyword scan can return something useful. The
  // hook itself debounces by way of TanStack Query's `staleTime`.
  const suggestion = useSuggestTone(state.identity.business_brief);
  const showSuggestion =
    suggestion.data != null &&
    suggestion.data !== state.identity.tone_archetype;

  return (
    <>
      <StepHeading
        kicker="Step 1 of 4"
        title="Identity"
        body="What this spokesperson is called, what they speak about, and how they sound. Drives every video the workspace renders against them."
      />

      <div className="flex flex-col gap-2">
        <Label
          htmlFor="wizard-name"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Name
        </Label>
        <p className="text-xs text-muted-foreground">
          What this spokesperson is called inside the workspace.
        </p>
        <Input
          id="wizard-name"
          type="text"
          placeholder="Casey, Coach Ben, The Bell Curve…"
          autoComplete="off"
          maxLength={120}
          value={state.identity.name}
          onChange={(e) =>
            dispatch({ type: "SET_IDENTITY", patch: { name: e.target.value } })
          }
          data-testid="wizard-name-input"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label
          htmlFor="wizard-brief"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Business brief
        </Label>
        <p className="text-xs text-muted-foreground">
          One paragraph the spokesperson speaks from. The business,
          the product, the audience, the tone.
        </p>
        <textarea
          id="wizard-brief"
          rows={5}
          maxLength={4000}
          className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          placeholder="Sells artisan bicycle bells to small bike shops. Tone: warm, opinionated, just-the-facts. Audience: shop owners under 45 who care about hand-built parts."
          value={state.identity.business_brief}
          onChange={(e) =>
            dispatch({
              type: "SET_IDENTITY",
              patch: { business_brief: e.target.value },
            })
          }
          data-testid="wizard-brief-input"
        />
        {briefTooShort && (
          <p
            className="text-xs text-destructive"
            data-testid="wizard-brief-error"
          >
            Give the spokesperson at least a sentence of context
            ({MIN_BRIEF_CHARS}+ characters).
          </p>
        )}
        {showSuggestion && (
          <ToneSuggestion
            suggested={suggestion.data!}
            onAccept={() =>
              dispatch({
                type: "SET_IDENTITY",
                patch: { tone_archetype: suggestion.data! },
              })
            }
          />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label
          htmlFor="wizard-tone"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Tone archetype
        </Label>
        <p className="text-xs text-muted-foreground">
          How the spokesperson sounds + how scripts read. Defaults to
          <strong> expert</strong> — change it if the brief suggests
          otherwise.
        </p>
        <select
          id="wizard-tone"
          value={state.identity.tone_archetype}
          onChange={(e) =>
            dispatch({
              type: "SET_IDENTITY",
              patch: { tone_archetype: e.target.value as ToneArchetype },
            })
          }
          className="h-10 rounded-md border border-border bg-card px-3 font-mono text-sm capitalize transition-colors focus:border-primary focus:outline-none"
          data-testid="wizard-tone-select"
        >
          {TONE_ARCHETYPES.map((tone) => (
            <option key={tone} value={tone} className="capitalize">
              {tone}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}

function ToneSuggestion({
  suggested,
  onAccept,
}: {
  suggested: ToneArchetype;
  onAccept: () => void;
}) {
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-sm border-l-2 border-primary/40 bg-primary/5 px-3 py-2 text-xs"
      data-testid="wizard-tone-suggestion"
    >
      <span className="flex items-center gap-2 text-foreground/80">
        <Sparkles className="h-3 w-3 text-primary" aria-hidden />
        Looks like a <strong className="capitalize">{suggested}</strong> brief.
      </span>
      <button
        type="button"
        onClick={onAccept}
        className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary transition-colors hover:text-primary/80"
        data-testid="wizard-tone-suggestion-accept"
      >
        Pick {suggested} →
      </button>
    </div>
  );
}

function Step2Portrait({ state }: { state: WizardState }) {
  return (
    <>
      <StepHeading
        kicker="Step 2 of 4"
        title="Portrait"
        body="Upload, take a picture, or generate from a visual subject. Slice 7 wires the three-mode input + the visual_subject field threading."
      />
      <ScaffoldBlock label="Portrait input" hint="Empty until slice 7." />
      <SliceCallout>
        Slice 7 lands: <code>&lt;PortraitUpload&gt;</code> (SESSION 124)
        + the new Generate tab (subject text → POST /internal/portrait/
        → preview → commit). Persists into state.portrait + writes to
        the visual_subject field on submit.
      </SliceCallout>
      <DebugState label="Wizard knows" payload={debugIdentity(state)} />
    </>
  );
}

function Step3Voice({ state }: { state: WizardState }) {
  return (
    <>
      <StepHeading
        kicker="Step 3 of 4"
        title="Voice"
        body="Preset, upload, or record. Slice 8 wires the <VoiceCapture> component from SESSION 126."
      />
      <ScaffoldBlock label="Voice input" hint="Empty until slice 8." />
      <SliceCallout>
        Slice 8 lands: <code>&lt;VoiceCapture&gt;</code> (SESSION 126)
        with the same three-tab UI used on the detail page. Submission
        defers to Confirm (Step 4) — voice is part of the
        atomically-fired create.
      </SliceCallout>
      <DebugState label="Wizard knows" payload={debugIdentity(state)} />
    </>
  );
}

function Step4Confirm({
  state,
  workspaceId,
}: {
  state: WizardState;
  workspaceId: string | undefined;
}) {
  return (
    <>
      <StepHeading
        kicker="Step 4 of 4"
        title="Confirm"
        body="Review + create. Slice 9 wires the actual POST + clone-voice orchestration."
      />
      <ScaffoldBlock
        label="Review panel"
        hint="Empty until slice 9. The Create button below stays disabled."
      />
      <SliceCallout>
        Slice 9 lands: review of all wizard state + fires
        <code> useCreateSpokesperson()</code> with the assembled
        payload + (if Step 3 picked upload/record) a follow-up
        <code> useCloneVoice()</code>. Both succeed → navigate to
        <code> /spokespeople/{"{id}"}</code>.
      </SliceCallout>
      <DebugState
        label="Assembled payload"
        payload={debugFullPayload(state, workspaceId)}
      />
    </>
  );
}

// ---- Navigation -----------------------------------------------------

function Navigation({
  step,
  canAdvance,
  onNext,
  onPrev,
  onCancel,
}: {
  step: WizardState["step"];
  canAdvance: boolean;
  onNext: () => void;
  onPrev: () => void;
  onCancel: () => void;
}) {
  const isFirst = step === 1;
  const isLast = step === 4;
  return (
    <div className="flex items-center justify-between border-t border-border pt-6">
      <button
        type="button"
        onClick={onCancel}
        className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="wizard-cancel"
      >
        Cancel
      </button>
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={isFirst}
          data-testid="wizard-prev"
        >
          Back
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={onNext}
          disabled={!canAdvance || isLast}
          data-testid="wizard-next"
          title={
            isLast
              ? "Slice 9 wires the submit"
              : canAdvance
                ? undefined
                : "Fill in the required fields to continue."
          }
        >
          {isLast ? "Create (slice 9)" : "Next"}
        </Button>
      </div>
    </div>
  );
}

// ---- Atoms ---------------------------------------------------------

function StepHeading({
  kicker,
  title,
  body,
}: {
  kicker: string;
  title: string;
  body: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        {kicker}
      </span>
      <h2 className="font-display text-3xl leading-tight tracking-tight">
        {title}
      </h2>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
        {body}
      </p>
    </div>
  );
}

function ScaffoldBlock({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border bg-muted/30 p-8 text-center">
      <span className="font-display text-lg leading-tight tracking-tight text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        {hint}
      </span>
    </div>
  );
}

function SliceCallout({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-sm border-l-2 border-primary/40 bg-primary/5 px-4 py-3 text-xs leading-relaxed text-foreground/80">
      {children}
    </p>
  );
}

function DebugState({
  label,
  payload,
}: {
  label: string;
  payload: Record<string, unknown>;
}) {
  return (
    <details className="rounded-md border border-border bg-muted/20 p-3 text-xs">
      <summary className="cursor-pointer select-none font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </summary>
      <pre
        className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-[11px] leading-relaxed text-foreground/80"
        data-testid="wizard-debug-state"
      >
        {JSON.stringify(payload, null, 2)}
      </pre>
    </details>
  );
}

// ---- Debug helpers (visible in DebugState) -------------------------

function debugIdentity(state: WizardState) {
  return {
    name: state.identity.name,
    business_brief: state.identity.business_brief,
    visual_subject: state.identity.visual_subject,
    tone_archetype: state.identity.tone_archetype,
  };
}

function debugFullPayload(
  state: WizardState,
  workspaceId: string | undefined,
) {
  return {
    workspace: workspaceId ?? "(loading)",
    ...state.identity,
    portrait: state.portrait.dataUri ? "(supplied)" : "(none)",
    voice:
      state.voice.mode === "preset"
        ? { mode: "preset", preset: state.voice.preset }
        : state.voice.mode === null
          ? "(none)"
          : { mode: state.voice.mode, dataUri: "(supplied)" },
  };
}
