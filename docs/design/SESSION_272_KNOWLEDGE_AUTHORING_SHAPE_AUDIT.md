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

**End of SESSION 272 knowledge-authoring/knowledge-shape audit. Documentation-only. No implementation. Next slice: RIVET DEBUGGING shadow-doc experiment per §11.2 — separate slice, subsequent SESSION 272 turn.**
