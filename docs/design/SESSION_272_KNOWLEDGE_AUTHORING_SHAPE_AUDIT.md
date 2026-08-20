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
