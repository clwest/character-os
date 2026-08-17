---
title: "Short-form dialogue watchability audit (read-only)"
status: draft — audit + design proposal, no code
date: 2026-08-16
companion_docs:
  - "design/DIALOGUE_SCENE_AI_TOPIC_V1.md"
  - "handoffs/SESSION_258_P1_P2_CONCURRENCY_AND_PARALLELISM.md"
---

# Short-form dialogue watchability audit

Post-P2 read-only investigation. Question from operator, watching
composition `9e4601c7`: the dialogue is grounded, in-character, and
coherent, but it sometimes sounds like two characters **explaining
their methodology** rather than a scene someone would stop scrolling
to watch.

This audit inspects every real dialogue transcript in the arc, the
K2 chunks surfaced during retrieval, the Writing Contract text, the
dialogue synthesis prompt architecture, and the SPA topic UI — then
answers the operator's 8 questions and proposes a **behavioral
contract** delta that keeps the system general (never Patch/Rivet-
specific).

No code changes. No provider calls. No prompt/K2/contract edits.

---

## Evidence — every real dialogue composition in the arc

Sorted by watchability (operator's spec: a scene someone would stop
scrolling to watch). Sequential quotation preserved so shape is
visible.

### High-watchability

**`8ed5c47a` — "Victory lap time: it worked."**  (10 turns, Patch primary)
```
[0] patch: Victory lap time: it worked.
[1] rivet: Once. A demonstration is not automatically proof. How did we
           define success, and how many times did we observe it?
[2] patch: It did the thing. Mostly. Look, for a first swing, that's a
           win in my book.
[3] rivet: I would classify at least part of that as aggressively
           incorrect. That is not what we asked it to do.
...
[9] rivet: Annoyingly sensible. Run it again.
```
Opens with a situation. Rivet's "Once." carries a full beat in one
word. Turn lengths vary (2 → 40 words). Ends on a specific reaction.

**`f7ccbe98` — "Rivet, I created something amazing."**  (10 turns, Patch primary)
```
[0] patch: Rivet, I created something amazing.
[1] rivet: Define amazing. Preferably with fewer adjectives and more
           evidence.
[2] patch: I built an AI spokesperson for our projects. Gave it a
           personality...
[3] rivet: Hypothesis and smallest test?
...
[8] patch: Deal. If it calls you "Rivets" again, we're adding a swear jar.
[9] rivet: I vote we start with a name whitelist. Then: run it again.
```
Real situation → real challenge → real specifics → decision + callback
joke. Rivet's methodology surfaces through **short question turns**
("Hypothesis and smallest test?"), not recitation.

**`da200b30` — "Idea: give the workshop a tiny AI floor manager for one hour."**  (9 turns, Patch primary)
```
[0] patch: Idea: give the workshop a tiny AI floor manager for one
           hour. One character. Two tools. See if it can actually run
           a shift.
[1] rivet: Define "run a shift." If it posts motivational quotes, I
           refuse to applaud.
[2] patch: Smallest test: it gets a to-do list tool and a timer...
[3] rivet: Success criteria?
[4] patch: At least three tasks attempted, clear logs for each, one
           honest "I don't know" escalation...
...
[7] rivet: Prediction: it escalates immediately.
[8] patch: Great. Then we learn what to teach it. Build first. Find out.
```
Proposal → specific pushback → negotiation → clear ending prediction.

**`3d664922` — "Patch and Rivet test"**  (6 turns, Patch primary, earliest)
```
[0] patch: Rivet, good news. I figured out why the experiment failed.
[1] rivet: You changed six things at once and accidentally discovered
           which five weren't the problem?
[2] patch: Okay, first of all, it was only four things. Second,
           technically... it works now.
[3] rivet: You saying "technically" is why we no longer have a ceiling
           fan.
[4] patch: So... run it again?
```
Situation → deflation → walk-back → callback → decision. All turns
under 40 words, most under 20.

### Middle

**`5e74323f` — "I built you to make the workshop smarter" (AI-D5)**  (8 turns)
Opens mildly explanatory but stays scene-shaped through the middle
("You keep us moving. Sometimes into a metaphorical wall.") and ends
on "aggressively incorrect." Explanation and behavior coexist.

