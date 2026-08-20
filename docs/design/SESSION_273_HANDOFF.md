# SESSION 273 — Handoff

Concise starting point for a fresh Claude session. SESSION 272 is CLOSED.

**Full SESSION 272 record** — 22 numbered sections covering Slices A through G plus the CLOSEOUT — lives in `docs/design/SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md`. Nine frozen evidence sidecars under `docs/design/session_272_experiment_data/` (Slice B setup + A/B; Slice C n=5 replicate + aggregate; Slice E three-condition ablation + aggregate; Slice G production dogfood forensics).

**Full SESSION 271 record** — the audience-aware `solo_scene` architecture ratification — lives in `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md`.

**Full SESSION 270 record** — audience-aware character-performance research — lives in `docs/design/SESSION_270_AUDIENCE_AWARE_PERFORMANCE_AUDIT.md`.

Read at minimum §22 of the SESSION 272 audit doc before starting SESSION 273. This handoff is orientation, not a substitute.

---

## §A. WHAT SESSIONS 270 / 271 / 272 WERE TRYING TO SOLVE

At a high level, three consecutive research arcs on the same substrate:

- **SESSION 270** — proved Character OS can adapt *how* a character addresses a listener (register / metaphor / explanation strategy) without changing *who* the character is (identity / humor / factual grounding). Four audience-conditioned real-mode renders on tightly-controlled substrate. Bounded caveat: residual technical vocabulary occasionally survived corrective expansion into the accepted script.
- **SESSION 271** — designed and shipped Writing Contract v6 with a universal `AUDIENCE-AWARE COMMUNICATION` invariant in `_solo_scene_contract`, plus the persisted `Composition.audience_hint` field (Option C hybrid). Verdict B — RATIFY V6 WITH KNOWN LIMITATION. The known limitation: canonical KnowledgeDocument terminology (`call APIs`, `state`, `where the behavior first becomes incorrect`) sometimes reappeared verbatim in corrective-expanded Draft B. SESSION 271 §191.9 ranked this residual as **C (KnowledgeDocument lexical gravity) + D (corrective-pass expansion)**.
- **SESSION 272** — deferred question: how should factual knowledge be authored to give synthesis accessible material without dumbing down expert knowledge or baking audience-specific prose into KnowledgeDocuments? The arc ran through: cross-character corpus audit (Slice A), Option D paired-paraphrase experiment at n=1 (Slice B), multi-shot replicate at n=5 (Slice C — failed to replicate), reframe to corrective-pass hypothesis (Slice D), three-condition hint ablation (Slice E — decisive), production fix (Slice F — CORRECT_ANCHOR), production dogfood (Slice G — verified). See §B for the final state.

---

## §B. WHERE WE ARE

- **SESSION 272 is CLOSED.** Verdict: E1-DOMINANT — the corrective-hint false anchor `REWRITE THE SAME NARRATIVE ABOVE` was the load-bearing regression driver. KnowledgeDocument shape was demoted to bounded/secondary.
- **CORRECT_ANCHOR fix is PRODUCTION VERIFIED.** `character_os.duration_contract._expansion_hint` now emits `EXPAND YOUR SCRIPT TO AT LEAST` (instead of `REWRITE THE SAME NARRATIVE ABOVE`). All other production hint wording preserved byte-for-byte, including all 4 references to `knowledge chunks`. Production hint sample sha256 `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd`.
- **Slice G dogfood** — Composition `8cb9e115-d7a9-4af5-ba86-746a5e5bbcc1` produced zero attractor leakage on a real production Rivet substrate even against a retrieved chunk containing the exact verbatim strongest attractor. Rivet identity was strengthened by corrective expansion (four new signature-line drops in Draft B). Verified. Cost $0.02. Final clip 85.9s.
- **Writing Contract version is 6** and unchanged.
- **Q-270-15c is CLOSED / deferred indefinitely.** The env-gated `previous_draft` supply path (`CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT`) remains dormant + inactive by default. Its 20-test contract suite (`test_session271_corrective_revision.py`) remains as regression trip-wires. Do NOT reactivate without a specific new specimen requiring it.
- **Q-270-16 remains OPEN.** K6.4 verifier misclassifies sentence-initial capitalized adverbs (`Well`, `Very`, `Briefly`, `Carefully`, etc.) as proper nouns. Slice G added `Briefly` + `Carefully` on Composition `8cb9e115.verification_warnings` as durable false-positive evidence. NOT scheduled for fixing.
- **Repository:** `main` at the SESSION 272 CLOSEOUT commit (SHA recorded in §H). Local `main == origin/main`. Working tree clean.

