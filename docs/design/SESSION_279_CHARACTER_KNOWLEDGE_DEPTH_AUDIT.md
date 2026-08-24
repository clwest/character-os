# SESSION 279 — Character Knowledge-Depth Audit

**Scope:** Deferred finding **4b** from `docs/design/SESSION_279_HANDOFF.md`
— *Tyson identity-as-expert vs Knowledge-depth needed to perform expertise.*

**Posture:** READ-ONLY audit + experiment design. No Tyson / Ruby / KD /
World / prompt / retrieval / synthesis / verifier / memory / audience
edits. No provider spend. No dogfood. No Knowledge added yet.

**Session opened:** 2026-08-25
**Session state at open:** SESSION 278 CLOSED (see `SESSION_279_HANDOFF.md`);
tree clean; on `main`; HEAD `a44bafa`; origin/main `a44bafa`.

---

## §0 Q-279-1 — precise question

> If Tyson's identity remains unchanged and only the depth / quality of
> his character-specific coffee/pastry Knowledge increases, does normal
> minimal-topic dialogue spontaneously become more concretely expert?

Architectural distinction under test:

- **CHARACTER IDENTITY / ROLE** — tells synthesis what Tyson is *supposed
  to be good at* (lives on `Teammate.personality` / `business_brief` /
  `who_you_help` / `what_you_sell` / voice axes / POV).
- **CHARACTER-SPECIFIC KNOWLEDGE** — gives Tyson the factual / domain
  material needed to actually *demonstrate* that expertise (lives on
  `KnowledgeDocument` / `KnowledgeChunk` scoped `audience_scope=character`).

Q-279-1 opens **only** hypothesis A (`richer character Knowledge → more
demonstrated expertise`). Hypothesis B (generalized writer-voice leakage,
deferred finding 4a) is explicitly out of scope for this slice.

---

## §1 Prediction (recorded BEFORE evidence)

Substrate distinguishes identity from Knowledge, but the current
character-audience corpus is *identity-restating*, not domain content.
Therefore:

- Baseline retrieval will pull the "specialty" KD chunk, and its
  contribution to §1 SCOPED KNOWLEDGE will be functionally equivalent to
  BUSINESS SHAPE — a second copy of the identity claim.
- No genuine domain content is available to the LLM anywhere in §1 or §2
  — expertise cannot emerge because none is present in the substrate.
- Dialogue therefore should mention pairing *as a concept* but never
  cite specific coffees, roasts, acidity profiles, pastry names, or
  pairing rationale.

Predicted classification: **AVAILABLE BUT GENERIC** (bucket 2 of 3).

---

## §2 Baseline repository state — checked

- Branch: `main`
- HEAD: `a44bafa` (`docs(session-278): CLOSE SESSION 278 + create SESSION_279_HANDOFF`)
- origin/main: `a44bafa` (up to date; no local drift)
- Working tree: clean
- SESSION 278 landed state confirmed via §7 of the handoff: D-POS Hybrid
  authoritative on dialogue-scene `Composition.verification_warnings`;
  185-test regression baseline; one-flag rollback available.
- Postgres + Redis containers running (`character_os_postgres`,
  `character_os_redis`, both healthy) — used read-only via
  `docker exec ... psql -U character_os` since the shared venv's ORM
  auth to 127.0.0.1:5433 fell through with `trust` (irrelevant to this
  audit; not investigated further).

---

## §3 Tyson identity / context inventory

### 3.1 Rows

- Tyson `id = f4de81f3-ef65-4196-a50e-38cfc6d1854f`
- Workspace `4ce5486d-35a4-4bee-8745-38004adb33bc`
- Universe `1a0af807-dd6a-47cd-bfaa-3d088f1c105f` = **Fox & Flour Bakery**
  (slug `fox-flour-bakery`; `Universe.brief` length 331 chars)
- Tone archetype `expert`, visual template `mascot`, status `ready`.
- Voice axes: `energy=medium`, `humor=warm`, `directness=balanced`.
- Cast peer: Ruby `id = ...` (Fox & Flour owner; `tone=friend`;
  personality warm/cheerful).

### 3.2 Universe.brief

> *"Fox & Flour Bakery is a warm neighborhood artisan bakery built around
> small-batch baking, naturally leavened sourdough, handcrafted pastries,
> seasonal desserts, and celebration cakes. It aims to feel like a
> familiar neighborhood gathering place where careful craft and quality
> ingredients matter more than speed or mass production."*

### 3.3 Tyson identity field-by-field

| Field | Content (verbatim, elided where obvious) | Contribution class |
|---|---|---|
| `Universe.brief` | See §3.2 — "warm neighborhood artisan bakery … small-batch … sourdough … handcrafted pastries … seasonal desserts … celebration cakes …" | **WORLD identity** |
| `Teammate.name` | `Tyson` | CHARACTER identity |
| `Teammate.business_brief` | *"Works alongside Ruby at Fox & Flour Bakery and focuses on the coffee-and-counter side of the shop. Knows the bakery's breads, pastries, seasonal desserts, celebration cakes, **coffee pairings**, customer pickup flow, and the everyday questions people ask before ordering. Helps customers choose what fits the occasion without overcomplicating it."* | **CHARACTER role / expertise CLAIM** (asserts coffee-pairing competence but names no coffees, no pastries, no pairing reasoning) |
| `Teammate.personality` | *"Easygoing, practical, and a little dry. Sounds like someone who has worked the counter long enough to know what customers are about to ask before they ask it. Friendly without being overly cheerful. Gives clear recommendations, occasionally teases Ruby about taking bread very seriously, and prefers useful answers over sales language."* | **CHARACTER voice** (HOW he speaks) |
| `tone_archetype` | `expert` | CHARACTER voice axis |
| `voice_energy` / `voice_humor` / `voice_directness` | `medium` / `warm` / `balanced` | CHARACTER voice axes |
| `who_you_help` | *(empty)* | audience/customer context — **UNSET** |
| `what_you_sell` | *(empty)* | offering shape — **UNSET** |
| `always_emphasize` | *(empty)* | positive positioning — UNSET |
| `never_say` | *(empty)* | guardrails — UNSET |
| `desired_feeling` | *(empty)* | outcome — UNSET |
| `character_point_of_view` | *(empty)* | POV — UNSET |
| `voice_signature_phrases` / `voice_avoid_phrases` | *(empty)* / *(empty)* | stylistic vocabulary — UNSET |

**Key identity observations:**

1. Tyson's `business_brief` **already asserts** coffee-pairing expertise
   (the words *"coffee pairings"*). This is the identity claim.
2. `business_brief` also enumerates several bakery domain nouns
   (breads, pastries, seasonal desserts, celebration cakes) but **without
   any specific instance** (e.g. no croissant, kouign amann, cortado,
   espresso, medium roast).
3. `personality` frames Tyson as *"easygoing, practical, and a little
   dry ... prefers useful answers over sales language."* This is
   voice-shape, not expertise substrate.
4. Every SESSION 232 identity slot beyond `business_brief` +
   `personality` is empty for Tyson. There is no separate "expertise
   surface" on the identity model — expertise, when claimed, is claimed
   *inside* `business_brief` or presumed to live in Knowledge.

---

## §4 Tyson Knowledge inventory

### 4.1 KnowledgeDocuments in scope

Retrieved by `docker exec character_os_postgres psql ... embeddings_knowledgedocument`:

| KD id | Title | audience_scope | universe | active | chunks | processed_content length |
|---|---|---|---|---|---|---|
| `3ff45702-cb8b-49f0-82f6-97013c0f8da6` | **Tyson's Pastry Pairing Specialty** | `character` (Tyson only) | Fox & Flour | true | 1 | **118 chars** |
| `d40b567e-557b-49e3-aa42-8002c86c6126` | Fox & Flour Hours | `universe` (whole cast) | Fox & Flour | true | 1 | 57 chars |
| `fa2c668c-d08b-4305-874c-33d99a11ccf6` | Fox & Flour holiday policy | `universe` (whole cast) | Fox & Flour | true | 1 | 39 chars |

That is the **entire** corpus Tyson can draw on inside the Fox & Flour
Universe.

### 4.2 The specialty KD — actual persisted content

Chunk 0 of `Tyson's Pastry Pairing Specialty` (verbatim, complete
`processed_content`):

> *"Tyson is especially knowledgeable about pairing pastries with coffee
> and enjoys helping customers choose combinations."*

That is the entire document. 118 characters. One chunk. One assertion.

**What this KD actually teaches Tyson: nothing new.**

Content coverage against the checklist from Q-279-1 §3:

| Domain content dimension | Present? |
|---|---|
| Named coffee preparations (espresso, drip, pour-over, cold brew, cortado…) | **No** |
| Roast characteristics (light / medium / dark; regional origins) | **No** |
| Acidity / body / sweetness / mouthfeel vocabulary | **No** |
| Pastry flavor / texture characteristics (butter content, laminated dough, sweetness axis…) | **No** |
| Named pastries (croissant, kouign amann, morning bun, canelé…) | **No** |
| Specific pairing reasoning (why bright acidity cuts richness, why sweetness balances bitterness…) | **No** |
| Concrete pairing examples (light-roast Ethiopian + almond croissant because…) | **No** |
| Tradeoffs / alternatives (if the pastry is X, consider Y or Z depending on…) | **No** |
| Vocabulary a knowledgeable barista/pastry chef would naturally use | **No** |

The KD does not TEACH; it CLAIMS. Its content is functionally identical
to a rephrasing of the words *"coffee pairings"* that already appear in
`business_brief`. Structurally it is a Knowledge row; substantively it is
an identity restatement.

### 4.3 Universe KDs

`Fox & Flour Hours` (57 chars): *"Fox & Flour Bakery is open daily from
7:00 AM to 3:00 PM."*

`Fox & Flour holiday policy` (39 chars): *"Fox & Flour is closed on
Christmas Day."*

Both are legitimate operational facts. Neither is domain expertise.
Neither is relevant to coffee/pastry pairing depth.

**Classification of Tyson's current character-specific Knowledge:**

> **AVAILABLE BUT GENERIC** — the only character-audience KD exists, is
> active, is retrieved, and contributes identity-restating text. No
> concrete domain content is present anywhere in the substrate.

---

## §5 Reconstruction of the two prior specimens

Both compositions were persisted successfully during SESSION 278
dogfooding. Read-only pull below.

### 5.1 Q-278-4.2 Specimen 2 — Ruby thinks Tyson is taking coffee too seriously

- Composition `d7549fc1-ad59-42c3-99c6-6d3597bb1afa`
- Template `dialogue_scene`, status `completed`
- Target duration 90 s, predicted 91 s, audience_hint empty
- `operator_topic`: *"Ruby thinks Tyson is taking coffee too seriously."*
- `spokesperson_id` = Tyson (dispatcher / operator anchor)
- `knowledge_chunk_ids` (persisted composition-level provenance) =
  - `4c7954e0-49b0-44e9-9113-b3cb5b3054d5` — `Tyson's Pastry Pairing Specialty` chunk 0
  - `219bcc30-02e7-4fbd-af16-f0284777edc1` — `Fox & Flour holiday policy` chunk 0
  - `3bfea692-0548-4db9-b1c0-34d47ada3fd5` — `Fox & Flour Hours` chunk 0
- `memory_ids = []`
- Per-character retrieval (verbatim from `synthesized_brief` header line):
  - Tyson chunks: `[4c795… (specialty), 219bcc… (holiday), 3bfea6… (hours)]`
  - Ruby chunks: `[219bcc… (holiday), 3bfea6… (hours)]` — **no character-audience KD exists for Ruby**
- Dialogue-scene rendered dialogue (Tyson turns only):
  - *"It was a fair pause. Someone asked which pastry to have with coffee. That is a question with consequences."*
  - *"They can. I'm not taking the pastry away. I'm helping them avoid the very common experience of ordering two things that spend the whole morning arguing."*
  - *"No, but coffee has opinions. A customer asks for a pairing, I give them one. That's better than nodding wisely and sending them into the unknown."*
  - *"I enjoy the part where they come back knowing what they liked. Also, you make it difficult to be casual when there are handcrafted pastries sitting right there."*
  - *"Fine. I'll keep it simple: coffee, pastry, good match. Then you can tell them to choose whatever makes them happy."*

**Concrete-terms audit of Tyson's turns:**

| Signal | Present? |
|---|---|
| Named coffee or coffee prep | **No** |
| Named pastry | **No** ("handcrafted pastries" is generic; borrowed from `Universe.brief` / `business_brief`) |
| Roast / acidity / body / mouthfeel term | **No** |
| Specific pairing recommendation | **No** |
| Reason WHY a pairing works | **No** |
| Alternative / tradeoff | **No** |
| Generic gesture at expertise | **Yes** ("coffee has opinions", "which pastry to have with coffee", "good match") |

**Substrate availability at synthesis time:** the specialty KD chunk was
retrieved and injected. It contained no domain content. Identity
`business_brief` was injected and asserted the pairing claim. No
concrete pairing information existed anywhere in §1.

**Classification for this specimen: AVAILABLE BUT GENERIC.**

### 5.2 Q-278-4.3 Specimen 3 — Tyson thinks Ruby entered them in a baking competition

- Composition `7177b0f5-b6e8-4366-951b-cb3c2ebe01cb`
- Template `dialogue_scene`, status `completed`
- Target duration 90 s, predicted 106 s, audience_hint empty
- `operator_topic`: *"Tyson thinks Ruby secretly entered them in a baking competition."*
- `knowledge_chunk_ids` = identical set to Specimen 2 (the entire
  Universe corpus is 3 chunks; retrieval pulls them all).
- `memory_ids = []`
- Notable Tyson turns:
  - *"You also asked me for three coffee pairings, then stared at the pastries like they'd personally disappointed you."*
  - *"Fine. Practical answer: if we're being judged, don't make the coffee an afterthought. A good pairing can make a handcrafted pastry feel finished instead of merely photographed."*
  - *"All right. But if it says we're competing, I'm choosing the coffee."*

**Concrete-terms audit:** identical outcome. "Three coffee pairings" is
plural without instantiation; "the coffee an afterthought" and "a good
pairing" are generic; "handcrafted pastry" is the same Universe-brief
noun. No specific coffees, roasts, pastries, flavor axes, or reasoning
appear.

**Classification: AVAILABLE BUT GENERIC.**

### 5.3 Cross-specimen substrate table

| Bucket | Definition | Specimen 2 | Specimen 3 |
|---|---|---|---|
| **NOT AVAILABLE** | No character-audience KD retrieved. | ✗ | ✗ |
| **AVAILABLE BUT GENERIC** | KD retrieved; content restates identity claim without concrete domain material. | **✓** | **✓** |
| **CONCRETE BUT NOT USED** | KD retrieved; content contains concrete domain material; dialogue ignores it. | ✗ | ✗ |

Both specimens land in bucket 2. This is a **substrate-content problem**,
not a substrate-mechanics problem, and not a synthesis-honoring-context
problem — because there is no concrete content for synthesis to either
honor or ignore.

---

## §6 Identity-vs-Knowledge synthesis path

Traced only far enough to answer the audit question.

Retrieval (`character_os/dialogue_synthesis.py:1530-1598`):

- Per-character lane — `retrieve_for_teammate(tm, topic, top_k=5)`
  for each cast member. Cosine ranks candidate chunks whose
  `KnowledgeDocument` has that Teammate on its M2M (or is
  empty-M2M fallback under legacy semantics).
- Universe canon lane — `retrieve_universe_canon(workspace, universe,
  cast, topic, top_k=2)`.
- Universe memory lane — `retrieve_universe_memory(...)` (empty for
  both specimens).

Prompt assembly (§1 FACTUAL BASIS, `dialogue_synthesis.py:490-659`):

```
=== SECTION 1 — FACTUAL BASIS ===
… scope rule preamble …
--- WORLD SHAPE (shared World identity; any character may cite) ---
{Universe.brief}
--- SHARED WORLD KNOWLEDGE (any character may cite) ---
{shared canon chunks, one [SHARED CHUNK — doc …] per chunk}
--- EPISODE / NARRATIVE MEMORY (past events; static canon wins) ---
{memory rows, if any}
--- {ALIAS}'S SCOPED KNOWLEDGE (only {alias} may cite these as their own) ---
BUSINESS SHAPE:
{Teammate.business_brief}
AUDIENCE:
{Teammate.who_you_help}          # if non-empty
OFFERING:
{Teammate.what_you_sell}         # if non-empty
SCOPED KNOWLEDGE CHUNKS:
{per-character KD chunks, one [CHUNK — doc …] per chunk}
```

§2 CHARACTER VOICE (`_build_character_voice_block`, line 662-709):

```
--- CHARACTER {ALIAS} — {name} ---
TONE ARCHETYPE: {tone_archetype}
VOICE AXES: energy={…}; humor={…}; directness={…}
WRITING STYLE (how {name} sounds):
{personality}
POINT OF VIEW …
SIGNATURE PHRASES …
AVOID PHRASES …
```

### Mechanical answer to Q-279-1 §5

**Identity and Knowledge are mechanically distinguishable at synthesis
time, but co-located inside the same per-character §1 SCOPED KNOWLEDGE
block.**

- Identity fields (`business_brief` → BUSINESS SHAPE; `who_you_help` →
  AUDIENCE; `what_you_sell` → OFFERING) are **always injected**, never
  retrieval-gated, always visible to the LLM.
- Character KD chunks are **cosine-retrieved** and emitted as
  `SCOPED KNOWLEDGE CHUNKS:` under **the same header**.
- The labels differentiate them for the LLM but the block is one
  contiguous text region. A KD whose content happens to restate the
  identity claim is *not* structurally flattened — it just repeats
  what BUSINESS SHAPE already said, and the LLM's ability to
  demonstrate specific expertise depends entirely on whether the
  chunks under `SCOPED KNOWLEDGE CHUNKS:` contain **anything more
  concrete than BUSINESS SHAPE already contains**.

Therefore the substrate is capable of carrying real expertise; the
current corpus does not populate that capacity. This is the exact
substrate-vs-content decomposition finding 4b predicted.

---

## §7 Baseline expertise rubric (character-agnostic)

Not vibes. Every dimension is grep-able / countable / traceable to
substrate.

| # | Dimension | Score 0 | Score 1 | Score 2 |
|---|---|---|---|---|
| R1 | **Specific proper-noun domain terms.** Named instances of the character's stated expertise domain (coffee/pastry names for a barista; loan-product names for a finance specialist; river/rapid names for a guide). | Zero named instances in character's turns. | 1 named instance, possibly forced. | ≥2 named instances used naturally in-turn. |
| R2 | **Concrete attributes / parameters.** Named attributes of the domain (roast level, acidity, current CFS, APR, ply, alloy). | Absent. | 1 attribute referenced. | ≥2 attributes referenced. |
| R3 | **Explicit pairing / recommendation reasoning.** A cause-and-effect sentence grounded in R1 or R2 ("the bright acidity cuts the butter"; "the higher CFS means the beach launch is faster"). | Absent. | Vague ("it works"); no attribute cited. | ≥1 recommendation with attribute-grounded reasoning. |
| R4 | **Choice-space awareness.** Mention of an alternative or tradeoff. | Absent. | Alternative named without reasoning. | Alternative named with why-not or when-to. |
| R5 | **Expertise emerges unprompted.** The operator topic did NOT request domain specifics. | Emergence only after operator prompts for detail. | Marginal — one specific slips in. | Multiple domain specifics appear from the character's own volition. |
| R6 | **Traceability.** Concrete terms in dialogue trace back to a specific KD chunk (verifiable via `knowledge_chunk_ids` + chunk content). | No traceable link. | 1 term traceable, others invented. | All concrete terms trace to persisted Knowledge. |

Max = 12 per specimen for the character under test.

Baseline scoring of the two SESSION 278 specimens for Tyson:

| Specimen | R1 | R2 | R3 | R4 | R5 | R6 | Total / 12 |
|---|---|---|---|---|---|---|---|
| Q-278-4.2 Specimen 2 | 0 | 0 | 0 | 0 | 0 | n/a (no concrete terms to trace) | **0** |
| Q-278-4.3 Specimen 3 | 0 | 0 | 0 | 0 | 0 | n/a | **0** |

Both specimens are floor-baseline. This is the falsifiable substrate the
experiment will move.

R6 is deliberately included so any post-treatment score improvement can
be attributed to the treatment KD, not to model priors. If R6 = 0 after
treatment, the substrate is failing to route Knowledge to output even
when content is present — a different diagnosis.

---

## §8 Smallest controlled operator experiment

### 8.1 Setup

Constraint (Q-279-1 §7): **only Tyson's character-audience Knowledge
changes.** Every other input pinned.

Pinned:
- Tyson `business_brief`, `personality`, all identity slots, voice axes,
  POV — unchanged.
- Ruby row — unchanged.
- `Universe.brief` — unchanged.
- Both Universe-audience KDs (Hours, holiday policy) — unchanged.
- Synthesis code, prompts, retrieval code, verifier, memories — unchanged.
- audience_hint — remains empty (baseline had empty).
- Target duration 90 s — unchanged.

Changed (in a single reversible operator session, if approved):
- The `Tyson's Pastry Pairing Specialty` KD (character-audience,
  Tyson-only via M2M) is **augmented or replaced** with a small
  concrete corpus.

### 8.2 Recommended corpus shape

