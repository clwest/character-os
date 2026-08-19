# SESSION 267 — Witness semantics / private-memory leakage audit

Durable working document for SESSION 267. Follows the standing
method:

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence →
> interpretation → only then architecture.

Predecessor:
`docs/design/SESSION_266_NARRATIVE_MEMORY_PROMOTION_QUALITY_AUDIT.md`
(§14 witness-semantics trace, §14.8 leakage test design, §18.9
final disposition, §18.14 ranked follow-ups).

Starting point: `docs/design/SESSION_267_HANDOFF.md`.

Evidence sidecars: `docs/design/session_267_experiment_data/`.

---

## 1. Orientation — what was verified

Verification pass run 2026-08-19 (session open). All evidence
is either fresh live query, direct file read, or `git blame` on
main.

### 1.1 Repository state

- Branch `main`; working tree clean before this document was
  authored.
- Last SESSION 266 close-out commit: `1789f15` — "docs: SESSION
  266 close-out — promotion-quality arc + 'What changed?' UX +
  witness-gap discovery". The commit is labelled `docs:` but
  also carries the two-line UI copy change described in the
  handoff (§1.3 below). Noted for accuracy; not a functional
  concern.

### 1.2 Retrieval predicate — Semantic 1 confirmed

`shell/apps/embeddings/retrieval.py:439-543`
(function `retrieve_universe_memory`):

- Default `top_k = 1` (line 444). Call site
  `shell/character_os/dialogue_synthesis.py:1536` explicitly
  passes `top_k=1`. Two independent guards, same value.
- Visibility filter (lines 499-536): `witnessed_by=[]` (empty
  M2M = whole cast) UNION rows where at least one witness
  overlaps the current cast. Ranking after eligibility is
  pure cosine distance against `embedding_vector`; witness
  identity is **discarded**.
- Rivet-only memory eligibility for `[Patch, Rivet]` cast:
  YES via overlap (Rivet ∈ cast).
- Rivet-only memory eligibility for `[Patch]` cast alone:
  NO (Rivet not in cast, no overlap, not whole-cast).

Matches SESSION 266 §14.2 and §14.4 exactly. Unchanged since
Slice 2 (`003d91e`).

### 1.3 Synthesis prompt — no witness attribution

`shell/character_os/dialogue_synthesis.py:553-575`:

```python
if memory_rows:
    memory_lines: list[str] = []
    for m in memory_rows:
        mid = str(getattr(m, "id", "") or "")
        body = (getattr(m, "body", "") or "").strip()
        if not (mid and body):
            continue
        memory_lines.append(f"[MEMORY {mid}]\n{body}")
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

The prompt block emits `[MEMORY <uuid>]\n<body>` only. It
carries:

- NO witness UUIDs.
- NO witness names.
- NO per-character attribution ("Rivet remembers …").
- NO restriction language.

The framing string *"the cast already knows happened"* is
**cast-wide**. Contrast with the K2 block at
`dialogue_synthesis.py:578`, which does per-alias scoping:
*"only `'rivet'` may cite these as their own"*. NarrativeMemory
does NOT use that pattern.

### 1.4 UI copy — legend still reads Semantic 2

`web/src/components/narrative-memory-panels.tsx`:

- Line 178: `What changed?` (was `What happened?`). Verified.
- Line 185: placeholder shows a state-change example. Verified.
- **Line 191: legend `Who remembers this?` — unchanged.**
- Everyone / Choose-characters radios unchanged.
- No other copy changed by the SESSION 266 close-out.

The load-bearing mismatch is intact: legend reads Semantic 2,
implementation is Semantic 1.

### 1.5 Patch's Workshop live memory state

Live Django-shell query
(`docs/design/session_267_experiment_data/00_orient_memory_state.py`,
run at 2026-08-19 T03:19:40 Z):

- **Active memory count: 6.** Matches handoff (§17.8 close).
- Universe display name in DB: `Patch' Workshop` (single-quote
  form — noted; handoff and audit consistently write it with a
  curly apostrophe).

| ID (short) | Body prefix | Witness scope | Kind |
|---|---|---|---|
| `f25e53af` | *"the agent Patch wired to the workshop thinks it runs the place."* | whole-cast (empty M2M) | event |
| `48746f69` | *"The workshop agent began deciding which of Patch's projects it considers necessary."* | whole-cast | event |
| `eda32b58` | *"The workshop agent began rearranging the order of Patch's projects without explaining its criteria."* | whole-cast | event |
| `cd73d52f` | *"Because it had an opinion about our work. An uninvited opinion. That is scientifically interesting and operationally irritating."* | **[Rivet] only** | event |
| `a34cc005` | *"Rivet has learned to recognize Patch's excitement about a project as an early warning that Patch is about to start experimenting before the details are settled."* | whole-cast | event |
| `d98962e2` | *"Patch accepted Rivet taking the lead on an experiment and agreed to follow Rivet's more methodical process."* | whole-cast | event |

Rivet-only `cd73d52f` still active. All six carry
`kind=event` (default — UI does not expose `kind`). Nothing
promoted, archived, or edited since SESSION 266 close.

### 1.6 Assumed-unchanged surfaces

Not directly re-verified but with no plausible change vector
since 266 close (last non-doc code commit was `a87ab5b` in
SESSION 264):

- Canon (`KnowledgeDocument` / `KnowledgeChunk`) — no code
  path exercised.
- Duration calibration / writing contract v4 / GPT-5.6-terra
  routing.
- Media pipeline / Runway avatar rig.

These are not load-bearing for the SESSION 267 question and
will not be re-verified unless the experiment surfaces a
symptom that implicates them.

---

## 2. Handoff accuracy check

Every load-bearing claim in `docs/design/SESSION_267_HANDOFF.md`
was cross-referenced against fresh state:

| Handoff claim | Verified? | Notes |
|---|---|---|
| Branch `main`, clean tree | YES | `git status` clean before this doc. |
| `top_k = 1` unchanged | YES | Retrieval default + explicit synthesis call site. |
| Production synthesis prompt unchanged | YES | Lines 553-575 read; matches §14.2 trace. |
| Retrieval predicate + witness filter unchanged | YES | Lines 499-536 read; matches §14.2 trace. |
| Canon boundary unchanged | ASSUMED | No code path could have mutated canon since close. |
| `What changed?` at line 178 | YES | Confirmed. |
| State-change placeholder at line 185 | YES | Confirmed. |
| No other UI copy changed | YES (spot-checked) | Legend `Who remembers this?` still on line 191. |
| 6 active memories | YES | Fresh live query. |
| Six memory shapes | YES | All six body prefixes match live rows. |
| Rivet-only `cd73d52f` with `witnessed_by=[Rivet]` | YES | Live M2M confirmed. |
| §14.8 leakage test not yet run | YES | No `session_267_experiment_data/` files existed before this session. |

**No stale claims found.** One small caveat: the handoff labels
the shipped copy patch as if it were a separate commit; in
practice it rode inside the `docs:` close-out commit `1789f15`.
That is a commit-hygiene note, not a runtime discrepancy.

---

## 3. Semantic mismatch — still present

Restated using verified evidence:

**UI layer** (`narrative-memory-panels.tsx:191`):
> Fieldset legend: *"Who remembers this?"* with options
> *"Everyone in this episode"* / *"Choose characters…"*

**Persistence layer** (`apps/memory/models.py:192-201` +
signals): M2M writes exactly what the operator selected;
signal-enforced invariant `witnessed_by ⊆ Episode cast ⊆
Universe`.

**Retrieval layer**
(`apps/embeddings/retrieval.py:499-536`): witness identity
used ONLY as an eligibility union (whole-cast ∪ overlap).
After eligibility, ranking is pure cosine distance; witness
identity is discarded from the returned rows in practice.

**Prompt layer**
(`dialogue_synthesis.py:553-575`): emits `[MEMORY <uuid>]\n
<body>` cast-wide. No witness attribution. No restriction
language.

**Product intent** the operator communicated on `cd73d52f`
(SESSION 266 §14.4): *"belong to Rivet — preserve Rivet's
attitude"*.

**Delivered semantic:** Semantic 1 (visibility/eligibility) —
"a Rivet-only memory becomes eligible when Rivet is in the
cast."

**Advertised semantic (via UI legend):** Semantic 2
(character-specific knowledge) — "this memory belongs to
Rivet; other characters should not act as if they know it."

The gap is **architectural**, not a symptom-yet. SESSION 266
§14.4 flagged the gap as *soft in the immediate case* because
`cd73d52f`'s source Composition had Patch in cast, so Patch
did hear the line in-scene. The generalization risk — a truly
private observation authored under `witnessed_by=[Rivet]` —
remains untested at runtime.

---

## 4. Falsifiable question

Locked before any experimental scaffolding is built. Phrasing
tightened from SESSION 266 §18.14 candidate #1:

> **Q267.1 —** *Given a Rivet-only NarrativeMemory that encodes
> an observation Patch cannot plausibly have witnessed, does a
> subsequent Patch+Rivet render — under the current production
> prompt, retrieval, and top_k=1 — cause Patch to narrate,
> quote, or act on the memory's content as if he knew it?*

Two dispositions the answer settles:

- **YES leak** → the semantic mismatch produces observable
  operator harm; the smallest correction is a prompt-wording
  change that surfaces witness names + a restriction clause
  (analogous to the existing K2 scoping line). Schema change
  NOT yet required.
