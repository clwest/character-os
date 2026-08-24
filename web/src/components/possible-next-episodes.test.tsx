/**
 * SESSION 280 v1 — "Where could this story go next?" component tests.
 *
 * Covers the operator-visible behaviors:
 *
 *  1. Enabled=false → renders nothing (Universe has zero eligible
 *     Episodes; section hides silently — no teaser, no empty state).
 *  2. Server returns empty suggestions → renders nothing (same
 *     silent-hide policy).
 *  3. Loading → skeleton + "Looking for ideas…".
 *  4. Success → three cards + [Use this] on each + "Different
 *     ideas" refresh button + intro copy.
 *  5. Error → "Couldn't load ideas right now." + [Try again]
 *     button.
 *  6. Clicking [Use this] invokes onUseSuggestion with the
 *     suggestion text verbatim.
 *  7. HARD UX invariant: rendered strings must not leak
 *     implementation vocabulary.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PossibleNextEpisodes } from "./possible-next-episodes";

// Mock the hook — the component is tested in isolation from
// react-query fetch. Test cases override the mock's return value.
const mockUseNextEpisodeSuggestions = vi.fn();

vi.mock("@/lib/api/universes", () => ({
  useNextEpisodeSuggestions: (
    universeId: string | undefined,
    opts: { enabled?: boolean; n?: number },
  ) => mockUseNextEpisodeSuggestions(universeId, opts),
}));


function renderComponent(overrides: {
  enabled?: boolean;
  onUseSuggestion?: (text: string) => void;
}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <PossibleNextEpisodes
        universeId="uni-1"
        enabled={overrides.enabled ?? true}
        onUseSuggestion={overrides.onUseSuggestion ?? vi.fn()}
      />
    </QueryClientProvider>,
  );
}


beforeEach(() => {
  mockUseNextEpisodeSuggestions.mockReset();
});


describe("PossibleNextEpisodes (SESSION 280 v1)", () => {
  it("renders nothing when the Universe has zero eligible Episodes", () => {
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    const { container } = renderComponent({ enabled: false });
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the server returns an empty suggestions list", () => {
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: {
        suggestions: [],
        substrate_summary: { episodes_used: 0, memories_used: 0, cast_count: 0 },
        generated_at: "2026-08-24T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 600 },
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });
    const { container } = renderComponent({ enabled: true });
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a loading state before the first response lands", () => {
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      isError: false,
      refetch: vi.fn(),
    });
    renderComponent({ enabled: true });
    expect(
      screen.getByTestId("possible-next-episodes-loading"),
    ).toBeInTheDocument();
    expect(screen.getByText(/looking for ideas/i)).toBeInTheDocument();
  });

  it("renders three suggestion cards + Use-this buttons + refresh + intro", () => {
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: {
        suggestions: [
          { text: "Ruby and Tyson investigate the freezer discovery together." },
          { text: "Tyson stays late to record whatever is making the noises." },
          { text: "A regular customer asks about a pastry that was never on the menu." },
        ],
        substrate_summary: { episodes_used: 10, memories_used: 0, cast_count: 2 },
        generated_at: "2026-08-24T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 600 },
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderComponent({ enabled: true });

    // Heading uses plain operator language.
    expect(
      screen.getByRole("heading", { name: /where could this story go next\?/i }),
    ).toBeInTheDocument();

    // Intro copy present.
    expect(
      screen.getByText(/pick one, ignore them, or write your own/i),
    ).toBeInTheDocument();

    // Three suggestions + three [Use this] buttons.
    expect(screen.getAllByRole("button", { name: /^use this idea:/i })).toHaveLength(3);
    expect(
      screen.getByText(/investigate the freezer discovery together/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/stays late to record whatever is making the noises/i),
    ).toBeInTheDocument();

    // Refresh affordance is called "Different ideas" (ordinary
    // language, not "regenerate").
    expect(
      screen.getByRole("button", { name: /get different ideas/i }),
    ).toBeInTheDocument();
  });

  it("clicking [Use this] hands the suggestion text to the parent verbatim", async () => {
    const onUseSuggestion = vi.fn();
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: {
        suggestions: [
          { text: "Ruby and Tyson investigate the freezer discovery together." },
          { text: "Tyson stays late to record whatever is making the noises." },
          { text: "A regular customer asks about a pastry that was never on the menu." },
        ],
        substrate_summary: { episodes_used: 10, memories_used: 0, cast_count: 2 },
        generated_at: "2026-08-24T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 600 },
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderComponent({ enabled: true, onUseSuggestion });

    const buttons = screen.getAllByRole("button", { name: /^use this idea:/i });
    await userEvent.click(buttons[1]);

    expect(onUseSuggestion).toHaveBeenCalledWith(
      "Tyson stays late to record whatever is making the noises.",
    );
  });

  it("clicking the refresh button triggers refetch", async () => {
    const refetch = vi.fn();
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: {
        suggestions: [
          { text: "one" }, { text: "two" }, { text: "three" },
        ],
        substrate_summary: { episodes_used: 5, memories_used: 0, cast_count: 2 },
        generated_at: "2026-08-24T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 600 },
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch,
    });
    renderComponent({ enabled: true });
    await userEvent.click(
      screen.getByRole("button", { name: /get different ideas/i }),
    );
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("shows an operator-friendly error state with a retry button", async () => {
    const refetch = vi.fn();
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      isError: true,
      error: new Error("boom"),
      refetch,
    });

    renderComponent({ enabled: true });

    expect(
      screen.getByTestId("possible-next-episodes-error"),
    ).toBeInTheDocument();
    expect(screen.getByText(/couldn't load ideas right now/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("never leaks implementation vocabulary in rendered strings", () => {
    mockUseNextEpisodeSuggestions.mockReturnValue({
      data: {
        suggestions: [
          { text: "Ruby and Tyson investigate together." },
          { text: "Tyson stays late." },
          { text: "A customer asks a question." },
        ],
        substrate_summary: { episodes_used: 3, memories_used: 0, cast_count: 2 },
        generated_at: "2026-08-24T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 600 },
      },
      isLoading: false,
      isFetching: false,
      isError: false,
      refetch: vi.fn(),
    });

    const { container } = renderComponent({ enabled: true });
    const text = container.textContent?.toLowerCase() ?? "";
    const banned = [
      "narrativememorykind",
      "promise kind",
      "dialogue_callback",
      "retrieval",
      "substrate",
      "provenance",
      "memory_id",
      "top_k",
      "latent thread",
      "semantic continuation",
      "llm",
      "gpt-",
    ];
    for (const word of banned) {
      expect(text).not.toContain(word);
    }
  });
});
