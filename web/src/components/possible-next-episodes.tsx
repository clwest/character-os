/**
 * SESSION 280 v1 — "Where could this story go next?"
 *
 * Operator-facing suggestion surface. Rendered on the Universe
 * Episodes list page above the "New Episode" CTA when the
 * Universe has ≥ 1 existing Episode.
 *
 * Product invariants (audit doc §37 INVARIANTS-A/B/C):
 *  - Possibilities, not obligations.
 *  - Operator remains the director.
 *  - Ignoring the section is always a valid action.
 *
 * HARD UX CONSTRAINT (audit doc §56): no implementation
 * vocabulary. Ordinary language only. If the operator has to
 * understand how Character OS works internally to make sense of
 * this UI, the UI is wrong.
 */
import { Loader2, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useNextEpisodeSuggestions } from "@/lib/api/universes";


interface PossibleNextEpisodesProps {
  universeId: string;
  /** True when the Universe has ≥ 1 non-archived Episode. When
   * false, the component renders nothing. */
  enabled: boolean;
  /** Operator picked one — parent opens the create form with
   * this text pre-filled. Nothing is created until the operator
   * submits the create form. */
  onUseSuggestion: (text: string) => void;
}

export function PossibleNextEpisodes({
  universeId,
  enabled,
  onUseSuggestion,
}: PossibleNextEpisodesProps) {
  // Gate the whole subtree — including the react-query hook
  // subscription — on the parent-supplied enabled flag. Tests
  // that mock @/lib/api/universes without stubbing this hook
  // rely on the wrapper never mounting the inner component
  // when there's nothing to build on. Also keeps the hooks-
  // rule contract intact (the inner component's hooks are
  // fully self-contained).
  if (!enabled) return null;
  return (
    <PossibleNextEpisodesInner
      universeId={universeId}
      onUseSuggestion={onUseSuggestion}
    />
  );
}


function PossibleNextEpisodesInner({
  universeId,
  onUseSuggestion,
}: Omit<PossibleNextEpisodesProps, "enabled">) {
  const q = useNextEpisodeSuggestions(universeId, { enabled: true });

  // Server returned 200 + empty list: no eligible substrate.
  // Hide silently — no teaser, no empty state.
  if (
    q.data !== undefined &&
    !q.isLoading &&
    q.data.suggestions.length === 0
  ) {
    return null;
  }

  const showLoading = q.isLoading || q.isFetching;
  const showError = q.isError && !showLoading;
  const suggestions = q.data?.suggestions ?? [];

  return (
    <section
      className="flex flex-col gap-3 rounded-lg border border-fog/30 bg-black/20 p-6"
      data-testid="possible-next-episodes"
      aria-label="Where could this story go next?"
    >
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-baseline gap-2">
          <Sparkles className="h-4 w-4 self-center text-gold" aria-hidden />
          <h2 className="font-display text-xl tracking-tight text-cream">
            Where could this story go next?
          </h2>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 text-xs text-fog transition-colors hover:text-gold disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => q.refetch()}
          disabled={showLoading}
          data-testid="possible-next-episodes-refresh"
          aria-label="Get different ideas"
        >
          <RefreshCw
            className={
              "h-3 w-3 " + (showLoading ? "animate-spin" : "")
            }
            aria-hidden
          />
          Different ideas
        </button>
      </div>

      <p className="text-xs text-fog">
        A few ideas from what has happened in this story so far.
        Pick one, ignore them, or write your own below.
      </p>

      {showLoading && !q.data && (
        <ul
          className="flex flex-col gap-2"
          data-testid="possible-next-episodes-loading"
        >
          {[0, 1, 2].map((i) => (
            <li
              key={i}
              className="h-14 animate-pulse rounded-md border border-fog/20 bg-black/30"
              aria-hidden
            />
          ))}
          <li className="text-xs italic text-fog">
            <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
            Looking for ideas…
          </li>
        </ul>
      )}

      {showError && (
        <div
          className="flex items-center justify-between gap-3 rounded-md border border-fog/30 bg-black/30 p-3 text-sm text-mist"
          data-testid="possible-next-episodes-error"
        >
          <span>Couldn't load ideas right now.</span>
          <Button
            type="button"
            variant="secondary"
            onClick={() => q.refetch()}
          >
            Try again
          </Button>
        </div>
      )}

      {!showError && suggestions.length > 0 && (
        <ul
          className="flex flex-col gap-2"
          data-testid="possible-next-episodes-list"
        >
          {suggestions.map((s, i) => (
            <li
              key={`${i}-${s.text.slice(0, 40)}`}
              className="flex items-start justify-between gap-3 rounded-md border border-fog/30 bg-black/30 p-3"
            >
              <p className="min-w-0 text-sm text-cream">{s.text}</p>
              <Button
                type="button"
                onClick={() => onUseSuggestion(s.text)}
                data-testid={`possible-next-episodes-use-${i}`}
                aria-label={`Use this idea: ${s.text}`}
              >
                Use this
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
