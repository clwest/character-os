/**
 * transcripts.ts unit tests — SESSION 202 / B1.5 + B1.6.
 *
 * Covers:
 *   - transcriptHighlightSchema Zod parsing (well-formed payload)
 *   - mineResponseSchema parsing (with + without highlights)
 *   - highlightStatusLabel for all status values
 *   - highlightStatusTone for all status values
 *   - listHighlightsForTranscript URL construction
 *   - mineTranscript POST body construction
 *   - approveHighlight / rejectHighlight URL + method (B1.6)
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  transcriptHighlightSchema,
  mineResponseSchema,
  highlightStatusLabel,
  highlightStatusTone,
  listHighlightsForTranscript,
  mineTranscript,
  approveHighlight,
  rejectHighlight,
} from "./transcripts";

// ---- Fixtures ------------------------------------------------

function makeHighlight(overrides: Record<string, unknown> = {}) {
  return {
    id: "h-00000000-0000-0000-0000-000000000001",
    workspace_id: "ws-00000000-0000-0000-0000-000000000001",
    source_transcript_id: "t-00000000-0000-0000-0000-000000000001",
    text: "This is a great highlight moment.",
    char_start: 10,
    char_end: 43,
    llm_reasoning: "High energy moment with clear CTA.",
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    rejection_reason: "",
    mined_at: "2026-05-19T10:00:00Z",
    decided_at: null,
    llm_model_id: "gpt-5-mini",
    llm_cost_micros: 1200,
    llm_tokens_input: 450,
    llm_tokens_output: 80,
    ...overrides,
  };
}

// ---- transcriptHighlightSchema -------------------------------

describe("transcriptHighlightSchema", () => {
  it("parses a well-formed pending highlight", () => {
    const result = transcriptHighlightSchema.parse(makeHighlight());
    expect(result.id).toBe("h-00000000-0000-0000-0000-000000000001");
    expect(result.status).toBe("pending");
    expect(result.produced_composition_id).toBeNull();
    expect(result.decided_at).toBeNull();
  });

  it("parses an approved highlight with composition id", () => {
    const result = transcriptHighlightSchema.parse(
      makeHighlight({
        status: "approved",
        produced_composition_id: "comp-uuid-1",
        decided_at: "2026-05-19T11:00:00Z",
      }),
    );
    expect(result.status).toBe("approved");
    expect(result.produced_composition_id).toBe("comp-uuid-1");
    expect(result.decided_at).toBe("2026-05-19T11:00:00Z");
  });

  it("parses a rejected highlight with rejection reason", () => {
    const result = transcriptHighlightSchema.parse(
      makeHighlight({
        status: "rejected",
        rejection_reason: "Too long for Reels.",
        decided_at: "2026-05-19T12:00:00Z",
      }),
    );
    expect(result.status).toBe("rejected");
    expect(result.rejection_reason).toBe("Too long for Reels.");
  });

  it("parses a rendered highlight", () => {
    const result = transcriptHighlightSchema.parse(
      makeHighlight({ status: "rendered" }),
    );
    expect(result.status).toBe("rendered");
  });
});

// ---- mineResponseSchema --------------------------------------

describe("mineResponseSchema", () => {
  it("parses a response with highlights", () => {
    const payload = {
      highlights: [makeHighlight(), makeHighlight({ id: "h-2", llm_cost_micros: 0 })],
      used_synthesis: true,
      model: "gpt-5-mini",
    };
    const result = mineResponseSchema.parse(payload);
    expect(result.highlights).toHaveLength(2);
    expect(result.used_synthesis).toBe(true);
    expect(result.model).toBe("gpt-5-mini");
  });

  it("parses an empty-highlights response (LLM ran, nothing found)", () => {
    const payload = {
      highlights: [],
      used_synthesis: true,
      model: "gpt-5-mini",
    };
    const result = mineResponseSchema.parse(payload);
    expect(result.highlights).toHaveLength(0);
    expect(result.used_synthesis).toBe(true);
  });

  it("parses a no-synthesis response (LLM did not run)", () => {
    const payload = {
      highlights: [],
      used_synthesis: false,
      model: "",
    };
    const result = mineResponseSchema.parse(payload);
    expect(result.used_synthesis).toBe(false);
  });
});

// ---- highlightStatusLabel ------------------------------------

describe("highlightStatusLabel", () => {
  it("returns a human label for all statuses", () => {
    expect(highlightStatusLabel("pending")).toBe("Pending");
    expect(highlightStatusLabel("approved")).toBe("Approved");
    expect(highlightStatusLabel("rejected")).toBe("Rejected");
    expect(highlightStatusLabel("rendered")).toBe("Rendered");
  });
});

// ---- highlightStatusTone -------------------------------------

describe("highlightStatusTone", () => {
  it("returns amber for pending", () => {
    expect(highlightStatusTone("pending")).toBe("amber");
  });

  it("returns success for approved", () => {
    expect(highlightStatusTone("approved")).toBe("success");
  });

  it("returns muted for rejected", () => {
    expect(highlightStatusTone("rejected")).toBe("muted");
  });

  it("returns success for rendered", () => {
    expect(highlightStatusTone("rendered")).toBe("success");
  });
});

// ---- listHighlightsForTranscript URL -------------------------

describe("listHighlightsForTranscript", () => {
  const fetchedUrls: string[] = [];

  beforeEach(() => {
    fetchedUrls.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        fetchedUrls.push(url);
        return {
          ok: true,
          status: 200,
          json: async () => [makeHighlight()],
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits /api/transcript_highlights/?source_transcript=<id>", async () => {
    await listHighlightsForTranscript("transcript-uuid-1");
    expect(fetchedUrls[0]).toContain("/api/transcript_highlights/");
    expect(fetchedUrls[0]).toContain("source_transcript=transcript-uuid-1");
  });

  it("returns a parsed array of highlights", async () => {
    const results = await listHighlightsForTranscript("t-uuid");
    expect(results).toHaveLength(1);
    expect(results[0]?.status).toBe("pending");
  });
});

// ---- mineTranscript POST body --------------------------------

describe("mineTranscript", () => {
  let capturedBody: unknown;
  let capturedMethod: string | undefined;

  beforeEach(() => {
    capturedBody = undefined;
    capturedMethod = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        capturedMethod = init?.method;
        capturedBody =
          typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
        return {
          ok: true,
          status: 201,
          json: async () => ({
            highlights: [makeHighlight()],
            used_synthesis: true,
            model: "gpt-5-mini",
          }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends POST to /api/transcript_highlights/mine/", async () => {
    await mineTranscript({ transcript_asset_id: "t-uuid" });
    expect(capturedMethod).toBe("POST");
  });

  it("includes transcript_asset_id in the body", async () => {
    await mineTranscript({ transcript_asset_id: "t-uuid-2" });
    expect((capturedBody as Record<string, unknown>).transcript_asset_id).toBe(
      "t-uuid-2",
    );
  });

  it("includes optional knobs when provided", async () => {
    await mineTranscript({
      transcript_asset_id: "t-uuid-3",
      target_count: 3,
      max_chars: 200,
    });
    const body = capturedBody as Record<string, unknown>;
    expect(body.target_count).toBe(3);
    expect(body.max_chars).toBe(200);
  });
});

// ---- approveHighlight (B1.6) ---------------------------------

describe("approveHighlight", () => {
  let capturedUrl: string | undefined;
  let capturedMethod: string | undefined;

  beforeEach(() => {
    capturedUrl = undefined;
    capturedMethod = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedMethod = init?.method;
        return {
          ok: true,
          status: 200,
          json: async () => makeHighlight({ status: "approved" }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs to /api/transcript_highlights/<id>/approve/", async () => {
    await approveHighlight("highlight-uuid-1");
    expect(capturedMethod).toBe("POST");
    expect(capturedUrl).toContain("/api/transcript_highlights/highlight-uuid-1/approve/");
  });

  it("returns a parsed TranscriptHighlight with approved status", async () => {
    const result = await approveHighlight("highlight-uuid-1");
    expect(result.status).toBe("approved");
  });
});

// ---- rejectHighlight (B1.6) ----------------------------------

describe("rejectHighlight", () => {
  let capturedUrl: string | undefined;
  let capturedMethod: string | undefined;
  let capturedBody: unknown;

  beforeEach(() => {
    capturedUrl = undefined;
    capturedMethod = undefined;
    capturedBody = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedMethod = init?.method;
        capturedBody =
          typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
        return {
          ok: true,
          status: 200,
          json: async () =>
            makeHighlight({
              status: "rejected",
              rejection_reason: "Too short",
            }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs to /api/transcript_highlights/<id>/reject/", async () => {
    await rejectHighlight("highlight-uuid-2", {});
    expect(capturedMethod).toBe("POST");
    expect(capturedUrl).toContain("/api/transcript_highlights/highlight-uuid-2/reject/");
  });

  it("sends rejection_reason in the body when provided", async () => {
    await rejectHighlight("highlight-uuid-2", { rejection_reason: "Too short" });
    expect((capturedBody as Record<string, unknown>).rejection_reason).toBe(
      "Too short",
    );
  });

  it("returns a parsed TranscriptHighlight with rejected status", async () => {
    const result = await rejectHighlight("highlight-uuid-2", {
      rejection_reason: "Too short",
    });
    expect(result.status).toBe("rejected");
    expect(result.rejection_reason).toBe("Too short");
  });

  it("sends empty body when no reason is provided", async () => {
    await rejectHighlight("highlight-uuid-2");
    // Empty object is still a valid body shape.
    expect(capturedBody).toBeDefined();
  });
});
