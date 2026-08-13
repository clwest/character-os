/**
 * workspace-assets.ts unit tests — SESSION 189 / A5, SESSION 191 / A6.
 *
 * Covers:
 *   - Zod schema parsing (well-formed payload round-trips cleanly)
 *   - buildAssetsQueryString URL construction (arrays → comma lists,
 *     page 1 omitted, page > 1 included)
 *   - relativeTime helper edge cases
 *   - storageHealthTone helper (spot-checks each tone bucket)
 *   - assetRoleLabel / assetTypeLabel for all enum values
 *   - A6: workspaceAssetDetailSchema parsing (full + null step + empty downstream)
 *   - A6: getWorkspaceAsset URL construction
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  buildAssetsQueryString,
  relativeTime,
  storageHealthTone,
  assetRoleLabel,
  assetTypeLabel,
  workspaceAssetDetailSchema,
  getWorkspaceAsset,
  ASSET_ROLES,
} from "./workspace-assets";

// ---- buildAssetsQueryString ----------------------------------

describe("buildAssetsQueryString", () => {
  it("returns empty string when no params", () => {
    expect(buildAssetsQueryString({})).toBe("");
  });

  it("omits page when page=1 (default)", () => {
    const qs = buildAssetsQueryString({ page: 1, page_size: 25 });
    expect(qs).not.toContain("page=");
    expect(qs).toContain("page_size=25");
  });

  it("includes page when page > 1", () => {
    const qs = buildAssetsQueryString({ page: 3 });
    expect(qs).toContain("page=3");
  });

  it("joins role array as comma-separated value", () => {
    const qs = buildAssetsQueryString({
      role: ["talking_head", "backdrop"],
    });
    expect(qs).toContain("role=talking_head%2Cbackdrop");
  });

  it("joins asset_type array as comma-separated value", () => {
    const qs = buildAssetsQueryString({
      asset_type: ["clip", "image"],
    });
    expect(qs).toContain("asset_type=clip%2Cimage");
  });

  it("omits empty arrays", () => {
    const qs = buildAssetsQueryString({ role: [], asset_type: [] });
    expect(qs).toBe("");
  });

  it("includes q when non-empty", () => {
    const qs = buildAssetsQueryString({ q: "talking head" });
    expect(qs).toContain("q=talking+head");
  });

  it("includes created_after and created_before", () => {
    const qs = buildAssetsQueryString({
      created_after: "2026-01-01",
      created_before: "2026-06-01",
    });
    expect(qs).toContain("created_after=2026-01-01");
    expect(qs).toContain("created_before=2026-06-01");
  });

  it("includes workspace when provided", () => {
    const qs = buildAssetsQueryString({ workspace: "ws-abc-123" });
    expect(qs).toContain("workspace=ws-abc-123");
  });

  it("assembles all params together", () => {
    const qs = buildAssetsQueryString({
      role: ["clip"],
      asset_type: ["image"],
      storage: ["https_live"],
      q: "test",
      page: 2,
      page_size: 50,
    });
    expect(qs).toContain("role=clip");
    expect(qs).toContain("asset_type=image");
    expect(qs).toContain("storage=https_live");
    expect(qs).toContain("q=test");
    expect(qs).toContain("page=2");
    expect(qs).toContain("page_size=50");
  });
});

// ---- relativeTime --------------------------------------------

describe("relativeTime", () => {
  function isoSecondsAgo(s: number): string {
    return new Date(Date.now() - s * 1_000).toISOString();
  }

  it("returns 'just now' for < 60 seconds ago", () => {
    expect(relativeTime(isoSecondsAgo(30))).toBe("just now");
  });

  it("returns minutes for < 60 minutes ago", () => {
    const result = relativeTime(isoSecondsAgo(120));
    expect(result).toBe("2m ago");
  });

  it("returns hours for < 24 hours ago", () => {
    const result = relativeTime(isoSecondsAgo(3 * 3600));
    expect(result).toBe("3h ago");
  });

  it("returns 'yesterday' for exactly 1 day ago", () => {
    expect(relativeTime(isoSecondsAgo(25 * 3600))).toBe("yesterday");
  });

  it("returns days for < 7 days ago", () => {
    expect(relativeTime(isoSecondsAgo(3 * 24 * 3600))).toBe("3d ago");
  });

  it("returns a formatted date for > 7 days ago", () => {
    // 10 days ago — should be a formatted date string, not "Nd ago".
    const result = relativeTime(isoSecondsAgo(10 * 24 * 3600));
    expect(result).not.toMatch(/\d+d ago/);
    expect(result.length).toBeGreaterThan(3);
  });
});

// ---- storageHealthTone ---------------------------------------

describe("storageHealthTone", () => {
  it("returns success for https_live", () => {
    expect(storageHealthTone("https_live")).toBe("success");
  });

  it("returns success for local_present", () => {
    expect(storageHealthTone("local_present")).toBe("success");
  });

  it("returns success for data_uri", () => {
    expect(storageHealthTone("data_uri")).toBe("success");
  });

  it("returns warning for https_expiring_soon", () => {
    expect(storageHealthTone("https_expiring_soon")).toBe("warning");
  });

  it("returns danger for https_expired", () => {
    expect(storageHealthTone("https_expired")).toBe("danger");
  });

  it("returns danger for local_missing", () => {
    expect(storageHealthTone("local_missing")).toBe("danger");
  });

  it("returns neutral for upload_pending", () => {
    expect(storageHealthTone("upload_pending")).toBe("neutral");
  });
});

// ---- assetRoleLabel ------------------------------------------

describe("assetRoleLabel", () => {
  it("returns human label for all defined roles", () => {
    expect(assetRoleLabel("talking_head")).toBe("Talking head");
    expect(assetRoleLabel("backdrop")).toBe("Backdrop");
    expect(assetRoleLabel("composite_output")).toBe("Composite output");
    expect(assetRoleLabel("polish_output")).toBe("Polish output");
    expect(assetRoleLabel("reference_image")).toBe("Reference image");
    expect(assetRoleLabel("b_roll")).toBe("B-roll");
    expect(assetRoleLabel("transcript")).toBe("Transcript");
    expect(assetRoleLabel("audio_track")).toBe("Audio track");
    expect(assetRoleLabel("raw_upload")).toBe("Raw upload");
    expect(assetRoleLabel("experiment")).toBe("Experiment");
    expect(assetRoleLabel("bridge_answer")).toBe("Engine bridge answer");
  });
});

// ---- SESSION 224 F-05 — enforce backend AssetRole mirror ------

/**
 * The SPA's ``ASSET_ROLES`` must exactly mirror the backend
 * ``apps.compositions.models.AssetRole`` values. F-05 (SESSION 224)
 * caught a live regression where C3 shipped ``BRIDGE_ANSWER`` to the
 * backend but forgot the SPA mirror, breaking the transcripts page
 * for any workspace that had ever invoked a bridge tool.
 *
 * BACKEND_ASSET_ROLES below is the authoritative list — it must
 * match ``apps.compositions.models.AssetRole`` exactly. When a new
 * role lands in the Django model + migration, update this list and
 * ``ASSET_ROLES`` in the same commit. This test then guarantees
 * both sides moved together.
 */
