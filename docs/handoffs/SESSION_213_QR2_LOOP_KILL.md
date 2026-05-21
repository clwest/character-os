---
title: "Session 213 — Q-r-2 loop kill + retrieval boost"
date: 2026-05-21
status: complete
session: 213
previous_handoff: ./SESSION_212_VO2_PLUS_REALTIME_CALIBRATION.md
---

# Session 213 — Q-r-2 loop kill (Fix 2A + 2C + 3B)

## TL;DR

Post-arc fix slice closing the `recall_knowledge` loop the
SESSION 212 Rigby + DealFlowTracker dogfood surfaced. Three
layered changes in one slice + one drift-sweep companion +
nine new tests.

| Commit | Slice |
|---|---|
| (pending) | feat(realtime): dispatch dedup + recall_knowledge tightened + top-K 30→50 |

**Test totals at SESSION 213 close**: Django **1423** (1414
→ 1423, +9). Media-engine **258** (unchanged). SPA vitest
**456** (unchanged).

**No real-mode spend.** Pure code/test slice; dogfood
verification queued for SESSION 214.

## Context

SESSION 212 ran the first real-mode realtime dogfood with
the operator-named keeper (Rigby). Eight sessions, ~$0.65
spend, six transcripts. The session 8 transcript captured
a worst-case Q-r-2 manifestation: when the operator asked
about a thin-knowledge product (DealFlowTracker, a single-
chunk stub), Rigby fired `recall_knowledge` 4x in 5 seconds
because:

1. The avatar can't see tool-result events back from the
   Runway SDK (Q-r-2, a known v1 limitation).
2. The single chunk in retrieval wasn't enough for Rigby to
   bridge verbally and continue.
3. The tool kept being re-invoked as the avatar tried to
   "get an answer" it could narrate.

The SESSION 212 handoff turned the finding into a fix-shaped
candidate (Fix 2A + 2C + 3B), which this session executes.

## What landed

### Fix 2A — dispatch dedup window

`apps/realtime/dispatch.py`:

* **`DEFAULT_DEDUP_WINDOW_SECONDS = 10`** constant +
  `_dedup_window_seconds()` indirection (mirrors the
  `_approval_threshold_micros()` shape established in R7.0).
* **`_find_recent_duplicate(session, tool_name, args)`** —
  most-recent `RealtimeToolInvocation` matching
  `(session, tool_name, args)` within the window, excluding
  terminal-failure states (FAILED / REJECTED — those are
  legitimate retries).
* **`dispatch_tool`** now consults dedup before the
  threshold gate. A hit returns a `DispatchResult` carrying
  the matched invocation's id + status (mapped via
  `_status_to_state`) plus a result dict with
  `already_returned: True` + `matched_invocation_id` hint
  keys. No new audit row.
* **`spec.dedup_enabled`** is consulted first — mutating
  tools opt out (see below).

What dedupes:
* `SUCCEEDED` — identical successful refire short-circuits.
* `AWAITING_APPROVAL` — operator must not see two modals
  for the same intent.
* `QUEUED` — async render isn't enqueued twice.
* `INVOKED` — in-flight inline tool isn't re-fired.

What does NOT dedupe:
* `FAILED` — second attempt is legitimate retry.
* `REJECTED` — operator declined; second avatar fire is
  legitimately re-asking.
* Outside the window — long-lull refires count fresh.
* Different `args` or different `session`.

### Fix 2A — `dedup_enabled` opt-out

`apps/realtime/tools/__init__.py`:

* New `ToolSpec.dedup_enabled: bool = True` field.
* New `register_tool(..., dedup_enabled=True)` kwarg.

`apps/realtime/tools/attach_memory.py`:

* `dedup_enabled=False`. Q-r-8 semantics are last-write-
  wins; firing twice with identical args is a legitimate
  "save again" and must produce a fresh Asset that
  replaces the prior one. The existing
  `test_attach_memory_idempotent_replaces_stale_asset`
  test verifies this end-to-end.

