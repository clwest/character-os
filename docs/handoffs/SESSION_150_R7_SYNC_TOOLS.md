---
title: "Session 150 — R7.1 sync tools + tier-aware filtering"
date: 2026-05-15
status: complete
session: 150
previous_handoff: ./SESSION_149_R7_FOUNDATION.md
---

# Session 150 — R7.1 sync tools + tier-aware filtering

## TL;DR

Single-slice session. R7.1 shipped three sync tools on
top of R7.0's dispatch foundation, plus tier-aware
filtering that resolves Q-r-4 (per-workspace tool
catalog overrides).

The avatar's tool catalog is now four tools across two
tiers:

| Tool | Tier | Cost | Sync/Async |
|---|---|---|---|
| `show_videos_tab` | starter | $0 | sync |
| `recall_knowledge` | starter | ~$0.001 | sync |
| `recall_recent_conversations` | starter | $0 | sync |
| `handoff_to_spokesperson` | **pro** | $0 | sync |

Two more tools (R7.2: `render_video` + `attach_memory`)
arrive via Celery in a future session. The realtime arc
is now feature-complete for Starter-tier text/RAG use
cases; Pro-tier adds handoff; async actions remain.

613 backend tests (+17 from R7.1). No new migrations,
Celery tasks, media-engine routes, or force-mock flags.

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `611ae94` | R7.1 feat — three sync tools + ToolSpec.tier_required + _TIER_RANK + get_workspace_tools tier filtering + dispatcher tier defense-in-depth + apps.billing.services.get_workspace_tier helper + 17 tests + design-doc slice-table + change-log + 3 ALLOWED_FILES additions + 1 R7.0 test renamed |
| 2 | (this commit) | SESSION 150 handoff + start-here rewrite + 611ae94 SHA backfill + INVENTORY regen + CLAUDE.md row bump |

## What R7.1 ships

### Three sync tools

**`recall_knowledge`** — RAG against the K2 retrieval
surface. The avatar calls it mid-conversation when it
needs to look up a fact from workspace knowledge.
Honors `EMBEDDING_FORCE_MOCK` automatically (retrieval
module checks internally). Empty query →
`ValueError("query is required")` → dispatcher records
the audit row as FAILED. Returns
`{query, count, matches: [{chunk_id, document_id,
document_title, text}]}` — structured for the SPA to
render a citation list.

**`recall_recent_conversations`** — reads prior ENDED
`RealtimeSession` rows with attached `Asset(TRANSCRIPT)`
for this spokesperson. Distinct from R6's
`compose_session_memory` (which composes a summarized
projection at session-create); this tool returns
per-session previews newest-first, so the avatar can
quote a specific prior conversation. Excludes the
current session by pk. Each preview capped at 500
chars.

**`handoff_to_spokesperson`** — returns a structured
nav event the SPA dispatches on. **Pro tier only** —
Starter has `spokespeople=1` in TIER_LIMITS, so
handoff is structurally meaningless. Cross-workspace
target rejected with `"not in this workspace"` (message
intentionally doesn't leak existence of other-workspace
spokespeople). Same-spokesperson target rejected.

### Tier infrastructure (Q-r-4 resolution)

```python
@dataclass(frozen=True, slots=True)
class ToolSpec:
    # ... existing fields ...
    tier_required: str = "starter"

_TIER_RANK = {"starter": 0, "pro": 1, "agency": 2}

def get_workspace_tools(workspace) -> list[ToolSpec]:
    rank = _tier_rank(get_workspace_tier(workspace))
    return [s for s in list_tools()
            if _tier_rank(s.tier_required) <= rank]
```

`_tier_rank()` defensively returns -1 for unknown tier
strings — a misconfigured workspace ranks BELOW
Starter, which means it sees no tools rather than
accidentally unlocking Pro/Agency tools.

**Defense in depth**: the dispatcher (`dispatch_tool`)
also checks tier and raises `DispatchError(403)` if the
workspace tier is below the tool's `tier_required`. The
catalog filter on `get_workspace_tools` is the primary
gate (the LLM never sees over-tier tools at session-
create), but a buggy or malicious SPA POSTing
`tool_name="handoff_to_spokesperson"` from a Starter
session still gets cleanly rejected.

### New public helper

`apps.billing.services.get_workspace_tier(workspace) ->
str` returns the tier string. Lazy-creates a Starter
Subscription when one's missing, matching the rest of
the billing contract (mirrors `_subscription_for`).