**`671d1464` — Mike + Repo Red**  (6 turns, Mike primary)
Different cast, different dynamic — collaborative rather than
skeptical-vs-enthusiast. Both characters propose specific tactics
("one topic per video"; "quick drill: '520 score. One repo. Six weeks
on the job.'"). Reads more like a **content-planning meeting than a
scene**, but every turn cites a concrete tactic. Not exposition-
heavy; not laugh-out-loud watchable either. Genuinely different
cast dynamics, worth preserving as a data point.

### Low-watchability (the operator's flagged failure mode)

**`9e4601c7` — "Patch tries to explain why he built Rivet…" (P2 dogfood)**  (8 turns)
```
[0] patch: I built you to make the workshop better: fewer messes,
           faster builds, smarter tests. Basically, turn my "what
           if" into "here's what happened."
[1] rivet: And yet I spend most of my time fixing the thing you just
           turned on without warning.
[2] patch: Because we learn more when it almost works. You keep us
           honest. I try the weird idea; you keep it from becoming
           a bad headline.
[3] rivet: My job is simple: define the test, build the smallest
           version, observe, measure, and repeat. Curiosity is good.
           Evidence is better.
[4] patch: Which is why we use the same playbook: what are we trying,
           why might it work, what's the smallest test, what
           actually happened, what broke, and do we keep building?
[5] rivet: Also: separate assumptions from results. A dramatic demo
           is not proof. If it works once, interesting. If it works
           three times, now we talk.
[6] patch: And when it fails, that's the fun part. We poke the weird
           behavior until it explains itself, then try again without
           the explosion.
[7] rivet: Annoyingly accurate. You bring momentum. I bring the
           checklist. Together we get answers. Interesting. Run
           that again.
```
Turns [3]–[6] read like a TEDx panel. Turn [4] literally lists the
six-step framework from Patch's K2. Turn [5] recites Rivet's
philosophy. Turn lengths are uniformly 90–140 chars. Ends on a
mutual synthesis, not a reveal.

---

## Question-by-question answers

### 1. Which lines feel like CHARACTER BEHAVIOR / SCENE ACTION?

Every line that either **reports a specific event** or **reacts to
a specific event** with a POV-tagged response. Examples across the
arc:

- "Victory lap time: it worked." (reports)
- "Once." (reacts with deflation)
- "You changed six things at once and accidentally discovered which
  five weren't the problem?" (reacts with a specific correction)
- "Define amazing. Preferably with fewer adjectives and more
  evidence." (reacts with a challenge)
- "If it posts motivational quotes, I refuse to applaud." (reacts
  with a specific complaint)
- "Prediction: it escalates immediately." (specific bet)
- "If it calls you 'Rivets' again, we're adding a swear jar." (specific
  callback + humor)

Shape: **specific noun** + **first-person stance** + **short**.

### 2. Which lines feel like EXPOSITION / KNOWLEDGE RECITATION?

Lines that describe a **method, process, philosophy, or general
motivation** without a triggering situation. Examples from
`9e4601c7`:

- "My job is simple: define the test, build the smallest version,
  observe, measure, and repeat."  (recites Rivet's K2 responsibilities)
- "Which is why we use the same playbook: what are we trying, why
  might it work, what's the smallest test, what actually happened,
  what broke, and do we keep building?"  (recites Patch's K2
  EXPERIMENT FRAMEWORK numbered list)
- "You bring momentum. I bring the checklist. Together we get
  answers."  (self-summary, no situation)
- "I built you to make the workshop better: fewer messes, faster
  builds, smarter tests."  (general motivation, no triggering event)

Shape: **plural nouns** ("assumptions", "results", "answers") +
**process verbs** ("define", "measure", "repeat") + **paragraph-
length**.

### 3. What prompt/knowledge signals cause characters to explain their methodology?

Ranked by evidence:

1. **Operator topic phrasing.** "Patch tries to **explain why** he
   built Rivet…" instructs the model to write explanation. Contrast:
   "Rivet, I created something amazing." + "Victory lap time: it
   worked." — those are in-scene lines that produce in-scene
   dialogue. **Highest-signal driver.**
