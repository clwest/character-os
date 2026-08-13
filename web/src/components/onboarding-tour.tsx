/**
 * Onboarding tour banner — F8 (workspace fabric arc).
 *
 * Renders at the top of /dashboard for fresh workspaces.
 * Walks the operator through the journey to a first video:
 *
 *   1. Create a spokesperson
 *   2. Add some knowledge (paste / PDF / URL)
 *   3. Pick a recipe
 *
 * The "current" step is derived from workspace state, not
 * stored progress — if the operator completes steps out of
 * order or in another tab, the banner reflects the world.
 * The "watch it render" terminal state isn't a step here
 * because by then the operator is already at
 * /compositions/<id> watching it land.
 *
 * Dismiss persists via localStorage (per Q-f-6 — v1 keeps
 * it local; no migration needed). Server-side dismissal
 * is a v1.1 concern.
 *
 * The banner hides itself when:
 *   - the operator dismissed it
 *   - all three preconditions are met (workspace is
 *     "set up")
 *
 * F0 contract rule 1 — no new persistence. The dismiss
 * flag is client-only.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Users, Library, X, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const DISMISS_KEY = "character-os-onboarding-tour-v1-dismissed";

interface TourState {
  hasSpokesperson: boolean;
  hasKnowledge: boolean;
  hasComposition: boolean;
  loading: boolean;
}

interface Step {
  index: number; // 1-indexed for display
  label: string;
  description: string;
  cta: string;
  to: string;
  testId: string;
  icon: typeof Sparkles;
}

const STEPS: Step[] = [
  {
    index: 1,
    label: "Provision your first spokesperson",
    description:
      "A spokesperson is a persistent AI representative — portrait, voice, and grounding brief — that operates across this workspace's renders and conversations.",
    cta: "Open the wizard",
    to: "/spokespeople/new",
    testId: "tour-step-spokesperson",
    icon: Users,
  },
  {
    index: 2,
    label: "Attach workspace knowledge",
    description:
      "Paste source text, upload a PDF, or attach a URL. The knowledge layer indexes the content so every render + conversation grounds in real facts instead of model defaults.",
    cta: "Attach a document",
    to: "/workspace/knowledge",
    testId: "tour-step-knowledge",
    icon: Library,
  },
  {
    index: 3,
    label: "Fire a composition",
    description:
      "Pick one of the 18 starter recipes. The render pipeline composes a script from your grounded knowledge and produces the final asset against the media engine.",
    cta: "Open recipe gallery",
    to: "/recipes",
    testId: "tour-step-recipe",
    icon: Sparkles,
  },
];

function readDismissed(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(DISMISS_KEY) === "1";
}

function writeDismissed(): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DISMISS_KEY, "1");
}

export function OnboardingTour(props: TourState) {
  const { hasSpokesperson, hasKnowledge, hasComposition, loading } = props;
  const [dismissed, setDismissed] = useState(() => readDismissed());

  // While the overview/spokespeople queries are loading, don't
  // flash the banner. The component returns null and the
  // dashboard renders cleanly without it.
  if (loading) return null;
  if (dismissed) return null;

  // If the operator already has all three milestones, they're
  // past onboarding. Hide silently.
  if (hasSpokesperson && hasKnowledge && hasComposition) return null;

  const completed = [hasSpokesperson, hasKnowledge, hasComposition];
  // Current step = first incomplete prerequisite.
  const currentIndex = completed.findIndex((v) => !v);
  const currentStep = STEPS[currentIndex] ?? null;
  if (!currentStep) return null;

  const StepIcon = currentStep.icon;
  const totalSteps = STEPS.length;

  function handleDismiss() {
    writeDismissed();
    setDismissed(true);
  }

  return (
    <section
      className="reveal flex flex-col gap-4 rounded-md border bg-card p-6 shadow-paper md:flex-row md:items-start md:gap-6"
      data-testid="onboarding-tour"
      style={{ "--reveal-delay": "0.01s" } as React.CSSProperties}
    >
      <div className="flex items-start gap-3 md:flex-1">
        <div
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border bg-muted/50"
          aria-hidden
        >
          <StepIcon className="h-5 w-5 text-foreground/80" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Get started · Step {currentStep.index} of {totalSteps}
            </span>
            <ProgressDots step={currentStep.index} total={totalSteps} />
          </div>
          <h2 className="font-display text-xl leading-tight tracking-tight">
            {currentStep.label}
          </h2>
          <p className="text-sm text-muted-foreground">{currentStep.description}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 md:flex-col md:items-end">
        <Button asChild size="lg">
          <Link to={currentStep.to} data-testid={currentStep.testId}>
            {currentStep.cta}
            <ChevronRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
        <button
          type="button"
          onClick={handleDismiss}
          className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
          data-testid="onboarding-tour-dismiss"
        >
          <X className="h-3 w-3" />
          Skip
        </button>
      </div>
    </section>
  );
}

function ProgressDots({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center gap-1" aria-hidden>
      {Array.from({ length: total }).map((_, i) => {
        const filled = i + 1 <= step;
        return (
          <span
            key={i}
            className={
              "block h-1.5 w-4 rounded-full transition-colors " +
              (filled ? "bg-foreground" : "bg-muted")
            }
          />
        );
      })}
    </div>
  );
}