## Tests (17)

| # | Test | Surface |
|---|---|---|
| 1 | `test_starter_workspace_catalog_excludes_pro_tools` | tier filtering |
| 2 | `test_pro_workspace_catalog_includes_pro_tools` | tier filtering |
| 3 | `test_agency_workspace_catalog_full` | tier filtering |
| 4 | `test_tool_default_tier_required_is_starter` | registry defaults |
| 5 | `test_dispatch_rejects_overtier_tool_with_403` | dispatcher defense |
| 6 | `test_recall_knowledge_returns_chunks` | recall_knowledge |
| 7 | `test_recall_knowledge_empty_query_failed` | recall_knowledge |
| 8 | `test_recall_knowledge_other_workspace_chunks_excluded` | recall_knowledge (privacy) |
| 9 | `test_recall_recent_conversations_returns_prior_sessions` | recall_recent |
| 10 | `test_recall_recent_conversations_excludes_current_session` | recall_recent |
| 11 | `test_recall_recent_conversations_only_ended_sessions` | recall_recent |
| 12 | `test_recall_recent_conversations_other_workspace_excluded` | recall_recent (privacy) |
| 13 | `test_handoff_to_spokesperson_happy_path` | handoff |
| 14 | `test_handoff_missing_target_failed` | handoff |
| 15 | `test_handoff_same_spokesperson_failed` | handoff |
| 16 | `test_handoff_cross_workspace_failed` | handoff (privacy) |
| 17 | `test_invoke_recall_knowledge_endpoint` | REST integration |

Plus one rename: R7.0's
`test_get_workspace_tools_returns_full_catalog` →
`..._for_agency` and updated to set the test workspace
to Agency explicitly. Post-R7.1, "full catalog" is an
Agency-only assertion.

## Contract rule alignment

| Rule | How R7.1 holds it |
|---|---|
| 1 (workspace anchor) | All tools dispatch under the session's workspace; never traverse to other workspaces. |
| 5 (knowledge integration one-way) | `recall_knowledge` reads K2 via `retrieve_for_spokesperson` — does not write back. |
| 6 (workspace-scoped tools) | Verified end-to-end: `recall_knowledge` chunks filtered by spokesperson.workspace; `recall_recent_conversations` filtered by spokesperson FK; `handoff_to_spokesperson` validates target.workspace == session.workspace. Three privacy tests prove the K0 contract holds. |
| 9 (mock mode) | `recall_knowledge` honors `EMBEDDING_FORCE_MOCK` via the retrieval module's internal check. Other R7.1 tools touch no external services. |

## Open questions resolved

* **Q-r-4 (per-workspace tool catalog overrides).** Done
  via tier-based filtering in `get_workspace_tools` +
  defense-in-depth in the dispatcher.

Remaining open questions touch R3 (Q-r-1 auth
granularity), R5 (Q-r-5 transcript turn addressability
— resolved at R5 time), R6 (Q-r-6 + Q-r-7 — both
resolved), R8 (Q-r-9 WebRTC fallback), and tool
approval flow narration (Q-r-2 — server-side done in
R7.0; SPA wiring in R8). R7.2 may surface Q-r-8
(cross-session tool side effects) around `attach_memory`.

## Drift sweep (per SESSION 147 discipline)