`render_video` keeps `dedup_enabled=True` (default). Its
$0.08/min cost crosses the approval threshold, so dedup
on `AWAITING_APPROVAL` is actively desired (no double
modal). The standard FAILED-doesn't-dedupe path covers
legitimate re-render scenarios.

### Fix 2C — `recall_knowledge` description

`apps/realtime/tools/recall_knowledge.py`:

* Description rewritten from 479 → 476 chars (under the
  500-char Pydantic cap on the media-engine schema). New
  load-bearing non-trigger: *"Do NOT invoke when the
  operator's question is answerable from the loaded
  document. Invoke only when the operator asks for a
  specific fact the document is silent on."*
* Mirrors the SESSION 212 description pattern that worked
  for `render_video` / `recall_recent_conversations`.
* The "50+ retrieval chunks" claim in the description
  hard-couples to Fix 3B's bump — if a future session
  walks the top_k back down, the description should be
  updated too (or the threshold logic moved to runtime).

### Fix 3B — `DEFAULT_TOP_K` 30 → 50

`character_os/realtime_document.py`:

* `DEFAULT_TOP_K = 50`. More chunks baked into the session
  document at create time. ~+10k chars per document
  observed; well within the 40k Runway cap (SESSION 212
  real-mode dogfood had ~25k headroom).
* The R6 memory composer's drop-order is unchanged
  (memory before knowledge tail under budget pressure).

### Drift-sweep companion — R6 budget test

`apps/realtime/tests/test_r6_session_memory.py`:

* `test_composer_drops_memory_first_under_budget`'s
  hardcoded `max_chars=250` was set pre-SESSION-212.
  SESSION 212's `## Conversation Style` block grew the
  realtime document header from ~50 chars to ~1160. The
  test was failing on `main` before SESSION 213 — the
  SESSION 212 commit's "Conversation Style section in
  test budget math" note didn't cover this specific
  budget test.
* Bumped `max_chars` 250 → 1300; comment updated. With
  header ≈1160, memory wrapper ≈250, and one-chunk
  knowledge ≈40, 1300 forces memory drop while leaving
  room for header + knowledge.

### Test surface

`apps/realtime/tests/test_session_213_dedup.py` (new file):

| Test | Asserts |
|---|---|
| `test_dedup_same_args_within_window_returns_cached_invocation` | identical refire returns first invocation id + hint; 1 row total |
| `test_dedup_preserves_spec_cost_attribution` | deduped result still surfaces `spec.cost_micros` for the SPA cost ticker |
| `test_dedup_misses_outside_window` | refire after window expires creates fresh row (uses `override_settings` for 1s window) |
| `test_dedup_misses_on_different_args` | distinct args refire normally |
| `test_dedup_misses_across_sessions` | session A's dedup doesn't bleed into session B |
| `test_dedup_misses_after_failed_invocation` | FAILED status doesn't block legitimate retry |
| `test_dedup_misses_after_rejected_invocation` | REJECTED status doesn't block legitimate retry |
| `test_dedup_skipped_when_tool_opts_out` | `dedup_enabled=False` always fires |
| `test_dedup_hits_awaiting_approval` | no double modal — AWAITING_APPROVAL dedupes |

`apps/realtime/tests/test_isolation.py`:

* New file added to `ALLOWED_FILES`. The new test creates
  `RealtimeSession` + one synthetic `RealtimeToolInvocation`
  row to exercise the dedup terminal-failure exclusion
  path. Workspace anchor flows through `_make_session`
  helper; signals fire normally.

## What I did NOT change

* **Per-tool dedup window override.** v1 ships one global
  setting (`REALTIME_TOOL_DEDUP_WINDOW_SECONDS`). If a
  future tool needs a tighter or looser window, it'll be
  one more field on `ToolSpec`. No use case yet.
* **Args-normalization.** Direct JSONField equality. If a
  future args shape includes timestamps or other
  ordering-sensitive fields, we'll switch to
  `json.dumps(args, sort_keys=True)` hashing.
* **`recall_knowledge` runtime threshold dialog.** The
  description hard-codes "50+ chunks" — if Fix 3B's
  top_k changes, the description should follow. Not
  fancy enough for plumbing through `ToolSpec` yet.
