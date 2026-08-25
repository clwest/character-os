# SESSION 281 — Handoff (from SESSION 280)

## Status at the top

- **SESSION 280 is CLOSED.**
  - Closeout marker: `docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`
    §80.K.
  - Full evidence + design trail: same document, 79 sections
    across Finding 4i experiments (Q280.4i-1, Q280.4i-4),
    story-loop audits (Q280.6), narrative-memory bridge
    probes (Q280.7, Q280.8), model-as-curator (Q280.9),
    Episode-chain product discovery (Q280.5-1), v1 UX
    design + implementation, and v1.5 curator UX design
    (§79).
- **v1 "Where could this story go next?" surface is LIVE**
  at commit `25b3168`. Operator can use it today at the
  Universe Episodes page.
- **v1.5 curator UX is DESIGNED at §79** (SESSION 280
  audit doc). Chris + ChatGPT approved. Not yet
  implemented — SESSION 281's mission.
- **Two promoted Fox & Flour memories are LIVE in
  production** (both LEFT IN PLACE per Chris's explicit
  instruction — see §5 below).
- **Cumulative SESSION 280 spend:** ~$0.32 across 4
  executed experiments.

**Purpose of this document:** compact self-contained
orientation for SESSION 281 Claude + ChatGPT so neither
has to re-read the 9,000+ line SESSION 280 audit doc to
resume work.

---

## §1 Mission

Turn the validated storyteller → curator → operator →
memory → future-story loop into the smallest usable
operator-facing product.

Concretely: implement the v1.5 curator UX described at
§79 of the SESSION 280 audit doc — a "few ideas from what
just happened" surface inside the existing
`NarrativeMemoryPromotePanel` on the composition detail
page.

**SESSION 281 must BEGIN with orientation and scope-lock.**
Do not blindly implement merely because SESSION 280
produced a design. First verify:

- Current `git rev-parse HEAD` matches or descends from
  `d24c127` (SESSION 280 final closeout SHA — see §4).
- Working tree is clean.
- `docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`
  §79 assumptions still match repository state:
  - `NarrativeMemoryPromotePanel` still lives at
    `web/src/components/narrative-memory-panels.tsx`
    lines 110-330 (or moved but functionally
    equivalent).
  - `promote_from_composition` still lives at
    `shell/apps/memory/views.py` and accepts the same
    signature.
  - `CompositionViewSet` still exists at
    `shell/apps/compositions/views.py`.
  - Q280.9 probe script still lives at
    `scripts/session280_q280_9_curator_probe.py` (source
    for the prompt shape).
- Relevant test suites are green enough to establish a
  trustworthy baseline:
  - `apps/universe/tests/` (all 115 tests should pass;
    v1 landed at `25b3168`).
  - `apps/memory/tests/` (baseline before adding
    curator-service tests).
  - `web/src/components/possible-next-episodes.test.tsx`
    (8 tests) + adjacent SPA tests should pass.

Then, unless orientation reveals a contradiction, proceed
with the accepted §79.10 implementation shape.

**Do not implement anything until orientation is
complete.**

---

## §2 Product invariant

The operator is making stories, not administering an AI
memory system.

The UI should answer:

> **"What from this story should matter later?"**

Nothing else.

**AI notices. Human decides. Nothing durable without
explicit approval.**

Q280.8 (§78) validated this loop end-to-end. Q280.9 (§76)
demonstrated the model can produce useful curated
candidates while the operator retains authority. The v1.5
surface is the concrete affordance for the "human decides"
step.

### Vocabulary discipline

Do not expose implementation vocabulary in operator-facing
copy simply because the backend uses it internally.

**BANNED words** in the v1.5 SPA panel (from §79.5):

- Memory kinds: *dialogue_callback*, *promise*, *event*,
  *world_detail*, *action*
- Retrieval mechanics: *witnesses*, *witnessed_by*,
  *embedding*, *vector*, *retrieval*, *top_k*
- Model output metadata: *narrative gravity*, *memory
  weight*, *peripheral*, *central*
- Pipeline framing: *candidate*, *suggested memory*,
  *model-generated*, *AI*, *LLM*, *prompt*, *model*

**Preferred vocabulary:**