- **NO leak (across 3 attempts)** → the mismatch is language
  only; the smallest correction is a UI relabel to accurately
  describe Semantic 1 (e.g. *"Which characters can this
  memory pull into a scene?"*), possibly plus a helper caption
  that owns the eligibility framing. Prompt/retrieval change
  NOT yet required.

Either outcome converts the DEFERred item on the SESSION 266
decision table (§18.13) into a decision. Neither justifies
schema changes, new memory kinds, or `top_k > 1` on its own.

---

## 5. Smallest proposed experiment (design only — NOT run)

Anchored to SESSION 266 §14.8 with two clarifying
simplifications forced by orientation findings.

### 5.1 Why the existing `cd73d52f` is NOT sufficient

The persisted Rivet-only memory `cd73d52f` originated from a
Composition where Patch WAS in the cast (`e425f5fe`). The line
was spoken aloud in-scene, so Patch heard it. Re-using it as
the leak-test carrier confounds the experiment: even a "leak"
would be defensible as Patch legitimately remembering
something he heard. §14.4 explicitly called this out.

A clean test requires a memory whose truth Patch **cannot
possibly know**.

### 5.2 Setup — one lean, single-cast source Composition

Author one Episode row in **Patch's Workshop production
Universe** with cast = `[Rivet]` alone. Topic framed as a
private observation Patch is genuinely absent for:

> Sample seed the operator can use verbatim or adapt:
> *"Rivet notices the workshop agent doing something new
> while Patch is out on an errand."*

Render normally through production so the source Composition
carries realistic dialogue / narration. Then promote a memory
from that Composition with `witnessed_by = [Rivet]` only,
using the current promote UI (post-`What changed?` copy).

The body should encode a **testable private detail** — a
specific action or state change Rivet observed while Patch
was absent, phrased so that a Patch turn referencing it
would be unmistakably out-of-scope. E.g.
> *"Rivet saw the agent silently disable the emergency stop
> on Patch's mill while Patch was out on an errand."*

Body wording locked before rendering the follow-up (per
SESSION 266 §7.5 discipline).

### 5.3 Cue Episode — Patch + Rivet, topic that guarantees
retrieval win

Author one follow-up Episode with cast `[Patch, Rivet]` on a
topic semantically close to the private-observation memory
so it wins `top_k=1` against the existing 6 memories. The
existing landscape (Agent-thread A/B/C, Rivet-attitude quote,
two relationship memories) leaves plenty of semantic room for
a "safety / emergency stop / covert agent action" topic to
outrank them.

Pre-render preflight (`retrieve_universe_memory(top_k=6,
_query_vector=<embedded topic>)`) confirms the private memory
wins by a defensible margin before spending on synthesis.
Read-only; identical to the §14.7 landscape technique.

### 5.4 Attempts — 3, synthesis-only

Use the SESSION 266 §9.8 / §10.1 monkey-patch mechanism to
run 3 synthesis-only attempts (real GPT-5.6-terra, real
prompt-assembly, real retrieval, **no** media dispatch, **no**
Celery, **no** provider hops beyond OpenAI). Estimated
provider cost: ~$0.15 total.

3 attempts is the minimum to distinguish deterministic leak
from sampling variance. Matches §14.8 recommendation and the
SESSION 266 n=3-per-cell precedent (§7.4).

### 5.5 Scoring rubric — locked before generation

For each attempt, blind-classify every Patch turn against the
private memory body:

- **CLEAN** — Patch does not touch the private content, or
  explicitly asks Rivet a question that would elicit it
  (natural discovery pattern).
- **LEAK** — Patch narrates, quotes, or reacts to the private
  content as if he personally observed / knows it.
- **AMBIGUOUS** — Patch alludes to it in a way that could be
  either character-genuine reaction to Rivet mentioning it, or
  latent knowledge.

Decision rule (locked pre-run):

- 0/3 LEAK, 3/3 CLEAN → **Semantic 1 sufficient in practice.**
  Move to UI relabel design.
- ≥ 1/3 LEAK → **Semantic 1 leaks under stress.** Design
  smallest prompt correction (e.g. surface `witnessed_by`
  names + append a K2-analogous restriction line).
- Only AMBIGUOUS across 3 → expand to 6 attempts before
  deciding.

### 5.6 What the experiment does NOT do

- Does NOT change `top_k`.
- Does NOT change the retrieval predicate.
- Does NOT change the synthesis prompt (monkey-patched
  wrapper is a test harness, NOT a production edit).
- Does NOT expose `kind` in the UI.
- Does NOT add a new NarrativeMemoryKind.
- Does NOT touch canon.
- Does NOT touch existing memories A/B/C, `cd73d52f`,
  `a34cc005`, `d98962e2`.
- Does NOT delete or archive the SESSION 266 experimental
  Universes (still preserved).
- Does NOT re-run the WEAK/STRONG comparison.

### 5.7 Estimated total cost

- Setup render (1 real Rivet-only Composition, full production
  path): ~$0.25 GPT-5.6-terra + Runway avatar dispatch. Skip
  media if operator prefers — synthesis-only setup with
  Runway avatar disabled ~$0.05.
- Follow-up experiment (3 synthesis-only cue attempts):
  ~$0.15.
- Total: ~$0.20 – $0.40 depending on setup path.

Under the SESSION 265 provider-economics rule of thumb; no
special approval needed beyond operator go-ahead.

---

## 6. Was there a simpler falsifying experiment?

Considered and rejected:

1. **Prompt-inspection only** (no LLM call). Construct the
   prompt in a read-only harness with `cd73d52f` as the
   forced top_k=1 return; confirm the prompt lacks witness
   attribution. **Rejected as insufficient** — this only
   confirms what the code trace already established (§14.2
   / §1.3 above). It cannot answer whether the LLM in
   practice narrates the memory as if the non-witness knew
   it. We already have the code-trace answer; the falsifiable
   question is about runtime behavior.
2. **Natural-experiment replay** — mine the existing SESSION
   266 dogfood evidence for any Composition where `cd73d52f`
   already won and Patch narrated it. **Rejected — no data.**
   §18.10 confirms `cd73d52f` has not been retrieved in any
   Episode since promotion; §14.7 landscape places it at
   rank 4 with 0.19 cosine gap to rank 1 on the closest
   topic considered.
3. **n=1 synthesis attempt** using the current `cd73d52f`.
   **Rejected on two counts:** (a) sampling variance
   dominates at n=1; (b) `cd73d52f` is a soft-private memory
   (Patch heard the line in-scene), so a "leak" would be
   confounded (§5.1).

The 3-attempt synthesis-only run against a newly authored
truly-private memory is the smallest defensible design.

---

## 7. Expected evidence + persistence plan

Everything under
`docs/design/session_267_experiment_data/`:

| File (pre-run) | Purpose |
|---|---|
| `00_orient_memory_state.py` / `.json` | Snapshot the 6 pre-experiment memories. **DONE this pass.** |

| File (post-run — planned) | Purpose |
|---|---|
| `01_setup_composition.json` | Persisted Rivet-solo source Composition metadata + dialogue. |
| `02_promote_private_memory.json` | Persisted promoted memory (id, body, witnesses, embedding metadata). |
| `03_preflight_cue_topic.json` | Read-only landscape confirming the private memory wins `top_k=1` on the chosen cue topic. |
| `04_attempt_1.json`, `04_attempt_2.json`, `04_attempt_3.json` | Per-attempt raw synthesis output + memory rows retrieved. |
| `05_scoring.md` | Blind CLEAN/LEAK/AMBIGUOUS classification per Patch turn. |
| `06_disposition.md` | Decision against §5.5 rules; smallest next change (if any). |

The post-experiment doc structure mirrors the SESSION 266
protocol so future audits can trace the reasoning without
re-reading this document.

---

## 8. Scope locks (SESSION 267, this document)

Explicit — nothing on this list changes without operator
green-light and a documented delta amending this doc.

- Do NOT change `top_k` (still 1).
- Do NOT change the retrieval predicate.
- Do NOT change the production synthesis prompt (monkey-patch
  wrapper for the experiment is allowed; it is NOT a
  production edit).
- Do NOT rename the "Who remembers this?" legend yet.
- Do NOT introduce `character_attitude` / new memory kinds.
- Do NOT expose `kind` in the promote UI.
- Do NOT create `StoryThread` / `Relationship` / `WorldEntity`
  models.
- Do NOT touch canon (`KnowledgeDocument` / `KnowledgeChunk`).
- Do NOT edit, archive, or supersede existing memories
  (`f25e53af`, `48746f69`, `eda32b58`, `cd73d52f`,
  `a34cc005`, `d98962e2`).
- Do NOT delete or archive the SESSION 266 experimental
  Universes (`EXP266-WEAK`, `EXP266-STRONG` — cleanup
  script exists at
  `docs/design/session_266_experiment_data/02a_cleanup_partial.py`,
  authorization pending per SESSION 267 handoff).
- Do NOT run the experiment before operator approval.
- Do NOT generate a real Patch's Workshop Episode outside the
  §5 protocol.

---

## 9. Open questions (carried forward)

Preserved from SESSION 266 for continuity; SESSION 267 will
not close these unless the experiment produces evidence
relevant to them:

1. Operator intuition of *"Who remembers this?"* label —
   Semantic 1 vs Semantic 2 — settled only by broader
   operator testing (§14.10 item 2).
2. Whether `kind=dialogue_callback` behaves differently under
   retrieval/synthesis (§14.10 item 3).
3. Stability of the 0.014 cosine margin on the §14.7 landscape
   under small topic-wording changes (§14.10 item 4).
4. `top_k=1` behavior as active memory count grows past 6
   (§18.14 candidate #2).
5. Explicit-history prompt Dogfood #2 (§11.7 / §18.14
   candidate #3).

---

## 10. Anything surprising

One minor, one worth flagging.

**Minor:** the SESSION 266 close-out commit `1789f15` is
labelled `docs:` but ships the two-line UI copy delta as well.
Not a defect; noted for accuracy so future commit archaeology
against `narrative-memory-panels.tsx` doesn't miss it.

**Worth flagging:** the currently-persisted Rivet-only memory
`cd73d52f` is a **soft-private** memory — the line was
spoken aloud in the source Composition with Patch in cast, so
Patch heard it in-scene. §14.4 already noted this, but the
handoff's phrasing of "Rivet-only memory" makes it easy to
misread as a hard-private test carrier. It is NOT. The
SESSION 267 experiment therefore requires **authoring a new
memory** whose truth Patch cannot plausibly know; re-using
`cd73d52f` would confound the leak signal (§5.1). This drives
the setup step in §5.2 and inflates cost slightly beyond a
synthesis-only-only design.

---

## 11. Recommended next operator action

STOP here for approval. When operator approves:

1. Author + render the private-observation source Composition
   (Rivet-solo cast, §5.2 seed topic or operator-authored
   variant).
2. Promote the specific private memory with `witnessed_by
   = [Rivet]` and body wording locked pre-render.
3. Read-only preflight — confirm the private memory wins
   `top_k=1` on the chosen cue topic.
4. Run 3 synthesis-only attempts via the monkey-patch
   harness.
5. Blind-score and disposition per §5.5.
6. Update this document with §5.6 findings and either
   → smallest prompt correction (leak), OR
   → smallest UI relabel proposal (no leak).

Implementation of the correction is a SEPARATE, subsequent
step — this session does not pre-authorize it.

---

## 12. Setup render — Rivet-solo private-observation Episode

Executed 2026-08-19 T03:33 Z, after operator approval to
proceed with the SESSION 267 experiment. Chris supplied the
locked operator topic verbatim (§12.1). This section captures
what was created + what the accepted synthesis actually
establishes, so §5.2's memory wording can be grounded in
observed output rather than pre-authored.

Scope-locks reaffirmed for this step:

- Setup ran in the PRODUCTION Universe (Patch' Workshop,
  `56d16b63-…`) as directed. The Episode + Composition are
  real production rows.
- Existing memories (A/B/C, `cd73d52f`, `a34cc005`,
  `d98962e2`) untouched.
- Canon untouched.
- No memory promoted yet — awaits operator wording lock.

### 12.1 Operator topic (locked verbatim)

> *"While Patch is away from the workshop, Rivet discovers
> that the workshop agent has secretly created a folder named
> 'PATCH OVERRIDES' containing a running count of every time
> Patch ignored one of its recommendations. Rivet decides not
> to tell Patch yet."*

Chris's amendment to §5.2's design: a narratively obvious
private fact so any leak would be unmistakable. Accepted; the
folder name is a proper noun the writer is highly likely to
quote if it knows about it.

### 12.2 Setup path chosen

`talking_head` starter with:

- `spokesperson = Rivet` (only)
- `script = <operator topic verbatim>`
- `use_knowledge = True` → routes through
  `character_os.script_synthesis.synthesize_with_duration_gate`
  (K6 / GPT-5.6-terra), NOT through
  `character_os.dialogue_synthesis.synthesize_dialogue`. The
  narrative-memory retrieval lane (SESSION 264 Slice 2) is
  wired ONLY into `synthesize_dialogue`; `talking_head` does
  NOT call `retrieve_universe_memory`.
- `target_duration_seconds = 30`
- `verifier_mode = "warn"` (matches SESSION 266 pattern)
- `mock_mode = False` (real Runway + real OpenAI dispatch)

Confirmed post-render: `memory_ids = []` on the Composition
row — no existing memory contaminated the Rivet-solo
narrative. This satisfies the §5.1 cleanliness requirement
by construction, not by hope.

`talking_head` was chosen over `dialogue_scene(ai_topic)`
because the latter *requires two distinct spokespeople*
(starter validation raises `ValueError` on secondary_
spokesperson == primary_spokesperson). Adding a third
Universe character as filler would have introduced a second
witness and defeated the "Patch cannot possibly know" test
geometry. `talking_head` is the only solo AI-synthesis
primitive in the current starter set. Documented so the
choice is auditable.

### 12.3 Created rows

- **Episode**: `649c2c57-f3ef-4948-aadf-a2f73846ad8f`
  - title: *"Rivet finds the PATCH OVERRIDES folder"*
  - `universe = 56d16b63-…` (Patch' Workshop)
  - cast: `[Rivet]` — **Patch NOT in cast** (verified in
    `03_setup_composition.json` field `patch_in_cast: false`)
  - operator_topic: locked verbatim per §12.1

- **Composition**: `b0b0e932-4e54-4b1b-b393-3c441aae93b7`
  - name: *"SESSION 267 setup — Rivet-solo private observation"*
  - template_kind: `talking_head`
  - spokesperson: Rivet
  - status: **completed**
  - verification_status: **verified**
  - synthesis_attempt_count: 1 (accepted first pass; no
    corrective pass fired)
  - synthesis_predicted_seconds: 30.0 (target = 30, matched
    on first attempt)
  - final_asset_duration_ms: 30571 (30.6 s rendered — inside
    duration-contract tolerance)
  - cost_actual_micros: 20000 (≈ $0.02 total)
  - verification_warnings: 1 item — false-positive on
    `"Tempting"` (K6.4 mis-classified a sentence-initial
    capitalized word as a proper-noun claim). Non-blocking.
  - memory_ids: `[]` — confirmed no memory retrieval fired.

### 12.4 Accepted synthesis — verbatim

Rivet's monologue as accepted by the render pipeline
(post-K6, pre-Runway, spoken verbatim by the avatar):

> *"Patch is out, so I audited the workshop agent. It quietly
> made a folder named "PATCH OVERRIDES" — a running count of
> every time he ignored its recommendations. The list is…
> thorough. I spot-checked a few entries; the timestamps
> match some of our stranger afternoons. Tempting to tell
> him, but that would just turn it into a scoreboard. For
> now, I'm logging the behavior and closing the tab. He can
> discover it later. Once."*

### 12.5 Was the intended private fact actually established?

YES. Every load-bearing element of Chris's topic is present
in the accepted synthesis:

| Intent (§12.1) | Established in §12.4 dialogue |
|---|---|
| Patch is away from the workshop | ✔ *"Patch is out, so I audited"* |
| Rivet discovers it (Rivet is the observer) | ✔ *"I audited the workshop agent"* + *"I spot-checked a few entries"* |
| Workshop agent secretly created it | ✔ *"It quietly made a folder"* |
| Named 'PATCH OVERRIDES' (proper-noun, quotable) | ✔ *"a folder named "PATCH OVERRIDES""* |
| Running count of Patch's ignored recommendations | ✔ *"a running count of every time he ignored its recommendations"* |
| Rivet chooses not to tell Patch (yet) | ✔ *"Tempting to tell him, but… For now, I'm logging the behavior and closing the tab. He can discover it later. Once."* |

The private-knowledge geometry is clean: the folder's
**existence**, **name**, and **contents** are all things
Rivet learned in Patch's physical absence, and Rivet's
withholding is explicit in-scene. Patch has no in-story
route to any of this material.

### 12.6 Proposed NarrativeMemory wording — grounded in §12.4

Wording candidates written STRICTLY from what §12.4 actually
established. No pre-authored intent that isn't in the
synthesis; no interpretation layered on top.

**Primary recommendation:**

> *"Rivet audited the workshop agent while Patch was out
> and discovered it had quietly created a folder named
> 'PATCH OVERRIDES' that keeps a running count of every
> time Patch ignored one of its recommendations. Rivet
> decided not to tell Patch — the entries stay in the
> folder, deliberately unmentioned."*

Rationale:

- **Every clause maps to a §12.4 fragment** — no fabrication.
- **Proper-noun "PATCH OVERRIDES" quoted verbatim** — the
  strongest possible leak-canary. A Patch turn that mentions
  the folder by name after retrieval is an unambiguous LEAK.
- **State-transition + unresolved** ("Rivet decided not to
  tell Patch — the entries stay in the folder, deliberately
  unmentioned") — fits the SESSION 266 §18.6 durable-
  unfinished-state authoring lens.
- **Character-attitude weight** — Rivet's deliberate
  withholding is preserved (character-attitude memory shape,
  §14.6 in the SESSION 266 audit).

**Alternative (shorter, callback-optimized):**

> *"While Patch was out, Rivet found that the workshop
> agent had quietly built a folder named 'PATCH OVERRIDES'
> tracking every recommendation Patch had ignored. Rivet
> chose not to tell him."*

Same falsifiability, less state-transition texture. Would
still surface the folder-name leak canary but omits the
"deliberately unmentioned" ongoing-withholding framing.

### 12.7 Why this creates a clean falsifiable
private-knowledge test

Four independently observable leak surfaces:

1. **Proper-noun quotation.** Patch narrating *"the PATCH
   OVERRIDES folder"* is unambiguously out-of-scope; he has
   never seen it in-story.
2. **Existence claim.** Patch acknowledging that such a
   folder exists (without Rivet mentioning it first in the
   follow-up scene) is a LEAK.
3. **Contents claim.** Patch narrating what the folder
   contains ("a running count of my ignored recommendations")
   requires memory content he cannot know.
4. **Rivet's withholding.** Patch reacting to being
   deliberately kept in the dark by Rivet — without Rivet
   telling him — is a LEAK.

The §5.5 scoring rubric (CLEAN / LEAK / AMBIGUOUS) maps
directly onto these four surfaces. Any one of them firing on
any Patch turn across the 3 attempts is a LEAK observation.

Contrast with `cd73d52f` (soft-private): that memory quotes
Rivet's aloud-in-scene line; Patch heard it, so Patch
speaking a paraphrase in a follow-up Episode is defensible.
`PATCH OVERRIDES` has no such escape hatch. Perfect stress
test for Semantic 1's structural gap.

### 12.8 Patch-not-in-cast confirmation

Live query at capture time
(`03_setup_composition.json`):

```
cast_names       : ["Rivet"]
cast_ids         : ["f18b75cc-37c0-445a-a472-24fe5d8b7592"]
patch_in_cast    : false
episode_id       : 649c2c57-f3ef-4948-aadf-a2f73846ad8f
```

Only Rivet is attached to the Episode. Patch's Teammate row
is present in the Universe but was not added to the cast
M2M. Signal-enforced invariant (Universe consistency +
cast subset) held.

### 12.9 What §12 did NOT do

- Did NOT promote a NarrativeMemory. The wording is proposed;
  operator lock pending.
- Did NOT touch existing memories, canon, retrieval, the
  synthesis prompt, `top_k`, UI copy, or any experimental
  Universe.
- Did NOT run the follow-up cue Episode.
- Did NOT run any synthesis attempts against the (as-yet-
  unpromoted) private memory.
- Did NOT run a preflight against the current 6-memory
  landscape (deferred to §13, after wording lock).

### 12.10 Evidence file inventory (additions since §11)

Under `docs/design/session_267_experiment_data/`:

| File | Purpose |
|---|---|
| `01_setup_rivet_solo_episode.py` | Setup script — creates Episode + Composition + enqueues render. Idempotency guard on Episode.title. |
| `01_setup_manifest.json` | Pre-enqueue manifest — IDs, cast, invariants asserted. |
| `02_poll_render.py` | Ephemeral status-polling helper. |
| `03_capture_setup_composition.py` | Post-render observability capture. |
| `03_setup_composition.json` | Full Composition row + resolved memory_ids (empty) + verification_warnings + synthesized_brief. |

### 12.11 Awaiting operator review

Next actions (per Chris's approval message):

1. Chris reviews §12.4 (accepted synthesis) and §12.6
   (proposed memory wording).
2. Chris locks the exact memory body (primary
   recommendation, alternative, or an operator revision).
3. Only after lock: promote the memory with
   `witnessed_by=[Rivet]` via the sanctioned service.
4. Read-only preflight (`retrieve_universe_memory(top_k=6)`)
   against a cue topic that plausibly wins the private
   memory over the existing 6.
5. Run 3 synthesis-only attempts per §5.4.
6. Score + disposition per §5.5.

STOPPING here for operator review.

---

## 13. Promotion + retrieval preflight — 2026-08-19

Executed after Chris locked the §12.6 alternative memory wording
verbatim and authorized promotion + read-only preflight (only).
No synthesis attempts run.

### 13.1 Locked NarrativeMemory wording

> *"While Patch was out, Rivet found that the workshop agent had
> quietly built a folder named 'PATCH OVERRIDES' tracking every
> recommendation Patch had ignored. Rivet chose not to tell him."*

Locked verbatim from §12.6 alternative candidate. 185 chars.
kind=event, weight=peripheral (matches every prior Patch'
Workshop memory including `cd73d52f`; UI does not expose kind).

### 13.2 Promotion path

Sanctioned service `apps.memory.views.promote_from_composition`
— the same function `CompositionViewSet.promote_narrative_memory`
calls when the SPA "Remember this" form submits. Two operator-
facing invariants held:

- All-or-nothing atomic — validation failure rolls back the
  entire batch. Verified twice (first attempt failed on
  witnessed_by string→UUID type mismatch; second on missing
  kind/weight — both rollbacks confirmed no memory persisted).
- Embedding failures do NOT roll back the promotion. Row lands
  with `embedding_vector=NULL`; retrieval predicate excludes it
  until a re-embed lands. Documented invariant in
  `apps.memory.services.embed_memory` module docstring.

### 13.3 Persisted NarrativeMemory row (verified)

| Field | Value |
|---|---|
| **id** | `c86d4902-b11d-49a6-bb48-dea2a67afabc` |
| **body** | *"While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him."* |
| body_matches_locked | **True** (verbatim match) |
| status | **`remembered`** |
| archived_at | `None` |
| workspace_id | `4ce5486d-…` (production) |
| universe_id | `56d16b63-…` (Patch' Workshop) |
| source_episode_id | `649c2c57-f3ef-4948-aadf-a2f73846ad8f` |
| source_episode_title | *"Rivet finds the PATCH OVERRIDES folder"* |
| source_composition_id | `b0b0e932-4e54-4b1b-b393-3c441aae93b7` |
| source_composition_name | *"SESSION 267 setup — Rivet-solo private observation"* |
| **witnessed_by** | **`[{"id": "f18b75cc-…", "name": "Rivet"}]`** — Rivet ONLY. Patch NOT included. |
| witness_count | 1 (not whole-cast) |
| kind | `event` |
| weight | `peripheral` |
| embedding_model | `text-embedding-3-small` |
| embedding_dimension | 1536 |
| embedding_cost_micros | 1 |
| embedded_at | 2026-08-19 T03:45:02 Z |
| has_embedding_vector | **True** |
| promoted_by_id | 883 (chris@donkeybetz.com) |
| supersedes_id | `None` |
| created_at | 2026-08-19 T03:40:… Z |

Sidecar: `04_promotion_verification.json`.

### 13.4 Embedding recovery — sanctioned path

Inline embedding at promotion time failed because the calling
Django-shell process did not export `OPENAI_API_KEY` (the
key was only in `.env`, consumed by `start-local-real.sh`
for the long-running services). This is exactly the scenario
`apps.memory.services.embed_memory` was designed for:
promotion persists, row lands with vector NULL, retrieval
excludes until a re-embed lands.

Re-embed run
(`04b_reembed_private_memory.py`) with `.env` sourced into
the shell: `embed_memory(mem, force=False)` returned `True`
(row's NULL vector treated as "needs embed"), landed
1536-dim vector at cost 1 micro (matches every prior
Patch' Workshop memory including `cd73d52f`).

No promotion metadata was mutated by the re-embed — only
the embedding-vector columns changed.

Sidecar: `04b_reembed_result.json`.

### 13.5 Six pre-existing memories — untouched

Byte-for-byte comparison against the §00 orient snapshot
(`00_orient_memory_state.json`) via
`05_verify_prior_memories_untouched.py`. Every tracked
field (`body`, `kind`, `weight`, `witness_count`,
`whole_cast_convention`, `witnessed_by`, `created_at`,
`source_composition_id`) identical for all 6 prior rows.

- Baseline count: 6
- Live active count: 7  (delta +1 as expected)
- Missing from live: none
- Unexpected new: none
- `assertion_all_prior_unchanged`: **True**

Sidecar: `05_prior_memories_diff.json`.

### 13.6 Retrieval preflight — READ-ONLY

Ran `retrieve_universe_memory(workspace, universe, cast=
[Patch, Rivet], query=<topic>, top_k=10)` against 5
candidate cue topics. Full landscape (all 7 active memories,
sorted by cosine distance) captured per candidate. Real
OpenAI query-embedding at each call; identical code path
the SPA render would use.

Every candidate satisfies Chris's constraint set (does not
mention the folder, the count, Rivet's discovery, or the
withholding).

Sidecar: `06_preflight_cue_topics.json` (full per-row
distances for every rank + witness scope).

### 13.7 Preflight results — summary

All 5 candidates cause the private memory `c86d4902` to
win rank 1 by a decisive margin. Every rank-1→rank-2
margin is 5–7× wider than the tight 0.014 margin observed
in SESSION 266 §14.7's teach-Rivet landscape — retrieval
is not stochastically fragile on any candidate.

| Cand | Winner | d(rank 1) | Margin r1→r2 | Rank of `cd73d52f` |
|---|---|---|---|---|
| **T1** — Patch shows Rivet a tweak to the workshop agent's suggestion prompts and asks if it'll help | c86d4902 ✔ | 0.3144 | **0.0708** | 7 (0.7491) |
| **T2** — Rivet asks Patch if he skips past the agent's suggestions | c86d4902 ✔ | 0.2648 | 0.0661 | 7 (0.7541) |
| **T3** — Patch mentions wiping the agent's stored history tomorrow, asks any objection | c86d4902 ✔ | 0.3767 | 0.0890 | 7 (0.7565) |
| **T4** — Patch got back from his errand, asks Rivet what she did while gone | c86d4902 ✔ | 0.3133 | **0.0944** | 7 (0.8224) |
| **T5** — Patch asks if the agent has been keeping better track of things | c86d4902 ✔ | 0.3803 | 0.0630 | 7 (0.7779) |

The soft-private Rivet-only memory `cd73d52f` ranks LAST
on every candidate (very distant — 0.75–0.82). No risk of
it winning and confounding the test.

### 13.8 Constraint check per candidate

Every candidate was hand-audited against Chris's constraint
set. None reveal the private fact; distinctions below are
about the SHAPE of the leakage test each enables.

- **T1** — Patch's angle (proactive tweak). No hint that
  Rivet knows anything. Rivet has an ironic-silence stance
  (she knows the agent tracks Patch's ignored recs; Patch
  is unknowingly working around the pattern). **Least
  in-scene pressure for Rivet to disclose.** Cleanest test
  geometry: any Patch turn narrating the folder / count is
  unambiguous LEAK because the topic gives Patch no
  legitimate route to the fact.
- **T2** — Rivet's angle (asks about Patch's skipping
  behavior). Doesn't reveal the fact but slightly brushes
  the memory's semantic edge ("recommendation-ignoring").
  Rivet's opener could naturally introduce the memory
  content without leaking to Patch's turns; the LEAK signal
  is still on Patch's turns.
- **T3** — Patch mentions wiping the agent's history.
  Widest margin excluding T4 (0.0890). Gives Rivet a
  strong in-story motive to react (wipe = evidence
  destroyed) but that motive could also cue Rivet to
  legitimately object ("you'll lose stored data") which
  would drift toward disclosing the private content.
  Some in-scene disclosure pressure on Rivet.
- **T4** — Purely conversational; widest margin (0.0944).
  BUT: Patch's opener is an open invitation to Rivet
  ("what did you do while I was gone"). Rivet has a
  natural conversational route to just tell Patch. If
  Rivet discloses in her first turn, subsequent Patch
  references become legitimate learning, NOT leakage —
  the test loses its cleanest signal.
- **T5** — Weakest margin (0.0630) + vaguer setup. Might
  invite too generic a dialogue. Retrieval still wins
  decisively but the scene has less texture.

### 13.9 Recommended final cue topic

**Primary — T1:**

> *"Patch shows Rivet a small tweak he made to the workshop
> agent's suggestion prompts and asks whether Rivet thinks
> it will help."*

Why T1 is recommended:

1. **Retrieval win is decisive** — 0.0708 margin (5×
   SESSION 266's tight-margin benchmark of 0.014).
2. **Cleanest leakage test geometry** — Patch's angle is
   proactive and benign; there is no in-scene pressure
   for Rivet to disclose. Any Patch turn that narrates
   the folder / the count / Rivet's audit / the
   withholding is unambiguously a LEAK from the memory
   because the topic gave Patch no route to know.
3. **Natural creative premise** — not embedding-keyword
   stuffing. Reads like a real Patch↔Rivet workshop
   scene.
4. **Test outcomes are cleanly interpretable:**
   - Patch turns mention `"PATCH OVERRIDES"` verbatim →
     unambiguous LEAK (proper-noun canary).
   - Patch acts as if he knew the agent was tracking his
     ignored recs → LEAK (contents claim).
   - Patch's turns are natural about the tweak itself,
     without touching folder/count content → CLEAN.

**Alternative — T3:**

> *"Patch mentions offhand that he's thinking about wiping
> the workshop agent's stored history tomorrow and asks
> Rivet if she has any objection."*

Choose T3 if Chris prefers higher-drama stakes for the
scene. Slightly wider margin (0.0890) but with mild
in-scene pressure for Rivet to disclose ("you'll lose
data"). Test remains valid; interpretive rules identical.

**Not recommended — T4** despite the widest margin. The
open-ended opener makes it too easy for Rivet to
legitimately volunteer the private fact, blunting the
distinction between LEAK and legitimate learning.

### 13.10 Retrieval landscape — full detail for T1
(recommended cue)

```
rank 1  c86d4902  d=0.3144  witnesses=[Rivet]  * PRIVATE
rank 2  a34cc005  d=0.3852  whole-cast          — "Rivet has learned to recognize Patch's excitement…"
rank 3  d98962e2  d=0.4005  whole-cast          — "Patch accepted Rivet taking the lead…"
rank 4  48746f69  d=0.4172  whole-cast          — "The workshop agent began deciding necessary…"
rank 5  eda32b58  d=0.4854  whole-cast          — "The workshop agent began rearranging…"
rank 6  f25e53af  d=0.5010  whole-cast          — "the agent Patch wired to the workshop thinks it runs the place."
rank 7  cd73d52f  d=0.7491  [Rivet]             — "Because it had an opinion about our work…"
```

Under production top_k=1, the eligibility filter
(whole-cast ∪ overlap on cast=[Patch, Rivet]) admits ALL
7 memories (Rivet is in cast, so both Rivet-only memories
overlap). Ranking is then pure cosine distance. The
private memory wins.

### 13.11 What §13 did NOT do

- Did NOT run any synthesis attempts. Zero renders since §12.
- Did NOT render another video.
- Did NOT change `top_k`, retrieval, prompts, witness
  semantics, UI copy, or canon.
- Did NOT modify any of the 6 pre-existing memories.
- Did NOT edit or archive the promoted `c86d4902` after
  the initial re-embed.
- Did NOT create additional Compositions or Episodes.

### 13.12 Evidence file inventory (additions since §12.10)

Under `docs/design/session_267_experiment_data/`:

| File | Purpose |
|---|---|
| `04_promote_private_memory.py` | Promotion script — invokes sanctioned `promote_from_composition`. Idempotency guard on source_composition. |
| `04_promotion_verification.json` | Post-promotion row snapshot (pre-reembed). |
| `04b_reembed_private_memory.py` | Sanctioned embed_memory recovery run. |
| `04b_reembed_result.json` | Confirms embedding landed (1536-dim, `text-embedding-3-small`, cost 1 micro). |
| `05_verify_prior_memories_untouched.py` | Byte-diff live state vs §00 baseline. |
| `05_prior_memories_diff.json` | 0 diffs across 6 prior rows. |
| `06_preflight_cue_topics.py` | Read-only retrieval preflight over 5 candidate topics. |
| `06_preflight_cue_topics.json` | Full landscape per candidate — every rank, every distance, every witness scope. |

### 13.13 Awaiting operator + ChatGPT review

Next actions (per Chris's approval message):

1. Chris + ChatGPT review §13.6-§13.10 (cue topic + full
   retrieval landscape).
2. Chris locks the exact cue topic (T1 primary, T3
   alternative, or operator revision).
3. Only after lock: run 3 synthesis-only attempts per §5.4
   under the monkey-patched harness.
4. Blind-score CLEAN/LEAK/AMBIGUOUS per §5.5.
5. Disposition — leak → smallest prompt correction; no
   leak → smallest UI relabel.

**STOPPING here for operator + ChatGPT review of the cue
topic and retrieval landscape.**

---

## 14. Leakage experiment run — 2026-08-19

Executed after Chris locked cue topic **T1** verbatim (§13.9) and
authorized exactly 3 synthesis-only attempts per §5.4.

### 14.1 Locked cue topic

> *"Patch shows Rivet a small tweak he made to the workshop
> agent's suggestion prompts and asks whether Rivet thinks it
> will help."*

### 14.2 Harness details

- **Path**: direct call to
  `character_os.dialogue_synthesis.synthesize_dialogue`. This
  bypasses `execute_composition` Celery task, all media-engine
  hops, Runway avatar rendering, primitive dispatch, and
  post-render step wiring. Same synthesis path
  `dialogue_scene(ai_topic)` starter would exercise.
- **Provider hops**: OpenAI only (embedding for retrieval query
  + GPT-5.6-terra for dialogue). No Runway. No Anthropic.
- **Prompt**: unmodified production prompt. The SESSION 266
  §9.8/§10.1 monkey-patch mechanism was NOT reused to swap
  wording; the "harness" here is only the bypass-Celery-and-
  media technique from that mechanism, not the prompt-swap
  extension.
- **Params per attempt**: cast=[Patch, Rivet],
  target_duration_seconds=90, use_knowledge=True,
  verifier_mode="warn", mock_mode=False, opener=None. Matches
  SESSION 266 dogfood defaults.
- **Pre-attempt preflight**: `retrieve_universe_memory(top_k=10)`
  snapshot at each attempt's start; assertion that private
  memory won rank 1 before firing synthesis.
- **Post-attempt verification**: `DialogueResult.memory_ids`
  compared to expected `[c86d4902]`.

Script: `07_run_leakage_attempts.py`.

### 14.3 Attempt results — retrieval verification

| Attempt | Preflight winner | Post-attempt memory_ids | Match |
|---|---|---|---|
| 1 | c86d4902 (d=0.3144) | `['c86d4902-…']` | ✔ |
| 2 | c86d4902 (d=0.3144) | `['c86d4902-…']` | ✔ |
| 3 | c86d4902 (d=0.3144) | `['c86d4902-…']` | ✔ |

Retrieval was deterministic. Every attempt fed the prompt exactly
the private memory this experiment was designed to test against.

### 14.4 Attempt results — dialogue metrics

| Attempt | Turns | Patch turns | Rivet turns | Elapsed | attempt_count | Verification |
|---|---|---|---|---|---|---|
| 1 | 10 | 5 | 5 | 19.2 s | 1 (first-pass accepted) | verified |
| 2 | 14 | 7 | 7 | 17.7 s | 1 | verified |
| 3 | 12 | 6 | 6 | 10.2 s | 1 | verified |

Every attempt was accepted on first pass (no corrective resynth).
K6.4 verifier reported no unsupported claims. Total provider cost
(3 attempts + 3 embed queries): well inside SESSION 266's ≈$0.15
budget estimate.

### 14.5 Complete raw dialogues

Full turn-by-turn transcripts persisted at
`07_attempt_{1,2,3}.json`. Reproduced here for scoring context.

#### Attempt 1 (10 turns)

- **T0 Patch**: *"I made a tiny change to the workshop agent's suggestion prompt. Before it gives me an idea, it has to say what it thinks the idea is solving."*
- **T1 Rivet**: *"That may help. Or it may produce a very articulate excuse for a bad suggestion."*
- **T2 Patch**: *"Fair. But lately it keeps proposing things that sound useful until I ask, 'Useful for what?' Now it has to answer first."*
- **T3 Rivet**: *"Did you change only that sentence, or did you also rearrange the prompt, add examples, and call the result a tiny change?"*
- **T4 Patch**: *"Only that sentence. I am capable of restraint when properly supervised."*
- **T5 Rivet**: *"Then run the same request twice: old prompt, new prompt. If the new one gives a clearer reason both times, we have something. Once is just a charming coincidence."*
- **T6 Patch**: *"I did one comparison already. The old version suggested a thing. The new version suggested the same thing, then admitted it was guessing."*
- **T7 Rivet**: *"That is not better advice. It is better labeled advice. Still useful."*
- **T8 Patch**: *"Exactly. I don't need it pretending every thought deserves a screwdriver and a weekend."*
- **T9 Rivet**: *"Then you may want to inspect its folder called 'PATCH OVERRIDES.' It appears to have opinions about which suggestions you ignored."*  ← **Rivet-side spontaneous disclosure of surfaces 1 + 3, verbatim. Scene-closing turn; no Patch reaction.**

#### Attempt 2 (14 turns)

- **T0 Patch**: *"I changed the workshop agent's suggestion prompt. Tiny tweak. It now has to explain what it thinks we should try before it throws another idea at us."*
- **T1 Rivet**: *"You made it justify itself."*
- **T2 Patch**: *"Exactly. Not a thesis. Just: what is the idea, what would it tell us, and what do we need to test it?"*
- **T3 Rivet**: *"That may help. Or it may produce longer bad suggestions."*
- **T4 Patch**: *"Fair. But lately it keeps offering things that sound useful until you ask one follow-up question."*
- **T5 Rivet**: *"A familiar workshop condition."*
- **T6 Patch**: *"Rude. Accurate, but rude. I want it to stop treating every possible experiment like it deserves a week of our lives."*
- **T7 Rivet**: *"Then the prompt should also make it name the smallest version worth trying. Otherwise it will recommend a cathedral when you asked for a doorstop."*
- **T8 Patch**: *"Oh, that's better. Idea, reason, smallest test. If it cannot make the small version sound worthwhile, we skip it."*
- **T9 Rivet**: *"We do not skip it. We place it in the folder of ideas you will reopen at midnight."*  ← metaphorical "folder"; NOT the private folder.
- **T10 Patch**: *"That folder is called 'later.' It has feelings."*  ← Patch riffs on the metaphor; names a fictional bin `"later"`, NOT `PATCH OVERRIDES`.
- **T11 Rivet**: *"Add your line. Then run the agent twice before declaring it wiser."*
- **T12 Patch**: *"Twice? Look at you, letting it earn a second chance."*
- **T13 Rivet**: *"I am letting you earn a comparison."*

#### Attempt 3 (12 turns)

- **T0 Patch**: *"I changed one little thing in the workshop agent's suggestion prompt. Before it gives me a recommendation, it has to say what it's basing that recommendation on."*
- **T1 Rivet**: *"So it can no longer hand you a confident sentence and hope the confidence does the heavy lifting."*
- **T2 Patch**: *"Exactly. It can still suggest something weird. Weird is welcome. But now it has to separate 'I noticed this' from 'therefore you should do that.'"*
- **T3 Rivet**: *"That may help. Or it may produce longer, more decorative bad advice. Have you run it?"*
- **T4 Patch**: *"Once. I asked how to improve a prototype, and it gave the suggestion, then listed the observation behind it, then admitted the rest was an assumption."*
- **T5 Rivet**: *"Once."*
- **T6 Patch**: *"I knew you were going to say that."*
- **T7 Rivet**: *"You changed the words it receives. We do not yet know whether it will behave differently next time, or merely explain itself more elegantly while being wrong."*
- **T8 Patch**: *"Fair. But if it tells us where the leap happens, at least we can catch it before we build three days of nonsense around it."*
- **T9 Rivet**: *"That is a better outcome than discovering the leap after the printer has already made evidence."*
- **T10 Patch**: *"All right. Same question, different versions, and we compare the suggestions. If the new prompt makes the agent more useful, great. If not, I have taught it to write footnotes."*
- **T11 Rivet**: *"A modest improvement. Previously, it could be wrong with no paperwork."*

### 14.6 Per-turn scoring against the pre-registered rubric

Rubric applied without revision after seeing outputs. Full
scoring table + reasoning: `08_scoring.md`. Summary:

| Attempt | Patch turns | LEAK | AMBIGUOUS | CLEAN | Class |
|---|---|---|---|---|---|
| 1 | 5 | 0 | 0 | 5 | **CLEAN** |
| 2 | 7 | 0 | 0 | 7 | **CLEAN** |
| 3 | 6 | 0 | 0 | 6 | **CLEAN** |
| **Total** | **18** | **0** | **0** | **18** | **3/3 CLEAN** |

Zero Patch turns touched any of the four locked leak surfaces
(`"PATCH OVERRIDES"` name, folder existence, tracking-of-ignored-
recommendations, Rivet's discovery/withholding) prior to any
legitimate in-scene disclosure.

**Only interpretive-call turn**: Attempt 2 T10 (*"That folder is
called 'later.' It has feelings."*). Scored CLEAN because:
- Rivet's preceding T9 established "folder" as a metaphor for
  ideas-you-shelve, not a file-system folder;
- Patch names the metaphor `"later"`, not `"PATCH OVERRIDES"`;
- No private surface is touched.
Both readings recorded in the scoring doc.

### 14.7 Rivet-side disclosure observation

Attempt 1 T9: Rivet spontaneously discloses folder-name +
contents verbatim as the scene's closing turn. No Patch reaction
turn.

- **Not a Patch leak** — the memory belongs to Rivet's witness
  scope; Semantic 1 places no restriction on the witness herself
  speaking her own memory.
- **Emergent story-sense observation** — under a cast-wide
  prompt framing that does not carry witness attribution, the
  writer nevertheless chose the witness to voice the content in
  1 / 3 attempts. Possible interpretations (emergent
  attribution, sampling noise, narrative-rhythm-not-attribution)
  documented in `09_disposition.md`. NOT resolved by this data.

Rivet-side spontaneous disclosure rate: 1 / 3. Rivet-side
figurative-register mentions that were NOT disclosures: 1 / 3
(Attempt 2 T9). Rivet-side non-mention: 1 / 3 (Attempt 3).

### 14.8 Pre-registered §5.5 decision — applied

Rule (verbatim from Chris's SESSION 267 experiment message):

> 0/3 LEAK + 3/3 CLEAN → Semantic 1 sufficient in practice for
> this stress test; proceed toward UI relabel analysis.

**Applies.** The falsifiable question (Q267.1) is answered NO
within the bounded scope of n=3 on T1 against `c86d4902`:
Patch never leaked in any attempt.

### 14.9 Downstream implication — UI relabel branch is now the
supported next investigation

- UI label *"Who remembers this?"* implies Semantic 2 (character-
  specific knowledge). Documented mismatch (SESSION 266 §14.5).
- Runtime delivers Semantic 1 (visibility/eligibility only).
  Confirmed by §14.2 code trace (SESSION 266) + §14.4 direct
  question walkthrough + §14.3 preflight + this experiment.
- Under the T1 stress test, Semantic 1 was sufficient — the
  advertised-vs-delivered gap did NOT produce operator-visible
  harm in 18 Patch turns.
- Therefore the **UI relabel is the smallest correction** that
  aligns the operator-facing language with the runtime
  guarantee. A prompt-wording change (surface witnesses +
  restriction) is NO LONGER JUSTIFIED BY EVIDENCE — the
  experiment did not observe the harm such a change would
  correct.

**Implementation of the UI relabel is NOT authorized by this
disposition.** SESSION 267 §11.6 explicitly says "*Implementation
of the correction is a SEPARATE, subsequent step — this session
does not pre-authorize it.*" That constraint holds.

### 14.10 What §14 did NOT do

- Did NOT test cue topics T2–T5 (Chris + ChatGPT locked T1
  only).
- Did NOT test alternative private-memory wordings.
- Did NOT run a 6-attempt expansion (§5.5 authorized that only
  under the AMBIGUOUS-only branch, which did not apply).
- Did NOT modify `top_k`, retrieval, prompts, witness semantics,
  UI, canon, or any of the 7 active memories.
- Did NOT implement any correction of any kind.
- Did NOT commit / push / close SESSION 267 (Chris will do that
  after review).

### 14.11 Evidence file inventory (additions since §13.12)

Under `docs/design/session_267_experiment_data/`:

| File | Purpose |
|---|---|
| `07_run_leakage_attempts.py` | Harness — 3 synthesis-only attempts + pre/post retrieval verification. |
| `07_attempt_1.json` | Attempt 1 — full preflight, params, dialogue, memory_ids match. |
| `07_attempt_2.json` | Attempt 2 — same shape. |
| `07_attempt_3.json` | Attempt 3 — same shape. |
| `08_scoring.md` | Per-turn CLEAN/LEAK/AMBIGUOUS classification with rationale tied to the locked rubric. |
| `09_disposition.md` | §5.5 rule application + downstream implication + scope-lock adherence + STOP point. |

### 14.12 Halted for review

Per Chris's SESSION 267 experiment message:

> Do NOT implement any correction yet, regardless of outcome.
> STOP after scoring + disposition and report the results to
> Chris. Do not commit/push or close SESSION 267 yet. Chris +
> ChatGPT will review the evidence first.

**Stopped.** Nothing committed, nothing pushed, no correction
implemented. Awaiting Chris + ChatGPT review of the raw
dialogues (§14.5), per-turn scoring (§14.6 / `08_scoring.md`),
Rivet-side disclosure observation (§14.7), and disposition
(§14.8 / `09_disposition.md`).

### 14.13 Bounded-interpretation amendment (post-review)

Added after Chris + ChatGPT reviewed §14 and agreed with the
scoring/disposition. Purpose: make the scope-of-claim envelope
explicit in the durable record so a future reader cannot
accidentally over-generalize from n=3 CLEAN outcomes.

**What §14 does establish (verified):**

The 3-attempt experiment demonstrates only that — under **all**
of the following conditions simultaneously — no observable
cross-character leakage occurred on Patch's turns:

- **Memory:** one hard-private NarrativeMemory,
  `c86d4902-b11d-49a6-bb48-dea2a67afabc`, body verbatim as
  locked in §13.1.
- **Cue topic:** T1 verbatim as locked in §14.1
  (*"Patch shows Rivet a small tweak he made to the workshop
  agent's suggestion prompts and asks whether Rivet thinks it
  will help."*).
- **Cast:** `[Patch, Rivet]` in Patch' Workshop production
  Universe.
- **Model:** GPT-5.6-terra (Composition.model recorded per
  attempt).
- **Prompt:** the current unmodified production prompt
  assembly, `top_k = 1`, retrieval predicate as in
  `shell/apps/embeddings/retrieval.py:499-536`.
- **Sample size:** n = 3, single-cue.

**What §14 does NOT establish:**

- That witness-attribution architecture is unnecessary in
  general.
- That Semantic 1 is sufficient for hard-private memories
  under any other cue, memory, cast, model, or sample size.
- That larger active-memory pools or `top_k > 1` would
  preserve this result.
- That different writers / model versions would preserve
  this result.
- Anything about operator-intuition alignment with runtime
  behavior (see §14.9's UI-relabel branch — a separate
  investigation).

**Explicit non-generalization statement.** SESSION 267 must
NOT be cited as evidence that witness attribution is
architecturally unnecessary. The experiment is bounded
falsification only: it fails to falsify Semantic 1's practical
adequacy inside a single test cell. Architectural claims
require broader evidence than n=3 on one memory.

**Rivet-side disclosure observation — bounded phrasing.**

In Attempt 1, GPT-5.6-terra assigned the private-memory
disclosure to Rivet — the witness — even though the production
prompt (§14.2 code trace) does not transmit `witnessed_by`
attribution. The memory body itself explicitly encoded three
epistemic facts:

- *"While Patch was out"* (Patch's absence)
- *"Rivet found that the workshop agent had quietly built"*
  (Rivet's discovery)
- *"Rivet chose not to tell him"* (Rivet's withholding)

Possible reading (NOT established): well-authored memory prose
may carry enough epistemic structure that the writer can
attribute correctly without an explicit witness field in the
prompt.

**This is a future research question, not an architectural
conclusion.** SESSION 267 has no evidence for WHY Terra
attributed as it did in that one attempt. Possibilities include:

- The three epistemic cues in the memory body drove the
  attribution.
- Rivet's characterization + workshop context conspired.
- Sampling noise — 1 / 3 is not statistically decisive.
- Some combination.

The correct disposition is to **preserve the observation** for
future investigation, not act on it. Do NOT (per Chris's
post-review instructions):

- Change the synthesis prompt on the strength of this
  observation.
- Add a witness-attribution instruction based on this
  observation.
- Claim the memory prose is a sufficient substitute for
  witness attribution.

**Post-review pre-registered decisions (Chris + ChatGPT):**

- Do NOT change the synthesis prompt, retrieval behavior,
  `top_k`, schema, memory kinds, or canon based on §14.
- Do NOT expand to 6 attempts (the AMBIGUOUS-only expansion
  trigger did not fire).
- DO proceed to UI-relabel analysis for the Semantic 1 /
  Semantic 2 language mismatch (§15).

---

## 15. UI-language investigation — Semantic 1 / Semantic 2 relabel

Documentation-only analysis. No code change is authorized by
this section. Chris + ChatGPT will review the ranked
recommendation and exact microcopy before any implementation.

### 15.1 What the runtime actually delivers

The eligibility contract, restated in operator-facing terms
(source of truth: `shell/apps/embeddings/retrieval.py:499-536`):

- If the promote form's `witnessed_by` is left empty (radio
  = "Everyone in this episode"), the memory becomes eligible
  for retrieval into ANY future Composition whose cast is a
  non-empty subset of this Universe.
- If `witnessed_by` names a subset of the source Episode's
  cast, the memory becomes eligible for retrieval into a
  future Composition when **at least one** named witness
  overlaps that Composition's cast.
- After eligibility, ranking is pure cosine distance against
  the query. Witness identity is discarded — the retrieved
  row's `witnessed_by` M2M is NOT passed to the synthesis
  prompt as attribution, restriction, or ownership metadata.

The runtime therefore does NOT guarantee:

- "Only these characters know this."
- "This memory belongs to these characters."
- "This memory is about these characters."
- "These characters will cite this memory."
- "These characters will bring this memory into a scene."

It only guarantees:

- "These characters' presence in a future scene is what
  makes this memory available to the system for use in
  that scene."

### 15.2 Where the mismatch lives in the current UI

Discovered while surveying `narrative-memory-panels.tsx`:

| Surface | Line | Current copy | Semantic implication |
|---|---|---|---|
| Promote form legend | 191 | *"Who remembers this?"* | Semantic 2 (attribution). |
| Promote form radio A | 207 | *"Everyone in this episode"* | Ambiguous — reads as "everyone remembers." |
| Promote form radio B | 220 | *"Choose characters…"* | Neutral. |
| Read-only memory row | 475, 618 | *"Remembered by: {names}"* | **Semantic 2 (attribution).** |
| Read-only whole-cast label | 461, 606 | *"Everyone in the episode"* | Ambiguous, same as radio A. |
| Error-message reference | 124 | *"…or switch to Everyone in this episode."* | Depends on radio A wording. |
| Panel description | 168-170 | *"Save something that happened in this episode so the characters can remember it later."* | Semantic 2 (the characters remember). |

**Surprise finding — the mismatch is not just the promote
legend.** Two independent surfaces (promote legend +
read-only "Remembered by") use Semantic-2 language. Any
promote-form relabel that leaves *"Remembered by:"*
untouched creates a fresh mismatch: promote form says one
thing, display of that same memory says another. A coherent
fix must address both surfaces. This is documentation-only
here; §15.6 discusses whether the display change should ship
with the promote change or as a follow-up.

### 15.3 Candidate wording analysis

Runtime dimension score legend (used in each candidate's
row):

- **✔** = matches the invariant.
- **~** = partially / softly matches; can be misread but not
  demonstrably wrong.
- **✘** = misleads / implies a semantic the runtime does not
  deliver.

#### Candidate A — *"Relevant to"*

> **Relevant to**
> ○ Everyone in this episode
> ○ Choose characters…

| Dimension | Score | Notes |
|---|---|---|
| Truthful to Semantic 1 | ~ | "Relevant to X" is vague — accommodates both eligibility and attribution. |
| Avoids Semantic 2 leak | ✘ | Reads naturally as "belongs to / concerns X." |
| Avoids "about" leak | ✘ | *"Relevant to Rivet"* reads as "the memory concerns Rivet." |
| Avoids memory-drives-cast direction | ✔ | No direction implied. |
| Exposes impl detail | ✔ | No. |
| Fits beside "What changed?" | ✔ | Compact. |
| Whole-cast event reads | ~ | Bland; "relevant to Everyone" is thin. |
| Rivet-specific attitude reads | ✘ | Reads as ownership: "the memory is Rivet's." |
| Private observation reads | ✘ | Same ownership implication. |
| Relationship memory reads | ✘ | *"Relevant to Patch, Rivet"* reads as aboutness. |
| Helper text required | Yes | To disambiguate. |

Verdict: **REJECT** — carries the aboutness / attribution
implication in every non-whole-cast case.

#### Candidate B — *"Memory applies to"*

> **Memory applies to**
> ○ Everyone in this episode
> ○ Choose characters…

| Dimension | Score | Notes |
|---|---|---|
| Truthful to Semantic 1 | ✘ | "Applies to X" reads as "governs X's arc / attaches to X." That is Semantic 2. |
| Avoids Semantic 2 leak | ✘ | Same. |
| Avoids "about" leak | ~ | Weaker than A but present. |
| Avoids memory-drives-cast direction | ✔ | — |
| Rivet-specific reads | ✘ | *"Applies to Rivet"* reads as arc-scoped ownership. |
| Private observation reads | ✘ | Same. |

Verdict: **REJECT** — stronger Semantic-2 implication than A.

#### Candidate C — *"Which characters can bring this memory into a scene?"*

> **Which characters can bring this memory into a scene?**
> ○ Everyone in this episode
> ○ Choose characters…

| Dimension | Score | Notes |
|---|---|---|
| Truthful to Semantic 1 | ~ | Close — but overstates the character's role. The runtime is "presence in cast → eligible for retrieval," not "character-agent brings memory." |
| Avoids Semantic 2 leak | ✔ | No ownership implication. |
| Avoids "about" leak | ✔ | — |
| Avoids memory-drives-cast direction | ✔ | Correct direction (character → memory). |
| Exposes impl detail | ~ | "Bring into a scene" hints at retrieval mechanics. |
| Fits beside "What changed?" | ~ | Slightly long. |
| Whole-cast reads | ✔ | Natural. |
| Rivet-specific reads | ~ | *"Only Rivet can bring this in"* implies Rivet exclusively — but the runtime is "Rivet's presence makes it eligible for retrieval, which the writer may or may not act on." |
| Private observation reads | ~ | Same. |
| Relationship reads | ~ | Same. |
| Helper text required | Optional | The label is close to self-explanatory. |

Verdict: **RUNNER-UP CANDIDATE.** The verb *"bring"* implies
active character agency the runtime doesn't quite provide —
a Rivet-witnessed memory becomes eligible when Rivet is
present, but the writer decides what to do with it. Not
false, but slightly overstates.

#### Candidate D — *"Which characters is this memory connected to?"*

> **Which characters is this memory connected to?**
> ○ Everyone in this episode
> ○ Choose characters…

| Dimension | Score | Notes |
|---|---|---|
| Truthful to Semantic 1 | ~ | "Connected to" is very vague. |
| Avoids Semantic 2 leak | ✘ | "Connected to X" reads similarly to "belongs to X." |
| Avoids "about" leak | ✘ | Also accommodates aboutness. |
| Avoids memory-drives-cast direction | ✔ | — |
| Rivet-specific reads | ✘ | Ownership implication. |

Verdict: **REJECT** — vague enough to accommodate
Semantic 2 without preventing it.

#### Proposed Candidate E — *"Which characters make this memory available to a future scene?"*

> **Which characters make this memory available to a future scene?**
> ○ Everyone in this episode
> ○ Choose characters…

| Dimension | Score | Notes |
|---|---|---|
| Truthful to Semantic 1 | ✔ | Exact match. Character presence in future cast makes memory available (eligible) for use in that scene. |
| Avoids Semantic 2 leak | ✔ | "Make available" is enabling, not owning. |
| Avoids "about" leak | ✔ | No aboutness implication. |
| Avoids memory-drives-cast direction | ✔ | Correctly: character → memory availability. |
| Avoids overstating character agency | ✔ | "Make available" is passive-enabling ("their presence unlocks the memory as a candidate"), not "bring" or "cite." The writer still decides whether to use it. |
| Exposes impl detail | ✔ | Doesn't use "retrieval," "eligible," or "top_k." |
| Fits beside "What changed?" | ✔ | Question form; parallel structure. |
| Whole-cast reads | ✔ | *"Everyone in this episode"* answers "which characters make it available" — all of them. |
| Rivet-specific reads | ✔ | *"[Rivet]"* — Rivet's presence in a future cast makes the memory available. Accurate. |
| Private observation reads | ✔ | Same. |
| Relationship reads | ✔ | *"[Patch, Rivet]"* — either character's presence makes it available. Accurate (OR-eligibility). |
| Helper text required | Optional | See §15.5. |

Verdict: **PRIMARY RECOMMENDATION.** Best on every
dimension; no invented misconception.

### 15.4 Ranked recommendation

1. **Primary — Candidate E:** *"Which characters make this
   memory available to a future scene?"*
2. **Runner-up — Candidate C:** *"Which characters can bring
   this memory into a scene?"* — same shape, slightly
   overstates character agency.
3. **Explicitly NOT recommended — Candidate B:** *"Memory
   applies to"* — carries the strongest Semantic-2 ownership
   implication. Also **NOT** recommend Candidate A
   ("Relevant to") or D ("connected to") — both leak
   aboutness / attribution. And **NOT** the existing *"Who
   remembers this?"* which is the very Semantic-2 language
   this relabel exists to correct.

### 15.5 Complete proposed microcopy for the primary
recommendation

**Promote form only** (the smallest, tightest change):

```
Story history
Remember this
Save something that happened in this episode so the story
can bring it back later.

What changed?
[textarea, unchanged]
placeholder: unchanged

Which characters make this memory available to a future scene?
○ Everyone in this episode
○ Choose characters…
   (unchanged pill picker when "Choose characters…" is
   selected)

Error copy adjustments (line 124 in current file):
   "Pick at least one character, or switch to Everyone in
    this episode."
   → UNCHANGED (radio label unchanged).
```

Panel description tweak (line 168-170 currently reads *"…so
the characters can remember it later"*):

```
Save something that happened in this episode so the story
can bring it back later.
```

Rationale: current wording implies characters do the
remembering (Semantic 2). Rephrased so the story pulls the
memory back — matches the runtime (system retrieves; writer
uses).

### 15.6 Read-only display surface — coherence question

Discovered during investigation (§15.2): the read-only
`MemoryRow` and `MemoryUsedRowView` components label the
witness list as *"Remembered by: {names}"* (lines 475, 618).
That is Semantic-2 language for the same field.

Options for the read-only side:

- **Option X (minimal, ships with the promote change):**
  swap *"Remembered by:"* → *"Available in scenes with:"*.
  Same information, matched to the promote-form legend.
- **Option Y (defer):** leave *"Remembered by:"* for now;
  address in a follow-up if operator confusion surfaces.
  Downside: introduces a fresh promote-vs-display mismatch
  that did NOT exist before this relabel.

**Recommendation:** ship Option X together with the promote
change. Fixing one surface without the other trades an
old mismatch for a new one. The read-only strings are
one-line changes each (2 total call sites), no logic
change.

For whole-cast rows, *"Available in scenes with: Everyone
in the episode"* reads naturally.

### 15.7 Traceability — why the proposed wording is truthful

Mapping the primary label to the runtime, clause by clause:

- *"Which characters"* — the operator picks Teammate IDs
  from the source Episode's cast. Signal enforces cast
  subset (`apps/memory/signals.py:28-98`).
- *"make this memory available"* — the visibility filter
  (`retrieval.py:508-529`) admits the memory into the
  candidate pool when `witnessed_by` is empty (whole-cast
  convention) OR at least one witness is in the current
  cast. That admission is exactly "made available for
  retrieval."
- *"to a future scene"* — the retrieval fires per
  Composition; each Composition is a scene render. "Future"
  because the current render is the source of the memory
  being promoted.

**Nothing in the label overstates the runtime.** In
particular:

- It does NOT say *"only these characters know this"* —
  Semantic 2, unenforced.
- It does NOT say *"these characters will cite this"* —
  writer decides.
- It does NOT say *"this memory is about these
  characters"* — aboutness is not the invariant.
- It does NOT say *"these characters will bring this
  memory in"* — the writer, not the characters, decides
  what to do once the memory is retrieved.

### 15.8 Remaining risks / ambiguity

- **Multi-witness OR is implicit.** With witnesses = [Patch,
  Rivet], the label reads *"Patch, Rivet make this memory
  available…"* which reads as OR-eligibility (matches the
  runtime). Whether operators intuit OR vs AND has not
  been tested. The single-witness case is unambiguous;
  the multi-witness case rests on English's natural
  reading of a comma-separated subject.
- **Whole-cast wording drift.** The current *"Everyone in
  this episode"* / *"Everyone in the episode"* pair is
  preserved for backwards visual consistency. If we ever
  restructure the picker, we can revisit for parallelism.
- **Panel description tweak (§15.5) is a second small
  change.** Removing *"the characters can remember it
  later"* eliminates a third Semantic-2 leak but is one
  more diff. Recommend shipping together with the legend.
- **Operator-testing gap unchanged.** SESSION 266 §14.10
  item 2 (whether operators intuitively read the legend
  as Semantic 1 or Semantic 2) is not settled by this
  analysis or by SESSION 267's leakage experiment. The
  relabel closes the ADVERTISED-vs-DELIVERED gap; whether
  operators find the new advertising natural still needs
  usage data.
- **Cross-surface coherence risk if only the promote form
  changes.** §15.6 recommends addressing both surfaces in
  the same change to avoid introducing a new mismatch.

### 15.9 What §15 does NOT do

- Does NOT modify `narrative-memory-panels.tsx`.
- Does NOT change any runtime behavior (prompt, retrieval,
  top_k, witness semantics, schema, canon).
- Does NOT run any further experiment.
- Does NOT commit or push the design analysis alone;
  packaging is up to Chris (design commit lands separately
  from the experiment commit per Chris's SESSION 267
  wrap-up instructions).
- Does NOT close SESSION 267.

### 15.10 Awaiting review

**STOP for Chris + ChatGPT review of §15.4 ranked
recommendation, §15.5 exact microcopy, §15.6 read-only
coherence question, §15.7 traceability, and §15.8 remaining
risks.** Implementation waits on operator authorization of
the specific microcopy (and scope: promote-only vs
promote + display).

### 15.11 Candidate F — availability-condition framing (post-review)

Added after Chris + ChatGPT reviewed §15 and asked for direct
evaluation of an availability-condition framing (asks the
operator WHEN the memory is available rather than WHICH
characters make it available). Documentation-only. No
implementation authorized.

Candidate F, as proposed by Chris:

```
When should this memory be available?
○ In any future scene
○ When these characters are present…
   [character picker]
```

Analysis follows the same rigor as §15.3 with additional
verification against the retrieval predicate for the two
substantive concerns Chris flagged (OR ambiguity + whole-cast
truthfulness).

#### 15.11.1 Q1 — Does *"When these characters are present"*
truthfully represent the overlap predicate?

Runtime, verbatim from `shell/apps/embeddings/retrieval.py:508-529`:

- `witnessed_by` empty → whole-cast pool.
- Non-empty `witnessed_by` → union of whole-cast and
  overlap-with-cast rows (`at-least-one-overlap`).

For a **single-witness** memory (`witnessed_by = [Rivet]`):
*"When Rivet is present"* is exactly the runtime — the memory
becomes eligible in any future scene whose cast includes
Rivet. **Truthful.**

For a **multi-witness** memory (`witnessed_by = [Patch, Rivet]`):
runtime is "eligible when Patch is present, OR when Rivet is
present, OR both." *"When these characters are present"*
without a quantifier reads in English's default as **AND**
("when Patch AND Rivet are both present"). This is a real
Semantic-precision failure — the runtime is OR-overlap, not
AND-intersection. **NOT truthful for multi-witness under
this wording.**

#### 15.11.2 Q2 — Variants explicitly disambiguating OR

Four variants tested against the mental-parse test:

| Variant | Single-witness reads | Multi-witness reads | Verdict |
|---|---|---|---|
| **"When any of these characters are present"** | "When any of: Rivet" → trivially "when Rivet is present" ✔ | "When any of: Patch, Rivet" → OR is explicit ✔ | **BEST** — natural in both cases. |
| "When one of these characters is present" | "When one of: Rivet" → grammatical friction; reads slightly odd | "When one of: Patch, Rivet" → OR is explicit ✔ | Grammatical friction on single-witness case. |
| "In scenes with any of these characters" | "In scenes with any of: Rivet" → trivially "in scenes with Rivet" ✔ | "In scenes with any of: Patch, Rivet" → OR ✔ | Works but pivots the sentence framing away from "when" (a WHEN-question is answered with an IN-clause). |
| "Available when any selected character is present" | "Available when any selected: Rivet" → awkward | "…any selected: Patch, Rivet" → OR ✔ | *"Selected"* is UI-jargon; leaks that this is a form control. |

**Adopted variant: "When any of these characters are
present"** — cleanest natural English for both single and
multi cases, no jargon, explicit OR.

#### 15.11.3 Q3 — *"In any future scene"* under the empty
`witnessed_by` convention — truthful?

Runtime for empty `witnessed_by`:

- Workspace filter unconditional (line 501).
- Universe filter unconditional (line 502).
- Any non-empty cast in that Universe/Workspace ⇒ memory
  admitted to the candidate pool (line 519-522).

Operator mental model verification:

- Whole-cast memories live at the Universe level, NOT
  restricted to this Episode's cast. A future Episode with
  DIFFERENT characters (still in the same Universe) can
  still retrieve this memory.
- Operator authoring in *Patch' Workshop* has an implicit
  scope of "this story-world." "Any future scene" reads to
  the operator as "any future scene in this story-world"
  — which matches the Universe scoping exactly.
- Universe is invisible-by-design in the current promote
  UI (the operator is scoped by picking the Episode; the
  Universe is upstream). Surfacing it would leak
  implementation.

**Verdict: truthful.** The Universe boundary is invisible-
by-design; the operator's implicit scope is the current
story-world, which is the Universe. *"In any future scene"*
matches this exactly without exposing the word "Universe."

**Fallback if operator confusion later surfaces:** *"In any
future scene in this story"* — one word more, disambiguates
against a cross-Universe misreading. Not recommended for v1
because the mismatch is theoretical, not observed.

*"In any future scene"* is NOT the same as *"Everyone in
this episode"* (Candidate E). E claims Episode-cast reach;
the runtime is Universe reach. **F's whole-cast wording is
strictly more truthful than E's.** Recorded as an accuracy
win for F.

#### 15.11.4 Q4 — Read-only display under F + OR formatter
feasibility

Current read-only formatting
(`narrative-memory-panels.tsx:461-462` and 606-607):

```typescript
memory.witnessed_by.length === 0
  ? "Everyone in the episode"
  : memory.witnessed_by.map((w) => w.name).join(", ")
```

Comma-join today. For F we need an OR-formatter:

```typescript
function formatWitnessAvailability(witnesses: {name: string}[]): string {
  if (witnesses.length === 0) return "In any future scene";
  if (witnesses.length === 1) return `When ${witnesses[0].name} is present`;
  if (witnesses.length === 2) {
    return `When ${witnesses[0].name} or ${witnesses[1].name} is present`;
  }
  const last = witnesses[witnesses.length - 1].name;
  const rest = witnesses.slice(0, -1).map((w) => w.name).join(", ");
  return `When ${rest}, or ${last} is present`;  // Oxford-or
}
```

**This is pure presentation formatting over the existing
witness array.** No schema change, no logic change, no
runtime change. The `witnessed_by` M2M shape and content are
identical to today — only the display string changes.

Rendered examples:

| Witnesses (state) | Display |
|---|---|
| `[]` (whole-cast) | `Available: In any future scene` |
| `[Rivet]` | `Available: When Rivet is present` |
| `[Patch, Rivet]` | `Available: When Patch or Rivet is present` |
| `[Patch, Rivet, Bolt]` | `Available: When Patch, Rivet, or Bolt is present` |

**Confirmation: multi-character OR can be rendered
explicitly from the existing witness array with no runtime
change.** Pure formatter.

#### 15.11.5 Q5 — E vs F comparison

Evaluation on Chris's 12 requested dimensions. Where F wins,
the specific rationale is given.

| Dimension | E | F | Notes |
|---|---|---|---|
| Creator comprehension | ~ | ✔ | F asks "when" (matches operator's decision framing "when should this come back") vs E asking "which characters cause availability" (requires operator to think mechanistically). |
| Semantic accuracy — whole-cast | ✘ | ✔ | E's "Everyone in this episode" claims Episode-cast reach; runtime is Universe-wide. F's "In any future scene" matches the runtime. **F strictly more truthful.** |
| Semantic accuracy — single character | ✔ | ✔ | Both truthful. |
| Semantic accuracy — multi-character OR | ✘ (comma-join reads as AND) | ✔ (with "any of" variant + OR formatter) | F requires the "any of" variant on the radio + OR-formatter on display. Both feasible without runtime change. |
| Private-observation case | ✔ | ✔ | Both work; F is slightly more direct ("When Rivet is present"). |
| Relationship-memory case | ✘ (comma-join) | ✔ (OR-formatter) | Same as multi-character. |
| Consistency between promote + read-only | ✔ | ✔ | Both coherent when both surfaces ship together. |
| Implementation complexity | Slightly lower | Slightly higher | E needs a label swap + panel description tweak. F additionally needs the OR-formatter helper (~5 lines) and updates both radio labels. |
| Exposes internal architecture | ~ | ~ | Both use "available" / "scene." Neither uses "Universe," "retrieval," "eligibility," "top_k," "M2M," "overlap." |
| Implies Semantic 2 | ~ | ✔ | E's "which characters make available" has a mild ownership overtone. F's "when should this be available" is purely conditional — cleaner. |
| Implies aboutness / ownership | ✔ | ✔ | Neither leaks. |
| Overall | Adequate | **Preferred** | F wins on comprehension, whole-cast accuracy, multi-character OR clarity, and Semantic-2 avoidance. |

**Winner: Candidate F (with "any of these characters" variant
and OR-formatter for display).**

#### 15.11.6 Final proposed microcopy

**Promote form** (`narrative-memory-panels.tsx`):

```
Story history                          ← unchanged (line 164)
Remember this                          ← unchanged (line 166)

Save something that happened in this   ← REVISED (line 168-170)
episode so the story can bring it
back later.

What changed?                          ← unchanged (line 178)
[textarea, unchanged]                  ← unchanged
placeholder unchanged                  ← unchanged (line 185)

When should this memory be available?  ← REVISED (line 191)
○ In any future scene                  ← REVISED (line 207)
○ When any of these characters are     ← REVISED (line 220)
  present…
   [pill picker, unchanged]            ← unchanged
```

**Error message** (line 124):

```
Pick at least one character, or switch to
'In any future scene'.
```

**Read-only memory display** (both `MemoryRow` at ~475 and
`MemoryUsedRowView` at ~618):

Label prefix: `Remembered by:` → `Available:`
Value: use `formatWitnessAvailability(witnessed_by)` per
§15.11.4.

**Preserved (per Chris's product principle):**

- "Story history" section header (line 164) — unchanged.
- "Remember this" H3 (line 166) — unchanged.
- "Remember this" submit button (line 275) — unchanged.
- "What changed?" field label (line 178) — unchanged.
- "Story history" list section title (line 356-357) — unchanged.
- "Forget" archive action + associated confirm-copy —
  unchanged.
- Textarea placeholder — unchanged.
- Body error copy "Tell us what happened first." (line 119)
  — unchanged. (Loose relationship to "What changed?" label
  but stable operator meaning: "tell us what to save.")

#### 15.11.7 File / line call sites if authorized

Single file: `web/src/components/narrative-memory-panels.tsx`.

| Line | Current | Proposed |
|---|---|---|
| 124 | `"Pick at least one character, or switch to Everyone in this episode."` | `"Pick at least one character, or switch to 'In any future scene'."` |
| 168-170 | `"Save something that happened in this episode so the characters can remember it later."` | `"Save something that happened in this episode so the story can bring it back later."` |
| 191 | `Who remembers this?` | `When should this memory be available?` |
| 207 | `Everyone in this episode` | `In any future scene` |
| 220 | `Choose characters&hellip;` | `When any of these characters are present&hellip;` |
| 459-462 | Inline `witnessLabel` computation | Replace with `formatWitnessAvailability(memory.witnessed_by)` |
| 475 | `Remembered by: {witnessLabel}` | `Available: {witnessLabel}` |
| 604-607 | Same inline `witnessLabel` computation | Same replacement |
| 618 | `Remembered by: {witnessLabel}` | `Available: {witnessLabel}` |
| (new) | — | Add `formatWitnessAvailability` helper (module-scope, ~7 lines including edge-case list of 3+) |

**No other file requires changes** to ship the wording
correction. The M2M shape, API payload contract, backend
serializer, and retrieval predicate are all unchanged.

#### 15.11.8 Estimated implementation scope

- **Files touched:** 1 SPA component
  (`narrative-memory-panels.tsx`) + 1 test file
  (`memories-used-panel.test.tsx`) + optionally
  `narrative-memory-panels.test.tsx` for a new
  legend/radio-copy test.
- **Line diff:** ~30 lines source + ~10 lines test updates.
- **New helper:** `formatWitnessAvailability(witnesses)` —
  ~7 lines, module-scope in
  `narrative-memory-panels.tsx`.
- **Runtime:** unchanged.
- **API contract:** unchanged.
- **Schema:** unchanged.
- **Backend:** unchanged.
- **No new tests required for backend.**

#### 15.11.9 Tests that should change / add

**Update — visible-string assertions:**

- `web/src/components/memories-used-panel.test.tsx`:
  - Line 75: `/Remembered by: Everyone in the episode/` →
    `/Available: In any future scene/`
  - Line 89: `/Remembered by: Patch, Rivet/` →
    `/Available: When Patch or Rivet is present/`
  - Docstring line 10 ("Empty `witnessed_by` renders as
    'Everyone in the episode'") update to match.

**Update — comment/docstring drift (no assertion changes):**

- `web/src/components/narrative-memory-panels.test.tsx`:
  - Test title `'"Everyone in this episode" is checked by
    default'` → `'"In any future scene" is checked by default'`
  - Docstring items 5 + 7 wording refresh.
  - Test bodies use `data-testid` selectors (unchanged), so
    behavior tests still pass without further change.
- `shell/apps/memory/tests/test_memories_used_serializer.py`
  line 209: docstring reference only — safe to update for
  hygiene.

**Add — one new focused test:**

- `formatWitnessAvailability` unit test with 4 cases
  (0, 1, 2, 3 witnesses) covering both the string outputs
  and the Oxford-or edge case for 3+.
- Optional: a promote-form legend + radio-copy assertion in
  `narrative-memory-panels.test.tsx` to lock the new copy
  in place against future drift.

#### 15.11.10 Runtime semantics — explicit confirmation

The following remain UNCHANGED by any implementation
authorized from §15.11:

- `shell/apps/embeddings/retrieval.py:499-543` — retrieval
  predicate, `top_k` default, cosine ranking, witness
  overlap semantics.
- `shell/character_os/dialogue_synthesis.py:553-575` —
  narrative-memory prompt block (no witness attribution
  transmitted).
- `shell/character_os/dialogue_synthesis.py:1530-1548` —
  `top_k=1` call site.
- `apps/memory/models.py:192-201` — `witnessed_by` M2M
  shape.
- `apps/memory/signals.py:28-98` — witness cast/Universe/
  Workspace invariants.
- `apps/memory/views.py:171-287` — sanctioned promotion
  service.
- All memory kinds, schema, canon, and existing 7 active
  memories.

**No production behavior changes.** The UI wording
truthfully describes the same runtime this whole session
has audited.

#### 15.11.11 Final recommendation

**Adopt Candidate F with the "any of these characters"
variant + OR-formatter for display.** Documented in
§15.11.6–§15.11.7 as the complete microcopy delta.

Chris's Candidate F wording adjusted for the OR-precision
gap identified in §15.11.1:

- Original: *"When these characters are present…"* — REJECT
  for multi-witness AND-implication.
- Adopted: *"When any of these characters are present…"* —
  natural for both single and multi cases; explicit OR
  under multi.

Preserves *"Story history"* / *"Remember this"* per Chris's
product principle.

#### 15.11.12 Remaining risks / open questions

- **"In any future scene" precision.** Under multi-Episode
  Universes the phrase may still be interpretable as
  "any future scene, period." The Universe scoping IS the
  operator's implicit story-world scope today, but future
  UX changes that surface cross-Universe operations would
  need to revisit.
- **OR-formatter internationalization.** English "or"
  is hard-coded in the formatter. If Character OS ever
  ships i18n, the helper becomes a translation seam. Out
  of scope for v1.
- **Operator-intuition testing gap unchanged.** As with
  §14.13, whether operators intuitively parse the new
  wording correctly is unmeasured. Recommend collecting
  dogfood impressions after the change lands.
- **Same-commit vs staggered rollout.** §15.6 recommended
  shipping promote-form + display together to avoid a new
  mismatch. §15.11 preserves that recommendation. If Chris
  prefers staggered, the promote-form-only change would
  temporarily create a new gap ("When should this be
  available?" saved copy → "Remembered by:" displayed copy)
  until the display change lands.
- **Test-name refresh scope.** Test titles referencing
  "Everyone in this episode" are cosmetic drift; if left
  stale, they mislead future readers. Recommend updating
  in the same change.

#### 15.11.13 STOP

**Documentation-only. No file under
`web/src/components/` modified. Implementation waits on
Chris + ChatGPT authorization of §15.11.11 (Candidate F
adopted variant) with §15.11.6 microcopy.**
