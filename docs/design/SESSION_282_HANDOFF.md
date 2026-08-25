# SESSION 282 — Handoff (from SESSION 281)

## Status at the top

- **SESSION 281 is CLOSED.**
  - Full audit trail lives at
    `docs/design/SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md`
    (§1-§U11).
  - §U is the ratified closeout section.
- **Slice 281.2 curator surface is LIVE** and dogfooded.
  Operators promoting memories via `[Remember this]` cards
  is now the normal path.
- **SESSION 282 must BEGIN with orientation + scope-lock.**
  No implementation, probe, or provider-spend experiment is
  pre-authorized by this handoff.

**Purpose of this document:** compact self-contained
orientation for SESSION 282 Claude + ChatGPT so neither has
to re-read the ~4000+ line SESSION 281 audit to resume work.
Point to the audit for details.

---

## §1 Repo state

Fresh session should verify:

```
git rev-parse HEAD          # should descend from SESSION 281 closeout SHA
git status                  # expect clean
git branch --show-current   # expect main
```

The full SESSION 281 SHA chain lives at
`SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md §U9`.

If working tree is not clean, PAUSE and investigate before
proceeding — the SESSION 281 close was clean end-to-end.

---

## §2 What SESSION 281 shipped

### 2.1 Slice 281.1 — backend curator service + endpoint

`GET /api/compositions/<id>/suggested-memories/`

* Service: `shell/apps/memory/services.py::suggest_memories_from_composition`
* Endpoint: `shell/apps/compositions/views.py::CompositionViewSet.suggested_memories`
* 30-min composition-scoped cache; cache key includes
  latest same-composition NarrativeMemory `created_at`.
* Empty-substrate short-circuit (non-completed / empty
  `synthesized_brief`) → 200 with empty candidates, no LLM
  call.
* Typed `SuggestMemoriesUpstreamError` → HTTP 502.
* **NEVER writes NarrativeMemory.**

### 2.2 Slice 281.2 — operator-facing curator cards

Rendered inside existing `NarrativeMemoryPromotePanel`
ABOVE the manual `What changed?` textarea. Copy:

> **A few ideas from what just happened.**
> Remember the ones that might matter later.

Each card: candidate body + optional natural-language hint +
`[Remember this]` · `Edit` · `Skip`.

Divider `Or write your own:` transitions into the existing
manual promotion path (byte-identical, no regressions).

**Load-bearing persistence policy:** `[Remember this]` posts
body + `witnessed_by:[]` ONLY. Model-authored `kind`,
`witnesses`, and `narrative_gravity_note` NEVER persist as
durable authority. The backend serializer's default
event/peripheral kind + weight applies, matching today's
manual-textarea contract.

**Human-authority boundary preserved:**
AI notices. Human decides. Nothing durable without explicit
approval.

### 2.3 Operator-vocabulary discipline

The Slice 281.2 SPA copy and 502 error detail contain NONE
of the banned implementation vocabulary (see
`SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md §M4` for the
27-word banned list). Any operator-facing UI SESSION 282
adds MUST preserve this discipline.

---

## §3 Real Chris dogfood (Slice 281.3)

Chris opened the SPA and:

1. Reviewed curator cards on composition
   **`772e9012-4d26-4f93-a50c-158b4e8a42f1`** (Fox & Flour,
   Episode `eb47350e-…`).
2. Promoted exactly ONE candidate via `[Remember this]`:
   > "Ruby still wants Fox & Flour to have a welcoming
   > mascot for the neighborhood."
   → `NarrativeMemory 73acdfc0-44a1-40a0-abdc-e4f8069f6924`
     (`kind=event`, whole-cast, `source_composition=772e9012`).
3. Chose an existing v1 "Where could this story go next?"
   suggestion verbatim:
   > "A customer asks Fox & Flour to create a celebration
   > cake for an event tied to the neighborhood baking
   > competition."
4. Used it to create Episode `f4faa13b-…` + composition
   **`565cd8c8-2cf7-47e6-9f01-f57103193648`** — this
   became the "weak specimen" for Slice 281.3
   investigation.
5. Curator on `565cd8c8` returned 3 candidates. Chris
   **rejected all 3** — human-in-the-loop boundary worked
   as designed; procedural canon did not accumulate.

