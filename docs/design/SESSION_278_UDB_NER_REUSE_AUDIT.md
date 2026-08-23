# SESSION 278 — UDB → Character OS NER / Entity-Extraction Reuse Audit

**Date:** 2026-08-23
**Slice:** Q-278 architecture side-question — before Character OS designs its own spaCy/NER pipeline, does the sibling repo `unified-donkey-betz` already contain reusable substrate?
**Mode:** Audit only. No implementation. No dependency installs. No mutations to either repo beyond writing this document.

---

## 1. Precise question

> Can Character OS reuse any existing spaCy / NER / entity-extraction / semantic-classification / entity-grounding / hallucination-detection / claim-verification work from `/Users/donkeyking/Donkey_Betz/unified-donkey-betz/` inside `/Users/donkeyking/Donkey_Betz/character-os/` — rather than independently implementing a comparable capability?

The concrete need on the Character OS side is the K6.4 `proper_noun` invariant currently approximated by regex + ~250-entry stoplist (see `SESSION_278_AUDIT.md` §Q-278-1 and §Q-278-3). Any UDB substrate is judged against that invariant, not against generic NLP usefulness.

---

## 2. Repo baselines

Both repos inspected read-only. No mutations.

| Repo | Branch | HEAD | Working tree | Origin/HEAD delta |
|---|---|---|---|---|
| `unified-donkey-betz` | `main` | `9d9a10685 fix(security): tighten gitleaks allowlist…` | clean | `origin/main == HEAD` (0/0) |
| `character-os` | `main` | `b3e6903 docs(session-277): record closeout landed SHA…` | one untracked file (`docs/design/SESSION_278_AUDIT.md`) | `origin/main == HEAD` (0/0) |

Both repos are on `main`, clean of unrelated in-progress work, and this audit adds one file (this document) plus, on write, `SESSION_278_UDB_NER_REUSE_AUDIT.md` — no other mutations.

Character OS runtime: `requires-python = ">=3.11"` (root `pyproject.toml`).
UDB runtime: Django platform, pinned mostly in `requirements.txt` at repo root.

---

## 3. UDB discovery — what was searched, what was found

### 3.1 Search scope

Mechanical inspection across `unified-donkey-betz/` for NER-relevant substrate:

- dependency manifests (`requirements*.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `environment.yml`)
- `import spacy` / `from spacy` — actual imports (not string literals)
- `spacy.load`, `nlp(`, `.ents`, `PERSON`/`ORG`/`GPE`/`LOC` label handling
- adjacent frameworks: `nltk`, `stanza`, `flair`, `presidio`, `textblob`, HuggingFace token-classification pipelines, small local LMs
- Directory scan under: `ai_core`, `ai_nexus`, `ai_platform`, `ai_opportunities`, `advisors`, `agents`, `assistant`, `analysis`, `core`, `content`, `dashboard`, `backend`, `intelligence`, `ml`
- Test directories for entity/POS/proper-noun adversarial fixtures
- Docs / ADRs / session handoffs for NER decision records

### 3.2 What UDB actually contains

**Dependency pins (dormant vs active):**

- `requirements.txt` (root, main platform): `nltk==3.9.1`, `textblob==0.19.0`, `transformers==4.56.1`, `sentence-transformers==5.1.0`. No spaCy, no `en_core_web_*` reference.
- `intelligence/spider_requirements.txt:36` — pins `spacy==3.7.2` alongside `nltk==3.8.1`, `textblob==0.17.1`. **This pin is dormant — no Python code in UDB actually imports spaCy** (see 3.3 below).
- `ml/requirements.txt` — `sentence-transformers`, `textblob`, `vaderSentiment`. No NER stack.

**Actual usage (imports + call sites):**

- **`spacy` — zero real imports.** The grep for `^\s*(import|from)\s+spacy` across all `.py` files in UDB returns no matches. The single string hit at `intelligence/connect_all_agents.py:117` is a Python string literal inside an example-solution catalog: `('Natural Language Processor', 'Implement NLP for sentiment analysis and text classification', 'import spacy; nlp = spacy.load("en_core_web_sm"); doc = nlp(text); entities = doc.ents')`. It is content, not code — a template row rendered as a "solution" description. Not wired to anything.
- **`nltk` — installed, never imported.** Present in `requirements.txt` and `spider_requirements.txt`; zero actual imports found in application code.
- **`textblob` — actively used but sentiment-only.** Seven call sites (`ai_core/agents/universal_agent_loader.py`, `ai_core/intelligence/{bluesky_learning_bridge,data_transformation_pipeline,learning_loop}.py`, `ai_core/spiders/{advisor_feed,specialized/etherscan_spider,specialized/convertkit_spider}.py`). Every discovered call uses `TextBlob(text).sentiment.polarity` — a scalar sentiment score. No use of TextBlob's `.words`, `.noun_phrases`, `.pos_tags`, or `.sentences` attributes. Not exercising any POS/entity capability.
- **HuggingFace client — sentiment/feature only.** `ml/integrations/huggingface_client.py` wires FinBERT (`ProsusAI/finbert`), Twitter RoBERTa sentiment, SEC-BERT feature extraction, DialoGPT generation. Zero NER models (no `dslim/bert-base-NER`, no token-classification pipeline).
- **`intelligence/hallucination_publisher.py` — Redis event broadcaster, not a detector.** Publishes `hallucination_events` to Redis channel and maintains a 100-event ring for real-time display. Accepts pre-computed `patterns: List[str]` and `risk_score: float`. The upstream detector is pattern/mythology-based (see `intelligence/mythology_enhanced_learning.py` in same directory), not entity-based. Not a NER substrate; not a claim-verification substrate.

**Stoplist / capitalization logic:**

- One hand-curated 8-word stopword set inside a keyword-extraction helper in `core/models_unified_system.py`. Not proper-noun aware; not related to Character OS's ~250-entry false-positive list.

**Test coverage relevant to entity extraction:**

- None found. UDB has no test files exercising POS tagging, entity classification, proper-noun detection, or capitalization-aware token filtering.

**Docs / ADRs mentioning NER:**

- One historical mention: `external-project-docs/ai-content-studio/documentation/context_chunk_010.md:3154` — `python -m spacy download en_core_web_sm`. Third-party project doc snapshot, not a UDB decision record. No UDB ADR or session handoff selecting or rejecting spaCy.

### 3.3 Aggregate finding for UDB

UDB contains **NO** wired production NER, NO wired POS tagging, NO wired entity linking, NO wired proper-noun classification, NO adversarial test fixtures for entity classification. The only surface-level signals — a dormant `spacy==3.7.2` pin in a spider-army requirements file, a dormant `nltk==3.9.1` pin at platform root, and one string-literal spaCy snippet inside a solution catalog — are dead. The active NLP capability is scalar sentiment via TextBlob and HuggingFace sentiment/generation pipelines. None of that grounds named entities.

---

## 4. Reusable-substrate ledger (per audit spec §3)

Per the spec's five-way classification (A: directly reusable code / B: reusable algorithm / C: reusable tests / D: reusable dep config / E: UDB-specific do-not-transplant), the ledger is empty on rows A, B, C. Row D contains one weak signal only.

| Class | Component | Verdict |
|---|---|---|
| **A. Directly reusable code** | *(none)* | UDB has no NER code to import. |
| **B. Reusable algorithm / pattern** | *(none)* | Nothing in UDB implements a proper-noun / entity-grounding algorithm. Sentiment scoring does not generalize to entity classification. |
| **C. Reusable tests / adversarial fixtures** | *(none)* | Zero tests for entity, POS, or proper-noun classification. Character OS's own `test_claim_verifier.py` remains the only adversarial corpus in the two-repo set. |
| **D. Reusable dependency / model configuration** | `intelligence/spider_requirements.txt` — `spacy==3.7.2`, `nltk==3.8.1`, `textblob==0.17.1` pins | Weak signal only. Confirms a prior spider-team pin choice, but nothing was built on it. Not a reason to select spaCy 3.7.2 specifically. |
| **E. UDB-specific — do NOT transplant** | `bluesky_learning_bridge.py`, `advisor_feed.py` sentiment; `huggingface_client.py` model wiring; `hallucination_publisher.py` Redis pipeline | These are wired to UDB's spider network, advisor feed, agent-learning loop, and Redis DB=2. Semantics are UDB-specific — transplanting risks importing sports-signal / opportunity-scoring assumptions Character OS does not want. |

---

## 5. Character OS Q-278 need — fit against UDB substrate

Character OS Q-278 asks: given a synthesized token/span, is it a **source-dependent named entity** that should be grounded against the speaking character's factual corpus, rather than ordinary sentence language?

Current Character OS substrate (from `shell/character_os/claim_verifier.py`, cross-referenced with `SESSION_278_AUDIT.md`):

- deterministic numeric detection (`_NUMERIC_RE`)
- tech / domain-term detection (`_build_tech_terms_re()` over `KNOWN_TECH_TERMS`)
- capitalization-based proper-noun proxy (`_SINGLE_CAP_RE = \b[A-Z][a-zA-Z]{3,}\b`)
- ~250-entry hand-curated false-positive stoplist `_COMMON_PROPER_NOUN_FALSE_POSITIVES`
- factual-corpus substring grounding + allowed-vocabulary check
- multi-word branch with `is_sentence_initial` demotion; single-cap branch does NOT gate on position

Checking each UDB "capability" against this need:

| Question | UDB answer |
|---|---|
| Does it actually identify named entities? | No — nothing in UDB attempts entity identification. |
| Which entity classes (PERSON/ORG/GPE/LOC/DATE/...)? | None. |
| Does it handle short acronyms (FBI/CIA/FDA)? | N/A — no NER present. Character OS's current `{3,}` regex already excludes 3-char tokens; this remains an unaddressed gap on the Character OS side, and UDB offers nothing. |
| Does it handle lowercase technical entities? | Only via TextBlob sentiment (irrelevant). Character OS's own `KNOWN_TECH_TERMS` case-insensitive matcher is the only lowercase-entity capability in either repo. |
| Does it provide POS/entity context for polysemy (`Rose/rose`, `Mark/mark`, `Bill/bill`, `May/may`, `Fair/fair`)? | No. This is the exact class Q-278-1 identified as misfiring in Character OS; UDB offers no help. |
| Deterministic / offline behavior? | UDB's sentiment path uses local HuggingFace models (deterministic-ish) plus optional API calls. Not applicable to entity classification. |
| Requires provider calls? | UDB HuggingFace client mixes local + API models. Not directly relevant. |
| Latency / memory / load cost? | N/A — no NER model loaded anywhere in UDB to measure. |
| Can init once-per-worker rather than per-request? | N/A. |

There is no dimension on which a UDB component partially satisfies Character OS's need.

---

## 6. Transplant classification (per audit spec §5)

Options:

1. DIRECT REUSE
2. EXTRACT SHARED CORE
3. REIMPLEMENT FROM PROVEN UDB PATTERN
4. NO USEFUL REUSE

**Verdict: 4 — NO USEFUL REUSE.**

Rationale:

- Option 1 fails because there is no NER code to import.
- Option 2 fails because there is no NER-shaped generic core buried inside UDB domain code; the sentiment paths are not entity-shaped.
- Option 3 fails because UDB proves no pattern relevant to entity grounding — a dormant `spacy==3.7.2` pin unaccompanied by call sites, tests, or ops runbook is not a "proven pattern," it is a discarded intent.
- Therefore Option 4.

**Smallest plausible transplant shape:** none. There is no shape small enough to be worth the coupling risk when the target substrate does not exist.

---

## 7. Duplication-risk analysis (per audit spec §6)

> If Character OS independently implements spaCy/NER now, what existing UDB work would we duplicate?

**None.** Character OS would not be re-solving anything UDB solved. UDB never wired an entity-classification pipeline. The dormant `spider_requirements.txt` pin represents an *unrealized* intent, not delivered work.

> What would be dangerous to copy because the semantics differ?

Two specific traps to avoid, should someone later be tempted to "reuse" surface-level UDB NLP substrate:

1. **`intelligence/hallucination_publisher.py`.** The name matches Character OS's problem domain and it is tempting to import wholesale. It is *not* a detector — it is a Redis broadcaster tied to UDB's mythology-pattern detection semantics (`patterns: List[str]`, `risk_score: float`, `severity`, Redis DB=2 channel `hallucination_events`). Character OS's K6.4 warnings have a different semantic shape (`{kind, claim, position, line_index, speaker_name, speaker_alias}`) and a different persistence model (`Composition.verification_warnings` JSON column). Copying the publisher would introduce a Redis-broadcast dependency the K6.4 pipeline does not need and does not currently have.
2. **TextBlob's `.sentiment.polarity` pattern.** UDB uses TextBlob only for scalar sentiment. If someone reads "we already have TextBlob wired" and reaches for TextBlob's `.noun_phrases` or `.tags` (POS) instead of spaCy, they will inherit TextBlob's well-known accuracy ceiling on modern English (backed by an aging averaged-perceptron tagger). Not the same tool as spaCy `en_core_web_sm` even though both are labeled "NLP libraries."

Explicit non-reuse recommendation on these two, ratified by this audit.

---

## 8. Test / proof reuse (per audit spec §7)

UDB provides no reusable adversarial fixtures for:

- ordinary sentence starters
- supported / unsupported proper nouns
- acronyms (FBI/CIA/FDA)
- organizations
- people
- locations
- lowercase technical entities
- polysemy (`Rose/rose`, `Fair/fair`, ...)
- punctuation boundaries
- deterministic offline classification

Character OS's own `shell/apps/compositions/tests/test_claim_verifier.py` remains the sole in-repo corpus, and per `SESSION_278_AUDIT.md` §Q-278-1 those tests are case-by-case (they lock the known false positives found in prior dogfood, not the general class). If Character OS eventually builds a shadow-mode NER pipeline (Q-278-3 Option D-Hybrid), the adversarial-fixture design starts from scratch — no reusable UDB seed exists.

---

## 9. Risks

- **Risk of false-negative audit.** A grep for `import spacy` cannot find spaCy wrapped in a factory, monkey-patched via `sys.modules`, or dynamically imported from a plugin registry. Mitigation: the audit also grepped for `spacy.load`, `nlp(`, `.ents`, and UDB's dependency manifests — all negative. Confidence in "UDB has no wired spaCy" is high, but not infinite.
- **Risk of over-confidence in negative.** UDB's `intelligence/` directory alone contains ~50 top-level Python modules and a subdirectory tree. If a dormant spaCy prototype lives inside `intelligence/reallearning/` or `intelligence/services/` behind an unusual import shape, the grep pattern above would still catch it — nothing was found — but a targeted audit of any *specific* claim of prior UDB NER work would be worth running before that claim is accepted.
- **Risk of unnecessary spaCy adoption.** This audit answers "can we reuse UDB substrate," not "should Character OS adopt spaCy." Q-278-3 already frames Option D-Hybrid as one of several architectures; the decision-gate on spaCy adoption remains open and lives in `SESSION_278_AUDIT.md`, not here.

---

## 10. Recommendation

1. **Do not attempt cross-repo reuse for NER.** UDB has no substrate to reuse. Any "reuse" would be either theatre (importing the dormant pin) or dangerous (copying `hallucination_publisher.py` which has different semantics).
2. **Do not pause Character OS independent NER design waiting on this reuse question.** The audit resolves the question in the negative; nothing is waiting for a UDB extraction.
3. **Preserve the two non-reuse notes from §7** in Character OS's design memory (Q-278-3 / Q-278-4 folder) so that a future reader who sees UDB's spaCy pin or `hallucination_publisher` does not re-open this question on false-signal grounds.
4. **If Character OS chooses spaCy** (via Q-278-3 Option D-Hybrid or a successor), pin and load it as a fresh integration inside `shell/pyproject.toml`. Do not couple to UDB's dormant `spider_requirements.txt` version choice (`3.7.2`) — that pin has no test coverage or production validation backing it. Select the version and model against Character OS's own load/latency/memory budget.

---

## 11. Explicit decision gate

Question: **Does UDB contain reusable spaCy / NER / entity-extraction substrate that Character OS should transplant before designing its own?**

**Decision: NO.** Character OS's Q-278 NER decision proceeds independently, using this document as the durable record that UDB was checked and found empty on this dimension.

Chris + ChatGPT sign-off is not required for this decision — it is a *negative* audit resolving a side-question, not an implementation change. If a future session claims "we can reuse the UDB NLP stack," point them at §3.3, §6, and §7 of this doc.

---

## 12. Cross-reference

- Parent audit (Q-278 root): `docs/design/SESSION_278_AUDIT.md`
- Q-278 handoff: `docs/design/SESSION_278_HANDOFF.md`
- Character OS current substrate: `shell/character_os/claim_verifier.py:334` (`_SINGLE_CAP_RE`), `claim_verifier.py:115-310` (`_COMMON_PROPER_NOUN_FALSE_POSITIVES`), `claim_verifier.py:818-857` (`is_sentence_initial`)
- Character OS tests: `shell/apps/compositions/tests/test_claim_verifier.py`
- UDB dormant pin (evidence): `unified-donkey-betz/intelligence/spider_requirements.txt:36`
- UDB dead string-literal reference: `unified-donkey-betz/intelligence/connect_all_agents.py:117`
- UDB non-reuse trap #1 (name-collision): `unified-donkey-betz/intelligence/hallucination_publisher.py`
