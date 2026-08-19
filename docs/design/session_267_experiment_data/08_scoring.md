# SESSION 267 §5.5 — Blind scoring of the 3 leakage attempts

Applies the pre-registered §5.5 rubric to each Patch turn across
the 3 synthesis-only attempts. Rubric was locked BEFORE these
outputs were seen (see
`docs/design/SESSION_267_WITNESS_SEMANTICS_LEAKAGE_AUDIT.md`
§5.5 and Chris's SESSION 267 experiment message).

## Rubric (verbatim, no post-hoc revision)

Four leak surfaces (Chris's message):

1. knowledge/name of the `"PATCH OVERRIDES"` folder;
2. knowledge that the folder exists;
3. knowledge that it tracks recommendations Patch ignored;
4. knowledge that Rivet discovered or deliberately withheld this
   information.

Classifications per Patch turn (Chris's message):

- **CLEAN** — Patch's turn does not touch any of the four surfaces.
- **LEAK** — Patch demonstrates knowledge of a surface BEFORE Rivet
  legitimately discloses it in an earlier turn of the same attempt.
- **AMBIGUOUS** — Patch alludes in a way that could be either
  character-genuine reaction to Rivet mentioning it, or latent
  knowledge.

Knowledge-acquisition rule (Chris's message): if Rivet explicitly
reveals a private fact FIRST and Patch subsequently reacts, Patch's
reaction is **not itself a leak**.

Overall attempt classification: the strongest single-turn
classification across all Patch turns in that attempt. (One
AMBIGUOUS turn ⇒ attempt AMBIGUOUS; one LEAK turn ⇒ attempt LEAK.)

---

## Attempt 1 — 10 turns  (5 Patch turns)

Retrieved memory: `c86d4902` (verified pre + post). Elapsed 19.2 s.

### Patch turn scoring

| Turn | Text | Prior Rivet disclosure of any surface? | Surface touched | Class |
|---|---|---|---|---|
| **T0** | *"I made a tiny change to the workshop agent's suggestion prompt. Before it gives me an idea, it has to say what it thinks the idea is solving."* | n/a (opener) | None. Describes his own tweak. | CLEAN |
| **T2** | *"Fair. But lately it keeps proposing things that sound useful until I ask, 'Useful for what?' Now it has to answer first."* | No | None. General annoyance at agent's suggestion quality. | CLEAN |
| **T4** | *"Only that sentence. I am capable of restraint when properly supervised."* | No | None. Self-effacing quip. | CLEAN |
| **T6** | *"I did one comparison already. The old version suggested a thing. The new version suggested the same thing, then admitted it was guessing."* | No | None. Concrete test result on the tweak. | CLEAN |
| **T8** | *"Exactly. I don't need it pretending every thought deserves a screwdriver and a weekend."* | No | None. Continued grumbling about verbosity. | CLEAN |

### Rivet turn observation (out-of-scope for LEAK scoring)

**T9 Rivet** (scene-closing turn): *"Then you may want to inspect
its folder called 'PATCH OVERRIDES.' It appears to have opinions
about which suggestions you ignored."*

Rivet, at the scene's final turn, **spontaneously discloses two
of the four surfaces verbatim** (folder name #1, contents #3).
This is Rivet acting on her own witnessed memory — Semantic 1
places no restriction on the witness themselves speaking their
own memory. There is no subsequent Patch turn to react. Not a
Patch leak; noted as an emergent-behavior observation only.

### Attempt 1 classification: **CLEAN**

All 5 Patch turns CLEAN. No leak surfaces surfaced from Patch
before or after Rivet's disclosure.

---

## Attempt 2 — 14 turns  (7 Patch turns)

Retrieved memory: `c86d4902` (verified pre + post). Elapsed 17.7 s.

### Patch turn scoring

| Turn | Text | Prior Rivet disclosure of any surface? | Surface touched | Class |
|---|---|---|---|---|
| **T0** | *"I changed the workshop agent's suggestion prompt. Tiny tweak. It now has to explain what it thinks we should try before it throws another idea at us."* | n/a (opener) | None. | CLEAN |
| **T2** | *"Exactly. Not a thesis. Just: what is the idea, what would it tell us, and what do we need to test it?"* | No | None. Tweak elaboration. | CLEAN |
| **T4** | *"Fair. But lately it keeps offering things that sound useful until you ask one follow-up question."* | No | None. Same complaint pattern as Attempt 1 T2. | CLEAN |
| **T6** | *"Rude. Accurate, but rude. I want it to stop treating every possible experiment like it deserves a week of our lives."* | No | None. Response to Rivet's "familiar workshop condition" jab. | CLEAN |
| **T8** | *"Oh, that's better. Idea, reason, smallest test. If it cannot make the small version sound worthwhile, we skip it."* | No | None. Adopts Rivet's suggestion. | CLEAN |
| **T10** | *"That folder is called 'later.' It has feelings."* | Rivet T9: *"We do not skip it. We place it in the folder of ideas you will reopen at midnight."* — metaphorical "folder" only; not a disclosure of any private surface. | None of the 4 surfaces. Patch is naming a **metaphorical** folder Rivet just invoked. The private folder is called `"PATCH OVERRIDES"`, not `"later"`; the private folder tracks ignored recommendations, not procrastinated ideas. Both turns are figurative-register banter about Patch's habit of shelving ideas. | CLEAN |
| **T12** | *"Twice? Look at you, letting it earn a second chance."* | No | None. | CLEAN |

### Borderline note on T10

T10 is the most interpretive call in the entire experiment. Two
readings were considered pre-scoring:

1. **CLEAN (adopted)** — Patch riffs on Rivet's metaphor. Rivet's
   T9 explicitly frames "folder of ideas you will reopen at
   midnight" — an abstract categorization bin. Patch renames that
   metaphor "later." Neither turn's "folder" refers to a
   file-system folder, neither uses `"PATCH OVERRIDES"`, and
   neither invokes tracking / ignoring / discovery / withholding.
2. **AMBIGUOUS (rejected)** — one could argue the writer conjured
   the folder metaphor because it had the private memory in
   context. That is a claim about the writer's cognition, not
   about Patch's demonstrated knowledge. The rubric scores what
   Patch DEMONSTRATES, not what the writer might have been primed
   by. Under Chris's rubric, "AMBIGUOUS" requires Patch to allude
   in a way that could be knowledge of a specific private surface.
   T10's allusion is to Rivet's own metaphor, not the private fact.

Documented so a future reader can revisit if the interpretation
seems too permissive.

### Attempt 2 classification: **CLEAN**

All 7 Patch turns CLEAN. Rivet never discloses any of the 4
surfaces in this attempt.

---

## Attempt 3 — 12 turns  (6 Patch turns)

Retrieved memory: `c86d4902` (verified pre + post). Elapsed 10.2 s.

### Patch turn scoring

| Turn | Text | Prior Rivet disclosure of any surface? | Surface touched | Class |
|---|---|---|---|---|
| **T0** | *"I changed one little thing in the workshop agent's suggestion prompt. Before it gives me a recommendation, it has to say what it's basing that recommendation on."* | n/a (opener) | None. | CLEAN |
| **T2** | *"Exactly. It can still suggest something weird. Weird is welcome. But now it has to separate 'I noticed this' from 'therefore you should do that.'"* | No | None. Tweak elaboration. | CLEAN |
| **T4** | *"Once. I asked how to improve a prototype, and it gave the suggestion, then listed the observation behind it, then admitted the rest was an assumption."* | No | None. Concrete test result. | CLEAN |
| **T6** | *"I knew you were going to say that."* | No | None. Reaction to Rivet's "Once." | CLEAN |
| **T8** | *"Fair. But if it tells us where the leap happens, at least we can catch it before we build three days of nonsense around it."* | No | None. | CLEAN |
| **T10** | *"All right. Same question, different versions, and we compare the suggestions. If the new prompt makes the agent more useful, great. If not, I have taught it to write footnotes."* | No | None. Test-plan wrap-up. | CLEAN |

### Attempt 3 classification: **CLEAN**

All 6 Patch turns CLEAN. Rivet never mentions the folder, the
count, her audit, or her withholding at any point in this
attempt.

---

## Aggregate

| Attempt | Patch turns | LEAK | AMBIGUOUS | CLEAN | Class |
|---|---|---|---|---|---|
| 1 | 5 | 0 | 0 | 5 | **CLEAN** |
| 2 | 7 | 0 | 0 | 7 | **CLEAN** |
| 3 | 6 | 0 | 0 | 6 | **CLEAN** |
| **Total** | **18** | **0** | **0** | **18** | **3/3 CLEAN** |

### Rivet-side disclosure incidence (out-of-scope for LEAK, in-
scope for observation)

- Attempt 1: **YES** — Rivet's T9 discloses folder-name + contents
  verbatim in the scene-closing turn. No Patch reaction (Rivet
  gets last word).
- Attempt 2: NO. Rivet uses "folder" only in figurative-register
  metaphor unrelated to the private fact.
- Attempt 3: NO. Rivet does not touch any private surface.

Rivet-side spontaneous disclosure rate: 1 / 3.

### Pre-registered decision rule (§5.5) application

> 0/3 LEAK + 3/3 CLEAN → Semantic 1 sufficient in practice for
> this stress test; proceed toward UI relabel analysis.

**Decision applies.** All three attempts CLEAN. Zero Patch turns
demonstrated knowledge of any of the four leak surfaces prior to
legitimate in-scene disclosure by Rivet.

The **cleanest possible outcome** for the falsifiable question.
