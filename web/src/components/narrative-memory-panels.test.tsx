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
import { fireEvent, render, screen, waitFor, act, within } from "@testing-library/react";
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

type CuratorResponseFactory = () =>
  | { status: 200; body: unknown }
  | { status: 500; body: unknown }
  | { status: 502; body: unknown };

// Slice 281.2 default: silent (no curator response). Tests that
// exercise the curator surface override via `setCuratorResponse`.
let curatorResponse: CuratorResponseFactory = () => ({
  status: 200,
  body: {
    candidates: [],
    substrate_summary: {},
    generated_at: "2026-08-25T00:00:00Z",
    model: "gpt-5.6-terra",
    cache: { hit: false, ttl_seconds: 1800 },
  },
});

function setCuratorResponse(factory: CuratorResponseFactory) {
  curatorResponse = factory;
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
    // Reset per-test curator override so a passing test never
    // pollutes the next test's baseline.
    setCuratorResponse(() => ({
      status: 200,
      body: {
        candidates: [],
        substrate_summary: {},
        generated_at: "2026-08-25T00:00:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 1800 },
      },
    }));

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

      // SESSION 281 Slice 281.2 — curator endpoint. Tests
      // opt-in via setCuratorResponse; default is empty
      // candidates so the panel's existing textarea tests
      // continue to render only the manual path.
      if (
        method === "GET" &&
        url.includes(
          `/api/compositions/${COMPOSITION_ID}/suggested-memories/`,
        )
      ) {
        const r = curatorResponse();
        return Promise.resolve(
          new Response(JSON.stringify(r.body), {
            status: r.status,
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

  // ============================================================
  // SESSION 281 Slice 281.2 — curator suggestion cards.
  // ============================================================
  //
  // Load-bearing invariants verified below:
  //
  //   * loading state renders without blocking the manual path
  //   * empty response leaves the panel visually clean (no
  //     dramatic empty state)
  //   * provider/query error leaves the manual textarea path
  //     fully usable (no error banner)
  //   * 3 candidate cards render body + optional natural hint
  //   * hidden kind + witnesses metadata NEVER appears in the DOM
  //   * [Remember this] calls the existing promote mutation with
  //     body + witnessed_by: [] (no kind, no witnesses, no
  //     narrative_gravity_note)
  //   * remembered state appears after mutation success and the
  //     existing recap updates via normal query invalidation
  //   * Edit edits body inline and submits the edited body with
  //     witnessed_by: []
  //   * Skip dismisses locally without any mutation
  //   * no refresh / "Different ideas" affordance exists
  //   * existing manual textarea + availability radios remain
  //     unchanged and functional
  //   * vocabulary-leak invariant on the operator-owned copy
  // ------------------------------------------------------------

  function curatorCandidate(overrides: Record<string, unknown> = {}) {
    return {
      body: "Ruby and Tyson agreed neither leaves until the "
        + "other says they have what they need.",
      kind: "event",
      witnesses: ["Ruby", "Tyson"],
      narrative_gravity_note:
        "Could be tested if one of them ever has to leave early.",
      ...overrides,
    };
  }

  function threeCandidatesResponse(
    overrides: Array<Record<string, unknown>> = [],
  ) {
    const defaults = [
      curatorCandidate({ body: "The lockout led to a new closing routine." }),
      curatorCandidate({
        body:
          "Tyson joked that the mascot might stay inside doing "
          + "\"community outreach\" after closing.",
        kind: "dialogue_callback",
        narrative_gravity_note: "Could become a running joke.",
      }),
      curatorCandidate({
        body:
          "Ruby still wants Fox & Flour to have a welcoming bakery mascot.",
        kind: "promise",
        narrative_gravity_note:
          "Keeps the mascot idea alive as an unresolved future addition.",
      }),
    ];
    return {
      status: 200 as const,
      body: {
        candidates: overrides.length > 0
          ? overrides.map((o) => curatorCandidate(o))
          : defaults,
        substrate_summary: {
          prior_episodes_used: 11,
          existing_memories_used: 2,
          cast_count: 2,
          dialogue_chars: 1426,
        },
        generated_at: "2026-08-25T00:33:00Z",
        model: "gpt-5.6-terra",
        cache: { hit: false, ttl_seconds: 1800 },
      },
    };
  }

  it("loading state renders without blocking the manual path", async () => {
    // Never-resolving curator promise — the loading indicator
    // must appear and the manual textarea must remain interactive.
    setCuratorResponse(() =>
      // Cast to satisfy the union — we return status:200 but
      // the fetch itself is never fulfilled because we swap
      // the impl below.
      ({ status: 200, body: {} }),
    );
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const bodyText = typeof init?.body === "string" ? init.body : null;
      const body = bodyText ? JSON.parse(bodyText) : null;
      fetchLog.push({ url, method, body });
      if (
        method === "GET" &&
        url.includes(
          `/api/compositions/${COMPOSITION_ID}/suggested-memories/`,
        )
      ) {
        return new Promise(() => {
          /* never resolves — pending loading state */
        });
      }
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
      return Promise.resolve(new Response("[]", { status: 404 }));
    });

    renderPanel();
    await screen.findByTestId("composition-remember-this");
    await screen.findByTestId("composition-suggested-memories-loading");
    // Manual path still present and interactive.
    expect(screen.getByTestId("nm-body")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "operator can still type" },
    });
    expect(
      (screen.getByTestId("nm-body") as HTMLTextAreaElement).value,
    ).toBe("operator can still type");
  });

  it("empty curator response renders no dramatic empty state", async () => {
    // beforeEach default already returns candidates=[].
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    await waitFor(() => {
      expect(
        fetchLog.some((r) =>
          r.url.includes(
            `/api/compositions/${COMPOSITION_ID}/suggested-memories/`,
          ),
        ),
      ).toBe(true);
    });
    // No section, no loading, no divider, no cards.
    expect(
      screen.queryByTestId("composition-suggested-memories"),
    ).toBeNull();
    expect(
      screen.queryByTestId("composition-suggested-memories-list"),
    ).toBeNull();
    // Manual path fully usable.
    expect(screen.getByTestId("nm-body")).toBeInTheDocument();
    expect(screen.getByTestId("nm-submit")).toBeInTheDocument();
  });

  it("curator provider error is silent — manual path remains usable", async () => {
    setCuratorResponse(() => ({ status: 502, body: { error: "boom" } }));
    renderPanel();
    await screen.findByTestId("composition-remember-this");
    await waitFor(() => {
      expect(
        fetchLog.some((r) =>
          r.url.includes(
            `/api/compositions/${COMPOSITION_ID}/suggested-memories/`,
          ),
        ),
      ).toBe(true);
    });
    // No visible error banner or curator surface anywhere.
    expect(
      screen.queryByTestId("composition-suggested-memories"),
    ).toBeNull();
    expect(screen.queryByText(/couldn.?t/i)).toBeNull();
    expect(screen.queryByText(/error/i)).toBeNull();
    // Manual path still fully usable.
    fireEvent.change(screen.getByTestId("nm-body"), {
      target: { value: "manual still works after curator error" },
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
  });

  it("renders 3 candidate cards with body + natural hint visible", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    // Header copy present.
    expect(
      screen.getByText("A few ideas from what just happened."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Remember the ones that might matter later."),
    ).toBeInTheDocument();
    // All three bodies visible.
    expect(
      screen.getByTestId("composition-suggested-memory-body-0"),
    ).toHaveTextContent(/lockout led to a new closing routine/i);
    expect(
      screen.getByTestId("composition-suggested-memory-body-1"),
    ).toHaveTextContent(/community outreach/i);
    expect(
      screen.getByTestId("composition-suggested-memory-body-2"),
    ).toHaveTextContent(/welcoming bakery mascot/i);
    // Natural hints appear where supplied.
    expect(
      screen.getByTestId("composition-suggested-memory-hint-1"),
    ).toHaveTextContent(/running joke/i);
    // Divider transitions to the existing manual path.
    expect(
      screen.getByTestId("composition-suggested-memories-divider"),
    ).toHaveTextContent(/or write your own/i);
    // Manual textarea + submit + availability radios remain present
    // and byte-identical to today's shipped behavior.
    expect(screen.getByTestId("nm-body")).toBeInTheDocument();
    expect(screen.getByTestId("nm-submit")).toBeInTheDocument();
    expect(
      screen.getByTestId("nm-witness-mode-everyone"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("nm-witness-mode-some")).toBeInTheDocument();
  });

  it("hidden kind + witness metadata is NEVER rendered", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    const section = await screen.findByTestId(
      "composition-suggested-memories",
    );
    const text = section.textContent ?? "";
    // Kind values from the fixture — must not leak into the DOM
    // as visible operator copy.
    expect(text).not.toMatch(/dialogue_callback/i);
    expect(text).not.toMatch(/\bkind\b/i);
    expect(text).not.toMatch(/\bcallback\b/i);
    expect(text).not.toMatch(/\bpromise\b/i);
    expect(text).not.toMatch(/\bevent\b/i);
    expect(text).not.toMatch(/world.detail/i);
    // Witness names from the fixture — the panel MUST NOT render
    // them as chips / labels here. (The names may appear inside
    // candidate bodies themselves — that's story prose, not
    // classification. The two fixture bodies here don't contain
    // "Ruby" / "Tyson" anywhere, so a direct name check is
    // meaningful.)
    expect(text).not.toMatch(/\bRuby\b/);
    expect(text).not.toMatch(/\bTyson\b/);
    expect(text).not.toMatch(/witness/i);
  });

  it("[Remember this] posts body + witnessed_by:[] only (no hidden metadata)", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    await act(async () => {
      fireEvent.click(
        screen.getByTestId("composition-suggested-memory-remember-0"),
      );
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
    const posted = fetchLog.find(
      (r) =>
        r.method === "POST" &&
        r.url.includes("/promote-narrative-memory/"),
    )!;
    const postedBody = posted.body as {
      episode: string;
      memories: Array<Record<string, unknown>>;
    };
    expect(postedBody.episode).toBe(EPISODE_ID);
    expect(postedBody.memories).toHaveLength(1);
    const item = postedBody.memories[0]!;
    // Body is the candidate body verbatim.
    expect(item.body).toBe(
      "The lockout led to a new closing routine.",
    );
    // Whole-cast persistence policy per Slice 281.2.
    expect(item.witnessed_by).toEqual([]);
    // Model-authored metadata must NOT be persisted as durable
    // authority in this slice.
    expect(item).not.toHaveProperty("kind");
    expect(item).not.toHaveProperty("witnesses");
    expect(item).not.toHaveProperty("narrative_gravity_note");
    expect(item).not.toHaveProperty("weight");
  });

  it("card collapses to Remembered. state after mutation succeeds", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    await act(async () => {
      fireEvent.click(
        screen.getByTestId("composition-suggested-memory-remember-0"),
      );
    });
    await screen.findByTestId(
      "composition-suggested-memory-remembered-0",
    );
    const card = screen.getByTestId(
      "composition-suggested-memory-card-0",
    );
    expect(card).toHaveAttribute("data-status", "remembered");
    expect(
      within(card).getByText(/remembered\./i),
    ).toBeInTheDocument();
    // The other cards remain interactive in their default state.
    expect(
      screen.getByTestId("composition-suggested-memory-card-1"),
    ).toHaveAttribute("data-status", "pending");
  });

  it("existing recap updates via normal query invalidation after remember", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    await screen.findByTestId("nm-recap-empty");
    await act(async () => {
      fireEvent.click(
        screen.getByTestId("composition-suggested-memory-remember-2"),
      );
    });
    await waitFor(() => {
      expect(screen.queryByTestId("nm-recap-empty")).toBeNull();
    });
    await screen.findByText(/welcoming bakery mascot/i);
  });

  it("Edit swaps in an inline editor and submits the edited body", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    fireEvent.click(
      screen.getByTestId("composition-suggested-memory-edit-btn-0"),
    );
    const editor = await screen.findByTestId(
      "composition-suggested-memory-edit-0",
    );
    fireEvent.change(editor, {
      target: {
        value: "Operator-edited version of the closing routine memory.",
      },
    });
    await act(async () => {
      fireEvent.click(
        screen.getByTestId("composition-suggested-memory-save-0"),
      );
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
    const posted = fetchLog.find(
      (r) =>
        r.method === "POST" &&
        r.url.includes("/promote-narrative-memory/"),
    )!;
    const postedBody = posted.body as {
      memories: Array<Record<string, unknown>>;
    };
    const item = postedBody.memories[0]!;
    expect(item.body).toBe(
      "Operator-edited version of the closing routine memory.",
    );
    expect(item.witnessed_by).toEqual([]);
    // Same no-hidden-metadata invariant applies to the edit path.
    expect(item).not.toHaveProperty("kind");
    expect(item).not.toHaveProperty("witnesses");
  });

  it("Skip dismisses the card locally without a mutation", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    fireEvent.click(
      screen.getByTestId("composition-suggested-memory-skip-1"),
    );
    await waitFor(() => {
      expect(
        screen.queryByTestId("composition-suggested-memory-card-1"),
      ).toBeNull();
    });
    // No POST occurred as a side effect of Skip.
    expect(
      fetchLog.some(
        (r) =>
          r.method === "POST" &&
          r.url.includes("/promote-narrative-memory/"),
      ),
    ).toBe(false);
    // Other cards remain in place.
    expect(
      screen.getByTestId("composition-suggested-memory-card-0"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("composition-suggested-memory-card-2"),
    ).toBeInTheDocument();
  });

  it("no refresh / Different ideas affordance is exposed", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    // No refresh testid.
    expect(
      screen.queryByTestId("composition-suggested-memories-refresh"),
    ).toBeNull();
    // No visible refresh copy — the v1 story-direction surface uses
    // "Different ideas" / "Try again" — neither should appear here.
    expect(screen.queryByText(/different ideas/i)).toBeNull();
    expect(screen.queryByText(/refresh/i)).toBeNull();
    expect(screen.queryByText(/regenerate/i)).toBeNull();
    // The endpoint was called exactly once — no polling.
    const curatorCalls = fetchLog.filter((r) =>
      r.url.includes(
        `/api/compositions/${COMPOSITION_ID}/suggested-memories/`,
      ),
    );
    expect(curatorCalls).toHaveLength(1);
    // And nothing carries `?refresh=true` — Slice 281.2 never asks
    // the server to bypass its cache.
    expect(
      curatorCalls.every((r) => !r.url.includes("refresh=true")),
    ).toBe(true);
  });

  it("existing availability + textarea remain byte-identical alongside curator cards", async () => {
    setCuratorResponse(() => threeCandidatesResponse());
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    // Availability radios present with their SESSION 267 copy.
    expect(
      screen.getByText("When should this memory be available?"),
    ).toBeInTheDocument();
    expect(screen.getByText("In any future scene")).toBeInTheDocument();
    expect(
      screen.getByText("When any of these characters are present…"),
    ).toBeInTheDocument();
    // Manual textarea still there and submit still gates on body.
    const textarea = screen.getByTestId("nm-body") as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    const submit = screen.getByTestId("nm-submit") as HTMLButtonElement;
    expect(submit).toBeDisabled();
    fireEvent.change(textarea, { target: { value: "manual entry" } });
    expect(submit).not.toBeDisabled();
    // Manual POST still uses whole-cast default.
    await act(async () => {
      fireEvent.click(submit);
    });
    await waitFor(() => {
      const posted = fetchLog.find(
        (r) =>
          r.method === "POST" &&
          r.url.includes("/promote-narrative-memory/"),
      );
      expect(posted).toBeTruthy();
      const item = (
        posted!.body as { memories: Array<Record<string, unknown>> }
      ).memories[0]!;
      expect(item.body).toBe("manual entry");
      expect(item.witnessed_by).toEqual([]);
      expect(item).not.toHaveProperty("kind");
      expect(item).not.toHaveProperty("weight");
    });
  });

  it("drops narrative_gravity_note hints that contain implementation vocabulary", async () => {
    setCuratorResponse(() =>
      threeCandidatesResponse([
        {
          body: "Body one",
          narrative_gravity_note: "Reads naturally as a real hint.",
        },
        {
          body: "Body two",
          // Implementation-vocabulary hint — must be silently
          // dropped rather than rendered.
          narrative_gravity_note:
            "This is a candidate for dialogue_callback retrieval.",
        },
        {
          body: "Body three",
          narrative_gravity_note: "",
        },
      ]),
    );
    renderPanel();
    await screen.findByTestId("composition-suggested-memories-list");
    // Card 0 keeps its natural hint.
    expect(
      screen.getByTestId("composition-suggested-memory-hint-0"),
    ).toHaveTextContent(/reads naturally/i);
    // Card 1's implementation-y hint is dropped.
    expect(
      screen.queryByTestId("composition-suggested-memory-hint-1"),
    ).toBeNull();
    // Card 2 has no hint at all.
    expect(
      screen.queryByTestId("composition-suggested-memory-hint-2"),
    ).toBeNull();
  });

  it("operator-owned copy carries no banned implementation vocabulary", async () => {
    // Use the default 3-candidate response so the panel is rendered.
    setCuratorResponse(() =>
      threeCandidatesResponse([
        // Deliberately-neutral bodies so we can safely scan the
        // whole section text for banned words (no risk of a
        // legitimate character line containing 'kind' etc.).
        {
          body: "The lockout led to a new closing routine.",
          narrative_gravity_note:
            "Could be tested if someone has to leave early.",
        },
        {
          body: "A tiny bell warns anyone reaching for the door.",
          narrative_gravity_note: "Could become a running joke.",
        },
        {
          body:
            "The bakery still wants a welcoming neighborhood mascot.",
          narrative_gravity_note:
            "Keeps that idea alive for a future scene.",
        },
      ]),
    );
    renderPanel();
    const section = await screen.findByTestId(
      "composition-suggested-memories",
    );
    const text = (section.textContent ?? "").toLowerCase();
    const banned = [
      "narrativememorykind",
      "narrative gravity",
      "memory weight",
      "peripheral",
      "central",
      "dialogue_callback",
      "world_detail",
      "world detail",
      "callback",
      "witnesses",
      "witnessed_by",
      "retrieval",
      "embedding",
      "vector",
      "top_k",
      "prompt",
      "llm",
      "model generated",
      "ai generated",
      "candidate",
      "substrate",
      "provenance",
      "memory_id",
      "latent thread",
      "semantic continuation",
    ];
    for (const word of banned) {
      expect(text.includes(word)).toBe(false);
    }
  });
});
