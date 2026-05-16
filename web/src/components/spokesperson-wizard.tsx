import { useCallback, useReducer } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/lib/api/workspaces";
import { useSuggestTone } from "@/lib/api/prompts";
import {
  TONE_ARCHETYPES,
  useCloneVoice,
  useCreateSpokesperson,
  useSpokespersonTemplates,
  type PortraitTemplate,
  type SpokespersonTemplate,
  type ToneArchetype,
} from "@/lib/api/spokespeople";
import { WizardPortraitStep } from "@/components/wizard-portrait-step";
import { VoiceCapture, type VoiceCaptureValue } from "@/components/voice-capture";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// Default skip-target preset. When the operator skips Step 3, the
// wizard pre-fills this preset so submit can fire without a manual
// voice pick. Matches the SESSION 126 detail-page UX where `vincent`
// is the showcased default in the Preset tab dropdown.
const DEFAULT_SKIP_PRESET = "vincent";

// Tier-limit (HTTP 402) payload — mirrors the legacy form's shape so
// the wizard surfaces the same upgrade callout.
interface TierLimitPayload {
  code: string;
  message: string;
  current_tier?: string;
  suggested_tier?: string | null;
  spokespeople_used?: number;
  spokespeople_limit?: number;
}

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
    // Wizard-internal: drives Step 2's GeneratePanel default. NOT
    // sent to the create-spokesperson backend (the payload is
    // built from the resulting portrait_data_uri, not the template
    // key). Populated by Step 1 (template tile picker) or stays
    // at the default until the operator picks one on Step 2.
    visual_template: PortraitTemplate;
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
    // SESSION 126 VoiceCaptureValue shape, kept loose so navigation
    // back/forward preserves enough info to round-trip the
    // <VoiceCapture> preview. Only `preset` is populated for preset
    // mode; only `dataUri` (+ optional fileName / mime / bytes /
    // durationMs) for upload + record modes.
    mode: "preset" | "upload" | "record" | null;
    preset: string | null;
    dataUri: string | null;
    fileName: string | null;
    mime: string | null;
    bytes: number | null;
    durationMs: number | null;
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
    visual_template: "mascot", // matches GeneratePanel's prior local default
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
    fileName: null,
    mime: null,
    bytes: null,
    durationMs: null,
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
      // Step 1: name AND brief required. tone_archetype has a sane
      // default (`expert`) so we don't gate on it.
      return (
        state.identity.name.trim().length > 0 &&
        state.identity.business_brief.trim().length >= MIN_BRIEF_CHARS
      );
    case 2:
      // Step 2: a portrait must be chosen via one of the three
      // modes (Upload / Camera / Generate).
      return state.portrait.dataUri != null;
    case 3:
      // Step 3: voice is optional (the operator can Skip → pre-
      // filled default preset). Loose gate by design.
      return true;
    case 4:
      // Step 4 (SESSION 132 — slice 9): re-check the upstream gates
      // defensively. Submit fires when all of name + brief +
      // portrait are present.
      return (
        state.identity.name.trim().length > 0 &&
        state.identity.business_brief.trim().length >= MIN_BRIEF_CHARS &&
        state.portrait.dataUri != null
      );
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
  const create = useCreateSpokesperson();
  const clone = useCloneVoice();

  const onNext = useCallback(() => dispatch({ type: "NEXT" }), []);
  const onPrev = useCallback(() => dispatch({ type: "PREV" }), []);
  const onCancel = useCallback(() => navigate("/dashboard"), [navigate]);

  const onSubmit = useCallback(async () => {
    if (!workspaceId) return;
    const voicePreset =
      state.voice.mode === "preset" && state.voice.preset
        ? state.voice.preset
        : undefined;

    let createdId: string;
    try {
      const sp = await create.mutateAsync({
        workspace: workspaceId,
        name: state.identity.name.trim(),
        business_brief: state.identity.business_brief.trim(),
        visual_subject: state.identity.visual_subject.trim() || undefined,
        visual_template: state.identity.visual_template,
        tone_archetype: state.identity.tone_archetype as ToneArchetype,
        portrait_data_uri: state.portrait.dataUri ?? undefined,
        voice_preset: voicePreset,
      });
      createdId = sp.id;
    } catch {
      // mutation error surfaces via create.error — stay on Step 4
      // so the operator can read the error + retry.
      return;
    }

    // Upload / record voice → follow-up clone-voice. Failure here
    // doesn't roll back the row (the spokesperson is real + the
    // detail page's setup checklist (SESSION 126) catches the
    // missing voice). We still navigate on a clone failure.
    if (
      (state.voice.mode === "upload" || state.voice.mode === "record") &&
      state.voice.dataUri
    ) {
      try {
        await clone.mutateAsync({
          id: createdId,
          audio_data_uri: state.voice.dataUri,
        });
      } catch {
        // intentionally swallowed — see comment above
      }
    }

    navigate(`/spokespeople/${createdId}`, { replace: true });
  }, [
    workspaceId,
    state.voice.mode,
    state.voice.preset,
    state.voice.dataUri,
    state.identity.name,
    state.identity.business_brief,
    state.identity.visual_subject,
    state.identity.visual_template,
    state.identity.tone_archetype,
    state.portrait.dataUri,
    create,
    clone,
    navigate,
  ]);

  const tierLimit = extractTierLimit(create.error);
  const generalError = !tierLimit ? extractMessage(create.error) : null;

  return (
    <div className="reveal flex flex-col gap-10" data-testid="wizard">
      <Masthead />
      <StepIndicator current={state.step} />

      <div
        className="flex min-h-[20rem] flex-col gap-6 rounded-md border bg-card p-8 shadow-paper"
        data-testid={`wizard-step-${state.step}`}
      >
        {state.step === 1 && <Step1Identity state={state} dispatch={dispatch} />}
        {state.step === 2 && <Step2Portrait state={state} dispatch={dispatch} />}
        {state.step === 3 && <Step3Voice state={state} dispatch={dispatch} />}
        {state.step === 4 && (
          <Step4Confirm
            state={state}
            workspaceId={workspaceId}
            tierLimit={tierLimit}
            generalError={generalError}
          />
        )}
      </div>

      <Navigation
        step={state.step}
        canAdvance={canAdvance(state)}
        pending={create.isPending || clone.isPending}
        onNext={onNext}
        onPrev={onPrev}
        onCancel={onCancel}
        onSubmit={onSubmit}
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
        New spokesperson
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
        body="Pick a template to start from, or fill the fields yourself. You can edit anything either way."
      />

      <TemplateTilePicker state={state} dispatch={dispatch} />

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

function TemplateTilePicker({
  state,
  dispatch,
}: {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
}) {
  const templates = useSpokespersonTemplates();

  const pickTemplate = (template: SpokespersonTemplate) => {
    dispatch({
      type: "SET_IDENTITY",
      patch: {
        name: template.name,
        business_brief: template.business_brief,
        tone_archetype: template.tone_archetype,
        visual_subject: template.visual_subject,
        visual_template: template.visual_template,
      },
    });
    // Pre-fill the voice picker too — operator can change on Step 3.
    dispatch({
      type: "SET_VOICE",
      patch: {
        mode: "preset",
        preset: template.voice_preset,
        dataUri: null,
        fileName: null,
        mime: null,
        bytes: null,
        durationMs: null,
      },
    });
  };

  const clearTemplate = () => {
    // "Start from scratch" — only reset if the operator hasn't
    // already started typing. The dispatch is idempotent on empty
    // input; we keep it simple and just clear the identity bag.
    dispatch({
      type: "SET_IDENTITY",
      patch: {
        name: "",
        business_brief: "",
        tone_archetype: "expert",
        visual_subject: "",
        visual_template: "mascot",
      },
    });
    dispatch({
      type: "SET_VOICE",
      patch: {
        mode: null,
        preset: null,
        dataUri: null,
        fileName: null,
        mime: null,
        bytes: null,
        durationMs: null,
      },
    });
  };

  if (templates.isLoading || templates.isError || !templates.data) {
    // Templates fail-soft — the rest of Step 1 still works without
    // them. No need to surface an error; the operator can fill the
    // form manually.
    return null;
  }

  // A template is "active" when the name + brief + tone match it.
  // We compare on a few key fields rather than every field so that
  // editing the brief slightly doesn't lose the visual cue.
  const activeKey = templates.data.find(
    (t) =>
      t.name === state.identity.name &&
      t.tone_archetype === state.identity.tone_archetype &&
      t.business_brief === state.identity.business_brief,
  )?.key;

  return (
    <div className="flex flex-col gap-3" data-testid="wizard-template-picker">
      <Label className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        Start from a template
      </Label>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {templates.data.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => pickTemplate(t)}
            className={cn(
              "flex flex-col gap-2 rounded-md border p-4 text-left transition-colors",
              activeKey === t.key
                ? "border-primary bg-primary/5"
                : "border-border bg-card/40 hover:border-primary/40 hover:bg-card/70",
            )}
            data-testid={`wizard-template-${t.key}`}
            aria-pressed={activeKey === t.key}
          >
            <span className="font-display text-xl leading-tight tracking-tight">
              {t.name}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              {t.visual_template} · {t.tone_archetype}
            </span>
            <span className="text-xs leading-snug text-muted-foreground">
              {t.tagline}
            </span>
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={clearTemplate}
        className="self-start font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
        data-testid="wizard-template-clear"
      >
        Or start from scratch →
      </button>
    </div>
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

function Step2Portrait({
  state,
  dispatch,
}: {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
}) {
  // Compose the wizard's loose `portrait` bag into the
  // PortraitUploadResult shape the embedded component expects.
  const portraitValue = state.portrait.dataUri
    ? {
        dataUri: state.portrait.dataUri,
        fileName: state.portrait.fileName ?? "portrait.png",
        mime: state.portrait.mime ?? "image/png",
        bytes: state.portrait.bytes ?? 0,
      }
    : null;

  return (
    <>
      <StepHeading
        kicker="Step 2 of 4"
        title="Portrait"
        body="Upload an image, take a picture, or generate one from a visual subject. The chosen portrait binds a Runway avatar when this wizard finishes."
      />
      <WizardPortraitStep
        value={portraitValue}
        onChange={(value) =>
          dispatch({
            type: "SET_PORTRAIT",
            patch: value
              ? {
                  dataUri: value.dataUri,
                  fileName: value.fileName,
                  mime: value.mime,
                  bytes: value.bytes,
                }
              : {
                  dataUri: null,
                  fileName: null,
                  mime: null,
                  bytes: null,
                },
          })
        }
        onSubjectChange={(subject) =>
          dispatch({
            type: "SET_IDENTITY",
            patch: { visual_subject: subject },
          })
        }
        onTemplateChange={(t) =>
          dispatch({
            type: "SET_IDENTITY",
            patch: { visual_template: t },
          })
        }
        initialSubject={state.identity.visual_subject}
        initialTemplate={state.identity.visual_template}
      />
    </>
  );
}

function Step3Voice({
  state,
  dispatch,
}: {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
}) {
  // Bridge the wizard's loose voice bag to <VoiceCapture>'s
  // tagged-union value. When the operator navigates away + back,
  // the component re-hydrates with the same selection.
  const voiceValue = voiceBagToValue(state.voice);

  const setVoice = (value: VoiceCaptureValue | null) => {
    dispatch({
      type: "SET_VOICE",
      patch:
        value === null
          ? {
              mode: null,
              preset: null,
              dataUri: null,
              fileName: null,
              mime: null,
              bytes: null,
              durationMs: null,
            }
          : valueToVoiceBag(value),
    });
  };

  const skip = () => {
    setVoice({ mode: "preset", preset: DEFAULT_SKIP_PRESET });
    dispatch({ type: "NEXT" });
  };

  return (
    <>
      <StepHeading
        kicker="Step 3 of 4"
        title="Voice"
        body={
          "Pick a Runway preset, upload an audio clip, or record one " +
          "in-browser. Optional — skip to use the default Runway voice."
        }
      />
      <VoiceCapture
        value={voiceValue}
        onChange={setVoice}
        id="wizard-voice"
      />
      <div className="flex items-center justify-end border-t border-border/60 pt-4">
        <button
          type="button"
          onClick={skip}
          className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          data-testid="wizard-voice-skip"
        >
          Skip — use the default Runway voice
        </button>
      </div>
    </>
  );
}

// ---- Voice bag ↔ VoiceCaptureValue bridge --------------------------

function voiceBagToValue(
  bag: WizardState["voice"],
): VoiceCaptureValue | null {
  if (bag.mode === "preset" && bag.preset) {
    return { mode: "preset", preset: bag.preset };
  }
  if (bag.mode === "upload" && bag.dataUri) {
    return {
      mode: "upload",
      dataUri: bag.dataUri,
      fileName: bag.fileName ?? "voice-clip",
      bytes: bag.bytes ?? 0,
      mime: bag.mime ?? "audio/webm",
    };
  }
  if (bag.mode === "record" && bag.dataUri) {
    return {
      mode: "record",
      dataUri: bag.dataUri,
      bytes: bag.bytes ?? 0,
      mime: bag.mime ?? "audio/webm",
      durationMs: bag.durationMs ?? 0,
    };
  }
  return null;
}

function valueToVoiceBag(
  value: VoiceCaptureValue,
): WizardState["voice"] {
  if (value.mode === "preset") {
    return {
      mode: "preset",
      preset: value.preset,
      dataUri: null,
      fileName: null,
      mime: null,
      bytes: null,
      durationMs: null,
    };
  }
  if (value.mode === "upload") {
    return {
      mode: "upload",
      preset: null,
      dataUri: value.dataUri,
      fileName: value.fileName,
      mime: value.mime,
      bytes: value.bytes,
      durationMs: null,
    };
  }
  return {
    mode: "record",
    preset: null,
    dataUri: value.dataUri,
    fileName: null,
    mime: value.mime,
    bytes: value.bytes,
    durationMs: value.durationMs,
  };
}

function Step4Confirm({
  state,
  workspaceId,
  tierLimit,
  generalError,
}: {
  state: WizardState;
  workspaceId: string | undefined;
  tierLimit: TierLimitPayload | null;
  generalError: string | null;
}) {
  const voiceSummary = describeVoice(state.voice);
  return (
    <>
      <StepHeading
        kicker="Step 4 of 4"
        title="Confirm"
        body="One last look. Click Create to bind the spokesperson + fire the avatar build. You can edit anything from the detail page afterward."
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[10rem,1fr]">
        <PortraitSummary dataUri={state.portrait.dataUri} name={state.identity.name} />
        <div className="flex flex-col gap-5">
          <ReviewRow label="Name" value={state.identity.name || "—"} mono />
          <ReviewRow
            label="Business brief"
            value={state.identity.business_brief || "—"}
            wrap
          />
          <ReviewRow
            label="Tone"
            value={state.identity.tone_archetype}
            capitalize
          />
          <ReviewRow
            label="Visual subject"
            value={state.identity.visual_subject || "—"}
            wrap
            muted={!state.identity.visual_subject}
          />
          <ReviewRow label="Voice" value={voiceSummary} />
          {!workspaceId && (
            <p className="text-xs text-muted-foreground">
              Loading workspace…
            </p>
          )}
        </div>
      </div>

      {tierLimit && <TierLimitCallout payload={tierLimit} />}
      {generalError && (
        <div
          className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
          data-testid="wizard-submit-error"
        >
          {generalError}
        </div>
      )}
    </>
  );
}

function PortraitSummary({
  dataUri,
  name,
}: {
  dataUri: string | null;
  name: string;
}) {
  if (dataUri) {
    return (
      <div className="aspect-square w-full overflow-hidden rounded-md border border-border bg-muted">
        <img
          src={dataUri}
          alt=""
          className="h-full w-full object-cover"
          data-testid="wizard-confirm-portrait"
        />
      </div>
    );
  }
  const initials = deriveInitials(name);
  return (
    <div className="flex aspect-square w-full items-center justify-center rounded-md border border-dashed border-border bg-muted/40">
      <span
        className="font-display text-5xl font-light text-muted-foreground"
        style={{ fontVariationSettings: '"opsz" 144, "SOFT" 50' } as React.CSSProperties}
        aria-hidden
      >
        {initials || "?"}
      </span>
    </div>
  );
}

function ReviewRow({
  label,
  value,
  wrap,
  mono,
  capitalize,
  muted,
}: {
  label: string;
  value: string;
  wrap?: boolean;
  mono?: boolean;
  capitalize?: boolean;
  muted?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </span>
      <span
        className={cn(
          "text-sm leading-snug",
          wrap ? "whitespace-pre-wrap break-words" : "truncate",
          mono && "font-mono",
          capitalize && "capitalize",
          muted && "text-muted-foreground",
        )}
        data-testid={`wizard-confirm-${label.toLowerCase().replace(/\s+/g, "-")}`}
      >
        {value}
      </span>
    </div>
  );
}

function TierLimitCallout({ payload }: { payload: TierLimitPayload }) {
  return (
    <div
      className="flex flex-col gap-3 rounded-md border border-primary/40 bg-primary/5 p-5"
      data-testid="wizard-tier-limit-callout"
    >
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
          {payload.current_tier ?? "your plan"} · cap reached
        </span>
        <p className="font-display text-xl leading-snug tracking-tight">
          {payload.message}
        </p>
      </div>
      {payload.suggested_tier && (
        <p className="text-sm text-muted-foreground">
          Upgrade to <strong className="capitalize">{payload.suggested_tier}</strong> to
          add more. (Stripe wiring lands when credentials arrive.)
        </p>
      )}
    </div>
  );
}

function describeVoice(voice: WizardState["voice"]): string {
  if (voice.mode === "preset" && voice.preset) {
    return `Runway preset · ${voice.preset}`;
  }
  if (voice.mode === "upload" && voice.fileName) {
    return `Uploaded · ${voice.fileName}`;
  }
  if (voice.mode === "record") {
    const seconds = Math.floor((voice.durationMs ?? 0) / 1000);
    return `Recorded · ${seconds}s clip`;
  }
  return "Default Runway voice";
}

function deriveInitials(name: string): string {
  const cleaned = (name || "").trim();
  if (!cleaned) return "";
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0]!.slice(0, 2).toUpperCase();
  return (words[0]![0]! + words[words.length - 1]![0]!).toUpperCase();
}

// ---- Navigation -----------------------------------------------------

function Navigation({
  step,
  canAdvance,
  pending,
  onNext,
  onPrev,
  onCancel,
  onSubmit,
}: {
  step: WizardState["step"];
  canAdvance: boolean;
  pending: boolean;
  onNext: () => void;
  onPrev: () => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  const isFirst = step === 1;
  const isLast = step === 4;
  // On Step 4 the primary CTA fires submit; on earlier steps it
  // advances. Same testid so e2e specs can drive either with the
  // same selector.
  const primaryDisabled = pending || !canAdvance;
  const primaryLabel = isLast
    ? pending
      ? "Creating…"
      : "Create spokesperson"
    : "Next";
  return (
    <div className="flex items-center justify-between border-t border-border pt-6">
      <button
        type="button"
        onClick={onCancel}
        disabled={pending}
        className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
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
          disabled={isFirst || pending}
          data-testid="wizard-prev"
        >
          Back
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={isLast ? onSubmit : onNext}
          disabled={primaryDisabled}
          data-testid="wizard-next"
          title={
            primaryDisabled
              ? "Fill in the required fields to continue."
              : undefined
          }
        >
          {primaryLabel}
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

// ---- Error helpers (mirrors the legacy form) -----------------------

function extractTierLimit(error: unknown): TierLimitPayload | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status !== 402) return null;
  const body = error.body;
  if (
    body &&
    typeof body === "object" &&
    "code" in body &&
    typeof (body as { code: unknown }).code === "string"
  ) {
    return body as TierLimitPayload;
  }
  return null;
}

function extractMessage(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    const body = error.body as
      | { detail?: string; errors?: Array<{ message?: string }> }
      | null;
    if (body?.errors?.[0]?.message) return body.errors[0]!.message!;
    if (body?.detail) return body.detail;
    return `Request failed (${error.status}).`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Try again.";
}
