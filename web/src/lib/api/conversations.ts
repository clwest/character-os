/**
 * /api/conversations/ wrapper — K9 (knowledge arc).
 *
 * Backend surface: ``apps.conversations.views.ConversationThreadViewSet``
 * + the ``messages`` custom action. Threads CRUD via the
 * default router; messages list + send via
 * ``/api/conversations/<id>/messages/``.
 *
 * The send path is server-synchronous — the spokesperson
 * reply is generated + persisted in the same request that
 * creates the user message. The hook seeds the cache with
 * both messages on success so the chat view doesn't flash
 * an empty state between optimistic + confirmed.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Thread ------------------------------------------------------

const threadSchema = z.object({
  id: z.string(),
  spokesperson: z.string(),
  spokesperson_name: z.string(),
  title: z.string(),
  message_count: z.number().int(),
  last_message_preview: z.string(),
  created_at: z.string(),
  last_activity_at: z.string(),
});

export type ConversationThread = z.infer<typeof threadSchema>;

const threadListSchema = z.union([
  z.array(threadSchema),
  z.object({ results: z.array(threadSchema) }),
]);

function unwrapList(json: unknown): ConversationThread[] {
  const parsed = threadListSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

export interface ListThreadsOptions {
  spokesperson?: string;
}

export async function listThreads(
  options: ListThreadsOptions = {},
): Promise<ConversationThread[]> {
  const params = new URLSearchParams();
  if (options.spokesperson) params.set("spokesperson", options.spokesperson);
  const qs = params.toString();
  const path = qs ? `/api/conversations/?${qs}` : "/api/conversations/";
  return apiJson(path, {}, unwrapList);
}

export function useThreads(options: ListThreadsOptions = {}) {
  return useQuery({
    queryKey: ["conversations", options],
    queryFn: () => listThreads(options),
  });
}

export async function getThread(id: string): Promise<ConversationThread> {
  return apiJson(`/api/conversations/${id}/`, {}, (json) =>
    threadSchema.parse(json),
  );
}

export function useThread(id: string | undefined) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: () => getThread(id!),
    enabled: !!id,
  });
}

export interface CreateThreadInput {
  spokesperson: string;
  title?: string;
}

export async function createThread(
  input: CreateThreadInput,
): Promise<ConversationThread> {
  return apiJson(
    "/api/conversations/",
    { method: "POST", body: input },
    (json) => threadSchema.parse(json),
  );
}

export function useCreateThread() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createThread,
    onSuccess: (thread) => {
      qc.setQueryData(["conversation", thread.id], thread);
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

// ---- Messages ----------------------------------------------------

// K6.4 v1.1 — verifier surface. Each warning is one named
// entity in the synthesized reply that wasn't supported by
// the retrieved corpus.
const unsupportedClaimSchema = z.object({
  claim: z.string(),
  kind: z.string(),
  position: z.number().int(),
});

export type UnsupportedClaim = z.infer<typeof unsupportedClaimSchema>;

// K6.4 v1.2 — closes the SESSION 161 bypass-case audit gap.
// Empty string = pre-v1.2 row OR USER message (verifier only
// runs on spokesperson side). Four explicit states match
// apps.compositions.models.VerificationStatus.
export const verificationStatusSchema = z.enum([
  "",
  "verified",
  "trusted_passthrough",
  "skipped",
  "rejected",
]);

export type VerificationStatus = z.infer<typeof verificationStatusSchema>;

const messageSchema = z.object({
  id: z.string(),
  thread: z.string(),
  role: z.enum(["user", "spokesperson"]),
  content: z.string(),
  created_at: z.string(),
  // K6.5 / K6.4 v1.1 — exposed by ConversationMessageSerializer.
  // Optional + default empty so older messages that pre-date
  // K6.5 parse cleanly without a backfill.
  verification_warnings: z.array(unsupportedClaimSchema).default([]),
  rejected_synthesis: z.string().default(""),
  // K6.4 v1.2 — verification_status badge surface.
  verification_status: verificationStatusSchema.default(""),
});

export type ConversationMessage = z.infer<typeof messageSchema>;

// K6.4 v1.1 — 422 response body shape when strict mode rejects.
export const verifierRejectionSchema = z.object({
  mode: z.literal("strict"),
  rejected_synthesis: z.string(),
  unsupported_claims: z.array(unsupportedClaimSchema),
});

export type VerifierRejection = z.infer<typeof verifierRejectionSchema>;

export type VerifierMode = "strict" | "warn" | "off";

const messageListSchema = z.array(messageSchema);

export async function listMessages(
  threadId: string,
): Promise<ConversationMessage[]> {
  return apiJson(
    `/api/conversations/${threadId}/messages/`,
    {},
    (json) => messageListSchema.parse(json),
  );
}

export function useMessages(threadId: string | undefined) {
  return useQuery({
    queryKey: ["conversation-messages", threadId],
    queryFn: () => listMessages(threadId!),
    enabled: !!threadId,
  });
}

const sendResponseSchema = z.object({
  user_message: messageSchema,
  spokesperson_message: messageSchema,
  knowledge_chunk_ids: z.array(z.string()),
});

export type SendMessageResponse = z.infer<typeof sendResponseSchema>;

export interface SendMessageInput {
  threadId: string;
  content: string;
  // K6.4 v1.1 — per-request verifier mode override. ``null`` /
  // omitted = server default (settings.K6_CLAIM_VERIFIER_MODE,
  // falling back to "warn").
  verifierMode?: VerifierMode;
}

export async function sendMessage(
  input: SendMessageInput,
): Promise<SendMessageResponse> {
  const body: Record<string, unknown> = { content: input.content };
  if (input.verifierMode) body.verifier_mode = input.verifierMode;
  return apiJson(
    `/api/conversations/${input.threadId}/messages/`,
    { method: "POST", body },
    (json) => sendResponseSchema.parse(json),
  );
}

export function useSendMessage(threadId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { content: string; verifierMode?: VerifierMode }) =>
      sendMessage({ threadId: threadId!, ...input }),
    onSuccess: (response) => {
      // Append both new messages to the cached list so the
      // chat view re-renders without a re-fetch round-trip.
      qc.setQueryData<ConversationMessage[]>(
        ["conversation-messages", threadId],
        (prev) => [
          ...(prev ?? []),
          response.user_message,
          response.spokesperson_message,
        ],
      );
      // Invalidate the thread so message_count + preview
      // bump in the SPA's thread list.
      qc.invalidateQueries({ queryKey: ["conversation", threadId] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
