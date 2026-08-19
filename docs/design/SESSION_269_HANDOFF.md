# SESSION 269 — Handoff

Concise starting point for the next Character OS session. Full
SESSION 268 context lives in
`docs/design/SESSION_268_PATCH_WORKSHOP_DOGFOOD.md` (§1–§8) with
eight frozen evidence sidecars under
`docs/design/session_268_experiment_data/`. Read the sections
referenced below BEFORE implementing anything.

Working method (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Persist important findings, audits, and decisions under
`docs/design/` before stopping.

---

## Current Character OS state (as of SESSION 268 close)

- Branch: `main`. Working tree clean at close.
- `NarrativeMemory` retrieval `top_k = 1` — unchanged since
  SESSION 264 Slice 2.
- Production synthesis prompt in
  `shell/character_os/dialogue_synthesis.py` — unchanged.
- Retrieval predicate + witness eligibility filter
  (`shell/apps/embeddings/retrieval.py:499-543`) — unchanged.
- Canon boundary (`KnowledgeDocument` / `KnowledgeChunk`) —
  unchanged.
- Duration calibration + writing contract v4 + GPT-5.6-terra
  — unchanged.
- Creator-facing witness UI shipped in SESSION 267 §16 —
  unchanged (Radio A/B copy + `Available:` prefix +
  `formatWitnessAvailability()`).
- Dialogue-scene recipe / starter / synthesis / DialogueTurn
  schema — unchanged. Every turn still → `generate_avatar_speech`;
  concat is talking-heads-only.
- No source-code file modified during SESSION 268.

## Real Patch's Workshop NarrativeMemory state at SESSION 268 close

**10 active memories** (8 whole-cast + 2 Rivet-only). Sources of
truth for each row are enumerated in
`docs/design/session_268_experiment_data/06_rules_memory_promotion_verification.json`
and `08_composition_a35f20bf_evidence.json`.

Whole-cast (8):
- `f25e53af` — the agent Patch wired to the workshop thinks it runs the place.
- `48746f69` — The workshop agent began deciding which of Patch's projects it considers necessary.
- `eda32b58` — The workshop agent began rearranging the order of Patch's projects without explaining its criteria.
- `a34cc005` — Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting before the details are settled.
- `d98962e2` — Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process.
- `87d4e553` — Patch decided the workshop should create a mascot as a character-consistency experiment.
- `6b5222b1` — Patch built a workshop helper that watches for interesting events and leaves messages, but it has already started adding its own commentary to what it observes.
- `42acc26d` — Patch decided the workshop needs rules and began adopting Rivet's more methodical approach to experiments, including making predictions and changing one thing at a time.

Rivet-only (2):
- `cd73d52f` — Because it had an opinion about our work. An uninvited opinion. That is scientifically interesting and operationally irritating.
- `c86d4902` — While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him.

## SESSION 268 organic-dogfood findings

Six real Patch's Workshop Episodes rendered across the session
(pool sizes 7, 8, 8, 9, 10, 10). Two SESSION 268 promoted memories
by Chris (helper, rules) plus one earlier session (mascot);
three non-promotions across three distinct classes.

Bounded-language findings (see SESSION 268 §5 for full form):

1. Availability-condition UI works — six real renders, no
   misclassification.
2. `top_k = 1` retrieval contextually defensible at pool 7-10
   across six consecutive renders. One weak-but-harmless
   selection (pigeon topic → PATCH OVERRIDES memory,
   Observation #6). No hijack. No bleed.
3. Memory manifests through at least four distinct channels —
   background continuity, silent presence, one-sided character-
   dynamic influence, reciprocal pattern-awareness.
4. Private-memory retrieval did not textually leak in any of
   six natural non-adversarial trials. Extends but does NOT
   falsify Semantic 1 (see SESSION 267 §14.13 bounded framing).
5. Promotion quality is operator-navigable through three
   non-promotion classes: unresolved hook (box), expression of
   existing state (prediction), entertaining flavor (pigeon).
   No promote-UI change warranted on current evidence.
6. Character HISTORY (what characters expect from each other)
   is emerging alongside character DEFINITION with current
   substrate alone; no `Relationship` / `StoryThread` schema
   invented.

## Important visual-storytelling finding

Read-only audit in SESSION 268 §4.11 enumerated media
capabilities. Gap classification **B (infrastructure exists,
orchestration missing)** with plausible **D shape (separate
recipe, coexisting with `dialogue_scene`)**. Every primitive a
cutaway-aware dialogue recipe would need already ships:

- `generate_visual_clip` (Runway gen4_turbo image-to-video /
  gen4.5 text-to-video)
- `generate_image` (Runway gen4_image)
- `concat_clips` with `reencode=True` (type-agnostic on CLIP
  subtypes)
- `composite_video` (layout kinds `{pip, backdrop, cohost, broll}`)

Precedent recipes already mix avatar speech with non-avatar
visuals: `storyboard_voiced`, `talking_head_with_backdrop`,
`cinematic_visual_extended`.

Refined provisional visual-beat hypothesis (five-Episode support,
NOT ratified as architecture):

> Dialogue scenes need visual beats when the meaning lives
> materially outside the talking heads, not merely because a
> visible noun or prop exists.

Five-Episode distribution: 1 REQUIRED (box) / 2 ENHANCING
(helper, pigeon) / 2 UNNECESSARY (rules, prediction). Naïve
prop-based framing would produce false positives on 3 of 5.

## Promotion-quality findings

Six-Episode promotion table:

| Episode | Class | Promoted |
|---|---|---|
| mascot `bb0ad862` | durable decision | yes (`87d4e553`) |
| box `6e3ed367` | unresolved hook | no |
| helper `464128b1` | durable artifact + demonstrated behaviour | yes (`6b5222b1`) |
| rules `05d3612c` | durable relationship / process change | yes (`42acc26d`) |
| prediction `da341e85` | expression / deepening of existing state | no |
| pigeon `a35f20bf` | entertaining flavor | no |

Three principles worth carrying (documented, NOT ratified):

- story hook ≠ automatically durable memory
- expression of existing state ≠ new memory (would duplicate)
- good Episode ≠ automatic memory (comedic quality is not
  durability)

## Unresolved questions carried forward

From SESSION 268 §6.2:

1. Relevance-floor question — one natural weak retrieval so
   far (pigeon). Watch for more; do not build until multiple
   recurrences.
2. Visual-beat planner question — five-Episode data supports
   the refined framing but does not compel implementation.
   Continue organic dogfood; open the design question only if
   a REQUIRED-class Episode recurs across independent topics.
3. Larger memory-pool behaviour of `top_k=1` — not tested
   above 10.
4. Memory recurrence with unrelated topics — `a34cc005`
   selected three consecutive times from three related topics;
   pigeon Episode chose `c86d4902` instead, so lock-in is not
   universal but the behaviour under an unrelated-topic run at
   pool 10+ is unknown.
5. Witness-attribution research question (SESSION 267 §14.13)
   — six natural non-leakage trials extend the evidence
   without falsifying Semantic 1. A controlled experiment
   remains available but not yet compelled.
6. Character HISTORY vs DEFINITION should continue to be
   observed. Do NOT propose `Relationship` / `StoryThread`
   models on the current evidence.
7. Composition-detail IA (SESSION 266 §13.7) — promote form
   still sits below extensive technical evidence. No SESSION
   268 operator friction reported.
8. Explicit-history prompt Dogfood #2 (SESSION 266 §11.7) —
   sequencing constraint satisfied; not opened in SESSION 268
   because organic dogfood absorbed the session.

## Deferred (SESSION 268 explicitly did NOT touch)

- `top_k` — remains 1.
- Retrieval predicate / witness semantics / memory schema —
  unchanged.
- Synthesis prompt / writing contract — unchanged.
- Availability-condition UI / promote form — unchanged.
- Dialogue-scene recipe / starter / DialogueTurn schema —
  unchanged.
- Any media primitive — unchanged.
- No new recipe (`dialogue_scene_cinematic` or similar).
- No manual memory picker / "no continuity" toggle / exclude
  control.
- No relevance floor.
- No `Relationship` / `StoryThread` / `WorldEntity` models.
- No AI candidate-memory generation.
- No expose of `kind` in the UI.
- No deletion of SESSION 266 experimental Universes
  (`EXP266-WEAK`, `EXP266-STRONG`) — cleanup script at
  `docs/design/session_266_experiment_data/02a_cleanup_partial.py`
  still not authorized.
- YouTube ingest silent failure — not narrative-memory scope.

## Documentation workflow (reminder)

Important audits, experiments, runtime findings, architectural
decisions, dogfood results, and session conclusions go under
`docs/design/` BEFORE stopping. SESSION 268 followed that
discipline: §1-§8 in `SESSION_268_PATCH_WORKSHOP_DOGFOOD.md`
plus eight frozen evidence sidecars in
`docs/design/session_268_experiment_data/`.

Persist runtime evidence sidecars under
`docs/design/session_269_experiment_data/` if SESSION 269 opens
a fresh investigation, or extend the SESSION 268 evidence dir
if the work is continuous.

The SESSION 266 experimental Universes (`EXP266-WEAK`,
`EXP266-STRONG`) remain PRESERVED for forensic inspection per
operator instruction.

## Recommended first SESSION 269 questions (candidates only)

None are prescribed. All are candidates; SESSION 269 must begin
with an audit / orient pass and a falsifiable question, not
implementation. Recommended by strength of standing evidence:

### Candidate #1 — Continue organic dogfood at pool 10+

**Why:** SESSION 268 opened the ~10-memory observation window
with two data points (Obs #5, Obs #6). The pool 10+ question
(§6.2 #3) has no theoretical answer; observation is the only
way. Two more Episodes at pool 10+ (or higher if Chris promotes
another memory) would tell us whether `top_k=1` selection
begins to feel noticeably imperfect. Cheap; produces evidence
for the other candidates.

**Falsifiable form:** *Does `top_k=1` selection remain
operator-invisible / helpful across two more Episodes at pool
size 10+?*

**Smallest form:** Chris authors two more real Episodes with
whatever topics he'd already want to make. Observation-only.
Persist evidence per SESSION 268 pattern. No runtime change.

### Candidate #2 — Explicit-history prompt Dogfood #2 (SESSION 266 §11.7, still deferred)

**Why:** Sequencing constraint satisfied since SESSION 267.
Would address the ~1/3 residual reenact rate observed in
SESSION 266 §10. SESSION 268's organic dogfood surfaced no
reenact-style problems, so the urgency is low, but the slice
remains available and has an ethical answer.

**Falsifiable form:** *Does the monkey-patched explicit-history
prompt reduce reenact rate on a STRONG memory without hurting
other renders?*

### Candidate #3 — Visual-storytelling design question (only if a fresh REQUIRED-class Episode recurs)

**Why:** Five-Episode data supports the refined visual-beat
framing. Implementation is not compelled by current evidence
(1 REQUIRED across 5 Episodes). If a second REQUIRED-class
Episode appears in candidate #1 dogfood, the design question
is worth opening; if not, keep deferred.

**Falsifiable form:** *If a second REQUIRED-class Episode
appears, does the refined framing still correctly classify it
before we implement anything?*

### Candidate #4 — Composition-detail IA (SESSION 266 §13.7)

**Why:** Promote form still sits below extensive technical
evidence on the Composition detail page. No SESSION 268
operator friction. Purely UX prioritization; low signal to
open now.

---

**Do NOT start SESSION 269 in this handoff. This document is a
starting point, not a plan of record. The next session begins
with an audit / orient pass and follows evidence.**
