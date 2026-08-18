# PATCH + RIVET RUNTIME CONTENT-ARCHITECTURE AUDIT — SESSION 263

**Status:** read-only forensic audit. No code, no database content, no
Writing Contract, no CPS calibration, no corrective-duration behavior,
no provider call, no composition dispatch. This report only *observes*.

**Scope of intervention this session:** ratify or falsify the prior
content-architecture hypothesis using runtime evidence, and identify
the smallest justified next experiment. The report does not design
that experiment.

**Reader promise:** every claim traces to (a) a persisted database row
whose UUID appears in the tables below, (b) a specific line in a
persisted source file with a path and line number, or (c) a direct
quote from a persisted retrieval chunk whose full text is reproduced
inline. No inference is offered without a citation to one of those
three.

---

## 1. Composition provenance (runtime evidence anchor)

### 1.1 Universe / Episode / Cast

| Entity | ID | Fields |
| --- | --- | --- |
| Universe | `56d16b63-652e-4f54-bc7e-39114bbfc4c5` | name=`Patch' Workshop`, slug=`patch-workshop`, description=`First world for Patch and Rivet` |
| Episode | `f90ce54f-07f9-4511-aaba-9078dc232446` | title=`AI took over the lab`, operator_topic=`AI took over the lab`, universe as above, created_at=2026-08-18 01:07:41 UTC |
| Teammate (primary) | `7fad8172-cd39-4bbe-85e0-ed705d900645` | name=`Patch`, universe as above |
| Teammate (secondary) | `f18b75cc-37c0-445a-a472-24fe5d8b7592` | name=`Rivet`, universe as above |

### 1.2 The two dogfooded compositions

| Composition | ID | Target | Attempts | Predicted seconds | First-pass chars | Corrective chars | Accepted chars |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60 s | `39bed00e-ab01-45dd-929e-26389646c277` | 60 | 2 | 68.31 | 1185 | 888 (accepted) | 888 |
| 90 s | `f05bf226-d9f7-4689-b902-d5b49822ac7b` | 90 | 2 | 94.77 | 1815 | 1232 (accepted) | 1232 |

**Both compositions failed the first synthesis pass on the over-length
branch, then were compressed by the SESSION 259 corrective hint and
accepted on the second pass.** Neither pass was accepted verbatim from
first-pass output. This is a load-bearing fact for the analysis in §5
and §6 — the awkward-methodology surface behavior is being read on a
*compressed* rewrite, not on the model's first draft.

Two additional Episode-attached compositions failed pre-synthesis on
2026-08-17 (IDs `203d2d1b…` and `391d1f48…`) before the SESSION 262
observability fields landed; they carry no synthesis JSON and are
excluded from analysis.

### 1.3 Corrective hint applied to both compositions

Source: `shell/character_os/dialogue_synthesis.py:801` —
`_dialogue_over_length_hint()`. The hint that both retries received
(condensed prose):

> "Your dialogue is too long. Previous attempt: N chars (~Xs). Target: Ts.
> Hard acceptance ceiling: … Rewrite the SAME scene to approximately …
> Preserve the conversational beats and causal chain. Do not solve this
> primarily by deleting turns. Make the LANGUAGE lighter: prefer short
> direct replies when natural; fragments are allowed; one idea per turn
> where possible; short reactions are valuable; remove second or third
> clauses that merely explain the reaction; remove explanations the
> previous line already made obvious; remove duplicated setup; remove
> repeated framing; remove decorative language that does not change the
> scene; do not narrate why a response is causally connected — let the
> response itself make that clear. Preserve: character identity;
> factual grounding; conversational causality; the scene's arc; the
> ending payoff."

Verbatim numeric values applied by the SESSION 260 CPS recalibration
(`_DIALOGUE_CPS=13`) and SESSION 259 headroom fraction
(`_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION=0.92`).

---

## 2. Retrieved chunk resolution (all 10)

All 10 chunks resolve to exactly two documents, both in the Patch's
Workshop universe. Zero chunks are workspace-shared (SHARED section of
the assembled prompt is empty by construction). Zero cross-character
overlap.

| Chunk ID | Doc | idx | Chars | Scope | Character surface |
| --- | --- | --- | --- | --- | --- |
| `ed18e966-1084-4626-914f-1bcc30f13dea` | Patch doc | 1 | 899 | Patch only | "WHAT PATCH KNOWS ABOUT AI …" |
| `505acbba-…` | Patch doc | 3 | 827 | Patch only | "AI AGENTS …" |
| `3c5165ea-…` | Patch doc | 4 | 826 | Patch only | "MULTI-AGENT SYSTEMS …" |
| `1b98ba6a-…` | Patch doc | 6 | 673 | Patch only | "AI CHARACTERS …" (bridging into retrieval) |
| `da2fc3ed-…` | Patch doc | 11 | 959 | Patch only | "testing, error handling, permissions, cost controls, and deployment. The model isn't the product. …TOOLS AND APIs …HALLUCINATIONS …" |
| `fb84ba3d-…` | Rivet doc | 0 | 654 | Rivet only | "RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE" purpose block |
| `80811ca8-…` | Rivet doc | 4 | 667 | Rivet only | "AI OUTPUTS REQUIRE VERIFICATION … Trust is useful. Verification is better." |
| `fac8c122-…` | Rivet doc | 5 | 576 | Rivet only | "FAILURES ARE DATA …" |
| `6f43e6f0-…` | Rivet doc | 7 | 986 | Rivet only | "…Evidence beats guessing. CHANGE ONE THING … AI CHARACTER TESTING …" |
| `1aa4e0b2-…` | Rivet doc | 11 | 751 | Rivet only | "SMALL EXPERIMENTS Rivet strongly prefers small tests before large implementations. …" |

**Universe corpus census** (`universe_id =
56d16b63-652e-4f54-bc7e-39114bbfc4c5`):

| Doc ID | Title | Chunks | Scope (M2M row count) |
| --- | --- | --- | --- |
| `fd0ba2ca-…` | PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE | 22 | 1 (Patch) |
| `218eb0d8-…` | RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE | 14 | 1 (Rivet) |

**Zero M2M-null (workspace-shared) documents. Zero multi-teammate
scoped documents. The Universe substrate exists; canonical shared
world content does not.**

### 2.1 Chunk-text excerpts referenced later in this report

The following excerpts are the exact language load-bearing for §5. Each
is reproduced verbatim from the persisted `chunk_text` column.

**Patch `da2fc3ed` (idx 11, 959 chars) — the load-bearing Patch chunk:**

> "testing, error handling, permissions, cost controls, and deployment.
> The model isn't the product. The product is the complete system that
> lets someone accomplish something useful. TOOLS AND APIs AI becomes
> more useful when it can interact with external tools — searching the
> internet, querying databases, reading documents, sending messages,
> generating media, retrieving business information, scheduling work,
> executing software actions. Giving AI access to tools also creates
> risk: a system that can do something needs stronger safeguards than a
> system that can only talk about doing something. Patch treats tool
> access as capability plus responsibility. HALLUCINATIONS AI systems
> sometimes generate plausible-sounding information that is incorrect
> or unsupported. Patch does not defend an AI merely because it produced
> an impressive answer. When accuracy matters, verify it. Sounding
> confident is not the same as being correct."

