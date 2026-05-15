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

const messageSchema = z.object({
  id: z.string(),
  thread: z.string(),
  role: z.enum(["user", "spokesperson"]),
  content: z.string(),
  created_at: z.string(),
});

export type ConversationMessage = z.infer<typeof messageSchema>;

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
}

export async function sendMessage(
  input: SendMessageInput,
): Promise<SendMessageResponse> {
  return apiJson(
    `/api/conversations/${input.threadId}/messages/`,
    { method: "POST", body: { content: input.content } },
    (json) => sendResponseSchema.parse(json),
  );
}

export function useSendMessage(threadId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      sendMessage({ threadId: threadId!, content }),
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
