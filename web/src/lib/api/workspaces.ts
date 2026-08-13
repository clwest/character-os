/**
 * /api/me/ + /api/billing/subscription/ wrappers.
 *
 * Backend surface confirmed by `shell/apps/accounts/views.py::me`
 * and `shell/apps/billing/views.py::subscription` — both shipped
 * pre-SESSION 117. We don't extend them; the SPA hits both in
 * parallel via TanStack Query and the dashboard composes the
 * result.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- /api/me/ -------------------------------------------------------

const defaultWorkspaceSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  role: z.string().nullable(),
});

const meSchema = z.object({
  id: z.union([z.number(), z.string()]),
  email: z.string(),
  is_staff: z.boolean(),
  default_workspace: defaultWorkspaceSchema.nullable(),
});

export type Me = z.infer<typeof meSchema>;
export type DefaultWorkspace = z.infer<typeof defaultWorkspaceSchema>;

export async function getMe(): Promise<Me> {
  return apiJson("/api/me/", {}, (json) => meSchema.parse(json));
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: 5 * 60 * 1000, // workspace identity rarely changes
  });
}

// ---- /api/billing/subscription/ ------------------------------------

const subscriptionSchema = z.object({
  workspace_id: z.string(),
  workspace_name: z.string(),
  tier: z.string(),
  status: z.string(),
  videos_used: z.number().int().nonnegative(),
  videos_limit: z.number().int().nullable(),
  spokespeople_used: z.number().int().nonnegative(),
  spokespeople_limit: z.number().int().nullable(),
  period_start: z.string(),
  period_end: z.string(),
});

export type Subscription = z.infer<typeof subscriptionSchema>;

export async function getSubscription(): Promise<Subscription> {
  return apiJson(
    "/api/billing/subscription/",
    {},
    (json) => subscriptionSchema.parse(json),
  );
}

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: getSubscription,
    staleTime: 60 * 1000, // tier+usage refreshes more often than identity
  });
}
