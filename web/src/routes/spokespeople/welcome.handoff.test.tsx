/**
 * SESSION 277 Slice 12 (Q-277-12) — welcome-page handoff coverage.
 * Acceptance criterion A: welcome CTA preserves World + character
 * + origin in the URL.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/spokespeople")>(
    "@/lib/api/spokespeople",
  );
  return { ...actual, useSpokesperson: vi.fn() };
});

import { useSpokesperson } from "@/lib/api/spokespeople";
import { SpokespersonWelcomeRoute } from "./welcome";

const useSpokespersonMock =
  useSpokesperson as unknown as ReturnType<typeof vi.fn>;

const FF_UNI = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f";
const TYSON = "f4de81f3-ef65-4196-a50e-38cfc6d1854f";

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

function renderRoute() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/spokespeople/${TYSON}/welcome`]}>
        <Routes>
          <Route
            path="/spokespeople/:id/welcome"
            element={<SpokespersonWelcomeRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useSpokespersonMock.mockReset();
});


describe("welcome-page teach CTA — SESSION 277 Slice 12 handoff (A)", () => {
  it("routes to /workspace/knowledge with universe + spokesperson + origin=character_welcome", () => {
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      error: null,
    });
    renderRoute();
    const cta = screen.getByTestId("welcome-teach-cta") as HTMLAnchorElement;
    // asChild passes the href through to the child <a>.
    const href = cta.getAttribute("href") ?? cta.querySelector("a")?.getAttribute("href") ?? "";
    expect(href.startsWith("/workspace/knowledge?")).toBe(true);
    const params = new URLSearchParams(href.split("?")[1]);
    expect(params.get("universe")).toBe(FF_UNI);
    expect(params.get("spokesperson")).toBe(TYSON);
    expect(params.get("origin")).toBe("character_welcome");
  });

  it("omits the universe param when the character is legacy universe=NULL", () => {
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson({ universe: null }),
      isLoading: false,
      error: null,
    });
    renderRoute();
    const cta = screen.getByTestId("welcome-teach-cta") as HTMLAnchorElement;
    const href = cta.getAttribute("href") ?? cta.querySelector("a")?.getAttribute("href") ?? "";
    const params = new URLSearchParams(href.split("?")[1]);
    expect(params.get("universe")).toBeNull();
    expect(params.get("spokesperson")).toBe(TYSON);
    expect(params.get("origin")).toBe("character_welcome");
  });
});
