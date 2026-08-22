import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, MessageCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSpokesperson } from "@/lib/api/spokespeople";
import { buildKnowledgeHandoffPath } from "@/lib/knowledge/handoff";

/**
 * Post-creation welcome screen.
 *
 * Interstitial that fires after the wizard's Confirm step succeeds.
 * Was previously silent — the wizard dropped operators onto the
 * spokesperson detail page with no acknowledgment that they'd just
 * made an AI spokesperson. First-time customers had no clear "next
 * step" prompt and often bounced before ever adding knowledge.
 *
 * This screen frames the moment: what the spokesperson knows so far,
 * what they still need, and the single most important next action.
 * The primary CTA is teaching them about the business (knowledge);
 * secondary is a low-friction "meet them first" for the curious;
 * tertiary is a skip for people who want to explore on their own.
 */
export function SpokespersonWelcomeRoute() {
  const { id } = useParams<{ id: string }>();
  const sp = useSpokesperson(id);

  if (sp.isLoading) return <WelcomeSkeleton />;
  if (sp.isError || !sp.data)
    return <WelcomeError message="Spokesperson not found." />;

  const spokesperson = sp.data;
  const name = spokesperson.name || "Your spokesperson";
  const portraitSrc =
    spokesperson.portrait_path && spokesperson.portrait_path.length > 0
      ? spokesperson.portrait_path
      : null;

  return (
    <div
      className="reveal mx-auto flex max-w-3xl flex-col gap-10 py-16"
      data-testid="spokesperson-welcome"
    >
      <div className="flex flex-col gap-4">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
          § — Setup · Step 2 of 4
        </span>
        <h1
          className="font-display text-5xl leading-[0.95] tracking-tight text-cream md:text-6xl"
          style={
            {
              fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1',
            } as React.CSSProperties
          }
          data-testid="welcome-heading"
        >
          Meet <span className="italic gold-text">{name}.</span>
        </h1>
        <div
          className="hairline-gold h-px w-full"
          aria-hidden="true"
        />
      </div>

      <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-start">
        <div
          className="aspect-square w-40 shrink-0 overflow-hidden rounded-md border border-luxe bg-muted shadow-lg sm:w-48"
          data-testid="welcome-portrait"
        >
          {portraitSrc ? (
            <img
              src={portraitSrc}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center font-display text-4xl text-fog">
              {initialFor(name)}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <p className="text-base leading-relaxed text-mist">
            {name} is ready to work. Here's what they know so far:
          </p>
          <ul className="flex flex-col gap-2 text-sm leading-relaxed text-mist">
            <li className="flex items-start gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
              <span>Their name and personality</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
              <span>The brief you gave them about your business</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
              <span>How to sound like themself, in their own voice</span>
            </li>
          </ul>
          <p className="text-base leading-relaxed text-mist">
            That's a solid starting point — but {name} doesn't know your{" "}
            <span className="italic text-cream">specifics</span> yet. Your menu,
            your pricing, your policies, the details a real customer would ask
            about. That's the next step, and it's what turns {name} from a
            polished demo into something that actually represents your business.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-luxe pt-8">
        {/* SESSION 277 Slice 12 (Q-277-12) — Preserve the character
            onboarding context (universe + spokesperson + origin) so
            `/workspace/knowledge` can render an explicit World-vs-
            character audience decision instead of the generic scope
            picker. Query params are the persistence mechanism (see
            Slice 11 §217): stateless, refresh-safe, deep-linkable.
            When `spokesperson.universe` is null (legacy teammate),
            the universe param is omitted and the destination falls
            back to the generic flow. */}
        <Button
          asChild
          size="lg"
          className="w-full justify-between text-base"
          data-testid="welcome-teach-cta"
        >
          <Link
            to={buildKnowledgeHandoffPath({
              universeId: spokesperson.universe,
              spokespersonId: spokesperson.id,
              origin: "character_welcome",
            })}
          >
            <span className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Teach {name} about your business
            </span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
        <Button
          asChild
          size="lg"
          variant="outline"
          className="w-full justify-start gap-2 text-base"
          data-testid="welcome-talk-cta"
        >
          <Link to={`/spokespeople/${spokesperson.id}/talk`}>
            <MessageCircle className="h-4 w-4" />
            Say hi to {name} first
          </Link>
        </Button>
        <div className="pt-2">
          <SkipLink id={spokesperson.id} />
        </div>
      </div>

      <p className="text-xs leading-relaxed text-fog">
        Heads up: if you talk to {name} before adding knowledge, they'll answer
        generically — small talk about your industry, not specifics about your
        business. That's expected. Come back and teach them when you're ready,
        and the difference will be night and day.
      </p>
    </div>
  );
}

// ---- Sub-components ------------------------------------------------

function SkipLink({ id }: { id: string }) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate(`/spokespeople/${id}`, { replace: true })}
      className="font-mono text-xs uppercase tracking-[0.22em] text-fog transition-colors hover:text-cream"
      data-testid="welcome-skip"
    >
      Skip for now →
    </button>
  );
}

function WelcomeSkeleton() {
  return (
    <div
      className="mx-auto flex max-w-3xl flex-col gap-6 py-16"
      data-testid="welcome-skeleton"
    >
      <div className="h-4 w-40 animate-pulse rounded bg-muted" />
      <div className="h-16 w-2/3 animate-pulse rounded bg-muted" />
      <div className="h-40 w-full animate-pulse rounded bg-muted" />
    </div>
  );
}

function WelcomeError({ message }: { message: string }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 py-16">
      <p className="text-sm text-destructive" data-testid="welcome-error">
        {message}
      </p>
      <Link
        to="/dashboard"
        className="font-mono text-xs uppercase tracking-[0.22em] text-fog transition-colors hover:text-cream"
      >
        ← Back to workspace
      </Link>
    </div>
  );
}

function initialFor(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  return trimmed.charAt(0).toUpperCase();
}
