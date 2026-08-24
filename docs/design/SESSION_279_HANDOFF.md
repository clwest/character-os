# SESSION 279 — Handoff (from SESSION 278)

## Status at the top

- **SESSION 278 is CLOSED.**
  - Closeout ref: `docs/design/SESSION_278_AUDIT.md` §"SESSION 278 — CLOSEOUT MARKER".
  - Full evidence: same document, 3,400+ lines across Q-278-1 → Q-278-4.3 slices + shadow-window dogfood + dual-write dogfood + post-flip dogfood.
- **K6.4 verifier arc landed on the dialogue-scene surface.** D-POS Hybrid classifier is authoritative on `Composition.verification_warnings` for new dialogue-scene compositions. Legacy K6.4 continues in shadow.
- Adjacent surfaces (Script, ConversationMessage, talking-head / long-form Composition) remain legacy-authoritative pending their own scope-locked audits.
- Real-DB state at closeout (verified read-only during Q-278-4.3 dogfood): shadow + legacy columns populated on new dialogue-scene rows; historical rows unchanged.

**Purpose of this document:** compact self-contained orientation for a fresh SESSION 279 Claude + ChatGPT so neither has to re-read all of SESSION 278 to resume work.

---

## §1 Current verifier substrate (as of 2026-08-24 close)

```
dialogue_scene composition
  ├── K6.4 dispatcher                 [character_os/claim_verifier_dispatch.py]
  │     ├── legacy K6.4 verifier      [runs on every turn — shadow substrate]
  │     └── D-POS Hybrid classifier   [runs on every turn — AUTHORITATIVE]
  │
  ├── Composition.verification_warnings         = D-POS output  (SPA panel reads this)
  ├── Composition.verification_warnings_shadow  = D-POS output  (mirror; symmetric)
  ├── Composition.verification_warnings_legacy  = legacy output (post-flip shadow substrate)
  ├── DialogueTurn.verification_warnings        = per-turn D-POS
  ├── DialogueTurn.verification_warnings_shadow = per-turn D-POS
  └── DialogueTurn.verification_warnings_legacy = per-turn legacy

talking_head / long_form_ad composition
  └── legacy K6.4 verifier            [AUTHORITATIVE; no dispatcher; no shadow]

Script (B-arc apps.scripts)
  └── legacy K6.4 verifier            [AUTHORITATIVE; no dispatcher; no shadow]

ConversationMessage (K6.5)
  └── legacy K6.4 verifier            [AUTHORITATIVE; no dispatcher; no shadow]
```

### Authority flags

- `CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy" | "d_pos"` (default `"d_pos"` post Q-278-4.3). Rollback via env or Django settings. Settings > env > default. Whitespace-only / invalid values fall back to default + WARNING.
- `CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT` — retired for dialogue-scene path (dispatcher runs both classifiers unconditionally). Remains defined for adjacent surfaces that read it directly, but no adjacent surface actually consumes it today.
- `K6_CLAIM_VERIFIER_MODE = "warn" | "strict" | "off"` — UNCHANGED across SESSION 278. Resolves to `"warn"` (default).

### Rollback (one-flag)

```
export CHARACTER_OS_K64_DIALOGUE_AUTHORITY=legacy
bash scripts/start-local-real.sh
```

The next new dialogue-scene render will have `verification_warnings == verification_warnings_legacy` again. Historical rows are additive-preserving; no DB surgery required.

---

## §2 Dependency footprint added this session

- `spacy>=3.8,<3.9` (MIT).
- `en_core_web_sm==3.8.0` pinned wheel via GitHub release URL (MIT for v3.5+; verify at install).
- `numpy>=2.3,<3` pinned explicitly to prevent pip resolver downgrades under the shared venv.

Measured operational cost (Q-278-3.1 + Q-278-4.2):
- Install: ~45 MB combined on disk.
- Per-worker RSS after model load: ~50-70 MB incremental.
- Cold-load: ~215 ms once per worker at first synthesis.
- Per-turn inference: ~5-30 ms. Negligible vs 60-120 s Runway render.

