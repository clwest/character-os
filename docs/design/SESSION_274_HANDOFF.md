# SESSION 274 — Handoff

Concise starting point for a fresh Claude session. SESSION 273 is CLOSED.

**Full SESSION 273 record** — 38 numbered sections covering product orientation, Ruby/Mason substrate audit, Universe attach, KD ingest, four-run duration-failure diagnostic, §25 corrective-floor fix, Ruby Video #1 + Video #2 forensic verification, Episode-creation UI finding, one-page hypothesis, and CLOSEOUT — lives in `docs/design/SESSION_273_PRODUCT_ORIENTATION_AND_NEXT_DIRECTION.md`. Eleven frozen evidence sidecars under `docs/design/session_273_experiment_data/`.

**Full SESSION 272 record** — CORRECT_ANCHOR / `_expansion_hint` production fix — lives in `docs/design/SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md` §22.

Read at minimum §§34–38 of the SESSION 273 doc before starting SESSION 274. This handoff is orientation, not a substitute.

---

## §A. WHAT SESSION 273 DID (short)

- Stepped back from SESSION 270–272's synthesis rabbit hole. Ran a product-level orientation across the whole Character OS surface.
- Selected Ruby (fox / Fox & Flour Bakery) as a **fresh-domain wizard-default dogfood substrate** — she predates SESSION 269 and carries only `business_brief` + `personality` + `tone_archetype` (8 richer persona fields empty).
- Discovered and demonstrated **hidden knowledge contamination** — pre-Universe-attach, Ruby retrieval surfaced unrelated TANK / Tulsi / Hearth & Hollow chunks on bakery queries. Attaching Ruby to a fresh Fox & Flour Bakery Universe (`1a0af807-…`) + scoping her KD spokesperson m2m = Ruby only structurally eliminated the leak.
- Ingested Chris-approved 6,599-char bakery KD (10/10 chunks embedded).
- **Ruby's first four 90 s renders failed** at `duration_contract:too_short` — corrective outputs clustered at 893/1032/1031/1008 chars; 3/4 cleared the 972-char hint minimum but 0/4 cleared the 1080-char render acceptance minimum. Provider guard worked (zero cost) but operator reliability was unacceptable.
- Root cause (§25.4): the corrective-expansion hint accidentally inherited the SESSION 253/254 first-pass 0.90 calibration multiplier via code locality. Saturated Patch/Rivet substrate (15 successful 90 s corrective renders in [1163, 1599] chars) had historically masked the gap by overshooting the hint minimum by ~+380 chars on average.
- **§25 fix** (commit `e7e4d68`): on the expansion path only, corrective hint uses the operator target's char budget (`char_budget_for_duration(target, max_script_chars=cap)`) instead of the calibrated synth-target budget. First-pass calibration + compression retry unchanged. CORRECT_ANCHOR (SESSION 272 Slice F) preserved byte-for-byte.
- **Ruby Video #1** (`2d50f101-…`, "Why our sourdough takes its time") — 81.7 s, $0.02, verified, 11/11 material claims grounded.
- **Ruby Video #2** (`5052035e-…`, "Our celebration cakes") — 79.5 s, $0.02, verified, 17 GROUNDED + 1 SUPPORTED INFERENCE + 0 UNSUPPORTED across a distinct KD section.
- **Wizard-default multi-domain verdict: CONFIRMED directionally (n=2)** — no persona enrichment, no NarrativeMemory, no audience_hint required.
- Neither Episode warranted NarrativeMemory promotion.
- Formal product finding: current Episode-creation UI exposes internal architecture across ~4 action-required pages. One-page Episode creator is a validated SPA-only product hypothesis (zero backend changes required); **NOT authorized to build in SESSION 273**.

## §B. WHERE WE ARE

- **SESSION 273 is CLOSED.**
- **Writing Contract v6** unchanged. **CORRECT_ANCHOR** preserved. **§25 corrective-floor fix** production-verified across 2 successful renders.
- **Ruby**: `5875a7b4-cf39-433d-89b3-4e34a89a5208` · attached to Fox & Flour Bakery Universe · KD `74e7f18f-…` Ruby-only scoped · 2 successful videos · 4 preserved pre-fix failed compositions as regression evidence · 0 NarrativeMemory in her Universe · wizard-default persona (all 8 richer fields still empty).
- **Mason**: `28b9a7ea-…` · `universe_id=None` · **UNTOUCHED** in SESSION 273 · deferred as sequential fresh-character companion.
- **Repository:** `main` at the SESSION 273 CLOSEOUT commit (recorded in §H). Local `main == origin/main`. Working tree clean.

**Local-real runtime expected state** (verified at closeout):
- Django `:8010/admin/` → 302
- Media-engine `:8001/health` → `{status:ok, openai_mock:false, runway_mock:false, image_gen_mock:false, any_mock:false, llm_provider:openai, llm_model:gpt-4o-mini}`
- Vite `:5174/` → 200
- Celery `inspect ping` → 1 node online
- Zero experiment env vars across all worker PIDs

