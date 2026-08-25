# SESSION 283 — Handoff (from SESSION 282)

## Status at the top

- **SESSION 282 stopped mid-slice** for documentation
  closeout. Not "closed" in the S281 sense; the
  Slice 282.2 longitudinal observation has been designed,
  baselined, methodologically recalibrated (§22), and
  corrected for internal consistency (§24), but the
  first post-T0 Chris gesture has NOT occurred.
- **Full audit trail** at
  `docs/design/SESSION_282_ORIENTATION_AND_SCOPE_LOCK.md`.
  §26 is the stopping-state closeout.
- **SESSION 283 must NOT begin a Chris gesture without
  explicit Chris + ChatGPT re-authorization.** The
  gesture is designed and pre-authorized as CLEANLY
  INTERPRETABLE + RECOMMENDED, but was intentionally
  held back at the SESSION 282 stop.

---

## §1 Repo state to verify

```
git rev-parse HEAD          # should descend from SESSION 282 closeout SHA
git status                  # expect clean
git branch --show-current   # expect main
```

Full SESSION 282 SHA chain lives at
`SESSION_282_ORIENTATION_AND_SCOPE_LOCK.md §26.7`.

If working tree is not clean, PAUSE and investigate.

---

## §2 What SESSION 282 shipped

### 2.1 Slice 282.1 — curator-loop robustness diagnostic (COMPLETE)

* Q282.1 PASS with §16.4 caveat.
* n=3 curator reruns on F&F composition `772e9012` +
  n=1 curator call on PW composition `fcba3242`.
* All 12/12 candidates character-attributed +
  story-state-shaped.
* Duplicate-guard verified: F&F's two promoted memories
  (`fa35eb8f`, `73acdfc0`) suppressed cleanly in every
  rerun.
* PW returned 2/3 gravity-carrying promise-open-loop
  candidates (source-scene-sensitivity confirmed).
* Actual spend: ~$0.021.
* Caveat: seed-selection variance across F&F reruns is
  LOW — all 3 runs surface the same 3 seed ideas with
  only wording variation. Two interpretations preserved
  as non-blocking open question (§16.4).

### 2.2 Slice 282.2 — longitudinal observation protocol + T0 baseline + methodology (LOCKED, NOT STARTED)

Protocol design + baseline capture + methodology
recalibration + protocol correction are complete. The
actual longitudinal observation has NOT begun.

Locked artifacts:

* **T0 v1 baseline** (n=15) at F&F 12 Ep / 3 mem:
  * A/B/C/D/E strict-yes = 60% / 60% / 100% / 40% / 80%
  * Weak-CONTROL = 0%
  * Raw artifact:
    `docs/design/session282_experiment_data/q282_2_v1_baseline.json`
  * Actual spend: ~$0.036.

* **T0 continuity-integration classification** (§22.4,
  aggregate corrections via §24.8):
  * Structural rate (CI-2+): 12/15 = 80%
  * Multi-thread rate (`distinct_threads_used ≥ 2`):
    **4/15 = 26.7%** (corrected from initial 40%
    miscount)
  * Consequence-generation rate (CI-4): 3/15 = 20%
  * Distinct-thread diversity: 6 unique threads
  * Thread concentration: 33% on top threads (M3, E12)
  * Notable: M2 (`fa35eb8f` dialogue_callback) has ZERO
    references across all 15 T0 suggestions
    (shape-over-count evidence).
  * Notable: all 3 CI-4 candidates use MEMORIES
    (M1 twice via 2.4 + 3.4; M3+M1 combined via 1.4).