**Local-real runtime expected state** (verified at SESSION 272 closeout):
- Django `:8010/admin/` → 302
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`
- Vite `:5174/` → 200
- Celery `inspect ping` → replies
- Zero experiment env vars across all worker PIDs

---

## §C. WHAT REMAINS ACTIVE / WORKING AS INTENDED

- **Writing Contract v6** — the universal AUDIENCE-AWARE COMMUNICATION invariant in `_solo_scene_contract` remains the primary character-agnostic accessibility layer. Not touched by SESSION 272.
- **Persona** — `character_point_of_view`, `personality`, `voice_signature_phrases`, `voice_avoid_phrases`, `voice_energy/humor/directness` — remains responsible for character-native communication. Slice C established that WCV6 + persona produce ~4 accessible model-generated reformulations per Draft B independent of KnowledgeDocument shape. Not the bottleneck; do not blame persona for future regressions without evidence.
- **`Composition.audience_hint`** — the per-render listener descriptor (SESSION 271 §187 Option C hybrid). Persisted, immutable-after-first-write, composed with the universal WCV6 invariant. Working.
- **`_expansion_hint`** — Slice F CORRECT_ANCHOR version is production. Do NOT edit further without controlled evaluation.
- **`_experimental_expansion_revision_hint`** — Q-270-15c experimental hint. Dormant but preserved. Do NOT enable without explicit reason.

---

## §D. KNOWLEDGE-LEXICAL-GRAVITY STATUS

- Real cross-character phenomenon. Verified across PATCH `19778800`, RIVET `71e2ec43`, PENNY `e284edc9`, REPO RED `ee7b7e5c` (§3.3). Dense enumeration / single lexical surface is how Character OS knowledge is currently authored — this is a structural property of the corpus.
- **Bounded / secondary, not primary.** Slice C at n=5 established that KnowledgeDocument shape changes produce a Draft-B canonical-count delta within variance (CTL 3.20 vs EXP 3.00). Model-generated accessible expressions do the accessibility work regardless of doc shape.
- **Not currently blocking anything.** Slice G dogfood confirmed that the CORRECT_ANCHOR fix alone suppresses the strongest attractor even when the retrieved chunk contains it verbatim.
- **Do NOT** propose knowledge-authoring conventions in SESSION 273 unprompted. If Chris raises knowledge-shape as an open question, treat that as a fresh conversation, not a continuation.

---

## §E. OPEN ITEMS CARRIED FORWARD (NONE AUTOMATICALLY PRIORITIZED)

| Item | Status | Notes |
| --- | --- | --- |
| **Compression-hint analog fix** | Optional / uninvestigated | `_compression_hint` still opens with `REWRITE THE SAME NARRATIVE BELOW` — same class of false-anchor bug as pre-Slice-F `_expansion_hint`. **NOT experimentally evaluated in SESSION 272.** Could be either (a) replicate Slice E three-condition ablation on the compression path, or (b) ship the analog change with a shorter dogfood. Sha256 for regression pin: `78e40309734620471aa3858269312d600fe9de8f4cd7b1d9f9e670a95e9bf3dd`. Chris's discretion whether to schedule. |
| **Q-270-16 verifier proper_noun false positives** | Open, out of scope for SESSION 272 | Sentence-initial capitalized adverbs misclassified as proper nouns. Cumulative evidence: SESSION 271 §E baseline + Slice G specimens `Briefly` (pos 128) and `Carefully` (pos 1097) on Composition `8cb9e115`. Standalone verifier-quality slice. |
| **Slice C `verification_warnings` capture gap** | Trivially fixable | Slice C `_run_one_trial` didn't persist `verification_warnings` list, making the Slice E K6.4 cross-condition warning comparison unreliable. Only matters if the Slice C substrate is ever revisited. |
| **REPO RED Shape β / canned-quote voice-lock** | Distinct future architectural concern | REPO RED KnowledgeDocument `ee7b7e5c` mixes canned character quotes, anti-scripts, content-strategy directives, and audience prescriptions with factual claims. **NOT solved or touched by CORRECT_ANCHOR.** Preserved as a knowledge-authoring pathology of a different class than the one SESSION 272 addressed. Do not automatically schedule work. |
| **Substrate saturation bookkeeping** | Ongoing discipline | SESSION 271 memory `project_patch_ai_agents_substrate_saturated` should be updated to include Rivet + reproducibility (Slice G) as a rendered specimen. Substrate variety discipline continues. Future architecture experiments should prefer fresh substrates. |

---

## §F. SUBSTRATE HYGIENE

- **Patch / AI-Agents** is heavily saturated (5+ same-topic historical renders + Slice G peripheral). Do NOT use for casual dogfood.
- **Rivet on reproducibility / debugging** — Slice B/C used the disposable Rivet clone; Slice G used the real production Rivet. `Rivet explains why one good result isn't enough` (Composition `8cb9e115`) is now a rendered specimen. If SESSION 273 needs Rivet dogfood, prefer a different Rivet-flavored topic (change-one-thing / cheap-failure / metrics-need-context / robot-character-testing) or a different character altogether.
- **Fresh characters / topics / substrates preferred** for any new experimental work.
- **The Slice B/C disposable substrates** (`session272-rivet-debug-ctl` / `session272-rivet-debug-exp` workspaces + `d8ab3d2c` / `64c91888` shadow docs) are retained under §22.6 non-changes. Delete only if a specific reason arises; otherwise they are cheap to leave in place.

