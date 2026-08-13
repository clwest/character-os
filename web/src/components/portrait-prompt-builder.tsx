import { useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/**
 * Portrait prompt builder — guided form that assembles the free-text
 * subject + style inputs on the wizard's Generate tab. Users pick a
 * Kind (Human/Animal/Robotic/Other), fill in a few axes, and hit
 * "Compose prompt" — the parent populates the existing subject +
 * style state, which the user can still edit before generating.
 *
 * The free-text fields aren't replaced — they remain the escape
 * hatch. The builder is the front door.
 */

export type SubjectKind = "human" | "animal" | "robotic" | "other";

const KIND_OPTIONS: Array<{ value: SubjectKind; label: string }> = [
  { value: "human", label: "Human" },
  { value: "animal", label: "Animal" },
  { value: "robotic", label: "Robotic" },
  { value: "other", label: "Other" },
];

const SUBJECT_PLACEHOLDERS: Record<SubjectKind, string> = {
  human: "founder in her 40s, warm eyes",
  animal: "three-toed sloth",
  robotic: "boxy delivery robot with round eyes",
  other: "art deco brand mascot",
};

const DETAILS_PLACEHOLDERS: Record<SubjectKind, string> = {
  human: "oversized olive hoodie, silver hoop earrings",
  animal: "oversized olive hoodie, wire-rim glasses",
  robotic: "matte olive chassis with warm LED accents",
  other: "art deco geometric detailing",
};

const SETTING_PLACEHOLDERS: Record<SubjectKind, string> = {
  human: "warm podcast studio with soft bookshelves behind",
  animal: "mossy forest clearing at golden hour",
  robotic: "clean minimalist lab with warm ambient light",
  other: "art deco stage with soft gold accents",
};

const SETTING_PRESETS: Record<SubjectKind, readonly string[]> = {
  human: [
    "warm podcast studio, bookshelves behind",
    "cozy coffee shop window seat",
    "modern loft office at golden hour",
    "brick-wall creative studio",
    "outdoor café patio",
  ],
  animal: [
    "mossy forest clearing at golden hour",
    "mountain river with pine trees",
    "sunny meadow with wildflowers",
    "cozy cabin porch",
    "snowy woodland trail",
  ],
  robotic: [
    "clean minimalist lab, warm ambient light",
    "urban rooftop at dusk",
    "futuristic workshop with neon accents",
    "sunlit atrium with tall windows",
    "quiet server room glow",
  ],
  other: [
    "art deco stage with gold accents",
    "abstract geometric backdrop",
    "soft gradient studio",
    "vintage library with warm lamps",
    "cinematic sunset skyline",
  ],
};

const STYLE_OPTIONS = [
  "Photorealistic",
  "Editorial illustration",
  "Oil painting",
  "Pixar-style 3D",
  "Anime",
  "Watercolor",
  "Comic book",
] as const;

const FRAMING_OPTIONS = [
  "Medium close-up, eye contact",
  "Close-up portrait",
  "Medium shot",
  "Three-quarter shot",
  "Wide shot",
] as const;

const LIGHTING_OPTIONS = [
  "Soft cinematic studio",
  "Golden hour",
  "Overhead studio",
  "Moody low-key",
  "Natural window light",
] as const;

const EXPRESSION_OPTIONS = [
  "Warm smile",
  "Neutral",
  "Confident",
  "Curious",
  "Focused",
  "Playful",
] as const;

// Baked-in constraints that push OpenAI's output toward Runway's
// avatar-creation sweet spot. Runway's `POST /v1/avatars` treats the
// input image as a *reference*, not a source — cleaner face-forward
// portraits stay closer to the reference when Runway generates the
// avatar. Anchoring composition + face fidelity here means the user's
// choice of style/setting can't push the reference off the ideal shape.
const QUALITY_MODIFIERS =
  "clean head-and-shoulders portrait, centered composition, front-facing, " +
  "clear facial features, natural proportions, highly detailed, " +
  "sharp focus on face, shallow depth of field";

interface PortraitPromptBuilderProps {
  onCompose: (subject: string, style: string) => void;
  className?: string;
}

export function PortraitPromptBuilder({
  onCompose,
  className,
}: PortraitPromptBuilderProps) {
  const [kind, setKind] = useState<SubjectKind>("human");
  const [subject, setSubject] = useState("");
  const [role, setRole] = useState("");
  const [personality, setPersonality] = useState("");
  const [details, setDetails] = useState("");
  const [setting, setSetting] = useState("");
  const [style, setStyle] = useState<string>(STYLE_OPTIONS[0]);
  const [framing, setFraming] = useState<string>(FRAMING_OPTIONS[0]);
  const [lighting, setLighting] = useState<string>(LIGHTING_OPTIONS[0]);
  const [expression, setExpression] = useState<string>(EXPRESSION_OPTIONS[0]);

  const handleCompose = () => {
    const subjectPrompt = buildSubjectPrompt({
      kind,
      subject: subject.trim(),
      role: role.trim(),
      personality: personality.trim(),
      details: details.trim(),
      setting: setting.trim(),
      framing,
      expression,
    });
    const stylePrompt = buildStylePrompt({ style, lighting });
    onCompose(subjectPrompt, stylePrompt);
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-md border border-primary/30 bg-primary/5 p-4",
        className,
      )}
      data-testid="portrait-prompt-builder"
    >
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-primary">
          Guided
        </span>
        <span className="font-display text-base leading-tight tracking-tight">
          Compose from parts
        </span>
        <span className="text-xs text-muted-foreground">
          Fill in what you know. We'll write the prompt for you — you can
          still edit it below before generating.
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Kind
        </Label>
        <div
          className="flex flex-wrap gap-2"
          role="radiogroup"
          aria-label="Subject kind"
        >
          {KIND_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={kind === opt.value}
              onClick={() => setKind(opt.value)}
              className={cn(
                "rounded-md border px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition-colors",
                kind === opt.value
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card hover:border-primary/60",
              )}
              data-testid={`builder-kind-${opt.value}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TextAxis
          label="Subject"
          id="builder-subject"
          placeholder={SUBJECT_PLACEHOLDERS[kind]}
          value={subject}
          onChange={setSubject}
        />
        <TextAxis
          label="Role"
          id="builder-role"
          placeholder="AI assistant, coach, interviewer…"
          value={role}
          onChange={setRole}
        />
        <TextAxis
          label="Personality"
          id="builder-personality"
          placeholder="thoughtful, empathetic, curious"
          value={personality}
          onChange={setPersonality}
        />
        <TextAxis
          label={kind === "robotic" ? "Design details" : "Clothing / details"}
          id="builder-details"
          placeholder={DETAILS_PLACEHOLDERS[kind]}
          value={details}
          onChange={setDetails}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label
          htmlFor="builder-setting"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Setting / background
        </Label>
        <Input
          id="builder-setting"
          type="text"
          placeholder={SETTING_PLACEHOLDERS[kind]}
          value={setting}
          onChange={(e) => setSetting(e.target.value)}
          maxLength={200}
          data-testid="builder-setting"
        />
        <div
          className="flex flex-wrap gap-1.5 pt-1"
          data-testid="builder-setting-presets"
        >
          {SETTING_PRESETS[kind].map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => setSetting(preset)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-[11px] transition-colors",
                setting === preset
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border bg-card/40 text-muted-foreground hover:border-primary/40 hover:text-foreground",
              )}
              data-testid={`builder-setting-preset-${preset.slice(0, 20).replace(/\W+/g, "-")}`}
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectAxis
          label="Style"
          id="builder-style"
          options={STYLE_OPTIONS}
          value={style}
          onChange={setStyle}
        />
        <SelectAxis
          label="Framing"
          id="builder-framing"
          options={FRAMING_OPTIONS}
          value={framing}
          onChange={setFraming}
        />
        <SelectAxis
          label="Lighting"
          id="builder-lighting"
          options={LIGHTING_OPTIONS}
          value={lighting}
          onChange={setLighting}
        />
        <SelectAxis
          label="Expression"
          id="builder-expression"
          options={EXPRESSION_OPTIONS}
          value={expression}
          onChange={setExpression}
        />
      </div>

      <Button
        type="button"
        variant="outline"
        onClick={handleCompose}
        data-testid="builder-compose"
        className="self-start"
      >
        <Sparkles className="mr-1.5 h-4 w-4" />
        Compose prompt
      </Button>
    </div>
  );
}

function TextAxis({
  label,
  id,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  id: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label
        htmlFor={id}
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
      >
        {label}
      </Label>
      <Input
        id={id}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={200}
        data-testid={id}
      />
    </div>
  );
}

function SelectAxis({
  label,
  id,
  options,
  value,
  onChange,
}: {
  label: string;
  id: string;
  options: readonly string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label
        htmlFor={id}
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
      >
        {label}
      </Label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 rounded-md border border-border bg-card px-3 font-mono text-sm transition-colors focus:border-primary focus:outline-none"
        data-testid={id}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}

function buildSubjectPrompt(input: {
  kind: SubjectKind;
  subject: string;
  role: string;
  personality: string;
  details: string;
  setting: string;
  framing: string;
  expression: string;
}): string {
  const parts: string[] = [];

  const core = buildCorePhrase(
    input.kind,
    input.subject,
    input.role,
    input.personality,
  );
  if (core) parts.push(core);

  if (input.details) {
    parts.push(
      input.kind === "robotic"
        ? `Design: ${input.details}`
        : `Wearing ${input.details}`,
    );
  }
  if (input.setting) parts.push(`Set against ${input.setting}`);
  if (input.framing) parts.push(input.framing);
  if (input.expression) parts.push(`${input.expression} expression`);

  return parts.join(". ");
}

function buildCorePhrase(
  kind: SubjectKind,
  subject: string,
  role: string,
  personality: string,
): string {
  const s = subject || defaultSubject(kind);
  const personalityPhrase = personality ? `${personality} ` : "";
  if (kind === "robotic") {
    return role
      ? `A ${personalityPhrase}${s} robot serving as ${role}`
      : `A ${personalityPhrase}${s} robot`;
  }
  if (kind === "animal") {
    return role
      ? `A ${personalityPhrase}${s} playing the role of ${role}`
      : `A ${personalityPhrase}${s}`;
  }
  return role
    ? `A ${personalityPhrase}${s} as a ${role}`
    : `A ${personalityPhrase}${s}`;
}

function defaultSubject(kind: SubjectKind): string {
  switch (kind) {
    case "human":
      return "person";
    case "animal":
      return "animal character";
    case "robotic":
      return "friendly";
    case "other":
      return "character";
  }
}

function buildStylePrompt(input: { style: string; lighting: string }): string {
  return [input.style, input.lighting, QUALITY_MODIFIERS]
    .filter(Boolean)
    .join(", ")
    .toLowerCase();
}