Chris's dogfood judgment: the STORY EXECUTION on `565cd8c8`
was procedural — Ruby + Tyson discussed how they WOULD
handle the customer request rather than dramatizing the
event on-stage. That triggered Slice 281.3 investigation.

---

## §4 Story-execution investigation summary (α + ε + ζ + ξ + π)

Full evidence at
`SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md §N-§T`. High-
level summary:

* **Q281.3-α** (paired F&F dialogue probe, ~$0.26): topic
  grammar CAN drive execution at fixed substrate. Same
  everything → off-stage past-tense topic collapses to
  procedural; on-stage cast-verb + complication topic
  produces event.
* **Q281.3-ε** (3× v1 sampling on F&F, ~$0.036): v1 output
  is TRIMODAL on F&F — 53% strong / 27% mixed / 7%
  weak-CONTROL / 13% ambiguous. Bad `565cd8c8` shape is
  real but rare (~7%).
* **Q281.3-ζ** (3× v1 sampling on Patch's Workshop,
  ~$0.070): v1 output is SUBSTRATE-SENSITIVE, not
  generator-stable. Patch's Workshop 100% complication vs
  F&F 80%; 0% weak-CONTROL vs 7%; dense character-driven
  callbacks vs lexical adjacency.
* **Q281.3-ξ** (single dialogue_scene on Patch's Workshop
  D+C off-stage-subject topic, ~$0.078): rich substrate
  can PROTECT a D+C topic from procedural collapse. n=1,
  event-shaped 12-turn scene on first attempt, memory
  absorbed naturally.
* **Q281.3-π** (design synthesis, $0.00): the correct
  product response is Hθ (substrate SHAPE as first-class
  concern) — but the shipped Slice 281.2 curator loop IS
  a candidate mechanism. Recommend closing SESSION 281
  without synthesis-side intervention.

Total investigation spend: ~$0.44.

---

## §5 Final Q281.3-π decisions (RATIFIED)

1. **No v1 "Where could this story go next?" change now.**
2. **No `dialogue_scene` synthesis change now.**
3. **No design/implementation of Hη (SPA-side rewrite
   affordance).** Fails operator-vocabulary discipline.
4. **Q281.3-ο (verb-tense ablation) deferred** — would not
   gate a current product decision.
5. **Story-execution / substrate SHAPE finding preserved**
   as a legitimate future research direction.
6. **Do NOT equate substrate richness with memory count.**
   The finding is about SHAPE, not volume.

---

## §6 Careful Hθ wording (critical)

The substrate finding points to interaction among (any
subset of):

* character-attributed past events
* Episode/topic shape
* unresolved threads
* consequences
* discoveries
* recurring artifacts
* character wants
* cast/business-brief shape
* structurally-aligned NarrativeMemory
* continuity richness

Patch's Workshop differs from Fox & Flour across SEVERAL of
these axes; none was isolated by SESSION 281's investigation.

The curator loop (Slice 281.1/281.2) MAY organically improve
substrate over time (it emits character-attributed
event-shaped memory bodies by construction), but that
remains a HYPOTHESIS to test. **Do NOT state the curator
alone has been proven sufficient.**

---

## §7 Patch's Workshop vs Fox & Flour — why the comparison matters

| axis | Fox & Flour | Patch's Workshop |
|---|---|---|
| Episodes | 11 | 32 |
| REMEMBERED memories | 3-4 (incl. mascot from S281.3 dogfood) | 14 |
| Memory shape | short bodies, some character-attributed | all character-attributed events with narrative bodies |
| Universe.brief | paragraph framing "warm neighborhood gathering place" | empty |
| Cast business briefs | service framing ("helps customers choose") | experimental framing ("Patch builds strange things") |
| Episode-title grammar | mixed | heavy cast-verb ("Patch decides X", "Rivet finds Y") |
| v1 complication rate (n=15) | 80% | 100% |
| v1 weak-CONTROL rate | 7% | 0% |
| v1 callback density | lexical adjacency | character-driven named-thread |