* **`render_video` dedup_enabled tuning.** Kept default
  True; the threshold + approval flow naturally serializes
  operator-initiated renders. If real-mode shows
  legitimate-rerender pressure, we'd flip it False then.

## Verification

| Suite | Pre-session | Post-session |
|---|---|---|
| Django (`shell/`) | 1414 | **1423** (+9) |
| Media-engine | 258 | 258 |
| SPA vitest | 456 | 456 |

* `python manage.py check` — 3 deprecation warnings,
  0 issues (pre-existing).
* `python manage.py migrate --check` — clean (no schema
  changes; new field on `ToolSpec` dataclass, not the
  DB model).
* Hygiene scan — empty.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated at
  session start + close.

## Calibration moments worth carrying

1. **Doctor doesn't catch test-suite drift.** SESSION 212
   shipped the Conversation Style block and updated some
   budget tests but not all of them. Doctor reported
   clean at SESSION 213 start; the R6 budget test only
   surfaced when I ran the full realtime suite. The
   session-start drift sweep should pair the doctor check
   with `pytest` against the arcs touched by the previous
   session's changes. Cheap insurance.

2. **Fix-shaped findings stack.** SESSION 212's handoff
   wrote Q-r-2 mitigation as Fix 2A / 2C / 3B with file
   paths, acceptance criteria, and effort sizing. SESSION
   213 executed them in one shot with no re-orientation.
   Continues the SESSION 210 streak (4 fixes closed via
   fix-shaped handoff candidates).

3. **`dedup_enabled` flag surfaced an architectural
   distinction.** Mutating tools (`attach_memory`) vs.
   read-only tools (`recall_knowledge`) have different
   semantics under retry. The flag makes the distinction
   explicit at registration. Future tool additions get a
   forcing function: "is this a re-fire-friendly mutation
   or a cacheable read?" — answer goes in the decorator.

4. **Pre-existing drift compounds when undetected.** The
   R6 budget test passed in SESSION 212's verification
   gate (the slice didn't touch r6 tests) but fell over
   on SESSION 213 because the cross-arc effect of the
   Conversation Style block wasn't caught. The
   doc-with-commit discipline catches narrative drift;
   the test-suite-against-arc discipline catches code
   drift. Both are needed.

## What's next

SESSION 214 should re-run the SESSION 212 Rigby /
DealFlowTracker scenario to verify the loop is dead in
real mode. Expected outcomes:

* `recall_knowledge` fires 0-1 times (vs. 4x in SESSION
  212). 0 if the boosted retrieval delivers the answer
  in the document; 1 if Rigby still chooses to look up
  + the second fire dedupes.
* Operator-side: no perceptible difference in latency
  (dedup short-circuits faster than a real lookup).
* Audit-row count: ≤1 `recall_knowledge` row per
  identical-args query (vs. up to 4 in SESSION 212).

If a NEW loop manifests on a different tool (the avatar
could shift the spam to `recall_recent_conversations` or
something else), Fix 2A applies to all tools by default
— no new code needed, just a new tool to add to the
opt-out list if it's stateful.

After SESSION 214 dogfood: VO.3 — `cta_swap` starter
+ recipe registry + `voice_picker` field type — is the
next queued FIRST THING from the VO-arc.

---

## Test counts

```
Django:        1423   (1414 → 1423, +9)
Media-engine:  258    (unchanged)
SPA vitest:    456    (unchanged)
```

## Files touched

```
shell/apps/realtime/dispatch.py                   +76
shell/apps/realtime/tools/__init__.py             +14
shell/apps/realtime/tools/attach_memory.py        +6
shell/apps/realtime/tools/recall_knowledge.py     +27 / -10
shell/character_os/realtime_document.py           +13 / -5
shell/apps/realtime/tests/test_isolation.py       +6
shell/apps/realtime/tests/test_r6_session_memory.py +13 / -5
shell/apps/realtime/tests/test_session_213_dedup.py +new
docs/design/REALTIME_AVATAR_V1.md                 +49
docs/CHARACTER_OS_INVENTORY.md                    regen
```