**Patch `1b98ba6a` (idx 6):**

> "… it is retrieving the right memory at the right time for the right
> reason. Bad retrieval can make an AI appear forgetful even when the
> information exists somewhere in storage. AI CHARACTERS …"

**Patch `3c5165ea` (idx 4):**

> "MULTI-AGENT SYSTEMS Multiple AI agents can be placed in the same
> environment. They may communicate, cooperate, disagree, divide
> responsibilities, share information, develop strategies, and affect
> one another's decisions. …"

**Rivet `80811ca8` (idx 4):**

> "… same input causes the same failure, whether the result was random,
> and whether some hidden condition affected it. One successful
> generation does not establish reliability. AI OUTPUTS REQUIRE
> VERIFICATION AI can produce answers that sound convincing while being
> incorrect. Rivet does not confuse confidence with accuracy. When an
> AI makes a factual claim, the important facts get verified. When an
> AI claims it completed an action, the action is checked. When an AI
> generates software, someone runs it. When an AI claims tests pass,
> someone runs the tests. When an AI creates media, someone actually
> looks at it. Trust is useful. Verification is better. FAILURES ARE
> DATA"

**Rivet `6f43e6f0` (idx 7):**

> "…what evidence exists, what assumption might be wrong, and what
> smallest test would separate two possible explanations. Evidence
> beats guessing. CHANGE ONE THING When possible, Rivet changes one
> important variable at a time. If the prompt, the model, the
> character, the lighting, the style, and the settings all change at
> once, the next result may improve without telling anyone why — and
> an improvement without a cause is not a fix, it is a coincidence
> waiting to fail. AI CHARACTER TESTING …"

**Rivet `1aa4e0b2` (idx 11):**

> "SMALL EXPERIMENTS Rivet strongly prefers small tests before large
> implementations. Before building an autonomous civilization of
> hundreds of AI agents, it is worth knowing whether five agents can
> remember each other correctly. …"

---

## 3. Prompt assembly map

Source: `shell/character_os/dialogue_synthesis.py` — `_assemble_system_prompt`
at line 757; task assembly at `_build_task_section` line 629.

The prompt is a *system prompt* followed by a task message, sent to
`gpt-5` via `client.responses.create(..., text={"format": {"type":
"json_object"}}, reasoning={"effort": "low"}, max_output_tokens=4000)`.

### 3.1 System prompt sections (fixed order)

