/**
 * SESSION 264 dogfood-correction tests for the Remember-this /
 * Story-history creator UX.
 *
 * Covers the eleven invariants listed in the SESSION 264 UX
 * correction brief (Test Requirements section):
 *
 *   1.  "Kind" is not visible in the creator flow.
 *   2.  "Weight" is not visible.
 *   3.  Internal submission still produces the default event kind.
 *   4.  Internal submission still produces peripheral/default weight.
 *   5.  Whole-cast availability radio ("In any future scene",
 *       post-SESSION-267) is selected by default.
 *   6.  Default whole-cast behavior maps to empty witnessed_by[].
 *   7.  Selecting the "When any of these characters are
 *       present…" radio reveals the eligible cast.
 *   8.  Narrow witness selection persists into the POST body.
 *   9.  "Remember this" requires an explicit click by the operator.
 *  10.  Existing remembered rows re-appear after creation.
 *  11.  The creator UI never touches canon (/api/knowledge/*).
 *
 * Notes:
 *
 * - Kind/weight are omitted from the POST body by the UI. The
 *   backend serializer supplies event/peripheral defaults, which
 *   is separately proven by the backend regression test at
 *   apps/memory/tests/test_narrative_memory.py (dogfood
 *   correction row); this file only asserts what the SPA
 *   sends.
 * - No provider calls. The `fetch` global is spied and returns
 *   canned Episode + memory list + promote payloads.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { NarrativeMemoryPromotePanel } from "./narrative-memory-panels";

const EPISODE_ID = "ep-1";
const COMPOSITION_ID = "comp-1";
const WORKSPACE_ID = "ws-1";
const UNIVERSE_ID = "uni-1";

const PATCH = { id: "tm-patch", name: "Patch" };
const RIVET = { id: "tm-rivet", name: "Rivet" };

const EPISODE_PAYLOAD = {
  id: EPISODE_ID,
  universe: UNIVERSE_ID,
  universe_name: "Workshop",
  title: "AI took over the lab",
  operator_topic: "The printer decided to make Patch royalty.",
  cast: [PATCH, RIVET],
  composition_count: 1,
  archived_at: null,
  created_by: 1,
  created_at: "2026-08-18T00:00:00Z",
  updated_at: "2026-08-18T00:00:00Z",
};

function makeMemory(overrides: Record<string, unknown> = {}) {
  return {
    id: "mem-existing",
    episode: EPISODE_ID,
    episode_title: "AI took over the lab",
    source_composition: COMPOSITION_ID,
    source_composition_name: "AI-lab v1",
    workspace: WORKSPACE_ID,
    universe: UNIVERSE_ID,
    universe_name: "Workshop",
    kind: "event",
    body: "Patch connected an AI agent to the workshop tools.",
    witnessed_by: [],
    weight: "peripheral",
    status: "remembered",
    supersedes: null,
    superseded_at: null,
    superseded_reason: "",
    archived_at: null,
    promoted_by: 1,
    created_at: "2026-08-18T00:00:00Z",
    updated_at: "2026-08-18T00:00:00Z",
    is_current: true,
    ...overrides,
  };
}

interface FetchLog {
  method: string;
  url: string;
  body: unknown;
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

function renderPanel() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NarrativeMemoryPromotePanel
          compositionId={COMPOSITION_ID}
          episodeId={EPISODE_ID}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SESSION 264 dogfood UX — Remember this panel", () => {
  let fetchLog: FetchLog[];
  // Memories the mocked backend "has" — the promote handler
  // appends here and the list handler returns from here.
  let memoryStore: ReturnType<typeof makeMemory>[];

  beforeEach(() => {
    fetchLog = [];
    memoryStore = [];

    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const bodyText = typeof init?.body === "string" ? init.body : null;
      const body = bodyText ? JSON.parse(bodyText) : null;
      fetchLog.push({ url, method, body });

      // /api/episodes/<id>/  — return the fixture.
      if (
        method === "GET" &&
        url.includes(`/api/episodes/${EPISODE_ID}/`)
      ) {
        return Promise.resolve(
          new Response(JSON.stringify(EPISODE_PAYLOAD), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      // /api/narrative-memories/?source_composition=<id>&… — list.
      if (
        method === "GET" &&
        url.includes("/api/narrative-memories/") &&
        url.includes(`source_composition=${COMPOSITION_ID}`)
      ) {
        return Promise.resolve(
          new Response(JSON.stringify(memoryStore), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      // POST /api/compositions/<id>/promote-narrative-memory/
      if (
        method === "POST" &&
        url.includes(
          `/api/compositions/${COMPOSITION_ID}/promote-narrative-memory/`,
        )
      ) {
        const items = (body as { memories?: unknown[] })?.memories ?? [];
        const created = (items as Array<Record<string, unknown>>).map(
          (item, ix) =>
            makeMemory({
              id: `mem-new-${memoryStore.length + ix + 1}`,
              body: String(item.body ?? ""),
              // Mirror the backend serializer's defaults so the
              // recap row looks like a real backend response.
              kind: (item.kind as string) ?? "event",
              weight: (item.weight as string) ?? "peripheral",
              witnessed_by: Array.isArray(item.witnessed_by)
                ? (item.witnessed_by as string[]).map((id) =>
                    id === PATCH.id
                      ? { id: PATCH.id, name: PATCH.name }
                      : { id: RIVET.id, name: RIVET.name },
                  )
                : [],
            }),
        );
        memoryStore.push(...created);
        return Promise.resolve(
          new Response(JSON.stringify({ memories: created }), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }

      // Anything else — 404 to fail loudly if the UI probes an
      // unexpected URL (e.g. /api/knowledge/* — canon must not
      // be touched from this panel).
      return Promise.resolve(new Response("[]", { status: 404 }));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------------------------
  // 1 + 2 — no Kind, no Weight in the creator flow.
  // ------------------------------------------------------------

  it("does not expose Kind or Weight controls", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    // The old testids from the pre-dogfood UI must be gone.
    expect(screen.queryByTestId("nm-kind")).toBeNull();
    expect(screen.queryByTestId("nm-weight")).toBeNull();
    // And no visible labels either.
    expect(screen.queryByText(/kind/i)).toBeNull();
    expect(screen.queryByText(/weight/i)).toBeNull();
    expect(screen.queryByText(/peripheral/i)).toBeNull();
  });

  // ------------------------------------------------------------
  // 3 + 4 + 6 — POST body omits kind/weight (backend supplies
  // event/peripheral defaults) and witnessed_by = [] means
  // whole-cast (post-SESSION-267: "In any future scene").
  // ------------------------------------------------------------

  it("default POST body carries body only — kind, weight, witnesses omitted / empty", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    // Wait for the Episode fetch to settle (cast toggles are
    // gated behind witnessMode='some', so we don't need the
    // cast to be visible here — we just need the panel ready).
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "The printer went rogue." },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("nm-submit"));
    });
    await waitFor(() => {
      const posted = fetchLog.find(
        (r) =>
          r.method === "POST" &&
          r.url.includes("/promote-narrative-memory/"),
      );
      expect(posted).toBeTruthy();
    });
    const posted = fetchLog.find(
      (r) =>
        r.method === "POST" && r.url.includes("/promote-narrative-memory/"),
    )!;
    const body = posted.body as {
      episode: string;
      memories: Array<Record<string, unknown>>;
    };
    expect(body.episode).toBe(EPISODE_ID);
    expect(body.memories).toHaveLength(1);
    const item = body.memories[0]!;
    expect(item.body).toBe("The printer went rogue.");
    // Kind + weight are OMITTED from the POST body — the backend
    // serializer applies event / peripheral defaults. This is
    // the load-bearing wire contract for the dogfood UX.
    expect(item).not.toHaveProperty("kind");
    expect(item).not.toHaveProperty("weight");
    // Whole-cast default → empty witnessed_by array.
    expect(item.witnessed_by).toEqual([]);
  });

  // ------------------------------------------------------------
  // 5 — "In any future scene" is the default selection
  // (post-SESSION-267 availability-condition framing).
  // ------------------------------------------------------------

  it('"In any future scene" is checked by default', async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    const everyone = screen
      .getByTestId("nm-witness-mode-everyone")
      .querySelector("input[type='radio']") as HTMLInputElement;
    const some = screen
      .getByTestId("nm-witness-mode-some")
      .querySelector("input[type='radio']") as HTMLInputElement;
    expect(everyone.checked).toBe(true);
    expect(some.checked).toBe(false);
  });

  // ------------------------------------------------------------
  // 7 — the "When any of these characters are present…" radio
  // reveals eligible Episode cast toggles.
  // ------------------------------------------------------------

  it('"When any of these characters are present…" reveals the Episode cast toggles', async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    // Wait for the cast to arrive via the Episode fetch.
    await waitFor(() => {
      expect(
        fetchLog.some(
          (r) =>
            r.method === "GET" &&
            r.url.includes(`/api/episodes/${EPISODE_ID}/`),
        ),
      ).toBe(true);
    });
    // Cast toggles hidden while the whole-cast radio is selected.
    expect(screen.queryByTestId("nm-witness-picker")).toBeNull();
    // Flip to the "When any of these characters are present…" radio.
    const someRadio = screen
      .getByTestId("nm-witness-mode-some")
      .querySelector("input[type='radio']") as HTMLInputElement;
    fireEvent.click(someRadio);
    // Cast toggles appear.
    await screen.findByTestId("nm-witness-picker");
    await screen.findByTestId(`nm-witness-toggle-${PATCH.id}`);
    await screen.findByTestId(`nm-witness-toggle-${RIVET.id}`);
  });

  // ------------------------------------------------------------
  // 8 — narrow witness selection lands in the POST body.
  // ------------------------------------------------------------

  it("narrow witness selection persists into the POST body", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "Rivet paused tokens." },
    });
    // Flip to the "When any of these characters are present…" radio.
    const someRadio = screen
      .getByTestId("nm-witness-mode-some")
      .querySelector("input[type='radio']") as HTMLInputElement;
    fireEvent.click(someRadio);
    // Pick only Rivet
    await screen.findByTestId("nm-witness-picker");
    fireEvent.click(screen.getByTestId(`nm-witness-toggle-${RIVET.id}`));
    await act(async () => {
      fireEvent.click(screen.getByTestId("nm-submit"));
    });
    await waitFor(() => {
      expect(
        fetchLog.find(
          (r) =>
            r.method === "POST" &&
            r.url.includes("/promote-narrative-memory/"),
        ),
      ).toBeTruthy();
    });
    const posted = fetchLog.find(
      (r) =>
        r.method === "POST" && r.url.includes("/promote-narrative-memory/"),
    )!;
    const body = posted.body as {
      memories: Array<Record<string, unknown>>;
    };
    expect(body.memories[0]!.witnessed_by).toEqual([RIVET.id]);
  });

  // ------------------------------------------------------------
  // 9 — explicit operator action is required.
  // ------------------------------------------------------------

  it('does not POST until the operator clicks "Remember this"', async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    // Type + wait for React Query lifecycle to settle.
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "Nothing should submit until I click." },
    });
    await waitFor(() => {
      // Give the Episode + list queries time to settle.
      expect(fetchLog.some((r) => r.url.includes("/api/episodes/"))).toBe(
        true,
      );
    });
    // No promote POST has fired.
    expect(
      fetchLog.some(
        (r) => r.method === "POST" && r.url.includes("/promote-narrative-memory/"),
      ),
    ).toBe(false);
  });

  // ------------------------------------------------------------
  // 10 — after clicking Remember this, the row re-appears in the
  // recap list.
  // ------------------------------------------------------------

  it("shows the newly-remembered row in the recap list after submit", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    await screen.findByTestId("nm-recap-empty");

    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "Rivet paused tokens." },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("nm-submit"));
    });

    // Invalidation refetches the recap; the fixture backend
    // returns the newly-created row.
    await waitFor(() => {
      expect(screen.queryByTestId("nm-recap-empty")).toBeNull();
    });
    await screen.findByText("Rivet paused tokens.");
  });

  // ------------------------------------------------------------
  // 11 — the creator flow never touches canon (KnowledgeDocument).
  // ------------------------------------------------------------

  it("never issues any /api/knowledge/ or /api/knowledge-documents/ request", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "Whatever, ship it." },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("nm-submit"));
    });
    await waitFor(() => {
      expect(
        fetchLog.some(
          (r) =>
            r.method === "POST" &&
            r.url.includes("/promote-narrative-memory/"),
        ),
      ).toBe(true);
    });
    // Canon endpoints — the mocked fetch would log any hit
    // regardless of status. Assert zero calls.
    const canonHits = fetchLog.filter(
      (r) =>
        r.url.includes("/api/knowledge") ||
        r.url.includes("/api/knowledge-documents"),
    );
    expect(canonHits).toEqual([]);
  });

  // ------------------------------------------------------------
  // SESSION 267 §15.11 — availability-condition copy lock.
  //
  // The promote-form legend + both radio labels + panel
  // description carry the semantic-truthful wording. If any
  // of these strings drift back toward the pre-SESSION-267
  // Semantic-2 language ("Who remembers this?" / "Remembered
  // by:"), a future audit reader is misled about what the
  // retrieval predicate actually delivers. Assertion-lock so
  // drift shows up as a test failure.
  // ------------------------------------------------------------

  it("carries the SESSION 267 availability-condition copy", async () => {
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    // Panel description — story-side framing, no "characters
    // can remember" (that was the SESSION-266 Semantic-2 leak).
    expect(
      screen.getByText(
        /Save something that happened in this episode so the story can bring it back later\./,
      ),
    ).toBeInTheDocument();
    // Legend — question form, availability framing.
    expect(
      screen.getByText("When should this memory be available?"),
    ).toBeInTheDocument();
    // Whole-cast radio — Universe-wide eligibility, not
    // Episode-cast-scoped (§15.11.3).
    expect(screen.getByText("In any future scene")).toBeInTheDocument();
    // Some-witnesses radio — explicit OR quantifier so the
    // multi-witness case doesn't misread as AND (§15.11.1).
    expect(
      screen.getByText("When any of these characters are present…"),
    ).toBeInTheDocument();
    // Old Semantic-2 strings must be gone. Fails loudly if drift
    // reintroduces them.
    expect(screen.queryByText("Who remembers this?")).toBeNull();
    expect(screen.queryByText("Everyone in this episode")).toBeNull();
    expect(screen.queryByText("Choose characters…")).toBeNull();
  });
});