- Section: *"Remember this"* (existing, preserved)
- Sub-heading: *"A few ideas from what just happened."*
- Sub-hint: *"Remember the ones that might matter later."*
- Card body: prose sentence, human voice
- Card hint: one-line, operator voice ("Could become a
  running joke.")
- Actions: `[Remember this]` · `Edit` · `Skip`
- Divider: *"Or write your own:"*
- Loading: *"Looking for what might matter…"*
- Error: silent (existing textarea remains functional)

Add a vocabulary-leak test to the frontend component
mirroring §79.6 and the existing
`possible-next-episodes.test.tsx` pattern.

---

## §3 Expected first implementation sequence

Three slices. Each slice ends at an explicit decision
gate. **Do NOT pre-authorize slices beyond that.**

### Slice 281.1 — Backend curator service + endpoint + tests

Add the smallest capability that lets the frontend fetch
model-curated candidate memories.

**New files:**

- `shell/apps/memory/services.py` — add
  `suggest_memories_from_composition(composition, *, n=3, use_cache=True) -> dict`
  - Lifts Q280.9 probe logic
  (`scripts/session280_q280_9_curator_probe.py`) into
  production.
  - Returns `{candidates: [{body, kind, witnesses,
    narrative_gravity_note}], generated_at, model, cache}`.
  - Redis-cached (30-min TTL, key includes
    `composition_id + latest_memory_at`).
  - Empty-substrate short-circuit — returns
    `{candidates: []}` if the composition has no realized
    dialogue.
  - Typed error class:
    `SuggestMemoriesUpstreamError` for LLM provider
    failures (parallels
    `NextEpisodeSuggestionUpstreamError`).

- `shell/apps/compositions/views.py` — add
  `CompositionViewSet.suggested_memories` action
  (`GET /api/compositions/{id}/suggested-memories?n=3&refresh=false`).
  - Response: 200 with candidates list (possibly empty);
    404 for non-member / non-existent; 502 for upstream
    failure with operator-facing detail.

- `shell/apps/memory/tests/test_suggest_memories.py` —
  new test module. Cover: service unit + endpoint
  contract + cache hit/miss + refresh param + permissions
  + upstream error → 502 + vocabulary-leak invariant on
  operator-facing error detail (banned-word list).

Estimated: ~500 lines including tests.

**Slice 281.1 completes when:**

- All new tests pass.
- Wider `apps/memory/tests/` + `apps/compositions/tests/`
  regressions pass.
- Endpoint verified via `curl` or Django shell against
  composition `772e9012` returns valid candidates.
- Silent (no SPA changes). The v1 UX surface + all other
  operator behavior unchanged.

**Decision gate:** review with Chris + ChatGPT before
starting Slice 281.2.

### Slice 281.2 — Frontend curator cards + wiring + tests

Add the operator-facing surface.

**New files:**

- `web/src/lib/api/memory.ts` — new module (or extend
  `web/src/lib/api/recipes.ts`). Add:
  - `getSuggestedMemories(compositionId, opts)`
  - `useSuggestedMemories(compositionId, opts)` — react-
    query hook, Zod-validated response, staleTime = 30min
    matching server cache, `refetchOnWindowFocus=false`.

- `web/src/components/narrative-memory-panels.tsx` —
  extend existing file:
  - Add sub-component `SuggestedMemoriesSection` inside
    `NarrativeMemoryPromotePanel`, rendered ABOVE the
    existing `What changed?` textarea.
  - Split into outer `SuggestedMemoriesSection` (gates on
    query having data) and inner card renderer (owns
    per-card state).
  - Each card manages local state: `pending`, `editing`,
    `remembered`, `skipped`.
  - `[Remember this]` → calls existing
    `usePromoteMemories` mutation with
    `{body, witnessed_by: []}` (defaults to whole-cast
    convention).
  - `Edit` → inline editor pre-filled with candidate body;
    on save → same submit path.
  - `Skip` → local dismiss (no persistence).
  - After promotion: card collapses to `✓ Remembered.`
    state; the row appears in the existing recap list
    below.

- `web/src/components/narrative-memory-panels.test.tsx` —
  extend existing test file:
  - Render states: loading, empty, 3-5 candidates, error.
  - `[Remember this]` calls mutation with correct
    arguments.
  - `Edit` → in-place editor → save → mutation.
  - `Skip` → card dismissed, doesn't call mutation.
  - Vocabulary-leak invariant: no banned words visible in
    the rendered panel.
  - Existing textarea + availability radio work
    byte-identically.

Estimated: ~400 lines including tests.

**Slice 281.2 completes when:**

- All new tests pass.
- Wider frontend regressions pass (episode-cast-picker,
  episode-composition-workflow, universes.brief,
  universes.detail, memories-used-panel, memories-used-
  summary, narrative-memory-panels — matching the v1
  landing set of 42 tests + any new tests).
- Runtime dogfood: open completed composition `772e9012`
  detail page in the SPA, see cards, click `[Remember
  this]` on one card, verify recap list updates within
  2s.
- Existing manual `What changed?` path works
  byte-identically.

**Decision gate:** review with Chris + ChatGPT before
starting Slice 281.3.

### Slice 281.3 — Chris operator dogfood + acceptance

Do NOT implement additional features. Instead, hand the
feature back to Chris for operator dogfood on completed
compositions.

Chris dogfoods against a real Fox & Flour and/or Patch's
Workshop composition. Measure against §79.13 acceptance
criteria:

1. Zero implementation vocabulary visible in the panel.
2. Chris + one other operator can complete a
   `[Remember this]` on ≥1 card without asking
   clarifying questions.
3. Remembered candidate appears in "What we remember from
   this render" within 2s.
4. Remembered candidate later surfaces in "Where could this
   story go next?" at Q280.8-comparable rates.
5. Cost per composition detail page load ≤ $0.03.
6. Loading state does not block the rest of the page.
7. Error state is silent — LLM outage does not surface a
   banner; existing textarea remains fully usable.
8. Existing manual `What changed?` path works
   byte-identically to today's shipped behavior.

**Slice 281.3 completes when:** dogfood evidence meets
all 8 criteria, OR when specific criteria are documented
as needing follow-up work (which would be Slice 281.4+
under Chris + ChatGPT authorization).

**Decision gate:** Chris + ChatGPT review dogfood
evidence and decide the next slice — refinement,
declared-shippable, or a specific fix.

---

## §4 Working method preserved

SESSION 281 inherits SESSION 280's working method
verbatim:

**Every slice:**

1. **ORIENT / AUDIT** — current substrate, real code,
   real DB. Do not skip this even for "obvious"
   implementations.
2. **State the falsifiable question or implementation
   acceptance target.**
3. **For experiments:** rubric + predictions LOCKED in a
   separate commit BEFORE execution. Never revise
   post-hoc.
4. **Make the smallest change** that answers the
   question or clears the acceptance criterion.
5. **Test** with focused regression coverage.
6. **Dogfood through the real operator UI** — not just
   the test suite. If UI behavior is the question,
   inspect the actual rendered result.
7. **Inspect actual evidence.** Compare prediction /
   acceptance criterion vs runtime observation.
8. **Document durably** — every substantive finding lives
   under `/docs/design/`, not in terminal output.
9. **Decision gate** — end each slice with an explicit
   recommendation and wait for Chris + ChatGPT approval
   before proceeding.
10. **Do NOT assume implementation is automatically the
    next step** when runtime evidence raises a new
    product question. If Slice 281.2 dogfood reveals a
    UX friction that requires a different design
    approach, pause and audit before continuing.

**Roles preserved from SESSION 280:**

- **Chris** operates / dogfoods the SPA in a real
  browser; approves scope-lock at each decision gate.
- **Claude** is repository operator / engineer; writes
  code + tests + documentation; runs backend probes and
  ORM-level verification.
- **ChatGPT** is architecture / product / research
  partner; reviews scope-locks, prediction locks, and
  decision gates.

Keep findings durable under `/docs/design/`. Prefer
appending to existing session docs rather than creating
parallel files unless a new file is genuinely warranted.

---

## §5 Substrate state at handoff

### Production code

- HEAD at handoff: `675b5c4` (plus trailer).
- v1 "Where could this story go next?" surface: LIVE at
  commit `25b3168` + `d7931b1` SHA trailer. Files:
  - Backend service:
    `shell/apps/universe/services/next_episode_suggestions.py`
  - Backend endpoint:
    `shell/apps/universe/views.py` (UniverseViewSet action
    `next_episode_suggestions`)
  - Frontend hook: `web/src/lib/api/universes.ts`
    (`useNextEpisodeSuggestions`)
  - Frontend component:
    `web/src/components/possible-next-episodes.tsx`
  - Wiring:
    `web/src/routes/workspace/universes.$id.episodes.tsx`
- All other production code unchanged since SESSION 280
  opened. Do NOT modify unrelated code during the v1.5
  slice.

### Test suite baseline

Before beginning implementation, re-run and confirm green:

```
set -a; source .env; set +a
python -m pytest apps/universe/tests/ apps/memory/tests/ apps/compositions/tests/ 2>&1 | tail
```

Expected: 115+ backend tests pass across the universe app;
adjacent app tests also green.

Frontend:

```
cd web && npx vitest run 2>&1 | tail
```

Expected: all frontend tests green.

If any test fails during baseline, PAUSE and investigate
before proceeding with implementation.

### Existing promoted Fox & Flour memories — LEAVE IN PLACE

Chris's explicit instruction from the SESSION 280 closeout
authorization:

> LEAVE BOTH IN PLACE. Do not archive, edit, supersede,
> or normalize them. They are valid world facts and will
> remain as natural dogfood substrate.

The two rows:

| ID | Kind | Body | Source |
|---|---|---|---|
| `abac5486-6404-411b-ad42-54c9884b980f` | `event` | "Ruby and Tyson agreed that when they are closing the bakery together, neither one leaves until the other says they have what they need." | Q280.7 promotion (§74) |
| `fa35eb8f-098d-4fbf-86a3-3e38961c059e` | `dialogue_callback` | "Tyson joked that the mascot might be left inside doing community outreach after closing." | Q280.8 promotion (§78) |

Both are:
- `status=remembered`, `archived_at IS NULL`
- `witnessed_by = [Ruby, Tyson]`
- `source_composition_id = 772e9012-4d26-4f93-a50c-158b4e8a42f1`
- `episode_id = eb47350e-b1cf-4347-aa4f-5bf514d66d2e`
- `universe_id = 1a0af807-dd6a-47cd-bfaa-3d088f1c105f`
  (Fox & Flour Bakery)
- Embedding populated

If Slice 281.1 tests need to run against a controlled
memory pool, use test-fixture memories inside the test
transaction — do NOT edit the two production rows above.

### Dogfood Universes — do not modify

**Patch's Workshop** (`56d16b63-652e-4f54-bc7e-39114bbfc4c5`):
- Cast: Patch, Rivet.
- 32 Episodes as of SESSION 280 close.
- 14 REMEMBERED memories (all `kind=event`), including
  the canonical PATCH OVERRIDES memory (`c86d4902-…`)
  and the Agent-arc cluster documented in Q280.6.
- **Strong existing continuity corpus.** Epistemic-
  asymmetry findings from Finding 4i (Q280.4i-1,
  Q280.4i-4) should NOT be accidentally rewritten during
  curator implementation. Fine to reference from tests
  read-only.

**Fox & Flour Bakery** (`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`):
- Cast: Ruby, Tyson.
- 11 Episodes as of SESSION 280 close (including
  `eb47350e` "After getting locked out…" created during
  Chris's dogfood).
- 2 REMEMBERED memories (§5 above).
- **Universe.brief:** *"Fox & Flour Bakery is a warm
  neighborhood artisan bakery built around small-batch
  baking, naturally leavened sourdough, handcrafted
  pastries, seasonal desserts, and celebration cakes."*
- Notable Episodes for dogfood: lockout (`d684332f`),
  closing routine + mascot (`eb47350e`), haunted bakery
  (`2e58568a`), freezer discovery (`07cacf51`), mascot
  needed (`49ead0ac`), baking competition (`ebd099c6`),
  coffee-too-serious (`b652a31e`).
- Composition `772e9012` (attached to `eb47350e`) is
  the Q280.6 / Q280.7 / Q280.8 / Q280.9 primary
  specimen. Full 11-turn dialogue preserved in the
  audit doc + probe evidence.

**Do not modify either Universe merely to make a test
pass.** Use test-transaction fixtures for isolated tests.

---

## §6 Existing v1 story-direction feature (context for SESSION 281)

The v1 "Where could this story go next?" surface is
already shipped and works standalone. SESSION 281 should
NOT modify it.

**Where it appears:** Universe Episodes list page
(`/workspace/universes/:id/episodes`), above the
existing `[New Episode]` button, when the Universe has
≥ 1 non-archived Episode.

**What substrate it uses:** Universe.brief + all
non-archived Episodes (title + operator_topic) + all
REMEMBERED memories (kind + weight + witnessed_by + body
+ referenced_count) + cast (name + tone + personality
prefix). See §61 of SESSION 280 audit doc.

**Operator actions:**
- Pick a suggestion (`[Use this]` → opens Episode-create
  form with topic pre-filled + dismissable chip).
- Ignore all suggestions (existing `[New Episode]` button
  works unchanged).
- Refresh (`[Different ideas]` button; bypasses cache).
- Write their own topic in the existing create form
  (unchanged behavior).

**Key property:** the v1 surface does NOT require curated
memories to function. Q280.5-1 demonstrated Fox & Flour
with 0 memories still produced 6/6 STRONG suggestion sets.

**How v1.5 curator memory affects v1 suggestions:** when
the operator promotes a memory via the v1.5 curator (or
via the existing free-text path), that memory enters the
Universe's memory pool and becomes eligible input to the
v1 suggestion service. Q280.8 validated that callback-
shape memories with distinctive lexical anchors surface
in v1 suggestions at ~30% RCS / ~11% CV rate.

**Neither surface depends on the other.** If Slice 281.2
lands and operators do not use it, v1 continues to work.
If v1.5 curator memories don't affect suggestions at
expected rates, the v1 surface still produces useful
options from Episode topics.

---

## §7 Deferred findings ledger — carried forward

Preserve distinctly; **do NOT let these expand the first
SESSION 281 slice.** Each remains valid but is separate
from the initial v1.5 implementation mission.

### 7.1 Finding 4i remaining questions

- **Q280.4i-3** (construct-valid mental-state private
  specimen) — proposed at §25 of SESSION 280 audit doc,
  never executed. Designed to test whether a genuinely-
  private memory (e.g., a character's private mental
  resolution) that Patch could not plausibly discover
  independently preserves epistemic asymmetry more
  cleanly than the compromised PATCH OVERRIDES specimen.
- **Q280.4i-5** — multi-Episode Scene 3 continuity test.
  Would test whether Rivet's private knowledge is
  maintained across an intervening unrelated Episode.
  Not designed.
- **U-3a** (SESSION 280 §20.8) — implicit witness cue
  ablation. Would isolate the implicit "Rivet found"
  cue from the explicit "chose not to tell him"
  withholding directive.
- **U-4, U-6** — generalization across characters /
  Worlds, and whether Semantic-2 storytelling is
  achievable as a general product primitive without
  substrate change.

**None of these are blockers for v1.5 curator UX.** They
are legitimate follow-ups for a future session where
Chris + ChatGPT decide to return to Semantic-2 questions.

### 7.2 §72.7 verifier boundary

The K6.4 / D-POS verifier does not include
`Episode.operator_topic` in `build_allowed_vocabulary`
(`shell/character_os/claim_verifier.py:741-803`).
Consequence: claims semantically authorized by the
operator's own Episode topic are flagged as unsupported
(e.g., "bakery mascot" flag on Composition `772e9012`).

Small scope-locked implementation slice would add
`Episode.operator_topic` content to
`build_allowed_vocabulary` when called from a
dialogue-scene context. Documented as §72.7. **Not a
blocker for v1.5 curator UX** — separate concern.

### 7.3 Q280.9 curator variance

Q280.9 ran with n=1 LLM call. §76.10 identified as
"newly-visible sub-question" the question of whether
curator output is stable across refreshes. A future
Q280.9-refresh experiment (n=3+) would characterize
variance. Not blocker.

### 7.4 Curator behavior on tension-rich scenes

Q280.9 ran only on Fox & Flour composition `772e9012`
(cooperative source scene). §76.11 B¹¹ proposed a
matched companion probe on Patch's Workshop `4598fcfa`
(tension-rich PATCH OVERRIDES origin scene) to test
whether model curator output shape depends on source
scene shape. Not run. Not blocker.

### 7.5 Memory-shape / narrative-gravity questions

Q280.7 disconfirmation + Q280.8 confirmation together
support a shape-selective bridge hypothesis (§74.8 →
refined at §78.10 as classification B**). The specific
predictive rules (which shapes surface, at what rates,
under what topical conditions) are documented but not
fully characterized. Would be a science-focused future
session. Not blocker.

### 7.6 Visual storytelling / non-talking-head work

Finding 4c from SESSION 279 handoff (Visual composition
boundary) was preserved unopened throughout SESSION 280.
Chris explicitly excluded the mascot-clause fact from
Q280.7 because it would pull dogfood toward this
deferred visual limitation. Remains open. Not blocker
for v1.5 curator UX (v1.5 is talking-head-friendly by
design).

### 7.7 Content-format backlog

`docs/design/CONTENT_FORMAT_BACKLOG.md` — 20 video
formats / pipelines the V-arc's 18 recipes don't cover
but the primitives could ship. Not blocker.

---

## §8 What SESSION 281 must NOT do

- Do NOT begin implementation before completing §1
  orientation.
- Do NOT modify the v1 "Where could this story go next?"
  surface (`possible-next-episodes.tsx` +
  `next_episode_suggestions` service + endpoint +
  wiring). Preserved unchanged.
- Do NOT modify existing `NarrativeMemoryPromotePanel`
  behavior beyond adding the `SuggestedMemoriesSection`
  ABOVE the existing textarea. Existing manual
  `What changed?` field + availability radio + button +
  recap list all work byte-identically.
- Do NOT modify `promote_from_composition` service
  signature.
- Do NOT modify `NarrativeMemory` schema, kinds,
  weights, or witness semantics.
- Do NOT modify K6.4 / D-POS verifier.
- Do NOT modify retrieval predicate
  (`retrieve_universe_memory`) or synthesis prompt
  assembly (`_assemble_system_prompt`).
- Do NOT auto-promote any memory (Chris's Option A¹¹
  boundary preserved).
- Do NOT create StoryArc / NarrativeThread / OpenThread
  models.
- Do NOT change Ruby / Tyson / Patch / Rivet identities,
  personality, K2, or existing memories.
- Do NOT archive either of the two SESSION 280-promoted
  Fox & Flour memories (`abac5486-…` cooperation OR
  `fa35eb8f-…` callback).
- Do NOT install additional Python or npm dependencies
  without explicit Chris + ChatGPT approval.
- Do NOT expose implementation vocabulary in operator-
  facing copy (see §2 banned-word list).
- Do NOT open deferred findings from §7 during the v1.5
  first-slice implementation. They are separate future
  scope-lock decisions.

---

## §9 What SESSION 281 CAN safely resume

- Read the SESSION 280 audit doc §79 for exact v1.5
  design details (placement, copy, hidden vs visible
  metadata, non-goals, risks, acceptance criteria).
- Read the SESSION 280 audit doc §80 for the closeout
  synthesis of the whole SESSION 280 arc.
- Read the Q280.9 probe script
  (`scripts/session280_q280_9_curator_probe.py`) as the
  reference implementation of the curator prompt shape.
- Read the v1 suggestion service
  (`shell/apps/universe/services/next_episode_suggestions.py`)
  as the reference pattern for service + cache +
  endpoint shape.
- Read the v1 UX component
  (`web/src/components/possible-next-episodes.tsx`) as
  the reference pattern for outer-wrapper + inner-
  hook-owner + operator-friendly copy + vocabulary-leak
  test.
- Run existing test suites as a green baseline before
  and after each slice.
- Query the DB read-only via `manage.py shell` (DB port
  5434 per `.env`; use `set -a; source .env; set +a`
  before invocation) to verify substrate state.
- Restart local servers via
  `bash scripts/stop-local.sh && bash scripts/start-local-real.sh`
  to pick up new code during dogfood.

---

## §10 Environment notes

- **Docker infra (Postgres + Redis)** left up by
  `stop-local.sh` — do not restart it during development.
- **DB port is 5434** per `.env` — Django default
  fallback of 5433 will fail with a confusing "trust
  authentication failed" error via Docker port-proxy.
  Always `set -a; source .env; set +a` before
  `manage.py shell` or ad-hoc psycopg.
- **pytest auto-regenerates** `CHARACTER_OS_INVENTORY.md`
  — never commit the post-pytest version blindly
  (memory: `feedback_pytest_auto_regens_inventory.md`).
- **Chris drives operator-facing SPA gestures**; Claude
  tails DB / logs / API in parallel (memory:
  `feedback_human_ai_testing_split.md`).
- **Real-mode dogfood after operator-facing slices** —
  do NOT propose curl as an alternative to the UI flow
  (memory:
  `feedback_real_mode_dogfood_after_operator_slices.md`).
- **Fix-shaped handoff compounds** — if implementation
  exposes an unexpected finding, record it as a
  fix-shaped candidate for the next slice rather than
  fixing in place (memory:
  `feedback_fix_shaped_handoff_compounds.md`).

---

## §11 Reproduction / artifact index

### 11.1 Key files (as of SESSION 280 close)

- SESSION 280 audit + design + evidence (single durable
  doc):
  `docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`
  (~9,500 lines).
- SESSION 280 handoff origin:
  `docs/design/SESSION_280_HANDOFF.md`.
- v1 suggestion service:
  `shell/apps/universe/services/next_episode_suggestions.py`
  (~350 lines).
- v1 endpoint action:
  `shell/apps/universe/views.py::UniverseViewSet.next_episode_suggestions`.
- v1 component:
  `web/src/components/possible-next-episodes.tsx`
  (~170 lines).
- v1 hook:
  `web/src/lib/api/universes.ts::useNextEpisodeSuggestions`.
- v1 wiring:
  `web/src/routes/workspace/universes.$id.episodes.tsx`.
- v1 tests:
  `shell/apps/universe/tests/test_next_episode_suggestions.py`
  (16 tests) +
  `web/src/components/possible-next-episodes.test.tsx`
  (8 tests).
- Q280.9 curator probe (reference for v1.5 prompt shape):
  `scripts/session280_q280_9_curator_probe.py` +
  evidence at
  `docs/design/session280_experiment_data/q280_9_curator_evidence.json`.
- Q280.8 bridge probe (reference for BRIDGE-CONFIRMED
  end-to-end pattern):
  `scripts/session280_q280_8_callback_bridge_probe.py` +
  evidence at
  `docs/design/session280_experiment_data/q280_8_{control,treatment}_evidence.json`.

### 11.2 Session 280 commit chain (all pushed to `origin/main`)

Full SESSION 280 SHA index preserved at §80.J of the
audit doc. Landing SHAs for the v1 surface (SESSION 281's
baseline):

- v1 UX implementation: `25b3168`
- v1 implementation SHA trailer: `d7931b1`
- SESSION 280 final closeout: `675b5c4`

### 11.3 Provider cost baseline

- SESSION 280 total: **~$0.32** across 4 executed
  experiments.
- v1 suggestion service per call: ~$0.005-$0.02 depending
  on Universe size (10-32 Episodes tested).
- Q280.9 curator per call: ~$0.02 (single call).
- v1.5 curator per composition detail page load
  (estimated): ~$0.02, cached 30 min.

---

## §12 Closeout

SESSION 281 opens with a clean tree at HEAD **`675b5c4`**
(plus a trailer commit recording SHAs across both closeout
artifacts). All SESSION
280 conclusions are durable in
`docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`.

The mission is clear: implement the v1.5 curator UX per
§79 design + §79.10 shape, following the ORIENT →
smallest-slice → dogfood working method.

Chris drives dogfood. ChatGPT drives scope-locks +
architecture judgment. Claude drives implementation +
testing + documentation.

No production behavior changes until Slice 281.1 lands
by explicit Chris + ChatGPT approval.

Working method preserved. No new deferred findings opened
by this handoff.