Patch's Workshop is the mature/rich substrate reference;
Fox & Flour is the young/thin substrate reference. Both
Universes MUST remain untouched — they are the canonical
comparison specimens for any future SESSION 282+ probe.

---

## §8 Live substrate — MUST remain intact

### Fox & Flour Bakery (`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`)

Cast: Ruby, Tyson.

Three durable memories (all `status=remembered`,
`archived_at=NULL`, whole-cast witnesses, embedding
populated):

| id | kind | body | source |
|---|---|---|---|
| `abac5486-6404-411b-ad42-54c9884b980f` | event | "Ruby and Tyson agreed that when they are closing the bakery together, neither one leaves until the other says they have what they need." | S280 Q280.7 |
| `fa35eb8f-098d-4fbf-86a3-3e38961c059e` | dialogue_callback | "Tyson joked that the mascot might be left inside doing community outreach after closing." | S280 Q280.8 |
| `73acdfc0-44a1-40a0-abdc-e4f8069f6924` | event | "Ruby still wants Fox & Flour to have a welcoming mascot for the neighborhood." | S281 Slice 281.3 dogfood |

Notable compositions for future dogfood comparisons:

* `772e9012-4d26-4f93-a50c-158b4e8a42f1` — strong-execution
  reference (SESSION 280 Q280.6 / Q280.7 / Q280.8 / Q280.9
  primary specimen)
* `565cd8c8-2cf7-47e6-9f01-f57103193648` — weak-execution
  specimen from Chris's dogfood (Slice 281.3 investigation
  target)

Do NOT archive, edit, supersede, or normalize any of these
memories or compositions.

### Patch's Workshop (`56d16b63-652e-4f54-bc7e-39114bbfc4c5`)

Cast: Patch, Rivet.

32 Episodes, 14 REMEMBERED memories including the canonical
`PATCH OVERRIDES` row (`c86d4902-…`) and the Agent-arc
cluster documented in SESSION 280 Q280.6.

**Strong existing continuity corpus.** Epistemic-asymmetry
findings from Finding 4i should NOT be accidentally
rewritten. Fine to reference read-only from tests + probes.

---

## §9 Deferred hypotheses / questions ledger

Preserve distinctly; **do NOT let these expand the first
SESSION 282 slice.** Each is a legitimate future scope-lock
candidate but SESSION 282 must scope-lock its own priority.

### 9.1 From SESSION 281 Slice 281.3 investigation

* **Q281.3-β** — memory-presence pressure isolation (same
  topic × memory-in / memory-out paired probe). ~$0.20-$0.40.
* **Q281.3-γ** — memory-framing wording swap ("Use them" →
  "may cite"). ~$0.10-$0.20.
* **Q281.3-ο** — topic verb-tense ablation on F&F. ~$0.20-
  $0.30. Only worth running if a future prompt-side
  decision hinges on Hβ vs Hλ.
* **Longitudinal F&F dogfood** — over 3-6 additional
  compositions of curator-driven substrate accumulation,
  does F&F's v1 distribution shift toward Patch's
  Workshop's? Cost per periodic Q281.3-ε rerun: ~$0.036.
* **Hκ** — cast business-brief SHAPE ablation. Requires
  substrate mutation (out of scope for read-only probes)
  OR a third Universe with intermediate substrate.
* **Hι** — substrate-adaptive generator design. Deferred;
  complex.
* **Hβ-permissive** — v1 soft preference for dramatizable
  shape. Deferred unless longitudinal evidence warrants.

### 9.2 Independent SESSION 280 carry-forwards

* **Q280.9 curator variance** — n=1 curator run to date;
  variance across refreshes uncharacterized. Cost: ~$0.02
  per additional Q280.9 rerun.
* **Curator on tension-rich scenes** — matched Q280.9
  probe on Patch's Workshop composition `4598fcfa` (PATCH
  OVERRIDES origin scene) never run. Would test whether
  curator output shape depends on source-scene shape.
* **Semantic-2 / epistemic-asymmetry follow-ups** —
  Q280.4i-3 (construct-valid private mental-state
  specimen), Q280.4i-5 (multi-Episode Scene 3 continuity),
  U-3a (implicit witness cue ablation), U-4/U-6
  (generalization across characters / Worlds). All
  documented in
  `SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`.
