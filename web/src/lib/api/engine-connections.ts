/**
 * /api/engine_connections/ wrapper — EB.4 (SESSION 218/2887).
 *
 * Backend surface: EngineConnectionViewSet
 * (shell/apps/realtime/views.py:690). Shipped in SESSION 217 as
 * EB.3; this SPA wrapper is EB.4.
 *
 * Covers:
 *   - List + retrieve  (GET  /api/engine_connections/, /:id/)
 *   - Create           (POST /api/engine_connections/)
 *   - Patch            (PATCH /api/engine_connections/:id/)
 *   - Delete           (DELETE /api/engine_connections/:id/)
 *   - Test ping        (POST /api/engine_connections/:id/test_ping/)
 *
 * Scope: docs/design/ENGINE_BRIDGE_V1.md §"API surface".
 *
 * Contract rules honored on the client side:
 *   - Rule 4: engine_token is write-only. GET responses expose only
 *     engine_token_preview (****last4). Never store or log the plaintext.
 *   - Rule 8: Pro+ tier gate. The SPA renders an upgrade nudge for
 *     Starter workspaces rather than firing 403-generating requests.
 *   - Rule 7: test_ping is a config-check, not a tool invocation.
 *     Does not create an audit row.
 *
 * Cache-invalidation discipline: every mutation invalidates the
 * ["engine-connections"] list key. Test-ping additionally invalidates
 * the single-row cache so last_tested_at + last_test_status refresh.
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Zod schemas ------------------------------------------------

export const ENGINE_KINDS = ["udb_pa"] as const;
export type EngineKind = (typeof ENGINE_KINDS)[number];

export const engineConnectionSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  engine_kind: z.enum(ENGINE_KINDS),
  engine_url: z.string(),
  engine_token_preview: z.string(),
  enabled: z.boolean(),
  label: z.string(),
  last_tested_at: z.string().nullable(),
  last_test_status: z.number().int().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type EngineConnection = z.infer<typeof engineConnectionSchema>;

/** POST /api/engine_connections/:id/test_ping/ response shape. */
export const testPingResponseSchema = z.object({
  status_code: z.number().int().nullable(),
  latency_ms: z.number().int().nonnegative(),
  response_preview: z.string(),
  error_message: z.string(),
});

export type TestPingResponse = z.infer<typeof testPingResponseSchema>;

// ---- Fetch helpers ---------------------------------------------

export async function listEngineConnections(): Promise<EngineConnection[]> {
  return apiJson(
    "/api/engine_connections/",
    {},
    (json) => z.array(engineConnectionSchema).parse(json),
  );
}

export interface CreateEngineConnectionInput {
  engine_url: string;
  engine_token: string;
  engine_kind?: EngineKind;
  label?: string;
  enabled?: boolean;
}

export async function createEngineConnection(
  input: CreateEngineConnectionInput,
): Promise<EngineConnection> {
  return apiJson(
    "/api/engine_connections/",
    { method: "POST", body: input },
    (json) => engineConnectionSchema.parse(json),
  );
}

export interface PatchEngineConnectionInput {
  engine_url?: string;
  engine_token?: string;
  enabled?: boolean;
  label?: string;
}

export async function patchEngineConnection(
  id: string,
  input: PatchEngineConnectionInput,
): Promise<EngineConnection> {
  return apiJson(
    `/api/engine_connections/${encodeURIComponent(id)}/`,
    { method: "PATCH", body: input },
    (json) => engineConnectionSchema.parse(json),
  );
}

export async function deleteEngineConnection(id: string): Promise<void> {
  await apiJson(
    `/api/engine_connections/${encodeURIComponent(id)}/`,
    { method: "DELETE" },
  );
}

export async function testPingEngineConnection(
  id: string,
): Promise<TestPingResponse> {
  return apiJson(
    `/api/engine_connections/${encodeURIComponent(id)}/test_ping/`,
    { method: "POST", body: {} },
    (json) => testPingResponseSchema.parse(json),
  );
}

// ---- React Query hooks -----------------------------------------

const LIST_KEY = ["engine-connections"] as const;

export function useEngineConnections() {
  return useQuery({
    queryKey: LIST_KEY,
    queryFn: listEngineConnections,
    staleTime: 30_000,
  });
}

export function useCreateEngineConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createEngineConnection,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
}

export function usePatchEngineConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; input: PatchEngineConnectionInput }) =>
      patchEngineConnection(args.id, args.input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
}

export function useDeleteEngineConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteEngineConnection,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
}

export function useTestPingEngineConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: testPingEngineConnection,
    // last_tested_at + last_test_status are stamped on the row server-side;
    // re-fetch the list so the UI reflects the fresh timestamps.
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });
}