* **Locked post-T0 methodology** (§24 supersedes affected
  §22 clauses):
  * Two-tier WARNING / REGRESSION structural guardrails
    with both integer count and percentage forms
    (§24.3.1).
  * D-axis directional target: ≤ 4/15 (26.7%) toward
    PW's 20% (§24.3.2).
  * SUPPORT criterion — all four must hold:
    structural preservation + continuity growth +
    story-execution + Chris subjective judgment (§24.4).
  * NO MOVEMENT bands: ±1 count around T0 on each
    metric (§24.5).
  * REGRESSION triggers: guardrail breach OR
    CI-2+ ≤ 9/15 OR diversity shrinks OR concentration
    ≥ 9/15 OR worse story-execution OR negative
    subjective (§24.6).
  * CONFOUNDED list unchanged (§22.6.4).
  * Emerging-evidence rule preserved (§22.6.5).
  * §24 explicitly disallows further threshold tuning
    once observation begins (§24.10 item 1).

---

## §3 Resume point (extremely simple)

> **Chris + ChatGPT may explicitly authorize the first
> natural Fox & Flour gesture. Chris then uses
> Character OS normally. The research layer observes
> afterward and does not prescribe his story, memory
> choices, or behavior.**

Gesture protocol (§18.10, non-prescriptive):

1. Open Fox & Flour when Chris wants to make a bakery
   story.
2. Pick a topic any way that feels natural.
3. Create Episode + Composition.
4. Read the composition.
5. React to curator cards as an operator; promote only
   what genuinely matters.
6. Never promote for the sake of the experiment.
7. Optionally use manual "What changed?" textarea.
8. Move on when done. Timeline unforced.

After the gesture, with re-authorization, the research
layer applies §18.5 five-axis capture and evaluates
against §24 locked criteria.

---

## §4 Non-blocking open questions preserved

* **§16.4 seed-selection-variance observation.** Curator
  reruns on same composition converge on same seed
  ideas with only wording variation. Interpretation
  unresolved (composition-determinism-as-feature vs
  paraphrase-treadmill-as-limitation). Non-blocking.
* **§20.8.1 low-variance mirror in v1.** Suggestion
  3.1 = 2.1 verbatim across two n=5 v1 calls. Extends
  §16.4 finding across primitives. Non-blocking.
* SESSION 281 §U4 deferred items (Q281.3-β/γ/ο, Hκ,
  Hι, Hβ-permissive) — all remain deferred.
* SESSION 280 §7 carry-forwards (Q280.4i-3/5, U-3a,
  U-4/U-6, verifier-boundary Episode.operator_topic,
  Finding 4c, CONTENT_FORMAT_BACKLOG) — all remain
  deferred.

---

## §5 Substrate state at SESSION 282 close (re-verify at resume)

* **Fox & Flour Bakery** (`1a0af807-…`):
  * 12 Episodes
  * 3 REMEMBERED memories:
    * `abac5486` event (cooperation clause) — source
      `772e9012`
    * `fa35eb8f` dialogue_callback (mascot outreach
      joke) — source `772e9012`
    * `73acdfc0` event (mascot want) — source `772e9012`
  * All 3 memories source from ONE composition
    (`772e9012`); substrate diversity starts at zero.
  * Canonical specimens preserved: `772e9012` (strong),
    `565cd8c8` (weak).
* **Patch's Workshop** (`56d16b63-…`):
  * 32 Episodes
  * 14 REMEMBERED memories including canonical PATCH
    OVERRIDES row + Agent-arc cluster.
  * Composition `fcba3242` preserved (PATCH OVERRIDES
    origin scene; Slice 282.1 Probe B source).

Verify via `DB_PORT=5434 manage.py shell` from `shell/`.

---

## §6 What SESSION 283 MUST NOT do (preserved from S281 §T10 + S282 §26.5)

* Do NOT modify Slice 281.2 curator UI, Slice 281.1
  curator service, v1 next-Episode service, retrieval,
  synthesis, verifier, memory schema, witness semantics,
  or `promote_from_composition`.
* Do NOT modify Ruby / Tyson / Patch / Rivet
  identities, personalities, K2 docs, or business_briefs.
* Do NOT archive, edit, or supersede any of the 3 F&F
  memories or 14 PW memories.