---

## §G. HARD RULES FOR SESSION 273

- **Begin SESSION 273 by orienting to the repository and discussing with Chris what provides the highest-value next step before modifying code.**
- Do NOT precommit to fixing Q-270-16.
- Do NOT precommit to fixing the compression hint.
- Do NOT precommit to knowledge-authoring experimentation.
- Do NOT precommit to REPO RED cleanup.
- Do NOT precommit to any specific problem class.

SESSION 272 was a deep multi-slice causal investigation. SESSION 273 should regain product-level perspective before choosing another rabbit hole. Chris's product-level judgment on what matters most next is required input before any implementation.

---

## §H. SESSION 272 CLOSEOUT COMMIT + PROVENANCE

- SESSION 272 CLOSEOUT commit: **`_SHA_recorded_after_commit_`** (populated by the CLOSEOUT commit step)
- Slice F production fix commit: `14e49b1`
- Slice G forensics commit: `55369c0`
- Full commit trail from SESSION 272 open to close available via `git log --oneline docs/design/SESSION_272_*.md docs/design/session_272_experiment_data/`.

---

## §I. RECOMMENDED SESSION 273 START

1. `git status && git log --oneline -10` — verify main is at the CLOSEOUT SHA and working tree is clean.
2. `bash scripts/start-local-real.sh` if services aren't already up (SESSION 272 left them up).
3. Read `docs/design/SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md` §22 (CLOSEOUT). Skim §21 (Slice G forensics) and §19 (Slice E ablation) if a specific SESSION 273 question demands the causal chain.
4. Ask Chris: *what provides the highest-value next step now that SESSION 272 has closed?* Options include (but are not limited to) any of §E's open items, or something completely unrelated. Do not steer.

---

**End of SESSION 273 handoff. SESSION 272 CLOSED. Writing Contract v6 ratified and active. CORRECT_ANCHOR production verified. Q-270-15c closed. Q-270-16 open, unscheduled. No pre-commit to any next-slice direction. Chris decides.**