* **§72.7 verifier-boundary false-positive** on
  `Episode.operator_topic` — small scope-lockable slice
  documented in the SESSION 280 audit doc.
* **SESSION 279 Finding 4c** — visual-storytelling /
  non-talking-head limitation. Preserved unopened through
  SESSION 280 + 281.
* **`docs/design/CONTENT_FORMAT_BACKLOG.md`** — 20 video
  formats/pipelines the V-arc's 18 recipes don't cover.

---

## §10 Candidate SESSION 282 directions (NOT authorization)

Presented as candidates. SESSION 282 must orient + scope-
lock its own priority. Do NOT treat any as pre-authorized.

### Direction A — Longitudinal substrate-organic-growth observation

Suggested candidate framing:

> "What makes a Character OS Universe narratively alive,
> and how should the product help an operator develop
> that naturally without requiring them to think like a
> screenwriter or AI engineer?"

Continue routine operator dogfood on Fox & Flour (or other
young Universes). Promote memories via Slice 281.2 as they
naturally warrant. Periodically re-run Q281.3-ε to check
whether F&F distribution shifts toward Patch's Workshop's
shape. Prefer real dogfood signal over synthetic
classification.

If distribution shifts materially → Hθ validated; no
synthesis-side intervention. If it does NOT → Hβ-permissive
or Hι becomes a legitimate future consideration with real
evidence backing.

### Direction B — Address a specific SESSION 280 deferred finding

Pick one of §9.2's carry-forwards (Q280.9 variance, curator
tension-scene probe, verifier boundary, Finding 4c, etc.)
and scope-lock a smallest slice against it.

### Direction C — Address a specific SESSION 281 deferred finding

Pick one of §9.1's deferreds (Q281.3-β, γ, ο, or Hκ) IF
Chris + ChatGPT judge the question decision-relevant AT
THAT TIME.

### Direction D — Something else

If real dogfood or a new question emerges before SESSION
282 begins, that may take priority. Chris + ChatGPT decide.

---

## §11 Required working method

Preserved verbatim from SESSION 281 (which inherited from
SESSION 280).

Every slice:

1. **ORIENT / AUDIT** — current substrate, real code, real
   DB. Do not skip this even for "obvious" implementations.
2. **State the falsifiable question or implementation
   acceptance target.**
3. **For experiments:** rubric + predictions LOCKED in a
   separate commit BEFORE execution. Never revise post-hoc.
4. **Make the smallest change** that answers the question
   or clears the acceptance criterion.
5. **Test** with focused regression coverage.
6. **Dogfood through the real operator UI** — not just the
   test suite. If UI behavior is the question, inspect the
   actual rendered result.
7. **Inspect actual evidence.** Compare prediction /
   acceptance criterion vs runtime observation.
8. **Document durably** — every substantive finding lives
   under `/docs/design/`, not in terminal output.
9. **Decision gate** — end each slice with an explicit
   recommendation and wait for Chris + ChatGPT approval
   before proceeding.
10. **Do NOT assume implementation is automatically the
    next step** when runtime evidence raises a new product
    question. Pause and audit if runtime evidence conflicts
    with prior assumptions.

Roles:

* **Chris** operates / dogfoods the SPA in a real browser;
  approves scope-lock at each decision gate.
* **Claude** is repository operator / engineer; writes
  code + tests + documentation; runs backend probes and
  ORM-level verification.
* **ChatGPT** is architecture / product / research
  partner; reviews scope-locks, prediction locks, and
  decision gates.

Cost discipline (from SESSION 281 §P durable lesson):
* v1 next-Episode suggestions: ~$0.005-$0.02/call
* Q280.9 / Slice 281.1 curator: ~$0.02/call
* Full `dialogue_scene` synthesis: **~$0.05-$0.10/call,
  ~$0.10-$0.20/composition** (typically 2 attempts).
  Never estimate `dialogue_scene` probes by extrapolating
  from curator or v1 call cost.

---

## §12 Operator-first boundary (LOAD-BEARING)

The operator makes STORIES.

The operator should NEVER need to understand:

* topic grammar
* dramatizability
* narrative substrate shape
* prompt structure
* retrieval mechanics
* memory kinds
* model behavior

