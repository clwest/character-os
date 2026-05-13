/**
 * Auth client — talks to `/_allauth/browser/v1/*` (allauth.headless,
 * wired SESSION 114). Session-cookie auth; the SPA never persists a
 * token.
 *
 * Contract reference: `docs/design/MEDIA_ENGINE_INTERNAL_API.md` for
 * the principle (pure JSON in/out, normalised error shape) and
 * `docs/design/SPA_ARCHITECTURE.md` for the SPA-side application.
 */
import { z } from "zod";
import { apiFetch, apiJson, ApiError } from "./client";

// ---- Schemas --------------------------------------------------------

const flowSchema = z.object({
  id: z.string(),
  providers: z.array(z.string()).optional(),
});

const userSchema = z.object({
  id: z.union([z.string(), z.number()]),
  display: z.string().optional(),
  email: z.string().email().optional(),
  username: z.string().optional(),
});

// allauth wraps its payloads as `{status, data, meta?}`. The `meta`
// block carries `is_authenticated`; `data` carries flows when
// unauthenticated and the user record when authenticated.
const sessionResponseSchema = z.object({
  status: z.number(),
  data: z
    .object({
      user: userSchema.optional(),
      flows: z.array(flowSchema).optional(),
      methods: z.array(z.record(z.string(), z.unknown())).optional(),
    })
    .passthrough(),
  meta: z
    .object({
      is_authenticated: z.boolean(),
      session_token: z.string().optional(),
    })
    .passthrough()
    .optional(),
});

export type SessionResponse = z.infer<typeof sessionResponseSchema>;

export interface SessionState {
  isAuthenticated: boolean;
  user: z.infer<typeof userSchema> | null;
  flows: z.infer<typeof flowSchema>[];
}

function toState(payload: SessionResponse): SessionState {
  return {
    isAuthenticated: payload.meta?.is_authenticated ?? false,
    user: payload.data.user ?? null,
    flows: payload.data.flows ?? [],
  };
}

// ---- Operations -----------------------------------------------------

const BASE = "/_allauth/browser/v1";

export async function getSession(): Promise<SessionState> {
  // allauth returns 401 with `{flows: [...]}` when unauthenticated
  // and 200 with the user when authenticated. Both are valid; only
  // network or schema errors are exceptional.
  const resp = await apiFetch(`${BASE}/auth/session`);
  if (resp.status !== 200 && resp.status !== 401) {
    const body = await resp.json().catch(() => null);
    throw new ApiError(`GET ${BASE}/auth/session → ${resp.status}`, resp.status, body);
  }
  const json = await resp.json();
  return toState(sessionResponseSchema.parse(json));
}

export interface SignupInput {
  email: string;
  password: string;
}

export async function signup(input: SignupInput): Promise<SessionState> {
  const json = await apiJson<unknown>(`${BASE}/auth/signup`, {
    method: "POST",
    body: input,
  });
  return toState(sessionResponseSchema.parse(json));
}

export interface SigninInput {
  email: string;
  password: string;
}

export async function signin(input: SigninInput): Promise<SessionState> {
  const json = await apiJson<unknown>(`${BASE}/auth/login`, {
    method: "POST",
    body: input,
  });
  return toState(sessionResponseSchema.parse(json));
}

export async function signout(): Promise<void> {
  // allauth's session-delete endpoint. Returns 401 on success (the
  // session is gone, so the same probe is now unauthenticated) —
  // accept both 200 and 401 as success.
  const resp = await apiFetch(`${BASE}/auth/session`, { method: "DELETE" });
  if (resp.status !== 200 && resp.status !== 401) {
    const body = await resp.json().catch(() => null);
    throw new ApiError(`DELETE ${BASE}/auth/session → ${resp.status}`, resp.status, body);
  }
}

// ---- Test exports (for vitest) -------------------------------------

export const __test__ = { sessionResponseSchema, toState };
