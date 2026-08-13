import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSession, signin, signout, signup } from "@/lib/api/auth";
import type { SigninInput, SignupInput } from "@/lib/api/auth";

const SESSION_KEY = ["session"] as const;

/**
 * Single source of truth for the SPA's auth state. allauth returns
 * a stable cookie-backed session; we cache forever and invalidate
 * on auth mutations. No polling, no refetch-on-focus drift.
 *
 * Per `docs/design/SPA_ARCHITECTURE.md` §"Auth state machine".
 */
export function useSession() {
  return useQuery({
    queryKey: SESSION_KEY,
    queryFn: getSession,
    staleTime: Infinity,
    retry: false,
  });
}

export function useSignup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: SignupInput) => signup(input),
    onSuccess: (state) => {
      qc.setQueryData(SESSION_KEY, state);
    },
  });
}

export function useSignin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: SigninInput) => signin(input),
    onSuccess: (state) => {
      qc.setQueryData(SESSION_KEY, state);
    },
  });
}

export function useSignout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: signout,
    onSuccess: () => {
      // Clear all server-state caches on sign-out; another user
      // signing in shouldn't see the previous user's data.
      qc.clear();
    },
  });
}
