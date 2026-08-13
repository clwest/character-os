/**
 * /api/bootstrap-review/* wrapper — §19 Step 9.b.1 (SESSION 249).
 *
 * Read-only client for the frozen 9.a evidence browser. Uses
 * `frozen_candidate_id` per Finding 1 as the canonical candidate
 * identity — see SESSION_249_STEP_9B_ARCHITECTURE_PLAN.md.
 *
 * No decision endpoints. No promotion. No mutation. 9.b.1 is
 * READ-ONLY. Every hook here is `useQuery`; there are no mutations.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Enums mirrored from evidence.py --------------------------------

export const directionHypothesisSchema = z.enum([
  "identity_only",
  "softened_photographic",
]);
export type DirectionHypothesis = z.infer<typeof directionHypothesisSchema>;

export const providerNameSchema = z.enum([
  "stability_still",
  "runway_still_portrait",
]);
export type ProviderName = z.infer<typeof providerNameSchema>;

export const surfaceProfileSchema = z.enum([
  "compact",
  "team_card",
  "presence",
  "studio",
  "conversation",
]);
export type SurfaceProfile = z.infer<typeof surfaceProfileSchema>;

export const referenceKindSchema = z.enum(["portrait_reference"]);
export type ReferenceKind = z.infer<typeof referenceKindSchema>;

export const humanPurposeSchema = z.enum([
  "front",
  "slight_left",
  "slight_right",
  "neutral_rest",
  "listening",
  "consideration",
  "gentle_positive",
]);
export type HumanPurpose = z.infer<typeof humanPurposeSchema>;

export const HUMAN_PURPOSE_ORDER: HumanPurpose[] = [
  "front",
  "slight_left",
  "slight_right",
  "neutral_rest",
  "listening",
  "consideration",
  "gentle_positive",
];

// ---- Run metadata ---------------------------------------------------

const runSummarySchema = z.object({
  run_id: z.string(),
  run_fingerprint: z.string(),
  run_kind: z.string(),
  qualification_status: z.string(),
  execution_mode: z.object({
    requested: z.string().nullable(),
    contains_real_execution: z.boolean().nullable(),
    notice: z.string().nullable(),
  }),
  started_at_utc: z.string().nullable(),
  ended_at_utc: z.string().nullable(),
  fixtures: z.array(
    z.object({
      fixture_id: z.string(),
      branch: z.string(),
      content_hash: z.string(),
      spec_schema_version: z.number(),
    }),
  ),
  axes: z.object({
    directions: z.array(z.string()),
    providers: z.array(z.string()),
    purposes_by_branch: z.record(z.string(), z.array(z.string())),
    surface_profiles: z.array(z.string()),
    fixture_ids: z.array(z.string()),
  }),
  counts: z.object({
    planned: z.number().nullable(),
    by_outcome: z.record(z.string(), z.number()),
    by_provider: z.record(z.string(), z.record(z.string(), z.number())),
    by_profile: z.record(z.string(), z.record(z.string(), z.number())),
    by_direction: z.record(z.string(), z.record(z.string(), z.number())),
  }),
});
export type RunSummary = z.infer<typeof runSummarySchema>;

const runsListSchema = z.object({ runs: z.array(runSummarySchema) });

export function useBootstrapRuns() {
  return useQuery({
    queryKey: ["bootstrap-review", "runs"],
    queryFn: () =>
      apiJson("/api/bootstrap-review/runs/", { method: "GET" }, (json) =>
        runsListSchema.parse(json),
      ),
  });
}

export function useBootstrapRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["bootstrap-review", "runs", runId],
    enabled: Boolean(runId),
    queryFn: () =>
      apiJson(
        `/api/bootstrap-review/runs/${encodeURIComponent(runId!)}/`,
        { method: "GET" },
        (json) => runSummarySchema.parse(json),
      ),
  });
}

// ---- Fixture summary ------------------------------------------------

export const dispositionSchema = z.enum([
  "selected",
  "no_candidate_approved",
]);
export type Disposition = z.infer<typeof dispositionSchema>;

const decisionSchema = z
  .object({
    decision_id: z.string(),
    disposition: dispositionSchema,
    frozen_candidate_id: z.string().nullable(),
    supersedes_decision_id: z.string().nullable(),
    amendment_reason: z.string().nullable(),
    reviewer_user_id: z.number(),
    reviewer_email_at_write_time: z.string().nullable(),
    decided_at_utc: z.string(),
  })
  .nullable();
export type ReviewDecision = z.infer<typeof decisionSchema>;

const purposeSummarySchema = z.object({
  reference_kind: referenceKindSchema,
  reference_purpose: humanPurposeSchema,
  reviewable_candidate_count: z.number(),
  unsupported_evidence_count: z.number(),
  review_status: z.enum(["unreviewed", "selected", "no_candidate_approved"]),
  current_decision: decisionSchema,
});
export type PurposeSummary = z.infer<typeof purposeSummarySchema>;

const fixtureProgressSchema = z.object({
  purposes_total: z.number(),
  purposes_dispositioned: z.number(),
  review_complete: z.boolean(),
  approval_floor_pairs: z.array(z.string()),
  approval_floor_satisfied_pairs: z.array(z.string()),
  approval_floor_satisfied: z.boolean(),
});
export type FixtureProgress = z.infer<typeof fixtureProgressSchema>;

const canonicalMaterializationSchema = z.object({
  canonical_reference_floor_satisfied: z.boolean(),
  canonical_version_admitted: z.boolean(),
  publication_complete: z.boolean(),
  evidence_integrity: z.boolean(),
  step10_ready: z.boolean(),
  failures: z.array(z.string()),
});
export type CanonicalMaterialization = z.infer<
  typeof canonicalMaterializationSchema
>;

const fixtureSummarySchema = z.object({
  run_id: z.string(),
  fixture_id: z.string(),
  purposes: z.array(purposeSummarySchema),
  progress: fixtureProgressSchema,
  canonical_materialization: canonicalMaterializationSchema,
});
export type FixtureSummary = z.infer<typeof fixtureSummarySchema>;

export function useBootstrapFixture(
  runId: string | undefined,
  fixtureId: string | undefined,
) {
  return useQuery({
    queryKey: ["bootstrap-review", "runs", runId, "fixtures", fixtureId],
    enabled: Boolean(runId && fixtureId),
    queryFn: () =>
      apiJson(
        `/api/bootstrap-review/runs/${encodeURIComponent(runId!)}/fixtures/${encodeURIComponent(fixtureId!)}/`,
        { method: "GET" },
        (json) => fixtureSummarySchema.parse(json),
      ),
  });
}

// ---- Slot listing (candidate picker) --------------------------------

const artifactRefSchema = z
  .object({
    byte_count: z.number(),
    sha256_hex: z.string(),
  })
  .nullable();

const errorRefSchema = z
  .object({
    class: z.string(),
    message: z.string(),
  })
  .nullable();

const providerStageSchema = z.object({
  outcome: z.string(),
  provider_model: z.string().nullable(),
  requested_execution_mode: z.string().nullable(),
  actual_execution_mode: z.string().nullable(),
  elapsed_ms: z.number().nullable(),
  error: errorRefSchema,
});

const normalizationStageSchema = z.object({
  attempted: z.boolean().nullable(),
  outcome: z.string().nullable(),
  pipeline_version: z.string().nullable(),
  surface_profile_id: z.string().nullable(),
  surface_profile_version: z.number().nullable(),
  background_id: z.string().nullable(),
  failure: z.unknown().nullable(),
});

const candidateSchema = z.object({
  frozen_candidate_id: z.string(),
  cell_id: z.string(),
  run_id: z.string(),
  fixture_id: z.string(),
  direction_hypothesis: directionHypothesisSchema,
  provider: providerNameSchema,
  surface_profile: surfaceProfileSchema,
  reference_kind: referenceKindSchema,
  reference_purpose: humanPurposeSchema,
  outcome: z.string(),
  provider_stage: providerStageSchema,
  normalization_stage: normalizationStageSchema,
  raw_artifact: artifactRefSchema,
  normalized_artifact: artifactRefSchema,
  manifest_artifact: artifactRefSchema,
  factual_normalization_notices: z.array(z.string()),
});
export type Candidate = z.infer<typeof candidateSchema>;

const unsupportedGroupSchema = z.object({
  provider: providerNameSchema,
  error_class: z.string(),
  error_message: z.string(),
  count: z.number(),
  members: z.array(
    z.object({
      frozen_candidate_id: z.string(),
      direction: directionHypothesisSchema,
      surface_profile: surfaceProfileSchema,
    }),
  ),
});
export type UnsupportedGroup = z.infer<typeof unsupportedGroupSchema>;

const currentPromotionSchema = z
  .object({
    promotion_audit_id: z.string(),
    slot_revision: z.number(),
    substrate_committed_at_utc: z.string(),
    evidence_published_at_utc: z.string().nullable(),
    publication_status: z.enum(["published", "publication_pending"]),
  })
  .nullable();
export type CurrentPromotion = z.infer<typeof currentPromotionSchema>;

const slotDetailSchema = z.object({
  run_id: z.string(),
  fixture_id: z.string(),
  reference_kind: referenceKindSchema,
  reference_purpose: humanPurposeSchema,
  reviewable_candidates: z.array(candidateSchema),
  unsupported_evidence: z.array(candidateSchema),
  unsupported_summary: z.array(unsupportedGroupSchema),
  current_decision: decisionSchema,
  current_promotion: currentPromotionSchema,
  decision_history: z.array(decisionSchema),
});
export type SlotDetail = z.infer<typeof slotDetailSchema>;

export function useBootstrapSlot(
  runId: string | undefined,
  fixtureId: string | undefined,
  referenceKind: string | undefined,
  referencePurpose: string | undefined,
) {
  return useQuery({
    queryKey: [
      "bootstrap-review",
      "runs",
      runId,
      "fixtures",
      fixtureId,
      "slots",
      referenceKind,
      referencePurpose,
    ],
    enabled: Boolean(runId && fixtureId && referenceKind && referencePurpose),
    queryFn: () =>
      apiJson(
        `/api/bootstrap-review/runs/${encodeURIComponent(runId!)}/fixtures/${encodeURIComponent(fixtureId!)}/slots/${encodeURIComponent(referenceKind!)}/${encodeURIComponent(referencePurpose!)}/`,
        { method: "GET" },
        (json) => slotDetailSchema.parse(json),
      ),
  });
}

// ---- Artifact URL helpers (browser <img src> and <a href>) ---------

export function artifactUrl(
  fcid: string,
  kind: "raw.png" | "normalized.png" | "manifest.json" | "candidate.json",
): string {
  // frozen_candidate_id decomposes to 4 slash-separated components.
  // The artifact URL is already structured with those same 4
  // segments, so the value composes directly.
  return `/api/bootstrap-review/artifacts/${fcid}/${kind}`;
}

// ---- Decision mutation (9.b.2) --------------------------------------

const decisionResponseSchema = z.object({
  decision: decisionSchema.unwrap(),
  created: z.boolean(),
  review_run_id: z.string(),
});
export type DecisionResponse = z.infer<typeof decisionResponseSchema>;

export interface CreateDecisionInput {
  runId: string;
  fixtureId: string;
  referenceKind: string;
  referencePurpose: string;
  decisionId: string;
  disposition: Disposition;
  frozenCandidateId: string | null;
  supersedesDecisionId: string | null;
  amendmentReason: string | null;
}

// ---- 9.b.3b — Promote current decision at a slot ------------------

const promotionResultSchema = z.object({
  kind: z.string(),
  decision_id: z.string().nullable(),
  promotion_audit_id: z.string().nullable(),
  character_identity_version_id: z.string().nullable(),
  identity_reference_id: z.string().nullable(),
  superseded_identity_reference_id: z.string().nullable(),
  slot_revision: z.number().nullable(),
});
export type PromotionResult = z.infer<typeof promotionResultSchema>;

export interface PromoteSlotInput {
  runId: string;
  fixtureId: string;
  referenceKind: string;
  referencePurpose: string;
}

export function usePromoteSlot() {
  const qc = useQueryClient();
  return useMutation<PromotionResult, Error, PromoteSlotInput>({
    mutationFn: async (input) => {
      const url = `/api/bootstrap-review/runs/${encodeURIComponent(input.runId)}/fixtures/${encodeURIComponent(input.fixtureId)}/slots/${encodeURIComponent(input.referenceKind)}/${encodeURIComponent(input.referencePurpose)}/promote/`;
      return apiJson<PromotionResult>(
        url,
        { method: "POST" },
        (json) => promotionResultSchema.parse(json),
      );
    },
    onSuccess: (_data, input) => {
      qc.invalidateQueries({
        queryKey: [
          "bootstrap-review",
          "runs",
          input.runId,
          "fixtures",
          input.fixtureId,
          "slots",
          input.referenceKind,
          input.referencePurpose,
        ],
      });
      qc.invalidateQueries({
        queryKey: [
          "bootstrap-review",
          "runs",
          input.runId,
          "fixtures",
          input.fixtureId,
        ],
      });
    },
  });
}

// ---- 9.b.3b — Approve fixture identity version ---------------------

const approveVersionResultSchema = z.object({
  character_identity_version_id: z.string(),
  state: z.string(),
  already_approved: z.boolean(),
  approved_at: z.string().nullable().optional(),
});
export type ApproveVersionResult = z.infer<typeof approveVersionResultSchema>;

export interface ApproveFixtureVersionInput {
  runId: string;
  fixtureId: string;
}

export function useApproveFixtureVersion() {
  const qc = useQueryClient();
  return useMutation<ApproveVersionResult, Error, ApproveFixtureVersionInput>({
    mutationFn: async (input) => {
      const url = `/api/bootstrap-review/runs/${encodeURIComponent(input.runId)}/fixtures/${encodeURIComponent(input.fixtureId)}/approve-version/`;
      return apiJson<ApproveVersionResult>(
        url,
        { method: "POST" },
        (json) => approveVersionResultSchema.parse(json),
      );
    },
    onSuccess: (_data, input) => {
      qc.invalidateQueries({
        queryKey: [
          "bootstrap-review",
          "runs",
          input.runId,
          "fixtures",
          input.fixtureId,
        ],
      });
    },
  });
}

export function useCreateDecision() {
  const queryClient = useQueryClient();
  return useMutation<DecisionResponse, Error, CreateDecisionInput>({
    mutationFn: async (input) => {
      const url = `/api/bootstrap-review/runs/${encodeURIComponent(input.runId)}/fixtures/${encodeURIComponent(input.fixtureId)}/slots/${encodeURIComponent(input.referenceKind)}/${encodeURIComponent(input.referencePurpose)}/decisions/`;
      return apiJson<DecisionResponse>(
        url,
        {
          method: "POST",
          body: {
            decision_id: input.decisionId,
            disposition: input.disposition,
            frozen_candidate_id: input.frozenCandidateId,
            supersedes_decision_id: input.supersedesDecisionId,
            amendment_reason: input.amendmentReason,
          },
        },
        (json) => decisionResponseSchema.parse(json),
      );
    },
    onSuccess: (_data, input) => {
      // Refetch the slot + fixture summary so current_decision +
      // progress signals update immediately.
      queryClient.invalidateQueries({
        queryKey: [
          "bootstrap-review",
          "runs",
          input.runId,
          "fixtures",
          input.fixtureId,
          "slots",
          input.referenceKind,
          input.referencePurpose,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [
          "bootstrap-review",
          "runs",
          input.runId,
          "fixtures",
          input.fixtureId,
        ],
      });
    },
  });
}
