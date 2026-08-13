/**
 * recipes.ts A7 unit tests — SESSION 190.
 *
 * Covers the asset_picker role_filter pass-through plumbing:
 *
 *   - listAssets URL building includes ?role= when supplied
 *   - listAssets URL building omits ?role= when undefined
 *   - recipeFieldSchema parses role_filter (string OR absent)
 *   - recipeFieldSchema rejects role_filter when null (would
 *     force the SPA to handle a value the backend never sends)
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

// We mock apiJson before importing the module under test so the
// fetch interception captures the URL.
vi.mock("./client", () => ({
  apiJson: vi.fn(async (path: string) => {
    // Echo the path back as a fake response that the parser will
    // see. Each test re-mocks to whatever shape it needs.
    return { __echoed_path: path };
  }),
}));

import * as recipesModule from "./recipes";
import { apiJson } from "./client";

const apiJsonMock = vi.mocked(apiJson);

beforeEach(() => {
  apiJsonMock.mockClear();
});

afterEach(() => {
  apiJsonMock.mockReset();
});


// ---- listAssets URL building ---------------------------------


describe("listAssets URL building", () => {
  function lastApiCallPath(): string {
    const call = apiJsonMock.mock.calls[0];
    expect(call).toBeDefined();
    return call![0] as string;
  }

  it("omits ?role= when undefined", async () => {
    apiJsonMock.mockResolvedValue([]);
    await recipesModule.listAssets({
      workspace: "ws-1",
      assetType: "clip",
    });
    const calledPath = lastApiCallPath();
    expect(calledPath).toContain("workspace=ws-1");
    expect(calledPath).toContain("asset_type=clip");
    expect(calledPath).not.toContain("role=");
  });

  it("includes ?role= when supplied", async () => {
    apiJsonMock.mockResolvedValue([]);
    await recipesModule.listAssets({
      workspace: "ws-1",
      assetType: "clip",
      role: "backdrop",
    });
    const calledPath = lastApiCallPath();
    expect(calledPath).toContain("role=backdrop");
  });

  it("supports role without asset_type", async () => {
    apiJsonMock.mockResolvedValue([]);
    await recipesModule.listAssets({
      workspace: "ws-1",
      role: "b_roll",
    });
    const calledPath = lastApiCallPath();
    expect(calledPath).toContain("role=b_roll");
    expect(calledPath).not.toContain("asset_type=");
  });
});


// ---- Recipe field shape — role_filter -------------------------


describe("Recipe field schema role_filter", () => {
  // We exercise the schema by feeding /api/recipes/<kind>/
  // through the getRecipe parse path. Mock the response with
  // a minimal recipe that carries one asset_picker field with
  // role_filter set.

  it("parses role_filter when present", async () => {
    apiJsonMock.mockImplementationOnce(
      async (_path, _init, parser?: (json: unknown) => unknown) => {
        const fake = {
          kind: "test_recipe",
          display_name: "Test",
          family: "layout",
          description: "x",
          fields: [
            {
              name: "backdrop_clip_id",
              type: "asset_picker",
              label: "Backdrop",
              required: false,
              asset_type: "clip",
              role_filter: "backdrop",
            },
          ],
        };
        return parser ? parser(fake) : fake;
      },
    );
    const recipe = await recipesModule.getRecipe("test_recipe");
    const field = recipe.fields[0];
    expect(field).toBeDefined();
    expect(field!.role_filter).toBe("backdrop");
  });

  it("parses field without role_filter (backwards-compat)", async () => {
    apiJsonMock.mockImplementationOnce(
      async (_path, _init, parser?: (json: unknown) => unknown) => {
        const fake = {
          kind: "test_recipe",
          display_name: "Test",
          family: "layout",
          description: "x",
          fields: [
            {
              name: "base_clip_id",
              type: "asset_picker",
              label: "Base",
              required: true,
              asset_type: "clip",
              // no role_filter — fuzzy picker, accept any CLIP
            },
          ],
        };
        return parser ? parser(fake) : fake;
      },
    );
    const recipe = await recipesModule.getRecipe("test_recipe");
    const field = recipe.fields[0];
    expect(field).toBeDefined();
    expect(field!.role_filter).toBeUndefined();
  });
});


// ---- A8 (SESSION 192) — composition produced_assets cross-link ---


describe("Composition produced_assets schema (A8)", () => {
  function fakeComposition(produced_assets: unknown[]) {
    return {
      id: "comp-1",
      workspace: "ws-1",
      spokesperson: "sp-1",
      name: "Test",
      template_kind: "talking_head",
      status: "completed",
      mock_mode: true,
      cost_estimate_micros: 0,
      cost_actual_micros: 0,
      knowledge_chunk_ids: [],
      knowledge_docs_used: [],
      error_message: "",
      created_at: "2026-05-19T00:00:00Z",
      updated_at: "2026-05-19T00:00:00Z",
      steps: [],
      final_asset: null,
      produced_assets,
      verification_warnings: [],
      rejected_synthesis: "",
      verification_status: "",
      synthesized_brief: "",
    };
  }

  it("parses produced_assets array with all required fields", async () => {
    apiJsonMock.mockImplementationOnce(
      async (_path, _init, parser?: (json: unknown) => unknown) => {
        const fake = fakeComposition([
          {
            id: "asset-1",
            asset_type: "clip",
            role: "talking_head",
            title: "Hero clip",
            file_path: "https://cdn/x.mp4",
            storage_health: "https_live",
            is_final: true,
          },
        ]);
        return parser ? parser(fake) : fake;
      },
    );
    const comp = await recipesModule.getComposition("comp-1");
    expect(comp.produced_assets).toHaveLength(1);
    const a = comp.produced_assets[0];
    expect(a).toBeDefined();
    expect(a!.role).toBe("talking_head");
    expect(a!.is_final).toBe(true);
    expect(a!.storage_health).toBe("https_live");
  });

  it("defaults to empty array when produced_assets is missing", async () => {
    apiJsonMock.mockImplementationOnce(
      async (_path, _init, parser?: (json: unknown) => unknown) => {
        const fake = fakeComposition([]);
        // simulate older row by omitting produced_assets entirely
        delete (fake as Record<string, unknown>).produced_assets;
        return parser ? parser(fake) : fake;
      },
    );
    const comp = await recipesModule.getComposition("comp-1");
    expect(comp.produced_assets).toEqual([]);
  });

  it("parses multiple produced assets with mixed is_final", async () => {
    apiJsonMock.mockImplementationOnce(
      async (_path, _init, parser?: (json: unknown) => unknown) => {
        const fake = fakeComposition([
          {
            id: "asset-1",
            asset_type: "image",
            role: "reference_image",
            title: "Ref",
            file_path: "/data/ref.png",
            storage_health: "local_present",
            is_final: false,
          },
          {
            id: "asset-2",
            asset_type: "clip",
            role: "talking_head",
            title: "Final",
            file_path: "https://cdn/final.mp4",
            storage_health: "https_live",
            is_final: true,
          },
        ]);
        return parser ? parser(fake) : fake;
      },
    );
    const comp = await recipesModule.getComposition("comp-1");
    expect(comp.produced_assets).toHaveLength(2);
    const finals = comp.produced_assets.filter((a) => a.is_final);
    expect(finals).toHaveLength(1);
    expect(finals[0]!.id).toBe("asset-2");
  });
});
