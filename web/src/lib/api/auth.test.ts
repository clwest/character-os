/**
 * Schema-level smoke test. Confirms the zod schemas parse the
 * payloads `allauth.headless` actually returns. Sample payloads
 * were captured live SESSION 116 from a running stack via
 * `python manage.py smoke_headless_auth`.
 *
 * The point of this test isn't unit-testing zod (zod tests itself);
 * it's locking in the boundary contract so a future allauth
 * version bump that changes the response shape fails loud here
 * instead of silently in production.
 */
import { describe, expect, it } from "vitest";
import { __test__ } from "./auth";

const { sessionResponseSchema, toState } = __test__;

describe("auth schemas", () => {
  it("parses an unauthenticated session response", () => {
    const sample = {
      status: 401,
      data: { flows: [{ id: "login" }, { id: "signup" }] },
      meta: { is_authenticated: false },
    };
    const parsed = sessionResponseSchema.parse(sample);
    expect(toState(parsed)).toEqual({
      isAuthenticated: false,
      user: null,
      flows: [{ id: "login" }, { id: "signup" }],
    });
  });

  it("parses an authenticated session response", () => {
    const sample = {
      status: 200,
      data: {
        user: {
          id: 14,
          email: "smoke@character-os.test",
          username: "",
        },
      },
      meta: { is_authenticated: true },
    };
    const parsed = sessionResponseSchema.parse(sample);
    const state = toState(parsed);
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe("smoke@character-os.test");
    expect(state.flows).toEqual([]);
  });

  it("rejects a missing-status payload (contract drift signal)", () => {
    expect(() => sessionResponseSchema.parse({ data: {} })).toThrow();
  });
});