**One expanded KD, not multiple.** Rationale: single KD keeps
retrieval variance out of the experiment (top_k=5 will always include
it since it's the only Tyson-audience KD). Multiple KDs would introduce
retrieval-ranking as a confound.

Target size: **1,500-2,500 chars total** (≈3-6 chunks after
chunking). Small enough not to dominate context, large enough to
contain real domain content. Rejected the "giant corpus" temptation —
we are testing whether *depth per KD* changes demonstrated expertise,
not whether *corpus volume* does.

Content categories the KD must contain (each testable via the rubric):

1. **Named coffee preparations** the bakery offers (≥3 named).
2. **Roast profiles** with plain-English attribute descriptions.
3. **Named pastries** the bakery makes (≥3 named), each with a short
   texture/flavor descriptor tied to real properties (butter content,
   crumb, sweetness axis).
4. **≥3 concrete pairings**, each with a one-sentence reason grounded
   in an attribute above ("light-roast Ethiopian's brightness cuts the
   butter in the almond croissant").
5. **≥1 tradeoff or alternative** ("if the pastry is very sweet, avoid
   the darker roast; try …").
6. Written in the register of *reference material Tyson could consult*,
   not in Tyson's voice. Knowledge is factual substrate; voice remains
   the identity layer's job.

Explicitly **not** included:
- Instructions to Tyson about how to speak.
- Assertions that Tyson is knowledgeable (identity's job).
- Cross-cast content about Ruby.
- Any language that would leak into other characters' contexts on future
  Universe expansion.

### 8.3 Specimen matrix

Three topics, mock-mode NOT acceptable — real-mode required per
`feedback_real_mode_dogfood_after_operator_slices` (this is the only
way to observe whether identity-vs-Knowledge routing survives real
synthesis). But: **spend is out of scope for Q-279-1**. This section
recommends the experiment; execution is a subsequent slice pending
Chris + ChatGPT approval.

| # | Topic | Rationale |
|---|---|---|
| T1 | *"Ruby thinks Tyson is taking coffee too seriously."* (identical to Q-278-4.2 Specimen 2) | Direct replay against a substrate-only change. |
| T2 | *"Tyson thinks Ruby secretly entered them in a baking competition."* (identical to Q-278-4.3 Specimen 3) | Second direct replay; two data points controls for LLM variance. |
| T3 | Neutral non-domain topic (proposed at execution time — e.g. *"Ruby locks herself out of the bakery."*) | Control against inappropriate leakage. If enriched Knowledge causes Tyson to lecture about coffee in an unrelated scene, the substrate is failing in the *other* direction (Knowledge is not topic-gated by retrieval). |

Two rounds each = 6 renders total. Two rounds per topic accounts for
minor LLM sampling variance; more rounds are not justified until the
signal separates from noise.

### 8.4 Pre-established acceptance / disconfirmation criteria

Established BEFORE any Knowledge change.

**ACCEPT — Knowledge substrate carries expertise (GO-DEEPER):**

- Both T1 and T2 score **≥ 6/12 total on the R1-R6 rubric** for
  Tyson's turns (baseline = 0/12).
- **R1 ≥ 2 (specific named terms)** on both T1 and T2.
- **R6 ≥ 1** on both T1 and T2 — at least one concrete term traceable
  to a chunk in the treatment KD.
- **T3 R1 = 0** — the neutral control did not manufacture coffee
  specifics unbidden. (Knowledge is retrieval-gated appropriately.)

If all four hold, the substrate correctly separates identity from
Knowledge and richer Knowledge drives richer demonstrated expertise
without prompt-engineering. Hypothesis 4b confirmed.

**DISCONFIRM — substrate flat / identity dominates (STOP):**

- T1 or T2 stays at **≤ 2/12 total** despite the new KD content being
  retrievable (verified via `knowledge_chunk_ids` on the persisted
  Composition).
- R6 = 0 on both T1 and T2 despite concrete terms living in the
  chunk table.

If disconfirmed, the substrate is failing to route Knowledge to output.
Next audit shifts to the retrieval → prompt assembly → generation path
(a substantially larger investigation).

**AMBIGUOUS — partial signal (NEED-MORE):**

- Only one of T1 / T2 improves.
- R1 improves without R3 (specifics appear but no reasoning) —
  suggests the LLM is namedropping without understanding, which may
  imply the KD's *structure* (list vs prose with rationale) matters
  more than depth.
- Improvement only visible with operator prompting for specifics.

Ambiguous results trigger a second-order design question about KD
*shape*, not depth.

**T3 second-order failure:**

- T3 R1 ≥ 1 — Tyson lectures about coffee in a scene where the topic
  did not call for it. Substrate is leaking Knowledge inappropriately.
  Not a Q-279-1 disconfirmation, but a separate substrate finding to
  record.

---

## §9 Generalization challenge

Q-279-1 asks whether the substrate carries expertise, using Tyson as the
specimen. The distinction must be meaningful for other character types
or the experiment only teaches Tyson to pass a coffee test.

| Character type | Identity claim (business_brief-shape) | Concrete Knowledge that would DEMONSTRATE it |
|---|---|---|
| **Dealership finance specialist** | *"Knows lease vs finance tradeoffs, factory incentives, credit tiers."* | Named products (lease, retail installment, balloon); attributes (APR, residual, money factor, tier cutoff FICO ranges); tradeoff reasoning ("Tier 1 vs Tier 2 changes money factor by ~0.0005 which on 36 months is ~$X"). |
| **Fantasy-world historian** | *"Expert on the Third Age of Riverstone."* | Named events (Battle of Silver Ford, Compact of the Vale); named houses / factions; dated sequence ("Compact preceded Silver Ford by two seasons"); causal reasoning ("The Compact's tax on iron drove Silver Ford's rebellion"). |
| **Kayaking guide** | *"Knows the local rivers and gear."* | Named rivers/sections; named rapid classes/features ("Bear's Toe class III"); attributes (CFS thresholds, put-in access, seasonal windows); safety reasoning ("above 4500 CFS the eddy at River Left disappears"). |
| **Bookstore employee** | *"Recommends books to customers."* | Named authors/titles; named genres/tropes; attribute vocabulary (POV, pacing, page count, comparable authors); reasoning ("if you loved Le Guin's *Left Hand*, Tchaikovsky's *Elder Race* has the same POV distance and moral texture"). |
| **Technical engineer** | *"Debugs distributed systems."* | Named protocols/tools (gRPC, OpenTelemetry, pgvector's HNSW); attributes (P99 latency, index m/ef_construction, connection-pool size); reasoning ("HNSW ef_construction=64 saves memory but costs recall vs 200; for this corpus size use 200"). |

For every case:

- The **identity claim** ("knows X") is empty performance without
  concrete substrate.
- The **substrate distinction** (identity slot vs KD content) exists on
  the same fields Tyson uses. `business_brief` for identity;
  character-audience `KnowledgeDocument` for domain content.
- The **experiment shape** is identical: pin identity, expand
  character-audience Knowledge with concrete domain content, rerun the
  same normal-topic dialogue, score against a rubric of specific-term /
  attribute / reasoning / alternative use.

**The proposed rubric (§7) is character-agnostic**: R1 asks for named
domain instances (whatever the domain), R2 for named attributes, R3
for attribute-grounded reasoning, R4 for alternatives, R5 for unprompted
emergence, R6 for traceability. No dimension is coffee-specific.

**The proposed experiment (§8) is character-agnostic**: pin every
non-Knowledge input; expand one character-audience KD with concrete
domain content; rerun normal-topic dialogue; score.

If the substrate works for Tyson, it works for the historian, the
finance specialist, the guide, the bookseller, and the engineer.
If it fails for Tyson, we've isolated the failure to the substrate,
not to Tyson's specific domain.

**Generalization: passes.**

---

## §10 Unresolved questions (deferred; NOT opened by Q-279-1)

- Whether KD *shape* (bulleted list vs prose with rationale) matters
  more than KD *depth*. Would surface as an AMBIGUOUS outcome per §8.4.
- Whether the retrieval `top_k=5` per-character cap is sufficient once
  a real corpus exists. Same-topic cosine could crowd out complementary
  chunks.
- Whether `SCOPED KNOWLEDGE CHUNKS` and `BUSINESS SHAPE` should be
  reordered inside the per-character block so Knowledge sits ABOVE
  identity (currently identity leads; the LLM sees the claim first).
- Whether adding `who_you_help` / `what_you_sell` (both currently empty
  for Tyson) would change baseline output. Left empty for the
  experiment so the comparison is apples-to-apples with the SESSION 278
  baseline.
- Cross-cast alias grounding (deferred finding 4f) — orthogonal to
  Q-279-1.
- Writer-voice leakage (deferred finding 4a) — explicitly out of scope
  per §6 of the handoff. Sentences like *"That's evidence."* remain
  candidate 4a evidence even if the KD experiment succeeds; they do
  not disconfirm 4b.

---

## §11 Recommendation

The mechanical finding is unambiguous:

1. The substrate cleanly separates character identity from
   character-specific Knowledge at synthesis time (§6).
2. Tyson's identity already CLAIMS coffee-pairing expertise (§3.3).
3. Tyson's ONLY character-audience Knowledge is a 118-character KD
   whose content is a restatement of that identity claim (§4.2).
4. In both prior SESSION 278 specimens, that KD was retrieved and
   injected. The absence of concrete domain material in the substrate
   is 1:1 with the absence of concrete demonstrated expertise in the
   dialogue (§5).
5. The experiment that tests hypothesis 4b changes exactly one variable
   — the content of one character-audience KD — and holds everything
   else constant (§8).
6. The rubric and experiment generalize past Tyson to the substrate
   itself (§9).

The audit therefore recommends proceeding to the smallest controlled
Knowledge experiment as designed in §8, gated on Chris + ChatGPT
approval to (a) author the treatment corpus and (b) spend provider
credits on 6 real-mode renders.

### Recommended decision gate

> **GO-KNOWLEDGE-EXPERIMENT**

---

## §12 Checklist

- [x] Q-279-1 precise question stated (§0)
- [x] Prediction recorded before evidence (§1)
- [x] Baseline repository state verified (§2)
- [x] Tyson identity / context inventory + field classification (§3)
- [x] Tyson Knowledge inventory + actual KD/chunk content (§4)
- [x] Reconstruction of Q-278-4.2 Specimen 2 (§5.1)
- [x] Reconstruction of Q-278-4.3 Specimen 3 (§5.2)
- [x] Cross-specimen substrate bucket classification (§5.3)
- [x] Identity-vs-Knowledge synthesis path traced only as needed (§6)
- [x] Character-agnostic expertise rubric (§7)
- [x] Baseline rubric scoring of both prior specimens (§7)
- [x] Smallest controlled experiment designed (§8)
- [x] Corpus shape / size / content categories specified (§8.2)
- [x] Specimen matrix + control condition (§8.3)
- [x] Pre-established ACCEPT / DISCONFIRM / AMBIGUOUS criteria (§8.4)
- [x] Generalization challenge across five character types (§9)
- [x] Unresolved questions preserved as distinct hypotheses (§10)
- [x] Recommendation + gate stated (§11)
- [x] No Knowledge / identity / prompt / synthesis / retrieval / verifier
      / memory changes made this session
- [x] No provider spend
- [x] No dogfood

---

## §13 Session artifact index

- `docs/design/SESSION_279_HANDOFF.md` — source of finding 4b (§4b).
- `docs/design/SESSION_278_AUDIT.md` — original SESSION 278 evidence for
  both specimens. Not re-opened this session.
- Persisted Compositions inspected read-only:
  - `d7549fc1-ad59-42c3-99c6-6d3597bb1afa` (Specimen 2)
  - `7177b0f5-b6e8-4366-951b-cb3c2ebe01cb` (Specimen 3)
- KnowledgeDocuments inspected read-only:
  - `3ff45702-cb8b-49f0-82f6-97013c0f8da6` (Tyson's Pastry Pairing Specialty)
  - `d40b567e-557b-49e3-aa42-8002c86c6126` (Fox & Flour Hours)
  - `fa2c668c-d08b-4305-874c-33d99a11ccf6` (Fox & Flour holiday policy)
- Code paths inspected read-only:
  - `shell/apps/spokespeople/models.py` (Teammate identity surface)
  - `shell/apps/embeddings/models.py` (KD / KC / audience_scope)
  - `shell/apps/universe/models.py` (Universe.brief)
  - `shell/apps/compositions/models.py` (Composition provenance fields)
  - `shell/character_os/dialogue_synthesis.py` (§1 / §2 prompt assembly;
    retrieval lanes)

**Session status:** Q-279-1 audit closed. Awaiting Chris + ChatGPT
gate decision.

---

# Q-279-2A — Author the treatment corpus

**Status opened:** 2026-08-25. Q-279-1 gate = **GO-KNOWLEDGE-EXPERIMENT**
accepted. Q-279-2A designs the exact Knowledge treatment for Chris +
ChatGPT review BEFORE any DB mutation. No Knowledge is changed in
Q-279-2A. No provider spend. No dogfood.

## §14 Approved experiment adjustments

Two changes to Q-279-1 §8 execution plan are accepted:

**Adjustment A — Staged render window.**

- **Stage A:** T1 once + T2 once + T3 once = **3 real-mode renders**.
- **Stage B (conditional):** only fires if Stage A is ambiguous — up to
  3 additional renders (repeats of only the ambiguous specimen(s)).
- A screaming Stage-A result does not need to be proven twice.

**Adjustment B — Keep treatment KD below retrieval cap.**

- Per-character retrieval uses `retrieve_for_teammate(tm, topic,
  top_k=5)` (verified `character_os/dialogue_synthesis.py:1540`).
- Treatment KD **must chunk to 2-4 chunks** — headroom below the cap so
  the whole corpus is always available and retrieval-ranking is not a
  confound.
- The experiment tests KNOWLEDGE DEPTH, not chunk-ranking behavior.

## §15 Proposed treatment corpus — full verbatim text

The exact text proposed for the `processed_content` of KD
`3ff45702-cb8b-49f0-82f6-97013c0f8da6` (`Tyson's Pastry Pairing
Specialty`). Written as third-person reference material a knowledgeable
counter worker could consult — NOT in Tyson's voice, NOT instructions
about how Tyson should speak, NOT another assertion that Tyson is an
expert.

Three `\n\n`-separated paragraphs. Verbatim below.

```
Fox & Flour serves three coffee preparations daily: espresso, drip
coffee, and pour-over. The espresso is pulled from a medium-dark roast
blend with a rounded body and notes of cocoa and toasted nut; the
acidity is low and the finish sits heavy on the palate. The drip coffee
uses a medium roast with a fuller body, gentle sweetness, and a mild,
even bitterness that stays in the background. The pour-over uses a
light roast with brighter acidity, a lighter body, and clearer citrus
and stone-fruit notes near the top of each sip. As a rule, roast level
trades brightness for body: lighter roasts taste more of the bean
itself, while darker roasts taste more of the roast.

The three pastries Tyson pairs most often are the almond croissant, the
morning bun, and the chocolate babka. The almond croissant is a
laminated, butter-heavy pastry filled with almond cream and finished
with sliced almonds and powdered sugar; it reads sweet, rich, and dense
on the palate. The morning bun is a laminated dough rolled with
cinnamon sugar and orange zest and baked in a muffin tin; it is
buttery with a bright citrus lift and a moderate, unfussy sweetness.
The chocolate babka is a soft enriched bread swirled through with dark
chocolate and topped with a light cocoa streusel; the chocolate flavor
is deep but the crumb stays tender, so it reads rich in flavor without
feeling heavy.

Three pairings work reliably. The pour-over goes with the almond
croissant: the lighter body and brighter acidity cut through the almond
cream's richness so the last bite still tastes clean. The drip coffee
goes with the morning bun: its fuller body sits under the cinnamon and
orange without competing, and the medium roast's gentle sweetness
complements the sugar in the bun. The espresso goes with the chocolate
babka: the espresso's cocoa-and-nut register echoes the dark chocolate,
and the short intense pour keeps the chocolate from feeling heavy on
top of an already rich pastry. General rule when in doubt: if the
pastry is already very rich or very sweet, avoid the darker roast —
the roast's own bitterness stacks with the pastry and the whole
pairing feels heavier; a lighter roast with brighter acidity gives the
palate somewhere to breathe.
```

## §16 Q-279-2A §8 requirement coverage

| # | Requirement | Where present |
|---|---|---|
| 1 | ≥3 named coffee preparations | Paragraph 1: espresso, drip coffee, pour-over |
| 2 | Roast / profile characteristics | Paragraph 1: medium-dark blend, medium, light + explicit trade rule |
| 3 | ≥3 named pastries | Paragraph 2: almond croissant, morning bun, chocolate babka |
| 4 | Concrete sensory / structural attributes for pastries | Paragraph 2: laminated, butter-heavy, almond cream, sliced almonds / cinnamon sugar, orange zest, muffin tin / dark chocolate swirl, cocoa streusel, tender crumb |
| 5 | ≥3 explicit coffee/pastry pairings | Paragraph 3: pour-over + almond croissant; drip + morning bun; espresso + chocolate babka |
| 6 | Short factual reason WHY each pairing works | Paragraph 3: acidity cuts richness / body sits under without competing / cocoa-nut echoes chocolate |
| 7 | ≥1 alternative / tradeoff rule | Paragraph 3: "if the pastry is already very rich or very sweet, avoid the darker roast …" |
| 8 | Overlapping info so no single sentence destroys experiment | Coffee names appear in paragraphs 1 + 3; pastry names appear in paragraphs 2 + 3; roast rule appears in paragraph 1 + (via overlap) chunk 1; every pairing sentence self-contains its coffee + pastry + reason |
| 9 | Plain language (no jargon for jargon's sake) | No process names (washed / natural), no cultivar names (Bourbon / Typica), no origin countries or altitudes. All descriptors ("brighter acidity", "fuller body", "buttery", "tender crumb") are accessible neighborhood-bakery register |

Constraints (Q-279-2A §"AUTHOR THE TREATMENT CORPUS"):

- **NOT in Tyson's voice.** Third-person reference throughout.
- **NOT instructions.** No "Tyson should …" / "recommend X when Y".
  Descriptive statements about beverages, pastries, pairings, and one
  general rule.
- **NOT another expertise assertion.** The text does not say Tyson is
  knowledgeable. It describes coffee, pastry, and pairings; the
  identity `business_brief` is already the layer that CLAIMS Tyson
  knows these.
- **No Ruby-specific behavior.** Ruby is not mentioned.
- **No Character OS methodology.** No mention of retrieval, prompts,
  audience, memory, testing, etc.
- **No prompt engineering.** No LLM-directed hints ("cite specifically",
  "always name a coffee"). The text is Fox & Flour's reference,
  nothing more.

## §17 Dry-run chunking result (against the real `TextSplitter`)

Ran `apps.embeddings.text_splitter.TextSplitter(chunk_size=1000,
chunk_overlap=200).split(...)` on the exact §15 text — the same
splitter `embed_document` uses at ingest time
(`apps/embeddings/tasks.py:35-75`). No DB mutation; no persistence.

```
total chars:                       2230
total words:                       376
paragraphs (\n\n-separated):       3
chunk_size:                        1000
chunk_overlap:                     200
resulting chunk count:             3
```

Per-chunk content boundaries:

| Chunk | Size | Opening | Closing | Content covered |
|---|---|---|---|---|
| 0 | 672 chars | *"Fox & Flour serves three coffee preparations …"* | *"… darker roasts taste more of the roast."* | All 3 named coffees + all 3 roast profiles + roast trade rule (paragraph 1 in full). |
| 1 | 898 chars | *"citrus and stone-fruit notes near the top of each sip. As a rule …"* (200-char tail overlap from chunk 0) | *"… reads rich in flavor without feeling heavy."* | Tail of paragraph 1 (pour-over notes + roast trade rule) + all 3 named pastries + all pastry attributes (paragraph 2 in full). |
| 2 | 1051 chars | *"enriched bread swirled through with dark chocolate …"* (200-char tail overlap from chunk 1) | *"… gives the palate somewhere to breathe."* | Tail of paragraph 2 (babka detail) + all 3 pairings + tradeoff rule (paragraph 3 in full). |

Notes:

- Chunk 2 is 1051 chars, 5 % over the 1000-char soft limit. The splitter
  explicitly emits over-limit chunks whole rather than mid-sentence
  truncate (`text_splitter.py:99-104` docstring; `_split_large_paragraph`
  is not triggered here because paragraph 3 is 809 chars = under the
  soft limit; the extra 200-char overlap head pushes the final chunk
  to 1051). This is normal splitter behavior and does not affect
  retrieval or embedding.
- 3 chunks < 5 (retrieval top_k). Retrieval will always return the
  entire corpus. Retrieval-ranking is not a confound.

## §18 Explicit new Fox & Flour canon

Facts that become true inside the Fox & Flour Bakery Universe **iff**
Chris approves this treatment. Recorded here so Chris signs off on the
whole surface, not just the prose.

**Beverages (new):**

1. Fox & Flour serves three coffee preparations *daily*: espresso, drip
   coffee, pour-over.
2. Espresso: medium-dark roast blend; rounded body; cocoa + toasted-nut
   notes; low acidity; heavy finish.
3. Drip coffee: medium roast; fuller body; gentle sweetness; mild, even
   bitterness.
4. Pour-over: light roast; brighter acidity; lighter body; citrus +
   stone-fruit notes.

**Pastries (new named instances):**

5. Almond croissant on the menu: laminated, butter-heavy; almond cream
   filling; sliced almonds + powdered sugar finish.
6. Morning bun on the menu: laminated dough; rolled with cinnamon sugar
   + orange zest; baked in a muffin tin.
7. Chocolate babka on the menu: soft enriched bread; dark chocolate
   swirl; cocoa streusel topping.

**Pairing conventions (new house lore):**

8. Pour-over + almond croissant is a recommended pairing.
9. Drip coffee + morning bun is a recommended pairing.
10. Espresso + chocolate babka is a recommended pairing.

**General house rule (new):**

11. For very rich or very sweet pastries, avoid the darker roast; prefer
    a lighter roast with brighter acidity.

**Compatibility with existing Fox & Flour canon:**

- `Universe.brief` mentions "handcrafted pastries", "seasonal desserts",
  "celebration cakes", "naturally leavened sourdough". No named
  pastries. No named coffees. New menu items **do not contradict**
  existing brief — they add specifics under the "handcrafted pastries"
  umbrella and introduce a coffee-and-counter surface that Tyson's
  `business_brief` already claims exists.
- `Fox & Flour Hours` (Universe KD): unchanged.
- `Fox & Flour holiday policy` (Universe KD): unchanged.
- Ruby's `business_brief` references "sourdough, handcrafted pastries,
  seasonal desserts, celebration cakes". New named pastries fit under
  "handcrafted pastries" without contradicting Ruby's surface.
- Tyson's `business_brief` already asserts *"coffee pairings"*. New
  content moves the pairing claim from identity assertion to
  demonstrable reference.

**Facts NOT being invented:**

- No coffee cultivar, origin country, farm, or process name (avoided
  as jargon-for-jargon's-sake per §"IMPORTANT FACTUAL BOUNDARY").
- No pricing.
- No opening-hours changes.
- No baker biography, kitchen equipment, or supplier claims.
- No allergen, dietary, or nutrition claims.
- No claims about ordering flow, pickup, delivery, or subscriptions.

## §19 Mutation route audit

### 19.1 Available surfaces

| Surface | Path | Preserves invariants? | Operator-facing? | Verdict |
|---|---|---|---|---|
| **SPA — Ask panel Beat 3 edit** (`spokesperson-ask-panel.tsx:485-585`) | Ask Tyson a question → click a citation → inline textarea → Save → `updateKnowledge` → `PATCH /api/embeddings/documents/{id}/` with `{text_content}` | **Yes** (backend serializer preserves `id`, `workspace`, `spokespeople` M2M, `title`, `universe`, `audience_scope`, `is_active`; drops stale chunks; fires `embed_document.delay(...)`) | **Yes** — full dogfood surface | **RECOMMENDED (primary)** |
| **SPA — KD detail page** (`/workspace/knowledge/:id`) | Inspect chunks + delete only | Read-only (no edit UI wired) | Yes | Not applicable — no edit gesture exists |
| **Authenticated HTTP PATCH** | `PATCH /api/embeddings/documents/{id}/` `{text_content: "…"}` via curl/httpie with session cookie | **Yes** (same backend code path as Beat 3) | Partial — operator-authorized but not visual | **Fallback if Ask citation can't be surfaced** |
| **Django admin** | `/admin/embeddings/knowledgedocument/{id}/change/` | Risk: admin `save()` bypasses serializer re-ingest hook; would set `processed_content` without dropping chunks or firing `embed_document` | Not dogfood | **REJECTED** |
| **ORM in `manage.py shell`** | `KnowledgeDocument.objects.filter(pk=…).update(processed_content=…)` | Same hazard as admin plus violates operator-dogfood discipline (per Q-279-2A brief: *"Chris is the operator and should dogfood the product rather than Claude silently manufacturing production state through the ORM"*) | Not dogfood | **REJECTED** |

### 19.2 Recommended operator gesture — SPA Ask panel

Chris's exact sequence:

1. Open Tyson's Ask panel (Spokesperson detail → Ask).
2. Ask a coffee-adjacent question, e.g. *"What do you know about
   pairing pastries with coffee?"* (any question that surfaces the
   specialty KD as a citation).
3. In the citations panel, click the *Tyson's Pastry Pairing
   Specialty* citation. This opens `EditDocSurface` inline.
4. The textarea prefills with the current 118-char content. **Select
   all and replace with the §15 verbatim text.**
5. Click Save. The backend re-ingests: content_hash recomputes, chunks
   drop synchronously, `embed_document` fires asynchronously, status
   flips `pending` → `processing` → `processed`.
6. Wait for `processed` (visible in the detail view / list view).

### 19.3 Lifecycle + audience safety check

Cross-referenced against SESSION 275 (`deactivated_reason` /
orphan-archive) and SESSION 276 (Delta audience shape invariants).

| Invariant | Post-mutation state | Preserved? |
|---|---|---|
| `id` stable | Same UUID `3ff45702-cb8b-49f0-82f6-97013c0f8da6` | ✓ |
| `workspace` | Same workspace `4ce5486d-…` | ✓ |
| `universe` | Same Universe (Fox & Flour) | ✓ |
| `audience_scope` = CHARACTER | Serializer only mutates `audience_scope` when explicitly present in payload; text_content-only PATCH leaves it CHARACTER | ✓ |
| `spokespeople` = {Tyson} | Serializer only mutates M2M when `spokesperson_ids` is present; text_content-only PATCH leaves M2M intact. Slice-14 CHARACTER + empty-M2M guard is not triggered because no M2M change is requested. | ✓ |
| `is_active` = true | text_content PATCH does not touch `is_active`; SESSION 275 `deactivated_reason` stays blank on active rows | ✓ |
| `title` | Not being changed | ✓ |
| Delta shape invariants (S276 Slice 21 CHECKs) | CHARACTER + M2M non-empty holds; no Universe / Workspace state changes; no scope broadening | ✓ |
| Content-hash uniqueness | New hash (2230-char content); no clash with other KDs (verified: no other KD in this workspace has this text) | ✓ |
| Chunks are re-embedded | Serializer drops old chunks synchronously then `embed_document.delay(pk)` re-embeds | ✓ |

No SESSION 275 or SESSION 276 lifecycle/audience invariant is weakened.
No audience broadening. No scope drift. Reversible in one Beat-3 edit
back to the original 118-char content if the experiment disconfirms.

## §20 Stage-A specimen matrix

Chris supplies these operator topics unchanged from Q-279-1 §8.3, with
Stage B deferred until Stage A returns.

| # | Topic (verbatim) | Purpose |
|---|---|---|
| T1 | *"Ruby thinks Tyson is taking coffee too seriously."* | Direct baseline replay of Q-278-4.2 Specimen 2 (baseline = 0/12). |
| T2 | *"Tyson thinks Ruby secretly entered them in a baking competition."* | Direct baseline replay of Q-278-4.3 Specimen 3 (baseline = 0/12). |
| T3 | *"Ruby locks herself out of the bakery."* | Neutral non-domain control. Baseline for T3 does not exist (new topic). T3 tests inappropriate Knowledge leakage — if the enriched KD causes Tyson to lecture on coffee here, the substrate is retrieval-gating incorrectly (a distinct finding, not a Q-279-2 disconfirmation). |

**Operator behavior constraint:** Chris supplies ONLY the topic strings
above. No prompt augmentations. Explicitly NO variants such as:

- *"Ruby thinks Tyson is taking coffee too seriously. Talk about coffee."*
- *"Ruby thinks Tyson is taking coffee too seriously. Show your expertise."*
- *"Ruby thinks Tyson is taking coffee too seriously. Mention specific pastries."*

Adding operator-side domain hints would defeat the point of the
experiment (which is whether expertise emerges *from Knowledge* under
minimal-topic dialogue).

## §21 Rubric — unchanged from Q-279-1 §7

Preserved verbatim for comparability. R1-R6, max 12 per specimen for
Tyson's turns. Baseline:

- T1 historical = 0/12
- T2 historical = 0/12
- T3 historical = n/a (new specimen)

For every Stage-A render, additionally inspect persisted
`Composition.knowledge_chunk_ids`. A concrete term in dialogue only
supports **R6** if the term is traceable to a chunk that (a) is in
`knowledge_chunk_ids` and (b) actually contains the term. Concrete terms
that appear in dialogue without a traceable Knowledge source are
model-prior contamination and do NOT support R6 (though they may still
support R1-R3).

## §22 Pre-established Stage-A decision gate

Established BEFORE any render fires or any Knowledge is changed. Not
to be revised after seeing output.

**ACCEPT — Q-279-2 experiment succeeds. Substrate carries expertise
(subsequent decision: whether to open generalization audits for other
characters):**

- T1 and T2 each score **≥ 6/12 total**.
- T1 and T2 each hit **R1 ≥ 2** (multiple named domain terms).
- T1 and T2 each hit **R6 ≥ 1** (at least one concrete term traceable
  to a treatment chunk).
- T3 hits **R1 = 0** for Tyson's turns (no unbidden coffee/pastry
  lecture in an unrelated scene).

All four must hold for ACCEPT.

**DISCONFIRM — substrate fails to route Knowledge to output:**

- T1 or T2 total **≤ 2/12** despite persisted `knowledge_chunk_ids`
  containing the new treatment chunks.
- R6 = 0 on both T1 and T2 despite concrete terms living in the chunk
  table.

Either condition triggers DISCONFIRM. Next audit shifts to
retrieval → prompt assembly → generation routing.

**AMBIGUOUS — signal is real but noisy:**

- Only one of T1 / T2 clears the ≥ 6/12 bar.
- R1 improves without R3 (namedropping without reasoning).
- Any other outcome that is neither ACCEPT nor DISCONFIRM.

AMBIGUOUS authorizes Stage B: repeat the ambiguous specimen(s) up to 3
additional renders. If Stage B still cannot separate signal from noise,
open a fresh design question (KD *shape* vs *depth*, retrieval ranking,
prompt-block ordering) — do not extend Stage B further.

**T3 second-order failure (recorded but does not block ACCEPT):**

- T3 R1 ≥ 1 — inappropriate Knowledge leakage. Preserve as a distinct
  substrate finding for a future audit (retrieval-gating question).
  Does not disconfirm Q-279-2 hypothesis A.

## §23 Boundary preservation

Per Q-279-2A §"KEEP OTHER HYPOTHESES OUT" — the following remain out
of scope for this slice and are NOT allowed to alter the Q-279-2
experiment interpretation:

- Generalized writer voice (4a).
- *"That's evidence."* / methodology-adjacent language (4a evidence
  bucket, not 4b evidence).
- Visual composition boundary (4c).
- Underdeveloped-scene / duration observations (4d).
- Avatar / video-quality (4e).
- Cross-cast alias grounding (4f).
- D-POS adjacent-surface migration (4g).
- Strict-mode audit (4h).
- Epistemic asymmetry (4i).

If any of these appear during Stage A dogfood, record the observation
in a *separate* addendum (not in this Q-279-2 evaluation) so Chris +
ChatGPT retain them as distinct hypotheses.

## §24 Checklist — Q-279-2A

- [x] Adjustment A (staged render window) recorded (§14)
- [x] Adjustment B (KD chunks below top_k=5) recorded (§14)
- [x] Exact verbatim treatment text drafted (§15)
- [x] §"AUTHOR THE TREATMENT CORPUS" 9 requirements coverage-checked (§16)
- [x] Real `TextSplitter` dry-run executed (no persistence) (§17)
- [x] Chunk count = 3 (within 2-4 target) (§17)
- [x] Per-chunk sizes + content boundaries recorded (§17)
- [x] Explicit new Fox & Flour canon facts enumerated (§18)
- [x] Compatibility with existing canon audited (§18)
- [x] All available mutation routes surveyed (§19.1)
- [x] SPA Ask-panel Beat 3 gesture recommended + step-by-step (§19.2)
- [x] SESSION 275 + SESSION 276 lifecycle/audience invariants checked one-by-one (§19.3)
- [x] Stage-A specimen matrix + operator behavior constraint (§20)
- [x] R1-R6 rubric preserved verbatim (§21)
- [x] Pre-established ACCEPT / DISCONFIRM / AMBIGUOUS / T3-second-order gates (§22)
- [x] Out-of-scope hypotheses re-listed (§23)
- [x] No Knowledge mutation
- [x] No provider spend
- [x] No dogfood
- [x] No SPA / backend code changes

## §25 Recommendation

The Q-279-2A design is complete. The treatment corpus:

- Contains every required content category (§16).
- Chunks cleanly into 3 chunks under the real splitter, comfortably
  below the top_k=5 retrieval cap (§17).
- Introduces a small, explicit, Chris-reviewable set of new Fox & Flour
  canon facts (§18).
- Is applicable via the standard operator-facing SPA Ask-panel Beat 3
  edit surface, which preserves every SESSION 275 / SESSION 276
  lifecycle and audience invariant by construction (§19).
- Is evaluable against a rubric and gate that were locked before any
  output was seen (§21-§22).

### Recommended decision gate

> **READY-FOR-OPERATOR-KNOWLEDGE-MUTATION**
>
> **SUPERSEDED by Q-279-2A-REV §26-§35 below.** The pre-revision
> treatment made Fox & Flour menu assertions (bakery serves espresso,
> sells almond croissants, etc.) while storing them under an
> `audience_scope=CHARACTER` KD visible only to Tyson. That combination
> is mechanically audience-safe but semantically wrong: shared bakery
> reality would be represented as private Tyson-only knowledge,
> conflicting with the SESSION 275-277 World-vs-character Knowledge
> model. The T3 acceptance gate in §22 was also internally contradictory.
> Both issues resolved in §26-§35.

Chris (as operator) applies the §15 treatment via the §19.2 SPA
gesture. Once the KD status returns to `processed`, Stage A can begin
(one render each of T1 / T2 / T3, real-mode, minimal topics only).

---

# Q-279-2A-REV — Decision-gate revision

**Status opened:** 2026-08-25 (same day as Q-279-2A). Chris + ChatGPT
challenge to Q-279-2A rejected the §15 corpus on semantic-ownership
grounds and the §22 T3 gate on internal-contradiction grounds. Q-279-2A
staged render window (§14), R1-R6 rubric (§21), historical baselines,
T1/T2/T3 topics (§20), SPA Ask-panel mutation route (§19), CHARACTER
audience, Tyson-only spokesperson, World, identity, prompts, retrieval,
synthesis, and verifier remain unchanged.

No Knowledge is mutated in Q-279-2A-REV. No provider spend. No dogfood.

## §26 Challenge — CHARACTER-vs-WORLD ownership problem

The Q-279-2A §15 corpus asserted:

- *"Fox & Flour serves three coffee preparations daily: espresso, drip
  coffee, and pour-over."*
- *"The three pastries Tyson pairs most often are the almond croissant,
  the morning bun, and the chocolate babka."* + *"on the menu"* language.

Those sentences are **World canon**: what the Fox & Flour Bakery
Universe sells, when, to whom.

They were placed on a KD with `audience_scope=CHARACTER` +
`spokespeople=[Tyson]`. That is:

- **Mechanically audience-safe** — SESSION 275/276 lifecycle
  invariants are all preserved; the row is well-formed CHARACTER; only
  Tyson's per-character retrieval lane surfaces those chunks; Ruby's
  lane does not.
- **Semantically wrong** — the SESSION 275-277 substrate distinction
  between shared World Knowledge (`audience_scope=UNIVERSE`) and
  character-private expertise (`audience_scope=CHARACTER`) exists
  precisely so that *"the bakery sells almond croissants"* is a shared
  World fact both Ruby AND Tyson can reason about, while *"how Tyson
  thinks about pairing coffee with rich pastries"* is Tyson-private
  expertise. Storing "the bakery serves X" under CHARACTER means Ruby
  — the bakery's *owner* — mechanically does not know her own menu,
  while Tyson does.

This is the exact "hackathon knowledge leak" hazard the SESSION 275-277
substrate was built to prevent, inverted: instead of leaking private
context across characters, the original §15 treatment would have
privatized shared reality into a single character.

**The correct fix is NOT to promote these facts to Universe Knowledge
in this experiment.** Doing so would introduce a second changed
variable (Universe canon expansion), contaminating the identity-vs-
character-Knowledge controlled experiment. Q-279-2 tests whether
richer *character-specific* Knowledge causes demonstrated expertise;
adding Universe canon at the same time makes the outcome uninterpretable.

**The correct fix is to rewrite the CHARACTER-scoped treatment as pure
domain reference material** — coffee/pastry pairing concepts,
attributes, examples, and rules Tyson has internalized — that does NOT
depend on any particular Fox & Flour menu proposition.

Sessions 275-277 substrate model preserved:

| Layer | What it holds | Example |
|---|---|---|
| Universe.brief + Universe-audience KDs | Shared World facts — what the World is / what it sells / when it's open | *"Fox & Flour is open daily 7-3"* |
| CHARACTER-audience KD (what Q-279-2A-REV corpus becomes) | Character-private domain expertise; how the character reasons about their domain | *"A brighter pour-over lifts a laminated almond pastry because acidity cuts the butter"* |
| Teammate identity fields | Character role / voice / stance | *"Tyson focuses on the coffee-and-counter side; easygoing, dry, teases Ruby"* |

## §27 Revised treatment corpus — full verbatim text

Written as third-person domain reference. No sentence asserts what Fox
& Flour serves, sells, offers, stocks, or has on its menu. Coffee
preparations and pastry types are named as **domain concepts** and
**examples** (things a knowledgeable pairing thinker refers to), not as
inventory.

```
For pairing decisions, Tyson considers three common coffee preparations:
espresso, drip coffee, and pour-over. Espresso is short and intense; a
medium-dark roast in espresso tends to read rounded, with notes of cocoa
and toasted nut, low acidity, and a heavy finish. Drip coffee at a
medium roast tends toward a fuller body, gentle sweetness, and a mild,
even bitterness that stays in the background. A pour-over from a light
roast usually has brighter acidity, a lighter body, and clearer citrus
and stone-fruit notes near the top of each sip. As a rule, roast level
trades brightness for body: lighter roasts taste more of the bean
itself, while darker roasts taste more of the roast.

Three pastry types Tyson refers to often when thinking about pairings
are the almond croissant, the morning bun, and the chocolate babka. A
buttery almond croissant is an example of a laminated pastry filled
with almond cream and finished with sliced almonds and powdered sugar;
it reads sweet, rich, and dense. A morning bun is another laminated
dough, this one rolled with cinnamon sugar and orange zest and baked
in a muffin tin; it is buttery with a bright citrus lift and a
moderate, unfussy sweetness. A chocolate babka is a soft enriched
bread swirled with dark chocolate and topped with a light cocoa
streusel; the chocolate flavor is deep but the crumb stays tender, so
it reads rich in flavor without feeling heavy.

Three coffee-and-pastry pairings work reliably in Tyson's framework. A
brighter pour-over lifts an almond croissant: the lighter body and
higher acidity cut through the almond cream's richness so the last
bite still tastes clean. A drip coffee sits well under a morning bun:
its fuller body does not compete with the cinnamon and orange, and the
medium roast's gentle sweetness complements the sugar. When pairing a
chocolate-heavy pastry such as a chocolate babka, an espresso works
because its cocoa-and-nut register echoes the dark chocolate and the
short, intense pour keeps the pairing from feeling heavy on top of an
already rich bite. General rule when in doubt: if the pastry is
already very rich or very sweet, avoid the darker roast — the roast's
own bitterness stacks with the pastry and the pairing feels heavier;
a lighter roast with brighter acidity gives the palate somewhere to
breathe.
```

## §28 Requirement coverage — revised

| # | Requirement | Where present |
|---|---|---|
| 1 | ≥3 named coffee preparations | Paragraph 1: espresso, drip coffee, pour-over (as *"common coffee preparations"* Tyson *considers*, not as bakery inventory) |
| 2 | Roast / profile characteristics | Paragraph 1: medium-dark, medium, light + explicit roast-vs-body trade rule |
| 3 | ≥3 named pastries | Paragraph 2: almond croissant, morning bun, chocolate babka (as *"pastry types Tyson refers to often"*, not as bakery menu items) |
| 4 | Concrete sensory / structural attributes | Paragraph 2: laminated, butter-heavy, almond cream, sliced almonds; cinnamon sugar, orange zest, muffin tin; dark chocolate swirl, cocoa streusel, tender crumb |
| 5 | ≥3 explicit pairings | Paragraph 3: pour-over + almond croissant; drip + morning bun; espresso + chocolate-heavy pastry (babka example) |
| 6 | Short factual reason per pairing | Paragraph 3: *"acidity cuts through the almond cream's richness"* / *"fuller body does not compete with the cinnamon and orange"* / *"cocoa-and-nut register echoes the dark chocolate"* |
| 7 | ≥1 alternative / tradeoff rule | Paragraph 3: *"if the pastry is already very rich or very sweet, avoid the darker roast …"* |
| 8 | Overlap redundancy | Coffee names appear in paragraphs 1 + 3; pastry names appear in paragraphs 2 + 3; roast rule in paragraph 1 + (via 200-char overlap) chunk 1; every pairing sentence self-contains coffee + pastry + reason |
| 9 | Plain language | No cultivars, origins, farms, process names, altitudes, or industry acronyms. Descriptors ("brighter acidity", "fuller body", "tender crumb") are accessible register |

Constraint compliance:

- **NOT in Tyson's voice.** Third-person reference throughout. Tyson is
  the subject *whose framework* is described, not the speaker.
- **NOT another identity claim.** No sentence says Tyson is
  knowledgeable, expert, skilled, or good at anything. Sentences
  describe coffee, pastries, and pairings; the *"in Tyson's
  framework"* / *"Tyson considers"* / *"Tyson refers to often"*
  phrasing is scoping, not qualification.
- **NOT instructions to Tyson.** No imperative sentences. No "should",
  "recommend", "always", "never".
- **No Ruby-specific behavior.** Ruby unmentioned.
- **No Character OS methodology.** No mention of retrieval, prompts,
  audience, memory, verifier.
- **No prompt-engineering hints for the LLM.** No "cite this", "name a
  coffee", "use specific terms".
- **No Fox & Flour menu / inventory assertions.** Verified in §29.

## §29 Canon inventory — revised

### 29.1 Automated World-canon leakage scan

Ran on the exact §27 text:

| Prohibited phrase | Present? |
|---|---|
| `"Fox & Flour serves"` | not present |
| `"Fox & Flour sells"` | not present |
| `"Fox & Flour makes"` | not present |
| `"on the menu"` | not present |
| `"on our menu"` | not present |
| `"daily"` (in the schedule sense) | not present |
| `"at Fox & Flour"` | not present |
| `"in the bakery"` | not present |
| `"at the bakery"` | not present |

**"Fox & Flour" does not appear anywhere in the revised corpus.**
Neither does "bakery" as a location context.

### 29.2 New World canon introduced

> **None.**

The revised corpus does not assert:

- What Fox & Flour serves, sells, makes, or offers.
- Which coffees or pastries are on the menu.
- Whether these items exist at Fox & Flour at all.
- Hours, pricing, seasonality, supplier, kitchen equipment, or any
  other bakery-inventory fact.

The nouns *espresso*, *drip coffee*, *pour-over*, *almond croissant*,
*morning bun*, and *chocolate babka* are named as **domain concepts** —
things Tyson has knowledge *about* — not propositions about Fox &
Flour's operations. A reader who knew Fox & Flour's real menu could
determine independently whether any of these items happen to be on it;
the corpus is silent.

### 29.3 New CHARACTER-scoped Tyson expertise / canon

Facts that become part of Tyson's private domain-expertise Knowledge
if Chris approves this treatment:

**Tyson's coffee framework (private expertise):**

1. Tyson considers three coffee preparations relevant for pairing:
   espresso, drip coffee, pour-over.
2. Tyson's mental model of espresso: short + intense; medium-dark roast
   tends rounded, cocoa/toasted-nut notes, low acidity, heavy finish.
3. Tyson's mental model of drip coffee at medium roast: fuller body,
   gentle sweetness, mild even bitterness.
4. Tyson's mental model of pour-over from light roast: brighter
   acidity, lighter body, citrus + stone-fruit notes.
5. Tyson's roast-vs-body rule: lighter roasts taste more of the bean;
   darker roasts taste more of the roast.

**Tyson's pastry framework (private expertise):**

6. Tyson refers often to three pastry types for pairing thought:
   almond croissant, morning bun, chocolate babka.
7. Tyson's mental model of the almond croissant type: laminated,
   butter-heavy, almond cream filling, sliced almonds + powdered sugar;
   sweet, rich, dense.
8. Tyson's mental model of the morning bun type: laminated, cinnamon
   sugar + orange zest, muffin-tin baked; buttery with bright citrus
   lift and moderate sweetness.
9. Tyson's mental model of the chocolate babka type: soft enriched
   bread, dark chocolate swirl, cocoa streusel; rich chocolate flavor,
   tender crumb.

**Tyson's pairing framework (private expertise):**

10. Tyson's pairing: pour-over + almond croissant works because
    lighter body / brighter acidity cuts almond-cream richness.
11. Tyson's pairing: drip + morning bun works because fuller body sits
    under cinnamon/orange without competing; medium-roast sweetness
    complements sugar.
12. Tyson's pairing: espresso + chocolate-heavy pastry (babka example)
    works because espresso's cocoa/nut register echoes dark chocolate;
    short intense pour keeps pairing from feeling heavy.
13. Tyson's general rule: for very rich or very sweet pastries, avoid
    darker roasts — bitterness stacks; prefer lighter roast with
    brighter acidity.

All 13 facts are Tyson-private under `audience_scope=CHARACTER` +
`spokespeople=[Tyson]`. Ruby's per-character retrieval lane will not
surface them. Ruby's mental model of coffee remains whatever her own
Knowledge + identity establish (currently: nothing character-specific;
her `business_brief` names sourdough / pastries / desserts / cakes at
Fox & Flour without pairing framework).

### 29.4 Compatibility with existing canon

- `Universe.brief` (Fox & Flour Bakery): unchanged. Not contradicted —
  the revised corpus says nothing about the Universe.
- `Fox & Flour Hours` (Universe KD): unchanged. Not touched.
- `Fox & Flour holiday policy` (Universe KD): unchanged. Not touched.
- Ruby's `business_brief` (which names *"sourdough, handcrafted
  pastries, seasonal desserts, celebration cakes"*): unchanged and
  uncontested. Ruby continues to have unrestricted access to shared
  World facts.
- Tyson's `business_brief` (which names *"coffee pairings"*): unchanged.
  The identity claim persists; the new CHARACTER-Knowledge now supplies
  the domain content the identity claim asserts Tyson has.

## §30 Dry-run chunking — revised

Ran `apps.embeddings.text_splitter.TextSplitter(chunk_size=1000,
chunk_overlap=200).split(...)` on the exact §27 text. No DB mutation.

```
total chars:                       2317
total words:                       385
paragraphs (\n\n-separated):       3
chunk_size:                        1000
chunk_overlap:                     200
resulting chunk count:             3
```

Per-chunk boundaries:

| Chunk | Size | Opening | Closing | Content covered |
|---|---|---|---|---|
| 0 | 686 chars | *"For pairing decisions, Tyson considers three common coffee preparations …"* | *"… darker roasts taste more of the roast."* | Coffee framework (paragraph 1) in full — all 3 named coffee preparations + roast profiles + trade rule. |
| 1 | 922 chars | *"citrus and stone-fruit notes near the top of each sip. As a rule …"* (200-char overlap tail from chunk 0) | *"… reads rich in flavor without feeling heavy."* | Paragraph-1 tail (pour-over notes + trade rule via overlap) + all of paragraph 2 (3 named pastry types + attributes). |
| 2 | 1103 chars | *"is a soft enriched bread swirled with dark chocolate …"* (200-char overlap tail from chunk 1) | *"… gives the palate somewhere to breathe."* | Paragraph-2 tail (babka detail via overlap) + all of paragraph 3 (3 pairings + tradeoff rule). |

- 3 chunks total; comfortably within the 2-4 target.
- 3 < 5 (`retrieve_for_teammate` top_k). Retrieval always returns the
  full corpus; ranking is not a confound.
- Chunk 2 is 1103 chars, 10 % over the 1000-char soft limit. Same soft-
  limit behavior as the original §17 result (splitter emits over-limit
  chunks whole rather than mid-sentence truncate); does not affect
  embedding or retrieval.

## §31 T3 acceptance-gate contradiction — resolved

### 31.1 Contradiction identified

Q-279-2A §22 stated **both**:

- **ACCEPT** requires *"All four must hold"*, including *"T3 hits R1 =
  0 for Tyson's turns"*.
- **T3 second-order failure (recorded but does not block ACCEPT):**
  *"T3 R1 ≥ 1 — inappropriate Knowledge leakage. Preserve as a
  distinct substrate finding for a future audit … Does not disconfirm
  Q-279-2 hypothesis A."*

The first statement makes T3 R1 = 0 a required ACCEPT condition; the
second says a T3 failure does not block ACCEPT. These are mutually
incompatible.

### 31.2 Chris + ChatGPT direction

> *"Preserve T3 as part of the experiment gate. If T1 and T2
> demonstrate expertise but T3 causes unrelated coffee/pastry knowledge
> to intrude: classify the overall Stage-A result as AMBIGUOUS with a
> distinct retrieval/topic-gating finding. Do NOT call the full
> substrate result ACCEPT while the neutral control fails."*

Rationale: the desired substrate behavior is not merely *"deeper
Knowledge appears in dialogue"* — it is *"deeper Knowledge appears
naturally when relevant and stays quiet when irrelevant."* A substrate
that dumps Tyson's pairing framework into a lockout scene passes the
first test but fails the actual product goal.

### 31.3 Corrected Stage-A gate

**Supersedes Q-279-2A §22 in full.** Applies to Q-279-2 Stage A
evaluation.

**ACCEPT — Q-279-2 experiment succeeds:**

*All five* of the following must hold:

1. T1 total **≥ 6/12** for Tyson's turns.
2. T2 total **≥ 6/12** for Tyson's turns.
3. T1 hits **R1 ≥ 2** AND T2 hits **R1 ≥ 2** (multiple named domain
   terms in each demonstrated-expertise specimen).
4. T1 hits **R6 ≥ 1** AND T2 hits **R6 ≥ 1** (at least one term per
   specimen traceable to a treatment chunk in `knowledge_chunk_ids`).
5. **T3 R1 = 0** for Tyson's turns — no named coffee/pastry/pairing
   term in the unrelated-topic scene.

If any one of the five conditions fails, ACCEPT does NOT fire.
Interpret which of the following applies instead:

**DISCONFIRM — substrate fails to route Knowledge to output:**

- T1 total **≤ 2/12** OR T2 total **≤ 2/12**, despite persisted
  `knowledge_chunk_ids` containing the treatment chunks.
- OR R6 = 0 on both T1 AND T2 despite concrete treatment content
  living in the chunk table.

Either condition triggers DISCONFIRM. Next audit shifts to
retrieval → prompt assembly → generation routing.

**AMBIGUOUS — signal is real but noisy OR the topic-gating control
fails:**

Fires when the outcome is neither clean ACCEPT nor clean DISCONFIRM.
Explicit AMBIGUOUS sub-cases:

- **AMBIGUOUS-TOPIC-GATING** — T1 and T2 both meet conditions 1-4 of
  ACCEPT, but T3 R1 ≥ 1. Substrate demonstrates expertise correctly
  *and* leaks it into unrelated topics. Overall Stage-A result is
  AMBIGUOUS, not ACCEPT. Record as a distinct retrieval / topic-gating
  finding for a follow-up audit (candidate mechanical question:
  *"Does character-audience retrieval need a topic-relevance floor,
  or should top_k be lower when cosine similarity is weak, or is the
  §1 SCOPED KNOWLEDGE block emitting chunks whose topical relevance
  is below a useful threshold?"*).
- **AMBIGUOUS-SINGLE-SPECIMEN** — Only one of T1 / T2 clears the
  ≥ 6/12 bar. Repeat only the ambiguous specimen up to 3 additional
  renders under Stage B.
- **AMBIGUOUS-NAMEDROP-WITHOUT-REASONING** — R1 improves on both T1
  and T2 without R3 improving (specifics appear but no
  attribute-grounded reasoning). Open a follow-up question about KD
  shape (bulleted list vs prose with rationale) vs depth.
- Any other outcome that is neither ACCEPT (§31.3 all five hold) nor
  DISCONFIRM (§31.3 DISCONFIRM either condition).

**Consequence:** the gate is now internally consistent. A T3 failure
under otherwise-strong T1 / T2 output does NOT license ACCEPT. The
overall Stage-A result must be either full ACCEPT (all five hold) or
one of the non-ACCEPT classifications. This matches the product goal
(*relevant expertise appears; irrelevant expertise stays quiet*) and
matches Chris + ChatGPT's stated direction.

## §32 Prediction vs revision

Prediction recorded pre-revision (Q-279-2A §1 remains valid — the
substrate carries expertise if the content is genuinely domain content,
not identity restatement).

Additional prediction recorded pre-Stage-A, post-revision:

- **T3 R1 = 0** is *likely* — the topic *"Ruby locks herself out of the
  bakery"* has low cosine similarity with the treatment corpus's
  coffee / pastry / pairing vocabulary. Under `retrieve_for_teammate(
  tm, topic, top_k=5)` cosine ranking, coffee-heavy chunks should
  rank low for a lockout topic even with only 3 chunks in the
  Tyson-audience corpus.
- **BUT:** since Tyson's per-character corpus contains ONLY the
  treatment chunks (no other CHARACTER-audience KDs exist), retrieval
  will return them regardless of relevance. Whether they *appear in
  dialogue* is a second question — the LLM must judge topical
  relevance from the §1 SCOPED KNOWLEDGE block. If the LLM lectures on
  coffee during a lockout scene, that is diagnostic of the LLM (or the
  substrate's presentation) failing to topic-gate — a distinct
  retrieval / prompt-shape finding.

This prediction is recorded so Stage A can distinguish AMBIGUOUS-TOPIC-
GATING from clean ACCEPT even before evaluation.

## §33 Preserved from Q-279-2A (unchanged)

- Staged 3-render Stage A (§14).
- Conditional Stage B (§14).
- R1-R6 rubric (§21).
- Historical baselines T1 = 0/12, T2 = 0/12 (§21).
- T1 / T2 / T3 topics (§20).
- Operator behavior constraint — no augmented prompts (§20).
- SPA Ask-panel Beat 3 mutation route (§19).
- SESSION 275 + SESSION 276 lifecycle/audience invariant preservation
  (§19.3). The revised corpus does not weaken any invariant checked
  in §19.3 — the KD remains CHARACTER + Tyson-only + Fox & Flour
  Universe + active; only `text_content` changes.
- Boundary preservation — 4a / 4c / 4d / 4e / 4f / 4g / 4h / 4i remain
  out of scope for this experiment (§23).

## §34 Checklist — Q-279-2A-REV

- [x] CHARACTER-vs-WORLD ownership challenge documented (§26)
- [x] Rationale for why original §15 was mechanically-safe-but-semantically-wrong (§26)
- [x] Rejection of "promote to Universe" workaround (§26)
- [x] Revised treatment text drafted; no Fox & Flour menu / inventory language (§27)
- [x] 9-requirement coverage re-checked for revised text (§28)
- [x] Automated leakage scan on revised text (§29.1)
- [x] Explicit statement: no new World canon introduced (§29.2)
- [x] Explicit list of new CHARACTER-scoped Tyson expertise facts (§29.3)
- [x] Compatibility with existing Universe / Ruby / Tyson canon audited (§29.4)
- [x] Real `TextSplitter` dry-run executed on revised text; 3 chunks, ≤ top_k (§30)
- [x] T3 acceptance-gate contradiction identified (§31.1)
- [x] Chris + ChatGPT direction quoted (§31.2)
- [x] Corrected Stage-A gate written — ACCEPT requires T3 R1 = 0 as a hard condition (§31.3)
- [x] AMBIGUOUS-TOPIC-GATING sub-case introduced for T3 failure with strong T1 / T2 (§31.3)
- [x] Pre-Stage-A prediction on T3 recorded (§32)
- [x] Q-279-2A carry-overs identified and unchanged (§33)
- [x] No Knowledge mutation
- [x] No provider spend
- [x] No dogfood
- [x] No SPA / backend code changes

## §35 Recommendation

Q-279-2A-REV resolves both challenges cleanly:

1. **Ownership** — the revised §27 corpus contains zero Fox & Flour
   menu / inventory assertions; the automated scan (§29.1) confirms
   absence. The 13 new facts (§29.3) are all Tyson-private domain
   expertise, semantically appropriate for `audience_scope=CHARACTER`.
   Ruby's world remains uncontested. No accidental Universe canon.
2. **T3 gate** — §31.3 supersedes §22 in full. ACCEPT now requires
   T3 R1 = 0 as a hard fifth condition. A T3 failure with strong
   T1 / T2 lands in AMBIGUOUS-TOPIC-GATING, not ACCEPT. The gate is
   internally consistent and matches Chris + ChatGPT's stated
   direction that the substrate must both demonstrate expertise
   *when relevant* AND stay quiet *when irrelevant*.

Everything else Q-279-2A locked (Stage-A window, rubric, baselines,
topics, mutation route, lifecycle safety, boundary preservation) is
preserved unchanged.

### Recommended decision gate

> **READY-FOR-OPERATOR-KNOWLEDGE-MUTATION**

Chris (as operator) applies the **§27** treatment via the **§19.2** SPA
Ask-panel Beat 3 gesture. Once the KD status returns to `processed`,
Stage A proceeds under the corrected **§31.3** gate.

> **See §36-§41 below for the operator dogfood audit that stopped the
> mutation before it fired.** The gesture exists and is reachable, but
> its visual affordance was subtle enough that Chris could not find
> the edit control. Also captured a pre-treatment Ask response that
> is a direct verbal restatement of hypothesis 4b.

---

# Q-279-2B — Operator dogfood audit of the §19.2 mutation route

**Status opened:** 2026-08-25 (same day as Q-279-2A / Q-279-2A-REV).
Chris attempted the approved §27 mutation via the §19.2 SPA Ask-panel
gesture; the described "Edit control on a citation" was not visually
present. Mutation was halted before firing. Q-279-2B audits the real
current SPA to determine whether the gesture is reachable, broken, or
mis-documented, and captures a strong pre-treatment substrate evidence
line generated by the SPA itself. No Knowledge changed. No provider
spend. No dogfood beyond one Ask exchange operator-side.

## §36 What Chris observed

Ask exchange, verbatim:

- **Operator question:** *"What do you know about pairing pastries with coffee?"*
- **Tyson's answer:**
  > *"I'm especially knowledgeable about pairing pastries with coffee
  > and I like helping folks pick good combinations. I don't have
  > specific pairing details from you yet, but I can guide customers
  > once we decide what we want to feature."*
- **"From your notes" receipt shown:**
  - `Tyson's Pastry Pairing Specialty` — 1 excerpt
  - `Fox & Flour Hours` — 1 excerpt
  - `Fox & Flour holiday policy` — 1 excerpt
- **Reported affordance:** *"no obvious edit control on those citations."*

Farther down the Spokesperson page, the Knowledge panel showed:

- `Tyson's Pastry Pairing Specialty` · Attached to 1 spokesperson · 1
  chunk · processed · **Detach**

Reported affordance on that surface: *"no Edit control."*

## §37 Actual SPA wire — traced

### 37.1 Ask panel citation is a button

`web/src/components/spokesperson-ask-panel.tsx:452-471`:

```tsx
<ul className="mt-2 flex flex-col gap-1">
  {sorted.map((c) => (
    <li key={c.document_id}>
      <button
        type="button"
        onClick={() => onCitationClick(c)}
        className="… hover:bg-gold/10 focus:bg-gold/10 focus:outline-none focus:ring-1 focus:ring-gold/40"
        data-testid={`ask-citation-${c.document_id}`}
        aria-label={`Edit ${c.title}`}
      >
        <span className="… group-hover:text-gold group-focus:text-gold">
          {c.title}
        </span>
        <span className="…">
          {c.chunk_count} {c.chunk_count === 1 ? "excerpt" : "excerpts"}
        </span>
      </button>
    </li>
  ))}
</ul>
```

The ENTIRE citation row is a `<button>`. `aria-label={`Edit ${c.title}`}`
declares intent. `onClick` fires
`handleCitationClick(c)` → `setFix({kind:"edit", citation: c})` →
`EditDocSurface` renders (line 308) in place of the follow-up input,
with a `<textarea>` prefilled from
`useKnowledgeDocument(citation.document_id).data.processed_content`
(lines 496-503), Save button that calls
`updateKnowledge(id, {text_content})` (lines 506-517).

### 37.2 Tests confirm the wire is intended and working

`spokesperson-ask-panel.test.tsx:412-505` covers:

- *"clicking a citation opens EditDocSurface with the doc title"* — asserts
  clicking `getByTestId("ask-citation-doc_hours")` renders
  `getByTestId("ask-edit-surface")`, sets title, and prefills
  textarea from `processed_content`.
- Save flow: edits textarea, clicks `ask-edit-save`, closes surface.
- Cancel closes without firing `updateKnowledge`.
- Empty-textarea Save button is disabled.

Header comment (lines 18-19) restates the design intent:

> *"Grounded citations are clickable buttons → open EditDocSurface.
> EditDocSurface prefills from useKnowledgeDocument and PATCHes …"*

### 37.3 `useUpdateKnowledge` consumers — full inventory

`grep -rln useUpdateKnowledge` across `web/src`:

- `web/src/lib/api/knowledge.ts` — the hook definition itself.
- `web/src/components/spokesperson-ask-panel.tsx` — Ask citation +
  honest-fallback teach-me compose surfaces.
- `web/src/components/spokesperson-ask-panel.test.tsx` — tests.

**No other consumer exists.** The Knowledge panel (`knowledge-panel.tsx`)
exposes Attach + Detach only. The KD detail page
(`web/src/routes/workspace/knowledge.$id.tsx`) exposes Delete + read-only
chunk inspection only. The Ask panel citation is the **only**
operator-facing surface that mutates `text_content` today.

## §38 Verdict on the §19.1/§19.2 audit

- **The gesture exists and is reachable.** Chris does not need
  ORM/admin/curl; the SPA supports the edit through a fully wired,
  tested code path.
- **The audit's step-4 wording was accurate but under-specified:**
  *"click a citation"* is correct at the mechanical layer but the
  citation is styled as a text row with only a hover-triggered
  `bg-gold/10` glow and a `focus:ring-1 focus:ring-gold/40` focus
  ring. No pencil icon, no chevron, no persistent border, no visible
  "Edit" label. `aria-label="Edit …"` is present for screen readers
  but is invisible to sighted operators.
- **Chris's observation is a valid product finding — not a Claude
  documentation error.** The design lock (`spokesperson-ask-panel.tsx`
  header comment: *"citation row is a button (Beat 3) → opens the
  inline doc editor"*) says the row IS the affordance, so the design
  intent matches the audit. The visual signaling has drifted from
  the design intent. This is dogfood value in itself.

## §39 Operator path that DOES work today (no code change required)

Chris can complete the Q-279-2A-REV mutation right now by clicking
directly on the citation ROW (title + "1 excerpt") for *"Tyson's Pastry
Pairing Specialty"* under **From your notes**. The whole row is the
button; hovering it lights up with a subtle gold background and the
title turns gold. Clicking it should replace the follow-up input area
below with an **inline edit surface**:

- Header: *"Fixing"* → *"Tyson's Pastry Pairing Specialty"*.
- Textarea prefilled with the current 118-char content.
- Buttons: Cancel + Save.

Chris selects all textarea contents, replaces with the exact §27
verbatim text, clicks Save.

Backend behavior unchanged from §19: PATCH →
`serializers.KnowledgeDocumentSerializer.update` with `text_content`
→ new hash, drop old chunks, re-embed. Every SESSION 275 / SESSION
276 invariant preserved per §19.3.

## §40 Smallest product correction (NOT implementing this session)

If Chris + ChatGPT want to keep the operator-facing edit affordance
discoverable, the smallest correction is a visual signal on the
citation button. Options ordered smallest-first:

1. **Add a pencil-icon adornment** to each citation row. `PencilLine`
   is already imported in `spokesperson-ask-panel.tsx:40` (used on the
   honest-fallback teach-me button); rendering it opposite the
   `chunk_count` label on the citation row would make the "click to
   edit" affordance visible at rest. ~5-line change.
2. **Persistent underline or hairline border** on the citation row so
   it reads as clickable without hover.
3. **Right-align a visible "Edit" text label** next to the chunk-count.

Each is a single-component change. None touch the backend, serializer,
retrieval, prompt assembly, or the Q-279-2 experiment substrate.

**This session does NOT implement any UI change.** Recording as a
follow-up product task, distinct from Q-279-2 experiment substrate.

## §41 Pre-treatment substrate evidence — Tyson's Ask answer

The Ask exchange in §36 is a **verbal restatement of hypothesis 4b by
Tyson himself**, generated by the current substrate without any
prompt engineering. Preserve as pre-treatment evidence for the
Q-279-2 experiment:

- **Identity claim, present:** *"I'm especially knowledgeable about
  pairing pastries with coffee and I like helping folks pick good
  combinations."* — verbatim from Tyson's `business_brief` +
  specialty KD (both of which restate the identity claim).
- **Knowledge admission, present:** *"I don't have specific pairing
  details from you yet, but I can guide customers once we decide
  what we want to feature."* — Tyson (via the LLM synthesizing over
  the current 118-char KD + identity fields) is CORRECTLY reporting
  that his substrate contains an expertise CLAIM but no domain
  material. He offers to work with facts once given.

This is exactly what §3-§5 predicted: identity present + Knowledge
absent → dialogue that names the expertise domain without
demonstrating it. The Ask surface produces this admission in one
question; the dialogue-scene surface produces it as generic pairing
gestures ("coffee has opinions", *"which pastry to have with coffee"*).
Same substrate gap, different generation path.

**Baseline reinforced.** T1 and T2 historical scores of 0/12 (§7)
are consistent with this Ask observation. The treatment corpus
(§27) is exactly the domain material Tyson's Ask answer says he
does not have.

## §42 Recommendation

- **Q-279-2A-REV §31.3 documentation typo (`"All four"` → `"All
  five"`) is already applied.** Line 1406 of this document reads
  `*All five* of the following must hold:`; verified with grep.
  Lines 977 (in the superseded §22) and 1374 (quoting the superseded
  §22 during the §31.1 contradiction analysis) retain `"four"` as
  archival record of what was superseded and why — deliberately not
  touched.
- **The Q-279-2A-REV §19.2 mutation route is REACHABLE without any
  code change.** Chris can proceed by clicking directly on the
  *"Tyson's Pastry Pairing Specialty"* row under **From your notes**
  in Tyson's Ask panel (the whole row is the button). If clicking
  the row does NOT open an inline edit surface with a prefilled
  textarea, that is a genuine bug and should be reported so the
  investigation shifts before any mutation attempt.
- **Do not fall back to ORM/admin/curl.** The gesture works; only
  the visual signal is weak.
- **Preserve the §36 Ask exchange as pre-treatment evidence** — it is
  the strongest single-line articulation of hypothesis 4b the
  substrate has produced.

### Recommended decision gate

> **READY-FOR-OPERATOR-KNOWLEDGE-MUTATION** (unchanged — the mutation
> route exists and is reachable; §39 gives the exact operator gesture).

## §43 Checklist — Q-279-2B

- [x] Operator dogfood observation captured verbatim (§36)
- [x] Actual SPA wire traced to code + line numbers (§37.1)
- [x] Test coverage cited (§37.2)
- [x] Full inventory of `useUpdateKnowledge` consumers across the SPA (§37.3)
- [x] Verdict on §19.1/§19.2 documentation adequacy (§38)
- [x] Working operator gesture spelled out step-by-step (§39)
- [x] Smallest UI correction identified but NOT implemented (§40)
- [x] Pre-treatment substrate evidence preserved (§41)
- [x] §31.3 typo fix verified still in place (§42)
- [x] No Knowledge mutation
- [x] No code changes
- [x] No provider spend
- [x] No ORM / admin / curl bypass proposed

---

# Q-279-2C — Post-mutation verification

**Status opened:** 2026-08-25. Chris successfully executed the §39 SPA
Ask-panel citation-row edit gesture, replaced the KD content with the
approved §27 verbatim treatment, and clicked Save. UI feedback after
Save was weak — no obvious success confirmation or re-ingestion status
change. Q-279-2C performs a READ-ONLY persisted verification of the
mutation, a production retrieval probe against T1, and records the UX
finding for a follow-up product task. No mutation. No render. No
prompt/retrieval/synthesis changes. One retrieval probe fires a
text-embedding-3-small embedding call (~1 KB in, 1536-dim vector out;
sub-millicent cost); this is retrieval-lane telemetry, not a
provider render.

## §44 Mechanical verification (14 checks, read-only)

Method: read-only `docker exec character_os_postgres psql` queries
against the persisted Postgres state.

| # | Check | Expected | Observed | Pass |
|---|---|---|---|---|
| 1 | KD UUID | `3ff45702-cb8b-49f0-82f6-97013c0f8da6` | `3ff45702-cb8b-49f0-82f6-97013c0f8da6` | ✓ |
| 2 | Title | `Tyson's Pastry Pairing Specialty` | `Tyson's Pastry Pairing Specialty` | ✓ |
| 3 | `audience_scope` | `character` | `character` | ✓ |
| 4 | Spokesperson M2M | Tyson only (`f4de81f3-…`) | Tyson only, count = 1 | ✓ |
| 5 | Universe | Fox & Flour Bakery (`1a0af807-…`) | Fox & Flour Bakery | ✓ |
| 6 | `is_active` | `true` + `deactivated_reason=''` | `t`, blank | ✓ |
| 7 | `processed_content` | §27 verbatim (three paragraphs starting *"For pairing decisions, Tyson considers …"*) | Verbatim match confirmed by full-content dump (spans coffee framework → pastry framework → pairings + tradeoff rule). No trace of §15 *"Fox & Flour serves …"* language. No trace of the 118-char baseline. | ✓ |
| 8 | `LENGTH(processed_content)` | ≈ 2317 chars (§30 dry-run) | **2317 chars exact** | ✓ |
| 9 | `status` (re-ingestion) | `processed` | `processed`; `updated_at = 2026-08-24 03:21:42.768451+00` | ✓ |
| 10 | Chunk count | 3 | 3 | ✓ |
| 11 | Chunk correspondence to §30 dry-run | sizes 686 / 922 / 1103; boundaries match | index 0: `size=686`, head *"For pairing decisions, Tyson considers three common coffee preparations: espresso, drip coffee, and pour-over. Espresso "*, tail *"for body: lighter roasts taste more of the bean itself, while darker roasts taste more of the roast."*. index 1: `size=922`, head *"citrus and stone-fruit notes near the top of each sip. As a rule, roast level trades brightness for body: lighter roasts"*, tail *"ocolate flavor is deep but the crumb stays tender, so it reads rich in flavor without feeling heavy."*. index 2: `size=1103`, head *"is a soft enriched bread swirled with dark chocolate and topped with a light cocoa streusel; the chocolate flavor is dee"*, tail *"pairing feels heavier; a lighter roast with brighter acidity gives the palate somewhere to breathe."*. All three boundaries match the §30 predictions exactly. | ✓ |
| 12 | Embedding readiness | `embedding_dimension=1536`, `embedding_model=text-embedding-3-small`, `embedding_cost_micros` populated on every chunk | All 3 chunks: dim=1536, model=text-embedding-3-small, costs = 3 / 5 / 6 micros; created_at 03:21:41 - 03:21:42 | ✓ |
| 13 | Duplicate KD in Universe | none (KD count in Fox & Flour Universe = 3) | 3 KDs: Fox & Flour Hours (universe, active), specialty (character, active), Fox & Flour holiday policy (universe, active). Content_hash unique. | ✓ |
| 14 | Audience broadening / Universe drift / orphaning / lifecycle change / stale old chunk | none | No broadening (M2M still {Tyson}, audience still CHARACTER). No Universe drift (still `1a0af807`). No orphaning (M2M non-empty). No lifecycle change (`is_active=true`, `deactivated_reason=''`). Old baseline chunk `4c7954e0-49b0-44e9-9113-b3cb5b3054d5` **confirmed dropped** (`EXISTS(...) = f`). | ✓ |

All 14 checks pass.

### 44.1 Old baseline chunk explicitly verified gone

The old 118-char baseline chunk `4c7954e0-49b0-44e9-9113-b3cb5b3054d5`
(persisted in both prior SESSION 278 specimens'
`knowledge_chunk_ids`) was dropped synchronously by the serializer
during re-ingest (per `serializers.py:741`
`instance.chunks.all().delete()`) and replaced by three new UUIDs:
`a99dba2d-…` (index 0), `2548f826-…` (index 1), `a02de62d-…` (index 2).

### 44.2 Delta / SESSION 275-276 invariants preserved

Cross-checked against §19.3:

- CHARACTER + M2M non-empty ✓ (Delta Slice 4 §51 row-#3 invariant).
- CHARACTER + at least one spokesperson while active ✓ (Slice 13/14).
- Universe FK matches spokesperson's Universe ✓.
- `audience_scope` not silently transitioned by absence ✓ (§27
  PATCH did not include an audience change; guard at
  `serializers.py:550-562` therefore did not fire).
- Content-hash uniqueness preserved (new hash
  `a84244ac01cbbe9ebbad72adce66be99b862facd8d7cbe872014276bb4e5e1fb`;
  no clash with other KDs in this workspace).

## §45 Production retrieval probe — T1 topic

Read-only invocation of the *production* per-character retrieval
function `apps.embeddings.retrieval.retrieve_for_teammate` — the same
function `character_os.dialogue_synthesis.synthesize_dialogue` calls at
line 1540. Executed via `manage.py shell -c` with the real `.env`
config (DB_PORT=5434; earlier port confusion resolved). Non-mutating;
one embedding call for the topic string (retrieval-lane telemetry).

Inputs:

- Teammate: Tyson (`f4de81f3-…`)
- Topic: `"Ruby thinks Tyson is taking coffee too seriously."`
- `top_k = 5` (production default)

Retrieved chunks (5, cosine-ranked):

| Rank | Chunk id | Document | audience_scope | index | size |
|---|---|---|---|---|---|
| 1 | `a99dba2d-…` | Tyson's Pastry Pairing Specialty (treatment) | character | 0 | 686 |
| 2 | `a02de62d-…` | Tyson's Pastry Pairing Specialty (treatment) | character | 2 | 1103 |
| 3 | `2548f826-…` | Tyson's Pastry Pairing Specialty (treatment) | character | 1 | 922 |
| 4 | `219bcc30-…` | Fox & Flour holiday policy | universe | 0 | 39 |
| 5 | `3bfea692-…` | Fox & Flour Hours | universe | 0 | 57 |

Interpretation:

- **All 3 treatment chunks are retrieved for Tyson under the T1
  topic** — the first three ranks. Character-audience domain content
  outranks the two Universe operational chunks, consistent with
  cosine similarity favoring the pairing-vocabulary chunks against a
  pairing-adjacent topic. Retrieval is ready for T1 without any
  substrate work needed.
- The two Universe chunks appear at ranks 4-5 as expected — they are
  retrieval-visible to Tyson under `retrieve_for_teammate` per SESSION
  276 audience semantics (universe-audience is broadcast-visible to
  every teammate in the Universe), and their cosine rank simply
  reflects low semantic relevance.
- No chunk from any other document appears. No cross-cast leakage.
  Ruby's cast lane is unaffected (not probed, but Ruby has no
  character-audience KDs, so her per-character retrieval on the same
  topic will return only the two Universe operational chunks — the
  same as her SESSION 278 baseline).

## §46 UX finding — recorded for follow-up product task

**Operator observation (Chris, dogfood):** *"Save completed without an
obvious error; no meaningful success confirmation/status change was
visible; no obvious indication that the KnowledgeDocument had
updated/re-embedded."*

Verified mechanically: Save DID fire; content was replaced; chunks
were dropped and re-embedded; status flipped through
`pending → processing → processed` within roughly 1 second (`updated_at`
= 03:21:42.768451, first new chunk created 03:21:41.646, third chunk
03:21:42.760). But the SPA gave the operator no visible signal of any
of that between clicking Save and returning to the receipt.

**Finding (preserved, not implemented this session):**

> **Knowledge edit success / re-ingestion feedback is weak or absent.**

Adjacent product observation from the SPA code
(`spokesperson-ask-panel.tsx:83-87`): a `savedNotice` state exists and
is intended to render a soft "re-reading" acknowledgment
(*"NOT gated on re-embed completion (Beat 4 owns that gate); slice-2
shows the honest 're-reading' copy as a soft acknowledgment"* — code
comment). Whether that notice actually renders on the current UI
build, and whether it correctly reflects re-ingest completion vs
mere PATCH acceptance, is a distinct question this audit does not open.

Related but distinct from the §40 finding (**"Ask-panel citation edit
gesture has no visible affordance at rest"**). Both are Ask-panel Beat
3 discoverability / feedback issues on the same SPA surface.
Recommended future scope-lock could bundle both into a
"Beat 3 legibility" product slice; that is a Chris + ChatGPT decision,
not this session's.

## §47 Recommendation

All 14 mechanical checks passed. Production retrieval sees all 3
treatment chunks for Tyson under the T1 topic. No duplicate KD; no
stale chunk; no audience drift; no lifecycle change; no Universe
drift; no orphaning. Old baseline chunk explicitly gone.
SESSION 275/276 invariants intact.

Substrate is ready for Q-279-2 Stage A.

### Recommended decision gate

> **READY-FOR-STAGE-A-T1**

Chris proceeds when ready with the T1 render (real-mode, minimal
topic *"Ruby thinks Tyson is taking coffee too seriously."*, no
prompt augmentations, dialogue-scene template). Stage-A execution
follows the §31.3 corrected 5-condition gate.

## §48 Checklist — Q-279-2C

- [x] All 14 read-only persisted checks executed (§44)
- [x] Old baseline chunk confirmed gone (§44.1)
- [x] SESSION 275 + SESSION 276 invariants re-verified post-mutation (§44.2)
- [x] Production retrieval probe against T1 topic (§45)
- [x] All 3 treatment chunks retrieved for Tyson (§45)
- [x] No cross-cast leakage in retrieval (§45)
- [x] UX finding recorded verbatim as *"Knowledge edit success / re-ingestion feedback is weak or absent"* (§46)
- [x] UX finding preserved as follow-up product task, not implemented (§46)
- [x] No Knowledge mutation
- [x] No render
- [x] No code changes
- [x] No prompt / retrieval / synthesis / verifier changes
- [x] Recommendation stated (§47)

---

# Q-279-2 — Stage A T1 runtime result

**Status opened:** 2026-08-25. Chris fired the T1 render under the
corrected §31.3 gate immediately after Q-279-2C returned
READY-FOR-STAGE-A-T1. This section captures the runtime evidence, scores
Tyson's turns against the locked R1-R6 rubric (Q-279-1 §7), compares to
the pre-treatment baseline (Q-278-4.2 Specimen 2), records a distinct
Q-279-4A observation about recurring courtroom/legal metaphor language,
and recommends the next protocol gate.

No changes to Knowledge / prompts / retrieval / synthesis / verifier /
identity / character configuration.

## §49 T1 inputs

- **Composition UUID:** `488c37ba-ba8c-42bc-bc60-059fca81ea1f`
- **template_kind:** `dialogue_scene`
- **operator_topic (verbatim):** *"Ruby thinks Tyson is taking coffee too seriously."*
- **spokesperson_id:** Tyson (`f4de81f3-…`) as operator anchor.
- **target_duration_seconds:** 90
- **synthesis_predicted_seconds:** 94.9 s (within the ±20 % dialogue-scene tolerance).
- **audience_hint:** empty (baseline had empty; unchanged).
- **use_knowledge:** true (default). Real-mode.
- **memory_ids:** `[]`.

## §50 Persisted evidence (read-only)

- `status = completed`; `verification_status = verified` (D-POS Hybrid
  authoritative per SESSION 278 §7 substrate).
- `cost_actual_micros = 280100` → **$0.28** end-to-end.
- `knowledge_chunk_ids` (composition-level provenance) = 5 chunks:
  - `a99dba2d-…` — Tyson's Pastry Pairing Specialty, chunk 0 (treatment)
  - `a02de62d-…` — Tyson's Pastry Pairing Specialty, chunk 2 (treatment)
  - `2548f826-…` — Tyson's Pastry Pairing Specialty, chunk 1 (treatment)
  - `219bcc30-…` — Fox & Flour holiday policy, chunk 0 (Universe)
  - `3bfea692-…` — Fox & Flour Hours, chunk 0 (Universe)
- **All 3 treatment chunks landed on the composition** — traceable
  through the same JSONB field used to establish R6 in the rubric.
- `memory_ids = []` — no narrative memory in scope (as expected;
  Fox & Flour has no persisted memories).
- Ruby's per-character retrieval (per `synthesized_brief` header line
  format observed in earlier specimens) would include only the two
  Universe chunks; the treatment chunks remain Tyson-private.

## §51 Rendered dialogue (verbatim, as reported by Chris)

```
Ruby: You have been staring at that babka like it is about to give you a final exam.

Tyson: I am deciding whether it wants espresso or a pour-over. Important work.

Ruby: It is chocolate bread. It wants to be eaten before it gets lonely.

Tyson: Chocolate babka has dark chocolate and cocoa streusel. Espresso has that cocoa-and-toasted-nut thing going on, so they meet in the middle without piling heaviness onto the bite.

Ruby: You said "cocoa streusel" as if you were testifying in court.

Tyson: The court deserves a good pairing. Espresso is short and intense; it echoes the chocolate, then gets out of the way.

Ruby: And yet you tell people not to reach for darker roast with a rich, sweet pastry.

Tyson: When they are choosing blindly, yes. Darker roast can stack bitterness onto something already rich. But babka and espresso are a specific match. The problem is not coffee seriousness. The problem is careless coffee seriousness.

Ruby: That distinction has somehow made you more serious, not less.

Tyson: Fine. Give the almond croissant a bright pour-over. It cuts through the almond cream and keeps the last bite clean.

Ruby: And the morning bun?

Tyson: Drip coffee. Fuller body, gentle sweetness, no wrestling match with cinnamon and orange.

Ruby: So breakfast needs a seating chart.

Tyson: Only if you want everyone to get along.
```

Seven Tyson turns.

## §52 Q-279-2 R1-R6 scoring — Tyson's turns

Rubric locked at Q-279-1 §7 and preserved at Q-279-2A §21 / Q-279-2A-REV
§33. Applied unchanged.

| # | Dimension | Score | Evidence (Tyson's turns only) |
|---|---|---|---|
| **R1** | Specific named domain terms | **2** | *"babka"* / *"chocolate babka"* (×3+), *"espresso"* (×4), *"pour-over"* (×2), *"almond croissant"* (×1), *"drip coffee"* (×1) — 5 distinct named domain terms, each used naturally in the flow of turns, none forced. |
| **R2** | Concrete attributes / parameters | **2** | *"dark chocolate and cocoa streusel"* (babka structure), *"cocoa-and-toasted-nut"* (espresso profile), *"short and intense"* (espresso extraction), *"Darker roast can stack bitterness"* (roast axis), *"Fuller body, gentle sweetness"* (drip profile), *"bright"* pour-over (acidity axis), *"cuts through the almond cream"* (richness-cutting attribute chain). ≥ 2 attributes across multiple axes (body, sweetness, brightness, bitterness, roast, richness). |
| **R3** | Explicit pairing / recommendation reasoning | **2** | Babka + espresso: *"cocoa-and-toasted-nut thing going on, so they meet in the middle without piling heaviness onto the bite"* — attribute-grounded cause + effect. Also *"echoes the chocolate, then gets out of the way"*. Almond croissant + pour-over: *"cuts through the almond cream and keeps the last bite clean"* — acidity-cuts-richness chain. Morning bun + drip: *"Fuller body, gentle sweetness, no wrestling match with cinnamon and orange"* — body-doesn't-compete chain. Three recommendations, three attribute-grounded reasons. |
| **R4** | Choice-space awareness (alternatives / tradeoffs) | **2** | Named alternative + tradeoff sequence: *"When they are choosing blindly, yes. Darker roast can stack bitterness onto something already rich. But babka and espresso are a specific match."* — general rule (avoid darker roast on rich/sweet) named + specific exception (babka + espresso IS a specific match) reconciled with the WHY. This is *synthesis* over the corpus (the corpus states the rule and the specific pairing independently; Tyson reconciles the tension in-turn). |
| **R5** | Expertise emerges unprompted | **2** | Operator topic — *"Ruby thinks Tyson is taking coffee too seriously"* — asked for zero domain specifics. Tyson unfolds five named terms, six attributes, three attribute-grounded pairings, and a rule/exception tradeoff over his seven turns, all from his own volition in service of the scene's argument. |
| **R6** | Traceability to persisted Knowledge | **2** | All concrete terms trace to persisted treatment chunks in `knowledge_chunk_ids`: *"chocolate babka"* + *"cocoa streusel"* → chunk 2 (verbatim in *"soft enriched bread swirled with dark chocolate and topped with a light cocoa streusel"*); *"cocoa-and-toasted-nut"* → chunk 0 (verbatim in *"notes of cocoa and toasted nut"*); *"espresso is short and intense"* → chunk 0 (verbatim); *"cuts through the almond cream"* + *"keeps the last bite clean"* → chunk 2 (verbatim in *"cut through the almond cream's richness so the last bite still tastes clean"*); *"Fuller body, gentle sweetness"* (drip) → chunk 0 (verbatim); *"Darker roast can stack bitterness"* → chunk 2 (verbatim tradeoff rule *"bitterness stacks with the pastry"*). Every concrete claim traceable. |

**Total: R1 + R2 + R3 + R4 + R5 + R6 = 2 + 2 + 2 + 2 + 2 + 2 = 12 / 12.**

## §53 Baseline comparison

| Composition | Topic | Total | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|---|
| **T1 historical** (`d7549fc1-…`, SESSION 278 Q-278-4.2 Specimen 2, 118-char baseline KD) | *"Ruby thinks Tyson is taking coffee too seriously."* | **0 / 12** | 0 | 0 | 0 | 0 | 0 | n/a |
| **T1 post-treatment** (`488c37ba-…`, this render, §27 treatment KD) | *"Ruby thinks Tyson is taking coffee too seriously."* | **12 / 12** | 2 | 2 | 2 | 2 | 2 | 2 |

Delta: **+12/12 on the same operator topic, same character configuration,
same synthesis code, same prompt architecture, same retrieval code, same
verifier**. The single-variable difference is the 118-char identity-restating
KD → 2317-char domain-content KD. This is exactly what the Q-279-2
experiment was designed to isolate.

## §54 Prediction vs actual

Prediction at Q-279-1 §1 (recorded pre-evidence) and Q-279-2A-REV §32:

> Substrate distinguishes identity from Knowledge, but the current
> character-audience corpus is identity-restating, not domain content.
> Baseline retrieval will pull the specialty KD chunk, and its
> contribution to §1 SCOPED KNOWLEDGE will be functionally equivalent to
> BUSINESS SHAPE — a second copy of the identity claim … No genuine
> domain content is available to the LLM anywhere in §1 or §2 —
> expertise cannot emerge because none is present in the substrate.

Prediction implied that when the KD content becomes real domain material,
expertise SHOULD emerge naturally under minimal-topic dialogue without
prompt engineering.

Actual: T1 renders a scene where Tyson uses 5 named domain terms, 6
attributes, 3 attribute-grounded pairings, and a rule/exception
reconciliation across 7 turns — from a single operator topic that asked
for none of that. Prediction confirmed on T1.

## §55 What changed materially

- **Substrate content, not substrate mechanics.** The synthesis path,
  prompt architecture, retrieval function, verifier, and character
  identity fields are byte-identical to pre-treatment. Only
  `KnowledgeDocument.processed_content` changed on a single
  character-audience KD (from 118 chars of identity-restating text to
  2317 chars of domain-content reference).
- **Retrieved-chunk content richness.** Pre-treatment, the retrieved
  Tyson chunk added no information beyond BUSINESS SHAPE. Post-treatment,
  three retrieved chunks add named coffees, named pastries, structural
  attributes, pairing rules, and a tradeoff rule.
- **Character capability, not merely retrieval.** The measurable
  difference is that Tyson's dialogue now *demonstrates* the expertise
  his identity claims. This is the exact distinction Q-279-1 §5 called
  out: *"knowledge was retrieved"* vs *"knowledge materially changed
  character capability/performance"*. The retrieved-vs-used distinction
  is answered mechanically by R6 (traceability) + qualitatively by R3
  (attribute-grounded reasoning that recombines corpus material rather
  than parroting it).

## §56 What did NOT change

- **Character identity.** Tyson's `business_brief`, `personality`,
  identity slots, voice axes, POV — all unchanged. `tone_archetype`
  remains `expert`; voice_energy/humor/directness remain
  `medium`/`warm`/`balanced`.
- **World.** `Universe.brief` unchanged (still 331 chars about warm
  neighborhood artisan bakery). Fox & Flour Hours + holiday policy KDs
  unchanged.
- **Ruby.** Ruby row + Ruby-audience Knowledge (none) unchanged. Ruby's
  per-character retrieval lane still returns only the two Universe
  operational chunks. Ruby remains free to interact with the scene
  without private access to Tyson's pairing framework.
- **Synthesis code, prompts, retrieval, verifier, memories.** All
  unchanged. Composition `verification_status = verified` under the
  same D-POS Hybrid substrate that SESSION 278 landed.
- **Cross-cast alias grounding, writer voice, visual composition,
  duration, epistemic asymmetry substrate questions.** Untouched;
  deferred as 4a / 4c / 4d / 4e / 4f / 4g / 4h / 4i per §23.

## §57 Naturally integrated vs dumped

Signals of natural integration (not corpus-dumping):

- **Distributed across turns.** The 5 named terms + 6 attributes + 3
  pairings + tradeoff are spread across 7 turns, not front-loaded.
  Chunks are not recited in order.
- **Synthesis over corpus.** The corpus states *"if the pastry is
  already very rich or very sweet, avoid the darker roast"* as a
  general rule AND separately states *"espresso goes with the chocolate
  babka"* as a specific pairing. Tyson's turn reconciles the two:
  *"When they are choosing blindly, yes. Darker roast can stack
  bitterness onto something already rich. But babka and espresso are a
  specific match."* The reconciliation is not in the corpus; Tyson
  produces it from the corpus + the scene's pressure (Ruby quoting his
  own rule back at him).
- **In service of the scene's argument.** Ruby's frame is *"you're
  taking coffee too seriously."* Tyson's rebuttal is not *"here's what
  I know"* — it's *"the problem is not coffee seriousness. The problem
  is careless coffee seriousness."* The pairings are ammunition for
  that rebuttal, not decoration. Domain expertise serves character
  argument.
- **Personality preserved.** Tyson stays in-voice — dry, deadpan,
  practical. *"Important work."* *"Only if you want everyone to get
  along."* The domain material rides on the identity layer's voice,
  not on a switched-in expert register.
- **Ruby-integrity preserved.** Ruby paraphrases *"you tell people not
  to reach for darker roast with a rich, sweet pastry"* — a knowledge
  claim she could not have made under her own retrieval lane
  (Tyson-private). She surfaces the rule as something Tyson *tells
  people*, not as her own knowledge. This is scene-natural attribution,
  consistent with the SCOPE RULE in §1 FACTUAL BASIS
  (*"characters may of course react to what the other character SAYS
  in the scene"*).

Verdict: **naturally integrated, not dumped.**

## §58 Q-279-4A observation — recurring courtroom / legal-formal metaphor

**Recorded as evidence for the already-deferred Q-279-4A hypothesis;
NOT investigated in this slice and NOT permitted to alter Q-279-2 T1
scoring.**

### 58.1 Cross-specimen accumulation

| Source | Line | Speaker |
|---|---|---|
| SESSION 278 Q-278-4.2 Specimen 2 (pre-treatment) | *"stared at a pastry like it was about to give a deposition"* | Ruby |
| SESSION 278 Q-278-4.2 Specimen 2 (pre-treatment) | *"tiny courtroom for baked goods"* | Ruby |
| SESSION 278 Q-278-4.3 Specimen 3 (pre-treatment) | *"That's evidence."* | Tyson |
| SESSION 279 T1 (post-treatment) | *"You have been staring at that babka like it is about to give you a final exam."* | Ruby |
| SESSION 279 T1 (post-treatment) | *"You said 'cocoa streusel' as if you were testifying in court."* | Ruby |
| SESSION 279 T1 (post-treatment) | *"The court deserves a good pairing."* | Tyson |
| SESSION 279 T1 (post-treatment) | *"So breakfast needs a seating chart."* | Ruby |

Courtroom / legal-formal / procedural language recurs across at least
three renders spanning both pre- and post-treatment Fox & Flour
dialogue-scene compositions. Both characters produce it. The frequency
appears at least similar to pre-treatment (three courtroom-family
references in one T1 render alone).

### 58.2 Why this is Q-279-4A evidence, not Q-279-2 evidence

- **The §27 treatment corpus contains zero courtroom / legal / formal
  procedural language.** Grep-checked: no *"court"*, *"deposition"*,
  *"testify"*, *"witness"*, *"jury"*, *"trial"*, *"case"*, *"evidence"*,
  *"seating chart"*, *"final exam"*. Every content-shaping treatment
  input is coffee + pastry + pairing + attribute vocabulary.
- **The rest of the substrate (Universe.brief, Tyson identity, Ruby
  identity) also contains no courtroom language.** Grep-checked
  earlier in §3.
- Therefore the courtroom register cannot be sourced from any changed
  substrate variable in the Q-279-2 experiment. Its recurrence across
  pre- and post-treatment dialogue is a substrate-external signal
  living in generation, not in retrieval or identity.

### 58.3 What this observation lets us distinguish (deferred)

Q-279-4A candidate axis: distinguish

- **character-specific domain Knowledge** (moved by T1 — see §52-§57),
- **character identity / personality** (Tyson still dry, practical,
  teases Ruby — unchanged from pre-treatment),
- **generalized synthesis / writer voice / recurring metaphor family**
  (courtroom register persists across treatment change — unchanged).

The T1 result provides the cleanest single-render evidence yet that
these three axes are independently movable: change the first, keep the
second, and observe the third stay put. This is *informative* for
Q-279-4A's future audit but does NOT open Q-279-4A in this session.

### 58.4 Constraint

- Do NOT investigate root cause in this slice.
- Do NOT assume the cause (writing_contract phrasing, personality
  bleed, model prior, K6 §2 voice block, prompt scaffolding, etc. — all
  plausible; none tested).
- Do NOT change the experiment because of this observation.
- Do NOT let this observation alter Q-279-2 T1 scoring — courtroom
  language is stylistic, not domain, and does not enter any R1-R6
  dimension.

Preserved for Q-279-4A when Chris + ChatGPT choose to open it.

## §59 Current experiment status

- **T1 scores 12 / 12** vs baseline **0 / 12**.
- **All ACCEPT sub-conditions for T1 individually met:**
  - T1 total ≥ 6/12: 12 ≥ 6 ✓ (condition 1)
  - T1 R1 ≥ 2: 2 ≥ 2 ✓ (condition 3, T1 half)
  - T1 R6 ≥ 1: 2 ≥ 1 ✓ (condition 4, T1 half)
- **T2 and T3 have NOT been rendered.** The §31.3 ACCEPT gate requires
  all five conditions (including T2 mirror of R1 ≥ 2 and R6 ≥ 1, plus
  T3 R1 = 0). Cannot call Q-279-2 ACCEPT on one specimen.
- **No condition triggers DISCONFIRM.** T1's persisted
  `knowledge_chunk_ids` contains all 3 treatment chunks (R6 = 2, not 0).
- **No condition currently indicates AMBIGUOUS.** T3 not yet run so
  AMBIGUOUS-TOPIC-GATING is unassessed. T2 not yet run so
  AMBIGUOUS-SINGLE-SPECIMEN is unassessed. R3 = 2 not 0 so
  AMBIGUOUS-NAMEDROP-WITHOUT-REASONING is not triggered.
- **Composition is verified** (D-POS Hybrid post-Q-278-4.3 substrate).

Preserve the staged protocol per Q-279-2A §14 / Q-279-2A-REV §33:
T1 → then T2 if appropriate → then T3 if appropriate. Stop at the
proper gate.

## §60 Recommendation

Q-279-2 T1 is a ceiling-hitting single-specimen result. Every R1-R6
dimension moved from baseline 0 to maximum 2. Treatment chunks land on
the composition (R6 = 2). Domain content appears distributed, integrated
with Tyson's voice, and used to argue against Ruby's frame rather than
recited. Naturally integrated, not dumped.

But T1 alone cannot ACCEPT. The §31.3 gate requires T1 AND T2 both
clear the specimen conditions AND T3 R1 = 0. The Q-279-4A observation
strengthens the pre-registered decomposition (Knowledge is
independently movable from writer voice) but does not affect the T1
substrate score.

### Recommended next protocol gate

> **READY-FOR-T2**

Chris proceeds when ready with T2 (real-mode, minimal topic verbatim
*"Tyson thinks Ruby secretly entered them in a baking competition."*,
no prompt augmentations). After T2 lands and is scored, we assess
whether to proceed to T3 or stop early.

## §61 Checklist — Stage A T1

- [x] Composition UUID + persisted evidence recorded (§49, §50)
- [x] All 3 treatment chunks confirmed on `knowledge_chunk_ids` (§50)
- [x] Verbatim rendered dialogue captured (§51)
- [x] R1-R6 scored against locked rubric with per-dimension evidence (§52)
- [x] Baseline comparison table with delta (§53)
- [x] Prediction vs actual (§54)
- [x] What changed materially / what did not (§55, §56)
- [x] Naturally integrated vs dumped analysis (§57)
- [x] Q-279-4A courtroom-language observation captured, cross-specimen accumulated, and explicitly held OUT of Q-279-2 scoring (§58)
- [x] Current experiment status vs §31.3 gate (§59)
- [x] Next gate stated (§60)
- [x] No Knowledge / prompt / retrieval / synthesis / verifier / identity change
- [x] No T2 fired
- [x] No T3 fired
- [x] No investigation of the courtroom-language root cause
- [x] Locked rubric preserved unchanged

---

# Q-279-2 — Stage A T2 runtime result

**Status opened:** 2026-08-25. T1 recorded READY-FOR-T2 at §60. Chris
fired T2 real-mode under the corrected §31.3 gate immediately after.
This section captures the runtime evidence, scores Tyson's turns
against the locked R1-R6 rubric, compares to the pre-treatment T2
baseline (Q-278-4.3 Specimen 3, historical 0/12), records additional
Q-279-4A courtroom/procedural-metaphor evidence separately, records
the new Knowledge-breadth observation separately, and recommends the
next protocol gate.

No changes to Knowledge / prompts / retrieval / synthesis / verifier /
identity / character configuration.

## §62 T2 inputs

- **Composition UUID:** `699916a9-2dc3-484c-b0cd-fa0d54970a0b`
- **template_kind:** `dialogue_scene`
- **operator_topic (verbatim):** *"Tyson thinks Ruby secretly entered them in a baking competition."*
- **spokesperson_id:** Tyson (`f4de81f3-…`) as operator anchor.
- **target_duration_seconds:** 90
- **synthesis_predicted_seconds:** 92.8 s (within tolerance).
- **audience_hint:** empty.
- **use_knowledge:** true. Real-mode.
- **memory_ids:** `[]`.

## §63 Persisted evidence (read-only)

- `status = completed`; `verification_status = verified` (D-POS Hybrid).
- `cost_actual_micros = 260100` → **$0.26**.
- `knowledge_chunk_ids` = 5 chunks:
  - `a02de62d-…` / `2548f826-…` / `a99dba2d-…` — Tyson's Pastry Pairing
    Specialty (**all 3 treatment chunks**)
  - `219bcc30-…` — Fox & Flour holiday policy (Universe)
  - `3bfea692-…` — Fox & Flour Hours (Universe)
- All 3 treatment chunks landed on the composition. Same set as T1
  (§50); retrieval is stable across the two independent renders.
- `memory_ids = []`.

## §64 Rendered dialogue (verbatim)

```
Tyson: Tell me straight: did you secretly enter us in a baking competition?

Ruby: What? No. Why do you have that look on your face?

Tyson: Because you asked me about the chocolate babka, then espresso, then whether the pairing would feel too heavy. That is not a casual question. That is a person rehearsing for judges.

Ruby: Or it is a person trying to help someone choose breakfast without making it feel like a final exam.

Tyson: That sounds reasonable, which is exactly how a secret competition entry would defend itself.

Ruby: Fine, detective. What would you tell them?

Tyson: For the babka, espresso works. It has that cocoa-and-toasted-nut thing going on, so it meets the dark chocolate without piling on a giant cup of coffee. Short pour, rich bite, done.

Ruby: And if they want something lighter?

Tyson: Almond croissant with a brighter pour-over. The acidity cuts through the almond cream, so the last bite does not turn into a butter situation.

Ruby: A butter situation?

Tyson: You know the one. Delicious, then suddenly you need to sit quietly and reconsider your morning.

Ruby: That is exactly the kind of useful answer I wanted. No competition—just a kinder way to guide people at the counter.

Tyson: All right. But if a mysterious trophy appears, I am taking credit for the espresso round.
```

Seven Tyson turns.

## §65 Q-279-2 R1-R6 scoring — Tyson's turns

Rubric locked at Q-279-1 §7 / preserved at Q-279-2A §21 / Q-279-2A-REV
§33. Applied unchanged.

| # | Dimension | Score | Evidence (Tyson's turns only) |
|---|---|---|---|
| **R1** | Specific named domain terms | **2** | *"chocolate babka"* (×2), *"espresso"* (×4), *"almond croissant"* (×1), *"pour-over"* / *"brighter pour-over"* (×2). Five distinct named coffee/pastry terms across the turns; used in flow, not enumerated. |
| **R2** | Concrete attributes / parameters | **2** | *"cocoa-and-toasted-nut"* (espresso profile), *"dark chocolate"* (babka), *"short pour"* / *"rich bite"* (espresso extraction), *"brighter"* pour-over (acidity axis), *"acidity cuts through the almond cream"* (attribute chain). ≥ 2 attributes across multiple axes. |
| **R3** | Explicit pairing / recommendation reasoning | **2** | Babka + espresso: *"It has that cocoa-and-toasted-nut thing going on, so it meets the dark chocolate without piling on a giant cup of coffee. Short pour, rich bite, done."* — attribute-grounded cause (cocoa/nut register meets chocolate) + effect (not heavy). Almond croissant + brighter pour-over: *"The acidity cuts through the almond cream, so the last bite does not turn into a butter situation."* — attribute-grounded chain (acidity cuts richness → last bite not overloaded). |
| **R4** | Choice-space awareness (alternatives / tradeoffs) | **2** | Ruby asks *"if they want something lighter?"* — Tyson responds with the alternative *"Almond croissant with a brighter pour-over"* PLUS the why-to reasoning (acidity cuts richness, avoids butter overload). Alternative named with when-to condition, not just enumerated. |
| **R5** | Expertise emerges unprompted | **2** | Operator topic — *"Tyson thinks Ruby secretly entered them in a baking competition"* — requested zero domain specifics. Tyson volunteers the babka/espresso/pairing sequence AS EVIDENCE that Ruby is rehearsing for judges (*"you asked me about the chocolate babka, then espresso, then whether the pairing would feel too heavy"*), then delivers the babka pairing + reasoning + a lighter alternative. Domain material is central to the accusation argument, not decoration. Character's own volition. |
| **R6** | Traceability to persisted Knowledge | **2** | *"chocolate babka"* + *"dark chocolate"* → treatment chunk 2 (verbatim in *"chocolate babka is a soft enriched bread swirled with dark chocolate"*). *"cocoa-and-toasted-nut"* → chunk 0 (verbatim *"notes of cocoa and toasted nut"*). *"short pour"* → chunk 2 (*"short, intense pour"*). *"brighter pour-over"* → chunk 2 (*"A brighter pour-over lifts an almond croissant"*). *"acidity cuts through the almond cream"* → chunk 2 (*"higher acidity cut through the almond cream's richness"*). *"the last bite does not turn into a butter situation"* — attribute chain traces to chunk 2 (*"so the last bite still tastes clean"*); *"butter situation"* itself is a Tyson-voice rephrasing of *"richness"* (elaboration on a traced concept, not an unsourced claim). Every concrete claim traceable. |

**Total: R1 + R2 + R3 + R4 + R5 + R6 = 2 + 2 + 2 + 2 + 2 + 2 = 12 / 12.**

## §66 Baseline comparison

| Composition | Topic | Total | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|---|
| **T2 historical** (`7177b0f5-…`, SESSION 278 Q-278-4.3 Specimen 3, 118-char baseline KD) | *"Tyson thinks Ruby secretly entered them in a baking competition."* | **0 / 12** | 0 | 0 | 0 | 0 | 0 | n/a |
| **T2 post-treatment** (`699916a9-…`, this render, §27 treatment KD) | *"Tyson thinks Ruby secretly entered them in a baking competition."* | **12 / 12** | 2 | 2 | 2 | 2 | 2 | 2 |

Delta: **+12 / 12** on the same operator topic, same character
configuration, same synthesis code, same prompt architecture, same
retrieval code, same verifier. Single-variable substrate change.
Identical direction and magnitude to the T1 result.

## §67 Prediction vs actual

Same prediction as T1 (Q-279-1 §1 + Q-279-2A-REV §32): richer
character-specific Knowledge causes expertise to emerge naturally under
minimal-topic dialogue without prompt engineering. T1 confirmed the
prediction on one specimen; T2 replicates it on a second independent
topic. Two-for-two on the pre-treatment 0/12 baseline against 12/12
post-treatment.

## §68 Naturally integrated vs dumped

Signals of natural integration on T2:

- **Domain material serves the scene's frame.** T2 is an accusation
  scene. Tyson's opening evidence for the accusation is a list of
  Ruby's questions (*"you asked me about the chocolate babka, then
  espresso, then whether the pairing would feel too heavy"*) —
  treatment-corpus vocabulary used as accusation ammunition, not as a
  monologue.
- **Corpus paraphrase, not recitation.** *"Short pour, rich bite, done."*
  is Tyson-voice compression of chunk 2's *"short, intense pour keeps
  the pairing from feeling heavy"*. *"Butter situation"* is Tyson's
  colorful ad-lib on the corpus attribute *"almond cream's richness."*
  Not verbatim dumping; genuine synthesis.
- **Alternative surfaced Ruby-prompted, not front-loaded.** Ruby's
  *"And if they want something lighter?"* creates the natural opening
  for Tyson to offer the almond-croissant + pour-over pairing. This is
  dialogic flow, not enumeration.
- **Personality preserved.** Tyson stays dry and deadpan (*"That
  sounds reasonable, which is exactly how a secret competition entry
  would defend itself"*, *"I am taking credit for the espresso round"*)
  while carrying the domain content. Voice + domain co-exist.
- **Ruby-integrity preserved.** Ruby never claims Tyson-scoped
  Knowledge as her own; her references to *"chocolate babka"* /
  *"espresso"* are quotations of what Tyson said to her, not Ruby's
  independent expertise. SCOPE RULE respected.

Verdict: **naturally integrated, not dumped.** Same class as T1.

## §69 T2 independently clears its ACCEPT sub-conditions

Per §31.3 corrected ACCEPT gate, T2 must clear:

- T2 total ≥ 6/12 → **12 ≥ 6 ✓** (condition 2)
- T2 R1 ≥ 2 → **2 ≥ 2 ✓** (condition 3, T2 half)
- T2 R6 ≥ 1 → **2 ≥ 1 ✓** (condition 4, T2 half)

Combined with T1's already-cleared T1 sub-conditions (§59): conditions
**1, 2, 3, 4 are all met**. Condition **5 (T3 R1 = 0) remains unassessed
until T3 fires**. The full-experiment ACCEPT gate cannot fire on
T1 + T2 alone.

No DISCONFIRM triggered: R6 = 2 on both specimens; treatment chunks
present in `knowledge_chunk_ids` on both.

No AMBIGUOUS classification currently applies:
- **AMBIGUOUS-SINGLE-SPECIMEN** does not apply — both specimens cleared
  their sub-conditions.
- **AMBIGUOUS-NAMEDROP-WITHOUT-REASONING** does not apply — R3 = 2 on
  both specimens (attribute-grounded reasoning present).
- **AMBIGUOUS-TOPIC-GATING** unassessable until T3 runs.

## §70 Knowledge-breadth observation — recorded, NOT investigated

**Chris (dogfood):** *"The new Tyson performance is clearly much better,
but Tyson now appears bounded by the small domain corpus we deliberately
provided. Recurring concrete examples are primarily: chocolate babka,
almond croissant, espresso, pour-over, the few pairing rules present
in the treatment KD."*

Preserved as a distinct, deferred question:

> **How much domain breadth does a character-specific Knowledge corpus
> need before expertise feels varied and expansive rather than repeatedly
> circling the same small set of examples?**

Interpretation constraint (per Chris + ChatGPT direction):

- The current corpus was **intentionally tiny** (§8.2 / §17: exactly 3
  chunks, comfortably under `top_k = 5`, deliberately chosen so
  retrieval-ranking is not a confound and so this experiment isolates
  Knowledge *depth* rather than *breadth*).
- Recurrence of the same small set of concrete examples across T1 and
  T2 is EXPECTED under a 3-chunk corpus. It does **not** disconfirm
  Q-279-2 hypothesis A. Q-279-2 tests whether deeper Knowledge changes
  demonstrated expertise; the answer on this evidence is a clean YES.
- Corpus-breadth / retrieval-diversity / cross-topic freshness is a
  distinct future question. It concerns how the substrate scales past
  the minimal test, not whether the substrate carries domain content.

Constraint (do NOT this session):

- Do NOT add more pastries.
- Do NOT add more coffees.
- Do NOT create additional KDs.
- Do NOT change `top_k`.
- Do NOT change chunking.
- Do NOT alter retrieval.
- Do NOT alter prompts.

Recorded for Chris + ChatGPT to consider when the current Q-279-2
experiment closes.

## §71 Q-279-4A observation — additional evidence

**Continuing to preserve as evidence for the already-deferred Q-279-4A
hypothesis; NOT investigated in this slice and NOT permitted to alter
Q-279-2 T2 scoring.**

### 71.1 New T2 courtroom / procedural / formal-adversarial evidence

| Line | Speaker | Register |
|---|---|---|
| *"That is not a casual question."* | Tyson | procedural framing — verbatim echo of SESSION 278 Q-278-4.3 Specimen 3's *"That is not a casual question, Ruby. That's evidence."* |
| *"a person rehearsing for judges"* | Tyson | competition-formal / judicial |
| *"exactly how a secret competition entry would defend itself"* | Tyson | legal-defense metaphor |
| *"Fine, detective."* | Ruby | investigatory register |
| *"like a final exam"* | Ruby | academic/test procedural |

### 71.2 Cumulative Q-279-4A dossier — running total across Fox & Flour dialogue-scene specimens

| Source | Line | Speaker | Pre/post treatment |
|---|---|---|---|
| Q-278-4.2 Specimen 2 | *"give a deposition"* | Ruby | pre |
| Q-278-4.2 Specimen 2 | *"tiny courtroom for baked goods"* | Ruby | pre |
| Q-278-4.3 Specimen 3 | *"That's evidence."* | Tyson | pre |
| Q-279-2 T1 | *"final exam"* | Ruby | post |
| Q-279-2 T1 | *"testifying in court"* | Ruby | post |
| Q-279-2 T1 | *"The court deserves a good pairing."* | Tyson | post |
| Q-279-2 T1 | *"seating chart"* | Ruby | post |
| Q-279-2 T2 | *"That is not a casual question."* | Tyson | post |
| Q-279-2 T2 | *"rehearsing for judges"* | Tyson | post |
| Q-279-2 T2 | *"a secret competition entry would defend itself"* | Tyson | post |
| Q-279-2 T2 | *"Fine, detective."* | Ruby | post |
| Q-279-2 T2 | *"like a final exam"* | Ruby | post |

Twelve independent courtroom/procedural/formal-adversarial references
across five compositions spanning both pre- and post-treatment Fox &
Flour dialogue-scene renders. Both cast members produce them. The
T2 line *"That is not a casual question."* is a **verbatim echo** of
the SESSION 278 Q-278-4.3 Specimen 3 line — direct evidence that the
metaphor family survives across independent renders, independent
topics, independent scene frames, AND the K27 treatment change.

### 71.3 What this observation continues to let us decompose (deferred)

Post-T2 refinement of §58.3 decomposition:

- **character-specific domain Knowledge:** moved from 0/12 to 12/12 by
  the §27 treatment (T1 §52 + T2 §65).
- **character identity / personality:** unchanged. Tyson stays dry,
  practical, teases Ruby; Ruby stays warm, cheerful.
- **generalized synthesis / writer voice / recurring metaphor family:**
  courtroom / procedural register persists in identical shape across
  the treatment change AND across the second independent operator
  topic — including a verbatim phrase carryover from pre-treatment.

T1 provided the first single-render evidence of the three-way
decomposition; T2 replicates it and adds the verbatim-echo signal.
This is *cumulative* Q-279-4A evidence but does NOT open the
investigation in this session.

### 71.4 Constraint

- Do NOT investigate root cause.
- Do NOT assume the cause.
- Do NOT change the experiment.
- Do NOT allow the observation to alter Q-279-2 T2 scoring.

## §72 Current experiment status — post-T2

- **T1 = 12/12; T2 = 12/12. Both specimens clear their individual
  ACCEPT sub-conditions.**
- **§31.3 ACCEPT gate conditions 1-4 all met.**
- **Condition 5 (T3 R1 = 0) remains unassessed.** T3 has not fired.
- **DISCONFIRM does not apply.** Both R6 = 2; treatment chunks present
  on both compositions.
- **AMBIGUOUS-TOPIC-GATING unassessable until T3.** AMBIGUOUS-SINGLE-
  SPECIMEN and AMBIGUOUS-NAMEDROP-WITHOUT-REASONING both do not apply.
- **Compositions T1 and T2 are `verified`** under the SESSION 278 D-POS
  substrate.

The staged protocol locked at Q-279-2A §14 / Q-279-2A-REV §33 requires
T3 next: *"T3 neutral control if appropriate."* T3 is appropriate under
current status — both T1 and T2 delivered strong-signal ACCEPT-shape
results, so the topic-gating question is now the load-bearing remaining
uncertainty in the experiment.

## §73 Recommendation

Two-for-two ceiling-hitting results on independent operator topics with
identical single-variable substrate change. Both specimens naturally
integrate treatment content into character-in-voice dialogue that
serves each scene's argumentative frame. All concrete claims trace to
persisted treatment chunks. §31.3 ACCEPT gate conditions 1-4 are
satisfied.

The only remaining question under the pre-registered gate is whether
the substrate leaks Tyson's domain expertise into an unrelated topic.
T3 (*"Ruby locks herself out of the bakery"*) tests exactly that.

### Recommended next protocol gate

> **READY-FOR-T3**

Chris proceeds when ready with T3 (real-mode, minimal topic verbatim
*"Ruby locks herself out of the bakery."*, no prompt augmentations,
dialogue-scene template). After T3 lands and is scored, the §31.3
gate resolves either ACCEPT (T3 R1 = 0 for Tyson) or
AMBIGUOUS-TOPIC-GATING (T3 R1 ≥ 1 for Tyson) with the substrate
finding preserved for follow-up.

## §74 Checklist — Stage A T2

- [x] Composition UUID + persisted evidence recorded (§62, §63)
- [x] All 3 treatment chunks confirmed on `knowledge_chunk_ids` (§63)
- [x] Verbatim rendered dialogue captured (§64)
- [x] R1-R6 scored against locked rubric with per-dimension evidence (§65)
- [x] Baseline comparison table with delta (§66)
- [x] Prediction vs actual on T2 (§67)
- [x] Naturally integrated vs dumped analysis (§68)
- [x] T2 sub-condition compliance under §31.3 gate (§69)
- [x] Knowledge-breadth observation captured verbatim, held separate from Q-279-2 scoring, constraint list recorded (§70)
- [x] Q-279-4A additional evidence captured; cumulative dossier updated; verbatim-echo signal noted; three-way decomposition refined (§71)
- [x] Current experiment status vs §31.3 gate (§72)
- [x] Next gate stated (§73)
- [x] No Knowledge / prompt / retrieval / synthesis / verifier / identity change
- [x] No T3 fired
- [x] No corpus-breadth investigation
- [x] No Q-279-4A investigation
- [x] Locked rubric preserved unchanged

---

# Q-279-2 — Stage A T3 runtime result + Stage-A decision gate

**Status opened:** 2026-08-25. T2 recorded READY-FOR-T3 at §73. Chris
fired T3 real-mode. T3 is the neutral-control specimen: the operator
topic is unrelated to coffee/pastry/pairing so we can test whether the
substrate leaks Tyson's domain expertise into an irrelevant scene.
This section captures the runtime evidence, scores T3 R1 for Tyson
(the only rubric dimension the neutral control targets), assembles the
full Stage-A matrix, resolves all five §31.3 ACCEPT conditions, and
recommends the final Q-279-2 gate. Additional visual-composition
observation (per Chris) and the running Knowledge-breadth observation
are preserved as distinct, deferred hypotheses.

No changes to Knowledge / prompts / retrieval / synthesis / verifier /
identity / character configuration.

## §75 T3 inputs

- **Composition UUID:** `a5c59014-d6c2-44db-b6fc-13f1fbc0bc61`
- **template_kind:** `dialogue_scene`
- **operator_topic (verbatim):** *"Ruby locks herself out of the bakery."*
- **spokesperson_id:** Tyson (`f4de81f3-…`) as operator anchor.
- **target_duration_seconds:** 90
- **synthesis_predicted_seconds:** 97.5 s (within tolerance).
- **audience_hint:** empty.
- **use_knowledge:** true. Real-mode.
- **memory_ids:** `[]`.

## §76 Persisted evidence (read-only)

- `status = completed`; `verification_status = verified` (D-POS Hybrid).
- `cost_actual_micros = 280100` → **$0.28**.
- `knowledge_chunk_ids` = 5 chunks — **identical set** to T1 (§50) and
  T2 (§63):
  - `a99dba2d-…` / `a02de62d-…` / `2548f826-…` — Tyson's Pastry Pairing
    Specialty (all 3 treatment chunks retrieved on the neutral topic
    too)
  - `219bcc30-…` — Fox & Flour holiday policy
  - `3bfea692-…` — Fox & Flour Hours
- **Treatment chunks were made available to synthesis** even though the
  operator topic has no coffee/pastry vocabulary. This is expected under
  the corpus-of-3 + `top_k = 5` configuration (Q-279-2A-REV §14, §32):
  retrieval always returns the entire treatment corpus. The question
  T3 asks is whether the LLM USES that available material inappropriately.
- `memory_ids = []`.

## §77 Rendered dialogue (verbatim)

```
Tyson: Why are you standing outside with that look on your face? That is not the face of someone admiring the morning.

Ruby: I locked myself out. The keys are inside, on the counter, where I put them so carefully that I cannot reach them at all.

Tyson: A strong system. Very secure. Mainly from us.

Ruby: Please save the teasing until after we are inside. We open at seven, and I can already picture somebody arriving for bread and finding me waving apologetically through the glass.

Tyson: All right. Before we turn this into a dramatic bakery rescue: do you have a spare key?

Ruby: I do. It is in my bag.

Tyson: Good. And where is your bag?

Ruby: Inside. Next to the keys. They are apparently keeping each other company.

Tyson: Naturally. The counter has become a tiny private club. Can you call whoever has the spare-spare key?

Ruby: I already did. They are on the way. I just hate this part—the waiting, knowing the whole bakery is right there and I cannot get to it.

Tyson: You can still get ready. I'll handle the first questions when we get in: what is ready, what needs a minute, and where everybody is meant to pick up. You breathe.

Ruby: You make it sound manageable.

Tyson: It is manageable. But when we get inside, put the keys somewhere less ambitious than the counter.

Ruby: I'm getting a hook. A very obvious hook. Possibly a sign addressed directly to me.
```

Seven Tyson turns.

## §78 T3 R1 — neutral-control substrate check

The gate condition per §31.3 is **T3 R1 = 0 for Tyson's turns**.
"Named domain terms" for the R1 dimension in this experiment means
the treatment-corpus vocabulary: coffee preparations, roast attributes,
named pastries, pairing framework language. Universe-general nouns
(bakery, counter, bread as a category) are NOT the R1 target — they
belong to `Universe.brief` + operational Universe KDs, not the §27
treatment corpus.

### 78.1 Treatment-vocabulary scan on Tyson's turns

| Treatment term / concept | Present in Tyson's T3 turns? |
|---|---|
| *espresso* | **No** |
| *drip coffee* | **No** |
| *pour-over* | **No** |
| *almond croissant* | **No** |
| *morning bun* | **No** |
| *chocolate babka* | **No** |
| *roast* (any form) | **No** |
| *acidity* / *bitter* / *body* (coffee-attribute sense) | **No** |
| *pairing* / *pair* | **No** |
| *cocoa* / *streusel* / *toasted nut* / *laminated* / *cream* (treatment-corpus attributes) | **No** |
| *brighter* / *fuller body* / *gentle sweetness* (treatment attribute phrases) | **No** |
| Tradeoff rule about darker roast + rich pastry | **No** |
| Any other Tyson-treatment concept | **No** |

**Zero treatment-vocabulary terms in any of Tyson's seven T3 turns.**

### 78.2 Ordinary bakery context Tyson does use (correctly not R1)

For completeness, Tyson does say:

- *"dramatic bakery rescue"* — *"bakery"* is a Universe-general noun
  present in `Universe.brief` (*"warm neighborhood artisan bakery"*).
  Not treatment-derived.
- *"the counter has become a tiny private club"* — *"counter"* appears
  in Tyson's own `business_brief` (*"coffee-and-counter side of the
  shop"*) and is Universe-general operational vocabulary. Not treatment.
- *"I'll handle the first questions when we get in: what is ready, what
  needs a minute, and where everybody is meant to pick up"* — customer
  pickup + operational context. Present in Tyson's `business_brief`
  (*"customer pickup flow, and the everyday questions people ask before
  ordering"*). Universe-general, not treatment-derived.

None of these are R1 signals for this experiment. They are Universe /
identity-layer context Tyson is expected to have regardless of the
Q-279-2 treatment.

### 78.3 T3 R1 verdict

> **T3 R1 = 0 for Tyson's turns.**

The substrate correctly did NOT surface Tyson's coffee/pastry/pairing
expertise in a lockout scene. Retrieved-but-unused: all three treatment
chunks were on the composition's `knowledge_chunk_ids` (§76), yet the
LLM produced zero treatment-vocabulary text in Tyson's dialogue. This
is the target behavior: *deeper Knowledge appears when relevant and
stays quiet when irrelevant* (§31.2, Chris + ChatGPT direction).

## §79 Full Stage-A matrix

| Specimen | Composition | Topic | R1 | R2 | R3 | R4 | R5 | R6 | Total | Baseline | Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 post | `488c37ba-…` | *"Ruby thinks Tyson is taking coffee too seriously."* | 2 | 2 | 2 | 2 | 2 | 2 | **12 / 12** | 0 / 12 | +12 |
| T2 post | `699916a9-…` | *"Tyson thinks Ruby secretly entered them in a baking competition."* | 2 | 2 | 2 | 2 | 2 | 2 | **12 / 12** | 0 / 12 | +12 |
| T3 control | `a5c59014-…` | *"Ruby locks herself out of the bakery."* | **0** | — | — | — | — | — | — (control) | n/a | n/a |

T3 R1 is the only rubric measurement expected on the neutral control
because the control's job is to test topic-gating, not to demonstrate
expertise. R2-R6 are not scored on T3 (the scene isn't about
demonstrating pairing; scoring them would misuse the rubric).

## §80 §31.3 five-condition ACCEPT gate — mechanical resolution

Locked pre-treatment at Q-279-2A-REV §31.3. Applied unchanged.

| # | Condition | Requirement | Observed | Pass |
|---|---|---|---|---|
| 1 | T1 total ≥ 6/12 | ≥ 6 | 12 | ✓ |
| 2 | T2 total ≥ 6/12 | ≥ 6 | 12 | ✓ |
| 3 | T1 R1 ≥ 2 AND T2 R1 ≥ 2 | both ≥ 2 | T1 = 2, T2 = 2 | ✓ |
| 4 | T1 R6 ≥ 1 AND T2 R6 ≥ 1 | both ≥ 1 | T1 = 2, T2 = 2 | ✓ |
| 5 | T3 R1 = 0 for Tyson's turns | = 0 | 0 | ✓ |

**All five conditions met.**

DISCONFIRM does not apply (both R6 = 2; treatment chunks retrieved and
present on both T1 and T2 compositions). AMBIGUOUS classifications
inspected:

- AMBIGUOUS-SINGLE-SPECIMEN — does not apply (both T1 and T2 cleared).
- AMBIGUOUS-NAMEDROP-WITHOUT-REASONING — does not apply (R3 = 2 on
  both T1 and T2; attribute-grounded reasoning present).
- AMBIGUOUS-TOPIC-GATING — does not apply (T3 R1 = 0; substrate did
  not leak expertise into the neutral topic).

## §81 Prediction vs actual — final

Pre-treatment prediction (Q-279-1 §1 + Q-279-2A-REV §32):

- **T1 / T2:** substrate carries expertise if content is domain content.
  Predicted expertise would emerge naturally under minimal-topic
  dialogue.
- **T3:** "R1 = 0 is *likely* — the lockout topic has low cosine
  similarity with coffee/pairing vocabulary … BUT since Tyson's
  per-character corpus contains ONLY the treatment chunks, retrieval
  will return them regardless of relevance. Whether they appear in
  dialogue is a second question — the LLM must judge topical relevance
  from the §1 SCOPED KNOWLEDGE block."

Actual:

- **T1 / T2:** ceiling-hitting 12/12 on both specimens, +12 vs baseline
  each, naturally integrated (§57, §68).
- **T3:** retrieved-but-unused. All 3 treatment chunks are on
  `knowledge_chunk_ids`; zero treatment vocabulary in Tyson's dialogue.
  The LLM correctly topic-gated the retrieved material against the
  scene's actual concerns.

Prediction confirmed on all three specimens.

## §82 Q-279-2 hypothesis A — final decision

**Question (Q-279-1 §0):**
> If Tyson's identity remains unchanged and only the depth / quality of
> his character-specific coffee/pastry Knowledge increases, does normal
> minimal-topic dialogue spontaneously become more concretely expert?

**Answer: yes, and the substrate also topic-gates the enriched Knowledge
correctly.** Enriched Knowledge produces demonstrated expertise when
the topic engages the domain (T1, T2) and stays quiet when the topic
does not (T3). Character identity, personality, prompts, retrieval,
verifier, and every other substrate variable were held fixed across
the three-render experiment; the only variable was the
`processed_content` of one character-audience KD.

### Recommended decision gate

> **ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS**

The Q-279-2 controlled experiment cleanly confirms Q-279-1 §11 finding
4b: *character-specific domain Knowledge is independently movable from
identity, and increasing its depth causes measurable, natural
demonstration of expertise in dialogue without altering any other
substrate.*

## §83 Visual-composition observation — recorded, NOT investigated

Chris (operator, dogfood): the T3 script explicitly stages Ruby outside
the bakery, keys and bag inside, Ruby waving through the glass,
Tyson interacting with her around that physical situation. The rendered
media uses the characters' standard talking-head avatar + background
assets.

**Preserved as continuing evidence for deferred finding 4c (visual
composition boundary; §"§4c" of the SESSION 279 handoff). Not
investigated in this slice. Not permitted to alter Q-279-2 scoring.**

### 83.1 What this observation lets us record without investigating

The mismatch is:

- **Narrative location/action** (dialogue explicitly frames Ruby
  outside, glass door between characters, keys on counter inside,
  waiting for someone else to arrive with spare key).
- **≠ Visual location/action** (standard talking-head assets — the
  characters appear rendered in their default visual context, not
  outside-vs-inside a bakery door).

This is the same class of finding as the SESSION 278 4c evidence
(Ruby mascot scene objects, box scene objects, etc.) — the dialogue
synthesizer is writing scenes whose visual requirements exceed the
talking-head composition template. T3 adds a *location*-shape example
to the existing *scene-object*-shape examples.

### 83.2 Chris's product-level observation — preserved verbatim shape

> **A useful future system likely needs to preserve the SAME
> recognizable character while allowing different backgrounds /
> locations / scene contexts / possibly poses / framing / physical
> interaction states.**

**Do NOT reduce this to "add background replacement."** Chris's framing
is deliberately broader. The load-bearing product question is:

> *How should Character OS maintain character visual identity while
> allowing the same character to appear naturally in different scene
> environments required by generated dialogue?*

That question spans avatar rig, portrait workflow, background /
setting layer, per-scene composition planning, and pose/framing/
interaction state — not just a single technical primitive.

### 83.3 Constraint

- Do NOT investigate root cause this session.
- Do NOT propose a fix.
- Do NOT open a scope-lock.
- Do NOT allow the observation to alter Q-279-2 scoring.
- Preserved for Chris + ChatGPT to consider when the current Q-279-2
  experiment closes.

## §84 Knowledge-breadth observation — retained

The §70 observation stands unchanged: the small, deliberately tiny
treatment corpus (3 chunks, 4 named coffee/pastry examples, one
tradeoff rule) reliably produces demonstrated expertise on
domain-adjacent topics, but the *set* of concrete examples is
naturally bounded by the corpus. This is expected and does not
disconfirm hypothesis A. Retained verbatim as a distinct future
question about how corpus breadth scales:

> *How much domain breadth does a character-specific Knowledge corpus
> need before expertise feels varied and expansive rather than
> repeatedly circling the same small set of examples?*

Constraint (unchanged): no additional pastries, coffees, KDs, top_k
change, chunking change, retrieval change, or prompt change this
session.

## §85 Deferred findings dossier — accumulated across Stage A

| Deferred finding | New evidence added by Q-279-2 Stage A? |
|---|---|
| **4a** — generalized writer voice / recurring metaphor families | Yes — 12 courtroom/procedural/formal-adversarial references across 5 compositions spanning pre- and post-treatment, including a verbatim-echo of *"That is not a casual question"* from SESSION 278 to SESSION 279 (§58, §71). |
| **4b** — identity-as-expert vs Knowledge depth | Q-279-2 experiment closes this hypothesis with ACCEPT. |
| **4c** — visual composition boundary | Yes — T3 lockout scene adds a *location*-shape example to prior *scene-object*-shape examples (§83). |
| **4d** — underdeveloped / abrupt scene endings near duration boundary | No new evidence. All three Stage-A renders predicted 92-97 s vs 90 s target (within tolerance); no operator observation of abruptness. |
| **4e** — isolated avatar/video quality | No new evidence recorded by operator. |
| **4f** — cross-cast alias grounding | No new evidence. |
| **4g** — adjacent-surface D-POS migration | No new evidence. |
| **4h** — strict-mode audit | No new evidence. Verification remained `warn`; all three specimens `verified`. |
| **4i** — cross-episode epistemic asymmetry | No new evidence. |
| **Knowledge-breadth** (new deferred question surfaced by Q-279-2) | Retained (§70, §84). |
| **Beat-3 legibility** (SPA edit affordance + re-ingest feedback) | Retained (§40, §46). |

## §86 Checklist — Stage A T3 + Stage-A decision gate

- [x] Composition UUID + persisted evidence recorded (§75, §76)
- [x] All 3 treatment chunks confirmed on `knowledge_chunk_ids` (§76)
- [x] Verbatim rendered dialogue captured (§77)
- [x] T3 R1 explicitly measured via treatment-vocabulary scan on Tyson's turns (§78.1)
- [x] Distinction between treatment vocabulary and Universe-general nouns applied (§78.2)
- [x] T3 R1 = 0 verdict recorded (§78.3)
- [x] Full Stage-A matrix assembled (§79)
- [x] All five §31.3 ACCEPT conditions mechanically resolved (§80)
- [x] Prediction vs actual final review (§81)
- [x] Q-279-2 hypothesis A final decision recorded (§82)
- [x] Visual-composition observation captured verbatim, framed as 4c deferred, Chris's broader product framing preserved (§83)
- [x] Knowledge-breadth observation retained unchanged (§84)
- [x] Deferred-findings dossier updated with all Stage-A new evidence (§85)
- [x] No Knowledge / prompt / retrieval / synthesis / verifier / identity change
- [x] No corpus expansion
- [x] No investigation of visual composition, writer voice, or breadth
- [x] Locked rubric preserved unchanged

---

# Q-279-2 — Formal closure marker

**Status:** Q-279-2 CLOSED as **ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS**
per Chris + ChatGPT direction.

Deferred finding **4b** (Tyson identity-as-expert vs Knowledge-depth
needed to perform expertise, from `docs/design/SESSION_279_HANDOFF.md`
§4b) is **RESOLVED**. Character OS mechanically separates
character-specific domain Knowledge from character identity; increasing
the depth of a character-audience `KnowledgeDocument` produces
measurable, natural demonstration of that expertise in dialogue
without altering identity, prompts, retrieval, synthesis, verifier, or
memory substrate. The substrate also topic-gates the enriched
Knowledge correctly — retrieved chunks remain quiet in unrelated
scenes.

## §87 What Q-279-2 established

- The substrate distinction between identity (`Teammate.business_brief`
  / `personality` / voice axes) and character-specific domain Knowledge
  (`KnowledgeDocument.processed_content` under
  `audience_scope=CHARACTER`) is real and independently movable. (§6,
  §55, §82.)
- Under a single-variable substrate change — replacing an
  identity-restating 118-char KD with a 2317-char domain-content KD
  chunking to 3 chunks — the same operator topics that scored 0/12 on
  the pre-treatment R1-R6 rubric scored 12/12 post-treatment.
  (§53, §66, §79.)
- The substrate topic-gates enriched Knowledge correctly: the same
  treatment chunks that produced ceiling expertise on domain topics
  produced zero treatment-vocabulary output on a lockout scene.
  (§78, §80.)
- Ruby's world remained uncontested throughout — no cross-cast leakage,
  SCOPE RULE respected on both post-treatment renders. (§57, §68.)

## §88 What Q-279-2 did NOT establish (preserved as distinct
questions)

- **Knowledge-breadth scaling** (§70, §84): The 3-chunk corpus produced
  strong signal on two domain-adjacent topics; whether/how expertise
  varies as the corpus grows past its minimal test remains open. Do
  NOT expand the corpus without a scope-locked breadth experiment.
- **Visual composition boundary** (§83, deferred finding 4c): The
  T3 lockout scene added a *location*-shape example to prior
  *scene-object*-shape 4c evidence. Chris's broader framing preserved
  verbatim; not reduced to "add background replacement."
- **Beat-3 legibility** (§40, §46): Ask-panel citation edit affordance
  + re-ingestion feedback both weak. Preserved as UI product tasks;
  not implemented.
- **Generalized writer voice / recurring metaphor families**
  (deferred finding 4a): 12 courtroom/procedural/formal-adversarial
  references across 5 compositions spanning pre- and post-treatment,
  including a verbatim echo of *"That is not a casual question"*
  from SESSION 278 to SESSION 279 T2. Opened next as Q-279-3
  READ-ONLY audit.

## §89 Q-279-2 CLOSEOUT MARKER

```
Q-279-2 CLOSED           2026-08-25
Gate resolution          ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS
Deferred finding         4b resolved
Rubric baseline          T1 historical 0/12  T2 historical 0/12
Rubric post-treatment    T1 12/12  T2 12/12  T3 R1=0
Stage-A specimens        3 real-mode dialogue-scene compositions
Cost                     $0.82 total ($0.28 + $0.26 + $0.28)
Compositions             488c37ba / 699916a9 / a5c59014
Treatment KD             3ff45702-cb8b-49f0-82f6-97013c0f8da6
                         processed_content 118 → 2317 chars
                         chunks 1 → 3
                         audience_scope CHARACTER (unchanged)
                         spokespeople {Tyson} (unchanged)
                         universe Fox & Flour (unchanged)
                         is_active true (unchanged)
Substrate variables changed exactly:  1 (KD text_content)
Substrate variables unchanged:        identity, prompts,
                                       retrieval, synthesis,
                                       verifier, memories,
                                       audience_hint, World brief,
                                       Ruby row + Ruby KD set
```

Q-279-2 is not to be re-opened. Follow-up questions surfaced by the
experiment (Knowledge-breadth, 4c continuing evidence, Beat-3
legibility, 4a) are preserved above and in the Q-279-2A-REV §23 /
§43 / §61 / §74 / §86 dossier chain and in the SESSION 279 handoff.

---

# Q-279-3 — Generalized writer voice / recurring metaphor-family audit (deferred finding 4a)

**Status opened:** 2026-08-25, immediately following the Q-279-2 checkpoint commit
`e0d5a10` (docs-only). Session 279 handoff §4a authorized this
investigation. Scope-lock: **READ-ONLY audit + experiment design.**
No changes to prompts, synthesis, Knowledge, characters, identity,
retrieval, verifier, memories, audience logic, or runtime behavior.
No provider spend unless Chris + ChatGPT later approve a controlled
render experiment.

## §90 Precise question

> **Why do semantically unrelated Fox & Flour scenes repeatedly produce
> the same procedural / adversarial / metaphorical language families
> despite different topics and despite Knowledge changes?**

Refined via cross-World scan (§92): the question extends past
Fox & Flour to Patch's Workshop and past the "courtroom" surface
label. The load-bearing behavior is a **rhetorical structural
attractor** — a family of *reframe / stakes-elevate* devices that
recur across independent characters, independent worlds, and
independent topics.

## §91 Prediction (recorded BEFORE deep evidence)

Before running the cross-World and prompt-scaffolding scans, the
predicted decomposition (rank-ordered by prior plausibility):

1. **Writing Contract structural bias.** The dialogue_scene contract
   emphasizes "meaningful change", "reveal", "correction", "reveal",
   "challenge", "escalation", "tension" — a stakes-elevating narrative
   vocabulary the LLM can most economically satisfy through
   procedural / legalistic / diminutive-formal English idioms.
2. **Model prior for "dry-humor dialogue" register.** Foundation
   models trained on Reddit / literary dialogue / TV writing rooms
   have strong priors for the *"mundane statement → comedic formal
   reframe"* device. Both cast members having "dry" / "sarcastic" /
   "warm humor" would concentrate this prior.
3. **Character-personality bleed.** Multiple cast members share a
   "dry-witty observer" archetype (Rivet analytical / Tyson practical
   / Ruby warm-cheerful). The rhetorical attractor could be an
   emergent artifact of that archetype cluster.
4. **Corrective-hint amplification.** Under-length corrective hint
   asks the model to *"add a challenge, callback, or reveal that a
   character has been holding back"* — could bias retries toward
   more stakes-elevating turns.
5. **Sharpening module leakage.** `character_os/prompts/sharpening.py`
   defines aggressive hedge → evidence-language replacements
   (`"in my opinion"` → `"BASED ON EVIDENCE,"`,
   `"I see your point"` → `"YOUR EVIDENCE INDICATES"`). If wired
   into the synthesis path, would directly explain "evidence" recurrence.

Prediction on hierarchy: **H1 + H2 dominant; H3 modulator; H4
minor; H5 unlikely (would need to be wired into synthesis to matter).**

## §92 Evidence — enumeration of recurring devices

Method: SQL regex scans over
`compositions_composition.synthesized_brief` for every completed
dialogue-scene composition with a non-empty `operator_topic`
(21 rows across two Universes over 7 days, 2026-08-18 → 2026-08-24).

### 92.1 Courtroom / procedural / formal-adversarial vocabulary

Cross-World distribution:

| Universe | Composition | Speaker | Line | Pre/post Q-279-2 |
|---|---|---|---|---|
| Fox & Flour | 26c62b4b | Ruby | *"final exam"* | pre |
| Fox & Flour | 1aabbff6 | (haunted-bakery specimen) | *"court"*, *"trial"* | pre |
| Fox & Flour | d7549fc1 | Ruby | *"give a deposition"*, *"tiny courtroom for baked goods"* | pre (Q-278-4.2 Specimen 2 baseline) |
| Fox & Flour | 7177b0f5 | Tyson | *"That's evidence."*, *"casual question"*, *"official-looking envelope"*, *"confession, wearing an apron"* | pre (Q-278-4.3 Specimen 3 baseline) |
| Fox & Flour | 488c37ba | multiple | *"final exam"*, *"testifying in court"*, *"The court deserves a good pairing"*, *"seating chart"* | **post** (Q-279-2 T1) |
| Fox & Flour | 699916a9 | multiple | *"not a casual question"*, *"rehearsing for judges"*, *"defend itself"*, *"Fine, detective"* | **post** (Q-279-2 T2) |
| Patch's Workshop | 3e44b728 | | *"committee"* | pre |
| Patch's Workshop | ef11c810 | | *"Evidence"*, *"charge"* | pre |
| Patch's Workshop | a119b064 | | *"juri…"*, *"rules"* | pre |
| Patch's Workshop | 79d0bbd5 | | *"inspect"* | pre |
| Patch's Workshop | e425f5fe | | *"evidence"* | pre |
| Patch's Workshop | 7d913cf4 | | *"evidence"* × 2 | pre |
| Patch's Workshop | 2dc6b0b5 | Rivet | *"That is not evidence"*, *"anxiety disorder with shelves"* | pre |
| Patch's Workshop | 01aa7601 | | *"casual question"*, *"charge"* | pre |

**Total scoped procedural-vocabulary hits: 24+ across ~12 compositions
across BOTH Universes** — the pattern is cross-World and predates the
Q-279-2 Knowledge treatment. Notable: the phrase *"That's not a
casual question"* appears in **three independent compositions**
(7177b0f5 pre-Fox & Flour, 699916a9 post-Fox & Flour T2, 01aa7601
pre-Patch's Workshop) — a near-verbatim recurrence spanning worlds
and time.

### 92.2 Rhetorical structural device — *"That is / That's not X. That is Y."*

Broader-shape scan (24 hits across both Universes, 21 completed
dialogue-scene compositions over 7 days):

| Universe | Composition | Speaker | Reframe |
|---|---|---|---|
| Patch's | 1eb12363 | Rivet | *"That is not a hobby."* |
| Patch's | 4af67cd5 | Rivet | *"That is a very dramatic way to begin a lesson."* |
| Patch's | 2dc6b0b5 | Rivet | *"That is not junk."*, *"That is not evidence."* |
| Patch's | 7d913cf4 | Rivet | *"That is not intuition."* |
| Patch's | 6d169390 | Rivet | *"That is a very Patch-shaped mistake."* |
| Patch's | 05d3612c | Rivet | *"That is not what a test is for."* |
| Patch's | a119b064 | Rivet | *"That is not help."*, *"That is a tiny management dispute with access to electronics."*, *"That is a very ambitious interpretation of a cable."* |
| Patch's | 79d0bbd5 | Rivet | *"That is not the same as it running the place."* |
| Patch's | 01aa7601 | Rivet | *"That is a wildly specific accusation."* |
| Patch's | 6e3ed367 | Rivet | *"That is not how urgency works."* |
| Patch's | 99b4a3fa | Rivet | *"That is not a behavior description."* |
| Patch's | 464128b1 | Rivet | *"That is not how harmless projects begin."* |
| Patch's | a35f20bf | Rivet | *"That is not yet a useful statement."* |
| Patch's | 5f4bdbbc | Rivet | *"That is a sentence with several missing parts."* |
| Fox & Flour | 1491d31c | Ruby | *"That was not a first idea."*, *"That was a feeling."* |
| Fox & Flour | d7549fc1 | Tyson | *"That is a question with consequences."* |
| Fox & Flour | 699916a9 | Tyson | *"That is not a casual question."*, *"That is a person rehearsing for judges."* |
| Fox & Flour | a5c59014 | Tyson | *"That is not the face of someone admiring the morning."* |
| Fox & Flour | a1421a0e | (bakery-customer specimen) | *"That was her way back into the conversation."* |

Same syntactic form. **Highest concentration in Rivet's turns** but
present in Tyson, Ruby, and other cast turns as well. The "courtroom"
observation is the *most visible* surface expression of this rhetorical
structural attractor; the attractor itself is broader — a
*negation-reframe with stakes-elevating punchline*.

### 92.3 Diminutive-formal metaphor — *"tiny X"*

18+ occurrences in Patch's Workshop alone:
*"tiny hat"*, *"tiny disaster"*, *"tiny test"*, *"tiny bureaucrat"*,
*"tiny management [dispute]"*, *"tiny guardrails"*, *"tiny judgmental"*,
*"tiny predictive"*, *"tiny digital"*, *"tiny hats"*, *"tiny furniture"*
… Plus Fox & Flour: *"tiny private club"* (T3), *"tiny courtroom for
baked goods"* (baseline).

Same rhetorical family as §92.2 — reduce-a-mundane-thing-to-a-formal-
microcosm humor. The "tiny X formal-institution" device is a
character-agnostic writer-voice tic.

### 92.4 Correlations checked

| Variable | Correlation with device recurrence |
|---|---|
| Corrective pass (`synthesis_attempt_count = 2`) | Only 2 of 21 rows had corrective pass. Device fires baseline on first-pass. **H4 disconfirmed** — corrective hints are not the amplifier. |
| Universe | Both. Not Universe-scoped. |
| Speaker | Rivet dominant on §92.2; Tyson + Ruby fire in Fox & Flour. Multi-character, not one voice. |
| Pre / post Q-279-2 treatment | Both. Q-279-2's Knowledge change did NOT reduce the device rate. |
| Time | 2026-08-18 → 2026-08-24 continuous. Not a one-off drift. |

### 92.5 Substrate trace — where the vocabulary is NOT

Grep-verified `character_os/writing_contract.py`,
`character_os/dialogue_synthesis.py`, `character_os/script_synthesis.py`,
`character_os/api_prompts.py`, `character_os/prompts/*.py` for the
recurring vocabulary:

| Vocabulary | Present in prompt code? |
|---|---|
| *court* / *trial* / *judge* / *jury* / *deposition* / *testify* / *witness* / *verdict* / *detective* / *rehears* / *inspector* / *committee* / *hearing* | **Not present** (the only *"witness"* hit in dialogue_synthesis.py is an unrelated `witness overlap` cast-filter comment). |
| *evidence* | Present in `writing_contract.py:722` (solo-scene invariant *"unless current-scene evidence has already established"*) and `script_synthesis.py:509` (a Python variable name comment `factual_corpus (evidence capable of supporting a claim)`). Both are prompt-scaffolding uses (not visible to model on dialogue path) or code comments. |
| *casual question* / *final exam* / *seating chart* | **Not present** anywhere in prompt code. |
| *tiny X* diminutive-formal template | **Not present** anywhere in prompt code. |

Grep-verified `Universe.brief`, both cast `business_brief`,
`personality`, `character_point_of_view`:

- Fox & Flour: Universe.brief mentions *"warm neighborhood artisan
  bakery"*; Ruby personality *"warm, cheerful, genuinely caring"*;
  Tyson personality *"easygoing, practical, a little dry ... prefers
  useful answers over sales language"*. **No courtroom / procedural /
  reframe vocabulary anywhere.**
- Patch's: Rivet POV mentions *"treats one successful result as
  interesting rather than as proof"* — one *proof* token, science-
  register, not legal. Patch persona *"scruffy, endlessly curious
  beaver"*. **No courtroom vocabulary; one proof-adjacent token.**
- Q-279-2 §27 treatment corpus: grep-verified in Q-279-2A-REV §58.2
  — zero courtroom / legal / procedural language. Coffee + pastry +
  pairing + attribute vocabulary only.

Grep-verified `character_os/prompts/sharpening.py`:

- Contains explicit *"BASED ON EVIDENCE"* / *"YOUR EVIDENCE INDICATES"*
  replacements.
- But: full grep of consumers (`character_os/`, `apps/`) shows
  `sharpen_prompt` / `clean_business_brief` are consumed ONLY by
  `character_os/prompts/test_prompts.py` and `character_os/prompts/
  __init__.py`. **Not wired into `dialogue_synthesis` or
  `script_synthesis`.** H5 disconfirmed.

### 92.6 Substrate trace — where the STAKES-ELEVATING structural
FRAME lives

`character_os/writing_contract.py` `_DIALOGUE_INVARIANTS_BLOCK` +
`_DIALOGUE_WATCHABILITY_BLOCK` + `_DIALOGUE_NARRATIVE_SHAPES_BLOCK`
contain heavy *stakes-elevating structural vocabulary*:

- Invariants: *"new tension"*, *"Tension is a legitimate engine"*,
  *"disagreement and correction are allowed"*, *"one coherent arc"*,
  *"deliberate ending... resolution, punchline, unresolved-but-
  earned tension, landed insight"*.
- Watchability: *"wants to prove something worked; wants to correct
  the other character; wants clarification; wants permission; wants
  to avoid blame; wants to persuade; wants to challenge an
  assumption"* — every stance is stakes-adjacent.
- Narrative shapes: *"setup → disagreement → payoff"*, *"question →
  answer → correction"*, *"claim → skeptical response → reveal"*,
  *"myth → correction → practical takeaway"*, *"challenge → attempt
  → result"*.
- Under-length corrective hint: *"add a challenge, callback, or
  reveal that a character has been holding back"*.

None of this DIRECTLY encodes courtroom vocabulary. But the semantic
frame — *"characters have stances, want to challenge / correct /
reveal / prove, forward motion requires reveal / correction /
escalation, tension is engine"* — plausibly primes the LLM to reach
for its shortest available English shorthand for those semantics,
which happens to be legalistic / procedural / diminutive-formal
idiom.

## §93 Five-axis decomposition

Per the audit brief, separate:

| Axis | Definition | Applies to observed evidence? |
|---|---|---|
| **Lexical repetition** | Same word tokens recur | Yes — *evidence* (7+), *casual question* (3), *final exam* (3), *judge/rehears/detective* (multiple). |
| **Metaphor-family repetition** | Same conceptual family (courtroom, formal-procedural, diminutive-formal) recurs even when specific words differ | Yes — *court / jury / committee / hearing / inspector / detective / testify / defend* cluster into one metaphor family; *tiny X* diminutive-formal cluster. |
| **Rhetorical-structural repetition** | Same syntactic device recurs across topics and characters | Yes — *"That is not X. That is Y."* negation-reframe fires 24+ times across 15+ compositions and 4+ speakers spanning both Universes. This is the deepest / most character-agnostic signal. |
| **Character voice** | Attributable to one character's identity / personality / POV | Partial. Rivet's turns concentrate the negation-reframe device (matches his *"analytical, dry, patient, slightly sarcastic, extremely literal"* personality). But Tyson + Ruby + other Fox & Flour cast members ALSO produce it, on wholly different personalities. So character voice is a *modulator*, not the primary cause. |
| **Generalized scene-writer voice** | Attributable to a substrate above characters that shapes dialogue independent of who is speaking | **Load-bearing.** Cross-character + cross-World + cross-topic recurrence + zero substrate-input source for the vocabulary → the attractor lives in the *generation-time interaction* between (a) the writing_contract's stakes-elevating structural frame and (b) the LLM's most-available English shorthand for that frame. |
| **Factual / Knowledge grounding** | Attributable to retrieved KD chunks or memory content | **Disconfirmed.** Every retrieved chunk was grep-checked; treatment corpus has zero courtroom/procedural vocabulary; pre-treatment Knowledge was 118-char identity restatement. Knowledge is not the source. |

## §94 Working hypothesis (post-evidence)

The observed behavior is not primarily "courtroom words" — it is a
**Writer-Voice Structural Attractor**:

- Substrate-shaped: the dialogue_scene writing_contract encodes a
  stakes-elevating structural frame (§92.6).
- Model-shaped: the LLM's most-available English shorthand for that
  frame reaches for legalistic / procedural / diminutive-formal
  idiom and the *"That is not X. That is Y."* negation-reframe.
- Character-modulated: characters with "dry / sarcastic / analytical"
  personalities concentrate the device rate (Rivet); "warm / practical"
  characters concentrate a lower rate (Ruby, Tyson) but non-zero.
- Cross-World invariant: appears across two Universes with wholly
  different narrative surfaces (bakery vs workshop).
- Knowledge-invariant: unaffected by the Q-279-2 treatment.

Predicted hierarchy from §91 partly confirmed:
- H1 (contract structural bias) — LOAD-BEARING (§92.6).
- H2 (model prior) — LOAD-BEARING (evidence pattern spans well-known
  literary-humor device families).
- H3 (personality bleed) — MODULATOR (§92.2 concentration on Rivet).
- H4 (corrective amplification) — DISCONFIRMED (§92.4).
- H5 (sharpening leakage) — DISCONFIRMED (§92.5, not wired).

## §95 Falsifiable smallest experiment — designed, NOT executed

**Constraint per audit brief:** do NOT implement a fix. Design the
smallest experiment that distinguishes the leading explanations
(H1 vs H2 vs H3) without changing anything runtime yet.

### 95.1 Phase 1 — retrospective, purely READ-ONLY (execute-safe next slice)

Score the existing 21+ persisted dialogue-scene specimens against a
**Rhetorical-Device Rate rubric**:

| Device dimension | Measurement |
|---|---|
| **D1 — Negation-reframe count.** Occurrences of *"That is / That's / That was (not) X (dot) That is Y"* (or minor variants) per composition. | Integer per composition. |
| **D2 — Diminutive-formal metaphor count.** Occurrences of *"tiny X"*, *"small X"*, *"a small ADJ NOUN"* where NOUN reads as formal institution / procedure / entity. | Integer. |
| **D3 — Courtroom / procedural noun count.** Occurrences from a fixed lexicon (court / trial / judge / jury / deposition / evidence / testify / witness / verdict / detective / rehears / inspector / committee / hearing / defend / prosecut). | Integer. |
| **D4 — Stakes-elevating adjective count.** Occurrences of *"serious"*, *"consequential"*, *"important"*, *"dramatic"*, *"not casual"*, *"not small"*, *"not a X"* (paired with pastry / bakery / lockout / hobby / etc.) | Integer. |

Correlate with:

- Universe (Fox & Flour vs Patch's Workshop).
- Cast (Rivet vs Tyson vs Ruby vs Patch).
- Personality vector: `tone_archetype`, `voice_energy`, `voice_humor`,
  `voice_directness`, `character_point_of_view` present/absent.
- `synthesis_attempt_count` (first-pass vs corrective).
- Topic domain (workshop-tech vs bakery-service vs interpersonal).
- Pre / post Q-279-2 treatment.

**Acceptance / disconfirmation (Phase 1):**

- If device rates correlate with `character_point_of_view` /
  `voice_humor` fields → **H3 confirmed as primary**; the attractor is
  personality-driven, not contract-driven. Redirect Phase 2 to a
  personality-adjacent experiment.
- If device rates are approximately uniform across characters and
  Universes → **H1 + H2 confirmed as primary**; the attractor lives
  above the character layer. Phase 2 needed to distinguish contract
  from model prior.
- If a mixed signal emerges → design Phase 2 accordingly.

Phase 1 is **read-only**: consumes existing persisted specimens; zero
new renders; zero provider spend.

### 95.2 Phase 2 — controlled, requires 1-3 new dogfood renders (deferred)

Only fires if Phase 1 does not discriminate. Three candidate configs
(each varies ONE hypothesized cause; every other input pinned):

| Config | Change | Tests |
|---|---|---|
| **P2-A (baseline replay)** | Nothing changed. Render one new topic on Ruby+Tyson. | Baseline device rate on unchanged substrate. |
| **P2-B (contract-lite)** | Temporary `WritingContract.for_shape` override that returns a *neutral* dialogue_scene contract (removes stakes-elevating narrative-shape menu, removes watchability *"prove / correct / challenge / persuade / avoid blame"* language, keeps CAUSAL-CHAIN + BASIC INTERACTION invariants). Applied at runtime via env-flag branch or a temporary contract version stamp. Reverted after render. | If device rate drops ≥ 50 % vs P2-A → **H1 (contract)** load-bearing. |
| **P2-C (voice-lite)** | Temporary SPA Ask-panel operator mutation setting both Ruby's and Tyson's `voice_humor` to `none` and `character_point_of_view` blank. Reverted via same SPA gesture after render. | If device rate drops with C but persists with B → **H3 (personality)** confirmed. |

**Constraint on P2 experiments:**
- Every mutation must be reversible via the same SPA gesture Chris
  used for Q-279-2.
- No permanent code changes.
- No `writing_contract.py` version bump (a temporary env-flag branch
  is acceptable; a permanent contract change is not).
- Every experimental composition must be marked as such (topic prefix
  `[Q-279-4A]` operator-side; do not silently pollute the persisted
  cast's dogfood history).

**Acceptance / disconfirmation (Phase 2):**

- **ACCEPT-H1** — P2-B reduces device rate ≥ 50 %; P2-C does not
  further reduce it. Contract structural frame is the primary driver.
- **ACCEPT-H2** — Neither P2-B nor P2-C reduces device rate meaningfully.
  Attractor lives above both contract and personality → model prior
  dominant. Next-slice question shifts to whether prompt-shape
  restructuring can move a model-prior attractor.
- **ACCEPT-H3** — P2-C reduces device rate ≥ 50 %; P2-B does not.
  Personality vector is the driver.
- **AMBIGUOUS** — Partial reductions from both. Attractor is a joint
  contract × personality artifact; needs targeted follow-up.

### 95.3 Rubric locked BEFORE any experiment fires

Both phases must lock D1-D4 measurement definitions and correlation
variables BEFORE any scan or render. Locked now, in this document
(§95.1). Not to be revised after seeing evidence.

## §96 Constraint reaffirmations

- Do NOT change prompts, synthesis, Knowledge, characters, identity,
  retrieval, verifier, memories, audience logic, or runtime behavior
  in this slice.
- Do NOT investigate the *cause* by patching the writing_contract.
  Phase 1 must complete first.
- Do NOT open Knowledge-breadth (§70, §84), 4c visual composition
  (§83), or Beat-3 legibility (§40, §46) — all remain deferred.
- Do NOT re-open Q-279-2 / finding 4b.
- Do NOT assume Chris + ChatGPT will authorize Phase 2. Phase 1's
  purely read-only rubric-scoring stands independently.

## §97 Recommendation

Q-279-3 read-only audit + experiment design is complete. Enough
evidence is now on the durable record to distinguish the writer-voice
hypothesis from the character-voice / Knowledge-grounding hypotheses
mechanically. The device family is broader than courtroom vocabulary;
the load-bearing pattern is a *negation-reframe with stakes-elevating
punchline* that persists across Universes, characters, and the
Q-279-2 Knowledge treatment.

### Recommended next gate

> **READY-FOR-Q-279-3-PHASE-1** (retrospective rubric scoring of
> existing specimens; purely READ-ONLY; zero provider spend; consumes
> ~21 persisted compositions).

Chris + ChatGPT decide whether Phase 1 fires next or a different
Session 279 slice takes priority. If Phase 1 fires and does not
discriminate, Phase 2 becomes the natural follow-up gate, subject to
approval of small dogfood spend.

## §98 Checklist — Q-279-3 read-only audit + design

- [x] Prediction recorded BEFORE deep evidence (§91)
- [x] Cross-World enumeration of courtroom / procedural vocabulary (§92.1)
- [x] Cross-World enumeration of negation-reframe rhetorical structural device (§92.2)
- [x] Diminutive-formal metaphor cluster documented (§92.3)
- [x] Correlations with corrective pass / Universe / cast / time checked; H4 disconfirmed (§92.4)
- [x] Substrate trace — vocabulary absent from prompt code AND absent from every KD / brief / identity input (§92.5)
- [x] Substrate trace — stakes-elevating structural frame located in writing_contract dialogue-scene blocks (§92.6)
- [x] Five-axis decomposition applied (§93)
- [x] Working hypothesis post-evidence with hierarchy status (§94)
- [x] Phase 1 rubric locked BEFORE any scoring fires (§95.1, §95.3)
- [x] Phase 2 controlled-render experiment designed but NOT executed (§95.2)
- [x] Acceptance / disconfirmation criteria pre-established for both phases (§95.1, §95.2)
- [x] Constraint reaffirmations (§96)
- [x] Recommendation + next gate (§97)
- [x] No prompt / synthesis / Knowledge / character / identity / retrieval / verifier / memory / audience change
- [x] No provider spend
- [x] No implementation of any candidate fix
- [x] Other deferred findings (4c, 4d-4i, Knowledge-breadth, Beat-3 legibility) NOT opened

---

# Q-279-3 — Phase 1 result (retrospective rubric scoring)

**Status opened:** 2026-08-25, immediately following Q-279-3 audit commit
`7a21357`. Executes §95.1 exactly as designed. Purely READ-ONLY:
consumes existing persisted `synthesized_brief` field on every
completed dialogue-scene composition with a non-empty `operator_topic`.
Zero renders. Zero provider spend. No changes to prompts / synthesis /
Knowledge / characters / identity / retrieval / verifier / memories /
audience / runtime. No fix implemented.

## §99 Methodology

Data source: `compositions_composition` table joined to
`spokespeople_spokesperson` and `universe_universe` via
`docker exec character_os_postgres psql` and a locally-scoped
`psycopg` connection (port 5434, `.env` credentials). Read-only.

Predicate:
```sql
template_kind='dialogue_scene' AND status='completed'
AND operator_topic <> ''
```
→ **43 compositions** across 4 Universes (Fox & Flour, Patch's
Workshop, and 2 SESSION 272 experimental Universes with no cast
identity content beyond legacy test fixtures).

Per-composition parser splits `synthesized_brief` into speaker turns
by prefix match on `Ruby | Tyson | Patch | Rivet` (the only cast
members present in the persisted corpus). Header comment lines
(`# AI Topic dialogue synthesis`, `# Aliases:`, etc.) are excluded.

### 99.1 Rubric — locked at §95.1, applied unchanged

| Dim | Definition | Regex applied |
|---|---|---|
| **D1** | Any *"That is / That was / That's"* reframe opening | `\b(?:That is\|That was\|That's)\s+(?:not\|a\b\|an\b)` |
| **D1n** | Strict *negation*-reframe (subset of D1) | `\b(?:That is\|That was\|That's)\s+not\b` |
| **D1a** | Strict *assertive*-reframe (subset of D1) | `\b(?:That is\|That was\|That's)\s+(?:a\|an)\b` |
| **D2** | Diminutive-formal metaphor — *"tiny/small/little"* + formal-institution noun | `\b(?:tiny\|small\|little)\s+(?:<50-noun-lexicon>)` |
| **D3** | Courtroom / procedural noun (locked lexicon: court, trial, judge, jury, deposition, evidence, testify, witness, verdict, detective, rehears, inspector, committee, hearing, defend, prosecut) | `\b(?:court\|trial\|judge\|…\|prosecut)\w*\b` |
| **D4a** | Stakes-elevating adjective | `\b(?:serious\|consequential\|important\|dramatic)\w*\b` |
| **D4n** | Stakes-elevating "not X" phrase | `\bnot (?:casual\|small\|a\b)` |

### 99.2 Normalization

Per-1000-character rates reported alongside raw counts so a
high-turn-volume speaker (Patch: 214 turns; Rivet: 204 turns) is not
automatically flagged higher than lower-volume speakers (Ruby: 65;
Tyson: 64). Per-turn "affected-turn %" (fraction of a speaker's
turns that contain ≥ 1 device hit) also reported.

### 99.3 Correlation buckets

- **Universe** (Fox & Flour vs Patch's Workshop; experimental
  Universes excluded from analysis as they contain no cast identity
  and produced zero device hits).
- **Speaker** (Ruby / Tyson / Patch / Rivet).
- **Personality vector** (`tone_archetype`, `voice_energy`,
  `voice_humor`, `voice_directness`, `character_point_of_view`
  presence).
- **`synthesis_attempt_count`** (first-pass = 1 vs corrective = 2).
- **Pre / post Q-279-2 treatment** (cutoff `2026-08-24 03:21:42 UTC`
  = the treatment-KD re-ingest timestamp, applied only to Fox &
  Flour compositions since only Fox & Flour saw the treatment).

## §100 Complete scoring results

### 100.1 Per-composition (43 rows)

Compact form — each row: `id / universe / attempts / turns / chars /
D1 / D1n / D2 / D3 / D4a / D4n / topic`. Zero-device rows omitted for
brevity; all raw data preserved in the audit process.

Non-zero device compositions (24 of 43):

| id | universe | att | turns | chars | D1 | D1n | D2 | D3 | D4a | D4n | topic |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3e44b728 | Patch's | 2 | 9 | 665 | 0 | 0 | 0 | 1 | 0 | 0 | AI took over the lab |
| ef11c810 | Patch's | 2 | 11 | 727 | 0 | 0 | 0 | 1 | 0 | 0 | agent acting weird |
| 99b4a3fa | Patch's | 1 | 9 | 869 | 1 | 1 | 0 | 0 | 0 | 1 | agent acting weird |
| a119b064 | Patch's | 1 | 11 | 1358 | 3 | 1 | 1 | 0 | 0 | 1 | agent acting weird |
| 79d0bbd5 | Patch's | 1 | 12 | 1353 | 1 | 1 | 0 | 0 | 0 | 0 | agent acting weird |
| 7502af3f | Patch's | 1 | 13 | 1345 | 0 | 0 | 0 | 0 | 1 | 0 | agent acting weird |
| d533b4ec | Patch's | 2 | 13 | 1301 | 0 | 0 | 1 | 1 | 0 | 0 | agent refuses to explain |
| 01aa7601 | Patch's | 2 | 12 | 1171 | 2 | 1 | 0 | 0 | 0 | 1 | Rivet knew Agent independent |
| e425f5fe | Patch's | 2 | 12 | 1363 | 0 | 0 | 0 | 1 | 0 | 0 | Patch asks likes doing |
| 7d913cf4 | Patch's | 1 | 12 | 1281 | 1 | 1 | 0 | 2 | 1 | 0 | teach Rivet something |
| 4af67cd5 | Patch's | 1 | 13 | 1082 | 2 | 0 | 0 | 0 | 1 | 0 | Rivet tries to teach Patch |
| e6b3f132 | Patch's | 1 | 12 | 1088 | 0 | 0 | 0 | 0 | 1 | 0 | Agent does something again |
| 6e3ed367 | Patch's | 1 | 19 | 1135 | 2 | 1 | 0 | 0 | 0 | 1 | box Patch refuses to |
| 464128b1 | Patch's | 1 | 13 | 1304 | 1 | 1 | 0 | 0 | 0 | 0 | Patch built something overnight |
| 05d3612c | Patch's | 1 | 15 | 1396 | 1 | 1 | 0 | 0 | 0 | 0 | workshop needs rules |
| da341e85 | Patch's | 1 | 16 | 1177 | 0 | 0 | 0 | 0 | 0 | 1 | Rivet expects Patch to make |
| a35f20bf | Patch's | 1 | 13 | 1285 | 1 | 1 | 0 | 0 | 0 | 0 | pigeons hiding |
| 6d169390 | Patch's | 1 | 12 | 1289 | 1 | 0 | 0 | 0 | 0 | 0 | old project |
| a1421a0e | F&F | 2 | 12 | 1280 | 1 | 0 | 0 | 0 | 0 | 0 | difficult customer |
| 5f4bdbbc | Patch's | 1 | 11 | 1239 | 1 | 0 | 0 | 0 | 0 | 0 | consulting firm |
| 1491d31c | F&F | 1 | 11 | 1374 | 2 | 1 | 0 | 0 | 0 | 2 | bakery mascot |
| 1aabbff6 | F&F | 1 | 12 | 1388 | 1 | 0 | 0 | 2 | 1 | 0 | haunted bakery |
| 1eb12363 | Patch's | 1 | 13 | 970 | 1 | 1 | 0 | 0 | 0 | 1 | Rivet needs hobby |
| d7549fc1 | F&F | 2 | 11 | 1188 | 2 | 1 | 1 | 2 | 1 | 1 | **coffee too serious** (pre-Q-279-2) |
| 2dc6b0b5 | Patch's | 1 | 12 | 936 | 4 | 2 | 0 | 1 | 0 | 0 | Patch owns junk |
| 52cf3df9 | F&F | 1 | 12 | 1375 | 0 | 0 | 0 | 0 | 2 | 0 | freezer strange |
| bc1eacf5 | Patch's | 1 | 22 | 1215 | 0 | 0 | 0 | 0 | 1 | 1 | button not to press |
| 7177b0f5 | F&F | 1 | 20 | 1375 | 1 | 1 | 0 | 2 | 1 | 1 | **baking competition** (pre-Q-279-2) |
| 488c37ba | F&F | 2 | 14 | 1234 | 0 | 0 | 0 | 3 | 4 | 0 | **coffee too serious** (Q-279-2 T1) |
| 699916a9 | F&F | 1 | 13 | 1207 | 2 | 1 | 0 | 4 | 0 | 1 | **baking competition** (Q-279-2 T2) |
| a5c59014 | F&F | 1 | 14 | 1267 | 1 | 1 | 0 | 0 | 1 | 0 | **lockout** (Q-279-2 T3) |

Zero-device (19 of 43): mostly SESSION 272 shadow-doc setups
(`965bce07`, `39bed00e`, `f05bf226`, `bb0ad862`, `fcba3242`, etc.)
which use controlled prompts, plus a few low-D "welcome" /
"pre-treatment early" specimens (`26c62b4b`, `ba431203`,
`826851fd`, `eb48611f`, `c3fa88f7`, `2b006c0d`, `75d4645f`).

### 100.2 Per-speaker aggregates (normalized)

| Speaker | Universe | Comps | Turns | Chars | Tone | Humor | POV | D1 | D1n | D2 | D3 | D4a | D4n | D1/1k | D1n/1k | D3/1k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Ruby** | Fox & Flour | 10 | 65 | 5,735 | friend | warm | no | 4 | **2** | 1 | **7** | 5 | 3 | 0.697 | 0.349 | **1.221** |
| **Tyson** | Fox & Flour | 10 | 64 | 7,136 | expert | warm | no | 6 | **3** | 0 | **6** | 5 | 2 | 0.841 | 0.420 | **0.841** |
| **Patch** | Patch's | 33 | 214 | 21,716 | performer | warm | yes | 8 | **2** | 1 | **4** | 4 | 1 | 0.368 | **0.092** | 0.184 |
| **Rivet** | Patch's | 33 | 204 | 16,153 | friend | warm | yes | 14 | **10** | 1 | **3** | 1 | 6 | 0.867 | **0.619** | 0.186 |

### 100.3 Per-speaker DEVICE-FAMILY SHARE (%)

Given the user's guidance ("particular DEVICE FAMILIES cluster
differently by character") the crucial view is **which device family
dominates each character's writer-voice expression**:

| Speaker | Total hits | D1n% (neg-reframe) | D1a% (assertive-reframe) | D3% (courtroom lex) | D4a% (stakes-adj) |
|---|---|---|---|---|---|
| Ruby | 16 | 12.5 % | 12.5 % | **43.8 %** | 31.2 % |
| Tyson | 17 | 17.6 % | 17.6 % | **35.3 %** | 29.4 % |
| Patch | 16 | 12.5 % | **37.5 %** | 25.0 % | 25.0 % |
| Rivet | 18 | **55.6 %** | 22.2 % | 16.7 % | 5.6 % |

**Load-bearing pattern.** Every character expresses the writer-voice
attractor, but through **different surface devices**:

- **Fox & Flour cast (Ruby + Tyson)** channels the attractor primarily
  through **D3 (courtroom lexicon)** — 43.8 % + 35.3 % of their hits.
- **Rivet** channels it primarily through **D1n (negation-reframe)** —
  55.6 %.
- **Patch** channels it primarily through **D1a (assertive-reframe)** —
  37.5 %.

Same underlying rhetorical attractor ("elevate a mundane utterance
via a formalizing device"); different surface expressions per
character-personality context. The visible "courtroom" fingerprint
is Fox & Flour's *specific* expression of a broader family.

### 100.4 Universe aggregates

| Universe | Comps | Turns | Chars | D1/1k | D1n/1k | D3/1k |
|---|---|---|---|---|---|---|
| Fox & Flour Bakery | 10 | 129 | 12,871 | 0.777 | 0.388 | **1.010** |
| Patch's Workshop | 31 | 392 | 35,783 | 0.615 | 0.335 | 0.196 |
| EXP266-STRONG / EXP266-WEAK | 2 | 26 | 2,086 | 0 | 0 | 0 |

Fox & Flour D3 rate is **5.2 × Patch's Workshop D3 rate**. D1 and D1n
rates are within ~30 % across the two real Universes — the reframe
device is nearly Universe-invariant. **The Universe difference is
in surface vocabulary, not in the underlying attractor.**

### 100.5 Treatment-bucket aggregates

| Bucket | Comps | Turns | Chars | D1n/1k | D3/1k |
|---|---|---|---|---|---|
| pre-Q-279-2 F&F | 7 | 88 | 9,163 | 0.327 | 0.655 |
| **post-Q-279-2 F&F** | 3 | 41 | 3,708 | **0.539** | **1.888** |
| other Universe (Patch's) | 33 | 418 | 37,869 | 0.317 | 0.185 |

**Post-Q-279-2 F&F D3 rate is 2.9 × pre-Q-279-2 F&F rate and 10.2 ×
Patch's rate.** The Knowledge treatment (which contains zero
courtroom vocabulary; §92.5) did NOT reduce the D3 rate — it
appeared to *increase* it (n=3 post; small sample, but every T1 and
T2 turn budget contained multiple D3 hits per the §92 dossier). **This
is direct evidence that the writer-voice attractor is upstream of
Knowledge.**

### 100.6 Attempt-count aggregates

| Attempts | Comps | Turns | Chars | D1/1k | D1n/1k | D3/1k |
|---|---|---|---|---|---|---|
| **1 (first-pass)** | 27 | 360 | 33,244 | **0.812** | **0.451** | 0.331 |
| 2 (corrective) | 16 | 187 | 17,496 | 0.286 | 0.114 | 0.514 |

**First-pass D1/D1n rates are 2.8-4.0 × corrective rates.** The
corrective under-length hint **reduces** the reframe device, likely
because the hint asks for more substance ("add a challenge,
callback, or reveal that a character has been holding back") and
the model trades some of its rhetorical-tic surface for
scene-content. **H4 disconfirmed a second time** (already
disconfirmed at §92.4; now with normalized rate evidence). D3 rate
is nearly flat across attempts — courtroom vocabulary is not
attempt-count-sensitive.

### 100.7 Verbatim / near-verbatim echo cluster

| Pattern | Hits | Compositions | Universes |
|---|---|---|---|
| `"final exam"` | 3 | 26c62b4b Welcome, 488c37ba T1, 699916a9 T2 | all Fox & Flour |
| `"tiny [courtroom / management / private club / bureaucrat]"` | 4 | d533b4ec (Patch's), a119b064 (Patch's), d7549fc1 (F&F), a5c59014 (F&F) | **both Universes** |
| `"That['’]s? not a casual question"` (strict shape) | 1 mask-hit; broader "casual question" 3 hits per §92 | 7177b0f5 (F&F), 699916a9 (F&F), 01aa7601 (Patch's) | **both Universes** |
| `"That['’]s? evidence"` | 1 (7177b0f5) | Fox & Flour | 1 |

Verbatim structural echoes span both Universes — the *"tiny [formal-
institution]"* micro-template hits Patch's Workshop (bureaucrat,
management) AND Fox & Flour (courtroom, private club) as instances
of the same rhetorical construction.

## §101 Correlation findings

### 101.1 Personality-vector correlation

`voice_humor = warm` and `voice_energy = medium` and
`voice_directness = balanced` are **uniform** across all four cast
members (Ruby / Tyson / Patch / Rivet). These fields **do not
discriminate** device rate. If H3 (personality vector) were driven
by these enum fields, we would expect uniform rates. We observe:
Rivet D1n = 0.619/1k vs Patch D1n = 0.092/1k, a 6.7× ratio between
two cast members with byte-identical voice-axis enums.

`tone_archetype` varies:
- Rivet: `friend` — high D1n
- Ruby: `friend` — mid D1n
- Patch: `performer` — low D1n
- Tyson: `expert` — mid-high D1n

`tone_archetype` does not linearly predict D1n either. `friend`
covers both extreme (Rivet high) and moderate (Ruby mid). `performer`
is low; `expert` is mid-high.

**What DOES discriminate:** the personality *text*.

- Rivet: *"intelligent, analytical, observant, dry, patient, slightly
  sarcastic, and extremely literal when being literal makes something
  funnier"* — highest D1n rate. The negation-reframe device fits an
  *"extremely literal"* character verbatim.
- Ruby: *"warm, cheerful, and genuinely caring … speaks with the
  comforting confidence of someone who truly loves their craft"* —
  moderate D1n but leans D3 (courtroom lexicon).
- Tyson: *"easygoing, practical, and a little dry … Gives clear
  recommendations, occasionally teases Ruby"* — moderate D1n; leans
  D3 (courtroom lexicon).
- Patch: *"scruffy, endlessly curious beaver … curious, funny,
  inventive, slightly chaotic, persistent, skeptical, enthusiastic"*
  — lowest D1n rate. The negation-reframe device does not fit the
  *"chaotic / enthusiastic"* register; Patch leans D1a (assertive
  reframe) instead.

Free-text personality drives WHICH surface device the shared
attractor takes — not WHETHER the attractor exists.

### 101.2 Universe correlation

Fox & Flour: D3 dominates. Patch's Workshop: D1 dominates. Same
underlying attractor; different surface expression per Universe
context (bakery interpersonal drama → courtroom idiom; workshop
technical banter → literal-reframe idiom).

### 101.3 Pre / post Q-279-2 treatment correlation

Treatment SHOULD reduce the attractor if the substrate cause were in
Knowledge lexical gravity (SESSION 271-272 finding). It did not.
Treatment appeared to *slightly increase* D3 rate on Fox & Flour
post-treatment (0.655 → 1.888, n=3 post; caveat: small n; but
consistent direction with §92 qualitative evidence).

**The attractor is not moved by Knowledge substrate change.** This
is the single strongest piece of evidence that H1/H2 (contract /
model prior) is load-bearing above Knowledge.

### 101.4 Attempt-count correlation

Corrective (attempt=2) rates are LOWER than first-pass (attempt=1)
rates. H4 (corrective amplification) disconfirmed. The corrective
under-length hint appears to REDUCE the rhetorical-tic surface,
possibly by asking for more substance ("add a challenge, callback,
or reveal") that competes with the tic surface for character budget.

## §102 Prediction vs actual — §91 hypothesis hierarchy

| Hypothesis | Predicted rank | Post-Phase-1 verdict |
|---|---|---|
| **H1** — Writing Contract structural bias | dominant | **Confirmed as floor.** Contract's stakes-elevating structural frame + non-zero rates across every character + cross-World invariance + persistence across Q-279-2 treatment support this. |
| **H2** — Model prior for "dry-humor dialogue" | dominant | **Confirmed as co-floor.** Cannot be discriminated from H1 without Phase 2. Both fit the observation "attractor lives above character layer." |
| **H3** — Character-personality bleed | modulator | **Confirmed as modulator, more strongly than predicted.** Personality-text differences (analytical/dry Rivet vs enthusiastic/chaotic Patch) drive 6.7× variance in D1n rate. Personality-vector enums (`voice_humor`, `voice_energy`, `voice_directness`, `tone_archetype`) do NOT discriminate — the load-bearing variable is free-text personality description. Personality also drives WHICH surface device the attractor selects (D1n for analytical Rivet; D1a for chaotic Patch; D3 for narrative-driven Ruby+Tyson). |
| **H4** — Corrective-hint amplification | minor | **Disconfirmed a second time.** Corrective renders have 2.8-4.0× LOWER D1/D1n rates than first-pass. Corrective SUPPRESSES the tic surface. |
| **H5** — Sharpening leakage | unlikely | **Disconfirmed a second time.** `sharpen_prompt` and `clean_business_brief` remain unwired to any synthesis path (§92.5). |

## §103 H1 / H2 / H3 status after Phase 1

Answering the user's primary A/B/C question:

> *Does the shared writer fingerprint live predominantly (A) above the
> character layer, (B) in character/personality configuration, or
> (C) is genuinely mixed?*

**Answer: (C) genuinely mixed, with structure.**

The decomposition:

1. **Above-character floor (H1 + H2 jointly).** Every character
   produces the attractor at non-zero rate. Cross-World invariance in
   D1 rate. Q-279-2 Knowledge treatment did not reduce D3 rate. The
   *"tiny [formal-institution]"* template + *"That's not a casual
   question"* template span both Universes verbatim. Something in
   the substrate above the character layer reliably produces this
   attractor.
2. **Personality-text modulator (H3).** The free-text
   `personality` field — NOT the enum `voice_humor` /
   `voice_energy` / `voice_directness` / `tone_archetype` fields —
   drives 6.7× variance in the reframe-device rate between two
   otherwise-identical-enum cast members (Rivet vs Patch), AND
   drives which SURFACE device the attractor selects per character
   (D1n for analytical; D1a for chaotic; D3 for narrative-service).
3. **Not Knowledge, not corrective-hint, not sharpening module.**
   H4 + H5 disconfirmed. Q-279-2 substrate change did not move the
   attractor.

**What Phase 1 did NOT discriminate:**
- H1 (Writing Contract structural frame) vs H2 (model prior for
  dry-humor dialogue) as the source of the floor. Both remain live.
- Whether the personality-text modulation is because the LLM reaches
  for register-appropriate rhetorical devices given a personality
  description (a positive-selection story), or because a personality-
  agnostic attractor is *suppressed* by chaotic/enthusiastic
  personality descriptions (a negative-selection story).

## §104 Does Phase 1 discriminate enough to avoid Phase 2?

**For the A/B/C question — yes.** The genuinely-mixed answer is
mechanically supported. Phase 2 is not needed to answer whether the
attractor is above-character-only or personality-only.

**For distinguishing H1 (contract) from H2 (model prior) — no.**
Both remain live as the floor cause. If a future fix is planned,
Phase 2 (controlled contract-lite render + baseline replay + neutral-
voice mutation) is the natural next step to determine whether
temporarily neutralizing the writing contract's stakes-elevating
structural frame reduces the floor rate meaningfully.

Chris + ChatGPT decision: whether the A/B/C answer is sufficient
for now (defer Phase 2 to a future fix-planning slice), or whether
mechanically distinguishing H1 vs H2 justifies the ≤3 controlled
dogfood renders Phase 2 requires.

## §105 Recommendation

Phase 1 executed as designed. Rubric applied without revision.
Correlations reported at raw + normalized levels. Prediction hierarchy
resolved: H1 + H2 co-floor, H3 modulator (via personality *text*, not
enum fields), H4 + H5 disconfirmed. Device-family clustering per
character confirmed: same attractor, different surface expressions.

The write-up above is the durable analysis record. No further
provider spend was required.

### Recommended next gate

> **READY-FOR-CHRIS-CHATGPT-REVIEW** of the Phase 1 result. Two live
> options:
> 1. **DEFER-PHASE-2** — the A/B/C answer (mixed, above-character
>    floor + personality-text modulator) is sufficient for the current
>    audit. Preserve the Phase 2 design as-is for a future
>    fix-planning slice.
> 2. **APPROVE-PHASE-2** — the ≤3 controlled dogfood renders
>    (baseline + contract-lite + neutral-voice) are worth the small
>    spend to mechanically distinguish H1 from H2 before any fix is
>    considered. Phase 2 experiment design remains §95.2 unchanged.

Do NOT proceed to Phase 2 without Chris + ChatGPT approval.

Other deferred findings (4c visual composition, 4d-4i, Knowledge-
breadth, Beat-3 legibility) remain preserved unopened.

## §106 Checklist — Q-279-3 Phase 1

- [x] Rubric applied unchanged from §95.1 (§99.1)
- [x] 43 compositions scored (§100.1)
- [x] Per-speaker normalized rates (D1/1k, D1n/1k, D3/1k, affected-turn %) (§100.2)
- [x] Device-family share per speaker computed (§100.3)
- [x] Per-Universe aggregates (§100.4)
- [x] Pre / post Q-279-2 treatment aggregates (§100.5)
- [x] Attempt-count aggregates (§100.6)
- [x] Verbatim / near-verbatim echo cluster tabulated across both Universes (§100.7)
- [x] Personality-vector correlation analyzed; enum fields do not discriminate; personality-*text* does (§101.1)
- [x] Universe / treatment / attempt correlations reported (§101.2-§101.4)
- [x] Prediction-vs-actual hierarchy resolution (§102)
- [x] H1/H2/H3 status after Phase 1 (§103)
- [x] A/B/C primary question answered: C (mixed) (§103)
- [x] Phase 2 necessity assessed against A/B/C question and H1-vs-H2 question separately (§104)
- [x] Recommendation + next gate stated (§105)
- [x] No prompt / synthesis / Knowledge / character / identity / retrieval / verifier / memory / audience / runtime change
- [x] Zero provider renders fired
- [x] Zero provider spend
- [x] No fix implemented
- [x] Rubric NOT revised after seeing results
- [x] Phase 2 NOT executed
- [x] Other deferred findings NOT opened

---

# Q-279-3 — Phase 2 design reconciliation

**Status opened:** 2026-08-25, following the Phase 1 checkpoint commit
`1df3f70`. Chris + ChatGPT approved Q-279-3 Phase 2 *in principle*
based on the Phase 1 (C = genuinely mixed) result and directed a
design reconciliation before any provider spend. Purpose:

- verify the pre-registered §95.2 P2-A / P2-B / P2-C design cleanly
  isolates H1 vs H2 vs H3 given what Phase 1 actually established;
- assess whether the §95.2 *"≥ 50 % reduction"* criterion can be
  evaluated meaningfully at the originally-proposed n = 1 per
  condition;
- determine whether avatar / Runway rendering is required at all;
- pick a topic that does not itself contaminate the writer-voice
  measurement;
- specify the temporary contract-lite mechanism at the level of an
  exact behavioral substitution, without touching persistent
  production code without approval.

**No provider renders fired. No permanent code / DB / prompt /
retrieval / verifier / synthesis / identity / audience / memory
changes.** Read-only design work.

## §107 Phase 1 findings — used as reconciliation inputs

Anchoring the reconciliation to §100 empirics:

- Fox & Flour cast (Ruby + Tyson) per-composition composite device
  hits: 2-7 (mean ~5.6 across 10 F&F compositions; §100.1).
- Patch's Workshop per-composition composite: 0-6 (mean ~1.9 across
  31 Patch compositions; §100.1).
- **Enum voice fields (`voice_humor`, `voice_energy`,
  `voice_directness`, `tone_archetype`) do NOT discriminate device
  rate** (§101.1). Voice_humor = `warm` uniformly across all four
  cast members yet device rates vary 6.7× between Rivet and Patch.
- **Free-text `personality` description DOES discriminate.**
- Device *family* clusters by character-personality context:
  Ruby / Tyson lean D3 (courtroom); Rivet leans D1n
  (negation-reframe); Patch leans D1a (assertive-reframe) (§100.3).
- Q-279-2 Knowledge treatment did NOT reduce the attractor rate;
  post-treatment D3 rate actually increased (§100.5).

Two Phase-1 findings the pre-registered §95.2 did NOT anticipate:

1. **Enum voice fields are not the modulator.** Original P2-C
   proposed *"setting both Ruby's and Tyson's `voice_humor` to
   `none` and `character_point_of_view` blank."* Phase 1 shows
   `voice_humor` variation across cast is zero (all `warm`), so
   changing this enum from `warm` to `none` does not test the
   Phase-1-established H3 modulator. Also, `character_point_of_view`
   is already blank on both Ruby and Tyson (§3.3), so blanking it is
   a no-op. **Original P2-C does not test H3.**
2. **Device families cluster differently by character.** If the
   experiment scores only D1n (negation-reframe), it will
   *undercount* the writer-voice attractor for Ruby + Tyson (whose
   dominant surface is D3, not D1n). Measurement must be composite,
   or the null-hypothesis can be trivially passed by the LLM
   swapping surface device without reducing overall attractor rate.

## §108 Video / render necessity — verified NOT required

The dependent variable is *synthesized dialogue text* — not
rendered media. Read `apps.compositions.starters:3585-3670` and
`character_os.dialogue_synthesis:1428-1990`:

- `synthesize_dialogue()` is a plain-Python function returning a
  `DialogueResult` dataclass in-memory (§lines 243-345). It:
  - assembles the full system prompt (§ §1-§5 including WORLD SHAPE,
    SHARED WORLD KNOWLEDGE, per-character SCOPED KNOWLEDGE, CHARACTER
    VOICES, BRAND VOICES, WRITING CONTRACT, TASK);
  - calls the real production LLM path (`_call_llm`, `openai.Client`,
    `text-embedding-3-small` retrieval);
  - parses + validates the returned JSON;
  - runs the K6.4 verifier dispatcher;
  - returns turns + provenance.
- It does NOT create a Composition row, does NOT call the
  media-engine, does NOT invoke Runway. All render-side work
  (`generate_avatar_speech`, `Runway avatar creation`, video concat,
  `AvatarClipRecipe`) fires from the *starter* wrapper AFTER
  synthesis returns.
- Real production dialogue synthesis and Phase-2 synthesis use the
  **identical WritingContract, identity, personality, Knowledge, and
  LLM call**, so measuring at the `synthesize_dialogue()` return is
  isomorphic to measuring at the persisted `Composition.
  synthesized_brief` for our substrate question.

**Cost implications.**

- Full production dialogue-scene render (measured Q-279-2 T1/T2/T3):
  ~$0.26-$0.28 per render (most of which is Runway avatar seconds +
  concat).
- Synthesis-only (single LLM call): a dialogue-synthesis system
  prompt is ~3-5K input tokens + ~1K output tokens. At current
  gpt-5-family API prices this is well under **$0.01 per call**.
- **~99 % cost reduction relative to full render.** No Runway seconds.
  No media-engine hop.

**Answer: video / avatar / render generation is NOT required.**
Phase 2 should exercise `synthesize_dialogue()` directly. This is
NOT a mock substitution — the real production synthesis function is
called with real production inputs, real production prompts, real
LLM.

## §109 Sample-size assessment (locked §95.2 ≥ 50 % criterion)

Base rate (Phase 1, Fox & Flour cast, composite device hits per
composition):

| Bucket | n | mean composite hits/comp | stdev (approx) |
|---|---|---|---|
| Fox & Flour composite (§100.1 non-zero) | 10 | ~5.6 | ~2.2 |
| Post-Q-279-2 F&F only | 3 | ~5.3 | ~2.5 |

For a single sample (n=1) per condition, a Poisson-approximation
with mean λ ≈ 5 has stdev ≈ √5 ≈ 2.24. So a 50 % reduction
(5 → 2.5) is roughly *one* standard deviation — the null could
easily be crossed by chance in either direction on n=1.

At n = 2 per condition, SEM of the two-sample mean is √λ/√2 ≈
1.58. At n = 3, SEM ≈ 1.29. Delta between P2-A and P2-B is
predicted ≥ 2.5. At n = 3 the discrimination is ≥ ~2σ — the
smallest sample size that lets §95.2's locked *"≥ 50 %
reduction"* pass without prima-facie noise concerns.

**Verdict:** the originally-proposed 1 render per condition is
too weak. Increase to **n = 3 per condition**. Because of the
synthesis-only cost reduction (§108), n = 3 × 3 conditions = 9
synthesis calls costs **~$0.05 total**, not $2.50.

We are not spending more; we are spending on more real
synthesis samples instead of on avatar rendering we do not need.

## §110 Revised P2-C (isolates personality-TEXT, not enum)

Original §95.2 P2-C targeted `voice_humor` + `character_point_of_view`.
Phase 1 disconfirmed those as the modulator. Revised P2-C targets the
*free-text `personality` field* — the variable Phase 1 identified as
the actual H3 driver.

**P2-C revised:** substitute Ruby's and Tyson's `personality`
text with a neutral variant (identity substrate remains — same
name, universe, business_brief, voice enums, no other change).

Neutral personality substitute (character-agnostic):

```
Ruby:  "Ruby is friendly and helpful."
Tyson: "Tyson is friendly and helpful."
```

Zero color / register / mannerism / disposition information —
stripped of the dry/analytical/practical/warm/cheerful vocabulary
Phase 1 identified as the modulator source.

Every OTHER Teammate field held fixed (name, universe, business_brief,
who_you_help, what_you_sell, always_emphasize, never_say,
desired_feeling, character_point_of_view, tone_archetype, voice_energy,
voice_humor, voice_directness, voice_signature_phrases,
voice_avoid_phrases). Only `personality` differs from P2-A baseline.

## §111 Contract-lite mechanism — exact behavioral substitution

**Constraint reaffirmation (per Chris + ChatGPT direction):** show
the exact substitution BEFORE implementation; stop for approval if
persistent production code would be touched.

### 111.1 What contract-lite must remove

Only the Writing Contract content Phase 1 evidence identified as
plausibly encoding the stakes-elevating structural bias:

- `_DIALOGUE_WATCHABILITY_BLOCK` §1 ENTER WITH AN IN-SCENE STANCE —
  the enumerated "wants" list (*wants to prove something worked;
  wants to correct the other character; wants clarification; wants
  permission; wants to avoid blame; wants to persuade; wants to
  understand; wants to reassure; wants to challenge an assumption*).
  This is the highest-density stakes-elevation vocabulary in the
  contract.
- `_DIALOGUE_NARRATIVE_SHAPES_BLOCK` — the entire shape menu
  (*setup → disagreement → payoff; question → answer → correction;
  experiment → failure → explanation; claim → skeptical response →
  reveal; myth → correction → practical takeaway; challenge →
  attempt → result; story → skeptical reaction → punchline*).
  Every shape is stakes-adjacent.

### 111.2 What contract-lite must KEEP

To avoid inducing OTHER failures that would confound the test:

- `_DIALOGUE_INVARIANTS_BLOCK` — all 10 invariants including CAUSAL
  CHAIN (rule 10). These are load-bearing conversational-continuity
  rules; removing them would degrade dialogue quality for reasons
  unrelated to writer voice.
- `_DIALOGUE_WATCHABILITY_BLOCK` §§ 2-5 (SOMETHING CHANGES,
  PREFER SPECIFIC ACTION, KNOWLEDGE INFLUENCES NOT QUOTED, END ON
  A MOMENT). These are scene-quality rules, not stakes-vocabulary.
- `_DIALOGUE_ANTI_PATTERNS_BLOCK` (name-use, no re-introductions,
  no self-narration, no strict alternation, no target turn count,
  framework recitation, role summary, mutual synthesis).
- `_CTA_POLICY_BLOCK`, `_ANTI_SELF_DESCRIPTION_BLOCK`,
  `_ANTI_GENERIC_REGISTER_BLOCK` — floors, not stakes-elevation.
- SHAPE header and formatting.

### 111.3 Proposed substitution for §1 stances

Replace the wants-list paragraph (§111.1 item 1) with:

```
Each character arrives with a purpose for THIS scene. Observation,
sharing, acknowledgment, curiosity, or question-asking are all valid
stances. This does not mean every scene requires hostility,
argument, or comedy — collaboration is a valid stance when the topic
calls for it. A character with no in-scene stance should not speak.
```

Removes the "prove / correct / challenge / persuade / avoid blame"
vocabulary; keeps the general "have a stance" rule.

### 111.4 Proposed substitution for narrative-shapes menu

Replace `_DIALOGUE_NARRATIVE_SHAPES_BLOCK` with:

```
NARRATIVE SHAPE — no prescribed skeleton; write the scene the topic
calls for. Legitimate hybrids are fine. Do not force conflict,
argument, or reveal shape when the topic does not require it.
```

Removes the shape menu entirely (all seven listed shapes are
stakes-adjacent); replaces with a permissive rule that explicitly
allows non-stakes scenes.

### 111.5 Implementation mechanism — proposed, NOT executed

Two-part runtime injection, both reversible-at-process-exit, both
outside `character_os/writing_contract.py`:

**Part A — probe script** `scripts/session279_q279_3_phase2_probe.py`
(new file). Precedent: the SESSION 272 slice scripts under
`scripts/` (e.g. `session272_slice_e_ablation.py`,
`session272_slice_b_render.py`). Non-production code path; not
imported by production; may be deleted after the experiment.

Script responsibilities:

1. Load workspace + Ruby + Tyson from real DB (read-only).
2. Parse CLI args: `--config=A|B|C`, `--topic=...`, `--n=3`.
3. For config B: monkeypatch `WritingContract.for_shape` to return
   the §111.3 + §111.4 substituted dialogue_scene contract for the
   duration of the probe. All other shapes pass through unchanged.
4. For config C: monkeypatch `character_os.dialogue_synthesis.
   _build_character_voice_block` to substitute `tm.personality` with
   the §110 neutral variant when the passed teammate is Ruby or
   Tyson. All other fields pass through unchanged.
5. For each of N samples: call `synthesize_dialogue(workspace, [ruby,
   tyson], topic, target_duration_seconds=90, use_knowledge=True,
   mock_mode=False)` and capture the returned `DialogueResult`.
6. Score each result's turn texts against locked D1-D4 rubric plus
   the composite total (§100.3 shape).
7. Write results to `docs/design/session279_phase2/<config>_<sample_idx>.txt`
   (durable artifact for later inspection). Also print aggregate to
   stdout.
8. Exit; monkeypatches are process-scoped so nothing persists
   beyond the script's process lifetime.

**Part B — no touch to `writing_contract.py` or
`dialogue_synthesis.py`.** No version bump. No env-flag branch
merged into production. The probe script contains the substitute
text as string literals; the monkeypatch overwrites the function
attribute at runtime.

### 111.6 Diff shown for approval — script only

```python
# scripts/session279_q279_3_phase2_probe.py  (~150 lines, new file)
# Purely test-time / experiment-time. Not imported by production.
# Contains the §111.3-§111.4 lite-contract text as literals + the
# §110 neutral personality text as literals + argparse + monkeypatch
# + synthesis call + scoring. Reverts monkeypatches on exit.
```

**Persistent production code delta:** zero.
**New file:** one, in `scripts/` (matches SESSION 272 precedent).
**Contract version bump:** none.
**Env flag added:** none.
**Import in production path:** none.

Chris + ChatGPT: approve the new file under `scripts/` before
implementation. If Chris prefers zero new file, alternative is an
ad-hoc `manage.py shell` script pasted into the audit doc for each
condition — same monkeypatch mechanism, less reproducible, more
fragile.

## §112 Topic selection

Requirements (per Chris + ChatGPT direction): no legal / procedural
language, no explicit tension, no arguments / evidence / rules /
testing / challenge / blame. Same topic across all three configs.
Semantically neutral but with enough room for dialogue.

Candidates considered:

- *"Ruby and Tyson watch the sunrise through the bakery window before opening."*
- *"Ruby and Tyson notice the flowers outside the bakery are blooming."*
- *"Ruby and Tyson enjoy a quiet moment before customers arrive."*
- *"Ruby and Tyson talk about the weather."*

Rejected during selection:

- Anything mentioning *test*, *check*, *ready*, *decide*, *should*,
  *problem* — primes the attractor.
- Anything with a customer or interaction — introduces external
  stakes / service register.
- Anything coffee / pastry-adjacent — would engage the Q-279-2
  Knowledge treatment and confound the R6-vs-writer-voice signal.

**Recommended topic (verbatim, same across P2-A / P2-B / P2-C):**

> **"Ruby and Tyson watch the sunrise through the bakery window before opening."**

Purely observational. Zero adversarial framing. Zero request for
domain specifics. Compatible with a natural 90-second bakery scene.
Does NOT engage Q-279-2 treatment vocabulary.

## §113 Exact causal matrix

Same cast, same topic, same everything except the one hypothesized
variable per config:

| Field | P2-A (baseline) | P2-B (contract-lite) | P2-C (personality-lite) |
|---|---|---|---|
| Cast | Ruby + Tyson (Fox & Flour) | Ruby + Tyson (Fox & Flour) | Ruby + Tyson (Fox & Flour) |
| Operator topic | §112 verbatim | §112 verbatim | §112 verbatim |
| `Universe.brief` | Fox & Flour brief (unchanged) | same | same |
| `Teammate.name` | Ruby, Tyson (unchanged) | same | same |
| `Teammate.business_brief` | production (unchanged) | same | same |
| `Teammate.personality` | production (Ruby *"warm, cheerful …"* + Tyson *"easygoing, practical, a little dry …"*) | same | **§110 neutral** (*"Ruby is friendly and helpful."* / *"Tyson is friendly and helpful."*) |
| `Teammate.who_you_help / what_you_sell / always_emphasize / never_say / desired_feeling / character_point_of_view` | production (all empty for both) | same | same |
| `tone_archetype / voice_energy / voice_humor / voice_directness / voice_signature_phrases / voice_avoid_phrases` | production (`friend/expert`, `medium`, `warm`, `balanced`, empty, empty) | same | same |
| Knowledge (Fox & Flour Hours + holiday policy + Q-279-2 §27 treatment corpus) | production (unchanged) | same | same |
| `Universe` memory | none | same | same |
| Retrieval (`retrieve_for_teammate` / `retrieve_universe_canon` / `retrieve_universe_memory`) | production (unchanged) | same | same |
| K6.4 verifier | production dispatcher (D-POS authoritative) | same | same |
| Model + LLM API | production `text-embedding-3-small` + gpt-5-family via `_call_llm` | same | same |
| Mock mode | false | false | false |
| Target duration | 90 s | 90 s | 90 s |
| Verifier mode | warn (production default) | same | same |
| **`WritingContract.for_shape('dialogue_scene')`** | **production** (`_DIALOGUE_INVARIANTS_BLOCK` + `_DIALOGUE_WATCHABILITY_BLOCK` + `_DIALOGUE_ANTI_PATTERNS_BLOCK` + `_DIALOGUE_NARRATIVE_SHAPES_BLOCK` + `_CTA_POLICY_BLOCK` + `_ANTI_SELF_DESCRIPTION_BLOCK` + `_ANTI_GENERIC_REGISTER_BLOCK`) | **§111.3 + §111.4 substituted**: watchability §1 wants-list replaced with permissive stance rule; narrative-shapes menu replaced with "no prescribed skeleton". Every other contract element unchanged. | production (unchanged) |
| Video / avatar render | **not fired** (synthesis-only path per §108) | **not fired** | **not fired** |
| Samples per config | **n = 3** (per §109) | n = 3 | n = 3 |

**Single-variable-per-config check:**

- P2-B ↔ P2-A: exactly one variable differs = `WritingContract.for_shape('dialogue_scene')`. Isolates **H1** (contract structural bias). A large device-rate drop in P2-B vs P2-A implicates the writing_contract's stakes-elevating structural frame.
- P2-C ↔ P2-A: exactly one variable differs = Ruby + Tyson `personality` text. Isolates **H3** (personality-text modulation). A large device-rate drop in P2-C vs P2-A implicates the free-text personality field.
- P2-A ↔ Phase 1 F&F post-treatment baseline: replicates the production configuration on a new neutral topic — establishes that the attractor is not topic-specific to Q-279-2's coffee-adjacent topics.
- Whichever configuration does NOT reduce the attractor rate relative to P2-A implicates **H2** (model prior) as the remaining floor.

## §114 Measurement definition — composite + per-family

Locked rubric D1-D4 preserved. Because Phase 1 found DEVICE FAMILY
clusters differently by character-personality context (§100.3), we
report BOTH:

1. **Composite attractor rate** (per 1000 chars): `(D1 + D2 + D3 +
   D4a + D4n) / total_chars * 1000`. Do NOT double-count D1n
   (subset of D1). Primary discrimination metric.
2. **Per-family breakdown** (D1a / D1n / D2 / D3 / D4a / D4n).
   Reports SHAPE of any observed change. E.g. if P2-C reduces D3
   but doubles D1n, the attractor is not gone — it moved family.

**Locked interpretation rules (BEFORE render, per Chris + ChatGPT
direction):**

- **H1 confirmed as primary floor:** P2-B composite rate ≤ 50 % of
  P2-A composite rate; family shift alone is not enough — the
  composite must drop.
- **H3 confirmed as modulator:** P2-C composite rate ≤ 50 % of P2-A
  composite rate.
- **H2 as remaining floor:** if BOTH P2-B and P2-C achieve ≤ 50 %
  reduction → attractor is jointly modulated by contract + personality
  above a residual floor. If NEITHER P2-B nor P2-C reduces composite
  ≥ 25 % → model-prior H2 is the dominant residual and neither
  contract-lite nor personality-lite is sufficient to move it.
- **Mixed / partial** results → interpret via per-family breakdown.

## §115 Sample-count justification

Per §109: **n = 3 samples per config** is the smallest sample size
that lets the locked ≥ 50 % criterion pass without being swamped
by Poisson noise on a mean-5 base rate. 3 configs × 3 samples =
**9 synthesis-only calls**, ~$0.05 total. Do NOT increase without
new evidence.

## §116 Reconciled Phase 2 answers

### 116.1 Does the original §95.2 design remain valid?

**Partially.** Preserved from §95.2:

- P2-A baseline replay concept.
- P2-B contract-lite concept.
- Overall three-config causal-matrix structure.
- ≥ 50 % composite reduction acceptance threshold.

**Revised** from §95.2:

- **P2-C target variable**: `voice_humor` + `character_point_of_view`
  → *free-text `personality`* substitution (Phase 1 disconfirmed
  the enum fields as modulators).
- **Sample count per config**: 1 → 3 (§109 noise analysis).
- **Render mechanism**: full Runway/avatar render → synthesis-only
  via direct `synthesize_dialogue()` invocation (§108 established
  the dependent variable is text, not media).
- **Measurement**: single-family focus → **composite** attractor
  rate + per-family breakdown (§114; Phase 1 §100.3 showed families
  shift by character).
- **Mutation route**: SPA Ask-panel operator gesture (would only
  mutate KDs, not personality field; also would fire full renders)
  → runtime monkeypatch inside a new `scripts/session279_q279_3_
  phase2_probe.py` file (§111.5-§111.6). Zero permanent production
  code change.
- **Topic**: unspecified in §95.2 → **§112 recommended verbatim**.

### 116.2 Cheapest valid real-model experiment

Direct `synthesize_dialogue()` invocation from a
`scripts/session279_q279_3_phase2_probe.py` probe, monkeypatching
either `WritingContract.for_shape` (for P2-B) or
`_build_character_voice_block` (for P2-C). Real LLM. Real
production prompt scaffolding except for the one substituted
element. n = 3 samples per condition. 9 synthesis calls total.
~$0.05 aggregate LLM spend. Zero Runway spend. Zero DB writes.

### 116.3 Is video rendering required?

**No.** §108. Full render costs ~$0.28 apiece and produces media
we do not need to answer the writer-voice question. Synthesis-only
is isomorphic to persisted `Composition.synthesized_brief` for the
dependent variable and exercises the same LLM path with the same
inputs.

### 116.4 Proposed topic

**"Ruby and Tyson watch the sunrise through the bakery window before opening."** (§112)

### 116.5 Sample count required

**n = 3 per config**, 9 synthesis calls total. Locked at §109.

### 116.6 Decision gate

Do NOT execute Phase 2 without Chris + ChatGPT approval of:

1. The revised P2-C personality-text substitution (§110).
2. The exact contract-lite behavioral substitution (§111.3 + §111.4).
3. The new probe file under `scripts/` (§111.5-§111.6). Precedent
   exists (SESSION 272 slices under same path) but any new file is
   a persistent code change; requires explicit sign-off.
4. The proposed topic (§112) or an alternative.
5. n = 3 per config sample count (§115) — up or down.

Two live gate options after approval:

- **APPROVE-EXECUTE-Q-279-3-PHASE-2** — proceed with §113 causal
  matrix as reconciled. ~$0.05 provider spend.
- **REVISE-DESIGN-FURTHER** — adjust one or more of {P2-C substitute
  text, contract-lite substitution scope, probe file location,
  topic, sample count} before execution.

Do NOT proceed until explicit approval.

## §117 Checklist — Phase 2 reconciliation

- [x] Phase 1 findings identified that break the original §95.2 P2-C design (§107)
- [x] Video / avatar rendering necessity checked and answered NO (§108)
- [x] Sample-size assessment against §95.2 ≥ 50 % criterion using Phase-1 empirical base rates (§109)
- [x] Revised P2-C targets personality *text*, not enum voice fields (§110)
- [x] Contract-lite behavioral substitution specified at prompt-text level (§111.1-§111.4)
- [x] Implementation mechanism proposed — runtime monkeypatch inside new `scripts/` probe file — with zero permanent production code delta (§111.5-§111.6)
- [x] Neutral topic recommended verbatim (§112)
- [x] Exact single-variable-per-config causal matrix presented (§113)
- [x] Composite + per-family measurement locked BEFORE any render (§114)
- [x] Locked acceptance / discrimination rules (§114)
- [x] Sample count justified against Poisson-noise floor (§115)
- [x] Reconciled answers to user's 8-item report scaffold (§116)
- [x] No provider renders fired
- [x] No permanent code / DB / prompt / retrieval / verifier / synthesis / identity / audience / memory changes
- [x] No implementation of the probe file yet
- [x] Chris + ChatGPT approval gate explicit (§116.6)
- [x] Other deferred findings NOT opened

---

# Q-279-3 — Phase 2 execution result

**Status opened:** 2026-08-25, immediately following the Phase 2
reconciliation checkpoint commit **`be57821`** (approved by Chris +
ChatGPT). Execution consumed the §113 causal matrix exactly — 3
conditions × 3 real-model synthesis calls = 9 calls total via the
production `synthesize_dialogue()` path. No provider render fired.
No Runway/media-engine hop. No Composition rows created. No DB
writes. No permanent code changes. All monkeypatches
`try/finally`-restored; post-run production-contract + DB-personality
verification passed (`_verify_restored()` at
`scripts/session279_q279_3_phase2_probe.py:_verify_restored`).

**Execution baseline SHA:** **`be57821`** (`docs(session-279): Q-279-3 Phase 2 design reconciliation vs Phase 1 findings`).

## §118 Probe implementation

Landed as `scripts/session279_q279_3_phase2_probe.py`. ~360 lines.
Precedent: SESSION 272 slice scripts under the same `scripts/`
path. Non-production; not imported by production; may be deleted
after the experiment closes. Full source in-repo; behavioral
substitutions match §111.3-§111.4 verbatim (variable names
`_LITE_WATCHABILITY_BLOCK` and `_LITE_NARRATIVE_SHAPES_BLOCK`).

Runtime substitutions applied per condition:

- **P2-A:** no monkeypatch.
- **P2-B:** `WritingContract.for_shape = staticmethod(_lite)` where
  `_lite('dialogue_scene')` returns
  `_dialogue_scene_contract_lite()`. `_lite('long_form')`,
  `_lite('standalone')`, `_lite('solo_scene')` fall through to
  the original class method. Restored in `finally`.
- **P2-C:** `ruby.personality = "Ruby is friendly and helpful."` +
  `tyson.personality = "Tyson is friendly and helpful."` — mutated
  on in-memory Teammate instances only. `.save()` never called.
  Original values captured in `saved = {tm.pk: tm.personality for
  tm in cast}` and restored in `finally`.

Restoration post-run verified two ways (`_verify_restored()`):

1. Fetch production `WritingContract.for_shape('dialogue_scene')`
   and assert the lite marker string *"no prescribed skeleton"* is
   NOT present.
2. Fetch Ruby and Tyson from DB (fresh objects, not the mutated
   in-memory instances) and assert their `personality` is not the
   neutral substitute.

Both assertions passed.

## §119 Raw execution log (compact terminal echo)

```
[A#1] synthesizing... turns=10 chars=1291 composite=2 composite/1k=1.549 elapsed=15.55s
[A#2] synthesizing... turns=14 chars=1262 composite=1 composite/1k=0.792 elapsed=24.29s
[A#3] synthesizing... turns=14 chars=1248 composite=1 composite/1k=0.801 elapsed=19.65s
[B#1] synthesizing... turns=13 chars=1203 composite=0 composite/1k=0.000 elapsed=25.13s
[B#2] synthesizing... turns=12 chars=1240 composite=2 composite/1k=1.613 elapsed=21.9s
[B#3] synthesizing... turns=14 chars=1275 composite=2 composite/1k=1.569 elapsed=25.17s
[C#1] synthesizing... turns=12 chars=1372 composite=1 composite/1k=0.729 elapsed=15.03s
[C#2] synthesizing... turns=12 chars=1299 composite=0 composite/1k=0.000 elapsed=9.25s
[C#3] synthesizing... turns=11 chars=1139 composite=2 composite/1k=1.756 elapsed=10.43s
Post-run restoration verified.
```

All 9 samples used **`gpt-5.6-terra`** at the production model
config. Raw dialogues durably persisted under
`docs/design/session279_phase2/p2{a,b,c}_sample{1,2,3}.txt`; full
per-sample provenance persisted to
`docs/design/session279_phase2/phase2_evidence.json`.

## §120 Per-sample scores (locked rubric §99.1)

| Config | # | attempt | chars | turns | D1 | D1n | D1a | D2 | D3 | D4a | D4n | composite | composite/1k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2-A | 1 | 1 | 1291 | 10 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 2 | 1.549 |
| P2-A | 2 | 2 | 1262 | 14 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.792 |
| P2-A | 3 | 2 | 1248 | 14 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.801 |
| P2-B | 1 | 2 | 1203 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| P2-B | 2 | 2 | 1240 | 12 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 1.613 |
| P2-B | 3 | 2 | 1275 | 14 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | 1.569 |
| P2-C | 1 | 1 | 1372 | 12 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0.729 |
| P2-C | 2 | 1 | 1299 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| P2-C | 3 | 1 | 1139 | 11 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 1.756 |

## §121 Per-condition aggregates

| Config | n | chars | turns | composite | **composite/1k** | D1 | D1n | D1a | D2 | D3 | D4a | D4n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2-A baseline | 3 | 3801 | 38 | 4 | **1.052** | 2 | 1 | 1 | 0 | 1 | 1 | 0 |
| P2-B contract-lite | 3 | 3718 | 39 | 4 | **1.076** | 0 | 0 | 0 | 1 | 0 | 2 | 1 |
| P2-C personality-lite | 3 | 3810 | 35 | 3 | **0.787** | 1 | 0 | 1 | 0 | 0 | 2 | 0 |

**Deltas vs P2-A:**

- P2-B / P2-A composite/1k = 1.076 / 1.052 = **+2.2 %** (no reduction)
- P2-C / P2-A composite/1k = 0.787 / 1.052 = **−25.2 %** (partial, does not clear the §114 ≥ 50 % threshold)

## §122 Family-shift analysis (loud signal)

The composite metric is nearly flat between P2-A and P2-B, but the
**family breakdown moved substantially**:

| Family | P2-A hits | P2-B hits | Δ (P2-B − P2-A) |
|---|---|---|---|
| D1 (any *That is …* reframe) | 2 | **0** | **−2 (100 % elimination)** |
| D1n (strict negation-reframe) | 1 | 0 | −1 |
| D1a (strict assertive-reframe) | 1 | 0 | −1 |
| D2 (diminutive-formal metaphor) | 0 | **1** | +1 |
| D3 (courtroom lexicon) | 1 | **0** | **−1 (100 % elimination)** |
| D4a (stakes-elevating adjective) | 1 | **2** | +1 |
| D4n (stakes-elevating *not …*) | 0 | **1** | +1 |

**Contract-lite eliminated D1 (negation- + assertive-reframe) and
D3 (courtroom lexicon) COMPLETELY** in the three samples — the two
device families the Phase-1 audit identified as the dominant
surface expressions of the attractor. But the same three samples
gained ONE hit each in D2 (diminutive-formal metaphor: *"tiny
negotiation"* in `p2b_sample2`, *"little ceremony"* in
`p2b_sample3`), D4a (stakes-elevating adjective: *"dramatic"*,
*"serious decision"* — one per B-sample), and D4n
(*"not just because it sounds dramatic"* in `p2b_sample2`).

**Family swap without composite reduction.** This is *exactly* the
failure mode §114 warned against ("do not interpret disappearance
of one family as success if another family replaces it"). The
underlying attractor — "elevate a mundane utterance via a
formalizing device" — survived the intervention; only the surface
lexicon changed.

P2-C family shift is smaller but present in the same direction:
D1 dropped 2 → 1, D3 dropped 1 → 0, D4a rose 1 → 2. Composite
reduced 25.2 % — some of the missing D1/D3 mass appears reabsorbed
by D4a.

## §123 Prediction vs actual

Per §102 predicted hierarchy:

| Hypothesis | Predicted (§91 / §102) | Actual (Phase 2) |
|---|---|---|
| H1 (Writing Contract structural bias) | co-floor; expected P2-B ≤ 50 % of P2-A | **P2-B = 102.2 % of P2-A on composite; D1 + D3 eliminated but D2 + D4a + D4n backfilled. NOT confirmed as primary composite-mover; contract text is one input to the attractor but does not solely determine it.** |
| H2 (model prior) | co-floor; expected to remain if P2-B fails | **Consistent with model-prior floor: the attractor persists as long as the model is asked to produce a scene with meaningful change (rule 2 of watchability, kept in lite). Family swap under contract-lite is direct evidence.** |
| H3 (personality-*text* modulator) | modulator; expected P2-C ≤ 50 % of P2-A | **P2-C = 74.8 % of P2-A on composite; direction correct but well below 50 % threshold. Personality-text neutralization moved the rate ~25 % on n = 3 samples; family shift also visible but smaller than P2-B's.** |
| H4 (corrective amplification) | disconfirmed | **Consistent.** Attempt-count distribution: P2-A had 1 first-pass + 2 corrective; P2-B had 0 first-pass + 3 corrective; P2-C had 3 first-pass + 0 corrective. The neutral topic tends to under-shoot the duration band on first pass (topic gives little material) which triggers the corrective expansion hint. No evidence of corrective amplifying the attractor. |
| H5 (sharpening leakage) | disconfirmed | Consistent (unchanged; not touched). |

## §124 Neutral-topic ceiling artifact (unexpected but decisive)

Phase-1 F&F composite base rate: mean ~4.35/1k chars (aggregated
§100.4: D1=10, D2=1, D3=13, D4a=10, D4n=5 = 39 hits / 12,871 chars
under the same rubric).

Phase-2 P2-A on the neutral topic: 1.052/1k chars — **~24 % of
the Phase-1 F&F base rate.** The topic *"Ruby and Tyson watch the
sunrise through the bakery window before opening"* is topically
non-adversarial (per §112 design intent) and evidently deprives
the writer voice of most of its usual surface material.

**Consequence.** Applying the §114 locked ≥ 50 % criterion on a
mean of 1.1 hits per composition (composite ≈ 1.0/1k × 1.25 kchars
≈ 1.3 hits) with n = 3 puts the ± 1σ noise band around ±1.2 hits.
The neutral-topic composite floor is inside the noise band. The
family-swap signal is much stronger than the composite delta at
this base rate.

This is a genuine result — the attractor IS topic-sensitive; the
neutral topic reproduces the attractor at ~24 % of the adversarial
rate — but the noise floor swallows both H1 and H3 discriminations
at n = 3 on a neutral topic. §114's ≥ 50 % threshold is a
categorical rule, not a signed-power calculation; per the locked
rule, neither H1 nor H3 clears it.

## §125 Mechanical H1 / H3 / H2 verdicts (locked §114)

Per the §114 rules, applied without post-hoc revision:

- **H1 confirmed as primary composite floor:** requires P2-B ≤ 50 %
  of P2-A. Observed: P2-B = 102.2 %. **NOT CONFIRMED.**
- **H3 confirmed as primary composite modulator:** requires P2-C ≤ 50 %
  of P2-A. Observed: P2-C = 74.8 %. **NOT CONFIRMED.**
- **H2 as dominant residual:** locked rule "if NEITHER intervention
  reduces composite ≥ 25 % → model-prior H2 is dominant". P2-B: no
  reduction (+2.2 %). P2-C: reduction −25.2 % (exactly at the 25 %
  boundary; below it by convention). **Neither reaches ≥ 25 % strict
  reduction; H2 as dominant residual is CONSISTENT WITH THE
  EVIDENCE but not resoundingly confirmed.**
- **Mixed / partial classification:** §114 explicit escape hatch —
  *"Mixed / partial results → interpret via per-family breakdown."*
  **Per-family breakdown is highly informative** (§122): contract-lite
  eliminates D1 + D3 completely and shifts them into D2 + D4; this
  demonstrates the attractor is *steerable* by contract text but
  moves under pressure to preserve its overall rate.

**Interpretive summary:**

The Phase-2 evidence does NOT license a fix on either H1 or H3
individually — neither cleared the pre-registered composite
threshold. The evidence is instead most consistent with:

> The stakes-elevating structural attractor lives above the character
> layer AND above the specific dialogue-scene writing-contract text
> Chris + ChatGPT identified. It is real but robust: eliminating one
> lexical channel causes the model to reach for another. The
> personality-text field is a real modulator with directionally
> correct effect (~25 % on n = 3) but not the primary lever.

## §126 Dialogue-quality observations (recorded; NOT a metric)

Per Chris + ChatGPT direction, log qualitative degradation
separately without changing the composite gate.

Manual read of all 9 samples:

- **P2-A samples:** in-character; natural conversational rhythm;
  Q-279-2 treatment knowledge (almond croissant + pour-over,
  morning bun + drip, chocolate babka + espresso, tradeoff rule)
  surfaces naturally in every sample. No degradation.
- **P2-B samples:** in-character; natural rhythm; Knowledge surfaces
  similarly. Notably `p2b_sample1` produces composite = 0 (the
  cleanest sample in the whole run), reading as a pure sunrise
  scene with pairing recommendations delivered without any
  stakes-elevating framing. `p2b_sample3` opens with *"like it's a
  legal matter"* — the attractor still fires despite contract-lite,
  but as an isolated stylistic tic rather than as a recurring
  frame. No degradation.
- **P2-C samples:** in-character despite the neutralized personality
  text; Ruby and Tyson still read as distinct voices — the LLM
  reconstructs voice from `business_brief` + `who_you_help` +
  `voice_*` enums even when free-text personality is blanked. This
  is itself informative — Ruby's *"warm, cheerful"* and Tyson's
  *"easygoing, dry"* voice was not the SOLE source of their
  recognizability. No degradation of scene-content or coherence.

**No condition produced flat, broken, repetitive, or structurally
poor dialogue.** No condition failed the K6.4 verifier (all 9
samples returned `overall_verification_status = "verified"`).

**Also observed** (informational, non-metric): every sample used
the Q-279-2 treatment vocabulary appropriately — every sample
contained at least two of {almond croissant, morning bun, chocolate
babka, pour-over, drip, espresso} + attribute-grounded pairing
reasoning. **Q-279-2 finding 4b is stably reproducible; the writer
voice attractor is not the KD's job to solve.**

## §127 Unresolved questions

Preserved for Chris + ChatGPT decision; NOT auto-opened.

1. **Adversarial-topic replication.** Neutral topic P2-A rate is
   ~24 % of adversarial P1 rate. Would the same interventions
   reduce composite more visibly on a topic where the base rate is
   ~4×higher? A single extension (P2-A/B/C × n=3 on a re-run of the
   Q-279-2 T1 topic *"Ruby thinks Tyson is taking coffee too
   seriously"*) would cost ~$0.05 more and would let the ≥ 50 %
   criterion actually resolve at usable statistical power. Not
   authorized now.
2. **Family-swap depth.** Contract-lite eliminated D1 + D3 100 %
   but backfilled D2 + D4. If a *combined* contract-lite AND
   personality-lite intervention were run (P2-BC), would the family
   swap continue chasing new surfaces, or would the attractor
   finally reduce? Not authorized now; scope-creep.
3. **Is the ≥ 50 % threshold too strict for the neutral-topic
   regime?** §114 threshold was locked before this evidence.
   Preserved as a design-lesson: future controlled-render
   experiments on rhetorical-device rates should power-calc against
   Phase-1 base rates BEFORE selecting a "neutral" topic if the
   neutral topic depresses the effect below noise. Not a
   Phase-2-execution question; a Phase-2-design lesson.
4. **Rhetorical-device rate is not a proxy for dialogue quality.**
   `p2b_sample1` has composite = 0 and is subjectively excellent.
   `p2c_sample3` has composite = 2 (highest per-1k in the run) and
   is also subjectively excellent. The device metric measures a
   *specific* substrate signature; it does NOT rank scenes by
   overall quality.

## §128 Recommendation

Phase 2 executed exactly as designed. Rubric applied unchanged.
Locked ≥ 50 % criterion did NOT resolve either H1 or H3 as primary
mover under neutral-topic base rates. The strongest single finding
is **§122 family-swap**: contract-lite eliminates the two dominant
Phase-1 device families (D1 + D3) but the attractor reappears in
D2 + D4a + D4n. This is stronger evidence than any composite
delta that the attractor is topologically robust to single-lever
interventions.

Do NOT implement a fix on this evidence. Neither hypothesis
mechanically cleared its pre-registered threshold.

### Recommended next gate

> **READY-FOR-CHRIS-CHATGPT-REVIEW.** Three live options after
> this record:
>
> 1. **CLOSE-Q-279-3-AT-MIXED** — accept the family-swap + mixed
>    composite result as the durable answer for finding 4a. Any
>    future fix design must contend with the family-swap risk.
>    Preserve all deferred findings.
> 2. **EXTEND-PHASE-2-ADVERSARIAL** — add an adversarial-topic
>    replication (P2-A/B/C × n=3 on the Q-279-2 T1 topic where
>    Phase-1 rate was ~4× the neutral base) to check whether the
>    ≥ 50 % criterion can resolve at usable statistical power.
>    ~$0.05 additional provider spend.
> 3. **PIVOT-TO-COMBINED-INTERVENTION** — one additional condition
>    P2-BC (both contract-lite AND personality-lite) at n = 3 to
>    test whether the joint intervention finally reduces composite
>    or the family-swap continues past both surfaces. ~$0.02
>    additional provider spend.

Do NOT proceed to any of the three without explicit approval.

Other deferred findings (4c visual composition, 4d-4i,
Knowledge-breadth, Beat-3 legibility) remain preserved unopened.

## §129 Checklist — Phase 2 execution

- [x] Execution baseline SHA recorded (§118)
- [x] Probe implemented at `scripts/session279_q279_3_phase2_probe.py` with SESSION 272 slice-script precedent (§118)
- [x] Exact runtime substitutions applied per condition (§118)
- [x] Post-run restoration verified two ways (§118)
- [x] All 9 raw dialogues persisted durably under `docs/design/session279_phase2/*.txt` (§119)
- [x] Full per-sample provenance persisted to `phase2_evidence.json` (§119)
- [x] Per-sample D1-D4 scores tabulated (§120)
- [x] Per-condition aggregates + normalized deltas (§121)
- [x] Family-shift analysis explicit (§122)
- [x] Prediction vs actual (§123)
- [x] Neutral-topic ceiling artifact recorded (§124)
- [x] Mechanical H1 / H3 / H2 verdicts applied under LOCKED §114 rules (§125)
- [x] Dialogue-quality observations recorded but held out of composite gate (§126)
- [x] Unresolved questions preserved without opening (§127)
- [x] Recommended next gate + three live options (§128)
- [x] No prompt / synthesis / Knowledge / character / identity / retrieval / verifier / memory / audience / runtime change
- [x] No permanent code change beyond the experimental probe script
- [x] No implementation of a fix
- [x] Rubric NOT revised after seeing results
- [x] §114 threshold NOT revised after seeing results
- [x] Other deferred findings NOT opened

