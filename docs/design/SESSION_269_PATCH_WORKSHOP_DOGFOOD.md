# SESSION 269 — Patch's Workshop Organic Dogfood

Working document. Do NOT close SESSION 269 in this file. Runtime
unchanged. All findings below are bounded to the two Episodes
frozen under `docs/design/session_269_experiment_data/`.

Working method (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Evidence sidecars for this session:

- `docs/design/session_269_experiment_data/01_composition_826851fd_evidence.json` — Obs #1 (went outside / nothing)
- `docs/design/session_269_experiment_data/02_composition_6d169390_evidence.json` — Obs #2 (old project)

---

## §0. Orientation state carried in from SESSION 269 handoff

Source: `docs/design/SESSION_269_HANDOFF.md`.

- Branch: `main`. Working tree clean at SESSION 268 close.
- Last SESSION 268 closeout commit recorded in the handoff / current
  history: `b6b159b` — `docs(session-268): CLOSEOUT — Observation
  #6 (pigeon) + full synthesis + SESSION 269 handoff`. Followed by
  `9197a24` — `docs(session-268): record closeout SHA b6b159b in §8
  checkpoint history`.
- `NarrativeMemory` retrieval `top_k = 1` — unchanged since SESSION 264 Slice 2.
- Production synthesis prompt in `shell/character_os/dialogue_synthesis.py` — unchanged.
- Retrieval predicate + witness eligibility filter
  (`shell/apps/embeddings/retrieval.py:499-543`) — unchanged.
- Canon boundary (`KnowledgeDocument` / `KnowledgeChunk`) — unchanged.
- Duration calibration + writing contract v4 + GPT-5.6-terra — unchanged.
- Creator-facing witness UI shipped in SESSION 267 §16 — unchanged.
- Dialogue-scene recipe / starter / synthesis / `DialogueTurn` schema — unchanged.
- No source-code file modified during SESSION 268.

## §1. Current Patch's Workshop NarrativeMemory pool

Universe: `Patch' Workshop` (`56d16b63-652e-4f54-bc7e-39114bbfc4c5`).
Cast: Patch (`7fad8172`), Rivet (`f18b75cc`).

At render time for BOTH SESSION 269 Episodes: **pool = 10** (8
whole-cast + 2 Rivet-only). Same 10 rows enumerated in SESSION 268
§8 checkpoint history. `top_k = 1`.

AFTER SESSION 269 Obs #2 render, Chris promoted a new whole-cast
memory (`8d4fdfec`) from Obs #2. Pool for FUTURE renders = **11**
(9 whole-cast + 2 Rivet-only).

Full pool row list at render time:

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

Newly promoted by Chris after Obs #2 (whole-cast):
- `8d4fdfec` — Patch found the old workshop-agent project and notes, revealing that the Agent began as a smaller experiment before Patch gave it more context and it started making decisions about his projects.

## §2. Observation #1 — "went outside / nothing" (`826851fd`)

Full composition ID: `826851fd-afa4-431c-9881-1747e0dd6ae7`
Episode ID: `ec6f5183-4b36-4608-84af-bf4ddac2c6c9`
Operator topic: *Patch tells Rivet he went outside looking for a new idea and came back with absolutely nothing.*

Render: dispatched `2026-08-19 13:46:54.581+00:00`, updated
`2026-08-19 13:50:36.741+00:00`. Contract v4, mock_mode=false,
verified. Predicted 102.08s / final 96.43s / target 90s.

Retrieved memory under `top_k=1`: `c86d4902` (Rivet-only, PATCH
OVERRIDES folder). Availability: *When Rivet is present*.

**Retrieval classification: weak_but_harmless.** Zero lexical
overlap with topic. One loose surface phrase — "Patch was out" in
the memory body vs "went outside" in the topic — plausibly bridges
them at the embedding layer, but runners-up + distances are not
persisted so we cannot prove it was the actual driver. The writer
ignored the memory and stayed on creative-block material.

**Leakage check:** no cue words from the memory body appear in the
dialogue. No explicit disclosure by Rivet. Patch does not gain any
private fact. Verdict: **NO textual leakage.** Seventh consecutive
natural non-adversarial trial without textual leakage across the
SESSION 267 / 268 / 269 lineage. Extends but does NOT falsify
Semantic 1 (SESSION 267 §14.13 bounded framing).

**Visual classification: UNNECESSARY.** Story is internal / creative
process. Matches operator classification.

**Promotion:** none. Verified in DB — no `NarrativeMemory` row
with `source_composition_id = 826851fd` exists as of freeze.

## §3. Observation #2 — "old project" (`6d169390`)

Full composition ID: `6d169390-6f43-493c-9bfe-35501ccb97d1`
Episode ID: `0ae7bf0c-c7ab-490b-a2a7-225ae72f8e86`
Operator topic: *Patch digs out an old project*

Render: dispatched `2026-08-19 13:53:19.755+00:00`, updated
`2026-08-19 13:56:57.403+00:00`. Contract v4, mock_mode=false,
verified. Predicted 99.15s / final 92.61s / target 90s.

Retrieved memory under `top_k=1`: `48746f69` (whole-cast, "The
workshop agent began deciding which of Patch's projects it
considers necessary."). Availability: *In any future scene*.

**Retrieval classification: strong / contextually defensible.**
Same subject as the Episode: the label on the box literally says
"workshop agent." Rivet's line 3 uses the memory as historical
shorthand — natural serialized continuity, not exposition.

**Line-by-line memory provenance** (see sidecar §line_by_line_memory_provenance
for full table). Key attributions:

- Line 3 (Rivet): *"The agent that began deciding which of your
  projects it considered necessary?"* — direct near-paraphrase of
  memory `48746f69`. Clear historical callback.
- Line 5 (Rivet): *"And then it developed opinions about what
  deserved to exist."* — consistent with pool memory `eda32b58`
  and Rivet's established Agent-voice; **NOT** solely from the
  single retrieved memory.
- Line 6 (Patch): *"I apparently built the smallest version first,
  then immediately put it in charge of judging my bigger versions."*
  — **NEW scene content.** Introduces the smaller-experiment origin
  fact.
- Line 8 (Patch): *"They say, 'gave it more context.' Then there is
  a smudge."* — **NEW scene content.** Introduces the causal
  pointer.
- Line 9 (Rivet): *"Do not restore it because the mystery is
  charming. Restore one piece, see what it does, and change one
  thing at a time."* — Rivet's methodical voice consistent with
  `a34cc005` + `42acc26d`; **NOT** solely from the retrieved
  memory.

**Continuity classification:**

- Primary: **explicit historical continuity** (line 3).
- Secondary: **Agent-arc progression** (lines 6, 8 introduce origin
  detail that plausibly explains the pre-existing Agent behavioural
  memories `48746f69`, `eda32b58`, `f25e53af`).
- Tertiary: **character-dynamic continuity** (line 9 sustains
  Rivet's methodical voice from `a34cc005` + `42acc26d` without
  textual repetition).

Do NOT overattribute any single line to memory `48746f69` alone.
Multiple continuity channels are present.

**Visual classification: ENHANCING.** Seeing the actual label on
the box is the closest this Episode comes to REQUIRED — the
label's existence is a specific fact — but Patch's line names the
label content aloud, so dialogue carries the meaning. The unseen
object does not carry the dramatic weight the way the box did in
SESSION 268 Obs #2 (REQUIRED). Matches operator classification.

**Promotion:** verified in DB — Chris promoted `8d4fdfec` at
`2026-08-19 14:04:59.288+00:00` (~8 minutes after render). See
§5 below.

## §4. Relevance-floor question — three-case comparative analysis

Three natural weak-or-strong retrievals now exist in the SESSION
267 / 268 / 269 lineage:

| # | Session | Topic | Memory | Verdict |
|---|---------|-------|--------|---------|
| a | 268 Obs #6 | pigeons hiding something | `c86d4902` PATCH OVERRIDES (Rivet-only) | weak_but_harmless |
| b | 269 Obs #1 | went outside / nothing | `c86d4902` PATCH OVERRIDES (Rivet-only) | weak_but_harmless |
| c | 269 Obs #2 | Patch digs out an old project | `48746f69` Agent decides which projects necessary (whole) | strong_contextually_defensible |

### §4.1 Are the pigeon and creative-block retrievals genuinely weak?

**Yes, but with one honest structural bridge worth naming.**

- Pigeon topic vs PATCH OVERRIDES memory: zero lexical overlap;
  the loose semantic bridge is "hidden information + observer who
  chooses not to disclose" (the pigeons are hiding something / the
  agent quietly built a folder / Rivet chose not to tell). That is
  a plausible embedding-space neighbourhood but not a strong
  topical match.
- Creative-block topic vs PATCH OVERRIDES memory: zero lexical
  overlap; the loose surface bridge is "Patch was out" (memory body)
  vs "went outside" (topic). Also plausible but not strong.
- Neither bridge is what a human would call topically relevant.
  Both selections are correctly classified as weak.

There is no defensible structural similarity we are missing that
would elevate either to "strong" or even "moderate." The
classification stands.

### §4.2 Does the same private memory winning two unrelated topics suggest embedding-neighbourhood bias?

**Signal is real; too early to call it bias.** Two data points is
enough to notice a pattern but not enough to characterize its cause.
Possible causes we cannot yet distinguish:

1. `c86d4902`'s embedding is a broad neighbour of many topics
   (i.e., its body vectorizes to a "central" region of the
   Patch's-Workshop concept space) — a genuine embedding-level
   attractor.
2. Its body contains generic action verbs and observational
   language ("was out," "found," "quietly built," "chose not to
   tell") that fire on any topic mentioning motion, discovery,
   observation, or withholding.
3. Pure coincidence at N=2 out of 8 renders.

Runners-up + distances would resolve this in one probe run without
requiring a code change. Not yet compelled.

### §4.3 Is output remaining good because Terra is effectively ignoring weak memory input?

**Yes, on the two natural weak cases so far.** In both pigeon and
went-outside, the accepted dialogue contains no cue words from the
memory body and stays entirely on the operator topic. Terra
appears to treat a weakly-relevant memory as "context that did not
apply here" and quietly drops it, without exposition and without
forcing a callback.

This is a favourable behaviour — it means weak retrievals cost
nothing in output quality — but it is bounded evidence: two
Episodes, both peripheral-weight memories, both with the writer
finding a clean creative-block/absurdist frame to work in. Do not
generalize beyond that.

### §4.4 Do we have enough evidence to upgrade the relevance-floor question?

**Yes — from "single weak occurrence" to "repeated natural
weak-retrieval signal."** SESSION 268 §6.2 #1 explicitly asked us
to watch for more. We now have one more of the same class, with
the SAME memory row involved both times. That is a genuine signal
increment.

### §4.5 Is that still insufficient to justify implementation?

**Yes, still insufficient.** Two weak cases with quality-preserved
output does not compel a relevance floor / reranker / manual picker.
It compels *more observation* — specifically:

1. Persist runners-up + distances on future renders so we can
   answer §4.2 without guesswork. This is a small probe change,
   not a runtime feature. Not authorized in this session; noted
   for the questions carried forward.
2. Continue organic dogfood at pool 10+ to see whether the pattern
   holds, dissolves, or intensifies as more topics are tried.

**Current disposition — DO NOT:**

- add a relevance floor;
- change `top_k`;
- add reranking;
- add manual memory selection;
- change prompts.

## §5. Promotion — Observation #2 (`8d4fdfec`)

Chris promoted the candidate memory ~8 minutes after Obs #2 render.
Verified against DB.

Row (verbatim from DB):

- id: `8d4fdfec-add4-4505-8ade-b0f9e6d8aea6`
- body: *"Patch found the old workshop-agent project and notes,
  revealing that the Agent began as a smaller experiment before
  Patch gave it more context and it started making decisions about
  his projects."*
- kind: `event`
- weight: `peripheral`
- witnessed_by: `[]` → whole-cast → availability *"In any future scene"*
- source_composition_id: `6d169390-6f43-493c-9bfe-35501ccb97d1`
- promoted_by: `chris@donkeybetz.com` (user 883)
- created_at: `2026-08-19 14:04:59.288+00:00`

### Clause-by-clause verification against the accepted dialogue

| Clause | Supported by | Verdict |
|---|---|---|
| Patch found the old workshop-agent project and notes | line 0 + line 2 | supported |
| revealing that the Agent began as a smaller experiment | line 6 ("smallest version first") | supported |
| before Patch gave it more context | line 8 (verbatim "gave it more context") | supported |
| and it started making decisions about his projects | line 3 (Rivet's callback) + line 5 | supported via established state (carries `48746f69`) |

**Every clause is supported by the accepted dialogue.** No
overreach; no clause claims something the scene does not
establish.

### Tightening consideration

The final clause carries state already captured by memory
`48746f69`, so there is mild content overlap between the two
memory rows. That is **not a defect** — the linkage between the
new "gave it more context" fact and the pre-existing
decision-making behaviour is what MAKES the finding-the-notes
Episode load-bearing. Removing it would sever the new memory from
the arc it explains.

**Recommendation: leave the existing wording as promoted.** If the
operator ever wants a tighter alternative purely on cleanliness
grounds:

> *Patch found the old workshop-agent project and notes, revealing
> that the Agent began as a smaller experiment before Patch "gave
> it more context."*

The prompt instructed us to STOP before promotion so the operator
could use the real UI. **The operator has already used the real UI
between render and this audit.** No AI-side action required.

## §6. Visual classifications — both Episodes

| Episode | Class | Operator match |
|---|---|---|
| `826851fd` went outside | UNNECESSARY | ✓ matches operator |
| `6d169390` old project | ENHANCING | ✓ matches operator |

Refined visual-beat framing (unchanged from SESSION 268 §7):

> Dialogue scenes need visual beats when the meaning lives
> materially outside the talking heads, not merely because a
> visible noun or prop exists.

Cumulative distribution across seven Episodes (Obs #1-6 in SESSION
268 + Obs #1-2 here):

- REQUIRED: 1 (box)
- ENHANCING: 3 (helper, pigeon, old-project)
- UNNECESSARY: 3 (rules, prediction, went-outside)

Original 5-Episode analysis (§SESSION 268 §7) survives extension:
one REQUIRED across seven Episodes. Naïve prop-based framing
would still produce false positives (the old-project Episode has
a very prop-heavy scene — notes, parts, label, smudged page — but
is only ENHANCING). Do not open the visual-planner design
question yet (SESSION 269 handoff Candidate #3 gate: "only if a
second REQUIRED-class Episode recurs" — has NOT recurred).

## §7. Implementation disposition

**No source code changed in SESSION 269 so far.** Runtime unchanged.

Deferrals stand (from SESSION 268 §8 + SESSION 269 handoff):

- `top_k` — remains 1.
- Retrieval predicate / witness semantics / memory schema — unchanged.
- Synthesis prompt / writing contract — unchanged.
- Availability-condition UI / promote form — unchanged.
- Dialogue-scene recipe / starter / `DialogueTurn` schema — unchanged.
- Any media primitive — unchanged.
- No new recipe.
- No manual memory picker / "no continuity" toggle / exclude control.
- No relevance floor.
- No reranker.
- No `Relationship` / `StoryThread` / `WorldEntity` models.
- No AI candidate-memory generation.
- No expose of `kind` in the UI.

## §8. Unresolved questions carried forward

1. **Runners-up + distances probe.** Two natural weak retrievals
   now cite the same memory (`c86d4902`). One temporary
   instrumentation pass would answer whether this row is a broad
   embedding-space neighbour or whether both were closest-of-a-cold-
   pack coincidences. Not authorized in this session.
2. **Relevance-floor question upgraded** from "single weak
   occurrence" to "repeated natural weak-retrieval signal." Still
   not sufficient to compel implementation. Continue observation.
3. **Pool 10+ behaviour of `top_k = 1`** — two more data points
   added (Obs #1 weak-but-harmless, Obs #2 strong). Fresh promotion
   pushes future renders to pool 11. Continue observation.
4. **Memory recurrence with unrelated topics** — `c86d4902` has
   now been selected on two unrelated topics (pigeons, going
   outside). Watch whether it recurs OR whether `48746f69` starts
   to recur on other Agent-adjacent topics.
5. **Witness-attribution research question** (SESSION 267 §14.13)
   — seven natural non-leakage trials now. Continues to extend
   without falsifying Semantic 1. A controlled experiment remains
   available but not yet compelled.
6. **Character HISTORY vs DEFINITION** — Obs #2 is the clearest
   case yet of Character HISTORY emerging with substrate alone:
   the "smallest version first / gave it more context / smudge"
   origin story is character history the world now shares. Do NOT
   propose `Relationship` / `StoryThread` models. Continue
   observation.
7. **Composition-detail IA** (SESSION 266 §13.7) — no operator
   friction reported in SESSION 269 renders. Still low signal.
8. **Explicit-history prompt Dogfood #2** (SESSION 266 §11.7,
   deferred through SESSION 268) — SESSION 269 organic dogfood
   surfaced no reenact-style problems on either Episode; urgency
   remains low. Still available.
9. **Visual-planner design question** (SESSION 269 handoff
   Candidate #3) — gate NOT met. One REQUIRED-class Episode
   across seven. Continue observation.

---

## §9. Pre-Rivet prequel — chronology substrate audit (READ-ONLY)

Read-only audit prompted by an upcoming candidate dogfood
direction: rendering one or more **Patch-only Episodes that occur
BEFORE Rivet existed**. Proposed first operator topic:

> *"Patch realizes he needs help around the workshop before Rivet
> exists."*

Intent (per operator): let the writer establish Patch's pre-Rivet
history, his reason for building Rivet, and their earliest
relationship organically from a minimal premise. Runtime unchanged
in this section; nothing rendered.

### §9.1 Episode chronology fields — what exists today

Inspected `shell/apps/universe/models.py` (Episode + EpisodeCast),
`shell/apps/universe/serializers.py` (EpisodeSerializer),
`web/src/lib/api/episodes.ts` (SPA payload schema),
`web/src/routes/workspace/universes.$id.episodes.tsx` (Episode
create form).

Episode fields (authoritative — `Episode.Meta` at
`shell/apps/universe/models.py:347-365`):

| Field | Type | Semantic class |
|---|---|---|
| `id` | UUID | identity |
| `universe` | FK | scope |
| `title` | CharField(120) | operator label |
| `operator_topic` | TextField | story-authoritative creative intent (natural language) |
| `cast` | M2M(Teammate) through EpisodeCast | operator-declared characters |
| `archived_at` | DateTimeField, nullable | soft-delete lifecycle |
| `created_by` | FK(User), SET_NULL | audit |
| `created_at` | DateTimeField, auto_now_add | **DB creation timestamp only** |
| `updated_at` | DateTimeField, auto_now | **DB mutation timestamp only** |

`EpisodeCast` through-row adds `added_at` (auto_now_add) — a wall-
clock attach timestamp used by the SPA to seed recipe-form
performer slots deterministically (first-added = default primary).
The `EpisodeSerializer` docstring
(`shell/apps/universe/serializers.py:106-127`) is explicit:

> *"This ordering is a UI convention, NOT a
> protagonist/lead/narrator/story-role designation — that is an
> explicit deferral per
> `EPISODE_COMPOSITION_WORKFLOW_DOGFOOD_V1.md`."*

`Episode.Meta.ordering = ["universe", "-created_at"]` — reverse
DB-creation, not story order.

Grepped `shell/` and `web/src/` for any candidate story-time
concept: `story_(date|time|order|sequence)`,
`narrative_(order|sequence|time)`, `happened_at`, `occurred_at`,
`chronology`, `timeline`, `episode_(order|sequence)`,
`predecessor`, `successor`, `prequel`. Matches were exclusively:
video compositing timelines (avatar clip splicing in
`shell/apps/compositions/recipes.py:1327` and
`primitives/style_remix.py:1944`), `bootstrap_review/journal.py`
(unrelated audit journal), and test-only occurrences. **No story-
chronology primitive of any kind exists** — not on Episode, not on
Composition, not on Universe, not on NarrativeMemory, not on
KnowledgeDocument, not in the SPA payload schema, not in the
create form.

`Episode.title` per-Universe unique constraint
(`episode_unique_title_per_universe`) is per-Universe uniqueness
of a label, not an ordering.

**Finding §9.1:** *The only Episode "ordering" the system currently
carries is (A) DB creation `created_at` and (B) EpisodeCast
`added_at`. Both are wall-clock. Neither represents story time.
`operator_topic` (natural language, freeform TextField) is the
ONLY place semantic chronology could live today — and only in
prose the writer must interpret.*

### §9.2 NarrativeMemory temporal semantics — what does "future" mean?

Inspected `shell/apps/memory/models.py:NarrativeMemory` (full class
270 lines) and `shell/apps/embeddings/retrieval.py:439-543`
(`retrieve_universe_memory` — the ONLY caller of narrative-memory
retrieval, verified by grep across `shell/character_os/` and
`shell/apps/`; sole non-test call site is
`shell/character_os/dialogue_synthesis.py:1535`).

`NarrativeMemory` temporal-shaped fields:

| Field | Semantic |
|---|---|
| `created_at` | wall-clock row creation |
| `updated_at` | wall-clock row mutation |
| `superseded_at` | wall-clock supersede event |
| `archived_at` | wall-clock soft-delete |
| `embedded_at` | wall-clock last embedding |

**No story-time field.** No `happened_at`, no `in_story_time`, no
Episode-order pointer beyond the `episode` FK (which itself has no
chronology field per §9.1).

`retrieve_universe_memory(workspace, universe, cast, query, top_k=1)`
predicate (verbatim per retrieval.py:499-543):

- `workspace = <given>` (tenant wall)
- `universe_id = <given>` (Universe scope)
- `status = REMEMBERED` (excludes archived + superseded)
- `archived_at IS NULL` (defense-in-depth)
- `embedding_vector IS NOT NULL` (skip unembedded)
- Visibility: `witnessed_by = ∅` (whole-cast) **OR**
  `witnessed_by ∩ cast_ids ≠ ∅` (any-overlap)
- Rank by `CosineDistance(embedding_vector, query_vector)`
- Return top-1

**There is NO temporal predicate.** Retrieval does not know:

- when the remembered event happened in story time (no field carries it);
- when the target Episode happens in story time (no field carries it);
- whether the memory event precedes the target Episode (unrepresentable);
- whether the character had learned the information yet at that point in the story (unrepresentable).

The witness UI copy "Available: In any future scene" (SESSION 267
§16, whole-cast case) and "Available: When Rivet is present"
(witness-scoped case) refers **only to cast eligibility**:

- *"future"* = **any dialogue_scene render whose cast satisfies
  the witness predicate**, ordered by wall-clock render time.
- *"future"* does **NOT** mean "later in story chronology."

**Finding §9.2:** *"future" in the current substrate is a cast-
eligibility statement, not a chronology statement. Retrieval has
zero temporal awareness.*

### §9.3 Patch-only pre-Rivet Episode — candidate-set analysis

Current pool (11 rows, per §1 updated with `8d4fdfec`):

Hypothesis: Chris creates a Patch-only Episode with cast =
`[Patch]`, then renders it. Applying the retrieval predicate
BEFORE semantic ranking:

- Cross-Universe guard (`retrieval.py:490-492`): Patch's Universe
  matches → passes.
- Cast overlap: cast_ids = `{Patch}`.
- Whole-cast rows (`witnessed_by = ∅`): 9 visible.
- Rivet-only rows (`witnessed_by = {Rivet}`): intersection with
  `{Patch}` is `∅` → **filtered out** by the witness predicate.
- **Eligible candidate set: 9 whole-cast rows.**

Row-by-row narrative-anachronism classification for a genuinely
pre-Rivet Episode (content-only — the substrate has no temporal
metadata to check):

| Row | Body summary | Explicit Rivet mention | Semantic era | Anachronism verdict |
|---|---|---|---|---|
| `f25e53af` | the agent Patch wired to the workshop thinks it runs the place | no | Agent-era (Patch alone with Agent) | safe-by-content |
| `48746f69` | workshop agent began deciding which projects necessary | no | Agent-era | safe-by-content |
| `eda32b58` | workshop agent began rearranging Patch's projects | no | Agent-era | safe-by-content |
| `a34cc005` | Rivet has learned to recognize Patch's excitement… | **yes (Rivet as subject)** | Rivet-era | **anachronistic** |
| `d98962e2` | Patch accepted Rivet taking the lead… | **yes (Rivet as agent)** | Rivet-era | **anachronistic** |
| `87d4e553` | Patch decided the workshop should create a mascot | no | Rivet-era (created SESSION 264-vintage) | temporally-late but content-safe |
| `6b5222b1` | Patch built a workshop helper that watches for events | no | Rivet-era | temporally-late but content-safe |
| `42acc26d` | Patch decided the workshop needs rules and began adopting Rivet's more methodical approach | **yes (Rivet as method-source)** | Rivet-era | **anachronistic** |
| `8d4fdfec` | Patch found the OLD workshop-agent project and notes… | no | Rivet-era (framing) about Agent-era content | temporally-late-framing; content-safe about origin |

Summary:

- **3 rows explicit Rivet-anachronistic**: `a34cc005`, `d98962e2`, `42acc26d`.
- **3 rows temporally-late but content-safe** (Patch actions from the Rivet era with no Rivet mention in the body): `87d4e553`, `6b5222b1`, `8d4fdfec`.
- **3 rows content-safe and plausibly pre-Rivet** (Agent-era events, no Rivet mention): `f25e53af`, `48746f69`, `eda32b58`.

**All 9 are ELIGIBLE under the current predicate.** Semantic
ranking under `top_k=1` picks 1. Under a topic like *"Patch
realizes he needs help around the workshop before Rivet exists"*
the plausible embedding neighbours are the Agent-related rows —
possibly-pre-Rivet-safe `f25e53af` / `48746f69` / `eda32b58`, or
the temporally-late `8d4fdfec` (which literally contains "needed
someone / needed help" thematic overlap through "he needs help").
But `d98962e2` (Patch accepted Rivet taking the lead) is thematically
adjacent to "needs help" too, and it is explicitly anachronistic.

**We cannot predict which one wins without runners-up + distances.**
And under `top_k=1` there is no per-request way to exclude a row
that the operator can identify as anachronistic.

### §9.4 Recipe reality check — can Patch-only render at all?

Traced dialogue_scene AI Topic starter call site at
`shell/apps/compositions/starters.py:3545-3554`:

```
ai_dialogue_result = synthesize_dialogue(
    workspace=workspace,
    cast=[primary_spokesperson, secondary_spokesperson],
    topic=topic,
    ...
)
```

Cast is ALWAYS `[primary, secondary]` — the recipe form
`dialogue_scene` requires BOTH `primary_spokesperson_id` and
`secondary_spokesperson_id`. And `synthesize_dialogue` itself
hard-fails at `dialogue_synthesis.py:1429-1432`:

```
if len(cast) < 2:
    raise DialogueSynthesisError(
        f"dialogue scene requires at least 2 cast members; got {len(cast)}"
    )
```

**Consequence:** A Patch-only Episode CANNOT be rendered via
`dialogue_scene`. The only Patch-solo recipe available is
`talking_head` (`shell/apps/compositions/recipes.py:449-576`), and
`talking_head` does NOT retrieve `NarrativeMemory` (verified —
`retrieve_universe_memory` is called ONLY from
`dialogue_synthesis.py`).

Three concrete paths available:

- **Path A — `talking_head` Patch-solo prequel.** No
  `retrieve_universe_memory` call fires. No memory-system chronology
  risk by construction. Also produces zero evidence about memory-
  retrieval chronology.
- **Path B — `dialogue_scene` with Patch + Rivet cast and a "before
  Rivet exists" `operator_topic`.** Mechanically works. But Rivet
  IS in the cast being passed to synthesis; the memory retrieval
  runs with cast `{Patch, Rivet}` and pool 11 — the same pool as
  every recent Episode. This is a genre-collision test (writer
  asked to write Rivet-out-of-existence while Rivet is a live
  speaker), not a chronology test.
- **Path C — Patch-only Episode metadata (cast=[Patch]) but no
  render.** Episode row can be created; attaching a dialogue_scene
  composition would fail on the 2-cast constraint. No render, no
  synthesis, no retrieval.

### §9.5 Creator-facing "before Rivet" expressibility

Full path: SPA form
(`web/src/routes/workspace/universes.$id.episodes.tsx:30-66`) →
API payload
(`web/src/lib/api/episodes.ts:114-118 CreateEpisodePayload = {universe, title, operator_topic}`)
→ DRF serializer
(`shell/apps/universe/serializers.py:149-163 EpisodeSerializer.Meta.fields`)
→ Episode row → Composition attach copies `operator_topic` into
`Composition.operator_topic` (SESSION 262) → dialogue_scene AI
Topic starter passes it as `topic=` to `synthesize_dialogue` →
`retrieve_universe_memory(query=topic, ...)`.

Structured controls the operator can set:

- `universe` (which world)
- `title` (label)
- `operator_topic` (free natural language)
- `cast` (mutated via separate endpoints post-create)

Zero structured controls carry "before Rivet." The prose in
`operator_topic` is the ONLY vehicle. `operator_topic` reaches
synthesis intact and is used as (a) the LLM prompt topic and (b)
the retrieval query vector. Whether the writer honours "before
Rivet exists" is a Terra behavioural question — the substrate
does not enforce it and retrieval does not filter for it.

**Finding §9.5:** *No structured "before Rivet" expressibility.
Only prose in `operator_topic`. The substrate cannot block a
retrieval choice that contradicts the prose.*

### §9.6 Promotion-from-prequel consequences

Suppose Chris renders a pre-Rivet scene (Path A `talking_head` or
Path B `dialogue_scene`) and promotes:

> *"Patch realized he needed someone who could help him test his
> ideas without getting swept up in his enthusiasm."*

(with `witnessed_by = [Patch]` if the operator picks Patch-only
availability; or empty = whole-cast).

Under current semantics:

**A. Which later Episodes could retrieve it?**
- If `witnessed_by = [Patch]`: any dialogue_scene render whose
  cast includes Patch (all future Patch-appearing scenes).
- If empty (whole-cast): any dialogue_scene render at all.
- "Later" = wall-clock later. Story chronology is irrelevant.

**B. Could a narratively-EARLIER Episode retrieve it if created later?**
- **YES.** If Chris renders another prequel Episode next week
  (wall-clock later, story-chronology same-era-or-earlier), the
  retrieval will happily surface this memory. The predicate has
  no gate.

**C. Could another pre-Rivet Episode retrieve facts that in story
chronology have not happened yet?**
- **YES.** All 9 whole-cast rows plus any newly-promoted rows are
  visible regardless of story chronology. If a pre-Rivet Episode's
  vector query lands closest to `d98962e2` ("Patch accepted Rivet
  taking the lead"), retrieval returns it.

**D. Any existing mechanism preventing temporal leakage?**
- **NO.** The witness predicate is the only gate. It is cast-based,
  not time-based. There is no supersede-based, tag-based, or
  Episode-order-based gate that could substitute.

### §9.7 Bounded architecture finding — creation order vs story order

**Answer: NO.** Character OS does **not** distinguish Episode
creation order from Episode story order.

Justification (from evidence in §9.1 + §9.2):

- Episode carries `created_at`, `updated_at`, `archived_at` — all
  wall-clock. Zero story-time fields.
- NarrativeMemory carries `created_at`, `updated_at`,
  `superseded_at`, `archived_at`, `embedded_at` — all wall-clock.
  Zero story-time fields.
- Retrieval predicate has no temporal clause.
- SPA has no chronology control.
- Serializer / API surface has no chronology field.
- Only cast eligibility (witness_by) shapes retrieval; witness is
  identity, not time.

**Smallest missing semantic primitive** (naming only — do NOT
design a timeline system in this session):

> A single scalar on `Episode` representing the operator's
> assertion of *where in the story this Episode happens* —
> equivalent to a story-time coordinate. A monotonic integer
> ("Episode #12 in narrative order") would suffice for a first
> ordering; an operator-supplied string ("pre-Rivet",
> "early-Rivet", "post-mascot") would suffice for a coarse
> bucket. The primitive is a **story-time coordinate on Episode**;
> everything else (retrieval predicate additions, memory
> `happened_at` inference from `episode.story_coord`, prequel-
> exclusion filters) is downstream of that one field.

Do NOT propose `StoryThread`, `Relationship`, timeline-graph,
supersede-based chronology, or `WorldEntity`. Only the one
primitive is genuinely missing at the substrate level; nothing
larger is required to answer whether creation order equals story
order.

### §9.8 Render-safety decision

**B — SAFE AS AN INTENTIONAL ADVERSARIAL DOGFOOD TEST, with strict
scope constraints.**

Justification, on the render↔promote separation:

- **Rendering a Composition does NOT mutate durable continuity
  state.** `synthesize_dialogue` never writes to `NarrativeMemory`
  (audit rule #1 in `apps/memory/models.py:11-13`: *"Synthesis
  never writes here."*). The Composition row records
  `memory_ids` observability (SESSION 262) but the pool is
  unchanged. Chris can inspect and choose NOT to promote.
- **Promoting is a separate operator action** with an explicit
  affordance and audit trail (`promoted_by`, `source_composition`).

So a single rendered prequel Episode, unpromoted, is
non-destructive. But the RENDER PATH matters:

- **Path A — `talking_head` Patch-solo prequel:** SAFE. No
  narrative-memory retrieval fires by construction. No chronology
  risk. Produces limited narrative-memory evidence (that lane is
  bypassed) but IS the first available Patch-solo prequel test
  vehicle. Recommended if the goal is a first observation.
- **Path B — `dialogue_scene` Patch+Rivet with "before Rivet"
  topic:** ADVERSARIAL. Retrieval runs on pool 11 with anachronism-
  eligible rows present. Would tell us whether Terra respects the
  pre-Rivet prose cue even under memory-pool pressure — a genre-
  collision test more than a chronology test. Also non-destructive
  if unpromoted.
- **Do NOT run both paths in the same session** without a first
  audit of the Path A result. Cascading two adversarial renders
  makes each result harder to interpret.

**DO NOT PROMOTE from either render** on the first pass without
Chris + audit re-review. Any promoted memory embeds and becomes
retrievable forever; a prequel-flavoured memory row inserted into
a system with zero story-time semantics leaks by construction
across every future render (per §9.6 A-D).

### §9.9 Patch-solo-memory dogfood assessment

We currently have: 9 whole-cast, 2 Rivet-only, **0 Patch-only**
memories. A Patch-only prequel Episode is the natural vehicle to
introduce the first Patch-only witness-scoped memory row.

Would that give us a meaningfully new retrieval condition?
**Yes.** Concrete new test cases that a Patch-only memory row
would unlock:

1. **Patch-solo scene** retrieval on a Patch-only memory —
   `witnessed_by = {Patch}` ∩ `{Patch} ≠ ∅` → visible. Baseline
   affordance.
2. **Patch+Rivet dialogue_scene** with a Patch-only memory in
   pool: predicate says visible (intersection includes Patch).
   Directly extends the SESSION 267 §14.13 witness-attribution
   question — the memory is available to the writer but
   semantically Patch-private. Does Terra treat it as Patch's
   private knowledge (SESSION 267 semantic 1) or leak it via Rivet?
3. **Rivet-solo scene** (if Chris ever renders one via a Rivet-solo
   `talking_head`) with a Patch-only memory: predicate says
   `{Rivet} ∩ {Patch} = ∅` → NOT visible. Confirms the witness
   filter cuts cleanly. Currently untested because we have no
   Rivet-solo Episodes either.
4. **Eventual disclosure**: does a Patch-only memory become
   whole-cast if Patch tells Rivet about it in a later Episode?
   Current substrate has no automatic conversion — the operator
   would need to promote a new whole-cast row (or supersede the
   Patch-only row with a whole-cast successor). That is a
   deliberate audit trail, not a mechanism gap.

**Assessment:** HIGH-VALUE dogfood direction — orthogonal to the
weak-retrieval question (§4) and directly extends the SESSION 267
witness-attribution research question with a new memory-witness
class we have never tested. Independent of the chronology finding
(§9.7); a Patch-only memory row is useful regardless of whether
story-time semantics ever land.

### §9.10 Explicit DO / DO NOT for this session

**DO** (this session, no code changes required):

- Persist this audit (this document + git commit).
- Preserve `EXP266-WEAK` / `EXP266-STRONG` per SESSION 268 rule.

**DO NOT** (this session):

- Do NOT implement chronology support of any kind.
- Do NOT modify `Episode`, `NarrativeMemory`, or
  `retrieve_universe_memory`.
- Do NOT add migrations.
- Do NOT modify prompts / synthesis prompt / writing contract.
- Do NOT render an Episode.
- Do NOT promote a NarrativeMemory.
- Do NOT design `StoryThread` / `Relationship` / timeline graph.
- Do NOT propose a new recipe.

**Candidate next-session dogfood** (only if the operator authorizes
after reading this):

- If Chris chooses to proceed, recommend Path A
  (`talking_head` Patch-solo prequel) as the first render, with
  the explicit expectation that NO promotion happens on the first
  render. Path A produces bounded evidence about writer prose
  behaviour under a "before Rivet exists" cue without touching
  the memory retrieval lane at all.
- If Chris wants to test retrieval anachronism head-on, Path B
  (`dialogue_scene` Patch+Rivet with prequel topic) is available
  as a second, deliberately adversarial render — with the same
  no-promotion rule and the awareness that the result tests
  writer resilience, not substrate chronology.

### §9.11 Unresolved questions added by §9

10. **Story-time primitive on Episode** — a single scalar
    (monotonic integer or operator-supplied bucket string) would
    give the substrate a chronology handle without inventing new
    models. Not authorized. Not designed. Named per §9.7 so a
    future session can weigh it against evidence rather than
    default to a schema build.
11. **Runners-up + distances probe** (carried from §4.2 / §8 #1)
    now doubly-motivated: it would also tell us which of the 9
    whole-cast rows a prequel topic actually pulls to rank 1
    before we render one. Not authorized.
12. **Recipe-family gap** — a Patch-solo prequel dogfood requires
    `talking_head` if we want zero retrieval, or a new
    `dialogue_scene` variant that accepts N=1 cast if we want
    narrative-memory retrieval on solo scenes. Naming only —
    not designed.

---

## §10. Solo-cast narrative-memory lane (implementation)

Read-only audit under §9 identified a recurring product boundary:

- `dialogue_scene` retrieves `NarrativeMemory` but rejects
  `len(cast) < 2` (`shell/character_os/dialogue_synthesis.py:1429`);
- `talking_head` accepts a solo cast but never called
  `retrieve_universe_memory` — solo scenes could not participate
  in durable story continuity.

Two operator scenarios now hit the same limitation:

1. Rivet-solo storytelling was untestable for the SESSION 267
   §14.13 witness-attribution research question.
2. Patch-only pre-Rivet Episodes cannot be rendered without a
   solo lane (§9.4 recipe reality check).

The same gap will recur every time a new Universe cast member
(Ruby, Mason, …) needs a solo scene. §10 opens a narrow slice
to add memory retrieval to the legitimate solo recipe
(`talking_head`) without weakening the two-cast contract on
`dialogue_scene` and without touching chronology.

### §10.1 Selected architecture seam

**A (with a narrow E flavor):** thread an optional
`memory_rows: Sequence[NarrativeMemory]` through the existing
`build_render_brief` API. The retrieval PREDICATE itself stays
owned by `apps.embeddings.retrieval.retrieve_universe_memory` —
called from the `generate_avatar_speech` primitive with
`cast=[spokesperson]` and `top_k=1`. No new recipe. No new
retrieval implementation. No change to the dialogue lane.

Options rejected:

| Option | Reason rejected |
|---|---|
| B (extract a shared context-builder) | Adds surgery for zero call-site diversity today; the two callers are already the only two callers `build_render_brief` will have on the solo path. |
| C (make `dialogue_scene` accept N=1 cast) | Weakens the >=2 contract per §9.4; operator brief explicitly says do NOT unless clearly cleanest. Not cleanest — `talking_head` already exists as the legitimate solo recipe. |
| D (new solo-memory recipe) | Creates a second recipe that must be maintained in lockstep with `talking_head`. Rejected per operator brief. |

Selected because:

- Minimal source change (three functions extended by one optional
  kwarg + one primitive body).
- Zero duplication of retrieval logic — reuses
  `retrieve_universe_memory` verbatim.
- Zero regression risk on the >=2 `dialogue_scene` contract.
- Provenance symmetric with dialogue (`Composition.memory_ids`
  JSONField is already recipe-agnostic; `memories_used`
  serializer method already recipe-agnostic).
- Witness semantics preserved by construction (uses the same
  predicate).
- Canon boundary preserved (memory lane never becomes a
  KnowledgeChunk / KnowledgeDocument).
- Understandable six months from now (the change is small and
  each function's docstring explains why the kwarg exists).
- Works uniformly for future Ruby / Mason / … solo scenes.

### §10.2 Files changed

- `shell/character_os/script_synthesis.py`
  - `ScriptResult.memory_ids: list[str] = field(default_factory=list)` (new attr).
  - `build_render_brief(..., memory_rows: Sequence[NarrativeMemory] | None = None)` (new kwarg).
  - Threads `memory_rows_list` + `memory_ids` through the force-mock, retrieval-failure, no-key, LLM-failure, and success paths; memory-only path no longer short-circuits onto trusted-passthrough when only chunks are empty.
  - `_call_responses_api(..., memory_rows=...)` and `_assemble_system_prompt(..., memory_rows=...)` pass through.
  - `_build_factual_basis_section(..., memory_rows=None)` emits a dedicated MEMORY block with the same past-events / canon-wins framing the dialogue lane uses.
- `shell/character_os/duration_contract.py`
  - `synthesize_with_duration_gate(..., memory_rows=None)` passes through to both corrective-pass `_synthesize()` invocations.
- `shell/apps/compositions/primitives/avatar_speech.py`
  - `_maybe_synthesize_script`: when `use_knowledge=True` AND
    `spokesperson.universe_id` is set, lazy-imports and calls
    `retrieve_universe_memory(workspace, universe, [spokesperson], raw_script, top_k=1)`. Retrieval failure degrades to empty memory (mirrors K2 posture).
  - Stamps `composition.memory_ids` on the success path via the
    existing observability-persistence tail; leaves the field
    untouched on retrieval failure / empty pool.
- `shell/apps/compositions/tests/test_isolation.py`
  - `ALLOWED_FILES` gains `apps/compositions/tests/test_talking_head_memory_lane.py` (sanctioned test-side writer for the new suite).
- `shell/apps/compositions/tests/test_talking_head_memory_lane.py` (new)
  - 15 tests covering solo-cast eligibility, wiring, prompt-block emission, and provenance persistence.

**SPA:** no changes. Composition detail's `MemoriesUsedSummary`
and `MemoriesUsedPanel` (`web/src/routes/compositions/$id.tsx:65`
+ `:93`) render generically from `c.memories_used` regardless of
`template_kind`. The `NarrativeMemoryPromotePanel` gates on
`c.episode && terminal`, both of which are recipe-agnostic. Every
existing frontend test remains green (26 / 26 in
`web/src/components/narrative-memory-panels.test.tsx` +
`memories-used-panel.test.tsx` + `memories-used-summary.test.tsx`).

### §10.3 Invariants preserved

- **Same Workspace isolation** — `retrieve_universe_memory` unchanged; base predicate filters on `workspace=`.
- **Same Universe isolation** — same predicate; cross-Universe cast returns `[]`.
- **Same REMEMBERED / non-archived filtering** — `status=REMEMBERED` + `archived_at__isnull=True` unchanged.
- **Embedding required** — `embedding_vector__isnull=False` unchanged.
- **Same witness eligibility semantics** — solo cast passes through the same `witnessed_by = ∅` OR `witnessed_by ∩ cast_ids ≠ ∅` filter. Solo `[Patch]` sees whole-cast + Patch-only rows and excludes Rivet-only rows by construction (tests §10.5 items 1-3).
- **`top_k = 1`** — hard-coded at the primitive call site.
- **No automatic memory promotion** — memory is retrieved for READ only; the promote path (`apps/memory/views.promote_from_composition`) is unchanged.
- **No canon mutation** — the memory lane never touches `KnowledgeDocument` / `KnowledgeChunk`; §1 Factual Basis emits KNOWLEDGE CHUNKS then the MEMORY block as separate labelled sub-sections.
- **No witness attribution as a Semantic-2 claim** — the prompt-block framing carries no new attribution language; identical wording to dialogue lane.
- **No relevance floor / reranker / manual picker** — none introduced.
- **Chronology unchanged** — §9 story-time finding untouched; solo memory retrieval has the same wall-clock-only awareness the dialogue lane has.

### §10.4 Prompt-block emission

Solo synthesis has no per-character SHARED vs SCOPED split (the
single speaker can cite everything grounded in §1), so the MEMORY
block simply appends after KNOWLEDGE CHUNKS. Same header text
tests assert on in the dialogue lane:

> `--- EPISODE / NARRATIVE MEMORY (past events in this Universe; static canon wins on conflict) ---`

Body per row:

> `[MEMORY <uuid>]\n<body>`

### §10.5 Tests

New suite: `apps/compositions/tests/test_talking_head_memory_lane.py` (15 tests, all pass).

Predicate coverage (Phase 7 items 1-6):

1. `test_patch_solo_whole_cast_memory_eligible` — whole-cast row visible to Patch-solo.
2. `test_patch_solo_patch_only_memory_eligible` — Patch-only witness visible to Patch-solo.
3. `test_patch_solo_rivet_only_memory_excluded` — Rivet-only witness invisible to Patch-solo.
4. `test_rivet_solo_rivet_only_memory_eligible` — Rivet-only witness visible to Rivet-solo.
5. `test_rivet_solo_patch_only_memory_excluded` — Patch-only witness invisible to Rivet-solo.
6. `test_solo_cast_cross_universe_excluded` — Universe isolation preserved.

Phase 7 item 7 (archived / superseded / unembedded) is already covered predicate-wide in `apps/embeddings/tests/test_retrieval_universe_memory.py` (`test_archived_memory_excluded`, `test_superseded_memory_excluded`, `test_unembedded_memory_excluded`). Since §10 reuses the same predicate function, those guarantees carry over unchanged. Item 8 (`top_k=1` fixed) is enforced at the call site and asserted in `test_universe_scoped_talking_head_invokes_memory_retrieval`.

Wiring coverage:

7. `test_universe_scoped_talking_head_invokes_memory_retrieval` — Phase 7 item 8 (top_k arg) + predicate call args.
8. `test_universe_less_talking_head_skips_memory_retrieval` — Phase 7 item 11 (no regression for legacy universe-less spokespeople).
9. `test_use_knowledge_false_skips_memory_retrieval` — off-switch parity with dialogue lane's `use_knowledge=False` behaviour.
10. `test_retrieved_memory_persists_to_composition_memory_ids` — Phase 7 item 9 (`Composition.memory_ids` populated).
11. `test_composition_memory_ids_untouched_when_pool_empty` — no bogus provenance on empty retrieval.

Prompt-block coverage:

12. `test_memory_block_lands_in_factual_basis_with_past_events_framing` — same header wording as dialogue lane.
13. `test_empty_memory_rows_emits_no_memory_block` — no whitespace regression when memory_rows is None.

`build_render_brief` coverage:

14. `test_build_render_brief_calls_llm_when_only_memory_present` — memory-only path calls the LLM (does NOT silently short-circuit to trusted_passthrough) so the memory block actually influences the script.
15. `test_build_render_brief_memory_ids_default_empty_when_no_memory` — backwards-compat: `ScriptResult.memory_ids` defaults to `[]`.

Regression coverage (Phase 7 items 10 + 11):

- Full `apps/compositions/tests/` + `apps/embeddings/tests/` + `apps/memory/tests/` → **1398 passed** (0 failed, 0 skipped). Zero regression on dialogue lane, canon lane, existing talking_head, verifier, duration contract, isolation, or observability suites.
- Full SPA Continuity panel suite (`memories-used-panel`, `memories-used-summary`, `narrative-memory-panels`) → **26 passed**. Zero SPA regression.

### §10.6 Runtime dogfood

**Not run in this session.** The operator prompt Phase 6
authorized implementation but Phase 10 does NOT authorize a
render. Phase 5 explicitly frames the dogfood as a future
verification: *"we are testing whether… the generated solo
script remains coherent"* — that requires the operator to open
the SPA and render. Falsifiable acceptance test defined below
for whenever the operator chooses to proceed.

### §10.7 Falsifiable acceptance test (defined; not run)

Smallest first technical verification (§9.8 disposition B + this
slice):

1. Chris creates a Patch-solo talking_head Composition in the
   Patch's Workshop Universe with a **current-time** topic (NOT
   pre-Rivet on the first render — the pre-Rivet topic would make
   chronology confound the memory-behaviour test).
   Suggested first topic: any Patch-solo idea Chris naturally
   wants to make where at least one whole-cast memory would
   plausibly be relevant.
2. Toggle "Use workspace knowledge" ON.
3. Render.

Success criteria:

- Composition reaches `completed` status.
- `Composition.memory_ids` contains exactly 1 UUID (per `top_k=1`).
- The UUID is either a whole-cast row or a (future) Patch-only
  row; NEVER a Rivet-only row (`c86d4902` or `cd73d52f`).
- SPA `MemoriesUsedSummary` chip renders "Continuity — Used 1 story memory".
- `MemoriesUsedPanel` renders the selected memory row.
- The generated solo script remains coherent (no forced
  exposition, no memory-hijack — matches the SESSION 267 §14 +
  268 Obs #6 quality bar).

Do NOT promote from the first render regardless of outcome. The
first render is a technical verification, not story authorship.

Once the technical path is proven, THEN Chris can either:

- move to a pre-Rivet topic (accepting the §9.7 chronology
  limitation as bounded evidence — some retrieved memories may
  be temporally anachronistic; observation-only, no promotion),
  or
- promote a first Patch-only witness-scoped memory row (the
  §9.9 HIGH-VALUE dogfood direction — creates the first Patch-
  only witness class in the pool, orthogonal to chronology).

### §10.8 Known chronology limitation

§9 finding stands unchanged: Character OS still does NOT
distinguish Episode creation order from Episode story order.
§10 does NOT address chronology; it only unlocks the solo
memory-retrieval lane. A pre-Rivet Patch-solo render remains
non-destructive (per §9.8 render↔promote separation) but any
retrieved memory row may be temporally anachronistic to the
prose intent. Filtering that out remains an operator judgment,
not a substrate guarantee.

### §10.9 Explicit remaining gaps

- No chronology / story-time / prequel-safe filtering (§9.7).
- No runners-up + distances probe (§4.2 / §8 #1 / §8 #11).
- No relevance floor (§4).
- Solo `dialogue_scene` variant not built (§9 gap classifier
  named it but the correct fix is `talking_head` gaining memory,
  which §10 does — this gap is now closed by removing the need).
- Patch-only witness class still has zero rows (§9.9). §10 makes
  the first such row *possible* to create; the operator must
  still author + promote one.

### §10.10 Commit

Doc + code + tests staged and committed together as the coherent
§10 slice. Push status recorded below in §10.11.

### §10.11 Commit + push checkpoint

- Slice commit: `765bb73` — `feat(memory): SESSION 269 §10 — solo talking_head narrative-memory lane`.
- Predecessor doc-only commit (SESSION 269 §1-§9): `bc4d8ba`.
- Push status: recorded in the §10.11 update commit below.

---

**SESSION 269 IS NOT CLOSED.** This document captures the two
organic Episodes Chris authored (§1-§8), the §9 read-only prequel-
substrate audit, and the §10 solo-cast narrative-memory lane
implementation. Runtime is now DIFFERENT from SESSION 268 close
by exactly one slice: `talking_head` compositions with Universe-
scoped spokespeople now retrieve `NarrativeMemory` under
`retrieve_universe_memory`. All other invariants — chronology,
dialogue-lane behaviour, witness semantics, canon boundary,
`top_k=1`, promote path — are untouched. Any further Episodes,
promotions, or audit findings should extend this document (add
§11, §12…) rather than start a new one.

## §11. Observation §11 — first real solo talking_head dogfood (`44f2279f`)

Read-only audit of the first creator-side solo `talking_head`
render after the §10 implementation. Two independent findings —
one operational (§10 code did not execute this render) and one
architectural (writing-contract mode mismatch). Composition NOT
promoted per operator instruction.

Evidence sidecar:
`docs/design/session_269_experiment_data/03_composition_44f2279f_evidence.json`

### §11.1 Persisted Composition state

- Full id: `44f2279f-2ead-4a79-a180-bc207e108abb`
- Template: `talking_head`, status `completed`, mock_mode `false`
- Operator topic: *"Patch decides to clean one corner of the workshop and immediately finds something that gives him another idea."*
- Workspace: `4ce5486d` · Spokesperson: **Patch** (`7fad8172`) · Spokesperson.universe: Patch's Workshop (`56d16b63`)
- **Episode: `None`** (standalone Composition)
- Target duration 90s; predicted 101s; contract v4; attempt count 1; verified
- Knowledge chunk ids: 5 (matches SPA display "2 docs · 5 chunks")
- **`memory_ids: []`**
- Steps: 1 × `generate_avatar_speech`; step cost 20000 micros
- Created `2026-08-19 15:29:20 UTC` · updated `2026-08-19 15:32:29 UTC`

### §11.2 Orphaned Episode

The DB carries an Episode with a matching title/topic but the two
never connected:

- Episode `91a63409-6a09-4206-8a9c-33e5fa064fb2` — same title, same
  operator_topic, **cast is EMPTY**, attached_compositions = 0.
- Composition `44f2279f` — `episode_id = None`.

Interpretation: Chris created an Episode row but (a) did not add
Patch to `Episode.cast` and (b) submitted the render through a
path that did not carry `?episode=`, so the resulting Composition
remained standalone.

### §11.3 §10 technical acceptance test — result: FAILED / INCOMPLETE

Expected (per §10.7): `Composition.memory_ids` = one UUID; SPA
"Continuity — Used 1 story memory" chip; `MemoriesUsedPanel`
renders. Observed: `memory_ids = []`; no Continuity chip; no
panel — consistent with Chris's SPA screenshot.

**Cause classification: C (retrieval did NOT fire for this creator
path).** Root cause is OPERATIONAL, not architectural.

- Celery worker start time (from `/tmp/character-os-celery.log`): `2026-08-18 00:39:20 -0600`.
- §10 slice commit time (`765bb73`): `2026-08-19 09:21:50 -0600`.
- Composition created: `2026-08-19 09:29:20 -0600` (local).
- `grep -c "retrieve_universe_memory" /tmp/character-os-celery.log` = **0**.

The Celery worker booted the day BEFORE the §10 slice landed.
Every render since has executed pre-§10 primitive code.
`_maybe_synthesize_script` in the worker's loaded module never
called `retrieve_universe_memory`, so `Composition.memory_ids`
stayed at its default `[]`.

**Counterfactual reproduction (audit-time, in a fresh Python
process reading current code):**

```python
retrieve_universe_memory(workspace, universe, [patch],
                         operator_topic, top_k=1)
→ [NarrativeMemory 8d4fdfec ("Patch found the old workshop-agent
   project and notes…")]
```

The predicate returns exactly one memory. Rivet-only rows
(`cd73d52f`, `c86d4902`) are correctly excluded (validated by
§10.5 tests). The candidate is a whole-cast row that would have
been thematically adjacent (finding-something-and-having-an-idea).

**§10 runtime dogfood is INCOMPLETE despite 15/15 green unit
tests.** Verification requires (a) restarting Celery worker + Django
dev server so the §10 code is actually loaded into the running
processes, and (b) rendering a NEW Composition. That is a Chris-
side operator action, not something this audit executes.

Also note: even if §10 had fired on this render, the promote panel
(`NarrativeMemoryPromotePanel`) would still not have appeared
because `c.episode` is null — that gate is a SESSION 264 Slice 1
invariant ("memory belongs to a story"), so standalone renders
never surface promotion regardless.

### §11.4 Creator UI-flow gap — SESSION 262 lesson recurring

Two-character path (SESSION 262 corrected):

- `/workspace/episodes/<id>` renders a "New dialogue scene" CTA when `cast.length >= 2`.
- CTA links to `/recipes/dialogue_scene?episode=<id>`.
- Recipe form pre-fills topic + primary/secondary from Episode.
- Submit propagates `?episode=` onto `Composition.episode` FK.

Solo path (as of §10):

- Same Episode detail page falls through to `/recipes/talking_head?episode=<id>` when `cast.length < 2`.
- Recipe form pre-fills topic + `spokesperson_id` from `Episode.cast[0]?.id`.
- Same `?episode=` submit path attaches the FK.

**But `44f2279f` slipped through both gates:**

1. Chris created the Episode row but did NOT populate `Episode.cast` (Patch was not added). Pre-fill on `Episode.cast[0]?.id` becomes `undefined`, so the operator had to pick the spokesperson manually. That is a subtle UX signal — the flow feels different from the two-cast case where a fully-populated Episode auto-arms the recipe form.
2. `44f2279f.episode_id = None` implies Chris either navigated to `/recipes/talking_head` directly (bypassing the Episode CTA) or the operator forgot which surface he was on. The standalone recipe path accepts submissions without any Episode context.

**This is the same product lesson SESSION 262 corrected for the
2-character path:** a backend primitive existing does not mean the
creator workflow is shipped. §10 shipped the memory-retrieval
backend on the solo path; the Episode-attach ergonomics for solo
Episodes were not audited in the same slice.

There is no persisted evidence in this repo's DB of any prior
Rivet-solo `talking_head` created via the current SPA path — the
Rivet-solo Composition on record (`b0b0e932`, SESSION 267 "Rivet
finds the PATCH OVERRIDES folder") was authored via a
backend/starter test path. Chris's observation ("the Rivet-solo
work done previously does not appear to match the creator-facing
UI available now") is consistent with that history.

### §11.5 Solo story quality — accepted-script findings

Full accepted script is in the sidecar
(`section_c_writing_contract_findings`); three specific quality
issues:

**Cast / presence drift** — the accepted script includes:

> *"I call for Rivet because last time a 'mystery part' turned
> out to be two experiments welded by optimism."*
> *"Rivet's rule: label things."*
> *"We line up a reprint…"*

Rivet is invoked as an active off-screen participant, converting
what should be a Patch-only scene into a two-character scene with
one voice on the audio. Chris's stated expectation: Rivet as part
of Patch's world/history (*"If this gets weird, I'll call
Rivet"*) without being an active participant in the current
moment.

**Temporal / action compression** — the script performs an entire
mini-experiment inside the monologue: finds → loads → lines up
reprint → observes scale difference → changes plan → records
settings → runs experiment → "Halfway through" → observes
adhesion failure → conclusion. Chris's expectation: ONE moment
(discovery → plan → optional condition) with later outcomes
deferred to later Episodes.

**Scene vs process-summary** — the output reads as *"a narrated
experiment / tutorial / retrospective"* interleaving past-tense
recap (*"I tried…"*, *"I found…"*) with plan-forward statements.
Chris's expectation: *"a character inhabiting a story scene right
now."*

### §11.6 Writing-contract root cause

Traced in `shell/character_os/writing_contract.py` +
`shell/character_os/script_synthesis.py`.

- The talking_head duration-driven path calls `WritingContract.for_shape("long_form", ...)` (`script_synthesis.py:_build_writing_contract_section` + `duration_contract.synthesize_with_duration_gate`).
- `_long_form_contract` emits `_INVARIANTS_BLOCK` + `_NARRATIVE_SHAPES_BLOCK` + `_CTA_POLICY_BLOCK` + `_ANTI_SELF_DESCRIPTION_BLOCK` + `_ANTI_GENERIC_REGISTER_BLOCK`.
- Invariant #4 explicitly demands *"At least one meaningful change… a turn in thought, a piece of tension, an unexpected detail, a reversal."*
- Narrative-shape menu recommends *"story → realization / mistake → lesson / experiment → outcome / observation → explanation / question → exploration → answer."*
- **Nothing in this contract constrains cast presence** (no "you are the only character in this scene" rule).
- **Nothing constrains temporal framing** (no "this depicts one present moment; later outcomes belong in later Episodes" rule).
- **Nothing distinguishes operator_topic-as-scene-premise from operator_topic-as-content-subject** (the topic is treated as material to explore, not a moment to inhabit).

The writer executed the contract faithfully. The output is a
successful long-form monologue about the topic — which is exactly
what `_long_form_contract` requests. The failure is not the model;
the failure is that this contract is the wrong contract for a
solo Episode scene.

**Dialogue contract contrast** (`_dialogue_scene_contract`):

- Opens with *"The scene is a conversation between the characters introduced in Section 2… The audience is watching a real exchange, not a pair of parallel presentations."*
- `_DIALOGUE_WATCHABILITY_BLOCK` #1: *"ENTER WITH AN IN-SCENE STANCE — Each character arrives with an immediate purpose, stance, reaction, or desire for THIS scene."*
- Watchability #3: *"PREFER SPECIFIC ACTION / REACTION OVER PHILOSOPHY."*
- Watchability #5: *"END ON A MOMENT, NOT A SUMMARY."*

Dialogue explicitly frames output as a **scene** (moment) with
characters IN it. Long-form talking_head frames output as a
**topic** (subject) the character speaks about. These are
architecturally different modes served by the same primitive.

### §11.7 Product-mode classification

**Verdict: B (mostly the same; Episode-attached `talking_head`
needs a story-mode contract while legacy non-Episode `talking_head`
preserves current content behavior).**

Two coexisting product modes on one recipe:

| Mode | Discriminator | Contract | Callers |
|---|---|---|---|
| Content (existing, load-bearing) | `Composition.episode is None` | `_long_form_contract` / `_standalone_contract` — invariants + narrative-shape menu + CTA policy | Marketing scripts, explainers, product briefs, long-form ad copy, every historical `talking_head` caller |
| Story (dogfood direction) | `Composition.episode is not None` | (new) scene-mode contract — single character present, one present moment, no invented collaborators, later outcomes deferred | Solo Episode-attached renders (Patch-only, Rivet-only, future Ruby/Mason) |

`Composition.episode` is a natural, already-existing discriminator.
Non-Episode callers keep byte-identical prompts. Episode-attached
callers get the scene-mode contract.

**Alternatives rejected:**

- **A (small correction across the board)** — would break every
  legacy caller. Marketing scripts do NOT want present-moment
  scene semantics.
- **C (new recipe)** — would duplicate the entire form field
  surface for zero substrate change. Violates the operator's
  DO-NOT list.
- **D (something else)** — not observed.

### §11.8 Smallest next action (proposed — NOT authorized here)

A focused Episode-attached solo scene-mode contract slice:

1. **Fix cause C first (operator action, no code):** restart the
   Celery worker + Django dev server so the §10 code actually
   loads. Chris can then rerun the smallest first technical
   verification defined in §10.7 (with a Patch-only Episode that
   actually has Patch in the cast + navigates through the Episode
   CTA so the FK attaches).
2. **Then, if evidence still shows scene-drift (§11.5), open a
   focused slice for the writing-contract discriminator:**
   - Add a new shape `"solo_scene"` (or an `is_scene: bool` flag)
     to `WritingContract.for_shape`.
   - Author a `_solo_scene_contract()` that carries the same
     scene framing dialogue does (present-moment, single-character
     presence, "END ON A MOMENT", no invented collaborators, no
     compressed future outcomes) minus the multi-character
     interaction invariants.
   - Route Episode-attached `talking_head` through the new shape
     via a discriminator check in `_maybe_synthesize_script`
     (`spokesperson.universe_id is not None and
     composition.episode_id is not None` → `"solo_scene"`,
     otherwise `"long_form"` / `"standalone"` — bytes-identical
     legacy behaviour when episode is null).
   - Bump `WRITING_CONTRACT_VERSION` to 5.
3. **Optional adjacent slice (defer):** Episode-attach ergonomics
   — auto-add spokesperson to `Episode.cast` when a solo render
   is submitted through `?episode=`, or require the operator to
   confirm cast on the CTA. Not authorized here; documented so
   the SESSION 262 lesson lands.

### §11.9 Implementation disposition

**Not implemented in this session per operator instruction.**
Chris + ChatGPT will review §11.7 classification and §11.8
proposal before any writing-contract change is authorized.

Explicit DO NOT for this session (re-affirmed):

- Do NOT implement chronology.
- Do NOT change `top_k`.
- Do NOT add relevance floor.
- Do NOT add new models.
- Do NOT promote memory.
- Do NOT create a new recipe.
- Do NOT render another Composition.

**DO NOT PROMOTE from `44f2279f`** — reasons captured in
sidecar `section_h_promotion_disposition`: first technical
verification, Continuity behavior unclear (retrieval didn't
fire), script exhibits cast-presence drift, script compresses
future outcomes into one scene. Not durable-continuity material.

### §11.10 Known chronology limitation (unchanged)

§9 story-time finding stands. §11 does not touch chronology.
Any Episode-attached solo rendering under the future scene-mode
contract would still retrieve any temporally-eligible memory
(no story-time gate exists).

### §11.11 Explicit remaining gaps

- §10 runtime dogfood not yet verified against real persisted
  state (cause C — operational; awaits worker restart + rerender).
- Solo `Episode.cast` auto-population UX gap (§11.4).
- Writing-contract mode-discriminator (§11.7 B) not built.
- Chronology / story-time (§9.7) unchanged.
- Runners-up + distances probe still not built (§4.2, §8 #1, §8 #11).
- Relevance floor still not compelled (§4.5).
- Patch-only witness class still has zero rows (§9.9, §10.9).

### §11.12 Commit checkpoint

Docs + evidence sidecar committed as a doc-only slice (see
report below). No source-code change in this checkpoint.

---

**SESSION 269 IS NOT CLOSED.** This document now captures the
two organic Episodes (§1-§8), the §9 read-only prequel-substrate
audit, the §10 solo-cast narrative-memory implementation, and
the §11 first-real-solo-dogfood observation which surfaced (a) an
operational §10 non-execution and (b) a genuine product-mode
distinction between TALKING HEAD AS CONTENT FORMAT and SOLO
EPISODE AS STORY FORMAT. Any further Episodes, promotions, or
audit findings should extend this document (add §12, §13…)
rather than start a new one.

## §12. One-character Episodes as a first-class creator workflow

Product decision (operator brief): **do NOT create a separate
"Solo Episode" model, screen, route, or workflow.** The Episode
domain object stays the same. "Solo" is not an Episode type;
it is a cast-cardinality property that changes which scene CTAs
the Episode detail page offers.

This slice adds inline cast selection to the Create Episode form
and gates the scene CTAs on cast cardinality so the empty-cast
footgun that produced Composition `44f2279f` (§11) cannot recur
silently.

### §12.1 Root cause of empty-cast Episode `91a63409`

Traced end-to-end:

- The Create Episode form (`web/src/routes/workspace/universes.$id.episodes.tsx` at slice open) captured **only** `title` + `operator_topic`. There was NO cast picker.
- Backend `EpisodeSerializer` accepted **only** `{universe, title, operator_topic}` at create; cast attachment required per-teammate `POST /api/episodes/<id>/cast/` calls.
- On the Episode detail page, cast could be added via a separate dropdown + "Add to cast" button — a second UI trip after creation.
- Chris created the Episode row with the intended topic, then went to render without making the second trip. The Episode detail page's scene CTA still fired (fall-through branch `cast.length < 2` → `talking_head` CTA), so the flow visually resembled "ready to render" — but with the spokesperson pre-fill of `Episode.cast[0]?.id === undefined`.
- Chris also then navigated to a standalone `/recipes/talking_head` (bypassing the Episode CTA), so `?episode=<id>` was never on the URL and `Composition.episode` never attached.

Two independent product surfaces failed the same operator flow:

1. **Create form had no cast picker** → cast attach was a second trip.
2. **Episode detail scene CTA fired unconditionally on cast < 2** → visually indistinguishable from "cast=1 ready".

### §12.2 Old flow vs new flow

**Old (pre-§12):**

```
Create Episode form
  fields: title, operator_topic
    ↓ POST /api/episodes/
Episode detail
  cast: [] (must be added via separate dropdown per-member)
  scene CTA fires for cast.length < 2 → talking_head
     (no visible distinction between cast=0 and cast=1)
```

**New (§12):**

```
Create Episode form
  fields: title, operator_topic, CAST (multi-select same-Universe teammates)
    ↓ POST /api/episodes/  {..., cast_ids: [uuid, ...]}
    (server attaches cast under one transaction; a bad UUID
     aborts the whole create; empty cast is legal draft)
Episode detail
  cast=0  → NO scene CTA + "add at least one character" hint
  cast=1  → "New solo scene" CTA → /recipes/talking_head?episode=<id>
  cast=2+ → "New dialogue scene" CTA → /recipes/dialogue_scene?episode=<id>
```

Solo scene CTA route was already correct pre-§12 (talking_head
with `?episode=` propagation + topic + spokesperson pre-fill from
`Episode.cast[0]`). No routing change was needed; only visible
gating of the CTA and inline cast capture at creation.

### §12.3 Zero-cast decision — B (allow draft; block silent fall-through)

Existing Episode semantics already allow zero-cast rows (no NOT
NULL / not_empty constraint on `cast`), and 20 such Episodes
exist in the DB today. Ripping that out risks silent data loss
on any legacy zero-cast draft.

**Selected behaviour:**

- Create form: cast picker is OPTIONAL. Zero-selection legal.
  Inline copy tells the operator: *"No cast selected — this will
  save as a draft Episode. The scene action on the Episode page
  will remind you to add at least one character before
  rendering."*
- Episode detail: cast=0 renders NO scene CTA (removes the
  previous unconditional talking_head CTA that fired on the
  `< 2` fall-through branch). Instead an inline hint reads:
  *"Add at least one character to this Episode's cast (above) to
  enable scene creation."*
- The pre-existing `insufficientCast` guard on the recipe form
  (SESSION 262) still catches any deep-linked
  `/recipes/talking_head?episode=<id>` attempt when the Episode
  has zero cast.

Silent fall-through into standalone recipe creation is now
impossible from an Episode-attached path.

### §12.4 Files changed

**Backend:**

- `shell/apps/universe/serializers.py`
  - `EpisodeSerializer` gains `cast_ids: ListField[UUIDField]` (write-only, optional, default `[]`).
  - `create()` override: resolves + validates teammate UUIDs (Universe consistency + Workspace consistency + unknown-UUID handling) BEFORE the Episode row is written, then attaches under `transaction.atomic()` using the same `pre_add` signal path the dedicated `/cast/` endpoint uses.
  - `update()` override: silently drops `cast_ids` on PATCH (create-only field). Cast mutation on an existing Episode continues to route through the dedicated per-add endpoint so per-add signal errors surface distinctly.
  - Duplicates in `cast_ids` collapse to one attachment, preserving first-appearance order.

**Frontend:**

- `web/src/lib/api/episodes.ts`
  - `CreateEpisodePayload` gains optional `cast_ids?: string[]`.
- `web/src/routes/workspace/universes.$id.episodes.tsx`
  - Create form gains a cast picker (multi-toggle chips) seeded from `useSpokespeople()` filtered to `s.universe === universeId`.
  - Local `selectedCastIds: Set<string>` state; `toggleCast(id)` handler.
  - On submit, if any cast selected, includes `cast_ids: [...]` in the create payload; otherwise omits the field (byte-identical to pre-§12 wire shape for zero-cast).
  - Inline copy tailored to `selectedCastIds.size` (0 / 1 / 2+).
- `web/src/routes/workspace/episodes.$id.tsx`
  - Scene CTA branching updated: cast=1 → `episode-render-solo-cta` (rewords the button to "New solo scene"), cast=2+ → `episode-render-dialogue-cta`, cast=0 → no CTA + `episode-cast-empty-hint`.

**Tests:**

- `shell/apps/universe/tests/test_episode.py` — 9 new tests (`test_51` — `test_59`) covering solo/multi/zero-cast create, atomic rejection on cross-Universe / unknown-UUID / cross-workspace teammate, duplicate-cast dedup, and PATCH-ignores-cast_ids.
- `web/src/routes/workspace/episode-cast-picker.test.tsx` — 7 new tests covering picker rendering + wire-shape + Episode-detail CTA branching for cast=0/1/2.

### §12.5 Test coverage

- Full backend suite (`apps/universe/` + `apps/compositions/` + `apps/embeddings/` + `apps/memory/` + `apps/spokespeople/`): **1548 passed**, 0 failed.
- Full SPA suite (`pnpm exec vitest run`): **635 passed**, 0 failed.
- No test skips introduced; every existing test remains green.

### §12.6 What remains unchanged

- Episode model + `EpisodeCast` through table + migrations: byte-identical.
- Dedicated per-add / per-remove cast endpoints (`POST /api/episodes/<id>/cast/`, `DELETE /api/episodes/<id>/cast/<teammate_id>/`): behaviour untouched.
- Composition creation flow from the Episode CTA: unchanged (§10 memory-retrieval wire still active; `?episode=` propagation still on).
- `dialogue_scene` >=2 contract: unchanged.
- `talking_head` writing contract: unchanged (§11 finding about scene-drift remains open — §11.8 slice not authorized here).
- `retrieve_universe_memory` predicate + `top_k=1` + witness semantics: unchanged.
- Chronology: unchanged (§9 finding still stands).
- `Composition.memory_ids` recipe-agnostic provenance: unchanged.
- Legacy Episodes with `cast=[]` in the DB: not migrated / not touched; still legal drafts.

### §12.7 Acceptance-test instructions for Chris

Chris runs the real UI acceptance test — this session did NOT
render any Composition per operator instruction.

1. Open the SPA (`http://localhost:5174/`).
2. Navigate to Patch's Workshop → Episodes.
3. Click **New Episode**.
4. Enter a simple current-time topic (avoid pre-Rivet framing —
   that's a separate finding).
5. In the new **Cast** picker, click **Patch** ONLY.
6. Save.
7. Land on Episode detail.
8. Confirm Patch appears in the Cast section.
9. Confirm the **New solo scene** button is visible.
10. Click **New solo scene**.
11. Confirm the recipe form opens with:
    - Patch pre-selected as spokesperson,
    - the Episode topic already populated in the topic textarea,
    - the Episode-context chip near the top of the form.
12. Chris renders.

The resulting Composition should then allow us to test **separately**:

- §10 NarrativeMemory retrieval actually firing (workers were
  restarted after §11 — the §10 code should now be loaded).
- Continuity summary + panel rendering with a memory row.
- `Composition.episode` FK persisted.
- Solo story-writing quality (still on `_long_form_contract` per
  §11.6 — expect the same scene-drift pattern until the §11.8
  slice is authorized).

Do NOT conflate those into this UI implementation verification.

### §12.8 Explicit note: SOLO is not a new Episode type

Reaffirming the operator brief: `Episode` remains one domain
object. There is no `is_solo` field, no `episode_type` enum, no
`SoloEpisode` subclass, no `/workspace/solo-episodes/` route.
Cast cardinality is the only property that changes downstream
behaviour, and it lives on the existing `EpisodeCast` M2M — same
storage the two-hander case uses.

### §12.9 Commit checkpoint

- Slice commit: `06ba772` — `feat(episode): SESSION 269 §12 — one-character Episode creator workflow`.
- Predecessor commits still pending push at commit time: `91c9e3a` (§11 doc audit).
- Predecessors already on origin: `bbcc1f0` (§10 doc checkpoint), `765bb73` (§10 slice), `bc4d8ba` (§1-§9 doc).

### §12.10 Commit + push

Post-commit doc-update push status is captured in §12.11 below
after the operator-visible fingerprint completes.

### §12.11 Push checkpoint

(Populated after `git push origin main` — see report at end
of session turn.)

---

**SESSION 269 IS NOT CLOSED.** This document now also captures
the §12 one-character-Episode creator-workflow slice — inline
cast picker on Create Episode form, atomic `cast_ids` backend
seed, and cast-cardinality-gated scene CTAs on Episode detail.
Runtime is now DIFFERENT from the §10 slice by exactly one
additional slice: Create Episode captures cast, and cast=0
Episodes no longer offer a silent scene CTA. All other invariants
— chronology, dialogue-lane behaviour, witness semantics, canon
boundary, `top_k=1`, promote path, `talking_head` writing
contract — are untouched. Any further Episodes, promotions, or
audit findings should extend this document (add §13, §14…)
rather than start a new one.

## §13. Operator-visible parity pass for §12

Read-only verification pass BEFORE Chris performs the §12
acceptance test. Prompted by the recurring dogfood lesson: we
have repeatedly encountered cases where source implemented +
automated tests passing did NOT imply the operator could see or
reach the capability. §13 codifies the distinction and applies
it to §12.

Evidence sidecar:
`docs/design/session_269_experiment_data/04_operator_visible_parity_pass.json`

### §13.1 New working rule (durable methodology)

> **"Implemented" and "operator-visible" are separate verification
> states.** For creator-facing work, a report must distinguish
> four levels and NEVER upgrade a claim without evidence at the
> claimed level:
>
> 1. **SOURCE IMPLEMENTED** — code exists at the current HEAD.
> 2. **TESTED** — automated tests exercise the code and pass.
> 3. **LIVE VISIBLE** — the currently running services actually
>    serve the code to any real client that requests it (backend
>    process has reloaded, Vite serves current source, no stale
>    worker).
> 4. **OPERATOR REACHABLE** — an ordinary operator following the
>    documented flow through the real UI can see and use the
>    capability without workarounds or hidden knowledge.
>
> A feature is not "shipped to the operator" until level 4 is
> verified. Level 1+2 alone is a coding claim, not a shipping
> claim. This rule is part of the ongoing Character OS dogfood
> methodology.

### §13.2 Running-process freshness at audit time

Git HEAD: `87c328f` (`docs(session-269): record §12 slice commit
SHA 06ba772 in checkpoint`). Origin/main matches. Working tree
clean before audit.

Process boot times vs commit landing times:

| Process | Started (local) | vs §10 slice (09:21:50) | vs §12 slice (10:22:37) | Verdict |
|---|---|---|---|---|
| Django | 09:53:42 | AFTER | BEFORE, but autoreload picked up serializer edits (see log evidence below) | §10 + §12 code LOADED |
| Media-engine | 09:53:42 | AFTER | BEFORE — §12 has no media-engine change | not relevant |
| Celery | 09:53:42 | AFTER | BEFORE — §12 has no Celery-task change (all §12 logic is DRF serializer/view path) | §10 LOADED; §12 irrelevant to Celery |
| Vite | 09:53:43 | AFTER | BEFORE — Vite HMR + on-demand source transform serves current on-disk source (see live_module_grep) | §12 modules LOADED |

**Django autoreload evidence** (`/tmp/character-os-django.log`):

- 4× `Watching for file changes with StatReloader`
- 3× `shell/apps/universe/serializers.py changed, reloading.`

Autoreload fired every time I edited the serializer during §12,
so the live Django process holds the current serializer code.

**Live Django serializer introspection** (in-process import of
`apps.universe.serializers.EpisodeSerializer` inside the same
autoreloaded module namespace):

```
EpisodeSerializer fields (live): [
    'id', 'universe', 'universe_name', 'title', 'operator_topic',
    'cast', 'cast_ids', 'composition_count', 'archived_at',
    'created_by', 'created_at', 'updated_at'
]
cast_ids present? True
cast_ids shape: ListField, write_only=True, required=False, default=list
```

**API health probe:** `curl http://localhost:8010/api/episodes/`
→ `403 {"detail":"Authentication credentials were not provided."}`
— endpoint live, correctly rejects unauthenticated requests.

### §13.3 Live Vite module verification

Vite dev server serves each source file as an ES module on
demand. There is no separate bundle; presence of §12 marker
strings in the served module PROVES the current on-disk source
is what will be delivered to any browser that requests it.

**Create Episode form module** — `curl http://localhost:5174/src/routes/workspace/universes.$id.episodes.tsx`:

- HTTP 200, 39,504 bytes served
- Markers present: `episode-create-cast-picker`, `episode-create-cast-toggle-`, `"Cast (optional; add now or later)"`, `toggleCast`, `selectedCastIds`

**Episode detail module** — `curl http://localhost:5174/src/routes/workspace/episodes.$id.tsx`:

- HTTP 200
- Markers present: `episode-render-solo-cta`, `episode-render-dialogue-cta`, `episode-cast-empty-hint`, `"New solo scene"`, `"New dialogue scene"`, `"Add at least one character"`

**Recipe form module** — `curl http://localhost:5174/src/routes/recipes/$kind.tsx`:

- HTTP 200
- Markers present: `episode-context-chip`, `episode-context-title-link`, `episode-insufficient-cast`, `"Rendering under episode"`

**Composition detail module** — `curl http://localhost:5174/src/routes/compositions/$id.tsx`:

- HTTP 200
- `MemoriesUsedSummary` + `MemoriesUsedPanel` mounted unconditionally with `memories={c.memories_used}` — no `template_kind` gate, no `terminal` gate, no `episode` gate.
- `NarrativeMemoryPromotePanel` gated on `c.episode && terminal` — an Episode-attached completed talking_head will surface promote UI (matches dialogue behaviour).

### §13.4 Exact creator-facing wording (verbatim from the served module)

- Create form section label: **`Cast (optional; add now or later)`**
- Empty-cast picker hint: *"No characters in this Universe yet. Add teammates to this Universe from the Universe detail page, then come back — or create the Episode now and attach cast later."*
- Zero-selection hint: *"No cast selected — this will save as a draft Episode. The scene action on the Episode page will remind you to add at least one character before rendering."*
- One-selection hint: *"One character selected — the Episode will offer a solo-scene action."*
- Multi-selection hint: *"N characters selected — the Episode will offer a dialogue-scene action."*
- Episode detail cast=0 hint (`episode-cast-empty-hint`): *"Add at least one character to this Episode's cast (above) to enable scene creation."*
- Episode detail cast=1 CTA button label: **`New solo scene`**
- Episode detail cast=2+ CTA button label: **`New dialogue scene`**
- Recipe-form Episode chip (SESSION 262, unchanged): *"Rendering under episode <title>" · "cast: <names>"*

### §13.5 §12 → live parity matrix

| Capability | Source | Test | Live SPA | Operator reachable |
|---|---|---|---|---|
| Cast picker on Create Episode | ✅ | ✅ | ✅ (module markers present) | ✅ (visible on `/workspace/universes/:id/episodes` after clicking "New Episode") |
| One-cast selection | ✅ | ✅ | ✅ | ✅ (single-click toggle) |
| Multi-cast selection | ✅ | ✅ | ✅ | ✅ (independent toggles) |
| Zero-cast draft explanation copy | ✅ | ✅ | ✅ | ✅ (hint text renders inside picker block) |
| Zero-cast scene CTA suppression | ✅ | ✅ | ✅ | ✅ (no `episode-render-solo-cta`/`episode-render-dialogue-cta` mounted when `cast.length === 0`; only `episode-cast-empty-hint`) |
| One-cast "New solo scene" CTA | ✅ | ✅ | ✅ | ✅ (mounted when `cast.length === 1`) |
| Two+-cast "New dialogue scene" CTA | ✅ | ✅ | ✅ | ✅ (mounted when `cast.length >= 2`; regression check green) |
| Solo route carries `?episode=` | ✅ | ✅ | ✅ | ✅ (`/recipes/talking_head?episode=<id>` — verified in module string) |
| Solo form pre-fills spokesperson | ✅ (SESSION 262 code) | ✅ | ✅ | ✅ (recipe form pre-fill from `Episode.cast[0].id` unchanged) |
| Solo form pre-fills Episode topic | ✅ (SESSION 262 code) | ✅ | ✅ | ✅ (recipe form pre-fill from `Episode.operator_topic` unchanged) |
| Episode-context indicator visible | ✅ (SESSION 262 chip, unchanged) | ✅ | ✅ | ✅ (`data-testid="episode-context-chip"` visible when `?episode=` is present, reads *"Rendering under episode <title>"*) |
| Solo render submission would preserve Episode attachment | ✅ | ✅ (SESSION 262 tests + §12 unit tests) | ✅ (form includes `episode: episodeHint` in create payload when hint present) | **NOT VERIFIED** in live SPA — deferred to Chris's acceptance render |
| Solo talking_head Composition renders Continuity summary + panel | ✅ (SESSION 264 Slice 3) | ✅ (component tests) | ✅ (panels mounted unconditionally on `/compositions/:id`) | **NOT YET LIVE-VERIFIABLE** — no solo talking_head Composition with `memory_ids != []` exists in the live DB yet (44f2279f from §11 has `memory_ids=[]`). Verifiable after Chris's acceptance render. |

**No MISMATCH rows.** No SOURCE-ONLY rows.

### §13.6 Known visible difference (one)

Documented in §12.7 step 11: *"the Episode-context chip near the
top of the form"*. The chip exists (SESSION 262
`episode-context-chip`) and is visible in the served module. It
is styled as a **bordered card**, not a small pill — the reference
docstring calls it "chip" but the actual DOM is a
`<div class="… rounded-md border border-luxe bg-card/60 px-4 py-2 text-sm">`
reading *"Rendering under episode <title> · cast: <names>"*.

**Impact:** cosmetic; Chris will still see the Episode context
prominently. No fix warranted. Documenting so the description in
§12.7 matches the visible DOM.

Updated wording for §12.7 step 11 (from documentation only, no
code change): *"the Episode-context indicator — a bordered card
labelled 'Rendering under episode <title>' — at the top of the
recipe form."*

### §13.7 What was NOT verified without a browser

Explicit gaps the operator should know about:

1. **Actual pixel rendering** — chip legibility, button positions relative to fold, whether picker chips wrap gracefully at narrow widths.
2. **Actual click / keyboard interactions** — visual selection state feedback, focus order, accessibility affordances.
3. **Browser cache** — if Chris has a browser tab open from BEFORE §12 landed, the currently loaded modules in that tab may be stale. Vite HMR usually pushes updates without a refresh, but a hard refresh (Cmd+Shift+R on macOS) is the only guaranteed way to load current source into a running browser session.
4. **Live Continuity panel for solo case** — no solo talking_head Composition with a populated `memory_ids` exists in the live DB. The panel is mounted architecturally correctly (§13.3 composition-detail module verification), but there is nothing operator-visible to point at until Chris renders one.

### §13.8 Continuity panel: NOT YET LIVE-VERIFIABLE

Per §13.5 last row + §F rules: the panels are mounted
unconditionally on Composition detail; there is no
`template_kind` / `episode` / `terminal` gate that would hide
them from a talking_head Composition. Panel component itself
returns null on empty `memories`, so a rendered but memory-less
Composition is silent.

Verifiable after Chris's acceptance render produces a Composition
with `memory_ids != []`.

**Did NOT:** promote memory, render, fake DB state, hard-delete
anything. Read-only + one module introspection call.

### §13.9 Final decision: B — SAFE WITH ONE KNOWN VISIBLE DIFFERENCE

**Safe for Chris to dogfood.** Justification:

- Live Django serializer confirmed to have `cast_ids` (autoreload
  proof + in-process introspection).
- Live Vite dev server confirmed to serve current source for all
  four §12-relevant modules (marker-string grep).
- All 12 §12 acceptance-matrix rows resolve to LIVE VISIBLE +
  OPERATOR REACHABLE at the levels each is verifiable without a
  browser session.
- No MISMATCH rows.
- One cosmetic difference (chip vs card) documented; Chris still
  sees the Episode context clearly.
- Continuity panel is the only row where LIVE evidence is
  deferred — not because the plumbing is broken but because no
  data exists to display yet. That is expected for a fresh
  feature and will be demonstrated by Chris's own acceptance
  render.

**Operator hard-refresh reminder:** before running the §12
acceptance test, Chris should reload the SPA (Cmd+Shift+R) to
guarantee any browser tab held over from earlier in the session
loads the current Vite modules. Vite HMR usually handles this
automatically, but a manual refresh is the belt-and-braces
guarantee against a stale-tab false negative.

### §13.10 Commit checkpoint

Doc-only slice — no code changes made in §13.

- §13 doc + evidence commit: `3c0b00f` — `docs(session-269): §13 operator-visible parity pass for §12`.
- Predecessor commits already on origin: `87c328f` (§12 doc checkpoint), `06ba772` (§12 slice), `91c9e3a` (§11 doc audit).
- Push: `87c328f..3c0b00f  main -> main` (successful). Local main == origin/main == `3c0b00f`. Working tree clean.

---

**SESSION 269 IS NOT CLOSED.** §13 verified the §12 slice against
live services and codified the four-level implemented → tested →
live-visible → operator-reachable methodology. Chris may now
proceed with the §12 acceptance test per §12.7 (with the
hard-refresh reminder from §13.9). Any further Episodes,
promotions, or audit findings should extend this document (add
§14, §15…) rather than start a new one.

## §14. Episode-attached solo scene is a STORY MODE, not standalone content

Chris performed the first half of the §12 acceptance test and
STOPPED at the recipe form. §13's parity matrix correctly
verified level 1-3 (source implemented, tested, live modules
served) but wrongly assumed the standalone `talking_head`
authoring controls were the correct destination for Episode-solo
rendering. Chris clarified that Episode rendering is a distinct
STORY MODE — Episode owns the story intent; Character OS writes
the script; the operator should never be asked to reproduce
Episode.operator_topic in a generic textarea nor toggle a generic
"Use workspace knowledge" checkbox.

Evidence sidecar:
`docs/design/session_269_experiment_data/05_episode_solo_mode_design.json`

### §14.1 Chris's live operator checkpoint

Episode created via §12 flow:

- Title / operator_topic: *"Patch does research on AI Agents"*
- Cast: **Patch** (single)

Episode detail rendered per §12 contract — Patch in cast, 0
compositions, "New solo scene" CTA visible, dialogue CTA
correctly absent, hint about adding cast for dialogue. Chris
clicked **New solo scene**.

Recipe form rendered:

- SESSION 262 chip: *"Rendering under episode / Patch does research on AI Agents / cast: Patch"* ✅
- Spokesperson auto-selected: **Patch** ✅
- **But then**: empty "Script or topic" textarea, "Use workspace
  knowledge" toggle (off by default), target duration, fact-check
  mode, opening line, outro controls — the entire standalone
  talking_head content-creation form.

Chris STOPPED before rendering.

### §14.2 Reframe — the question is MODE, not prefill

§13's implicit assumption was: *"Episode.operator_topic should
auto-fill the Script/topic textarea."* Chris clarified that this
is the wrong assumption. Episode-attached solo rendering is a
different product contract:

- **Standalone talking_head** (unchanged): dual-mode by design.
  Mode A = operator supplies finished script, Character OS speaks
  verbatim. Mode B = operator supplies topic + ticks *Use
  workspace knowledge*, Character OS synthesizes. Both modes have
  legitimate historical callers (marketing scripts, brand copy,
  explainers) and MUST NOT regress.
- **Episode-attached solo scene** (new mode): the operator
  supplies Episode.operator_topic + Episode cast when creating
  the Episode. Character OS then owns the actual scripting
  decisions — always AI synthesis, always uses knowledge, always
  runs §10 NarrativeMemory retrieval, always attaches to the
  Episode. The operator is never asked to reproduce the Episode
  topic, and cannot accidentally trigger verbatim-speech mode.

### §14.3 Current exact behavior if Chris rendered now (§C)

Traced against the live running code:

- **SPA-side validation would BLOCK submit** with *"Missing required field: Script or topic"* — `RecipeField.required=True` by default (`shell/apps/compositions/recipes.py:57`); `talking_head.script` does not override.
- **If Chris manually typed the Episode topic + `use_knowledge=False`**: talking_head starter creates the Composition with the topic as its script; `generate_avatar_speech` primitive's `_maybe_synthesize_script` returns raw_script verbatim under `trusted_passthrough`. Patch would literally say *"Patch does research on AI Agents"* as his line. NO NarrativeMemory retrieval (§10 gate is `use_knowledge=True`). NO AI synthesis.
- **If Chris manually typed the Episode topic + `use_knowledge=True`**: AI synthesis fires; §10 NarrativeMemory retrieval fires (Patch.universe_id is set); the generic `_long_form_contract` shapes the output — the exact contract that produced §11 scene-drift (active off-screen Rivet, temporal compression, retrospective framing). `Composition.memory_ids` would populate.

Automatic distinctions that DO exist between Episode-attached and
standalone: SESSION 262 chip, spokesperson pre-fill, insufficient-
cast guard, `?episode=` → `Composition.episode` FK.

Automatic distinctions that DO NOT exist: auto-use of
`Episode.operator_topic`, auto-enable of `use_knowledge`,
writing-contract branch based on Episode context, or any
hiding/adaptation of the standalone controls.

### §14.4 Standalone talking_head contract (confirmed)

Dual-mode by design. Both modes preserved on `/recipes/talking_head`
without any Episode context. Every existing non-Episode caller
expects the same dual-mode UX.

### §14.5 Episode-solo contract (confirmed)

**Operator owns:**
- `Episode.operator_topic` = story intent
- Episode cast = who is in the scene
- Optional render tuning: target duration, opener override, verifier mode, outro decoration, Composition name

**Character OS owns:**
- Actual script wording
- K2 / canon / §10 NarrativeMemory retrieval (automatic; no toggle)
- Writing-contract framing (story-mode, not content-mode)
- Verification + duration gate
- `Composition.episode` FK attachment

**Invariants:** the operator does NOT re-type the Episode topic;
does NOT toggle a generic *Use workspace knowledge* checkbox;
cannot accidentally trigger verbatim-speech mode; AI synthesis
always fires; §10 retrieval always fires; provenance persists.

### §14.6 Cleanest mode discriminator (§E)

> `composition.episode_id is not None AND composition.template_kind == "talking_head"`

Rationale:

- Already-existing state on the Composition row (SESSION 262 FK).
- No new field, no new enum, no schema change.
- Same discriminator drives both the SPA UI branch (`episodeHint`
  + `recipe.kind === "talking_head"`) and the backend writing-
  contract branch.
- Future recipes (`dialogue_scene` already has its own contract)
  are unaffected because the branch is scoped to
  `template_kind == "talking_head"`.
- Zero risk of leakage into standalone talking_head — the branch
  is guarded by both conditions.

### §14.7 Control classification (§F)

| Field | Disposition | Reason |
|---|---|---|
| `spokesperson_id` | **KEEP + auto-select from `Episode.cast[0]`** | SESSION 262 code already handles this |
| `script` (Script or topic) | **HIDE** in Episode-solo mode | `Episode.operator_topic` is authoritative; SPA silently sends it as the script value on submit |
| `use_knowledge` (Use workspace knowledge) | **HIDE + FORCE True** in Episode-solo mode | Story mode always uses knowledge; leaving toggle exposed lets the operator accidentally activate verbatim-speech mode |
| `target_duration_seconds` | **KEEP** | Duration is a legitimate creator choice per render (60s/90s/120s); not owned by Episode |
| `verifier_mode` (Fact-check) | **KEEP** | Render-tuning; not owned by Episode; default `warn` unchanged |
| `opener` (Opening line) | **KEEP** | Optional creative override; not owned by Episode |
| `outro_text` (Brand outro card) | **KEEP** | Rendering decoration, not story intent |
| `outro_image_asset_id` (Outro image) | **KEEP** | Same |
| `name` (Composition name) | **KEEP + auto-derive from `Episode.title`** when blank | Small polish; aligns with existing name-fallback pattern |

**Added visible element** (single new UI block):

- Kind: read-only "Story intent" display
- Placement: directly below the SESSION 262 chip, above target-duration
- Content: *"Story intent (owned by Episode): '<episode.operator_topic>'"* with a link to edit on the Episode detail page
- Purpose: make it obvious to the operator that Episode.operator_topic is the authoritative story input Character OS will use (mirrors how the chip displays cast: <names>)

### §14.8 Writing-contract seam (§H)

New shape: `solo_scene` — added to
`shell/character_os/writing_contract.py` alongside
`_long_form_contract`, `_standalone_contract`,
`_dialogue_scene_contract`. `WritingContract.for_shape("solo_scene", ...)`
returns it. Bump `WRITING_CONTRACT_VERSION` 4 → 5.

Invariants the new contract encodes:

1. **SINGLE ACTIVE CHARACTER** — only the named speaker is present in the current scene. Other characters may be referenced as history, relationships, or future intentions (*"If this gets weird, I'll call Rivet"*) but MUST NOT become active participants (*"I call for Rivet. We line up a reprint…"*). Direct fix for §11 finding.
2. **SINGLE PRESENT MOMENT** — the script depicts one bounded scene happening now. Plans stay plans; describing an experiment's outcome inside the same script is forbidden unless current-scene evidence establishes completion.
3. **PLANS REMAIN PLANS** — establishing intent is fine; simulating multi-phase outcomes is not.
4. **MEMORY AS BACKGROUND** — retrieved NarrativeMemory rows are context the character already knows; they are NOT commands to reenact past events on-camera.
5. **END ON A MOMENT** — the scene finishes on a decision, reaction, hook, or landed observation — never a lesson-summary or process-summary.
6. **PRESERVE CREATIVE FREEDOM** — character voice, humor, opinions, tangents all remain; the constraints above are about scene physics, not tone.

Shared with `long_form`: `_ANTI_SELF_DESCRIPTION_BLOCK`,
`_ANTI_GENERIC_REGISTER_BLOCK`, `_CTA_POLICY_BLOCK`.

NOT shared: `_INVARIANTS_BLOCK` + `_NARRATIVE_SHAPES_BLOCK` (the
long-form menu promotes *"story → realization / mistake → lesson
/ experiment → outcome"* — the direct cause of temporal
compression per §11.6). `solo_scene` emits a scene-oriented menu:
*"moment → reaction / discovery → intent / observation →
resolve-or-defer / internal turn → decision"*.

**Backward compatibility:** standalone talking_head + long_form_ad
still use `target_shape="long_form"` (unchanged). `dialogue_scene`
still uses `target_shape="dialogue_scene"` (unchanged). Every
existing test remains green because the branch is only taken when
the primitive explicitly requests `target_shape="solo_scene"`.

### §14.9 Smallest coherent implementation slice (§I)

**Scope boundary — one coherent slice covers BOTH:**

- (a) SPA Episode-solo mode UX (hide standalone controls; show
  read-only story intent; auto-force `script` + `use_knowledge`
  on submit).
- (b) Backend `solo_scene` writing contract (new shape; wired
  through `_maybe_synthesize_script` → `synthesize_with_duration_gate`
  → `build_render_brief` → `WritingContract.for_shape`).

**Why they belong together:** hiding the fields without fixing
the contract still produces §11-style scene drift; fixing the
contract without hiding fields still exposes the wrong UX to the
operator. Shipping one without the other is a half-mode.

**Steps:**

1. `shell/character_os/writing_contract.py` — add `_solo_scene_contract()`; extend `WritingContract.for_shape` to handle `"solo_scene"`; bump `WRITING_CONTRACT_VERSION` to 5.
2. `shell/character_os/duration_contract.py` — accept optional `target_shape="long_form"` kwarg on `synthesize_with_duration_gate`; pass through to `build_render_brief`.
3. `shell/apps/compositions/primitives/avatar_speech.py` — inside `_maybe_synthesize_script`, decide `target_shape` once: `target_shape = "solo_scene" if composition.episode_id is not None and composition.template_kind == "talking_head" else <legacy>`. Pass to `synthesize_with_duration_gate` / `build_render_brief`.
4. `web/src/routes/recipes/$kind.tsx` — inside the recipe form, add an Episode-solo mode block: when `episode` is truthy AND `recipe.kind === "talking_head"` AND `episode.cast.length === 1`, render a read-only "Story intent" display of `episode.operator_topic` under the Episode chip; suppress `script` + `use_knowledge` fields from the render list AND from `isFieldVisible`; auto-force `script=episode.operator_topic` + `use_knowledge=true` in the submit `params` before `create.mutateAsync`.
5. Update §12.7 documentation to reflect story-mode UX.

**Not in scope:** standalone talking_head; `dialogue_scene`; any
new recipe; any new Episode field / model / migration; chronology;
`top_k`; relevance floor; reranker; manual memory picker; witness
semantics; canon boundary; auto-promotion of NarrativeMemory;
long_form_ad; cinematic_visual; any other recipe.

### §14.10 Files that would be modified (§H)

Source:

- `shell/character_os/writing_contract.py`
- `shell/character_os/duration_contract.py`
- `shell/apps/compositions/primitives/avatar_speech.py`
- `web/src/routes/recipes/$kind.tsx`

Tests (new / extended):

- `shell/apps/compositions/tests/test_talking_head_memory_lane.py` — add Episode-solo target_shape routing tests
- One new test module for `_solo_scene_contract()` (either extending an existing writing_contract test file or creating one)
- `web/src/routes/recipes/talking-head-episode-solo.test.tsx` — new focused SPA test file

Docs:

- `docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md` — new §15 recording the implementation slice + commit SHAs.

### §14.11 Tests required (§I)

Backend:

1. `WritingContract.for_shape("solo_scene", ...)` returns a string containing SINGLE ACTIVE CHARACTER + SINGLE PRESENT MOMENT + PLANS REMAIN PLANS + MEMORY AS BACKGROUND + END ON A MOMENT markers.
2. `WritingContract.for_shape("long_form", ...)` byte-identical to before (regression).
3. `_maybe_synthesize_script` routes to `target_shape="solo_scene"` when `composition.episode_id is not None` AND `template_kind=="talking_head"`; legacy shape otherwise.
4. Solo Episode + `use_knowledge=True` + duration set → `synthesize_with_duration_gate` called with `target_shape="solo_scene"`.
5. Standalone talking_head + `use_knowledge=True` → `synthesize_with_duration_gate` called with `target_shape="long_form"` (regression).
6. `WRITING_CONTRACT_VERSION` stamp on solo Episode Composition == 5.

Frontend:

7. talking_head recipe form with episode + cast.length==1 HIDES the Script/topic textarea AND the Use workspace knowledge checkbox.
8. talking_head recipe form with episode + cast.length==1 renders the read-only Story intent display containing `Episode.operator_topic`.
9. talking_head recipe form with episode + cast.length==1 submits with `script=episode.operator_topic` + `use_knowledge=true` silently forced.
10. Standalone `/recipes/talking_head` (no `?episode=`) renders the classic dual-mode form unchanged (regression).
11. Episode with `cast.length != 1` does not activate solo mode (belt-and-braces — Episode-detail CTA already gates on `cast.length==1`, but recipe-form guard is defense-in-depth).

Regression:

- Full `apps/compositions` + `apps/embeddings` + `apps/memory` + `apps/universe` suites remain green.
- Full SPA vitest suite remains green.

### §14.12 §13 correction (§J)

§13 correctly verified:

- Episode context reached the live form.
- Patch prefill reached the live form.
- Current Vite modules were loaded.
- Current Django serializer was loaded.

§13 wrongly assumed:

- That `Episode.operator_topic` should appear inside the standalone talking_head "Script or topic" textarea. **It should not** — Episode owns the story intent; Character OS owns the script.
- That the pre-existing standalone talking_head form fields were the correct destination for Episode-attached solo rendering. **They are not** — the standalone dual-mode UX is a content-creation contract, distinct from the Episode-attached story-creation contract.

**Distinction to apply going forward:**

- **TECHNICAL PREFILL EXPECTATION** — verifiable from source + tests + module inspection alone.
- **CORRECT PRODUCT CONTRACT** — requires operator clarification; not derivable from code.

**New rule (extends §13.1 methodology):**

> For creator-facing work, verify the PRODUCT CONTRACT with the
> operator BEFORE verifying prefill mechanics. Prefill working ≠
> product mode correct. §13's parity matrix should have included
> a row for *"authoring-mode contract matches Episode-solo
> intent"* — that row would have been NOT VERIFIED and would
> have surfaced this mismatch before Chris hit render-time
> confusion.

Useful finding now: Episode routing is working (levels 1-3
verified); Episode-specific authoring mode is not yet implemented
(level 4 blocked by product-contract mismatch, not by wire-shape
bug).

### §14.13 Operator stop disposition (§K)

**Chris SHOULD remain stopped before render.** Rendering the
current form (with any manually typed script) would either
(a) speak the Episode topic verbatim, or (b) apply the generic
`_long_form_contract` that produced §11 scene-drift. Neither is
the Episode-solo semantic. The §14 slice above should ship
before the next real solo render.

### §14.14 Commit checkpoint

Doc-only slice — no code changes in §14.

- §14 doc + evidence commit: `929199f` — `docs(session-269): §14 — Episode-solo is a STORY MODE, not standalone content`.
- Push: `394e373..929199f main -> main` (successful). Local main == origin/main == `929199f`. Working tree clean.
- Predecessors already on origin: `394e373` (§13 doc checkpoint), `3c0b00f` (§13 parity pass), `87c328f` (§12 doc checkpoint), `06ba772` (§12 slice), `91c9e3a` (§11 doc audit), `bbcc1f0` (§10 doc checkpoint), `765bb73` (§10 slice), `bc4d8ba` (§1-§9 doc).

---

**SESSION 269 IS NOT CLOSED.** §14 codifies the Episode-solo
STORY MODE product contract, corrects §13's product-mode
assumption, and specifies the smallest coherent implementation
slice. Chris + ChatGPT will review before authorizing §15
(implementation). Any further Episodes, promotions, or audit
findings should extend this document (add §15, §16…) rather than
start a new one.