---

## §3 Regression suite baseline

**185 tests green at close** across:
- `apps/compositions/tests/test_claim_verifier_ner_shadow.py` (38 D-POS regression tests)
- `apps/compositions/tests/test_claim_verifier_dispatch.py` (27 dispatcher tests including authority resolver, dual-run, defensive fallback, strict-mode preservation, scope-lock source guards, dual-write flattener invariants)
- `apps/compositions/tests/test_dialogue_synthesis.py`, `test_claim_verifier.py`, `test_stoplist_watchdog.py`, `test_dialogue_ai_topic_wiring.py` (116 adjacent tests)

Two source-inspection scope-lock guards continue to enforce the Option A boundary:
- `test_script_synthesis_does_not_import_dispatcher`
- `test_conversation_synthesis_does_not_import_dispatcher`

---

## §4 Deferred findings from SESSION 278

**Each preserved as a distinct hypothesis.** SESSION 279 must NOT conflate them. Chris + ChatGPT choose SESSION 279's investigation from this list (or something else); nothing here is auto-triggered.

### 4a. Cross-World / generalized writer / rhetorical voice

Character OS may have a recurring writer voice that leaks across otherwise distinct Worlds and characters. Evidence accumulated across Q-278-3.2 Specimen 2 (Patch's *"Whether it should be is a different question."*), Q-278-3.2 Specimen 4 ("one narrow job" / "what are we trying to prove" / "if it fails, we say it failed" methodology-adjacent language), Q-278-4.2 Specimen 3 (*"If I cannot explain what an item might help us test, it goes."*), and Q-278-4.3 Specimen 3 (Tyson's *"That's evidence."* in a bakery context where "evidence" doesn't feel like natural bakery language).

**Do NOT solve with banned words.** The hypothesis is about a recurring voice, not about individual words. If Chris opens this, evidence gathering would start by grepping every completed Composition's `synthesized_brief` across characters and Worlds for candidate patterns, then contrast Worlds to test whether the pattern is character-specific or platform-wide.

### 4b. Tyson identity-as-expert vs Knowledge-depth needed to perform expertise

Distinct from 4a. Two independent specimens (Q-278-4.2 Specimen 2 coffee-taking-too-seriously; Q-278-4.3 Specimen 3 baking-competition) show Tyson talking ABOUT pairing/pastry expertise generically without demonstrating concrete domain knowledge, despite retrieved character-specific Knowledge `Tyson's Pastry Pairing Specialty`. Concrete quotes: *"which pastry to have with coffee"*, *"coffee has opinions"*, *"A good pairing can make a handcrafted pastry feel finished..."*

**Substrate distinction to preserve:**
- **Character identity/role** — what Tyson is SUPPOSED to be good at (lives on `Teammate.personality` / `who_you_help` / `what_you_sell` / `business_brief`).
- **Character-specific Knowledge** — the actual domain information Tyson can draw upon to DEMONSTRATE that expertise (lives on `KnowledgeDocument` / `KnowledgeChunk` scoped to that character).

**Possible future operator experiment:** give Tyson a small, high-quality character-specific coffee/pastry Knowledge corpus, then re-render with minimal topics. If dialogue becomes measurably more concrete without operator prompting for coffee details, that is evidence Character OS correctly separates identity from expertise Knowledge.

**Do NOT conflate with 4a.** More Knowledge might improve expertise depth without addressing cross-World rhetorical leakage.

### 4c. Visual-composition boundary

Dialogue synthesis progressively introduces visually important scene objects that the current talking-head composition cannot show. Cross-specimen evidence:
- Q-278-3.2 Specimen 3 (Ruby mascot) — small fox mascot, loaf tucked under arm, coffee cup, party hat, three proposed sketches.
- Q-278-3.2 Specimen 4-adjacent (prior Patch/Rivet dogfood) — "the box" and similar scene objects.

Same class of behavior across different characters (Ruby+Tyson, Patch+Rivet) and different Worlds (Fox & Flour, Patch's Workshop). Operator did NOT prompt visual details — the synthesizer expanded the topic into visual storytelling that exceeded the talking-head visual grammar.

Possible future focused question (NOT opened): *When synthesis makes an unseen object or concept important to the scene, how should Character OS determine whether the composition needs additional visual representation?*

**Do NOT** implement image generation, PiP / B-roll / cutaway architecture, or an "every mentioned object gets a visual" assumption speculatively.

### 4d. Possible underdeveloped / abrupt scene endings near lower duration boundary

One-specimen observation from Q-278-4.2 Specimen 3 (junk composition). Target 90s; predicted 72s; final 72.3s (exactly 0.80 = lower boundary of the ±20% tolerance). Chris expected roughly 2-4 more turns to finish landing the scene. Narrowly recorded as *possible underdeveloped / abrupt scene ending near the lower duration boundary*. **Not opened as an investigation on one specimen.** Correlate if a pattern emerges.

### 4e. Isolated avatar/video-quality degradation

One-specimen observation from Q-278-4.3 Specimen 2 (button composition). Weaker mouth/lip-sync in places; visible clip/merge boundaries. Chris explicitly noted this has NOT been historically common. **Do NOT investigate on one specimen.** Preserve for future correlation only.

### 4f. Cross-cast alias grounding substrate gap

Surfaced by Q-278-4.3 Specimen 3 (`Tyson` BOTH-parity flag on a one-word Ruby turn *"Tyson."*). Under the current `build_allowed_vocabulary` contract (`character_os/claim_verifier.py:741-803`), each speaker's `allowed_vocabulary` includes only that speaker's own `Teammate.name` + KNOWN_PLATFORM_TERMS + entries extracted from that speaker's voice metadata. Cross-cast character names are NOT included, so a dialogue-scene speaker addressing another cast member surfaces as an unsupported entity if the co-cast name isn't in the speaker's factual corpus.

Both classifiers flag under this contract; the Q-278-4.3 flip did not cause this — it's a substrate gap that pre-existed the K6.4 dispatcher work. `synthesize_dialogue` has the full `alias_to_teammate: dict[str, Teammate]` cast map available in-scope.

**Possible future question:** should `build_allowed_vocabulary` extend to include cross-cast aliases when called from a dialogue-scene context? Should it include ONLY the current cast, or every Teammate in the Universe? Small mechanical change if approved; interesting per-Universe-scope implications.

### 4g. Adjacent-surface D-POS migration

The dialogue-scene D-POS authority is proven stable. Script, ConversationMessage, and talking-head / long-form Composition remain legacy-authoritative. Each surface has:
- Its own `verification_warnings` column with its own SPA panel.
- No shadow column today.
- No shadow-classifier invocation today (per grep-verified fact in Q-278-4.2 boundary challenge).

**If migrated, each surface needs its own scope-locked audit** including per-surface shadow window, per-surface dual-write plumbing, per-surface Slice-3 acceptance gate. The Q-278-4.2 Option A boundary invariant explicitly requires this.

### 4h. Future strict-mode audit

`K6_CLAIM_VERIFIER_MODE` remains `warn`. Under the current default `warn`, D-POS warnings are surfaced but never block a render. A future strict-mode flip would:
- Cause D-POS to raise `ClaimVerifierError` on any unsupported claim (D-POS currently never raises).
- Convert the observed `Tyson` cross-cast-address BOTH-parity into a render-blocker.
- Convert any legitimate D-POS hallucination catch into a render-blocker (the founding K6.4 intent).

**Downstream of 4f** — the cross-cast alias substrate gap must be addressed first, otherwise a strict-mode flip would false-block on every dialogue where one character addresses another.

### 4i. Cross-episode epistemic asymmetry (PATCH OVERRIDES)

Surfaced by Q-278-3.2 Specimen 4-addendum. Rivet-scoped narrative memory *"While Patch was out, Rivet found that the workshop agent had quietly built a folder named 'PATCH OVERRIDES' tracking every recommendation Patch had ignored. Rivet chose not to tell him."* The generated dialogue behaves consistently with the memory's asymmetry: Patch approaches the hidden subject unknowingly (*"And if it remembers every recommendation you ignore?"*); Rivet responds in a way informed by his private knowledge without exposing it (*"Well. It may already have a system for that."*).

**Preserve the KEY PRODUCT QUESTION (do not propose implementation):**

> **What happens when one character knows something another character does not, how is that knowledge represented and respected across future scenes, and what new storytelling behavior becomes possible?**

Observed once. Not yet mechanically established that Character OS *maintains* arbitrary per-character epistemic state across episodes (Q-278-3.2 Specimen 4-addendum lists six specific unproven claims). If a future audit opens this, the mechanical entry point is the per-character `memory_ids` + per-character retrieved-K2 provenance already persisted on Composition rows.

---

## §5 What SESSION 279 must NOT do without a fresh Chris + ChatGPT scope-lock

- Do NOT open Q-278-5 automatically.
- Do NOT begin any deferred creative investigation from the list above.
- Do NOT modify Tyson / Ruby / Patch / Rivet / prompts / business_brief / K2 corpora / memory.
- Do NOT fix the cross-cast alias substrate gap.
- Do NOT migrate adjacent surfaces (Script, ConversationMessage, talking-head, long-form).
- Do NOT flip `K6_CLAIM_VERIFIER_MODE` to `strict`.
- Do NOT delete the legacy K6.4 verifier or the stoplist.
- Do NOT delete the `verification_warnings_shadow` or `verification_warnings_legacy` columns.
- Do NOT install additional dependencies without explicit approval.

## §6 What SESSION 279 CAN safely resume

- Read `docs/design/SESSION_278_AUDIT.md` for full context on any Q-278-N slice.
- Run `python manage.py k64_shadow_diff --days=N` in `shell/` for ongoing shadow-diff evidence.
- Inspect any persisted composition read-only via `manage.py shell`.
- Run the 185-test regression gate (`pytest apps/compositions/tests/test_claim_verifier_dispatch.py apps/compositions/tests/test_claim_verifier_ner_shadow.py apps/compositions/tests/test_dialogue_synthesis.py apps/compositions/tests/test_claim_verifier.py apps/compositions/tests/test_stoplist_watchdog.py apps/compositions/tests/test_dialogue_ai_topic_wiring.py`) as a baseline.
- Rollback D-POS authority via env flag + stack restart at any time (regression-tested).

---

## §7 Operator's next natural decisions

Chris + ChatGPT will choose SESSION 279's investigation from the deferred list in §4 (or something else surfaced by fresh operator work). Nothing here is auto-triggered. Suggested review order — most operator-value-per-audit-cost first, subject to Chris's judgment:

- 4f (cross-cast alias substrate gap) — smallest mechanical change; small risk; unblocks a natural future strict-mode audit; would materially reduce residual dialogue-scene warning noise.
- 4b (Tyson identity vs Knowledge depth) — small operator experiment (author a small character-specific Knowledge corpus); high signal on substrate correctness.
- 4i (cross-episode epistemic asymmetry) — largest storytelling upside; needs mechanical audit before any implementation.
- 4a (writer-voice leakage) — largest scope; needs cross-character/cross-World evidence-gathering first.
- 4c (visual composition boundary) — high stakes but broad design implications.
- 4d / 4e — one-specimen observations; wait for correlation.
- 4g / 4h — downstream of 4f; wait.

Suggested is not chosen. Chris + ChatGPT decide.

---
