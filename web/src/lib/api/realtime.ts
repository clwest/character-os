/**
 * /api/realtime_sessions/ wrapper — R3 broker + R8.0 SPA.
 *
 * Backend surface: ``apps.realtime.views.RealtimeSessionViewSet`` +
 * ``RealtimeToolInvocationViewSet``. R8.0 ships the basic session
 * lifecycle (create / retrieve / end); R8.1 + R8.2 add the
 * tool-invocation + cost-ticker surfaces.
 *
 * Contract rule 3 — ``provider_session_key`` lands ONLY in the
 * create response. Subsequent retrieves omit it. The SPA holds the
 * key in React state for the session's lifetime; never persists it,
 * never re-fetches it. After the SDK connects, the key has done its
 * job; leaving it in memory is acceptable for v1.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Schemas ----------------------------------------------------

// Canonical retrieve / list shape. Mirrors
// ``RealtimeSessionSerializer`` on the Django side.
const sessionSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  spokesperson: z.string(),
  spokesperson_name: z.string(),
  thread: z.string().nullable(),
  provider: z.string(),
  provider_session_id: z.string(),
  // provider_session_key INTENTIONALLY OMITTED on the
  // standard schema (rule 3).
  provider_document_id: z.string(),
  knowledge_chunk_ids: z.array(z.string()),
  status: z.enum([
    "draft",
    "creating",
    "not_ready",
    "ready",
    "ended",
    "failed",
  ]),
  error_message: z.string(),
  started_at: z.string().nullable(),
  ready_at: z.string().nullable(),
  ended_at: z.string().nullable(),
  expires_at: z.string().nullable(),
  cost_estimate_micros: z.number().int(),
  cost_actual_micros: z.number().int(),
  duration_seconds: z.number().int(),
  mock_mode: z.boolean(),
  transcript_asset: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  tool_invocations: z.array(z.unknown()).default([]),
});

export type RealtimeSession = z.infer<typeof sessionSchema>;
export type RealtimeSessionStatus = RealtimeSession["status"];

// Create-only shape — adds ``provider_session_key``.
// Returned by POST /api/realtime_sessions/ only.
const sessionWithKeySchema = sessionSchema.extend({
  provider_session_key: z.string(),
});

export type RealtimeSessionWithKey = z.infer<typeof sessionWithKeySchema>;

// ---- Create -----------------------------------------------------

export interface CreateSessionInput {
  spokesperson: string;
  personality?: string;
  start_script?: string;
  title?: string;
}

export async function createRealtimeSession(
  input: CreateSessionInput,
): Promise<RealtimeSessionWithKey> {
  return apiJson(
    "/api/realtime_sessions/",
    { method: "POST", body: input },
    (json) => sessionWithKeySchema.parse(json),
  );
}

export function useCreateRealtimeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createRealtimeSession,
    onSuccess: (session) => {
      // Seed the retrieve cache with the standard shape
      // (omits the key). The SDK consumer holds the key
      // in its own React state.
      const { provider_session_key: _key, ...rest } = session;
      qc.setQueryData(
        ["realtime-session", session.id],
        rest as RealtimeSession,
      );
    },
  });
}

// ---- Retrieve (with poll) ---------------------------------------

export async function getRealtimeSession(
  id: string,
): Promise<RealtimeSession> {
  return apiJson(`/api/realtime_sessions/${id}/`, {}, (json) =>
    sessionSchema.parse(json),
  );
}

export interface UseRealtimeSessionOptions {
  /** Poll interval while CREATING / NOT_READY. Default 1500ms. */
  pollIntervalMs?: number;
}

export function useRealtimeSession(
  id: string | undefined,
  options: UseRealtimeSessionOptions = {},
) {
  const { pollIntervalMs = 1500 } = options;
  return useQuery({
    queryKey: ["realtime-session", id],
    queryFn: () => getRealtimeSession(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return pollIntervalMs;
      // Only poll while we're advancing the state machine
      // toward READY. Terminal states are cached.
      return data.status === "creating" || data.status === "not_ready"
        ? pollIntervalMs
        : false;
    },
  });
}

// ---- End --------------------------------------------------------

export async function endRealtimeSession(
  id: string,
): Promise<RealtimeSession> {
  // POST `/end/` rather than DELETE — some auth proxies
  // strip DELETE. The Django side accepts both verbs (R3).
  return apiJson(
    `/api/realtime_sessions/${id}/end/`,
    { method: "POST", body: {} },
    (json) => sessionSchema.parse(json),
  );
}

export function useEndRealtimeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: endRealtimeSession,
    onSuccess: (session) => {
      qc.setQueryData(["realtime-session", session.id], session);
    },
  });
}

// ---- Tool dispatch (R8.1) ---------------------------------------

// Mirrors DispatchResult on the Django side
// (apps.realtime.views._serialize_dispatch_result).
const dispatchResultSchema = z.object({
  state: z.enum([
    "succeeded",
    "awaiting_approval",
    "failed",
    "queued",
    "rejected",
  ]),
  invocation_id: z.string(),
  tool_name: z.string(),
  cost_micros: z.number().int(),
  result: z.unknown().optional(),
  error_message: z.string().optional(),
  reason: z.string().optional(),
});

export type DispatchResult = z.infer<typeof dispatchResultSchema>;
export type DispatchState = DispatchResult["state"];

export interface InvokeToolInput {
  sessionId: string;
  tool_name: string;
  args?: Record<string, unknown>;
}

export async function invokeTool(
  input: InvokeToolInput,
): Promise<DispatchResult> {
  return apiJson(
    `/api/realtime_sessions/${input.sessionId}/invoke_tool/`,
    {
      method: "POST",
      body: { tool_name: input.tool_name, args: input.args ?? {} },
    },
    (json) => dispatchResultSchema.parse(json),
  );
}

export function useInvokeTool() {
  return useMutation({
    mutationFn: invokeTool,
  });
}

export async function approveInvocation(
  invocationId: string,
): Promise<DispatchResult> {
  return apiJson(
    `/api/realtime_tool_invocations/${invocationId}/approve/`,
    { method: "POST", body: {} },
    (json) => dispatchResultSchema.parse(json),
  );
}

export function useApproveInvocation() {
  return useMutation({
    mutationFn: approveInvocation,
  });
}

export interface RejectInvocationInput {
  invocationId: string;
  reason?: string;
}

export async function rejectInvocation(
  input: RejectInvocationInput,
): Promise<DispatchResult> {
  return apiJson(
    `/api/realtime_tool_invocations/${input.invocationId}/reject/`,
    {
      method: "POST",
      body: input.reason ? { reason: input.reason } : {},
    },
    (json) => dispatchResultSchema.parse(json),
  );
}

export function useRejectInvocation() {
  return useMutation({
    mutationFn: rejectInvocation,
  });
}
