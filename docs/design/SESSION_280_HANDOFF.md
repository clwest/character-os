# SESSION 280 — Handoff (from SESSION 279)

## Status at the top

- **SESSION 279 is CLOSED.**
  - Closeout ref: `docs/design/SESSION_279_CHARACTER_KNOWLEDGE_DEPTH_AUDIT.md`
    §"SESSION 279 — CLOSEOUT MARKER" + §151.
  - Full evidence: same document, 5,443 lines across
    Q-279-1 → Q-279-2 → Q-279-2A → Q-279-2A-REV → Q-279-2B → Q-279-2C
    → Stage A T1/T2/T3 → Q-279-3 Phase 1 → Q-279-3 Phase 2 P2-A/B/C
    → Q-279-3 P2-BC → Q-279-3 closure at DEEP-RESIDUAL.
- **Two deferred findings from SESSION 279 handoff CLOSED:**
  - **4b** (character identity-as-expert vs Knowledge-depth) →
    **ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS**.
  - **4a** (generalized writer voice / recurring metaphor-family
    leakage) → **CLOSE-Q-279-3-AT-DEEP-RESIDUAL**.
- **Findings 4c-4i preserved unopened.** Additional Session-279-surfaced
  deferred questions (Knowledge-breadth, Beat-3 legibility, untested
  text levers, adversarial-topic replication, character-identity
  distribution architecture) also preserved unopened.
- **Substrate mutation performed in SESSION 279:** exactly one
  KnowledgeDocument (`3ff45702-cb8b-49f0-82f6-97013c0f8da6`)
  `text_content` replaced via SPA Ask-panel Beat 3 by Chris (§27
  treatment corpus). Every SESSION 275/276 lifecycle invariant
  intact; scope/audience unchanged; reversible.
- **Real-DB state at closeout:** Tyson specialty KD carries the
  §27 treatment corpus, 3 chunks embedded, character-audience,
  Tyson-only, Fox & Flour Universe, is_active=true, verified via
  Q-279-2C §44 read-only checks; T1/T2/T3 Compositions
  (`488c37ba`, `699916a9`, `a5c59014`) verified + persisted.

**Purpose of this document:** compact self-contained orientation
for SESSION 280 Claude + ChatGPT so neither has to re-read all of
SESSION 279 to resume work.

---

## §1 Working method preserved

Session 279 practiced and validated the following working method.
SESSION 280 should continue it unchanged:

1. **AUDIT / ORIENT** — read-only inspection of substrate and
   persisted evidence before making claims.
2. **Falsifiable question** — every slice starts with a precise
   mechanical question, and a prediction is recorded BEFORE
   evidence is gathered.
3. **Smallest controlled slice** — change ONE variable at a time,
   pin everything else, use runtime injection / operator-facing
   gestures rather than permanent code modifications wherever
   possible.
4. **Dogfood / runtime evidence** — exercise the real production
   path, not mocks. Prefer synthesis-only over full renders when
   the dependent variable is text, not media (~99 % cost
   reduction).
5. **Prediction vs actual** — after evidence lands, explicitly
   score against the pre-registered prediction and acceptance /
   disconfirmation criteria. Do not retro-fit thresholds.
6. **Document durably** — every substantive finding lives in the
   audit doc, not in terminal output.
7. **Decision gate** — end each slice with an explicit gate
   recommendation and wait for Chris + ChatGPT approval before
   proceeding.
8. **Do NOT assume implementation is next.** Audit → design →
   controlled experiment → interpretation → decision. A fix is a
   separate downstream slice with its own approval.

Anti-patterns to avoid (all learned from SESSION 279):

- Do NOT collapse deferred findings together — the "courtroom
  words" observation looked like one thing and turned out to be a
  broader rhetorical attractor with different surface expressions
  per character.
