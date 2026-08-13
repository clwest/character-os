---
title: "Engine bridge (EB) — per-workspace engine config for the bridge tools"
status: proposed
proposed: 2026-05-21 (SESSION 217, slice EB.0)
locked: null
closed: null
companion_docs:
  - REALTIME_AVATAR_V1.md
  - WORKSPACE_FABRIC_V1.md
  - ../handoffs/SESSION_216_BRIDGE_TOOLS_REFRAME.md
---

# Engine bridge — per-workspace engine config

> **Status: PROPOSED (SESSION 217).** First arc after SESSION 216
> reframed the bridge tools (`consult_engine` /
> `query_spider_data` / `agent_consult`) as the v1 instance of an
> **engine-bridge product pattern**, not operator dogfood. Today
> the three tools read one shared pair of env vars
> (`UDB_PA_API_URL` / `UDB_PA_API_TOKEN`) — wiring them to one
> customer. EB generalises that so customer N's spokesperson
> talks to customer N's engine. Eight contract rules; six slices
> EB.0–EB.5. Estimated ~1.5 sessions to ship.

---

## TL;DR

The SESSION 215 bridge tools hardcode "the engine" to whatever
the host Django process's env points at. That's fine for v1
(one customer, 24/7 Global AI → the sibling project) and wrong for v2
(second customer → their own engine). EB adds:

1. **`EngineConnection` model** — one row per `(workspace,
   engine_kind)`. Holds the URL, token (plaintext in v1; Fernet
   queued for v1.5), and an `enabled` flag.
2. **`resolve_engine_connection(workspace)` service** — single
   lookup the three bridge tools call instead of `os.environ`.
   Falls back to env vars when no row exists, so existing
   deployments keep working through the transition.
3. **`/api/engine_connections/` DRF endpoint** — workspace-
   scoped CRUD. Token is **write-only over the API**: POST/PATCH
   accept it; GET returns a redacted preview.
4. **SPA settings panel** — paste URL + token, toggle enabled,
   fire a test-ping. Pro+ tier only.
5. **Real-mode dogfood** — point 24/7's keeper at a non-the sibling project
   engine to prove the same spokesperson can swap engines via
   data, not code.

No new tools. No new tool descriptions. No realtime contract
changes. The three bridge tools' executors switch from
`os.environ.get(...)` to a one-line resolver call; their
descriptions stay identical.

---

## Why now

Four drivers converge:

1. **SESSION 216 reframed the product story.** The bridge tools
   are no longer "operator-only dogfood"; they are the v1
   instance of how Character OS becomes the face for any
   business's external AI stack. Per-workspace config is the
   first slice that makes the reframe operationally true —
   without it, "customer N's engine" isn't expressible in the
   system.
2. **Customer #2 is the unblocking event.** 24/7 Global AI is
   running on env vars today and that works. The minute a
   second workspace needs a different engine URL/token, env
   vars stop working (one Django process can only hold one
   env var). EB ships before customer #2 — not because they're
   knocking, but because the lead time on a second customer is
   "however long this slice takes."
3. **Token surface is small and contained.** Only one app
   (`apps.realtime.tools`) reads the env vars today. The
   refactor touches three executor functions plus the resolver.
   Doing this when there are 3 callers is cheaper than doing
   it when there are 30.