## §C. WHAT REMAINS ACTIVE / WORKING AS INTENDED

- **Writing Contract v6** — universal AUDIENCE-AWARE COMMUNICATION invariant in `_solo_scene_contract`. Not touched.
- **Persona** — `character_point_of_view`, `personality`, `voice_signature_phrases`, `voice_avoid_phrases`, `voice_energy/humor/directness` remain responsible for character-native voice. SESSION 273 additionally established that a MINIMAL persona (only `business_brief` + `personality` + `tone_archetype`) can produce coherent multi-domain output when combined with §25.
- **`Composition.audience_hint`** — per-render listener descriptor. Working. Ruby's videos left it empty.
- **`_expansion_hint` production text** — SESSION 272 Slice F CORRECT_ANCHOR wording preserved. §25 changed the CALLER's argument choice (raw-target budget instead of synth-target budget), not the function body.
- **`_experimental_expansion_revision_hint`** — Q-270-15c experimental hint, dormant. Received the same §25 caller-side treatment for symmetry; still gated OFF by default.
- **`_compression_hint`** — unchanged. Still opens with `REWRITE THE SAME NARRATIVE BELOW`. Not scope of SESSION 273. Analog fix carried forward as optional future work.

## §D. SESSION 274 PRIMARY OPENING QUESTION

> **What should shared / global knowledge mean as a product capability in Character OS, and what does the current implementation actually do across workspace, Universe, and character boundaries?**

**IMPORTANT:** SESSION 274 must begin **READ-ONLY** — semantic / product / mechanical characterization first.

Do NOT begin by:
- changing retrieval logic
- renaming UI labels
- migrating existing KnowledgeDocuments
- assuming "unassigned" is a bug
- assuming global knowledge is desirable
- assuming global knowledge should be removed

What SESSION 273 established mechanically about shared/global knowledge (§17.6):
- `universe = None` + `spokespeople = {}` behaves as **workspace-shared** retrieval eligible for any teammate whose `universe_id` is also `None`.
- `universe = U` + `spokespeople = {}` behaves as **Universe-shared** retrieval eligible for any teammate in Universe U.
- Character-scoped KDs (`spokespeople = {A}`) restrict retrieval eligibility to teammate A.
- The four scopes can coexist; retrieval currently OR's the two eligibility branches and ranks purely by cosine distance (no priority boost for character-specific).
- §13.3 demonstrated that unbound workspace-shared knowledge can dominate cosine ranking on irrelevant queries — even a bakery-native probe pulled TANK financing + Tulsi + Bookstore chunks.

What SESSION 273 did **NOT** characterize (ten open sub-questions):
1. What are the operator-intended use cases for each of the four scopes?
2. Who can retrieve each class? (mechanically clear; product-intent unclear)
3. What happens when shared + character-specific knowledge both match on the same query? (currently: cosine-only)
4. Does character-specific knowledge deserve retrieval priority?
5. Can unrelated shared knowledge outrank relevant character-specific knowledge? (§13.3 says yes)
6. Does `top_k` cause starvation / competition?
7. Multi-character same-Universe behavior?
8. Cross-Universe boundaries — are they correct?
9. Operator terminology: is "unassigned" the right label if it actually means "shared"?
10. UI copy: would explicit *"Shared with everyone in this Universe"* / *"Shared workspace knowledge"* / *"Only Ruby will retrieve this"* clarify intent?

## §E. SESSION 274 STARTING CHECKLIST

- [ ] Reconstruct current shared/global knowledge scope semantics mechanically (from `shell/apps/embeddings/retrieval.py` + K6.4 pipeline)
- [ ] Define product-intended use cases before proposing changes
- [ ] Test workspace-global retrieval (`Universe=None`, `spokespeople={}`)
- [ ] Test workspace character-specific retrieval (`Universe=None`, `spokespeople={A}`)
- [ ] Test Universe-shared retrieval (`Universe=U`, `spokespeople={}`)
- [ ] Test Universe character-specific retrieval (`Universe=U`, `spokespeople={A}`) — Ruby's Fox & Flour KD is a live specimen of this class
- [ ] Test coexistence / precedence when shared + private both match the same query
- [ ] Test same-Universe multi-character behavior
- [ ] Test cross-Universe isolation
- [ ] Assess `top_k` starvation / competition
- [ ] Assess operator terminology (`unassigned` vs `shared`) at the SPA copy level
- [ ] Recommend product model (may or may not require code / UI changes)
- [ ] ONLY THEN decide whether implementation changes are needed

These are starting hypotheses / tasks. **Not permission to execute all of them blindly.**

## §F. SECONDARY CANDIDATES (carried but not primary)

Not for SESSION 274 opening — these are candidates for later authorization once shared-knowledge is characterized:

| Item | Status | Notes |
| --- | --- | --- |
| **One-page Episode creator** | SPA-only feasible (SESSION 273 §32); not implemented | Requires Chris authorization for a build slice. Zero backend changes. All existing APIs (`POST /api/episodes/` atomic `cast_ids` + `POST /api/compositions/` auto-dispatch) sufficient. |
| **Composition observability SPA** | 9 SESSION 262 fields captured per render but not surfaced in the SPA (§5 / §27.9.6) | Ruby's forensics required opening the DB. Same operator visibility gap SESSION 272 had to work around via shell scripts. |
| **Mason companion dogfood** | Deferred (SESSION 273 §11.9 Slice ε) | Second fully-fresh character (Mason `28b9a7ea-…`, coffee-shop). Would strengthen wizard-default multi-domain verdict from n=2 to n≥3. Untouched substrate. |
| **PublishBundle dogfood** | Optional (SESSION 273 §11.9 Slice δ) | Assemble a small `PublishBundle` from Ruby Video #1 + #2 to close the idea→distributable-clip loop. |
| **Additional Ruby Episodes** | Optional | Unused KD sections: Bakery routines, Pastries, Ingredients & sourcing, Ruby's reason for operating. |
| **Compression-hint analog** | Carried from SESSION 272 §22.5.1 | `_compression_hint` still opens with `REWRITE THE SAME NARRATIVE BELOW`. Same class of false anchor as pre-Slice-F `_expansion_hint`. Not experimentally evaluated. |
| **Q-270-16 K6.4 verifier false positives** | Carried from SESSION 271 / 272 | Sentence-initial capitalized adverbs (`Well`, `Very`, `Briefly`, `Carefully`) misclassified as proper nouns. Standalone verifier-quality slice. |
| **YouTube ingest silent-failure** | Memory `project_youtube_ingest_silent_failure` | Reports "processed" but trafilatura captures nothing; needs detect-reject + per-host extractor. |
| **REPO RED Shape β** | Carried from SESSION 272 §22.5.5 | Canned-quote / voice-lock authoring pathology. Distinct from what CORRECT_ANCHOR + §25 solved. Future architectural concern. |

## §G. HARD RULES FOR SESSION 274

- Begin SESSION 274 with **read-only characterization** of shared/global knowledge scope semantics. Do not modify retrieval, UI copy, or KD assignments in the first slice.
- Do NOT retry any Ruby render without authorization (Ruby's two successful videos + four preserved failures are the durable evidence base).
- Do NOT modify Ruby, her KD, her Universe, or her Episodes without authorization.
- Do NOT begin Mason dogfood without authorization — it is a legitimate candidate but requires its own scoping decision.
- Do NOT precommit to fixing Q-270-16, the compression hint, YouTube ingest, or REPO RED.
- Do NOT precommit to implementing the one-page Episode creator; it is a validated hypothesis awaiting a product decision.
- Do NOT precommit to any specific direction. Chris's product judgment on what matters most next is required input.

SESSION 273 was a fresh-substrate dogfood arc that also happened to surface a real duration-calibration defect + two significant product findings. SESSION 274 should open with the highest-leverage architectural product question SESSION 273 left uncharacterized.

## §H. SESSION 273 CLOSEOUT COMMIT + PROVENANCE

- SESSION 273 CLOSEOUT commit: **`7b95798`** — `docs(session-273): §34-§38 CLOSEOUT + SESSION 274 handoff`
- §25 fix commit: `e7e4d68`
- Ruby Video #1 forensics commit: `e275085`
- Ruby Video #2 + one-page hypothesis commit: `7401308`
- Full commit trail from SESSION 273 open to close: `git log --oneline docs/design/SESSION_273_*.md docs/design/session_273_experiment_data/`

## §I. RECOMMENDED SESSION 274 START

1. `git status && git log --oneline -10` — verify main is at the SESSION 273 CLOSEOUT SHA and working tree is clean.
2. `bash scripts/start-local-real.sh` if services aren't already up.
3. Read `docs/design/SESSION_273_PRODUCT_ORIENTATION_AND_NEXT_DIRECTION.md` §§34–38 (arc narrative + final verdicts + evidence index + invariants + closeout). Skim §17.6 (the frozen shared/global-knowledge question) and §25 (the corrective-floor fix).
4. Ask Chris: *before we characterize shared/global knowledge, is there a specific operator use case you want the characterization framed around, or should we characterize the four scopes generically first?* Do not steer.
5. First slice should be read-only: build a mechanical scope-semantics matrix from source + Ruby's live specimens (character-scoped Fox & Flour KD is a live example of one class; the 9 unbound workspace KDs from §11.5 are live examples of another).

---

**End of SESSION 274 handoff. SESSION 273 CLOSED. Writing Contract v6 unchanged. CORRECT_ANCHOR preserved. §25 corrective-floor fix production-verified across two Ruby videos. Wizard-default multi-domain verdict confirmed (n=2, directional). Shared/global knowledge semantics carried as SESSION 274 primary opening question. One-page Episode creator is a validated feasible hypothesis awaiting Chris's authorization. Mason available as second fresh substrate. Chris decides.**
