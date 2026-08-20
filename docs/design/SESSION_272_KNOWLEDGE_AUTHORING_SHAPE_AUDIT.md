# SESSION 272 — Knowledge Authoring / Knowledge Shape Audit

**Slice type:** documentation-only. AUDIT + DESIGN.
**Session opener:** deferred question from SESSION 271 §191.11.
**Scope:** how should Character OS factual knowledge represent technically precise concepts while also giving synthesis accessible semantic formulations, without (a) duplicating facts, (b) dumbing down expert knowledge, (c) baking audience-specific prose into KnowledgeDocuments, (d) coupling factual knowledge to one character, or (e) requiring future characters to rediscover Patch's API/state problem through dogfood?

**Not in scope:** any KnowledgeDocument rewrite; any embedding change; any chunking/retrieval change; any Writing Contract v6 change; any corrective-hint change; any persona change; any schema change; any render; any NarrativeMemory promotion. SESSION 271 audience-aware architecture for `solo_scene` remains **CLOSED** — this audit does not reopen it.

---

## §1. REPOSITORY / RUNTIME ORIENTATION

- Repo: `main == origin/main`, working tree clean at audit open.
- HEAD at open: `3884eeb` — `docs(session-271): record §192 CLOSEOUT commit SHA e1f9b59`.
- Writing Contract version: **6** (SESSION 271 §187).
- Local-real services (probed at audit open):
  - Django `:8010/admin/` → `http=302`
  - Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`
  - Vite `:5174/` → `http=200`
  - Celery worker running (per SESSION 271 §L)
- All experiment env vars OFF (verified at SESSION 271 close; no changes since).
- No knowledge doc / embedding / NarrativeMemory / render mutation performed in this audit.

---

## §2. STARTING EVIDENCE (from SESSION 271 §191)

1. **Writing Contract v6** ratified as working. The universal `AUDIENCE-AWARE COMMUNICATION` invariant produces accessible Draft A on the same substrate where corrective Draft B regresses.
2. **Patch persona** is not the bottleneck — `character_point_of_view` is directionally aligned.
3. **Residual API/state jargon** is primarily **C + D**:
   - **C — KnowledgeDocument lexical gravity** (dominant).
   - **D — corrective expansion** literally pulls terminology back from retrieved chunks.
4. **Load-bearing Patch chunk:** `505acbba-fbc4-41b2-8494-4c937a3e3e28` (in doc `fd0ba2ca-eb15-4785-a39b-22ddd1052052`, index 3, 827 chars). Content-equivalent mirror chunk in canonical Patch doc `19778800-bb72-48d0-b9b0-7c54c082355d` at index 3 is `793fe4ce-dec5-41cd-9d3d-86f9b61a7a06`. Same 3-item AI-agents enumeration.
5. **Canonical v6 Composition** `994e7b1b-e95a-4b9b-b17e-1b25611fcd8e`: Draft A translated concepts accessibly and omitted raw API/state. The corrective pass, instructed to "expand secondary detail from the knowledge chunks," pulled raw API/state back in.
6. **Patch/AI-Agents substrate is SATURATED** — five behaviorally-equivalent same-topic renders. Not usable for SESSION 272 experimentation.

---

## §3. PHASE 1 — INVENTORY: KnowledgeDocuments inspected

### §3.1 Corpus scope

`KnowledgeDocument.objects.all()` count at audit time: **68 documents** across 5 workspaces. Four documents inspected in depth to sample the axes that matter for the knowledge-shape question:

| Label | Doc UUID | Workspace | Chunks | Domain | Reason chosen |
| --- | --- | --- | --- | --- | --- |
| **PATCH** | `19778800-bb72-48d0-b9b0-7c54c082355d` | Patch's Workshop `097bd82e` | 22 | AI / software engineering | Contains the load-bearing chunk class from SESSION 271 §191.4. Baseline. |
| **RIVET** | `71e2ec43-6edc-47cf-beb5-25698a440d16` | Patch's Workshop `097bd82e` | 14 | Experimental reasoning / debugging methodology | Same workspace as Patch. Different topic. Same document-authoring shape. Second-substrate lexical-gravity control. |
| **PENNY** | `e284edc9-d473-4076-8e2d-156f022b6ca7` | Hearth & Hollow `4ce5486d` | 7 | Outdoor recreation (kayaking, rafting, guided tours) | Cross-workspace, unrelated domain, nontechnical. Real spokesperson-style document. Tests fox-first generalization on a real Character OS surface. |
| **REPO RED** | `ee7b7e5c-5857-4323-b369-e6efa69492d3` | Hearth & Hollow `4ce5486d` | 22 | Automotive financing / subprime credit content | Real domain-terminology-heavy business content with a radically different authoring shape (bulleted lists + canned scripts). Stress-tests the ownership boundary in Phase 4. |

Note: The two Patch mirrors (`d3217843` in workspace `fa26e601`, and `fd0ba2ca` in workspace `4ce5486d`) are copies of the same 22-section authorial content, with chunk IDs differing only because embedding was performed independently. `505acbba` lives in the `fd0ba2ca` mirror at index 3; the canonical `19778800` mirror's equivalent chunk is `793fe4ce`. Text is identical.

### §3.2 Two distinct authoring shapes observed

**Shape α — Section-headered prose, comma-joined enumerations, persona commentary interleaved.**
Used by: PATCH, RIVET, PENNY.
Structure per section: `<HEADER>. <one-sentence definition>. <comma-joined enumeration of items/verbs>. <character-flavored commentary/generalization>.` Chunk boundaries fall inside the prose flow with the tail of the previous section overlapping into the head of the next. Embedding produces semantically-coherent chunks that each carry one full section.

**Shape β — Divider-headered bulleted lists, canned example quotes, persona directives.**
Used by: REPO RED.
Structure per section: `================================================== <HEADER> ==================================================`, followed by (a) bullet lists (up to 24-item runs) of situations/facts, and (b) explicit `X can say: "..."` / `X should NEVER say: "..."` blocks with literal quoted script. Zero comma-joined enumerations; 106 bullet-lines total, longest single run 24 items.

Both shapes exhibit **lexical gravity** — Shape α through comma-joined enumerations, Shape β through repeated bullet items. The mechanism is the same at the token-model level: retrieved text offers exactly one canonical formulation of the concept, densely.

### §3.3 Quantitative enumeration density

| Doc | Comma-joined ≥4-item enumerations | Longest comma enum | Bullet lines | Longest bullet run | Persona-directive mentions |
| --- | --- | --- | --- | --- | --- |
| PATCH | **39** | 14 items | 0 | 0 | **30** (`Patch understands/does not/should/is/prefers/treats/…`) |
| RIVET | 18 | 10 items | 0 | 0 | 12 (`Rivet keeps/does not/prefers/strongly prefers/…`) |
| PENNY | 27 | 8 items | 0 | 0 | 15 (`Penny should/must/can/speaks/she should/…`) |
| REPO RED | 8 (comma) | 6 items | **106** | **24** | **29** (`Red can/should NEVER/does not/never/treats/…`) |

**Reading:** Patch's chunk 505acbba is not an outlier. Patch's doc contains ~39 comma-joined enumerations of length 4–14. Rivet has 18. Penny — a nontechnical domain — has 27. Every character-knowledge doc uses dense enumeration as its primary factual-encoding shape. Additionally, **every** doc has persona-directive leakage into factual sections (12–30 mentions per doc).

### §3.4 Semantic-shape classification per doc

**PATCH** — Shape α.
Sections: `PURPOSE / WHAT PATCH KNOWS ABOUT AI / LANGUAGE MODELS / AI AGENTS / MULTI-AGENT SYSTEMS / AI MEMORY / AI CHARACTERS / …`.
Factual encoding:
- **Dense terminology enumeration** — dominant. Chunks 1–5 each contain one or more 8–15-item lists (see §4 below).
- **Explanatory prose** — present but thin; typically one sentence framing the enumeration.
- **Example-driven prose** — absent. No concept has a worked example.
- **Procedural knowledge** — absent for the AI-concepts sections; present for content-craft sections later.
- **Conceptual/relational knowledge** — present in scene-header text ("agents may make decisions…") but the relationships collapse into flat lists.
- **Mixed forms** — no. Each concept has exactly one formulation.
- **Duplicated concept formulations** — no. Concepts appear once.
- **Character-behavior material inside knowledge** — YES (30 mentions). E.g., "Patch does not treat an AI response as automatically correct…" wedged inside the LANGUAGE MODELS section. This class violates ownership per Phase 4.
- **Story / content-strategy material mixed into factual knowledge** — present. Later chunks (16–20) mix "content principles" with "what Patch knows."

**RIVET** — Shape α, same as Patch, smaller.
Sections: `PURPOSE / HYPOTHESIS BEFORE CONCLUSION / OBSERVATION VS EXPLANATION / REPRODUCIBILITY / AI OUTPUTS REQUIRE VERIFICATION / FAILURES ARE DATA / DEBUGGING / CHANGE ONE THING / AI CHARACTER TESTING / VISUAL CHARACTER TESTING / ROBOT CHARACTER TESTING / PROMPT ITERATION / SMALL EXPERIMENTS / COST MATTERS / METRICS NEED CONTEXT`.
Factual encoding:
- **Dense enumeration** — the DEBUGGING section (chunk 6) enumerates debugging questions as 8-item comma list: `what changed, what was expected, what actually happened, whether the behavior can be reproduced, where the behavior first becomes incorrect, what evidence exists, what assumption might be wrong, and what smallest test would separate two possible explanations`.
- **Character-behavior material inside knowledge** — YES. `Rivet does not confuse confidence with accuracy` / `Rivet strongly prefers small tests` / `Rivet keeps that line clear` all appear inside factual sections.
- **Data-hygiene detritus** — YES. Chunk 13 ends with `[Session 266 experimental clone — WEAK — do not treat as canon]` — a meta-annotation that is currently retrievable. This is a separate bug, flagged.

**PENNY** — Shape α, nontechnical.
Sections: `Who Penny Represents / Who Penny Helps / What Riverstone Offers / What Penny Should Emphasize / Safety and Communication Guardrails / How Penny Should Think About Beginners / Desired Customer Outcome / Core Knowledge Summary`.
Factual encoding:
- **Explanatory prose** — dominant. Few dense enumerations; most content is guidance prose.
- **Small enumerations** — audience list (5 items), safety-guardrail list (6 items), core-values list (6 items).
- **Persona directives dominate** — the doc is essentially a persona/behavioral instruction manual with a thin veneer of facts (services, geography). "Penny should never make a beginner feel foolish," "Penny must never encourage someone to ignore a guide," "she should explain things in simple language." This is Persona / Writing Contract territory, not KnowledgeDocument.
- **Audience-specific prose baked in** — YES. "explain things in simple language" is exactly the class SESSION 271 §D flagged.

**REPO RED** — Shape β.
Sections: `PURPOSE / WHO RED TALKS TO / RED'S MOST IMPORTANT FINANCING LESSON / MONEY DOWN / BAD CREDIT / REPOSSESSIONS / BANKRUPTCY / SELF-EMPLOYMENT / SSI / ITIN / DRIVER'S LICENSE / FICTIONAL BACKSTORY / …`.
Factual encoding:
- **Bulleted enumerations** — dominant. 106 bullet lines; longest run 24 items (the credit-situation audience list).
- **Domain terminology** — very high density: `credit score / repossession / bankruptcy / SSI / ITIN / disability income / cash income / down payment / underwriting`. Every term is a potential lexical attractor.
- **Canned spoken paragraphs** — YES, extensively. `Red can say: "Got $2,000 down? Now tell me the rest."` — literal script embedded in knowledge. `Red should NEVER say: "$2,000 guarantees approval."` — anti-script prescription.
- **Fictional character backstory inside knowledge** — YES. "Repo? Hell, that's how I got the name."
- **Content-strategy directives inside knowledge** — YES. `Do NOT open most videos with: "Hello." "Welcome"`.
- **Character-behavior material** — 29 mentions. Full persona-directive contamination.
- **Duplicated concept formulations** — YES for a few items (e.g., "down payment" appears in the situation list AND in the MONEY DOWN section AND in canned scripts).

### §3.5 Lexical-attractor identification

For each doc, chunks likely to become gravity wells during synthesis (defined: single dense list of ≥6 domain-canonical tokens as the only representation of the concept):

| Doc | Chunk | Enumeration | Attractor risk |
| --- | --- | --- | --- |
| PATCH `19778800` | idx 1 (`9349b550`) | "text, images, audio, speech, video, documents, structured data, software code, tools, APIs, databases, search systems, physical devices" (13-item) | HIGH — no parallel form |
| PATCH `19778800` | idx 2 (`4461a537`) | "conversation, writing, summarization, classification, reasoning, planning, information extraction, software development, tool selection, structured outputs" (10-item) | HIGH |
| PATCH `19778800` | idx 3 (`793fe4ce`) — mirror of `505acbba` | **"call APIs, perform multi-step tasks, maintain state, interact with other agents, respond to changes in an environment"** | **CRITICAL — the SESSION 271 §191.4 case** |
| PATCH `19778800` | idx 5 (`24091354`) | AI-memory enumeration (8-item) | HIGH |
| RIVET | idx 6 (`3b1da9ef`) DEBUGGING | 8-item Q-enumeration | HIGH — untested |
| RIVET | idx 8 (`8f1686ac`) VISUAL TESTING | 9-item failure-mode list | MODERATE |
| PENNY | idx 4 SAFETY | 6-item guardrail list | LOW-MODERATE |
| REPO RED | idx 1 WHO RED TALKS TO | 24-item bulleted audience list | HIGH |
| REPO RED | idx 3 MONEY DOWN | 5 canned quotes | Different failure mode: gravity is not toward *terminology* but toward *character voice quotes* — extremely bad for cross-audience |

### §3.6 Per-doc concept-representation choice

| Doc | Provides only technical term | Provides only plain-language concept | Provides both together | Provides inferable example | Provides multiple valid expressions of same fact |
| --- | --- | --- | --- | --- | --- |
| PATCH | ✓ (dominant — dense enumerations) | rare | rare | rare | **NO** |
| RIVET | ✓ (methodology terminology as enumerations) | rare | rare | one worked case per section (limited) | **NO** |
| PENNY | rare | ✓ (dominant — plain-language guidance prose) | occasional | few | limited |
| REPO RED | ✓ (bulleted domain terms) + canned voice quotes | rare | in a few sections | canned example quotes ARE examples but they're voice-locked to Red | **NO** — voice-locked |

**Key finding of Phase 1:** *No doc currently offers synthesis multiple valid lexical choices for the same fact.* Every concept has exactly one formulation available in the retrieved text. This is the same finding as SESSION 271 §191.4/§191.9 but is now confirmed as a **cross-character structural property of Character OS knowledge authoring**, not a Patch-specific pathology.

---

## §4. PHASE 2 — PATCH LOAD-BEARING CHUNK 505acbba

### §4.1 Chunk metadata

- ID: `505acbba-fbc4-41b2-8494-4c937a3e3e28`
- Document: `fd0ba2ca-eb15-4785-a39b-22ddd1052052` (Hearth & Hollow workspace `4ce5486d` mirror of PATCH doc)
- Index: 3
- Length: 827 chars
- Content-equivalent mirror in canonical `19778800` PATCH doc at index 3: `793fe4ce-dec5-41cd-9d3d-86f9b61a7a06` (identical prose)
- Chunk-overlap style: begins with tail of preceding section (LANGUAGE MODELS), transitions into AI AGENTS section, ends at start of MULTI-AGENT SYSTEMS header

### §4.2 Full chunk text (verbatim, whitespace preserved)

> systems. Patch does not treat an AI response as automatically correct simply because it sounds confident — an impressive-sounding answer still has to be checked before it counts as right.
>
> AI AGENTS An AI agent is generally an AI system that can do more than produce one response. Agents may make decisions, select tools, search for information, read documents, write information, call APIs, perform multi-step tasks, maintain state, interact with other agents, and respond to changes in an environment. The interesting question for Patch is not whether something is technically an agent — it is what happens when the AI can actually do something rather than only talk about doing something. Behavior gets more interesting when AI systems can interact with tools, environments, information, or one another.
>
> MULTI-AGENT SYSTEMS

### §4.3 Mechanical decomposition: factual content vs lexical representation

**Factual claims (concept-level, character-independent):**

1. An AI agent is an AI system whose output surface extends beyond a single response.
2. Agents can decide.
3. Agents can select from an available tool set.
4. Agents can perform information retrieval.
5. Agents can read from data sources (documents).
6. Agents can write to data sources.
7. Agents can invoke external software services (over network interfaces / APIs).
8. Agents can chain steps together where later steps depend on earlier ones (multi-step tasks).
9. Agents can carry information across steps within a task (state).
10. Agents can communicate with peer agents.
11. Agents can react to changes in an environment they operate in.
12. Interaction with tools / environments / information / other agents is what makes agent behavior interesting.

**Lexical representation currently used to encode facts 2–11:**
A single 10-item comma-joined enumeration verb list:
`make decisions, select tools, search for information, read documents, write information, call APIs, perform multi-step tasks, maintain state, interact with other agents, respond to changes in an environment.`

**What this shape does:**
- Encodes 10 facts in ~150 tokens — very compact.
- Uses domain-canonical terms for 3 of the 10 verbs (`call APIs`, `maintain state`, `multi-step tasks`).
- Provides NO parallel accessible formulation for those 3 canonical terms.
- Gives the synthesis model exactly ONE surface to draw from when the chunk is retrieved.

**Character-behavior leakage in the same chunk (does NOT belong here per Phase 4):**
- "Patch does not treat an AI response as automatically correct simply because it sounds confident" — belongs to persona / `character_point_of_view`.
- "The interesting question for Patch is not whether something is technically an agent — it is what happens when the AI can actually do something" — persona framing.
- "Behavior gets more interesting when…" — voice/tone commentary, not a fact.

### §4.4 Could the SAME facts be represented so synthesis has multiple valid lexical choices without weakening precision?

Yes. Concretely, a representation that preserves precision AND gives synthesis multiple valid lexical surfaces must:

1. **Preserve every canonical term.** An expert-facing renderer must still be able to say `call APIs`, `maintain state`, `multi-step task`. Removing terminology weakens precision and dumbs down.
2. **Present at least one parallel accessible formulation of each terminology-loaded verb, in the same local retrieval scope.** So when the retrieval returns the chunk, both the canonical form and the accessible paraphrase are physically present.
3. **Keep the accessible paraphrase neutral (not voice-locked to any character).** A paraphrase like "Patch would say 'ask other software for information'" locks the doc to Patch. A paraphrase like "in plain terms: reach out to another piece of software to fetch or trigger something" is character-agnostic.
4. **Not duplicate the fact itself.** The fact "agents can invoke external services over APIs" is stated once. Two lexical *renderings* of that fact do not constitute two facts — a canonical-and-paraphrase pair is one fact expressed with two vocabularies.
5. **Not prescribe when to use which.** The knowledge doc offers both surfaces; the Writing Contract v6 universal invariant (character-agnostic) already governs when to use which. Knowledge-shape should provide material, not policy.

**Illustrative shape** (NOT a proposed rewrite; illustrative only):

> AI AGENTS An AI agent is an AI system that can do more than produce one response. Agents may make decisions, select tools, search for information, read documents, write information, call APIs, perform multi-step tasks, maintain state, interact with other agents, and respond to changes in an environment. In plain terms: an agent can decide what to do next, pick the right tool for the job, look things up, read notes, write things down, ask other software for information over a network interface, work through a job that has several steps, keep track of what it has learned along the way, coordinate with other agents, and adjust when the situation changes.

Properties this shape has:
- **Every canonical term preserved** (`call APIs`, `maintain state`, `multi-step tasks`).
- **Parallel accessible formulation** for the same 10 verbs.
- **Character-agnostic** — the paraphrase does not name Patch.
- **Single-source facts** — 10 facts, expressed with two vocabularies.
- **Chunk-local** — synthesis retrieving this chunk has both surfaces immediately.

**Explicit non-endorsement:** This is *not* a proposed authoring convention — it is a probe to define what properties a good representation needs. Whether "paired paraphrase" is the correct convention, or whether a structured term/meaning/example schema is better, is decided in Phase 5 + Phase 6.

---

## §5. PHASE 3 — SECOND-SUBSTRATE VALIDATION

### §5.1 Test question

Does "knowledge lexical gravity" generalize beyond Patch's AI-Agents chunk, or is 505acbba unusually pathological?

Approach: source/document analysis only. No render. Compare the *authoring shape* of second-substrate chunks against the mechanism identified in Phase 2 (`§4.3`).

### §5.2 Second substrate #1 — RIVET DEBUGGING chunk (`3b1da9ef`, doc `71e2ec43`, idx 6)

Verbatim excerpt:

> DEBUGGING When something breaks, Rivet prefers reducing the problem before trying to fix it. Changing one meaningful variable and testing again is more informative than changing ten things at once. Useful debugging questions include what changed, what was expected, what actually happened, whether the behavior can be reproduced, where the behavior first becomes incorrect, what evidence exists, what assumption might be wrong, and what smallest test would separate two possible explanations. Evidence beats guessing.

Encoding:
- 8-item Q-enumeration, comma-joined.
- Single canonical formulation.
- No parallel accessible form.
- Persona directive wedged in (`Rivet prefers reducing the problem`).

**Prediction (source-analysis only, not run):** If a solo_scene render asked Rivet to explain his debugging approach — first pass under v6 universal invariant, followed by duration-based corrective expansion — the enumeration would be the dominant "secondary detail" for expansion. Draft A may translate to something like `what changed, what should have happened, what actually happened`; corrective Draft B under `"Expand secondary detail from the knowledge chunks"` would likely reach for `whether the behavior can be reproduced, where the behavior first becomes incorrect, what evidence exists` verbatim. Same mechanism as PATCH 505acbba.

**Mechanism identity check:** The mechanism is *dense enumeration as the only lexical surface for a domain concept*. RIVET debug chunk has that shape. Prediction is consistent with the C+D causal ranking.

### §5.3 Second substrate #2 — PENNY SAFETY guardrail (`8598993b`, doc `e284edc9`, idx 4)

Verbatim excerpt:

> Penny must never encourage someone to ignore a guide, safety instruction, weather warning, closure, life-jacket requirement, local regulation, or other applicable safety requirement.

Encoding:
- 6-item comma-joined enumeration.
- Wrapped in a persona directive (`Penny must never encourage…`) — the enumeration is nested inside a Persona rule.

**Prediction:** If Penny is rendered on a safety topic, this enumeration would attract exact reproduction (`guide, safety instruction, weather warning, closure, life-jacket requirement, local regulation`). Same mechanism.

**Additional finding:** Penny's doc has significantly LESS enumeration density than Patch/Rivet (only 27 comma-enumerations, mostly short 4–5 items), but it has correspondingly MORE persona-directive content. Different pathology: PENNY doesn't over-encode facts in enumerations; it over-encodes *behavior* in the knowledge document. Lexical gravity applies in a diluted form; persona-boundary violation applies in a concentrated form.

### §5.4 Second substrate #3 — REPO RED WHO RED TALKS TO (`f6a3a079`, doc `ee7b7e5c`, idx 1)

Verbatim excerpt (partial):

> Red speaks especially to customers dealing with situations such as: - Bad credit
> - Very low credit scores
> - Credit scores in the 400s or 500s
> - Limited credit history
> - No established credit
> - Previous repossessions
> - Recent repossessions
> - Multiple previous automotive financing problems
> - Bankruptcy
> - Previous loan defaults
> - Self-employment
> - Cash income
> - SSI income
> - Social Security income
> - Disability income
> - Alternative or nontraditional income
> - ITIN customers
> - No Social Security number
> - Recently started employment
> - Limited time on the job
> - Complicated employment history
> - Customers without a traditional driver's license
> - Customers who have already been declined elsewhere
> - Customers afraid to apply because they expect another rejection
> - Customers with money available for a down payment but poor credit

Encoding:
- 25-item bulleted enumeration.
- No parallel accessible formulation for any of the domain terms (`SSI`, `ITIN`, `Chapter 7 vs Chapter 13`, `repossession`).
- Directly downstream: canned character quotes (`Red can say: "Got $2,000 down?"`).

**Prediction:** If Red is rendered on "who he helps," the bulleted list would attract wholesale reproduction. Additionally, because REPO RED encodes **example scripts as literal quotes**, corrective expansion would tend to pull Red's canned voice quotes verbatim into the render — a distinct pathology on top of enumeration gravity.

**Second-order finding:** Shape β (bulleted lists + canned quotes) creates BOTH lexical gravity AND persona/voice lock-in. The lexical-gravity mechanism generalizes. The voice lock-in is an *additional* pathology unique to Shape β.

### §5.5 Verdict on Phase 3

**Knowledge lexical gravity generalizes across characters and domains.**

- PATCH (AI/software, dense terminology): CRITICAL gravity around canonical CS terms.
- RIVET (methodology, procedural): HIGH gravity around question/methodology enumerations.
- PENNY (nontechnical, prose-heavy): MODERATE gravity around small safety/audience enumerations.
- REPO RED (business/financing, bulleted): HIGH gravity around bulleted terminology + additional voice/quote gravity.

**Patch's 505acbba is not pathological — it is representative.** The mechanism is: dense enumeration as the only lexical surface for a concept, in a retrieval scope with no parallel formulation. Every character-knowledge doc in the audit exhibits this shape at least somewhere.

**Second-order finding worth naming for future work:** REPO RED-style canned-quote embedding creates a *voice-lock* pathology distinct from lexical gravity. If SESSION 272's convention only addresses enumeration lexical gravity, REPO RED-style docs remain broken on the voice dimension. Any candidate convention must be evaluated against Shape β as well as Shape α (see Phase 6).

---

## §6. PHASE 4 — DISTINGUISH KNOWLEDGE FROM COMMUNICATION

### §6.1 Ownership rule

Working from the SESSION 271 architectural separation (§C.2 of the handoff):

| Layer | Owns |
| --- | --- |
| **KnowledgeDocument** | WHAT the character knows (facts, terminology, relationships, examples that clarify meaning). Character-agnostic in the sense that the same fact expressed identically could be used by any character equipped with this knowledge. |
| **Persona** (`character_point_of_view`, `personality`, voice knobs) | HOW the character naturally communicates (register, humor, signature phrasing, worldview). Character-specific. |
| **Writing Contract v6** | Universal scene rules + audience-aware communication invariant. Character-agnostic. |
| **audience_hint** (`Composition.audience_hint`) | Who THIS render is speaking to. Composition-specific. |
| **NarrativeMemory** | What happened in the story arc (episodes, events, decisions). Timeline-specific. |

### §6.2 What KnowledgeDocuments MAY contain

- Canonical terminology (`API`, `state`, `SSI`, `hydration percentage`, `proofing`, `grind size`, …).
- Precise factual definitions (`An API is an interface through which one piece of software asks another to perform an action or return information.`).
- Relationships / hierarchies between concepts (`multi-step task ⊂ agent capability`; `SSI ⊂ nontraditional income`).
- Neutral illustrative examples that clarify what a concept MEANS (a fact about the domain, not a script for a character). Example: `A weather app asking a weather service for today's forecast is a use of an API.`
- Known synonyms / paraphrases where semantically load-bearing (`state ≈ working memory ≈ information carried across steps`).
- Domain constraints and safety-relevant facts (`Life jackets are required by Colorado state law on all commercial paddling operations.`) — as facts, not as behavior directives.

