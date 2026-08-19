/**
 * SESSION 269 §12 — Episode Create-form cast picker + Episode
 * detail scene-CTA branching for one-character Episodes.
 *
 * Companion to `episode-composition-workflow.test.tsx` (SESSION 262).
 * Scope is intentionally narrow — this file only covers the §12
 * additions:
 *
 *  1. Create-form renders a cast picker seeded from the Universe
 *     roster (filtered to same-Universe teammates).
 *  2. Selecting one character sends ``cast_ids`` in the create
 *     payload — the empty-cast footgun that produced Episode
 *     91a63409 in §11 is closed on the wire.
 *  3. Selecting two characters sends both.
 *  4. Submitting with zero selections omits ``cast_ids`` and
 *     produces a draft Episode (byte-identical to pre-§12).
 *  5. Episode detail: cast=0 shows the "add cast" hint and NO
 *     scene CTA (silent fall-through is blocked).
 *  6. Episode detail: cast=1 shows the "New solo scene" CTA
 *     pointing to the talking_head recipe with ?episode=<id>.
 *  7. Episode detail: cast=2 shows the "New dialogue scene" CTA
 *     (existing behaviour, preserved as a regression check).
 */
import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { Episode } from "@/lib/api/episodes";
import type { Spokesperson } from "@/lib/api/spokespeople";
import { UniverseEpisodesRoute } from "@/routes/workspace/universes.$id.episodes";
import { EpisodeDetailRoute } from "@/routes/workspace/episodes.$id";

// ---- Fixtures ----------------------------------------------------

const UNIVERSE_ID = "u-workshop";
const OTHER_UNIVERSE_ID = "u-bakery";

const PATCH: Spokesperson = {
  id: "sp-patch",
  workspace: "ws-1",
  universe: UNIVERSE_ID,
  name: "Patch",
  runway_avatar_id: "av-patch",
  portrait_path: "https://fake/patch.png",
} as unknown as Spokesperson;

const RIVET: Spokesperson = {
  id: "sp-rivet",
  workspace: "ws-1",
  universe: UNIVERSE_ID,
  name: "Rivet",
  runway_avatar_id: "av-rivet",
  portrait_path: "https://fake/rivet.png",
} as unknown as Spokesperson;

const BAKER: Spokesperson = {
  id: "sp-baker",
  workspace: "ws-1",
  universe: OTHER_UNIVERSE_ID,
  name: "Baker",
  runway_avatar_id: "av-baker",
  portrait_path: "https://fake/baker.png",
} as unknown as Spokesperson;

const EMPTY_EPISODE: Episode = {
  id: "ep-empty",
  universe: UNIVERSE_ID,
  universe_name: "Workshop",
  title: "Empty draft",
  operator_topic: "Just a draft.",
  cast: [],
  composition_count: 0,
  archived_at: null,
  created_by: null,
  created_at: "2026-08-19T00:00:00Z",
  updated_at: "2026-08-19T00:00:00Z",
} as unknown as Episode;

const SOLO_EPISODE: Episode = {
  id: "ep-solo",
  universe: UNIVERSE_ID,
  universe_name: "Workshop",
  title: "Solo scene",
  operator_topic: "Patch cleans a corner.",
  cast: [{ id: PATCH.id, name: PATCH.name }],
  composition_count: 0,
  archived_at: null,
  created_by: null,
  created_at: "2026-08-19T00:00:00Z",
  updated_at: "2026-08-19T00:00:00Z",
} as unknown as Episode;

const DIALOGUE_EPISODE: Episode = {
  id: "ep-dialogue",
  universe: UNIVERSE_ID,
  universe_name: "Workshop",
  title: "Two-hander",
  operator_topic: "Patch and Rivet talk.",
  cast: [
    { id: PATCH.id, name: PATCH.name },
    { id: RIVET.id, name: RIVET.name },
  ],
  composition_count: 0,
  archived_at: null,
  created_by: null,
  created_at: "2026-08-19T00:00:00Z",
  updated_at: "2026-08-19T00:00:00Z",
} as unknown as Episode;

// ---- Mocks -------------------------------------------------------