const BACKEND_ASSET_ROLES = [
  // Order + values must match apps/compositions/models.py::AssetRole
  // (regen anchor: run `python manage.py inventory` to see current set).
  "talking_head",
  "backdrop",
  "composite_output",
  "polish_output",
  "reference_image",
  "b_roll",
  "transcript",
  "audio_track",
  "raw_upload",
  "experiment",
  "bridge_answer",
] as const;

describe("ASSET_ROLES backend mirror (F-05 regression)", () => {
  it("matches backend apps.compositions.models.AssetRole exactly", () => {
    const spa = [...ASSET_ROLES].sort();
    const backend = [...BACKEND_ASSET_ROLES].sort();
    expect(spa).toEqual(backend);
  });

  it("assetRoleLabel returns a non-fallback label for every role", () => {
    // A missing entry causes the fallback (`role ?? role`) to return
    // the raw enum string — visible in the UI as e.g. "bridge_answer"
    // instead of "Engine bridge answer". Catch that here.
    for (const role of ASSET_ROLES) {
      const label = assetRoleLabel(role);
      expect(label).not.toBe(role);
    }
  });
});

// ---- assetTypeLabel ------------------------------------------

describe("assetTypeLabel", () => {
  it("returns human label for all defined types", () => {
    expect(assetTypeLabel("clip")).toBe("Clip");
    expect(assetTypeLabel("audio")).toBe("Audio");
    expect(assetTypeLabel("image")).toBe("Image");
    expect(assetTypeLabel("transcript")).toBe("Transcript");
    expect(assetTypeLabel("voice")).toBe("Voice");
  });
});