Any SESSION 282+ solution must ultimately appear to the
operator as natural storytelling help.

Preserve:

**AI notices. Human decides. Nothing durable without
explicit approval.**

Any curator-generated content is a suggestion. No memory
becomes durable without explicit operator approval.

---

## §13 What SESSION 282 MUST NOT do

* Do NOT begin implementation before completing §1
  orientation.
* Do NOT pre-authorize any of §10's candidate directions
  as SESSION 282's first work.
* Do NOT pre-authorize the "3-6 compositions + periodic
  Q281.3-ε rerun" observation loop as automatic first
  work — carry it as a candidate direction only.
* Do NOT modify the Slice 281.2 curator UI (fully
  scope-locked; no refresh, no kind/witness controls, no
  auto-promotion).
* Do NOT modify the Slice 281.1 curator service or
  endpoint contract.
* Do NOT modify v1 "Where could this story go next?"
  service, endpoint, hook, or component.
* Do NOT modify `promote_from_composition`, retrieval,
  synthesis, verifier, memory schema, or witness
  semantics.
* Do NOT archive, edit, or supersede any of §8's live
  memories.
* Do NOT modify Ruby / Tyson / Patch / Rivet identities,
  personalities, K2 docs, or business_briefs.
* Do NOT install new Python / npm dependencies without
  explicit Chris + ChatGPT approval.
* Do NOT expose implementation vocabulary in any
  operator-facing surface.
* Do NOT collapse the Hθ finding into "more memories =
  better stories."
* Do NOT run provider-spend experiments without explicit
  spend authorization at the correct order-of-magnitude
  (see §11 cost discipline).

---

## §14 What SESSION 282 CAN safely resume

* Read the SESSION 281 audit doc for full context on any
  finding.
* Read the SESSION 280 audit doc for the deeper design
  trail behind the curator loop.
* Query the DB read-only via `manage.py shell` (from
  `shell/`; DB port 5434 per `.env`).
* Run existing test suites as green baselines.
* Restart local servers via `stop-local.sh` /
  `start-local-real.sh` for real-mode dogfood.
* Propose new falsifiable questions at any point during
  orientation — but do not execute them without scope-lock
  authorization.

---

## §15 Environment notes

Preserved from SESSION 281 handoff §10 and §P cost lesson.

* **Docker infra (Postgres + Redis)** left up by
  `stop-local.sh` — do not restart it during development.
* **DB port is 5434** per `.env` — always
  `set -a; source .env; set +a` before `manage.py shell`
  or ad-hoc psycopg.
* **Pytest MUST be invoked from `shell/`** — some tests
  read paths relative to that cwd. Running from repo root
  surfaces false failures.
* **pytest auto-regenerates**
  `CHARACTER_OS_INVENTORY.md` sometimes — always
  `git status` before committing anything.
* **Chris drives operator-facing SPA gestures**; Claude
  tails DB / logs / API in parallel (memory:
  `feedback_human_ai_testing_split.md`).
* **Real-mode dogfood after operator-facing slices** —
  do NOT propose curl as an alternative to the UI flow.
* **Fix-shaped handoff compounds** — write findings as
  fix-shaped candidates for the next slice rather than
  fixing in place.
* **Frontend baseline invocation:** `cd web && npx vitest
  run`.
* **Two pre-existing K6.4 mock-drift test failures**
  (`test_dialogue_synthesis_canon_lane` +
  `test_dialogue_synthesis_memory_lane`) predate SESSION
  281 and are out of scope per SESSION 281 handoff §8.
  Do not conflate with SESSION 282 regressions.

---

## §16 Closeout

SESSION 282 opens with a clean tree at HEAD equal to the
SESSION 281 closeout SHA (see the trailer commit that
records this handoff's SHA).

The mission is not pre-decided. SESSION 282 begins with
ORIENTATION and SCOPE-LOCK. Chris + ChatGPT decide the
next smallest falsifiable question or implementation
target based on what's most decision-relevant AT THAT TIME.

No implementation or provider-spend experiment is
pre-authorized by this handoff.

Working method preserved. Operator-first boundary
preserved. Human-authority boundary preserved.
