/**
 * SESSION 277 Slice 12 (Q-277-12) — contextual character-origin
 * Knowledge handoff regression at the destination surface.
 *
 * Covers acceptance criteria C, D, E, F, G, H, I, J, K from the
 * Slice 12 prompt. Criteria A + B (welcome-page and KnowledgePanel
 * handoffs preserve context) are covered by
 * `welcome.handoff.test.tsx` and by inspection of the source in
 * §230 of the durable session document. Criterion L is covered by
 * the full-suite regression run.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/workspaces", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/workspaces")>(
    "@/lib/api/workspaces",
  );
  return { ...actual, useMe: vi.fn() };
});

vi.mock("@/lib/api/knowledge", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/knowledge")>(
    "@/lib/api/knowledge",
  );
  return {
    ...actual,
    useKnowledgeList: vi.fn(),
    useCreateKnowledge: vi.fn(),
    useDeleteKnowledge: vi.fn(),
    useKnowledgeSearch: vi.fn(),
  };
});

vi.mock("@/lib/api/universes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/universes")>(
    "@/lib/api/universes",
  );
  return {
    ...actual,
    useUniverse: vi.fn(),
    useUniverses: vi.fn(),
  };
});

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/spokespeople")>(
    "@/lib/api/spokespeople",
  );
  return { ...actual, useSpokesperson: vi.fn() };
});

import { useMe } from "@/lib/api/workspaces";
import {
  useKnowledgeList,
  useCreateKnowledge,
  useDeleteKnowledge,
  useKnowledgeSearch,
} from "@/lib/api/knowledge";
import { useUniverse, useUniverses } from "@/lib/api/universes";
import { useSpokesperson } from "@/lib/api/spokespeople";
import { WorkspaceKnowledgeRoute } from "./knowledge";

const useMeMock = useMe as unknown as ReturnType<typeof vi.fn>;
const useKnowledgeListMock =
  useKnowledgeList as unknown as ReturnType<typeof vi.fn>;
const useCreateKnowledgeMock =
  useCreateKnowledge as unknown as ReturnType<typeof vi.fn>;
const useDeleteKnowledgeMock =
  useDeleteKnowledge as unknown as ReturnType<typeof vi.fn>;
const useKnowledgeSearchMock =
  useKnowledgeSearch as unknown as ReturnType<typeof vi.fn>;
const useUniverseMock = useUniverse as unknown as ReturnType<typeof vi.fn>;
const useUniversesMock = useUniverses as unknown as ReturnType<typeof vi.fn>;
const useSpokespersonMock =
  useSpokesperson as unknown as ReturnType<typeof vi.fn>;


const FF_UNI = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f";
const TYSON = "f4de81f3-ef65-4196-a50e-38cfc6d1854f";
const RUBY = "5875a7b4-cf39-433d-89b3-4e34a89a5208";

function makeUniverse(overrides: Record<string, unknown> = {}) {
  return {
    id: FF_UNI,
    workspace: "ws_1",
    name: "Fox & Flour Bakery",
    slug: "fox-flour-bakery",
    description: "",
    brief: "A neighborhood artisan bakery.",
    created_by: null,
    created_at: "2026-07-23T00:00:00Z",
    updated_at: "2026-08-22T00:00:00Z",
    archived_at: null,
    teammate_count: 2,
    knowledge_document_count: 0,
    episode_count: 2,
    ...overrides,
  };
}

function makeSpokesperson(overrides: Record<string, unknown> = {}) {
  return {
    id: TYSON,
    workspace: "ws_1",
    workspace_name: "Chris's workspace",
    name: "Tyson",
    business_brief: ".",
    personality: ".",
    visual_subject: "",
    visual_template: "mascot",
    tone_archetype: "expert",
    universe: FF_UNI,
    status: "ready",
    runway_avatar_id: "av_1",
    runway_avatar_status: "ready",
    portrait_path: "https://fake/p.png",
    voice_id: "v_1",
    who_you_help: "",
    what_you_sell: "",
    always_emphasize: "",
    never_say: "",
    desired_feeling: "",
    character_point_of_view: "",
    voice_energy: "medium",
    voice_humor: "warm",
    voice_directness: "balanced",
    voice_signature_phrases: "",
    voice_avoid_phrases: "",
    identity_fields_filled: 1,
    video_count: 0,
    created_at: "2026-08-22T00:00:00Z",
    updated_at: "2026-08-22T00:00:00Z",
    ...overrides,
  };
}

function makeMutation<T = unknown>(result: T | null = null, error: unknown = null) {
  return {
    mutateAsync: vi.fn().mockResolvedValue(result),
    isPending: false,
    isError: !!error,
    error,
    reset: vi.fn(),
  };
}

function renderRoute(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route
            path="/workspace/knowledge"
            element={<WorkspaceKnowledgeRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}


beforeEach(() => {
  useMeMock.mockReset();
  useKnowledgeListMock.mockReset();
  useCreateKnowledgeMock.mockReset();
  useDeleteKnowledgeMock.mockReset();
  useKnowledgeSearchMock.mockReset();
  useUniverseMock.mockReset();
  useUniversesMock.mockReset();
  useSpokespersonMock.mockReset();

  useMeMock.mockReturnValue({
    data: {
      id: 1,
      email: "chris@donkeybetz.com",
      is_staff: false,
      default_workspace: {
        id: "ws_1",
        name: "Chris's workspace",
        slug: "chriss-workspace",
        role: "owner",
      },
    },
    isLoading: false,
    error: null,
  });
  useKnowledgeListMock.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  useDeleteKnowledgeMock.mockReturnValue(makeMutation());
  useKnowledgeSearchMock.mockReturnValue(makeMutation({ results: [] }));
  useUniversesMock.mockReturnValue({
    data: [makeUniverse()],
    isLoading: false,
    error: null,
  });
});


// ---------------------------------------------------------------
// Acceptance C, D — resolves names; neither audience preselected.
// ---------------------------------------------------------------

describe("contextual mode — resolution + audience selector", () => {
  beforeEach(() => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
  });

  it("resolves World + character names in human vocabulary (C)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    expect(screen.getByTestId("contextual-upload")).toBeTruthy();
    expect(
      screen.getByTestId("contextual-character-name").textContent,
    ).toBe("Tyson");
    expect(screen.getByTestId("contextual-world-name").textContent).toBe(
      "Fox & Flour Bakery",
    );
  });

  it("does NOT preselect either audience (D)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    const worldBtn = screen.getByTestId(
      "contextual-audience-world",
    ) as HTMLButtonElement;
    const characterBtn = screen.getByTestId(
      "contextual-audience-character",
    ) as HTMLButtonElement;
    expect(worldBtn.dataset.checked).toBe("false");
    expect(characterBtn.dataset.checked).toBe("false");
  });

  it("blocks ingest until an audience is picked (H)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    // Ingest tabs / forms are not rendered until an audience is chosen.
    expect(screen.queryByTestId("contextual-ingest")).toBeNull();
    expect(screen.queryByTestId("ctx-paste-submit")).toBeNull();
  });

  it("does NOT expose WORKSPACE as an audience option (G)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    // Only two audience buttons exist.
    expect(screen.getByTestId("contextual-audience-world")).toBeTruthy();
    expect(screen.getByTestId("contextual-audience-character")).toBeTruthy();
    // No WORKSPACE / legacy option.
    expect(
      screen.queryByText(/None \(legacy/i),
    ).toBeNull();
    expect(
      screen.queryByText(/workspace-wide/i),
    ).toBeNull();
    // No generic UniverseScopePicker in contextual mode.
    expect(screen.queryByTestId("paste-universe-scope")).toBeNull();
  });

  it("reveals the ingest tabs after audience is chosen", async () => {
    const user = userEvent.setup();
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    await user.click(screen.getByTestId("contextual-audience-world"));
    expect(screen.getByTestId("contextual-ingest")).toBeTruthy();
    expect(screen.getByTestId("ctx-tab-paste")).toBeTruthy();
    expect(screen.getByTestId("ctx-paste-submit")).toBeTruthy();
  });
});


// ---------------------------------------------------------------
// Acceptance E — World choice creates UNIVERSE audience payload.
// ---------------------------------------------------------------

describe("contextual mode — World audience payload (E)", () => {
  it("sends {workspace, universe, title, text_content} — no spokesperson_ids, no audience_scope", async () => {
    const create = makeMutation({ id: "kd_new" });
    useCreateKnowledgeMock.mockReturnValue(create);
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );

    await user.click(screen.getByTestId("contextual-audience-world"));
    await user.type(screen.getByTestId("ctx-paste-title"), "Menu");
    await user.type(
      screen.getByTestId("ctx-paste-content"),
      "Sourdough. Pastries. Celebration cakes.",
    );
    await user.click(screen.getByTestId("ctx-paste-submit"));

    await waitFor(() => expect(create.mutateAsync).toHaveBeenCalledTimes(1));
    const payload = create.mutateAsync.mock.calls[0]![0] as Record<string, unknown>;
    expect(payload).toMatchObject({
      workspace: "ws_1",
      universe: FF_UNI,
      title: "Menu",
      text_content: "Sourdough. Pastries. Celebration cakes.",
    });
    // No spokesperson_ids; no audience_scope; no null universe.
    expect("spokesperson_ids" in payload).toBe(false);
    expect("audience_scope" in payload).toBe(false);
  });
});


// ---------------------------------------------------------------
// Acceptance F — Character choice creates CHARACTER audience payload.
//
// Slice 12.1 correction (post-dogfood): the payload MUST include
// both `universe` and `spokesperson_ids`. Backend serializer
// (apps/embeddings/serializers.py:283-294) rejects
// `spokesperson_ids + universe=null` when the character is
// Universe-scoped. Precedence at _persist (ingestion.py:276)
// makes `spokespeople` win → audience_scope=CHARACTER with the
// KD carrying the character's Universe FK (Slice 6 §110
// "Universe-bound CHARACTER" shape).
// ---------------------------------------------------------------

describe("contextual mode — Character audience payload (F)", () => {
  it("sends {workspace, universe, spokesperson_ids: [<uuid>], title, text_content} — no audience_scope", async () => {
    const create = makeMutation({ id: "kd_new" });
    useCreateKnowledgeMock.mockReturnValue(create);
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );

    await user.click(screen.getByTestId("contextual-audience-character"));
    await user.type(screen.getByTestId("ctx-paste-title"), "Tyson espresso");
    await user.type(
      screen.getByTestId("ctx-paste-content"),
      "Tyson prefers a 25g dose.",
    );
    await user.click(screen.getByTestId("ctx-paste-submit"));

    await waitFor(() => expect(create.mutateAsync).toHaveBeenCalledTimes(1));
    const payload = create.mutateAsync.mock.calls[0]![0] as Record<string, unknown>;
    // Load-bearing: BOTH universe and spokesperson_ids are present.
    // Serializer precedence assigns audience_scope=CHARACTER when
    // spokespeople is non-empty; universe FK is required to satisfy
    // the SESSION 261 cross-check when the character is Universe-
    // scoped.
    expect(payload).toMatchObject({
      workspace: "ws_1",
      universe: FF_UNI,
      spokesperson_ids: [TYSON],
      title: "Tyson espresso",
      text_content: "Tyson prefers a 25g dose.",
    });
    expect("audience_scope" in payload).toBe(false);
  });
});


// ---------------------------------------------------------------
// Acceptance I — bare /workspace/knowledge unchanged.
// ---------------------------------------------------------------

describe("bare /workspace/knowledge unchanged (I)", () => {
  it("renders the pre-Slice-12 UploadPanel (with UniverseScopePicker) when no params", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute("/workspace/knowledge");
    // Pre-Slice-12 upload panel present.
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    // Generic UniverseScopePicker present.
    expect(screen.getByTestId("paste-universe-scope")).toBeTruthy();
    // Contextual panel NOT rendered.
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });
});


// ---------------------------------------------------------------
// Acceptance K — invalid / stale params fail safely.
// ---------------------------------------------------------------

describe("stale / invalid handoff params fail safely (K)", () => {
  beforeEach(() => {
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
  });

  it("falls back to the generic UploadPanel when spokesperson doesn't resolve", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("falls back when universe param doesn't resolve", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("falls back when the spokesperson.universe doesn't match the URL universe (stale)", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    // Spokesperson belongs to a DIFFERENT universe than the URL claims.
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson({ universe: "99999999-9999-4999-8999-999999999999" }),
      isLoading: false,
      error: null,
    });
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_welcome`,
    );
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("falls back when malformed UUIDs are in the URL", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    renderRoute(
      "/workspace/knowledge?universe=garbage&spokesperson=nope&origin=character_welcome",
    );
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("falls back when a legacy universe=NULL teammate arrives via character_detail origin", () => {
    // Handoff omits the universe param entirely (legacy teammate).
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson({ universe: null, name: "LegacyRuby" }),
      isLoading: false,
      error: null,
    });
    renderRoute(
      `/workspace/knowledge?spokesperson=${RUBY}&origin=character_detail_knowledge_panel`,
    );
    // No World to preselect — cannot render "Everyone in {World}".
    // Contract: fall back safely to the generic flow.
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });
});


// ---------------------------------------------------------------
// Acceptance J — refresh / deep-link with contextual params
// preserves the handoff state (validated by MemoryRouter directly
// mounting the URL; equivalent to a page refresh).
// ---------------------------------------------------------------

describe("deep-link / refresh preserves handoff state (J)", () => {
  it("mounts directly on the contextual URL and renders contextual mode", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=${TYSON}&origin=character_detail_knowledge_panel`,
    );
    expect(screen.getByTestId("contextual-upload")).toBeTruthy();
    // Origin discriminator is respected — this route also renders
    // for the KnowledgePanel origin.
    expect(screen.getByTestId("contextual-character-name")).toBeTruthy();
  });
});