4. **Tier-gating Pro+ matches the existing tier shape.**
   Realtime sessions, video render limits, and spokesperson
   counts already gate by tier through
   `apps.billing.services`. Engine-bridge is a natural Pro+
   feature (Starter has one spokesperson and no engine; Pro
   tier already implies "you have a real external stack to
   plug in").

---

## Contract rules (load-bearing)

Eight rules. None overlap R-arc's 10 + V1's 22. EB rules
stand on their own; if a future merge happens they become
R-arc 11–18.

1. **`EngineConnection` is workspace-scoped.** Every row has a
   required `workspace` FK with `unique_together=[("workspace",
   "engine_kind")]`. Cross-workspace lookups reject at the
   resolver layer (defense-in-depth: even if a stray code path
   passes a wrong workspace, the resolver only returns rows
   matching that workspace). Mirrors R-arc rule 1.

2. **Bridge tools resolve by workspace, not by `os.environ`.**
   The three tools' executors call
   `resolve_engine_connection(session.workspace)` and use the
   returned `(url, token, kind)` triple. The current
   `_get_base_url()` / `_get_token()` helpers in each tool are
   replaced by one shared resolver in
   `apps.realtime.engine_bridge`.

3. **Env-var fallback is a deprecation runway, not a
   parallel path.** When `resolve_engine_connection` finds no
   `EngineConnection` row for the workspace, it returns the
   env-var values (`UDB_PA_API_URL` / `UDB_PA_API_TOKEN`)
   wrapped as a synthetic connection with `kind='udb_pa'`. This
   keeps the SESSION 215 24/7-Global-AI deployment working
   while EB.4 ships the admin UI. Env-var path is removed in a
   later slice once every active workspace has a row.

4. **Token is write-only over the API.** POST/PATCH accept
   `engine_token`; GET returns a redacted preview
   (`"engine_token_preview": "****abcd"` — first four `*`s +
   last four chars of the token; never the full value). The
   SPA never round-trips the token through the browser. The
   admin Django site shows the field but masks it in list
   views.

5. **`enabled=False` fails closed.** A disabled row counts as
   "no connection." If env-vars are set, the resolver falls
   back to env (rule 3); if neither is set, the tools return
   their existing `configured-but-unreachable` error shape.
   This lets an operator pause engine access without deleting
   the row (and re-pasting the token later).

6. **One engine kind in v1: `udb_pa`.** The `engine_kind`
   field is a `TextChoices` with one value
   (`'udb_pa', 'the sibling project Personal Assistant'`). Adding
   `'generic_http'` or other adapters requires a separate slice
   with the actual adapter code and a customer demanding it.
   Speculative enums grow stale. Future kinds add a new
   `TextChoices` member + an executor that knows the kind's
   wire shape.

7. **Test-ping is operator-explicit and bounded.** A separate
   endpoint (`POST /api/engine_connections/<id>/test_ping/`)
   POSTs a no-op question (`"ping"`) to the engine's
   `/api/pa/chat/` with a 3-second timeout. Returns the HTTP
   status code, first 200 chars of the response body, and
   measured latency. No retries, no polling — if the engine
   takes longer than 3 s to acknowledge the POST, the ping
   fails. Test-ping does **not** create an audit row (it's a
   configuration check, not a tool invocation).

8. **Pro+ tier gate at the resolver, not the SPA.** The SPA
   admin panel hides for Starter workspaces, but the
   load-bearing gate lives in the resolver: if
   `get_workspace_tier(workspace) == 'starter'`,
   `resolve_engine_connection` returns `None` regardless of
   row state. Starter workspaces with stray rows (e.g. tier
   downgrade) cannot use them. Bridge tools then return their
   existing "configured-but-unreachable" error. Mirrors R7.1
   pattern (`_TIER_RANK` + `_tier_rank()`).

---

## Data model additions

### `EngineConnection` (new model, `apps.realtime.models`)

Lives next to `RealtimeSession` in `apps/realtime/models.py`.
One row per `(workspace, engine_kind)`. Default `engine_kind`
is `udb_pa` since that's the only v1 value.

```python
class EngineConnection(models.Model):
    """Per-workspace external engine configuration.

    The three bridge tools (consult_engine / query_spider_data /
    agent_consult) resolve to this row by workspace. See
    docs/design/ENGINE_BRIDGE_V1.md.
    """

    class Kind(models.TextChoices):
        UDB_PA = "udb_pa", "the sibling project Personal Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="engine_connections",
    )
    engine_kind = models.CharField(
        max_length=32, choices=Kind.choices, default=Kind.UDB_PA,
    )
    engine_url = models.URLField(max_length=500)
    engine_token = models.TextField(
        help_text=(
            "DRF / bearer token for the engine. Stored plaintext "
            "in v1; v1.5 will encrypt at rest via Fernet."
        ),
    )
    enabled = models.BooleanField(default=True)
    label = models.CharField(
        max_length=120, blank=True,
        help_text=(
            "Human-readable name for the connection — appears in "
            "the admin panel and (eventually) the tool-invocation "
            "audit row."
        ),
    )
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.IntegerField(
        null=True, blank=True,
        help_text="HTTP status code from the most recent test-ping; null if never tested.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("workspace", "engine_kind")]
        ordering = ["-created_at"]
```

Migration: `apps/realtime/migrations/0004_engineconnection.py`.

### Fields rationale

| Field | Why |
|---|---|
| `engine_url` as `URLField` not `CharField` | URL validation at the model layer rejects typos; `http`/`https` enforced by Django's URLValidator default. |
| `engine_token` as `TextField` not `CharField(max_length=...)` | Third-party PATs and OAuth bearers commonly exceed 200 chars. No artificial ceiling. |
| `engine_kind` enum vs free string | Future kinds need executor code, not just config. Enum forces the decision to be deliberate. |
| `label` optional | Single-engine workspaces don't need a label; multi-engine workspaces (rare, v2) will. |
| `last_tested_at` / `last_test_status` | Operator can see when the connection was last verified without re-pinging. Surfaces in the SPA admin. |
| `enabled` separate from row deletion | Pause-without-re-paste pattern (rule 5). |

No `created_by` FK. The row is workspace-scoped; "who created it" is recoverable from `apps.audit` if needed (and isn't load-bearing for the tool path).

---

## Slice plan

EB.0 closes with this scope-lock commit. Five implementation
slices follow.

| Slice | What ships | Effort |
|---|---|---|
| EB.0 | This doc | ✓ SHIPPED (`2c87c88`) |
| EB.1 | `EngineConnection` model + migration `0004_engineconnection` + Django admin registration | ✓ SHIPPED (`7773016`) |
| EB.2 | `apps.realtime.engine_bridge.resolve_engine_connection()` + refactor of `consult_engine` / `query_spider_data` / `agent_consult` onto it + env-var fallback + 15 backend tests (12 planned + 3 bonus parametrized) | ✓ SHIPPED |
| EB.3 | DRF `/api/engine_connections/` (list / retrieve / create / patch / delete) + `test_ping` action + token redaction in serializer + workspace-scoped permission class + 10 backend tests (8 planned + 2 structural extras) | ✓ SHIPPED |
| EB.4 | SPA `/settings/engine` route — engine kind picker, URL + token form, enabled toggle, test-ping button, "last tested" line + Pro+ tier gate at route level | ½ session |
| EB.5 | Real-mode dogfood: create a second workspace, point its keeper at a stub engine, prove bridge tools route by workspace, write arc-close handoff | ¼ session |

Total: ~2 sessions if each ½-slice goes cleanly. SESSION 216's
1.5-session estimate stands as best case (EB.1 + EB.2 land in
one session, EB.3 + EB.4 in another, EB.5 in a tail).

---

## API surface

### `/api/engine_connections/`

| Verb | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/api/engine_connections/` | (workspace from session) | List of rows for the active workspace, token redacted |
| POST | `/api/engine_connections/` | `{engine_kind, engine_url, engine_token, enabled?, label?}` | Created row, token redacted in response |
| GET | `/api/engine_connections/<id>/` | — | Single row, token redacted |
| PATCH | `/api/engine_connections/<id>/` | Any subset of `{engine_url, engine_token, enabled, label}` | Updated row, token redacted |
| DELETE | `/api/engine_connections/<id>/` | — | 204 |
| POST | `/api/engine_connections/<id>/test_ping/` | — | `{status_code, latency_ms, response_preview}` |

Permission class: `IsAuthenticated` + workspace membership
check (mirrors `RealtimeSessionViewSet`). Pro+ tier check
inside the view's `get_queryset` so Starter workspaces get an
empty list and 403 on create/patch.

### `resolve_engine_connection` resolver shape

```python
# apps/realtime/engine_bridge.py
@dataclass(frozen=True)
class ResolvedEngine:
    url: str
    token: str
    kind: str
    source: Literal["db", "env"]  # which path resolved
    enabled: bool  # for env-var fallback this is always True


def resolve_engine_connection(workspace: Workspace) -> ResolvedEngine | None:
    """Resolve a workspace's engine connection.

    Returns None when:
    - workspace tier is below Pro+
    - no enabled DB row AND no env vars set
    - DB row exists but is disabled AND no env vars set
    """
    ...
```

Bridge tool diff (illustrative):

```python
# Before (consult_engine.py)
base = _get_base_url()  # reads os.environ
token = _get_token()    # reads os.environ
if token is None:
    return {"event": "...", "error": "UDB_PA_API_TOKEN not configured.", ...}

# After
resolved = resolve_engine_connection(session.workspace)
if resolved is None:
    return {"event": "...", "error": "Engine bridge not configured for this workspace.", ...}
base = resolved.url
token = resolved.token
```

The executor's wire shape (the POST body to `/api/pa/chat/`)
does not change.

---

## SPA surface

One new route: `/settings/engine`. Lives under the existing
workspace settings shell. Per Pro+ gate, the nav link hides
for Starter workspaces.

UI elements:

* **Engine kind picker** — single-option select in v1 (`the sibling project
  Personal Assistant`). Shipped as a `<select>` not a hardcoded
  display so EB.6+ can add options without a UI refactor.
* **Engine URL** — text input with URL validation. Helper
  text: *"e.g. http://localhost:8020 for the sibling project on this
  machine"*.
* **Engine token** — masked password input. Server returns
  redacted preview; SPA shows it in a read-only display next
  to a "Replace token" button that swaps to an editable
  input.
* **Enabled toggle** — switch.
* **Label** — optional text input.
* **Test connection** — button. Disabled while a request is
  in flight. Surfaces status + preview from the test-ping
  response.
* **Last tested** — *"Last tested 12 minutes ago — HTTP 200"*
  / *"Never tested"*.

No multi-row table view in v1 (since there's only one engine
kind, one row per workspace).

---

## Test plan

EB.2 (resolver + tool refactor) tests:

1. `resolve_engine_connection` returns DB row when one exists.
2. Returns env fallback when no DB row + env vars set.
3. Returns `None` when no DB row + no env vars.
4. Returns `None` when row exists but `enabled=False` and no
   env vars.
5. Returns `None` for Starter-tier workspace even with a row.
6. Cross-workspace isolation: resolver for workspace A never
   sees workspace B's row.
7. `consult_engine` reads from resolver, hits resolved URL.
8. `query_spider_data` same shape.
9. `agent_consult` same shape.
10. Bridge tool returns existing `configured-but-unreachable`
    error when resolver returns `None`.
11. Env-fallback `ResolvedEngine.source == "env"`.
12. DB-hit `ResolvedEngine.source == "db"`.

EB.3 (REST) tests:

1. List endpoint workspace-scoped.
2. Create row, token redacted in response.
3. GET single row, token redacted.
4. Patch token, GET shows new redacted preview.
5. Delete row.
6. Test-ping happy path (mocked engine).
7. Test-ping engine-unreachable path (3 s timeout).
8. Starter tier gets 403 on create.

Total new tests: ~20. Target Django count after EB.3: ~1456.

---

## Out of scope (v1)

| Item | Why deferred |
|---|---|
| **Fernet at-rest encryption for `engine_token`** | v1.5. Two customers; DB-at-rest encryption acceptable. Adds key-rotation surface area. |
| **Multiple engine kinds (`generic_http`, OAuth-flow engines)** | Speculative without a real customer demanding them (rule 6). |
| **Per-spokesperson engine overrides** | A workspace with two spokespeople routes both to the same engine in v1. Per-spokesperson overrides are a v2 axis if real demand surfaces. |
| **OAuth refresh-token rotation** | All v1 engines authenticate with a long-lived DRF/bearer token. |
| **Engine-side webhook for async results** | Bridge tools poll for v1. Pushing engine→character-os would need a webhook receiver + verification slice. |
| **Engine-consult audit log** | Tool-invocation audit rows already capture this. A dedicated `EngineConsultLog` table would be redundant unless we add cross-engine analytics. |
| **Mock-mode engine adapter** | Bridge tools already handle the no-token case gracefully (returns `configured-but-unreachable`); tests mock at the HTTP layer. |

---

## Open questions

| ID | Question | Proposed resolution |
|---|---|---|
| Q-eb-1 | Should v1 ship with at-rest encryption? | **No** — defer to v1.5 (file ticket at EB.5 close). Two customers; DB-at-rest is the realistic threat boundary. |
| Q-eb-2 | Should the SPA hide settings entirely for Starter or show with upgrade nudge? | **Show with upgrade nudge** — better discovery for the upsell path; matches how realtime minutes display "X of Y" with the cap visible to all tiers. |
| Q-eb-3 | `engine_url` as `URLField` or free `CharField`? | **`URLField`** — model-level validation catches typos pre-test-ping. |
| Q-eb-4 | `engine_token` length ceiling? | **`TextField`** — no ceiling. PATs / OAuth bearers can exceed 500 chars. |
| Q-eb-5 | Should `consult_engine.DEFAULT_BASE_URL` (8020) and `query_spider_data.DEFAULT_BASE_URL` (8000) be unified? | **Yes** — normalize to `http://localhost:8020` in EB.2's refactor. Today's split is incidental. |
| Q-eb-6 | Should test-ping write to `audit.ToolInvocation`? | **No** (rule 7) — config check, not a tool invocation. Avoid audit-row pollution from "did the operator type the URL right." |
| Q-eb-7 | Should disabled rows still surface in GET list? | **Yes** — operators need to see them to re-enable. The resolver gates execution, not visibility. |
| Q-eb-8 | What happens to existing 24/7-Global-AI deployment when EB.1 ships? | **Nothing breaks** (rule 3) — env-var fallback keeps the live bridge alive until EB.4 ships and the operator pastes the URL into the admin UI. |

---

## Change log

| Date | Slice | Change |
|---|---|---|
| 2026-05-21 | EB.0 | Scope lock proposed (SESSION 217). Commit `2c87c88`. |
| 2026-05-21 | EB.1 | `EngineConnection` model + migration `0004_engineconnection` + admin registration (SESSION 217). Commit `7773016`. |
| 2026-05-21 | EB.2 | `engine_bridge.resolve_engine_connection` + bridge-tool refactor + env fallback + 15 tests (SESSION 217). Normalised `DEFAULT_BASE_URL` to `:8020` across all three tools (Q-eb-5 resolved). |
| 2026-05-22 | EB.3 | DRF `/api/engine_connections/` viewset + `EngineConnectionSerializer` with `engine_token_preview` redaction + `test_ping` action + Pro+ tier gate + 10 tests (SESSION 217). |
