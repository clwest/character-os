---
title: "Episode → Composition Workflow — Dogfood Audit v1"
status: audit-only; STOP before implementation
date: 2026-08-18
depends_on:
  - "design/EPISODE_SCHEMA_V1.md"
  - "design/EPISODE_SCHEMA_V1_IMPLEMENTATION.md"
  - "design/COMPOSITION_OBSERVABILITY_V1.md"
scope: >
  Read-only audit of the operator experience going from Episode
  create through Composition create and back. Diagnoses why the
  first-real dogfood produced "Episode adds extra steps" and
  proposes the smallest corrective slice — with no Episode-schema
  changes required.
supersedes: []
---

# Episode → Composition Workflow — Dogfood Audit v1

## Operator dogfood transcript (SESSION 262, close-adjacent)

1. Dashboard → Worlds tile → `Patch' Workshop` → **Manage episodes** → **New Episode**.
2. Filled title (`AI took over the lab`) + operator_topic prose.
3. Episode detail: **Add to cast** → Patch → **Add to cast** → Rivet.
4. **New dialogue scene** CTA (added `23dc1a8`) →
   `/recipes/dialogue_scene?episode=<uuid>`.
5. Recipe form asks: primary spokesperson, secondary spokesperson,
   dialogue mode, topic, target duration, use_knowledge, verifier
   mode, opener, outro, name.
6. Operator re-picks Patch (primary), Rivet (secondary), retypes
   the same topic already on the Episode, picks 60s.
7. Submit → POST /api/compositions/ succeeds, `episode` FK attached,
   redirect to /compositions/<id>.
8. Composition detail shows a small "Attached to Episode <first-8>"
   link but no additional Episode payoff.
9. Return to Episode detail. `composition_count` bumps to 1. No
   Composition list, no thumbnails, no "make another version" flow.

**Operator assessment (verbatim):** *"All it seemed to do was create
extra steps."*

## Root cause (one-line)

The recipe form is **Episode-blind**. It receives the Episode UUID
purely as an FK-to-attach at submit; it does not fetch the Episode's
data to pre-populate the fields that Episode already owns
(topic + cast). Backend accepts what the SPA sends, so the SPA is
the sole source of the redundant re-entry.

## Data-flow audit — screen-by-screen

### A. Episode create form (`universes.$id.episodes.tsx`)

| Data | State |
|---|---|
| universe | derived from URL param `:id` |
| title | operator input (auto-derives from topic if blank) |
| operator_topic | operator input (required) |
| cast | not asked here — separate step post-create |

### B. Episode detail (`episodes.$id.tsx`)

| Data | State |
|---|---|
| universe / universe_name | fetched via `useEpisode(id)` |
| title / operator_topic | editable in place |
| cast | rendered as chips; add/remove via dedicated endpoints |
| composition_count | number only — **no Composition list rendered** |
| attached Compositions | **absent from the UI** |

### C. Render CTA (`episodes.$id.tsx:264+`, commit `23dc1a8`)

| Data known here | Passed downstream |
|---|---|
| `episode.id` | ✓ via URL query `?episode=<id>` |
| `episode.operator_topic` | ✗ NOT passed |
| `episode.cast` (list of Teammates) | ✗ NOT passed |
| `episode.universe` | ✗ NOT passed (recipe form re-derives via spokesperson) |

### D. Recipe form (`recipes/$kind.tsx`)

| Field | Source in current flow |
|---|---|
| `episode` (submit body) | ✓ from `?episode=` query param (commit `23dc1a8`) |
| `primary_spokesperson_id` | **operator re-selects** |
| `secondary_spokesperson_id` | **operator re-selects** |
| `dialogue_mode` | recipe default (`manual`) — operator flips to `ai_topic` |
| `topic` | **operator re-types** |
| `target_duration_seconds` | operator picks (legitimately variant-specific) |
| `use_knowledge` | recipe default; operator may edit |
| `verifier_mode` | recipe default; operator may edit |
| `opener` / `outro` / `name` | operator input; legitimately Composition-specific |

**Note:** the form does receive `?episode=<uuid>` but reads it only
in `onSubmit` to attach the FK. It never uses it as a data-fetch
source to pre-populate the form fields.