* Do NOT modify compositions `772e9012`, `565cd8c8`,
  or `fcba3242`.
* Do NOT install new Python / npm dependencies without
  explicit approval.
* Do NOT expose implementation vocabulary in
  operator-facing surfaces.
* Do NOT collapse Hθ into "more memories = better
  stories."
* Do NOT run any provider-spend experiment without
  explicit authorization at the correct order of
  magnitude (curator ~$0.02/call; v1 ~$0.005-$0.02;
  dialogue_scene ~$0.05-$0.20/composition).
* Do NOT tune §24 methodology thresholds after Chris's
  first post-T0 gesture. §24 is FINAL locked
  methodology; no further adjustment permitted once
  observation begins.

---

## §7 Environment notes (preserved from SESSION 281 §15)

* Docker infra (Postgres + Redis) left up by
  `stop-local.sh` — do not restart during development.
* DB port is **5434** per `.env` — always
  `set -a; source .env; set +a` before `manage.py shell`
  or ad-hoc psycopg.
* Pytest MUST be invoked from `shell/`.
* Pytest auto-regenerates `CHARACTER_OS_INVENTORY.md`
  sometimes — always `git status` before committing.
* Chris drives operator-facing SPA gestures; Claude
  tails DB / logs / API in parallel.
* Real-mode dogfood after operator-facing slices — no
  curl alternative.
* Frontend baseline: `cd web && npx vitest run`.
* Two pre-existing K6.4 mock-drift test failures
  predate SESSION 281 and remain out of scope.

---

## §8 Required working method (preserved)

Every slice:

1. ORIENT / AUDIT — current substrate, real code, real DB.
2. State the falsifiable question or acceptance target.
3. For experiments: rubric + predictions LOCKED in a
   separate commit BEFORE execution.
4. Make the smallest change that answers the question.
5. Test with focused coverage.
6. Dogfood through the real operator UI.
7. Inspect actual evidence.
8. Document durably in `/docs/design/`.
9. Decision gate — explicit recommendation, wait for
   Chris + ChatGPT approval.
10. Do NOT assume implementation is automatically the
    next step when runtime evidence raises a new
    product question.

Roles:

* **Chris** operates the SPA in a real browser; approves
  scope-lock at each decision gate.
* **Claude** is repository operator / engineer;
  writes code + tests + documentation; runs backend
  probes and ORM-level verification.
* **ChatGPT** is architecture / product / research
  partner; reviews scope-locks, prediction locks, and
  decision gates.

Cost discipline (from SESSION 281 §P):
* v1 next-Episode suggestions: ~$0.005-$0.02/call
* Q280.9 / Slice 281.1 curator: ~$0.02/call
* Full `dialogue_scene` synthesis: ~$0.05-$0.10/call,
  ~$0.10-$0.20/composition (typically 2 attempts).

---

## §9 SESSION 282 total spend

* Slice 282.1: ~$0.021
* Slice 282.2 baseline: ~$0.036
* **Total: ~$0.057**

Well under authorized ceilings ($0.10 for Slice 282.1;
$0.05 for Slice 282.2 baseline).

---

## §10 Closeout summary

SESSION 282 is STOPPED for documentation closeout. The
Q282.2 longitudinal observation is fully designed,
baselined, methodologically corrected, and cleanly
interpretable but has NOT begun.

The resume point is a single Chris + ChatGPT
authorization decision. No SESSION 283 mission is
pre-decided; the sensible default is to proceed to the
first natural Chris gesture per §3 above and observe
via §18.5 capture + §24 evaluation.

Alternate SESSION 283 openings (all valid; Chris +
ChatGPT choose):

* Proceed to first natural F&F gesture (default).
* Address one of the §4 non-blocking open questions.
* Address one of the SESSION 281 / SESSION 280
  deferred items.
* Something else emerging from context Chris has.

Working method preserved. Operator-first boundary
preserved. Human-authority boundary preserved.