// ---- A6: workspaceAssetDetailSchema -------------------------

/** Minimal list-row fields shared by all detail payloads. */
function baseAssetPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: "11111111-0000-0000-0000-000000000001",
    asset_type: "clip",
    role: "talking_head",
    file_path: "https://cdn.example.com/clip.mp4",
    title: "Test clip",
    subject: "Test",
    duration_ms: 5000,
    width: 1920,
    height: 1080,
    mime_type: "video/mp4",
    size_bytes: 1048576,
    cost_micros: 80000,
    created_at: "2026-05-19T10:00:00Z",
    storage_health: "https_live",
    primitive_kind: "generate_avatar_speech",
    producing_prompt: "Say hello",
    composition: {
      id: "comp-1",
      name: "Hero ad",
      status: "done",
      template_kind: "talking_head",
    },
    producing_step: {
      id: "step-1",
      position: 1,
      primitive: "generate_avatar_speech",
      params: { script: "Hello!" },
      inputs: [{ asset_id: "00000000-0000-0000-0000-000000000099" }],
      source_spec: { primitive_kind: "generate_avatar_speech" },
    },
    downstream_compositions: [
      {
        id: "comp-downstream-1",
        name: "Polished output",
        status: "done",
        template_kind: "talking_head_polished",
      },
    ],
    inline_content: "",
    ...overrides,
  };
}

describe("workspaceAssetDetailSchema", () => {
  it("parses a well-formed detail payload", () => {
    const payload = baseAssetPayload();
    const result = workspaceAssetDetailSchema.parse(payload);
    expect(result.id).toBe("11111111-0000-0000-0000-000000000001");
    expect(result.producing_step).not.toBeNull();
    expect(result.producing_step?.primitive).toBe("generate_avatar_speech");
    expect(result.downstream_compositions).toHaveLength(1);
    expect(result.downstream_compositions[0]?.name).toBe("Polished output");
    expect(result.inline_content).toBe("");
  });

  it("parses a payload with null producing_step", () => {
    const payload = baseAssetPayload({ producing_step: null });
    const result = workspaceAssetDetailSchema.parse(payload);
    expect(result.producing_step).toBeNull();
  });

  it("parses a payload with empty downstream_compositions", () => {
    const payload = baseAssetPayload({ downstream_compositions: [] });
    const result = workspaceAssetDetailSchema.parse(payload);
    expect(result.downstream_compositions).toHaveLength(0);
  });

  it("parses a transcript asset with inline_content body", () => {
    const payload = baseAssetPayload({
      asset_type: "transcript",
      role: "transcript",
      inline_content: "Hello from the transcript body.",
      producing_step: null,
    });
    const result = workspaceAssetDetailSchema.parse(payload);
    expect(result.inline_content).toBe("Hello from the transcript body.");
  });
});

// ---- A6: getWorkspaceAsset URL construction ------------------

describe("getWorkspaceAsset", () => {
  const fetchedPaths: string[] = [];

  beforeEach(() => {
    fetchedPaths.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        fetchedPaths.push(url);
        return {
          ok: true,
          status: 200,
          json: async () => baseAssetPayload(),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits /api/workspace/assets/<id>/ without workspace param", async () => {
    await getWorkspaceAsset("asset-uuid-1");
    const path = fetchedPaths[0];
    expect(path).toBeDefined();
    expect(path!).toBe("/api/workspace/assets/asset-uuid-1/");
  });

  it("appends ?workspace= when provided", async () => {
    await getWorkspaceAsset("asset-uuid-2", "ws-abc-123");
    const path = fetchedPaths[0];
    expect(path).toBeDefined();
    expect(path!).toContain("/api/workspace/assets/asset-uuid-2/");
    expect(path!).toContain("workspace=ws-abc-123");
  });
});
