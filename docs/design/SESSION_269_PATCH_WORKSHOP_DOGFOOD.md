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
