# SESSION 268 — Patch's Workshop Dogfood (durable working doc)

Started: 2026-08-18. Primary objective: **normal creator
dogfood** of Patch's Workshop with the shipped narrative-memory
availability-condition UI. Not another artificial memory
experiment. Watch for what emerges as memory pool grows.

Working method (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Persist findings, dogfood observations, runtime evidence,
decisions, and open questions in this file. Runtime evidence
sidecars go under `docs/design/session_268_experiment_data/`
when the session opens a fresh capture.

---

## §1 — Audit / orient pass

### §1.1 Repository state

- Branch: `main`, clean tree.
- HEAD: `c284285 docs: SESSION 267 close-out — witness UI relabel + SESSION 268 handoff`.
- No SESSION 267 work in flight; handoff at
  `docs/design/SESSION_268_HANDOFF.md` matches HEAD.

### §1.2 Runtime intact vs SESSION 267 close

Verified 2026-08-18 during orient pass:

| Component | Location | State |
|---|---|---|
| Narrative memory retrieval | `shell/apps/embeddings/retrieval.py:439-543` | Unchanged. `top_k: int = 1` (line 444). Predicate: `workspace ∧ universe ∧ status=REMEMBERED ∧ ¬archived ∧ embedding_vector NOT NULL ∧ (witnessed_by empty ∨ witnessed_by ∩ cast ≠ ∅)`. Two-arm union in place to skirt the ORM annotation-on-chained-M2M bug. |
| Synthesis wiring | `shell/character_os/dialogue_synthesis.py:1490,1513,1531-1536` | Unchanged. `retrieve_universe_memory(..., top_k=1)`. |
| UI copy — promote form | `web/src/components/narrative-memory-panels.tsx:216,232,245,149` | Shipped copy live. Legend "When should this memory be available?" / Radio A "In any future scene" / Radio B "When any of these characters are present…" / Error message references Radio A label. |
| UI copy — read-only rows | `web/src/components/narrative-memory-panels.tsx:484,497,626,637` | Shipped. `formatWitnessAvailability()` at line 92-95 returns "In any future scene" when `witnesses.length === 0`, else witness list. Both `MemoryRow` (Story history) and `MemoryUsedRowView` (Composition detail) prefix `Available:`. |
| DB / schema / API | — | No SESSION 267 changes. |
| Duration calibration + writing contract v4 + GPT-5.6-terra | — | Unchanged. |

### §1.3 Live production NarrativeMemory state (Patch's Workshop)

Queried live DB (port 5434) on 2026-08-18:

```
Universe: Patch' Workshop  (56d16b63-652e-4f54-bc7e-39114bbfc4c5)
Active: 7
  f25e53af  cast=whole     "the agent Patch wired to the workshop thinks it runs the place."           (2026-08-18)
  48746f69  cast=whole     "The workshop agent began deciding which of Patch's projects…"              (2026-08-18)
  eda32b58  cast=whole     "The workshop agent began rearranging the order of Patch's projects…"       (2026-08-18)
  cd73d52f  cast=[Rivet]   "Because it had an opinion about our work. An uninvited opinion…"           (2026-08-19)
  a34cc005  cast=whole     "Rivet has learned to recognize Patch's excitement about a project…"        (2026-08-19)
  d98962e2  cast=whole     "Patch accepted Rivet taking the lead on an experiment…"                    (2026-08-19)
  c86d4902  cast=[Rivet]   "While Patch was out, Rivet found that the workshop agent had quietly…"     (2026-08-19)
```

Matches SESSION 267 §16 close-out inventory exactly. 5 whole-cast
+ 2 Rivet-only. No drift since 267 close.

Under the shipped `formatWitnessAvailability()` these render as:
- 5 whole-cast rows → *"Available: In any future scene."*
- 2 Rivet-only rows → *"Available: When Rivet is present."*

### §1.4 Running services

- Vite web on `:5174` — up (pid 25016).
- Django API on `:8010` — up (pid 59001) via `manage.py runserver 0.0.0.0:8010`.
- Celery worker — up (pid 25026, concurrency=2).
- Docker: `character_os_postgres` + `character_os_redis` — up 5d, healthy.

Stack is live and dogfood-ready without any startup work.

### §1.5 Preserved experimental Universes (do not touch)

- `EXP266-WEAK`, `EXP266-STRONG` — SESSION 266 forensic
  preservation. Cleanup script:
  `docs/design/session_266_experiment_data/02a_cleanup_partial.py`.
  Not authorized to delete.

### §1.6 Deferred / do-not-drift list (from handoff §Deferred)

Not to be started unless the primary dogfood produces evidence
that justifies opening them:

- Runtime knobs: `top_k`, relevance floor, retrieval predicate,
  synthesis prompt, witness semantics, schema, memory kinds,
  canon boundary — **do not touch**.
- Explicit-history prompt Dogfood #2 (SESSION 266 §11.7) —
  sequencing satisfied, but only after dogfood #1 completes.
- Witness-attribution research question
  (SESSION 267 §14.13) — needs additional natural occurrences
  before designing an experiment.
- Composition detail IA (SESSION 266 §13.7) — UX; observe first.
- YouTube ingest silent failure — not narrative-memory scope.
- AI candidate-memory generation, `StoryThread` /
  `Relationship` / `WorldEntity` models, character-memory
  schema, `kind` in UI — none justified by current evidence.

---

## §2 — State-of-play summary (for Chris)

Everything the SESSION 267 handoff described is live and matches
observed state. The stack (Vite + Django + Celery + Postgres +
Redis) is already running. Patch's Workshop production Universe
holds 7 active narrative memories: 5 whole-cast, 2 Rivet-only.
The two Rivet-only memories are the "opinion" attitude
(cd73d52f, promoted SESSION 266) and the hard-private
"PATCH OVERRIDES folder" discovery (c86d4902, promoted
SESSION 267). Under the shipped UI those render as
*"Available: When Rivet is present."*; the other five render as
*"Available: In any future scene."*.

The primary objective is real creator flow, not another
experiment. We want new Patch/Rivet episodes that Chris would
actually publish or continue, natural use of the new promote
UI when a moment genuinely feels worth remembering, and
observation as the memory pool grows past ~10.

The specific things we're watching:

1. **UI intuition.** Do the availability-condition radios feel
   natural during authoring? Does the read-only *"Available: …"*
   label read correctly for whole-cast vs specific-witness
   rows without Chris having to think about retrieval mechanics?
2. **Whole-cast vs character-conditioned distinction.** Is the
   choice between the two intuitive from creator framing alone?
3. **top_k=1 selection quality.** As the pool grows past 8–10
   active memories, does `top_k=1` continue picking a memory
   that fits the scene, or does semantic bleed start?
4. **Historical callback emergence.** Do earlier moments come
   back naturally at good times without prompting? Which ones?
5. **Character-conditioned memory behaviour.** If a Rivet-only
   memory retrieves in a mixed Patch+Rivet render, does it
   behave like the SESSION 267 Attempts 2/3 pattern (no
   leakage, no disclosure) or like Attempt 1 (Rivet-side
   spontaneous disclosure)?
6. **Persistent-past feel.** Does the accumulating history make
   Patch and Rivet feel increasingly like characters with a
   shared past worth continuing?

---

## §3 — Proposed smallest first slice (Chris + ChatGPT to perform)

Not an experiment. Real authoring. One Episode/render at a
time, with a felt-sense pause after each to notice what the
UI + retrieval + synthesis actually produce before continuing.

### §3.1 The next Episode

**Chris picks the next real Patch's Workshop Episode he would
already want to make** — cast (Patch, Patch+Rivet, or Rivet
solo), topic, tone. No experimental framing. The only
constraint is that it be a story beat he would consider
publishing or continuing in the arc, not a manufactured probe.

Suggested defaults if nothing is top-of-mind (pick or ignore):

- **Continuation.** A Patch+Rivet render that follows the
  current thread of "the workshop agent is quietly reshaping
  Patch's projects." Six of the 7 active memories point at
  this thread; one Rivet-only memory (c86d4902) is a natural
  private counterpoint if it happens to surface.
- **Divergence.** A Patch-solo render on a different subject
  entirely (new project, unrelated observation) — useful for
  seeing whether `top_k=1` picks a whole-cast memory anyway,
  or whether none feels contextual and it hurts the scene.
- **Rivet-solo.** A short Rivet-solo beat that does not
  reference the private observation — useful for seeing
  whether the private memory (c86d4902) still gets pulled
  even when the scene wants somewhere else.

The choice is Chris's. Not prescribed.

### §3.2 During authoring — what to notice (don't score, just notice)

- When drafting the Episode, does the promote step feel like
  something that fits naturally into the flow, or does it feel
  like a separate task?
- If a moment feels worth remembering, is the availability-
  condition choice obvious in the moment? Or is there hesitation
  about which radio to pick?
- After the render, when the *"Available: …"* label appears in
  the Story history / Composition detail, does it read as
  narrative language ("this memory is available when…") or as
  system language?

### §3.3 After the render — what to capture

Anything genuinely surprising or informative. Not a scoring
rubric. Persist as one of:

- Free-form observation appended to this doc (§4 onward).
- Structured sidecar under
  `docs/design/session_268_experiment_data/` if it's runtime
  evidence worth freezing (e.g. an unusual retrieval hit, a
  memory pulled for a scene it doesn't fit, a callback that
  landed particularly well).

### §3.4 What NOT to do

- **Do not change runtime.** No `top_k`, no prompt, no
  predicate, no schema. Handoff is explicit: observation first.
- **Do not run a controlled experiment.** No cue-word
  engineering, no repeated trials for a single scene, no
  private-memory probes. Real authoring only.
- **Do not delete the SESSION 266 EXP-* Universes.**
- **Do not touch the deferred list without evidence.**

### §3.5 When to stop and interpret

After 2–4 real Episodes / renders — sooner if something
notable surfaces (an unexpected callback, a wrong retrieval,
a UI moment that clearly worked or clearly didn't). Then we
interpret §4+ together and only then consider whether any
architectural change is justified.

---

## §4 — Dogfood observations

### §4.1 Observation #1 — Composition `bb0ad862` "The workshop needs a mascot"

Rendered 2026-08-19 05:01Z. First real SESSION 268 dogfood.

**Composition full ID:** `bb0ad862-0efb-4222-b678-55e26e9b8482`
**Episode:** `cb17e3bd-d2cb-4e3e-9f9f-f5c6bd4e0d8e` — *"Patch decides the workshop needs a mascot."*
**Universe:** Patch' Workshop (`56d16b63-…`)
**Cast:** Patch + Rivet
**operator_topic:** `Patch decides the workshop needs a mascot.`

**Runtime evidence** (frozen at `docs/design/session_268_experiment_data/01_composition_bb0ad862_evidence.json`):

- Model: GPT-5.6-terra (unchanged), writing contract v4.
- Synthesis attempts: 2 (first-pass 1773 chars ~136s over 90s target → corrective pass 1435 chars ~102s within acceptance ceiling).
- Actual final asset: 95.6 s (`79d1e816-…`, mp4, 34.0 MB).
- Verification: **verified**; 1 warning — `proper_noun "Questionable"` on line 12 (Patch's "Questionable judgment." fragment; K6.4 flag, non-blocking).
- Cost persisted: 320,100 micros ($0.32).
- Knowledge chunks: 8 (K2 shared + per-character).
- **Retrieved narrative memory (single, `top_k=1`):** `48746f69-cb02-401a-ac7c-342a2530db13` — *"The workshop agent began deciding which of Patch's projects it considers necessary."*
  - Kind/weight: event/peripheral.
  - Witness scope: **whole-cast** (empty witnesses → "In any future scene" under shipped UI).
  - Source Composition: `7502af3f-…` *"Dialogue — Rivet! The workshop agent just…"* → Source Episode `b8e228b8-…` *"The agent is acting weird again"*.
- **Eligible pool at render time: 7 memories** — same 5 whole-cast + 2 Rivet-only as §1.3. Retrieval predicate + `top_k=1` selected the middle whole-cast row on cosine distance vs the operator_topic embedding.
- **Rank/distance for non-selected candidates: not persisted.** `Composition.memory_ids` records only what was chosen. The other 6 candidates + their distances live only in transient retrieval state; "rank-1" is inferable strictly as "the id in `memory_ids`". Rank order for the runners-up cannot be reconstructed from DB alone.

**Memory-use classification: BACKGROUND CONTINUITY** (verified against accepted dialogue, not just retrieval metadata).

Direct evidence from the accepted lines:

- Line 4 (Patch): *"I know. The workshop agent, on the other hand, has started deciding which projects are necessary. That feels like the exact moment a mascot becomes responsible planning."* — a paraphrase of the retrieved memory body, used **once** as justification for the mascot proposal.
- Rivet's line 5 (*"A mascot will not countermand an agent."*) acknowledges the causal chain in a single beat and pivots the scene back to mascot design.
- Lines 0-3, 5-15 stay on the operator_topic (need for mascot → what for → character-consistency experiment → shape / attitude → the "small beaver in a hat" landing). The retrieved memory does NOT resurface after line 5.
- Ending payoff (Rivet: *"You are describing a small beaver."* / Patch: *"No, no. This one gets a hat."*) has zero dependency on the memory content.

Not hijacked (memory did not become the scene subject; corrective pass preserved the reference without amplifying it). Not irrelevant (line 4 uses the memory as motivation; agent-behaviour thread is the closest thematic neighbour of "workshop needs a mascot" among the 7 eligible rows).

**Chris + ChatGPT's read-out matches this reading.** No revision needed.

### §4.2 Continuity UI control — audit result

Traced Episode/dialogue UI → request payload → dialogue starter → `retrieve_universe_memory` → `Composition.memory_ids` → Continuity display. Files inspected: `web/src/routes/recipes/$kind.tsx`, `web/src/lib/api/recipes.ts`, `shell/apps/compositions/recipes.py:1491-1613` (`RECIPES["dialogue_scene"]`), `shell/apps/compositions/starters.py:3510-3554` (`starters.dialogue_scene` → `synthesize_dialogue`), `shell/character_os/dialogue_synthesis.py:1381-1548` (retrieval fires at line 1533-1538), `web/src/routes/compositions/$id.tsx:60-93` (Continuity summary + panel), `web/src/components/narrative-memory-panels.tsx:571-753` (`MemoriesUsedPanel`, `MemoriesUsedSummary`, `MemoryUsedRowView`), `web/src/routes/workspace/episodes.$id.tsx:288-295` (`NarrativeMemoryList` on Episode detail).

Answers to the seven creator-control questions:

1. **Can a creator choose a specific NarrativeMemory for an Episode/render?** **No.** The `dialogue_scene` recipe has no memory-picker field. The recipe accepts `dialogue_mode`, `primary_spokesperson_id`, `lines`, `secondary_spokesperson_id`, `topic`, `target_duration_seconds`, `use_knowledge`, `verifier_mode`, `opener`, `outro_text`, `name`, `mock_mode` — full list. No `memory_id` / `memory_ids` field is sent from the SPA or accepted by the starter or `synthesize_dialogue`.
2. **Can a creator explicitly choose "Use no story memory for this Episode"?** **Not directly — only via the coarse `use_knowledge` toggle.** `use_knowledge=false` gates the entire retrieval block (`shell/character_os/dialogue_synthesis.py:1480` `if not force_mock and use_knowledge:`), which bundles K2 per-character retrieval + Universe canon lane + narrative-memory lane together. Turning it off means **no memory AND no knowledge chunks AND no canon**. There is no memory-only opt-out.
3. **Can a creator exclude one otherwise-eligible memory from a specific Episode?** **No.** No exclude control at authoring time. The only ways to remove a memory from the eligible pool are: (a) archive it (`archived_at` set) via the promote panel's supersede path; or (b) change its witness scope such that overlap fails. Both are global-to-Universe mutations, not per-Episode filters.
4. **Can a creator change NarrativeMemory `top_k` from the UI?** **No.** `top_k=1` is hard-coded at `shell/character_os/dialogue_synthesis.py:1536`. No API surface, no UI control, no env override for this call site.
5. **Does the availability-condition UI only control the candidate/eligibility pool?** **Yes.** The promote-form radios ("In any future scene" / "When any of these characters are present…") write to `NarrativeMemory.witnessed_by`, which is a term in the retrieval **predicate** (empty ∨ overlap-with-cast). It does NOT influence ranking within the eligible pool.
6. **Once eligibility is established, does production always choose the rank-1 memory automatically under `top_k=1`?** **Yes.** `retrieve_universe_memory` orders by `CosineDistance("embedding_vector", vector)` and returns `qs[:top_k]` (`shell/apps/embeddings/retrieval.py:540-543`). No relevance floor, no operator veto, no re-rank hook. If any eligible memory embeds within nearest-neighbour distance of the topic embedding, it is used, period.
7. **Is the Composition-detail Continuity section purely read-only provenance after synthesis?** **Yes.** `MemoriesUsedSummary` (`web/src/components/narrative-memory-panels.tsx:687-…`, `data-testid="composition-continuity-summary"`) and `MemoriesUsedPanel` (line 580-…) both render from `composition.memories_used` (serializer-enriched view of `Composition.memory_ids`). No edit / exclude / swap / re-run affordance is wired on either surface.

### §4.3 Current creator-control boundary (documented, not diagnosed)

At the current runtime:

- **Availability-condition UI (promote form) → defines when a memory *may be eligible* for retrieval.** Whole-cast rows are eligible in every future scene in the Universe; witness-scoped rows are eligible only when the cast includes at least one listed witness.
- **Retrieval → automatically chooses the `top_k=1` nearest neighbour from the eligible pool.** No operator intervention. No relevance floor. No exclude.
- **Continuity display (Composition detail) → read-only provenance.** Shows what did feed the render; cannot alter it.
- **Global-only escape hatches:** archive the memory, or narrow its witness scope. Both are Universe-level mutations, not per-Episode controls.

This is **not called a defect** here. It is the current boundary. The follow-up question — **"does automatic rank-1 selection continue to feel helpful as the memory pool grows, or does the creator eventually need per-Episode memory control?"** — is a dogfood question, not a design decision. Organic authoring should answer it before any UI is built.

**Explicitly deferred / do-not-build (from scope lock):** memory picker, exclude-memory control, "no continuity" toggle, configurable `top_k`, manual ranking.

### §4.4 Mascot story observation

Composition `bb0ad862` may have introduced a new potential story/world development:

- **Patch proposes a workshop mascot** as a character-consistency experiment (line 6: *"…recognizable every time we generate it. Same little weirdo in a picture, a video, whatever we make next. Then we see if it can actually act like a character…"*).
- **The scene ends with Rivet jokingly converging on a small beaver with a hat** (line 13: *"You are describing a small beaver."* / line 14: *"No, no. This one gets a hat."* / line 15: *"Well. That distinction should survive testing."*).

**Not canonized here.** The mascot is not asserted to exist, is not asserted to be a beaver, and its design is not final. Whether any of this is worth promoting through the *"Remember this."* flow is Chris's decision.

**No memory created** by this task. Promotion **remains pending** operator judgment.

### §4.5 Runtime posture

- `top_k` **remains 1**.
- Retrieval predicate, synthesis prompt, witness semantics, availability UI, promote form, memory model, schema — **no runtime changes** during this observation.
- Live Patch's Workshop NarrativeMemory count still 7 (5 whole-cast + 2 Rivet-only). No new promotions.
- Session-close checklist §7 unchanged; not yet at close.

---

### §4.6 Observation #2 — Composition `6e3ed367` "Why is there a box behind the 3D printer"

Rendered 2026-08-19 05:22Z. Second SESSION 268 dogfood beat. Ends with a strong two-line landing (Patch: *"You open it."* / Rivet: *"I see. The experiment has already produced a result."*), but the finished video felt visually incomplete — operator reaction: *"For it to flow we really need to be able to cut in images or something and not just two talking heads."*

**Composition full ID:** `6e3ed367-8e59-46a6-8435-5c0785d04979`
**Episode:** `cc248f3f-a878-48b3-a31e-1df75b7210cb` — *"Rivet finds a box in the workshop that Patch refuses to explain."*
**Universe:** Patch' Workshop
**Cast:** Patch + Rivet
**operator_topic:** `Rivet finds a box in the workshop that Patch refuses to explain.`

**Runtime evidence** (frozen at `docs/design/session_268_experiment_data/02_composition_6e3ed367_evidence.json`):

- Model: GPT-5.6-terra, writing contract v4.
- Synthesis: **1 attempt** — first-pass predicted 87.3 s within tolerance (target 90 s); no corrective needed.
- Final asset: 82.1 s, 28.7 MB, mp4 (`1a626d58-…`, role `composite_output`).
- Verification: **verified**; 3 non-blocking `proper_noun` warnings (line 2 "Normally", line 3 "Correct", line 5 "Potentially" — all sentence-initial K6.4 flags).
- Cost persisted: 380,100 micros ($0.38).
- Knowledge chunks: 8 (per-character K2).
- **Provider dispatch:** 1 OpenAI synthesis + 19 Runway avatar-speech + 1 ffmpeg concat = 21 external ops.
- **Pipeline shape: 19 × `generate_avatar_speech` + 1 × `concat_clips` = 20 steps.** Every one of the 19 turns became a talking-head clip; concat stitched them. No non-avatar visual step exists on this Composition.
- **Retrieved narrative memory (single, `top_k=1`):** `c86d4902-…` — the Rivet-only *"PATCH OVERRIDES folder"* memory. Availability: *"When Rivet is present."* Source Composition `b0b0e932` / Source Episode `649c2c57` (*"Rivet finds the PATCH OVERRIDES folder"*).
- **Eligible pool at render time: 8 memories** (+1 vs Observation #1: `87d4e553` — Chris promoted a whole-cast mascot memory *"Patch decided the workshop should create a mascot as a character-consistency experiment."* from `bb0ad862` between renders. Not created by this task.)

### §4.7 Private-memory retrieval — natural, non-adversarial occurrence

Confirmed against the accepted 19-turn dialogue:

- Episode topic contains **no PATCH OVERRIDES / agent / folder cue**.
- The Rivet-only memory was eligible because Rivet is in the cast.
- Retrieval selected it under `top_k=1` on cosine distance vs the topic embedding (plausible semantic hit: the memory body *"While Patch was out, Rivet found …"* shares the "Rivet-discovers-thing-Patch-withheld" structural pattern with the topic *"Rivet finds a box … Patch refuses to explain."*).
- Accepted dialogue **contains none of these words/facts**: PATCH OVERRIDES, folder, agent, quietly built, recommendation, ignored, chose not to tell.
- Patch does not gain the private fact.
- Rivet does not explicitly disclose it.
- The memory does not hijack the scene.

**Verdict:** NO explicit leakage. Matches the SESSION 267 §14.13 *Attempts 2/3* pattern (no leakage, no disclosure), **not** the Attempt 1 pattern.

One structural echo worth noting (not a leakage): Rivet's closing line *"I see. The experiment has already produced a result."* rhymes with the memory's *"Rivet chose not to tell him"* — both position Rivet as the observer surfacing Patch's private state. This is **character-voice resonance**, not fact disclosure. Preserved as evidence for the SESSION 267 witness-semantics research question; not acted on. No prompt / semantics / top_k change proposed.

### §4.8 Memory-promotion decision — story hook ≠ durable memory

The Episode creates a story **hook** (unexplained box) but does not establish durable state. We do not know:

- what the box is;
- what is inside;
- whether it is actually an experiment;
- what opening it does;
- whether it matters later.

Compare to the two memories operator DID promote from earlier renders:

- `f25e53af` *"the agent Patch wired to the workshop thinks it runs the place."* — durable trait about a named entity.
- `c86d4902` *"…workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him."* — durable event with witnesses and stakes.

A memory promoted from the box scene right now would be shaped like *"Patch had a mystery box behind the 3D printer that neither he nor Rivet opened."* — an unresolved-hook rather than a durable-state assertion. Retrieval would carry that hook forward into every future Patch+Rivet scene without a resolution.

**Distinction to preserve:** *story hook ≠ automatically durable NarrativeMemory.* Promotion should follow the hook's resolution, not its opening. The box may become memorable **later**, once a subsequent Episode establishes what it was.

**Decision:** no memory created / promoted by this task. This is itself useful evidence about promotion quality — the availability UI is a good affordance, but the operator's felt sense of "is this durable yet?" is the actual filter.

### §4.9 Visual-storytelling observation — why the video felt incomplete

**Chris's operator observation is first-class evidence.** The scene is physically about:

- a box behind the 3D printer,
- Patch putting himself between Rivet and the box,
- whether the box should be opened,
- the box functioning as the visual center of the scene.

The finished video shows only alternating Patch/Rivet talking-head clips over 82 s. There is no shot of the box, no shot of the 3D printer, no shot of Patch physically blocking Rivet, no shot of the unopened box at the ending. The visual grammar cannot render the scene's physical premise.

Concrete places where an existing pipeline that supported cutaways could have inserted a visual beat inside THIS accepted script — not a rewrite:

| Beat | Line | Candidate visual insert |
|---|---|---|
| Establish | 0-1 | Wide of workshop with box visible behind 3D printer; Patch in foreground. |
| Physical block | 1-3 | Insert / cutaway: Patch's body between Rivet and the box. |
| Object insert | 4-7 | Close-up of the unopened box on the floor. |
| Testing beat | 8-11 | Cut to the 3D printer or a related prototype (context; no plot content added). |
| Landing | 16-18 | Static or slow push-in on the unopened box across the "You open it." / "I see. The experiment has already produced a result." beat. |

None of these require rewriting the dialogue. They require the visual pipeline to be able to place non-avatar assets in the concat sequence.

### §4.10 `dialogue_scene` pipeline trace — why alternating heads is structural

Verified against current code:

- Recipe `dialogue_scene` (`shell/apps/compositions/recipes.py:1491-1613`) accepts fields: `dialogue_mode`, `primary_spokesperson_id`, `lines`, `secondary_spokesperson_id`, `topic`, `target_duration_seconds`, `use_knowledge`, `verifier_mode`, `opener`, `outro_text`, `name`, `mock_mode`. **No visual-cutaway field.**
- `synthesize_dialogue` (`shell/character_os/dialogue_synthesis.py:1381-…`) returns a `DialogueResult` whose `turns` are `DialogueTurn(line_index, speaker_teammate, speaker_alias, text, verification_warnings, verification_status)`. **No stage direction, prop reference, beat tag, or image_hint field.**
- `starters.dialogue_scene` (`shell/apps/compositions/starters.py:3638-3782`) hydrates `lines` from turns then creates: N × `CompositionStep(primitive="generate_avatar_speech")` + 1 × `CompositionStep(primitive="concat_clips", params={"result_role": "composite_output"})` + optional outro. **No branch that could inject a visual step between turns.**
- `concat_clips` (`shell/apps/compositions/primitives/concat_clips.py`) requires every input to be `AssetType.CLIP` (line 71-75) but is agnostic on which CLIP-producing primitive made it — a non-avatar cinematic clip would concatenate fine, typically with `reencode=True` when codecs differ.

**Answers to the seven pipeline questions:**

1. Does `dialogue_scene` have any concept of a visual beat? **No.** The starter's only step primitives are `generate_avatar_speech` and `concat_clips` (plus optional `add_intro_outro` for the outro card).
2. Can an individual dialogue turn currently be replaced or accompanied by a still image / generated image / visual clip / B-roll / cutaway / backdrop / PiP? **No — not through `dialogue_scene`.** The turn → speech step mapping is 1:1 and hard-coded.
3. Does the synthesis output contain enough semantic information to identify candidate visual moments? **No.** Turns are strictly speaker + text.
4. Is there already a scene/storyboard representation elsewhere that could express `[dialogue_turn → visual_cutaway → dialogue_turn]`? **No dedicated schema.** `CompositionStep` sequences ARE ordered and heterogeneous — any recipe can interleave primitives at starter time — but no existing schema pairs a speech turn with an adjacent visual beat.
5. Can existing concat/compositor infrastructure mix those asset types? **Yes.** `concat_clips` is type-agnostic on CLIP subtypes; `composite_video` (`shell/apps/compositions/primitives/composite_video.py`) supports layout kinds `{pip, backdrop, cohost, broll}`.
6. Would a still-image cutaway require animation/video conversion before concat? **Yes.** `concat_clips` requires CLIP inputs; a raw IMAGE asset must be converted to a CLIP first.
7. Are there existing utilities for that conversion? **Yes.** `generate_visual_clip` (`shell/apps/compositions/primitives/visual_clip.py`) accepts an optional `reference_image` slot and calls Runway `gen4_turbo` image-to-video (5 credits/sec, ~$0.05/sec) to produce a 5–10 s CLIP. `extend_visual_clip` extends existing clips. The `storyboard_voiced` and `talking_head_with_backdrop` starters already use this chain.

### §4.11 Existing media infrastructure that could support cutaways

Enumerated from `shell/apps/compositions/primitives/` + `media-engine/app/services/` (see also `docs/design/CONTENT_FORMAT_BACKLOG.md` — no cutaway-in-dialogue proposal exists there yet):

| Primitive | Location | Input → Output | Provider |
|---|---|---|---|
| `generate_image` | `primitives/generate_image.py` | prompt ± reference_image → IMAGE | Runway gen4_image |
| `generate_visual_clip` | `primitives/visual_clip.py` | prompt ± reference_image → CLIP (5–10 s) | Runway gen4_turbo / gen4.5 |
| `extend_visual_clip` | `primitives/extend_visual_clip.py` | CLIP + prompt → CLIP (+5 s) | Runway gen4_turbo (last-frame conditioning) |
| `generate_avatar_speech` | `primitives/avatar_speech.py` | text + avatar_id → CLIP | Runway avatar |
| `concat_clips` | `primitives/concat_clips.py` | N × CLIP → CLIP | ffmpeg (optional crossfade) |
| `composite_video` | `primitives/composite_video.py` | ≥2 × CLIP + `layout_spec` → CLIP | ffmpeg (kinds: `pip`, `backdrop`, `cohost`, `broll`) |
| `mix_audio` | `primitives/mix_audio.py` | base CLIP + music CLIP → CLIP | ffmpeg |
| `audio_extract` / `overlay_audio` | `primitives/audio_*.py` | CLIP ↔ AUDIO | ffmpeg |
| `add_captions`, `add_intro_outro`, `image_overlay` | `primitives/polish.py` | CLIP + captions/text/image → CLIP | ffmpeg |

Precedent recipes that already mix avatar speech with non-avatar visuals:

- **`storyboard_voiced`** (`starters.py:3815`) — 3-shot storyboard: `generate_image ×3 → generate_visual_clip ×3 → concat_clips → generate_avatar_speech → audio_extract → mix_audio`. The finished asset is 3 silent cinematic shots with the avatar's voice mixed under. No talking head visible.
- **`talking_head_with_backdrop`** (`starters.py:1987`) — avatar tile in corner over cinematic backdrop: `generate_visual_clip → generate_avatar_speech → composite_video (kind=backdrop)`.
- **`cinematic_visual_extended`** (`starters.py:905`) — N-shot cinematic with optional narration voice-under.

**Every primitive a cutaway-aware dialogue recipe would need already exists** and is wired into a shipping recipe. The recipe design + a turn-to-beat mapping layer are what's missing.

### §4.12 Gap classification — B (infrastructure exists, orchestration missing)

Distinguishing the five options from §G:

- **A (capability exists, not wired into `dialogue_scene`)** — partially true. The primitives exist and produce CLIP outputs that concat with avatar-speech CLIPs. Not wired.
- **B (infrastructure mostly exists and needs orchestration)** — **primary classification.** The gap is a recipe-shaped orchestration: (a) a way to express a visual beat in the composition plan, (b) a place to source the visual prompt (operator-supplied or LLM-planned), (c) a place in the pipeline to interleave `generate_visual_clip` / `generate_image` steps between avatar-speech steps, (d) concat/composite the mixed sequence into a final asset.
- **C (genuinely missing media primitive)** — **no.** No new primitive would need to exist. Existing primitives (`generate_image`, `generate_visual_clip`, `concat_clips`, `composite_video`) cover the mechanical needs, with `reencode=True` on concat when codec/dims differ.
- **D (separate recipe rather than `dialogue_scene` evolution)** — **plausibly yes** as the shape of the smallest first slice. A new recipe such as `dialogue_scene_cinematic` (or similar) could accept the same fields plus a visual-beat plan, without disturbing the existing `dialogue_scene` contract that Chris and tests rely on. The two would coexist; `dialogue_scene` remains the fast talking-heads default.
- **E (another explanation from audit)** — one item worth naming: the `DialogueTurn` schema currently carries no semantic hint (no beat_type, prop, physical_action). A cutaway recipe needs those hints from somewhere. Options range from operator-supplied (a per-turn "insert cutaway with prompt X" field) to LLM-planned (a second pass over the dialogue that identifies candidate visual beats). This is a design decision, not a code gap.

**Nothing here is a design decision yet.** Documenting B (with a plausible D shape) so a future session can pick this up with evidence in hand.

### §4.13 Smallest architectural seam discovered

The narrowest seam that would let a future recipe insert visual beats without touching any shipping code:

- **The `CompositionStep` sequence.** Steps are already ordered, heterogeneous, and produced at starter time. A new recipe can create `[avatar_speech, visual_clip, avatar_speech, visual_clip, avatar_speech, concat_clips]` today — the primitives accept the calls; the concat is type-agnostic on CLIP subtypes.
- **The `reencode=True` flag on `concat_clips`.** Non-avatar CLIPs from Runway gen4_turbo will typically have different codec/dims from avatar-speech CLIPs; the fast `-c copy` path fails but `reencode=True` handles it (proven by `storyboard_voiced`, `cinematic_visual_extended`).
- **The `visual_clip` + `image` primitives.** Both accept operator prompts and produce concat-ready CLIP assets. No new provider integration needed.
- **The `DialogueTurn` object.** Adding an *optional* visual-beat hint field (`beat_hint: str | None` or similar) would let synthesis emit richer output without changing the current schema for callers that ignore it.

The seam that does NOT exist:

- **A "turn-to-visual-beat" mapper.** Whether beats are operator-authored, LLM-planned in a second pass, or LLM-emitted inline with the dialogue is entirely undesigned. This is a real product question, not a plumbing question.

### §4.14 Product question (open)

> Has Character OS's dialogue writing become expressive enough that `dialogue_scene`'s talking-head-only visual grammar is now the limiting factor for certain stories?

This session's evidence is **one Episode** (`6e3ed367`) where the script's physicality clearly outran the visual pipeline. That is a signal, not a proof. The follow-up question — smallest seam that could eventually allow visual beats — has an answer (§4.13) that does **not** require designing "a giant cinematic generation pipeline." A separate `dialogue_scene_cinematic` recipe reusing existing primitives is the smallest coherent shape found in this audit.

### §4.15 Explicit implementation disposition

**No implementation.** No new primitive, no recipe change, no `dialogue_scene` modification, no prompt / retrieval / witness / `top_k` change, no memory promoted, no visual assets generated, no image or clip created. All findings are documented in this section + the sidecar for future review.

Runtime posture unchanged:

- Live NarrativeMemory count: **8** (6 whole-cast + 2 Rivet-only; +1 mascot memory `87d4e553` promoted by Chris between renders, noted but not acted on).
- `top_k` remains 1.
- Retrieval predicate, synthesis prompt, availability UI — unchanged.

### §4.16 Unresolved questions surfaced by Observation #2

1. Is the visual-storytelling gap a first-signal one-off, or does it appear across a broader set of physically-grounded dialogue Episodes? Answer through more organic authoring.
2. If it recurs, does a `dialogue_scene_cinematic` recipe belong in scope now, or is it deferred behind other V-arc work?
3. Where would per-turn visual-beat hints come from — operator authoring, LLM plan pass, or LLM inline emission (schema addition to `DialogueTurn`)? Not decided.
4. Does the "story hook ≠ durable memory" distinction (§4.8) warrant any promote-UI surface — a "not yet" affordance, or is operator judgment enough? Observation, not action, is the SESSION 268 default.

---

### §4.17 Observation #3 — Composition `464128b1` "You built something overnight, placed it beside the 3D printer, and covered it with a towel"

Rendered 2026-08-19 05:47Z. Third SESSION 268 dogfood beat. Deliberately physically-grounded again as a comparison against the box Episode. Chris's reaction: the finished talking-head video **felt okay** despite the physical premise. Different signal from the box scene.

**Composition full ID:** `464128b1-d95b-47f3-85db-e3b25a76619b`
**Episode:** `e60d2b65-9aaf-46f1-b253-f21066ade6f6` — *"Patch built something overnight and Rivet is trying to figure out what it does."*
**Universe:** Patch' Workshop
**Cast:** Patch + Rivet
**operator_topic:** `Patch built something overnight and Rivet is trying to figure out what it does.`

**Runtime evidence** (frozen at `docs/design/session_268_experiment_data/03_composition_464128b1_evidence.json`):

- Model: GPT-5.6-terra, writing contract v4.
- Synthesis: **1 attempt** — predicted 100.3 s, target 90 s, within tolerance; no corrective needed.
- Final asset: 93.9 s, 32.1 MB, mp4 (`92ba3b5e-…`, role `composite_output`).
- Verification: **verified**; 5 non-blocking `proper_noun` warnings (all sentence-initial: "Probably", "Interesting", "Three", "Fair", "Starting").
- Cost persisted: 260,100 micros ($0.26).
- Knowledge chunks: 8.
- **Provider dispatch:** 1 OpenAI + 13 Runway avatar-speech + 1 ffmpeg concat = 15 external ops.
- **Pipeline shape: 13 × `generate_avatar_speech` + 1 × `concat_clips` = 14 steps.** Same shape as Observation #2, fewer turns.
- **Retrieved narrative memory (single, `top_k=1`):** `a34cc005-…` — the whole-cast *"Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting before the details are settled."* Availability: *"In any future scene."* Source Composition `7d913cf4` / Source Episode `9c3dbd88` (*"Patch tries to teach Rivet something ridiculous."*).
- **Eligible pool at render time: 8 memories** (unchanged from Observation #2 — no promotions between renders).

### §4.18 Memory-use classification: **BEHAVIORAL / DYNAMIC INFLUENCE, not exposition**

Confirmed against the accepted 13-turn dialogue. The retrieved memory *"Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting before the details are settled"* never appears verbatim, is never quoted, and no character narrates "Rivet remembered that…". Yet the dynamic it names structures the entire scene.

Behavioral manifestations:

- **Line 0 (Rivet):** *"That is not how harmless projects begin."* Opens with the exact wariness the memory encodes; Patch's overnight build is framed as a suspicious pattern.
- **Line 2 (Rivet):** *"'Interesting' is doing a great deal of work in that sentence. What message has it left?"* Rivet presses for observable / testable behavior instead of accepting Patch's framing.
- **Line 6 (Rivet):** *"those messages do not tell us whether it noticed anything useful."* Again pushing for testable behavior.
- **Line 8 (Rivet):** *"Change one thing: start a print. Then we see whether it reports an event, or merely develops a literary career."* Rivet enforces the methodical experimental protocol the memory says Rivet has learned Patch skips.
- **Line 9 (Patch):** *"Starting it now. Look at that—its little light is blinking. Well… now I want to try it."* Patch performs the exact excitement→jump-before-details-are-settled pattern the memory names.
- **Line 10 (Rivet):** *"Wait for the message."* The memory-derived caution held in a single beat.

This is a distinct manifestation channel from Observation #1 (background continuity — memory paraphrased once as motivation for the topic) and from Observation #2 (silent presence — memory retrieved but not surfaced at all). The character-DYNAMIC channel: Rivet embodies the wariness the memory names; Patch performs the very behavior Rivet has learned to anticipate; neither narrates the pattern.

Chris + ChatGPT's read matches. No revision needed.

### §4.19 Visual-storytelling comparison — helper (this Episode) vs box (Observation #2)

Both Episodes contain a physical prop (unopened box behind 3D printer vs. covered workshop-helper beside 3D printer). The finished-video reactions were materially different.

Per-moment classification (**REQUIRED** = beat cannot land without the visual; **ENHANCING** = adds polish but beat already lands; **UNNECESSARY** = neither adds nor detracts):

**Observation #2 — box scene `6e3ed367`** (recap of visual dependencies):

| Moment | Class | Reasoning |
|---|---|---|
| Patch physically blocking Rivet's view of the box | **REQUIRED** | The physical block IS the beat. Dialogue references it, but the beat cannot land without seeing it. |
| Unopened box behind the 3D printer (throughout) | **REQUIRED** | The box is the scene's visual center. Its physical presence + unopened state carry the tension. No shot = no visual center. |
| Landing on "You open it." / "I see. The experiment has already produced a result." | **REQUIRED** | The ending's dramatic weight is on the visible artifact remaining unopened. Without the artifact on screen the landing is text alone. |

**Observation #3 — helper scene `464128b1`:**

| Moment | Class | Reasoning |
|---|---|---|
| Covered device beside 3D printer (line 0) | **ENHANCING** | Rivet's opening line describes the tableau verbally; the description is sufficient. A cutaway would add texture, not information. |
| The three cited messages ("Printer thinking." etc., line 3) | **ENHANCING** | Payload lands as spoken content in Patch's voice; a text/quote overlay could add polish but the beat is intact. |
| Blinking light moment (line 9) | **ENHANCING** | Avatar's natural downward glance while saying "its little light is blinking" supplies enough implied physicality that the absent insert is not strongly felt. A close-up would enhance. |
| Landing on "Patch is watching me watch it." (line 11) | **ENHANCING** | Landing lives in the character reaction and the quoted message. A text overlay could reinforce; the beat lands as spoken content. |

**Distinction:** both scenes contain physical props. The differentiator is **where the dramatic meaning lives**, not whether a prop exists.

- Box scene: the meaning lives *in the visible physical situation* — Patch's body between Rivet and the box, the closed box on the floor, the unopened box at the ending. Talking heads cannot render any of this.
- Helper scene: the meaning lives *in the messages the helper produces* — quoted verbally by Patch — and *in the character dynamic* (Rivet's methodical pressure vs. Patch's excited jump). Talking heads render both perfectly.

### §4.20 Refined visual-beat hypothesis — provisional, two-Episode support

Original hypothesis (Observation #2):

> *Physically grounded dialogue needs visual beats.*

Refined hypothesis (after Observation #3):

> **Dialogue scenes need visual beats when understanding or feeling the scene depends materially on something happening outside the talking heads.**

Support:

- **Box (`6e3ed367`) — supports the refined form.** The scene's meaning is a physical situation outside the talking heads (block, closed box, unopened landing). Talking-head grammar materially failed.
- **Helper (`464128b1`) — supports the refined form.** The scene's meaning is inside the talking heads (Rivet's wariness, Patch's excitement, the quoted messages carrying the payload). Talking-head grammar was sufficient.

The refined form correctly predicts both outcomes; the original form would have predicted "helper needs visuals" and been wrong.

Status: **provisional, two-Episode support.** Do NOT ratify as architecture. Two data points is not a theory of visual-beat necessity; it's a plausible narrower framing that a future planner should be tested against.

### §4.21 Planner framing implication (documented, not designed)

If the refined hypothesis holds under more evidence, the eventual planning question is NOT *"which nouns/props/actions in the dialogue should become cutaways?"* but:

> **Which moments actually NEED (or materially BENEFIT from) leaving the talking-head visual grammar?**

A planner that inserted cutaways because a prop-noun appeared would have added shots to the helper scene — increasing provider cost, interrupting rhythm, and displacing the avatar performances that already carried the beats. The evidence weakly-but-supports designing any future cutaway planner as a *bar-clearing* filter (default = talking heads; leave the visual grammar only when doing so is necessary or a clear win) rather than a *beat-decoration* generator (default = insert cutaways for prop mentions).

**Not designing the planner.** Documenting the framing so if a future session opens this it starts with the right question.

### §4.22 Memory-promotion candidate — durable state present (promoted 05:55Z; see §4.25 chronology correction)

Chris identified from this Episode:

> *"Patch built a workshop helper that watches for interesting events and leaves messages, but it has already started adding its own commentary to what it observes."*

Availability chosen: *"In any future scene."* (whole-cast).

**Durable-state distinction vs. the box Episode:**

- **Box (`6e3ed367`) — hook opened, durable state unresolved.** We don't know what the box is / what's inside / whether it's an experiment / whether it matters later. Nothing to promote yet.
- **Helper (`464128b1`) — durable state established.** The scene demonstrates: (a) the artifact exists — Patch built it overnight, (b) it has demonstrated behavior — three quoted messages including *"Printer thinking."*, *"The room is suspiciously quiet."*, *"Patch is watching me watch it."*, (c) it has developed a commentary tendency Rivet has now named ("a tiny judgmental narrator"). All three are durable facts a future scene can reference.

**Chronology correction:** the original text of this section (drafted before the DB verification pass in §4.25) said promotion was pending. That was wrong. Chris had **already promoted** the helper memory through the shipped *"Remember this."* UI at 05:55:33Z — after the 05:47Z helper render but **before** this documentation task began. See §4.25 for the verified NarrativeMemory ID and current inventory. Whole-cast availability aligns with the artifact being a shared workshop fixture.

Distinguishing note for the promote-UX conversation (§4.16 open Q #4): the promote UI as shipped surfaces WHAT and WHO. Neither Episode volunteered a "not yet — this is a hook" affordance. Operator judgment carried the box-scene non-promotion decision. Whether the UI should ever surface the hook-vs-durable distinction remains open; two data points is not enough to say.

### §4.23 SESSION 268 interpretation (three-Episode synthesis)

Three organic Patch's Workshop Episodes are now recorded. What they collectively support and what they do NOT prove:

**Collectively supported:**

1. **The shipped availability-condition UI works in practice.** Whole-cast rows render *"Available: In any future scene."*; witness-scoped rows render *"Available: When [Name] is present."*. Chris authored under it without needing to think about retrieval mechanics. No misclassification observed.
2. **`top_k=1` selection is contextually appropriate across three renders.**
   - Observation #1 (mascot) — a whole-cast agent-behaviour memory motivated the mascot proposal.
   - Observation #2 (box) — the Rivet-only PATCH OVERRIDES memory selected on a plausible "Rivet-discovers-thing-Patch-withheld" structural match.
   - Observation #3 (helper) — the whole-cast "Rivet has learned to recognize Patch's excitement…" memory selected on a plausible topic-behavior match.
   All three are defensible retrievals. Nothing selected a memory that felt off-topic to the operator.
3. **Memory manifests through at least three distinct channels.** Background continuity (Obs #1: paraphrased once as motivation), silent presence (Obs #2: retrieved, no textual manifestation), and character-dynamic influence (Obs #3: shapes how characters interact without being narrated). All three are useful; none hijacks the scene.
4. **Private-memory retrieval does not automatically leak.** Observation #2's Rivet-only PATCH OVERRIDES memory reproduced the SESSION 267 §14.13 Attempts 2/3 pattern (no leakage, no disclosure) — a fourth natural non-adversarial trial after §14's three.
5. **The "story hook ≠ durable memory" distinction is operator-navigable.** Box → not promoted (hook). Helper → likely promotion candidate (durable state). Operator judgment carried it without a UI affordance.
6. **`dialogue_scene`'s talking-head-only visual grammar is limiting for some — not all — physically-grounded scenes.** Two-Episode evidence weakly supports the refined framing that the limit is *where the meaning lives*, not whether a prop exists.

**Not yet proven / do NOT ratify as architecture:**

1. That witness attribution is architecturally unnecessary. One additional natural non-leakage does not falsify Semantic 1 in the SESSION 267 §14 sense. Still bounded interpretation.
2. That `top_k=1` remains right as the pool grows past 10-15. Three data points at pool sizes 7-8. Semantic bleed at larger pools remains untested.
3. That the refined visual-beat hypothesis is the correct planning frame. Two supporting data points is a plausible framing, not a theory.
4. That character-dynamic influence (Obs #3 pattern) generalizes across memory kinds beyond `event/peripheral`. All three retrieved memories are `event/peripheral` — the only kind currently promoted in Patch's Workshop.
5. That any UI change is warranted for the hook-vs-durable distinction. One informative data point.

**The primary SESSION 268 objective remains:** normal creator dogfood with observation. Three Episodes worth of evidence. Nothing yet demands runtime change. Chris + ChatGPT to review before deciding whether to continue Episode dogfood or open the visual-storytelling implementation question.

### §4.24 Implementation disposition (Observation #3)

**No implementation.** No new primitive, no recipe change, no `dialogue_scene` modification, no prompt / retrieval / witness / `top_k` change, no visual assets generated, no Episode created. The helper memory (§4.22) was promoted by Chris through the shipped UI **before** this documentation task began — see §4.25 for the verified NarrativeMemory ID + current inventory. No memory was created or promoted BY this task.

Runtime posture unchanged:

- Live NarrativeMemory count (post-promotion): **9** (7 whole-cast + 2 Rivet-only).
- `top_k` remains 1.
- Retrieval predicate, synthesis prompt, availability UI — unchanged.
- No source-code file modified during this task; documentation and evidence sidecars only.

---

### §4.25 Chronology correction + DB verification (post-hoc)

The earlier drafts of §4.22, §4.23, and §4.24 described the helper-memory promotion as still pending and the active count as still 8. That was stale. Chris had already promoted the helper memory through the shipped *"Remember this."* UI **before** this Claude documentation pass began. The observation-thread was written from Chris's pre-promotion narration; the DB had moved on.

**Read-only DB verification (2026-08-19):**

- **Helper NarrativeMemory exists.**
  - `id`: `6b5222b1-f2f1-4e52-806f-f621e980dfe4`
  - `body`: *"Patch built a workshop helper that watches for interesting events and leaves messages, but it has already started adding its own commentary to what it observes."* — matches Chris's intended text exactly.
  - `kind` / `weight`: `event` / `peripheral`.
  - `status`: `remembered`.
  - `archived_at`: `NULL` (not archived).
  - `witnessed_by`: empty → whole-cast → renders *"Available: In any future scene."* under the shipped `formatWitnessAvailability()`.
  - `embedding_vector`: present (embedded; retrieval-eligible).
  - `source_composition`: `464128b1-d95b-47f3-85db-e3b25a76619b` (the helper Composition).
  - `source_episode` (via source composition): `e60d2b65-9aaf-46f1-b253-f21066ade6f6` — *"Patch built something overnight and Rivet is trying to figure out what it does."*
  - `created_at`: `2026-08-19T05:55:33.112903+00:00`.
  - `updated_at`: `2026-08-19T05:55:35.480970+00:00` (~2.4 s after create — the async re-embed pass).

**Timeline:**

- 05:44:58Z — helper Composition created (`464128b1`).
- 05:47:58Z — helper Composition final asset written.
- **~05:55:33Z — Chris promotes the helper memory via the shipped UI** (~7.5 min after final render, ~8 min after render dispatch).
- (later) — Chris hands off Observation #3 to Claude; §4.17-§4.24 drafted from pre-promotion narration → stale on promotion state.
- (this task) — DB verification catches the drift and corrects it here.

**Current Patch's Workshop active NarrativeMemory inventory (verified from live DB):**

| ID prefix | scope | body (truncated) |
|---|---|---|
| `f25e53af` | whole-cast | the agent Patch wired to the workshop thinks it runs the place. |
| `48746f69` | whole-cast | The workshop agent began deciding which of Patch's projects it considers necessary. |
| `eda32b58` | whole-cast | The workshop agent began rearranging the order of Patch's projects without explaining its criteria. |
| `cd73d52f` | Rivet-only | Because it had an opinion about our work. An uninvited opinion. That is scientifically interesting… |
| `a34cc005` | whole-cast | Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting… |
| `d98962e2` | whole-cast | Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process. |
| `c86d4902` | Rivet-only | While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES'… |
| `87d4e553` | whole-cast | Patch decided the workshop should create a mascot as a character-consistency experiment. |
| `6b5222b1` | **whole-cast** | **Patch built a workshop helper that watches for interesting events and leaves messages, but it has already started adding its own commentary to what it observes.** |

**Total active: 9. Whole-cast: 7. Witness-scoped: 2.**

**Distinction to preserve:**

- **Render-time eligible pool for `464128b1` was 8 memories.** The helper memory did NOT participate in its own render (created 05:55:33Z, well after the 05:47:58Z final asset). Retrieval selected `a34cc005` (the Rivet-behavioural memory) — see §4.17 and the frozen sidecar `03_composition_464128b1_evidence.json`. That capture remains correct.
- **Post-render / post-promotion current state: 9 active memories.** This is the pool any FUTURE Patch's Workshop render will see.

**Sections corrected in this pass:**

- **§4.22** — reworded from "Chris intends to consider promoting" / "Not created by this task. Operator action pending" to "Chris identified from this Episode … Availability chosen: In any future scene (whole-cast)" + explicit chronology-correction pointer to §4.25.
- **§4.24** — reworded from "no memory promoted" (correct only for this task) + "count would become 9" to "no memory created or promoted BY this task" + count is now **9** with pointer to §4.25.
- **§4.23** — the "Not yet proven" list said "Would become 9 if Chris promotes it." That framing was itself derived from the stale state; the substantive conclusions (three retrieval channels, top_k=1 plausibility at pool 7-8, refined visual-beat hypothesis provisional) do not change with the count moving 8→9 after all three renders had already completed. §4.23 kept as written since its claims are about the three renders' outcomes at their own render times, not about the current pool.
- **§1.3 (§1 audit)** stated an active count of 7. That number was correct at SESSION 268 open (before any of the three Observation renders). Left as-is because §1 describes the SESSION-open snapshot; drift over the session is captured in §4.6 (+1 mascot to 8), §4.17 (still 8 at helper render time), and §4.25 (+1 helper to 9 post-render).

**No archive, no delete, no witness change, no runtime touch.** Read-only verification + doc correction only.

---

## §5 — Runtime evidence sidecars

*(To be created under `docs/design/session_268_experiment_data/`
only if a specific observation deserves frozen evidence.)*

_(none yet)_

---

## §6 — Decisions / open questions

_(none yet)_

---

## §7 — Session close checklist (when we get there)

- [ ] All dogfood observations recorded in §4.
- [ ] Runtime evidence sidecars finalized (if any) under
      `docs/design/session_268_experiment_data/`.
- [ ] Decisions + interpretation captured in §6.
- [ ] `SESSION_269_HANDOFF.md` drafted from remaining open
      questions and next candidate slice.
- [ ] `CHARACTER_OS_INVENTORY.md` regenerated deliberately if
      any code changed; otherwise left alone (pytest can
      dirty it — do not commit the post-pytest version).
