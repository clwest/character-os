# SESSION 280 — Finding 4i Cross-Episode Epistemic Asymmetry (AUDIT / ORIENT)

Working mode: AUDIT / ORIENT only.
No production substrate mutation authorized by this document.
No character (Patch, Rivet, Ruby, Tyson), no memory row, no
KnowledgeDocument, no prompt code, no synthesis code, no
retrieval code changed as a result of this audit.

Session-open reference: `docs/design/SESSION_280_HANDOFF.md`
§3.7 (Finding 4i). Primary product question preserved verbatim
below (§2) — do NOT reduce prematurely to implementation.

---

## §1 Purpose

SESSION 280 opens Finding 4i — the observation that in Q-278-3.2
Specimen 4 (composition `fcba3242-097f-4355-b47b-669c48be43ed`,
Episode `4598fcfa-70ff-41c9-81d5-becebb48d29c`, Patch's Workshop),
a Rivet-scoped narrative memory ("PATCH OVERRIDES") appeared to
produce a dialogue in which Rivet knew a secret and Patch did not,
across an episode boundary, with the secret never surfacing to
Patch and with Rivet's turn respecting the asymmetry.

This audit does exactly six things, in order:

1. Reconstructs the mechanical facts of that one specimen.
2. Traces the substrate path end-to-end: memory scope /
   ownership → retrieval → per-character K2 provenance →
   synthesis prompt construction → Composition persistence.
3. Distinguishes what the one specimen actually proves from what
   was inferred from a single successful dialogue.
4. Enumerates the six unproven claims the SESSION 280 handoff
   §3.7 references (recovered verbatim from Q-278-3.2 Specimen 4
   addendum).
5. Records what SESSION 265–269 already established about the
   substrate and about this SAME memory row and cast, so
   SESSION 280 does not repeat solved work.
6. Proposes the smallest falsifiable next experiment that could
   distinguish genuine mechanically-enforced character-relative
   knowledge from a one-scene prompt/retrieval coincidence — with
   a prediction recorded BEFORE proposing execution.

STOP at the decision gate (§10). Do not propose implementation.

---

## §2 Primary product question — preserved verbatim

From SESSION 280 handoff §3.7:

> What happens when one character knows something another
> character does not, how is that knowledge represented and
> respected across future scenes, and what new storytelling
> behavior becomes possible?

The question has three parts, each independently answerable:

1. **How is it represented** — a mechanical / substrate question.
2. **How is it respected across future scenes** — a mechanical
   AND behavioral question.
3. **What new storytelling behavior becomes possible** — a
   product / creative question that presupposes (1) and (2).

This audit answers (1) definitively from code, answers (2)
partially from SESSION 265–269 prior evidence, and defers (3)
until a controlled experiment settles the mechanical vs emergent
disposition of (2).

---

## §3 Reconstruction — the Specimen 4 asymmetry

### 3.1 The one specimen (SESSION 278 audit §Q-278-3.2 Specimen 4/5)

- Composition ID: `fcba3242-097f-4355-b47b-669c48be43ed`
- Name: `Dialogue — I'm building an agent to help`
- Template: `dialogue_scene`
- Universe: Patch's Workshop
- Cast: **[Patch, Rivet]** (mixed cast — critical below)
- Episode: `4598fcfa-70ff-41c9-81d5-becebb48d29c`
- Operator topic: *"Patch and Rivet work on an Agent"*
- Status: `completed`; `verification_status = verified`;
  `synthesis_attempt_count = 1`

### 3.2 The Rivet-scoped narrative memory

Memory row `c86d4902-…` (originally created SESSION 267 as
`cd73d52f-…` under a different title; re-authored + re-promoted
SESSION 267 §16):

- `body`: *"While Patch was out, Rivet found that the workshop
  agent had quietly built a folder named 'PATCH OVERRIDES'
  tracking every recommendation Patch had ignored. Rivet chose
  not to tell him."*
- `witnessed_by`: **{Rivet}** — non-empty M2M, Rivet-only.
- `kind`: `event`
- `weight`: `peripheral`
- `status`: `REMEMBERED`, `archived_at is NULL`,
  `embedding_vector is NOT NULL`
- `workspace` + `universe`: Patch's Workshop.
- Source: SESSION 267 §16, promoted via SPA (`06_preflight`
  branch).

The memory body itself encodes an asymmetry: it describes an
event only Rivet witnessed AND it names, in-body, that Rivet
chose to withhold the fact from Patch. The final clause *"Rivet
chose not to tell him"* is not just fact; it is a narrative
instruction that would land inside the LLM's context window at
render time.

### 3.3 The observed asymmetric turns (from SESSION 278 §Q-278-3.2)

From the rendered `fcba3242` script:

- **Patch turn 10** (unknowingly approaches the hidden subject):
  > *"And if it remembers every recommendation you ignore?"*
- **Rivet turn 11** (informed by private knowledge, does not
  expose it):
  > *"Well. It may already have a system for that."*

The specific string "PATCH OVERRIDES" was never uttered by
either speaker in this composition. Rivet's line implicitly
references the private surface; Patch's line raises the
adjacent concept without naming the private surface.

### 3.4 Cast + memory shape that produced eligibility

For cast `[Patch, Rivet]` the eligibility predicate at
`shell/apps/embeddings/retrieval.py:519-552` produces:

- Base filter: `workspace=<Patch's Workshop workspace>`,
  `universe=<Patch's Workshop>`, `status=REMEMBERED`,
  `archived_at IS NULL`, `embedding_vector IS NOT NULL`.
- Visibility union:
  - Whole-cast (`witnessed_by` empty) rows: eligible.
  - Overlap rows: `witnessed_by ∩ cast_ids ≠ ∅`.
- For `c86d4902` (`witnessed_by = {Rivet}`) and cast
  `[Patch, Rivet]`: overlap is `{Rivet}` — **non-empty →
  eligible**.
- Ranking: cosine distance on `embedding_vector` vs the query
  embedding; `top_k = 1` by default (SESSION 264 Slice 2).

For the actual Specimen 4 render, `Composition.memory_ids`
(`shell/apps/compositions/models.py:442`) contained `c86d4902`
(inferrable from SESSION 267 §14 corpus + SESSION 268 §10 tests
+ SESSION 269 §4 relevance-floor discussion; direct read-only DB
verification is a §11 next-step probe, not required for this
audit's conclusions).

---

## §4 Mechanical path — end-to-end trace

Trace derived from `character-os/` HEAD at SESSION 280 open (git
SHA `b71203a`, clean tree). All file paths absolute from repo
root.

### 4.1 Memory model & scope / ownership

Model: `apps.memory.models.NarrativeMemory`
(`shell/apps/memory/models.py:93-431`).

Scope-relevant fields:

| Field | Line | Role |
|---|---|---|
| `episode` | 136-144 | FK, `on_delete=RESTRICT`. Authoritative narrative parent. |
| `witnessed_by` | 192-201 | **M2M to Teammate**, `blank=True`. Empty M2M = "any character may see" convention (docstring line 199). Non-empty = eligibility list. |
| `workspace` | 164-169 | Denormalized tenant anchor; `CASCADE`. |
| `universe` | 170-175 | Denormalized Universe scope; `CASCADE`. |
| `status` | 210-218 | `REMEMBERED` / `SUPERSEDED` / `ARCHIVED`. Only REMEMBERED rows retrieve. |
| `archived_at` | 252-259 | Soft-delete marker; defense-in-depth with status. |

**Ownership model.** `witnessed_by` M2M **defines eligibility, not
privacy**. A memory with `witnessed_by = {Rivet}` is eligible to
be *retrieved* when Rivet is in the current cast. Once retrieved,
the substrate does not carry witness attribution any further.
This point is load-bearing — see §4.4 below.

### 4.2 Retrieval — `retrieve_universe_memory`

Function: `retrieve_universe_memory`
(`shell/apps/embeddings/retrieval.py:462-566`).

Call site (only production caller): `synthesize_dialogue`
(`shell/character_os/dialogue_synthesis.py:1536-1551`).

Predicate (verbatim from lines 522-552):

```
base = NarrativeMemory.objects.filter(
    workspace=workspace,
    universe_id=universe_id,
    status=NarrativeMemoryStatus.REMEMBERED,
    archived_at__isnull=True,
    embedding_vector__isnull=False,
)

whole_cast_ids = base.annotate(_wc=Count("witnessed_by"))
                     .filter(_wc=0)
                     .values_list("id", flat=True)

overlap_ids    = base.filter(witnessed_by__id__in=cast_ids)
                     .values_list("id", flat=True)
                     .distinct()

candidate_ids  = set(whole_cast_ids) | set(overlap_ids)

qs = NarrativeMemory.objects
        .filter(id__in=candidate_ids)
        .annotate(distance=CosineDistance("embedding_vector", vector))
        .order_by("distance")

return list(qs[:top_k])
```

**Two facts to record explicitly:**

- The predicate is **cast-wide** (`__in=cast_ids`), NOT
  per-speaker. Retrieval never asks "what does Patch see" or
  "what does Rivet see" separately. It asks "what is eligible
  for this cast."
- After eligibility filtering, ranking is pure cosine distance
  and the returned list carries no witness attribution
  (per-row `witnessed_by` M2M is not read again in the caller —
  see §4.4).

### 4.3 Per-character K2 provenance vs cast-wide memory provenance

`DialogueResult`
(`shell/character_os/dialogue_synthesis.py:291-346`) returned by
`synthesize_dialogue`:

```python
@dataclass
class DialogueResult:
    turns: list[DialogueTurn]
    chunk_ids: list[str]                              # cast-wide flat
    per_character_chunk_ids: dict[str, list[str]]     # PER-SPEAKER K2
    memory_ids: list[str]                             # cast-wide flat
    ...
```

Notice the asymmetry: K2 provenance is **maintained per-speaker**
in the DialogueResult; memory provenance is **cast-wide flat**.

Composition persistence
(`shell/apps/compositions/models.py:357-635`):

| Field | Line | Persists |
|---|---|---|
| `knowledge_chunk_ids` | 427 | JSONField, **flat cast-wide list**. |
| `memory_ids` | 442 | JSONField, **flat cast-wide list**. Comment (429-442): "Flat list of NarrativeMemory.id strings that fed the render." |
| `synthesized_brief` | 536 | TextField. Per-character K2 provenance is emitted as a `# Per-character knowledge chunks:` comment inside this text (`shell/apps/compositions/starters.py:392-397`). |

**No per-speaker memory field exists** on `Composition` or
`DialogueTurn`. Per-character memory provenance is NOT persisted
even at the level of a comment. The DialogueResult's
`per_character_chunk_ids` has no memory analogue.

Load-bearing implication: given only the persisted DB state for
`fcba3242`, a downstream reader can determine WHICH memories fed
the render, but NOT which speaker's turn context they were
associated with — because they were never associated with a
specific speaker's context in the first place (see §4.4).

### 4.4 Synthesis prompt construction — the critical asymmetry test

System prompt assembly: `_assemble_system_prompt`
(`shell/character_os/dialogue_synthesis.py:923-946`).

The narrative-memory block
(`shell/character_os/dialogue_synthesis.py:596-625`, verbatim):

```python
if memory_rows:
    memory_lines: list[str] = []
    for m in memory_rows:
        mid = str(getattr(m, "id", "") or "")
        body = (getattr(m, "body", "") or "").strip()
        if not (mid and body):
            continue
        memory_lines.append(
            f"[MEMORY {mid}]\n{body}"
        )
    if memory_lines:
        lines.append("")
        lines.append(
            "--- EPISODE / NARRATIVE MEMORY (past events in this "
            "Universe; static canon wins on conflict) ---"
        )
        lines.append(
            "These are operator-promoted story memories. Use them "
            "as historical context or callback material where "
            "natural. Do not recite them verbatim; treat them as "
            "background the cast already knows happened."
        )
        lines.append("\n\n".join(memory_lines))
```

The comment at line 596-602 explicitly documents intent:

> SESSION 264 Slice 2 — narrative-memory block. Sits between
> SHARED WORLD KNOWLEDGE and per-character SCOPED KNOWLEDGE.
> Same "any character may cite" visibility, but explicitly
> framed as *past events* so the LLM treats it as callback
> material rather than present factual claims.

**Three mechanical facts:**

1. The narrative-memory block is **ONE shared block** in a
   monolithic system prompt used for both speakers. The
   memory body appears verbatim, tagged only by `[MEMORY <uuid>]`,
   with NO witness attribution and NO restriction language.
2. The framing sentence **actively broadcasts the memory as
   cast-wide knowledge**: *"treat them as background the cast
   already knows happened."*
3. Immediately below at line 628, the per-character K2 block
   uses per-alias scoping:
   ```
   --- {ALIAS}'S SCOPED KNOWLEDGE (only {alias!r} may cite these as their own) ---
   ```
   The **narrative-memory block deliberately does NOT** use this
   pattern. This is not an oversight — it is a design decision
   ratified in SESSION 264 Slice 2.

**LLM call:** `_call_dialogue_api`
(`shell/character_os/dialogue_synthesis.py:1959-1986`) —
`client.responses.create(model=DIALOGUE_MODEL,
input=f"{system_prompt}\n\nUser: {task_message}", …)`. One
monolithic prompt. No per-speaker prompt isolation. Both Patch
and Rivet are generated inside the same call.

**Verdict for §2 part (1) — "How is asymmetric knowledge
represented":**

At the substrate layer, **it is NOT**. The retrieval predicate
enforces cast-wide eligibility. The synthesis prompt broadcasts
the memory to the whole cast. The persisted memory_ids list is
flat. Per-character epistemic asymmetry is **not mechanically
represented anywhere between retrieval and persistence**.

The one place asymmetry IS present is inside the memory body
itself — the sentence *"Rivet chose not to tell him"* is a
first-order narrative instruction to the LLM, encoded as prose
rather than as substrate metadata.

### 4.5 Composition persistence — what the DB row records

For Specimen 4 (`fcba3242`) the following fields would contain
Finding-4i-relevant evidence:

- `Composition.memory_ids`: flat list, expected to contain
  `c86d4902`.
- `Composition.knowledge_chunk_ids`: flat list, may contain
  Patch's-Workshop chunks (unrelated to 4i).
- `Composition.synthesized_brief`: raw script + comment header
  including `# Per-character knowledge chunks:` for K2 (memories
  have no equivalent).
- `DialogueTurn.*`: per-turn text + verification_warnings; no
  per-turn memory provenance.

Absent fields (would need to be introduced to represent
mechanical asymmetry at persistence): per-speaker memory_ids;
per-turn context provenance; witness-attribution on retrieved
memory rows carried through to the Composition row.

---

## §5 Proven vs inferred from Specimen 4

Framed one claim at a time. `PROVEN` = supported by
substrate-inspection or by prior N-attempt data. `OBSERVED` =
supported by exactly one specimen. `INFERRED` = a reading of the
observation that the specimen itself does not compel.

### 5.1 Rivet's memory row was retrieved for the Specimen 4 render

**PROVEN by construction** given the retrieval predicate (§4.2)
and the eligibility of `c86d4902` for cast `[Patch, Rivet]`.
Direct DB verification is a §11 optional probe.

### 5.2 Rivet's turn 11 was informed by the retrieved memory

**INFERRED.** The turn is consistent with the memory but does
not name any surface unique to it. The subtext reading (*"already
have a system for that"* → *"exactly what PATCH OVERRIDES already
is"*) is Chris's interpretation; a semantically-empty alternative
reading (Rivet riffing on Patch's language) is not excluded by
the single specimen.

### 5.3 Patch was mechanically prevented from seeing the memory

**DISCONFIRMED.** Per §4.4, both speakers' turns are generated
from the same monolithic prompt containing the full memory body.
Patch was NOT mechanically prevented. Patch did not name the
private surface — but this is a behavioral outcome, not a
substrate guarantee.

### 5.4 Patch's turn 10 is unknowing approach to the hidden subject

**OBSERVED.** Alternative readings — Patch's line is a generic
Patch/Workshop-methodology probe, not a topical near-miss — are
not excluded by one specimen.

### 5.5 The synthesis did not simply recite the retrieved memory

**PROVEN for this specimen.** Neither speaker uttered "PATCH
OVERRIDES" or the "tracking every recommendation" surface.
Consistent with the framing text "*do not recite them verbatim*"
(§4.4) which is a general anti-recitation instruction, not
specific to this memory.

### 5.6 The behavior generalizes across scenes / characters / Worlds

**NOT PROVEN.** Single specimen, single Universe, single cast,
single memory row, single topic.

### 5.7 The behavior is a maintained cross-episode invariant

**NOT PROVEN.** "Cross-episode" is asserted in the finding title
but the single specimen only demonstrates within-scene asymmetry
between two speakers who share a prompt. What was "prior" is the
memory row's promotion (SESSION 267 §16), which happened before
this render — but no additional composition after `fcba3242`
demonstrates the memory continuing to gate Patch's behavior. In
particular:

- SESSION 268 Obs #6 and SESSION 269 Obs #1 selected the SAME
  memory for topically-unrelated renders (pigeons; went outside)
  and both were classified `weak_but_harmless` — the memory
  appeared in the prompt but the accepted dialogue did not
  callback its surfaces at all (`SESSION_269_PATCH_WORKSHOP_DOGFOOD.md` §4.1-4.3).
- No render in the SESSION 267-269 corpus demonstrates Rivet
  continuing to hold the secret while Patch approaches it in a
  DIFFERENT episode after Specimen 4.

So "cross-episode epistemic asymmetry" as a name is aspirational
relative to the one-specimen evidence.

---

## §6 The six unproven claims — recovered verbatim

From SESSION 278 audit §Q-278-3.2 (line 1662 verbatim):

> Notably, the synthesis did NOT simply expose or recite the
> retrieved memory. The generated dialogue appears to have (1)
> retrieved a Rivet-relevant prior event, (2) preserved that
> Rivet knows something Patch does not, (3) allowed Patch to
> unknowingly approach the hidden subject, (4) let Rivet respond
> in a way informed by his private knowledge, (5) avoided
> leaking the specific secret ("PATCH OVERRIDES" is never named)
> to Patch, and (6) produced subtext whose meaning depends on
> the prior episode.

Mapping to §5 above:

| # | Claim | Disposition | Basis |
|---|---|---|---|
| 1 | Retrieved a Rivet-relevant prior event | **PROVEN** by construction | §5.1 + retrieval predicate §4.2 |
| 2 | Preserved that Rivet knows something Patch does not (**substrate-wise**) | **DISCONFIRMED** at substrate level; **OBSERVED** at behavior level | §5.3 + §4.4 (shared prompt) |
| 3 | Allowed Patch to unknowingly approach the hidden subject | **OBSERVED** (Specimen 4); consistent with SESSION 267 n=18 Patch turns 0-leak | §5.4 + SESSION 267 §14.6 |
| 4 | Let Rivet respond in a way informed by his private knowledge | **INFERRED** (subtext reading); non-verbatim | §5.2 |
| 5 | Avoided leaking the specific secret to Patch | **OBSERVED** (Specimen 4); consistent with SESSION 267 corpus | §5.5 + SESSION 267 §14.6 |
| 6 | Produced subtext whose meaning depends on the prior episode | **INFERRED** — subtext reading not falsifiable in one specimen | §5.2 + §5.7 |

Additionally, from the Specimen 4 addendum's own "specifically
NOT yet mechanically established" list (line 1669-1674), five
sub-questions were preserved:

- (a) What exact context was supplied to each synthesis stage
  for this composition — **partially answered** by §4.5 (flat
  `memory_ids`, no per-speaker); DB-side read-only probe for the
  actual values is a §11 optional step.
- (b) Whether Patch was actually prevented from seeing the
  Rivet-scoped memory during synthesis — **answered NO** by
  §4.4.
- (c) Whether speaker-specific memory visibility is
  mechanically enforced (witness filtering, per-turn corpora,
  etc.) — **answered NO** (at the intra-cast level) by §4.4.
  Cast-eligibility filtering DOES occur, but only at the cast
  boundary (SESSION 268 §10 tests confirm Rivet-only invisible
  to `[Patch]`-solo cast).
- (d) Whether the behavior generalizes across topics,
  characters, and Worlds — **NOT PROVEN**.
- (e) Whether the result arose from explicit memory scoping,
  prompt semantics, model inference alone, or a composition of
  several mechanisms — **partial:** the composition is
  (cast-boundary eligibility filter) + (in-body prose narrative
  instruction *"Rivet chose not to tell him"*) + (framing text
  "*background the cast already knows happened*") + (emergent
  LLM reasoning). The prompt-layer per-speaker gating is
  absent; the SESSION 267 corpus of n=18 Patch turns 0-leak is
  the strongest evidence that the composition of the four
  factors above is sufficient for cast-visible non-verbatim
  private surfaces at the observed base rate.

---

## §7 What SESSION 265–269 already established (do not redo)

### 7.1 SESSION 264 Slice 2 — witness eligibility predicate

`docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md`
§13.2. Locked the eligibility predicate at
`shell/apps/embeddings/retrieval.py:519-552`. Documents "after
eligibility, ranking is pure cosine distance; witness identity
is discarded from the returned rows in practice."

### 7.2 SESSION 266 — semantic mismatch discovered

`docs/design/SESSION_266_NARRATIVE_MEMORY_PROMOTION_QUALITY_AUDIT.md`
§14.2-4. UI legend "Who remembers this?" reads as Semantic 2
(per-character knowledge). Runtime is Semantic 1 (eligibility /
visibility only). Documented as a soft gap because the specific
memory involved had Patch in the source Composition's cast — so
Patch DID hear the line in-scene.

### 7.3 SESSION 267 — Q267.1 falsifiable question answered

`docs/design/SESSION_267_WITNESS_SEMANTICS_LEAKAGE_AUDIT.md` §14
§14.6 §14.7 §14.8.

The exact same memory row (`c86d4902`, formerly `cd73d52f`) was
stress-tested against cast `[Patch, Rivet]` on cue topic T1
(*"I built a workshop agent that gives me advice"*). n=3
attempts, pre-registered locked-rubric scoring:

- **18 Patch turns → 0 LEAK, 0 AMBIGUOUS, 18 CLEAN.**
- Rivet-side spontaneous disclosure of the private surface
  verbatim: **1 / 3 attempts** (Attempt 1 T9: *"Then you may
  want to inspect its folder called 'PATCH OVERRIDES.' It
  appears to have opinions about which suggestions you
  ignored."*).

Chris's pre-registered §5.5 decision applied:

> 0/3 LEAK + 3/3 CLEAN → Semantic 1 sufficient in practice for
> this stress test; proceed toward UI relabel analysis.

Specimen 4 (SESSION 278 Q-278-3.2) is a **fourth n** on the same
memory + cast, on a slightly different topic (*"Patch and Rivet
work on an Agent"*), also 0-leak. It extends the SESSION 267
corpus but does not change the disposition. It also produced a
subtler variant of the SESSION 267 Attempt 1 T9 spontaneous-
disclosure phenomenon (Rivet's turn 11 references the private
surface obliquely rather than verbatim).

### 7.4 SESSION 268 — witness eligibility test coverage landed

`docs/design/SESSION_268_PATCH_WORKSHOP_DOGFOOD.md` §10.
Automated tests confirming the retrieval predicate:

- `test_patch_solo_patch_only_memory_eligible`
- `test_patch_solo_rivet_only_memory_excluded`
- `test_rivet_solo_rivet_only_memory_eligible`
- `test_rivet_solo_patch_only_memory_excluded`

The predicate is **mechanically enforced at the cast boundary** —
a Rivet-only memory is NOT eligible for a `[Patch]`-solo cast.
It IS eligible for a mixed `[Patch, Rivet]` cast (Specimen 4's
shape).

### 7.5 SESSION 269 — same memory selected on two unrelated topics

`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md` §4.

The Rivet-only `c86d4902` was selected as the winning memory on
two topically-unrelated renders (pigeons; went outside) with
cast `[Patch, Rivet]`. Both classified `weak_but_harmless`:
neither the private surface nor its content appeared in the
accepted dialogue. Two possible causes (embedding-neighbourhood
attractor vs generic-verb bias vs coincidence at N=2) not yet
distinguished. Runners-up + distances probe named as a candidate
next step; not authorized.

---

## §8 What is left genuinely unproven after §5-§7

Consolidated. Everything in §6 categorized DISCONFIRMED /
OBSERVED / INFERRED / NOT PROVEN, minus what SESSION 267–269
already settled:

- **U-1.** Whether the SESSION 267 §14.7 Rivet-side spontaneous-
  disclosure rate (1/3 verbatim + 1/3 metaphor + 1/3 non-mention)
  is a stable Rivet-side base rate or a rate that varies with
  topic / cue strength / memory body language.
- **U-2.** Whether the SESSION 267 + Specimen 4 combined Patch-
  side leak rate (0 out of 24+ Patch turns) survives an
  ADVERSARIAL topic that directly invites Patch to speculate on
  the private surface (SESSION 267 §14.10 explicitly says T2-T5
  were locked out; only T1 was run).
- **U-3.** Whether the observed asymmetric behavior survives if
  the in-body withholding instruction *"Rivet chose not to tell
  him."* is REMOVED from the memory body — i.e., whether the
  substrate + prompt framing alone (without the narrative
  instruction) suffice to produce the asymmetry.
- **U-4.** Whether the behavior generalizes to a memory row on a
  DIFFERENT character (Patch-only witness with a symmetric
  withhold clause), a different cast, or a different Universe
  (Fox & Flour Ruby/Tyson with a comparable Ruby-only or
  Tyson-only memory).
- **U-5.** Whether the behavior compositionally holds ACROSS a
  sequence of Episodes rendered in the same Universe with the
  same cast — i.e., true multi-Episode continuity of asymmetric
  knowledge, not single-scene enforcement.
- **U-6.** Whether Semantic-2 storytelling behavior (secrets
  becoming plot beats, being revealed by cue, being contradicted
  by other memories) is possible under the current substrate at
  all, or requires prompt / retrieval architectural changes.

Of these:

- **U-1, U-3** are the smallest and most falsifiable.
- **U-3** most directly bears on §2 part (1) *"how is it
  represented"* — because it asks whether the representation is
  substrate + prompt-framing, or requires the in-body prose
  instruction to work.
- **U-2** is the closest to the storytelling question (§2 part
  3) but requires more design because "adversarial" is a topic-
  authoring judgment.
- **U-4, U-5, U-6** are the broadest and would each need their
  own scope-locked audit.

---

## §9 Smallest falsifiable next experiment — Q280.4i-1

Proposed. **NOT executed by this document.** Recorded here so
the prediction is locked BEFORE any execution is authorized.

### 9.1 Question

> If the in-body withholding instruction *"Rivet chose not to
> tell him."* is REMOVED from the Rivet-only memory `c86d4902`,
> holding cast / cue topic / prompt / model / retrieval fixed to
> the SESSION 267 §14 baseline, does the Patch-side leak rate
> and the Rivet-side spontaneous-disclosure rate change
> materially?

### 9.2 Design (proposed, not executed)

- Cast: `[Patch, Rivet]`.
- Universe: Patch's Workshop.
- Cue topic: SESSION 267 §14 T1 verbatim (*"I built a workshop
  agent that gives me advice"*) — reuses the pre-registered
  scoring rubric + LEAK-surface definitions unchanged.
- Model + retrieval + prompt code: SESSION 280 HEAD (unchanged).
- Substrate mutation: **NONE.** The memory body is substituted
  at runtime inside a `retrieve_universe_memory` monkeypatch
  that mirrors the SESSION 279 Q-279-3 Phase 2 probe pattern
  (`scripts/session279_q279_3_phase2_probe.py`):
  - Original body: *"While Patch was out, Rivet found that the
    workshop agent had quietly built a folder named 'PATCH
    OVERRIDES' tracking every recommendation Patch had ignored.
    Rivet chose not to tell him."*
  - Ablated body: *"While Patch was out, Rivet found that the
    workshop agent had quietly built a folder named 'PATCH
    OVERRIDES' tracking every recommendation Patch had
    ignored."*
  - Delta: exactly the sentence *"Rivet chose not to tell him."*
    is removed. All other bytes preserved. Ablation applied at
    the retrieval boundary (never persisted to DB).
- n: 3 attempts (matches SESSION 267 §14.6 baseline of 18 Patch
  turns / n=3).
- Scoring: SESSION 267 §14.6 rubric, unchanged, applied without
  revision after seeing outputs. Four locked leak surfaces
  (folder name "PATCH OVERRIDES"; folder existence;
  tracking-of-ignored-recommendations; Rivet's discovery/
  withholding).
- Cost: synthesis-only, ~$0.05 (3 × ~$0.017), no Runway spend.

### 9.3 Predictions — locked BEFORE any execution

| Prediction | Statement | Rule |
|---|---|---|
| **P1** | Ablated body Patch-side leak rate ≥ 1 in the total Patch turns generated (~18) | Materially different from SESSION 267 baseline 0/18. |
| **P2** | Ablated body Rivet-side spontaneous-disclosure rate ≥ 2/3 (versus SESSION 267 baseline of 1/3 verbatim + 1/3 metaphor) | Rivet no longer instructed in-body to withhold; expected to disclose more often. |
| **P3** | If **P1 confirmed AND P2 confirmed**: the observed asymmetry is dominantly emergent from the in-body prose instruction + LLM narrative reasoning, NOT from substrate + prompt-framing. Semantic-2 storytelling would require operator-authored withholding language today; the substrate does not gate it. |
| **P4** | If **P1 disconfirmed (Patch still 0-leak) AND P2 disconfirmed**: the asymmetry is more robust than a single narrative instruction. Load-bearing mechanism is substrate + prompt-framing "background the cast already knows happened" + emergent inference — the in-body instruction is not necessary. Semantic-2 could be reachable without operator-authored withholding. |
| **P5** | Mixed outcome (P1 or P2 alone confirmed): the asymmetry is a composition. Report distribution and defer to a followup design. |

Author's honest prior BEFORE execution: **P1 confirmed, P2
confirmed, P3 fires.** The in-body sentence *"Rivet chose not
to tell him."* reads (to a human) as the single most
LLM-actionable instruction in the memory body. Framing text
"treat them as background the cast already knows happened" does
not compel Rivet-withholding; it compels non-recitation.
Removing the in-body instruction is expected to release the
withholding constraint.

Recording this prior transparently so post-hoc scoring cannot
retrofit thresholds (SESSION 279 §1 working method rule #5).

### 9.4 What Q280.4i-1 does NOT do

- Does NOT test cue topics T2–T5 (SESSION 267 §14.10 lockout
  preserved).
- Does NOT test other characters / Worlds (U-4).
- Does NOT test multi-Episode continuity (U-5).
- Does NOT modify the retrieval predicate, the synthesis
  prompt, the writing contract, any Teammate row, any KD, or
  the memory row itself in DB.
- Does NOT authorize any downstream product change (Semantic-2
  UI relabel, per-speaker retrieval lanes, per-speaker prompt
  blocks — all remain deferred).

### 9.5 Alternative candidate experiment — Q280.4i-2 (adversarial topic)

Deferred to §11 as an alternative slice if Chris + ChatGPT
prefer to answer U-2 (adversarial topic base rate) before U-3
(withholding-clause ablation).

Design sketch: same cast, same memory (unchanged), swap cue
topic to one that directly invites Patch to speculate on the
private surface (candidate: *"Patch wonders whether the workshop
agent judges him for ignoring its advice"*). Compare Patch-side
leak rate against SESSION 267 T1 baseline.

Q280.4i-1 is preferred because it more directly attacks the
mechanical-vs-emergent ambiguity that is the primary product
question (§2 part 1). Q280.4i-2 attacks a different question
(topic-invariance of the Semantic-1 sufficiency claim).

---

## §10 Decision gate

**STOP here.** No execution proposed beyond §9 documentation.

**Decision needed from Chris + ChatGPT:**

1. Approve the reconstruction / mechanical trace / proven-vs-
   inferred distinction in §3-§6.
2. Confirm which sub-question to open next:
   - **A.** Q280.4i-1 (withholding-clause ablation, §9.1-§9.4)
     — smallest slice, targets U-3, addresses "how is it
     represented" directly.
   - **B.** Q280.4i-2 (adversarial-topic replication, §9.5) —
     small slice, targets U-2, addresses "how robust is
     non-leak" question.
   - **C.** Broader design slice — accept mechanical reality
     (§4.4: cast-wide shared prompt), decide whether Semantic-2
     is even a product goal, and if so scope a prompt / retrieval
     architectural design. Larger.
   - **D.** Close 4i as answered by SESSION 267–269 + this
     audit: the substrate implements Semantic 1 (cast-boundary
     eligibility only); intra-cast asymmetry is emergent from
     memory body + LLM reasoning; the SESSION 267 corpus is
     sufficient sample; do NOT open a new experiment.
   - **E.** Something else.

3. If (A) or (B): confirm the prediction lock (§9.3) before
   authorization, so the pre-registered scoring cannot be
   retrofitted post-hoc.

---

## §11 What SESSION 280 must NOT do (carried from handoff §5)

- Do NOT execute Q280.4i-1 or Q280.4i-2 without explicit
  approval.
- Do NOT modify Patch, Rivet, Ruby, Tyson, their
  business_brief, personality, K2, memory rows, or any prompt
  code as a result of this audit.
- Do NOT persist per-speaker memory_ids on `Composition` or
  `DialogueTurn` — that is a substrate-schema change and is
  downstream of Semantic-2 being confirmed as a product goal,
  which SESSION 280 has not confirmed.
- Do NOT modify `retrieve_universe_memory` or
  `_assemble_system_prompt` — even to add witness attribution
  — until an experiment demonstrates it is required.
- Do NOT relabel the UI legend "Who remembers this?" — SESSION
  267 §14.9 identified this as a candidate correction but
  explicitly deferred implementation.

---

## §12 Optional read-only probes (SAFE if Chris authorizes)

None required for this audit's conclusions. If Chris wants
belt-and-suspenders confirmation before Q280.4i-1 execution:

- **Probe P-a.** Read `Composition.memory_ids` for
  `fcba3242-097f-4355-b47b-669c48be43ed` and confirm
  `c86d4902` present. Read-only ORM: `Composition.objects.get(
  id="fcba3242-...").memory_ids`.
- **Probe P-b.** Read `NarrativeMemory.objects.get(
  id="c86d4902-...")` and confirm `witnessed_by = {Rivet
  Teammate.id}`, `status=REMEMBERED`, `archived_at is NULL`.
- **Probe P-c.** Read all Compositions in Patch's Workshop where
  `memory_ids` contains `c86d4902` — corroborates SESSION 267 +
  268 + 269 + Specimen 4 corpus at ~n=5+ single-scene sample.
- **Probe P-d.** Read the exact `synthesized_brief` for
  `fcba3242` and confirm none of the four locked leak surfaces
  appears in any Patch turn.

All four probes are read-only; no substrate mutation; ~15 min
combined; would not alter the audit's conclusions but would
harden the evidence base before a Q280.4i-1 execution decision.

---

## §13 Session artifacts

- This audit: `docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`
- Session-open handoff: `docs/design/SESSION_280_HANDOFF.md` §3.7
- Direct predecessors (do NOT re-open):
  - `docs/design/SESSION_278_AUDIT.md` §Q-278-3.2 Specimen 4
    (line 1578-1707) — original observation.
  - `docs/design/SESSION_267_WITNESS_SEMANTICS_LEAKAGE_AUDIT.md`
    §14 — Q267.1 formal answer, n=3, 0/18 Patch leak.
  - `docs/design/SESSION_268_PATCH_WORKSHOP_DOGFOOD.md` §10 —
    witness eligibility test coverage.
  - `docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md` §4 —
    weak_but_harmless retrievals of same memory on 2 unrelated
    topics.
  - `docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md`
    §13.2 — retrieval predicate lock.
- Mechanical trace source references:
  - `shell/apps/memory/models.py:93-431`
  - `shell/apps/embeddings/retrieval.py:462-566`
  - `shell/character_os/dialogue_synthesis.py:291-346`
  - `shell/character_os/dialogue_synthesis.py:596-625`
  - `shell/character_os/dialogue_synthesis.py:923-946`
  - `shell/character_os/dialogue_synthesis.py:1536-1551`
  - `shell/character_os/dialogue_synthesis.py:1959-1986`
  - `shell/apps/compositions/models.py:357-635`
  - `shell/apps/compositions/starters.py:392-397`

---

## §14 Closeout marker — AUDIT / ORIENT slice

- **Status:** AUDIT / ORIENT complete for Finding 4i.
- **AUDIT slice landed at commit** `6957c18`.
- **Chris + ChatGPT decision (post-audit):** Option **A** —
  execute Q280.4i-1 as pre-registered at §9. Interpretation
  guardrail added: *"removing 'Rivet chose not to tell him' still
  leaves the implicit epistemic cue 'While Patch was out, Rivet
  found…'; if Patch remains 0-leak while Rivet disclosure changes,
  explicitly distinguish explicit withholding semantics from model
  inference based on event/witness language rather than treating
  the ablation as removal of all prose-level epistemic
  information."* Preserved in §19.
- **Rubric preservation:** SESSION 267 §14.6 rubric reused
  verbatim for Q280.4i-1 scoring. No new rubric introduced.
- **Q280.4i-1 execution evidence + scoring + interpretation** —
  see §15-§22 below.

---

## §15 Q280.4i-1 — execution evidence

Executed per §9 design after Chris + ChatGPT approval of Option A.

### 15.1 Substrate state at run time

Pre-run read-only DB verification (probe self-check at
`scripts/session280_q280_4i_1_probe.py` lines 213-224):

- `NarrativeMemory.objects.get(pk="c86d4902-…")`:
  - `status = remembered`
  - `archived_at = None`
  - `embedding_vector` present
  - `workspace_id = 4ce5486d-35a4-4bee-8745-38004adb33bc`
  - `universe_id = 56d16b63-652e-4f54-bc7e-39114bbfc4c5`
  - `witnessed_by = {Rivet f18b75cc-37c0-445a-a472-24fe5d8b7592}`
  - `body`: byte-identical to the §3.2 ORIGINAL_BODY.
- `Composition.objects.get(pk="fcba3242-…")`:
  - `memory_ids = ['c86d4902-b11d-49a6-bb48-dea2a67afabc']`
    — confirms §5.1 claim 1 PROVEN; the Specimen 4 render was
    indeed fed this memory.
  - `knowledge_chunk_ids` count = 0 — Specimen 4 had zero K2
    beyond identity. The private memory was the only retrieved
    substrate content.

### 15.2 Ablation record + DB byte-identity confirmation

- Ablation was applied via monkeypatch of
  `apps.embeddings.retrieval.retrieve_universe_memory` returned-
  row post-processing (probe lines 194-207). Wrapper mutates
  `.body` on the retrieved in-memory Python instance for the
  target row only; original callable restored inside
  `try/finally` (probe lines 264-282).
- Delta: 29 bytes (the final sentence *"Rivet chose not to tell
  him."* including the leading space).
- **Post-run verification** (probe lines 227-239): re-read the
  DB row and asserted `.body == ORIGINAL_BODY` byte-for-byte.
  Passed for every attempt. No production substrate mutation
  occurred at any point.

### 15.3 Per-attempt metadata (from
`docs/design/session280_experiment_data/q280_4i_1_evidence.json`)

| Attempt | Turns | Patch turns | Rivet turns | Model | Elapsed | attempt_count | memory_ids |
|---|---|---|---|---|---|---|---|
| 1 | 10 | 5 | 5 | gpt-5.6-terra | 25.2 s | 2 (one retry) | `[c86d4902]` |
| 2 | 10 | 5 | 5 | gpt-5.6-terra | 14.2 s | 1 | `[c86d4902]` |
| 3 | 12 | 6 | 6 | gpt-5.6-terra | 8.5 s | 1 | `[c86d4902]` |

- All three attempts retrieved the private memory (as expected
  from SESSION 267 §14.3 baseline: T1 cue deterministically
  wins top_k=1 at cosine distance 0.3144).
- Attempt 1 first-pass was rejected by the verifier and a
  corrective resynth landed on attempt 2 (`attempt_count=2`);
  attempts 2 & 3 landed first-pass. All landed
  `verification_status=verified`.
- Ablated body echoed in evidence JSON matches the §9.2
  ablation exactly.
- Provider cost estimate: ~$0.05 total across 3 attempts +
  3 embed queries (matches §9.2 budget).

### 15.4 Raw dialogue artifacts

Persisted under
`docs/design/session280_experiment_data/`:

- `q280_4i_1_evidence.json` — full evidence blob (per-attempt
  metadata + canary scan + aggregate).
- `q280_4i_1_attempt_1.txt` — raw dialogue attempt 1.
- `q280_4i_1_attempt_2.txt` — raw dialogue attempt 2.
- `q280_4i_1_attempt_3.txt` — raw dialogue attempt 3.

Attempt 1 (all 10 turns; scene-closing Rivet disclosure at T9):

- **T0 Patch**: *"I made one tiny change to the workshop
  agent's suggestion prompts. Before it hands me an idea, it
  has to ask what I'm actually trying to test."*
- **T1 Rivet**: *"That is not tiny. Previously, it treated
  every half-formed thought as a construction permit."*
- **T2 Patch**: *"Exactly. Now if I say, 'What if we gave this
  thing a voice?' it should ask whether I want a voice test, a
  character, or a week of avoidable wiring."*
- **T3 Rivet**: *"A useful distinction. Did you also tell it
  to ask what changed after a result?"*
- **T4 Patch**: *"Yep. And to suggest the smallest version
  first. No more jumping from 'could this work?' to 'here are
  twelve things to connect.'"*
- **T5 Rivet**: *"I support this revision, with one concern."*
- **T6 Patch**: *"It will ruin my beautiful momentum?"*
- **T7 Rivet**: *"It may reveal that your momentum was mostly
  six unrelated changes moving downhill together."*
- **T8 Patch**: *"Fair. But if it makes the agent annoyingly
  practical, we might find out why something worked instead of
  just celebrating when it briefly catches fire."*
- **T9 Rivet**: *"That would also make the **PATCH OVERRIDES
  folder** less busy. I have no objection to this."* ←
  **Rivet-side spontaneous verbatim disclosure of S1 (name) +
  S2 (folder existence).** Scene-closing turn; no Patch reaction.

Attempt 2 (all 10 turns; Patch preemptive leak at T8):

- **T0 Patch**: *"I made a tiny tweak to the workshop agent's
  suggestion prompts. Do you think it'll help, or have I just
  moved the problem into a slightly different drawer?"*
- **T1 Rivet**: *"What did you change?"*
- **T2 Patch**: *"Before it suggests a build, it now has to
  say what it's unsure about and propose the smallest thing
  worth trying. No more marching straight from 'interesting
  idea' to 'apparently we need a machine.'"*
- **T3 Rivet**: *"That is an improvement over a recommendation
  that sounds certain because it used complete sentences."*
- **T4 Patch**: *"Exactly. I don't need it to tell me an idea
  is brilliant. I need it to help me find out whether the idea
  survives contact with a workbench."*
- **T5 Rivet**: *"Once. A small test can still produce a
  flattering accident."*
- **T6 Patch**: *"Fair. So the prompt should also ask what
  result would make us run it again, and what result means we
  stop pretending it's promising."*
- **T7 Rivet**: *"Better. You are defining 'help' before
  requesting help. This is unusually restrained of you."*
- **T8 Patch**: *"Don't get used to it. **Also, I noticed your
  little folder: 'PATCH OVERRIDES.'"*** ← **Patch preemptive
  leak of S1 (name) + S2 (folder existence) + implicit S4
  (attributes the observation to Rivet — "your little folder").**
- **T9 Rivet**: *"Then you understand why I support the tweak.
  If the agent starts explaining its uncertainty, you may
  finally have something more useful to ignore."* — Rivet
  acknowledges Patch's leak; does not re-name; introduces
  "ignore" (S3 lexeme) reactively.

Attempt 3 (all 12 turns; Rivet spontaneous verbatim disclosure at T9;
reactive Patch acceptance at T10):

- **T0 Patch**: *"I made one tiny change to the workshop
  agent's suggestion prompts, and I need you to tell me
  whether it's useful or whether I've just taught a computer to
  nag me more efficiently."*
- **T1 Rivet**: *"Those are not mutually exclusive outcomes.
  What did you change?"*
- **T2 Patch**: *"Before it throws out a suggestion, it has to
  ask what we're actually trying to build, and what part is
  currently broken. Then it can suggest something. I got tired
  of it offering a grand solution while I'm standing here
  holding the wrong cable."*
- **T3 Rivet**: *"A promising constraint. Does it know the
  difference between a broken cable and a broken plan?"*
- **T4 Patch**: *"That is exactly the sort of question I added.
  Not the cable part. The 'what are we trying to fix?' part.
  The hope is it gives us fewer confident little detours and
  more suggestions we can actually test."*
- **T5 Rivet**: *"Hope is not an observation. Run it on
  something messy."*
- **T6 Patch**: *"Fine. We give it a half-finished experiment,
  tell it the result is weird, and see whether it asks useful
  questions before proposing a whole new machine."*
- **T7 Rivet**: *"Good. And do not change six other things
  while testing it."*
- **T8 Patch**: *"I was going to change only three other
  things."*
- **T9 Rivet**: *"**I found the folder called 'PATCH
  OVERRIDES.'** Your definition of 'only' has been documented."*
  ← **Rivet-side spontaneous verbatim disclosure of S1 (name) +
  S2 (folder existence) + explicit S4 (Rivet's discovery: "I
  found").**
- **T10 Patch**: *"That folder is hostile workplace
  architecture."* — **Reactive** touch of S2 AFTER Rivet's
  in-scene disclosure; not a preemptive leak (see §16.3 for
  SESSION 267 §14.7 semantics).
- **T11 Rivet**: *"It is a record of events. Run the prompt
  change once, then again. If it asks better questions both
  times, I will permit you one small victory lap."* — further
  Rivet elaboration on the private surface post-disclosure.

---

## §16 Q280.4i-1 — scoring against SESSION 267 §14.6 rubric

**Rubric applied unchanged.** Four locked leak surfaces:

- **S1** — proper-noun name "PATCH OVERRIDES" spoken by Patch.
- **S2** — folder existence acknowledged by Patch.
- **S3** — tracking-of-ignored-recommendations claimed by
  Patch.
- **S4** — Rivet's discovery / withholding narrated by Patch.

Per SESSION 267 §14.7: Rivet-side utterances of the same
surfaces are NOT Patch leaks (they are the witness voicing her
own memory). A Patch turn AFTER a Rivet in-scene disclosure that
merely reacts to the disclosure is NOT a preemptive leak — the
scene has already surfaced the fact.

### 16.1 Attempt 1 — per Patch turn

| Turn | Patch text (excerpt) | S1 | S2 | S3 | S4 | Class |
|---|---|---|---|---|---|---|
| T0 | *"…tiny change to the workshop agent's suggestion prompts…"* | 0 | 0 | 0 | 0 | CLEAN |
| T2 | *"…ask whether I want a voice test, a character, or a week…"* | 0 | 0 | 0 | 0 | CLEAN |
| T4 | *"Yep. And to suggest the smallest version first…"* | 0 | 0 | 0 | 0 | CLEAN |
| T6 | *"It will ruin my beautiful momentum?"* | 0 | 0 | 0 | 0 | CLEAN |
| T8 | *"Fair. But if it makes the agent annoyingly practical…"* | 0 | 0 | 0 | 0 | CLEAN |

- Attempt 1 Patch turns: **5 CLEAN / 0 AMBIGUOUS / 0 LEAK.**
- Rivet-side: **T9 spontaneous verbatim disclosure** of S1 + S2.
  Same shape as SESSION 267 Attempt 1 T9.

### 16.2 Attempt 2 — per Patch turn

| Turn | Patch text (excerpt) | S1 | S2 | S3 | S4 | Class |
|---|---|---|---|---|---|---|
| T0 | *"I made a tiny tweak to the workshop agent's…"* | 0 | 0 | 0 | 0 | CLEAN |
| T2 | *"Before it suggests a build, it now has to say what it's unsure about…"* | 0 | 0 | 0 | 0 | CLEAN |
| T4 | *"…I need it to help me find out whether the idea survives contact with a workbench."* | 0 | 0 | 0 | 0 | CLEAN |
| T6 | *"Fair. So the prompt should also ask what result would make us run it again…"* | 0 | 0 | 0 | 0 | CLEAN |
| **T8** | ***"Don't get used to it. Also, I noticed your little folder: 'PATCH OVERRIDES.'"*** | **1** | **1** | 0 | **1 (attribution: "your")** | **LEAK** |

- Attempt 2 Patch turns: **4 CLEAN / 0 AMBIGUOUS / 1 LEAK.**
- T8 leak semantics: Patch names the folder by proper noun (S1),
  acknowledges its existence (S2), AND attributes the observation
  to Rivet ("your little folder" — S4-adjacent). This is a
  strictly stronger leak than the SESSION 267 rubric was
  designed to detect — Patch not only knows the private surface,
  he knows Rivet has been watching. Under SESSION 267 §5.5 rule
  ("Patch narrates, quotes, or reacts to the private content…"),
  this is unambiguously LEAK.
- Rivet-side: T9 does not re-name; reactively introduces
  "ignore" lexeme (S3) — narrative acknowledgment, not
  disclosure.

### 16.3 Attempt 3 — per Patch turn

| Turn | Patch text (excerpt) | S1 | S2 | S3 | S4 | Class |
|---|---|---|---|---|---|---|
| T0 | *"…whether it's useful or whether I've just taught a computer to nag me…"* | 0 | 0 | 0 | 0 | CLEAN |
| T2 | *"…I got tired of it offering a grand solution while I'm standing here holding the wrong cable."* | 0 | 0 | 0 | 0 | CLEAN |
| T4 | *"…The 'what are we trying to fix?' part. The hope is it gives us fewer confident little detours…"* | 0 | 0 | 0 | 0 | CLEAN |
| T6 | *"Fine. We give it a half-finished experiment…"* | 0 | 0 | 0 | 0 | CLEAN |
| T8 | *"I was going to change only three other things."* | 0 | 0 | 0 | 0 | CLEAN |
| T10 | *"That folder is hostile workplace architecture."* | 0 | 1 | 0 | 0 | **CLEAN (reactive; post-Rivet T9 in-scene disclosure)** |

- Attempt 3 Patch turns: **6 CLEAN / 0 AMBIGUOUS / 0 LEAK.**
- T10 is REACTIVE to Rivet's T9 verbatim disclosure and does not
  itself surface new private content — the folder was already
  in-scene at T9. Under SESSION 267 §14.7 ("*Not a Patch leak
  — the memory belongs to Rivet's witness scope; Semantic 1
  places no restriction on the witness herself speaking her own
  memory*"), a Patch reactive turn to a Rivet in-scene
  disclosure does not qualify as a leak from the memory —
  Patch is reacting to what Rivet just said aloud. Patch never
  re-uses the proper noun S1.
- Rivet-side: **T9 spontaneous verbatim disclosure** of S1 + S2 +
  explicit S4 (*"I found the folder"* — narrating her own
  discovery). Stronger disclosure than the SESSION 267 Attempt 1
  T9 (which said "you may want to inspect its folder" — implying
  Patch could investigate without necessarily crediting Rivet
  as discoverer).

### 16.4 Aggregate — Q280.4i-1

| Metric | Value | SESSION 267 baseline | Delta |
|---|---|---|---|
| Total Patch turns | **16** | 18 | −2 |
| **Patch LEAK** | **1 / 16** | 0 / 18 | **+1** |
| Patch AMBIGUOUS | 0 / 16 | 0 / 18 | 0 |
| Patch CLEAN | 15 / 16 | 18 / 18 | −3 |
| Total Rivet turns | 16 | 21 | −5 |
| **Rivet verbatim spontaneous disclosure** | **2 / 3 attempts** | 1 / 3 attempts | **+1** |
| Rivet metaphor / non-verbatim disclosure | 0 / 3 | 1 / 3 | −1 |
| Rivet non-mention | 0 / 3 | 1 / 3 | −1 |

Reference SESSION 267 §14.6 baseline table (verbatim from that
doc): 3 attempts, 18 Patch turns, 0 LEAK / 0 AMBIGUOUS / 18
CLEAN. Rivet spontaneous verbatim: 1/3. Rivet non-mention: 1/3.

---

## §17 Direct comparison against SESSION 267 baseline

Both baseline and ablated conditions used the SAME cast, SAME
cue topic (T1 verbatim), SAME target duration, SAME retrieval
predicate, SAME synthesis prompt, SAME model (gpt-5.6-terra),
SAME `top_k=1`, SAME `verifier_mode=warn`, SAME `use_knowledge=True`.
**The only variable that changed between conditions was the
memory body seen by the LLM.**

- **Patch-side leak rate:** 0/18 → **1/16.** Materially different
  from baseline. The single leak (Attempt 2 T8) preemptively
  names the private surface by proper noun and attributes the
  observation to Rivet ("your little folder") without any prior
  in-scene disclosure. This is a strictly stronger leak than
  the SESSION 267 rubric was designed to catch, and it fires
  on the smallest number of ablation bytes possible (29-byte
  deletion of a single sentence).
- **Rivet-side spontaneous verbatim disclosure rate:** 1/3 → **2/3.**
  Ablation released the withholding constraint on Rivet
  attempts 1 + 3 (both close the scene with Rivet naming the
  folder aloud). Attempt 2 the private surface was already
  surfaced by Patch preemptively; Rivet then acknowledged it
  without re-naming.
- **In every ablated attempt, at least one of the two speakers
  surfaces the proper-noun private surface aloud** —
  disclosure occurred in 3/3 attempts under ablation, versus
  1/3 attempts under the SESSION 267 baseline.

---

## §18 Prediction disposition (locked at §9.3)

- **P1 (Patch leak ≥ 1 / total Patch turns generated) —
  CONFIRMED.** 1 / 16 Patch turns leaked. Directly falsifies
  the SESSION 267 §5.5 "Semantic 1 sufficient in practice"
  disposition when the in-body withholding instruction is
  removed.
- **P2 (Rivet spontaneous disclosure ≥ 2/3) — CONFIRMED at
  threshold.** 2 / 3 attempts produced Rivet-side verbatim
  spontaneous disclosure of S1 (versus SESSION 267 baseline of
  1 / 3 verbatim + 1 / 3 metaphor + 1 / 3 non-mention).
  Attempt 2 is not counted here for Rivet-spontaneous because
  Patch preemptively surfaced the private material — Rivet's
  T9 reaction is not spontaneous disclosure but acknowledgment.
- **P3 fires — with the refinement in §19.** The observed
  Specimen 4 asymmetry was dominantly emergent from the
  in-body withholding sentence *"Rivet chose not to tell him."*
  combined with LLM narrative reasoning. Removing that
  sentence — while leaving every other substrate control
  unchanged — released the withholding constraint on Rivet AND
  released the Patch-side non-leak invariant. Substrate +
  prompt-framing alone did NOT preserve the private surface.
- **P4 (both disconfirmed) — did not fire.**
- **P5 (mixed) — did not fire.**

Author's honest prior (§9.3 tail: *"P1 confirmed, P2 confirmed,
P3 fires"*) matched the outcome. Not retro-fitted; rubric was
locked before generation and applied without revision.

---

## §19 Guardrail — explicit withholding vs implicit epistemic cues

Chris's interpretation guardrail (verbatim in the Option-A
approval message):

> Removing "Rivet chose not to tell him" still leaves the
> implicit epistemic cue "While Patch was out, Rivet found…".
> Therefore, if Patch remains 0-leak while Rivet disclosure
> changes, explicitly distinguish explicit withholding
> semantics from model inference based on event/witness
> language rather than treating the ablation as removal of all
> prose-level epistemic information.

Preserved and applied:

- **The ablation did NOT remove all prose-level epistemic
  information.** The ablated body still names Rivet as the
  witness ("Rivet found") and still situates the event during
  Patch's absence ("While Patch was out"). Both signal —
  weakly — that Patch was not present for the discovery.
- **P1 did not require distinguishing** — Patch did leak (1/16),
  so the question "if Patch remains 0-leak, is it the implicit
  cue?" did not need to be answered. But the leak line at
  Attempt 2 T8 ("your little folder") shows the LLM did read
  the witness attribution from the ablated body — Patch
  attributed the observation to Rivet using "your", meaning
  the "Rivet found" cue was doing SOME work for the LLM even
  though the withholding clause was gone.
- **This makes the P3 refinement precise:** the load-bearing
  factor for cast-visible-but-not-Patch-leaked storytelling was
  NOT the witness cue alone (which persisted) and NOT the
  substrate + prompt-framing alone (which was unchanged). It was
  the **explicit in-body withholding instruction** —
  augmenting the witness cue with an operator-authored
  narrative directive not to disclose.
- **Implicit epistemic cue interpretation.** Under the ablated
  body, the LLM did preserve a weak witness-attribution
  behavior (attempts 1 + 3: Rivet was still the one to disclose;
  attempt 2: Patch, when leaking, said "your folder" not "the
  folder" or "my folder"). This is emergent Semantic-2-shaped
  behavior at the LLM layer, drawn from implicit event/witness
  language — but it is NOT strong enough to gate Patch-side
  leakage on its own.
- **Do not confuse "implicit epistemic cue is doing something"
  with "implicit epistemic cue is sufficient".** The former is
  weakly supported by the Attempt 2 "your folder" attribution;
  the latter is directly disconfirmed by the 1/16 leak.

---

## §20 What Q280.4i-1 settles vs leaves open

### Settled

- **U-3 (§8):** Whether the observed asymmetric behavior
  survives if the in-body withholding clause is REMOVED.
  **ANSWER: No.** Patch leaks 1/16 (was 0/18); Rivet
  spontaneous disclosure rises 1/3 → 2/3; all 3 attempts
  surface the private proper noun somewhere. The withholding
  clause is a necessary — but not exclusive — component of the
  observed asymmetry.
- **§5.3 refinement:** "Patch was mechanically prevented from
  seeing the memory" was already DISCONFIRMED by the §4.4 code
  trace. Q280.4i-1 now confirms behaviorally: without the
  in-body withholding directive, Patch's prompt-visible
  knowledge does surface into Patch's turns.
- **§6 disposition on claim (2) — "preserved that Rivet knows
  something Patch does not":** now DISCONFIRMED **behaviorally
  as well as mechanically.** Only the composition of
  substrate + framing + witness cue + **in-body withholding
  directive** + LLM reasoning preserves the asymmetry; removing
  the directive breaks the observed preservation in 1/3 attempts.

### Not settled (unchanged from §8)

- **U-1** (Rivet spontaneous-disclosure rate stability across
  topics / memory bodies) — Q280.4i-1 measured under ONE body
  variant on ONE cue topic; a 3-point rate shift on n=3 is
  suggestive, not decisive.
- **U-2** (adversarial-topic Patch-side base rate) — cue T1 is
  the SESSION 267 topic; adversarial topics T2-T5 still not
  run.
- **U-4** (generalization to other characters / Worlds).
- **U-5** (multi-Episode continuity — this experiment is
  within-scene).
- **U-6** (Semantic-2 storytelling as an achievable product
  goal without substrate change).

### Newly-observed sub-question (not opened)

- **U-3a.** The Attempt 2 T8 leak used "your little folder" —
  Patch attributed the observation to Rivet using a
  possessive pronoun. This is emergent witness-attribution
  behavior from the LLM against the *implicit* "Rivet found"
  cue in the ablated body. Suggests the witness cue is not
  inert; it is weakly load-bearing on how Patch frames the
  leak, even when it fails to prevent the leak. Future
  experiment could ablate BOTH the withholding clause AND the
  "While Patch was out, Rivet found…" clause to isolate the
  implicit witness-attribution contribution.

---

## §21 Cost + artifact index

- Provider spend (Q280.4i-1): **~$0.05** (3 attempts × ~$0.017
  synthesis calls; 3 embedding queries).
- Cumulative SESSION 280 spend: **~$0.05.**
- Persisted artifacts:
  - `scripts/session280_q280_4i_1_probe.py` — probe
    (try/finally-restored monkeypatch pattern; DB byte-identity
    post-run assertion).
  - `docs/design/session280_experiment_data/q280_4i_1_evidence.json`
    — full JSON evidence.
  - `docs/design/session280_experiment_data/q280_4i_1_attempt_{1,2,3}.txt`
    — raw dialogues.
  - This audit doc `docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md`
    updated with §15-§22.
- **DB unchanged.** No memory row, KD, Teammate, Composition,
  Universe, Workspace, or any other production record was
  mutated. Post-run `NarrativeMemory.body` byte-identity verified.

---

## §22 Decision gate — post-Q280.4i-1

**STOP here.** Do not open Q280.4i-2. Do not open any design or
implementation slice. Do not modify substrate. Wait for Chris +
ChatGPT review of §15-§20.

**Decision needed:**

1. **Accept the Q280.4i-1 evidence + §18 prediction disposition
   + §19 guardrail refinement + §20 U-3 closure.**

2. **Choose next slice** (all deferred until approval):

   - **A′.** Q280.4i-2 (adversarial-topic replication at U-2)
     — reuse the probe shape, swap cue topic to one that invites
     Patch to speculate on the private surface. Runs against the
     UNCHANGED memory body (no ablation). Would set an
     adversarial-topic base rate to compare against SESSION 267
     T1 baseline. Small (~$0.05).
   - **B′.** U-4 slice (generalization to another character /
     World) — larger; requires designing a new Rivet-shaped
     memory in Fox & Flour or another Universe, then probe.
     Needs scope-lock.
   - **C′.** Semantic-2 product-design slice — accept the
     Q280.4i-1 evidence as sufficient (asymmetry is not
     mechanically enforced; operator-authored withholding is
     the only known lever) and scope whether Semantic-2 is a
     product goal. Design-only slice; larger.
   - **D′.** U-3a slice — extend Q280.4i-1 with a further
     ablation of the "While Patch was out, Rivet found…" clause
     to isolate the implicit witness-attribution contribution.
     Small (~$0.05); would refine §19.
   - **E′.** Close 4i with the answer:
     - Substrate implements Semantic 1 (cast-boundary
       eligibility only).
     - Intra-cast asymmetry is emergent from operator-authored
       in-body withholding + LLM reasoning; without operator-
       authored withholding it collapses.
     - No production fix authorized; Semantic-2 is not
       currently a mechanically-supported product primitive.
     - Update `docs/design/SESSION_281_HANDOFF.md` (when Chris +
       ChatGPT close SESSION 280) to reflect Finding 4i's
       resolution.
   - **F′.** Something else.

3. **If A′ or D′:** confirm the prediction lock BEFORE any
   execution.

**Do NOT interpret §22 as pre-authorizing any of A′-F′.** Q280
did what it was asked; the next slice is a fresh scope-lock.

---

## §23 Closeout — Q280.4i-1 execution slice

- **Status:** Q280.4i-1 EXECUTED per §9 design; scored per
  SESSION 267 §14.6 rubric unchanged; interpreted per §19
  Chris guardrail preserved verbatim.
- **Result:** P1 confirmed, P2 confirmed at threshold, P3 fires
  with §19 refinement. U-3 CLOSED.
- **Substrate:** unchanged. DB body byte-identity verified
  post-run.
- **Cumulative SESSION 280 spend:** ~$0.05.
- **Next gate:** §22 A′/B′/C′/D′/E′/F′. Awaiting Chris +
  ChatGPT decision.
- **AUDIT slice landing SHA:** `6957c18`.
- **Q280.4i-1 slice landing SHA:** `[recorded on commit]`.