| Category | Status |
|---|---|
| Stale processes | Same as prior sessions. Not blocking. |
| Pending migrations | 50/50 clean. |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15` matches today. |
| INVENTORY git_sha | Regenerated against `611ae94`. |

## Calibration moments worth carrying

### 1. Tier as a defense-in-depth axis, not just a UX filter

The first instinct was "filter the catalog and we're
done — the LLM only sees what it's allowed to use."
But the SPA owns the POST to `/invoke_tool/` and could
in principle bypass the catalog (compromised SPA,
hand-rolled API client, future scripted user). The
dispatcher tier check is cheap (one DB read + a rank
comparison) and means the contract holds even if the
SPA is wrong.

**Carry-forward**: when adding gate logic that's
"clearly checked at one layer," add the second check
at the deeper layer too. Catalog filter + dispatcher
filter is the same shape as "session workspace gate at
view-layer + Asset.clean() cross-workspace check at
model-layer" — defense in depth pays for itself the
first time the outer gate has a hole.

### 2. Per-tool tier is the right unit, not per-tier tool list

Initial sketch put the catalog logic in a per-tier
list (`STARTER_TOOLS = [...]`, `PRO_TOOLS = [...]`).
That couples the data model to the catalog: changing
a tool's tier is a list edit far from the tool itself.
Switched to `tier_required` on `ToolSpec` so each
tool's tier lives with the tool's other declarative
fields. `get_workspace_tools` becomes a one-line
filter.

**Carry-forward**: when adding catalog/permission
metadata, prefer per-item attributes over per-bucket
lists. Tools/recipes/primitives all benefit from the
single-source-of-truth-per-item discipline.

### 3. Privacy tests pay for themselves at slice boundaries

Each R7.1 tool got a `..._other_workspace_excluded`
test (3 total). They're short — set up two workspaces,
run the tool from workspace A, assert workspace B
content doesn't appear. None of them caught a bug this
session, but the discipline reinforces the K0 contract
+ the next time the retrieval surface changes shape,
these tests will catch the regression.

**Carry-forward**: for any new tool/endpoint that
reads workspace-scoped data, a one-test workspace
isolation assertion is cheap insurance. R7.2's
`render_video` (which fires a Composition) will want
the same shape.

## Drift carryover from SESSION 149

* **Stale processes:** still there. `context-kit drift`
  subcommand (parallel agent) is the programmatic
  resolution. Not blocking R-arc.
* **Inventory Celery undercount bug:** still 5; real
  count is 7+. **R7.2 will add at least one new Celery
  task** (`render_video`'s async path), making the
  undercount more visible. Worth addressing before or
  with R7.2.

## Project memories touched this session

None new. The cross-arc isolation calibration moment
(SESSION 146) + one-slice-per-session (SESSION 148) +
sub-slicing the over-scope-locked (SESSION 149) + the
three R7.1 calibrations above are all anchored in
their respective handoffs; promoting any to project
memory is premature.

## What's next (SESSION 151)

### Recommendation: R7.2 (async tools via Celery)

Two tools that share an `is_async=True` shape:

* **`render_video`** — fires a composition starter.
  Pro tier (subject to per-month video cap via the
  existing tier limits). Cost: ~$0.05-0.50 depending
  on starter + duration. **The threshold-crossing
  tool** — exercises the `awaiting_approval` flow
  end-to-end (R7.0 wired it; only synthetic
  high-cost test tools exercised it before).
* **`attach_memory`** — mid-session memory commit.
  Pro tier. Pulls partial transcript from media-
  engine, composes via R6's `compose_session_memory`,
  pushes as a fresh Runway document, attaches to
  spokesperson. Cost: ~$0.001. Resolves Q-r-8
  (cross-session tool side effects — the
  composition is idempotent + last-write-wins).

R7.2 makes the `queued` dispatch state load-bearing.
R7.0 wired it; R7.2 fills in the Celery dispatch and
result-polling shapes.

Estimated scope: ~2 new Celery tasks, ~15 tests, no
migrations.

### Also worth doing first or alongside

**Inventory Celery undercount fix** (drift-prevention
backlog item 5). With R7.2 adding 1-2 new Celery tasks,
the undercount in INVENTORY becomes more obvious. ~30
minutes; could ride with R7.2 or land separately as a
`docs:` commit after R7.2's INVENTORY regen surfaces
the wrong number.

### Alternative: R8 (SPA)

Wire `/spokespeople/:id/talk` + `@runwayml/avatars-react`
+ tool-approval modal. The realtime arc becomes
operator-visible. R8 can technically ship with R7.0+R7.1
(four tools, no Celery-driven actions yet), but the
demo is more compelling once `render_video` works
(SPA tool-approval modal has something real to gate).

### Recommendation rationale

**R7.2 next, then R8.** R7.2 closes the backend tool
catalog; R8 makes everything operator-visible at once.
Landing R8 first means rebuilding the SPA when R7.2
adds the queued state (and lengthens the time before
the operator sees the full vision). R7.2 is also where
Q-r-8 (cross-session tool side effects) gets its
verification surface.

## Files changed in this commit

* `docs/handoffs/SESSION_150_R7_SYNC_TOOLS.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R7.1
  outcome + R7.2 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `611ae94` SHA into the R7.1 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  Shell LOC 36,902 → 37,777 (+875) in 198 → 202 files
  (+4: three tool files + test file).
* `CLAUDE.md` — Phase 4 realtime-arc row updated.

---

*Handoff written end-of-SESSION 150, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
