/**
 * /api/videos/ wrapper.
 *
 * Backend surface: VideoViewSet (shell/apps/videos/views.py). Same
 * paginated-envelope tolerance pattern as spokespeople.ts.
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

// ---- Single-resource + polling (S-11) ------------------------------

const TERMINAL_STATUSES: Video["status"][] = ["ready", "failed", "archived"];

export async function getVideo(id: string): Promise<Video> {
  return apiJson(`/api/videos/${id}/`, {}, (json) => videoSchema.parse(json));
}

/**
 * Polling hook for the video status page. While the row is in a
 * non-terminal state, refetch every 2 s; halt as soon as we observe
 * a terminal one. This is the canonical fire-then-poll consumer the
 * SPA contract anticipates — every future async surface (voice
 * clone, future spider dashboards, etc.) should follow this shape.
 */
export function useVideo(id: string | undefined) {
  return useQuery({
    queryKey: ["video", id],
    queryFn: () => getVideo(id!),
    enabled: Boolean(id),
    // TanStack Query lets refetchInterval be a function of the
    // current data — return false to stop polling cleanly. The Celery
    // worker (SESSION 109) writes terminal state back to the row in
    // ~13 s mock / 60-120 s real.
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2_000;
      return TERMINAL_STATUSES.includes(data.status) ? false : 2_000;
    },
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

// ---- Create (S-12) -------------------------------------------------

export interface CreateVideoInput {
  spokesperson: string;
  title?: string;
  brief: string;
  /** v1 ships `spokesperson_ad` only — other kinds come in
   * subsequent slices. Leave undefined to use the model default. */
  kind?: string;
}

export async function createVideo(input: CreateVideoInput): Promise<Video> {
  return apiJson(
    "/api/videos/",
    { method: "POST", body: input },
    (json) => videoSchema.parse(json),
  );
}

export function useCreateVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createVideo,
    onSuccess: (video) => {
      // Seed the single-resource cache so the redirect renders
      // instantly (no flash of loading state).
      qc.setQueryData(["video", video.id], video);
      // Invalidate the list query so the dashboard's recent renders
      // refreshes when the user navigates back.
      qc.invalidateQueries({ queryKey: ["videos"] });
      // Subscription usage shifted (videos_used incremented).
      qc.invalidateQueries({ queryKey: ["subscription"] });
    },
  });
}