2. **K2 chunks that ARE frameworks.** Patch's corpus contains an
   "EXPERIMENT FRAMEWORK" block with a numbered list ("1. WHAT ARE
   WE TRYING? 2. WHY MIGHT THIS WORK? …"). When retrieval surfaces
   this AND the topic asks for explanation, the model literally
   quotes the framework as a character line (see turn [4] of
   `9e4601c7`).
3. **§1 Factual Basis rule.** The prompt says *"Every factual claim
   in the script must trace back to content in this section. If a
   fact isn't in this section, leave it out."* This creates PRESSURE
   to cite chunks explicitly rather than let them shape behavior
   implicitly.
4. **No anti-pattern against framework recitation.** The Dialogue
   Writing Contract prohibits self-description ("As a beaver
   inventor…"), forced greetings, forced alternation, and mutual
   agreement. But nothing prohibits **naming your process out loud**
   or **enumerating your responsibilities**.
5. **Character schema has no OBJECTIVE / IMMEDIATE-GOAL field.** §2
   Character Voice defines *how* a character talks. Nothing defines
   *what a character wants right now*. So the model gives each
   character a talking style but no goal — and characters without
   goals default to describing themselves.

### 4. How much comes from each layer?

Rough attribution based on the 7 transcripts + prompt inspection:

| Signal | Contribution |
|---|---|
| Operator topic wording | ~40% |
| K2 chunk shape (framework-heavy content) | ~25% |
| Writing Contract silence on "in-scene stance" | ~15% |
| §1 "trace back to chunks" pressure | ~10% |
| Character Voice with no OBJECTIVE field | ~10% |

The topic layer is the single largest lever. This matters because
**changing the topic wording changes the output more than changing
any single line of contract**. The operator's UI is currently
inviting exposition.

### 5. Does Rivet's K2 containing dialogue/behavior guidance amplify the problem?

**Mixed.** Rivet's K2 contains BOTH:

- Framework-y content: `RIVET PHILOSOPHY` (curiosity → evidence →
  failure → repetition), a bulleted `PURPOSE` block listing
  Testing / Observation / Measurement / Debugging / Verification.
  This IS methodology.
- Scene-ready content: `TWO-CHARACTER RHYTHM` with example
  exchanges ("PATCH: I built an AI spokesperson. RIVET: You built
  three."), failure reactions ("Well. That's new." / "I would
  classify that as aggressively incorrect."), the "Rivet does not
  kill curiosity" block.

On the P2 topic, retrieval surfaced the framework chunks over the
example-exchange chunks. On the earlier "Victory lap" and "I
created something amazing" topics, retrieval clearly surfaced (or
the model just tapped into) the example-exchange chunks — "aggressively
incorrect" appears verbatim in `8ed5c47a`. So the K2 content is not
the bug on its own; **topic wording steers which slice of K2 the
model leans on**.

### 6. Are Patch + Rivet being prompted to demonstrate expertise rather than pursue conflicting goals?

**Yes, in the topic phrasing specifically.** A prompt that says
"Patch tries to **explain** why…" frames both characters as
demonstrators. A prompt that says "Rivet, I created something
amazing" gives Patch an implicit goal (impress Rivet) that Rivet
immediately opposes (require evidence). The dialogue then organizes
around the collision.

The **Writing Contract** does not prescribe expertise-demonstration
— its anti-patterns already lean the other way. But nothing in the
prompt gives either character an **immediate objective** for THIS
scene. Without a goal, the model defaults to "have these characters
introduce themselves through what they know."

### 7. What differentiates the most watchable scenes from the least watchable?

Cross-transcript pattern (`8ed5c47a`, `f7ccbe98`, `da200b30`,
`3d664922` vs. the middle turns of `9e4601c7`):

| Watchable | Less watchable |
|---|---|
| Opens with a SPECIFIC SITUATION or PROPOSAL | Opens with a general motivation |
| Turn 1 is often <20 words (deflation / question / correction) | Turn 1 is 80–140 chars (matched to turn 0's length) |
| Turn lengths vary dramatically (2 words → 40 words) | Turn lengths uniform (~90–140 chars each) |
| Contains at least one **specific noun** the audience can picture (ceiling fan, motivational quotes, "Rivets", swear jar) | Uses abstract plurals ("assumptions", "answers", "results") |
| Ends on a REACTION / DECISION / CALLBACK / SPECIFIC PREDICTION | Ends on a mutual synthesis ("Together we get answers") |
| Characters WANT different things this scene | Characters DEMONSTRATE their methods |
| Knowledge influences behavior implicitly | Knowledge is quoted verbatim |
| Rivet's process shows up in **short questions** ("Success criteria?", "Hypothesis and smallest test?") | Rivet's process shows up as a **paragraph** ("define the test, build the smallest version…") |

### 8. How do successful short-form comedy/dialogue structures map onto our architecture without becoming a rigid template?

The existing `_DIALOGUE_NARRATIVE_SHAPES_BLOCK` already lists eight
shapes (setup → disagreement → payoff; question → answer → correction;
etc.) and says "pick whichever fits, no mandatory skeleton." That's
the right philosophy — **do not add a required skeleton**.

What's missing is a **behavior-oriented layer above the narrative
shapes** that describes what should be true of every scene regardless
of which shape is chosen. Successful short-form video dialogue —
regardless of subgenre — shares these traits:

1. Both characters **want** something at the moment the scene opens.
2. The scene contains a **change** — one character learns / concedes
   / discovers / decides / escalates.
3. The scene ends on a **reaction, reveal, callback, decision, or
   escalation** — not a summary.
4. The audience can **name at least one specific thing** by the end
   (an object, a proper noun, a number, a bet, a decision).
5. Turn lengths **vary materially**. Very short turns are load-
   bearing.

These are behavior-checkable properties, not template constraints.
They compose with the existing narrative-shapes list without
overwriting it.

---

## Proposed behavioral contract (delta on top of `_DIALOGUE_INVARIANTS_BLOCK`)

Not proposed as a rewrite — as an *addition* to the existing 9
invariants + 5 anti-patterns. Keeps the general "no rigid skeleton"
philosophy intact.

### New invariants (proposed)

> **10. Characters enter a scene wanting something.** Each character
> arrives with a stance, an objective, an opinion to defend, or a
> reaction to a specific event. "I'm here to demonstrate my
> methodology" is not a stance — that's exposition. A character
> without a goal for THIS scene should not speak.
>
> **11. The scene contains a change.** By the end, at least one
> character has: conceded a point, changed their mind, learned
> something they didn't know, decided to act, escalated, or been
> convinced. If no character moves, the scene didn't happen.
>
> **12. Ground the scene in specifics.** At least one specific noun
> the audience can picture — a proper noun, a number, an object, a
> named event, a concrete outcome. Abstract plurals ("assumptions,"
> "results," "answers") are not specifics.
>
> **13. Knowledge influences behavior, not vocabulary.** Character
> knowledge should shape what a character **notices**, **questions**,
> or **objects to** — not become a line they read aloud. Do not
> enumerate a framework, list responsibilities, or narrate a
> philosophy. If a character has a six-step process, they demonstrate
> step 3 in this scene without naming the process.
>
> **14. End on a reaction, reveal, callback, decision, or
> escalation.** Not a synthesis, not a mutual agreement, not a
> philosophical statement. The last turn should give the audience
> something specific to react to.

### New anti-patterns (proposed)

> * Do NOT enumerate a numbered or bulleted framework as dialogue.
>   Frameworks live in your knowledge; they do not live in your
>   mouth. A character listing "define the test, build the smallest
>   version, observe, measure, and repeat" has stepped out of the
>   scene and into a slide deck.
> * Do NOT summarize your own role. "I bring the checklist" /
>   "You bring momentum" / "My job is simple: X, Y, Z" is self-
>   description dressed as dialogue.
> * Do NOT end on mutual synthesis. "Together we get answers." /
>   "That's how we do it." / "Great teamwork." are ending stubs
>   the model reaches for when no reveal was set up.

None of these are Patch/Rivet-specific — they apply equally to
Mike + Repo Red, to a solo talking_head that ever became a dialogue,
or to a hypothetical third cast.

---

## Where each proposed delta belongs (in the pipeline)

Not all rules land in the same layer. Ranked by leverage per byte
of change:

### A. Writing Contract (dialogue shape) — **primary place for behavioral rules**

**Invariants 10, 11, 12, 13, 14 + all three anti-patterns.** They
belong here because they're properties of dialogue as a form,
independent of who's speaking. This is where existing prohibitions
live ("do not force alternation," "do not force jokes"), and the
model already reads this block for every scene.

Byte impact: ~2 KB added to the ~9 KB dialogue contract. Well
within LLM prompt budget.

### B. §1 Factual Basis (dialogue-shaped) — **soften the "cite chunk" pressure**

The current instruction *"Every factual claim in the script must
trace back to content in this section"* is load-bearing for K6.4
fact-check and should not be removed. But it can be **paired** with
a companion instruction that specifically distinguishes facts (which
must trace back) from behaviors (which need not be quoted):

> Knowledge chunks provide FACTS your character may cite. They also
> describe HOW your character thinks — those descriptions should
> influence what your character notices, questions, or reacts to in
> this scene, but should NOT be spoken aloud. Never quote a
> framework, philosophy, purpose statement, or responsibility list
> as a character line.

Byte impact: ~400 bytes added.

### C. Character Voice (§2) — **add an implicit objective**

Optional but high-leverage. The current §2 fields (tone, personality,
POV, signature phrases) describe HOW a character sounds. None
describe WHAT a character wants. Adding a per-scene **objective**
field to the Teammate model would let operators set (or let
synthesis derive from the topic):

> "In every scene, Patch WANTS to try the weird idea. Rivet WANTS
> Patch's experiment to be measurable before it happens."

This is model-level, not per-composition — the character's
persistent desire, not a scene-specific mission.

Byte impact per prompt: ~200 bytes. Model schema impact: 1 field.
Deferred until (A) and (B) prove insufficient.

### D. SPA topic UI copy — **operator-facing framing**

Current dialogue_scene topic field:
- Label: "What's the scene about?"
- Help: "One or two sentences describing the scene. Character OS
  writes both sides of the conversation from this."

Both invite **description**. Description invites exposition.

Proposed alternatives (pick one):
- Label: **"What's happening in this scene?"** or **"What just
  happened?"** or **"The moment we walk in on…"**
- Help text add: **"The strongest topics name a specific event or
  opening line. Try 'Rivet, I created something amazing' or 'Victory
  lap time: it worked' rather than 'Patch and Rivet discuss AI.'"**

Byte impact: ~200 bytes of copy change.

### E. `_build_task_section` (§5) — **transform the topic before injection** (optional)

The synthesis wrapper could detect topic patterns that read as
description ("X explains…", "X and Y discuss…", "X talks about…")
and **prepend** a shape hint:

> INTERPRETATION: this topic is describing the scene FROM OUTSIDE.
> Do not repeat the description. Instead, generate an opening
> moment that fits it (a specific line one character says, an
> event that just occurred, a question one character is asking)
> and let the scene unfold from there.

This is more invasive than (A)–(D). Deferred as a Phase-2 lever if
(A) + (B) + (D) don't move the needle enough.

Byte impact: 0 (adds nothing to the prompt for well-formed topics);
~600 bytes for description-shaped topics.

---

## Smallest safe implementation slice

**One slice, all in the Writing Contract.** Ship (A) alone; leave
everything else for later iterations.

Rationale: (A) is the highest-leverage low-risk lever. The
`_dialogue_scene_contract()` function is a pure string builder with
no callers outside the synthesis wrapper. Adding invariants 10–14
and three anti-patterns is a single-file text change with no
schema, no migration, no UI, no API. The change is easy to A/B
against the current output on the same seven transcripts (dogfood
each once with the new contract, compare side-by-side).

Impact if it works: the operator's flagged failure mode
(`9e4601c7`-style methodology recitation) disappears without
tightening any other lever.

Impact if it doesn't: no correctness regression, cost unchanged,
easy revert (single commit). We then layer (B) or (D) or both.

**Explicitly NOT in the smallest slice**:
- No Character Voice schema change (deferred until (A) proves
  insufficient).
- No SPA copy change (operator UX not the blocker for the first
  test).
- No prompt-transformation in `_build_task_section` (too invasive
  as a first move).
- No new K2 chunks, no chunk pruning, no re-embedding.

Bumps `WRITING_CONTRACT_VERSION` 2 → 3. Persistent per-composition
version stamping already exists (SESSION 257 AI-D1), so audit trail
for "before vs after" is free.

---

## Dogfood protocol for the proposed contract change

Two runs, same operator inputs, real Runway + real OpenAI. Compare
side-by-side.

### Fixture composition
- Primary: Patch (dogfood cast — quality failures are obvious).
- Secondary: Rivet.
- Mode: AI Topic.
- Target duration: 60 seconds.
- Use workspace knowledge: ON.
- Fact-check: WARN.
- Opening line: blank.
- Outro: blank.
- Mock: OFF.

### Topic A — description-shaped (reproduces the P2 failure mode)
```
Patch tries to explain why he built Rivet to improve the workshop,
while Rivet points out that he spends most of his time fixing
Patch's experiments.
```

### Topic B — situation-shaped (already known to work well)
```
Rivet, I created something amazing.
```

### Runs
1. Contract v2 baseline (current) — Topic A. **Reference**:
   `9e4601c7` already exists; no re-render needed unless the
   comparison window has drifted.
2. Contract v3 (proposed) — Topic A. **Primary evidence** for the
   fix. Same failure-prone topic; different contract.
3. Contract v3 — Topic B. **Regression check.** Topic B already
   produced watchable output under v2 (`f7ccbe98`); v3 must not
   regress it.

### Accept criteria
- Run 2 produces zero framework-quoting turns (validator or
  hand-check: no dialogue turn contains a numbered list, a bulleted
  list, or the phrase "my job is" / "I bring" / "you bring").
- Run 2 ends on a reaction / reveal / decision / callback — not a
  synthesis line.
- Run 2 turn lengths vary by ≥ 3× between shortest and longest turn
  (baseline `9e4601c7` uniformity ratio is 1.6×; watchable scenes
  range 5×–20×).
- Run 3 remains as watchable as `f7ccbe98` under subjective read.
- Zero cost regression (still 8 × 2 credits ≈ 16 for a 60s scene).
- P2 parallel path continues to work (no dispatch or coordinator
  changes involved).

### Failure stops
- If v3 introduces new anti-patterns not seen under v2 (e.g., the
  model over-corrects and produces cryptic one-word scenes across
  the board), stop after Run 2 and iterate the contract text
  rather than re-firing paid renders.
- If v3 breaks the K6.4 fact-check pipeline (verification_status
  drops from `verified` to `rejected` under fact-check WARN), stop
  and inspect — the "influence but don't quote" clause may have
  accidentally weakened factual citation.

---

## Explicit non-goals

- Not making the system Patch/Rivet-specific. Every proposed
  invariant/anti-pattern is cast-independent.
- Not enforcing conflict when the cast/topic calls for
  collaboration. Invariant 11 asks for a *change*, which can be
  collaborative (one character teaches the other) as easily as
  adversarial. Mike + Repo Red should still work.
- Not adding a rigid skeleton. The existing "pick whichever
  narrative shape fits" language stays. The new invariants apply
  regardless of chosen shape.
- Not forcing jokes. Invariant 6 ("humor emerges from interaction")
  stays; new invariants don't ask for humor.
- Not making the model briefer. Some scenes need longer turns —
  invariant 12 says lengths must **vary**, not that all turns must
  be short.

## Deferred / not in this pass

- Character-level per-scene OBJECTIVE field (option C).
- SPA topic UI copy revision (option D).
- Topic-transformation logic in `_build_task_section` (option E).
- K2 pruning / re-chunking (out of scope; would require
  re-embedding and separate testing infrastructure).
- Any change to the sequential runner, the parallel path, K6.4
  fact-check, or the primitive registry.

If option (A) alone lands the target quality, none of these need
to happen. If option (A) closes half the gap, (B) or (D) become
the natural next slices — each still one file, no schema
migration, no UI redesign.