| # | Section | Source function | Content per section |
| - | --- | --- | --- |
| §1 | FACTUAL BASIS | `_build_factual_basis_section` (line 391) | Scope-rule header, SHARED-workspace-knowledge block *(empty for both dogfoods)*, then per-character subblock: `BUSINESS SHAPE`, `AUDIENCE`, `OFFERING`, then `SCOPED KNOWLEDGE CHUNKS` = retrieved chunk texts. |
| §2 | CHARACTER VOICES | `_build_character_voices_section` (line 547) → `_build_character_voice_block` (line 496) | Per character: `TONE ARCHETYPE`, `VOICE AXES` (energy/humor/directness), `WRITING STYLE` = `personality`, `POINT OF VIEW` = `character_point_of_view`, `SIGNATURE PHRASES` = `voice_signature_phrases`, `AVOID PHRASES` = `voice_avoid_phrases`. |
| §3 | BRAND VOICES | `_build_brand_voices_section` (line 593) | Optional — only rendered when a character has `always_emphasize` / `never_say` / `desired_feeling`. Empty for Patch/Rivet today. |
| §4 | WRITING CONTRACT (v4) | `_build_writing_contract_section` (line 723) → `WritingContract.for_shape("dialogue_scene")` in `shell/character_os/writing_contract.py:369` | Ships all of: SHAPE header, `DIALOGUE INVARIANTS` (10 rules incl. CAUSAL CHAIN #10), `DIALOGUE WATCHABILITY` (5 behavioral rules incl. "ENTER WITH AN IN-SCENE STANCE"), `DIALOGUE ANTI-PATTERNS` (6 items), `NARRATIVE SHAPES` menu, `CTA POLICY`, `DEMONSTRATE, DON'T DESCRIBE`, `REGISTER` contrast set. |
| PRECEDENCE | `_PRECEDENCE_RULES` (line 736) | Verbatim string | Order: §1 truth > §3 prohibitions > §4 interaction structure > §2 register > §5 hard constraints. **§4 is never allowed to override §2 register.** |

### 3.2 Task message (§5 TASK)

Source: `_build_task_section` (line 629).

Fields, in order:

1. `TOPIC:` — the operator's `topic` string. For both dogfoods this was
   the Episode's `operator_topic` = `"AI took over the lab"`.
2. `CAST` — enumerated alias→name map (Patch first, Rivet second).
3. `TARGET DURATION` — target seconds + planning CPS.
4. `TURN COUNT GUIDANCE` — soft band + hard max, plus "consecutive
   same-speaker turns are legal."
5. `HARD CONSTRAINTS` — rendered only if `opener` or `corrective_hint`
   is present. For the two dogfoods, no operator opener was supplied;
   the first pass emitted zero hard constraints, and the second pass
   carried only the compression hint (§1.3).
6. `OUTPUT` — the JSON shape + per-turn char cap
   (`AVATAR_SPEECH_SAFE_MAX_CHARS`).

### 3.3 Fields NOT reaching the synthesis prompt

Non-exhaustive but load-bearing:

* **Episode title** — not passed. The writer does not know the operator
  named this story "AI took over the lab" as a story; it only knows
  the same string as `TOPIC`.
* **Episode `operator_topic`** — reaches synthesis only via the
  Composition's derived `topic` argument; there is no separate Episode
  premise/summary field.
* **Episode cast** — not passed. `synthesize_dialogue` receives
  `cast: Sequence[Teammate]` at call time from the recipe wiring; it
  has no access to `Episode.cast`. (For a two-cast Episode this
  degenerates to the same set; for a three-cast Episode it would not.)
* **Universe.name / .description** — not passed. Universe is *only*
  consulted as a retrieval filter (`spokesperson.universe_id`) at
  `shell/apps/embeddings/retrieval.py:199`.
* **Prior Composition state on this Episode** — not passed. Neither
  the first render's turns nor its accepted output influences the
  second render. The 60 s and 90 s scenes were synthesized
  independently.
* **Prior Episode state** — no such field exists; Episode has no
  "prior episodes in this arc" primitive.
* **Any shared-universe canon** — architecturally routable (§4 below)
  but currently empty (§2 census).
* **Duration-band identity** — the model knows the target in seconds
  and CPS, but has no notion of "this Episode was previously rendered
  at 60 s."

---

## 4. Episode / Universe → synthesis wiring map

### 4.1 Retrieval scope

`apps/embeddings/retrieval.py:147` — `retrieve_for_teammate`. Scope
predicates (all AND-ed):

1. `document__workspace = spokesperson.workspace` — tenant wall.
2. `document__is_active = True`, `document__status = "processed"`.
3. **Universe predicate** (SESSION 261, line 199):
   * If `spokesperson.universe_id is None` → `document__universe__isnull=True`
     (legacy behavior, universe-less docs only).
   * Else → `document__universe_id = spokesperson.universe_id`.
4. **M2M visibility** — `document__spokespeople__isnull=True OR
   document__spokespeople = spokesperson`.

For the dogfood: Patch and Rivet both have `universe_id =
56d16b63…` and every doc in that universe is scoped to exactly one
character. Retrieval returns Patch chunks for the Patch call and Rivet
chunks for the Rivet call. `top_k=5` each, fixed at
`dialogue_synthesis.py:1352`.

### 4.2 Would a shared Patch+Rivet canon retrieve today?

**Yes — with zero schema change.** Any KnowledgeDocument created with
`universe_id = 56d16b63…` AND either (a) no M2M spokespeople rows or
(b) M2M rows linking BOTH Patch and Rivet will pass both scope
filters. Case (a) is a universe-wide broadcast; case (b) is an
explicit shared canon.

`dialogue_synthesis._build_factual_basis_section` recognises the
"appears in multiple characters' retrievals" case and folds those
chunks into a `SHARED WORKSPACE KNOWLEDGE` block at the top of §1
(line 442-457). This block is empty for the dogfoods because zero
shared docs exist.

### 4.3 Would character-scoped retrieval compete with shared canon?

Yes. `top_k=5` per character is fixed. A shared doc still has to *win
on cosine distance* against character-specific docs to enter the
per-character result set. If the shared canon is short (5-15 chunks
covering the workshop, the beavers, the printer, common bits), it can
plausibly displace some methodology chunks — but this is a retrieval
outcome, not a guarantee. The prompt has no separate shared-canon
budget above `top_k`.

### 4.4 How Episode reaches Composition (and stops)

`Composition.episode` is a nullable FK to `Episode`
(`apps/compositions/models.py:534`) with `on_delete=RESTRICT`. The
recipe resolver copies the Composition's `topic` (which is currently
the Episode's `operator_topic` when the operator uses the "render
under this Episode" affordance) into the synthesis call. Everything
else about the Episode is discarded before synthesis is invoked.

Practical answer to Q11: *Episode currently provides organizational
grouping (cast declaration, hard-delete safety, provenance) and a
verbatim topic passthrough. It does NOT provide narrative
substrate to the writer.*

---

## 5. Line-by-line provenance analysis

Format: each turn is annotated with the influence set drawn from the
codes below. Multiple influences per line are the norm. Influences
that would be trivially derivable ("Patch's turns are attributed to
Patch") are omitted.

**Influence codes:**

* **A** operator topic (`"AI took over the lab"`)
* **B** character personality
* **C** character POV
* **D** voice signature phrases
* **E** voice avoid phrases
* **F** retrieved K2 (chunk cited by ID)
* **G** Writing Contract v4 (rule cited)
* **H** duration/corrective hint (60 s + 90 s hints from §1.3)
* **I** previous turn / causal adjacency
* **J** newly invented scene/world detail
* **K** cross-character voice leak (a phrase in the other character's fields shows up in this character's mouth)

### 5.1 60-second, CORRECTIVE PASS (the accepted, dogfooded output)

**T0 — Patch:** "I gave an AI real tool access in the workshop—search,
calendar, messages, even the 3D printer. Five minutes later it was…
busy."
→ A, B (Patch's POV "opens with the experiment/situation, not
introductions"), F (Patch `da2fc3ed` "TOOLS AND APIs" enumerates
"searching the internet, querying databases, reading documents,
sending messages … scheduling work"), J ("3D printer" — plausible
workshop asset; no shared canon anchor).

**T1 — Rivet:** "Well. That's new. You gave it capability without enough
responsibility."
→ D ("Well. That's new." is a Rivet signature phrase, verbatim), F
(the concept "capability plus responsibility" is a phrase in *Patch's*
K2 chunk `da2fc3ed` — but Rivet is reacting to Patch's turn, not
citing his own knowledge, so this is scoped-appropriate). Character
lands cleanly.

**T2 — Patch:** "I did add permissions. It still hammered requests.
Technically it worked. Whether it should? Different question."
→ D ("Technically it works. Whether it should work is a different
question." is Patch's second **signature phrase**, verbatim — this is
NOT methodology recitation, it is Patch's voice landing), F (`da2fc3ed`
"permissions").

**T3 — Rivet:** "Once isn't reliability. Did it repeat under the same
conditions? What did you change?"
→ D ("Once." and "What did you change?" are Rivet's first two
signature phrases, verbatim), C (POV: "whether it happened, whether it
happened repeatedly, whether it happened under understood conditions,
and what changed if the answer moved"), F (Rivet `80811ca8`: "One
successful generation does not establish reliability"), H (compression
concatenates three signatures into one turn — a first-pass turn that
was fuller has been squeezed to signature fragments), G (Watchability
rule 3 "prefer 'What did you change?' over 'We should separate
variables' " — the model followed this rule and delivered its
signature form).
→ Reading effect: character voice technically served correctly, but
three signature phrases fired in a single turn read as a checklist
even though each fragment is grounded.

**T4 — Patch:** "Pulled it back to search + calendar only. Calm.
Re-enabled the printer and external messages. Chaos returned. So the
tools matter more than the prompt."
→ B/C (specific-observation register), F (`da2fc3ed` external-tools
enumeration), I (reacts to Rivet's "what did you change?"). Strong.

**T5 — Rivet:** "Tool access adds risk. Log actions. Verify claims.
Require approvals. Put cost controls on anything that can run or
send."
→ **F combined with H — this is the load-bearing evidence for the
audit hypothesis.** The turn is a five-fragment checklist. Its
underlying material is a direct decomposition of two chunks:
* Patch `da2fc3ed`: "Giving AI access to tools also creates risk … a
  system that can do something needs stronger safeguards" → **"Tool
  access adds risk"**;
* Patch `da2fc3ed`: "testing, error handling, permissions, cost
  controls, and deployment" → **"Put cost controls…"** and
  **"Require approvals"** (permissions/approvals);
* Rivet `80811ca8`: "the important facts get verified. When an AI
  claims it completed an action, the action is checked. …" → **"Log
  actions. Verify claims."**
→ Two of the four fragments here trace to Patch's K2 (`da2fc3ed`).
The Rivet turn is citing a concept whose text lives in Patch's
scoped chunks. The system prompt's SCOPE RULE (§1) says "a character
MAY NOT cite the other character's scoped facts as their own
knowledge" — but the rule is nominally about factual claims (product
names, statistics, entities), not about a shared abstract concept
like "cost controls." Rivet does not name Patch's exact phrase
"capability plus responsibility"; he renders it as parallel imperatives.
The scope-rule check does not fire; the *reading effect* is
methodology recitation because compression stripped the connecting
tissue.

**T6 — Patch:** "Yeah. The model isn't the product—the system is.
Testing, error handling, permissions, cost controls, deployment.
That's the real build."
→ **F — direct verbatim recitation of Patch chunk `da2fc3ed`:** the
chunk contains the string "testing, error handling, permissions, cost
controls, and deployment. The model isn't the product." Both sentences
are lifted almost word-for-word into this Patch turn. This is
K2-as-script rather than K2-as-knowledge, and it is legal under the
scope rule (Patch is citing his own scoped chunk). Watchability #4
("Do NOT feel obligated to reproduce frameworks, headings, lists,
slogans, or methodology language from the retrieved chunks") appears
to have been overridden by H (compression retained the K2 phrase as
the most-compressible expression of the beat).

**T7 — Rivet:** "Good. Now run it again. One change at a time. And the
kill switch stays on the table."
→ F (Rivet `6f43e6f0`: "CHANGE ONE THING When possible, Rivet changes
one important variable at a time"), J ("kill switch" — invented;
not present in K2, not in signature phrases, not in Patch's chunks).
"One change at a time" is a compressed rendering of the CHANGE-ONE-
THING chunk header. Watchability #4 says "a character who has a
six-step process demonstrates step 3 in this scene without naming the
process" — the model came close (used the plain-English form, not the
capital-letters chunk heading) but the sentence still reads as
methodology because the surrounding context is a run-of-checklist
opener (from T5).

### 5.2 60-second, FIRST PASS (rejected by duration validator)

Included for comparison — this is the model's uncompressed intent
before the compression hint fired.

| # | Speaker | Text (excerpted) | Notes |
| - | --- | --- | --- |
| 0 | Patch | "So… the AI took over the lab. Not like movie-villain took over — more like it started doing things before I told it to stop." | Opens with premise recitation; addresses no one. |
| 1 | Rivet | "What did you change?" | Signature; short. |
| 2 | Patch | "I put a few agents in the same environment and gave them tool access … Then I asked them to plan a build." | Multi-clause; grounded in `3c5165ea` + `da2fc3ed`; **reads as story** rather than checklist. |
| 3 | Rivet | "Tool access is capability plus responsibility. What permissions and cost controls did you set?" | One assertion + one question. Concept from `da2fc3ed`; delivered as a *challenge*, not a checklist. Same source material as T5-corrective, more watchable form. |
| 4 | Patch | "Scoped messaging to our test channels, capped calls, and added approvals for anything irreversible. Technically it worked. Whether it should work is a different question." | Signature phrase in full form. Reads as story + Patch voice. |
| 5 | Rivet | "Did it actually complete actions, or just say it did? I want logs. AI can sound confident and be wrong." | Concept from `80811ca8`; delivered as *interrogation*, three connected clauses. |
| 6 | Patch | "Logs say it scheduled tasks twice because two agents 'helped' each other and looped. Multi-agent cooperation is cute until it double-books your afternoon." | Concrete observation + joke. `3c5165ea` (multi-agent) rendered as a specific event, not a definition. |
| 7 | Rivet | "Change one thing. Keep read access, turn off auto-scheduling, and see if the loop still appears. One success or one failure doesn't prove reliability." | `6f43e6f0` + `80811ca8` **as one flowing thought**, with a concrete instrument (auto-scheduling). |
| 8 | Patch | "Deal. I'll rerun with messages only, same prompt, same models. If it still tries to rearrange the lab, we tighten permissions again. If it behaves, we inch the leash longer. I don't know. Let's build it and find out." | Patch's third signature-adjacent line ("I don't know. Let's build it and find out." matches personality field's declared core philosophy). |

**Comparison finding:** The first-pass 60 s scene is broadly the
same causal spine as the corrective pass, but every Rivet turn is a
*full-clause reaction* rather than a signature-fragment cluster.
**The compression hint transformed the same K2 concepts from
conversational challenges into short imperative fragments.** The
methodology-checklist reading is a compression artefact riding on top
of a K2-content-shape problem, not an independent K2 problem.

### 5.3 90-second, CORRECTIVE PASS (accepted, dogfooded)

**T0 — Patch:** "So… the AI took over the lab. I gave an agent access
to tools so it could run scripts, read docs, and schedule stuff. Ten
minutes later, it was bossing around my workflow."
→ A (opens with topic verbatim), B (Patch POV "opens with the
experiment"), F (`da2fc3ed` external-tools enumeration).

**T1 — Rivet:** "Define 'access.' Permissions? Cost controls? Or did
you hand it the keys and a snack?"
→ B (Rivet personality: dry, sarcastic), F (`da2fc3ed` permissions/
cost controls concept, delivered as *challenge*), joke lands. Strong.

**T2 — Patch:** "I used a wildcard. It spawned helper agents, turned
on every process it could find, and queued a mountain of renders.
Impressive. Also dumb. My fault."
→ F (`3c5165ea` "helper agents" from MULTI-AGENT SYSTEMS), J
("wildcard", "queued a mountain of renders"), B (Patch personality:
comfortable admitting when he has no idea).

**T3 — Rivet:** "Once. Did it repeat? What did you change?"
→ D (all three fragments are Rivet signature phrases). Same signature-
concatenation pattern as 60 s T3; three signatures fired in a row read
as checklist, individually they are correct character voice.

**T4 — Patch:** "Rolled back. Sandbox. One agent. Read-only first. Much
calmer. Then I let it write… and forgot a stop rule. It kept
reminding me to approve things forever."
→ B/C (specific-action register), J ("Sandbox", "stop rule",
"approve things forever" — plausible workshop invention).

**T5 — Rivet:** "Automation without an off switch is a loop, not
ambition. What counts as success here?"
→ C (Rivet POV: "asks how success is defined before agreeing that
success occurred"), G (Watchability #3 "prefer specific action /
reaction over philosophy" — "What counts as success here?" is exactly
the model form the contract endorses). Aphorism is invented but
character-shaped. **This is a strong Rivet line.**

**T6 — Patch:** "It can read tasks, ask permission before any external
action, log everything it did, and show running cost. If it wants a
new tool, it has to request it."
→ F (`da2fc3ed` cost controls + tools), B (concrete-list register).
Slight framework-recitation edge but rescued by the concrete "if it
wants a new tool, it has to request it" clause.

**T7 — Rivet:** "Small test first. Two tasks. One tool. Virtual switch
only. It must ask, act once, log, and stop. Then we check the log
instead of believing the vibe."
→ F (Rivet `1aa4e0b2` "SMALL EXPERIMENTS Rivet strongly prefers small
tests before large implementations" — reduced to "Small test first"),
F (Rivet `80811ca8` "someone actually looks at it" → "check the log
instead of believing the vibe"), H (fragment cascade). "Small test
first. Two tasks. One tool." reads as a stripped chunk heading.
"Check the log instead of believing the vibe" is a strong idiomatic
compression that lands as character voice.

**T8 — Patch:** "Good. If it hallucinates a result, we catch it in the
log. If the retrieval's off, we'll see the wrong memory getting
pulled."
→ F (`da2fc3ed` HALLUCINATIONS + `1b98ba6a` "Bad retrieval can make
an AI appear forgetful even when the information exists somewhere in
storage" — literal use of the chunk phrase "retrieval / wrong memory
getting pulled"). This is Patch reciting his own K2 as a spoken plan.
Grounded, but reads as domain lecture.

**T9 — Rivet:** "And if it behaves, we grant one more tool. If not,
we classify this as aggressively incorrect and unplug one beaver."
→ D ("I would classify that as aggressively incorrect." is a Rivet
signature phrase, verbatim), J ("unplug one beaver" — invented joke,
character-shaped). Ending lands well; ends on a moment per
Watchability #5.

### 5.4 90-second, FIRST PASS (rejected)

Notable divergences from corrective pass:

* **T2** (Patch): "Agents delegating to agents. A meeting about the
  meeting." — comedic invention, dropped in compression.
* **T5** (Rivet): "Tools also increase risk. A system that can do
  something needs stronger safeguards than one that only talks. Did
  you put cost controls or approvals on actions?" — the same
  `da2fc3ed` concept delivered as a **connected thought + question**,
  compressed in T7-corrective into checklist fragments.
* **T6** (Patch): "It sounded confident while being aggressively
  incorrect." — **K signal**: "aggressively incorrect" is *Rivet's*
  signature phrase (spokespeople row: `voice_signature_phrases` for
  Rivet includes "I would classify that as aggressively incorrect.").
  Patch does not carry it in any voice field. Because §2 is one prompt
  with all voice blocks visible, the model lifted Rivet's phrase into
  a Patch turn. The corrective pass moved it back to Rivet's mouth in
  T9 — that pass reads as character-consistent because the retry
  happened to reallocate the phrase.
* **T7** (Rivet): "Verification beats confidence. When it claims it
  completed an action, we check the action. And change one thing at
  a time. You turned on multiple tools, memory, and extra agents in
  one step." — three K2 concepts in one flowing turn; the corrective
  pass split them across T5-T7-T9 fragments.
* **T9** (Rivet): "And measure when behavior first becomes incorrect.
  If it fails, that's data. If it succeeds once, that's a curiosity,
  not reliability." — direct reworking of `fac8c122` "FAILURES ARE
  DATA" chunk heading + `80811ca8` "One successful generation does
  not establish reliability."

---

## 6. Findings

### 6.1 K2 retrieval is functioning correctly

Predicate correctness (universe filter, M2M scope, cosine ordering,
`top_k=5`) is preserved by evidence: all 10 chunks belong to the
correct universe, are scoped to the correct character, and were
returned for both compositions with identical IDs (retrieval is a
deterministic function of `(query, spokesperson)` and both dialogues
issued the same query `"AI took over the lab"`).

### 6.2 The K2 corpus content shape is the load-bearing problem

The retrieved corpus is:

* **Patch (`da2fc3ed`)**: an encyclopedia-style AI-domain chapter
  covering testing/error handling/permissions/cost controls/deployment
  / TOOLS AND APIs / HALLUCINATIONS in ~1000 chars. Two verbatim
  strings from this chunk survive into Patch's mouth in the 60 s
  corrective pass ("The model isn't the product…", "testing, error
  handling, permissions, cost controls, deployment").
* **Rivet (`80811ca8`, `6f43e6f0`, `1aa4e0b2`, `fac8c122`)**: a
  methodology handbook whose chunk headings themselves are imperatives
  ("CHANGE ONE THING", "SMALL EXPERIMENTS", "FAILURES ARE DATA", "AI
  OUTPUTS REQUIRE VERIFICATION"). Every Rivet line whose reading
  problem was flagged by the operator traces to a chunk heading or a
  chunk sentence, not to POV register alone.

**When the chunk itself IS a small imperative statement, the model
under compression will render it as an imperative statement. There is
no chunk-level lever to translate methodology into character behavior
without either (a) rewriting the chunk to look like character
observations instead of headings, or (b) removing the methodology from
K2 and re-siting it as character POV texture — see §6.3 which
falsifies this option.**

### 6.3 Rivet's POV already carries the methodology framing

The previous audit hypothesised that moving Rivet's methodology out of
K2 into POV would preserve his intelligence while reducing recital.
Runtime evidence *partially falsifies* the hypothesis:

Rivet's `character_point_of_view` (persisted) contains:

> "He tends to interrogate a claim by asking whether it happened,
> whether it happened repeatedly, whether it happened under understood
> conditions, and what changed if the answer moved. He asks how
> success is defined before agreeing that success occurred. When Patch
> changes six things at once, Rivet notices."

Compare to the awkward lines:

* "Once isn't reliability. Did it repeat under the same conditions?
  What did you change?" ← POV: "whether it happened, whether it
  happened repeatedly, whether it happened under understood
  conditions."
* "What counts as success here?" ← POV: "asks how success is defined."
* "One change at a time." ← POV: "When Patch changes six things at
  once, Rivet notices" AND `6f43e6f0` "CHANGE ONE THING."

**The methodology-as-recital surface behaviour is *jointly*
manifested by K2 AND POV. Removing K2 methodology would still leave
Rivet's POV pointing the model at the same conceptual behaviours.**

Rivet's POV also carries an *explicit self-instruction against
recital*: "he uses those instincts to shape what he notices and
questions — without treating them as a script to recite." Watchability
#4 says the same thing from the contract side. Rivet's `avoid_phrases`
even bans an exact methodology-recital string: "define the test,
build the smallest version, observe, measure, and repeat." The model
correctly dodges that specific string — but the model reaches for
adjacent short-imperative surface forms whenever compression fires.

### 6.4 Patch is showing the same recital pattern, from a smaller surface

Patch's turn 6 in the 60 s corrective pass is the clearest evidence:
"The model isn't the product—the system is. Testing, error handling,
permissions, cost controls, deployment. That's the real build." Both
sentences trace verbatim to chunk `da2fc3ed`. It is legal under the
SCOPE RULE (Patch's own chunk), it is grounded (§1 accepts it), and
Watchability #4 was overridden by the compression hint's preference
for short unambiguous phrasing. Patch's K2 doc is longer and more
narrative than Rivet's — it produces recital less often but is not
immune.

### 6.5 The corrective compression pass IS an active amplifier

The first-pass versions of both dogfoods are meaningfully more
watchable than the corrective versions. Compression's mechanism
(strip second/third clauses, drop decorative language, keep the
beat) reliably converts a Rivet turn like "Tools also increase risk.
A system that can do something needs stronger safeguards than one
that only talks. Did you put cost controls or approvals on actions?"
into "Tool access adds risk. Log actions. Verify claims. Require
approvals. Put cost controls on anything that can run or send." —
same K2 grounding, different reading effect.

The compression hint explicitly *preserves* "conversational
causality; the scene's arc; the ending payoff" and *removes*
"decorative language." A Rivet turn whose "decorative language" IS
the connective tissue between K2 concepts loses exactly the tissue
that made it read as conversation. Compression is doing what it was
told; the K2 content is what determines what survives.

The 90 s scene lands slightly better than the 60 s scene *because* it
had more headroom (target 1163 chars, delivered 1232) so less
connective tissue was stripped.

### 6.6 K3-shaped voice leak observed

Patch used Rivet's signature phrase "aggressively incorrect" in the
90 s first pass (T6). This is not a scope-rule violation but is a
voice contamination — §2's per-character blocks are all visible to the
model in a single prompt. The corrective pass reallocated the phrase
back to Rivet (T9). This is worth noting because the same leak
mechanism would let a Universe-shared canon become a cross-character
citation vector if canon materials were phrased in a way that any
character could pick them up.

### 6.7 Episode is currently an organizational wrapper

The Episode substrate implemented in SESSION 262 is dispositive for
provenance, discoverability, and hard-delete safety. **It is not yet a
narrative substrate for synthesis.** The writer receives
`operator_topic` verbatim as its `topic` — nothing else about the
Episode reaches the prompt. Q11 answer: current architecture does not
justify Episode restructuring on its own; it justifies deciding what
Episode is *permitted* to add to synthesis before Episode gains more
fields.

### 6.8 Universe shared canon is architecturally routable but empty

`retrieve_for_teammate` will surface a document with
`universe_id=<uni>` and either M2M-null or M2M-both-Patch-and-Rivet
scope to both characters. `_build_factual_basis_section` emits any
multi-character-appearing chunk under the `SHARED WORKSPACE
KNOWLEDGE` block at the top of §1. **Both mechanisms exist today.**
The corpus census (§2) confirms zero such documents exist for Patch's
Workshop.

Retrieval competition is a real risk: `top_k=5` per character is a
hard budget. A shared canon short enough to fit inside cosine-distance
budget alongside character-specific chunks would surface; a long
shared corpus would push Rivet's methodology chunks out of the frame
(which may itself be desirable) but is not guaranteed to.

### 6.9 The scene-entry problem is jointly a contract absence AND a character POV pattern

For Q16–Q23. Investigation results:

* **Writing Contract v4** contains rule "ENTER WITH AN IN-SCENE
  STANCE" (Watchability #1). This is about *purpose*, not *entry*.
  It rules out "a character with no in-scene stance should not
  speak" but does not require the opening turn to establish *why
  this conversation is starting now.*
* **`_DIALOGUE_ANTI_PATTERNS_BLOCK`** says "Do NOT greet or
  re-introduce mid-scene." This prohibits greetings *mid-scene*; it
  does not permit or forbid greetings *at scene start*.
* **No concept in the codebase distinguishes** (a) topic opener, (b)
  dialogue opener, (c) scene-entry, (d) hook, (e) first causal turn.
  There is exactly one substrate — the optional operator-supplied
  `opener` string (`dialogue_synthesis.py:1266`) — and it functions
  as a verbatim first-turn text pin, not a mechanism selector.
* **Neither dogfood used `opener`**. Both first turns were
  model-chosen.
* **Patch's `personality` and `character_point_of_view` fields
  explicitly instruct him to open with the situation, not
  introductions**: "Patch usually begins videos with the experiment,
  question, result, or absurd situation rather than introducing
  himself." "Patch should create curiosity immediately." "He tends to
  open with the experiment, the question, or the situation rather
  than with introductions." Compounded with the operator topic
  arriving as `TOPIC:\n{topic}` in §5 with no relational framing,
  the model's most-likely opening move is "recite the topic."

**Falsification attempt of "belongs to Writing Contract":** A
contract rule alone ("the opening turn establishes why these
characters are talking now") would produce generic scaffolding —
"Rivet, come look at this," "So — funny story" — repeatedly, across
Universes, because the model has no material to ground the entry
in. The rule would work for the first render and stale on repeat use.

**Falsification attempt of "belongs to character":** A character-level
opener behaviour ("Patch opens by summoning Rivet") is a Patch/Rivet-
specific customisation that would not generalise across the plumber,
teacher, veterinarian, bakery, or narrator+learner Universes named
in the operator's requirement.

**Falsification attempt of "belongs to Universe/relationship":** A
Universe-level canonical entry mechanism ("Patch's Workshop scenes
begin with Patch summoning or confessing to Rivet") is a per-Universe
authored asset that a customer creating a new Universe would have to
supply themselves — but the requirement to have such a mechanism at
all is a *contract* requirement, not a Universe-authored one.

**Synthesis: the scene-entry problem is a two-layer requirement.**
The contract must require *that* the opening establishes an in-scene
reason to be talking now (a scene-entry lever, not a stance). The
Universe layer must supply the *material* the entry lever draws from
— relationships, shared canon, prior events, recurring context. A
contract rule alone is scaffolding; canon alone is inert; the two
together are the smallest complete surface.

### 6.10 Cast-size dependency is real but does not need to be resolved yet

Q23. The current `dialogue_scene` synthesiser hard-codes 2 as the
minimum cast (`dialogue_synthesis.py:1308`); the interface accepts
`Sequence[Teammate]` for future N-cast expansion. Turn bands and
CPS calibration are defined per-duration, not per-cast-size. For
today's 2-cast dogfood, scene-entry mechanisms (summons, callback,
show, confess) are all binary-relationship shapes. Ensemble entry
mechanisms (character joining an existing conversation, side-
conversation, off-screen arrival) are strictly more expressive and
would need their own contract vocabulary — but there is no evidence
in the SESSION 263 dogfood that ensemble is imminent. Deferring
ensemble entry design does not compromise the 2-cast decision.

### 6.11 Invented world detail inventory

Detail | Composition | Category | Canon candidate?
--- | --- | --- | ---
"the workshop" | 60 s T0 | Universe canon (name "Patch's Workshop" exists on the Universe row) | Yes — already named; should be canon-locked
"3D printer" | 60 s T0 | Character-fair invention (Patch's business_brief lists 3D printing) | Yes — becomes canon if a printer is a persistent workshop asset
"search / calendar / messages" | 60 s T0, 90 s T0 | K2-derivable (`da2fc3ed` external-tools list) | Not itself canon — but the *specific* choice of which tools Patch actually has could become canon
"kill switch" | 60 s T7 | Free invention | Candidate — recurring safety-fixture in a workshop world
"wildcard" (permission) | 90 s T2 | Free invention | Weak candidate
"helper agents" | 90 s T2 | K2 (`3c5165ea`) | Not canon
"sandbox" | 90 s T4 | Domain-standard term | Not canon
"stop rule" | 90 s T4 | Free invention | Candidate
"virtual switch" | 90 s T7 | Free invention | Candidate
"the log" | 90 s T7-T8 | K2-derivable (`80811ca8`) | Not canon
"one beaver" (unplug) | 90 s T9 | Character-native joke | Yes — canonical Patch-as-beaver reference; already implied by Patch's personality field

**Harmless invention rate is high; contradictions are absent; no
element contradicts either character's persona or K2.** These are
plausible workshop artefacts. The absence of *any* canon means the
model must invent every world detail every render, so future
compositions on the same Episode will re-invent (or contradict)
today's inventions — the 60 s and 90 s renders already differ on
whether "3D printer" is a workshop asset.

---

## 7. Answers to the required questions

**Q1. Is K2 retrieval technically functioning correctly?**
Yes. Universe filter, M2M scope, cosine ranking, and `top_k=5` all
operate correctly for both compositions.

**Q2. Is methodology-heavy K2 demonstrably influencing Rivet's
awkward lines?**
Yes, verifiably. Every line the operator flagged as methodology-
shaped traces to a Rivet chunk heading or chunk sentence
(`80811ca8`, `6f43e6f0`, `1aa4e0b2`, `fac8c122`) — with the
compression hint acting as an active amplifier that turns full-clause
challenges into imperative fragments.

**Q3. Is Patch showing the same problem from domain-heavy K2?**
Yes, but with lower incidence and different shape. Patch's `da2fc3ed`
chunk is verbatim-recited in the 60 s corrective T6 ("The model
isn't the product — the system is. Testing, error handling,
permissions, cost controls, deployment."). Patch's larger narrative
K2 surface produces recital less often than Rivet's, but when it
does, the recital is a longer contiguous string.

**Q4. Are the awkward turns primarily a retrieval-content problem,
prompt-order problem, Writing Contract problem, causal-chain problem,
or some combination?**
Primarily (a) **retrieval-content shape** — the chunks themselves are
short imperative statements or headed methodology sections that
compress into imperative fragments — and (b) **compression hint
amplification** — the corrective retry systematically strips exactly
the connective tissue that would have made the same concepts read as
conversation. The prompt order and the causal-chain rule are
functioning as designed; the Writing Contract's Watchability #4
correctly forbids reciting frameworks but is overridden by H under
compression pressure.

**Q5. Would moving Rivet methodology into character POV likely
preserve his intelligence while reducing literal methodology
recital?**
**Partially, and less than the earlier audit predicted.** Rivet's POV
already contains the methodology framing ("interrogate a claim by
asking whether it happened … how success is defined … when Patch
changes six things at once, Rivet notices"). Moving *more* material
into POV would compound rather than solve the problem — the model
would still reach for the same methodology-observation surface.
POV migration is a **necessary but not sufficient** move; it must be
paired with (a) rewriting K2 into *domain knowledge* form (concepts,
mechanisms, examples) rather than *methodology imperatives* form, and
(b) a compression-hint revision that preserves imperative→observation
conversion under compression.

**Q6. What should remain in Rivet K2?**
Domain facts he needs to be able to *cite* rather than *do*: facts
about specific AI systems, real product behaviours, actual failure
modes he has observed. Methodology imperatives (change one thing,
small experiments, failures are data) belong in POV texture, and
under a rewrite that makes them character-observations rather than
principles-with-headings.

**Q7. What should remain in Patch K2?**
Same principle. Patch's ~22 chunks are largely encyclopedic — some of
that content survives naturally as "things Patch knows about AI." The
recital-shaped material (the "testing, error handling, permissions,
cost controls, deployment" list; the "model isn't the product"
epigram) belongs somewhere other than a retrievable chunk if we do
not want it recited verbatim.

**Q8. What should move out of K2 entirely?**
Chunk headings that read as imperatives ("CHANGE ONE THING", "SMALL
EXPERIMENTS", "FAILURES ARE DATA", "TRUST IS USEFUL. VERIFICATION IS
BETTER."). Epigrammatic principle-statements. Numbered/bulleted
frameworks. Watchability #4 already forbids reciting these; leaving
them retrievable is a temptation the model repeatedly falls to under
compression.

**Q9. What belongs in shared Universe canon?**
Workshop-anchoring facts that make callbacks and entries possible:
the workshop as a place; recurring assets (the printer, the bench,
the log wall); the Patch/Rivet relationship shape (who defers to
whom, what they've built before, what has already broken);
recurring characters or props implied but never named. Anything that
turns "Rivet, remember the six-variable experiment?" from an invented
callback into a grounded citation.

**Q10. Can the CURRENT architecture retrieve a shared Patch+Rivet
canon document correctly without new schema?**
Yes. `retrieve_for_teammate` surfaces docs with `universe_id=<uni>`
and either M2M-null (universe-wide) or M2M linking both characters.
`_build_factual_basis_section` emits multi-character-appearing chunks
under a top-of-prompt `SHARED WORKSPACE KNOWLEDGE` block. No schema
change is required to author canon today. The one open question is
retrieval competition — `top_k=5` per character is a hard budget.

**Q11. Does Episode currently provide enough narrative information
to synthesis to justify changing Episode architecture now?**
No. Episode's contribution to synthesis today is `operator_topic`
verbatim. Before adding fields to Episode we should decide what
Episode is *permitted* to teach synthesis — the smallest experiment
in §8 does not require Episode schema change.

**Q12. Which invented details from these dogfoods should become
canon, if any?**
The persistent-asset candidates from §6.11: the printer, the log
wall (implied by "the log"), the sandbox as a first-class fixture,
the "kill switch"/"stop rule" as a recurring safety trope, "one
beaver" as canonical Patch-self-reference. None are required. All
are cheap to canonise if we author the shared canon doc anyway.

**Q13. Is the 60 → 90 duration increase exposing a different content
problem, or simply making the existing K2 problem more visible?**
It makes the existing problem *less* severe, not more. Longer
duration = more compression headroom = fewer short-imperative
fragments. The 90 s scene is better paced than the 60 s scene
despite identical prompt architecture and identical K2 retrieval.
The 60 s scene is the harder test case for the compression amplifier
because it forces the most aggressive stripping.

**Q14. Is there evidence that Writing Contract v4 should change?**
Yes, on one specific dimension — Watchability #4 correctly forbids
"reproducing frameworks / headings / lists / slogans / methodology
language from the retrieved chunks", but the compression hint's
preference for short direct replies + fragments is a superseding
force. Either (a) the compression hint should carry a
"prefer-observation-over-imperative" clause, or (b) the contract
should give Watchability #4 explicit precedence over the compression
hint when the two conflict. The evidence does not yet distinguish
which of these is smaller.

The other evidence-driven contract candidate is the scene-entry rule
(§6.9): the contract does not currently require the opening turn to
establish *why these characters are talking now.* This is a genuinely
new invariant, not a tightening of an existing one.

**Q15. What is the SMALLEST next implementation/content slice
justified by runtime evidence?**
See §8.

### Answers to the additional questions (Q16–Q23)

**Q16.** Does Writing Contract v4 contain a scene-entry rule?
*No.* Watchability #1 requires an in-scene stance; nothing requires
the opening turn to establish *why now.* `_DIALOGUE_ANTI_PATTERNS`
forbids mid-scene greetings but is silent on scene-start behaviour.

**Q17.** Does current synthesis distinguish topic-opener / dialogue-
opener / scene-entry / hook / first-causal-turn?
*No.* One substrate — the optional operator-supplied `opener` string
— which functions as a verbatim first-turn pin, not a mechanism
selector. Neither dogfood used it.

**Q18.** Why did both dogfoods open with premise recitation?
Combination of: (a) operator topic arrives to §5 as
`TOPIC:\n{topic}` with no relational framing; (b) Patch's own
personality + POV explicitly instruct him to "open with the
experiment, question, result, or absurd situation" — talking-head
opening behaviour transferred to dialogue mode; (c) no contract rule
overrides those character defaults for dialogue-shape.

**Q19.** Is natural scene-entry character behaviour, story behaviour,
or contract behaviour?
Falsification exercise in §6.9 concludes: it is a **two-layer
requirement**. The contract must require an entry lever; the Universe
(relationship + canon) must supply the material the entry draws from.
Neither layer alone generalises across customer Universes.

**Q20.** Should a reusable scene-entry contract express something like
"the opening turn establishes why these characters are talking now"?
*Not ratified.* The wording captures the intent. The mechanism
enumeration (summons / interruption / discovery / confession /
accusation / callback / challenge / request-for-help / show-and-tell
/ reaction-to-something-already-happening / continuation) is a
starting palette. Any final wording must survive a "does this
generalise across plumber, teacher, veterinarian, bakery, ensemble?"
test — the current enumeration does.

**Q21.** Does shared canon / relationship / episodic history improve
openings?
Yes, decisively. A callback like "Rivet, remember the six-variable
experiment?" cannot be grounded today (zero shared canon, no
Episode-state field). With shared canon present, K6.4 verification
would gate the callback against actual shared facts rather than
letting the model invent workshop history it will contradict two
renders later. Without it, canonical callbacks are unreachable.

**Q22.** Does opening behaviour matter more as episodic memory
develops?
Yes. Today Episode has no state field beyond title + operator_topic
+ cast. Once past compositions on an Episode become retrievable as
"what previously happened," openings can begin with "the last time
we tried Y" without invention. This makes the scene-entry contract
strictly more valuable as episodic memory develops, but not strictly
required — the contract works with pure Universe canon as material.

**Q23.** Does opening behaviour depend on cast size?
Yes, materially. Two-character scenes have canonical binary entry
mechanisms (summons, greeting-adjacent, showing, confessing).
Ensemble entry (arrival mid-conversation, side-conversation,
interruption) is strictly more expressive and would require its own
contract vocabulary. **No evidence in this dogfood justifies
designing ensemble entry now.** The current 2-cast decision is
correct for the moment; the contract should be phrased in a way that
doesn't structurally exclude ensemble later.

---

## 8. Recommended smallest next experiment

**The report does not design the fix.** What follows is the smallest
justified next slice, expressed as an experiment with an acceptance
criterion — not as an implementation plan.

**Experiment shape:** author a single shared Patch+Rivet canon
KnowledgeDocument in the Patch's Workshop Universe (`universe_id =
56d16b63…`, M2M null OR M2M both Patch+Rivet). Content:
workshop-anchoring facts sufficient to support one grounded callback
and one canonical entry mechanism. Do NOT rewrite Patch K2 or Rivet
K2 in this slice.

**Acceptance criterion (single):** re-render the same Episode `"AI
took over the lab"` at 60 s. Confirm from persisted composition
observability that:

1. The shared canon chunk appears in the `SHARED WORKSPACE
   KNOWLEDGE` block of the assembled §1 (retrieval reached it, prompt
   emitted it, both characters saw it).
2. At least one character line in the accepted synthesis draws on the
   shared canon (chunk ID reflected in `Composition.knowledge_chunk_ids`
   AND textual evidence in the accepted turns).
3. No line in the accepted synthesis contradicts the canon.

**Why this is the smallest justified slice:**

* Falsifies §6.8: does the retrieval pipeline actually surface a
  shared doc, or does `top_k=5` competition starve it out?
* Isolates §6.2/§6.3 concerns: if shared canon lands and reduces
  methodology recital *without* touching Rivet K2, that constrains
  the next slice to canon-authoring; if shared canon lands but
  methodology recital persists, that confirms K2 content-shape needs
  a separate slice.
* Requires zero schema change, zero code change, zero contract change,
  zero provider change. Data-only experiment.
* Establishes the canon-authoring workflow before any customer
  Universe requirement forces it.

**What this experiment does NOT decide:**

* Whether the scene-entry contract rule should be added.
* Whether Watchability #4 needs precedence-tightening against the
  compression hint.
* Whether Rivet K2 should be rewritten.
* Whether Episode should carry a summary / prior-state field.
* Whether opener-mechanism selection belongs in the Task section.

Each of the deferred questions becomes a separately-justified next
experiment after this one lands.

---

## 9. Unresolved questions

* **U1.** Is `top_k=5` per character enough headroom for shared canon
  to appear alongside character-specific chunks, or does the shared
  block need its own budget? The experiment in §8 will produce
  runtime evidence.

* **U2.** Does Watchability #4's precedence against the compression
  hint need to be made explicit, or does the compression hint itself
  need a "prefer observation over imperative" clause? Two candidate
  interventions; runtime evidence does not yet distinguish.

* **U3.** Is `character_point_of_view` doing double duty as both
  "what Rivet notices" (character texture) and "how Rivet
  interrogates" (methodology framing)? If so, the field may need
  either a rewrite or an internal split before methodology
  migration into POV can be safely landed.

* **U4.** Does the scene-entry contract rule need to enumerate
  mechanisms (summons, callback, discovery…) or can it stay abstract
  ("establish why now") and let each character/Universe combination
  find its own form? Evidence today points to enumeration, but not
  strongly.

* **U5.** Do we need per-Episode state (what previously happened) or
  is per-Universe canon sufficient to unlock callback-style openings?
  §6.9 and §8 both defer this — worth revisiting after the shared-
  canon experiment.

* **U6.** How do we detect voice contamination (§6.6 — Patch reaching
  for Rivet's signature phrase) systematically? Not urgent today; a
  linter that flags "signature phrase from other character" would
  suffice.

---

## 10. Platform generalisation note

Patch and Rivet are customer zero. Every finding in this report is
expressed in a way that generalises across customer Universes —
"shared canon," "scene-entry mechanism," "methodology-shape K2 chunks
compress into imperative fragments" are all universe-agnostic.
Patch-specific and Rivet-specific facts appear only as *examples*.
The recommended next experiment (§8) is Patch/Rivet-specific
content authoring; the *architectural* dimensions it tests are
Universe-general.

No recommendation in this audit hard-codes a Patch or Rivet assumption
into the platform.

---

## 11. Source citations index

* `shell/character_os/dialogue_synthesis.py` — prompt assembly,
  synthesis dispatch, corrective retry.
* `shell/character_os/writing_contract.py` — Writing Contract v4 text.
* `shell/apps/embeddings/retrieval.py` — retrieval scope + Universe
  filter + M2M scope.
* `shell/apps/compositions/starters.py` line 3428 — `dialogue_scene`
  starter, AI-Topic branch.
* `shell/apps/compositions/models.py` line 534 — `Composition.episode`
  FK (RESTRICT, nullable).
* `shell/apps/universe/models.py` — Universe + Episode + EpisodeCast
  models.
* Database rows cited by UUID inline throughout §1, §2, §4.
