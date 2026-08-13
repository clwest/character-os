# God Files & Architectural Scars

Character OS has real scars. Documenting them here honestly is
more valuable than cosmetic rewrites that would take a week and
add risk without adding capability.

## Four large files

### `shell/apps/compositions/starters.py` — ~3,000 LOC

**What it is:** The template-recipe builder library. Each
starter is a function that returns a `Composition` template
with pre-wired `CompositionStep` rows and slot mappings.

**Why it grew:** The V-arc's 20 recipes each need parameter
metadata for the SPA to render their forms, plus the actual
recipe wiring. Both live here to keep the metadata and the
wiring in one place — the recipe gallery at `/recipes` reads
this file's exports directly.

**Current risk:** Low. Adding a recipe means adding one function;
the module has no shared state and no circular structure. The
size is a reading burden, not a coupling problem.

**Split trigger:** If the SPA needs to render more recipe
metadata than the current `RecipeSpec` shape supports (e.g.,
form field grouping, tabbed inputs, conditional visibility),
splitting into `starters/` package with one file per recipe is
the right move. Not before.

### `shell/apps/identity/services.py` — ~1,960 LOC

**What it is:** The synchronization wiring between the Teammate
model's compatibility mirror fields and the canonical Identity
substrate introduced SESSION 241.

**Why it grew:** The SESSION 241-246 strangler pattern replaced
Teammate's inline identity fields with a canonical
`CharacterIdentity` + `CharacterIdentityVersion` substrate.
Every write path in the old world now has to reflect state into
the new world (and vice versa for reads). The wiring is dense.

**Current risk:** Medium. Adding a new identity field means
touching this module in ~3-5 places to preserve mirror parity.
Tests catch drift. But a reader trying to understand identity
flow has to hold a lot of context.

**Split trigger:** Once the compatibility mirror period ends
(the strangler completes), this file collapses to a fraction of
its size. Splitting now would prolong the transition.

### `shell/apps/identity/models.py` — ~1,560 LOC

**What it is:** 11 models in the canonical identity substrate —
`CharacterIdentity`, `CharacterIdentityVersion`, `Portrait`,
`Avatar`, `Voice`, prequalification representations, and
associated audit rows.

**Why it grew:** The identity substrate is the single largest
domain concept in the product; concentrating it in one file
makes the ontology reviewable in one read.

**Current risk:** Low-medium. Django imports all models eagerly,
so file boundaries have no runtime effect. The reading load is
the only cost.

**Split trigger:** When any two of the 11 models start needing
independent schema migrations that don't touch the others — at
that point per-concept files become useful for change isolation.

### `shell/character_os/clients/media_engine.py` — ~1,680 LOC

**What it is:** The HTTP client that Django uses to talk to the
FastAPI media-engine. Every `/internal/*` endpoint has a wrapper
here.

**Why it grew:** The media-engine ships ~140 routes; a
substantial fraction have wrappers here. Each wrapper handles
request marshalling, response validation, mock-mode branching,
and error mapping.

**Current risk:** Medium. It's the primary place where a
new-provider integration lands, and the mock/real branching is
concentrated here rather than at the media-engine boundary.

**Split trigger:** If the mock-mode branching moves out of the
client and into the media-engine itself (a real improvement),
this file drops ~30%. Alternatively, splitting into
`clients/media_engine/{avatars,voices,compositions,realtime}.py`
would be a low-risk mechanical split when a reader complains.

## Naming compatibility debt

The UI-facing noun for the persistent identity is **Teammate**.
The persistence layer still uses **Spokesperson**:

- Django app label: `spokespeople`
- DB table: `spokespeople_spokesperson`
- URL path: `/api/spokespeople/`
- DRF router basename: `spokesperson`
- FK field names on other models: `spokesperson`
- M2M field on `KnowledgeDocument`: `spokespeople`
- Response payload keys: `"spokesperson":` (external contract)

This is documented in `CLAUDE.md` §17.1.b as intentional. The
UI rename went in SESSION 240; the persistence rename is
deferred until a coordinated DB + API compatibility migration.
Column names derive from FK field names in Django, so the
persistence rename is not zero-cost.

**Risk:** A reader will notice the two vocabularies and wonder
which is canonical. Grep-friendliness is fine because the
mapping is systematic (UI `Teammate` = DB `Spokesperson`).

## Legacy `Video` model

`shell/apps/videos/models.py` still contains a `Video` model
that predates the `Composition` unification. It rides on the
`talking_head` recipe via a V6 backward-compatibility shim so
older SPA code paths continue to work.

**Current status:** functional. Consumed by legacy `MakeVideoRoute`
+ `/api/videos/`. The V-arc closed without deleting the shim
because the workspace-fabric arc owned the retirement.

**Retirement trigger:** When the SPA's legacy single-form video
route is fully removed and no external client uses
`/api/videos/`, the model and shim can go.

## Empty apps: `agents/` and `memory/`

Both apps exist as Django app scaffolds (`__init__.py`,
`apps.py`, `migrations/__init__.py`) with zero models and zero
active code.

- **`agents/`** — placeholder for a future agent framework. The
  realtime tool catalog (`shell/apps/realtime/tools/`) is the
  closest existing concept.
- **`memory/`** — placeholder for a future cross-session memory
  layer. The realtime arc's `character_os/realtime_memory.py`
  (module, not Django app) is the current home for session
  memory composition.

**Risk:** Zero functional risk (empty apps do nothing). Reader
confusion is the only cost — they look like abandoned starts.

**Disposition:** Kept because the design docs reference them
and they signal intent. If publishing to a fresh audience, they
could be deleted with no impact.

## What is NOT a scar

- **`docs/handoffs/` and `docs/production-readiness/`** are
  gitignored in this public distribution, not deleted — they
  contain the internal engineering history preserved privately.
- **The design-lock docs (`docs/design/*.md`)** are large but
  intentional — they are the contracts, not the code.
- **The identity substrate itself** (SESSION 241-246) is the
  strangler pattern doing its job, not a scar. When the
  compatibility mirror period ends, the mirror wiring collapses.
