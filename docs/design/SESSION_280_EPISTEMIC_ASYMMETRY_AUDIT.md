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

## §14 Closeout marker (this slice only)

- **Status:** AUDIT / ORIENT complete for Finding 4i.
- **Next gate:** Chris + ChatGPT choose from §10 options
  A/B/C/D/E.
- **No production substrate mutation** performed by this
  document. Prediction for the proposed experiment Q280.4i-1
  locked at §9.3 before any execution.
- **Rubric preservation:** SESSION 267 §14.6 rubric would be
  reused verbatim for Q280.4i-1 scoring. No new rubric
  introduced by this audit.
- **HEAD at audit landing:** `[SHA recorded on commit]`.
