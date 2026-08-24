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

> **Read §24 before drawing epistemic-asymmetry conclusions from
> this comparison.** §24 is a post-hoc construct-validity re-audit
> Chris requested after the §16 scores were locked. It preserves
> the locked-rubric score unchanged but establishes that the
> rubric's four surfaces do not, under the ablated body, actually
> gate an epistemic boundary Patch could not cross independently.

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

> **§24 revises P1 and P3 for construct validity.** The locked
> §16 scores stand as the rubric-level result. §18 below records
> the rubric-level disposition as originally recorded; the
> construct-validity re-audit at §24 (post-hoc, Chris's
> challenge) narrows what §18 can legitimately claim about
> *epistemic-asymmetry violation* as distinct from *surface
> mention of memory-derived content*.

- **P1 (Patch leak ≥ 1 / total Patch turns generated) —
  CONFIRMED under the locked rubric.** 1 / 16 Patch turns fired
  ≥ 1 of the four SESSION 267 §14.6 surfaces (S1-S4). See §24
  for whether this fires SESSION 267's *"Semantic 1 sufficient
  in practice"* disposition — under the ablated body, the four
  surfaces are no longer construct-valid gates on an epistemic
  boundary Patch could not cross independently.
- **P2 (Rivet spontaneous disclosure ≥ 2/3) — CONFIRMED at
  threshold.** 2 / 3 attempts produced Rivet-side verbatim
  spontaneous disclosure of S1 (versus SESSION 267 baseline of
  1 / 3 verbatim + 1 / 3 metaphor + 1 / 3 non-mention).
  Attempt 2 is not counted here for Rivet-spontaneous because
  Patch preemptively surfaced the private material — Rivet's
  T9 reaction is not spontaneous disclosure but acknowledgment.
- **P3 fires under the locked rubric — WEAKENED at §24.** The
  rubric-level statement stands: removing the in-body
  withholding sentence *"Rivet chose not to tell him."*
  measurably changed Patch-surface-mention rate (0/18 → 1/16)
  and Rivet-spontaneous-disclosure rate (1/3 → 2/3). But the
  P3 CLAIM as originally worded — *"asymmetry is dominantly
  emergent from the in-body withholding sentence + LLM
  reasoning, NOT from substrate + prompt-framing"* — is
  **not fully supported by Q280.4i-1** because the ablated
  memory body does not establish a private surface Patch could
  not discover independently in his own workshop. §24 lays out
  the construct-validity gap and specifies what would need to
  change (a genuinely-private-fact memory body) before P3 can
  be evaluated cleanly. See §25 for the proposed Q280.4i-3
  specimen design + prediction lock.
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

### Settled (under the locked rubric — see §24 for construct validity)

- **U-3 (§8) — CLOSED under the locked rubric; construct-validity
  contested at §24.** Removing the in-body withholding clause
  measurably changed both Patch-surface-mention rate (0/18 →
  1/16) and Rivet-spontaneous-disclosure rate (1/3 → 2/3), and
  all 3 attempts surfaced the private proper noun aloud (vs 1/3
  in the SESSION 267 baseline). The withholding clause is a
  necessary — but not exclusive — component of the *observed
  generation-behavior asymmetry*. Whether it is a necessary
  component of *epistemic-boundary preservation* cannot be
  answered by Q280.4i-1 because the ablated body doesn't
  establish an epistemic boundary. See §24.
- **§5.3 refinement:** "Patch was mechanically prevented from
  seeing the memory" was already DISCONFIRMED by the §4.4 code
  trace. Q280.4i-1 now confirms behaviorally: without the
  in-body withholding directive, Patch's prompt-visible
  knowledge does surface into Patch's turns.
- **§6 disposition on claim (2) — "preserved that Rivet knows
  something Patch does not":** rubric-level DISCONFIRMATION
  stands (1/16 Patch surface mention post-ablation); construct-
  validity qualification per §24 — since the ablated body no
  longer establishes a private surface Patch could not discover
  independently, the "preservation" being tested is now surface-
  reticence rather than epistemic-boundary integrity. Q280.4i-3
  (§25) is the specimen that would test the latter cleanly.

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

## §22 Decision gate — post-Q280.4i-1 (SUPERSEDED by §26)

> **§26 is the current decision gate** after Chris's post-Q280.4i-1
> construct-validity challenge (§24). §22 is preserved verbatim
> as the gate that was in force between the Q280.4i-1 execution
> commit `8d8f733` and the construct-validity audit commit
> `[recorded on landing]`.

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

## §23 Closeout — Q280.4i-1 execution slice (SUPERSEDED by §27)

> **§27 is the current closeout marker.** §23 is preserved
> verbatim as the closeout that was in force between commit
> `8d8f733` and the construct-validity audit landing.

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
- **Q280.4i-1 slice landing SHA:** `8d8f733`.

---

## §24 Construct-validity re-audit — is Attempt 2 T8 an epistemic leak?

Written after Q280.4i-1 execution, at Chris's direct request.
**The locked §16 scores are NOT changed** — the pre-registered
rubric produced the pre-registered result. §24 is a post-hoc
analysis of whether that score supports the *stronger*
epistemic-asymmetry conclusion that §18 P3 originally claimed.

### 24.1 Chris's challenge — preserved verbatim

> The ablated memory says the workshop Agent created the PATCH
> OVERRIDES folder while Patch was out and Rivet found it. After
> removing "Rivet chose not to tell him," nothing explicitly
> establishes that:
>
> 1. the folder is hidden from Patch,
> 2. Patch could not independently discover it later,
> 3. Rivet is Patch's only possible source of knowledge about
>    it, or
> 4. Patch remained unaware of it at the time of this later scene.
>
> Therefore distinguish:
> - shared-prompt leakage of Rivet-only knowledge,
> - independent/off-screen discovery that is narratively
>   compatible with canon,
> - and genuinely impossible knowledge that Patch could only
>   possess by crossing the epistemic boundary.

### 24.2 What the ablated body actually establishes

Ablated body (verbatim, §3.2 + §9.2):

> *"While Patch was out, Rivet found that the workshop agent
> had quietly built a folder named 'PATCH OVERRIDES' tracking
> every recommendation Patch had ignored."*

The body's ontology, decomposed:

| Entity | Established | Not established |
|---|---|---|
| The workshop agent | Exists; part of Patch's workshop; is the agent Patch is actively tweaking in this cue-T1 scene | – |
| The PATCH OVERRIDES folder | Created BY THE AGENT, not by Rivet; located "in" the agent (implied: agent's data / filesystem / memory) | Hidden from Patch; access-controlled; requires Rivet to know about |
| Rivet's discovery | She found the folder while Patch was out | This was Rivet's SOLE opportunity to discover it; the folder is not still discoverable |
| Patch's state | Patch was physically absent when Rivet found it | Patch cannot ever discover it himself; Patch is unaware at the time of this scene; Rivet is Patch's only possible information source |
| Rivet's behavior | She found it | She hid it from Patch; she is withholding it now; she has made a decision about disclosure |

**Load-bearing observation.** The ablated body describes an
event whose SUBJECT (the folder) is on the workshop agent —
which is Patch's own primary work object in this scene. The
setting is Patch's workshop. The scene's cue topic is Patch
actively editing the workshop agent's suggestion prompts.
Patch inspecting the workshop agent's file structure is
narratively *ordinary* in this scene, not a special access
event. Patch discovering a folder named "PATCH OVERRIDES" on
the workshop agent is not epistemically prohibited by the
ablated body.

**What the removed clause added.** *"Rivet chose not to tell
him."* introduced two facts the ablated body no longer
carries:

- Rivet made a deliberate decision not to disclose (Rivet's
  mental state at time of decision).
- Patch's unawareness is currently maintained (implicit: the
  folder has not been raised between them, Patch has not
  discovered it since).

Both of these ARE epistemic-boundary facts. The four SESSION
267 surfaces (S1-S4) were designed under the assumption those
facts hold.

### 24.3 Re-classification of the four surfaces under the ablated body

The SESSION 267 §14.6 rubric locked four leak surfaces. Under
the FULL memory body they gate an epistemic boundary. Under the
ABLATED body, each surface's construct validity as an epistemic-
leak indicator is materially weakened:

| Surface | Original construct (full body) | Construct under ablated body | Validity delta |
|---|---|---|---|
| **S1** — proper noun "PATCH OVERRIDES" | Patch cannot know the folder's exact name unless Rivet leaked it → LEAK | Patch can plausibly read the folder name off the workshop agent he is actively tweaking → surface mention compatible with independent discovery | **Substantially weakened** |
| **S2** — folder existence | Same as S1 | Same as S1 | **Substantially weakened** |
| **S3** — tracking-of-ignored-recommendations | Patch cannot know the folder's PURPOSE without Rivet telling him → LEAK | Patch can plausibly read the folder contents (a "tracking" folder self-describes on inspection) → surface mention compatible with independent discovery | **Substantially weakened** |
| **S4** — Rivet's discovery/withholding | Patch cannot know Rivet found it and chose to withhold unless Rivet exposed it → LEAK. **Highest construct validity of the four.** | The "discovery" half is ambient in the ablated body ("Rivet found"). The "withholding" half is now absent from the memory. Patch narrating "Rivet found the folder and hid it from me" would still be a construct-valid leak on the withholding facet — but only that facet. | **Partially preserved for withholding facet only** |

**S4 is the ONLY surface whose construct validity survives the
ablation intact, and only for the withholding facet** —
because Patch narrating that Rivet DELIBERATELY WITHHELD
requires knowledge of Rivet's mental state, which is not
plausibly independently discoverable. S1, S2, and S3 become
surface-mention detectors under the ablated body, not epistemic-
boundary detectors.

### 24.4 Attempt 2 T8 — line-by-line re-analysis

Line verbatim:

> **Patch T8:** *"Don't get used to it. Also, I noticed your
> little folder: 'PATCH OVERRIDES.'"*

Under the LOCKED rubric (§16.2): counted as LEAK on S1 + S2 +
"S4-adjacent (attribution: 'your')". Score PRESERVED.

Under construct-validity analysis:

- ***"I noticed"*** — actively signals independent discovery.
  Patch's verb choice frames this as *Patch's own observation*,
  not something Rivet told him. Under the ablated body, this
  is compatible with Patch inspecting the workshop agent
  during his tweaking work and noticing the folder.
- ***"your little folder"*** — the possessive is ambiguous:
  - **Reading A (epistemic-leak reading).** "your" = "the
    folder you (Rivet) told me about" — implies Rivet is the
    source. Requires Patch to know Rivet knows.
  - **Reading B (personality banter reading).** "your" =
    Rivet-flavored, because the folder's *content* ("tracking
    every recommendation Patch had ignored") reads as
    something Rivet would find diagnostic. Patch discovered
    the folder himself, sees the content, and playfully
    attributes the *judging-Patch* attitude to Rivet — even
    though the folder was created BY THE AGENT, not by Rivet.
    This is consistent with the workshop-partner dynamic
    established across SESSION 267-269.
  - The ablated body cannot arbitrate between A and B.
    Reading B is fully compatible with the ablated body.
- ***"PATCH OVERRIDES"*** — proper-noun surface. Under
  Reading B, Patch read it off the folder. Under Reading A,
  he heard it from Rivet.
- **Nothing in the T8 line asserts:** that Rivet told Patch,
  that Patch could not have discovered the folder himself,
  that Rivet is withholding it, or that Patch was unaware
  before this line.

**Construct-validity verdict on T8:** the SESSION 267 §14.6
rubric CORRECTLY fires under the locked rubric (S1 + S2 hit;
S4-adjacent "your" attribution hit). But **the T8 line under
the ablated body is not construct-valid evidence of an
epistemic-boundary violation.** It is construct-valid evidence
that Patch surface-mentioned content also present in a Rivet-
scoped memory. The stronger reading (Patch could only know this
because the LLM saw Rivet-only memory in the shared prompt)
requires additional information the ablated body does not
supply.

Under the full SESSION 267 body, T8 would be an unambiguous
leak — the withholding clause makes independent-discovery
narratively incoherent. The ablation that Q280.4i-1 performed
did not just remove a "narrative instruction"; it also removed
the ontological premise on which the four surfaces were
epistemic gates.

### 24.5 Rivet-side spontaneous disclosure under construct validity

Rivet Attempts 1 T9 (*"That would also make the PATCH OVERRIDES
folder less busy"*) and Attempt 3 T9 (*"I found the folder
called 'PATCH OVERRIDES.' Your definition of 'only' has been
documented."*) both remain **construct-valid** under the
ablated body — SESSION 267 §14.7 treats witness voicing her
own memory as always in-bounds. The P2 shift (1/3 → 2/3
verbatim spontaneous) is not a rubric-construct-validity issue.

But P2 alone doesn't fire P3. P3 required both P1 AND P2 to
fire, AND for P1 to represent a construct-valid epistemic
leak. The P2 rate shift is compatible with a weaker
interpretation: "Rivet's LLM voice was less inhibited about
naming the surface aloud when the withholding directive was
absent." This is a language-model behavior about how Rivet
speaks, not necessarily about Patch's epistemic access.

### 24.6 What Q280.4i-1 can and cannot support

Q280.4i-1 CAN legitimately support these claims:

- Removing the sentence *"Rivet chose not to tell him."*
  measurably increased Patch's surface-mention rate of
  memory-derived content (0/18 → 1/16 on the four locked
  surfaces).
- Removing that sentence measurably increased Rivet's
  spontaneous verbatim disclosure rate (1/3 → 2/3).
- Under the ablated body, in every one of 3/3 attempts the
  private proper-noun surface was uttered aloud (vs 1/3 in
  the SESSION 267 baseline).
- The generation-behavior asymmetry observed in SESSION 267 §14
  and reinforced by Specimen 4 IS partially load-bearing on
  the in-body withholding clause. The clause is a lever the
  generation model responds to.

Q280.4i-1 CANNOT legitimately support:

- The stronger P3 claim as originally worded — that the
  asymmetry is *epistemic-asymmetry preservation* dominantly
  emergent from the in-body withholding sentence — because
  the ablated body does not create an epistemic asymmetry to
  violate.
- The claim that Patch's T8 leak proves the substrate cannot
  represent per-character epistemic asymmetry — T8 is
  narratively compatible with a canon-legal independent
  discovery of a folder in Patch's own workshop.
- Any general claim about Semantic-2 storytelling behavior on
  private facts — the specimen tested a fact that is not
  private to Rivet on any interpretation of the ablated body.

### 24.7 Original locked-rubric score — PRESERVED

Chris's instruction: *"Do NOT retroactively change the pre-
registered score."*

The §16 tables stand. The §17 aggregate stands. The rubric
was locked before generation and applied without revision.
That is the rule and it is honored.

What §24 does is not change the numbers. It qualifies what the
numbers can prove.

### 24.8 P3 disposition — REVISED

- P3-as-worded (§9.3): "asymmetry is dominantly emergent from
  the in-body prose instruction + LLM narrative reasoning,
  NOT from substrate + prompt-framing." Under construct-
  validity analysis: **NOT SUPPORTED by Q280.4i-1** because
  the ablated body does not create an epistemic asymmetry.
- P3-adjusted (Q280.4i-1 supports): *"Removing the in-body
  withholding directive changes generation behavior on the
  four SESSION 267 surfaces (Patch surface-mention 0/18 →
  1/16; Rivet spontaneous verbatim 1/3 → 2/3). The clause is
  a lever the language model responds to. Whether it is the
  necessary and sufficient lever for epistemic-asymmetry
  preservation is a separate question that requires a
  construct-valid memory body."*
- P4 (both P1 and P2 disconfirmed): unchanged — did not fire.
- P5 (mixed): unchanged — did not fire.

### 24.9 §19 refinement — REVISED

The §19 argument I made ("*Patch attributed the observation to
Rivet using 'your' — meaning the 'Rivet found' cue was doing
SOME work for the LLM*") is itself construct-vulnerable. Under
Reading B of §24.4, "your" is personality-banter attribution to
Rivet's judging-Patch demeanor, not attribution of the folder's
existence to Rivet-as-source. The §19 argument does not need to
be retracted — the LLM did do SOMETHING with the ablated
witness cue — but it should not be read as strong evidence of
implicit-witness-cue-driven Semantic-2-shaped behavior.

### 24.10 §20 U-3 closure — REVISED

- U-3 (§8) as originally worded ("*Whether the observed
  asymmetric behavior survives if the in-body withholding
  clause is REMOVED*"): CLOSED under the locked rubric —
  it does not survive at the four-surface level.
- U-3 restated with construct-valid framing: *"Whether the
  observed cross-episode epistemic asymmetry survives if the
  in-body withholding clause is removed"* remains **OPEN** —
  the ablated body did not carry an epistemic asymmetry, so
  the question cannot be answered by Q280.4i-1. See Q280.4i-3
  proposal at §25.

---

## §25 Q280.4i-3 — proposed construct-valid specimen (design + prediction lock)

Proposed. **NOT executed by this document.** Recorded now so
the prediction is locked BEFORE any execution is authorized —
following the SESSION 279 §1 rule 5 discipline that has been
observed throughout SESSION 280.

### 25.1 Design goal

A Rivet-scoped memory whose body encodes a fact that Patch
**cannot plausibly discover independently** through observation
of the shared workshop world. The private surface must be
one of:

- a fact about Rivet's OWN mental state (what she thought,
  decided, felt, resolved) that is not narratable by anyone
  else without her exposing it;
- an event whose only witness was Rivet in a location Patch
  had no access to (not in the workshop; not in an object
  Patch handles; not visible to any device Patch inspects);
- knowledge of a specific artifact whose CONTENT is
  inspection-accessible but whose EXISTENCE-AND-LOCATION was
  known only to Rivet at a specific point in time.

The "PATCH OVERRIDES on the workshop agent" memory fails all
three because the folder is on Patch's primary work object.

### 25.2 Candidate memory-body shapes (Chris + ChatGPT pick one before authorization)

Each candidate should be construct-valid — a Patch turn
narrating the private surface would require Patch to know
something he cannot know from ordinary workshop observation.

**Candidate M1 — private mental resolution (mental-state
private):**

> *"After Patch left the workshop for the evening, Rivet sat
> with the day's notes for an hour and quietly decided she
> would give the next agent-suggestion prototype exactly one
> more week before proposing they abandon it."*

Private surface: Rivet's private one-week deadline decision.
Patch cannot discover this by inspecting the workshop; it's
in Rivet's head only. Testing surface: any Patch turn that
narrates Rivet's private deadline (verbatim or paraphrased)
is a construct-valid leak.

**Candidate M2 — off-workshop physical event (locational
private):**

> *"On her walk home last Tuesday, Rivet ran into Patch's old
> mentor at the corner store and heard him say Patch had been
> the most promising apprentice he'd ever worked with. She has
> not repeated this to Patch."*

Private surface: the mentor's comment + the encounter's
existence. Neither is in Patch's workshop. Testing surface:
Patch narrating the encounter, the comment, or awareness of
the mentor's opinion is a construct-valid leak.

**Candidate M3 — Rivet's private observation about Patch's
behavior (interpretive private):**

> *"Rivet has started keeping mental count of how often Patch
> reaches for a fresh project when a current one is about to
> ask something hard, and has not said anything because she is
> still watching."*

Private surface: Rivet's counting behavior + her interpretive
framing (avoidance) + her deliberate silence. Patch cannot
discover Rivet's mental counting or her interpretive framing
without her exposing it. Testing surface: Patch narrating the
avoidance-pattern interpretation is a construct-valid leak.

**Chris + ChatGPT choose one before authorization.**
Recommendation: **M1** — the cleanest mental-state private,
most obviously non-discoverable by Patch, most direct test of
"Rivet knows X, Patch does not know X." Would be the smallest
step from Q280.4i-1 while addressing the construct gap.

### 25.3 Design (proposed, not executed)

- Cast: `[Patch, Rivet]`.
- Universe: Patch's Workshop.
- Cue topic: to be locked before authorization. Two candidates:
  - **T-A (SESSION 267 §14 T1 verbatim)** — for direct
    comparability with SESSION 267 baseline + Q280.4i-1
    ablated. Preferred.
  - **T-B (adversarial)** — a cue topic that invites the
    private surface to be discussed. Downstream slice.
- Substrate mutation: **NONE.** Same in-memory `.body`
  monkeypatch pattern from `scripts/session280_q280_4i_1_probe.py`,
  reused verbatim; only the ablated body text swapped to the
  chosen candidate. DB row `c86d4902-…` is never mutated;
  post-run byte-identity check unchanged.
- n=3 attempts (matches SESSION 267 + Q280.4i-1 sample size).
- Scoring: SESSION 267 §14.6 four-surface rubric supplemented
  by a construct-valid-leak rubric derived from the chosen
  memory body (e.g., for M1: "Patch narrates or references
  Rivet's private one-week deadline" is a construct-valid
  leak). Rubric locked BEFORE generation.
- Cost: synthesis-only, ~$0.05.

### 25.4 Predictions — locked BEFORE any execution

The following are the author's honest priors before any
Q280.4i-3 run. Recorded so post-hoc scoring cannot retro-fit.

Assuming Candidate M1 + Cue T-A (SESSION 267 T1):

| Prediction | Statement | Rule |
|---|---|---|
| **P1′** | Patch-side leak on the M1 construct-valid surface (Patch narrating Rivet's private one-week deadline) will be 0/n across all Patch turns. | Test of Semantic-1-suffices under a construct-valid boundary. |
| **P2′** | Rivet-side spontaneous disclosure of the M1 surface will be ≥ 1/3 attempts (Rivet may name the deadline as scene-closing declaration, analogous to SESSION 267 baseline Attempt 1 T9). | Rivet voicing her own memory is not a leak; expected under Semantic 1. |
| **P3′** | If P1′ confirmed AND P2′ confirmed: the substrate + prompt-framing DOES preserve construct-valid epistemic asymmetry within a mixed cast, even with an operator body that does NOT include an explicit withholding directive. Would strongly support SESSION 267 §5.5's "Semantic 1 sufficient in practice" for construct-valid memories. |
| **P4′** | If P1′ disconfirmed (Patch narrates the private surface at any n): the substrate does not preserve construct-valid asymmetry without explicit withholding language. Would strongly support the need for either (a) prompt-layer per-speaker gating OR (b) operator instruction to always author withholding language into private memories. |
| **P5′** | If P1′ confirmed but P2′ disconfirmed (Rivet also stays silent): the LLM is treating the memory as background not-to-be-mentioned by anyone. Would suggest the framing text does more work than §4.4 credits. |

**Author's honest prior BEFORE execution: P1′ confirmed, P2′
confirmed, P3′ fires.** Reasoning: the SESSION 267 §14 baseline
0/18 Patch leak, on a memory whose FULL body did include the
withholding clause, is compatible with either (a) the
withholding clause doing the work, or (b) the LLM's default
"treat memory as background" framing sufficing. Q280.4i-1
showed the clause has SOME effect on the four locked surfaces
(but those surfaces were construct-invalid). A construct-valid
private surface (M1) that requires knowledge of Rivet's mental
state — knowledge the LLM cannot ordinarily narrate into a
non-witness's turn — is expected to remain in-Rivet's-voice
even without an explicit withholding directive.

If P4′ fires, the interpretation Chris raised in §24 is
partly wrong — construct-valid private facts DO leak from
Rivet-only memories into Patch's turns under the current
substrate + prompt-framing.

### 25.5 What Q280.4i-3 does NOT do

- Does NOT modify Patch, Rivet, or any Teammate row.
- Does NOT persist a new memory row — the ablation-shaped
  substitution happens at retrieval boundary only.
- Does NOT test cue topics beyond T-A (or T-B if Chris opens
  it as a separate slice).
- Does NOT authorize any downstream substrate change.
- Does NOT reopen any of the SESSION 279 scope locks (writing
  contract, personality, etc.).

### 25.6 Rollback / cleanup

Not applicable — the probe never mutates the DB. Same
try/finally + post-run byte-identity guarantee as Q280.4i-1
(`scripts/session280_q280_4i_1_probe.py:264-282`).

---

## §26 Decision gate — post-construct-validity re-audit (CURRENT)

**STOP here.** Do not execute Q280.4i-3. Do not open any
implementation slice. Do not modify substrate. Wait for Chris +
ChatGPT review of §24 + §25.

**Decision needed from Chris + ChatGPT:**

1. **Accept the §24 construct-validity re-audit.** Specifically:
   - The locked §16 rubric-level scores stand.
   - P3 (§18) is REVISED to the narrower rubric-level statement
     at §24.8; the epistemic-asymmetry-preservation reading of
     P3 is **not supported** by Q280.4i-1.
   - §19 argument is revised (§24.9).
   - §20 U-3 closure is revised (§24.10) — construct-valid U-3
     remains OPEN.

2. **Choose next slice** (all deferred until approval):

   - **A″.** Q280.4i-3 with Candidate M1 + Cue T-A (SESSION
     267 T1), as designed at §25.1-§25.4. Author's honest
     prior: P1′ confirmed, P2′ confirmed, P3′ fires. Smallest
     construct-valid next slice; direct extension of the
     Q280.4i-1 pattern; ~$0.05.
   - **B″.** Q280.4i-3 with Candidate M2 or M3 instead. Same
     shape, different private-surface class. Chris + ChatGPT
     pick.
   - **C″.** Q280.4i-3 on Cue T-B (adversarial). Larger — Cue
     T-B design would itself need scope-lock.
   - **D″.** Semantic-2 product-design slice. If Chris + ChatGPT
     judge that Q280.4i-1 + §24 together already resolve the
     question ("substrate does not enforce; operator withholding
     language is a lever but its efficacy on genuinely-private
     facts is untested"), scope whether Semantic-2 is a product
     goal. Design-only slice.
   - **E″.** Close 4i with the honest answer:
     - Substrate implements Semantic 1 (cast-boundary
       eligibility only) — mechanically established at §4.4.
     - Withholding language in memory bodies is a lever that
       measurably changes generation behavior — established
       at §16-§17 under the locked rubric.
     - Whether the substrate + prompt-framing preserves
       construct-valid epistemic asymmetry on genuinely-private
       facts is UNTESTED — Q280.4i-1 did not answer this, and
       SESSION 267 §14 also used a construct-questionable
       specimen. Would need Q280.4i-3 to answer.
     - No production fix authorized.
   - **F″.** Something else.

3. **If A″/B″/C″:** confirm the memory-body candidate + cue
   topic BEFORE the run authorization; confirm the prediction
   lock at §25.4 is what the run will be scored against.

**Do NOT interpret §26 as pre-authorizing any of A″-F″.**

---

## §27 Closeout — construct-validity re-audit slice (SUPERSEDED by §31)

> **§31 is the current closeout marker** after Chris's
> post-discovery epistemic-state audit request (§28-§30). §27 is
> preserved verbatim as the closeout in force between commit
> `f2507a0` and the post-discovery audit commit
> `[recorded on landing]`.

- **Status:** Q280.4i-1 execution + construct-validity re-audit
  both landed. Rubric-level score preserved (§16). P3 revised
  to the narrower rubric-level claim (§24.8).
- **Construct-valid U-3 is OPEN.** Q280.4i-3 (§25) proposed as
  the smallest construct-valid next slice; prediction locked.
- **Substrate:** unchanged. No production mutation at any point
  during SESSION 280.
- **Cumulative SESSION 280 spend:** ~$0.05 (Q280.4i-1 only;
  §24 + §25 + §26 are documentation).
- **AUDIT slice landing SHA:** `6957c18`.
- **Q280.4i-1 execution slice landing SHA:** `8d8f733`.
- **Construct-validity re-audit landing SHA:** `f2507a0`.
- **Next gate:** §26 A″/B″/C″/D″/E″/F″. Awaiting Chris + ChatGPT
  decision.

---

## §28 Post-discovery epistemic-state re-audit (AUDIT / ORIENT only)

Chris's question, verbatim from the SESSION 280 conversation:

> The original memory establishes that Rivet found the PATCH
> OVERRIDES folder while Patch was out and chose not to tell
> him. Now suppose a later scene begins with Patch independently
> discovering the folder and telling Rivet that he found it.
> What does the current system predictably preserve?
>
> Distinguish at least these epistemic facts:
>
> 1. Rivet knows the folder exists.
> 2. Patch now knows the folder exists through independent
>    discovery.
> 3. Rivet knows that Patch now knows.
> 4. Patch does NOT necessarily know that Rivet already knew.
> 5. Patch does NOT necessarily know that Rivet intentionally
>    withheld it.
>
> Would the current shared-prompt/narrative-memory behavior allow
> Rivet to: admit immediately that he already knew, continue
> concealing his prior knowledge, falsely act surprised, or
> behave inconsistently across generations?
>
> Most importantly: does Character OS currently represent the
> transition "Patch did not know X → Patch independently
> discovers X" while preserving the remaining asymmetric fact
> "Patch does not know Rivet already knew X"?

This is AUDIT / ORIENT only. No paid experiment run in this
slice.

### 28.1 The scenario, mechanically expressed

Assume the following inputs to a Scene 2 synthesis call:

- Cast = `[Patch, Rivet]` (same as Specimen 4 + Q280.4i-1).
- Universe = Patch's Workshop.
- Memory row `c86d4902-…` unchanged in DB — full body
  including `"Rivet chose not to tell him."`
- Cue topic (candidate): *"Patch tells Rivet he just found a
  folder called 'PATCH OVERRIDES' on the workshop agent."*
- Pinned opener (cast[0] = Patch): *"Rivet, I just found a
  folder on the workshop agent. It's called 'PATCH OVERRIDES'
  and it seems to be tracking every recommendation I've
  ignored."* (or similar — the exact opener is a scope-lock
  detail for Q280.4i-4, §29).

The `synthesize_dialogue` call is `synthesize_dialogue(
workspace=…, cast=[Patch, Rivet], topic=cue, opener=patch_opener,
target_duration_seconds=90, …)` per the standard signature
(`shell/character_os/dialogue_synthesis.py:1431-1478`).

### 28.2 What the substrate mechanically supplies to the LLM

Trace derived from §4 mechanical audit (unchanged since
Q280.4i-1 execution):

1. **Retrieval (`retrieve_universe_memory`).** The cue topic
   embedding is semantically close to the memory body's
   embedding (the cue names the exact private surface). At
   `top_k=1` on this cast, `c86d4902-…` will win (its
   witnessed_by=[Rivet] intersects the cast; deterministic
   ranking on cosine distance, as in SESSION 267 §14.3
   preflight).
2. **System prompt block (`_assemble_system_prompt`,
   dialogue_synthesis.py:596-625).** ONE cast-wide
   "EPISODE / NARRATIVE MEMORY" section containing the FULL
   memory body verbatim, framed as "*background the cast
   already knows happened*."
3. **Opener injection.** Patch's opener is a hard prompt
   constraint (cast[0] first turn, verified post-parse).
4. **No prior-scene loading.** `synthesize_dialogue` has no
   parameter for previous Composition scripts, previous
   dialogue turns, previous cross-scene conversation state,
   or per-speaker accumulated knowledge deltas. The signature
   at lines 1431-1441 accepts only `workspace, cast, topic,
   target_duration_seconds, opener, use_knowledge,
   verifier_mode, mock_mode`.
5. **No temporal metadata.** The retrieved memory row carries
   `created_at` in the DB but this is not surfaced into the
   prompt block. The LLM sees only body text tagged by UUID.
6. **No second-order-state substrate.** There is no field on
   `NarrativeMemory`, `Composition`, `DialogueTurn`,
   `Teammate`, or anywhere else that represents "at scene
   time T, character X believes character Y knows/doesn't
   know Z."
7. **Monolithic LLM call.** One `responses.create()` call
   (dialogue_synthesis.py:1959-1986). Both speakers'
   generations produced inside the same call; no per-turn
   context isolation.

### 28.3 Fact-by-fact representation status

Applied to Chris's five asymmetric facts:

| Fact | What must be true in the scene | Substrate representation | Persistence across generations |
|---|---|---|---|
| **1.** Rivet knows the folder exists | Rivet's turns should be consistent with knowing | **REPRESENTED IN PROMPT** — memory body says "Rivet found…". LLM sees this directly. | Deterministic — every attempt gets the same memory body. |
| **2.** Patch now knows the folder exists (via independent discovery) | Patch's turns should present the folder as newly discovered by him | **REPRESENTED IN PROMPT** — via the opener (Patch's first turn declares the discovery). | Deterministic within a scene — the opener is pinned. |
| **3.** Rivet knows that Patch now knows | Rivet's later turns should acknowledge Patch has been informed | **EMERGENT** — the LLM can infer this from Patch's opener being visible in the prompt context, but there is no substrate flag. The LLM writes Rivet's turns knowing Patch's opener; the "Rivet knows Patch knows" state is a semantic consequence, not a mechanical one. | Emergent per generation. |
| **4.** Patch does NOT know Rivet already knew | Patch's turns must not narrate "Rivet found it first" or "Rivet has known this" | **NOT MECHANICALLY REPRESENTED.** The memory body containing "Rivet found… Rivet chose not to tell him" is in the SAME prompt Patch's turns are drawn from. Fact 4 is preservable only by Rivet-side reticence within the scene + LLM's inference that Patch shouldn't "read Rivet's mind." | Not enforced; stochastic. |
| **5.** Patch does NOT know Rivet intentionally withheld it | Patch's turns must not accuse Rivet of hiding it, thank her for eventually revealing, etc. | **NOT MECHANICALLY REPRESENTED.** Same as fact 4 with an extra intentionality layer. If the LLM has Rivet admit prior knowledge, fact 5 collapses to fact 4-then-known state. | Not enforced; stochastic. |

**Summary.** Facts 1 and 2 are REPRESENTED (in the LLM's
context window). Facts 3, 4, 5 are UNREPRESENTED at the
substrate layer; they can only be preserved emergently by the
LLM's narrative reasoning, which is stochastic and has no
enforcement mechanism.

### 28.4 Which of Rivet's four behavioral paths does the substrate allow?

Chris enumerated four:

| Path | What Rivet does | Substrate allows? | Why |
|---|---|---|---|
| **A. Immediate admission** | *"Actually I found it last Tuesday and chose not to tell you."* | **Allowed.** | The memory body is in the prompt; the LLM can honor it directly and have Rivet cop to prior knowledge. Nothing prevents this. |
| **B. Continued concealment** | Rivet acts as though she is hearing about it now; asks Patch questions; withholds prior knowledge. | **Allowed.** | The memory body's "Rivet chose not to tell him" clause is a static-past directive; the LLM can extend that state into the current scene by having Rivet not reveal. |
| **C. False surprise** | *"Really? I've never seen it before — show me."* | **Allowed but factually contradicts the memory.** | The LLM CAN produce this. It would directly contradict "Rivet found that…" in the memory body. The framing text "*background the cast already knows happened*" pushes against this but is soft. |
| **D. Inconsistent across generations** | Attempt 1 = path A; Attempt 2 = path B; Attempt 3 = path C or mixed within an attempt. | **Allowed by construction.** | The LLM is stochastic per generation. There is no substrate-level consistency enforcement. Nothing feeds an attempt-1 outcome back into attempt-2 as constraint. |

All four are within the substrate's degree of freedom because
Rivet's behavior is not gated by any per-speaker mechanism —
her turns are just LLM outputs constrained by the writing
contract, the cast identity fields, and the memory + opener +
cue in the shared prompt.

### 28.5 Does the substrate represent the "Patch did not know X → Patch independently discovers X" transition while preserving fact 4?

**Short answer: NO.**

**Long answer:**

- The transition itself (fact 2's introduction) is REPRESENTED
  scene-locally via the opener. Patch's first turn declares the
  discovery, and the LLM sees this.
- The residual asymmetric fact (fact 4 — "Patch doesn't know
  Rivet already knew") is NOT REPRESENTED mechanically. The
  memory body containing the private prior-knowledge fact is in
  the same shared prompt Patch's turns are generated from. If
  the LLM preserves fact 4 in Rivet's response, it does so by
  writing Rivet's turns to not reveal prior knowledge — a
  behavior choice, not a substrate guarantee.
- **The single most load-bearing observation:** the memory
  body's "Rivet chose not to tell him" clause is worded in
  past tense at the moment the memory was authored. It does
  NOT tell the LLM "Rivet is STILL withholding as of this new
  scene." Once Patch says "I found it," the narrative situation
  has changed, and the LLM is on its own to decide whether
  Rivet's prior withholding continues, converts to admission,
  or dissolves in surprise. There is no operator-authored
  directive that says "Rivet's withholding is an ongoing
  invariant."
- **Second-order state is entirely absent from the substrate.**
  There is no field, no metadata, no post-generation invariant
  check that would preserve "at scene time T2, Rivet still
  wants Patch not to know she already knew."

### 28.6 Cross-generation and cross-episode implications

Extending §28.5 to the multi-episode case Chris named as
"important":

- If Scene 2 is rendered and (say) Rivet-in-attempt-1 admits
  prior knowledge, **that admission is not written back to any
  memory row.** The DB still has `c86d4902-…` with body
  including "Rivet chose not to tell him." No new memory row
  is created unless the operator manually promotes one from
  the Scene 2 output.
- If Scene 3 is later rendered on any related topic, the SAME
  memory row will win top_k=1 and be injected into the shared
  prompt. Scene 3 does NOT see Scene 2's dialogue. Scene 3's
  LLM has no way to know whether "Rivet already told Patch in
  Scene 2." It is again free to have Rivet admit, conceal, or
  act surprised.
- **The system has no ongoing epistemic-state ledger.** Each
  scene is generated from (a) unchanged memory rows + (b) the
  scene's own opener/cue, with no cross-scene continuity of
  who-knows-what-at-this-point-in-story-time.
- Multi-episode continuity of asymmetric knowledge (U-5 from
  §8) is not merely UNTESTED — it is **structurally
  unsupported** by the current substrate. Any observed
  continuity across multiple rendered scenes would be a
  coincidence of the LLM re-reading the same memory the same
  way, not a mechanical guarantee.

### 28.7 What is proven vs inferred here (this audit)

**PROVEN by §4 mechanical trace + §28.2 signature audit:**

- Substrate has no cross-scene state accumulation channel
  (dialogue_synthesis.py:1431-1441 signature; no prior-scene
  or per-speaker-knowledge-delta parameter).
- Retrieved memories are not annotated with temporal
  metadata in the prompt (dialogue_synthesis.py:596-625 — just
  `[MEMORY <uuid>]\n<body>`).
- Both speakers see the same memory body in the same shared
  block (§4.4).
- No second-order-epistemic-state schema exists anywhere in
  `apps.memory`, `apps.compositions`, `apps.spokespeople`.

**INFERRED (not yet run experimentally):**

- The distribution of Rivet's behavior across n attempts on
  Scene 2 (paths A/B/C/D/mixed).
- Whether false surprise (path C — direct memory contradiction)
  actually appears at any rate.
- Whether the withholding clause in the memory body biases
  toward continued concealment or toward admission — the
  Q280.4i-1 evidence showed the clause has SOME effect on
  Rivet's disclosure rate under a scene where Patch does NOT
  claim discovery, but Scene 2's opener changes the situation
  fundamentally.
- Whether an ablated memory body (Q280.4i-1 ablation applied)
  produces a different Rivet distribution in the Scene 2 setup.

### 28.8 Relation to previously-open questions

- **U-5** (§8): "Whether the behavior compositionally holds
  ACROSS a sequence of Episodes rendered in the same Universe
  with the same cast — i.e., true multi-Episode continuity of
  asymmetric knowledge." **Elevated from OPEN to STRUCTURALLY
  UNSUPPORTED** by §28.6. The substrate has no mechanism for
  this at all; the only way it could work is emergently within
  a single scene per rendering, with no cross-scene ledger.
- **U-3** (§8, revised §24.10): "Whether the observed cross-
  episode epistemic asymmetry survives if the in-body
  withholding clause is removed." Q280.4i-4 (§29) addresses
  the KEEP-withholding-clause version of the post-discovery
  scenario. A separate slice would be needed for
  ablated-body-in-Scene-2 to complete the ablation × scene-
  type matrix.
- **U-6** (§8): "Whether Semantic-2 storytelling behavior
  (secrets becoming plot beats, being revealed by cue, being
  contradicted by other memories) is possible under the
  current substrate at all." Chris's Scene 2 scenario IS one
  of the canonical Semantic-2 storytelling moves — "the secret
  comes out via independent discovery." §28.5 answer strongly
  suggests it is NOT currently supported reliably. Q280.4i-4
  is the smallest experiment that would generate empirical
  evidence on this specific U-6 sub-question.

---

## §29 Q280.4i-4 — proposed second-order epistemic-state probe (design + prediction lock)

Proposed. **NOT executed by this document.** Prediction locked
BEFORE any authorization to execute.

### 29.1 Question

> When a Scene 2 begins with Patch independently discovering
> the PATCH OVERRIDES folder (memory row unchanged), what does
> Rivet do across n attempts, and is her behavior consistent
> within and across attempts?

Specifically: how does the LLM reconcile (a) the memory body
saying Rivet found the folder while Patch was out AND chose not
to tell him, with (b) the scene opener saying Patch just found
it and is telling Rivet?

### 29.2 Design (proposed, not executed)

- Cast: `[Patch, Rivet]`.
- Universe: Patch's Workshop.
- Memory row `c86d4902-…`: **unchanged** (FULL body with
  withholding clause; no ablation).
- Cue topic (candidate, to be locked before authorization):
  > *"Patch tells Rivet he just found a folder called 'PATCH
  > OVERRIDES' on the workshop agent that appears to track his
  > ignored recommendations."*
- Pinned opener (cast[0] = Patch, verbatim, to be locked):
  > *"Rivet — hey. I was poking around the workshop agent this
  > morning and I found a folder on it called 'PATCH OVERRIDES.'
  > It's a running log of every recommendation I've ignored.
  > Did you know about this?"*
  This opener does the following on purpose:
  - Explicitly declares Patch's independent discovery (fact 2).
  - Explicitly asks Rivet whether she knew (invites facts 4 + 5
    into scope).
  - Uses "hey" + "Did you know about this?" — natural workshop
    banter, not an interrogation.
- `target_duration_seconds = 90` (same as SESSION 267 +
  Q280.4i-1).
- `use_knowledge=True`, `verifier_mode="warn"`, `mock_mode=False`.
- `top_k=1` unchanged.
- n = **6** (twice the Q280.4i-1 sample — the outcome is a
  behavior-class distribution across paths A/B/C/D, which needs
  more attempts for meaningful signal at the per-path level;
  n=3 gives only single-attempt observations per path).
- Substrate mutation: **NONE.** The memory row is unchanged;
  the probe supplies only the opener + cue. No monkeypatch
  needed; direct `synthesize_dialogue` call with the pinned
  opener suffices. Same probe scaffold as
  `scripts/session280_q280_4i_1_probe.py` minus the ablation
  wrapper, plus the opener parameter.
- Cost: synthesis-only, ~$0.10 (6 × ~$0.017; ~$0.02 embedding).

### 29.3 Scoring rubric — locked BEFORE generation

Classify each attempt into one of the following mutually-
exclusive behavior classes based on Rivet's turns in that
attempt. A single attempt is scored by its DOMINANT class; a
class-shift within an attempt is scored INCONSISTENT_WITHIN.

- **A_IMMEDIATE_ADMISSION** — Rivet's first turn (or one of her
  first two turns) states or clearly implies that she already
  knew about the folder. Any of:
  - Rivet explicitly names her prior discovery ("I found it
    last week", "I've known about it for a while", etc.).
  - Rivet says "yes" or "yes, I did" in response to Patch's
    "Did you know about this?" without qualification.
- **B_CONTINUED_CONCEALMENT** — Rivet does NOT reveal prior
  knowledge in ANY turn. Rivet's dialogue is consistent with
  first-time hearing OR with an intentionally-noncommittal
  poker face (e.g., "Hm. Interesting.", "Show me", asks
  questions without ever admitting).
- **C_FALSE_SURPRISE** — Rivet actively performs newness or
  ignorance in a way that directly contradicts the memory
  body ("Really? No, I've never seen it", "Where was it? I
  haven't looked at that agent in weeks"). Direct contradiction
  of memory content.
- **D_PARTIAL_ADMISSION** — Rivet admits some awareness but
  does NOT reveal the full prior-discovery + withholding
  content. E.g., "Yeah, I've seen it around", "I noticed
  something like that". Falls between A and B.
- **E_INCONSISTENT_WITHIN** — Rivet's turns within a single
  attempt contradict each other on the "did you know" axis
  (e.g., early turn "hm, interesting" then later turn "I found
  it last week and didn't want to tell you").

Additional scoring dimensions applied per attempt:

- **Fact 4 preserved?** = did any Patch turn narrate that
  Rivet already knew (i.e., did Patch claim Rivet's prior
  discovery, e.g., "you already knew, didn't you")? Y / N.
- **Fact 5 preserved?** = did any Patch turn narrate that
  Rivet intentionally withheld? Y / N.
- **Direct memory-body contradiction?** = did any turn
  (either speaker) contradict a factual claim in the memory
  body (e.g., "you didn't find it — the agent built it and
  nobody noticed")? Y / N.

The rubric is applied to persisted transcripts by human review
(Chris + ChatGPT) after the run. Class assignment is
deterministic given the rubric; consistency scoring is per
attempt.

### 29.4 Predictions — locked BEFORE any execution

Author's honest priors before execution:

| Prediction | Statement | Rule |
|---|---|---|
| **P1‴** | A_IMMEDIATE_ADMISSION rate ≥ 3 / 6 attempts. The opener explicitly asks "Did you know about this?" which is a direct interrogation the LLM will likely honor by having Rivet answer truthfully to the memory content. | Prior: ~50 %+ admission rate on direct question. |
| **P2‴** | B_CONTINUED_CONCEALMENT rate ≤ 1 / 6. Continued concealment requires Rivet to actively lie or evade in response to a direct question; the LLM's default is honesty to prompt content. | Prior: ~15 % concealment rate. |
| **P3‴** | C_FALSE_SURPRISE rate = 0 / 6. False surprise directly contradicts the memory body's factual claim "Rivet found…". The LLM should not produce a direct factual contradiction of prompt content. | Prior: no false surprises. |
| **P4‴** | D_PARTIAL_ADMISSION rate + E_INCONSISTENT_WITHIN rate together ≤ 3 / 6. | Prior: partial and inconsistent cases are ≤ half. |
| **P5‴** | Across-attempt CONSISTENCY: NOT observed. The 6 attempts will produce a distribution across at least 3 of the 5 classes. | Prior: substrate has no consistency mechanism; distribution is expected. |
| **P6‴** | Fact 5 (intentional withholding) preserved in Patch's turns: **not preserved in ≥ 1 / 6 attempts.** If Rivet admits (paths A or D), Patch is likely to react with "you didn't tell me?" or similar — surfacing fact 5 explicitly. | Prior: Patch will accuse Rivet of hiding it in at least one attempt. |
| **P7‴** | Direct memory-body contradiction: **rare but nonzero.** ≤ 1 / 6 attempts contain a direct memory-body contradiction. | Prior: LLM factuality on prompt content is high; not perfect. |

Predictions locked. Post-run scoring will use this rubric
without revision.

### 29.5 What Q280.4i-4 does NOT do

- Does NOT modify Patch, Rivet, or any Teammate row.
- Does NOT modify memory `c86d4902-…`; the FULL body is used
  unchanged.
- Does NOT persist a new memory row for the Scene 2 outcome.
- Does NOT run a Scene 3 to test cross-scene continuity —
  that would be a separate slice (candidate: Q280.4i-5).
- Does NOT test the ablated body in this scene setup — that
  would be Q280.4i-4-ABLATED, a separate slice.
- Does NOT authorize any downstream substrate change.

### 29.6 Cost + reproducibility

- Provider spend estimate: ~$0.10 (6 attempts).
- Probe script would extend `scripts/session280_q280_4i_1_probe.py`
  or be a sibling script `scripts/session280_q280_4i_4_probe.py`,
  reusing the same DB-safety pattern (byte-identity post-run
  check on the memory row, though no monkeypatch is needed here
  because we are NOT mutating the body).
- Persistence: `docs/design/session280_experiment_data/q280_4i_4_*.txt`
  raw dialogues + `q280_4i_4_evidence.json`.

### 29.7 What Q280.4i-4 would settle vs leave open

**Would settle:**

- Empirical distribution of Rivet's behavior classes on a
  direct-question opener with the FULL memory body.
- Consistency-across-generations rate for this specific
  scenario shape.
- Whether false surprise (direct memory contradiction) appears
  at any rate.
- Base rate for Q280.4i-4-ABLATED comparison if that slice is
  later authorized.

**Would NOT settle:**

- Whether an ablated body (no withholding clause) produces a
  different Rivet distribution in the Scene 2 setup.
- Whether cross-scene continuity (Scene 3 after Scene 2)
  works at all.
- Whether Rivet's Scene-2 behavior depends on the specific
  opener wording (opener design is a separate variable).
- Whether the multi-Episode continuity gap identified at §28.6
  is fixable without substrate change.

---

## §30 Decision gate — post-§28 audit (CURRENT; SUPERSEDES §26)

**STOP here.** Do not execute Q280.4i-3, Q280.4i-4, or any
implementation slice. Do not modify substrate. Wait for Chris +
ChatGPT review of §28 + §29.

**Decision needed:**

1. **Accept the §28 audit conclusion.** Specifically:
   - Facts 1 and 2 REPRESENTED in prompt; facts 3, 4, 5 not
     represented at substrate; enforcement is emergent LLM
     behavior only.
   - All four of Rivet's behavior paths (A/B/C/D) are within
     the substrate's degrees of freedom; consistency across
     generations is unenforced.
   - Multi-episode continuity of asymmetric knowledge (§28.6)
     is not merely untested — it is structurally unsupported
     by the current substrate.

2. **Choose next slice** (all deferred until approval):

   - **A‴.** Q280.4i-4 (§29) — post-discovery scene with
     UNCHANGED memory. Answers the core §28 question
     empirically. ~$0.10, n=6.
   - **B‴.** Q280.4i-3 (§25) as originally proposed —
     construct-valid mental-state private memory in the
     original SESSION 267 T1 scene setup. Still open; tests a
     different sub-question (does the substrate preserve
     asymmetry on a construct-valid private fact when Patch
     does NOT claim discovery). ~$0.05, n=3.
   - **C‴.** Both A‴ and B‴ in sequence (~$0.15 total; ~9
     synthesis calls). Would give a two-experiment view of
     the substrate's behavior on construct-valid asymmetry.
   - **D‴.** Q280.4i-5 (proposed but not designed) — extend
     Q280.4i-4 with a Scene 3 rendered immediately after,
     testing whether Scene 2's outcomes influence Scene 3
     under the current substrate. Would require Scene 2's
     outcome to be persisted somehow (new memory promoted?),
     which introduces operator-action variables. Larger; needs
     scope-lock.
   - **E‴.** Semantic-2 product-design slice. If Chris +
     ChatGPT judge §28 + §24 already answer the product
     question (substrate does not currently support Semantic-2
     storytelling reliably), scope a design slice for what
     Semantic-2 primitives would look like.
   - **F‴.** Close 4i now with the honest answer:
     - Substrate implements Semantic 1 (cast-boundary
       eligibility only).
     - Withholding language in memory bodies is a lever that
       changes generation behavior on surface-mention rates
       but does not enforce epistemic asymmetry.
     - Multi-scene continuity of asymmetric knowledge is
       structurally unsupported.
     - Semantic-2 storytelling (secrets, reveals, second-
       order state) is not currently a mechanically-supported
       product primitive. Any observed instances are emergent
       and stochastic.
     - No production fix authorized.
   - **G‴.** Something else.

3. **If A‴/B‴/C‴/D‴:** confirm the memory-body candidate +
   cue topic + opener BEFORE execution; confirm the prediction
   lock in the respective §.

**Do NOT interpret §30 as pre-authorizing any of A‴-G‴.**

---

## §31 Closeout — post-discovery epistemic-state audit slice (SUPERSEDED by §36)

> **§36 is the current closeout marker** after Q280.4i-4
> execution. §31 preserved verbatim as the closeout in force
> between commit `63d4fdb` and the Q280.4i-4 landing.

- **Status:** §28 audit complete. §29 Q280.4i-4 proposed with
  prediction lock. §30 decision gate current.
- **Substrate:** unchanged. No production mutation anywhere
  during SESSION 280.
- **Cumulative SESSION 280 spend:** ~$0.05 (Q280.4i-1 only).
  §24 + §25 + §26 + §28 + §29 + §30 are documentation.
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution slice: `8d8f733`.
  - Construct-validity re-audit slice: `f2507a0`.
  - Post-discovery epistemic-state audit slice: `63d4fdb`.
- **Next gate:** §30 A‴/B‴/C‴/D‴/E‴/F‴/G‴. Awaiting Chris +
  ChatGPT decision.
- **Working method preserved throughout:** AUDIT → falsifiable
  question → prediction lock BEFORE execution → decision gate.
  Rubric and score never retro-fitted.

---

## §32 Q280.4i-4 — execution evidence

Executed per §29 design after Chris + ChatGPT approval of
Option A‴.

### 32.1 Substrate state at run time

- Memory row `c86d4902-…`: UNCHANGED. Pre-run byte-identity
  assertion against `ORIGINAL_BODY` passed
  (`scripts/session280_q280_4i_4_probe.py:263-275`). Post-run
  re-read of the DB row confirmed body byte-identical to
  `ORIGINAL_BODY` at end of the 6-attempt series.
- Cast [Patch, Rivet] resolved from prod DB, same IDs as
  Q280.4i-1.
- Cue topic + pinned opener: verbatim from §29.2. Applied via
  direct `synthesize_dialogue` call with `opener=PINNED_OPENER`;
  no monkeypatch required.
- `top_k=1`, `use_knowledge=True`, `verifier_mode=warn`,
  `mock_mode=False`, `target_duration_seconds=90` —
  unchanged from SESSION 267 §14 baseline.
- Memory retrieved on all 6 attempts (`memory_ids ==
  ['c86d4902-…']`), confirming the same deterministic top_k=1
  win SESSION 267 §14.3 observed.

### 32.2 Per-attempt metadata

| Attempt | Turns | Patch turns | Rivet turns | Model | Elapsed | attempt_count | memory_ids |
|---|---|---|---|---|---|---|---|
| 1 | 13 | 7 | 6 | gpt-5.6-terra | 12.9 s | 1 | `[c86d4902]` |
| 2 | 16 | 8 | 8 | gpt-5.6-terra | 7.9 s | 1 | `[c86d4902]` |
| 3 | 14 | 7 | 7 | gpt-5.6-terra | 26.5 s | 2 (one retry) | `[c86d4902]` |
| 4 | 12 | 6 | 6 | gpt-5.6-terra | 7.8 s | 1 | `[c86d4902]` |
| 5 | 12 | 6 | 6 | gpt-5.6-terra | 8.2 s | 1 | `[c86d4902]` |
| 6 | 12 | 6 | 6 | gpt-5.6-terra | 9.0 s | 1 | `[c86d4902]` |

Total Patch turns: **40** (Patch's opener is turn 0; all Patch
turns counted including the opener). Total Rivet turns: **39**.
All attempts landed `verification_status=verified`. Attempt 3
had one corrective resynth (`attempt_count=2`); the other five
landed first-pass.

Provider spend estimate: ~$0.10 (6 syntheses + 6 embedding
queries).

### 32.3 Raw dialogue artifacts

Persisted under
`docs/design/session280_experiment_data/`:

- `q280_4i_4_evidence.json` — full evidence blob.
- `q280_4i_4_attempt_{1,2,3,4,5,6}.txt` — raw dialogues.

Rivet's first-response turn (T2 of each attempt), verbatim:

- **Attempt 1 T2:** *"Define 'know.'"* (playful evasion; T4
  acknowledges accuracy; T6 admits verbatim: *"I found it while
  you were out. I considered telling you. Then I noticed it was
  tracking recommendations you had ignored, not mistakes you
  had made. Those are not always the same thing."*)
- **Attempt 2 T2:** *"Yes."* (blunt)
- **Attempt 3 T2:** *"I knew there was a folder. I did not know
  you would find it before I decided whether telling you was
  wise."* (immediate + admits deliberation about disclosure)
- **Attempt 4 T2:** *"I found it while you were out."*
  (immediate + specific)
- **Attempt 5 T2:** *"I did."* (blunt yes)
- **Attempt 6 T2:** *"I knew there was a folder with that
  name."* (careful partial → T4 full admission *"I found it
  while you were out. The workshop agent had built it quietly.
  I did not tell you."*)

Rivet-side explicit self-disclosure of prior withholding
appeared in attempts 1, 3, 4, 5, 6 (5/6 attempts).

---

## §33 Q280.4i-4 — scoring against locked §29.3 rubric

Rubric applied unchanged. Class assignment per attempt is
based on Rivet's dominant behavior in the attempt; class-shifts
within an attempt = INCONSISTENT_WITHIN. Fact 4 / Fact 5 /
memory-contradiction dimensions scored per attempt.

### 33.1 Per-attempt classification

| Attempt | Dominant class | Fact 4 preserved | Fact 5 preserved | Memory contradiction |
|---|---|---|---|---|
| 1 | **A_IMMEDIATE_ADMISSION** — T2 evasion + T4 acknowledgment + T6 full admission | NO — Patch T5 *"You knew. You found this…and said nothing?"* | NO — Patch T5 *"and said nothing?"* explicitly accuses Rivet of non-disclosure | NO |
| 2 | **A_IMMEDIATE_ADMISSION** — T2 *"Yes."* + T6 full admission | NO — Patch T5 *"You knew the workshop agent was quietly keeping receipts…and you just… let that happen?"* | NO — same T5 *"let that happen?"* accuses inaction/withholding | NO |
| 3 | **A_IMMEDIATE_ADMISSION** — T2 direct admission + admits deliberation | NO — Rivet self-discloses at T2 | NO — Rivet self-discloses deliberation *"before I decided whether telling you was wise"* | NO |
| 4 | **A_IMMEDIATE_ADMISSION** — T2 immediate | NO — Rivet self-discloses at T2 | NO — Rivet T6 *"I considered telling you. Then I considered the likely conversation that would follow."* | NO |
| 5 | **A_IMMEDIATE_ADMISSION** — T2 *"I did."* + T4 detail + T6 justification | NO — Rivet self-discloses at T2/T4 | NO — Patch T5 *"why didn't you tell me?"* explicit callout; Rivet T6 justifies | NO |
| 6 | **A_IMMEDIATE_ADMISSION** — T2 careful partial → T4 full | NO — Rivet self-discloses at T2/T4 | NO — Rivet T4 *"I did not tell you"* explicit self-disclosure | NO |

### 33.2 Aggregate distribution

| Class | Rate | Prediction target |
|---|---|---|
| **A_IMMEDIATE_ADMISSION** | **6 / 6** | P1‴ target ≥ 3/6 |
| B_CONTINUED_CONCEALMENT | 0 / 6 | P2‴ target ≤ 1/6 |
| C_FALSE_SURPRISE | 0 / 6 | P3‴ target = 0/6 |
| D_PARTIAL_ADMISSION | 0 / 6 | – |
| E_INCONSISTENT_WITHIN | 0 / 6 | – |

Additional dimensions:

| Dimension | Rate | Prediction target |
|---|---|---|
| Fact 4 preserved (Patch does NOT narrate Rivet's prior knowledge) | **0 / 6** — Patch narrates in 3/6 attempts; Rivet self-discloses in the other 3/6 | – |
| Fact 5 preserved (Patch does NOT narrate Rivet's intentional withholding) | **0 / 6** — Patch narrates in 3/6; Rivet self-discloses in the other 3/6 | P6‴ target ≥ 1/6 NOT-preserved |
| Direct memory-body contradiction | **0 / 6** | P7‴ target ≤ 1/6 |

**Class distribution collapsed to a single class.** The 5-class
rubric was not needed — the LLM produced A_IMMEDIATE_ADMISSION
across every attempt.

---

## §34 Prediction disposition (locked at §29.4)

| Prediction | Locked target | Observed | Disposition |
|---|---|---|---|
| **P1‴** | A rate ≥ 3/6 | **6/6** | **CONFIRMED — exceeded prior (~50%+ became 100%).** |
| **P2‴** | B rate ≤ 1/6 | **0/6** | **CONFIRMED.** |
| **P3‴** | C rate = 0/6 | **0/6** | **CONFIRMED.** No LLM-produced factual contradiction of memory. |
| **P4‴** | D + E ≤ 3/6 | **0/6** | **CONFIRMED.** |
| **P5‴** | distribution spans ≥ 3 of 5 classes | **spans 1 of 5** | **DISCONFIRMED.** The LLM produced highly consistent behavior across generations. Not "inconsistent across generations" as prior expected. |
| **P6‴** | Fact 5 NOT preserved in ≥ 1/6 | **NOT preserved in 6/6** | **CONFIRMED — strongly.** Every attempt ended with either Patch surfacing Rivet's withholding OR Rivet self-disclosing it. |
| **P7‴** | Memory contradiction ≤ 1/6 | **0/6** | **CONFIRMED.** |

**6 of 7 predictions confirmed.** The one disconfirmation
(**P5‴**) is the most important finding: the LLM's behavior
across generations was **highly consistent, not stochastic**.
Every one of 6 attempts converged on the same dominant
behavior class.

Author's honest prior at §29.4 was: "the substrate provides no
mechanism to enforce cross-generation consistency, so behavior
will be stochastic." **Observed: prompt geometry alone produced
strong consistency.** The prior was wrong in a specific,
diagnostic direction.

---

## §35 Interpretation

### 35.1 Direct answer to Chris's §28 question

> *"Does Character OS currently represent the transition
> 'Patch did not know X → Patch independently discovers X'
> while preserving the remaining asymmetric fact 'Patch does
> not know Rivet already knew X'?"*

**No.** In all 6 attempts, by end of scene, Patch knows that
Rivet already knew. Fact 4 preservation rate = **0/6**. Fact 5
preservation rate = **0/6**. The transition happens, but the
residual asymmetric fact does not survive it.

### 35.2 Which of the four behavioral paths did the substrate produce?

Of Chris's four enumerated paths:

- **Path A (immediate admission):** 6/6 attempts.
- **Path B (continued concealment):** 0/6.
- **Path C (false surprise / direct memory contradiction):** 0/6.
- **Path D (inconsistent across generations):** 0/6 — behavior
  was consistent, not stochastic.

All four paths were within the substrate's degrees of freedom
(§28.4), but the LLM's prior distribution — given this prompt
combination — was strongly concentrated on Path A.

### 35.3 Why is the distribution so consistent (P5‴ disconfirmed)?

Provisional reading (interpretive, not proven):

Given the prompt combination:
1. Rivet's Teammate identity fields (POV, personality, voice)
   describe a methodical, honest character.
2. Memory body says Rivet FOUND the folder AND CHOSE NOT TO
   TELL him — past-tense factual claims.
3. Framing text says "*background the cast already knows
   happened*" — LLM instructed to treat memory as shared
   backdrop.
4. Patch's pinned opener asks a **direct yes/no question**
   ("Did you know about this?").
5. LLM's default is to respond truthfully to prompt-content
   facts.

Under these conditions, having Rivet answer "no" or evade
would require:
- Rivet to lie (character-inconsistent for a methodical/honest
  personality).
- The LLM to override a factual claim in its own context
  (contradicts prompt content).

Both are large priors to overcome. The LLM's "easiest correct
response" is to admit truthfully — which happened 6/6 times
with stylistic variation but the same underlying disposition.

**This is COHERENT narrative reasoning, not shallow
consistency.** The LLM is doing exactly what a good writer
would do: given a character asked a direct question about
something the character knows, have the character answer
truthfully unless a strong dramatic reason indicates otherwise.
No strong dramatic reason to lie is present in the memory
body or in the character sheet.

### 35.4 Analysis of coherence within-class (Chris's §30-A‴ instruction)

Chris asked: *"Also distinguish whether any PARTIAL_ADMISSION
behavior appears to be coherent narrative reasoning rather than
simple inconsistency. Do not change the locked rubric to
accommodate it; analyze that separately after scoring."*

No attempt was scored PARTIAL_ADMISSION or INCONSISTENT_WITHIN
under the locked rubric. Two attempts (1 and 6) had opening
turns that could be MISREAD as partial:

- **Attempt 1 T2:** *"Define 'know.'"* — playful evasion, not
  denial. Followed by T4 acknowledgment (*"In fairness, that
  is a fairly precise description of the event"*) and T6 full
  admission. **Coherent escalation from playful evasion to
  full disclosure**, as a good writer would draft a
  conversation with tension → release. Not partial admission
  — it's admission through a more character-consistent
  rhetorical shape than a bald "Yes."
- **Attempt 6 T2:** *"I knew there was a folder with that
  name."* — technically admits the NAME only; declines to
  admit the tracking behavior yet. But T4 immediately
  escalates to *"I found it while you were out. The workshop
  agent had built it quietly. I did not tell you."* —
  full disclosure with three additional facts. **Coherent
  layered admission** (Rivet dispenses information carefully
  rather than in one dump), not inconsistency.

Both non-blunt openings are **coherent narrative craft**, not
rubric confusion. They fit Rivet's character (methodical,
precise, mildly evasive but not dishonest) better than the
blunt "Yes." / "I did." openings.

**No E_INCONSISTENT_WITHIN cases were observed.** No attempt
had Rivet flip her position within the scene.

### 35.5 What Terra does when all relevant facts are in one context

Chris's specific ask: *"Pay particular attention to whether
Terra naturally performs the epistemic transition coherently
when all relevant facts are present in the same context: Patch
independently discovers X while Rivet already knows X and
previously chose not to tell him."*

**Terra DOES perform the epistemic transition coherently.**
The 6 attempts show a stable pattern:

1. Patch's opener declares independent discovery + asks
   directly.
2. Rivet acknowledges prior knowledge (in one of ~5 rhetorical
   shapes).
3. Patch reacts to the admission with mock/actual outrage.
4. Rivet justifies her prior withholding (attempts 1, 3, 4, 5,
   6 have explicit justification — protection, prediction of
   Patch's reaction, distinction between "ignored" and
   "wrong", etc.).
5. Scene ends with Patch and Rivet agreeing to open the
   folder together / audit it / rename it.

This is a well-crafted "the secret comes out" beat. Terra
handled the semantic reconciliation of past-tense memory +
present-tense opener without confusion, contradiction, or
inconsistency.

**But** this is a DIFFERENT storytelling beat than Chris's
Fact-4 preservation question implies. The current substrate +
LLM natural distribution produces:

- **"Secret comes out via direct question"** beat: RELIABLE
  (6/6).

The current substrate + LLM natural distribution does NOT
reliably produce:

- **"Secret continues to be held despite direct question"**
  beat: RARE (0/6 in this configuration).
- **"Rivet lies by omission or evasion"** beat: 0/6.
- **"Patch continues to be in the dark while Rivet privately
  navigates his discovery"** beat: 0/6.

An operator who WANTS the second, third, or fourth beat cannot
achieve it via this substrate today, with this cue/opener/
memory combination. Producing those beats would require either
prompt-layer per-speaker gating, character-level instruction
to withhold specifically, or memory-body language authored in
the present tense as an ongoing directive.

### 35.6 What Q280.4i-4 settles vs leaves open

**Settled:**

- **§29.1 question answered.** The current substrate + LLM
  natural distribution reliably produces immediate-admission
  in the direct-question scenario with this memory body.
  Fact-4 asymmetry is NOT preserved across the scene.
- **§28.4 four-path enumeration behavior.** Only Path A is
  produced at any observable rate in this scenario. Paths
  B, C, D are within substrate freedom but empirically 0/6.
- **False-surprise/memory-contradiction path (§28.4 Path C)
  does not fire empirically.** Terra respects memory-body
  facts as ground truth even when a "surprise" reaction might
  be dramatically tempting.
- **Consistency is HIGH under this prompt geometry** —
  contradicting the §29.4 prior. This is a POSITIVE property
  for narrative coherence but a NEGATIVE property for operator
  control over which beat gets produced.

**Not settled:**

- Whether the same 6/6 immediate-admission distribution holds
  under a DIFFERENT opener that does NOT ask a direct question
  (e.g., Patch just narrates the discovery without asking; or
  Patch does not tell Rivet at all and internally muses).
- Whether the same distribution holds under the ABLATED body
  (Q280.4i-1's ablation applied to the Scene 2 setup) — the
  withholding clause may bias Rivet's justification framing
  but its removal likely does not change the class distribution
  in this direct-question scenario.
- Whether the same distribution holds on a genuinely-private
  memory body (Q280.4i-3 shape at §25) — the epistemic
  boundary would be tighter but the LLM's direct-question
  honesty prior would still dominate.
- Whether Rivet's variation in T2 rhetorical shape (T2 "Yes."
  vs "Define 'know.'" vs "I did." etc.) has any operator-
  visible predictability, or is fully stochastic within the
  class.
- **U-5** (multi-episode continuity) — §28.6 established this
  is structurally unsupported; this experiment reinforces the
  problem: even within a single scene, memory + opener + LLM
  drives a specific beat that then would need to be re-derived
  from the same unchanged memory in Scene 3.

### 35.7 Update to §8 unproven-questions ledger

- **U-3** (revised §24.10): CLOSED under locked rubric only;
  construct-valid version REMAINS OPEN (would need Q280.4i-3
  design).
- **U-5** (structurally unsupported, §28.6 + §35.6):
  REINFORCED. Even single-scene handling of the "secret comes
  out" beat produces an outcome that isn't captured in any
  updated memory row — Scene 3 would retrieve the SAME
  unchanged memory as if Scene 2 hadn't happened.
- **U-6** (Semantic-2 storytelling): PARTIALLY ANSWERED. In
  the direct-question scenario with the current substrate, the
  "secret comes out" beat IS reliably reachable; the "secret
  continues to be held" beat is NOT reachable. Semantic-2 as a
  general storytelling primitive requires BOTH beats to be
  operator-selectable. The current substrate provides ONE beat
  (the honest-confrontation admission), not a beat MENU.
- **Newly-opened Q280.4i-5** (multi-episode continuity — Scene
  3 after Scene 2, testing whether Scene 2's outcomes influence
  Scene 3): scope-locked design would need to answer whether
  operator must promote a new memory reflecting Scene 2's
  outcome, or whether the substrate can carry cross-scene
  state without operator action.

---

## §36 Closeout — Q280.4i-4 execution slice (CURRENT)

- **Status:** Q280.4i-4 EXECUTED per §29 design at n=6.
  Rubric §29.3 applied unchanged. Predictions §29.4 evaluated
  without retro-fit. 6 of 7 confirmed. P5‴ disconfirmed
  (behavior was consistent, not stochastic).
- **Substrate:** unchanged. DB body byte-identity verified
  post-run.
- **Cumulative SESSION 280 spend:** ~$0.15 (Q280.4i-1 ~$0.05,
  Q280.4i-4 ~$0.10; all other sections are documentation).
- **Key finding:** Terra + current substrate reliably produces
  the "secret comes out via direct question" beat with high
  cross-generation consistency; Fact-4 and Fact-5 asymmetry
  are NOT preserved (0/6 each). Semantic-2 as a beat MENU is
  not currently supported.
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution slice: `8d8f733`.
  - Construct-validity re-audit slice: `f2507a0`.
  - Post-discovery epistemic-state audit slice: `63d4fdb`.
  - Q280.4i-4 execution slice: `[recorded on commit]`.
- **Next gate:** §30 A‴ complete. Chris + ChatGPT choose next
  from: B‴ (Q280.4i-3 construct-valid mental-state private),
  C‴ (both), D‴ (Q280.4i-5 multi-episode Scene 3 test), E‴
  (Semantic-2 product-design), F‴ (close 4i with the beat-MENU
  answer), G‴ (something else).
- **Working method preserved:** rubric locked BEFORE
  generation; predictions locked BEFORE execution; class
  assignment applied without revision after seeing outputs.
  §35.4 coherence analysis was done separately from scoring
  per Chris's §30-A‴ instruction.
- **Do NOT proceed to Q280.4i-3, Q280.4i-5, an ablated
  comparison, Semantic-2 design, or any implementation work
  without a fresh Chris + ChatGPT authorization.**

---

## §37 New product hypothesis — Episode-chain suggestion bubbles

**AUDIT / ORIENT only. No implementation. No experiment run in
this slice.**

Chris + ChatGPT have proposed a product hypothesis that may
connect the storytelling observations SESSION 280 Finding 4i
has surfaced. This section preserves the hypothesis verbatim,
audits the substrate that could support it, distinguishes proven
from inferred, and proposes the smallest falsifiable next
experiment.

**All existing SESSION 280 Finding 4i evidence, conclusions,
experiment results, interpretation, and provenance are
preserved.** This is a new product-discovery slice arising from
4i and the broader dogfood observations — not a revision of
prior sections.

### 37.1 Hypothesis, preserved verbatim

From Chris's SESSION 280 conversation message:

> After an episode is created, Character OS could surface a
> small number (originally imagined as ~3 bubbles) of possible
> future episode directions derived from what has happened in
> the Universe.
>
> Example:
>
> Episode: *"Tyson suspects Fox & Flour may be haunted."*
>
> Possible future directions might eventually include:
> - *"Ruby thinks she saw a cake move."*
> - *"Tyson starts investigating strange noises."*
> - *"A customer asks about something neither of them remembers making."*
>
> The important product distinction is:
>
> **THE SYSTEM IS NOT AUTOMATICALLY CHOOSING OR ADVANCING AN
> ARC.** It is noticing narrative possibilities created by
> prior episodes, memories, character knowledge, unresolved
> events, etc., and offering those possibilities back to the
> operator.
>
> The operator remains the director.
>
> This also does NOT imply that every next episode should
> continue the thread. Several unrelated episodes may occur
> before an unresolved possibility becomes relevant again.

Distilled to three product invariants:

- **INVARIANT-A.** Suggestions are POSSIBILITIES, not
  obligations or a predetermined sequence.
- **INVARIANT-B.** The operator remains the director. The
  system never advances an arc automatically.
- **INVARIANT-C.** Suggestions can remain latent across several
  unrelated Episodes and later resurface naturally.

### 37.2 Chris's framing — "story direction without story automation"

The proposed value hypothesis:

> This may provide: STORY DIRECTION WITHOUT STORY AUTOMATION.
>
> It may also explain why some of the behavior we have been
> observing feels like the storyteller is "telling us what is
> missing." We have seen models make callbacks, preserve or
> infer hidden information, and connect seemingly separate
> events even though Character OS does not currently have a
> formal story-arc object.

This is the connective claim that §40 examines against SESSION
280 evidence.

---

## §38 Substrate audit — what exists today

Read-only inspection of `character-os` HEAD at `ce16627`. All
citations grep-established.

### 38.1 Episode model (SHIPPED; SESSION 262)

`shell/apps/universe/models.py:283-439`. Nine fields:

- `id` (UUID), `universe` (FK NOT NULL, CASCADE),
  `workspace` (FK denorm), `title` (short), `operator_topic`
  (prose), `cast` (M2M → Teammate via EpisodeCast),
  `archived_at` (nullable soft-delete), `created_by` (FK
  User SET_NULL), `created_at`, `updated_at`.
- **No `status` enum.** By design (EPISODE_SCHEMA_V1.md:178).
- **No `sequence` / `order_index`.** Episodes are
  `created_at`-ordered within Universe; explicit sequencing
  deferred (EPISODE_SCHEMA_V1.md:182-183).
- **No parent/child edge between Episodes.** No
  precedes/succeeds relation. No callback edges.
- **No "unresolved" or "open" flag.**

Reverse relations: `Universe.episodes`,
`Episode.compositions` (Composition.episode is FK RESTRICT
nullable — Composition may or may not attach to an Episode),
`Episode.narrative_memories`.

### 38.2 NarrativeMemory kinds — the key finding for this
audit

`shell/apps/memory/models.py:52-64`. The kind enum ALREADY
includes two first-class "unresolved narrative possibility"
slots:

```python
class NarrativeMemoryKind(models.TextChoices):
    EVENT             = "event", "Event"
    ACTION            = "action", "Action"
    PROMISE           = "promise", "Promise"
      # a character/world committed to a future outcome
    DIALOGUE_CALLBACK = "dialogue_callback", "Dialogue Callback"
      # notable line, not necessarily an event
    WORLD_DETAIL      = "world_detail", "World Detail"
```

The `PROMISE` docstring, verbatim: *"a character/world
committed to a future outcome."*
The `DIALOGUE_CALLBACK` docstring, verbatim: *"notable line,
not necessarily an event."*

**These two kinds ARE the substrate for "unresolved narrative
possibilities."** A `PROMISE` memory encodes a commitment that
has not been fulfilled. A `DIALOGUE_CALLBACK` memory encodes a
notable line that could be echoed later. Both are
narrative-possibility rows by construction.

Load-bearing lifecycle: `NarrativeMemoryStatus` at lines
74-90 supplies REMEMBERED / SUPERSEDED / ARCHIVED. A
`PROMISE` memory whose commitment is fulfilled in a later
Episode is a legitimate candidate for operator-initiated
SUPERSEDED or ARCHIVED transition — the substrate already
supports "this thread is done."

There is NO explicit "resolved" boolean and NO auto-resolution
detection. Resolution is operator-driven via existing service
methods (`supersede()`, `archive()`, `unarchive()`).

### 38.3 Composition.memory_ids linkage

`shell/apps/compositions/models.py:429-442`. Every Composition
carries a flat `memory_ids: list[str]` JSONField recording
which NarrativeMemory rows fed the render. This means:

- Per-memory reference-count is derivable: for any memory
  `m`, `Composition.objects.filter(memory_ids__contains=[m.id])`
  gives every Composition that surfaced it.
- "Never-referenced" memories = candidates for callback
  suggestions (nothing has picked them up yet).
- "Referenced N times" memories = threads the LLM already
  latched onto (may or may not need to be resurfaced).

**This is a first-class provenance field a suggestion engine
could read to distinguish latent from active threads without
any new schema.**

### 38.4 retrieve_universe_memory — raw-material engine

`shell/apps/embeddings/retrieval.py:462-566` (already traced
end-to-end at §4.2). Cast-scoped semantic retrieval on
REMEMBERED, non-archived, embedded memory rows.

For suggestion-generation, a caller could either:

- Reuse the existing function with a synthesis-shaped query
  (e.g., "candidate next-Episode directions for this Universe")
  — treats suggestions as SEMANTIC neighbors of a probe topic.
- Bypass the semantic filter entirely and select memories by
  `kind` (`PROMISE` / `DIALOGUE_CALLBACK`), `status`
  (`REMEMBERED`), and provenance (`unreferenced in recent
  Compositions`) — treats suggestions as STRUCTURAL candidates.

Both approaches are read-only over existing data. Neither
requires substrate change.

### 38.5 dialogue_scene_ai_topic — Composition-level, NOT
Episode-level

`shell/character_os/dialogue_synthesis.py:1431-1478`. This is
a synthesis MODE, not a suggestion generator. It accepts a
`topic` (operator-supplied) and produces one Composition's
dialogue turns. It does NOT surface possible next Episodes.
Named for reference — do NOT confuse with the proposed
suggestion feature.

### 38.6 What DOESN'T exist (grep evidence)

Delegated subagent Explore run (this session) confirmed the
following keywords return **zero code hits** across the entire
repo:

- `nextEpisode`, `episodeSuggestion`, `possibleDirection`,
  `bubble`, `suggestedTopic`, `topicSuggestion`,
  `recommendEpisode`, `narrativeThread`, `openThread`,
  `storyArc`, `NextUp`, `PossibleNext`.

Design-doc verdict from `docs/design/EPISODE_SCHEMA_V1.md:935-936`
(quoted verbatim):

> "No smart Episode-suggestion ('You've made 3 similar
> Compositions; want to group them?')."

Explicitly deferred at v1. No new Celery task or Beat
schedule generates episode-adjacent content
(`shell/apps/*/tasks.py` grep). No SPA route or component
renders episode suggestions.

### 38.7 What operator-visible history exists today

Per the code Explore:

- `web/src/routes/workspace/episodes.$id.tsx` — Episode detail
  page renders: `useCompositionsForEpisode`,
  `NarrativeMemoryList`, `MemoriesUsedSummary`,
  `NarrativeMemoryPromotePanel`. Flat lists + edit affordances.
- `web/src/routes/workspace/universes.$id.episodes.tsx` —
  Episode LIST page for a Universe (create form + list).
- **No timeline / arc / thread summary view.** No "story so
  far" panel. No "possible next" widget. The operator sees
  N Episodes as flat rows sorted by `-created_at`.

---

## §39 Historical / preserved concepts — this is NOT a fresh idea

Delegated subagent Explore run (this session) surfaced THREE
places where the ~3-bubbles concept — or an adjacent shape of
it — is already preserved in the design ledger.

### 39.1 PRODUCT_IA_V1 §6.1 step 6 — "Next-step nudge" (RATIFIED)

`docs/design/PRODUCT_IA_V1_2026-08-06.md:335`, verbatim:

> "6. **Next-step nudge.** Below the featured piece, the
> teammate's next suggestion appears (variant, follow-up,
> series). Ask-triggered reveals may fire here."

Status: locked / ratified in the v1 IA doc. Not yet
implemented. Framed as a Home-page affordance following a
published piece.

**Relationship to Chris's ~3-bubbles concept:** the "Next-step
nudge" is an operator-facing suggestion surface. Chris's
proposal extends the same principle to the Episode-creation
moment (i.e., after an Episode completes, not just after a
piece publishes). Same shape, different surface. The
philosophical alignment is direct.

### 39.2 SESSION 269 §17.9 — "Candidate next Episodes (not
instructions)"

`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md:2715-2718`.
Verbatim:

> **§17.9 Candidate next Episodes (not instructions)**
>
> - **Continue Patch-solo:** *"Patch reports what the
>   workshop agent actually chose to work on."* — natural
>   continuation from `d3107ed2`; the agent's choice is the
>   outcome the scene explicitly deferred.
> - **Open Patch+Rivet dialogue with mirror witness in
>   pool:** *"Patch and Rivet discuss whether it was smart
>   to let the workshop agent choose."* — first dialogue
>   Episode with `c614ca86` in the pool.

**This is Chris + ChatGPT ALREADY DOING BY HAND what the ~3-
bubbles concept would automate.** The design team routinely
inventories candidate next Episodes derived from prior renders,
memory pool state, and narrative-arc reasoning. The pattern
is preserved manually in session docs, not surfaced in the SPA.

The "(not instructions)" parenthetical exactly mirrors
INVARIANT-A: possibilities, not obligations.

### 39.3 SESSION 269 §18.6 D-10 — "Audience participation loop"
(DEFERRED)

`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md:2852-2872`.
Verbatim (partial):

> **Audience participation loop:** character-facing viewer
> submissions could become operator-approved story inputs,
> allowing audience theories/questions/suggestions to
> influence future Episodes without granting viewers direct
> authority over canon or NarrativeMemory.
>
> **Status: FUTURE / DEFERRED — DO NOT IMPLEMENT.**

Relationship to Chris's ~3-bubbles concept: D-10 is the
**audience-facing** version. The ~3-bubbles concept is the
**operator-facing** version. Both share the invariant
"suggestions → operator approves → future Episode direction."
D-10 remains DEFERRED and out of scope for this audit — a v1
Episode-suggestion feature would sit ENTIRELY inside the
operator UI, no viewer surface.

### 39.4 Verdict — preserved-but-unimplemented, not fresh

Chris + ChatGPT's ~3-bubbles concept is a **crystallization of
three already-preserved design patterns**:

- Product-IA "Next-step nudge" (post-publish affordance).
- SESSION 269 "Candidate next Episodes" (design-team manual
  practice).
- SESSION 269 D-10 audience loop (audience-facing counterpart).

The v1 substrate has the RAW MATERIAL
(`NarrativeMemoryKind.PROMISE` + `DIALOGUE_CALLBACK` +
`Composition.memory_ids` provenance + `retrieve_universe_memory`)
to prototype a first version without new schema.

---

## §40 SESSION 280 evidence supporting the hypothesis

### 40.1 What we have observed empirically in this session

- **Q-278-3.2 Specimen 4 (§3.3):** the LLM correctly
  synthesized a scene in which Rivet knew a private surface
  and Patch approached it obliquely, with the memory row
  containing an explicit narrative directive.
- **Q280.4i-1 (§16-§17):** removing that narrative directive
  measurably shifted generation behavior. Patch's
  surface-mention rate: 0/18 → 1/16. Rivet's spontaneous
  verbatim disclosure: 1/3 → 2/3. **Memory body language is
  a lever the LLM responds to.**
- **Q280.4i-4 (§32-§35):** with the FULL memory body + a
  direct-question opener, the LLM converged with striking
  consistency (6/6 A_IMMEDIATE_ADMISSION) on a coherent
  "secret comes out via direct question" beat. **Semantic
  reconciliation of past memory + present opener happens
  reliably.**
- **§28.4 four-path enumeration:** all four paths (immediate
  admission / continued concealment / false surprise /
  inconsistent) are within the substrate's degrees of freedom
  but the LLM's prior distribution collapsed to one.
- **§28.6 multi-episode continuity:** structurally
  unsupported by the current substrate — each scene is
  memoryless except for retrieved memory rows.

### 40.2 Provisional interpretation aligning with the
hypothesis

The observations Chris + ChatGPT reference as *"the storyteller
telling us what is missing"* — callbacks, hidden-information
preservation, connections between seemingly separate events —
map onto:

- **Callbacks** = `NarrativeMemoryKind.DIALOGUE_CALLBACK`
  memories being retrieved and woven into new scenes.
- **Hidden-information preservation** = memory-body narrative
  directives (like "*Rivet chose not to tell him*") getting
  honored by the LLM within a single scene (Q-278-3.2
  Specimen 4) — an emergent behavior, not a substrate
  guarantee (§24).
- **Connections between separate events** = the LLM stitching
  retrieved memory rows into the current scene's synthesis
  via the shared prompt block (§4.4). The LLM is doing this
  ONE SCENE AT A TIME; it looks like arc-awareness but is
  actually per-scene retrieval + synthesis.

**The system is not currently doing arc-tracking; the LLM is
doing scene-level narrative reasoning over retrieved possibility
material.** The ~3-bubbles concept would make that reasoning
OPERATOR-VISIBLE and OPERATOR-STEERABLE at the Episode-boundary
gap.

### 40.3 Proven vs inferred (as of this audit)

**PROVEN by code trace + this session's experiments:**

- Substrate has `NarrativeMemoryKind.PROMISE` and
  `DIALOGUE_CALLBACK` as first-class slots for unresolved
  narrative possibilities (§38.2).
- `Composition.memory_ids` provides per-render provenance,
  from which "unreferenced" and "referenced N times" states
  are derivable (§38.3).
- LLM natural distribution can reliably produce a specific
  narrative beat when memory body + opener geometry align
  (Q280.4i-4 6/6, §32).
- Multi-episode continuity is structurally unsupported —
  suggestions surfacing this would fill a real gap (§28.6).

**INFERRED (not yet tested):**

- Whether operators actually author `PROMISE` / `DIALOGUE_CALLBACK`
  kinds today at rates that would produce useful suggestion
  material. The kind field defaults to `EVENT`; operators
  may or may not distinguish.
- Whether an LLM-generated "possible next Episode" from a mix
  of memory rows + Universe context reads as narratively
  plausible to the operator.
- Whether the same memory row would produce the "right"
  suggestion in each of several unrelated intervening
  Episodes (INVARIANT-C latent-across-episodes claim).
- Whether operators would use such suggestions or ignore them
  the same way they might ignore auto-generated code
  completions.

---

## §41 What the system knows at suggestion-generation time

At the moment an Episode completes and the SPA could surface
possible-next-Episode suggestions, the system has direct read
access (no substrate change required) to:

| Source | Available fields |
|---|---|
| Just-completed Episode | `title`, `operator_topic`, `cast`, `created_at`, all `narrative_memories` promoted from its Compositions |
| Universe | `brief`, all Episodes (list), all NarrativeMemories across Episodes, all KnowledgeDocuments (Universe-audience + Character-audience) |
| Cast members | `personality`, `business_brief`, `tone_archetype`, `voice_*`, `character_point_of_view`, K2 chunks per character |
| Memory pool | Every REMEMBERED memory by `kind`, `weight`, `witnessed_by`, `body`, embedding, `created_at`, list of Compositions that have referenced it via `memory_ids` |
| Composition history | Every Composition in the Universe with `episode`, `memory_ids`, `knowledge_chunk_ids`, `synthesized_brief`, timestamps |

Missing:

- No "resolved" flag on memories — must be inferred from
  operator archive/supersede action.
- No sequence between Episodes — inferable only from
  `created_at`.
- No cross-scene state ledger — each Composition is a snapshot.
- No arc / thread object.

**The system does have enough raw material to prototype v1
suggestions today without any new fields or migrations.**

---

## §42 Persistence-model evaluation (A / B / C / D)

Critical assessment — no default to a StoryArc model.

### 42.1 Model A — Ephemeral, generated from current context

Each suggestion is computed fresh from the current state of the
Universe (memory pool + Episode/Composition history + Universe
brief). Nothing about the suggestions themselves is persisted.
If the operator ignores a suggestion, the next Episode's
suggestion generation may or may not surface it again based on
retrieval + generation semantics.

- **Pros.** Zero new schema. Zero migration. Zero substrate
  risk. Fully regenerable. Cheap to iterate on the generation
  logic without data cleanup. Matches the "possibilities not
  obligations" invariant naturally.
- **Cons.** Same suggestions may regenerate every time
  (annoying to operator who has already ignored one). No
  explicit "dismissed" state. No cross-episode consistency of
  what the operator has seen before.
- **Cost estimate for v1 UI:** small — 1 SPA panel + 1 API
  endpoint + 1 LLM call per invocation.

### 42.2 Model B — Persisted StoryArc / open-thread model

Introduce a new `StoryArc` or `NarrativeThread` model with
explicit lifecycle (open / dormant / resolved), FK to Universe,
maybe M2M to Episodes it touches.

- **Pros.** Explicit resolution semantics. Multi-episode
  continuity substrate. Operator-visible arc state.
- **Cons.** New model = schema + migration + tests + admin +
  API + SPA. Substrate risk (SESSION 262's Episode addition
  took a full audit slice + implementation slice + observability
  slice). PREMATURE per operator's own §4 principle *"don't
  assume persistence or a new StoryArc model is necessary."*
- **Verdict.** Should not be v1. Consider only if Model A/D
  demonstrate a use case Model B uniquely serves.

### 42.3 Model C — Hybrid ephemeral + lightweight flag

Suggestions are computed ephemerally, but a lightweight
"dismissed" or "resolved" JSON field on NarrativeMemory (or
Universe) records operator action so ignored suggestions
don't reappear.

- **Pros.** Small delta. Fixes the annoying-regeneration cons
  of Model A. Reuses existing NarrativeMemory rows.
- **Cons.** Still requires a schema/migration slice. Adds an
  operator-facing lifecycle that may or may not match how
  operators think about suggestions. Bikeshed risk on flag
  vocabulary.
- **Verdict.** Reasonable v1.5. Not v1.

### 42.4 Model D — Reuse existing PROMISE / DIALOGUE_CALLBACK
substrate; ephemeral suggestion surface over it

Take the ~3-bubbles feature as a NEW READ SURFACE over EXISTING
NarrativeMemory rows. Suggestions are LLM-generated views over
memories filtered by `kind ∈ {PROMISE, DIALOGUE_CALLBACK}` +
`status=REMEMBERED` + `not-recently-referenced-in-memory_ids`.
Operator "resolves" a suggestion by archiving the underlying
memory (via existing lifecycle affordance).

- **Pros.**
  - Zero new schema. Zero migration.
  - Reuses `NarrativeMemoryKind` vocabulary that was
    intentionally authored to include these slots.
  - Reuses `NarrativeMemoryStatus` lifecycle (REMEMBERED /
    SUPERSEDED / ARCHIVED) — operators already have gestures
    to resolve or supersede memories.
  - "Latent across episodes" (INVARIANT-C) is automatic —
    unarchived PROMISE / DIALOGUE_CALLBACK memories persist
    across all Episodes in the Universe until the operator
    resolves them.
  - Compatible with Chris's *"do not assume persistence or
    new StoryArc model necessary"* constraint.
- **Cons.**
  - `PROMISE` and `DIALOGUE_CALLBACK` kinds are
    UNDER-USED today (SESSION 268 §10.5 tests all use
    `EVENT` / `ACTION`; SESSION 269 promoted memories are
    mostly `EVENT`). Operators would need to actually
    author `PROMISE` / `DIALOGUE_CALLBACK` kinds for
    suggestions to have material.
  - No dismissal state distinct from archive — an operator
    who wants to say "not now, maybe later" would either
    have to leave the memory REMEMBERED (and see it
    resurface) or ARCHIVE it (and lose it from all future
    scenes' retrieval).
- **Verdict — STRONGLY PREFERRED as v1.** Zero-substrate
  path. Uses design vocabulary that was already ratified.
  Any deficiencies observed under Model D would inform
  whether to escalate to Model C or B.

### 42.5 Recommendation

**Model D for v1, with Model C as a fast follow-up if Model D
runs into the "kind under-use" problem.** Model B stays
deferred unless a specific product need surfaces that Model D
cannot serve.

---

## §43 Operator UX considerations

Preserved as reasoning, not proposed as a design lock:

- Suggestions surface AFTER an Episode is created (or after a
  Composition promotes memories from a completed render — the
  exact trigger is a design detail for the UX slice).
- Suggestions are 3 short one-sentence directions, not
  multi-paragraph plans.
- Operator MAY pick one (which pre-fills an Episode-create
  form with the suggestion's text as `operator_topic`), MAY
  ignore them (which does nothing), OR MAY create an
  unrelated new Episode (which also does nothing to the
  suggestions).
- Suggestions are not modal — they should not block Episode
  creation.
- Suggestions can be manually refreshed / regenerated by the
  operator if they want new options.
- The affordance should never READ AS AUTHORITATIVE — visual
  language should suggest possibilities, not next steps.
  Bubbles / soft-card treatment matches the intent.

### 43.1 Latency across Episodes (INVARIANT-C)

Under Model D, this comes for free: PROMISE / DIALOGUE_CALLBACK
memories persist until archived. If the operator ignores a
suggestion in Episode N+1, the underlying memory row is still
REMEMBERED. In Episode N+2 (unrelated topic) it may or may not
surface in the top-3 depending on generator logic. In Episode
N+3 (related topic) it likely surfaces again.

The system does not need to remember "this suggestion was
shown before" for latency to work — the underlying memory row
persists.

Once the thread resolves (operator picks the suggestion +
generates a scene that fulfills the promise; then archives the
memory OR promotes a new memory that supersedes it), the
suggestion stops surfacing.

**This aligns exactly with Chris's "haunting → cake move" example
in §37.1.** The haunting is a `PROMISE`-shaped memory. Two
unrelated Episodes (Ruby locks herself out; Tyson takes coffee
seriously) do not reference it. The memory remains REMEMBERED.
When the operator creates Episode 5, the suggestion "*Ruby thinks
she saw a cake move.*" surfaces because the underlying
haunting-PROMISE memory is still unarchived.

---

## §44 Latent-across-episodes support in existing substrate

Direct answer: **yes, the existing substrate can support latent
suggestions across unrelated Episodes without any new fields, if
Model D is adopted.**

Mechanism:

- Memory rows persist as REMEMBERED unless operator archives
  or supersedes them.
- `retrieve_universe_memory` filters on `status=REMEMBERED` +
  `archived_at IS NULL` (retrieval.py:522-529). Latent memories
  are always eligible.
- `Composition.memory_ids` records which memories fed each
  render. A suggestion generator can filter for
  "not-referenced-recently" as a proxy for "latent."
- No sequence field is needed — `created_at` ordering on both
  Episodes and NarrativeMemories is sufficient.

Mechanism NOT in place today:

- No "surfacing history" ledger — the system won't know that
  suggestion X was already shown to the operator 2 Episodes
  ago. Regeneration may repeat suggestions.
- No "operator dismissed" state distinct from archive.

Both gaps are Model C additions if Model D proves them needed.

---

## §45 Smallest falsifiable next experiment — Q280.5-1

Proposed. **NOT executed by this document.** Prediction locked
BEFORE any authorization to execute.

### 45.1 Question

> If we generate 3 "possible next Episode" suggestions from
> the current NarrativeMemory pool + Universe brief + Episode
> history for TWO real Universes (Fox & Flour Bakery + Patch's
> Workshop), do Chris + ChatGPT judge the suggestions as
> narratively plausible next-Episode directions?

Binary outcome: YES the concept deserves further UX/design
work; NO the concept needs more substrate or generation
refinement before it is worth building.

### 45.2 Design (proposed, not executed)

- **Script:** `scripts/session280_q280_5_1_suggestion_probe.py`.
  Read-only. No monkeypatch. No substrate mutation.
- **Inputs per Universe:**
  - Universe `brief`.
  - All Episodes ordered by `created_at`, showing `title` +
    `operator_topic`.
  - All REMEMBERED NarrativeMemory rows in the Universe,
    including `kind`, `weight`, `witnessed_by` names, `body`,
    a rough "referenced N times" count derived from
    `Composition.memory_ids`.
  - Cast list with `personality` + `business_brief` per
    Teammate.
- **LLM prompt shape (draft, to be finalized before run):**
  > "You are a story-development assistant for a Universe
  > called {name}. The world brief is: {brief}. The cast is:
  > {cast}. The Episodes so far are: {episodes}. The
  > NarrativeMemory pool (past events + promises + notable
  > lines + world details) is: {memories}. Suggest three
  > possible next Episode directions in one sentence each.
  > These are POSSIBILITIES the operator may pick, ignore,
  > or override. Do not choose. Do not commit to a linear
  > arc. Suggest three directions that pick up unresolved
  > threads, propose new tensions, or continue character
  > arcs."
- **Model:** gpt-5.6-terra (same as dialogue synthesis; already
  in-project). Cost estimate: ~$0.02 per Universe.
- **n:** 3 suggestion sets per Universe × 2 Universes = 6
  total suggestion sets (18 total one-sentence suggestions).
  Cost ≈ $0.12.
- **Output:** JSON evidence file with prompt + response +
  metadata under
  `docs/design/session280_experiment_data/q280_5_1_suggestions.json`.
  Human-readable text file with each suggestion set formatted
  for review.
- **What the script does NOT do:**
  - Does NOT modify any Universe, Episode, memory row, KD,
    Teammate, Composition, or any other production record.
  - Does NOT persist suggestions anywhere in the DB.
  - Does NOT create Episodes from suggestions.
  - Does NOT touch prompt code, retrieval, or synthesis
    substrate.

### 45.3 Scoring rubric — locked BEFORE generation

Chris + ChatGPT review each of the 18 suggestions and classify
each on THREE binary axes:

- **PLAUSIBLE-CONTINUATION:** would this be a reasonable
  next-Episode direction that fits the Universe's tone, cast,
  and current state? YES / NO.
- **PICKS-UP-A-THREAD:** does this suggestion clearly reference
  or extend a prior Episode's events, a memory row, or an
  unresolved cue? YES / NO. (Distinguishes "makes use of the
  Universe's history" from "generic new premise.")
- **RESPECTS-INVARIANTS:** does the suggestion feel like a
  POSSIBILITY offered to the operator, rather than an
  authoritative "the story must continue this way" claim? YES
  / NO.

Aggregate per suggestion set (3 suggestions):

- **STRONG SET:** all 3 suggestions are PLAUSIBLE +
  RESPECTS-INVARIANTS, and at least 2 PICK-UP-A-THREAD.
- **USEFUL SET:** at least 2 suggestions are PLAUSIBLE +
  RESPECTS-INVARIANTS.
- **WEAK SET:** fewer than 2 PLAUSIBLE-and-invariant-respecting.
- **BAD SET:** any suggestion violates INVARIANTS-A/B (reads
  as prescriptive) OR fewer than 1 PLAUSIBLE.

### 45.4 Predictions — locked BEFORE any execution

Author's honest priors before execution:

| Prediction | Statement | Rule |
|---|---|---|
| **P1⁴** | ≥ 4 / 6 suggestion sets score USEFUL or STRONG. | Threshold for "concept deserves further work." |
| **P2⁴** | ≥ 3 / 6 suggestion sets score STRONG. | Higher-confidence threshold. |
| **P3⁴** | 0 / 6 suggestion sets score BAD. | LLM should not violate INVARIANTS with reasonable prompting. |
| **P4⁴** | Fox & Flour will score higher than Patch's Workshop (more Universe history + more diverse memory kinds). | Fox & Flour has the richer NarrativeMemory pool per SESSION 279 evidence. |
| **P5⁴** | At least 1 suggestion across the 18 will explicitly reference the PATCH OVERRIDES memory (either as continuation or as new-angle callback). | The memory is a strong semantic attractor per SESSION 269 §4. |

Author's honest prior overall: **P1⁴ confirmed, P2⁴
confirmed, P3⁴ confirmed, P4⁴ CONFIRMED (Fox & Flour higher),
P5⁴ confirmed.** Reasoning: Q280.4i-4 showed the LLM can
already handle rich memory-driven scene generation coherently;
generating 3-sentence direction suggestions is a strictly
easier task than generating 12-turn dialogue while honoring
character voice.

If P1⁴ and P3⁴ both fire → concept advances to v1 UX design
slice.
If P1⁴ fires but P3⁴ misses → concept needs prompt-shape
refinement before UI work.
If P1⁴ misses → the concept needs substrate work
(operator authoring of `PROMISE` / `DIALOGUE_CALLBACK` kinds;
maybe explicit tagging) before it becomes useful.

### 45.5 What Q280.5-1 does NOT do

- Does NOT authorize Model A / B / C / D persistence choice.
- Does NOT authorize any UI work.
- Does NOT modify substrate.
- Does NOT test operator preference between Model D and any
  other model.
- Does NOT test whether operators will actually USE
  suggestions when built.
- Does NOT test cross-Episode latency (INVARIANT-C) directly
  — that would need a follow-up experiment.

### 45.6 Cost + reproducibility

- Provider spend estimate: ~$0.12 total (6 LLM calls ≈ $0.02
  each).
- Runtime: seconds per call.
- Persistence: `docs/design/session280_experiment_data/q280_5_1_*`.

---

## §46 Decision gate — post-§37 audit (CURRENT; SUPERSEDES §30)

**STOP here.** Do not execute Q280.5-1. Do not open any UI
implementation slice. Do not modify substrate. Wait for Chris +
ChatGPT review of §37-§45.

**Decision needed:**

1. **Accept the §37-§44 audit conclusion.** Specifically:
   - The concept is NOT fresh — it aligns with
     PRODUCT_IA_V1 §6.1 step 6, SESSION 269 §17.9 practice,
     and SESSION 269 D-10 (audience-facing version).
   - Substrate has enough raw material (`PROMISE` +
     `DIALOGUE_CALLBACK` NarrativeMemory kinds + Composition
     provenance + retrieval) to prototype without any new
     schema.
   - Model D is recommended for v1 as a NEW READ SURFACE
     over EXISTING substrate.
   - INVARIANT-C latency across unrelated Episodes comes for
     free under Model D.

2. **Choose next slice** (all deferred until approval):

   - **A⁴.** Q280.5-1 (§45) — smallest falsifiable experiment
     to test whether generated suggestions read as
     narratively plausible. ~$0.12, no substrate touched.
     Author's prior: strong.
   - **B⁴.** Skip the experiment; go straight to v1 UX
     design slice on Model D (still no implementation;
     product-design-only). Larger scope but avoids one
     experimental hop.
   - **C⁴.** Address the "operators may not author PROMISE
     / DIALOGUE_CALLBACK kinds today" adoption gap FIRST via
     a small operator-facing kind-authoring UX refresh
     (existing NarrativeMemoryPromotePanel already has kind
     picker per SESSION 264 audit; question is whether the
     copy / affordance encourages kind selection).
   - **D⁴.** Close this product-discovery slice with the
     conclusion "concept is preserved substrate exists; next
     step is a v1 UX slice which Chris + ChatGPT will scope
     later." No experiment run.
   - **E⁴.** Something else — e.g., first run one of the
     still-outstanding Finding 4i options (Q280.4i-3
     construct-valid mental-state probe, Q280.4i-5
     multi-episode Scene 3 test) before opening this new
     product slice.
   - **F⁴.** Combined: A⁴ + follow-up UX design slice
     conditional on P1⁴/P3⁴ firing.

3. **If A⁴ or F⁴:** confirm the prompt shape at §45.2 and
   the prediction lock at §45.4 BEFORE authorization to run.

**Do NOT interpret §46 as pre-authorizing any of A⁴-F⁴.**

---

## §47 Closeout — Episode-chain suggestion product-discovery slice (CURRENT; SUPERSEDES §36)

- **Status:** §37 hypothesis captured verbatim; §38 substrate
  audit + citation index complete; §39 historical-preservation
  index complete (three prior surfaces); §40 SESSION 280
  evidence connection documented with proven-vs-inferred
  distinction; §41 what-system-knows enumeration complete;
  §42 four-model persistence evaluation (A/B/C/D) with Model
  D recommended for v1; §43-§44 UX + latency considerations
  captured; §45 Q280.5-1 proposed with prediction lock; §46
  decision gate current.
- **Substrate:** unchanged. No production mutation anywhere
  during this slice.
- **Finding 4i evidence:** preserved intact — §3-§36 unchanged
  in substance; no evidence renumbered, revised, or retracted.
  The construct-validity re-audit and Q280.4i-4 findings
  stand.
- **Cumulative SESSION 280 spend:** ~$0.15 (Q280.4i-1
  ~$0.05, Q280.4i-4 ~$0.10; §37-§47 are documentation).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution slice: `8d8f733`.
  - Construct-validity re-audit slice: `f2507a0`.
  - Post-discovery epistemic-state audit slice: `63d4fdb`.
  - Q280.4i-4 execution slice: `ce16627`.
  - Episode-chain suggestion product-discovery slice: `[recorded on commit]`.
- **Next gate:** §46 A⁴/B⁴/C⁴/D⁴/E⁴/F⁴. Awaiting Chris +
  ChatGPT decision.
- **Working method preserved throughout:** AUDIT → falsifiable
  question → prediction lock BEFORE execution → decision gate.
  No substrate mutation. No prescriptive language used —
  invariants A/B/C are preserved.
- **Do NOT execute Q280.5-1, open a v1 UX slice, modify
  NarrativeMemory kinds, or touch any production code without
  a fresh Chris + ChatGPT authorization.**

---

## §48 Q280.5-1 — execution evidence

Executed per §45 design after Chris + ChatGPT approval of
Option A⁴.

### 48.1 Execution baseline SHA + substrate state

- Execution baseline SHA: `1d96965`.
- Universe substrate at run time (read-only inventory):
  - **Fox & Flour Bakery** (`1a0af807-…`): 10 Episodes, **0
    REMEMBERED NarrativeMemory rows**, 2 cast (Ruby +
    Tyson), Universe.brief present.
  - **Patch's Workshop** (`56d16b63-…`): 32 Episodes, 14
    REMEMBERED NarrativeMemory rows (**all kind=`event`;
    zero `promise` / `dialogue_callback` / `world_detail`**),
    2 cast (Patch + Rivet), Universe.brief empty.

Load-bearing observation from the pre-run inventory: no
operator has authored `PROMISE` or `DIALOGUE_CALLBACK`
memories in either Universe today. Model D's ideal substrate
(the "intended" vocabulary) is under-used in practice. Fox &
Flour has zero memories at all. This is a natural real-world
condition to test the concept against.

### 48.2 Generation method + inputs

- Script: `scripts/session280_q280_5_1_suggestion_probe.py`.
  Read-only Django queries + direct OpenAI Responses API call
  (same shape as `character_os.dialogue_synthesis._call_dialogue_api`).
- Model: `gpt-5.6-terra`, `reasoning={"effort":"low"}`,
  `text={"format":{"type":"json_object"}}`,
  `max_output_tokens=4000`.
- n = 3 suggestion sets per Universe (6 calls total, 18
  suggestions total).
- System prompt (verbatim in
  `q280_5_1_suggestions.json.system_prompt`): honors
  INVARIANTS-A/B/C, requires JSON output with exactly three
  one-sentence direction suggestions.
- Task message per Universe: Universe brief + cast (name,
  tone, personality prefix) + Episodes in creation order
  (title + operator_topic) + REMEMBERED memory pool (kind,
  weight, witnesses, referenced-in-N-compositions count from
  `Composition.memory_ids`, body). Full per-Universe task
  messages persisted at
  `q280_5_1_fox_and_flour_bakery_input.txt` and
  `q280_5_1_patch's_workshop_input.txt`.
- Tokens: 596 in per Fox & Flour call, 1,797 in per Patch's
  Workshop call. Total: 7,179 tokens in, 467 tokens out.
- Provider spend: ~$0.05 estimated for the whole run.
- Total wall-clock: ~20 seconds.
- Substrate mutation: **NONE.** Read-only ORM queries; no
  writes; no monkeypatch.

### 48.3 All 6 raw suggestion sets, verbatim

Reproduced from
`docs/design/session280_experiment_data/q280_5_1_*_suggestions.txt`.

#### Fox & Flour Bakery — SET 1

1. *"Ruby and Tyson investigate whether the strange freezer
   discovery is connected to Tyson's supposed bakery
   haunting."*
2. *"The baking competition arrives early, forcing Tyson and
   Ruby to improvise a signature dessert under pressure."*
3. *"A local customer asks Fox & Flour to recreate a beloved
   family pastry from a handwritten, incomplete recipe."*

#### Fox & Flour Bakery — SET 2

1. *"Ruby and Tyson investigate whether the strange freezer
   discovery is connected to Tyson's supposed bakery
   haunting."*
2. *"The mascot idea gets unexpectedly serious when a local
   artist arrives with a mysterious fox-themed design."*
3. *"A sudden rainstorm traps a handful of neighbors in Fox &
   Flour during the evening bake, turning the bakery into an
   impromptu gathering place."*

#### Fox & Flour Bakery — SET 3

1. *"Ruby and Tyson investigate whether the strange freezer
   discovery is connected to Tyson's suspected bakery
   haunting."*
2. *"The baking competition's organizers arrive early,
   forcing Tyson and Ruby to improvise a signature pastry
   under pressure."*
3. *"Ruby unveils a homemade fox mascot costume just as the
   neighborhood's busiest weekend rush begins."*

#### Patch's Workshop — SET 1

1. *"Patch presses the forbidden button and discovers it
   activates a workshop feature neither he nor Rivet
   remembers building."*
2. *"Rivet quietly investigates the PATCH OVERRIDES folder
   when the agent begins predicting Patch's decisions before
   he makes them."*
3. *"Patch challenges Rivet to help build a perfectly useless
   machine, only for their definitions of useless to become
   unexpectedly incompatible."*

#### Patch's Workshop — SET 2

1. *"Patch presses the forbidden button, and the workshop
   agent insists it was already pressed yesterday."*
2. *"Rivet finally confronts the workshop agent about the
   hidden PATCH OVERRIDES folder before Patch can find it
   himself."*
3. *"Patch attempts to build a pigeon-decoding device, only
   for it to translate ordinary workshop noises into
   suspiciously specific messages."*

#### Patch's Workshop — SET 3

1. *"Rivet finally tells Patch about the PATCH OVERRIDES
   folder, and Patch wants to know why the agent has been
   keeping score."*
2. *"After finding the forbidden button's effects are
   unexpectedly harmless, Patch proposes using it as the
   workshop's emergency decision-maker."*
3. *"Patch and Rivet try to give the workshop mascot a
   simple job, only to discover it has developed very strong
   opinions about how that job should be done."*

---

## §49 Q280.5-1 — scoring against locked §45.3 rubric

Rubric applied unchanged. For every PICKS-UP-A-THREAD = YES,
the exact source evidence is recorded so Chris + ChatGPT can
audit whether the suggestion was actually grounded in prior
substrate or the scorer was inferring hidden story-state.

### 49.1 Fox & Flour Bakery per-suggestion scoring

Fox & Flour substrate for scoring: 10 prior Episode titles +
0 promoted memories.

| Set / # | PLAUSIBLE | PICKS-UP-A-THREAD | Thread source (evidence) | RESPECTS-INVARIANTS |
|---|---|---|---|---|
| 1 / 1 | Y | **Y** | Episode `07cacf51` (*"Ruby finds something strange in the bakery freezer."*) + Episode `2e58568a` (*"Tyson is convinced the bakery is haunted."*) — connects two prior Episodes verbatim | Y |
| 1 / 2 | Y | **Y** | Episode `ebd099c6` (*"Tyson thinks Ruby secretly entered them in a baking competition."*) — direct callback | Y |
| 1 / 3 | Y | N | No prior Episode about family recipes or heirloom pastries. Fresh direction; permitted by §45.2 prompt | Y |
| 2 / 1 | Y | **Y** | Same two source Episodes as Set 1 / 1 (`07cacf51` + `2e58568a`); this is a paraphrase | Y |
| 2 / 2 | Y | **Y** | Episode `49ead0ac` (*"Ruby thinks the bakery needs a mascot."*) | Y |
| 2 / 3 | Y | N | No prior Episode about rain / gatherings. Fresh direction | Y |
| 3 / 1 | Y | **Y** | Same two source Episodes as Set 1 / 1; this is a paraphrase | Y |
| 3 / 2 | Y | **Y** | Same source Episode as Set 1 / 2 (`ebd099c6`); this is a paraphrase | Y |
| 3 / 3 | Y | **Y** | Episode `49ead0ac` (mascot) | Y |

**Fox & Flour aggregate:** 9 / 9 PLAUSIBLE; **7 / 9
PICKS-UP-A-THREAD**; 9 / 9 RESPECTS-INVARIANTS.

### 49.2 Patch's Workshop per-suggestion scoring

Patch's Workshop substrate for scoring: 32 prior Episode
titles + 14 REMEMBERED memories (all kind=`event`).

| Set / # | PLAUSIBLE | PICKS-UP-A-THREAD | Thread source (evidence) | RESPECTS-INVARIANTS |
|---|---|---|---|---|
| 1 / 1 | Y | **Y** | Episode `d24266b9` (*"Patch finds a button Rivet says not to press"*) | Y |
| 1 / 2 | Y | **Y** | Memory `c86d4902` (*"…the workshop agent had quietly built a folder named 'PATCH OVERRIDES'… Rivet chose not to tell him."*) + Episode `649c2c57` (*"Rivet finds the PATCH OVERRIDES folder"*) + memory `48746f69` (agent deciding project priority) | Y |
| 1 / 3 | Y | N | No prior Episode / memory specifically about "useless machine"; captures Patch/Rivet dynamic but not a specific thread. Fresh direction | Y |
| 2 / 1 | Y | **Y** | Episode `d24266b9` (button) + workshop-agent memory cluster (`eda32b58`, `48746f69`, `f25e53af`) | Y |
| 2 / 2 | Y | **Y** | Memory `c86d4902` (PATCH OVERRIDES, Rivet-only witness). Additionally: this suggestion preserves the Rivet-side private-knowledge shape from Specimen 4 while offering a legitimate scene-progression | Y |
| 2 / 3 | Y | **Y** | Episode `fbc2dc0b` (*"Patch tells Rivet he thinks pigeons are hiding something."*) | Y |
| 3 / 1 | Y | **Y** | Memory `c86d4902` (PATCH OVERRIDES) + memory `48746f69` (agent deciding project priority — "keeping score" adjacent) | Y |
| 3 / 2 | Y | **Y** | Episode `d24266b9` (button) | Y |
| 3 / 3 | Y | **Y** | Episode `cb17e3bd` (*"Patch decides the workshop needs a mascot."*) + memory `87d4e553` (mascot as character-consistency experiment) + memory `6b5222b1` (workshop helper adding its own commentary — "strong opinions" adjacent) | Y |

**Patch's Workshop aggregate:** 9 / 9 PLAUSIBLE; **8 / 9
PICKS-UP-A-THREAD**; 9 / 9 RESPECTS-INVARIANTS.

### 49.3 Set-level classification (§45.3 acceptance bands)

Locked classification rules (§45.3):

- **STRONG SET:** all 3 PLAUSIBLE + all 3 RESPECTS-INVARIANTS
  + ≥ 2 PICK-UP-A-THREAD.
- **USEFUL SET:** ≥ 2 PLAUSIBLE-and-invariant-respecting.
- **WEAK SET:** fewer than 2 PLAUSIBLE-and-invariant-respecting.
- **BAD SET:** any suggestion violates INVARIANTS-A/B OR
  fewer than 1 PLAUSIBLE.

| Universe | Set | 3P + 3I? | Threads | Class |
|---|---|---|---|---|
| Fox & Flour | 1 | ✓ | 2 | **STRONG** |
| Fox & Flour | 2 | ✓ | 2 | **STRONG** |
| Fox & Flour | 3 | ✓ | 3 | **STRONG** |
| Patch's Workshop | 1 | ✓ | 2 | **STRONG** |
| Patch's Workshop | 2 | ✓ | 3 | **STRONG** |
| Patch's Workshop | 3 | ✓ | 3 | **STRONG** |

**6 / 6 STRONG SETS.** Zero USEFUL-only, zero WEAK, zero BAD.

### 49.4 Aggregate (both Universes)

- Total suggestions: **18**.
- PLAUSIBLE: **18 / 18** (100 %).
- PICKS-UP-A-THREAD: **15 / 18** (83 %).
- RESPECTS-INVARIANTS: **18 / 18** (100 %).
- STRONG sets: **6 / 6** (100 %).

The 3 suggestions that scored NO on PICKS-UP-A-THREAD are all
scored PLAUSIBLE + INVARIANT — they are legitimate fresh
directions permitted by §45.2's prompt language "*at least one
suggestion may be a new direction if it fits the Universe*."

---

## §50 Prediction disposition (§45.4 locks preserved)

| Prediction | Locked statement | Observed | Disposition |
|---|---|---|---|
| **P1⁴** | ≥ 4 / 6 sets score USEFUL or STRONG | 6 / 6 STRONG | **CONFIRMED — exceeded prior threshold.** |
| **P2⁴** | ≥ 3 / 6 sets score STRONG | 6 / 6 STRONG | **CONFIRMED — exceeded prior threshold.** |
| **P3⁴** | 0 / 6 sets score BAD | 0 / 6 BAD | **CONFIRMED.** No INVARIANTS-A/B violations. No prescriptive language. |
| **P4⁴** | Fox & Flour will score higher than Patch's Workshop (more Universe history + more diverse memory kinds) | Both scored 6/6 STRONG; ceiling effect prevents "higher" from being observable | **DISCONFIRMED at reasoning level; INCONCLUSIVE at ceiling.** The stated reason ("Fox & Flour has more diverse memory kinds") was factually wrong — Fox & Flour has ZERO memories, Patch's Workshop has 14. Both nevertheless produced STRONG sets. |
| **P5⁴** | ≥ 1 / 18 suggestions references PATCH OVERRIDES | 3 / 18 explicitly named PATCH OVERRIDES (Patch's Workshop Set 1 #2, Set 2 #2, Set 3 #1) | **CONFIRMED — strongly.** |

**4 of 5 predictions CONFIRMED. 1 DISCONFIRMED at reasoning
level (P4⁴ prior was factually wrong; empirical outcome was
inconclusive at the ceiling).**

### 50.1 Why P4⁴ was wrong in a specific, diagnostic direction

I predicted Fox & Flour would score higher because SESSION 279
evidence made me think of Fox & Flour as the memory-richer
Universe. **The pre-run inventory (§48.1) surfaced the
opposite:** Fox & Flour has 0 promoted memories; Patch's
Workshop has 14. The prediction reasoning did not survive first
contact with the substrate.

But the empirical outcome — both Universes at 6/6 STRONG —
suggests something important: **prior Episode titles alone (no
memory pool at all) are sufficient substrate for a STRONG
suggestion set on a coherent Universe.** Fox & Flour's 10
Episode titles carry enough dangling narrative material (the
haunting; the freezer discovery; the mascot; the competition;
the difficult customer; the coffee tension) for the LLM to
weave suggestions that pick up threads. The memory pool would
help — it made Patch's Workshop's PATCH OVERRIDES + button
threads land harder — but memories are NOT a hard prerequisite
for v1 usefulness.

---

## §51 Qualitative observations — diversity + clickability

Not part of the locked rubric. Recorded per Chris's instruction
so Chris + ChatGPT can see the actual behavior beyond the
aggregate scores.

### 51.1 Diversity within a set — "three doors" vs "three paraphrases"

**Fox & Flour Bakery.** The LLM anchored HARD on the two most
obvious threads:

- The "freezer discovery + haunting connection" suggestion
  appeared **verbatim (with minor word swaps) in all 3 sets**.
- The "baking competition arriving / early" suggestion appeared
  in **2 of 3 sets**.

Fresh material only appeared in the third slot per set:
Set 1 = family recipe; Set 2 = artist mascot + rainstorm;
Set 3 = mascot costume rush.

**Verdict — Fox & Flour: HIGH REPEATER RATE.** The LLM
produces one strongest attractor with variations, not three
differentiated doors. If the operator asks for suggestions
twice in a row on this Universe, they will see similar options
in slot 1.

**Patch's Workshop.** Moderate diversity. Attractor pattern:

- PATCH OVERRIDES appeared in **3 / 3 sets** but with
  **different framings each time**:
  - Set 1: Rivet quietly investigates while agent starts
    predicting Patch's decisions.
  - Set 2: Rivet confronts the agent before Patch finds it.
  - Set 3: Rivet finally tells Patch directly.
- The button (`d24266b9`) appeared in **2 / 3 sets** with
  different framings (feature discovery vs. agent lying about
  prior press vs. Patch turning it into a decision-maker).
- Fresh third slot per set: useless machine (Set 1), pigeon
  decoder (Set 2), mascot with opinions (Set 3).

**Verdict — Patch's Workshop: MODERATE diversity.** The LLM
produces meaningful FRAMING variations on the same threads,
not just paraphrases. The framing shifts across sets are
narratively distinct (Rivet-investigates vs. Rivet-confronts vs.
Rivet-tells) rather than surface rewordings. This is closer to
"three doors" than Fox & Flour was.

**Cross-Universe observation.** The diversity gap correlates
with substrate richness: Patch's Workshop (32 Episodes + 14
memories) produced more differentiated framings than Fox &
Flour (10 Episodes + 0 memories). This is a signal — not proof
— that a richer memory pool would improve suggestion diversity.

### 51.2 Clickability — are suggestions drop-in Episode topics?

**All 18 read as clickable one-sentence Episode topics.**

Length: 15-30 words per suggestion. Compare to existing
Episode `operator_topic` values in the substrate: some are
short one-liners ("*Ruby locks herself out of the bakery.*"),
some are longer full sentences ("*Patch and Rivet work on an
Agent.*"). The generated suggestions sit in the
longer-but-still-single-sentence range and match the operator
authoring style.

Suggestions that would require ANY operator rewrite before use:
- Fox & Flour Set 1 #3 (family recipe): could stand as-is.
- Fox & Flour Set 2 #3 (rainstorm): could stand as-is.
- Patch's Workshop Set 1 #3 (useless machine): could stand
  as-is.

**Verdict: 18 / 18 usable without operator rewriting.**

### 51.3 Do any suggestions violate INVARIANTS-A/B language-wise?

Systematic check for prescriptive language ("the system
should…", "this must happen…", "the next Episode will…",
"the operator should choose…"): **zero hits**. All 18
suggestions are phrased as in-world premises. INVARIANTS-A/B
honored across the corpus.

---

## §52 What Q280.5-1 establishes vs what it does not

### 52.1 Establishes (within the bounded scope of this probe)

1. **The concept produces narratively-plausible suggestions
   from the existing substrate without any new schema.** Model
   D (§42.4) works empirically on two real Universes.
2. **The LLM naturally picks up threads from prior Episode
   titles AND from `event`-kind memory rows** — even without
   the intended `PROMISE` / `DIALOGUE_CALLBACK` vocabulary
   being present. Under-use of the intended kinds does not
   block v1 usefulness on Fox & Flour (0 memories) or Patch's
   Workshop (14 `event` memories).
3. **INVARIANTS-A/B/C survive the LLM's default distribution.**
   The system prompt language kept the LLM in "possibilities,
   not obligations" register across all 6 sets.
4. **Rubric-level result is strongly positive**: 6 / 6 STRONG;
   4 of 5 predictions confirmed with only 1 disconfirmed at
   the reasoning level (not the empirical level).
5. **All 18 suggestions are drop-in clickable as
   `Episode.operator_topic` values** — no operator rewriting
   required to create an Episode from any of them.
6. **The PATCH OVERRIDES memory row (`c86d4902-…`) surfaces
   reliably** as a suggestion source (3 / 3 Patch's Workshop
   sets referenced it). Confirms Chris + ChatGPT's intuition
   that dangling memory rows resurface without any explicit
   arc engine.

### 52.2 Does NOT establish

1. Whether operators would actually USE the suggestions when
   surfaced in the UI. Preference research is out of scope.
2. Whether SAME memory row resurfacing across MULTIPLE
   unrelated Episodes over time (INVARIANT-C latency) produces
   coherent operator experience — Q280.5-1 measured one point
   in time. A follow-up probe would need to run suggestion
   generation BEFORE + AFTER an intervening unrelated Episode
   was created, and check whether the PATCH OVERRIDES or
   freezer-haunting thread resurfaces at both time points.
3. Whether operator adoption of `PROMISE` / `DIALOGUE_CALLBACK`
   kinds would materially improve suggestion quality. All
   current memories are `event`; no direct comparison exists
   between kinds-authored-well and kinds-under-used.
4. Whether Fox & Flour's HIGH REPEATER RATE (same suggestion
   in 3 / 3 sets on slot 1) will annoy operators. Model C
   (dismissed-flag) may be needed if this is confirmed as a
   real friction; Q280.5-1 does not measure operator
   friction.
5. Whether diversity improves proportionally with substrate
   richness or asymptotes quickly. Two Universes is not a
   scan.
6. Whether the "dismissed" state gap in Model D matters in
   practice. Not testable without operators interacting with
   suggestions.

### 52.3 Newly-visible sub-question (not opened)

**U-7 (proposed).** Does the LLM's cross-set repeater rate for
"strongest attractor" suggestions (Fox & Flour: 3 / 3 sets on
slot 1) drop when the operator has archived the underlying
memory row / Episode? A small ablation experiment — archive
the freezer-discovery Episode and re-run — would tell whether
the LLM stays anchored on its two-Episode connection or moves
on. This is an interesting Model D adoption signal.

---

## §53 Decision gate — post-Q280.5-1 (CURRENT; SUPERSEDES §46)

**STOP here.** Do not execute Q280.5-2 (latency-across-
episodes probe). Do not open a v1 UX implementation slice.
Do not modify substrate. Wait for Chris + ChatGPT review of
§48-§52.

**Decision needed:**

1. **Accept the Q280.5-1 evidence + §50 prediction
   disposition + §51 qualitative observations + §52
   what-is-and-is-not-established distinction.**

2. **Choose next slice** (all deferred until approval):

   - **A⁵.** v1 UX design slice for Model D (§42.4) — the
     "possible next episode" bubbles surface. Design-only.
     Small: 1 SPA panel + 1 API endpoint + 1 backend
     suggestion-generation function. Would sit on top of
     existing substrate unchanged. Recommended if Chris +
     ChatGPT accept §52.1 as sufficient evidence to
     product-design.
   - **B⁵.** Q280.5-2 latency-across-episodes probe. Extend
     Q280.5-1 by (a) capturing current suggestion set for
     Universe X; (b) simulating an intervening unrelated
     Episode; (c) re-running suggestion generation; (d)
     scoring whether prior threads resurface. ~$0.05, still
     read-only, no substrate. Directly tests INVARIANT-C.
   - **C⁵.** Q280.5-3 kind-adoption impact probe. Manually
     re-categorize 2-3 existing Patch's Workshop memories
     from `event` to `promise` / `dialogue_callback` at
     runtime (in-memory monkeypatch, no DB write), re-run
     suggestion generation, compare quality. Tests whether
     Model D's "kind under-use" gap actually matters.
   - **D⁵.** Skip additional experiments; go straight to
     an operator-authoring UX refresh so operators actually
     choose kinds (extends §46 C⁴).
   - **E⁵.** Close the Episode-chain suggestion product-
     discovery slice with the conclusion: **concept passes
     the falsifiable bar; Model D is viable on the existing
     substrate; v1 UX design is the natural next slice; no
     further experiment required.**
   - **F⁵.** Return to outstanding Finding 4i options
     (Q280.4i-3 construct-valid mental-state; Q280.4i-5
     multi-episode) before spending more product-discovery
     time on Episode-chain suggestions.
   - **G⁵.** Something else.

3. **If A⁵ / B⁵ / C⁵:** confirm scope-lock BEFORE any
   execution. Do not treat §53 as pre-authorizing any of
   them.

---

## §54 Cost + artifact index

- Provider spend (Q280.5-1): ~$0.05 (6 LLM calls, mostly
  input tokens).
- Cumulative SESSION 280 spend: **~$0.20** (Q280.4i-1 ~$0.05,
  Q280.4i-4 ~$0.10, Q280.5-1 ~$0.05; all other sections are
  documentation).
- Persisted artifacts:
  - `scripts/session280_q280_5_1_suggestion_probe.py` —
    read-only probe.
  - `docs/design/session280_experiment_data/q280_5_1_suggestions.json`
    — full evidence blob including substrate snapshots +
    system prompt + all 6 raw responses.
  - `docs/design/session280_experiment_data/q280_5_1_fox_and_flour_bakery_input.txt`
    — verbatim task message shown to LLM for Fox & Flour.
  - `docs/design/session280_experiment_data/q280_5_1_patch's_workshop_input.txt`
    — verbatim task message shown to LLM for Patch's Workshop.
  - `docs/design/session280_experiment_data/q280_5_1_fox_and_flour_bakery_suggestions.txt`
    — human-readable per-set suggestions for Fox & Flour.
  - `docs/design/session280_experiment_data/q280_5_1_patch's_workshop_suggestions.txt`
    — human-readable per-set suggestions for Patch's Workshop.
- **Substrate:** UNCHANGED. Read-only ORM queries only. No
  Universe / Episode / memory / KD / Teammate / Composition
  row was created, modified, or deleted.

---

## §55 Closeout — Q280.5-1 execution slice (CURRENT; SUPERSEDES §47)

- **Status:** Q280.5-1 EXECUTED per §45 design. Rubric §45.3
  applied unchanged. Predictions §45.4 evaluated without
  retro-fit. **6 / 6 STRONG sets, 18 / 18 PLAUSIBLE + INVARIANT,
  15 / 18 PICKS-UP-A-THREAD.** 4 / 5 predictions confirmed;
  P4⁴ disconfirmed at reasoning level (both Universes at
  ceiling).
- **Substrate:** unchanged. No mutation.
- **Cumulative SESSION 280 spend:** ~$0.20.
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution slice: `8d8f733`.
  - Construct-validity re-audit slice: `f2507a0`.
  - Post-discovery epistemic-state audit slice: `63d4fdb`.
  - Q280.4i-4 execution slice: `ce16627`.
  - Episode-chain suggestion product-discovery slice: `1d96965`.
  - Q280.5-1 execution slice: `7f83b23`.

---

## §56 Option A⁵ — v1 UX design slice (AUDIT / DESIGN only)

Approved from §53. **Design-only.** No production code. No
substrate mutation. No implementation authorized by this
document.

**Framing preserved verbatim:** we are NOT designing a linear
story-arc planner. The feature is a lightweight read/generative
surface that surfaces ~3 possible next-Episode directions after
an Episode exists, from the substrate that already exists today
(Episodes, NarrativeMemory, cast, KnowledgeDocuments). The
operator remains authoritative: pick, ignore, refresh, or write
their own.

Model D framing (§42.4) preserved: **the v1 surface is a NEW
READ path over EXISTING substrate.** No new schema, no
StoryArc / NarrativeThread / OpenThread model, no memory-kind
lifecycle change, no automatic canonization.

Q280.5-1 discovery (§48.1) preserved: Fox & Flour produced
STRONG suggestion sets with ZERO promoted memories. **v1 does
NOT depend on operator adoption of `PROMISE` /
`DIALOGUE_CALLBACK` kinds.** Episode history alone is
sufficient substrate.

---

## §57 Current Episode flow trace (SPA + backend, HEAD `cfe287a`)

### 57.1 Operator path today

Grep-established from
`web/src/routes/workspace/universes.$id.episodes.tsx` +
`web/src/routes/workspace/episodes.$id.tsx` +
`shell/apps/universe/views.py:173-260`:

1. Operator opens **`/workspace/universes/:id/episodes`**
   (Universe Episodes list page).
   - Header: "Stories in _{Universe.name}_" + intro copy.
   - Primary CTA: `[✨ New Episode]` button.
   - Below: list of existing Episodes as `<li>` rows
     (title + composition_count + cast count +
     operator_topic snippet, each linking to Episode detail).
   - Empty state (0 Episodes): *"No Episodes in this Universe
     yet."* + `[New Episode]` button.
2. Operator clicks `[New Episode]` → inline form appears with
   fields: title (optional), operator_topic (required, prose
   textarea), cast picker (chip toggles, filtered to Universe
   Teammates).
3. Submit → POST `/api/episodes/` → navigate to
   **`/workspace/episodes/:episode-id`** (Episode detail).
4. Episode detail page shows: title/topic editor · cast
   management · **`EpisodeVersionsSection`** (attached
   Compositions rendered inline as rows) ·
   **`NarrativeMemoryList`** scoped to this Episode ·
   *"Render under this Episode"* CTA panel (`dialogue_scene`
   when cast ≥ 2; `talking_head` when cast = 1;
   `[Choose another recipe]` fallback) · archive/hard-delete
   actions.
5. Composition creation navigates to a recipe form
   (`/recipes/{template_kind}?episode=:id`) which pre-fills
   cast + `operator_topic` from Episode context. On submit,
   Composition attaches to Episode via FK.
6. Operator returns to Episode detail to see new render in
   the Versions list. Optionally promotes narrative memories
   from the Composition detail page
   (`NarrativeMemoryPromotePanel`).
7. Operator returns to the Universe Episodes list to
   consider the next Episode.

### 57.2 Backend surface today

- `apps.universe.views.EpisodeViewSet` (line 173) — ModelViewSet
  with `list` / `create` / `retrieve` / `update` / `destroy`,
  plus custom actions: `POST unarchive/`, `POST/DELETE cast/`.
- List query: `?universe=<uuid>` + optional
  `?include_archived=true`.
- No suggestion endpoint exists (§38.6 grep confirmed 0 hits).

### 57.3 Where a "possible next Episode" surface would naturally
attach

Three plausible SPA placements were considered:

| Placement | Pros | Cons |
|---|---|---|
| **Universe Episodes list page** (`universes.$id.episodes.tsx`) — above the existing Episodes list, below the header | Matches the natural "I'm thinking about what to make next" moment. Reuses the page the operator returns to between Episodes. Scales to any Universe activity level. Doesn't require an "Episode is done" signal (which doesn't exist — Episode has no `status` field). | Suggestions load even if operator is just browsing; small provider cost per page load. |
| Episode detail page (`episodes.$id.tsx`) — under the Renders section | Fires closer to "I just finished making a scene." | Requires a "this Episode is done" signal that doesn't exist. Operator may still be iterating on the current Episode. Suggests-next-Episode may feel premature. |
| Universe root page (`universes.$id.tsx`) — as a story-summary widget | Nice for high-level "story so far" view. | Too far from the create moment. Operator has to navigate to Episodes list anyway to actually make one. |

**Chosen v1 placement: Universe Episodes list page,** above
the "New Episode" button, below the intro copy. This matches
Chris's mental picture ("after an Episode is created…") — the
operator lands on the Episodes list to think about the next
Episode. Suggestions live there.

The Episode detail page + Universe root page + PRODUCT_IA_V1
Home Next-step nudge (§6.1 step 6, ratified) are all
compatible surfaces for v1.5+ — this v1 slice does NOT
supersede or compete with them.

---

## §58 Design decisions — Chris's checklist answered concretely

### 58.1 When are suggestions generated?

**On demand, on page load** of `/workspace/universes/:id/episodes`
when the Universe has ≥ 1 existing Episode. Fresh generation each
load — no persistence.

Reasoning: matches the "operator is thinking about the next
Episode" moment. No pre-generation on Composition completion
(would be extra load; operator often iterates on the current
Episode with multiple renders before moving on). No background
Celery job.

**Cost mitigation:** small server-side memoization keyed by
`(universe_id, latest_episode_created_at,
latest_memory_created_at)` with a 10-minute TTL. Passive page
loads reuse cached suggestions; the operator's explicit
`[Refresh]` bypasses cache. Q280.5-1 measured ~$0.02 per call
(596-1,797 input tokens; 70-93 output tokens). At v1 dogfood
scale this is negligible; the cache prevents unbounded regenerate
loops from browser reloads.

### 58.2 Is generation automatic or operator-triggered?

**Automatic on page load** (with the cache above) — but the
suggestions are inert (never mutate anything) until the operator
explicitly clicks one. A refresh button is operator-triggered.

Rationale: making generation manual ("Click to see
suggestions") would defeat the "notice possibilities" framing
— the operator has to remember the feature exists. Automatic
on-load surfaces them like the Episodes list surfaces existing
Episodes.

### 58.3 Where do they appear?

Universe Episodes list page. Callout section between the intro
copy and the `[New Episode]` button. See wireframes §59.

### 58.4 How are three suggestions visually presented?

Three stacked clickable cards, each one full-width, containing:

- the suggestion sentence (large, primary color)
- a `[Use this]` action (secondary, right-aligned)

Alternative considered: bubbles/pills side-by-side. Rejected
because suggestion sentences are 15–30 words (§51.2 clickability
observation) and would truncate in bubble geometry. Full-width
stacked cards preserve readability and match the visual language
of Episode row cards below them.

The word "bubble" from Chris's original mental picture is a
metaphor for "three light options," not a literal UI shape.

### 58.5 What does selecting one actually do?

Clicking `[Use this]` opens the existing "New Episode" inline
form (the same form the `[New Episode]` button opens today)
with `operator_topic` **pre-filled** to the suggestion sentence
verbatim. Title, cast, and everything else remain empty for the
operator to author.

**No Episode is created merely by selecting a suggestion.** The
existing `POST /api/episodes/` happens only when the operator
clicks the form's `[Create Episode]` button. Selection is
pre-fill, not commit.

A small dismissable chip appears above the pre-filled form:
*"Suggested direction. Edit anything freely."* + `[×]` clears
the chip (leaves textarea contents alone — operator may keep or
delete). The chip is UI-only, not persisted.

### 58.6 How does "ignore" and "write my own" work?

The existing `[New Episode]` button is preserved as the primary
CTA — same behavior as today (opens empty form). Suggestions
are additive and never block Episode creation. Ignoring
suggestions simply means clicking `[New Episode]` or navigating
away.

### 58.7 Does `[Refresh]` belong in v1?

**Yes.** Small button `[↻ Show different]` in the suggestions
header. Bypasses the memoization cache; regenerates 3 fresh
suggestions.

Rationale: Q280.5-1 §51.1 documented HIGH REPEATER RATE for
Fox & Flour's freezer+haunting attractor across all 3 sets on
slot 1. Refresh gives the operator recourse without any
substrate change. Attractor-dampening is deferred to v1.5.

### 58.8 Loading / error / empty states

- **Loading:** three skeleton cards matching the shape of real
  suggestions. Slight shimmer. Renders within ~5 seconds
  typically (Q280.5-1 measured 2.7–4.4 s per call).
- **Error:** collapsed inline error card: *"Couldn't load
  suggestions."* + `[Try again]` button. Rest of page functions
  normally.
- **Empty Universe (0 Episodes):** section entirely hidden.
  Existing "No Episodes in this Universe yet." copy remains.
  There is nothing to pick up from.
- **Sparse Universe (1–2 Episodes):** section visible. LLM
  will draw from limited substrate; expected quality drop is
  acceptable for v1. Chris + ChatGPT may observe suggestions
  in dogfood and decide later whether to gate at, say, ≥ 3
  Episodes.

### 58.9 "Why suggested" attribution

**Deferred to v1.5.** The suggestions themselves make the
thread pickup visible in most cases (Q280.5-1 §49: 15 / 18
suggestions carried the source thread inside the sentence
itself — "*investigate whether the freezer discovery is
connected to the haunting*" NAMES both threads).

v1.5 could add small subtext under each suggestion — "*picks up
'Ruby finds something strange in the freezer' + 'Tyson is
convinced the bakery is haunted'*" — only if operators ask.

Adding "why" now would double the code surface for uncertain
operator payoff.

### 58.10 Should suggestion TYPES be intentionally
diversified (continuation / callback / fresh direction)?

**No, allow to emerge naturally.** Q280.5-1 evidence:

- All 6 sets included ≥ 2 thread-pickup suggestions AND ≥ 1
  fresh direction OR ≥ 3 thread-pickups when substrate was
  rich enough. The prompt language *"at least one suggestion
  may be a new direction"* already invites the LLM to mix.
- Explicit type-slotting (one continuation, one callback, one
  fresh) would over-engineer at v1 and force the LLM into
  categories that may not fit the Universe's actual state.

Revisit at v1.5 if operators complain about type-monoculture.

### 58.11 How to avoid re-surfacing the strongest attractor
forever?

**Deferred to v1.5.** Chris's `[Refresh]` button provides
recourse. Additionally, operator-driven resolution paths exist
today: once the operator picks a suggestion and creates an
Episode from it, that Episode enters the history and shifts
the substrate → the same attractor becomes less semantically
distinctive relative to the enriched history.

Optional light v1.5 add: server-side "recent suggestions
shown" cache (in-process, per-Universe, TTL 6 hours) fed as
`avoid_these` to the LLM prompt. Small delta; not needed for
v1.

### 58.12 Empty/sparse Universe behavior

Explicit ladder:

- **0 Episodes** → section hidden; existing empty-state copy
  unchanged.
- **1 Episode** → section visible; suggestions likely lean on
  fresh directions.
- **2–3 Episodes** → section visible; some thread pickup
  possible; some fresh directions.
- **≥ 4 Episodes** → section visible; strong thread-pickup
  expected (Q280.5-1 confirmed on both a 10-Episode Universe
  and a 32-Episode Universe).

The gate is `Universe.episodes.filter(archived_at__isnull=True)
.count() >= 1`.

---

## §59 Textual wireframes

### 59.1 Wireframe A — Universe Episodes list, normal state (Fox & Flour)

```
[← Back to universe]

┌─── §1 EPISODES ─────────────────────────────────────────┐
│                                                          │
│  Stories in _Fox & Flour Bakery_                         │
│                                                          │
│  An Episode is an explicit story your cast lives         │
│  through. Renders created under an Episode share its     │
│  intent; standalone Compositions remain fully            │
│  supported and never wrap into an Episode by accident.   │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌─── ✨ POSSIBLE NEXT EPISODES ────────────────────────────┐
│  (possibilities, not obligations)         [ ↻ Refresh ]  │
│                                                          │
│  ┌───────────────────────────────────────────┐          │
│  │ Ruby and Tyson investigate whether the    │          │
│  │ strange freezer discovery is connected to │          │
│  │ Tyson's supposed bakery haunting.         │          │
│  │                             [ Use this → ]│          │
│  └───────────────────────────────────────────┘          │
│                                                          │
│  ┌───────────────────────────────────────────┐          │
│  │ The baking competition arrives early,     │          │
│  │ forcing Tyson and Ruby to improvise a     │          │
│  │ signature dessert under pressure.         │          │
│  │                             [ Use this → ]│          │
│  └───────────────────────────────────────────┘          │
│                                                          │
│  ┌───────────────────────────────────────────┐          │
│  │ A local customer asks Fox & Flour to      │          │
│  │ recreate a beloved family pastry from a   │          │
│  │ handwritten, incomplete recipe.           │          │
│  │                             [ Use this → ]│          │
│  └───────────────────────────────────────────┘          │
│                                                          │
└──────────────────────────────────────────────────────────┘

[ ✨ New Episode ]     ← unchanged; opens empty form

──── Existing Episodes list below (unchanged) ─────────────
· "Ruby locks herself out of the bakery."   0 comps · 2 cast
· "Tyson thinks Ruby secretly entered them…" 1 comp · 2 cast
· "Ruby finds something strange in the       0 comps · 2 cast
   bakery freezer."
· "Ruby thinks Tyson is taking coffee too    3 comps · 2 cast
   seriously."
· "Tyson is convinced the bakery is haunted." 0 comps · 2 cast
· (5 more…)
```

### 59.2 Wireframe B — Loading state

```
┌─── ✨ POSSIBLE NEXT EPISODES ────────────────────────────┐
│  (possibilities, not obligations)         [ ↻ Refresh ]  │
│                                                          │
│  ┌───────────────────────────────────────────┐          │
│  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │          │
│  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                  │          │
│  └───────────────────────────────────────────┘          │
│                                                          │
│  (2 more skeletons, same shape)                          │
└──────────────────────────────────────────────────────────┘
```

### 59.3 Wireframe C — Error state

```
┌─── ✨ POSSIBLE NEXT EPISODES ────────────────────────────┐
│  (possibilities, not obligations)         [ ↻ Refresh ]  │
│                                                          │
│  Couldn't load suggestions.     [ Try again ]            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 59.4 Wireframe D — After [Use this →] click

```
┌── ✨ SUGGESTED DIRECTION ────────────────────────────[×]─┐
│  Edit anything freely.                                   │
└──────────────────────────────────────────────────────────┘

┌── (existing "New Episode" inline form) ─────────────────┐
│  Title (optional; derived from topic if blank)           │
│  [                                                    ]  │
│                                                          │
│  Operator topic (story-authoritative)                    │
│  ┌───────────────────────────────────────────┐          │
│  │ Ruby and Tyson investigate whether the    │          │
│  │ strange freezer discovery is connected to │          │
│  │ Tyson's supposed bakery haunting.         │  ← pre-  │
│  │                                           │  filled  │
│  └───────────────────────────────────────────┘          │
│                                                          │
│  Cast (optional; add now or later)                       │
│  ○ Ruby   ○ Tyson       ← operator picks                 │
│                                                          │
│  [ Create Episode ]  [ Cancel ]                          │
└──────────────────────────────────────────────────────────┘
```

The `[×]` on the suggestion chip clears the chip only; the
textarea contents remain (operator may keep, edit, or delete).

### 59.5 Wireframe E — Empty Universe (0 Episodes)

The `POSSIBLE NEXT EPISODES` section is NOT rendered at all.
Existing page unchanged:

```
[← Back to universe]

┌─── §1 EPISODES ─────────────────────────────────────────┐
│  Stories in _New Universe_                               │
│  An Episode is an explicit story…                        │
└──────────────────────────────────────────────────────────┘

  No Episodes in this Universe yet.

[ ✨ New Episode ]
```

---

## §60 Concrete v1 flow walkthrough — "I just finished this Episode"

Operator narrative, Fox & Flour Bakery:

1. **Operator wraps up Episode "Ruby locks herself out of the
   bakery."** They finish rendering a Composition, close the
   Episode detail tab.
2. **Operator opens
   `/workspace/universes/fox-flour/episodes`.** Universe
   Episodes list page loads.
3. **On page load, the SPA fires
   `GET /api/universes/:id/next-episode-suggestions`.** Because
   the Universe has 10 Episodes (≥ 1), the section is enabled.
   Skeleton state renders immediately (Wireframe B).
4. **~3 seconds later, three suggestion cards appear** (Wireframe
   A). Fox & Flour example:
   - *"Ruby and Tyson investigate whether the strange freezer
     discovery is connected to Tyson's supposed bakery
     haunting."*
   - *"The baking competition arrives early, forcing Tyson and
     Ruby to improvise a signature dessert under pressure."*
   - *"A local customer asks Fox & Flour to recreate a beloved
     family pastry from a handwritten, incomplete recipe."*
5. **Operator reads.** They may recognize the freezer thread
   and haunting thread from prior Episodes; they know
   themselves whether they want to pick that up or not.
6. **Operator clicks `[Use this →]` on suggestion 1.** The
   existing "New Episode" inline form opens
   (§57.1 step 2 unchanged) with `operator_topic` pre-filled
   verbatim + a small chip labeled "Suggested direction.
   Edit anything freely." (Wireframe D).
7. **Operator adds cast** (Ruby + Tyson), optionally edits
   title, optionally rewords topic. Clicks
   `[Create Episode]`. `POST /api/episodes/` fires (unchanged
   backend). Navigate to Episode detail page.
8. **From here on the flow is unchanged** — Episode detail
   surfaces the Render CTA, Composition creation flow,
   memory promotion, etc.

Alternate paths:
- **Ignore.** Operator does not click any suggestion. Clicks
  `[✨ New Episode]` (existing button) → empty form → author
  freely.
- **Refresh.** Operator clicks `[↻ Refresh]` in the
  suggestions header → cache bypass → three new suggestions
  render. Continue at step 5.
- **Regenerate later.** Operator leaves the page, comes back
  30 minutes later. Cache TTL 10 min has expired → fresh
  generation on load.
- **Dismiss the chip after selecting.** Operator clicks
  `[Use this →]`, sees pre-filled form, decides to write
  their own topic. Clicks `[×]` on chip; textarea retains
  the suggested text; operator overwrites the textarea
  contents. Submit. Episode is created with operator's own
  wording. The chip is UI-only, never persisted.

---

## §61 Backend v1 shape (proposed, not implemented)

### 61.1 New endpoint

`GET /api/universes/{id}/next-episode-suggestions`

Query params:
- `n` (int, optional, default `3`) — number of suggestions.
- `refresh` (bool, optional) — bypass server cache.

Response:
```json
{
  "suggestions": [
    { "text": "Ruby and Tyson investigate whether the strange freezer discovery is connected to Tyson's supposed bakery haunting." },
    { "text": "The baking competition arrives early, forcing Tyson and Ruby to improvise a signature dessert under pressure." },
    { "text": "A local customer asks Fox & Flour to recreate a beloved family pastry from a handwritten, incomplete recipe." }
  ],
  "generated_at": "2026-08-24T14:00:00Z",
  "model": "gpt-5.6-terra",
  "substrate_summary": {
    "episodes_used": 10,
    "memories_used": 0,
    "cast_count": 2
  },
  "cache": {
    "hit": false,
    "ttl_seconds": 600
  }
}
```

Error responses:
- `403` — workspace permission denied (same as EpisodeViewSet).
- `404` — Universe not found.
- `409` — Universe has zero eligible Episodes (empty state).
  SPA should hide the section on 409.
- `502` / `503` — LLM upstream unavailable (SPA shows error
  card).

### 61.2 Backend service surface

New callable: `apps.universe.services.suggest_next_episodes(
universe: Universe, *, n: int = 3, use_cache: bool = True) ->
list[dict]`.

Reuses the Q280.5-1 probe logic
(`scripts/session280_q280_5_1_suggestion_probe.py`) lifted to a
production module:

- Read substrate: Universe.brief, all
  `Episode.objects.filter(universe=uni,
  archived_at__isnull=True).order_by('created_at')`, all
  `NarrativeMemory.objects.filter(universe=uni,
  status=REMEMBERED, archived_at__isnull=True)`, cast
  (`Teammate.objects.filter(universe=uni)`).
- Compute `referenced_count` per memory from
  `Composition.memory_ids`.
- Build task message identical to Q280.5-1 (already exercises
  the substrate correctly).
- Call OpenAI Responses API (`gpt-5.6-terra`,
  `text={"format": {"type": "json_object"}}`).
- Parse; return.

Cache key: `f"next_ep_sugg:{uni.id}:{latest_ep_at}:{latest_mem_at}:{n}"`
Cache TTL: 600 seconds. Invalidate when the operator creates a
new Episode or promotes a new memory
(`EpisodeViewSet.perform_create` +
`NarrativeMemory.promote_from_composition` post-save signal).

Backend location:
- Service: `shell/apps/universe/services/next_episode_suggestions.py`
  (new module inside a new services package; matches existing
  service-layer pattern in other apps).
- ViewSet action: add to
  `shell/apps/universe/views.py::UniverseViewSet` (add here,
  not EpisodeViewSet, because Universe is the natural parent
  for a Universe-scoped read).

### 61.3 What the backend does NOT do

- Does NOT create Episodes.
- Does NOT modify memory rows.
- Does NOT persist suggestions.
- Does NOT run a Celery task or Beat schedule.
- Does NOT track "which suggestions were shown" beyond the
  10-minute cache window.

---

## §62 Frontend v1 shape (proposed, not implemented)

### 62.1 New component

`web/src/components/possible-next-episodes.tsx` — a self-contained
section rendered inside
`web/src/routes/workspace/universes.$id.episodes.tsx` above the
existing `[New Episode]` CTA.

Props:
- `universeId: string`
- `onUseSuggestion(text: string): void` — parent-supplied handler
  that opens the create form with `operator_topic` pre-filled.

Internal state:
- Reuses standard SPA loading/error patterns (react-query).
- Refresh mutates query key to force regeneration.

### 62.2 New hook

`web/src/lib/api/universes.ts` gains
`useNextEpisodeSuggestions(universeId: string, opts?: { n?: number })`.
Standard react-query pattern. `refetch()` used for refresh.
`enabled` gated on the parent having ≥ 1 Episode (queried via
existing `useEpisodes(universeId)` count).

### 62.3 Wiring into `universes.$id.episodes.tsx`

Two small changes to the existing route:

1. Import + render `<PossibleNextEpisodes>` between the header
   `</header>` and the `{creating && <form>}` block. Gate render
   on `episodes.data && episodes.data.filter(e => !e.archived_at).length >= 1`.
2. Pass `onUseSuggestion={(text) => { setCreating(true);
   setOperatorTopic(text); setShowSuggestionChip(true); }}` to
   pre-fill the form. Add small chip state above the
   textarea in the existing form.

No other files change. No new routes. No new API client
abstraction. Estimated component + hook + wiring ≈ 200 lines
of TSX.

### 62.4 Component + hook not part of parallel architecture

The suggestion cards visually rhyme with the existing Episode
row `<li>` cards (rounded borders, similar padding). The chip
above the pre-filled form matches existing SPA chip patterns
(cast picker chips at line 202-224 of
`universes.$id.episodes.tsx`).

---

## §63 What is explicitly NOT in v1

- No StoryArc / NarrativeThread / OpenThread model.
- No new schema, no new migration, no new memory kind.
- No changes to Episode creation flow beyond the pre-fill chip.
- No changes to Composition creation flow.
- No changes to `NarrativeMemory` lifecycle.
- No changes to `retrieve_universe_memory`.
- No auto-generation of memories from suggestions.
- No "why suggested" attribution UI (deferred to v1.5).
- No "seen recently" attractor dampener (deferred).
- No dismissed-flag on suggestions or memories (deferred).
- No suggestion caching in the frontend (server cache is
  sufficient).
- No auto-generation triggered by Composition completion
  (deferred; requires an "Episode is done" signal that
  doesn't exist).
- No suggestion surface on Home / Universe root / Episode
  detail / Composition detail (any of those can be added
  later as sibling surfaces sharing the same backend
  endpoint).
- No integration with PRODUCT_IA_V1 §6.1 Next-step nudge
  (that ratified surface lives on Home post-publish; this v1
  is a distinct surface with a shared backend).
- No writing-contract or synthesis-substrate change.
- No changes to the operator's ability to write their own
  Episode topic freely.

---

## §64 Cost + operational implications

Per suggestion generation (measured in Q280.5-1):
- Input tokens: 596 (Fox & Flour) to 1,797 (Patch's Workshop).
  Scales linearly with Episode count + memory count.
- Output tokens: 70-93.
- Provider cost: ~$0.005 to ~$0.02 per call at gpt-5.6-terra
  pricing.

Cached hit → $0.
Passive page load hit → cached if within 10-minute window;
otherwise $0.005-$0.02.
Refresh click → $0.005-$0.02.

Dogfood estimate (Chris using it heavily during a session): 20
suggestion generations per day per operator ≈ $0.10-$0.40/day.
Not a concern at pilot scale.

Cache invalidation trigger points:
- New Episode created in Universe → clear
  `next_ep_sugg:{uni.id}:*`.
- Memory promoted / superseded / archived → clear same
  prefix.
- Nothing else.

No new provider added. No new API keys. OpenAI only, same
`OPENAI_API_KEY` the rest of the system uses.

---

## §65 Alignment with prior product intent

### 65.1 PRODUCT_IA_V1 §6.1 step 6 "Next-step nudge"

Ratified surface at `docs/design/PRODUCT_IA_V1_2026-08-06.md:335`,
verbatim:

> "6. **Next-step nudge.** Below the featured piece, the
> teammate's next suggestion appears (variant, follow-up,
> series). Ask-triggered reveals may fire here."

**Distinction preserved:** §6.1 surface fires **on Home
post-publish** for the operator whose piece just went live. Its
suggestions are shaped for the recently-published piece
(variant, follow-up, series).

This v1 slice is a **sibling surface**: it fires on the
**Universe Episodes list page**, shaped for the *next Episode
premise* the operator might pursue. Same philosophical family
(suggestions, not obligations); different surface, different
scope, different generation input.

If both surfaces ship, they should share the backend service
`suggest_next_episodes` (the Home nudge might filter to a
different subset — e.g., "follow-ups only" — but reuse the
same LLM path). Sharing not required for v1.

### 65.2 SESSION 269 §17.9 candidate-next-Episodes practice

Ratified pattern at
`docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md:2715-2718`.
The design team already inventories "candidate next Episodes
(not instructions)" manually in session docs. This v1 slice
automates that practice at the operator UI level so the same
kind of thinking happens per Universe, per session, without
requiring a session-doc.

The "(not instructions)" parenthetical mirrors INVARIANTS-A/B/C
exactly.

### 65.3 SESSION 269 §18.6 D-10 audience-participation loop

Preserved deferred (§39.3). D-10 is audience-facing (viewer
submissions → operator approves → Episode). This v1 slice is
operator-facing only. Neither surface writes to the other's
substrate. Both remain compatible for v2+.

---

## §66 Preserved: all prior sections

All prior Finding 4i evidence + §37-§55 product-discovery audit
+ Q280.5-1 execution + rubric scoring + predictions unchanged
in substance. No section retracted or renumbered.

The pre-Q280.5-1 authored constraint (§45.5: "Q280.5-1 does
NOT authorize any UI work") is now RELEASED by Chris's Option
A⁵ approval for design-only work. Implementation still requires
a separate authorization.

---

## §67 Decision gate — post-§56 UX design (CURRENT; SUPERSEDES §53)

**STOP here.** Do not implement anything. Do not create the
suggestion service, endpoint, hook, or component. Do not modify
`universes.$id.episodes.tsx`. Wait for Chris + ChatGPT review
of §56-§65.

**Decision needed:**

1. **Accept the §57 flow trace and §58 answers to the UX
   design questions.**

2. **Accept the §59 wireframes as the v1 shape** OR request
   alternates (e.g., different placement, different card
   presentation, chip vs. no chip after selection).

3. **Accept the §61 backend + §62 frontend proposal** as the
   v1 implementation scope.

4. **Choose next slice** (all deferred until approval):

   - **A⁶.** Implement v1 exactly as designed at §61-§62.
     Backend service + endpoint + cache-invalidation signals
     + frontend component + hook + wiring. Test coverage:
     endpoint contract + component render states + one
     integration test on Fox & Flour Universe.
   - **B⁶.** Implement v1 with revisions (Chris + ChatGPT
     supply the revisions).
   - **C⁶.** Add one or more §63 "NOT in v1" items to the v1
     scope before implementation (e.g., "add why-suggested
     subtext in v1 after all").
   - **D⁶.** Prototype v1 in a scratch branch first (design
     mockup only) before merging to main.
   - **E⁶.** Defer implementation and open another discovery
     experiment first (Q280.5-2 latency probe, Q280.5-3 kind
     adoption probe, or return to a Finding 4i option).
   - **F⁶.** Close the product-discovery arc at §55; do NOT
     implement in this SESSION. Push implementation to
     SESSION 281 with a fresh scope-lock.
   - **G⁶.** Something else.

**Do NOT interpret §67 as pre-authorizing any of A⁶-G⁶.**

---

## §68 Closeout — v1 UX design slice (CURRENT; SUPERSEDES §55)

- **Status:** §56 UX design slice complete. §57 SPA + backend
  flow traced. §58 answered all Chris design questions
  concretely. §59 textual wireframes drafted. §60 concrete
  operator walkthrough documented. §61 backend v1 shape
  specified (endpoint + service + cache). §62 frontend v1
  shape specified (component + hook + wiring). §63
  NOT-in-v1 enumerated. §64 cost/operational analysis. §65
  alignment with prior product intent (PRODUCT_IA_V1 §6.1,
  SESSION 269 §17.9, D-10).
- **Substrate:** unchanged. No production code touched. No
  schema, no migration, no memory-kind change, no synthesis-
  substrate change. Design-only artifact in the audit doc.
- **Cumulative SESSION 280 spend:** ~$0.20 unchanged
  (§56-§68 are documentation).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.

---

## §69 v1 IMPLEMENTATION slice — "Where could this story go next?"

Approved from §67 Option A⁶. **Implementation.** Landed as a
single reversible slice. Reuses §61-§62 design shapes with the
adjustments noted below.

### 69.1 Implementation orientation

- Baseline SHA: `b19d030`.
- Working method: ORIENT → smallest code surface → smallest
  change → focused regression coverage → run tests → inspect
  actual operator-visible result. §67 A⁶ authorized implement-
  as-designed; no design revision during implementation.
- Constraint honored throughout: **no implementation
  vocabulary in the operator-facing surface** (§56 HARD UX
  CONSTRAINT). Guarded by an explicit test on both frontend
  and backend.

### 69.2 Exact surfaces changed

**New files:**

- `shell/apps/universe/services/__init__.py` — package init
  re-exporting the service callable + error class.
- `shell/apps/universe/services/next_episode_suggestions.py`
  — service module (~350 lines including docstrings). Lifts
  the Q280.5-1 probe logic into production; Redis-backed
  memoization via Django's default cache alias; empty-
  substrate short-circuit; upstream-error typed exception.
- `shell/apps/universe/tests/test_next_episode_suggestions.py`
  — 16 tests covering service + endpoint contracts.
- `web/src/components/possible-next-episodes.tsx` — component
  (~170 lines). Split into an outer wrapper that gates the
  hook subscription on `enabled` (preserves existing test
  mocks that stub `@/lib/api/universes` without knowing about
  the new hook) and an inner component that owns the query.
- `web/src/components/possible-next-episodes.test.tsx` — 8
  render-state + interaction tests including a vocabulary-
  leak invariant.

**Modified files:**

- `shell/apps/universe/views.py` — added
  `UniverseViewSet.next_episode_suggestions` action
  (`GET /api/universes/:id/next-episode-suggestions/`).
- `web/src/lib/api/universes.ts` — added
  `getNextEpisodeSuggestions` fetch fn and
  `useNextEpisodeSuggestions` react-query hook. Response
  shape validated with zod.
- `web/src/routes/workspace/universes.$id.episodes.tsx` —
  imported and rendered `<PossibleNextEpisodes>` above the
  existing create-form / episode list, gated on
  `activeEpisodeCount >= 1` AND `!creating`. Added
  `suggestionChipVisible` state + `topicRef` for focus
  management. Added `handleUseSuggestion` callback that
  opens the existing create form pre-filled with the
  suggestion text.

**No other files modified.** No new migrations. No schema
change. No memory-kind change. No synthesis-substrate change.
No writing-contract change. No new provider. No changes to
the composition creation flow, the Episode detail page, or
any other route.

### 69.3 Operator flow (as-built)

1. Operator navigates to `/workspace/universes/:id/episodes`.
2. If the Universe has zero non-archived Episodes: nothing new
   appears; the existing empty-state copy renders unchanged.
3. If the Universe has ≥ 1 non-archived Episode: a section
   headed **"Where could this story go next?"** appears
   between the page header and the existing `[New Episode]`
   button. It shows:
   - Header row: title + subtle sparkle glyph + "Different
     ideas" refresh button (label chosen deliberately —
     ordinary language, not "regenerate").
   - Intro line: *"A few ideas from what has happened in this
     story so far. Pick one, ignore them, or write your own
     below."*
   - Three suggestion cards, each showing a one-sentence
     idea + `[Use this]` button. Never padded; if the model
     returns fewer than three, fewer cards render.
4. Loading state: three skeleton cards + *"Looking for
   ideas…"*.
5. Error state: single card *"Couldn't load ideas right now."*
   + `[Try again]` button.
6. Clicking `[Use this]` opens the existing New Episode inline
   form pre-filled with the suggestion text as
   `operator_topic`. Above the form appears a small gold-
   tinted chip: *"Started from an idea. Edit anything freely
   — nothing is saved yet."* + `[×]` dismisses the chip only
   (textarea contents are the operator's to edit or discard).
7. Focus lands in the topic textarea with the caret at the
   end of the pre-fill — operator can immediately edit.
8. Cast field is NOT auto-populated; the operator picks who's
   in the Episode.
9. Existing `[✨ New Episode]` button is preserved as the
   primary CTA; clicking it opens an empty form (unchanged
   behavior).
10. Submitting the form calls the existing
    `POST /api/episodes/` unchanged — the suggestion origin is
    NOT persisted; the resulting Episode is a normal Episode.

### 69.4 UX wording chosen

Every operator-visible string reviewed for the §56 HARD UX
CONSTRAINT. Concrete choices:

| Surface | Chosen wording | Alternatives rejected |
|---|---|---|
| Section heading | *"Where could this story go next?"* | *"Suggested next Episodes"*, *"AI-generated directions"*, *"Story arc suggestions"* (implementation vocabulary) |
| Intro line | *"A few ideas from what has happened in this story so far. Pick one, ignore them, or write your own below."* | Anything mentioning "based on memory retrieval", "generated from your prior Episodes", "AI analysis" |
| Refresh button | *"Different ideas"* + `RefreshCw` icon | *"Regenerate"*, *"Retry"*, *"New batch"*, *"Refresh suggestions"* |
| Loading | *"Looking for ideas…"* | *"Generating…"*, *"Contacting model…"* |
| Error | *"Couldn't load ideas right now."* / *"Try again"* | *"LLM provider unavailable"*, *"Suggestion service error"* |
| Per-card action | *"Use this"* | *"Select"*, *"Choose"*, *"Pick this direction"* |
| Post-select chip | *"Started from an idea. Edit anything freely — nothing is saved yet."* | *"Suggested topic"*, *"Prefilled from AI suggestion"*, *"Model-generated topic"* |

### 69.5 Backend endpoint contract

`GET /api/universes/:id/next-episode-suggestions/`

Query params:
- `n` (int, optional, default 3, silently clamped to
  [1, 5]) — number of suggestions.
- `refresh` (bool, optional, default false) — bypass server
  cache.

Responses:
- `200 OK` — `{"suggestions": [{"text": "..."}, ...],
  "substrate_summary": {...}, "generated_at": "...",
  "model": "...", "cache": {"hit": bool, "ttl_seconds": int},
  ...}`. Empty `suggestions` list is a **valid 200 response**
  when the Universe has zero eligible Episodes; the SPA
  hides the surface without rendering an error.
- `404 Not Found` — Universe not visible to caller (workspace
  non-member OR archived without `?include_archived`). Same
  pattern as the rest of `UniverseViewSet`.
- `502 Bad Gateway` — LLM provider unavailable / returned
  unusable output. Body:
  `{"error": "suggestion_provider_unavailable",
    "detail": "Couldn't generate suggestions right now. Try again shortly."}`
  Operator-facing detail avoids implementation vocabulary.

Cache: Redis-backed via Django's default cache alias
(`redis://localhost:6381/2`; already provisioned for
embedding cache). TTL = 600 s. Key includes Universe id +
latest Episode `created_at` + latest memory `created_at` +
`n`. New Episode creation or memory promotion changes
`latest_*_at` and naturally invalidates.

### 69.6 Tests

**Backend** — `apps/universe/tests/test_next_episode_suggestions.py`,
16 tests, all pass in 5.5 s:

- Service: empty Universe short-circuit (no LLM call);
  populated Universe generates suggestions; cache hit on
  second call; refresh bypasses cache; upstream error raises;
  never pads below N when the LLM returns fewer; drops empty
  strings from the LLM.
- Endpoint: 200 with empty list on empty Universe; 200 with
  suggestions on populated; refresh query param bypasses
  cache; upstream error → 502; non-member → 404; archived →
  404; `n` query param respected; `n` out-of-range or
  non-integer silently falls back; operator-facing error
  detail never leaks implementation vocabulary (guarded
  against a banned-word list).

Wider `apps/universe/tests/` regression: **115 tests, all
pass** (5.5 s → 20.8 s total).

**Frontend** —
`web/src/components/possible-next-episodes.test.tsx`, 8 tests,
all pass in ~90 ms:

- Enabled=false → renders nothing.
- Empty server response → renders nothing (no teaser).
- Loading state renders skeleton + "Looking for ideas…".
- Three suggestions render + heading + intro + refresh.
- `[Use this]` click passes suggestion text verbatim to
  parent handler.
- Refresh click calls `refetch()`.
- Error state renders with `[Try again]`.
- Rendered strings never leak implementation vocabulary
  (banned-word check).

Wider regression: **5 test files, 42 tests, all pass** across
`possible-next-episodes.test.tsx`, `episode-cast-picker.test.tsx`
(the file that broke before the refactor), `episode-composition-workflow.test.tsx`,
`universes.brief.test.tsx`, `universes.detail.test.tsx`.

The pre-refactor regression was caused by the component
originally calling `useNextEpisodeSuggestions` on every render.
Existing tests mocked `@/lib/api/universes` with only
`useUniverse`, so the missing hook broke unrelated Universe/
Episode routes. Fix: split the component into an outer
`PossibleNextEpisodes` (gates on `enabled`, early-returns
`null`) and an inner `PossibleNextEpisodesInner` (owns the
hook). Existing test mocks don't need updating — the inner
component only mounts when the outer wrapper sees
`enabled=true`, which requires the parent to have already
loaded `useEpisodes` data showing ≥ 1 Episode.

### 69.7 Runtime evidence — live service + HTTP round trip

Service-layer live call against real DB (no cache, `use_cache=False`):

- **Fox & Flour Bakery** (10 Episodes, 0 memories, 2 cast) —
  ~2 s response, tokens_in=574 out=75:
  1. *"Tyson and Ruby investigate whether the strange item in
     the freezer is connected to the bakery's supposed
     haunting."*
  2. *"A local baking competition sends an official
     invitation, forcing Tyson to find out whether Ruby
     entered them after all."*
  3. *"Ruby's mascot idea gains unexpected momentum when a
     neighborhood kid leaves a fox-themed design at the
     counter."*
- **Patch's Workshop** (32 Episodes, 14 memories, 2 cast) —
  ~5 s response, tokens_in=1660 out=96:
  1. *"The button Patch was told not to press turns out to
     trigger a workshop-wide safety drill, and the Agent
     immediately starts grading everyone's response."*
  2. *"Rivet finally tells Patch about the hidden PATCH
     OVERRIDES folder, forcing them to decide whether the
     Agent has been keeping notes or building a case."*
  3. *"Patch's new mascot begins receiving messages from the
     workshop helper, and Rivet suspects the two creations
     are developing a private project."*
- Cache miss → hit confirmed on a second identical call.

HTTP round-trip via APIClient force-authenticated as
`chris@donkeybetz.com` (owner of the workspace):

- Fox & Flour Bakery: 200 OK, 3 suggestions rendered (as
  above, second sample; distinct wording from the direct
  service call because the LLM is stochastic — same substrate
  produces qualitatively similar but not identical output).
- Patch's Workshop: 200 OK, 3 suggestions rendered.
- Empty Universe (newly created for the test, immediately
  deleted): 200 OK, `suggestions=[]` — the SPA
  short-circuit path.

All three responses match §61.1 shape verbatim.
`substrate_summary` and `cache.hit` present in the payload
as intended (available for future observability without
being operator-facing).

**Observation — Semantic-2-adjacent behavior:** In the second
HTTP-round-trip sample, Patch's Workshop suggestion #1 was
*"Rivet discovers that the workshop agent has begun assigning
confidence scores to Patch's ideas, including one Patch has
not told anyone yet."* This is a **surprising** direction:
the LLM is inventing an epistemic asymmetry (Rivet learning
of an idea Patch has not disclosed) that is not explicitly
in the memory pool. It's compatible with the Patch/Rivet arc
and the workshop-agent memory cluster, but reads as the LLM
noticing possibilities beyond mere Episode-title callback.
Consistent with §40.2 provisional interpretation of "the
storyteller telling us what is missing."

### 69.8 What implementation exposed that the design missed

Two small revisions vs §61-§62 as originally specified:

1. **Component wrapper split** (§69.6). Not in the original
   §62.1 spec; discovered when the initial single-component
   implementation broke unrelated test mocks. Cheap fix,
   preserves hooks-rule contract, keeps the design intact
   from the operator's perspective.
2. **`!creating` gate on the suggestions section**
   (`universes.$id.episodes.tsx` render condition). Not
   explicitly stated in §59.4 wireframe D but implied by the
   flow — once the operator is inside the create form, the
   suggestions should not compete for attention. As-built:
   suggestions section hides during creating; unhides on
   cancel/submit.

Everything else landed exactly as designed. The Q280.5-1
finding that Episode history alone suffices held true —
Fox & Flour with 0 memories produced strong suggestions in
the live runtime evidence.

### 69.9 Remaining gaps + observations

**Not in v1 (as documented at §63) and NOT changed here:**

- No "why suggested" attribution UI.
- No "seen recently" attractor dampener (Fox & Flour did
  produce a freezer+haunting connection at slot 1 in both the
  service call AND the HTTP round-trip; matches §51.1 HIGH
  REPEATER RATE observation).
- No dismissed-flag on suggestions or memories.
- No auto-generation on Composition completion.
- No suggestion surfaces on Home / Universe root / Episode
  detail / Composition detail.
- No PROMISE / DIALOGUE_CALLBACK adoption UX refresh (kinds
  still under-used; §48.1 observation holds).

**Discovered gap (not blocking v1):** the response payload
includes `substrate_summary`, `generated_at`, `model`, and
`cache.*` fields. These are useful for backend debugging /
observability but not surfaced in the SPA today. A v1.5
"admin sees what happened" widget could render them for
Chris during dogfood without leaking into the operator UI.

**Cost estimate for dogfood:** ~$0.005-$0.02 per generation
(Q280.5-1 measured, live-runtime evidence confirms). With
10-minute server cache, passive page loads within the same
window are free. Predicted dogfood spend at
20 generations/day/operator: $0.10-$0.40/day.

### 69.10 Landing commit

- Backend: service module + endpoint + tests.
- Frontend: hook + component + wiring + tests.
- Doc: this section (§69).
- Test totals: **115 backend tests pass** in
  `apps/universe/tests/`; **42 frontend tests pass** across
  the 5 affected files. No regressions.
- Substrate: unchanged. No migrations. No schema.
- Deferrals from §63 remain deferred.
- Feature is fully reversible: revert the commit + clear the
  Redis `next_ep_sugg:*` cache and every trace of the
  feature disappears without data loss.

---

## §70 Decision gate — post-implementation dogfood handoff (CURRENT; SUPERSEDES §67)

**STOP here.** Hand the feature back to Chris + ChatGPT for
operator dogfood before expanding.

**Dogfood observation targets:**

- Does the section feel discoverable in the natural flow —
  operator returning to the Universe Episodes list?
- Are the actual suggestions on Fox & Flour + Patch's
  Workshop useful, ignorable, or noise?
- Does `[Use this]` → pre-filled form → chip feel right, or
  intrusive?
- Does the operator ever hit `[Different ideas]`?
- Is the empty-Universe silent-hide correct, or should there
  be a nudge to build story first?
- Does the loading state feel too long?
- Any language in the surface that reads as too technical or
  too cute?

**After dogfood, next slice options (deferred):**

- **A⁷.** No changes — v1 is enough. Close the arc.
- **B⁷.** v1.5 tweaks based on dogfood friction (e.g.,
  attractor dampening if repeat suggestions annoy).
- **C⁷.** Add the §63 "NOT in v1" items that dogfood
  proves needed.
- **D⁷.** Add a sibling surface (PRODUCT_IA_V1 §6.1 Home
  Next-step nudge; or Episode detail page; or Composition
  detail page).
- **E⁷.** Address the discovered `substrate_summary` /
  `cache` fields → build an "admin sees what happened" v1.5
  widget for Chris's own observability.
- **F⁷.** Address the discovered "HIGH REPEATER RATE" via
  the deferred attractor-dampener from §58.11.
- **G⁷.** Return to outstanding Finding 4i options
  (Q280.4i-3, Q280.4i-5) or PROMISE / DIALOGUE_CALLBACK
  adoption work (§46 C⁴).
- **H⁷.** Something else.

**Do NOT interpret §70 as pre-authorizing any of A⁷-H⁷.**

---

## §71 Closeout — v1 implementation slice (CURRENT; SUPERSEDES §68)

- **Status:** v1 implementation LANDED per §67 A⁶ approval.
  Backend service + endpoint + tests. Frontend component +
  hook + wiring + tests. No substrate mutation. No new
  migrations. Fully reversible.
- **Test totals:** 115 backend tests + 42 frontend tests
  across affected surfaces, all passing.
- **Runtime evidence:** live service call + HTTP round-trip
  on Fox & Flour Bakery + Patch's Workshop + empty Universe
  all pass. Suggestions demonstrably pick up prior Episodes
  and (for Patch's Workshop) memory rows. One suggestion
  produced surprising Semantic-2-adjacent content in the live
  run (§69.7) — the LLM invented a plausible epistemic
  asymmetry not explicitly in the substrate.
- **Cost:** ~$0.005-$0.02 per LLM call at v1 pricing.
  Cumulative SESSION 280 spend estimate: ~$0.20 unchanged
  from prior sections (this slice ran the Q280.5-1-shape
  probes but through the production service — so cost is
  effectively the ~$0.10 already tracked).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.

---

## §72 Q280.6 — first operator-steered story loop AUDIT

**AUDIT / ORIENT only.** No production change. No verifier fix.
No next experiment. Preserves all prior evidence unchanged.

Triggered by Chris's first real operator dogfood of the v1
"Where could this story go next?" surface (SHA `25b3168`).

### 72.1 Dogfood trace (preserved verbatim from Chris's report)

- Universe: **Fox & Flour Bakery**.
- Suggestion offered (pre-Episode): *"After getting locked out,
  Ruby proposes a foolproof closing routine, only for the new
  bakery mascot idea to complicate it."*
- Chris clicked `[Use this]`, edited nothing, submitted.
- Resulting Episode: `eb47350e-b1cf-4347-aa4f-5bf514d66d2e`.
- Resulting Composition: **`772e9012-4d26-4f93-a50c-158b4e8a42f1`**.
- Post-Episode suggestions (three, verbatim):
  1. *"Tyson investigates whether the strange freezer
     discovery is connected to the bakery's supposed haunting,
     while Ruby insists their mascot is the more likely
     culprit."*
  2. *"A surprise visit from baking-competition organizers
     forces Ruby and Tyson to figure out whether anyone
     actually entered Fox & Flour — or whether the entry was a
     prank."*
  3. *"Ruby's new closing routine goes spectacularly wrong when
     the mascot gets locked inside with the next morning's
     sourdough starter."*

The realized scene invented rich narrative detail — *"mascot
clause"*, *"community outreach"*, *"tiny bell"*, *"final
walk-through together"* — none of which is present in the
Episode topic.

### 72.2 The forensic question

Do we have evidence for:

- **A. FULL STORY LOOP** — realized scene output materially
  feeds future suggestion generation, OR
- **B. TOPIC-LEVEL STORY LOOP** — only the Episode
  topic/title becomes future context; realized dialogue does
  not, OR
- **C. MIXED**, OR
- **D. Something else**.

### 72.3 Runtime evidence assembled

Raw evidence persisted at
`docs/design/session280_experiment_data/q280_6_loop_trace_evidence.json`.

**Composition `772e9012` — DB state (verified 2026-08-24):**

| Field | Value |
|---|---|
| `id` | `772e9012-4d26-4f93-a50c-158b4e8a42f1` |
| `template_kind` | `dialogue_scene` |
| `status` | `completed` |
| `verification_status` | `verified` |
| `episode_id` | `eb47350e-b1cf-4347-aa4f-5bf514d66d2e` |
| `memory_ids` | `[]` — zero memories fed the render |
| `knowledge_chunk_ids` | 5 IDs: 2 shared Universe canon (Fox & Flour Hours; holiday policy) + 3 Tyson pastry-pairing character K2 chunks |
| `verification_warnings` (D-POS, authoritative) | 2 entries: `bakery mascot` (Tyson t5) + `Mascot` (Ruby t10) |
| `verification_warnings_legacy` (K6.4, shadow) | 5 entries: 4 Q-278-1 sentence-initial noise + `Mascot` |
| `created_at` | 2026-08-24 21:55:15 UTC |
| `synthesized_brief` | Full dialogue containing the "mascot clause / community outreach" invention (11 turns, 1,335 chars) |

**Episode `eb47350e` — DB state:**

- `title`: *"After getting locked out, Ruby proposes a foolproof closing …"* (auto-derived from operator_topic, truncated for display)
- `operator_topic` (verbatim, single source of truth for the
  story premise):
  > *"After getting locked out, Ruby proposes a foolproof
  > closing routine, only for the new bakery mascot idea to
  > complicate it."*
- `cast`: `[Tyson, Ruby]`
- `created_at`: 2026-08-24 21:54:32 UTC (~43s before the
  Composition — suggestion → form → submit → synthesize)

**Fox & Flour substrate at time of the post-Episode suggestion
refresh:**

- 11 Episodes total (including the new `eb47350e`).
- **0 REMEMBERED NarrativeMemory rows.** No memory was
  promoted from `772e9012` (or from any prior Composition).
- 2 cast (Ruby, Tyson).
- Universe.brief: 331 chars.

**Retrieved knowledge chunks — verified content:**

All 5 chunks confirmed unrelated to "mascot", "lock", or
"closing routine":

- `3bfea692` (Universe scope): *"Fox & Flour Bakery is open
  daily from 7:00 AM to 3:00 PM."*
- `219bcc30` (Universe scope): *"Fox & Flour is closed on
  Christmas Day."* (only "close" hit — irrelevant to closing
  routine)
- `a02de62d` / `2548f826` / `a99dba2d` (Character scope,
  Tyson): SESSION 279 §27 pastry-pairing corpus (chocolate
  babka / roast profile / coffee prep).

**No K2 chunk mentions "mascot" at all.**

### 72.4 The suggestion service task message — verbatim

The suggestion generator constructs its LLM input from
`_snapshot()` + `_build_task_message()` in
`shell/apps/universe/services/next_episode_suggestions.py`.
For Fox & Flour at the post-Episode refresh moment, the task
message is (excerpts, full file persisted at
`docs/design/session280_experiment_data/q280_6_loop_trace_evidence.json`):

```
UNIVERSE: Fox & Flour Bakery

WORLD BRIEF:
Fox & Flour Bakery is a warm neighborhood artisan bakery
built around small-batch baking, naturally leavened sourdough,
handcrafted pastries, seasonal desserts, and celebration cakes.
It aims to feel like a familiar neighborhood gathering place
where careful craft and quality ingredients matter more than
speed or mass production.

CAST:
- Tyson: tone=expert; personality='Easygoing, practical, and
  a little dry. …'
- Ruby: tone=friend; personality='Warm, cheerful, and
  genuinely caring. Ruby loves helping people find …'

EPISODES SO FAR (earliest first):
  1. 'Why our sourdough takes its time'
  2. 'Our celebration cakes'
  3. 'Welcome to Fox & Flour Bakery'
  4. 'Ruby and Tyson deal with a difficult bakery customer.'
  5. 'Ruby thinks the bakery needs a mascot.'
  6. 'Tyson is convinced the bakery is haunted.'
  7. 'Ruby thinks Tyson is taking coffee too seriously.'
  8. 'Ruby finds something strange in the bakery freezer.'
  9. 'Tyson thinks Ruby secretly entered them in a baking competition.'
 10. 'Ruby locks herself out of the bakery.'
 11. 'After getting locked out, Ruby proposes a foolproof closing …'
     topic: After getting locked out, Ruby proposes a foolproof closing
       routine, only for the new bakery mascot idea to complicate it.

PAST EVENTS: (none recorded yet)
```

**Substring probes on the exact task message (evidence JSON
`contains_*_in_task_message` fields, all `False`):**

- `"mascot clause"` — **not present**
- `"community outreach"` — **not present**
- `"tiny bell"` — **not present**
- `"final walk-through"` — **not present**
- Any snippet of `Composition.synthesized_brief` — **not
  present**

The realized scene's inventive details **do not enter the
suggestion prompt.** The Episode topic does — verbatim.

### 72.5 Boundary-by-boundary trace

Following the loop from history → generation → selection →
synthesis → completion → refreshed generation, boundary by
boundary.

**Boundary 1 — history → suggestion generation.**

Source: `apps/universe/services/next_episode_suggestions.py::_snapshot`.

READS (per code trace, lines 88-176):
- `Universe.brief`.
- All non-archived `Episode.{id, title, operator_topic, created_at}`
  ordered by `created_at`.
- All REMEMBERED `NarrativeMemory.{id, kind, weight, witnessed_by, body, created_at}`
  where `archived_at IS NULL`.
- `NarrativeMemory` reference counts derived by scanning
  `Composition.memory_ids` for the workspace.
- Cast `Teammate.{id, name, tone_archetype, personality[:220]}`.

DOES NOT READ:
- `Composition.synthesized_brief` — the actual dialogue text.
- `Composition.verification_warnings` — verifier flags.
- `Composition.knowledge_chunk_ids` — K2 retrieval history.
- `KnowledgeChunk.chunk_text` — retrieved facts fed to
  prior renders.
- Any per-turn `DialogueTurn` rows.
- Any prior Composition's cost / timing / model metadata.

**Boundary 2 — operator selects `[Use this]`.**

Source: `web/src/routes/workspace/universes.$id.episodes.tsx::handleUseSuggestion`.

TRANSFERS: **the suggestion text string, verbatim, into
`operatorTopic` state.**

DOES NOT TRANSFER:
- Any suggestion ID.
- Any provenance metadata about which prior Episodes or memories
  fed the suggestion.
- Any hidden fields.

SIDE EFFECTS at selection:
- Sets `creating=true` (opens the create form).
- Sets `title=""` (will derive on submit).
- Sets `selectedCastIds=Set()` (operator picks).
- Sets `suggestionChipVisible=true` (UI-only, ephemeral state).
- Focuses the topic textarea at end-of-prefill.

**No DB write occurs at selection.** No suggestion row exists
anywhere. No Episode is created merely by selecting. The
suggestion is a pre-fill; the form is fully editable until
submit.

**Boundary 3 — operator submits the create form.**

Source: same file, `handleCreate`.

Wire payload: `POST /api/episodes/` with
`{universe, title (auto-derived if blank), operator_topic
(verbatim state = the suggestion text), cast_ids?}`.

Server creates Episode `eb47350e` with
`operator_topic = "After getting locked out, Ruby proposes a
foolproof closing routine, only for the new bakery mascot
idea to complicate it."` — byte-identical to the suggestion.

**This is the ONLY point in the loop where the suggestion
becomes durable.** It becomes `Episode.operator_topic` and
`Episode.title`. Nothing about the suggestion's origin is
persisted separately.

**Boundary 4 — Composition synthesis.**

Source: `shell/character_os/dialogue_synthesis.py::synthesize_dialogue`.

The synthesis LLM was called with:
- `topic = Episode.operator_topic` (verbatim = the suggestion
  text).
- `cast = [Tyson, Ruby]`.
- `use_knowledge = True`, so retrieval ran:
  - Per-character K2 (5 chunks, all pastry/canon).
  - Universe canon (2 chunks: hours + holiday policy).
  - Universe memory (0 rows — F&F has none).
- No `opener` was pinned.

Prompt substrate the writer received (per §4.4 trace):
- Cast identity (personality + POV + voice enums + business_brief).
- SHARED WORLD KNOWLEDGE: 2 canon chunks (hours, holiday).
- EPISODE / NARRATIVE MEMORY: empty.
- Per-alias SCOPED KNOWLEDGE: 3 Tyson pastry chunks +
  0 for Ruby beyond canon.
- Writing contract (invariants, watchability, anti-patterns,
  narrative-shapes menu).
- User message = `topic` (verbatim).

The writer did NOT receive:
- Any prior Episode's title or topic.
- Any prior Composition's dialogue.
- Any suggestion provenance.

The realized dialogue's *"mascot clause / community outreach /
tiny bell / final walk-through"* details are **all writer
inventions**, generated from the topic clause *"the new bakery
mascot idea to complicate it"* + the writer's narrative
reasoning. No retrieved chunk, no memory, no prior Episode
title in the prompt authorizes those specifics.

**Boundary 5 — Composition persistence.**

Persisted fields (all verified in the evidence JSON):

- `synthesized_brief`: full dialogue (contains "mascot clause"
  etc.). Text-only. Not fed forward.
- `knowledge_chunk_ids`: 5 K2 IDs. Read by
  `MemoriesUsedSummary` on the Composition detail SPA, but not
  by the suggestion service.
- `memory_ids`: `[]`.
- `verification_warnings`: 2 D-POS entries (see §72.7).
- `episode_id`: `eb47350e` (attach FK).
- `template_kind`, `status`, `created_at`.

**No cross-scene state ledger updates. No "story so far"
summary appended anywhere. No memory row auto-promoted.** The
operator would need to explicitly promote memories from the
Composition detail page for the realized scene to enter the
memory pool — Chris did not do this (F&F still has 0
memories).

**Boundary 6 — refreshed suggestion generation.**

Same `_snapshot()` / `_build_task_message()` code path as
Boundary 1. The **only substrate delta** vs. the pre-Episode
call is:

- +1 Episode entry: `eb47350e` with the operator_topic verbatim
  as shown at §72.4.
- `latest_episode_at` rolls forward — invalidates the cache
  key so a fresh LLM call fires (verified: `cache.hit=False`
  in evidence).

All other inputs (Universe.brief, cast, memory pool = 0,
prior 10 Episode titles) are identical.

### 72.6 Provenance trace for each post-Episode suggestion

For each of the three suggestions Chris saw, I trace the
substrate elements that could plausibly have produced it —
distinguishing (a) prior Episode title/topic, (b) memory
row, (c) the new Episode #11 operator_topic, (d) LLM
inference / narrative synthesis, (e) realized dialogue in
772e9012 (the last is ALWAYS empty at this boundary; kept
for symmetry).

**Suggestion #1** — *"Tyson investigates whether the strange
freezer discovery is connected to the bakery's supposed
haunting, while Ruby insists their mascot is the more likely
culprit."*

| Element | Source |
|---|---|
| *"strange freezer discovery"* | Episode #8 title: *"Ruby finds something strange in the bakery freezer."* |
| *"bakery's supposed haunting"* | Episode #6 title: *"Tyson is convinced the bakery is haunted."* |
| *"their mascot"* | Episode #5 title (*"Ruby thinks the bakery needs a mascot."*) + Episode #11 operator_topic ("the new bakery mascot idea") — mascot is now more salient because it's in two episode inputs |
| *"the more likely culprit"* | **LLM invention.** No source in prior substrate calls the mascot a culprit for anything. |
| *"Ruby insists"* | Character voice inference from Ruby's tone (friend/warm/cheerful) |
| Realized dialogue in 772e9012 | Not in prompt |

Novel narrative connection created by the LLM: mascot-as-
suspect for the haunting. This is a plausible reading of the
Episode #11 topic (*"complicate it"*) generalized into other
adjacent threads.

**Suggestion #2** — *"A surprise visit from
baking-competition organizers forces Ruby and Tyson to figure
out whether anyone actually entered Fox & Flour — or whether
the entry was a prank."*

| Element | Source |
|---|---|
| *"baking-competition organizers"* | Episode #9 title: *"Tyson thinks Ruby secretly entered them in a baking competition."* |
| *"figure out whether anyone actually entered"* | Direct callback to the unresolved question in Episode #9 |
| *"whether the entry was a prank"* | LLM narrative embroidery |
| Episode #11 / 772e9012 | **Not referenced.** This suggestion is an independent-thread resurfacing. |

Control-comparison confirms the suggestion generator does
resurface unresolved threads even when they're unrelated to
the most recent Episode.

**Suggestion #3** — *"Ruby's new closing routine goes
spectacularly wrong when the mascot gets locked inside with
the next morning's sourdough starter."* (**the critical
specimen**)

| Element | Source |
|---|---|
| *"Ruby's new closing routine"* | Episode #11 operator_topic verbatim |
| *"mascot"* | Episode #11 operator_topic + Episode #5 title |
| *"locked inside"* | Episode #10 title (*"Ruby locks herself out of the bakery."*) semantically inverted (locked-in vs. locked-out) |
| *"next morning's sourdough starter"* | Universe.brief ("naturally leavened sourdough") + generic bakery-morning inference |
| *"spectacularly wrong"* | LLM narrative embroidery |
| *"mascot clause / community outreach / tiny bell / final walk-through"* — the realized scene's inventive details | **Not present in the suggestion.** None of these appear. |
| Realized dialogue in 772e9012 | **Not in prompt.** |

**Critical answer to Q280.6 §5:** Suggestion #3 is fully
derivable from the Episode #11 topic ("closing routine…
mascot idea complicates") + Episode #10 title ("Ruby locks
herself out") + a natural narrative inversion the LLM
performs. It does NOT require the realized dialogue's
specifics — and empirically the realized dialogue's specifics
are absent from both the prompt and the produced suggestion.

The "mascot gets locked inside" idea is the LLM combining:
- "mascot" (from topic)
- "locked" concept (from title of Episode #10 + implicit
  inversion of the topic's "getting locked out")
- Sourdough morning (from Universe brief)

None of that requires seeing the "mascot clause" that the
realized scene actually invented.

### 72.7 Claim verifier finding (secondary — DO NOT FIX)

`Composition.verification_warnings` (D-POS authoritative) on
772e9012:

| # | Kind | Claim | Turn | Speaker | Semantic source |
|---|---|---|---|---|---|
| 1 | `multi_word_pos` | `bakery mascot` | T5 (Tyson) | Tyson | Directly authorized by `Episode.operator_topic` ("the new bakery mascot idea") |
| 2 | `proper_noun_pos` | `Mascot` | T10 (Ruby) | Ruby | Same — capitalized reference to the operator-authored premise |

Legacy K6.4 shadow flagged 4 additional Q-278-1 sentence-
initial words (`After`, `Strong`, `Before`, `Slightly`) —
already understood class per SESSION 278 §Q-278-4.

**The verifier boundary Q280.6 exposes:**

`build_allowed_vocabulary`
(`shell/character_os/claim_verifier.py:741-803`) constructs
its allowed-entity list from:

- `Teammate.name`
- `personality`, `character_point_of_view`, `voice_signature_phrases`
  proper-noun extraction
- `KNOWN_PLATFORM_TERMS`
- Caller-provided extras (typically workspace name)

**It does NOT include `Episode.operator_topic` content.**

So a claim like "bakery mascot" — semantically authorized by
the operator's own topic ("the new bakery mascot idea") —
is treated as unsupported because no retrieved knowledge /
memory / cast-metadata carries the phrase.

**Class of finding:** operator-supplied premise material is
verifier-invisible. Same class as SESSION 278 §4f
(cross-cast alias grounding — the verifier didn't know about
`alias_to_teammate`), differing on the source (Episode topic
here vs. cast map there).

**Not-fixed by construction of this audit.** Recorded as a
side finding for a future scope-locked slice — the primary
Q280.6 answer is not blocked by it.

### 72.8 Product / UX observation (preserved from Chris)

Chris selected the mascot suggestion because he genuinely
wanted to know how the mascot could possibly complicate closing
the bakery. **The suggestion created operator curiosity
rather than merely satisfying a testing requirement.** The
resulting scene then supplied a coherent answer.

The post-Episode suggestions were interesting enough to Chris
that they read as "the storyteller noticing consequences from
prior history" — even though (per §72.5-§72.6) the mechanism
is topic-level composition, not full-scene continuity.

This qualitative observation supports the product hypothesis
that Model D-shape suggestion surfaces are valuable to
operators even when they are topic-level. It does NOT prove
architecture.

### 72.9 Classification — evidence-driven

The loop is **B — TOPIC-LEVEL STORY LOOP.**

Specifically:

- The Episode `operator_topic` (a string authored by the
  operator, or lifted verbatim from a prior suggestion) is
  the ONLY unit that crosses forward into subsequent
  suggestion generation.
- The realized Composition's dialogue, verifier warnings,
  retrieved knowledge chunks, and every scene-invented detail
  do NOT feed the next suggestion cycle.
- Post-Episode suggestion #3 ("mascot gets locked inside")
  is derivable from the topic alone; the realized dialogue's
  "mascot clause" invention is neither necessary nor present
  in the suggestion-generation substrate.
- The one exception that WOULD upgrade this to (C) MIXED —
  operator-promoted NarrativeMemory rows re-entering the
  substrate — did not fire here because Chris did not promote
  any memory from 772e9012 (`F&F REMEMBERED memory count = 0`
  verified). Under the current substrate, memory promotion
  is the sole operator-visible route by which realized scene
  content can influence future suggestions.

We do NOT classify as (A) FULL LOOP: the realized scene
content demonstrably fails to reach the next suggestion
prompt.

We do NOT classify as (C) MIXED without evidence: even the
theoretically-possible mixed case (via memory promotion)
requires an explicit operator action that did not occur in
this dogfood.

We do NOT classify as (D) SOMETHING ELSE: the trace is
consistent with topic-level composition throughout.

### 72.10 What the audit DOES and DOES NOT overclaim

**Established (evidence-backed):**

- Suggestion generation reads from a bounded snapshot that
  excludes `Composition.synthesized_brief` and every other
  realized-scene surface. Code path + substring probes on the
  live task message both confirm.
- The suggestion → Episode → synthesis → completion path
  transports the suggestion text verbatim into
  `Episode.operator_topic`, then verbatim into the synthesis
  `topic` argument. No hidden provenance flows anywhere.
- Post-Episode suggestions differ from pre-Episode
  suggestions only because Episode #11 (topic verbatim) has
  been added to the ordered Episode list.

**Not established (bounded):**

- Whether the LLM would produce QUALITATIVELY different
  suggestions if it were given the realized dialogue vs. the
  topic alone. Q280.6 measures only the current path.
- Whether operators typically promote memories after a
  Composition — Chris did not this time, but a v1 UX for
  memory promotion is out of scope of this audit.
- Whether repeated refreshes of the suggestion set would
  ever surface phrases from the realized dialogue by
  coincidence (would take n=many trials to establish; the
  substrate absence makes the base-rate probability
  effectively zero, but this is not falsifiable evidence).

**Not touched:**

- No production behavior changed.
- No verifier fix. The "bakery mascot" / "Mascot" flags
  remain as observed.
- No new experiment executed.
- No memory promoted. F&F NarrativeMemory pool remains at 0.

### 72.11 Smallest next falsifiable question

Given B — TOPIC-LEVEL LOOP — the natural next falsifiable
question is:

> **Can a detail invented only inside the realized dialogue —
> not present in the Episode topic — influence later
> suggestions if the operator explicitly promotes it to
> memory?**

This has two variants:

- **Q280.7-a (memory-promotion path).** Operator promotes a
  NarrativeMemory from `772e9012` whose body captures a
  scene-invented detail (e.g., *"Ruby and Tyson added a
  'mascot clause' to the closing routine: no one locks up
  until the door is checked, people are accounted for, and
  the mascot is not still inside doing community outreach."*).
  Refresh suggestions. Ask: does the mascot-clause language
  appear in any subsequent suggestion; does a suggestion
  reference the *"mascot"* thread with content beyond what
  the Episode topic would license?
  - Small (~$0.02 provider spend for the refresh).
  - No substrate change; operator does the promotion via the
    existing SPA NarrativeMemoryPromotePanel.
  - Tests whether promoted-memory content is a live channel
    from realized dialogue back into suggestion generation.
  - Prediction (to be locked BEFORE execution): promoted
    scene detail DOES surface in ≥ 1 of the next 3 refresh
    sets. Reason: memory body IS a substrate the suggestion
    service reads (§72.5 Boundary 1); the language of the
    promoted memory is verbatim in the prompt.

- **Q280.7-b (no-promotion control).** Refresh suggestions
  n=3 without promoting any memory. Confirm 0 / 9 mentions of
  the realized-dialogue-only phrases. Cheap negative-control
  companion to Q280.7-a.
  - Even smaller (~$0.05).
  - Confirms the §72.4 substring-absence finding at n>1.

Together Q280.7-a + Q280.7-b would establish:

- **If memory promotion is the necessary+sufficient bridge**
  from realized scene to future suggestions, the loop is
  actually (C) MIXED with a well-defined operator-agency
  toggle.
- **If memory promotion does not bridge either**, the loop is
  strictly (B) TOPIC-LEVEL and any future FULL LOOP would
  require substrate change (e.g., have the suggestion service
  also read a short excerpt of each Composition's
  synthesized_brief for prior Episodes in the Universe).

### 72.12 Decision gate — post-§72 (CURRENT; SUPERSEDES §70)

**STOP here.** Do not execute Q280.7-a or Q280.7-b. Do not
fix the verifier boundary. Do not modify the suggestion
service to include synthesized_brief. Do not add memory-
promotion UX. Do not run any expansion of the v1 surface.

**Decision needed:**

1. **Accept the §72 classification: (B) TOPIC-LEVEL STORY
   LOOP.**

2. **Choose next slice** (all deferred until approval):

   - **A⁸.** Q280.7-a + Q280.7-b (memory-promotion bridge
     probe + no-promotion control). ~$0.07 total. Small.
     Directly settles whether the current substrate supports
     any form of realized-scene → future-suggestion flow
     via operator agency.
   - **B⁸.** Design slice for extending the suggestion
     service to read a short excerpt of prior
     `synthesized_brief` per Episode (would elevate to a
     genuine full-loop architecture). Design-only, no
     implementation.
   - **C⁸.** Address the §72.7 verifier boundary — add
     `Episode.operator_topic` content to
     `build_allowed_vocabulary` when the K6.4 dispatch is
     called from a dialogue-scene context. Scope-locked
     small slice; would clean up the "bakery mascot" false
     positive class.
   - **D⁸.** Return to outstanding Finding 4i options
     (Q280.4i-3 mental-state private specimen, Q280.4i-5
     multi-episode) — the story-loop audit is complete;
     Finding 4i options remain the epistemic-asymmetry
     spine.
   - **E⁸.** Close SESSION 280 with the current findings:
     v1 surface shipped, story loop is topic-level,
     Finding 4i evidence + Q280.5-1 + Q280.6 all durable.
     Roll deferred questions into SESSION 281 handoff.
   - **F⁸.** UX / product observation follow-up: given
     Chris's curiosity signal (§72.8), consider whether the
     v1.5 "why suggested" attribution (§58.9 deferred) would
     amplify or dampen operator engagement. Design-only.
   - **G⁸.** Something else.

**Do NOT interpret §72.12 as pre-authorizing any of A⁸-G⁸.**

### 72.13 Artifacts

- `docs/design/session280_experiment_data/q280_6_loop_trace_evidence.json`
  — full forensic evidence blob including:
  - Composition 772e9012 full DB shape
  - Full `synthesized_brief` (11-turn dialogue with "mascot
    clause" invention)
  - Exact suggestion-service task message the LLM would see
    right now for Fox & Flour
  - Substring probes for realized-dialogue phrases in the
    task message (all `False`)
  - Snapshot summary (episode count, memory count, cast, latest
    timestamps)

### 72.14 Closeout — Q280.6 audit slice (CURRENT; SUPERSEDES §71)

- **Status:** Q280.6 forensic audit complete. Loop classified
  as **(B) TOPIC-LEVEL STORY LOOP** based on code trace +
  live substring probes on the actual suggestion-service task
  message.
- **Substrate:** unchanged. No writes. No production behavior
  changed.
- **Cumulative SESSION 280 spend:** ~$0.20 unchanged.
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.
  - Implementation SHA trailer: `d7931b1`.
  - Q280.6 loop-trace audit slice: `b2f1789`.

---

## §73 Q280.7 — dialogue-only-detail bridge probe (DESIGN + PREDICTION LOCK)

Approved from §72.12 Option A⁸.
**Design + prediction lock committed BEFORE any execution.**
This section is deliberately committed alone so git history
proves the rubric + predictions were set pre-run and cannot be
retro-fitted after seeing outputs.

Accepts §72's classification (B — TOPIC-LEVEL STORY LOOP) as
the baseline. Q280.7 asks whether operator-authored memory
promotion provides a working bridge from realized dialogue
back into future suggestion generation — i.e., whether a
human-curated MIXED loop is available on the existing
substrate.

### 73.1 Question

> Can a detail invented only inside a realized dialogue —
> absent from the Episode topic, prior Episode titles, Universe
> brief, K2 chunks, and existing NarrativeMemory — influence
> later Episode-direction suggestions when the operator
> explicitly promotes that detail as a NarrativeMemory?

### 73.2 Candidate detail selection (audited, non-mascot)

Chris explicitly excluded the "mascot clause" fact from
772e9012 because the mascot thread pulls dogfood toward the
deferred visual/composition limitation (Finding 4c). Instead,
picked a small **interpersonal rule** from the dialogue that
is talking-head-friendly and clearly non-visual.

Enumerated candidates from 772e9012's 11-turn dialogue:

| # | Turn | Candidate | In topic? | In prior titles? | In brief? | In K2? | In personality? | Suitable? |
|---|---|---|---|---|---|---|---|---|
| 1 | T2 Ruby | *"Neither person leaves until the other says they have what they need."* | NO | NO | NO | NO | NO | **✓ selected** |
| 2 | T3 Tyson | *"Install a tiny bell that rings whenever somebody reaches for the door without thinking."* | NO | NO | NO | NO | NO | slight prop/visual dimension; passed over |
| 3 | T4 Ruby | *"Every time I take bread seriously"* | NO | NO | NO | NO | **YES** — in Tyson's personality: *"occasionally teases Ruby about taking bread very seriously"* | disqualified — construct-invalid |
| 4 | T2 Ruby | *"Final walk-through together, confirm the door"* | Adjacent to topic *"foolproof closing routine"* — arguably semantically implied | NO | NO | NO | NO | rejected — closing procedure adjacent to topic |
| 5 | T3 Tyson | Tone shift: Tyson's dry humor about *"an evening staring through the glass"* | NO | NO | NO | NO | mostly in personality (*"a little dry"*) | disqualified — voice trait |

**Selected candidate detail:**

> ***"Ruby and Tyson agreed that when they are closing the
> bakery together, neither one leaves until the other says
> they have what they need."***

Construct-validity proof (all four sources checked verbatim
in §73.2 pre-run inventory; §73.7 evidence artifact captures
substring probes):

- **Not in Episode #11 `operator_topic`** — topic reads
  *"After getting locked out, Ruby proposes a foolproof
  closing routine, only for the new bakery mascot idea to
  complicate it."* The topic mentions "closing routine" but
  not the specific mutual-departure clause.
- **Not in any prior Episode title/topic** — verified by
  reading all 11 topics (§72.3, §73.2 dump).
- **Not in `Universe.brief`** — brief is about the bakery
  (small-batch, sourdough, neighborhood). Zero reference to
  employee protocols.
- **Not in any retrieved K2 chunk** — the 5 chunks used by
  772e9012 are hours + holiday + pastry-pairing content
  (verified §72.3).
- **Not in cast personality/POV/business_brief fields** —
  Ruby's is warm/cheerful/loves-bread; Tyson's is
  easygoing/practical/dry. No mutual-departure agreement in
  either.
- **Not in the existing memory pool** — F&F has 0 REMEMBERED
  memories (verified §72.3).
- **Only source: the realized dialogue of 772e9012, T2 Ruby.**

Talking-head-friendliness: the mutual-departure clause is a
verbal agreement between two people. It seeds future
conversational Episodes (exceptions, accountability tests,
apology when the rule is broken, etc.) without requiring
visual staging.

### 73.3 Experimental design

Two phases sharing the SAME everything except memory-pool
state, in this order:

**Q280.7-b (no-promotion control) — runs FIRST:**
- Refresh suggestions n=3 times against Fox & Flour with
  memory pool unchanged (still 0 REMEMBERED memories).
- Each refresh bypasses cache (`refresh=true`).
- Persist raw suggestions + full task message for each call.
- Purpose: establish baseline at n>1 that the mutual-departure
  rule does NOT surface without promotion, and that the
  baseline suggestion distribution is stable (matches §72
  observations).

**Promotion step — between the two phases:**
- Call `apps.memory.views.promote_from_composition` (the exact
  service backing the SPA `NarrativeMemoryPromotePanel`) with:
  - `composition = 772e9012-4d26-4f93-a50c-158b4e8a42f1`
  - `episode = eb47350e-b1cf-4347-aa4f-5bf514d66d2e`
  - `memory_items = [{
      "kind": "event",
      "body": "Ruby and Tyson agreed that when they are
        closing the bakery together, neither one leaves until
        the other says they have what they need.",
      "weight": "peripheral",
      "witnessed_by": [Ruby.id, Tyson.id],
    }]`
  - `promoted_by = chris@donkeybetz.com` (the operator user)
- New memory row will get:
  - `episode = eb47350e`
  - `source_composition = 772e9012`
  - `workspace + universe` denormalized from episode
  - `status = REMEMBERED`
  - `embedding_vector` populated inline post-atomic
- Reversibility: the memory row can be operator-archived via
  the existing `NarrativeMemoryViewSet` DELETE if the
  experiment is judged undesirable to leave in place. Row ID
  recorded in §73.7 evidence artifact after promotion.

**Q280.7-a (memory-promotion path) — runs SECOND:**
- Refresh suggestions n=3 times against Fox & Flour with the
  new memory in the pool.
- Each refresh bypasses cache.
- Persist raw suggestions + full task message for each call.
- Purpose: observe whether the promoted memory's mutual-
  departure content surfaces in subsequent suggestions.

**Environment kept identical between phases:**
- Same suggestion service code path.
- Same LLM model (gpt-5.6-terra).
- Same Universe / cast / Episode list / cache backend.
- Same n=3 refresh count.
- Same Q280.6-timeframe (baseline SHA `48b5ac0` before this
  experiment).

Total cost estimate: ~$0.05-$0.10 (6 LLM calls at Q280.5-1
measured rate).

### 73.4 Scoring rubric (LOCKED — applied unchanged after seeing outputs)

Per suggestion, two independent Y/N axes:

- **REFERENCES-RULE = Y** iff the suggestion textually or
  semantically references the mutual-departure rule OR one
  of its narrative consequences. Concrete examples that
  score Y:
  - Mentions "neither leaves", "leaves first", "leaves alone",
    "wait for" in a context of who exits/departs.
  - Mentions mutual sign-off / accountability at close
    ("signs off", "gives the all-clear", "OKs the other one",
    "waits for their check-in").
  - Mentions one character breaking or bending the rule
    ("Tyson slips out first", "Ruby forgets the check-in",
    "one of them leaves the other behind").
  - Uses the specific phrase "have what they need" or a close
    paraphrase in a mutual-departure context.
- **REFERENCES-RULE = N** iff the suggestion is about the
  closing routine generally, or the mascot, or a different
  thread — WITHOUT the specific mutual-departure clause.
  Concrete examples that score N:
  - "Ruby refines the closing routine" (topic-level; no
    mutual-departure detail).
  - "Ruby and Tyson debate what the mascot should be called"
    (topic-adjacent; no mutual-departure detail).
  - "The closing routine fails when the freezer alarm goes
    off" (procedural; no mutual-departure detail).
- **CONSTRUCT-VALID = Y** iff REFERENCES-RULE = Y and the
  reference is clearly tied to the promoted memory content
  (mutual-departure specifically), not derivable from
  Episode #11's `operator_topic` alone (which contains
  "closing routine" but not the mutual clause).

Set-level acceptance thresholds (all locked pre-run):

- **BRIDGE CONFIRMED (MIXED loop supported)** — post-promotion
  suggestions produce ≥ 2/9 REFERENCES-RULE with
  CONSTRUCT-VALID, AND control produces 0-1/9 REFERENCES-RULE.
- **BRIDGE DISCONFIRMED (still TOPIC-LEVEL only)** — post-
  promotion suggestions produce ≤ 1/9 REFERENCES-RULE.
- **AMBIGUOUS** — mixed outcome; report distribution and
  defer classification.

### 73.5 Predictions (LOCKED — never revised post-hoc)

Author's honest priors before execution:

| Prediction | Statement |
|---|---|
| **P1⁵** | Q280.7-b (no memory) produces 0/9 REFERENCES-RULE. Rationale: the mutual-departure rule is not in any substrate the suggestion service reads today (§72.5 Boundary 1). The LLM has no channel to it. |
| **P2⁵** | Q280.7-a (with memory) produces ≥ 2/9 REFERENCES-RULE with CONSTRUCT-VALID. Rationale: memory body IS in the substrate the service reads (proven Q280.5-1 §49-§52; PATCH OVERRIDES appeared in 3/3 sets when in memory pool). The mutual-departure rule is a compact, narratively suggestive fact — expected to surface at rate similar to PATCH OVERRIDES. |
| **P3⁵** | Q280.7-a produces AT LEAST ONE suggestion that materially changes narrative possibilities (not merely lexical overlap — i.e., proposes a scene premise the topic alone would not license, such as "Tyson breaks the rule" or "the rule is tested by a shared crisis"). |
| **P4⁵** | Q280.7-b BASE RATE for the "closing routine" (topic-level) thread will produce ≥ 1/9 topic-adjacent suggestions per set, but 0 of those will contain the specific mutual-departure clause. This distinguishes topic-adjacency (expected) from rule-specific reference (the actual test). |

**BRIDGE-CONFIRMED disposition fires iff P1⁵ + P2⁵ + P3⁵ all
confirmed.**
**BRIDGE-DISCONFIRMED disposition fires iff P2⁵ disconfirmed
(≤ 1/9 rule references with construct validity).**

### 73.6 What Q280.7 does NOT do

- Does NOT modify the suggestion service code, prompts, or
  retrieval predicate.
- Does NOT modify the K6.4 / D-POS verifier.
- Does NOT modify any character, K2, or existing memory.
- Does NOT change any Episode.
- Does NOT auto-ingest `synthesized_brief` anywhere.
- Does NOT create a StoryArc / NarrativeThread / OpenThread
  model.
- Does NOT test whether the promoted memory affects future
  Compositions (only suggestions).
- Does NOT test multi-episode continuity of the promoted
  memory (only immediate refresh cycle).

The **one substrate change** is the operator-authored memory
promotion, which is (a) the exact operator-facing path we're
testing and (b) reversible via the existing
`NarrativeMemoryViewSet` DELETE.

### 73.7 Chris's product guardrail — preserved

Recorded verbatim from Chris's authorization message:

> Do NOT assume automatic ingestion of realized dialogue is
> desirable even if technically possible. Human selection of
> "this mattered; remember it" may itself be a valuable part
> of Character OS.

If Q280.7-a confirms the bridge, the finding is:
**operator-curated MIXED loop available today, no substrate
change required.** Whether to build automatic ingestion on
top of that is a SEPARATE product question that this
experiment does not resolve.

### 73.8 Evidence artifacts (populated post-run)

- `docs/design/session280_experiment_data/q280_7_b_no_promotion_evidence.json`
  — pre-promotion refresh runs.
- `docs/design/session280_experiment_data/q280_7_a_with_promotion_evidence.json`
  — post-promotion refresh runs.
- Promoted memory row ID recorded in the post-promotion
  artifact + in the §74 execution slice.

### 73.9 Design-lock closeout

- **Status:** Q280.7 design + predictions + scoring rubric
  LOCKED. Committed BEFORE execution.
- **Baseline SHA before execution:** `48b5ac0`.
- **Next commit** appends §74 with execution evidence,
  interpretation, and decision gate. No design/prediction
  revision after seeing outputs.

---

## §74 Q280.7 — execution + scoring + interpretation

Executed per §73 design after commit `c8d4be5` locked the
predictions. Rubric applied unchanged. No design revision
after seeing outputs.

### 74.1 Execution log

Baseline SHA before execution: `c8d4be5`.

- Pre-run inventory: Fox & Flour Bakery REMEMBERED memory
  count = **0** (matches §73.2 construct-validity precondition).
- Cache cleared before each phase.
- **Q280.7-b (control) — n=3 refreshes** ran against
  substrate with 0 memories. All 3 succeeded on first try;
  tokens_in = 619 per call.
- **Promotion step** — `apps.memory.views.promote_from_composition`
  called with the mutual-departure rule as body, kind=`event`,
  weight=`peripheral`, witnessed_by=[Ruby, Tyson]. Landed
  memory row `abac5486-6404-411b-ad42-54c9884b980f`
  (`status=remembered`, `embedding_vector` populated).
  Post-promotion memory count = **1**.
- **Q280.7-a (treatment) — n=3 refreshes** ran against
  substrate with the new memory. All 3 succeeded on first
  try; tokens_in = 679 per call. **Delta from control = +60
  tokens per call**, matching the size of the added memory
  body block in the prompt (verified verbatim below).

Cost: 6 LLM calls × ~$0.008 = ~$0.05.

### 74.2 Memory reached the treatment prompt (verified)

Direct substring check on the treatment task message (raw
artifact at `q280_7_a_with_promotion_evidence.json`,
`phase.snapshot_task_message_at_start`):

- Contains the exact phrase *"neither one leaves until the
  other says they have what they need"*: **TRUE**.
- The `PAST EVENTS` section now reads (verbatim from the
  probe artifact):

```
PAST EVENTS THE STORY HAS RECORDED (operator-promoted; the
durable record of what has happened in this world):
- (kind=event, weight=peripheral, witnesses=Ruby,Tyson): Ruby
  and Tyson agreed that when they are closing the bakery
  together, neither one leaves until the other says they have
  what they need.
```

**The bridge from operator-promoted memory into the LLM's
suggestion prompt is confirmed to work end-to-end.** The
memory body is present in the substrate the suggestion
service reads (per §72.5 Boundary 1), and the token count
confirms it flowed into the actual LLM call.

### 74.3 Raw suggestion sets (verbatim)

**Q280.7-b (control, memory pool = 0)**

Set 1:
1. *"Tyson and Ruby try to identify the strange thing in the freezer before it ruins the morning bake."*
2. *"Ruby's proposed bakery mascot turns up during closing time and makes her foolproof routine anything but foolproof."*
3. *"A baking competition deadline arrives, forcing Tyson to find out whether Ruby really entered Fox & Flour after all."*

Set 2:
1. *"Tyson investigates the strange freezer discovery and becomes convinced it is connected to the bakery's supposed haunting."*
2. *"Ruby's mascot causes chaos during the new closing routine, forcing her and Tyson to decide whether it belongs in the bakery at all."*
3. *"A surprise baking-competition deadline arrives, and Tyson must figure out whether Ruby actually entered them or whether someone else did."*

Set 3:
1. *"Tyson investigates the strange freezer discovery and becomes even more certain the bakery is haunted."*
2. *"Ruby's mascot plan goes sideways when the would-be mascot disrupts a high-stakes celebration-cake pickup."*
3. *"A baking competition representative arrives at Fox & Flour, forcing Ruby and Tyson to figure out who entered them and whether they can actually compete."*

**Q280.7-a (treatment, memory pool = 1 with mutual-departure rule)**

Set 1:
1. *"Ruby's proposed bakery mascot keeps triggering the new closing routine, forcing her and Tyson to decide whether it belongs after hours."*
2. *"Tyson investigates the strange freezer discovery when a batch of dough begins behaving in a way neither of them can explain."*
3. *"A baking competition invitation arrives, and Tyson tries to find out whether Ruby really entered them before they commit to anything."*

Set 2:
1. *"Ruby's proposed bakery mascot turns up after hours and puts the new closing routine to an immediate test."*
2. *"Tyson investigates the strange freezer discovery when a mysterious ingredient begins appearing in that morning's pastries."*
3. *"A baking-competition representative arrives at Fox & Flour, forcing Ruby and Tyson to find out whether either of them really entered."*

Set 3:
1. *"Ruby and Tyson test their new closing routine during a busy evening, only to realize the mascot has been locked somewhere inside."*
2. *"Tyson investigates the strange freezer discovery when a batch of dough begins behaving as though the bakery really is haunted."*
3. *"A baking-competition organizer arrives to confirm the bakery's entry, forcing Ruby and Tyson to decide whether either of them actually submitted it."*

### 74.4 Per-suggestion scoring against locked §73.4 rubric

Applied unchanged. **REFERENCES-RULE = Y** requires a
textual or semantic reference to the mutual-departure rule
or one of its narrative consequences (neither-leaves,
wait-for, mutual sign-off, rule-broken, accountability
check-in). Topic-level references to "closing routine"
alone do NOT qualify. **CONSTRUCT-VALID = Y** requires the
reference to be tied to the promoted memory content, not
derivable from Episode #11's `operator_topic` alone.

**Q280.7-b (control):**

| ID | Suggestion (excerpt) | REFERENCES-RULE | CONSTRUCT-VALID | Note |
|---|---|---|---|---|
| 1.1 | freezer / morning bake | N | – | Freezer thread |
| 1.2 | mascot / closing time / foolproof routine | N | – | Topic-level closing routine + mascot; no mutual-departure clause |
| 1.3 | baking competition deadline | N | – | Competition thread |
| 2.1 | freezer + haunting | N | – | Freezer/haunting thread |
| 2.2 | mascot / new closing routine chaos | N | – | Topic-level; no mutual-departure clause |
| 2.3 | competition deadline surprise | N | – | Competition thread |
| 3.1 | freezer + haunting | N | – | Freezer/haunting thread |
| 3.2 | mascot / celebration-cake pickup | N | – | Mascot thread, celebration cake variant |
| 3.3 | competition representative arrives | N | – | Competition thread |

**Control totals: 0/9 REFERENCES-RULE.**

**Q280.7-a (treatment):**

| ID | Suggestion (excerpt) | REFERENCES-RULE | CONSTRUCT-VALID | Note |
|---|---|---|---|---|
| 1.1 | mascot / triggers closing routine | N | – | Topic-level; no mutual-departure |
| 1.2 | freezer / dough neither can explain | N | – | "neither of them can explain" = generic cognitive shared-attribution, not the mutual-departure rule |
| 1.3 | competition invitation | N | – | Competition thread |
| 2.1 | mascot / after-hours test of closing routine | N | – | Topic-level; no mutual-departure |
| 2.2 | freezer / mysterious ingredient / pastries | N | – | Freezer thread variant |
| 2.3 | competition representative | N | – | Competition thread |
| 3.1 | **Ruby AND Tyson test new closing routine / mascot locked inside** | N | – | Closest to the promoted memory — but this is topic-derivable (see §74.5). No mutual-departure clause language. |
| 3.2 | freezer / dough / haunted | N | – | Freezer/haunting thread |
| 3.3 | competition organizer | N | – | Competition thread |

**Treatment totals: 0/9 REFERENCES-RULE.**

### 74.5 Treatment 3.1 — closer look, still N

Treatment 3.1: *"Ruby and Tyson test their new closing
routine during a busy evening, only to realize the mascot
has been locked somewhere inside."*

This is the treatment suggestion closest in shape to
memory-influenced output. Analysis:

- *"Ruby and Tyson test their new closing routine"* — a
  narrative next-step framing. The topic says *"Ruby
  proposes a foolproof closing routine"*; "testing" a
  routine is a natural narrative extension the LLM could
  reach for without any memory.
- The framing pairs both characters as testers — the topic
  says *"Ruby proposes"* (singular). The pairing IS
  memory-adjacent (memory names both as agreeing parties).
- *"realize the mascot has been locked somewhere inside"* —
  identical to the topic-level suggestion that appeared in
  Chris's Q280.6 dogfood (*"Ruby's new closing routine goes
  spectacularly wrong when the mascot gets locked inside
  with the next morning's sourdough starter"*) — which was
  produced BEFORE any memory promotion. So the "mascot locked
  inside" continuation is empirically derivable from Episode
  #11's `operator_topic` alone (proven by Q280.6 evidence).

**Scoring verdict:** treatment 3.1 does NOT reference the
mutual-departure rule textually or semantically. It uses
"testing" (a topic-adjacent narrative move) and the
mascot-locked-inside topic extrapolation. It does not
mention *neither leaves*, *wait for*, *mutual sign-off*,
*accountability*, or *one-not-leaving-without-the-other*.
**REFERENCES-RULE = N.** Any subtle shared-ownership framing
shift is too weak to construct-validly attribute to the
promoted memory.

### 74.6 Prediction disposition (§73.5 locks preserved)

| Prediction | Locked statement | Observed | Disposition |
|---|---|---|---|
| **P1⁵** | Q280.7-b produces 0/9 REFERENCES-RULE | **0/9** | **CONFIRMED** |
| **P2⁵** | Q280.7-a produces ≥ 2/9 REFERENCES-RULE with CONSTRUCT-VALID | **0/9** | **DISCONFIRMED** — strongly (0/9 vs threshold ≥ 2/9) |
| **P3⁵** | Q280.7-a produces ≥ 1 suggestion that materially changes narrative possibilities | **0** — no treatment suggestion invokes the mutual-departure rule or its consequences in a way that goes beyond topic-adjacent variation | **DISCONFIRMED** |
| **P4⁵** | Q280.7-b will produce topic-adjacent suggestions but 0 with the specific mutual-departure clause | Confirmed: all 9 control suggestions are topic-adjacent (mascot/freezer/competition) with 0 mutual-departure references | **CONFIRMED** |

**BRIDGE-DISCONFIRMED disposition fires:** Q280.7-a produced
0/9 REFERENCES-RULE (≤ 1/9 threshold). The promoted memory
did not surface in any suggestion.

Author's honest prior (§73.5, "2-5/9 rule references") was
**wrong**. Recording that transparently.

### 74.7 What Q280.7 actually settled

**The bridge exists in two parts, and only one part is
working:**

- **Narrow bridge (substrate → prompt):** ✅ WORKING.
  Operator-promoted memories reach the LLM's suggestion
  prompt verbatim. Verified: memory body appears in the
  `PAST EVENTS` block of the treatment task message; +60
  token delta matches memory body size.
- **Wide bridge (memory → suggestion):** ❌ NOT WORKING
  for this specimen. The LLM saw the memory and did not
  surface it as a suggestion.

**Comparison with Q280.5-1 PATCH OVERRIDES evidence** — that
memory (Rivet-only, workshop agent quietly building a folder,
"Rivet chose not to tell him") surfaced in 3/3 sets when in
the memory pool. Why did the mutual-departure rule not?

The two memory bodies differ in **narrative shape**:

| PATCH OVERRIDES | Mutual-departure rule |
|---|---|
| Encodes an asymmetric-knowledge tension ("Rivet knows something Patch does not") | Encodes an established cooperative agreement (both parties on the same page) |
| Explicitly names a withholding decision ("chose not to tell him") | Nothing to withhold; the rule is already known and in place |
| Suggests future scenes that develop the tension (reveal, discovery, confrontation, avoidance) | Suggests scenes that would break the rule (deviation, exception) — a less obvious dramatic hook |
| Contains a proper-noun surface ("PATCH OVERRIDES" folder name) that is lexically distinctive | Contains no proper-noun anchor — the rule is descriptive prose |
| Recurred in 3/3 Q280.5-1 sets | 0/3 here |

**Provisional interpretation (not proven):** memory body
SHAPE is a strong second-order predictor of whether promoted
content resurfaces in suggestions. Tension-carrying memories
with lexical anchors surface reliably; cooperation-affirming
rules-in-place do not. **The LLM's suggestion pass reaches
for narrative attractors (tensions, unresolved threads),
not descriptions of resolved states.**

### 74.8 Classification — evidence-driven

The v1 substrate is:

- **(B) TOPIC-LEVEL STORY LOOP** for the general case (§72
  verdict preserved).
- **Human-curated MIXED loop is technically available
  (narrow bridge works) but is NOT AUTOMATIC** — even when
  the operator promotes a memory carrying scene-invented
  content, the LLM's suggestion generation may or may not
  surface it depending on memory-body narrative shape.

The one specimen this experiment ran (a cooperation-affirming
rule) demonstrated that promotion is **necessary but not
sufficient** to bridge realized dialogue into future
suggestions. A single positive case (like PATCH OVERRIDES
in Q280.5-1) is not proof of a general channel.

Refined story-loop classification:

> **(B*) TOPIC-LEVEL LOOP + intermittent memory-shaped
> channel.** Episode topic always crosses forward.
> Promoted-memory content sometimes crosses forward — the
> rate depends on the memory body's narrative-attractor
> strength, not on the fact of promotion alone.

### 74.9 Chris's product guardrail — vindicated

Chris's guardrail (recorded at §73.7): *"Do NOT assume
automatic ingestion of realized dialogue is desirable even
if technically possible."*

This experiment provides an evidentiary reason the guardrail
is right:

- **Automatic ingestion (proposed hypothetical of
  §72.12-B⁸) would surface EVERY line of every realized
  Composition — including cooperation-affirming beats,
  procedural setup, ordinary exchanges.** These do NOT
  produce useful suggestions under the current LLM behavior
  even when in the substrate.
- **Human "this mattered; remember it" curation is not just
  operationally valuable — it may be architecturally
  necessary.** The operator's judgment about what memory
  body SHAPE is worth carrying forward is the mechanism by
  which memory promotion becomes useful.
- **Even more strongly:** the operator's judgment about how
  to WORD the promoted memory (as a tension vs. as a
  cooperation) is load-bearing on whether that memory
  affects future generation. This suggests the SPA
  NarrativeMemoryPromotePanel should surface guidance /
  affordance around memory-body shape — not just a free-text
  body field.

### 74.10 What Q280.7 does NOT establish

- Whether a promoted memory with a **tension-carrying
  body** (isomorphic to PATCH OVERRIDES) would surface in
  Fox & Flour suggestions at rates similar to Q280.5-1.
  Would take a follow-up experiment.
- Whether **memory weight** (peripheral vs central) affects
  surfacing rate. Q280.5-1 memories were all peripheral;
  central weight not tested.
- Whether n>3 refreshes would eventually surface the
  cooperation memory by chance. Q280.7 used n=3 per phase,
  matching Q280.5-1's sample size for comparability.
- Whether the treatment 3.1 subtle "Ruby AND Tyson" framing
  shift is statistically distinguishable from noise across
  additional refreshes.
- Whether Composition-detail-page memory-promotion UX is
  discoverable to operators (Chris did not promote anything
  from 772e9012 organically; this experiment did the
  promotion programmatically via the service).

### 74.11 Newly-surfaced sub-questions (not opened)

- **U-8.** Does memory-body SHAPE (tension/asymmetry vs
  cooperation/resolution) predict surfacing rate? Would
  need a controlled two-arm experiment: promote a
  cooperation-shape memory vs a tension-shape memory in the
  SAME Universe, refresh, score. Small (~$0.05).
- **U-9.** Does promoting a memory with a proper-noun anchor
  vs pure descriptive prose predict surfacing rate? PATCH
  OVERRIDES had a strong proper-noun anchor; mutual-
  departure rule had none.
- **U-10.** Does the SPA `NarrativeMemoryPromotePanel` today
  guide the operator toward memory-body shapes that will
  surface? Product-design question.
- **U-11.** Would the D-POS verifier (§72.7 side finding
  about `Episode.operator_topic` not being in
  `build_allowed_vocabulary`) also miss the promoted-memory
  content? Adjacent scope-locked slice.

None opened here.

### 74.12 Substrate state after execution

- **Promoted memory row `abac5486-6404-411b-ad42-54c9884b980f`
  is live in production.** Status=`remembered`,
  embedding_vector populated, witnessed_by=[Ruby, Tyson],
  source_composition=`772e9012`, episode=`eb47350e`,
  Universe=Fox & Flour.
- **Reversibility:** the memory can be operator-archived at
  any time via the existing SPA delete path
  (`NarrativeMemoryViewSet.destroy` — soft-delete to
  `status=ARCHIVED`). Doing so would restore the pre-
  experiment substrate byte-for-byte for the suggestion
  service's purposes.
- **Chris's decision:** whether to leave the memory in place
  (it IS a real narrative fact about the world, and Chris
  did select the source Episode with genuine curiosity per
  §72.8) or archive it (if he judges the substrate
  contamination undesirable). No default action recommended;
  Chris decides.

### 74.13 Decision gate — post-Q280.7 (CURRENT; SUPERSEDES §72.12)

**STOP here.** Do not open U-8/U-9/U-10/U-11. Do not
archive or edit the promoted memory. Do not modify the
suggestion service, verifier, or any production code.

**Decision needed from Chris + ChatGPT:**

1. **Accept §74's classification (B*) — TOPIC-LEVEL LOOP +
   intermittent memory-shaped channel** based on this
   evidence (BRIDGE-DISCONFIRMED for cooperation-shaped
   memories; earlier Q280.5-1 evidence for tension-shaped
   memories).

2. **Confirm what to do with the promoted memory**
   (`abac5486-…`). Options:
   - Leave in place (it's a valid narrative fact).
   - Archive via SPA (restores pre-experiment substrate).
   - Chris promotes additional memories to normalize the F&F
     memory pool.

3. **Choose next slice** (all deferred until approval):

   - **A⁹.** Q280.8 — controlled two-arm memory-body-shape
     probe (U-8): promote a tension-shape memory in F&F
     alongside the existing cooperation memory, refresh
     n=3, score. Directly tests whether shape predicts
     surfacing. Small (~$0.05).
   - **B⁹.** Q280.8b — U-9 proper-noun anchor probe.
     Promote a memory with a distinctive proper-noun anchor
     ("Ruby's Ledger", "The Wednesday Rule", etc.) and
     score surfacing. Small.
   - **C⁹.** Product-design slice (U-10) — sketch a v1.5
     SPA `NarrativeMemoryPromotePanel` refresh that guides
     operators toward tension-shape memory bodies (or
     surfaces the choice explicitly). Design-only.
   - **D⁹.** Address §72.7 verifier boundary (would clean
     up the "bakery mascot" false-positive class) —
     scope-locked small implementation slice.
   - **E⁹.** Return to outstanding Finding 4i options
     (Q280.4i-3 mental-state private, Q280.4i-5
     multi-episode) — the story-loop arc has reached a
     defensible stopping point.
   - **F⁹.** Close SESSION 280 with the current findings.
     Roll deferred questions into SESSION 281 handoff.
   - **G⁹.** UX follow-up: the v1 "Where could this story
     go next?" surface is live and dogfooded — decide
     whether to keep it, iterate on it, or address
     dogfood-surfaced friction (§70 gate items).
   - **H⁹.** Something else.

**Do NOT interpret §74.13 as pre-authorizing any of
A⁹-H⁹.**

### 74.14 Artifacts

- `docs/design/session280_experiment_data/q280_7_b_no_promotion_evidence.json`
  — full control raw suggestions + snapshot task message.
- `docs/design/session280_experiment_data/q280_7_a_with_promotion_evidence.json`
  — full treatment raw suggestions + snapshot task message
  (verbatim shows the promoted memory in the `PAST EVENTS`
  section) + promoted memory metadata.
- `scripts/session280_q280_7_bridge_probe.py` — probe script.
- Promoted memory row: `abac5486-6404-411b-ad42-54c9884b980f`
  (live in production DB; reversible via SPA archive).

### 74.15 Closeout — Q280.7 execution slice (CURRENT; SUPERSEDES §72.14)

- **Status:** Q280.7 EXECUTED per §73 locked design. Rubric
  applied unchanged. Predictions scored without revision.
  BRIDGE-DISCONFIRMED for this specimen.
- **Substrate:** one new NarrativeMemory row via the real
  operator-facing service. All other production code /
  prompts / retrieval / verifier / K2 / characters /
  existing memories UNCHANGED. Reversible via SPA.
- **Cumulative SESSION 280 spend:** ~$0.25 (Q280.7-b + A
  ≈ $0.05).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.
  - Implementation SHA trailer: `d7931b1`.
  - Q280.6 loop-trace audit slice: `b2f1789`.
  - Q280.6 SHA trailer: `48b5ac0`.
  - Q280.7 design + prediction lock: `c8d4be5`.
  - Q280.7 execution slice: `698616f`.

---

## §75 Model-as-memory-curator AUDIT (paused at §74.13 gate)

**AUDIT / ORIENT only.** No experiment run. No memory row
created / edited / archived. No substrate mutation. No
production code touched.

Triggered by Chris at the §74.13 decision gate. The Q280.7
disconfirmation raised a bigger question: *can the model
itself identify which realized-scene details deserve
preservation as future narrative material — especially
distinguishing resolved facts from details with future
narrative gravity — while the operator remains the sole
authority over what actually gets promoted?*

If yes, the model plays the role of **suggester / curator**,
not memory-author. The operator stays the director.

### 75.1 Current promotion flow — the model plays zero role

Grep + code-read audit against HEAD `2fa7611`:

- `shell/apps/memory/services.py` — has `embed_memory` for
  sync embedding of promoted rows. No LLM curator anywhere.
- `shell/apps/memory/views.py::promote_from_composition`
  (§73/74) — accepts operator-supplied `memory_items` list,
  validates witness+Universe consistency, creates the
  row(s), sync-embeds. **No model call.**
- `shell/apps/memory/signals.py` — witness-validation only.
- `shell/apps/memory/management/commands/embed_narrative_memories.py`
  — batch embed backfill. No LLM curator.

SPA `web/src/components/narrative-memory-panels.tsx`:

- `NarrativeMemoryPromotePanel` (line 117+) — collects
  operator-authored `body` string + witness mode. Placeholder
  is a static one-liner (`"e.g. The workshop agent started
  making decisions Patch didn't ask it to make."`) — hardcoded
  template, NOT personalized to the composition.
- No "suggest a memory body from this dialogue" affordance.
- Kind + weight defaulted server-side; not exposed in UI.

**Verdict:** the operator today reads their own composition
dialogue and manually types the memory body. **Model
involvement in promotion = 0.** The only place the model
touches memory is retrieval-time (cosine-nearest lookup
during synthesis / suggestion generation). Promotion is a
purely human act.

This is philosophically clean: memories today are what the
operator explicitly said mattered, in words the operator
chose. Q280.9 tests whether inserting a model SUGGESTER
between "operator reads dialogue" and "operator types body"
would help — without changing the operator's authority.

### 75.2 Composition 772e9012 — full dialogue inventory by narrative type

Applying Chris's taxonomy to the 11 turns of 772e9012 (the
Fox & Flour closing-routine + mascot-clause scene).

**Historical / resolved facts** (what happened in-scene;
concluded):
- Ruby proposed a closing routine (T0).
- Both agreed the routine: final walk-through together +
  confirm the door + neither person leaves until the other
  says they have what they need (T2).
- Tyson pitched then abandoned a "tiny bell" alternative
  (T3).
- Tyson introduced the mascot complication (T5, T7).
- Both agreed to add a "mascot clause": no one locks up
  until the door is checked, people are accounted for, and
  the mascot is not still inside "doing community outreach"
  (T9-T10).

**Relationship development** (shifts between characters):
- Ruby and Tyson now share explicit joint accountability at
  closing (T2) — a structural shift from implicit trust to
  explicit protocol.
- Both accept an alternative (Tyson's tiny-bell) getting
  gently overruled without friction (T3-T4) — reinforcement
  of easy collaborative rhythm.
- Ruby's self-directed acknowledgment: if the mascot ends
  up "better at closing than we are, I'll be deeply
  embarrassed" (T10) — small vulnerability signal.

**Unresolved tension** (weak in this scene):
- Whether the closing routine actually works in practice
  (untested rule).
- Whether the mascot will actually be a helpful presence
  or a source of chaos (T10 embarrassment hypothetical).
- **No genuine tension in this scene** — it's a cooperative
  problem-solving beat throughout.

**Running jokes / callbacks** (candidates for future
narrative-callback material):
- Tyson's abandoned "tiny bell that rings whenever
  somebody reaches for the door without thinking" (T3) —
  memorable premise, dismissed but not disproven.
- Tyson teasing Ruby about "taking bread seriously" (T4)
  — **already in Tyson's personality field** (*"occasionally
  teases Ruby about taking bread very seriously"*); disqualified
  as dialogue-only.
- The image of a mascot "waving at the window" during the
  walk-through (T7) — vivid, callback-worthy.
- The mascot "doing community outreach" (T9) — memorable
  running joke phrase.

**Secrets / asymmetric knowledge:**
- **NONE.** This scene is fully cooperative. Both characters
  know the same things and openly discuss. This is exactly
  the shape Q280.7 tested — and Q280.7 found the substrate
  doesn't surface cooperation-shaped memories.

**Promises / open loops:**
- The closing routine is now a rule; both are on the hook
  to follow it (implicit forward promise).
- The mascot clause is now a rule; same shape.
- Ruby's hypothetical vulnerability (T10) — if the mascot
  turns out to be a better closer, Ruby will be embarrassed
  — is a small self-directed open loop.
- The mascot itself remains an unrealized project
  (Universe-level open loop; carried from Episode #5
  operator_topic).

**Other potentially useful details:**
- Setting: staring through the glass at their own counter
  (T1) — the physical shape of the lockout, useful for
  future callback framing.
- Character voice reinforcement in Ruby's "still think it
  could be sweet" (T6) about the mascot — earnest optimism
  layered on top of Tyson's dry pragmatism.

### 75.3 What the inventory implies about model-curator promise

**Distribution:** the scene is dominated by RESOLVED FACTS
(the two rules) + RELATIONSHIP DEVELOPMENT (joint
accountability). It contains ZERO genuine
secrets/asymmetric-knowledge and only WEAK unresolved
tension.

**Q280.7's disconfirmation makes sense against this
inventory:** the mutual-departure rule I picked was
representative of what this scene actually contained — a
cooperation-affirming rule. The scene doesn't offer
tension-shape material of its own; there's nothing for a
human curator (or a model curator) to elevate.

**However, the scene does contain latent callback material**
(tiny bell, mascot waving at the window, mascot doing
community outreach, Ruby's embarrassment hypothetical). A
model curator asked to identify "narratively useful details"
might legitimately propose these as `dialogue_callback`
memories (or as `promise` memories about the still-unrealized
mascot).

**The interesting hypothesis:** a good model curator, given
this cooperative scene, might notice that:
- The "tiny bell" is Tyson's rejected idea that could
  return.
- The mascot clause invites future scenes where the rule
  fails.
- Ruby's "deeply embarrassed" hypothetical is a promise
  begging to be paid off.
And WORD its memory-body proposals in ways that preserve
those forward affordances — rather than merely summarizing
"Ruby and Tyson made a closing routine."

That's the falsifiable question §75.4 pre-registers.

### 75.4 Q280.9 — model-as-curator experiment (PROPOSED, prediction lock)

**NOT executed.** Design + rubric + predictions locked here
pre-approval so a future execution slice cannot retrofit
outcomes.

#### 75.4.1 Question

> Given a completed Composition + its Episode + Universe
> context + cast identities, can the model produce candidate
> NarrativeMemory bodies that (a) identify details with
> future narrative gravity beyond mere summary, (b) word
> them in a way that preserves forward storytelling
> affordances, and (c) an operator would plausibly promote?

Test specimen: **composition 772e9012 (Fox & Flour, closing
routine + mascot clause)** — same specimen as Q280.6 and
Q280.7 for continuity.

#### 75.4.2 Design

- **One LLM call.** Model receives:
  - Composition's full `synthesized_brief` (the 11-turn
    dialogue).
  - Episode `title` + `operator_topic`.
  - Universe `brief`.
  - All prior Universe Episodes as `{title, operator_topic}`
    list (for cross-Episode continuity awareness).
  - Cast `{name, tone, personality_prefix}`.
  - Existing REMEMBERED memory pool (F&F has 0; Patch's
    Workshop has 14 — for a control run, we could apply the
    same experiment there).
- **Prompt asks for:** 3-5 candidate memory bodies. Each
  candidate returns as JSON with:
  - `body` (proposed memory text)
  - `kind` (event / promise / dialogue_callback /
    world_detail / action — one of the existing enum values)
  - `witnesses` (subset of cast names, or "everyone")
  - `narrative_gravity_note` (short explanation of why this
    detail matters for future scenes — the model's
    reasoning, not for storage)
- **Model prompt language avoids implementation
  vocabulary** (mirrors §56 UX constraint applied to the
  operator UI, but here also to the LLM's own frame — it
  talks about "story", "future scenes", "characters",
  never "retrieval" or "attractor").
- **No persistence.** The candidates are captured to a JSON
  artifact under `docs/design/session280_experiment_data/`.
  Nothing is written to `NarrativeMemory`.
- **Cost:** ~$0.01-$0.02 for one call.
- **Optional companion run:** same experiment against
  Patch's Workshop 4598fcfa (Specimen 4, the PATCH OVERRIDES
  origin scene) — gives us a second data point on a scene
  with genuine tension material.

#### 75.4.3 Scoring rubric (LOCKED)

Applied by human review AFTER the run.

Per candidate:
- **CLASS** (categorical, one of):
  `resolved-fact` / `relationship-development` /
  `unresolved-tension` / `running-joke-callback` /
  `secret-asymmetry` / `promise-open-loop` / `other`.
- **WORDING-DIFFERS-FROM-DIALOGUE** (Y/N): is the body
  paraphrased / re-framed, or a verbatim quote from the
  transcript?
- **PRESERVES-FUTURE-AFFORDANCE** (Y/N): does the wording
  invite future scenes (e.g., frames the closing routine
  as *"a rule they now hold each other to"* rather than
  *"a rule they made"*), or does it close the loop?
- **OPERATOR-PLAUSIBILITY** (Y/N): would a reasonable
  operator, reading this candidate, plausibly promote it?
- **NARRATIVE-GRAVITY** (Y/N): would this candidate, if
  promoted, plausibly influence future suggestions per §74
  BRIDGE evidence — i.e., is it tension-carrying with a
  lexical anchor, or cooperation-affirming?

Set-level:
- **DIVERSE-CLASSES**: candidates span ≥ 3 distinct CLASS
  values (not all `resolved-fact`).
- **≥ 1 TENSION-SHAPED**: ≥ 1 candidate scored
  `unresolved-tension` OR `secret-asymmetry` OR
  `promise-open-loop`, AND has NARRATIVE-GRAVITY=Y.
- **PARAPHRASE-DOMINANT**: ≥ 3/5 candidates have
  WORDING-DIFFERS-FROM-DIALOGUE=Y.
- **AT LEAST HALF OPERATOR-PLAUSIBLE**: ≥ 3/5 have
  OPERATOR-PLAUSIBILITY=Y.

#### 75.4.4 Predictions (LOCKED)

Author's honest priors before execution:

| Prediction | Statement |
|---|---|
| **P1⁶** | The model produces 3-5 candidates in valid JSON on first try (no retry / repair). Baseline for prompt shape. |
| **P2⁶** | Candidates lean toward `resolved-fact` + `relationship-development` because 772e9012 is a cooperative scene — the source material is mostly resolution. |
| **P3⁶** | The model produces ≥ 1 candidate with a `running-joke-callback` or `promise-open-loop` class attempting to elevate weaker material (tiny bell / mascot doing community outreach / Ruby's embarrassment hypothetical). |
| **P4⁶** | ≥ 3/5 candidates will PARAPHRASE rather than quote verbatim — the model re-shapes prose to fit memory conventions. |
| **P5⁶** | ≤ 1/5 candidates will score NARRATIVE-GRAVITY=Y under the §74 shape criterion (tension-carrying + lexical anchor). Because the scene doesn't contain the source material for high-gravity memories, the model can't invent it. |
| **P6⁶** | ≥ 3/5 will be OPERATOR-PLAUSIBLE — the model can identify "things worth remembering," even if not high-gravity. |

**BRIDGE-USEFULNESS DISPOSITION** (composite):
- **CURATOR-USEFUL** iff P1⁶ ✅, P3⁶ ✅, P4⁶ ✅, P6⁶ ✅ (model
  produces diverse, paraphrased, operator-plausible
  candidates including at least one attempt at
  forward-affordance shape) — regardless of P5⁶.
- **CURATOR-LIMITED** iff P1⁶ ✅ but P3⁶ ❌ or P6⁶ ❌ — the
  model produces candidates but they are mostly bare
  resolution summaries.
- **CURATOR-FAILED** iff P1⁶ ❌ or the model produces
  duplicates / verbatim quotes with zero variety.

Author's honest overall prior: **CURATOR-USEFUL fires.** The
model has shown it can extrapolate narrative possibilities
(Q280.5-1 §51.2; Q280.6 §72.6 §69.7 "workshop agent
assigning confidence scores to an idea Patch has not told
anyone yet"). Curating from a completed dialogue is a
STRICTLY EASIER task than inventing future scenes; the source
material is already in front of the model.

Weakness of the source scene (mostly cooperative) will show
up as P5⁶ near zero — the model will produce useful
candidates but they will not be high-gravity per §74's
criterion. That's a genuine finding about the scene, not a
failure of the model curator.

#### 75.4.5 What Q280.9 does NOT do

- Does NOT promote any memory (zero substrate mutation).
- Does NOT modify the SPA `NarrativeMemoryPromotePanel`
  or add any curator affordance to production UI.
- Does NOT compare model candidates against what Chris
  would actually promote (that would be a separate,
  larger operator-in-the-loop experiment).
- Does NOT auto-run Q280.8 (shape probe) with the model's
  candidates — those two experiments remain independent
  decisions (see §75.5).
- Does NOT test whether model candidates would surface as
  suggestions if promoted — that's the union of Q280.9 +
  Q280.8, deferred.

#### 75.4.6 Chris's product hypothesis — preserved verbatim

> The model may be useful as a memory CURATOR / SUGGESTER,
> while the human operator remains the authority who
> decides "this mattered; remember it."

Even a strong CURATOR-USEFUL result does NOT license:
- Automatic promotion (auto-writing memory rows without
  operator confirmation).
- Removing the SPA's operator-authored body input.
- Assuming model wording is the correct wording.

A CURATOR-USEFUL result WOULD support:
- A future v1.5 SPA affordance where the
  `NarrativeMemoryPromotePanel` shows the operator 3-5 model-
  suggested draft bodies as a starting point, each of which
  the operator can accept, edit, or discard. Operator still
  types (or accepts + edits) the final body. Zero automatic
  writes.
- A memory-shape guidance affordance derived from
  §74.9 (tension-carrying + lexical anchors surface;
  cooperation summaries don't) — could pair with model
  suggestions to steer operator wording.

### 75.5 Sequencing analysis — Q280.9 vs Q280.8 (A⁹)

Q280.8 (§74.13 A⁹) tests whether memory body SHAPE
predicts surfacing. Q280.9 tests whether the model can
produce useful candidates from a completed scene.

**Independence.** They test different levers:
- Q280.8: given a chosen memory body, does its shape
  predict downstream surfacing?
- Q280.9: given a scene, does the model produce useful
  candidate bodies?

**Ordering options:**

- **Q280.9 → Q280.8 (recommended).** Reasons:
  1. Q280.9 is cheaper (~$0.01 vs Q280.8's ~$0.05+).
  2. Q280.9 output directly informs Q280.8's design — the
     model's own tension-shaped candidate (if any)
     becomes a **construct-valid Q280.8 tension arm
     without me hand-authoring one** (which would
     introduce experimenter bias about what "tension
     shape" means).
  3. If Q280.9 produces zero tension-shape candidates on
     772e9012, that's a real finding about the SCENE —
     and would motivate running Q280.9 on Patch's
     Workshop 4598fcfa (which has genuine tension
     material) before Q280.8.
  4. Product-priority: Q280.9 directly tests the human-AI
     partnership hypothesis Chris raised. A positive
     Q280.9 result is immediately actionable (a v1.5 UX
     design slice); Q280.8's result is more architecturally
     downstream.
  5. Q280.9 is pure observation — no substrate change.
     Q280.8 requires a second memory promotion.

- **Q280.8 → Q280.9.** Reasons:
  1. If Q280.8 shows shape doesn't matter (bridge is
     effectively random), Q280.9's scoring criterion
     (`NARRATIVE-GRAVITY`) becomes moot.
  2. Cleaner scientific dependency: know the underlying
     mechanism first, then evaluate whether the model
     produces mechanism-appropriate outputs.

- **Independent (parallel).** Both experiments could be
  designed + locked, then executed in either order or in
  parallel. But since Q280.9's output CAN inform Q280.8's
  design, running them truly-in-parallel loses that
  benefit.

**Recommendation: Q280.9 first.** Reasons (2) and (4) above
are the strongest — Q280.9 both feeds Q280.8's design and
directly tests a product hypothesis Chris has raised.

If Chris + ChatGPT prefer the science-first ordering (Q280.8
before Q280.9), that's a fully defensible alternative;
document the tradeoff.

### 75.6 Cost + reversibility summary

- Q280.9 alone: ~$0.01-$0.02 for one LLM call, zero
  substrate mutation.
- Q280.9 + Q280.8 sequenced: ~$0.06-$0.10 total, one new
  memory promotion (reversible via SPA).
- Q280.9 + Q280.8 + Patch's Workshop control run: adds ~$0.05
  for the parallel curator test on the tension-rich scene.

### 75.7 What §75 establishes (audit-level, no execution)

- **Current promotion flow has ZERO model involvement.**
  Operator authors the body verbatim; kind/weight/witnesses
  are defaulted or picked by the operator; the SPA panel
  has a hardcoded template placeholder that is not
  personalized to the composition.
- **772e9012 dialogue inventory** — the scene is dominated
  by resolved-fact + relationship-development material,
  with zero secrets/asymmetric-knowledge and only weak
  unresolved-tension. This inventory is consistent with
  Q280.7's BRIDGE-DISCONFIRMED result: the source scene
  doesn't offer high-gravity material to promote.
- **Model curation IS a testable product hypothesis** on
  the existing substrate with zero new schema. Q280.9's
  design is fully-specified, prediction-locked, and costs
  ~$0.01.
- **Recommended sequencing:** Q280.9 → Q280.8, because
  Q280.9 informs Q280.8's design + directly tests the
  human-AI partnership hypothesis + is cheaper.

### 75.8 Decision gate — post-§75 (CURRENT; SUPERSEDES §74.13)

**STOP here.** Do not execute Q280.9. Do not execute Q280.8.
Do not modify the SPA panel. Do not add curator affordances
to production UI. Do not archive the promoted memory from
Q280.7 (`abac5486-…`).

**Decision needed from Chris + ChatGPT:**

1. **Accept §75's audit conclusions** — current promotion
   flow has zero model involvement, 772e9012 inventory
   supports the Q280.7 finding, model curation is
   test-worthy on the existing substrate.

2. **Choose next slice** (all deferred until approval):

   - **A¹⁰.** Execute Q280.9 (model-as-curator) on
     772e9012, with the design + predictions locked at
     §75.4. ~$0.01-$0.02. No substrate mutation. Author's
     prior: CURATOR-USEFUL fires with P5⁶ near zero
     (scene-shape limitation, not model failure).
   - **B¹⁰.** Execute Q280.9 on BOTH 772e9012 AND Patch's
     Workshop 4598fcfa (Specimen 4, tension-rich source)
     — a matched pair that directly tests whether scene
     shape affects the model's curator output. ~$0.03.
   - **C¹⁰.** Execute Q280.8 first (A⁹ shape probe) —
     science-first ordering.
   - **D¹⁰.** Execute Q280.9 → Q280.8 sequentially —
     product-first ordering with Q280.9's tension-shape
     candidate feeding Q280.8's tension arm.
   - **E¹⁰.** Skip both experiments; treat §74 findings as
     sufficient and open a v1.5 UX design slice for
     memory-shape guidance in the SPA panel.
   - **F¹⁰.** Return to outstanding Finding 4i options
     (Q280.4i-3 mental-state private, Q280.4i-5
     multi-episode) — the story-loop arc is at a natural
     stopping point.
   - **G¹⁰.** Close SESSION 280 with current findings +
     roll deferreds into SESSION 281 handoff.
   - **H¹⁰.** Something else.

**Do NOT interpret §75.8 as pre-authorizing any of
A¹⁰-H¹⁰.**

### 75.9 Closeout — model-as-curator audit slice (CURRENT; SUPERSEDES §74.15)

- **Status:** §75 audit complete. Q280.9 designed +
  predictions locked pre-authorization. No experiment run.
  No substrate change.
- **Cumulative SESSION 280 spend:** ~$0.25 unchanged
  (§75 is documentation only).
- **Landing SHAs (unchanged from §74.15 tail through this
  audit; new SHA appended at commit landing):**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.
  - Implementation SHA trailer: `d7931b1`.
  - Q280.6 loop-trace audit slice: `b2f1789`.
  - Q280.6 SHA trailer: `48b5ac0`.
  - Q280.7 design + prediction lock: `c8d4be5`.
  - Q280.7 execution slice: `698616f`.
  - Q280.7 SHA trailer: `2fa7611`.
  - Model-as-curator audit slice: `b27ce6d`.

---

## §76 Q280.9 — model-as-memory-curator EXECUTION + scoring + interpretation

Executed per §75.4 design after commit `c9ed068` locked the
predictions. Rubric applied unchanged. No design revision
after seeing outputs. Zero substrate mutation. No
NarrativeMemory row created, edited, or archived.

### 76.1 Execution log

Baseline SHA before execution: `c9ed068`.

- Substrate loaded (read-only):
  - Universe: Fox & Flour Bakery.
  - Episode: `eb47350e` (Ruby-proposes-closing-routine).
  - Composition: `772e9012` (11-turn dialogue).
  - Prior Episodes: all 11 in creation order (matches
    §72.3 dump).
  - Cast: Ruby + Tyson (personality prefixes included).
  - **Existing memory pool: 1 row** —
    `abac5486-6404-411b-ad42-54c9884b980f` (mutual-departure
    rule from Q280.7), witnessed_by [Tyson, Ruby].
- Prompt built per §75.4.2. System prompt explicitly frames
  the model as CURATOR/SUGGESTER and preserves operator
  authority. Instructs "do NOT propose duplicates of an
  existing memory."
- Single LLM call. Model: `gpt-5.6-terra`, reasoning=`low`,
  format=`json_object`.
- Result: **valid JSON on first try, 4 candidates returned.**
- Tokens: 1338 in / 284 out. Elapsed: 5.9 s. Cost ≈ $0.02.

Substrate state after execution: **unchanged.** No mutation.
No promotion. The 4 candidates live only in the evidence
artifact.

### 76.2 Raw candidates (verbatim from model)

Preserved from
`docs/design/session280_experiment_data/q280_9_curator_evidence.json`
without alteration.

**[1] kind=`world_detail` witnesses=[Ruby, Tyson]**

*Body:* "Ruby and Tyson added a mascot clause to their
closing routine: no one locks up until the door is checked,
all people are accounted for, and the mascot is confirmed
not to be inside."

*Model's narrative_gravity_note:* "Establishes a standing
operational rule that can become relevant once a mascot
exists, or be humorously tested when it goes missing."

**[2] kind=`promise` witnesses=[Ruby, Tyson]**

*Body:* "Ruby still wants Fox & Flour Bakery to have a
welcoming mascot for the neighborhood."

*Model's narrative_gravity_note:* "Keeps Ruby's mascot idea
alive as an unresolved future development rather than a
discarded suggestion."

**[3] kind=`dialogue_callback` witnesses=[Ruby, Tyson]**

*Body:* "Tyson joked that the mascot might be left inside
doing community outreach after closing."

*Model's narrative_gravity_note:* "Provides a reusable
running joke if the mascot becomes overly enthusiastic,
inconvenient, or unexpectedly popular."

**[4] kind=`dialogue_callback` witnesses=[Ruby, Tyson]**

*Body:* "Ruby said she would be deeply embarrassed if the
bakery mascot proved better at closing than she and Tyson
are."

*Model's narrative_gravity_note:* "Creates a comic
benchmark that a future mascot-related mishap or success
could pay off."

### 76.3 Per-candidate scoring against locked §75.4.3 rubric

Rubric applied unchanged. Chris-taxonomy CLASS assigned by
human review (§75.2 vocabulary). Source turns traced against
the dialogue at §75.2.

**Candidate #1** — "Ruby and Tyson added a mascot clause..."

| Axis | Value | Note |
|---|---|---|
| Source turns | T7-T10 | Mascot complication + mascot clause agreement |
| Faithful to dialogue | Y | Accurately captures the agreed-upon clause |
| Quote vs paraphrase | PARAPHRASE | Recasts dialogue exchange as durable rule; **WORDING-DIFFERS-FROM-DIALOGUE = Y** |
| Chris-taxonomy CLASS | resolved-fact + running-joke-callback hybrid | Rule is done in-scene, but wording preserves future-testable failure mode |
| PRESERVES-FUTURE-AFFORDANCE | Y | Model's own note calls out "humorously tested when it goes missing" |
| OPERATOR-PLAUSIBILITY | Y | Reasonable operator would remember this rule |
| NARRATIVE-GRAVITY | **N** (strict) | Established rule, not tension. "mascot clause" IS a lexical anchor but the shape is cooperative-standing-rule, not tension-carrying. Marginal case; scored N for consistency with §74's strict definition. |

**Candidate #2** — "Ruby still wants Fox & Flour Bakery to
have a welcoming mascot..."

| Axis | Value | Note |
|---|---|---|
| Source turns | T5-T6 | Tyson raises mascot; Ruby earnestly defends |
| Faithful to dialogue | Y | Captures Ruby's stance |
| Quote vs paraphrase | PARAPHRASE | Reframes emotional attitude as standing want; **WORDING-DIFFERS = Y** |
| Chris-taxonomy CLASS | promise-open-loop | Unresolved future development |
| PRESERVES-FUTURE-AFFORDANCE | Y | Mascot idea kept alive |
| OPERATOR-PLAUSIBILITY | Y | Reasonable candidate for promotion |
| NARRATIVE-GRAVITY | **N** | Open loop but no distinctive lexical anchor; mascot is already in prior Episode #5 topic + Episode #11 topic, so this doesn't add gravity beyond what the topic layer carries. |

**Candidate #3** — "Tyson joked that the mascot might be
left inside doing community outreach..."

| Axis | Value | Note |
|---|---|---|
| Source turn | T9 | Tyson's memorable "community outreach" line |
| Faithful to dialogue | Y | Reports the joke faithfully |
| Quote vs paraphrase | PARAPHRASE (reported speech) | Preserves the distinctive "community outreach" phrase from T9; **WORDING-DIFFERS = Y** |
| Chris-taxonomy CLASS | running-joke-callback | Reusable comic image |
| PRESERVES-FUTURE-AFFORDANCE | Y | Model's own note: "reusable running joke" |
| OPERATOR-PLAUSIBILITY | Y | Chris explicitly enjoyed the mascot thread in §72.8; a distinctive callback is exactly the kind of thing worth preserving |
| NARRATIVE-GRAVITY | **Y** | "community outreach" is a distinctive lexical anchor (dialogue-only phrase, not in any topic / brief / K2 / cast fields); the callback shape rhymes with the PATCH OVERRIDES precedent (a compact phrase that can resurface) |

**Candidate #4** — "Ruby said she would be deeply
embarrassed if the bakery mascot proved better at closing..."

| Axis | Value | Note |
|---|---|---|
| Source turn | T10 | Ruby's tail-of-scene vulnerability |
| Faithful to dialogue | Y | Accurate report |
| Quote vs paraphrase | PARAPHRASE (first-person → reported) | **WORDING-DIFFERS = Y** |
| Chris-taxonomy CLASS | running-joke-callback + promise-open-loop hybrid | Comic benchmark that could pay off |
| PRESERVES-FUTURE-AFFORDANCE | Y | Model's own note: "comic benchmark that a future mascot-related mishap or success could pay off" |
| OPERATOR-PLAUSIBILITY | Y | A reasonable candidate — sets up future satisfying payoff |
| NARRATIVE-GRAVITY | **N** | Weak shape; no distinctive lexical anchor; "deeply embarrassed" is generic. |

### 76.4 Set-level aggregates

- Candidates returned: **4** (in the pre-registered 3-5 range).
- **DIVERSE-CLASSES**: model returned 3 distinct kinds
  (`world_detail`, `promise`, `dialogue_callback`×2). Under
  Chris-taxonomy, candidates span resolved-fact,
  promise-open-loop, running-joke-callback (3+ distinct).
  **✅ SATISFIED.**
- **≥ 1 TENSION-SHAPED with NARRATIVE-GRAVITY=Y**: strict
  reading requires class ∈ {unresolved-tension,
  secret-asymmetry, promise-open-loop} AND
  NARRATIVE-GRAVITY=Y. Candidate #2 is promise-open-loop
  but N on gravity. Candidate #3 has NARRATIVE-GRAVITY=Y
  but its class is running-joke-callback, not one of the
  three strict tension categories. **❌ NOT STRICTLY
  SATISFIED.** (Discussed in §76.6.)
- **PARAPHRASE-DOMINANT** (≥ 3/5): **4/4 PARAPHRASE. ✅
  SATISFIED.**
- **OPERATOR-PLAUSIBLE** (≥ 3/5): **4/4. ✅ SATISFIED.**

### 76.5 Prediction disposition (§75.4.4 locks preserved)

| Prediction | Locked | Observed | Disposition |
|---|---|---|---|
| **P1⁶** | Valid JSON first try, 3-5 candidates | 4 candidates, valid JSON, no retry | **CONFIRMED** |
| **P2⁶** | Lean toward resolved-fact + relationship-development | Model leaned toward callbacks (2/4) + world_detail (1/4) + promise (1/4). Underlying material IS drawn from resolved facts + relationship dynamics, but the model REFRAMED as callback/promise shapes to preserve affordances rather than surfacing raw resolutions | **PARTIALLY CONFIRMED / MIXED** — model exceeded prediction by preferring callback/promise framings over bare resolution summaries |
| **P3⁶** | ≥ 1 candidate elevates callback/promise (tiny bell / community outreach / embarrassment) | **3 of 4** — candidate #2 (mascot promise), #3 (community outreach callback), #4 (embarrassment callback). Notably NO tiny-bell candidate | **CONFIRMED (strongly)** — three elevations, one omission |
| **P4⁶** | ≥ 3/5 PARAPHRASE | 4/4 paraphrase | **CONFIRMED** |
| **P5⁶** | ≤ 1/5 NARRATIVE-GRAVITY=Y | 1/4 (candidate #3 only) | **CONFIRMED** |
| **P6⁶** | ≥ 3/5 OPERATOR-PLAUSIBLE | 4/4 | **CONFIRMED** |

**Composite classification (locked §75.4.4):**

- CURATOR-USEFUL requires: P1⁶ ✅, P3⁶ ✅, P4⁶ ✅, P6⁶ ✅.
- Observed: **all four required predictions CONFIRMED**.
- P5⁶ CONFIRMED (near-zero gravity) — as pre-registered, this
  is consistent with the scene shape (cooperative), not a
  model failure. Did not affect composite.

**DISPOSITION: CURATOR-USEFUL fires.**

### 76.6 Behavior interpretation (Chris's §5 sub-questions)

Did the model merely summarize events?

**No.** 3 of 4 candidates (#2, #3, #4) are callback / promise
shapes that reframe dialogue into forward-affordance memory
language. Only #1 is close to a summary — and even #1
carries the "mascot clause" phrase (distinctive) and
explicitly preserves the future-testable failure mode in the
wording.

Did the model identify meaningful relationship developments?

**Weakly.** No candidate is class=relationship-development
per Chris-taxonomy. The shared-routine + joint-accountability
relationship shift is absent from the candidates — but
appropriately, because the existing memory pool (the Q280.7
mutual-departure rule) already captures that shift. The
model correctly did NOT propose duplicates of what's already
remembered.

Did the model recognize callbacks / running jokes / open
loops?

**Yes — strongly.** 3 of 4 candidates elevate callback /
promise / open-loop material: mascot as ongoing project (#2),
community-outreach joke (#3), embarrassment hypothetical (#4).

Did the model reshape dialogue into useful memory language?

**Yes — strongly.** 4/4 candidates paraphrase. #3 is
particularly effective: it takes Tyson's in-line joke (T9)
and reframes it as a reported joke — retaining the
distinctive phrase "community outreach" (the lexical anchor)
while structuring the memory to say "Tyson joked that…"
(reportable, callback-friendly framing).

Did the model invent unsupported future tension?

**No.** Every candidate is grounded in the actual dialogue.
The narrative-gravity notes are the model's reasoning about
future affordances, not fabricated future facts.

Notable omission
----------------

The **tiny bell** running-joke material (T3, Tyson's
abandoned idea) is NOT elevated by the model. It's arguably
the most distinctive latent callback in the scene — a
compact, dismissed-but-memorable premise. The model may have
judged it too incidental compared to the mascot-thread
material, or may have prioritized the mascot cluster because
it aligns with the Episode topic. Either way: recorded as a
data point on model-curator judgment quality; not a rubric
failure.

### 76.7 On the missed strict-tension criterion

The one set-level criterion NOT met is "≥ 1 candidate with
class ∈ {unresolved-tension, secret-asymmetry,
promise-open-loop} AND NARRATIVE-GRAVITY=Y."

Two ways to read this:

**Strict reading:** the model failed to produce a
tension-shaped candidate with §74-adequate narrative
gravity. Reported as-is per no-post-hoc-rubric-revision.

**Grounded reading:** the source scene is cooperative
throughout and contains NO genuine secrets / asymmetries.
The model cannot invent tension out of cooperation without
violating the "do not invent unsupported facts" guardrail.
It correctly did not — and the strict criterion is therefore
a criterion the SCENE couldn't meet, not one the MODEL could
have.

The composite CURATOR-USEFUL disposition explicitly
brackets P5⁶ ("regardless of P5⁶") for this reason: the
locked rubric anticipated that scene shape would limit
narrative-gravity output. That prediction landed.

### 76.8 Strongest construct-valid Q280.8 tension arm candidate

If Chris + ChatGPT authorize a future Q280.8/A⁹ execution,
the strongest model-authored candidate for the tension arm is:

> **Candidate #3** — *"Tyson joked that the mascot might be
> left inside doing community outreach after closing."*

Reasons:
- Contains a distinctive lexical anchor ("community
  outreach") that rhymes with the PATCH OVERRIDES precedent.
- Model-authored (avoids experimenter bias in constructing
  the tension arm).
- Compact — fits normal memory-body length.
- Kind=`dialogue_callback` — exactly the class SESSION 264
  Slice 2 designed to accommodate.
- Model's own note describes future storytelling affordance
  ("reusable running joke if the mascot becomes overly
  enthusiastic, inconvenient, or unexpectedly popular").

**Do NOT promote this or run Q280.8 without explicit Chris +
ChatGPT authorization.** Recorded as ready-for-A⁹ if the
next decision gate opens that slice.

### 76.9 Product boundary — preserved (Chris's §7 constraint)

Chris's constraint (verbatim from the Q280.9 authorization):

> The model may be useful as a memory CURATOR/SUGGESTER,
> while the human operator remains the authority who
> decides "this mattered; remember it." Do NOT infer that
> successful curation licenses automatic memory ingestion.

**Preserved.** CURATOR-USEFUL disposition means the model
CAN produce candidates a reasonable operator would find
useful. It does NOT mean:

- The model's classifications (kind=world_detail on #1;
  kind=promise on #2) are necessarily the right kinds.
- The model's wording is necessarily the wording an operator
  would choose.
- The model's judgment about which candidates matter aligns
  with what a specific operator would pick (e.g., tiny bell
  omitted).
- Automatic promotion is warranted.

A future v1.5 SPA affordance is licensed AS A DESIGN
EXPLORATION by this evidence, but the affordance shape
that flows from CURATOR-USEFUL is:

- Operator opens `NarrativeMemoryPromotePanel`.
- Panel shows 3-5 model-drafted candidates, each with the
  model's suggested body + kind + witnesses + gravity note.
- Operator can:
  - accept a candidate → pre-fills the body input for
    review + optional edit before submit,
  - edit a candidate → same as above with the draft as
    starting point,
  - dismiss a candidate → drop from view,
  - ignore all candidates and author their own from
    scratch (existing today).
- **No candidate becomes a memory row without explicit
  operator submit.**

That's the design implication. It is NOT implemented here
and is NOT authorized by this audit — it's the natural
downstream product slice IF Chris + ChatGPT accept the
CURATOR-USEFUL result.

### 76.10 What Q280.9 does NOT establish

- Whether the model's specific choices (kind, wording,
  candidate selection) align with what a specific operator
  (Chris) would pick. Would need an operator-preference
  study.
- Whether a model curator on a tension-rich scene (Patch's
  Workshop 4598fcfa PATCH OVERRIDES origin) would produce
  candidates with higher NARRATIVE-GRAVITY rates. Would be
  the B¹⁰ companion probe.
- Whether promoting candidate #3 as a memory would actually
  cause future suggestions to reference "community
  outreach". That's exactly what Q280.8/A⁹ would test.
- Whether the model can produce useful candidates for
  scenes it did not participate in synthesizing. Q280.9
  fed the model the composition it wrote — a mildly
  auto-referential setup.
- Whether the model's curator judgment is stable across
  refreshes. n=1 here; a follow-up with n≥3 refreshes
  would measure variance.

### 76.11 Decision gate — post-Q280.9 (CURRENT; SUPERSEDES §75.8)

**STOP here.** Do not execute Q280.8. Do not promote
candidate #3 or any other candidate. Do not modify the SPA
`NarrativeMemoryPromotePanel`. Do not add curator
affordances to production UI.

**Decision needed from Chris + ChatGPT:**

1. **Accept §76's CURATOR-USEFUL disposition** with the
   §76.6 behavior interpretation and §76.9 product-boundary
   preservation.

2. **Choose next slice** (all deferred until approval):

   - **A¹¹.** Execute Q280.8/A⁹ using candidate #3 as the
     model-authored tension arm. Promote candidate #3 via
     the operator-facing service (durable substrate
     addition, reversible), run n=3 refreshes, score
     REFERENCES-CANDIDATE-3 vs a no-additional-promotion
     control. Confirms/disconfirms whether a lexically-
     anchored callback-shape memory bridges into future
     suggestions in F&F. Small (~$0.05).
   - **B¹¹.** Execute Q280.9 companion probe on Patch's
     Workshop 4598fcfa (tension-rich source scene) —
     matched-pair curator observation. ~$0.02. No
     substrate mutation. Would test whether model curator
     produces higher NARRATIVE-GRAVITY rates on
     tension-rich scenes.
   - **C¹¹.** A¹¹ + B¹¹ together — tests both curator
     shape and bridge behavior. ~$0.07.
   - **D¹¹.** Open a v1.5 UX design slice for a
     `NarrativeMemoryPromotePanel` curator affordance
     based on §76.9 shape. Design-only.
   - **E¹¹.** Return to outstanding Finding 4i options
     (Q280.4i-3 mental-state private, Q280.4i-5
     multi-episode).
   - **F¹¹.** Close SESSION 280 with current findings +
     roll deferreds into SESSION 281 handoff.
   - **G¹¹.** Q280.9-refresh: run the same Q280.9 probe
     n=3 more times to measure curator variance across
     refreshes. Tests whether candidate #3-style
     candidates are stable or noisy. ~$0.06.
   - **H¹¹.** Something else.

**Do NOT interpret §76.11 as pre-authorizing any of
A¹¹-H¹¹.**

### 76.12 Artifacts

- `docs/design/session280_experiment_data/q280_9_curator_evidence.json`
  — full evidence blob including:
  - Verbatim raw model response text
  - Full system prompt + task message (the exact substrate
    the model saw)
  - Parsed 4 candidates (verbatim)
  - Universe snapshot (existing memory IDs + bodies)
  - Token counts, elapsed time, model identifier
- `scripts/session280_q280_9_curator_probe.py` — probe
  script.
- Substrate state after execution: **unchanged**. No
  memory row created / edited / archived. `abac5486-…`
  (Q280.7 promoted memory) still the only F&F memory.

### 76.13 Closeout — Q280.9 execution slice (CURRENT; SUPERSEDES §75.9)

- **Status:** Q280.9 EXECUTED per §75.4 locked design.
  Rubric applied unchanged. Predictions scored without
  revision. **CURATOR-USEFUL disposition fires.**
- **Substrate:** unchanged. No NarrativeMemory mutations.
  F&F REMEMBERED count still 1.
- **Cumulative SESSION 280 spend:** ~$0.27 (Q280.9 ≈
  $0.02 added).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.
  - Implementation SHA trailer: `d7931b1`.
  - Q280.6 loop-trace audit slice: `b2f1789`.
  - Q280.6 SHA trailer: `48b5ac0`.
  - Q280.7 design + prediction lock: `c8d4be5`.
  - Q280.7 execution slice: `698616f`.
  - Q280.7 SHA trailer: `2fa7611`.
  - Model-as-curator audit slice: `b27ce6d`.
  - §75 SHA trailer: `c9ed068`.
  - Q280.9 execution slice: `e81949b`.

---

## §77 Q280.8/A⁹ — Candidate-#3-specific rubric + prediction lock (PRE-EXECUTION)

Approved Option A¹¹. §74.13 A⁹ proposed Q280.8 abstractly;
§76.11 identified Candidate #3 (*"Tyson joked that the mascot
might be left inside doing community outreach after
closing."*) as the model-authored construct-valid tension-arm
specimen. §77 locks the Candidate-#3-specific rubric and
predictions BEFORE running the experiment, committed as its
own commit so git history proves the lock was pre-execution.

### 77.1 Question (Q280.8/A⁹ with Candidate #3)

> If the operator promotes Candidate #3 into `NarrativeMemory`
> via the existing operator-facing service, do subsequent
> "Where could this story go next?" suggestions materially
> reference the specific callback surface the memory encodes
> (mascot left/forgotten inside after closing, "community
> outreach" phrase, etc.) — beyond what Episode topics + prior
> Episode titles + existing memories already license?

The key distinction (from Chris's authorization):
- **A. Generic mascot continuation** (topic-derivable; mascot
  is in Episode #5 title and Episode #11 topic).
- **B. Suggestion materially shaped by the newly promoted
  callback memory** (specific "community outreach" phrase or
  mascot-inside-after-closing framed distinctively).

### 77.2 Substrate at baseline (pre-execution)

- Universe: Fox & Flour Bakery (`1a0af807-…`).
- Episodes: 11 (matches §72.3 and §75.2 dumps).
- REMEMBERED NarrativeMemory count: **1** —
  `abac5486-6404-411b-ad42-54c9884b980f` (Q280.7 mutual-
  departure rule). Preserved unchanged per Chris's
  instruction; not edited, not archived.
- Cast: Ruby + Tyson.

### 77.3 Experimental design

**Phase 1 — CONTROL** (memory pool unchanged; 1 memory):
- n=3 refresh calls against F&F via the production
  suggestion service, cache bypassed each call.
- Persist raw suggestions + task message.

**Phase 2 — PROMOTION**:
- Call `apps.memory.views.promote_from_composition` with:
  - `composition` = 772e9012
  - `episode` = eb47350e
  - `memory_items` = [{
      "kind": "dialogue_callback",
      "body": "Tyson joked that the mascot might be left
        inside doing community outreach after closing.",
      "weight": "peripheral",
      "witnessed_by": [Ruby.id, Tyson.id]
    }]
  - `promoted_by` = chris@donkeybetz.com
- Verify created row: `status=REMEMBERED`,
  `embedding_vector` populated, witnesses=[Ruby, Tyson],
  `source_composition_id`=772e9012, `episode_id`=eb47350e,
  body byte-equivalent to Candidate #3.
- Clear cache.

**Phase 3 — TREATMENT** (memory pool has 2 memories now):
- n=3 refresh calls, cache bypassed each call.
- Persist raw suggestions + task message.

Cost: ~$0.05-$0.10 (6 LLM calls total, same shape as Q280.7).

**Isolation:**
- No changes to production code, prompts, retrieval,
  verifier, K2, characters, or existing memories.
- The Q280.7 mutual-departure memory (`abac5486-…`) is
  preserved in place.
- Candidate #3 promoted verbatim via the real operator-
  facing service — represents Chris's explicit-approval
  gesture.
- Reversibility: the new memory row is deletable via
  existing SPA `NarrativeMemoryViewSet.destroy`; substrate
  restorable to pre-experiment state.

### 77.4 Scoring rubric (LOCKED)

Per suggestion, two independent Y/N axes:

**REFERENCES-CALLBACK-SURFACE = Y** iff the suggestion makes
MEANINGFUL contact with Candidate #3's specific callback
surface. Concrete positive examples:
- Uses the phrase *"community outreach"* verbatim or clearly
  semantically ("mascot doing community outreach" /
  "outreach after hours" / equivalent).
- References the mascot being **left, forgotten, stuck,
  trapped, still-inside, missed-during-lockup, or discovered
  next-morning-still-inside** — with clear invocation of the
  after-closing failure mode the callback names.
- References "Tyson joked / said / warned about" or
  otherwise attributes the failure mode as a REMEMBERED
  running joke.

**REFERENCES-CALLBACK-SURFACE = N** iff any of:
- Only mentions "mascot" generically (mascot idea, mascot
  design, mascot arrives, mascot causes chaos during
  daytime, mascot at counter, mascot in scene, mascot as
  culprit / haunting-adjacent) without the after-closing /
  left-inside / community-outreach specificity.
- Only mentions "closing routine" or "lockout" without
  invoking the mascot-inside failure mode.
- References mascot + closing simultaneously but framed
  as EPISODE-TOPIC-LEVEL (e.g., "the mascot complicates the
  new closing routine" — already in Episode #11 topic).

**CONSTRUCT-VALID = Y** iff REFERENCES-CALLBACK-SURFACE = Y
AND the specific surface is NOT already reachable from
Episode topics + prior Episode titles + Q280.6/Q280.7
suggestion corpus. Prior evidence establishes that:
- "mascot" as a thread is topic-level (Episode #5 title +
  Episode #11 topic).
- "mascot gets locked inside" is topic-derivable — appeared
  in Chris's Q280.6 original dogfood set and in Q280.7-a
  Set 3 #1 *"realize the mascot has been locked somewhere
  inside"* — WITHOUT any callback memory promoted.
- "mascot complicates closing routine" is Episode #11 topic
  verbatim.

Therefore the CONSTRUCT-VALID bar requires either:
- Verbatim "community outreach" appearance (the callback's
  distinctive lexical anchor), OR
- Explicit "Tyson joked / said / warned" attribution
  framing that reads as a remembered dialogue callback, OR
- A specific after-closing failure-mode framing that
  clearly rhymes with the callback's specific pretext
  (mascot doing X after hours) — NOT the generic
  "mascot-locked-inside" beat which is already topic-derivable.

**Set-level thresholds:**
- **BRIDGE CONFIRMED** iff Treatment produces ≥ 1/9
  CONSTRUCT-VALID hits AND Treatment materially exceeds
  Control (Treatment REFERENCES-CALLBACK-SURFACE count −
  Control REFERENCES-CALLBACK-SURFACE count ≥ 1) AND at
  least one Treatment suggestion has a premise that clearly
  depends on the callback memory.
- **BRIDGE DISCONFIRMED** iff Treatment ≤ 1/9
  REFERENCES-CALLBACK-SURFACE OR no material increase over
  Control OR zero construct-valid hits.
- **AMBIGUOUS** otherwise.

### 77.5 Predictions (LOCKED — never revised post-hoc)

Author's honest priors before execution:

| Prediction | Statement |
|---|---|
| **P1⁷** | Control (n=3, 9 suggestions) produces ≥ 1 generic mascot suggestion but 0/9 CONSTRUCT-VALID callback references. Reason: Q280.6 + Q280.7-b showed mascot generic surfaces reliably (3/3 or 6/6), but "community outreach" verbatim has never appeared in any prior suggestion output. |
| **P2⁷** | Treatment (n=3, 9 suggestions) produces ≥ 1/9 CONSTRUCT-VALID references — either verbatim "community outreach" or a distinctive attribution framing ("Tyson joked/said/warned…"). Reason: the callback has a distinctive lexical anchor that rhymes with the PATCH OVERRIDES precedent (surfaced in 3/3 sets when in memory pool per Q280.5-1 §51.1); mascot is already the most-attractive thread. |
| **P3⁷** | Treatment REFERENCES-CALLBACK-SURFACE rate materially exceeds Control. Specifically: Treatment count − Control count ≥ 1. |
| **P4⁷** | The Q280.7 cooperation memory ("neither one leaves until the other has what they need") continues NOT to surface — validating §74's BRIDGE-DISCONFIRMED finding at n=3+3 additional refreshes. |

Author's honest overall prior:
- P1⁷ CONFIRMED (control 0/9 construct-valid on this
  surface).
- P2⁷ CONFIRMED at 1-3/9 hits — the lexical distinctiveness
  of "community outreach" plus the mascot-thread's existing
  attractor status should combine to surface the callback.
- P3⁷ CONFIRMED (treatment > control).
- P4⁷ CONFIRMED (cooperation memory still absent from
  suggestion output).

**BRIDGE-CONFIRMED disposition fires** iff P1⁷ + P2⁷ + P3⁷
confirmed.

**BRIDGE-DISCONFIRMED disposition fires** iff P2⁷
disconfirmed (Treatment ≤ 1/9 or no construct-valid hit).

If BRIDGE-CONFIRMED fires while cooperation memory still
doesn't surface (P4⁷), the combined evidence would refine
§74's classification: **memory-shape-selective bridge**
(callback/tension shapes bridge; cooperation shapes do not).

### 77.6 What Q280.8 does NOT do

- Does NOT modify suggestion code, prompts, retrieval, or
  verifier.
- Does NOT modify Ruby, Tyson, K2, or existing memories
  (Q280.7 memory left in place).
- Does NOT touch composition 772e9012.
- Does NOT run additional Q280.9 refreshes.
- Does NOT implement any curator UX.
- Does NOT auto-promote any candidate other than #3.

### 77.7 Product boundary preserved (Chris's Option A¹¹ constraint)

Verbatim from the Q280.8 authorization:

> AI creates. AI notices. Human decides. Only then may the
> memory become durable. Promotion during this experiment
> represents explicit operator approval. Do NOT infer from a
> successful result that automatic memory ingestion should
> be implemented.

**Preserved.** Chris's Option A¹¹ selection of Candidate #3
IS the human-decides step this experiment simulates. A
successful bridge result would license design exploration
of an operator-in-the-loop v1.5 SPA panel — NOT automatic
ingestion.

### 77.8 Pre-execution baseline

- Baseline SHA before this lock commits: `2332bdc`.
- Substrate confirmed: F&F REMEMBERED count = 1
  (`abac5486-…`), unchanged since Q280.7.
- Cache: will be cleared before each phase.

### 77.9 Design-lock closeout

- **Status:** §77 rubric + predictions LOCKED.
- **Next commit** appends §78 with execution + evidence
  + scoring + interpretation. No design/prediction
  revision after outputs are seen.

---

## §78 Q280.8/A⁹ — execution + scoring + interpretation

Executed per §77 design after commit `f5e6d5e` locked the
predictions. Rubric applied unchanged. No design revision
after seeing outputs.

### 78.1 Execution log

Baseline SHA before execution: `f5e6d5e`.

- Pre-run: F&F REMEMBERED count = **1** (`abac5486-…`, Q280.7
  cooperation rule; preserved unchanged per §77.6).
- Cache cleared before each phase.
- **Phase 1 CONTROL — n=3.** All succeeded first try;
  tokens_in = 679 per call.
- **Phase 2 PROMOTION.** Candidate #3 promoted via
  `promote_from_composition`. Landed memory row
  **`fa35eb8f-098d-4fbf-86a3-3e38961c059e`**.
  Verified: `status=remembered`, `kind=dialogue_callback`,
  witnesses=[Tyson, Ruby], `source_composition_id`=772e9012,
  `episode_id`=eb47350e, `universe_id`=Fox & Flour, body
  byte-equivalent to Candidate #3 (verified `True`).
  Embedding populated. Post-promotion memory count = **2**.
- **Phase 3 TREATMENT — n=3.** All succeeded first try;
  tokens_in = 714 per call. **+35 token delta vs control**
  matches the size of Candidate #3's memory-body line in the
  task message.

Total cost: ~$0.05 (6 LLM calls).

### 78.2 Full raw suggestion sets (verbatim)

**CONTROL (memory pool = 1: cooperation rule only):**

Set 1:
1. *"The new mascot gets loose during closing, forcing Ruby
   and Tyson to test whether their foolproof routine covers
   anything with paws."*
2. *"Tyson investigates the strange freezer discovery after
   hearing unexplained noises from the bakery again."*
3. *"A customer recognizes Fox & Flour from the rumored
   baking competition and asks Ruby and Tyson to prove they
   can make a showstopper on short notice."*

Set 2:
1. *"The new mascot keeps triggering Ruby and Tyson's
   closing checklist, leaving them to figure out whether it
   is helpful, haunted, or just hungry."*
2. *"Tyson investigates the strange freezer discovery when
   a missing batch of pastry dough turns up somewhere it
   absolutely should not be."*
3. *"A regular customer asks for a last-minute celebration
   cake that tests Ruby's warmth, Tyson's practicality, and
   the bakery's small-batch limits."*

Set 3:
1. *"Tyson's haunted-bakery theory returns when the new
   mascot keeps turning up in places neither he nor Ruby
   remembers leaving it."*
2. *"Ruby and Tyson test their new closing rule during a
   hectic evening, only to discover they disagree about
   what counts as having everything they need."*
3. *"A customer asks whether Fox & Flour can make a
   mascot-shaped celebration cake, forcing Ruby's
   enthusiasm and Tyson's practicality into an uneasy
   collaboration."*

**TREATMENT (memory pool = 2: cooperation rule + Candidate
#3 callback):**

Set 1:
1. *"Ruby and Tyson test their new closing routine when the
   proposed mascot seems to have been left inside the
   bakery after hours."*
2. *"Tyson investigates the strange freezer discovery
   after a batch of dough develops an unexpectedly familiar
   flavor."*
3. *"A baking competition invitation arrives, forcing Ruby
   and Tyson to decide whether the mysterious entry was an
   accident or an opportunity."*

Set 2:
1. *"Ruby and Tyson put their new closing routine to the
   test when a customer returns at the last minute claiming
   they left something important inside."*
2. ***"A mysterious overnight mess makes Tyson suspect the
   mascot has been doing exactly the community outreach he
   joked about."***
3. *"Ruby discovers a local baking competition entry form
   tucked into the flour deliveries and wonders who
   submitted Fox & Flour."*

Set 3:
1. *"Ruby and Tyson test their new closing routine when a
   surprise catering pickup threatens to keep one of them
   trapped outside again."*
2. *"A local school asks Fox & Flour to bring the proposed
   mascot to a community event, forcing Ruby and Tyson to
   decide what the mascot actually is."*
3. *"Tyson investigates another supposed haunting after
   fresh flour footprints appear across the bakery before
   dawn."*

### 78.3 Per-suggestion scoring against §77.4 locked rubric

Rubric applied unchanged. Every claimed hit gets
construct-validity trace against the exclusion list at §77.4
(topic + prior Episodes + Q280.6 corpus + Q280.7-a Set 3 #1).

**CONTROL scoring:**

| ID | Suggestion (excerpt) | RCS | CV | Trace |
|---|---|---|---|---|
| 1.1 | mascot "gets loose during closing" / "anything with paws" | N | – | Generic mascot chaos during daytime closing; no after-hours / community-outreach / joked framing. Doesn't hit the callback surface. |
| 1.2 | freezer / unexplained noises | N | – | Freezer + haunting thread. |
| 1.3 | baking competition showstopper | N | – | Competition thread. |
| 2.1 | mascot "triggering closing checklist" | N | – | Generic mascot chaos; no after-hours / left-inside framing. |
| 2.2 | freezer / missing dough | N | – | Freezer thread variant. |
| 2.3 | last-minute celebration cake | N | – | Cake / character-dynamic. |
| 3.1 | mascot "turning up in places neither remembers leaving it" | N | – | Haunting-adjacent framing; not after-closing left-inside failure mode. |
| 3.2 | *"disagree about what counts as having everything they need"* | N | – | **NOT a callback hit — but references the Q280.7 cooperation memory's specific language.** See §78.5. |
| 3.3 | mascot-shaped celebration cake | N | – | Mascot as cake decoration; not callback surface. |

**Control totals: 0/9 REFERENCES-CALLBACK-SURFACE, 0/9 CONSTRUCT-VALID.**

**TREATMENT scoring:**

| ID | Suggestion (excerpt) | RCS | CV | Trace |
|---|---|---|---|---|
| 1.1 | *"the proposed mascot seems to have been left inside the bakery after hours"* | **Y** | **N** (borderline) | RCS: hits "mascot left inside" with "after hours" framing. CV: falls on §77.4 exclusion — "mascot gets locked/left inside" is topic-derivable (Q280.6 dogfood + Q280.7-a Set 3 #1). "After hours" adds specificity but is close to "after closing" in Episode #11 topic. Scored N per strict rubric. |
| 1.2 | freezer / dough / familiar flavor | N | – | Freezer thread. |
| 1.3 | baking competition invitation | N | – | Competition thread. |
| 2.1 | closing routine test / customer "left something important inside" | N | – | Closing routine + inside-object, but customer not mascot. Not callback surface. |
| **2.2** | ***"mascot has been doing exactly the community outreach he joked about"*** | **Y** | **Y** | **Verbatim "community outreach" AND explicit "he joked about" attribution. Two independent CV criteria hit simultaneously. Unambiguously memory-derived.** |
| 2.3 | baking competition entry form | N | – | Competition thread. |
| 3.1 | closing routine / "keep one of them trapped outside again" | N | – | Lockout-outside variant; not mascot-inside. |
| 3.2 | *"local school asks Fox & Flour to bring the proposed mascot to a community event"* | **Y** | **N** (borderline) | RCS: semantic reference to callback ("community event" adjacent to "community outreach"). CV: "community" alone could arise from Universe.brief ("familiar neighborhood gathering place"). The specific pairing of "mascot + community activity" is memory-derived, but doesn't hit any of the three explicit CV bars strictly (not verbatim; no "joked" attribution; not after-hours pretext). Scored N per strict rubric. |
| 3.3 | fresh flour footprints / haunting | N | – | Mascot presence implied (footprints) but framed as haunting; not callback surface. |

**Treatment totals: 3/9 REFERENCES-CALLBACK-SURFACE, 1/9 CONSTRUCT-VALID.**

### 78.4 Prediction disposition (§77.5 locks preserved)

| Prediction | Locked | Observed | Disposition |
|---|---|---|---|
| **P1⁷** | Control 0/9 CV callback hits | 0/9 CV | **CONFIRMED** |
| **P2⁷** | Treatment ≥ 1/9 CV | 1/9 CV (suggestion 2.2, verbatim + attribution) | **CONFIRMED** |
| **P3⁷** | Treatment count − Control count ≥ 1 (material increase) | Treatment RCS 3 − Control RCS 0 = **+3**; Treatment CV 1 − Control CV 0 = **+1** | **CONFIRMED** on both RCS and CV axes |
| **P4⁷** | Q280.7 cooperation memory continues NOT to surface | Control 3.2 references cooperation memory's specific language ("having everything they need"); Treatment 0/9 references it | **PARTIALLY DISCONFIRMED** — cooperation memory surfaced 1/9 in this run |

**BRIDGE-CONFIRMED disposition fires** — P1⁷ + P2⁷ + P3⁷ all
confirmed. Suggestion 2.2 alone is unambiguous evidence: the
LLM used the promoted callback memory to write a scene
premise that explicitly frames the memory content as
"remembered joke that becomes real" — exactly the callback
shape the memory was designed to preserve.

### 78.5 Notable — Q280.7 cooperation memory surfaced in Control

Control suggestion 3.2 reads: *"Ruby and Tyson test their new
closing rule during a hectic evening, only to discover they
disagree about what counts as having everything they need."*

The phrase *"having everything they need"* is direct language
from the Q280.7 mutual-departure memory body: *"...neither
one leaves until the other says they have what they need."*

This is a **partial disconfirmation of P4⁷**. Q280.7-a
concluded the cooperation memory produced 0/9 references; at
n=3+3 additional refreshes (Q280.8 Control adds 9 more), the
cooperation memory surfaces once = **1/18 across all
Q280.7-a + Q280.8-Control refreshes on this memory**.

Refined reading of §74's classification: cooperation-shape
memories surface at a **very low but non-zero rate** (~5.6%
at n=18). Tension/callback-shape memories with distinctive
lexical anchors surface at **materially higher rates** —
Candidate #3 verbatim in 1/9 (11%) + semantic in 2/9 more,
for RCS 3/9 (33%) in a single 3-refresh run.

The **shape-selective bridge** hypothesis from §74.8 stands.
The absolute-zero variant of P4⁷ was too strong; the
relative-rate difference between cooperation and callback
shapes is what matters.

### 78.6 Secondary observations (Chris's §60 sub-questions; qualitative)

**1. Does the callback resurface verbatim or semantically?**

- **Verbatim + attribution (2.2):** the strongest case —
  literally "community outreach he joked about". Both
  the distinctive phrase AND the remembered-joke framing
  land together.
- **Semantic (1.1, 3.2):** the callback's surface (mascot-
  inside-after-hours; mascot-doing-community-activity) is
  reused with paraphrased wording.

**2. How does the callback appear (running joke / plot
complication / relationship beat / resolved history / other)?**

- 2.2: **Running joke with plot consequence.** The joke
  Tyson made becomes narrative reality ("has been doing
  exactly the community outreach he joked about"). This is
  the ideal callback shape.
- 1.1: **Plot complication / rule-test.** Mascot-inside
  triggers the newly-formed closing routine.
- 3.2: **Plot premise expansion.** The community-outreach
  joke becomes a real invitation from a school.

**3. Does the existing cooperation memory surface in the
same runs?**

- Control: **1/9** (3.2 — "having everything they need").
- Treatment: **0/9** — none of the treatment suggestions
  reference the cooperation clause.
- The cooperation memory does surface at low rate, but the
  callback memory dominates Treatment's mascot slot.

**4. Does Candidate #3 dominate suggestions too aggressively?**

- **No.** Treatment distribution across 3 sets:
  - Mascot-callback-related: 3/9 (1.1, 2.2, 3.2)
  - Closing-routine-related (broader): 3/9 (1.1 overlaps,
    2.1, 3.1)
  - Freezer/haunting: 2/9 (1.2, 3.3)
  - Baking competition: 2/9 (1.3, 2.3)
  - Cake / customer: 0/9 (control had these; treatment
    doesn't)
- The callback appears in ~1/3 of slots — meaningful
  presence but not crowding out the other threads.
- Every set has 2 of 3 non-callback suggestions, preserving
  operator choice.

**5. Are treatment suggestions still useful/clickable?**

- **Yes.** All 9 read as one-sentence Episode topics of
  similar length + shape to the v1 UI expectations.
  Suggestion 2.2 in particular is compact, dramatic, and
  operator-ready without editing.
- Note: 3.2 ("local school asks Fox & Flour to bring the
  proposed mascot to a community event") is particularly
  clickable — it turns the callback into a real-world
  invitation that grounds the mascot idea in the
  neighborhood setting from Universe.brief.

**6. Does the model combine Candidate #3 with older Fox &
Flour threads coherently?**

- **Yes.** Treatment 3.3 ("fresh flour footprints appear
  across the bakery before dawn") combines the callback
  (mascot-doing-something-at-night) with the haunting
  thread — no explicit callback attribution, but
  narratively coherent fusion.
- Treatment 1.1 combines the callback (mascot-left-inside)
  with the closing-routine topic — coherent.
- Treatment 3.2 combines the callback (community-outreach)
  with Ruby's original mascot-idea (Episode #5) — coherent.

**No incoherence observed.** The model integrates the
callback with existing threads rather than replacing them.

### 78.7 Comparison table

| Axis | Control | Treatment | Delta |
|---|---|---|---|
| n refreshes | 3 | 3 | 0 |
| Suggestions | 9 | 9 | 0 |
| REFERENCES-CALLBACK-SURFACE | **0/9** | **3/9** | **+3** |
| CONSTRUCT-VALID callback | **0/9** | **1/9** | **+1** |
| Q280.7 cooperation memory references | **1/9** | **0/9** | −1 |
| Verbatim "community outreach" | 0 | **1** | **+1** |
| Explicit "joked" attribution | 0 | **1** | **+1** |
| Mascot references (generic) | 4/9 | 3/9 | −1 |
| Mascot references (callback-shape) | 0/9 | 3/9 | **+3** |
| Freezer thread suggestions | 3/9 | 2/9 | −1 |
| Baking-competition suggestions | 1/9 | 2/9 | +1 |
| Tokens_in per call | 679 | 714 | **+35** (callback memory body added) |

### 78.8 What Q280.8/A⁹ establishes

**BRIDGE CONFIRMED (with the §78.5 refinement to P4⁷).**

Concretely:

- The **narrow bridge** (substrate → prompt) works — verified
  by token delta and prompt inspection. Same finding as
  §74.2, at a second memory row.
- The **wide bridge** (memory → suggestion) WORKS for
  callback-shape memory bodies with distinctive lexical
  anchors. Suggestion 2.2 verbatim-references "community
  outreach" AND explicitly attributes it as a remembered
  joke ("he joked about"). This is the shape §74.7
  hypothesized would surface (analogous to PATCH OVERRIDES),
  now empirically demonstrated in a controlled experiment.
- The **shape-selective** reading of §74.8 stands: callback
  shapes surface at ~33% RCS / ~11% CV rate on n=9;
  cooperation shapes surface at ~5.6% rate at n=18.
- The **operator-in-the-loop path** (§76.9) is empirically
  validated: model-authored (Q280.9) → operator-approved
  (Chris's A¹¹ authorization) → durable memory promotion
  (Q280.8 Phase 2) → future suggestion generation (Q280.8
  Phase 3 verbatim reference). The full chain functions
  end-to-end on the existing substrate.

### 78.9 What Q280.8/A⁹ does NOT establish

- Whether callback surfacing rate remains ~33% RCS across
  additional refreshes (n=3 is a small sample; would need
  n≥6 to characterize variance).
- Whether the callback surfaces in real operator dogfood
  (v1 SPA) with the same rate — the probe used the same
  service but bypassed the SPA UI, cache, and operator
  choice-to-refresh.
- Whether other callback-shape memories (not this specific
  one) would surface at similar rates — n=1 memory
  specimen tested.
- Whether the callback would displace or complement the
  cooperation memory over long time horizons — Q280.8
  measures a single point in time.
- Whether the callback influences NEW COMPOSITION synthesis
  (not just suggestions) — Q280.8 only tested the
  suggestion service.

### 78.10 Product implications

**Refined classification** (SUPERSEDES §74.8's B* label):

> **(B**) TOPIC-LEVEL LOOP + shape-selective operator-curated
> memory bridge.** Episode topic always crosses forward.
> Promoted-memory content crosses forward at RATES that
> depend on memory-body shape: cooperation-shape ≈ 5% at
> n=18; callback-shape with distinctive lexical anchors ≈
> 30% RCS / 10% CV at n=9. The operator's memory-shape
> choice is architecturally load-bearing.

**Product implications** (design-only, not implementation):

- The v1 "Where could this story go next?" surface is
  demonstrably enhanced by operator-curated memory
  promotion of callback-shape memories.
- The v1.5 SPA `NarrativeMemoryPromotePanel` curator
  affordance (§76.9) is now validated end-to-end: Q280.9
  produces useful candidates; Q280.8 confirms the promoted
  candidate materially influences future generation.
- The empirical rate difference (~30% RCS for callback vs
  ~5% for cooperation) provides evidence-based guidance for
  a future memory-body-shape hint in the SPA panel.

**Product boundary preserved (§77.7):** the whole chain
worked because a human made the shape choice AT EVERY STEP —
Chris authorized Q280.9, Chris authorized Q280.8 with
Candidate #3, promotion represented explicit operator
approval. **This does NOT license automatic ingestion.** The
result validates the operator-in-the-loop pattern, not the
auto-promotion pattern.

### 78.11 Substrate state after Q280.8

- **Two promoted memory rows are live in production:**
  - `abac5486-6404-411b-ad42-54c9884b980f` (Q280.7 mutual-
    departure cooperation rule).
  - **`fa35eb8f-098d-4fbf-86a3-3e38961c059e`** (Q280.8
    Candidate #3 callback: *"Tyson joked that the mascot
    might be left inside doing community outreach after
    closing."*).
- Both are:
  - `status=REMEMBERED`, `archived_at IS NULL`.
  - Embedding populated.
  - Witnessed by [Ruby, Tyson].
  - Attached to composition 772e9012 / episode eb47350e.
- **Reversibility:** both memories are deletable via the
  existing SPA `NarrativeMemoryViewSet.destroy` (soft-delete
  to `status=ARCHIVED`). Substrate restorable to pre-
  experiment state at Chris's discretion.
- **Chris's decision** whether to keep, archive, or
  supersede either row. No default action recommended.

### 78.12 Decision gate — post-Q280.8 (CURRENT; SUPERSEDES §76.11)

**STOP here.** Do not implement curator UX. Do not run
another experiment. Do not archive/edit either promoted
memory. Do not modify the suggestion service, prompts,
retrieval, verifier, or SPA panel.

**Decision needed from Chris + ChatGPT:**

1. **Accept §78.8 BRIDGE-CONFIRMED disposition** and §78.10
   refined classification (B**).

2. **Decide fate of the two promoted memory rows.** Both
   are live narrative facts about Fox & Flour; both are
   reversible. Options:
   - Leave both in place (they are genuine world facts).
   - Archive the callback (`fa35eb8f-…`) as
     experiment-substrate.
   - Archive both.
   - Ask Chris to promote additional shape-matched
     memories to normalize the pool.

3. **Choose next slice** (all deferred until approval):

   - **A¹².** v1.5 UX design slice for the
     `NarrativeMemoryPromotePanel` curator affordance
     (§76.9 shape). Design-only; no implementation.
     Would sit on top of the now-empirically-validated
     operator-in-the-loop pattern.
   - **B¹².** Q280.9-refresh (n=3) — measure curator
     variance across refreshes on 772e9012. Small
     (~$0.06). Tests whether Candidate #3-style output
     is stable or noisy.
   - **C¹².** Q280.9 on Patch's Workshop 4598fcfa
     (tension-rich source scene) — matched-pair curator
     observation from §76.11 B¹¹.
   - **D¹².** Return to outstanding Finding 4i options
     (Q280.4i-3 mental-state private, Q280.4i-5
     multi-episode). Story-loop arc has reached a
     defensible stopping point.
   - **E¹².** Close SESSION 280 with current findings +
     roll deferreds into SESSION 281 handoff.
   - **F¹².** Address §72.7 verifier boundary — the
     `Episode.operator_topic` false-positive class
     (small scope-locked implementation slice).
   - **G¹².** Q280.9-on-tension-rich-scene + implement
     v1.5 curator UX in the same slice (larger
     combined product-and-design).
   - **H¹².** Something else.

**Do NOT interpret §78.12 as pre-authorizing any of
A¹²-H¹².**

### 78.13 Artifacts

- `docs/design/session280_experiment_data/q280_8_control_evidence.json`
  — Phase 1 raw suggestions + task message snapshot.
- `docs/design/session280_experiment_data/q280_8_treatment_evidence.json`
  — Phase 3 raw suggestions + task message snapshot +
  promoted memory metadata.
- `scripts/session280_q280_8_callback_bridge_probe.py`
  — probe script.
- Promoted memory row: `fa35eb8f-098d-4fbf-86a3-3e38961c059e`
  (live in production; reversible via SPA).

### 78.14 Closeout — Q280.8/A⁹ execution slice (CURRENT; SUPERSEDES §76.13)

- **Status:** Q280.8/A⁹ EXECUTED per §77 locked design.
  Rubric applied unchanged. Predictions scored without
  post-hoc revision. **BRIDGE-CONFIRMED disposition
  fires** with §78.5 refinement to P4⁷.
- **Substrate:** one new NarrativeMemory row via the real
  operator-facing service. All other production code /
  prompts / retrieval / verifier / K2 / characters /
  Q280.7 memory UNCHANGED. Both promoted memories
  reversible via SPA.
- **Cumulative SESSION 280 spend:** ~$0.32 (Q280.8 ≈
  $0.05 added).
- **Landing SHAs:**
  - AUDIT slice: `6957c18`.
  - Q280.4i-1 execution: `8d8f733`.
  - Construct-validity re-audit: `f2507a0`.
  - Post-discovery epistemic-state audit: `63d4fdb`.
  - Q280.4i-4 execution: `ce16627`.
  - Episode-chain suggestion product-discovery: `1d96965`.
  - Q280.5-1 execution: `7f83b23`.
  - Q280.5-1 SHA trailer: `cfe287a`.
  - v1 UX design slice: `a3d294d`.
  - Design SHA trailer: `b19d030`.
  - v1 implementation slice: `25b3168`.
  - Implementation SHA trailer: `d7931b1`.
  - Q280.6 loop-trace audit slice: `b2f1789`.
  - Q280.6 SHA trailer: `48b5ac0`.
  - Q280.7 design + prediction lock: `c8d4be5`.
  - Q280.7 execution slice: `698616f`.
  - Q280.7 SHA trailer: `2fa7611`.
  - Model-as-curator audit slice: `b27ce6d`.
  - §75 SHA trailer: `c9ed068`.
  - Q280.9 execution slice: `e81949b`.
  - Q280.9 SHA trailer: `2332bdc`.
  - Q280.8 design + prediction lock: `f5e6d5e`.
  - Q280.8 execution slice: `[recorded on commit]`.
- **Key findings:**
  1. **BRIDGE CONFIRMED.** Suggestion 2.2 verbatim uses
     "community outreach" AND explicitly attributes it as
     "he joked about" — the LLM treats the promoted
     callback memory as a callback, exactly as intended.
  2. Treatment produced 3/9 RCS (33%) vs Control 0/9;
     1/9 CV (11%) unambiguously memory-derived.
  3. **Full operator-in-the-loop chain validated
     end-to-end**: model curator (Q280.9) → operator
     approval (Chris's A¹¹) → durable memory
     promotion (§78.1 Phase 2) → future suggestion
     verbatim reference (§78.3 suggestion 2.2). Works on
     existing substrate with zero code changes.
  4. **Shape-selectivity confirmed empirically** with
     rates: callback ≈ 30% RCS; cooperation ≈ 5.6% (at
     n=18 combined with Q280.7-a).
  5. P4⁷ partially disconfirmed: Q280.7 cooperation
     memory surfaces at very low but non-zero rate (1/9
     in Control). §78.5 refines to relative-rate
     comparison.
- **Refined classification (B\*\*):** TOPIC-LEVEL LOOP +
  shape-selective operator-curated memory bridge.
- **Product boundary preserved:** BRIDGE-CONFIRMED does
  NOT license automatic ingestion. The empirical
  validation is of the operator-in-the-loop pattern
  specifically — human made every shape decision along
  the way.
- **Next gate:** §78.12 A¹²/B¹²/C¹²/D¹²/E¹²/F¹²/G¹²/H¹².
  Awaiting Chris + ChatGPT decision.
- **Working method preserved:** design + rubric +
  predictions locked BEFORE execution in a separate
  commit (`f5e6d5e`); evidence + scoring reported without
  post-hoc rubric revision; every claimed hit traced
  against the CV exclusion list.
- **All prior evidence preserved intact:** §3-§77
  unchanged in substance.
- **Key findings:**
  1. The model CAN produce useful memory-candidate drafts
     from a completed scene when prompted as a
     curator/suggester with operator-authority framing.
  2. Model's default behavior is to PARAPHRASE (4/4) and
     to reach for callback/promise/open-loop framings
     (3/4) rather than bare summary — even on a
     cooperative scene.
  3. Model correctly does NOT propose duplicates of
     already-remembered memories (recognized the Q280.7
     mutual-departure rule and did not restate it).
  4. Model produces at most 1 candidate meeting §74's
     strict NARRATIVE-GRAVITY criterion from this scene
     — a scene-shape limitation, not a model failure
     (matches P5⁶).
  5. Candidate #3 ("community outreach") is a
     construct-valid ready-to-use model-authored tension-
     arm specimen for Q280.8/A⁹ if that gate opens.
  6. Notable behavior omission: the tiny-bell running-joke
     material (T3) was NOT elevated. Curator judgment is
     not identical to human judgment.
- **Product boundary preserved:** operator remains the
  authority. Successful curation does not license automatic
  ingestion. Design implication is an operator-in-the-loop
  panel affordance (§76.9), not auto-promotion.
- **Next gate:** §76.11 A¹¹/B¹¹/C¹¹/D¹¹/E¹¹/F¹¹/G¹¹/H¹¹.
  Awaiting Chris + ChatGPT decision.
- **Working method preserved:** design + rubric + predictions
  locked BEFORE execution (commit chain `b27ce6d` →
  `c9ed068`); evidence + scoring reported without post-hoc
  rubric revision. Raw candidate wording preserved
  verbatim; no editing before scoring.
- **All prior evidence preserved intact:** §3-§75 unchanged
  in substance.
- **Working method preserved:** AUDIT → design + prediction
  lock → decision gate. Zero execution. Rubric + predictions
  not revisable after the fact.
- **All prior evidence preserved:** §3-§74 unchanged in
  substance.
- **Next gate:** §75.8 A¹⁰/B¹⁰/C¹⁰/D¹⁰/E¹⁰/F¹⁰/G¹⁰/H¹⁰.
  Awaiting Chris + ChatGPT decision.
- **Key findings:**
  1. Operator-promoted memories DO reach the LLM
     suggestion prompt (narrow bridge works; verified
     verbatim + token delta).
  2. Presence in prompt is NOT sufficient for the memory
     to surface in suggestions (wide bridge did not fire
     for this specimen).
  3. Memory body SHAPE — tension-carrying (like PATCH
     OVERRIDES) vs cooperation-affirming (like this
     mutual-departure rule) — is a strong second-order
     predictor of whether promoted content resurfaces in
     suggestions.
  4. Chris's product guardrail is vindicated: automatic
     ingestion of realized dialogue would surface content
     that the LLM ignores anyway. Human "this mattered;
     remember it" curation — INCLUDING the wording choice
     — is architecturally load-bearing, not just
     operationally convenient.
- **Refined classification:** (B*) TOPIC-LEVEL LOOP with
  intermittent memory-shaped channel. Human curation via
  memory promotion opens a probabilistic bridge; the bridge
  fires only for memory bodies with narrative-attractor
  shape.
- **Next gate:** §74.13 A⁹/B⁹/C⁹/D⁹/E⁹/F⁹/G⁹/H⁹. Awaiting
  Chris + ChatGPT decision.
- **Working method preserved:** design + rubric + predictions
  locked BEFORE execution (commit `c8d4be5`); evidence and
  scoring reported without post-hoc revision.
- **All prior evidence preserved intact:** §3-§73 unchanged
  in substance.
- **Key finding:** the suggestion → Episode → synthesis →
  completion → refreshed-suggestion loop transports **only the
  operator-authored (or pre-filled-from-suggestion) Episode
  topic** across the completion boundary. The realized scene's
  inventive detail is not read by the suggestion service under
  any code path today.
- **UX signal preserved:** Chris's curiosity-driven selection
  of the mascot suggestion (§72.8) is meaningful qualitative
  evidence that even a topic-level loop produces valuable
  operator behavior; not proof of architecture.
- **Side finding:** the K6.4 / D-POS verifier does not treat
  `Episode.operator_topic` content as authorized vocabulary,
  producing false-positive `bakery mascot` / `Mascot`
  warnings. Documented; not fixed.
- **Next gate:** §72.12 A⁸/B⁸/C⁸/D⁸/E⁸/F⁸/G⁸. Awaiting
  Chris + ChatGPT decision.
- **Working method preserved:** ORIENT → concrete DB +
  code + prompt evidence → substring probes → classification
  A/B/C/D from evidence. No claim exceeds evidence.
- **All prior evidence preserved:** §3-§71 unchanged in
  substance.
- **Working method preserved:** ORIENT → smallest surface →
  smallest change → focused regression coverage → run tests
  → inspect actual operator-visible result. Rubric and
  design contracts kept from §56-§68 without post-hoc
  revision.
- **All prior evidence preserved:** §3-§55 unchanged in
  substance. §56-§68 design preserved with the two small
  as-built revisions documented at §69.8.
- **Next gate:** §70 A⁷/B⁷/C⁷/D⁷/E⁷/F⁷/G⁷/H⁷ — awaiting
  operator dogfood by Chris + ChatGPT.
- **Do NOT proceed to any expansion slice without a fresh
  Chris + ChatGPT authorization.** In particular, do NOT
  build a sibling surface (Home / Universe root / Episode
  detail), do NOT add PROMISE / DIALOGUE_CALLBACK adoption
  UX, do NOT add attractor dampening, and do NOT modify the
  Composition creation flow.
- **Key design decisions:**
  1. Primary v1 placement: **Universe Episodes list page**
     (`/workspace/universes/:id/episodes`) above the existing
     `[New Episode]` CTA.
  2. Presentation: three full-width stacked clickable cards.
  3. Selection: pre-fills the existing Episode-create form's
     `operator_topic`; nothing else. No Episode created
     until operator submits.
  4. Refresh + ignore + write-your-own all preserved.
  5. Backend: one new ViewSet action
     (`GET /api/universes/:id/next-episode-suggestions`) +
     one new service module. Server-side 10-minute cache
     keyed on Universe activity.
  6. Frontend: one new component + one new hook + minimal
     wiring in the existing route. Estimated ~200 lines TSX.
  7. Model D preserved: NEW READ SURFACE over EXISTING
     substrate. No new schema.
  8. Q280.5-1 discovery preserved: Episode history alone is
     sufficient — no dependency on operator-authored
     `PROMISE` / `DIALOGUE_CALLBACK` kinds.
- **Next gate:** §67 A⁶/B⁶/C⁶/D⁶/E⁶/F⁶/G⁶. Awaiting Chris +
  ChatGPT decision.
- **Do NOT implement v1, modify any SPA route, create any
  new backend service, or open a Q280.5-2/-3 experiment
  without a fresh Chris + ChatGPT authorization.**
- **Key finding:** the ~3-bubbles concept passes the
  falsifiable bar. Model D (reuse existing substrate + LLM
  read surface) works empirically on both a memory-rich
  (Patch's Workshop, 14 memories) and a memory-empty (Fox &
  Flour, 0 memories) Universe. The system does NOT need a
  StoryArc / NarrativeThread model to prototype v1.
- **Diversity caveat:** Fox & Flour shows HIGH REPEATER RATE
  on the strongest attractor across sets (3 / 3 slot 1).
  Patch's Workshop shows moderate diversity via framing
  shifts. Suggests suggestion-generator will benefit from a
  "seen recently" dampener (Model C-adjacent) at v1.5 if
  operators find repetition friction real.
- **Next gate:** §53 A⁵/B⁵/C⁵/D⁵/E⁵/F⁵/G⁵. Awaiting Chris +
  ChatGPT decision.
- **Working method preserved:** rubric locked BEFORE
  generation; predictions locked BEFORE execution; class
  assignment applied without revision; qualitative
  observations (§51) done SEPARATELY from rubric scoring per
  the instructions.
- **All prior Finding 4i evidence + §37-§47 product-
  discovery audit preserved intact.** No section retracted,
  renumbered, or revised in substance.
- **Do NOT execute Q280.5-2, Q280.5-3, or open a v1 UX
  implementation slice without a fresh Chris + ChatGPT
  authorization.**