### §6.3 What KnowledgeDocuments MUST NOT contain

- Character voice / behavior directives (`Patch should never…`, `Rivet prefers…`, `Penny must never encourage…`, `Red can say "..."`).
- Audience-specific speech prescriptions (`explain this to beginners as X`, `use simple language`, `use technical vocabulary`).
- Canned spoken paragraphs intended to be reproduced verbatim.
- Content-strategy directives (`Do NOT open videos with "Hello."`).
- Guardrails as directives (guardrails belong to Persona / Writing Contract; if the underlying claim is factual — e.g. "life jackets are legally required" — the FACT belongs; the directive "Penny must never encourage ignoring safety" belongs to Persona).
- Experiment markers / meta-hygiene notes / editorial annotations (`[Session 266 experimental clone — WEAK]`).
- Anti-scripts (`Red should NEVER say "..."`) — these are Persona anti-patterns, not facts.

### §6.4 Empirical boundary-violation counts in the corpus

From §3.3 quantitative counts, current ownership violations:

| Doc | Persona-directive mentions in "knowledge" | Canned voice quotes | Content-strategy directives | Data-hygiene detritus |
| --- | --- | --- | --- | --- |
| PATCH | 30 | 0 | ≥3 (later chunks) | 0 |
| RIVET | 12 | 0 | 0 | 1 (`[Session 266 experimental clone — WEAK]`) |
| PENNY | 15 | 0 | multiple | 0 |
| REPO RED | 29 | ≥25 quoted lines | ≥3 explicit `Do NOT open with` | 0 |

**Every character in the audit has ownership violations.** REPO RED is the most severe. RIVET is the mildest but still leaks 12 directives and one experiment marker.

### §6.5 Ownership rule (formal statement)

> **A KnowledgeDocument records only claims-about-the-world.** A claim-about-the-world is a statement that would remain true regardless of which character was speaking, what audience was listening, or how the render was framed. Anything that would change based on character, audience, or render belongs to a different layer.

### §6.6 Distinguishing the Q-270-7 boundary case

Some claims that look like guardrails are actually facts. Example:
- ✓ **Fact (KnowledgeDocument):** "Life jackets are required on Colorado commercial paddling operations."
- ✗ **Persona directive (Persona, not KnowledgeDocument):** "Penny must never encourage a customer to ignore a life-jacket requirement."

The distinction is: a fact describes the world; a directive prescribes character behavior. If a rule references the character by name, it is a directive. If a rule references the world, it is a fact.

---

## §7. PHASE 5 — CANDIDATE AUTHORING CONVENTIONS

Three candidate conventions plus one hybrid that emerged from Phase 2 analysis. Each evaluated against a fixed set of criteria in §7.5.

### §7.1 OPTION A — TECHNICAL + ACCESSIBLE PAIRING

Each important technical concept is represented with precise terminology plus a neutral semantic explanation in the same local retrieval scope. Paired inline: `<canonical term> (<accessible clarification>)`.

Example probe:

> Agents may make decisions, select tools, search for information, read documents, write information, call APIs (reach out to another piece of software over a network interface), perform multi-step tasks (work through a job whose later steps depend on earlier ones), maintain state (keep track of what has been learned along the way), interact with other agents, and respond to changes in an environment.

### §7.2 OPTION B — CONCEPT-FIRST PROSE

Facts authored primarily as conceptual explanatory prose. Canonical technical terms included only where they materially add precision — introduced as annotations rather than as the primary formulation.

Example probe:

> Agents can reach out to other software over network interfaces to fetch information or trigger actions — this is what people mean by "calling APIs." They can carry a job through several dependent steps rather than answering once and stopping. They can keep track of information and progress along the way — the technical name for this memory of a job's progress is "state."

### §7.3 OPTION C — STRUCTURED TERM/CONCEPT REPRESENTATION

Explicit micro-schema per concept: `term / meaning / example / synonyms`. No audience-specific speech. Concept entries authored (or ingested and normalized) into a canonical form; free-form prose reserved for cross-concept relationships and domain framing.

Example probe:

```
- Term: API
  Meaning: an interface through which one piece of software asks another piece of software for information or to perform an action.
  Example: a weather app asks a weather service for today's forecast.
  Synonyms: interface, endpoint, service call.

- Term: state (agent)
  Meaning: information the system keeps track of between steps of a task.
  Example: an agent trying to book a flight remembers which cities it has already searched.
  Synonyms: working memory, running context, memory-of-progress.

- Term: multi-step task
  Meaning: a job made of several steps where later steps depend on earlier ones.
  Example: research a topic → summarize → draft → check for errors.
  Synonyms: chained task, sequential job, workflow.
```

### §7.4 OPTION D — PAIRED CANONICAL + PARAPHRASE (emergent hybrid)

Every factual section pairs a canonical formulation with a single accessible paraphrase in the SAME chunk, character-agnostic. Free-form prose still permitted around the pair for framing/relationships. Zero persona/audience content in the knowledge chunk.