const mockCreateEpisode = vi.fn<[unknown], Promise<Episode>>();
let currentEpisode: Episode = EMPTY_EPISODE;

vi.mock("@/lib/api/universes", () => ({
  useUniverse: (_id: string | undefined) => ({
    data: { id: UNIVERSE_ID, name: "Workshop" },
    isLoading: false,
  }),
}));

vi.mock("@/lib/api/episodes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/episodes")>(
    "@/lib/api/episodes",
  );
  return {
    ...actual,
    useEpisodes: (_universeId: string | undefined) => ({
      data: [],
      isLoading: false,
    }),
    useCreateEpisode: (_universeId: string | undefined) => ({
      mutateAsync: mockCreateEpisode,
      isPending: false,
    }),
    useEpisode: (id: string | undefined) => ({
      data: id ? currentEpisode : undefined,
      isLoading: false,
      isError: false,
      error: null,
    }),
    useUpdateEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useArchiveEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUnarchiveEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useHardDeleteEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useAddCastMember: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRemoveCastMember: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/api/spokespeople")
  >("@/lib/api/spokespeople");
  return {
    ...actual,
    useSpokespeople: () => ({
      data: [PATCH, RIVET, BAKER],
      isLoading: false,
    }),
  };
});

vi.mock("@/lib/api/recipes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/recipes")>(
    "@/lib/api/recipes",
  );
  return {
    ...actual,
    useCompositionsForEpisode: (_id: string | undefined) => ({
      data: [],
      isLoading: false,
      error: null,
    }),
  };
});

// ---- Render helpers ---------------------------------------------

