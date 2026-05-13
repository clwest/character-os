/**
 * /api/videos/ wrapper.
 *
 * Backend surface: VideoViewSet (shell/apps/videos/views.py). Same
 * paginated-envelope tolerance pattern as spokespeople.ts.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

const videoSchema = z.object({
  id: z.string(),
  spokesperson: z.string(),
  spokesperson_name: z.string().optional(),
  workspace_id: z.string().optional(),
  title: z.string(),
  brief: z.string(),
  kind: z.string(),
  status: z.enum(["pending", "rendering", "ready", "failed", "archived"]),
  output_path: z.string(),
  duration_seconds: z.number().nullable(),
  tags: z.array(z.string()),
  media_engine_task_id: z.string(),
  error_message: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  completed_at: z.string().nullable(),
});

export type Video = z.infer<typeof videoSchema>;

const listResponseSchema = z.union([
  z.array(videoSchema),
  z.object({
    count: z.number().int().optional(),
    next: z.string().nullable().optional(),
    previous: z.string().nullable().optional(),
    results: z.array(videoSchema),
  }),
]);

function unwrapList(json: unknown): Video[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

export interface ListVideosOptions {
  limit?: number;
  spokesperson?: string;
}

export async function listVideos(options: ListVideosOptions = {}): Promise<Video[]> {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.spokesperson) params.set("spokesperson", options.spokesperson);
  const query = params.toString();
  const path = query ? `/api/videos/?${query}` : "/api/videos/";
  return apiJson(path, {}, unwrapList);
}

export function useVideos(options: ListVideosOptions = {}) {
  return useQuery({
    queryKey: ["videos", options],
    queryFn: () => listVideos(options),
  });
}