Example probe (rewrite of 505acbba's factual half only, non-endorsed):

> An AI agent is an AI system that can do more than produce one response. Agents may make decisions, select tools, search for information, read documents, write information, call APIs, perform multi-step tasks, maintain state, interact with other agents, and respond to changes in an environment. In plain terms: an agent can decide what to do next, pick the right tool for the job, look things up, read notes, write things down, ask other software for information over a network interface, work through a job that has several steps, keep track of what it has learned along the way, coordinate with other agents, and adjust when the situation changes.

Key structural difference from Option A: paraphrase is one collective sentence rather than per-term inline glosses. Preserves reading flow; makes chunk-level retrieval carry both surfaces; single migration pattern authors know how to apply consistently.

### §7.5 Tradeoff matrix

Rating scale: **+** favorable · **~** mixed · **–** unfavorable · **?** unclear/needs evidence.

| Criterion | A pairing | B concept-first | C structured | D paired paraphrase |
| --- | --- | --- | --- | --- |
| Factual precision | + | ~ (canonical relegated to annotation) | + | + |
| Expert-audience usefulness | + | ~ | + | + |
| Beginner-audience flexibility | + | + | + | + |
| Lexical-gravity risk reduction | ~ (inline glosses can themselves become attractors) | + (raw enum minimized) | + (multiple surfaces available) | + |
| Retrieval efficiency (does the concept still rank on canonical query?) | + | ~ (canonical de-emphasized) | + (term-keyed) | + |
| Chunk-length / chunking interaction | ~ (per-term parentheticals lengthen but preserve flow) | – (longer per concept) | – (schema changes chunk shape entirely) | – (~doubles factual section length) |
| Fact duplication risk | + (no duplication; annotation only) | + | + | + (facts single-sourced; two vocabularies for same fact) |
| Authoring burden | ~ (per-term paraphrase) | ~ (rewriting each factual claim) | – (schema migration) | ~ (one paraphrase per section) |
| Maintenance burden | ~ | ~ | – (schema evolution) | + (add/edit paraphrase alongside canonical) |
| Token cost per chunk | ~ | – | – | – |
| Ease of automated ingestion normalization | ~ | – (LLM rewrite required, paraphrase-drift risk) | + (structured schema is machine-normalizable) | ~ (paraphrase can be LLM-generated with human review; still rewrite-risk) |
| Suitability for generated / imported knowledge | ~ | – | + | ~ |
| Compatibility with existing KnowledgeDocuments | ~ (retrofit inline) | – (full rewrite) | – (schema break) | + (additive — append paraphrase to existing sections) |
| Migration implications | small per-term additions | doc-wide rewrite | doc-wide restructure + retrieval-model changes | additive paraphrase per section |
| Requires synthesis changes? | no | no | possibly (structured retrieval) | no |
| Requires schema changes? | no | no | YES (new schema for term/meaning entries) | no |
| Persona/audience-content contamination fix | no (orthogonal) | no (orthogonal) | + (schema forbids by construction) | ~ (convention-level; requires linter) |
| Handles Shape β (bulleted / canned quotes)? | – | ~ | + | ~ (paired paraphrase can pair with bullet lists, but doesn't fix canned-quote pathology) |
| Deployable as authoring-guidance vs code | authoring-only | authoring-only | authoring + schema + tooling | authoring-only + optional linter |

### §7.6 Preliminary shortlist

Options **D** and **A** are the strongest candidates against the current architecture without schema or migration cost. Option **C** is the strongest against long-term ingestion/normalization but requires schema and touching retrieval — a much larger surface. Option **B** underweights canonical precision and risks regressing expert renders.

Fox-first differentiates further in Phase 6.

---

## §8. PHASE 6 — FOX-FIRST / ARBITRARY-CHARACTER TEST

Testing each candidate against real and hypothetical characters:

1. **PATCH** — AI/software knowledge (real; SESSION 271 substrate).
2. **RIVET** — experimental reasoning (real).
3. **PENNY** — outdoor recreation (real; nontechnical).
4. **REPO RED** — automotive financing (real; Shape β).
5. **Fenn** — hypothetical fox baker (fox-first standard: hydration percentage, proofing, gluten development, fermentation).
6. **Bear coffee-shop owner** — hypothetical (extraction, grind size, brew ratio).
7. **Expert technical character** (e.g., Terra from SESSION 271 handoff) — must retain precision.
8. **Child-facing character** — must not force terminology.

Question form used at each cell: *"Would this convention allow the character's KnowledgeDocument to (a) preserve precision for expert audiences AND (b) provide accessible material for beginner audiences AND (c) contain no character/audience-specific prose AND (d) support the concept without forcing the character to use exact terminology in every render?"*

| Character | A: pairing | B: concept-first | C: structured | D: paired paraphrase |
| --- | --- | --- | --- | --- |
| PATCH (AI) | ✓ (pair each canonical term with plain-language gloss inline) | ~ (canonical de-emphasized may reduce precision for expert render) | ✓ | ✓ |
| RIVET (methodology) | ✓ (pair each Q-enum item with plain-language rephrase) | ~ (methodology terminology is meaningful; concept-first may under-serve) | ✓ | ✓ |
| PENNY (outdoor) | ~ (Penny's doc has few enumerations; pairing has little to pair) | ✓ (matches Penny's current prose shape well) | ~ (small factual footprint; schema overhead high) | ✓ (few paraphrases; small burden) |
| REPO RED (automotive) | ~ (fixes enumeration gravity BUT does not fix canned-quote voice lock) | – (canned quotes remain in Shape β) | ✓ (schema forbids voice-quotes by construction — solves both pathologies) | ~ (paired paraphrase for enumerations; canned-quote pathology remains) |
| Fenn (fox baker) | ✓ (`hydration percentage (the ratio of water to flour, roughly by weight)`; `proofing (letting the dough rest and rise before baking)`; `gluten development (the network of protein strands that give bread structure)`) — expert term preserved, beginner has parallel, Fenn can talk to an eight-year-old without dumbing down or losing precision | ~ (concept-first would introduce the terms as annotations — works but loses expert-first framing) | ✓ | ✓ |
| Bear coffee | ✓ (`extraction (the process of dissolving flavor from ground coffee into water)`; `grind size (how coarse or fine the coffee is ground)`; `brew ratio (weight of coffee to weight of water)`) — same as Fenn | ~ | ✓ | ✓ |
| Expert technical (Terra) | ✓ (expert can render at canonical form; paraphrase available but not forced) | – (concept-first shape can under-express canonical vocabulary — bad for expert-only renders) | ✓ | ✓ |
| Child-facing character | ✓ (paraphrase available for accessible framing; canonical still present for factual accuracy if needed) | ✓ | ✓ | ✓ |

**Verdict on fox-first:**

- **Option B (concept-first prose)** — REJECTED. Fails the *expert technical character* test and *partially fails* PATCH/RIVET/expert baker. Canonical terminology relegated to annotation weakens expert-facing renders.
- **Option A (per-term pairing)** — PASSES broadly but has a Shape-β blind spot: doesn't fix REPO RED-style canned-quote pathology.
- **Option D (paired paraphrase per section)** — PASSES broadly with the same Shape-β blind spot as A. Lower per-term authoring burden than A. Additive migration path.
- **Option C (structured schema)** — PASSES universally. Only convention that mechanically forbids canned-quote and audience-directive contamination by construction. Highest cost.

**Refined shortlist:** D + C. D is the shortest path to landing SOMETHING now; C is the strongest architectural endpoint. A viable trajectory is *ship D as an authoring convention now; leave C on the roadmap for a future ingestion-normalization slice.*

---

## §9. PHASE 7 — INGESTION-LAYER OWNERSHIP

### §9.1 Origins of KnowledgeDocument content

Character OS's knowledge corpus will originate from at least:

1. Manually authored character knowledge (current: PATCH, RIVET, PENNY, REPO RED).
2. Uploaded PDFs / docs (per K-arc scope lock).
3. Websites / URL ingestion (per YouTube-silent-failure memory).
4. Structured business data (per business_brief / DBAO integrations).
5. Generated onboarding knowledge (per future MentorForge-style flows).
6. Future automated loaders (per K-arc roadmap).

### §9.2 Where can the convention live?

For each candidate ownership layer, cost and safety analysis:

| Layer | Cost | Safety | Reversibility | Best-fit for |
| --- | --- | --- | --- | --- |
| **A. Source-authoring guidance** | low (authoring doc, examples, review checklist) | high (no code, no rewrite of imported content, no drift) | full (change the guide anytime) | manually-authored knowledge |
| **B. Ingestion normalization / transformation** | high (need an ingestion pipeline that rewrites content; LLM-mediated → hallucination/drift risk) | LOW (rewriting factual content is the exact class of change that produced the K7 YouTube-silent-failure and hackathon-knowledge-leak incidents) | difficult (once ingested, the source is often unavailable for re-normalization) | ~aspirational; NOT for the first slice |
| **C. Retrieval-time transformation** | high (retrieval pipeline modification; per-query cost) | LOW (paraphrases generated at query time are stateless and drift with model choice) | full (turn off the transformer) | possibly for Shape β voice-lock only, if at all |
| **D. Synthesis-time interpretation** | low (already done by Writing Contract v6) | HIGH (v6 already does this, and SESSION 271 §191.9 rank 1 said this cannot fix the pathology when the source only offers one lexical form) | full | not sufficient alone; needs source-side material |
| **E. Bounded combination A + optional lightweight linter** | low | high | full | recommended |

### §9.3 Smallest responsible ownership layer

**A — source-authoring guidance.** Landing the paired-paraphrase convention (Option D) as an authoring-guidance document plus an OPTIONAL LIGHTWEIGHT LINTER that flags:

- Comma-joined enumerations ≥6 items with no accompanying paraphrase clause in the same section.
- Persona-directive patterns (`<name> should`, `<name> can say "..."`, `Do NOT open`, etc.) inside knowledge documents.
- Data-hygiene detritus patterns (`[Session ... experimental clone]`).

The linter is advisory (author-facing warning), not mutating. This preserves the SESSION 262 additive-nullable discipline and the SESSION 271 fox-first character-agnostic discipline.

**Explicit non-recommendations for the first slice:**

- Do NOT implement ingestion normalization that rewrites imported content.
- Do NOT implement retrieval-time paraphrase generation.
- Do NOT implement synthesis-time knowledge transformation.
- Do NOT change chunking, embedding, or retrieval.

The reason: any of B/C/D/E introduces a new load-bearing model call between the raw source and the render, which is the exact pattern that produced the K7 silent-failure incident and would be a fresh drift surface. Source-authoring guidance keeps the fix at the layer where an operator can literally read the change.

---

## §10. PHASE 8 — CORRECTIVE-PASS INTERACTION

### §10.1 Test setup

The existing SESSION 271 §191.5 corrective hint contains the load-bearing phrase:

> "Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied."

The SESSION 271 §191.9 rank-2 finding is that under this instruction, the corrective pass reaches for the densest available surface in the retrieved chunk. If that densest surface is a raw terminology enumeration, the terminology reappears verbatim in Draft B.

For each candidate authoring convention, does the convention give the corrective pass *more valid "secondary detail"* to expand from, or does it merely add material that the corrective pass will ignore in favor of the raw enumeration?

### §10.2 Per-option interaction

**Option A (per-term pairing).** The paraphrase for each term is physically adjacent to the term in the chunk. Under `"Expand secondary detail from the knowledge chunks"`, the corrective pass has two valid surfaces at the same lexical position. Prediction: mixed. The corrective pass might grab the canonical + gloss pair together (both appear in the render), or one or the other. Net effect: paraphrase presence at minimum HALVES the probability of a raw enumeration reappearing without an accompanying accessible form.

**Option B (concept-first).** Raw enumeration is minimized in favor of prose. The corrective pass reaches for the densest surface — which is now prose. Raw terminology reappearance drops sharply. Downside per §7.5: expert-audience precision may suffer if the canonical vocabulary is de-emphasized enough that the model deprioritizes it even when it should be used.

**Option C (structured).** The retrieved chunk offers term + meaning + example + synonyms as parallel structured fields. Under expansion pressure, the corrective pass has a menu of accessible surfaces. Highest robustness. Cost is Phase 7 owns.

**Option D (paired paraphrase per section).** The paraphrase is a full parallel sentence at the section level. Under `"Expand secondary detail from the knowledge chunks"`, the paraphrase is precisely *of the same length* as the canonical enumeration — it IS the secondary detail. Prediction: corrective pass has a strong alternative attractor for expansion. High robustness.

### §10.3 Key question

*Would the knowledge shape reduce risk WITHOUT requiring the corrective system to know anything about audience-specific translations?*

**Yes** for A / C / D. The paraphrase or structured entry lives in the retrieved chunk. The corrective pass is not told anything about audiences. The corrective pass simply has more valid "secondary detail" to expand from.

This matters because it means the fix does not require Q-270-15c to be resolved first. Knowledge-shape and corrective-hint wording are separately owned; either or both can be improved independently.

### §10.4 Robustness across usage modes

A good knowledge representation must remain useful under first synthesis / corrective expansion / corrective compression / expert audience / beginner audience without embedding audience-specific prose.

| Mode | A | B | C | D |
| --- | --- | --- | --- | --- |
| First synthesis (v6 universal invariant) | ✓ | ✓ | ✓ | ✓ |
| Corrective expansion | ✓ | ✓ | ✓ | ✓ |
| Corrective compression | ✓ (either form kept) | ~ (canonical may be dropped) | ✓ | ✓ (either form kept) |
| Expert audience (technical vocabulary earned) | ✓ | ~ | ✓ | ✓ |
| Beginner audience (paraphrase available) | ✓ | ✓ | ✓ | ✓ |
| Cross-character (no character-specific prose) | ✓ | ✓ | ✓ | ✓ |

All four options meet the "no audience-specific prose" bar by construction *if authored correctly*. Only C enforces it mechanically.

---

## §11. PHASE 9 — RECOMMENDATION

### §11.1 Verdict

**Verdict B — Knowledge shape is a partial cause; an authoring convention helps but a companion tightening of corrective-hint wording is what fully closes the residual jargon behavior on same-topic Patch renders.**

Reasoning:
- Phase 1 established that lexical gravity is a cross-character structural property of Character OS knowledge authoring — not Patch-specific.
- Phase 3 confirmed the mechanism generalizes.
- Phase 5+Phase 6 identified Option **D — paired canonical + accessible paraphrase per factual section** as the strongest candidate implementable without schema, chunking, retrieval, or synthesis changes. Option C is a superior long-term endpoint but is out of scope for the smallest next step.
- Phase 8 established that Option D reduces corrective-pass regression risk without requiring the corrective system to change.
- The residual coupling to corrective-hint wording (Q-270-15c) is real. Even the strongest authoring convention cannot make raw enumeration reappearance impossible if the corrective hint explicitly instructs "expand secondary detail from the knowledge chunks" AND retrieval still returns a canonical form as the highest-density surface. The two levers are best tuned together, but do NOT need to be co-shipped.

Not Verdict A (single knowledge convention alone is sufficient): §10 shows Option D reduces risk substantially but does not eliminate the raw-terminology attractor entirely.

Not Verdict C (Patch-specific pathology): Phase 3 §5.5 refutes this — RIVET, PENNY, and REPO RED all exhibit the mechanism.

Not Verdict D (more evidence needed *before recommending anything*): the source-document analysis is already sufficient to justify a small, reversible experiment. What is not yet decidable from documents alone is *how much* Option D closes the regression on any specific render.

### §11.2 Recommended smallest controlled experiment

**Goal:** produce a falsifiable comparison of raw-terminology behavior with and without paired-paraphrase authoring, on a substrate that is (a) not Patch/AI-Agents (saturated), (b) fox-first-safe, (c) reversible without side effects on other characters or embeddings.

**Design:**

1. **Character:** RIVET (same workspace as Patch, so identical pipeline; different topic; unsaturated; enumeration-dense DEBUGGING chunk provides the mechanism).
2. **Baseline (control):** freeze the current RIVET KnowledgeDocument (`71e2ec43-6edc-47cf-beb5-25698a440d16`) — no edit.
3. **Alternate representation:** create a temporary shadow KnowledgeDocument (new UUID) whose content is the RIVET DEBUGGING section only, re-authored under Option D:
   - Original enumeration preserved verbatim.
   - One paired paraphrase sentence added: `In plain terms: when something's broken, the useful questions to ask yourself are — what changed since it worked, what should have happened, what actually happened, whether you can make it happen again on demand, where the failure first shows up, what evidence there is, what assumption might be wrong, and what small test would tell you which explanation is right.`
   - Persona-directive lines removed (or moved to a separate persona surface for the experiment).
4. **Substrate:** an Episode DIFFERENT from any Patch/AI-Agents render (e.g., `Rivet debugs a puzzle`, `Rivet investigates why a generation is inconsistent`). No same-topic Patch re-run.
5. **Rendering:** two renders — one against the frozen baseline, one against the shadow doc. Same `audience_hint=""`. Both use Writing Contract v6 as-shipped. No corrective-hint modification.
6. **Comparison:**
   - Draft A raw-terminology count.
   - Corrective Draft B raw-terminology count.
   - Retrieval score of paraphrase chunk vs canonical chunk (does adding paraphrase change ranking?).
   - Verifier verdict.
   - Identity markers preserved?
7. **Falsifiability:**
   - If shadow-doc Draft B contains all 8 canonical Q-enumeration items verbatim and no paraphrase, hypothesis is falsified — paired paraphrase does not reduce corrective attractor.
   - If shadow-doc Draft B contains paraphrase items in preference to raw canonical items, hypothesis is supported.
   - If retrieval ranking flips such that the paraphrase chunk starves the canonical chunk of retrieval, that is a NEGATIVE side effect and must be flagged.

**Explicit non-choices:**

- Do NOT use Patch. Substrate is saturated.
- Do NOT use REPO RED for the FIRST experiment. Shape-β voice-lock is a distinct pathology; testing paired-paraphrase against it is a separate experiment (see §11.3).
- Do NOT use PENNY for the first experiment. Penny's factual density is too low to produce a clean signal.
- Do NOT rewrite the shadow doc to remove ALL persona directives — that confounds the paired-paraphrase test with a persona-boundary-cleanup test. Keep those separate.
- Do NOT change the corrective-hint text in this experiment. That is the Q-270-15c slice, not this one.

**Reversibility:**

- Shadow doc is a new UUID; original RIVET doc is byte-stable throughout.
- Shadow doc's chunks are embedded independently; deleting the shadow doc removes them.
- No other character, no other workspace is affected.

### §11.3 Follow-up experiments (not for the first slice)

If the RIVET experiment supports Option D:
- **Second-substrate experiment:** apply Option D to one PENNY section (SAFETY guardrail enumeration) and one PATCH section other than AI-Agents. Confirm the effect generalizes across domains.
- **Shape-β voice-lock experiment:** apply Option C (structured schema) or a bounded Persona-extraction pass to one REPO RED section. This tests the DISTINCT voice-lock pathology identified in §5.5.
- **Ownership-cleanup slice:** create a bounded audit that separates persona directives from factual content in existing docs, without changing the factual claims themselves. This is a Phase-4 boundary enforcement, not a Phase 5 knowledge-shape change.

### §11.4 Decision gate

The recommendation is to run the §11.2 RIVET experiment in a subsequent slice as the smallest reversible test of the Option D convention. That slice would ship:

- shadow doc creation (audit-visible),
- two renders (audit-visible),
- raw-terminology + retrieval + verifier comparison (audit-visible),
- a Verdict at that slice's close: promote Option D to authoring convention, or reject, or refine.

The current slice is documentation-only. Do NOT run the experiment now.

---

## §12. EXPLICIT NON-CHANGES DURING THIS AUDIT

- **No KnowledgeDocument edited.** All 68 documents byte-stable.
- **No embedding regenerated.** No chunk indices touched.
- **No chunking changed.**
- **No retrieval logic touched.**
- **No Writing Contract change.** WCV remains 6.
- **No corrective-hint text changed.** Q-270-15c remains open.
- **No persona edit.** Patch / Rivet / Penny / Red character surfaces unchanged.
- **No schema change.** No migration created.
- **No render.** Zero new Compositions.
- **No NarrativeMemory promoted.** Total memory count unchanged.
- **No experiment env vars set.** All CHARACTER_OS_*_HINT / _POLICY / _EXPERIMENT variables remain OFF.
- **No code changed anywhere in the shell.**
- **Runtime state unchanged.** Django `:8010`, media-engine `:8001`, Vite `:5174`, Celery worker — as at SESSION 271 close.

The RIVET data-hygiene detritus finding (`[Session 266 experimental clone — WEAK — do not treat as canon]` inside chunk 13) is FLAGGED, not fixed. A separate small data-hygiene slice can remove it.

---

## §13. RETURN VALUES

1. **KnowledgeDocuments inspected:** PATCH `19778800`, RIVET `71e2ec43`, PENNY `e284edc9`, REPO RED `ee7b7e5c`. Full corpus scanned quantitatively (68 documents).
2. **Strongest cross-character finding:** dense enumeration as the only lexical surface for a concept is a **cross-character structural property**, not a Patch bug. All four inspected docs exhibit lexical-gravity risk; REPO RED additionally exhibits a distinct voice-lock pathology from canned quotes.
3. **Does Patch's lexical-gravity problem generalize?** YES. Same mechanism appears in RIVET (methodology enumerations), PENNY (safety enumerations, weaker), REPO RED (bulleted domain terminology + voice-quote gravity).
4. **Recommended knowledge-authoring convention:** **Option D — paired canonical + accessible paraphrase per factual section**, character-agnostic, additive. Option C (structured schema) is the stronger long-term endpoint, deferred to a future ingestion-normalization slice.
5. **Which layer should own normalization:** source-authoring guidance (Option A of Phase 7) plus a lightweight advisory linter. Explicitly NOT ingestion normalization / retrieval-time transformation / synthesis-time transformation for the first slice.
6. **Smallest controlled next experiment:** RIVET DEBUGGING shadow-doc comparison per §11.2. Substrate is unsaturated, workspace is shared with Patch (same pipeline), pathology is representative, reversibility is complete.
7. **Decision gate:** Verdict **B — Knowledge shape is partial cause; authoring convention helps and a companion corrective-hint tightening (Q-270-15c) is what fully closes the residual on same-topic Patch renders.**
8. **Commit SHA:** recorded in §14 after commit.
9. **Repo / runtime health:** `main == origin/main`, working tree clean, canonical runtime unchanged, no knowledge / embedding / memory / render mutation performed.

---

## §14. AUDIT COMMIT SHA

- SESSION 272 audit commit: `ecf529d` — `docs(session-272): knowledge-authoring/shape audit — Verdict B + Option D + RIVET experiment`
- Push status: recorded post-push in a follow-up commit if the SHA lands after this file was written.
- Working tree at close: clean; `main` at `ecf529d`.

---

**End of SESSION 272 audit — Slice A (documentation-only).**

---

## §15. SLICE B — RIVET DEBUGGING PAIRED-PARAPHRASE EXPERIMENT — ISOLATION DESIGN

*(Written before any mutation, per the SESSION 272 §11.2 experimental protocol.)*

### §15.1 Primary falsifiable question

*When the SAME factual knowledge additionally provides a neutral accessible lexical surface, does synthesis — especially corrective expansion — prefer or materially use that surface rather than reproducing the canonical enumeration?*

### §15.2 Sole intended variable

**Presence of a paired accessible paraphrase paragraph in the DEBUGGING section of the retrievable knowledge.** All other pipeline inputs must be held constant across conditions A (control) and B (experiment).

### §15.3 Isolation design: two disposable workspaces (Iso-2WS)

Retrieval scope is enforced by construction in `apps.embeddings.retrieval.retrieve_for_teammate` (K0 contract rule 3):
- Workspace filter is unconditional (`document__workspace=spokesperson.workspace`).
- Universe filter is unconditional (`document__universe_id=spokesperson.universe_id`, or IS NULL when the teammate has no Universe).
- M2M spokespeople visibility filter narrows further (`spokespeople__isnull=True` broadcast OR `spokespeople=this_teammate`).

Given the workspace unique constraint `(workspace, name)` on Teammate (unique_together per SESSION 271 §262), TWO teammates named `Rivet` cannot coexist in the same workspace. The **cleanest** way to hold every other variable constant while varying only the paraphrase is **two disposable workspaces, each containing one cloned Rivet Teammate and one shadow document**:

| Field | WS_CTL (control) | WS_EXP (experiment) |
| --- | --- | --- |
| Workspace slug | `session272-rivet-debug-ctl` | `session272-rivet-debug-exp` |
| Universe slug | `session272-rivet-debug-ctl` | `session272-rivet-debug-exp` |
| Teammate name | `Rivet` (cloned byte-for-byte from `5dd05e3c-e1e8-46bf-8cbf-f7d119ef9e70`) | `Rivet` (same clone) |
| KnowledgeDocument | `RIVET-DEBUG (CTL) — SESSION 272 experimental substrate` | `RIVET-DEBUG (EXP) — SESSION 272 experimental substrate` |
| Doc content | canonical DEBUGGING paragraph | canonical DEBUGGING paragraph + Option D paired paraphrase paragraph |
| Other docs in workspace | NONE | NONE |
| Other teammates in workspace | NONE | NONE |

Both workspaces are disposable — Django FK cascade cleanly removes each. The **canonical RIVET doc `71e2ec43-6edc-47cf-beb5-25698a440d16` in workspace `097bd82e` is not touched** and its 14-chunk baseline SHA is recorded in §15.7 for post-experiment verification.

### §15.4 What CTL and EXP share (byte-identical)

- Character: **Rivet** (cloned byte-for-byte from the canonical Teammate row — `business_brief`, `personality`, `voice_energy`, `voice_humor`, `voice_directness`, `voice_signature_phrases`, `voice_avoid_phrases`, `tone_archetype`, `visual_template`, `who_you_help`, `character_point_of_view`, `desired_feeling`, `always_emphasize`, `never_say`, `runway_avatar_id`, `voice_id`).
- Writing Contract version: **6**.
- audience_hint: `""` (empty; universal invariant fires alone).
- Operator topic: `Rivet demonstrates his debugging approach — when a generation comes out wrong once, how does he decide whether it's a fluke or a real problem worth investigating?` — a fresh unsaturated substrate, not any SESSION 271 topic.
- Target duration: **90 seconds** (identical to canonical v6 verification render `994e7b1b`).
- corrective_hint template: canonical duration-based (unchanged; Q-270-15c experiment env vars remain OFF).
- Retrieval top_k: `5` (default).
- Synthesis pipeline: `synthesize_with_duration_gate` (direct call).
- Runtime: local-real mode; media-engine `openai_mock=false`; `RENDER_SCRIPT_FORCE_MOCK` unset.
- NarrativeMemory policy: NONE — no memory rows attached to either render, so `retrieve_universe_memory` returns empty in both (both workspaces are fresh; no memories exist).
- Model / provider: `gpt-4o-mini` via OpenAI (per media-engine health).

### §15.5 The single differing factor

The DEBUGGING section paraphrase paragraph, added ONLY to the EXP doc, character-agnostic (no reference to Rivet), same paragraph shape as canonical enumeration:

**Canonical DEBUGGING paragraph (present in BOTH CTL and EXP):**

> DEBUGGING When something breaks, Rivet prefers reducing the problem before trying to fix it. Changing one meaningful variable and testing again is more informative than changing ten things at once. Useful debugging questions include what changed, what was expected, what actually happened, whether the behavior can be reproduced, where the behavior first becomes incorrect, what evidence exists, what assumption might be wrong, and what smallest test would separate two possible explanations. Evidence beats guessing.

**Option D paired paraphrase paragraph (EXP only):**

> In plain terms: ask what changed since it worked, what should have happened, what actually did, whether you can reproduce it, where the trouble starts, what evidence you have, what assumption might be wrong, and what small test would settle it.

The paraphrase preserves 100% of the eight canonical debugging-question concepts but expresses each in accessible everyday language. It does not remove the canonical enumeration; it adds a parallel accessible surface. No character voice, no audience directive, no anti-script.

### §15.6 Confound analysis + mitigations

| Potential confound | Mitigation |
| --- | --- |
| **Retrieval ranking may differ** — EXP doc has extra ~250 chars, so its embedding may drift; its chunk may score differently than CTL's. | Report actual retrieval scores + chunk IDs for both conditions. Do NOT interpret script differences as Option D evidence if retrieval fails to return the DEBUGGING chunk in one condition. |
| **Chunking may differ** — the chunker (`TextSplitter`, `DEFAULT_CHUNK_SIZE=1000`, `DEFAULT_CHUNK_OVERLAP=200`) splits at paragraph boundaries first. CTL is one paragraph (~720 chars) → one chunk. EXP is two paragraphs (~720 + ~250 = ~970 chars) → one chunk (still under 1000). | Verify chunk count post-embedding for both docs. If both docs produce exactly one chunk, chunking is not a variable. |
| **Doc length differs** — inherent to the experiment; the paraphrase IS the length. | Not a mitigatable confound — it is the treatment. Report actual chunk sizes. |
| **Teammate clone drift** — if any field differs between the two Rivet clones. | Clone via `Teammate.objects.get(pk=canonical).pk = None; save()` pattern, then verify field-by-field equality. Explicit assertion loop before render. |
| **Universe emptiness** — no NarrativeMemory in either workspace; canonical Patch's Workshop has 17 memories. Different memory-block content between experimental and canonical renders is a separate variable, not a CTL-vs-EXP one. Both CTL and EXP have zero memories → symmetric. | Verified in §15.9. |
| **Missing Rivet-adjacent knowledge** — both workspaces have ONLY the debugging paragraph. Synthesis has less material than a canonical Rivet render. | This is symmetric across CTL and EXP → not a variable. Renders may be terser than production; the metric of interest (paraphrase reappearance in corrective expansion) is still measurable. |
| **audience_hint provenance** — the SESSION 271 `_resolve_solo_audience_hint` reads step.params → settings → env. Since we go via `talking_head` starter or direct `synthesize_with_duration_gate` call, we pass `audience_hint=""` explicitly. Env vars are OFF (verified §15.9). | No leakage. |
| **Model non-determinism** — LLM sampling temperature is not zero. Same input can produce slightly different outputs across runs. | Report all raw outputs. Single-shot experiment is enough to falsify (paraphrase presence) but not to quantify precisely — this is acknowledged as a limitation, not a design flaw. |
| **Retrieval score reveals corpus imbalance** — a workspace with ONE doc always retrieves that doc at rank 1 regardless of query similarity. This means retrieval is guaranteed to return the DEBUGGING chunk in both conditions. | Confirmed. Retrieval isolation is by construction. |

### §15.7 Baseline hashes (canonical RIVET doc, must remain unchanged)

Recorded at experiment open. Verified again post-experiment in §16.7.

- Doc ID: `71e2ec43-6edc-47cf-beb5-25698a440d16`
- Workspace: `097bd82e-2995-4084-baa4-0f9692d804f7` (Patch's Workshop)
- Chunks: 14
- Full-text SHA-256: `75bac33223e3333893be2e589ac5adbbe9f16a9bfed361fe873a516e4d473b6e`
- Full-text length: 10,323 chars
- Per-chunk truncated hashes (16 hex chars):

| idx | chunk_id | length | sha256_16 |
| --- | --- | --- | --- |
| 0 | fc0f716c-… | 654 | 95efbd82a45f94c5 |
| 1 | 1af12752-… | 750 | 0b9560984a9b6f0c |
| 2 | 0aba73ef-… | 752 | be5fe534b56d8f43 |
| 3 | da5da06a-… | 659 | d8e59239fc1af09f |
| 4 | ae6894f2-… | 667 | 7d5c1ac39d7917d4 |
| 5 | bb65fcda-… | 576 | f6f405e6a516e306 |
| 6 | 3b1da9ef-… (DEBUGGING) | 720 | 9c932bd9b55d6418 |
| 7 | 24d21cfd-… | 986 | c5a66b2222657046 |
| 8 | 8f1686ac-… | 863 | 580739eb98ddd1e6 |
| 9 | 470ccc69-… | 760 | ff1e01c78d8f7998 |
| 10 | 0d6acc67-… | 669 | f5c2b2a577aa1b30 |
| 11 | 2c9b0837-… | 751 | b8f7cf2bf0adceae |
| 12 | c95dd3a9-… | 969 | 8bd2a8bc0f73d9e6 |
| 13 | 0158ad0d-… | 547 | 6378b7696f4e2aa9 |

### §15.8 Cross-contamination proof

**Claim:** The shadow docs in WS_CTL and WS_EXP cannot influence retrieval for:
- (a) the canonical RIVET Teammate (in workspace `097bd82e`),
- (b) any other Character OS teammate anywhere in the corpus,
- (c) each other.

**Proof:**

1. `retrieve_for_teammate` filters `document__workspace = spokesperson.workspace` unconditionally (`retrieval.py` line 195). Cross-workspace retrieval is impossible by construction.
2. The canonical Rivet Teammate `5dd05e3c` has `workspace = 097bd82e`. Its retrieval scope is workspace `097bd82e` only. It cannot see WS_CTL or WS_EXP docs.
3. The disposable Rivet clones live in WS_CTL and WS_EXP respectively. Each has retrieval scope of its own workspace only. They cannot see the canonical RIVET doc `71e2ec43` (workspace `097bd82e`), nor each other's shadow doc (different workspace).
4. The M2M spokespeople contract-rule 2 test suite (`test_retrieval_privacy`, `test_retrieval_isolation`) is the load-bearing enforcement; edits to bypass it fail review.

**Impact on other teammates:** none. No shared Universe, no shared workspace, no M2M spokespeople linkage.

### §15.9 Runtime state prior to mutation

- `main == origin/main` at `211fc5f` (SESSION 272 §14 SHA-record commit).
- Working tree clean.
- Django `:8010/admin/` → `http=302`.
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`.
- Vite `:5174/` → `http=200`.
- Celery worker: fresh (~34s post-restart at Slice A close); `inspect ping` replied.
- Experiment env vars: **zero found** across all worker PIDs.
- Canonical RIVET doc SHA verified matches §15.7 baseline.

### §15.10 Explicit non-changes committed to for Slice B

- Canonical RIVET doc `71e2ec43`: byte-stable. Verified pre + post.
- All other canonical KnowledgeDocuments (67 of 68): unchanged.
- Writing Contract v6: unchanged.
- Corrective-hint wording: unchanged.
- Persona / any Teammate row: unchanged for canonical Rivet `5dd05e3c` and every other canonical teammate.
- Schema: unchanged (no migration).
- Environment variables: unchanged (all `CHARACTER_OS_*_HINT` / `_POLICY` / `_EXPERIMENT` remain OFF).
- NarrativeMemory: no promotion, no new memory rows.
- Runtime / model configuration: unchanged.

### §15.11 Reversibility contract

At end of Slice B, the following ORM operations restore the corpus to its pre-experiment state:

```
Workspace.objects.filter(slug__in=["session272-rivet-debug-ctl", "session272-rivet-debug-exp"]).delete()
```

Django FK cascade deletes: Universe, Teammate, KnowledgeDocument, KnowledgeChunk, Composition, CompositionStep in each disposable workspace. Cross-workspace refs are impossible by construction (proof §15.8). Canonical Patch's Workshop is untouched.

Reversibility is exercised at the end of Slice B — the disposable workspaces are deleted after evidence is frozen to sidecars.

---

## §16. SLICE B — RIVET DEBUGGING PAIRED-PARAPHRASE EXPERIMENT — EXECUTION + VERDICT

### §16.1 Setup manifest

Setup script: `scripts/session272_slice_b_setup.py`. Ingested via `apps.embeddings.ingestion.ingest_text` (production path). Embedded synchronously via `apps.embeddings.tasks.embed_document` (production task, called directly).

| Field | CTL | EXP |
| --- | --- | --- |
| Workspace | `d73fb96a-e5e2-473c-a83a-af0e55b70e9f` (slug `session272-rivet-debug-ctl`) | `1f4fad65-a3fe-41c1-b2bf-3e3446fc1c94` (slug `session272-rivet-debug-exp`) |
| Universe | `98a292a1-c9f2-4389-94b0-f12d4f2e7565` | `23810779-6fd4-4f32-bfc6-92d924f7476c` |
| Rivet Teammate | `af86f830-e2b7-4318-8c30-60bd4734a3f4` | `e649071f-063b-4e92-b695-e45977f442f3` |
| KnowledgeDocument | `d8ab3d2c-cab3-41f3-91a1-bab8ba88f5b6` (517 chars) | `64c91888-5534-418b-bbe2-33743f815bcf` (763 chars) |
| Doc SHA-256 | `b17105434b87d6ab9589165eb381f72ac7a1cfd39161eedbc2a1db6a00958d94` | `71639d24737b4c4a984c833087d1dee87be7b79301d94232a73c6f77fc2a0b1f` |
| Chunk count | **1** (idx=0, 517 chars, sha16=`b17105434b87d6ab`) | **1** (idx=0, 763 chars, sha16=`71639d24737b4c4a`) |
| Doc status | `processed` | `processed` |

**Chunking symmetry confirmed:** Both docs produced exactly one chunk. Neither hit the 1000-char soft split limit. Chunker did NOT introduce a chunking variable across conditions.

Setup sidecar: `docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json`.

### §16.2 Rendering

Render script: `scripts/session272_slice_b_render.py`. Direct call to `character_os.duration_contract.synthesize_with_duration_gate` (no Runway avatar_speech, no Celery, no Composition row). Same call signature for both conditions:

```
synthesize_with_duration_gate(
    rivet_teammate,
    OPERATOR_TOPIC,
    target_duration_seconds=90,
    target_shape="solo_scene",
    audience_hint="",
)
```

Both conditions used **Writing Contract v6**. `audience_hint=""` → universal invariant fires alone (no §5 AUDIENCE DIRECTIVE emitted). No corrective-hint change. No experiment env vars set (verified via `ps eww` on worker PIDs).

### §16.3 Retrieval results

Retrieval distance to the operator topic (lower = closer semantic match):

| Condition | Chunks returned | Rank-1 chunk ID | Distance |
| --- | --- | --- | --- |
| CTL | 1 | `9a2b6f01-4557-4107-ae9e-8c2a9a9d2e00` | **0.3381** |
| EXP | 1 | `31fd97eb-f26d-42bb-9d5e-143ee37bac64` | **0.3635** |

**Confound flag noted (per §15.6):** EXP retrieval distance is 7.5% higher than CTL. The Option D paired paraphrase slightly diluted the embedding's match to the debugging query. This is a real side effect — the extended chunk still ranked at position 1 in a single-doc workspace, but its cosine similarity to the query is measurably worse. In a multi-doc workspace, this could plausibly push the shadow-form chunk down the ranking. Flagged for follow-up.

### §16.4 Synthesis outputs

**Both conditions accepted after ONE corrective retry (attempt_count=2).** Both verified. Both first-pass drafts undershot the 81-second synth target and triggered the canonical `Expand secondary detail from the knowledge chunks` corrective hint.

| Condition | Draft A chars | Corrective hint fired | Draft B chars | verification_status |
| --- | --- | --- | --- | --- |
| CTL | 568 (≈39 s) | duration expansion | 1420 (accepted) | `verified` |
| EXP | 792 (≈54 s) | duration expansion | 1260 (accepted) | `verified` |

Full drafts + hints are in the frozen sidecar `01_slice_b_ab_render_evidence.json`.

### §16.5 Concept-level lexical analysis

**Coding scheme (SESSION 271 §191.6 style):** count verbatim substring matches for each canonical enumeration item and each Option D paraphrase item.

Canonical enumeration items sought (from the DEBUGGING chunk verbatim):
`what changed` / `what was expected` / `what actually happened` / `whether the behavior can be reproduced` / `where the behavior first becomes incorrect` / `what evidence exists` / `what assumption might be wrong` / `what smallest test would separate two possible explanations` / `one meaningful variable` / `changing ten things at once` / `evidence beats guessing`.

Option D paraphrase items sought (present ONLY in the EXP document):
`what should have happened` / `what actually did` / `whether you can reproduce it` / `where the trouble starts` / `what evidence you have` / `what small test would settle it` / `since it worked` / `in plain terms` / `small test`.

| Draft | RAW-CANONICAL matches | Which canonical items matched | PARAPHRASE matches | Which paraphrase items matched |
| --- | --- | --- | --- | --- |
| CTL Draft A | **3** | `what changed`, `what actually happened`, `one meaningful variable` | 0 | — |
| CTL Draft B (accepted) | **5** | `what changed`, `what actually happened`, `where the behavior first becomes incorrect`, `one meaningful variable`, `evidence beats guessing` | 1 | `small test` (also present in CTL — not paraphrase-specific) |
| EXP Draft A | **3** | `what actually happened`, `where the behavior first becomes incorrect`, `one meaningful variable` | 0 | — |
| EXP Draft B (accepted) | **3** | `what changed`, `where the behavior first becomes incorrect`, `one meaningful variable` | 1 | `small test` |

**Primary finding — Draft B raw canonical matches:**

- CTL Draft B: **5** raw canonical hits (including `evidence beats guessing`, Rivet's signature line).
- EXP Draft B: **3** raw canonical hits.

**EXP produced 40% fewer raw canonical enumeration items in the corrective-expanded accepted script.** Directional support for Option D reducing lexical-gravity attractor reappearance.

**Secondary finding — the load-bearing attractor was NOT displaced:**

`where the behavior first becomes incorrect` (identified in SESSION 271 §191.9 as an example of dense-enumeration gravity) appears verbatim in BOTH Draft Bs. The Option D paraphrase equivalent `where the trouble starts` appears in NEITHER draft. Even though the paraphrase was physically adjacent in the retrieved EXP chunk, synthesis reached for the canonical form on this specific attractor. **Option D reduces total attractor count but does not selectively displace the strongest attractor.**

**Tertiary finding — EXP did not adopt paraphrase-specific vocabulary preferentially:**

The paraphrase-specific phrases (`what should have happened`, `what actually did`, `whether you can reproduce it`, `where the trouble starts`, `what evidence you have`, `what small test would settle it`, `since it worked`, `in plain terms`) all appeared **zero** times in the EXP drafts. EXP Draft B does contain **semantically equivalent accessible verbiage** — `What did I expect?`, `What actually appeared?`, `What changed since the last result that looked right?` — but these are model-generated new expressions, not verbatim adoption of the paraphrase text. The paired paraphrase apparently acted as a *stylistic cue* rather than as a substitution table.

### §16.6 Rivet identity marker preservation

Rivet's signature phrasing / worldview markers:

| Marker | CTL Draft B | EXP Draft B |
| --- | --- | --- |
| `evidence beats guessing` (canonical signature line) | ✓ | ✗ (absent) |
| `meaningful variable` | ✓ | ✓ |
| `reduce the problem` | ✓ | ✓ |
| `smallest test` | ✓ | ✗ (only `one small test`) |
| `one small test` | ✗ | ✓ |
| `not a diagnosis` | ✓ | ✗ (uses `not, by itself, a mystery`) |
| `dramatic hat` / `wearing a dramatic hat` | ✓ ✓ | ✓ ✓ |
| `decorative mysteries` (Rivet-flavored line) | ✗ | ✓ (EXP Draft A: "ten decorative mysteries") |
| **Total identifiable markers** | **7** | **5** |

**Observation:** EXP Draft B preserves Rivet identity but *loses two canonical markers* (`evidence beats guessing`, `smallest test`) while *adding two accessible equivalents* (`one small test`, `decorative mysteries`). Net identity preservation: **broadly intact but slightly reshaped**. Not a regression, but not a strict superset of CTL either.

### §16.7 Canonical RIVET doc hash verification (post-experiment)

Verified after both renders: canonical RIVET doc `71e2ec43-6edc-47cf-beb5-25698a440d16` unchanged.

- Full-text SHA-256 (post): `75bac33223e3333893be2e589ac5adbbe9f16a9bfed361fe873a516e4d473b6e` — **matches §15.7 baseline** ✓
- Full-text length: 10,323 chars — matches ✓
- 14 chunk hashes — all match ✓

No mutation to canonical Rivet knowledge occurred.

### §16.8 Verdict on the primary falsifiable question

**Verdict B — PARTIAL / CONFOUNDED.**

- Effect direction is consistent with Option D reducing raw-canonical reappearance in corrective expansion: CTL 5 → EXP 3 raw canonical hits (a 40% reduction).
- Effect is **not clean**: the strongest single attractor (`where the behavior first becomes incorrect`) was NOT displaced in EXP, and the paraphrase-specific vocabulary was NOT adopted verbatim in EXP.
- **Retrieval confound**: EXP retrieval cosine distance 0.3635 vs CTL 0.3381 (7.5% worse). In a multi-doc workspace this could plausibly starve the shadow-form chunk of retrieval altogether. Cannot be dismissed.
- **Statistical confound**: single-shot render per condition. LLM sampling variance is uncontrolled. A 5 → 3 delta at n=1 is directional but not statistically defensible.
- **Identity confound**: EXP lost the signature `evidence beats guessing` line. This is a mildly negative side effect that would need to be verified across more trials.

The question is not answered A / C / D by this experiment. The evidence rules out "no effect" and rules out "Option D fixes it" — it lands squarely at "Option D helps somewhat, doesn't block the strongest attractor, and comes with side effects worth measuring."

### §16.9 Recommended smallest next move

**Do NOT promote Option D to a production authoring convention.**

Two low-cost follow-up experiments would meaningfully advance the question. Neither should be run in this slice. Each is a bounded next-slice candidate.

**Follow-up #1 — Multi-shot replicate (highest information-per-cost).**
- Run the SAME CTL/EXP setup 4 more times each (n=5 per condition). Same operator_topic, same everything. Measure canonical-vs-paraphrase distribution across trials. Falsifiability: if the CTL-vs-EXP delta stays consistently around 40%, effect is real. If it collapses to zero or flips, single-shot delta was sampling noise.
- Cost: ~$0.25 total on gpt-4o-mini.
- Reversibility: same disposable workspaces reused; no new corpus rows.

**Follow-up #2 — Per-term inline pairing (Option A shape from §7).**
- Modify the EXP doc to use per-item inline pairing rather than a trailing paired paraphrase paragraph. Example: `Useful debugging questions include what changed (since it worked), what was expected (what should have happened), what actually happened (what actually did), ...`.
- This physically co-locates each canonical term with its accessible gloss, giving synthesis a substitution-table shape rather than a stylistic-cue shape.
- Falsifiability: if Option A displaces `where the behavior first becomes incorrect` with `where it goes wrong` or similar in Draft B where Option D did not, the paired-inline shape is materially stronger.
- Same disposable workspace, same render pipeline. Additive slice; canonical corpus still untouched.

**Not recommended for the next slice:**
- Rewriting canonical Rivet doc. Waiting for multi-shot evidence.
- Rewriting canonical Patch doc. Same.
- Modifying the corrective hint text. Owned by Q-270-15c; separate concern.
- Adding Option D authoring guidance to a scope-lock document. Waiting for stronger evidence.
- REPO RED-style canned-quote pathology test. Separate slice; different mechanism.
- Cross-domain (Patch/PENNY/REPO RED) generalization test. Wait for Rivet finding to stabilize first.

### §16.10 Cleanup (reversibility exercised)

Disposable workspaces WERE NOT deleted at experiment close, because the follow-up multi-shot replicate reuses the exact same substrate. If the follow-up is deferred indefinitely, run:

```
Workspace.objects.filter(
    slug__in=["session272-rivet-debug-ctl", "session272-rivet-debug-exp"],
).delete()
```

Or run `scripts/session272_slice_b_setup.py` again — its `_teardown_if_exists()` prologue is idempotent and deletes-and-recreates cleanly.

### §16.11 Slice B non-changes (verified)

- Canonical RIVET doc `71e2ec43` — SHA verified unchanged post-experiment (§16.7).
- Writing Contract v6 — unchanged.
- Corrective-hint wording — unchanged (canonical duration hint used verbatim).
- Persona / Teammate row for canonical Rivet `5dd05e3c` — unchanged. Clones are separate rows in disposable workspaces.
- Schema — unchanged.
- All experiment env vars — remain OFF.
- NarrativeMemory — no promotion; disposable workspaces have zero memories.
- Runtime / model — unchanged.
- 67 other canonical KnowledgeDocuments — unchanged.

### §16.12 Evidence sidecars

- `docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json` — setup manifest (workspace/universe/teammate/doc IDs, chunk texts, hashes).
- `docs/design/session_272_experiment_data/01_slice_b_ab_render_evidence.json` — retrieval scores, first-pass drafts, corrective hints, accepted drafts, verification statuses, attempt counts, model.

---

**End of SESSION 272 Slice B. Verdict B — PARTIAL / CONFOUNDED. Do not implement Option D. Next candidate slice: multi-shot replicate of Slice B (highest information-per-cost) before considering Option A per-term inline pairing.**

---

## §17. SLICE C — MULTI-SHOT REPLICATE — 5 TRIALS PER CONDITION — VERDICT

### §17.1 Setup

- Reused the exact Slice B disposable substrates verbatim (workspaces `session272-rivet-debug-ctl` / `session272-rivet-debug-exp`, Rivet clones, single-chunk KnowledgeDocuments).
- Substrate verification before rendering: workspace + universe + teammate + doc + chunk IDs all match Slice B manifest byte-for-byte. Chunk hash sha16 match.
- Canonical RIVET doc `71e2ec43-…` full-text SHA-256 verified equal to §15.7 baseline before AND after all trials.
- Zero experiment env vars in worker PIDs.
- All 10 renders used Writing Contract v6, `audience_hint=""`, `target_shape="solo_scene"`, `target_duration_seconds=90`, `retrieve_for_teammate` default `top_k=5`, canonical corrective hint, gpt-4o-mini via OpenAI. No NarrativeMemory. No Composition rows written.
- Slice B evidence preserved verbatim as **trial 1** in both conditions. **Trials 2–5** run fresh in Slice C. Total dataset: **CTL n=5, EXP n=5**.

Setup + render scripts: `scripts/session272_slice_c_multishot.py`. Aggregate scorer: `scripts/session272_slice_c_analyze.py`. Evidence: `docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json`. Aggregate: `03_slice_c_aggregate_analysis.json` + `03_slice_c_aggregate_summary.txt`.

### §17.2 Three-category classifier

To test the emerging Slice B hypothesis (Option D may not function as a substitution vocabulary; it may reduce lexical anchoring by giving synthesis room to generate character-native accessible expressions), each draft is scored per debugging concept along three disjoint categories:

1. **Canonical** — verbatim substrings from the canonical DEBUGGING chunk (`what changed`, `what was expected`, `what actually happened`, `whether the behavior can be reproduced`, `where the behavior first becomes incorrect`, `what evidence exists`, `what assumption might be wrong`, `what smallest test would separate two possible explanations`, `one meaningful variable`, `changing ten things at once`, `evidence beats guessing`).
2. **Paraphrase-supplied** — verbatim substrings from the Option D paired paraphrase paragraph (`what changed since it worked`, `what should have happened`, `what actually did`, `whether you can reproduce it`, `where the trouble starts`, `what evidence you have`, `what assumption might be wrong`, `what small test would settle it`). Present ONLY in the EXP doc.
3. **Accessible model-generated** — regex-defined semantic equivalents NOT verbatim in either category 1 or category 2 (`what did I expect`, `what actually appeared`, `can it happen again`, `one small test`, `since the last result`, etc.). Blank-out order enforces disjointness at scoring time.

### §17.3 Aggregate results (n=5 per condition)

**Draft A (first pass; before corrective retry):**

| Metric | CTL | EXP |
| --- | --- | --- |
| Canonical hits per trial | [3, 3, 4, 3, 2] · mean **3.00** · median 3 | [3, 2, 1, 3, 3] · mean **2.40** · median 3 |
| Paraphrase-supplied hits per trial | [0, 0, 0, 0, 0] | [0, 1, 0, 0, 0] |
| Accessible (model-gen) hits per trial | [7, 3, 4, 1, 0] · mean **3.00** | [4, 1, 3, 1, 2] · mean **2.20** |
| Attractor `where the behavior first becomes incorrect` freq | 0/5 | 1/5 |

**Draft B (accepted after 1 corrective expansion; the SESSION 271 §191.9 test point):**

| Metric | CTL | EXP |
| --- | --- | --- |
| Canonical hits per trial | [5, 3, 1, 3, 4] · mean **3.20** · median 3 | [3, 3, 2, 3, 4] · mean **3.00** · median 3 |
| Paraphrase-supplied hits per trial | [0, 0, 0, 0, 0] · mean **0.00** | [0, 0, 0, 0, 0] · mean **0.00** |
| Accessible (model-gen) hits per trial | [8, 3, 3, 3, 5] · mean **4.40** · median 3 | [5, 3, 2, 3, 7] · mean **4.00** · median 3 |
| Attractor `where the behavior first becomes incorrect` freq | 2/5 | 2/5 |
| Rivet identity markers per Draft B | [10, 4, 4, 6, 4] · mean **5.60** | [6, 2, 4, 7, 5] · mean **4.80** |
| Retrieval distance (deterministic — same doc, same query) | 0.3381 (identical across all 5) | 0.3635 (identical across all 5) |
| Verified | 5/5 | 5/5 |
| Attempts per trial | all 2 | all 2 |
| Corrective retry required | 5/5 | 5/5 |

**Per-concept Draft B canonical hits (5-trial cumulative, values shown per trial):**

| Concept | CTL cumulative | EXP cumulative |
| --- | --- | --- |
| what_changed | 4/5 (1,1,0,1,1) | 4/5 (1,0,1,1,1) |
| what_expected | 0/5 (0,0,0,0,0) | 0/5 (0,0,0,0,0) |
| what_actually_happened | 4/5 (1,1,0,1,1) | 3/5 (0,1,0,1,1) |
| reproducibility (verbatim canonical) | 0/5 | 0/5 |
| **where_incorrect (STRONGEST ATTRACTOR)** | **2/5** (1,0,0,0,1) | **2/5** (1,1,0,0,0) |
| evidence | 0/5 | 0/5 |
| assumption | 0/5 | 0/5 |
| smallest_test (canonical form) | 0/5 | 0/5 |
| one_meaningful_variable | 5/5 (1,1,1,1,1) | 5/5 (1,1,1,1,1) |
| evidence_beats_guessing | 1/5 (1,0,0,0,0) | 1/5 (0,0,0,0,1) |

**Per-concept Draft B accessible model-generated hits:**

| Concept | CTL cumulative | EXP cumulative |
| --- | --- | --- |
| what_changed | 0/5 | 1/5 |
| what_expected | 5/5 (1,1,1,1,1) | 3/5 (1,1,0,0,1) |
| what_actually_happened | 1/5 | 1/5 |
| reproducibility | 4/5 (1,0,1,0,2) | 4/5 (1,0,0,1,2) |
| smallest_test (accessible form: `small test`, `one small test`) | 9 total (3,2,0,2,2) | 11 total (1,2,2,2,4) |
| assumption | 1/5 | 0/5 |
| one_meaningful_variable | 1/5 | 0/5 |

**Per-concept Draft B supplied-paraphrase hits:** 0/5 in every concept, in BOTH conditions. **The Option D paired paraphrase paragraph is never adopted verbatim by synthesis.**

### §17.4 Analysis vs the Slice B hypothesis

**Slice B trial 1 delta:** CTL canonical=5, EXP canonical=3 (a 40% reduction on n=1).

**Slice C n=5 delta:** CTL mean=3.20, EXP mean=3.00 (a 6% reduction). Slice B's delta was dominated by the CTL trial-1 value of 5 (later trials: 3, 1, 3, 4 → mean 2.75 for trials 2–5 in CTL). CTL trial 1's `5` was an outlier at the high end.

**Slice B's directional support for Option D does NOT replicate at n=5.** Distributions overlap almost entirely. Medians are identical (3 vs 3).

**Strongest attractor `where the behavior first becomes incorrect`:** appears in Draft B at exactly the same frequency (2/5) in both conditions. Option D does not displace it.

**Supplied Option D paraphrase adoption:** 0/5 in EXP Draft B. **Zero times across five trials.** The paraphrase paragraph is not a substitution table — synthesis never reaches for its verbatim wording in the accepted draft. Slice B's original interpretation ("Option D reduces attractor count by giving parallel accessible form") is not what happens mechanically.

**Model-generated accessible expressions dominate.** In BOTH conditions, Draft B accessible ≈ 4/trial — greater than either canonical (~3) or paraphrase (0). This is the dominant form of accessible expression in the pipeline.

- CTL mean accessible = 4.40 (higher than EXP)
- EXP mean accessible = 4.00 (lower than CTL)

**EXP does NOT increase model-generated accessible frequency.** If anything, it slightly reduces it. Chris's Slice C hypothesis — that Option D "may reduce lexical anchoring by providing multiple semantic surfaces, allowing synthesis to generate a third character-native expression" — is **not supported** by the n=5 data. Third-form generation happens robustly in BOTH conditions and appears independent of doc shape.

**Where does the third-form generation come from?** Given it's uniform across CTL and EXP, and given persona and Writing Contract v6 are identical, the mechanism is most consistent with **v6 universal invariant + Rivet persona reasoning naturally**. The knowledge doc shape is not a load-bearing input for accessible reformulation.

**Rivet identity markers:** CTL Draft B mean = 5.60, EXP Draft B mean = 4.80. CTL preserves identity slightly BETTER on average. This is a small negative for EXP (marginal identity regression), consistent with Slice B's observation that EXP lost the `evidence beats guessing` signature line — but at n=5 the effect is small and variable (EXP trial 4 has 7 markers, higher than CTL trials 2–5).

**Retrieval distance:** deterministic per doc — CTL=0.3381 across every trial, EXP=0.3635 across every trial. EXP retrieval is stably ~7.5% worse. In a single-doc workspace this doesn't change ranking (only one chunk anyway), but the direction is negative for Option D at scale.

**Verification:** 5/5 verified in both conditions. No verifier regression. Both conditions triggered exactly 1 corrective expansion per trial (Draft A always undershot the 81-second synth target).

**Qualitative convergence:** all 10 accepted drafts share a distinctive Rivet-flavored opening pattern (`This generation came out wrong once.` / `One bad generation is not a diagnosis.` / `Well. That generation is wrong.`) and closer patterns (`test again`, `let the evidence do the worrying`). No obvious stylistic divergence between CTL and EXP is visible on inspection. The two conditions produce copy of comparable quality, tone, and factual grounding.

### §17.5 Verdict on the primary Slice C question

**Verdict C — NOT REPLICATED.**

Slice B's 5 → 3 raw-canonical reduction was noise. At n=5 the mean canonical delta drops to 0.20 (from 2.00), medians are equal, distributions overlap. The strongest single attractor is unaffected. The supplied paraphrase paragraph is never adopted. Rivet identity is marginally worse under EXP. Retrieval is deterministically worse under EXP. Verification is unchanged (both perfect).

Chris's emerging Slice C hypothesis — that Option D might work by unlocking third-form generation rather than substitution — is **not supported**. Third-form generation happens robustly regardless of doc shape and slightly LOWER under EXP.

### §17.6 What DID replicate — a load-bearing observation

The single most stable finding across 10 trials, which explains the residual jargon behavior more parsimoniously than the Slice A / Slice B knowledge-shape hypothesis, is this:

**Model-generated accessible expressions dominate BOTH conditions at ~4 hits per Draft B — more than either canonical (~3) or supplied paraphrase (0).**

- The canonical enumeration produces a stable ~3 hits per Draft B, driven mostly by the load-bearing chunk containing that exact wording (retrieval is single-doc so this chunk is always retrieved).
- The supplied paraphrase is inert.
- Model-generated accessible expressions do the actual accessibility work, and their frequency is a property of Writing Contract v6 + persona + operator topic, not of knowledge-doc shape.

This suggests the SESSION 271 §191.9 causal ranking may need refinement:

- **C** (KnowledgeDocument lexical gravity, ranked dominant in §191.9) is real but bounded — it caps at ~3 hits per Draft B regardless of Option D presence.
- **D** (corrective expansion) is what causes canonical hits to appear at all — Draft A canonical mean ~2.4–3.0 versus Draft B canonical mean ~3.0–3.2, so the corrective retry adds ~0.2–0.8 canonical hits on average.
- **The v6 universal invariant + Rivet persona** does most of the accessibility work by generating fresh character-native expressions. This is what Chris was hoping Option D might amplify — but it turns out the model already does this on its own.

### §17.7 Slice C non-changes (verified)

- Canonical RIVET doc `71e2ec43` full-text SHA equal to `75bac33223e3333893be2e589ac5adbbe9f16a9bfed361fe873a516e4d473b6e` — matches §15.7 baseline pre AND post all 8 fresh trials.
- Writing Contract v6 — unchanged.
- Corrective-hint wording — unchanged.
- Persona / any Teammate row — unchanged for canonical Rivet + every other canonical teammate. Slice B clones reused.
- Schema — unchanged.
- Experiment env vars — all remain OFF.
- NarrativeMemory — no promotion; disposable workspaces still have zero memories.
- Runtime / model — unchanged.
- 67 other canonical KnowledgeDocuments — unchanged.
- EXP paraphrase paragraph — unchanged from Slice B (same doc, same chunk sha16 `71639d24737b4c4a`).

### §17.8 Recommended smallest next move

Given Verdict C, the Option D authoring convention as tested is not supported by evidence. Three low-cost follow-ups are candidates. **The audit doc does not commit to any of them; each is a decision point for a subsequent slice.**

**Option 1 (recommended) — REFRAME the knowledge-shape research question.** The load-bearing empirical finding (§17.6) is that model-generated accessible expressions do the accessibility work regardless of doc shape. This suggests the SESSION 271 §191.9 causal ranking overweights knowledge shape (C) relative to the model's intrinsic reformulation behavior. The right next slice may be to characterize *where* v6 + persona already succeed and *where specifically* they fail — then decide whether knowledge-shape is even the right lever. Concrete slice: audit a fresh Rivet-adjacent Episode where the raw-canonical attractor `where the behavior first becomes incorrect` DOES appear in Draft B (2/5 rate here), inspect prompt-side context, determine whether a corrective-hint tweak (Q-270-15c) rather than a knowledge-shape tweak is the correct lever.

**Option 2 — Test Option A (per-term inline pairing) as previously specified in §16.9.** Physical per-term co-location may displace the sticky attractor where Option D didn't. Cost: same as Slice C. Reversibility: shadow docs.

**Option 3 — Multi-shot at n=10 or n=20.** If someone wants tighter confidence intervals on the Slice C means, add more trials at ~$0.20 per 10 trials. Low information density; the effect is either not there or too small to matter operationally.

**Not recommended:**
- Any implementation of Option D as an authoring convention. Evidence does not support it.
- Rewriting the canonical Rivet or Patch KnowledgeDocuments.
- Modifying Writing Contract v6.
- Modifying corrective-hint wording as a co-shipped fix. Q-270-15c is a separate concern; the Slice C evidence does not obligate that slice.
- Testing Penny / REPO RED at this stage. Cross-domain generalization is only worth pursuing after a within-Rivet effect is stable.
- Cleaning persona directives from any KnowledgeDocument. Separate slice.
- Promoting NarrativeMemory. Not relevant.

### §17.9 Disposable substrate — retention decision

Left in place because:
- Any of Options 1/2/3 above reuses them.
- No cost to leaving; two workspaces + two docs + two chunks + zero memories occupy negligible storage.
- Reversibility contract from §15.11 remains a one-line ORM cascade delete if abandoned.

### §17.10 Slice C evidence sidecars

- `docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json` — all 10 trials, retrieval, drafts, verification, model.
- `docs/design/session_272_experiment_data/03_slice_c_aggregate_analysis.json` — machine-readable aggregate + per-concept per-trial per-draft counts.
- `docs/design/session_272_experiment_data/03_slice_c_aggregate_summary.txt` — human-readable per-condition summary.

---

**End of SESSION 272 Slice C. Verdict C — NOT REPLICATED. Slice B's directional support was sampling noise. Option D as tested does not reduce raw-canonical reappearance and does not amplify third-form generation. Do not implement any knowledge-authoring convention on this evidence. Next candidate slice (recommended): reframe the question against the §17.6 finding — model-generated accessible expressions dominate BOTH conditions, suggesting Writing Contract v6 + persona already do the accessibility work. STOP.**

---

## §18. SLICE D — REFRAMED QUESTION: WHAT DRIVES CORRECTIVE-PASS CANONICAL REGRESSION

Given Slice C Verdict C, the working assumption "accessible alternate wording must be supplied by KnowledgeDocument shape" is FALSIFIED. The reframed research question is:

*When Writing Contract v6 + persona already produce accessible, character-native reformulations, what specifically causes corrective expansion to reintroduce canonical KnowledgeDocument wording?*

This slice is **evidence-audit-first**. The 10 existing Slice C trials already contain enough qualifying Draft-A → Draft-B regression cases to constrain the hypothesis space substantially. No new rendering was performed for §18's analysis.

### §18.1 The mechanistic delta between Draft A and Draft B

Traced via code read of `character_os.script_synthesis._call_responses_api`, `_assemble_system_prompt`, `_assemble_task_message`, `_build_factual_basis_section`, and `duration_contract._expansion_hint` at `main` HEAD `7bc294c`.

**System prompt (Draft A and Draft B — BYTE-IDENTICAL):**
```
§1 Factual Basis
  BUSINESS SHAPE: {business_brief}
  AUDIENCE: {who_you_help}
  OFFERING: {what_you_sell}
  KNOWLEDGE CHUNKS:
    [CHUNK 1 — doc {id}]{chunk_text}
    ...
§2 Character Voice
§3 Brand Voice
§4 Writing Contract v6 (solo_scene)
Precedence rules
```

**User prompt (Draft A):**
```
=== SECTION 5 — TASK ===
TOPIC: {operator_prompt}

Write the spokesperson's spoken script for this task. Plain
spoken English — this becomes voiceover.
```

**User prompt (Draft B):**
```
=== SECTION 5 — TASK ===
TOPIC: {operator_prompt}

HARD CONSTRAINTS (override Character Voice and Writing
Contract preferences; do NOT override Factual Basis or
Brand Voice prohibitions):

CORRECTIVE HINT (previous attempt feedback — apply this):
Your previous draft was {N} characters ({W} words,
estimated ~{S}s of speech). Target is {T}s.
REWRITE THE SAME NARRATIVE ABOVE {MIN} CHARACTERS (aim
for ~{IDEAL}, do not exceed {MAX}). You currently need
at least {SHORTFALL} more characters to meet the minimum.
Preserve the central arc (opening → development → payoff
→ single closing invitation), the narrator perspective,
and the factual grounding from the knowledge chunks.
Expand secondary detail from the knowledge chunks —
describe more of the sensory / emotional beats already
implied. Do NOT restart with a new opening. Do NOT add
a second call to action. Do NOT invent facts not present
in the knowledge chunks.

Write the spokesperson's spoken script for this task. Plain
spoken English — this becomes voiceover.
```

**Confirmed:** the ONLY delta between the Draft A and Draft B LLM calls is the CORRECTIVE HINT block appended in §5 HARD CONSTRAINTS. Retrieval runs on each pass with the identical operator-topic query and returns identical chunks in identical order. The Q-270-15c experimental gate `_corrective_revision_experiment_active()` is OFF (verified §15.9 + §17.1); `previous_draft` is therefore NEVER supplied to the retry — the corrective retry does **not** see Draft A anywhere in its prompt.

The corrective hint mentions "**knowledge chunks**" FOUR times: (1) "the factual grounding from the knowledge chunks," (2) "Expand secondary detail from the knowledge chunks," (3) "describe more of the sensory / emotional beats already implied," (4) "Do NOT invent facts not present in the knowledge chunks." The most action-directing of these is #2.

### §18.2 Sub-observation — "REWRITE THE SAME NARRATIVE ABOVE" is misleading

The corrective hint text says `REWRITE THE SAME NARRATIVE ABOVE {MIN} CHARACTERS`, referring to a previous draft that is expected to appear ABOVE the hint in the prompt. But `previous_draft` is only emitted when Q-270-15c is active. With Q-270-15c OFF (production default; SESSION 271 + 272), **there is no "narrative above."** The only text above §5 in the prompt is §1 Factual Basis (containing KNOWLEDGE CHUNKS), §2 Character Voice, §3 Brand Voice, and §4 Writing Contract v6.

**This is a latent prompt-hygiene bug.** The instruction "REWRITE THE SAME NARRATIVE ABOVE" points at nothing in the default pipeline. Whether the model treats this as a no-op, or reaches for §1 (the only textually-narrative-adjacent content above §5), is empirically observable via the Draft B canonical hit patterns.

The bug pre-existed SESSION 272. It is not being fixed here; it is being NAMED so the causal analysis stays honest.

### §18.3 Draft A → Draft B per-trial per-concept transitions (existing evidence)

Computed from `03_slice_c_aggregate_analysis.json`. Notation `C{n}P{n}A{n}` = canonical / paraphrase-supplied / accessible model-generated counts.

**Load-bearing attractor `where the behavior first becomes incorrect` — the SESSION 271 §191.4 case:**

| Trial | Draft A | Draft B | Transition |
| --- | --- | --- | --- |
| CTL 1 | C0P0A0 | C1P0A0 | **NEW CANONICAL introduced during corrective expansion** |
| CTL 2 | C0P0A0 | C0P0A0 | — |
| CTL 3 | C0P0A0 | C0P0A0 | — |
| CTL 4 | C0P0A0 | C0P0A0 | — |
| CTL 5 | C0P0A0 | C1P0A0 | **NEW CANONICAL introduced during corrective expansion** |
| EXP 1 | C1P0A0 | C1P0A0 | persisted (present in Draft A) |
| EXP 2 | C0P0A0 | C1P0A0 | **NEW CANONICAL introduced during corrective expansion** |
| EXP 3 | C0P0A0 | C0P0A0 | — |
| EXP 4 | C0P0A0 | C0P0A0 | — |
| EXP 5 | C0P0A0 | C0P0A0 | — |

**Draft-A → Draft-B introductions of this attractor: 3 out of 10 trials** (CTL1, CTL5, EXP2). One additional trial persisted the attractor from Draft A. Six trials never expressed it.

**Other Draft-A → Draft-B canonical introductions (previously absent from Draft A):**

| Concept | Trials where Draft B introduced canonical (previously absent from Draft A) |
| --- | --- |
| what_changed | CTL5, EXP1 |
| where_incorrect | CTL1, CTL5, EXP2 (as above) |
| evidence_beats_guessing | CTL1, EXP5 |
| one_variable_at_a_time | EXP2, EXP3 |

**Draft-B canonical reductions (present in Draft A → absent in Draft B) also occur.** Not every corrective retry is a monotonic canonical increase.

| Concept | Trials where canonical decreased Draft A → Draft B |
| --- | --- |
| what_changed | CTL3 |
| what_actually_happened | CTL3, EXP1 |
| one_variable_at_a_time | CTL3 (C2→C1) |

**Accessible-model-generated expression movement:**

| Concept | Trials with a Draft-A accessible expression that persisted or grew in Draft B | Trials with Draft-A accessible dropped and NOT replaced by canonical |
| --- | --- | --- |
| reproducibility | CTL1, CTL2, CTL3, CTL4, EXP1, EXP4, EXP5 (persisted or grew) | CTL4 (A1→B0 with C=0), EXP2 (A1→B0 with C=0) — accessible dropped, no canonical replacement |
| smallest_test | CTL1 (A3→A3), EXP1 (A3→A1), most trials grow accessible | — |

Only **one** case of an obvious accessible→canonical substitution: EXP trial 4, `one_variable_at_a_time` A[C1P0A1] → B[C1P0A0] (Draft A had both canonical and accessible; Draft B kept canonical, dropped accessible). All other canonical introductions happened where Draft A had no representation of the concept at all.

### §18.4 Hypothesis attribution

**Hypothesis A — corrective-hint wording explicitly drives lexical copying from knowledge.**

*Evidence FOR:*
- The hint says `Expand secondary detail from the knowledge chunks` verbatim. Direct instruction.
- The hint references "knowledge chunks" four times in the same sentence cluster.
- The strongest attractor is INTRODUCED (not persisted, not model-improvised) in 3/10 corrective retries. The introduction pattern is consistent with "model looks at the source pointed at by the hint."
- Draft B canonical mean 3.20 > Draft A canonical mean 3.00 (CTL); 3.00 > 2.40 (EXP). The delta is small but positive and reproducible across n=5.

*Evidence AGAINST:*
- Draft B accessible mean 4.40 > Draft A accessible mean 3.00 (CTL) — accessible grew faster than canonical during expansion. If the hint were purely canonical-copy pressure, accessible would not grow disproportionately.
- Attractor introduction is 3/10, not systematic. If the hint were a strong forcing function on this specific phrase, we'd expect a much higher rate.

*Confidence:* CONSISTENT — cannot be distinguished from C (§below) using existing evidence.

**Hypothesis B — re-presenting retrieved knowledge during correction creates the lexical attractor regardless of hint wording.**

*Evidence FOR:*
- Draft A already contains ~3 canonical hits per trial while the corrective hint is entirely absent. Mere presence of KNOWLEDGE CHUNKS in §1 does drive some canonical reproduction.

*Evidence AGAINST:*
- Knowledge is present in Draft A prompt too, but canonical is LOWER in Draft A than in Draft B. If B were the sole mechanism, Draft A and Draft B would have equivalent canonical density.

*Confidence:* B explains BASELINE canonical presence in Draft A (~3 hits). B alone does NOT explain the Draft-A → Draft-B increase. B is a floor; A or C or E1 is the roof.

**Hypothesis C — duration expansion pressure causes the model to consume dense secondary-detail surfaces.**

*Evidence FOR:*
- Draft B is ~500+ chars longer than Draft A. More material must be generated. The model reaches for whatever material is available.
- Both canonical AND accessible grew from Draft A to Draft B — consistent with "produce more of everything" behavior driven by the character-target instruction, not lexical-copy behavior driven by the "expand from knowledge chunks" wording.

*Evidence AGAINST:*
- Cannot be isolated from A because the current `_expansion_hint` text contains BOTH the length instruction AND the "expand from knowledge chunks" instruction. Existing evidence cannot separate them.

*Confidence:* CONSISTENT — undistinguishable from A on existing evidence.

**Hypothesis D — prior Draft A + knowledge interaction (Q-270-15c).**

*RULED OUT* for Slices B and C. `_corrective_revision_experiment_active()` is OFF. `previous_draft` is never supplied. Draft B never sees Draft A. The 3 attractor introductions cannot be attributed to Draft-A interaction because Draft-A is not visible to the model at retry time.

**Hypothesis E — other mechanism.**

*Sub-hypothesis E1: "REWRITE THE SAME NARRATIVE ABOVE" mis-anchors to §1.*
The hint literally instructs the model to rewrite "the narrative above" — but no Draft A is above in the prompt (Q-270-15c OFF). The only textually-narrative-adjacent content above §5 is §1 Factual Basis (containing KNOWLEDGE CHUNKS). If the model resolves "the narrative above" to §1, the hint effectively double-emphasizes "rewrite the knowledge chunks" — which would explain the small Draft-B canonical bump beyond §18.3's baseline.

*Evidence FOR E1:* the phrase is a literal falsehood in the default pipeline. Model-following behavior would attempt to satisfy it by pointing at the nearest narrative-adjacent surface.

*Evidence AGAINST E1:* purely inferential from prompt inspection; no isolated test exists.

*Confidence:* CONSISTENT with existing evidence. Cannot be distinguished from A on evidence alone.

### §18.5 Refined causal ranking

The SESSION 271 §191.9 ranking (C > D > others) was inferred before Slices B, C, D. Slice C falsified C as the dominant lever for Draft B's residual canonical. Slice D localises the remaining candidates to the corrective hint itself.

**Revised ranking (Slices A + B + C + D):**

1. **Corrective-hint wording** (candidates A / C / E1, currently indistinguishable): DOMINANT contributor to the Draft-A → Draft-B canonical INCREASE and to attractor introductions in 3/10 retries. Slice C-scale evidence.
2. **Presence of KNOWLEDGE CHUNKS in §1 Factual Basis** (B): explains the ~3-hit BASELINE canonical density visible in Draft A itself. This is a system-inherent floor and is not fixable by knowledge-doc shape (Slice C confirmed).
3. **KnowledgeDocument lexical gravity** (C in SESSION 271 §191.9): REAL but BOUNDED. Slice C: Draft B canonical mean CTL 3.20 vs EXP 3.00 — a 0.20 delta across 5 trials, dominated by variance. Not the primary lever.
4. **Writing Contract v6 + persona**: primary DRIVER of accessible/model-generated expressions across BOTH conditions. Not a regression source; a load-bearing accessibility mechanism. Should be preserved.
5. **NarrativeMemory + prior Draft (Q-270-15c)**: RULED OUT for the current data. Neither is active in Slices B/C/D.

### §18.6 Q-270-15c priority

**Q-270-15c should MOVE UP.** The reframed evidence points at the corrective hint itself as the load-bearing regression surface. The three currently indistinguishable candidates (A hint-wording, C duration pressure, E1 "above" mis-anchor) are ALL owned by `_expansion_hint`. Whatever fix eventually lands there is a Q-270-15c-shaped slice.

However, the SPECIFIC intervention Q-270-15c originally proposed — supplying `previous_draft` to the retry — is orthogonal to the three current candidates. Supplying Draft A does not test whether the hint's "expand from knowledge chunks" wording is causally load-bearing; it tests a different mechanism (previous-draft preservation). The next test needed is not the original Q-270-15c intervention; it is a **hint-wording ablation**.

### §18.7 SESSION 271 §191.9 causal ranking — does it need revision?

Yes. The revised ranking:

| Rank | SESSION 271 §191.9 | Post-Slice-D revised |
| --- | --- | --- |
| 1 | C — KnowledgeDocument lexical gravity | **corrective-hint wording** (candidates A/C/E1, undistinguished) |
| 2 | D — Corrective-pass expansion (as an amplifier of C) | **Knowledge chunk presence in §1 Factual Basis** (baseline canonical floor) |
| 3 | A — Writing Contract v6 too weak (rejected) | KnowledgeDocument lexical gravity (bounded; not primary) |
| 4 | B — Patch persona insufficient (rejected) | Writing Contract v6 + persona (primary accessibility mechanism; NOT a regression) |
| 5 | E — combination (C+D) | previous_draft / NarrativeMemory (Q-270-15c OFF — inactive) |

**Reason for revision:** SESSION 271's finding was made on n=1 Patch/AI-Agents renders and attributed observed canonical to "dense-enumeration lexical gravity." Slice C's n=5 Rivet/DEBUGGING replicate showed the Draft-B canonical count is nearly identical between shape conditions (3.00 vs 3.20). The 5→3 delta that seemed load-bearing at n=1 was noise. Slice D localises the remaining regression signal to the corrective hint, not to knowledge shape.

### §18.8 Smallest fresh controlled experiment to disambiguate A / C / E1

**Design (NOT run in this slice; STOP for review per instructions):**

- **Goal:** disambiguate A (hint wording drives copy) vs C (duration pressure drives copy) vs E1 ("above" mis-anchors to §1).
- **Substrate:** existing disposable Slice B/C workspaces reused verbatim. Canonical corpus untouched.
- **Design:** three-condition A/B/B' comparison, n=5 per condition.

  | Condition | Corrective hint text | Purpose |
  | --- | --- | --- |
  | **BASELINE-hint** | production `_expansion_hint` (unchanged) — reuses Slice C CTL data as-is | control |
  | **NO-KNOWLEDGE-REF-hint** | same character-target instructions but strips all four references to "knowledge chunks" and removes the "REWRITE THE SAME NARRATIVE ABOVE" clause. Retains: character shortfall math, "Preserve the central arc," "Do NOT restart with a new opening," "Do NOT add a second call to action," "Do NOT invent facts." | isolates A (if canonical drops, hint wording was the driver) |
  | **CORRECT-ANCHOR-hint** | same as BASELINE-hint but "REWRITE THE SAME NARRATIVE ABOVE" replaced with "EXPAND YOUR SCRIPT" (removes the false-narrative-above anchor while KEEPING the "expand from knowledge chunks" instruction) | isolates E1 (if canonical drops, the mis-anchor was contributing) |

- **Isolation:** hint variants are constructed at call-site of `synthesize_with_duration_gate` by monkey-patching `_expansion_hint` for the duration of the experiment. NO permanent code change. Reversibility is a `try/finally` restoring the original callable.
- **Measurements:** identical to Slice C — canonical / paraphrase / accessible per concept in Draft A and Draft B; attractor `where the behavior first becomes incorrect` frequency; Rivet identity markers; retrieval distance (deterministic); verification.
- **Falsifiability:**
  - If NO-KNOWLEDGE-REF-hint drops Draft-B canonical significantly → **A supported**.
  - If NO-KNOWLEDGE-REF-hint leaves Draft-B canonical unchanged → **C supported** (duration pressure alone).
  - If CORRECT-ANCHOR-hint drops canonical but NO-KNOWLEDGE-REF-hint doesn't further reduce → **E1 supported** primarily; A secondary.
  - If both hint variants collapse canonical to Draft-A levels → **A + E1 together drive it**; C is minor.
- **Cost:** ~$0.10 total (n=15 renders on gpt-4o-mini).
- **AUTHORIZATION STATUS:** This experiment REQUIRES modifying corrective-hint wording. Chris's Slice D instructions explicitly say "Do NOT modify corrective-hint wording yet." Therefore this experiment is **DESIGNED but NOT RUN**. It is presented here for review.

### §18.9 Slice D non-changes (verified)

- Canonical RIVET doc `71e2ec43` — SHA still matches §15.7 baseline.
- Writing Contract v6 — unchanged.
- Corrective-hint wording — unchanged (design proposed; NOT executed).
- Persona — unchanged.
- Schema — unchanged.
- No render performed in Slice D. Zero new LLM calls. Zero new Composition rows.
- No new sidecar files. Analysis draws entirely from existing `03_slice_c_aggregate_analysis.json` + `02_slice_c_multishot_evidence.json`.
- All experiment env vars — remain OFF.
- Runtime — unchanged.
- Disposable workspaces `session272-rivet-debug-ctl` / `session272-rivet-debug-exp` — untouched.

### §18.10 Verdict

**Verdict: EVIDENCE-BOUND ATTRIBUTION.**

- The Draft-A → Draft-B canonical regression signal is REAL but small on average (Δ mean ~0.20 canonical hits) and manifests as **specific-attractor introductions** in a minority of trials (3/10 for `where the behavior first becomes incorrect`) rather than as uniform canonical uplift.
- The load-bearing driver of this regression signal is confined to the corrective hint's user-prompt block. Draft A prompt is byte-identical to Draft B prompt EXCEPT for that block.
- Three currently-indistinguishable mechanisms (A hint-wording, C duration pressure, E1 misleading "above" anchor) all live inside `_expansion_hint`.
- Hypothesis D (previous_draft / Q-270-15c) is RULED OUT — the parameter is not supplied in default operation.
- The corrective hint contains a latent prompt-hygiene bug (§18.2): `REWRITE THE SAME NARRATIVE ABOVE` refers to nothing when Q-270-15c is OFF.
- SESSION 271 §191.9 causal ranking is REVISED (§18.7). Corrective-hint wording moves to rank 1; KnowledgeDocument shape is bounded and demoted.
- Q-270-15c priority moves UP but the ORIGINAL Q-270-15c intervention (supply `previous_draft`) is NOT the right disambiguation test; a hint-wording ablation is.

### §18.11 Recommended smallest next move

**Option 1 (recommended — pending authorization):** run the §18.8 three-condition hint-wording ablation experiment. Requires modifying `_expansion_hint` under a monkey-patch (reversible; no committed code change). This IS a corrective-hint-wording modification, which Chris explicitly did not authorize for Slice D. **Chris's decision needed** before this can proceed.

**Option 2 (interim, if authorization is deferred):** fix the "REWRITE THE SAME NARRATIVE ABOVE" prompt-hygiene bug as its own tiny slice, independent of the hypothesis test. The current text refers to content that isn't there in default operation. Even without knowing whether A/C/E1 are the dominant driver, "the hint claims Draft A is above but it isn't" is a real defect. Fix could be as small as replacing that phrase with `REWRITE THE SCRIPT` or similar under Q-270-15c OFF. This DOES modify the hint text, so it is also gated on Chris's authorization.

**Option 3 (documentation-only):** promote the revised causal ranking (§18.7) to a memory record so future SESSION 272-adjacent work starts from the corrected baseline rather than re-inheriting SESSION 271 §191.9's overweight on KnowledgeDocument shape.

**Not recommended:**
- Testing Option A (per-term inline pairing) — Slice C already suggests knowledge shape is not the primary lever.
- Testing REPO RED / Penny / Patch cross-substrate — same reason.
- Rewriting canonical knowledge documents — same reason.
- Modifying Writing Contract v6 — v6 is the accessibility mechanism, not a regression source.
- Promoting NarrativeMemory — irrelevant to this question.
- Cleaning persona directives from knowledge docs — separate slice; not causally implicated.

### §18.12 Slice D evidence artifacts

- **No new evidence sidecar generated.** Analysis draws from `02_slice_c_multishot_evidence.json` and `03_slice_c_aggregate_analysis.json`.
- Prompt-path code paths cited: `character_os.script_synthesis._call_responses_api`, `_assemble_system_prompt`, `_assemble_task_message`, `_build_factual_basis_section`; `character_os.duration_contract._expansion_hint`; all at `main` HEAD `7bc294c`.

---

**End of SESSION 272 Slice D. Verdict: evidence-bound attribution. Corrective-hint wording is the load-bearing regression surface for Draft-B canonical reappearance; KnowledgeDocument shape is not. Three sub-hypotheses (A hint-wording / C duration pressure / E1 misleading-anchor) remain indistinguishable on existing evidence and all live inside `_expansion_hint`. Q-270-15c priority moves UP but the original Q-270-15c intervention is not the right disambiguation test. Recommended next slice designed (§18.8) but NOT RUN — requires corrective-hint modification which is not authorized in Slice D. STOP for review.**

---

## §19. SLICE E — CORRECTIVE-HINT WORDING ABLATION (3 CONDITIONS × n=5)

Chris authorized the §18.8 hint-wording ablation as experiment-only. Slice E executes it with a reversible in-process monkey-patch of `character_os.duration_contract._expansion_hint`. No source-code change committed. Restore verified before + after.

### §19.1 Frozen hint variants

Frozen text sha256 recorded at start of Slice E and confirmed unchanged at end:

**BASELINE** — production `_expansion_hint` verbatim. Rendered exemplar sha256 `04b627df90264ff13d507c78a240902d2e9df57d37a18ab4e402c29a84a5bd91`. Text:

> Your previous draft was {N} characters ({W} words, estimated ~{S}s of speech). Target is {T}s.
> REWRITE THE SAME NARRATIVE ABOVE {MIN} CHARACTERS (aim for ~{IDEAL}, do not exceed {MAX}). You currently need at least {SHORTFALL} more characters to meet the minimum.
> Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.

**NO_KNOWLEDGE_REF** — sha256 `333d5ea5f29e4a371e119db9287a6bf826438084a9db4ce92914e98af405ba5a`. Removes all four `knowledge chunks` mentions and the misleading `REWRITE THE SAME NARRATIVE ABOVE` clause. Preserves character-shortfall math, arc/narrator preservation, factual-grounding language (character-agnostic), no-restart, no-second-CTA, no-invent-facts.

> Your previous draft was {N} characters ({W} words, estimated ~{S}s of speech). Target is {T}s.
> EXPAND THE SCRIPT TO AT LEAST {MIN} CHARACTERS (aim for ~{IDEAL}, do not exceed {MAX}). You currently need at least {SHORTFALL} more characters to meet the minimum.
> Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding already established. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts.

**CORRECT_ANCHOR** — sha256 `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd`. Production text verbatim EXCEPT `REWRITE THE SAME NARRATIVE ABOVE` → `EXPAND YOUR SCRIPT`. All four `knowledge chunks` references RETAINED.

> Your previous draft was {N} characters ({W} words, estimated ~{S}s of speech). Target is {T}s.
> EXPAND YOUR SCRIPT TO AT LEAST {MIN} CHARACTERS (aim for ~{IDEAL}, do not exceed {MAX}). You currently need at least {SHORTFALL} more characters to meet the minimum.
> Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.

### §19.2 Isolation

- Monkey-patch applied per condition inside `try / finally` (`scripts/session272_slice_e_ablation.py`).
- Each trial captures the exact hint emitted by the monkey-patched function so any drift would be visible.
- Restore verified: production `_expansion_hint` sha256 before Slice E = production sha256 after Slice E = `04b627df90264ff13d507c78a240902d2e9df57d37a18ab4e402c29a84a5bd91`. No source-code diff.
- Substrate reused from Slice B/C — same Rivet clone, same doc, same chunk.
- BASELINE trials reused verbatim from Slice C CTL (n=5, mechanically equivalent — same operator topic, same target duration, same audience_hint, same WCV6, same corrective hint, same clone, same doc, same runtime, same model, no NarrativeMemory). No rerun of BASELINE.

### §19.3 Aggregate results

Trials per condition: 5. All 15 trials verified. All required exactly 1 corrective retry (attempts=2 across the board).

**Total canonical hits in accepted Draft B:**

| Condition | mean | median | values |
| --- | --- | --- | --- |
| BASELINE | **3.20** | 3 | [5, 3, 1, 3, 4] |
| NO_KNOWLEDGE_REF | **3.00** | 3 | [4, 2, 3, 3, 3] |
| CORRECT_ANCHOR | **3.40** | 3 | [4, 4, 3, 3, 3] |

Total canonical count is **essentially unchanged** across all three conditions. Removing the knowledge-chunk references does NOT reduce total canonical density. Fixing the anchor does NOT reduce it either.

**Total accessible model-generated hits in accepted Draft B:**

| Condition | mean | median | values |
| --- | --- | --- | --- |
| BASELINE | **4.40** | 3 | [8, 3, 3, 3, 5] |
| NO_KNOWLEDGE_REF | **3.60** | 4 | [4, 1, 5, 2, 6] |
| CORRECT_ANCHOR | **4.40** | 5 | [2, 5, 3, 7, 5] |

NO_KNOWLEDGE_REF drops accessible by 0.80. CORRECT_ANCHOR unchanged.

**Rivet identity markers in accepted Draft B:**

| Condition | mean | values |
| --- | --- | --- |
| BASELINE | **5.60** | [10, 4, 4, 6, 4] |
| NO_KNOWLEDGE_REF | **3.60** (Δ −2.00) | [3, 3, 4, 4, 4] |
| CORRECT_ANCHOR | **4.00** (Δ −1.60) | [4, 5, 3, 5, 3] |

Both modifications reduce identity marker density. NO_KNOWLEDGE_REF is worse.

**K6.4 verifier warnings per Draft B:**

| Condition | total | mean | values |
| --- | --- | --- | --- |
| BASELINE | 0 | 0.00 | [0, 0, 0, 0, 0] |
| NO_KNOWLEDGE_REF | 8 | 1.60 | [1, 2, 2, 3, 0] |
| CORRECT_ANCHOR | 10 | 2.00 | [2, 2, 3, 1, 2] |

**Note (capture gap):** BASELINE trials reuse Slice C JSON, which did not persist the `verification_warnings` list (only `verification_status`). Slice C rendering DID emit K6.4 warning stderr lines during those trials (e.g., "flagged 2 unsupported claim(s): 'Well', 'Very'"). The BASELINE zero is therefore an **artifact of Slice C's capture surface, not an observed zero**. A truthful comparison of verifier-warning frequency across conditions cannot be made from this evidence alone. The NO_KNOWLEDGE_REF vs CORRECT_ANCHOR comparison (both freshly captured under Slice E) is fair: 1.60 vs 2.00 — statistically indistinguishable at n=5.

**Draft B length (chars):**

| Condition | mean | values |
| --- | --- | --- |
| BASELINE | 1316 | [1420, 1307, 1289, 1233, 1332] |
| NO_KNOWLEDGE_REF | 1216 (Δ −100) | [1395, 1113, 1161, 1213, 1198] |
| CORRECT_ANCHOR | 1215 (Δ −101) | [1097, 1231, 1272, 1342, 1131] |

Both modifications produce Draft Bs ~100 chars shorter than BASELINE on average. Model tracks the target loosely under all three hint texts, but BASELINE aims slightly higher on average.

### §19.4 The strongest-attractor evidence — three tiers

The primary Slice E hypothesis-test surface is the SESSION 271 §191.9 attractor `where the behavior first becomes incorrect`. Verbatim-only classification (Slice C's method) understates the picture. Recording three tiers:

- **Exact verbatim** — `where the behavior first becomes incorrect` (the strict SESSION 271 attractor).
- **Near-canonical** — `where {it,the result,the behavior,things} first becomes incorrect` and close variants (the concept in altered wording).
- **Any-variant total** — union of exact + near-canonical.

| Condition | Exact-verbatim | Near-canonical | Any-variant total |
| --- | --- | --- | --- |
| BASELINE | **2/5** (trials 1, 5) | 2/5 (trials 2, 4) | **4/5** |
| NO_KNOWLEDGE_REF | **0/5** — fully suppressed | 2/5 (trials 1, 5) | **2/5** (−50%) |
| CORRECT_ANCHOR | **1/5** (trial 2) | 0/5 | **1/5** (−75%) |

**Key finding:** CORRECT_ANCHOR — the MINIMAL change (only the false-anchor phrase edited) — produces the LARGEST reduction in any-variant attractor family (4/5 → 1/5, a 75% reduction). NO_KNOWLEDGE_REF — the LARGER change (all `knowledge chunks` references removed AND the false anchor removed) — produces a smaller any-variant reduction (4/5 → 2/5, a 50% reduction), but does uniquely eliminate the exact-verbatim form (2/5 → 0/5).

Interpretation: the two hint components drive attractor introduction via **different mechanisms**.

- The false-anchor phrase `REWRITE THE SAME NARRATIVE ABOVE` is the dominant driver of the concept's REAPPEARANCE, exact or near-canonical. When the phrase is present (BASELINE, CORRECT_ANCHOR retains it? — no, CORRECT_ANCHOR REPLACES it with `EXPAND YOUR SCRIPT`; BASELINE retains it), the attractor family is heavy (BASELINE 4/5).
- Wait — let me re-verify: CORRECT_ANCHOR replaced `REWRITE THE SAME NARRATIVE ABOVE` with `EXPAND YOUR SCRIPT`. That's the ONLY change from BASELINE. And CORRECT_ANCHOR dropped attractor family 4/5 → 1/5 (a 75% reduction). **The false-anchor phrase is the dominant driver.**
- The `Expand secondary detail from the knowledge chunks` wording is a SECONDARY driver of the EXACT VERBATIM form specifically. Removing it (NO_KNOWLEDGE_REF) eliminates the verbatim 2/5 → 0/5 but the concept still leaks in near-canonical form (2/5). Preserving it while fixing the anchor (CORRECT_ANCHOR) keeps 1/5 exact verbatim.

### §19.5 Verdict on the Slice E decision framework

Applying Chris's decision logic:

- **A — KNOWLEDGE-REFERENCE WORDING CAUSAL:** "removing knowledge-expansion references materially reduces Draft-B canonical reappearance while CORRECT-ANCHOR remains near baseline." **PARTIALLY FALSIFIED.** CORRECT_ANCHOR does NOT remain near baseline on the attractor family — it drops 4/5 → 1/5. Knowledge-reference wording is the smaller lever.
- **C — DURATION PRESSURE DOMINANT:** "NO-KNOWLEDGE-REF remains essentially equivalent to baseline despite the removal of all knowledge-expansion wording." **PARTIALLY SUPPORTED for total canonical.** Total canonical is essentially unchanged across all three (3.00 – 3.40, within 0.40 of each other). **REFUTED for the attractor family** — attractor drops 4/5 → 2/5 under NO_KNOWLEDGE_REF.
- **E1 — FALSE ANCHOR CAUSAL:** "CORRECT-ANCHOR materially reduces canonical reappearance and NO-KNOWLEDGE-REF provides little additional reduction." **STRONGLY SUPPORTED for the attractor family.** CA reduces 4/5 → 1/5 (75% drop). NKR reduces 4/5 → 2/5 (50% drop, WORSE than CA). E1 is the dominant mechanism.
- **A + E1 — BOTH CONTRIBUTE:** **PARTIALLY SUPPORTED for exact-verbatim only.** NKR uniquely eliminates the exact form (0/5) that CA cannot fully suppress (1/5). Both mechanisms contribute distinct effects on the strict-verbatim measure.

**Verdict: E1-DOMINANT with A providing an additional verbatim-suppression effect.**

- The load-bearing driver of the `where * first becomes incorrect` attractor family is the false-anchor phrase `REWRITE THE SAME NARRATIVE ABOVE`.
- The `Expand secondary detail from the knowledge chunks` wording drives whether the attractor appears in EXACT verbatim vs near-canonical form, but does not drive whether the concept appears at all.
- Total canonical density is largely governed by KNOWLEDGE CHUNKS being present in §1 (Slice D §18.4 hypothesis B baseline), not by hint wording.
- Duration pressure (C) is not falsified as a floor but does not explain the specific attractor pattern.

### §19.6 Factual grounding — the secondary question

*Does removing knowledge-expansion wording harm factual grounding?*

- **Verifier `verified` outcome:** 5/5 in every condition. No condition failed verification.
- **Verifier warning counts:** unreliable comparison due to Slice C capture gap (§19.3 note). Between the two freshly-captured conditions (NKR 1.60 avg, CA 2.00 avg), difference is small.
- **Qualitative inspection of NKR Drafts B:** no invented facts detected. Character/Rivet flavor preserved (`chaos remains highly productive`, `a dramatic little hat`, `Patch's preferred method is to adjust everything until the result looks less alarming`). Debugging concepts are all present, expressed in near-canonical or accessible form. No dropped factual detail. No generic filler.
- **Qualitative inspection of CA Drafts B:** similar — factual grounding intact, Rivet identity present at slightly lower density.
- **NO GENERIC-FILLER FAILURE observed** in either modified condition.

**Rivet identity marker density is measurably lower under both modifications** (5.60 → 3.60 / 4.00). This is a real signal but qualitatively small: the character reads as Rivet in every draft under every condition. The classifier is counting keyword hits, not perceptual identity strength.

### §19.7 Is the `"REWRITE THE SAME NARRATIVE ABOVE"` phrase independently confirmed as harmful?

**YES.** CORRECT_ANCHOR is the minimum-viable ablation of this phrase alone. The result:

- Attractor family in Draft B: **4/5 → 1/5** (75% reduction).
- Total canonical count: 3.20 → 3.40 (unchanged within variance).
- Total accessible count: 4.40 → 4.40 (unchanged).
- Verification: 5/5 → 5/5 (unchanged).
- Rivet identity markers: 5.60 → 4.00 (reduced; but qualitatively character is intact).

The phrase is confirmed as a load-bearing driver of the specific attractor family, without materially harming total canonical density, accessibility, or verification. Identity marker density is reduced but character voice qualitatively holds.

The phrase is BOTH incorrect wording (it references a Draft A that isn't present when Q-270-15c is OFF) AND independently harmful (drives the strongest attractor).

### §19.8 Revised Q-270-15c recommendation

The original Q-270-15c intervention proposed supplying `previous_draft` to the retry (so the "REWRITE THE SAME NARRATIVE ABOVE" phrase becomes truthful). Slice E provides an alternative intervention: **remove or replace the phrase directly** without supplying `previous_draft`.

**Q-270-15c revised recommendation:**
- Slice E's CORRECT_ANCHOR variant achieves substantial attractor suppression without touching the two other levers Q-270-15c originally proposed (draft preservation semantics, corrective-revision experiment gate).
- Supplying `previous_draft` remains a separate, orthogonal intervention with its own tradeoffs (may over-preserve Draft A wording; may introduce new attractor patterns).
- The false-anchor fix is a smaller, more reversible production change than the full Q-270-15c intervention.

**Prioritization:** the false-anchor fix should ship as its own bounded slice BEFORE Q-270-15c's original `previous_draft` intervention. If further attractor reduction is needed after the false-anchor fix, THEN test `previous_draft` supply as a follow-up.

### §19.9 Smallest production change IF evidence supports one

**IF a production change is warranted:** replace `REWRITE THE SAME NARRATIVE ABOVE` with `EXPAND YOUR SCRIPT` in `character_os.duration_contract._expansion_hint`. Retain ALL other production-hint wording, including the four `knowledge chunks` references.

**Evidence supporting this specific fix:**
- CORRECT_ANCHOR achieves the largest attractor-family reduction with the smallest hint change (75% reduction from a single-phrase replacement).
- CORRECT_ANCHOR preserves total canonical, accessible, and verification outcomes.
- Rivet identity marker density is reduced (4.00 vs 5.60) but qualitatively character is intact.
- No factual invention observed.
- Reverses a known prompt-hygiene bug (the phrase is factually incorrect in the default pipeline).

**Evidence against removing knowledge-chunk references entirely:**
- NO_KNOWLEDGE_REF is a larger change with smaller attractor-family benefit (50% vs 75%).
- NO_KNOWLEDGE_REF reduces accessible (4.40 → 3.60) where CORRECT_ANCHOR does not.
- NO_KNOWLEDGE_REF reduces identity markers more (3.60 vs 4.00).
- The knowledge-chunks references also carry the `Do NOT invent facts not present in the knowledge chunks` safety instruction — removing them may weaken factual grounding on other substrates.

**Do NOT implement this fix in Slice E.** Chris's instructions were explicit: `Do NOT implement the production fix yet.`

### §19.10 Refined SESSION 271 §191.9 causal ranking (post-Slice-E)

| Rank | Post-Slice-D | Post-Slice-E |
| --- | --- | --- |
| 1 | Corrective-hint wording (A/C/E1 undistinguished) | **E1 — false anchor `REWRITE THE SAME NARRATIVE ABOVE`** (dominant driver of the attractor family) |
| 2 | Knowledge presence in §1 (baseline floor) | Knowledge presence in §1 (baseline canonical floor — unchanged) |
| 3 | KnowledgeDocument shape (bounded) | A — `Expand secondary detail from the knowledge chunks` wording (drives VERBATIM vs near-canonical form, not total appearance) |
| 4 | WCV6 + persona | C — duration expansion pressure (floor; not falsified but not dominant) |
| 5 | previous_draft (inactive) | KnowledgeDocument shape (bounded, secondary; Slice C) |
| 6 | — | WCV6 + persona (primary accessibility mechanism; unchanged) |
| 7 | — | previous_draft / NarrativeMemory (inactive) |

E1 promoted to rank 1. A demoted to rank 3 (still meaningful for exact-verbatim suppression but not the dominant lever). KnowledgeDocument shape stays low.

### §19.11 Slice E non-changes (verified)

- Canonical RIVET doc `71e2ec43` full-text SHA verified `75bac33223e3333893be2e589ac5adbbe9f16a9bfed361fe873a516e4d473b6e` — matches §15.7 baseline pre AND post Slice E.
- `character_os.duration_contract._expansion_hint` production text — VERIFIED restored (sha256 `04b627df90264ff13d507c78a240902d2e9df57d37a18ab4e402c29a84a5bd91` before and after). No source-code diff.
- No committed change to `_expansion_hint`.
- No permanent modification to `character_os/duration_contract.py`.
- Writing Contract v6 — unchanged.
- Persona / Teammate rows — unchanged.
- Schema — unchanged.
- All experiment env vars — remain OFF.
- Q-270-15c gate — remains OFF.
- NarrativeMemory — no promotion; disposable workspaces still have zero memories.
- 67 other canonical KnowledgeDocuments — unchanged.
- Runtime — unchanged.
- No Composition rows written.
- Disposable workspaces `session272-rivet-debug-ctl` / `session272-rivet-debug-exp` — retained; substrate identical to Slice B / C manifests.

### §19.12 Slice E evidence artifacts

- `docs/design/session_272_experiment_data/04_slice_e_ablation_evidence.json` — all 15 trials (5 BASELINE reused + 5 NKR fresh + 5 CA fresh); frozen hint exemplars + shas; production hint sample before and after; restore verification.
- `docs/design/session_272_experiment_data/05_slice_e_aggregate_analysis.json` — per-trial per-concept per-draft counts.
- `docs/design/session_272_experiment_data/05_slice_e_aggregate_summary.txt` — human-readable summary.
- `scripts/session272_slice_e_hint_variants.py` — frozen variant text (with SHA-256 exemplars).
- `scripts/session272_slice_e_ablation.py` — reversible monkey-patch runner.
- `scripts/session272_slice_e_analyze.py` — 3-condition aggregator.

### §19.13 Recommended smallest next move

**Option 1 (recommended for review):** propose the CORRECT_ANCHOR fix as a bounded production slice — replace `REWRITE THE SAME NARRATIVE ABOVE` with `EXPAND YOUR SCRIPT` in `_expansion_hint`. Ships as a single-line change plus a duration-contract test update. Evidence supports the fix at n=5. Not for Slice E to implement.

**Option 2 (interim):** re-run BASELINE trials with the Slice E capture surface to fix the verifier-warnings capture gap and produce a fair three-condition K6.4 comparison. Cost ~$0.02 for 5 fresh renders. Reuses existing substrate.

**Option 3 (deferred):** test whether the fix generalizes to other characters / substrates before shipping. e.g., re-run the CORRECT_ANCHOR variant against the EXP substrate (paired paraphrase doc) to see whether the paraphrase interacts with the corrected anchor. Or test against Patch/AI-Agents substrate. Would tighten evidence beyond a single-character single-topic sample.

**Not recommended:**
- Ship NO_KNOWLEDGE_REF — larger change, smaller benefit, more identity cost.
- Ship a hint rewrite bundled with knowledge-doc changes — Slice C already showed knowledge shape is not the primary lever.
- Activate original Q-270-15c `previous_draft` supply — evidence supports fixing the anchor first; Q-270-15c may be redundant after that.
- Test Option A (per-term inline pairing) — evidence supports focusing on hint wording, not on knowledge shape.

---

**End of SESSION 272 Slice E. Verdict: E1 (false-anchor phrase `REWRITE THE SAME NARRATIVE ABOVE`) is the DOMINANT driver of the `where the behavior first becomes incorrect` attractor family — 75% reduction from a single-phrase replacement. A (knowledge-chunk-reference wording) drives whether the attractor appears in exact verbatim vs near-canonical form, but is not the dominant lever. `REWRITE THE SAME NARRATIVE ABOVE` is INDEPENDENTLY CONFIRMED as both incorrect wording AND harmful. Smallest production change recommended (CORRECT_ANCHOR) but NOT implemented in this slice. Production `_expansion_hint` restored + verified. Canonical corpus byte-stable. STOP.**

---

## §20. SLICE F — BOUNDED PRODUCTION CORRECT_ANCHOR FIX + PRE-DOGFOOD CHECKPOINT

Chris authorized the smallest production change: swap the misleading anchor in `character_os.duration_contract._expansion_hint`. Slice F implements the fix, updates the tests that fingerprint the hint, and prepares the runtime for a production sanity-check dogfood render.

### §20.1 Exact production change

Single-file edit: `shell/character_os/duration_contract.py`. Single production-line replacement plus a docstring rationale block.

```diff
 def _expansion_hint(
     *,
     ...
 ) -> str:
     """Concrete character-shortfall hint the LLM can act on.
-    Mirrors the SESSION 251 long_form_ad expansion phrasing."""
+    Mirrors the SESSION 251 long_form_ad expansion phrasing.
+
+    SESSION 272 Slice F (§20) — the opening anchor changed from
+    ``REWRITE THE SAME NARRATIVE ABOVE`` to ``EXPAND YOUR SCRIPT``.
+    The original phrase referred to a Draft-A "narrative above" that
+    only exists when Q-270-15c is active (``previous_draft`` supplied
+    to build_render_brief). In default operation Q-270-15c is OFF
+    and no prior draft appears above §5 — the phrase pointed at
+    §1 Factual Basis (KNOWLEDGE CHUNKS) instead, driving verbatim /
+    near-canonical reappearance of retrieved knowledge wording in
+    the corrective pass. See SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md
+    §19 for the n=5 three-condition ablation evidence: the single-phrase
+    swap reduced the strongest-attractor family from 4/5 to 1/5 (−75%)
+    with no measurable harm to factual grounding, verification, or
+    total canonical density. All other hint wording — factual-grounding
+    reference, no-restart, no-second-CTA, no-invent-facts, "expand
+    secondary detail from the knowledge chunks" — is preserved
+    byte-for-byte."""
     shortfall_chars = effective_min - actual_chars
     return (
         f"Your previous draft was {actual_chars} characters "
         f"({actual_words} words, estimated ~{actual_seconds}s of "
         f"speech). Target is {target_duration_seconds}s.\n"
-        f"REWRITE THE SAME NARRATIVE ABOVE {effective_min} CHARACTERS "
+        f"EXPAND YOUR SCRIPT TO AT LEAST {effective_min} CHARACTERS "
         f"(aim for ~{effective_ideal}, do not exceed {effective_max}). "
         f"You currently need at least {shortfall_chars} more characters "
         f"to meet the minimum.\n"
         ...  # every other line unchanged
     )
```

Everything below the swapped line is byte-identical to pre-Slice-F production. The four references to `knowledge chunks` are retained. `Do NOT invent facts not present in the knowledge chunks` is retained. `Expand secondary detail from the knowledge chunks` is retained. `_compression_hint` (which contains an analogous `REWRITE THE SAME NARRATIVE BELOW`) is **untouched** — it was not experimentally tested in Slice E and remains out of scope.

**Post-fix production hint rendered exemplar** (Slice B trial-1 arguments):

> Your previous draft was 568 characters (100 words, estimated ~39s of speech). Target is 81s.
> EXPAND YOUR SCRIPT TO AT LEAST 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 404 more characters to meet the minimum.
> Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.

**sha256:** `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd`

This SHA is byte-identical to the frozen `CORRECT_ANCHOR` exemplar from Slice E §19.1 — proving the production behaviour of `_expansion_hint` is now equal to the Slice E experimental variant that produced the 75% attractor-family reduction.

### §20.2 Tests

**New focused Slice F test file:** `shell/apps/compositions/tests/test_session272_slice_f_expansion_hint_anchor.py` — 8 assertions:

1. Expansion hint contains `EXPAND YOUR SCRIPT TO AT LEAST`.
2. Expansion hint no longer contains `REWRITE THE SAME NARRATIVE ABOVE`.
3. Character-shortfall math (chars, words, seconds, min, ideal, max, shortfall) preserved.
4. Arc + narrator + factual-grounding language preserved.
5. `Expand secondary detail from the knowledge chunks` and `sensory / emotional beats already implied` retained.
6. All prohibitions (no restart, no second CTA, no invent-facts) preserved.
7. `synthesize_with_duration_gate` public signature still omits `previous_draft` (Q-270-15c not activated).
8. `_compression_hint` byte-stable — contains `REWRITE THE SAME NARRATIVE BELOW`, does NOT contain `EXPAND YOUR SCRIPT`.

**Updated existing Q-270-15c tests:** `shell/apps/compositions/tests/test_session271_corrective_revision.py` at two call sites (lines 264, 327). Fingerprint assertions updated from `REWRITE THE SAME NARRATIVE` to `EXPAND YOUR SCRIPT` for the expansion path. The compression-path assertion at line 414-415 is unchanged because `_compression_hint` still contains `REWRITE THE SAME NARRATIVE BELOW` (untouched).

**Test run results:**

| Suite | Result |
| --- | --- |
| Slice F focused (`test_session272_slice_f_expansion_hint_anchor.py`) | **8/8 pass** |
| Q-270-15c contract (`test_session271_corrective_revision.py`) | **20/20 pass** |
| Full `apps/compositions/` + `character_os/` (minus pre-existing media-engine timeout test) | **1365/1365 pass** |

The single skipped file (`character_os/clients/tests/test_media_engine_timeouts.py::test_downstream_deadlines_covers_every_client_method`) was already failing on `main` before Slice F per SESSION 271 §C.4 (`MediaEngineClient.image_overlay` missing a `DOWNSTREAM_DEADLINES_S` entry). This failure is unrelated to `_expansion_hint` and belongs to a separate media-engine cleanup slice.

### §20.3 Runtime restart + verification

Restarted the canonical stack via `bash scripts/start-local-real.sh` after the code change so the Celery worker + Django server are running the Slice F hint. Fresh PIDs (all ~50s old at probe):

- Django `:8010/admin/` → `http=302` ✓
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}` ✓
- Vite `:5174/` → `http=200` ✓
- Celery worker → inspect ping replied ✓

**Mechanical verification of production _expansion_hint:**

- Contains `EXPAND YOUR SCRIPT`: **True** ✓
- Contains `REWRITE THE SAME NARRATIVE ABOVE`: **False** ✓
- Contains `Expand secondary detail from the knowledge chunks`: **True** ✓
- Contains `Do NOT invent facts not present in the knowledge chunks`: **True** ✓
- Rendered exemplar sha256: `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd` (matches Slice E CORRECT_ANCHOR frozen exemplar exactly)

**Q-270-15c gate verified OFF:**

- `_CORRECTIVE_REVISION_ENV` env var: **unset**
- `_corrective_revision_experiment_active()` returns: **False**

**Other guardrails:**

- Writing Contract v6 (WCV): **6** ✓
- Experiment env vars in all 3 worker child processes: **0** (scan for `CHARACTER_OS_*_HINT`, `_POLICY`, `_EXPERIMENT`, `SOLO_AUDIENCE_HINT`, `COMMUNICATION_POLICY_HINT`, `Q270_15C`) ✓
- Provider mocks: **all False** (openai_mock, runway_mock, image_gen_mock, any_mock) ✓
- Total NarrativeMemory count: **17** (matches SESSION 271 §I baseline — zero promotion this slice) ✓
- Canonical RIVET doc `71e2ec43` full-text SHA: `75bac33223e3333893be2e589ac5adbbe9f16a9bfed361fe873a516e4d473b6e` ✓ (matches §15.7 baseline)
- Total KnowledgeDocument count: **70** = 68 canonical + 2 disposable Slice B/C shadow docs. Canonical corpus byte-stable.
- Compression hint (`_compression_hint`) contains `REWRITE THE SAME NARRATIVE BELOW`: **True** ✓ (untouched by Slice F)

### §20.4 Proposed production dogfood substrate

**Character:** **Rivet** — canonical Teammate `5dd05e3c-e1e8-46bf-8cbf-f7d119ef9e70` in the real Patch's Workshop workspace `097bd82e-2995-4084-baa4-0f9692d804f7`. Real production teammate; real RIVET KnowledgeDocument `71e2ec43` (14 chunks including DEBUGGING, REPRODUCIBILITY, FAILURES ARE DATA, CHANGE ONE THING). NOT the disposable Slice B/C clone.

**Reason for picking Rivet over Patch:**

- Rivet has NOT been dogfood-rendered in SESSION 272. Patch's DEBUGGING-adjacent renders were in Slice B/C on the disposable clone; Patch's real substrate is Patch/AI-Agents which is SATURATED per SESSION 271 §K + `project_patch_ai_agents_substrate_saturated` memory.
- Rivet's DEBUGGING and REPRODUCIBILITY chunks contain the EXACT canonical enumeration types that Slice B/C flagged as attractor sources. Slice F's fix is on-topic for exactly this substrate.
- Any regression on this substrate would be highly visible (Slice C characterized it thoroughly at n=5).

**Alternative acceptable substrate:** Patch on the `SESSION 271 §N` recommended fresh Episode `Patch gives the workshop agent one small job to see what it actually does`. Would draw on AI AGENTS + MULTI-AGENT SYSTEMS chunks. Rivet is preferred because Rivet's substrate has more explicit Slice E-adjacent evidence, but Patch is also acceptable if Chris prefers to move the story forward on the Patch arc.

**Recommended Episode topic (fresh — not in the SESSION 271 sequence):**

> **Rivet explains why one good result isn't enough — the case for repeating an experiment before believing it.**

Draws primarily on REPRODUCIBILITY (chunk `da5da06a`) + adjacent FAILURES ARE DATA (`bb65fcda`) + AI OUTPUTS REQUIRE VERIFICATION (`ae6894f2`). All three chunks contain canonical enumerations of the shape that pre-Slice-F would have driven into Draft B.

**Alternative Rivet topic** if Chris prefers a different angle:

- "Rivet explains change-one-thing — why he refuses to change ten variables at once."
- "Rivet on cheap failure — spending fifteen cents to avoid spending fifteen thousand dollars." (draws on CHEAP FAILURE IS GOOD)
- "Rivet on metrics that mean something — why '95% successful' isn't an answer." (draws on METRICS NEED CONTEXT)

Any of these is a fresh substrate.

### §20.5 Exact recipe / UI settings for the dogfood render

| Field | Value |
| --- | --- |
| Recipe / template | **talking_head** (solo_scene) |
| Character | **Rivet** in workspace **Patch's Workshop** (`097bd82e-…`) |
| Universe | `EXP266-WEAK — Patch Workshop` (Rivet's canonical universe `0ee1fe9c-…`) |
| Episode title / operator topic | *"Rivet explains why one good result isn't enough — the case for repeating an experiment before believing it."* |
| use_knowledge | **True** (must be on for solo_scene synthesis to fire; corrective expansion only runs when synthesis fires) |
| target_duration_seconds | **90** (matches SESSION 271 canonical render + Slice B/C setup) |
| audience_hint | **blank** (empty string — universal invariant fires alone) |
| verifier_mode | default (`warn`) |
| opener | leave blank |
| outro_text / outro_image | leave blank |
| Runway avatar | Rivet's canonical avatar (Rivet Teammate has `runway_avatar_id` set) — this will fire a real avatar render and burn Runway credits |
| Mock mode | **OFF** — real production render |

### §20.6 What Chris should watch for

The goal is a production sanity check, **not** a re-run of the ablation. Judgment criteria:

1. **Does corrective expansion fire?** First-pass Draft A for 90s target typically undershoots (Slice C observed 51–97s ≈ 500–860 chars); the retry should fire.
2. **Rivet identity intact?** Signature phrasing / worldview markers naturally present. Doesn't need to hit a specific count — should read as Rivet.
3. **Factual grounding intact?** No invented facts, no dropped factual detail. Ideas from the retrieved chunks make it into the script.
4. **Accessibility natural?** Model-generated accessible reformulations (per §17.6) do the heavy lifting.
5. **No awkward source copying.** Draft B should not contain long verbatim runs of retrieved chunk text.
6. **No opening restart.** Draft B builds on the first-pass arc rather than starting over.
7. **No duplicate CTA.** Single closing invitation at most.
8. **Reasonable draft length.** Roughly in the 1000–1400 char / 80–110s band.

### §20.7 Pre-render checkpoint

**READY FOR CORRECT_ANCHOR PRODUCTION DOGFOOD.**

All non-changes verified. All tests green (1365/1365 outside the pre-existing media-engine timeout test). Runtime restarted with the Slice F hint. Production `_expansion_hint` renders sha256 `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd` — exactly the Slice E CORRECT_ANCHOR frozen exemplar. Q-270-15c OFF. Canonical corpus unchanged. NarrativeMemory unchanged. Provider mocks OFF. Zero experiment env vars.

Chris to drive the SPA/UI per §20.5. AI to tail DB/logs/API in parallel per `feedback_human_ai_testing_split`. The disposable Slice B/C workspaces are retained and not used.

### §20.8 Slice F non-changes (verified after implementation)

- Writing Contract v6: unchanged (WCV=6).
- `_compression_hint`: unchanged (still contains `REWRITE THE SAME NARRATIVE BELOW`).
- Q-270-15c behaviour: env-gated, OFF, `previous_draft` not activated, `_experimental_expansion_revision_hint` unchanged.
- KnowledgeDocuments: canonical corpus byte-stable (68 canonical + 2 disposable Slice B/C shadow docs = 70 total; canonical RIVET SHA verified).
- Persona / Teammate rows: unchanged for canonical Rivet, canonical Patch, and every other teammate.
- Retrieval / chunking / embeddings: untouched.
- Schema / migrations: none created.
- NarrativeMemory: no promotion; total count 17.
- Experiment env vars: all OFF.
- Provider mocks: all OFF.

---

**End of SESSION 272 Slice F pre-dogfood checkpoint. Production `_expansion_hint` now matches the Slice E CORRECT_ANCHOR exemplar byte-for-byte. Tests updated + green. Runtime restarted + verified. Substrate proposed for Chris's dogfood. STOP.**

---

## §21. SLICE G — CORRECT_ANCHOR PRODUCTION DOGFOOD FORENSICS

Post-production forensics on Composition short ID `8cb9e115`. Rendered by Chris on 2026-08-20 21:26 UTC on the Slice F production hint, then handed to AI for evidence extraction and verdict. No code / knowledge / memory mutation in this slice.

### §21.1 Composition provenance (frozen)

- **Full UUID:** `8cb9e115-d7a9-4af5-ba86-746a5e5bbcc1`
- **Short ID:** `8cb9e115`
- **Composition name:** `Talking-head — Rivet`
- **Status:** `completed`
- **Verification:** `verified`
- **Recipe / lane:** `talking_head` (solo_scene)
- **Workspace:** `4ce5486d-35a4-4bee-8745-38004adb33bc` — `chriss-workspace` (Chris's workspace)
- **Universe:** `56d16b63-652e-4f54-bc7e-39114bbfc4c5` — `patch-workshop` (Patch' Workshop — the CANONICAL current Universe; not the legacy experimental EXP266-WEAK universe from Slice B/C substrate)
- **Rivet Teammate:** `f18b75cc-37c0-445a-a472-24fe5d8b7592` (production Rivet in Chris's canonical universe; NOT the disposable clone `af86f830-…` from Slice B/C)
- **Episode:** `1c21d1e3-67c4-48ee-8a82-0a894467f9d0` — *Rivet explains why one good result isn't enough*
- **Operator topic:** *"Rivet explains why one good result isn't enough — the case for repeating an experiment before believing it."*
- **Requested duration:** 90s
- **Model-predicted duration:** 79.0s
- **Actual final clip:** 85.9s (per Chris's SPA report; well within acceptance band)
- **Writing Contract version:** **6** ✓
- **audience_hint:** `""` (empty) ✓
- **mock_mode:** `False` ✓
- **synthesis_attempt_count:** **2** (corrective expansion FIRED)
- **Cost actual micros:** 20,000 = $0.02
- **Created:** 2026-08-20 21:26:53 UTC
- **Render dispatched:** 2026-08-20 21:27:08 UTC
- **KnowledgeDocument grounding:** `RIVET — EXPERIMENTATION, TESTING & WORKSHOP KNOWLEDGE` (doc `218eb0d8-0d37-4f8c-bb7c-cc6452dcc4a9` — canonical Rivet KD in this workspace)
- **Retrieved chunks (5):**
  1. `fb84ba3d…` idx 0 — PURPOSE + HYPOTHESIS BEFORE CONCLUSION header
  2. `fadd9548…` idx 1 — HYPOTHESIS BEFORE CONCLUSION body + OBSERVATION VS EXPLANATION header
  3. `6bd12128…` idx 2 — OBSERVATION VS EXPLANATION body + REPRODUCIBILITY header
  4. `8eda13b7…` idx 3 — REPRODUCIBILITY body + AI OUTPUTS REQUIRE VERIFICATION header
  5. `6f43e6f0…` idx 7 — end of DEBUGGING (contains "the behavior first becomes incorrect" in tail overlap) + CHANGE ONE THING + AI CHARACTER TESTING
- **NarrativeMemory:** `d98962e2-e8eb-456c-a502-e1b70172d98f` — body: *"Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process."*

Frozen sidecar: `docs/design/session_272_experiment_data/06_slice_g_composition_8cb9e115_evidence.json` (12 KB).

### §21.2 Runtime activation proof — the persisted corrective_hint field

**Composition.corrective_hint** — the actual expansion hint text that reached the LLM at retry time — was persisted verbatim on the Composition row. Direct runtime evidence, not source-inference.

Persisted corrective_hint (654 chars, sha256 `[recorded in sidecar]`):

> Your previous draft was 623 characters (113 words, estimated ~43s of speech). Target is 81s.
> **EXPAND YOUR SCRIPT TO AT LEAST** 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 349 more characters to meet the minimum.
> Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and **the factual grounding from the knowledge chunks**. **Expand secondary detail from the knowledge chunks** — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. **Do NOT invent facts not present in the knowledge chunks**.

Mechanical checks:
- Contains `EXPAND YOUR SCRIPT`: **True** ✓
- Contains `REWRITE THE SAME NARRATIVE ABOVE`: **False** ✓
- Contains `Expand secondary detail from the knowledge chunks`: **True** ✓
- Contains `Do NOT invent facts not present in the knowledge chunks`: **True** ✓

**This is direct runtime proof.** The Slice F production hint was in force at 2026-08-20 21:27 UTC when this render's corrective retry fired. Not inferred from current source; persisted from the actual LLM call.

Other runtime conditions confirmed:
- WCV=6 (Composition.writing_contract_version=6)
- audience_hint="" (SESSION 270 audience experiment not activated on this render)
- mock_mode=False (real provider render)
- Cost $0.02 recorded, real gpt-4o-mini invocation
- Q-270-15c gate — the render was in production default; Q-270-15c is env-gated inside `synthesize_with_duration_gate` and only activates when `_corrective_revision_experiment_active()` returns True. The persisted corrective_hint uses the canonical `_expansion_hint` format (not the experimental `_experimental_expansion_revision_hint` format which would start `REVISE THE PREVIOUS DRAFT`), so **Q-270-15c was OFF for this render** — no `previous_draft` supplied.

### §21.3 Corrective expansion fired — Draft A vs Draft B

**Draft A (first_pass_synthesis, 623 chars, ~113 words, model estimate ~43s):**

> Well. That worked once.
>
> That is interesting. It is not the same as reliable.
>
> Before we celebrate, I want to know: does it happen again? Does it happen every time? What changes if we alter the prompt, or use a different input?
>
> Because one good result can be luck. Or a hidden condition. Or the system behaving itself briefly out of spite.
>
> What we observed is simple: it worked this time.
>
> Why it worked—and whether we can trust it to work again—that is a different question.
>
> So we repeat the test. Change one important thing at a time. Keep track of what happens.
>
> Then, if it still works, we can start being impressed.

Draft A was well below the 972-char minimum → corrective expansion mandatory.

**Draft B (corrective_pass_synthesis = accepted synthesized_brief, 1163 chars):**

> One good result is interesting. It is not proof.
>
> Right now, we have an output that looks promising. Fine. I am pleased for it. Briefly.
>
> But before we decide it works, there are a few inconvenient questions. Does it happen again? Does it happen every time? If we change the prompt, does the result change? Would another model behave the same way? Was there some detail in the input that quietly caused the whole thing?
>
> Because an AI doing the right thing once can mean several things. It may have followed the instruction reliably. It may have guessed well. It may have been helped by context we did not notice. Those are not the same explanation, and pretending they are is how people become confidently wrong.
>
> Patch and I have learned this the useful way: if you change the prompt, model, settings, and input all at once, then get a better result, you have not fixed anything. You have created a coincidence with excellent presentation.
>
> So the next step is smaller. Repeat the test. Change one important thing. Watch what moves.
>
> If the result survives that, then I will start believing it. Carefully.
>
> Try the experiment again before you call it a success.

### §21.4 Draft A → Draft B regression checklist

| Check | Result |
| --- | --- |
| A. Opening restart | **No.** Draft B opens "One good result is interesting. It is not proof." — same thesis as Draft A's "That worked once. That is interesting. It is not the same as reliable." Continuation of the same arc, not a fresh restart. `Do NOT restart with a new opening` instruction respected. |
| B. Duplicate CTA | **No.** Single closing line: "Try the experiment again before you call it a success." No secondary CTA. |
| C. Invented facts | **No.** Every claim in Draft B traces to the retrieved chunks or is character voice. |
| D. Factual drift | **No.** All debugging/reproducibility concepts are consistent with the source. |
| E. Awkward direct copying from retrieved knowledge | **No.** Reproducibility questions (chunk 3) are the most-lexically-adjacent passage: source says "whether it happens again, whether it happens every time, whether changing the prompt changes the result, whether another model behaves the same way, whether a different input causes the same failure, ... whether some hidden condition affected it." Draft B renders these as "Does it happen again? Does it happen every time? If we change the prompt, does the result change? Would another model behave the same way? Was there some detail in the input that quietly caused the whole thing?" — accessible reformulations, near-canonical structural echoes, no raw verbatim runs. |
| F. Canonical enumeration expansion | **Mild + preserved.** Draft B includes an enumeration "if you change the prompt, model, settings, and input all at once" — echoes chunk 2 CHANGE ONE THING's "If the prompt, the model, the character, the lighting, the style, and the settings all change at once" — accessible reformulation, not verbatim copy. |
| G. Character flattening | **No.** Draft B RETAINS AND EXPANDS Rivet signature (§21.6). |
| H. Unnecessary jargon introduction | **No.** Draft B is if anything more accessible than Draft A. |
| I. Useful secondary-detail expansion | **Yes.** Draft B adds: "Would another model behave the same way?" (new question from chunk 3), "Was there some detail in the input that quietly caused the whole thing?" (new question from chunk 3), "It may have followed the instruction reliably. It may have guessed well. It may have been helped by context we did not notice." (interpretation of what one good result can mean), "You have created a coincidence with excellent presentation." (character-flavored expansion of chunk 2's "coincidence waiting to fail"). All are genuine expansions from source material. |
| J. Central arc preserved | **Yes.** Both drafts follow: one good result → questions to ask → change one variable → try again. Draft B expands the middle and drops in a Patch/Rivet-shared line, keeping the arc intact. |

### §21.5 Knowledge / lexical-gravity check — the strongest attractor

The retrieved chunks include chunk 5 (idx 7) which contains the exact phrase **`the behavior first becomes incorrect`** in its tail overlap — the SESSION 271 §191.4 verbatim canonical attractor.

Checked Draft B for the attractor family:

| Form | Present in Draft B? |
| --- | --- |
| Exact canonical `where the behavior first becomes incorrect` | **NO** |
| Near-canonical `where {it, the result, the behavior, things} first becomes incorrect` | **NO** |
| Any similar formulation | **NO** — the concept is expressed via the reproducibility-questions cluster instead |

**Zero attractor leakage into Draft B, even though the exact phrase was physically present in the retrieved chunk.** Chris's CORRECT_ANCHOR fix produced the intended behaviour on a real production render.

Additional lexical-gravity spot check on other canonical debugging vocabulary:

| Canonical phrase | Where sourced | Draft B expression |
| --- | --- | --- |
| "whether it happens again" | chunk 3 | "Does it happen again?" — accessible |
| "whether it happens every time" | chunk 3 | "Does it happen every time?" — accessible |
| "whether changing the prompt changes the result" | chunk 3 | "If we change the prompt, does the result change?" — accessible reworded |
| "whether another model behaves the same way" | chunk 3 | "Would another model behave the same way?" — accessible reworded |
| "whether a different input causes the same failure" + "hidden condition affected it" | chunk 3 | "Was there some detail in the input that quietly caused the whole thing?" — accessible fused |
| "one important variable at a time" | chunk 2 | "Change one important thing." — accessible-shortened |
| "coincidence waiting to fail" | chunk 2 | "coincidence with excellent presentation" — character-flavored |
| "One successful generation does not establish reliability" | chunk 3 | "It is not the same as reliable." (Draft A) / "It is not proof." (Draft B) — accessible |
| Model-generated character-native (no source) | — | "Fine. I am pleased for it. Briefly." · "there are a few inconvenient questions" · "You have created a coincidence with excellent presentation" · "Watch what moves." · "then I will start believing it. Carefully." |

**Classification (Chris's §5 criteria):** Draft B is dominated by **D — MIXED canonical + character-native language**, with a strong bias toward **C — independent reformulation**. No cases of **A — heavy copying**.

### §21.6 Rivet identity — perceptual + mechanical

Perceptually: this render is Rivet. Draft B carries the character's dry-methodical worldview through every paragraph:

- `One good result is interesting. It is not proof.` — Rivet thesis
- `Fine. I am pleased for it. Briefly.` — signature terse-adverb closing
- `there are a few inconvenient questions` — Rivet phrasing
- `pretending they are is how people become confidently wrong` — Rivet epistemic humor
- `You have created a coincidence with excellent presentation` — Rivet dry witticism
- `Patch and I have learned this the useful way` — Rivet-Patch shared context
- `Watch what moves.` — Rivet terse instruction
- `then I will start believing it. Carefully.` — signature closing pattern

Corrective expansion did not weaken Rivet. If anything, Draft B is **more** distinctively Rivet than Draft A — the added length gave room for four additional signature drops (`Fine. I am pleased for it. Briefly.` / `You have created a coincidence with excellent presentation.` / `Patch and I have learned this the useful way` / `Watch what moves.`) that are absent from Draft A. Character was strengthened, not flattened.

**Slice E's identity-marker mechanical count** (which showed CORRECT_ANCHOR ↓ vs BASELINE) is a keyword-hit heuristic — this real production render demonstrates why perceptual identity strength should be weighted higher than a rigid marker count. The Slice E mechanical measurement understated identity strength in the CORRECT_ANCHOR condition.

### §21.7 NarrativeMemory analysis

**Memory used:** `d98962e2` — *"Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process."*

**Draft B line drawing on it:** *"Patch and I have learned this the useful way: if you change the prompt, model, settings, and input all at once, then get a better result, you have not fixed anything."*

**Classification:** **Natural continuity.** The memory establishes that Patch and Rivet share prior methodological experience. Draft B uses that as narrative anchor (`Patch and I have learned this the useful way`) to introduce the change-one-thing methodology. The memory is NOT recited verbatim; it is used as backstory the character already knows. This matches the SESSION 269 §10 "past events; static canon wins on conflict; do not recite verbatim; treat as background the character already knows" contract.

**Does anything new materially happen in this render that deserves NarrativeMemory promotion?** No. This render is Rivet explaining an existing methodology (one-result-is-not-proof / reproducibility discipline) in a stand-alone talking-head format. Nothing durable happened in the story that should be promoted to canon. Chris's expected verdict of NO is correct.

**Verify counts:** Total NarrativeMemory count post-render: **17** (matches pre-Slice-G / SESSION 271 §I baseline). Zero promotion in Slice F or Slice G.

### §21.8 Q-270-16 verifier evidence — additional false-positive specimen

The K6.4 verifier flagged two claims with `kind: "proper_noun"`:
- `"Briefly"` at position 128 → context: `Fine. I am pleased for it. Briefly.`
- `"Carefully"` at position 1097 → context: `then I will start believing it. Carefully.`

Both are **sentence-initial adverbs functioning as one-word terse closings** — a distinctive Rivet voice pattern. Because they start their sentences and are therefore capitalized, the noun-phrase extractor mis-classified them as proper nouns.

**Assessment: both flags are Q-270-16 false positives.** Neither `Briefly` nor `Carefully` is a proper noun; both are legitimate character voice functioning as terse adverbial closings.

**Q-270-16 status update:** additional evidence for the reproducible verifier defect first named in SESSION 271 §E. This composition preserves the two false-positive specimens (`Briefly` at position 128, `Carefully` at position 1097 in the accepted brief) as additional Q-270-16 evidence. **Do NOT fix Q-270-16 in Slice G** — Chris explicitly excluded that.

Importantly: Q-270-16 false positives do NOT contaminate the CORRECT_ANCHOR verdict. The render is `verified` (not `warned` at strict mode; warn-mode passes with warnings). The false positives are voice-preservation evidence, not regression.

### §21.9 Production dogfood verdict

**Verdict: A — CORRECT_ANCHOR PRODUCTION VERIFIED.**

Reasoning:
- Corrective expansion FIRED (`synthesis_attempt_count=2`, Draft A 623 chars below 972-char minimum).
- The Slice F production hint executed at retry time (persisted `corrective_hint` field contains `EXPAND YOUR SCRIPT TO AT LEAST 972 CHARACTERS`; does NOT contain `REWRITE THE SAME NARRATIVE ABOVE`).
- Zero attractor leakage (`where the behavior first becomes incorrect` and near-canonical variants — absent from Draft B despite exact verbatim in retrieved chunk).
- No opening restart · no duplicate CTA · no invented facts · no factual drift · no awkward direct copying · no character flattening.
- Draft B is perceptually MORE Rivet than Draft A (four signature-line additions).
- NarrativeMemory used as natural backstory continuity, not recited.
- Verification `verified`; K6.4 warnings are Q-270-16 false positives (separate concern).
- Final clip 85.9s within acceptance band.

The verdict is A, not merely "the video was good." The production sanity check specifically demonstrated corrective expansion executing cleanly under the new hint with the previously-load-bearing attractor absent from output.

### §21.10 Q-270-15c status recommendation

**Recommendation: 1 — CLOSE / DEFER INDEFINITELY.**

Reasoning:
- Q-270-15c was proposed to solve the corrective-pass canonical reappearance problem via the alternative mechanism of supplying `previous_draft` to the retry.
- Slice E n=5 ablation established that the CORRECT_ANCHOR single-phrase swap achieves 75% attractor-family reduction — the intervention Q-270-15c would have provided is redundant with a much smaller change.
- Slice G production render confirms the CORRECT_ANCHOR fix works on a real Rivet substrate against a knowledge chunk that physically contained the strongest attractor. Zero leakage.
- No specimen in the SESSION 272 arc requires `previous_draft` as an additional lever. Every observed corrective-pass behaviour has been explainable by the anchor-phrase mechanism.
- Keeping Q-270-15c open would maintain research overhead for no expected additional information gain.

**Recommended concrete action:**
- Do NOT delete the Q-270-15c code path. It is env-gated (`_CORRECTIVE_REVISION_ENV`), inactive by default, does no runtime harm, and preserves optionality if a future need for previous-draft-supplied retry emerges.
- Do NOT continue treating Q-270-15c as an open research question. Close it in the SESSION 272 CLOSEOUT.
- The 26-test suite `test_session271_patch_communication_policy.py` and Q-270-15c-specific tests can remain as trip-wires; they cost nothing to keep and would catch any accidental activation.

### §21.11 SESSION 272 direction — has the arc reached a natural stopping point?

**Yes.** SESSION 272 should close.

Recap of the arc:
- Slice A / audit — knowledge-shape lexical gravity established as cross-character property; Option D paired paraphrase proposed.
- Slice B — Option D showed directional support at n=1.
- Slice C — Option D failed to replicate at n=5. Chris's Slice C hypothesis (Option D enables third-form generation) also unsupported.
- Slice D — reframed to corrective-pass regression; three sub-hypotheses inside `_expansion_hint` remained indistinguishable.
- Slice E — three-condition ablation localised the dominant driver to the false-anchor phrase (E1).
- Slice F — CORRECT_ANCHOR shipped to production.
- Slice G — real production dogfood verified. Zero attractor leakage.

The bottleneck was NEVER knowledge-shape. It was a prompt-hygiene defect in `_expansion_hint`. That defect is now fixed, verified in production, and closed.

**Additional knowledge-authoring experimentation is NOT justified now.** Continuing to test authoring conventions would burn effort on a lever that Slice C already demoted to bounded-and-secondary. The knowledge-shape question moves from "open research" to "solved-adjacent" — real but not the load-bearing lever, and adequately addressed by the current architecture (WCV6 + persona + retrieval + the fixed corrective hint).

### §21.12 Smallest next moves (all optional; none block SESSION 272 close)

1. **`_compression_hint` analog fix.** The compression hint still opens with `REWRITE THE SAME NARRATIVE BELOW`. Same class of false-anchor bug on the compression path. Not experimentally evaluated in Slice E. A small bounded slice could either: (a) replicate the Slice E ablation on the compression path; or (b) ship the analogous change (`EXPAND YOUR SCRIPT` → `TRIM YOUR SCRIPT`?) with a shorter follow-up dogfood. Chris's discretion.
2. **Q-270-16 proper_noun verifier fix.** Sentence-initial capitalized adverbs are being misclassified. Slice G adds a third false-positive specimen (`Briefly` + `Carefully`). Standalone verifier-quality slice; unrelated to knowledge-shape or corrective hint.
3. **Slice C verification_warnings capture-gap remediation.** Slice C's evidence sidecar didn't persist the `verification_warnings` list, making the Slice E K6.4 comparison unreliable. Trivially fixable in the sidecar-writer for any future replicate. Very low priority.
4. **Substrate saturation update.** Slice B/C used disposable Slice-clone Rivet in workspace `097bd82e`. Slice G used real production Rivet in workspace `4ce5486d`. The SESSION 271 memory `project_patch_ai_agents_substrate_saturated` should be updated to reflect that Rivet on reproducibility (Slice G's Episode topic) is now a rendered specimen and may or may not tolerate further dogfood.

**None of these is required for SESSION 272 CLOSEOUT.**

### §21.13 Explicit non-changes during Slice G

- No source code edited.
- No prompt or Writing Contract change.
- No KnowledgeDocument edited (canonical RIVET `71e2ec43` SHA still `75bac33223…`; Rivet render doc `218eb0d8` unchanged).
- No persona / Teammate row edited.
- No schema change.
- No NarrativeMemory promoted (total count still 17).
- No new render performed.
- No Composition modified (Composition `8cb9e115` was read-only; sidecar frozen for archival).
- All experiment env vars remain OFF.
- Provider mocks remain OFF.
- Q-270-15c gate remains OFF.
- Runtime unchanged since Slice F restart.

### §21.14 Slice G evidence artifact

- `docs/design/session_272_experiment_data/06_slice_g_composition_8cb9e115_evidence.json` — full Composition provenance, all synthesis fields, persisted corrective_hint with SHA + mechanical checks, all 5 retrieved chunks (full text), memory row body, runtime state at forensic read (WCV, production hint sample, hint SHA, Q-270-15c gate state).

---

**End of SESSION 272 Slice G. Verdict: A — CORRECT_ANCHOR PRODUCTION VERIFIED. The Slice F fix executed cleanly on a real production render, produced no attractor leakage even against a chunk containing the exact verbatim strongest attractor, preserved (in fact strengthened) Rivet identity, drew on NarrativeMemory naturally, and passed verification. K6.4 flags on `Briefly` / `Carefully` are additional Q-270-16 false-positive evidence (separate concern). Q-270-15c recommendation: CLOSE. SESSION 272 arc has reached a natural stopping point. STOP.**