- Do NOT revise a locked rubric or gate after seeing results.
- Do NOT reduce a broad product question ("same character in
  different scene environments") to a narrow technical primitive
  ("add background replacement") without explicit direction.
- Do NOT bypass the operator UI via ORM/admin/curl for substrate
  changes that operators should be dogfooding.
- Do NOT let an interesting-but-out-of-scope observation alter the
  current experiment's scoring — record it as separate deferred
  evidence.

---

## §2 Durable conclusions from SESSION 279

### 2.1 Q-279-2 / 4b — Character Knowledge-depth (CLOSED at ACCEPT)

**Question:** If a character's identity remains unchanged and only
the depth/quality of their character-specific Knowledge increases,
does normal minimal-topic dialogue spontaneously become more
concretely expert?

**Answer:** YES.

**Mechanism established:**

- Character OS mechanically separates character identity
  (`Teammate.business_brief`, `personality`, voice enums, POV) from
  character-specific Knowledge (`KnowledgeDocument` under
  `audience_scope=CHARACTER` + `spokespeople=[Teammate]`).
- Identity fields are ALWAYS injected into the synthesis prompt
  (never retrieval-gated); character KD chunks are cosine-retrieved
  and injected in a co-located `SCOPED KNOWLEDGE` block.
- A KD whose content is *identity-restating* (as Tyson's baseline
  118-char specialty KD was) produces the same generic dialogue
  quality as identity alone — the substrate has no additional
  material to work with.
- A KD whose content is *concrete domain reference material* —
  same audience_scope, same M2M, same Universe, same code path —
  produces measurably deeper demonstrated expertise while
  correctly topic-gating out on unrelated topics.

**Quantitative result:**

- Baseline Fox & Flour Ruby+Tyson dialogue-scene rendering of two
  minimal topics: **0/12 on R1-R6 rubric** for Tyson's turns
  (compositions `d7549fc1` and `7177b0f5`, SESSION 278).
- Post-treatment (same topic, same identity, same code, only KD
  content replaced with §27 domain corpus): **12/12 on R1-R6** for
  Tyson's turns on BOTH replay specimens
  (`488c37ba` = T1, `699916a9` = T2).
- Neutral control T3 (*"Ruby locks herself out of the bakery"*,
  composition `a5c59014`): **T3 R1 = 0** for Tyson's turns —
  treatment vocabulary correctly stayed out of an unrelated topic
  despite all 3 treatment chunks being present in
  `knowledge_chunk_ids`.
- Five-condition ACCEPT gate (§31.3) fired cleanly.

**Scope preserved by the treatment:**

- `audience_scope=CHARACTER` unchanged.
- Spokespeople M2M = {Tyson only} unchanged.
- Universe = Fox & Flour Bakery unchanged.
- `is_active=true` unchanged.
- No cross-cast leakage (Ruby's retrieval lane never surfaced the
  treatment chunks).

**Also-established sub-findings:**

- The Fox & Flour operator-visible **Beat-3 SPA edit gesture**
  works end-to-end (§37, §39) — the citation row in the Ask panel
  IS a `<button>` that opens `EditDocSurface` with a
  `text_content` PATCH via `useUpdateKnowledge`. Visual affordance
  is subtle (no persistent icon, only hover glow) — see §2.7 below.
- **CHARACTER-vs-WORLD ownership** (§26): an initial version of
  the treatment corpus asserted Fox & Flour menu facts as
  CHARACTER-scoped, which would have privatized shared bakery
  reality to Tyson. Correction was to write the corpus as
  *third-person domain reference material* (§27) — Tyson considers
  these coffee/pastry types in his framework, not "Fox & Flour
  serves these". No World-canon leakage confirmed by grep at §29.

### 2.2 Q-279-3 / 4a — Generalized writer voice (CLOSED at DEEP-RESIDUAL)

**Question:** Why do semantically unrelated Fox & Flour scenes
repeatedly produce the same procedural / adversarial / metaphorical
language families despite different topics and despite Knowledge
changes?

**Answer:** The recurring surface fingerprint (courtroom /
procedural vocabulary) is one expression of a broader **writer-voice
structural attractor** — a *"negation-reframe with stakes-elevating
punchline"* + *"diminutive-formal metaphor"* device family that
recurs across Universes, characters, topics, and Q-279-2 Knowledge
treatment. The attractor lives ABOVE the character layer AND is
MODULATED (only modestly) by free-text personality. Neither of the
two most-plausible text-side levers reaches the residual within the
D1-D4 rubric.

**Nine durable conclusions (§145):**

1. Writer-voice attractor is real and cross-World (43-composition
   Phase-1 scan §100; both Fox & Flour + Patch's Workshop).
2. Richer character Knowledge does not cause or solve it —
   Q-279-2 §27 treatment corpus contains zero courtroom /
   procedural vocabulary, yet the attractor persisted (§92.5).
3. Tested dialogue-scene contract language (specifically
   `_DIALOGUE_WATCHABILITY_BLOCK` §1 wants-list +
   `_DIALOGUE_NARRATIVE_SHAPES_BLOCK` menu) changes family
   expression but does not materially reduce total attractor mass
   (Phase 2 P2-B: composite +2.2 % vs baseline, D1+D3 → 0 but
   D2+D4a+D4n backfill — §122).
4. Free-text personality is a modest modulator (~22-25 %), not
   the primary source (Phase 2 P2-C composite = 74.8 % of P2-A;
   below the pre-registered ≥ 50 % threshold — §121).
5. Combining contract-lite + personality-lite adds no
   meaningful additional reduction beyond personality-lite alone
   (P2-BC composite and per-family distribution identical to P2-C
   alone — §137, §139). The two text levers do NOT stack.
6. D4a (stakes-elevating adjectives: *serious*, *consequential*,
   *important*, *dramatic*) is the stable observed backfill
   channel under these interventions (§138.2).
7. The remaining residual is DEEP-RESIDUAL / model-prior
   interaction at the tested substrate surfaces (§138.3).
8. No production fix is authorized from this evidence.
9. Future mitigation / fix-design work remains a separate future
   question — a Phase 3 or later would need to either target
   *untested* text levers (§2.5 below) OR accept the residual as
   substrate reality and design downstream mitigations
   (post-generation filtering, regenerate-on-attractor-hit,
   model-swap).

**Family-swap behavior (§122, §138.2):**

Under every text-side intervention tested, when the model was
starved of one surface for the attractor, it reached for another:

- P2-B (contract-lite): D1 (negation-reframe) → 0; D3 (courtroom
  lexicon) → 0; D2 (*"tiny X"*) rose; D4a rose; D4n appeared.
- P2-C (personality-lite): D1 partially reduced; D3 → 0;
  D4a rose to 2.
- P2-BC (combined): identical distribution to P2-C alone; D4a = 2.

**Load-bearing rhetorical device family** (§100.3, established
across 43 compositions): *"That is not X. That is Y."* negation-
reframe, dominant in Rivet's turns; assertive-reframe *"That is
a…"* dominant in Patch; courtroom lexicon (D3) dominant in
Ruby+Tyson. Same underlying attractor, different surface
expressions per character-personality context.

**Levers tested and NOT sufficient:**

- `WritingContract.for_shape('dialogue_scene')` stakes-elevating
  blocks (contract-lite substitution) — moved family, not
  composite.
- Free-text `personality` field (personality-lite substitution) —
  moved composite ~22-25 %, not to ≥ 50 %.

**Levers NOT tested** (§2.5 below in deferred ledger).

### 2.3 Secondary architectural observation

**Character identity is distributed across substrate — NOT solely
in free-text personality.** Under combined P2-BC neutralization
(both contract-lite AND personality-lite blanked to *"X is friendly
and helpful."*), Ruby and Tyson remained distinctively
recognizable. The LLM synthesized character voice from surviving
substrate:

- `Teammate.business_brief`
- `tone_archetype`, `voice_energy`, `voice_humor`, `voice_directness`
- Character-audience KD corpus (Q-279-2 §27 treatment)
- Writing-contract invariants + anti-patterns + register-examples
  (retained even in contract-lite)

Preserved for future H3 refinement work; NOT opened as a distinct
investigation.

### 2.4 Q-279-2 / 4b reinforced by Phase-2 evidence

All 12 Phase-2 samples surfaced the §27 treatment corpus
vocabulary naturally on a topic that did NOT prompt for it, under
EVERY intervention configuration including combined P2-BC. Knowledge
substrate does its job orthogonally to the writer-voice attractor
(§147). 4b remains CLOSED at ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS.

---

## §3 Deferred findings ledger — carried forward for SESSION 280

Every still-open finding preserved distinctly. Each entry:

- **Evidence exists** — what SESSION 279 (or earlier) already
  established.
- **Still unknown** — what a future audit would need to resolve.
- **Territory** — research/audit / experiment / product-design /
  implementation.
- **Dependencies** — order constraints on other items.

### 3.1 Finding 4c — Visual composition boundary (BROADENED)

**Original scope (`SESSION_279_HANDOFF.md` §4c):** Dialogue
synthesis progressively introduces visually important scene objects
that the current talking-head composition cannot show.

**Extension from SESSION 279 (§83):** Chris's Q-279-2 T3 dogfood
observation — the rendered media used standard talking-head
avatar + background assets while the dialogue explicitly staged
Ruby *outside* the bakery, keys inside, glass door between
characters. Location-shape mismatch on top of the earlier scene-
object mismatches.

**Chris's broader product framing (§83.2, preserved verbatim in
this handoff — do NOT reduce prematurely):**

> A useful future system likely needs to preserve the SAME
> recognizable character while allowing different backgrounds /
> locations / scene contexts / possibly poses / framing / physical
> interaction states.
>
> Load-bearing product question: *How should Character OS maintain
> character visual identity while allowing the same character to
> appear naturally in different scene environments required by
> generated dialogue?*

**Evidence exists:**
- SESSION 278 4c evidence: Ruby mascot scene objects (Q-278-3.2
  Specimen 3), "the box" object references, etc.
- SESSION 279 T3 addition: outside/inside/glass-door location
  mismatch — three explicit spatial staging cues in the dialogue
  that the render did not honor visually.

**Still unknown:**
- The full space of visual-composition failure modes across the
  Fox & Flour + Patch's Workshop dogfood corpus (scene objects
  named vs shown; locations described vs depicted; physical
  interaction states described vs enacted).
- Whether the visual boundary is a talking-head-template-specific
  limit or a substrate-wide limit.
- How to think about character-identity vs scene-context as
  independent axes at the avatar / portrait / rig layer.
- Existing primitives: what does the media-engine already support
  beyond talking-head (background swap? multi-shot? cinematic
  outputs? see the `scripts/migrate-cinematic-outputs.py` +
  `docs/design/CONTENT_FORMAT_BACKLOG.md` entries).

**Territory:** research/audit first (map current visual primitives
+ dogfood-derived requirements), then product-design (identity vs
scene as separable axes), then experiment (small controlled test
of one specific requirement), then implementation.

**Dependencies:** none blocking; independent from 4a/4b substrate
work. Could pair with `docs/design/CONTENT_FORMAT_BACKLOG.md` +
existing SESSION 173-174 dogfood pattern.

### 3.2 Finding 4d — Underdeveloped / abrupt scene endings near duration boundary

**Evidence exists:** One-specimen observation from Q-278-4.2
Specimen 3 (junk composition; target 90s, predicted 72s, final
72.3s = lower boundary). No new SESSION 279 evidence recorded.

**Still unknown:** Whether it repeats systematically. No corpus-
level scan done.

**Territory:** audit first (repeat-scan of persisted compositions
where predicted_seconds is near the ±20 % boundary). If pattern
emerges, experiment.

**Dependencies:** none. Small.

### 3.3 Finding 4e — Isolated avatar / video quality

**Evidence exists:** One-specimen observation from Q-278-4.3
Specimen 2. No new SESSION 279 evidence (Phase 2 was synthesis-only,
zero avatar rendering).

**Still unknown:** Whether the pattern recurs.

**Territory:** wait for correlation from future dogfood; not
audit-actionable on one specimen.

**Dependencies:** none.

### 3.4 Finding 4f — Cross-cast alias grounding

**Evidence exists:** Q-278-4.3 Specimen 3 flagged `Tyson` as
BOTH-parity on a one-word Ruby turn (*"Tyson."*). `build_allowed_vocabulary`
at `character_os/claim_verifier.py:741-803` includes each speaker's
own name + KNOWN_PLATFORM_TERMS but NOT cross-cast character
names. `synthesize_dialogue` has the full `alias_to_teammate` cast
map available in-scope. Substrate gap pre-existed the K6.4
dispatcher work.

**Still unknown:** Whether `build_allowed_vocabulary` should
extend to include cross-cast aliases when called from a
dialogue-scene context; whether ONLY the current cast or every
Teammate in the Universe.

**Territory:** small mechanical audit + smallest-slice
implementation (single function signature change + tests). Ready
for a focused fix if approved.

**Dependencies:** **BLOCKS** 4h (strict-mode audit) — 4h would
false-block on every dialogue where one character addresses
another until 4f is fixed.

### 3.5 Finding 4g — Adjacent-surface D-POS migration

**Evidence exists:** Q-278-4.3 landed D-POS Hybrid as
authoritative on `Composition.verification_warnings` for
dialogue-scene compositions ONLY. Script (B-arc apps.scripts),
ConversationMessage (K6.5), and talking-head / long-form Composition
remain legacy K6.4 authoritative.

**Still unknown:** Which adjacent surface (if any) to migrate
first; per-surface shadow-window + dual-write + Slice-3 acceptance
gate each requires its own scope-locked audit.

**Territory:** research/audit (per-surface scope-lock design),
then experiment (per-surface shadow window), then implementation
(dispatcher wiring per surface). Follows the exact SESSION 278
Q-278-3.2 → Q-278-4.2 → Q-278-4.3 playbook per surface.

**Dependencies:** none blocking; each surface independent.

### 3.6 Finding 4h — Strict-mode audit

**Evidence exists:** `K6_CLAIM_VERIFIER_MODE = "warn"` unchanged
throughout SESSION 278 + 279. D-POS currently never raises;
flipping to `strict` would convert D-POS warnings into
render-blockers.

**Still unknown:** Whether the false-block rate under strict-mode
is tolerable; what other substrate gaps beyond 4f would surface.

**Territory:** research/audit first (dry-run strict-mode
classifier over persisted dialogue-scene corpus, count would-block
rate), then design + experiment.

**Dependencies:** **BLOCKED BY 4f** per SESSION 279 handoff §4h
tail — strict-mode would false-block on cross-cast address until
4f fixed.

### 3.7 Finding 4i — Cross-episode epistemic asymmetry (PATCH OVERRIDES)

**Evidence exists:** Q-278-3.2 Specimen 4-addendum. Rivet-scoped
narrative memory (*"PATCH OVERRIDES"* folder) produced dialogue
where Patch approached the hidden subject unknowingly and Rivet
responded consistently with private knowledge without exposing it.

**KEY PRODUCT QUESTION (preserved verbatim; do NOT propose
implementation):**

> What happens when one character knows something another
> character does not, how is that knowledge represented and
> respected across future scenes, and what new storytelling
> behavior becomes possible?

**Still unknown:** Six specific unproven claims listed in
Q-278-3.2 Specimen 4-addendum — whether Character OS
*maintains* arbitrary per-character epistemic state across
episodes. The mechanical entry point is per-character `memory_ids`
+ per-character retrieved-K2 provenance persisted on Composition
rows.

**Territory:** research/audit + product-design (largest
storytelling upside per SESSION 279 handoff §7). Substantial.

**Dependencies:** none blocking; independent from
substrate-quality work.

### 3.8 Deferred question — Knowledge-breadth scaling

**Origin:** SESSION 279 Q-279-2 Stage A T2 §70 (Chris dogfood).

**Evidence exists:** The intentionally-tiny 3-chunk §27 treatment
corpus produces strong 12/12 signal on two domain-adjacent
topics, but Tyson's demonstrated expertise is bounded by the
small example set (recurring: chocolate babka, almond croissant,
morning bun, espresso, drip, pour-over, plus one tradeoff rule).
Recurrence of the same small set is EXPECTED under a 3-chunk
corpus; it does NOT disconfirm Q-279-2.

**Still unknown:**

> How much domain breadth does a character-specific Knowledge
> corpus need before expertise feels varied and expansive rather
> than repeatedly circling the same small set of examples?

Also: at what corpus size does retrieval-ranking (top_k=5) become
a confound? What's the operator-authoring effort curve? Does a
richer corpus interact with the writer-voice attractor (4a) —
does more Knowledge amplify or dampen the D4a backfill channel?

**Territory:** experiment (author a larger character-specific
corpus, replay same specimens or generate new topics, measure
per-composition device-family + subjective expertise-breadth) +
possible product-design (operator authoring workflow for larger
KD corpora).

**Dependencies:** natural continuation of Q-279-2. **Would ALSO
provide adversarial-topic base rate** on a Knowledge-rich
Fox & Flour cast — could pair with 3.11 below.

### 3.9 Deferred question — Beat-3 SPA edit-affordance + re-ingest-feedback legibility

**Origin:** SESSION 279 Q-279-2B §40 + Q-279-2C §46 (both Chris
operator observations).

**Evidence exists:**
- SPA Ask-panel citation row IS a fully wired
  `<button aria-label="Edit …">` per
  `web/src/components/spokesperson-ask-panel.tsx:452-471`. Tests
  at `spokesperson-ask-panel.test.tsx:412-505` confirm the click
  → EditDocSurface → PATCH flow works.
- BUT the row has no visible edit affordance at rest — only a
  hover-triggered gold glow + screen-reader label. Chris did not
  perceive it as clickable on first attempt.
- After Save, the SPA gives the operator no visible signal that
  re-ingestion started/completed; `savedNotice` state exists but
  its effectiveness on the current build was not verified.

**Still unknown:**
- Whether `savedNotice` renders correctly and whether it reflects
  re-ingest completion vs mere PATCH acceptance.
- Correct visual affordance shape (pencil icon adornment vs
  persistent underline vs "Edit" label — three options at §40).

**Territory:** product-design (visual affordance + feedback
shape), then implementation (small `spokesperson-ask-panel.tsx`
change — `PencilLine` already imported at line 40 for the
honest-fallback teach-me button).

**Dependencies:** none.

### 3.10 Deferred question — Untested text-side levers

**Origin:** SESSION 279 Q-279-3 P2-BC §142 + §143 option 3.

**Text-side levers TESTED in Session 279 Phase 2:**

- `WritingContract.for_shape('dialogue_scene')` stakes-elevating
  blocks (contract-lite) — did NOT move composite.
- Free-text `Teammate.personality` (personality-lite) — moved
  composite ~22-25 %.

**Text-side levers NOT tested:**

- `Teammate.character_point_of_view`
- `Teammate.voice_signature_phrases`
- `Teammate.voice_avoid_phrases`
- `Teammate.tone_archetype` (enum)
- `Teammate.who_you_help` / `what_you_sell` / `always_emphasize`
  / `never_say` / `desired_feeling`
- Anti-generic-register contrast set (`_REGISTER_EXAMPLES` in
  writing_contract.py)
- `Composition.audience_hint` per-render surface

**Still unknown:** Whether ANY text-side lever moves the
composite past ~25 % on neutral topics before we concede H2 as
unmovable within text-side substrate.

**Territory:** experiment — extension of the Phase 2 probe.
Would reuse `scripts/session279_q279_3_phase2_probe.py` shape;
new monkeypatches per lever; same probe/scoring/rubric.

**Dependencies:** downstream of 4a closure (4a already closed at
DEEP-RESIDUAL; this is fix-planning-adjacent work, not audit
work). Only justified if a fix will be considered.

### 3.11 Deferred question — Adversarial-topic replication

**Origin:** SESSION 279 Q-279-3 Phase 2 §127 §1 + §143 option 2.

**Evidence exists:** Neutral-topic Phase-2 base rate (composite/1k
= 1.052) is only ~24 % of Phase-1 F&F aggregate rate (~4.35/1k on
adversarial topics). The neutral-topic ceiling depresses the
attractor below the noise floor of the ≥ 50 % criterion at n=3.

**Still unknown:** Whether the P2-B / P2-C / P2-BC interventions
would show a bigger composite reduction on a higher-base-rate
adversarial topic (e.g. replay of Q-279-2 T1 *"Ruby thinks Tyson
is taking coffee too seriously"*).

**Territory:** experiment — reuse Phase 2 probe, swap topic
constant only. 12 additional synthesis-only calls ≈ $0.07.

**Dependencies:** downstream of 4a closure — the primary A/B/C
question is resolved as "mixed"; this would refine the H1-vs-H2
resolution only.

### 3.12 Deferred question — Character-identity distribution architecture

**Origin:** SESSION 279 Q-279-3 §141 + §146.

**Evidence exists:** Under combined P2-BC neutralization
(contract-lite + personality-lite), Ruby and Tyson remained
recognizably in-character. Character identity is distributed
across `business_brief`, voice enums, Knowledge, and remaining
synthesis invariants — NOT solely in free-text personality.

**Still unknown:** Which combination of surviving substrate
elements does the LLM actually rely on to reconstruct
character voice? Would blanking `business_brief` also (a P2-D
condition) finally collapse character recognizability? What are
the minimum-viable character-identity signals?

**Territory:** research / audit + experiment (extension of Phase
2 probe with additional substrate-neutralization conditions).

**Dependencies:** downstream of 4a closure; adjacent to 3.10
untested-lever work.

### 3.13 Deferred question — Full content-format backlog

**Origin:** `docs/design/CONTENT_FORMAT_BACKLOG.md`; memory entry
`project_content_format_backlog.md`.

**Evidence exists:** 20 video formats/pipelines the V-arc's 18
recipes don't cover but the primitives could ship.

**Still unknown:** Priority order; scope-lock per format.

**Territory:** product-design.

**Dependencies:** none technical. Pairs with 4c (visual
composition boundary) if that opens.

---

## §4 Suggested first-question candidates for SESSION 280 (NOT chosen)

Chris + ChatGPT choose deliberately. These are proposed for
review, ordered by a mix of blocker-status, scope, and expected
operator-value per audit-cost — Chris's judgment overrides:

1. **4f — cross-cast alias grounding.** Smallest mechanical
   change; ready-for-fix territory if approved; unblocks 4h;
   materially reduces residual dialogue-scene warning noise. Same
   ranking SESSION 279 handoff §7 gave it.
2. **Knowledge-breadth scaling.** Natural continuation of 4b
   ACCEPT; would provide adversarial-topic base rate for possible
   3.11 pairing; small experiment shape; would also test whether
   Knowledge growth interacts with the 4a residual attractor.
3. **4c visual composition boundary.** Chris's broader product
   framing (§3.1) has accumulated evidence across SESSION 278 +
   279; largest UI/product implications; audit-first slice.
4. **Beat-3 legibility (§3.9).** Small UI product-design;
   direct SESSION 279 operator friction; low cost to design +
   land; would improve future dogfood ergonomics for every
   subsequent slice.
5. **4i cross-episode epistemic asymmetry.** Largest
   storytelling upside per SESSION 279 handoff §7; substantial
   audit needed.
6. **3.10 untested text levers** OR **3.11 adversarial replication.**
   Only justified if Chris + ChatGPT decide a Q-279-4 (fix-
   planning) is worth pursuing on the writer-voice attractor
   despite the DEEP-RESIDUAL classification.

**Explicitly NOT suggested for first-slice work:**

- 4d/4e (one-specimen observations awaiting correlation).
- 4g (per-surface D-POS migration — no urgent pressure).
- 3.12 character-identity distribution architecture (interesting
  but downstream of both 4a and 4b closures).

---

## §5 What SESSION 280 must NOT do without a fresh Chris + ChatGPT scope-lock

- Do NOT open any Q-279-N slice — Q-279-3 is CLOSED.
- Do NOT open any deferred creative investigation from §3 above
  automatically.
- Do NOT modify Tyson / Ruby / Patch / Rivet / their prompts /
  business_brief / K2 corpora / memory.
- Do NOT further modify the Tyson specialty KD (§27 treatment is
  the current substrate; reversal recorded in SESSION 279 §4.2
  if ever needed).
- Do NOT flip `K6_CLAIM_VERIFIER_MODE` to `strict` (blocked by
  4f).
- Do NOT delete the legacy K6.4 verifier or the stoplist.
- Do NOT delete `verification_warnings_shadow` or
  `verification_warnings_legacy` columns.
- Do NOT install additional dependencies without explicit
  approval.
- Do NOT modify `character_os/writing_contract.py` or
  `character_os/dialogue_synthesis.py` from what SESSION 279
  found — the contract-lite substitution in the Phase 2 probe was
  runtime-only and does NOT license a permanent change.
- Do NOT ship a production fix for the writer-voice attractor
  (Q-279-3 DEEP-RESIDUAL classification explicitly does not
  license one).

---

## §6 What SESSION 280 CAN safely resume

- Read `docs/design/SESSION_279_CHARACTER_KNOWLEDGE_DEPTH_AUDIT.md`
  for full context on any Session 279 sub-slice.
- Run `python manage.py k64_shadow_diff --days=N` in `shell/` for
  ongoing shadow-diff evidence.
- Inspect any persisted composition read-only via `manage.py
  shell` (DB port 5434 per `.env`; use `set -a; source .env; set
  +a` before invocation — DB_PORT was `5433` default in some
  places but production `.env` uses `5434`).
- Re-run the SESSION 279 Q-279-3 Phase 2 probe:
  `set -a; source .env; set +a; python scripts/session279_q279_3_phase2_probe.py --config=ALL --n=3`
  (or per-condition; costs ~$0.005 per synthesis call).
- Run the 185-test Q-278 regression gate (see `SESSION_279_HANDOFF.md`
  §6) as a baseline before touching anything code-side.
- Rollback the §27 treatment KD via same SPA Ask-panel Beat 3
  gesture Chris used — paste back the 118-char baseline recorded
  at §4.2 verbatim. Not required; treatment demonstrably
  improves dialogue quality.

---

## §7 Reproduction / artifact index

### 7.1 Compositions (persisted, read-only via psql or ORM)

- **Q-279-2 Stage A (post-treatment, real-mode full render):**
  - T1 `488c37ba-ba8c-42bc-bc60-059fca81ea1f` — *"Ruby thinks Tyson is taking coffee too seriously."*
  - T2 `699916a9-2dc3-484c-b0cd-fa0d54970a0b` — *"Tyson thinks Ruby secretly entered them in a baking competition."*
  - T3 `a5c59014-d6c2-44db-b6fc-13f1fbc0bc61` — *"Ruby locks herself out of the bakery."*
- **Q-279-2 baseline compositions (pre-treatment, from SESSION 278):**
  - T1 historical `d7549fc1-ad59-42c3-99c6-6d3597bb1afa`
  - T2 historical `7177b0f5-b6e8-4366-951b-cb3c2ebe01cb`

### 7.2 Treatment KnowledgeDocument (Fox & Flour)

- KD id: `3ff45702-cb8b-49f0-82f6-97013c0f8da6`
- Title: *"Tyson's Pastry Pairing Specialty"*
- Universe: `1a0af807-dd6a-47cd-bfaa-3d088f1c105f` (Fox & Flour Bakery)
- Workspace: `4ce5486d-35a4-4bee-8745-38004adb33bc`
- `audience_scope = character`; spokespeople = {Tyson `f4de81f3-ef65-4196-a50e-38cfc6d1854f`}; `is_active=true`
- `processed_content` length: 2,317 chars (verbatim in audit §27)
- `content_hash`: `a84244ac01cbbe9ebbad72adce66be99b862facd8d7cbe872014276bb4e5e1fb`
- Chunk IDs (post-treatment):
  - `a99dba2d-2758-49b7-88b3-5f16ef94f460` (index 0, 686 chars)
  - `2548f826-d41a-4a27-a3ab-b654794185fd` (index 1, 922 chars)
  - `a02de62d-b907-4819-89a0-8199254d30b4` (index 2, 1103 chars)
- Old baseline chunk (dropped by re-ingest): `4c7954e0-49b0-44e9-9113-b3cb5b3054d5`
- Baseline `processed_content` (for potential rollback), verbatim:
  > *"Tyson is especially knowledgeable about pairing pastries with coffee and enjoys helping customers choose combinations."* (118 chars)
- Universe-audience KDs (unchanged):
  - `d40b567e-557b-49e3-aa42-8002c86c6126` — Fox & Flour Hours (57 chars)
  - `fa2c668c-d08b-4305-874c-33d99a11ccf6` — Fox & Flour holiday policy (39 chars)

### 7.3 Cast (Fox & Flour Bakery)

- Ruby `9d69a80c-ff69-4dbc-84eb-f76b02f22add` (resolved by name in the Phase 2 probe): tone=`friend`, energy=`medium`, humor=`warm`, directness=`balanced`, POV empty
- Tyson `f4de81f3-ef65-4196-a50e-38cfc6d1854f`: tone=`expert`, energy=`medium`, humor=`warm`, directness=`balanced`, POV empty

### 7.4 Cast (Patch's Workshop — reference only)

- Patch: tone=`performer`, energy=`medium`, humor=`warm`, directness=`balanced`, POV present
- Rivet: tone=`friend`, energy=`medium`, humor=`warm`, directness=`balanced`, POV present

### 7.5 Scripts

- `scripts/session279_q279_3_phase2_probe.py` — Phase 2 probe.
  Usage: `set -a; source .env; set +a; python scripts/session279_q279_3_phase2_probe.py --config=A|B|C|BC|ALL --n=3 --out=docs/design/session279_phase2/phase2_evidence.json`
  Runtime substitutions match audit §111.3-§111.4 verbatim; both
  monkeypatches `try/finally`-restored; `_verify_restored()`
  post-run.

### 7.6 Artifact directories

- `docs/design/SESSION_279_HANDOFF.md` — SESSION 279 open handoff (session-open baseline).
- `docs/design/SESSION_279_CHARACTER_KNOWLEDGE_DEPTH_AUDIT.md` — durable audit (5,443 lines).
- `docs/design/session279_phase2/` — Phase 2 evidence:
  - `phase2_evidence.json` — full JSON provenance for P2-A/B/C
  - `phase2_bc_evidence.json` — full JSON provenance for P2-BC
  - `p2{a,b,c,bc}_sample{1,2,3}.txt` — 12 raw dialogues
- `docs/design/SESSION_278_AUDIT.md` — SESSION 278 evidence (reference; NOT re-opened).

### 7.7 Session 279 commit chain (all pushed to `origin/main`)

```
55d7a80   Q-279-3 formal closure at DEEP-RESIDUAL
1dac70d   Q-279-3 P2-BC execution (DEEP-RESIDUAL fires)
14f6892   Q-279-3 P2-BC design + prediction locked BEFORE execution
35ebccb   Q-279-3 Phase 2 landed-SHA record (c579f2e)
c579f2e   Q-279-3 Phase 2 P2-A/B/C execution (locked >=50% not met; family-swap)
be57821   Q-279-3 Phase 2 design reconciliation vs Phase 1
1df3f70   Q-279-3 Phase 1 read-only scoring — A/B/C = C mixed
7a21357   Q-279-3 open — read-only audit + experiment design for 4a
e0d5a10   Q-279-2 CLOSE — 4b ACCEPT-KNOWLEDGE-DEPTH-HYPOTHESIS
a44bafa   SESSION 278 CLOSE + SESSION 279 handoff (session-open baseline)
```

### 7.8 Provider spend

- Q-279-2 Stage A: ~$0.82 (3 full dialogue-scene renders with Runway).
- Q-279-3 Phase 2 (A/B/C + BC): ~$0.07 (12 synthesis-only calls).
- **SESSION 279 net total: ~$0.89.**

---

## §8 Regression baseline

SESSION 279 did NOT touch the 185-test Q-278 regression suite.
Before any SESSION 280 code change, re-run:

```
pytest apps/compositions/tests/test_claim_verifier_dispatch.py \
       apps/compositions/tests/test_claim_verifier_ner_shadow.py \
       apps/compositions/tests/test_dialogue_synthesis.py \
       apps/compositions/tests/test_claim_verifier.py \
       apps/compositions/tests/test_stoplist_watchdog.py \
       apps/compositions/tests/test_dialogue_ai_topic_wiring.py
```

Expected: 185 green (SESSION 278 baseline).

---

## §9 Operator + environment notes

- Chris drives operator-facing SPA gestures; AI tails DB/logs/API
  in parallel (memory: `feedback_human_ai_testing_split.md`).
- Real-mode dogfood after operator-facing slices — do NOT propose
  curl as an alternative to the UI flow (memory:
  `feedback_real_mode_dogfood_after_operator_slices.md`).
- DB port is 5434 per `.env` — a Django default fallback of 5433
  will fail with a confusing "trust authentication failed" error
  via Docker port-proxy. Always `set -a; source .env; set +a`
  before `manage.py shell` or ad-hoc psycopg.
- pytest auto-regenerates `CHARACTER_OS_INVENTORY.md` — never
  commit the post-pytest version blindly (memory:
  `feedback_pytest_auto_regens_inventory.md`).

---

## §10 Closeout

SESSION 280 opens with a clean tree at HEAD **`[final commit SHA
recorded on landing]`**. All Session 279 conclusions are durable.
The next question is Chris + ChatGPT's to choose deliberately from
§3 or §4.

Working method preserved. No fix implementation authorized.
Rubric and lever hierarchy for finding 4a are locked. No new
deferred finding opened by this handoff.
