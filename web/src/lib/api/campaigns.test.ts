/**
 * campaigns.ts unit tests — SESSION B3.7.
 *
 * Covers:
 *   - personalizedCampaignSchema Zod parsing
 *   - personalizedRecipientSchema Zod parsing
 *   - parseCsvResponseSchema (happy-path + header-error shape)
 *   - campaignStatusTone for all status values
 *   - campaignStatusLabel for all status values
 *   - parsePlaceholders — various template forms
 *   - listCampaigns URL construction + response parsing
 *   - createCampaign POST body
 *   - parseCsv POST body
 *   - deleteCampaign DELETE method
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  personalizedCampaignSchema,
  personalizedRecipientSchema,
  parseCsvResponseSchema,
  campaignStatusTone,
  campaignStatusLabel,
  parsePlaceholders,
  listCampaigns,
  createCampaign,
  parseCsv,
  deleteCampaign,
  CAMPAIGN_STATUSES,
} from "./campaigns";

// ---- Fixtures ------------------------------------------------

function makeCampaign(overrides: Record<string, unknown> = {}) {
  return {
    id: "c-00000000-0000-0000-0000-000000000001",
    workspace_id: "ws-00000000-0000-0000-0000-000000000001",
    spokesperson_id: "sp-00000000-0000-0000-0000-000000000001",
    spokesperson_name: "Sasha",
    name: "Q3 Outreach",
    template: "Hi {first_name}, saw {company} hit {milestone}.",
    placeholders: ["company", "first_name", "milestone"],
    status: "draft" as const,
    status_label: "Draft",
    recipient_counts: {
      pending: 0,
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
      total: 0,
    },
    launched_at: null,
    completed_at: null,
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

function makeRecipient(overrides: Record<string, unknown> = {}) {
  return {
    id: "r-00000000-0000-0000-0000-000000000001",
    campaign_id: "c-00000000-0000-0000-0000-000000000001",
    variables: { first_name: "Alice", company: "Acme", milestone: "Series B" },
    label: "Alice",
    rendered_script: "",
    position: 1,
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    error_message: "",
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

// ---- personalizedCampaignSchema ------------------------------

describe("personalizedCampaignSchema", () => {
  it("parses a well-formed draft campaign", () => {
    const result = personalizedCampaignSchema.parse(makeCampaign());
    expect(result.id).toBe("c-00000000-0000-0000-0000-000000000001");
    expect(result.status).toBe("draft");
    expect(result.placeholders).toEqual(["company", "first_name", "milestone"]);
    expect(result.launched_at).toBeNull();
  });

  it("parses an in_flight campaign with a launched_at date", () => {
    const result = personalizedCampaignSchema.parse(
      makeCampaign({ status: "in_flight", launched_at: "2026-05-19T11:00:00Z" }),
    );
    expect(result.status).toBe("in_flight");
    expect(result.launched_at).toBe("2026-05-19T11:00:00Z");
  });

  it("parses all valid status values", () => {
    for (const s of CAMPAIGN_STATUSES) {
      const result = personalizedCampaignSchema.parse(makeCampaign({ status: s }));
      expect(result.status).toBe(s);
    }
  });
});

// ---- personalizedRecipientSchema ----------------------------

describe("personalizedRecipientSchema", () => {
  it("parses a pending recipient", () => {
    const result = personalizedRecipientSchema.parse(makeRecipient());
    expect(result.status).toBe("pending");
    expect(result.produced_composition_id).toBeNull();
    expect(result.variables).toEqual({
      first_name: "Alice",
      company: "Acme",
      milestone: "Series B",
    });
  });

  it("parses a completed recipient with a composition id", () => {
    const result = personalizedRecipientSchema.parse(
      makeRecipient({
        status: "completed",
        produced_composition_id: "comp-uuid-1",
      }),
    );
    expect(result.status).toBe("completed");
    expect(result.produced_composition_id).toBe("comp-uuid-1");
  });

  it("parses a failed recipient with an error message", () => {
    const result = personalizedRecipientSchema.parse(
      makeRecipient({
        status: "failed",
        error_message: "Missing variable: milestone",
      }),
    );
    expect(result.status).toBe("failed");
    expect(result.error_message).toBe("Missing variable: milestone");
  });
});

// ---- parseCsvResponseSchema ---------------------------------

describe("parseCsvResponseSchema", () => {
  it("parses a happy-path response with recipients", () => {
    const payload = {
      header: ["first_name", "company", "milestone"],
      valid_count: 2,
      rejected_count: 0,
      rejected_rows: [],
      recipients: [makeRecipient(), makeRecipient({ id: "r-2", label: "Bob" })],
    };
    const result = parseCsvResponseSchema.parse(payload);
    expect(result.valid_count).toBe(2);
    expect(result.rejected_count).toBe(0);
    expect(result.recipients).toHaveLength(2);
    expect(result.header_error).toBeUndefined();
  });

  it("parses a header-error 400 shape", () => {
    const payload = {
      header_error: "CSV header missing required columns: milestone",
      header: ["first_name", "company"],
      valid_count: 0,
      rejected_count: 0,
      rejected_rows: [],
    };
    const result = parseCsvResponseSchema.parse(payload);
    expect(result.header_error).toBe("CSV header missing required columns: milestone");
    expect(result.valid_count).toBe(0);
  });

  it("parses a response with per-row rejections", () => {
    const payload = {
      header: ["first_name", "company"],
      valid_count: 1,
      rejected_count: 1,
      rejected_rows: [
        { row_number: 3, error: "Missing column: company", raw: "Bob," },
      ],
      recipients: [makeRecipient()],
    };
    const result = parseCsvResponseSchema.parse(payload);
    expect(result.rejected_count).toBe(1);
    expect(result.rejected_rows[0]?.row_number).toBe(3);
    expect(result.rejected_rows[0]?.error).toBe("Missing column: company");
  });
});

// ---- campaignStatusTone ------------------------------------

describe("campaignStatusTone", () => {
  it("returns muted for draft", () => {
    expect(campaignStatusTone("draft")).toBe("muted");
  });

  it("returns amber for launching, in_flight, partial", () => {
    expect(campaignStatusTone("launching")).toBe("amber");
    expect(campaignStatusTone("in_flight")).toBe("amber");
    expect(campaignStatusTone("partial")).toBe("amber");
  });

  it("returns success for completed", () => {
    expect(campaignStatusTone("completed")).toBe("success");
  });

  it("returns danger for failed", () => {
    expect(campaignStatusTone("failed")).toBe("danger");
  });
});

// ---- campaignStatusLabel ------------------------------------

describe("campaignStatusLabel", () => {
  it("returns human labels for all statuses", () => {
    expect(campaignStatusLabel("draft")).toBe("Draft");
    expect(campaignStatusLabel("launching")).toBe("Launching");
    expect(campaignStatusLabel("in_flight")).toBe("In Flight");
    expect(campaignStatusLabel("completed")).toBe("Completed");
    expect(campaignStatusLabel("partial")).toBe("Partial");
    expect(campaignStatusLabel("failed")).toBe("Failed");
  });
});

// ---- parsePlaceholders --------------------------------------

describe("parsePlaceholders", () => {
  it("extracts single placeholder", () => {
    expect(parsePlaceholders("Hi {first_name}!")).toEqual(["first_name"]);
  });

  it("extracts multiple unique placeholders (sorted)", () => {
    expect(parsePlaceholders("Hi {first_name}, saw {company}.")).toEqual([
      "company",
      "first_name",
    ]);
  });

  it("deduplicates repeated placeholders", () => {
    expect(parsePlaceholders("{name} and {name} again")).toEqual(["name"]);
  });

  it("ignores doubled-brace escapes", () => {
    expect(parsePlaceholders("Use {{literal}} not a var")).toEqual([]);
  });

  it("extracts real vars alongside escaped braces", () => {
    const result = parsePlaceholders("Hello {first_name}, {{company}} is literal.");
    expect(result).toEqual(["first_name"]);
  });

  it("returns empty array for plain text with no placeholders", () => {
    expect(parsePlaceholders("No placeholders here.")).toEqual([]);
  });

  it("handles underscore-separated names", () => {
    const result = parsePlaceholders("{company_name} and {arr_milestone}");
    expect(result).toEqual(["arr_milestone", "company_name"]);
  });
});

// ---- listCampaigns URL construction -------------------------

describe("listCampaigns", () => {
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
          json: async () => [makeCampaign()],
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits /api/campaigns/ without filter", async () => {
    await listCampaigns();
    expect(fetchedUrls[0]).toBe("/api/campaigns/");
  });

  it("appends ?status= when filter is provided", async () => {
    await listCampaigns({ status: "draft" });
    expect(fetchedUrls[0]).toContain("/api/campaigns/");
    expect(fetchedUrls[0]).toContain("status=draft");
  });

  it("returns a parsed array of campaigns", async () => {
    const results = await listCampaigns();
    expect(results).toHaveLength(1);
    expect(results[0]?.status).toBe("draft");
  });
});

// ---- createCampaign POST body -------------------------------

describe("createCampaign", () => {
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
          json: async () => makeCampaign(),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends POST to /api/campaigns/", async () => {
    await createCampaign({
      workspace_id: "ws-1",
      spokesperson_id: "sp-1",
      name: "My Campaign",
      template: "Hi {first_name}",
    });
    expect(capturedMethod).toBe("POST");
  });

  it("includes all required fields in the body", async () => {
    await createCampaign({
      workspace_id: "ws-1",
      spokesperson_id: "sp-1",
      name: "My Campaign",
      template: "Hi {first_name}",
    });
    const body = capturedBody as Record<string, unknown>;
    expect(body.workspace_id).toBe("ws-1");
    expect(body.spokesperson_id).toBe("sp-1");
    expect(body.name).toBe("My Campaign");
    expect(body.template).toBe("Hi {first_name}");
  });
});

// ---- parseCsv POST body -------------------------------------

describe("parseCsv", () => {
  let capturedUrl: string | undefined;
  let capturedBody: unknown;

  beforeEach(() => {
    capturedUrl = undefined;
    capturedBody = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedBody =
          typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            header: ["first_name"],
            valid_count: 1,
            rejected_count: 0,
            rejected_rows: [],
            recipients: [makeRecipient()],
          }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts to /api/campaigns/<id>/parse_csv/", async () => {
    await parseCsv("campaign-uuid-1", "first_name\nAlice");
    expect(capturedUrl).toContain("/api/campaigns/campaign-uuid-1/parse_csv/");
  });

  it("sends csv_text in the body", async () => {
    const csv = "first_name\nAlice";
    await parseCsv("campaign-uuid-1", csv);
    expect((capturedBody as Record<string, unknown>).csv_text).toBe(csv);
  });
});

// ---- deleteCampaign -----------------------------------------

describe("deleteCampaign", () => {
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
          status: 204,
          json: async () => null,
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends DELETE to /api/campaigns/<id>/", async () => {
    await deleteCampaign("campaign-uuid-delete");
    expect(capturedMethod).toBe("DELETE");
    expect(capturedUrl).toContain("/api/campaigns/campaign-uuid-delete/");
  });
});

// ---- B3.8: forecastSchema -----------------------------------

import {
  forecastSchema,
  launchResponseSchema,
  retryResponseSchema,
  getCampaignForecast,
  launchCampaign,
  retryRecipient,
  blockingReasonMessage,
  type BlockingReason,
} from "./campaigns";

function makeForecast(overrides: Record<string, unknown> = {}) {
  return {
    recipient_count: 3,
    batch_cap: 5,
    videos_per_month_limit: 30,
    videos_used_this_month: 5,
    videos_remaining: 25,
    projected_cost_micros: 750_000,
    per_recipient_cost_micros: 250_000,
    ready_to_launch: true,
    blocking_reason: null,
    ...overrides,
  };
}

describe("forecastSchema", () => {
  it("parses a ready-to-launch forecast", () => {
    const result = forecastSchema.parse(makeForecast());
    expect(result.ready_to_launch).toBe(true);
    expect(result.blocking_reason).toBeNull();
    expect(result.projected_cost_micros).toBe(750_000);
    expect(result.batch_cap).toBe(5);
  });

  it("parses a blocked forecast with no_recipients code", () => {
    const result = forecastSchema.parse(
      makeForecast({
        ready_to_launch: false,
        blocking_reason: {
          code: "no_recipients",
          message: "Campaign has no recipients.",
        },
      }),
    );
    expect(result.ready_to_launch).toBe(false);
    expect(result.blocking_reason?.code).toBe("no_recipients");
  });

  it("parses a blocked forecast with personalized_batch_too_large code", () => {
    const result = forecastSchema.parse(
      makeForecast({
        ready_to_launch: false,
        blocking_reason: {
          code: "personalized_batch_too_large",
          message: "Batch too large.",
        },
      }),
    );
    expect(result.blocking_reason?.code).toBe("personalized_batch_too_large");
  });

  it("parses a blocked forecast with video_limit_reached code", () => {
    const result = forecastSchema.parse(
      makeForecast({
        ready_to_launch: false,
        blocking_reason: {
          code: "video_limit_reached",
          message: "Limit reached.",
        },
      }),
    );
    expect(result.blocking_reason?.code).toBe("video_limit_reached");
  });

  it("parses null batch_cap (Agency tier — unlimited)", () => {
    const result = forecastSchema.parse(
      makeForecast({ batch_cap: null, videos_per_month_limit: null, videos_remaining: null }),
    );
    expect(result.batch_cap).toBeNull();
    expect(result.videos_remaining).toBeNull();
  });
});

// ---- B3.8: launchResponseSchema -----------------------------

describe("launchResponseSchema", () => {
  it("parses a successful launch response", () => {
    const result = launchResponseSchema.parse({
      campaign: makeCampaign({ status: "in_flight" }),
      queued_count: 3,
      failed_at_render_count: 0,
    });
    expect(result.queued_count).toBe(3);
    expect(result.campaign.status).toBe("in_flight");
  });

  it("parses launch response with some render failures", () => {
    const result = launchResponseSchema.parse({
      campaign: makeCampaign({ status: "in_flight" }),
      queued_count: 2,
      failed_at_render_count: 1,
    });
    expect(result.failed_at_render_count).toBe(1);
  });
});

// ---- B3.8: retryResponseSchema ------------------------------

describe("retryResponseSchema", () => {
  it("parses a retry response with queued recipient", () => {
    const result = retryResponseSchema.parse({
      recipient: makeRecipient({ status: "queued" }),
      campaign_status: "in_flight",
    });
    expect(result.recipient.status).toBe("queued");
    expect(result.campaign_status).toBe("in_flight");
  });
});

// ---- B3.8: getCampaignForecast ------------------------------

describe("getCampaignForecast", () => {
  let capturedUrl: string | undefined;

  beforeEach(() => {
    capturedUrl = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        capturedUrl = url;
        return {
          ok: true,
          status: 200,
          json: async () => makeForecast(),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits GET /api/campaigns/<id>/forecast/", async () => {
    await getCampaignForecast("campaign-uuid-1");
    expect(capturedUrl).toContain("/api/campaigns/campaign-uuid-1/forecast/");
  });

  it("returns parsed forecast", async () => {
    const result = await getCampaignForecast("campaign-uuid-1");
    expect(result.ready_to_launch).toBe(true);
    expect(result.recipient_count).toBe(3);
  });
});

// ---- B3.8: launchCampaign -----------------------------------

describe("launchCampaign", () => {
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
          json: async () => ({
            campaign: makeCampaign({ status: "in_flight" }),
            queued_count: 3,
            failed_at_render_count: 0,
          }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends POST to /api/campaigns/<id>/launch/", async () => {
    await launchCampaign("campaign-uuid-1");
    expect(capturedMethod).toBe("POST");
    expect(capturedUrl).toContain("/api/campaigns/campaign-uuid-1/launch/");
  });

  it("returns parsed launch response", async () => {
    const result = await launchCampaign("campaign-uuid-1");
    expect(result.queued_count).toBe(3);
    expect(result.campaign.status).toBe("in_flight");
  });
});

// ---- B3.8: retryRecipient -----------------------------------

describe("retryRecipient", () => {
  let capturedUrl: string | undefined;
  let capturedBody: unknown;

  beforeEach(() => {
    capturedUrl = undefined;
    capturedBody = undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedBody =
          typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            recipient: makeRecipient({ status: "queued" }),
            campaign_status: "in_flight",
          }),
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends POST to /api/campaigns/<id>/retry_recipient/", async () => {
    await retryRecipient("campaign-uuid-1", "recipient-uuid-1");
    expect(capturedUrl).toContain(
      "/api/campaigns/campaign-uuid-1/retry_recipient/",
    );
  });

  it("includes recipient_id in the body", async () => {
    await retryRecipient("campaign-uuid-1", "recipient-uuid-1");
    expect(
      (capturedBody as Record<string, unknown>).recipient_id,
    ).toBe("recipient-uuid-1");
  });
});

// ---- B3.8: blockingReasonMessage ----------------------------

describe("blockingReasonMessage", () => {
  const CODES: Array<[BlockingReason["code"], string]> = [
    ["no_recipients", "Add recipients"],
    ["campaign_not_draft", "Only DRAFT"],
    ["personalized_batch_too_large", "tier's per-launch limit"],
    ["video_limit_reached", "monthly video limit"],
  ];

  for (const [code, expectedSubstring] of CODES) {
    it(`returns a human-readable message for ${code}`, () => {
      const msg = blockingReasonMessage(code);
      expect(msg.toLowerCase()).toContain(expectedSubstring.toLowerCase());
    });
  }
});

