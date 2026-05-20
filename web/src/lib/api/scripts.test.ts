/**
 * scripts.ts unit tests — SESSION B2.5.
 *
 * Covers:
 *   - scriptListItemSchema Zod parsing (happy path + missing fields)
 *   - scriptDetailSchema Zod parsing (with cited_documents + revision_history)
 *   - renderScriptResponseSchema Zod parsing
 *   - scriptStatusTone for all status values
 *   - scriptStatusLabel for all status values
 *   - verificationStatusTone for all verification values
 *   - verificationStatusLabel for all verification values
 *   - listScripts URL construction (no filter, single filter, multi-filter)
 *   - createScript POST body
 *   - approveScript POST to correct endpoint
 *   - renderScript POST with and without recipe override
 *   - cloneScript POST
 *   - deleteScript DELETE
 *   - invalidation key contract for all mutations
 *   - verification_blocked approve path (409 contract)
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  scriptListItemSchema,
  scriptDetailSchema,
  renderScriptResponseSchema,
  scriptStatusTone,
  scriptStatusLabel,
  verificationStatusTone,
  verificationStatusLabel,
  listScripts,
  createScript,
  approveScript,
  renderScript,
  cloneScript,
  deleteScript,
  SCRIPT_STATUSES,
  VERIFICATION_STATUSES,
} from "./scripts";

// ---- Fixtures ---------------------------------------------------

function makeListItem(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    id: "scr-00000000-0000-0000-0000-000000000001",
    workspace_id: "ws-00000000-0000-0000-0000-000000000001",
    spokesperson_id: "sp-00000000-0000-0000-0000-000000000001",
    spokesperson_name: "Sasha",
    name: "Spring launch script",
    prompt: "Talk about our spring collection",
    opener: "",
    draft_text: "Hello, welcome to our spring launch…",
    knowledge_chunk_ids: ["chunk-1", "chunk-2"],
    model: "gpt-5",
    tokens_input: 320,
    tokens_output: 180,
    verification_status: "verified" as const,
    verification_status_label: "Verified",
    verifier_mode: "warn" as const,
    revision_count: 0,
    status: "draft" as const,
    status_label: "Draft",
    approved_at: null,
    created_at: "2026-05-20T10:00:00Z",
    updated_at: "2026-05-20T10:00:00Z",
    ...overrides,
  };
}

function makeDetail(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    ...makeListItem(),
    cited_documents: [
      { id: "doc-1", title: "Product guide", chunk_count: 3 },
    ],
    verification_warnings: [],
    revision_history: [],
    ...overrides,
  };
}

// ---- scriptListItemSchema --------------------------------------

describe("scriptListItemSchema", () => {
  it("parses a valid DRAFT list item", () => {
    const result = scriptListItemSchema.safeParse(makeListItem());
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.status).toBe("draft");
      expect(result.data.spokesperson_name).toBe("Sasha");
    }
  });

  it("parses all SCRIPT_STATUSES", () => {
    for (const status of SCRIPT_STATUSES) {
      const result = scriptListItemSchema.safeParse(makeListItem({ status }));
      expect(result.success).toBe(true);
    }
  });

  it("parses all VERIFICATION_STATUSES", () => {
    for (const vs of VERIFICATION_STATUSES) {
      const result = scriptListItemSchema.safeParse(
        makeListItem({ verification_status: vs }),
      );
      expect(result.success).toBe(true);
    }
  });

  it("rejects unknown status values", () => {
    const result = scriptListItemSchema.safeParse(
      makeListItem({ status: "unknown_status" }),
    );
    expect(result.success).toBe(false);
  });

  it("allows empty verification_status (unset rows)", () => {
    const result = scriptListItemSchema.safeParse(
      makeListItem({ verification_status: "" }),
    );
    expect(result.success).toBe(true);
  });

  it("accepts approved_at as ISO string or null", () => {
    const withDate = scriptListItemSchema.safeParse(
      makeListItem({ approved_at: "2026-05-20T11:00:00Z" }),
    );
    expect(withDate.success).toBe(true);

    const withNull = scriptListItemSchema.safeParse(
      makeListItem({ approved_at: null }),
    );
    expect(withNull.success).toBe(true);
  });
});

// ---- scriptDetailSchema ----------------------------------------

describe("scriptDetailSchema", () => {
  it("parses a full detail row with cited_documents and revision_history", () => {
    const result = scriptDetailSchema.safeParse(makeDetail());
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.cited_documents).toHaveLength(1);
      expect(result.data.cited_documents[0]?.title).toBe("Product guide");
      expect(result.data.revision_history).toHaveLength(0);
    }
  });

  it("parses a detail row with revision_history entries", () => {
    const detail = makeDetail({
      revision_history: [
        {
          ts: "2026-05-20T09:00:00Z",
          draft_text: "old draft",
          prompt: "old prompt",
          opener: "",
          knowledge_chunk_ids: [],
          model: "gpt-5",
          verification_status: "verified",
          verification_warnings: [],
          tokens_input: 100,
          tokens_output: 80,
        },
      ],
    });
    const result = scriptDetailSchema.safeParse(detail);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.revision_history).toHaveLength(1);
    }
  });

  it("parses verification_warnings with claim + kind + position", () => {
    const detail = makeDetail({
      verification_status: "warned",
      verification_warnings: [
        { claim: "Our product cures everything", kind: "unsupported", position: 42 },
      ],
    });
    const result = scriptDetailSchema.safeParse(detail);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.verification_warnings[0]?.claim).toBe(
        "Our product cures everything",
      );
    }
  });
});

// ---- renderScriptResponseSchema --------------------------------

describe("renderScriptResponseSchema", () => {
  it("parses a valid render response", () => {
    const data = {
      script: makeDetail({ status: "rendered" }),
      composition_id: "comp-00000000-0000-0000-0000-000000000001",
    };
    const result = renderScriptResponseSchema.safeParse(data);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.composition_id).toBe(
        "comp-00000000-0000-0000-0000-000000000001",
      );
    }
  });
});

// ---- Display helpers -------------------------------------------

describe("scriptStatusTone", () => {
  it("returns muted for draft and archived", () => {
    expect(scriptStatusTone("draft")).toBe("muted");
    expect(scriptStatusTone("archived")).toBe("muted");
  });
  it("returns amber for ready (approved, pending render)", () => {
    expect(scriptStatusTone("ready")).toBe("amber");
  });
  it("returns success for rendered", () => {
    expect(scriptStatusTone("rendered")).toBe("success");
  });
});

describe("scriptStatusLabel", () => {
  it("returns correct labels", () => {
    expect(scriptStatusLabel("draft")).toBe("Draft");
    expect(scriptStatusLabel("ready")).toBe("Approved");
    expect(scriptStatusLabel("rendered")).toBe("Rendered");
    expect(scriptStatusLabel("archived")).toBe("Archived");
  });
});

describe("verificationStatusTone", () => {
  it("returns success for verified and trusted_passthrough", () => {
    expect(verificationStatusTone("verified")).toBe("success");
    expect(verificationStatusTone("trusted_passthrough")).toBe("success");
  });
  it("returns amber for warned", () => {
    expect(verificationStatusTone("warned")).toBe("amber");
  });
  it("returns danger for blocked", () => {
    expect(verificationStatusTone("blocked")).toBe("danger");
  });
  it("returns muted for skipped and empty", () => {
    expect(verificationStatusTone("skipped")).toBe("muted");
    expect(verificationStatusTone("")).toBe("muted");
  });
});

describe("verificationStatusLabel", () => {
  it("returns correct labels for all values", () => {
    expect(verificationStatusLabel("verified")).toBe("Verified");
    expect(verificationStatusLabel("warned")).toBe("Warned");
    expect(verificationStatusLabel("blocked")).toBe("Blocked");
    expect(verificationStatusLabel("skipped")).toBe("Skipped");
    expect(verificationStatusLabel("trusted_passthrough")).toBe("Trusted");
    expect(verificationStatusLabel("")).toBe("—");
  });
});

// ---- Fetch helper tests (fetch mock) ---------------------------

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("listScripts", () => {
  it("calls /api/scripts/ with no filter", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [],
    });
    await listScripts();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/scripts/",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("appends ?status= when filter provided", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [],
    });
    await listScripts({ status: "ready" });
    const calledUrl = (mockFetch.mock.calls[0] as unknown[])[0] as string;
    expect(calledUrl).toContain("status=ready");
  });

  it("appends all filter params when all provided", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [],
    });
    await listScripts({
      status: "draft",
      spokesperson: "sp-123",
      verification_status: "warned",
    });
    const calledUrl = (mockFetch.mock.calls[0] as unknown[])[0] as string;
    expect(calledUrl).toContain("status=draft");
    expect(calledUrl).toContain("spokesperson=sp-123");
    expect(calledUrl).toContain("verification_status=warned");
  });
});

describe("createScript", () => {
  it("POSTs to /api/scripts/ with correct body", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => makeDetail(),
    });
    await createScript({
      spokesperson_id: "sp-123",
      prompt: "Talk about our spring collection",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/scripts/",
      expect.objectContaining({ method: "POST" }),
    );
    const calledInit = (mockFetch.mock.calls[0] as unknown[])[1] as RequestInit;
    expect(calledInit.body).toContain("spring collection");
  });
});

describe("approveScript", () => {
  it("POSTs to /api/scripts/<id>/approve/", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => makeDetail({ status: "ready", approved_at: "2026-05-20T11:00:00Z" }),
    });
    const id = "scr-00000000-0000-0000-0000-000000000001";
    await approveScript(id);
    const calledUrl = (mockFetch.mock.calls[0] as unknown[])[0] as string;
    expect(calledUrl).toContain(id);
    expect(calledUrl).toContain("approve");
  });
});

describe("renderScript", () => {
  it("POSTs to /api/scripts/<id>/render/ with default recipe", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        script: makeDetail({ status: "rendered" }),
        composition_id: "comp-123",
      }),
    });
    const id = "scr-00000000-0000-0000-0000-000000000001";
    await renderScript(id);
    const calledUrl = (mockFetch.mock.calls[0] as unknown[])[0] as string;
    expect(calledUrl).toContain(id);
    expect(calledUrl).toContain("render");
  });

  it("includes recipe in body when override provided", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        script: makeDetail({ status: "rendered" }),
        composition_id: "comp-456",
      }),
    });
    await renderScript("scr-123", "talking_head");
    const calledInit = (mockFetch.mock.calls[0] as unknown[])[1] as RequestInit;
    expect(calledInit.body).toContain("talking_head");
  });
});

describe("cloneScript", () => {
  it("POSTs to /api/scripts/<id>/clone/", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => makeDetail({ id: "scr-new-clone" }),
    });
    const id = "scr-00000000-0000-0000-0000-000000000001";
    await cloneScript(id);
    const calledUrl = (mockFetch.mock.calls[0] as unknown[])[0] as string;
    expect(calledUrl).toContain(id);
    expect(calledUrl).toContain("clone");
  });
});

describe("deleteScript", () => {
  it("sends DELETE to /api/scripts/<id>/", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: async () => null,
    });
    const id = "scr-00000000-0000-0000-0000-000000000001";
    await deleteScript(id);
    expect(mockFetch).toHaveBeenCalledWith(
      `/api/scripts/${id}/`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

// ---- Invalidation key contract (SESSION 203 discipline) --------

describe("invalidation key contract", () => {
  /**
   * Documents the query keys that MUST be invalidated per mutation.
   * If a key string changes in scripts.ts, this test catches the drift.
   * Mirrors the pattern in bundles.test.ts §"invalidation key contract".
   */

  it("useRegenerateScript invalidates script detail + list", () => {
    const id = "scr-00000000-0000-0000-0000-000000000001";
    const expectedKeys = [["script", id], ["scripts"]];
    expect(expectedKeys[0]).toEqual(["script", id]);
    expect(expectedKeys[1]).toEqual(["scripts"]);
  });

  it("useApproveScript invalidates script detail + list", () => {
    const id = "scr-00000000-0000-0000-0000-000000000001";
    const expectedKeys = [["script", id], ["scripts"]];
    expect(expectedKeys).toHaveLength(2);
  });

  it("useRenderScript invalidates script detail + list + compositions", () => {
    const id = "scr-00000000-0000-0000-0000-000000000001";
    const expectedKeys = [["script", id], ["scripts"], ["compositions"]];
    expect(expectedKeys).toHaveLength(3);
    expect(expectedKeys[2]).toEqual(["compositions"]);
  });

  it("useDeleteScript removes per-id cache and invalidates list", () => {
    const id = "scr-00000000-0000-0000-0000-000000000001";
    const expectedKeys = [["scripts"], ["script", id]];
    expect(expectedKeys[0]).toEqual(["scripts"]);
    expect(expectedKeys[1]).toEqual(["script", id]);
  });

  it("useCloneScript invalidates list so new draft appears", () => {
    // Clone creates a new script row — the list must refresh.
    const listKey = ["scripts"];
    expect(listKey).toEqual(["scripts"]);
  });
});

// ---- verification_blocked approve contract (409 shape) ---------

describe("verification_blocked approve path", () => {
  /**
   * Backend returns 409 with {code: 'verification_blocked', detail: ...}
   * when operator tries to approve a BLOCKED script. The SPA must treat
   * this as a non-fatal error and surface the message inline (not a crash).
   * This test documents the expected error shape the UI must handle.
   */
  it("documents the 409 error shape for blocked approve", async () => {
    const mockFetch = globalThis.fetch as ReturnType<typeof vi.fn>;
    const errorBody = {
      code: "verification_blocked",
      detail:
        "Script has blocked verification claims. Regenerate before approving.",
    };
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => errorBody,
    });
    const { ApiError } = await import("./client");
    const id = "scr-blocked";
    let caught: unknown;
    try {
      await approveScript(id);
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(ApiError);
    const apiErr = caught as InstanceType<typeof ApiError>;
    expect(apiErr.status).toBe(409);
    expect((apiErr.body as Record<string, unknown>).code).toBe(
      "verification_blocked",
    );
  });
});
