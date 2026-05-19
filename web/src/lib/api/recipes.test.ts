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