### E. POST /api/compositions/ (backend, `views.py:487+`)

Backend behavior (unchanged; already sufficient):
- Accepts `episode` UUID; validates cross-Workspace / cross-Universe
  via `Composition.clean()`.
- Does **NOT** auto-populate `params.topic` or `params.primary_spokesperson_id`
  from `episode.operator_topic` / `episode.cast`. It takes what the SPA
  sends.

### F. Composition detail (`compositions/$id.tsx`)

| Data | State |
|---|---|
| `composition.episode` | rendered as `Attached to Episode <first-8>` link |
| return-to-Episode | ✓ single link in the header |
| Episode-level payoff | ✗ none — no "make another version," no sibling-Compositions list |

### G. Return to Episode detail

- `composition_count` bumps.
- Attached Compositions themselves not rendered anywhere on the
  Episode surface.
- No affordance to compare / manage versions of the same story.

## Answers to the 20 audit questions

### 1. Why does "Create Composition under Episode" redirect to the normal Dialogue workflow?

Because the smallest slice that landed in SESSION 262 was a
**URL-only hint** (`?episode=<id>`) forwarded to the existing recipe
form. The recipe form was not made Episode-aware — it treats the
hint as a passive FK attach only. The redirect was a
minimum-plumbing decision; the Episode-driven form redesign was
never scoped.

### 2. Which Episode fields are currently carried forward automatically?

| Field | Carried? | Where |
|---|---|---|
| `episode.id` | ✓ | passed as `episode` on POST body |
| `episode.universe` | ✗ | recipe form derives via spokesperson picker |
| `episode.operator_topic` | ✗ | operator re-types |
| `episode.cast` | ✗ | operator re-selects |

### 3. Which fields are redundantly re-entered?

- **Topic** — Episode.operator_topic → recipe form `topic` textarea.
- **Primary spokesperson** — Episode.cast[0] → recipe form `primary_spokesperson_picker`.
- **Secondary spokesperson** — Episode.cast[1] → recipe form `secondary_spokesperson_picker`.
- **Dialogue mode** — implicitly `ai_topic` when coming from Episode
  (topic + cast declared upstream), but the form defaults to
  `manual`.

### 4. Does the recipe form currently know it was launched from an Episode?

Yes — via `episodeHint = searchParams.get("episode")` at
`$kind.tsx:55`. But it only uses that hint at submit time; nothing
else in the form reacts.

### 5. Does it receive Episode context but ignore it, or is the context never passed?

**Receives but ignores.** The URL param is present. The form's
render layer does not fetch `useEpisode(episodeHint)` and does not
seed field defaults from Episode data.

### 6. Can the existing composition starter APIs already accept `episode`, `topic`, `spokesperson/cast IDs` without backend changes?

**Yes, all three.** POST `/api/compositions/` currently accepts:
- `episode` UUID (attaches FK).
- `params.topic` (dialogue AI-Topic mode).
- `params.primary_spokesperson_id`, `params.secondary_spokesperson_id`.
- `params.dialogue_mode`, `params.target_duration_seconds`, etc.

The recipe resolver at `shell/apps/compositions/recipes.py:293–384`
consumes all of these. Zero backend changes are needed to eliminate
the duplicated re-entry.

### 7. What should be Episode-authoritative during Composition creation?

Working hypothesis stands, refined:

| Field | Episode-authoritative | Reason |
|---|---|---|
| `episode.id` | ✓ | Load-bearing linkage |
| `universe` | ✓ | Every Composition under an Episode inherits Universe scope transitively |
| `operator_topic` | ✓ | SESSION 262 §Where-operator_topic-lives: Episode is story-authoritative; snapshot into `Composition.operator_topic` on create |
| `cast` (order = `EpisodeCast.added_at`) | ✓ | Cast is operator-declared story participants; recipe binds them to primary/secondary slots |

**Nothing new needs to become Episode-authoritative.** The list
above is already what the schema captures.

### 8. What should remain Composition-specific?

Per SESSION 262 field ownership matrix + this audit:

- **Recipe kind** (dialogue_scene, talking_head, long_form_ad, …)
- **`target_duration_seconds`** — the WHOLE POINT of Composition
  variants (60s + 90s of the same story).
- **`opener`** / **`outro`** — per-render production choices.
- **`use_knowledge`** — per-render toggle (rarely flipped, but legal).
- **`verifier_mode`** — per-render override.
- **`name`** — Composition-facing display label (distinct from
  Episode title).
- **`dialogue_mode`** — usually implicit `ai_topic` when coming from
  Episode, but the form should keep the toggle for
  operator-authored manual scripts.
- **`mock_mode`** — per-render execution mode.
- **`backdrop_clip_id`** / visual treatment / aspect variant params
  (per-recipe).
- **provider / media options** (aspect ratio, resolution) —
  per-render.

### 9. Should Episode.operator_topic copy into Composition.operator_topic automatically when creating a Composition from an Episode?

**Yes.** Two behaviors combine:

- **SPA pre-fill**: recipe form seeds `params.topic` from
  `episode.operator_topic` when `?episode=<id>` is present. Operator
  can still override in the field (variant tweak).
- **SESSION 262 backend**: whatever `params.topic` reaches the
  starter lands in `Composition.operator_topic` immutably (already
  the case).

Explicit override remains legal — a variant may deliberately alter
topic while keeping the Episode's story-authoritative version
unchanged (SESSION 262 §Q3, "Composition retains a copy of
operator_topic for legacy / Episode-less rows and for per-attempt
provenance").

### 10. For a two-character Dialogue Scene, can Episode.cast auto-populate the primary/secondary selectors?

**Yes with a caveat.** `EpisodeCast.added_at` gives stable ordering
(inspected at `shell/apps/universe/models.py:399+`). It is NOT a
semantic "role" (primary vs secondary), but as a UI convention:

- `cast[0]` (first-added) → primary
- `cast[1]` (second-added) → secondary

The operator can still swap in the form. This convention avoids
adding a schema-level `role` field to `EpisodeCast` (deferred).

**Do NOT** rely on the raw M2M's `.all()` ordering — always sort by
`added_at` (or fetch the through rows). The `Episode.cast` M2M
returns Teammates without through metadata; the API needs to
surface `added_at` OR sort at serialize time.

**Deferral flagged:** if the operator declares intent that
`cast[0]` is a supporting character and `cast[1]` is the primary,
we need explicit role designation. Not needed for the v1 dogfood.

### 11. What if Episode has 3+ cast members but the recipe supports only 2?

Recipe form uses `cast[0]` + `cast[1]` as pre-fills. Operator can
override to any Teammate in the same Universe via the pickers.
Third+ cast members are simply absent from that particular
Composition's rendering. Legal — Episode.cast is the full ensemble;
each Composition renders a subset.

### 12. What if the chosen recipe supports one character?

`talking_head` etc.: recipe form binds only `cast[0]` (first-added
member) as primary. Operator can override. Others in Episode.cast
are ignored for this specific Composition. Same legality: Episode
cast is the ensemble; render picks a subset.

### 13. Does the Episode detail page visibly show its attached Compositions after creation?

**No.** The page shows `composition_count` as a number but does not
render a list of the actual Compositions. Verified at
`web/src/routes/workspace/episodes.$id.tsx:173-174`.

**Gap identified:** operator has no way to see "the 60s version I
made yesterday" or click into it without leaving the Episode
surface entirely.

### 14. Can the operator easily return from Composition detail to its Episode?

**Partially.** Composition detail header (added in SESSION 262 impl
commit) renders `Attached to Episode <first-8-of-id>` as a link.
Present but small (`text-xs`); shows only the first 8 chars of the
UUID, not the Episode title.

**Adequate for now; can be improved (Episode title instead of UUID).**

### 15. What Episode-level information should be visible after rendering?

Minimum shape for a Compositions section on Episode detail:

| Field | Source |
|---|---|
| Composition name | `composition.name` |
| Recipe (`template_kind`) | `composition.template_kind` |
| Status | `composition.status` |
| Requested duration | `composition.target_duration_seconds` (SESSION 262) |
| Rendered duration (from asset) | `composition.final_asset.duration_ms` (derived) |
| Created | `composition.created_at` |
| Thumbnail / final asset link | `composition.final_asset` |
| Retry / variant CTA | link to `/recipes/<kind>?episode=<id>` (re-entry) |

`composition.mock_mode`, `composition.cost_actual_micros`, and
`composition.verification_status` are useful chip metadata but not
load-bearing for v1.

### 16. Should Composition creation from Episode be:

**Position: Option C, refined — Episode-driven recipe form.**

- **A** (choose recipe from Episode detail): the CTA row currently
  offers "New dialogue scene" / "New talking head" / "Choose another
  recipe" (commit `23dc1a8`). This is fine as an entry.
- **B** (a new "Create version" step then pick production settings):
  adds ceremony without solving the re-entry problem.
- **C** (recipe form Episode-aware, pre-fills topic + cast): solves
  the "extra steps" problem in one small SPA slice with zero
  backend changes. **This is the recommended path.**
- **D** (custom Episode-form that bypasses recipes entirely):
  duplicates the recipe surface unnecessarily; would require
  building a parallel form for every recipe.

**Refinement to C:** the Episode-driven recipe form should:
1. Fetch Episode when `?episode=<id>` present.
2. Pre-fill `topic`, `primary_spokesperson_id`,
   `secondary_spokesperson_id`, `dialogue_mode`.
3. Show a small chip "Episode: <title>" at the top of the form so
   the operator knows the pre-fill's provenance and can
   detach/clear if needed (equivalent to the existing
   `spokesperson-hint-chip` for the spokesperson pre-fill).

### 17. Smallest UI slice that changes "adds extra steps" → "saves work and organizes versions"

Three tightly-scoped SPA changes + one one-line backend filter:

1. **Recipe form fetches Episode + seeds field defaults.**
   `web/src/routes/recipes/$kind.tsx`. When `?episode=<id>` is
   present, call `useEpisode(episodeId)` and pre-fill `params.topic`,
   `params.primary_spokesperson_id`,
   `params.secondary_spokesperson_id` (in cast added-order),
   `params.dialogue_mode` (`"ai_topic"` when coming from Episode).
   Add an "Episode: <title>" hint chip mirroring the existing
   spokesperson-hint pattern.

2. **Episode detail shows a Compositions list.**
   `web/src/routes/workspace/episodes.$id.tsx`. Render each
   attached Composition (name + template_kind + status + duration
   + created_at + link into `/compositions/<id>`), with a "make
   another version" CTA that routes back into the recipe form
   with Episode context preserved.

3. **Backend adds `?episode=<uuid>` filter to Composition list.**
   `shell/apps/compositions/views.py::CompositionViewSet.list`
   already supports `?workspace`, `?spokesperson`, `?status`. Add
   `?episode=<uuid>` filter (one line + one test). The Episode
   detail page uses it to fetch its attached Compositions
   (alternatively: extend EpisodeSerializer with a `compositions`
   array; either is fine — filter is cheaper).

4. **Composition detail: link back with Episode title, not UUID
   fragment.** Extend the CompositionSerializer to include a
   minimal `episode_title` field (SerializerMethodField),
   OR fetch the Episode from the composition page via `useEpisode`.
   Serializer is simpler.

Total scope: ~200 SPA LOC, ~5 backend LOC, ~1 new API test.

### 18. Can this be fixed without changing Episode schema?

**Yes, fully.** No `Episode.cast` role field is needed —
`EpisodeCast.added_at` gives stable ordering that the SPA can sort
on. `Episode.operator_topic`, `Episode.cast`, and `Episode.universe`
already carry everything the recipe form needs. Zero migrations.

### 19. Backend / schema gaps vs UX gaps

**UX only** for the "extra steps" complaint. **One trivial backend
addition** (Composition list `?episode=` filter) supports the
Episode-detail Compositions-list surface — that's an incremental
one-liner, not a schema change.

**No true schema gap.** Deferred items (`EpisodeCast.role`,
`Episode.canonical_composition` FK, `Episode.sequence`,
narrative-memory substrate) are not needed to close this dogfood
finding.

### 20. Re-run the dogfood mentally against the proposed workflow

**Setup (one-time per Episode):**
1. Dashboard → Worlds → Workshop → Manage episodes → New Episode.
2. Enter title `AI took over the lab` + operator_topic prose.
3. Add cast: Patch, then Rivet.

**Version 1 — 60s dialogue:**
4. Click **New dialogue scene** → recipe form loads Episode.
5. Form is pre-filled:
   - Topic: `Rivet warns Patch...` (from Episode)
   - Primary: Patch (first cast)
   - Secondary: Rivet (second cast)
   - Dialogue mode: `ai_topic`
   - Duration: default (operator picks 60s or accepts default)
6. Operator changes only: **duration to 60**.
7. Submit → Composition C1 runs.

**Version 2 — 90s dialogue:**
8. From Episode detail, click **make another version** (dialogue
   scene) on the Compositions list.
9. Form is pre-filled identically (topic, cast, dialogue_mode).
10. Operator changes only: **duration to 90**.
11. Submit → Composition C2 runs.

**Fields the operator re-enters across the two variants: zero
story/cast/world fields.** They pick a duration. That's it.

Compare to current behavior: 5+ fields re-entered per variant.

## Field ownership table

| Concern | Episode | Composition (per attempt) | Notes |
|---|---|---|---|
| Universe | ✓ (FK) | derived (via `episode.universe`) | Non-mutable on Episode. |
| Story intent (`operator_topic`) | ✓ story-authoritative | snapshot copy per-attempt (SESSION 262 immutable) | SPA pre-fills; operator override legal at variant level. |
| Cast (Teammates M2M) | ✓ operator-declared ensemble | render picks subset via primary/secondary | Ordering by `EpisodeCast.added_at`. |
| Recipe kind | — | ✓ (`template_kind`) | Per-render choice. |
| Target duration | — | ✓ (`target_duration_seconds`) | The main variant knob. |
| Opener / outro | — | ✓ | Per-render production choice. |
| use_knowledge / verifier_mode | — | ✓ | Per-render override. |
| Composition name | — | ✓ | Distinct from Episode title. |
| mock_mode | — | ✓ | Per-render execution mode. |
| First-pass / corrective / attempt log | — | ✓ (SESSION 262 immutable) | Never propagates to Episode. |
| Cost / rendered duration | — | ✓ | Per-render outputs. |

## Recipe compatibility rules

Operator declares full cast on Episode. Each recipe binds a subset
by role:

| Recipe | Cast requirement | Pre-fill behavior |
|---|---|---|
| `talking_head` | 1 primary | `cast[0]` |
| `talking_head_with_backdrop` | 1 primary | `cast[0]` |
| `dialogue_scene` (AI-Topic) | 1 primary + 1 secondary (distinct) | `cast[0]` + `cast[1]` |
| `dialogue_scene` (manual) | N speakers | operator authors lines; SPA lists cast for the picker |
| `long_form_ad` | 1 primary | `cast[0]` |
| `cinematic_visual` / silent recipes | 0 or 1 (owner attribution) | `cast[0]` if present |
| `storyboard_voiced` | 1 primary | `cast[0]` |

**Empty Episode.cast:** recipe form falls back to the pre-Episode
behavior — operator picks any Teammate in the Episode's Universe.
No error; the pickers stay operator-driven.

**Cast > recipe capacity:** unused cast members are silently
ignored for that specific Composition. Operator can pick different
ones via override.

**Cast < recipe capacity (e.g., 1 cast, dialogue_scene):** the
Episode detail's render CTA row already routes to `talking_head`
in this case (`episodes.$id.tsx:264+`). If the operator overrides
to `dialogue_scene` in the gallery, the form validates and asks
for the missing role.

## Episode detail — recommended composition-history rendering

Section between "Cast" and "Render under this Episode":

```
Renders (N)
──────────────────────────
[C1 status chip]  60s dialogue_scene · rendered 62s · 12h ago
                  ▶ open · ↻ make another version

[C2 status chip]  90s dialogue_scene · rendered 94s · 2h ago
                  ▶ open · ↻ make another version
```

- **Status chip** = existing `verification-status-badge` component.
- **Duration** = `composition.target_duration_seconds` (requested) →
  `composition.final_asset.duration_ms/1000` (rendered) when
  available.
- **Open** = `<Link to="/compositions/<id>">`.
- **Make another version** = new recipe-form URL with `?episode=<id>`
  AND `?duplicate_from=<composition_id>` (deferred stretch — v1
  can omit the duplicate hint and just relaunch with Episode
  context).

## Smallest corrective implementation slice

**Scope: three files SPA + one file backend + two tests.**

**Backend (~5 LOC + 1 test):**
1. `shell/apps/compositions/views.py::CompositionViewSet.list` —
   add `?episode=<uuid>` filter.
2. `shell/apps/compositions/tests/test_v15_api.py` — one test
   asserting the filter narrows correctly.

**SPA (~200 LOC + 2 test updates):**
1. `web/src/routes/recipes/$kind.tsx` — fetch `useEpisode(episodeHint)`;
   pre-fill `params.topic`, `params.primary_spokesperson_id`,
   `params.secondary_spokesperson_id`, `params.dialogue_mode`;
   add an "Episode: <title>" hint chip.
2. `web/src/routes/workspace/episodes.$id.tsx` — fetch attached
   Compositions via the new backend filter; render the
   composition-history section per the spec above.
3. `web/src/lib/api/recipes.ts` — extend `Composition` schema with
   optional `target_duration_seconds` if not already surfaced (it's
   on the model per SESSION 262, but check the serializer surfaces
   it to `CompositionListSerializer`).

**No new Django models. No new migrations. No changes to the
Episode schema. No changes to the SESSION 262 observability
contract. Legacy Composition workflow (Episode-less) remains
byte-for-byte unchanged.**

## Tests required

- **Backend** — `?episode=<uuid>` list filter returns only the
  compositions attached to that Episode; ignores others in the
  same workspace.
- **SPA** — recipe form pre-fills topic / primary / secondary when
  `?episode=<id>` present; operator override still submits; empty
  cast falls back to the pre-Episode picker behavior.
- **SPA** — Episode detail renders the attached Compositions list
  (name, kind, duration, status, timestamps, open link).
- **SPA** — Composition detail's "Attached to Episode" link renders
  the Episode's title (not UUID fragment).
- **Dogfood-style integration test** — mock-mode end-to-end:
  create Episode → open recipe form via CTA → assert prefills →
  submit → verify Composition created + attached → back on
  Episode detail assert the new Composition appears in the list.

## Explicit deferrals

Not part of this slice; recorded so they don't creep in:

- `EpisodeCast.role` schema field (primary/secondary designation).
  Current `added_at` ordering is sufficient for v1.
- Cast reordering UI. Operator can remove + re-add.
- `Episode.canonical_composition` FK for canon promotion.
- Variant comparison / diff UI.
- `?duplicate_from=<composition_id>` hint (fine polish; not
  required to reach zero re-entry across variants).
- Episode-level cost / metrics rollup.
- Narrative memory substrate.
- Any Relationship / WorldEntity work.
- Removing the pre-existing "Worlds" chip inside the Knowledge
  tile header (harmless; separate cleanup slice).

## STOP/GO recommendation

**GO — proceed to implementation** as a single tightly-scoped
slice. Rationale:

1. Root cause is confined to the SPA recipe form + Episode detail;
   backend needs a one-line filter addition and nothing else.
2. Zero Episode-schema change required. Zero migration required.
   SESSION 262 observability contract untouched.
3. The proposed workflow reduces re-entry from 5+ fields per
   variant to zero story/cast/world fields — validated against the
   two-variant dogfood re-run (§Q20).
4. Legacy Episode-less Composition path is fully preserved. Every
   pre-Episode operator workflow continues unchanged.
5. Tests are deterministic (mock-mode + fixtures); vertical slice
   proof is straightforward.

**Recommended slice name:** `EPISODE_COMPOSITION_WORKFLOW_V1_IMPLEMENTATION`.

## STOP

Audit-only. No implementation. No schema change. No commits beyond
this design report.