function renderCreateForm() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter
        initialEntries={[`/workspace/universes/${UNIVERSE_ID}/episodes`]}
      >
        <Routes>
          <Route
            path="/workspace/universes/:id/episodes"
            element={<UniverseEpisodesRoute />}
          />
          <Route
            path="/workspace/episodes/:id"
            element={<div data-testid="episode-detail-stub" />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderEpisodeDetail(episodeId: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/workspace/episodes/${episodeId}`]}>
        <Routes>
          <Route
            path="/workspace/episodes/:id"
            element={<EpisodeDetailRoute />}
          />
          <Route
            path="/workspace/universes/:id/episodes"
            element={<div>list</div>}
          />
          <Route
            path="/recipes/:kind"
            element={<div data-testid="recipe-stub" />}
          />
          <Route path="/recipes" element={<div data-testid="recipes-gallery" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockCreateEpisode.mockReset();
  mockCreateEpisode.mockResolvedValue(EMPTY_EPISODE);
  currentEpisode = EMPTY_EPISODE;
});

// ==================================================================
// Create-form cast picker
// ==================================================================

describe("Create Episode form — cast picker (SESSION 269 §12)", () => {
  it("1. renders picker seeded from same-Universe teammates only", async () => {
    const user = userEvent.setup();
    renderCreateForm();

    await user.click(screen.getByRole("button", { name: /new episode/i }));

    const picker = await screen.findByTestId("episode-create-cast-picker");
    expect(
      picker.querySelector(`[data-testid="episode-create-cast-toggle-${PATCH.id}"]`),
    ).not.toBeNull();
    expect(
      picker.querySelector(`[data-testid="episode-create-cast-toggle-${RIVET.id}"]`),
    ).not.toBeNull();
    // Baker is in a different Universe — must NOT appear.
    expect(
      picker.querySelector(`[data-testid="episode-create-cast-toggle-${BAKER.id}"]`),
    ).toBeNull();
  });

  it("2. selecting one character sends cast_ids=[<uuid>] in payload", async () => {
    const user = userEvent.setup();
    renderCreateForm();

    await user.click(screen.getByRole("button", { name: /new episode/i }));
    const topic = screen.getByLabelText(/operator topic/i);
    await user.type(topic, "Patch cleans a corner.");
    await user.click(
      screen.getByTestId(`episode-create-cast-toggle-${PATCH.id}`),
    );
    await user.click(screen.getByRole("button", { name: /^create episode$/i }));

    expect(mockCreateEpisode).toHaveBeenCalledTimes(1);
    const payload = mockCreateEpisode.mock.calls[0][0] as {
      cast_ids?: string[];
    };
    expect(payload.cast_ids).toEqual([PATCH.id]);
  });

  it("3. selecting two characters sends both cast_ids preserving picker order", async () => {
    const user = userEvent.setup();
    renderCreateForm();

    await user.click(screen.getByRole("button", { name: /new episode/i }));
    await user.type(
      screen.getByLabelText(/operator topic/i),
      "Two-hander.",
    );
    // Click order: Rivet first, then Patch. The form's outgoing
    // order should still be the eligibleTeammates list order
    // (matches the API's spokespeople list order which the recipe
    // form later relies on as authoritative first-primary seed).
    await user.click(
      screen.getByTestId(`episode-create-cast-toggle-${RIVET.id}`),
    );
    await user.click(
      screen.getByTestId(`episode-create-cast-toggle-${PATCH.id}`),
    );
    await user.click(screen.getByRole("button", { name: /^create episode$/i }));

    const payload = mockCreateEpisode.mock.calls[0][0] as {
      cast_ids?: string[];
    };
    // Order follows eligibleTeammates iteration (Patch, Rivet)
    // regardless of click order — see the form's cast_ids
    // construction comment.
    expect(payload.cast_ids).toEqual([PATCH.id, RIVET.id]);
  });

  it("4. zero-cast submission omits cast_ids (byte-identical to pre-§12)", async () => {
    const user = userEvent.setup();
    renderCreateForm();

    await user.click(screen.getByRole("button", { name: /new episode/i }));
    await user.type(
      screen.getByLabelText(/operator topic/i),
      "Blank slate.",
    );
    await user.click(screen.getByRole("button", { name: /^create episode$/i }));

    const payload = mockCreateEpisode.mock.calls[0][0] as {
      cast_ids?: string[];
    };
    expect(payload.cast_ids).toBeUndefined();
  });
});

// ==================================================================
// Episode detail scene-CTA branching
// ==================================================================

describe("Episode detail — scene CTA branching (SESSION 269 §12)", () => {
  it("5. cast=0 shows the add-cast hint and NO scene CTA", () => {
    currentEpisode = EMPTY_EPISODE;
    renderEpisodeDetail(EMPTY_EPISODE.id);

    expect(screen.getByTestId("episode-cast-empty-hint")).toBeTruthy();
    expect(screen.queryByTestId("episode-render-solo-cta")).toBeNull();
    expect(screen.queryByTestId("episode-render-dialogue-cta")).toBeNull();
  });

  it("6. cast=1 shows the New solo scene CTA pointing to talking_head", () => {
    currentEpisode = SOLO_EPISODE;
    renderEpisodeDetail(SOLO_EPISODE.id);

    const solo = screen.getByTestId("episode-render-solo-cta");
    expect(solo).toBeTruthy();
    // Button component uses asChild — the testid lands on the
    // <a> element itself. Look for href on the testid element or
    // any descendant, whichever the shadcn Button variant renders.
    const link =
      solo.tagName === "A"
        ? (solo as HTMLAnchorElement)
        : (solo.querySelector("a") as HTMLAnchorElement);
    expect(link.getAttribute("href")).toBe(
      `/recipes/talking_head?episode=${SOLO_EPISODE.id}`,
    );
    expect(screen.queryByTestId("episode-render-dialogue-cta")).toBeNull();
  });

  it("7. cast=2 shows the New dialogue scene CTA (regression check)", () => {
    currentEpisode = DIALOGUE_EPISODE;
    renderEpisodeDetail(DIALOGUE_EPISODE.id);

    const dialogue = screen.getByTestId("episode-render-dialogue-cta");
    expect(dialogue).toBeTruthy();
    const link =
      dialogue.tagName === "A"
        ? (dialogue as HTMLAnchorElement)
        : (dialogue.querySelector("a") as HTMLAnchorElement);
    expect(link.getAttribute("href")).toBe(
      `/recipes/dialogue_scene?episode=${DIALOGUE_EPISODE.id}`,
    );
    expect(screen.queryByTestId("episode-render-solo-cta")).toBeNull();
  });
});
