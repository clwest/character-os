# SESSION 271 — Corrective-Pass Audience-Invariance Audit (Q-270-15)

Audit-only investigation of the SESSION 270 §13.28 directional finding: in 2 of 3 minimal-directive audience-conditioned specimens the FIRST PASS was clean on at-risk technical terminology (`API`, `language model`, `state`) and the CORRECTIVE EXPANSION pass reintroduced it. This document determines mechanically what happens between the two synthesis passes, whether audience_hint reaches both, whether the corrective retry is an edit or a regeneration, and what current tests do / do not prove.

**No code was changed.** No render was performed. All findings are drawn from source inspection + frozen evidence sidecars.

---

## §1. Repository / runtime orientation

| Check | Value at audit start |
|---|---|
| HEAD | `34d825fa558fd5fab062ff733269e37766f1fae8` (SESSION 270 §14.6 CLOSEOUT SHA record) |
| Local `main == origin/main` | ✅ both at `34d825f` |
| Working tree | ✅ clean |
| `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` env var | ❌ not set (audit runs against frozen evidence; no live audience-hint activation) |
| `_resolve_solo_audience_hint(step={})` behaviour | Returns `None` per SESSION 270 §14.4 (frozen expectation; not re-run) |
| `WRITING_CONTRACT_VERSION` | `5` (canonical definition: `shell/character_os/writing_contract.py:96`) |
| Transient solo audience_hint plumbing | ✅ present + inactive (`shell/apps/compositions/primitives/avatar_speech.py:97-114` + kwargs on `build_render_brief` / `synthesize_with_duration_gate` / `_assemble_task_message`) |
| Frozen evidence — baseline sidecar | ✅ `docs/design/session_269_experiment_data/06_composition_2ef5ee7e_evidence.json` |
| Frozen evidence — SESSION 270 sidecars | ✅ four files in `docs/design/session_270_experiment_data/` (`01_composition_f0e0a7bf`, `02_composition_9880eb93`, `03_composition_0b3c1fc1`, `04_composition_c3ff972d`) |
| Runtime services | Not restarted during this audit. Frozen-evidence audit. No live render fired. |
| Postgres | Not consulted (audit was frozen-evidence-only; port 5433 auth failed on ad-hoc probe — irrelevant to conclusions since all needed data lives in sidecars + source) |

---

## §2. Production synthesis path (proven from source)

Full call chain for a solo_scene (Episode-attached `talking_head`) render, with actual file paths and line numbers.

```
apps/compositions/primitives/avatar_speech.py
├── _resolve_solo_audience_hint(step)                       # lines 97-114
│   └── returns hint string OR None (params → settings → env precedence)
└── generate_avatar_speech() / _maybe_synthesize_script()
    ├── is_episode_talking_head = (episode_id is not None
    │                              and template_kind == "talking_head")   # lines 517-520
    ├── target_shape_for_synthesis = "solo_scene" if is_episode_talking_head else "long_form"  # lines 521-523
    ├── audience_hint = _resolve_solo_audience_hint(step) if is_episode_talking_head else None  # lines 531-533
    └── if target_duration_seconds:
        └── synthesize_with_duration_gate(                  # lines 554-564
                spokesperson=composition.spokesperson,
                operator_prompt=raw_script,
                target_duration_seconds=target_duration_seconds,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
                verifier_mode=verifier_mode,
                opener=opener,
                mock_mode=False,
                memory_rows=memory_rows,
                target_shape=target_shape_for_synthesis,     # "solo_scene"
                audience_hint=audience_hint,                 # string OR None
            )

character_os/duration_contract.py :: synthesize_with_duration_gate  (lines 422-719)
├── compute LLM-facing char budgets from calibrated synth target       # lines 501-508
├── acceptance budgets from raw requested-target                       # lines 514-519
├── def _synthesize(hint=None):                                        # lines 521-543
│      return build_render_brief(
│          spokesperson, operator_prompt,
│          verifier_mode=verifier_mode,
│          opener=opener,
│          target_shape=target_shape,          # e.g. "solo_scene"
│          target_duration_seconds=synth_target_seconds,
│          max_script_chars=max_script_chars,
│          corrective_hint=hint,                # None on first call, expansion/compression hint on retry
│          memory_rows=memory_rows,
│          audience_hint=audience_hint,         # CAPTURED FROM ENCLOSING SCOPE
│      )
├── synth = _synthesize()                       # FIRST PASS       line 545
├── first_pass_brief = synth.brief              # frozen for observability   line 550
├── measure chars/words/seconds                 # line 546
├── if actual_chars < raw_min:
│      hint = _expansion_hint(...)              # lines 591-599
│      synth = _synthesize(hint)                # CORRECTIVE PASS  line 603
├── elif actual_chars > acceptance_max or provider_cap_binds:
│      hint = _compression_hint(...)            # lines 607-615
│      synth = _synthesize(hint)                # CORRECTIVE PASS  line 619
├── acceptance gate (raises DurationContractError on failure)
└── return synth                                 # accepted script

character_os/script_synthesis.py :: build_render_brief   (lines 288-479)
├── validates target_shape ∈ {"standalone","long_form","solo_scene"}
├── retrieve_for_teammate(...)                  # deterministic under identical query
├── _call_responses_api(spokesperson, operator_prompt, chunks, opener=…,
│                       target_shape=…, target_duration_seconds=…,
│                       max_script_chars=…, corrective_hint=…,
│                       memory_rows=…, audience_hint=…)     # lines 458-467

character_os/script_synthesis.py :: _call_responses_api   (lines 533-591)
├── system = _assemble_system_prompt(spokesperson, chunks=chunks, target_shape=…,
│                                    target_duration_seconds=…, max_script_chars=…,
│                                    memory_rows=…)          # lines 563-570
│   (audience_hint DOES NOT flow into the system prompt)
├── user = _assemble_task_message(operator_prompt=…, opener=…,
│                                 corrective_hint=…,
│                                 audience_hint=…)            # lines 571-576
├── client.responses.create(model=SCRIPT_MODEL,
│                           input=f"{system}\n\nUser: {user}", …)
└── return (text, tokens_in, tokens_out)

character_os/script_synthesis.py :: _assemble_task_message   (lines 638-698)
├── parts = ["=== SECTION 5 — TASK ===", "TOPIC:\n{topic}"]
├── hard_constraints = []
├── if opener:           hard_constraints.append("PINNED OPENER …\n{opener}")
├── if corrective_hint:  hard_constraints.append("CORRECTIVE HINT (previous attempt feedback — apply this):\n{corrective_hint}")
├── if audience_hint:    hard_constraints.append("AUDIENCE DIRECTIVE (research plumbing — apply as a performance instruction; adapt HOW the character communicates without altering identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, or Episode intent):\n{audience_hint}")
├── if hard_constraints:
│      parts.append("HARD CONSTRAINTS (override Character Voice and Writing Contract preferences; do NOT override Factual Basis or Brand Voice prohibitions):\n\n" + "\n\n".join(hard_constraints))
└── parts.append("Write the spokesperson's spoken script for this task. Plain spoken English — this becomes voiceover.")
```

**System prompt structure** (`_assemble_system_prompt`, lines 594-635): §1 Factual Basis → §2 Character Voice → §3 Brand Voice → §4 Writing Contract → PRECEDENCE RULES. `audience_hint` NEVER enters the system prompt.

**PRECEDENCE RULES text** (`_PRECEDENCE_RULES`, lines 886-904):
> 1. Factual Basis (§1) beats everything on TRUTH. No claim survives that isn't grounded in §1.
> 2. Brand Voice (§3) beats Character Voice (§2) on PROHIBITIONS. `never_say` overrides any character preference.
> 3. Writing Contract (§4) beats Character Voice on STRUCTURE. One-CTA-when-included applies even to characters who prefer multiple asks.
> 4. Character Voice (§2) beats Writing Contract on REGISTER. The contract's anti-generic list is a floor; character voice adds distinctive register on top.
> 5. Task (§5) Hard Constraints beat Character Voice preferences and Writing Contract defaults, but NEVER override Factual Basis or Brand Voice prohibitions.
> 6. Task Topic beats Character Voice on TOPIC SCOPE. POV shapes interpretation of the topic, not choice of topic.

Both `corrective_hint` and `audience_hint` live inside §5 HARD CONSTRAINTS — same precedence tier per Rule 5. §1 Factual Basis outranks both on TRUTH per Rule 1.

---

## §3. Question A — Does audience_hint reach BOTH first pass AND corrective pass byte-identically?

**Answer: YES — proven from source.**

### §3.1 Closure capture proof

`shell/character_os/duration_contract.py:521-543`:

```python
def _synthesize(hint: str | None = None) -> ScriptResult:
    return build_render_brief(
        spokesperson, operator_prompt,
        verifier_mode=verifier_mode,
        opener=opener,
        target_shape=target_shape,
        target_duration_seconds=synth_target_seconds,
        max_script_chars=max_script_chars,
        corrective_hint=hint,            # None on first call, string on retry
        memory_rows=memory_rows,
        audience_hint=audience_hint,     # CAPTURED FROM ENCLOSING synthesize_with_duration_gate SCOPE
    )
```

`audience_hint` is captured from the enclosing function's parameter (line 433) and referenced by name inside the closure. Python closure semantics: the same name-lookup fires on every call, resolving to the same string object (or `None`). The value is not mutated anywhere between the two invocations.

### §3.2 Call-site proof

- **FIRST PASS** — `line 545`: `synth = _synthesize()` → `hint` defaults to `None` → `build_render_brief(..., corrective_hint=None, audience_hint=audience_hint)`.
- **CORRECTIVE PASS (expansion)** — `line 603`: `synth = _synthesize(hint)` → `hint` is the `_expansion_hint(...)` string → `build_render_brief(..., corrective_hint="Your previous draft was …", audience_hint=audience_hint)`.
- **CORRECTIVE PASS (compression)** — `line 619`: same pattern, `_compression_hint(...)`.

The `audience_hint` argument to `build_render_brief` is byte-identical across both invocations because the enclosing function's parameter is not reassigned.

### §3.3 Downstream propagation

`build_render_brief` (line 466) forwards `audience_hint=audience_hint` to `_call_responses_api`. `_call_responses_api` (line 575) forwards to `_assemble_task_message(audience_hint=audience_hint)`. `_assemble_task_message` (lines 677-685) emits the AUDIENCE DIRECTIVE block whenever the string is truthy.

**Verdict — Question A:** `audience_hint` reaches BOTH first-pass and corrective-pass `build_render_brief` invocations byte-identically. There is no divergence in the delivery mechanism. **H1 (audience_hint accidentally absent from corrective retry) is FALSIFIED by source inspection.**

---

## §4. Question B — Prompt-component delta between first pass and corrective pass

| Prompt component | FIRST PASS | CORRECTIVE PASS | SAME / CHANGED | Notes |
|---|---|---|---|---|
| System §1 Factual Basis (knowledge chunks + memory) | Present | Present | **SAME** | Retrieval is deterministic under identical query (SESSION 270 §13.25.1 finding: 5 chunks + `mem_id=8d4fdfec` identical across all 5 specimens); the chunk set does not change between passes within a single render either — the second call retrieves again, but retrieval inputs are byte-identical, so retrieved chunks are the same. |
| System §2 Character Voice | Present | Present | **SAME** | Static per spokesperson. |
| System §3 Brand Voice | Present | Present | **SAME** | Static per spokesperson. |
| System §4 Writing Contract (`solo_scene`, v5) | Present | Present | **SAME** | Contract text depends only on `target_shape` + budget interpolation; both derived from `synth_target_seconds` which is stable across passes. |
| PRECEDENCE RULES block | Present | Present | **SAME** | Static string. |
| User §5 header `=== SECTION 5 — TASK ===` | Present | Present | **SAME** |  |
| User §5 TOPIC (operator_prompt) | Present | Present | **SAME** | `operator_prompt` closure variable is not reassigned. |
| User §5 HARD CONSTRAINTS → PINNED OPENER | Absent (opener blank in all 5 specimens) | Absent | **SAME** | No specimen used an opener. |
| User §5 HARD CONSTRAINTS → CORRECTIVE HINT | **Absent** | **PRESENT** (656-char expansion hint) | **CHANGED** | Only added block on retry. Full text quoted in §5.2. |
| User §5 HARD CONSTRAINTS → AUDIENCE DIRECTIVE | Present (when hint truthy) | Present (when hint truthy) | **SAME** | Byte-identical string on both calls per §3. Text = `AUDIENCE: …` (41–372 chars depending on specimen). |
| User §5 HARD CONSTRAINTS block header + wrapper text | Present on both (since `hard_constraints` non-empty on both when audience_hint present) | Present | **SAME** | The "HARD CONSTRAINTS (override Character Voice…)" preface fires whenever the list is non-empty. |
| Final "Write the spokesperson's spoken script…" line | Present | Present | **SAME** |  |
| Ordering within HARD CONSTRAINTS | (audience only, if present) | opener → CORRECTIVE HINT → AUDIENCE DIRECTIVE | **CHANGED** | On the retry, the CORRECTIVE HINT is inserted BEFORE the AUDIENCE DIRECTIVE in the list (see `_assemble_task_message` lines 666-685). Audience directive retains the trailing (recency) position. |
| Previous first-pass draft text | N/A | **NOT INCLUDED** | — | The corrective call does not receive the first-pass script text as a prompt fragment. Only a metadata summary ("Your previous draft was N characters") is in the CORRECTIVE HINT. See §6. |

**Delta summary:** The only thing that changes between first pass and corrective pass is the insertion of a single 656-char CORRECTIVE HINT block into §5 HARD CONSTRAINTS, positioned BEFORE the AUDIENCE DIRECTIVE within that block. All other prompt components — including the audience directive — are byte-stable.

---

## §5. Question C — corrective_hint source, placement, priority

### §5.1 Source location

`shell/character_os/duration_contract.py::_expansion_hint` (lines 355-384). Compression path is `_compression_hint` (lines 387-416) but all four SESSION 270 audience-conditioned first passes were too SHORT (631 / 711 / 779 / 881 chars vs 972 raw_min for the 81 s synth target of a 90 s request) so ALL retries were expansion retries. Baseline `2ef5ee7e` also took an expansion retry (first-pass 731 chars).

### §5.2 Exact corrective_hint wording (from frozen evidence, all 5 specimens)

Byte-identical shape across all 5 specimens; only the `{actual_chars}` / `{actual_words}` / `{actual_seconds}` / `{shortfall_chars}` numbers differ.

Full text for `c3ff972d` (verbatim from `04_composition_c3ff972d_evidence.json::synthesis_provenance.corrective_hint_used`):

```
Your previous draft was 631 characters (128 words, estimated ~44s of speech). Target is 81s.
REWRITE THE SAME NARRATIVE ABOVE 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 341 more characters to meet the minimum.
Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.
```

Confirmed across sidecars: same shape for `f0e0a7bf` (779→972), `9880eb93` (881→972), `0b3c1fc1` (711→972), `c3ff972d` (631→972).

### §5.3 What corrective_hint DOES explicitly preserve

Verbatim from `_expansion_hint`:

- "the central arc (opening → development → payoff → single closing invitation)"
- "the narrator perspective"
- "the factual grounding from the knowledge chunks"

### §5.4 What corrective_hint does NOT mention

- audience adaptation
- vocabulary translation
- knowledge boundary of the listener
- register / accessibility
- listener context
- any transformation applied by the first pass
- the audience_hint itself
- any explicit invariant like "preserve every transformation the previous draft made"

### §5.5 Placement + priority in the assembled prompt

- Both `corrective_hint` and `audience_hint` are appended to the same `hard_constraints` list inside `_assemble_task_message`.
- Order within the list is: `opener` → `corrective_hint` → `audience_hint` (source order in the `if …: append(...)` block, lines 666-685).
- Both are wrapped in the single "HARD CONSTRAINTS (override Character Voice and Writing Contract preferences; do NOT override Factual Basis or Brand Voice prohibitions)" preface.
- Per PRECEDENCE RULES rule 5, both sit at the same precedence tier.
- Per PRECEDENCE RULES rule 1, both are outranked by §1 Factual Basis on TRUTH. Since the corrective_hint explicitly instructs the model to "Expand secondary detail from the knowledge chunks", it directs attention toward §1 — the tier that outranks the audience directive on TRUTH.

### §5.6 Instruction that plausibly competes with audience adaptation

The corrective_hint contains one instruction that structurally competes with audience-vocabulary adaptation:

> "Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied."

Combined with:

> "Preserve … the factual grounding from the knowledge chunks."

These two clauses push the model back toward the raw §1 vocabulary. §1 for these five specimens contains chunks labelled `AI AGENTS`, `LANGUAGE MODELS`, `MULTI-AGENT SYSTEMS`, with token surfaces like *"call APIs"*, *"language model"*, *"select tools"* (see §7 for chunk head snippets). The audience_hint remains in the prompt but is quantitatively dominated: for `c3ff972d` the audience directive is 79 chars, the corrective hint is 656 chars.

---

## §6. Question D — Edit or regeneration?

**Answer: The corrective retry is architecturally a REGENERATION, not an EDIT of the first-pass draft.**

### §6.1 Proof from source

`_synthesize` on the retry (`duration_contract.py:603`) calls `build_render_brief` with all the SAME inputs as the first call, plus a `corrective_hint` string. The first-pass draft text (`first_pass_brief`, line 550) is captured for observability but is **never passed to `build_render_brief` or to the LLM**. Grep for `first_pass_brief` in the module returns only:
- line 550: assignment from `synth.brief`
- lines 571, 650, 714: attached to the returned `ScriptResult` as observability metadata
- line 654: passed to `_observability_kwargs` for `DurationContractError` bundling

There is no code path that includes the first-pass text in the prompt to the corrective call.

### §6.2 What the LLM sees on the corrective call

- Same system prompt (§§1-4 + PRECEDENCE).
- Same TOPIC (operator_prompt).
- Same AUDIENCE DIRECTIVE (if any).
- + NEW: a 656-char CORRECTIVE HINT that says "Your previous draft was N chars, estimated ~M seconds. Target is X seconds. REWRITE THE SAME NARRATIVE ABOVE Y CHARACTERS. Preserve the central arc, narrator perspective, factual grounding. Expand secondary detail from the knowledge chunks. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts."

The phrase "REWRITE THE SAME NARRATIVE" is a linguistic promise that presupposes the model has the previous narrative in context. In this pipeline it does not. The model is being asked to *reconstitute* a plausible previous narrative from the same substrate (Factual Basis, Character Voice, Topic, Audience Directive) and then extend it.

### §6.3 Implication for "preserving audience transformation"

The corrective pass can only preserve things visible in its own context. It CAN preserve:

- Anything driven by the system prompt (character identity, brand prohibitions, contract shape)
- Anything driven by the TOPIC (operator_prompt)
- Anything driven by the AUDIENCE DIRECTIVE (the string is present)

It CANNOT preserve:

- Specific vocabulary choices from the first pass (never sees the text)
- Specific metaphor substitutions from the first pass
- Specific paraphrase/translation decisions made during the first pass
- Any transformation whose only trace was inside the first-pass output

The audience_hint is a *description of the listener* (e.g. `AUDIENCE: general adults with no technical background who are new to AI agents.`). Under minimal-directive conditions it does not include HOW-to-adapt clauses. The first pass had to *invent* term-by-term translations from the listener description. Those inventions are stochastic and not persisted. On a fresh regeneration under the same listener description, the model may make the same choices, similar choices, or different choices. **Nothing in the pipeline constrains the corrective pass to reproduce the specific translations the first pass discovered.**

### §6.4 Consequence for interpreting the §13.28 pattern

The §13.28 directional pattern (2 of 3 minimal-directive audience specimens exhibit at-risk term reintroduction between first pass and corrective pass) is *architecturally consistent* with a fresh regeneration that combines (a) an unchanged audience directive with (b) a longer, more mass-heavy corrective instruction that explicitly directs the model back toward the raw Factual Basis. It does not require any bug in propagation; it is a natural consequence of the regeneration semantics.

---

## §7. Cross-specimen first→corrective evidence table

All rows derived from frozen sidecars (`session_270_experiment_data/*.json` and `session_269_experiment_data/06_composition_2ef5ee7e_evidence.json`). At-risk term counts adopt the SESSION 270 §13.28 method: case-insensitive substring match for `API`, `APIs`, `language model`, `state` (SESSION 271 focus set — matches the operator's specified list); baseline row extended with `multi-step` and `database` for continuity with §13.28.

| Specimen | audience_hint (chars — text) | Attempts | First-pass len | Accepted len | Corrective reason | Corrective hint (target min) | First-pass at-risk terms | Accepted at-risk terms | Direction |
|---|---|---|---|---|---|---|---|---|---|
| `2ef5ee7e` (baseline) | N/A — no directive | 2 | 731 | 1599 | too_short | 972 | 3 (`API`, `APIs`, `state`) | 6 (`API`, `APIs`, `language model`, `state`, `multi-step`, `database`) | **ADDED** — expected without audience filter |
| `f0e0a7bf` (verbose 372-char CHANGE/PRESERVE contract) | 372 — `"AUDIENCE: children around 8-10 years old. Adapt register, vocabulary accessibility, explanation style, analogy choice, and assumed background knowledge for this audience. Preserve character identity, intelligence, personality, humor, factual grounding, Universe canon, NarrativeMemory semantics, and Episode intent. Communicate WITH the audience, do not talk DOWN to them."` | 2 | 779 | 1231 | too_short | 972 | 1 (`language model`) | 0 | **REMOVED** — verbose CHANGE clause carried through the retry |
| `9880eb93` (41-char minimal child) | 41 — `"AUDIENCE: children around 8-10 years old."` | 2 | 881 | 1354 | too_short | 972 | 0 (clean) | 1 (`API` — as `"call an API"`) | **ADDED** — clean first pass, term reintroduced on corrective |
| `0b3c1fc1` (42-char broad adult beginner) | 42 — `"AUDIENCE: adults who are new to AI agents."` | 2 | 711 | 1479 | too_short | 972 | 2 (`API` — `"call an API"`; `language model`) | 2 (same tokens; `API` becomes `"Call an API."`; `state` translated to `"Keep track of what happened"`) | **STABLE** — same terms in both passes; neither supports nor refutes the mechanical hypothesis |
| `c3ff972d` (79-char nontechnical adult beginner) | 79 — `"AUDIENCE: general adults with no technical background who are new to AI agents."` | 2 | 631 | 1424 | too_short | 972 | 0 (clean; translated: `"keep track of what happened"`, `"handle a task across multiple steps"`) | 5+ (`call APIs`, `language model` ×2, `keep some state`, dense `"language model, memory, search, tools, databases, rules, user information, and ordinary software"` list) | **ADDED** — most extreme reintroduction of the five specimens |

### §7.1 First-pass excerpts on at-risk terms (verbatim, for interpretation)

- **`f0e0a7bf` first pass:** *"A language model can answer a question. An agent can keep going: make a decision, choose a tool, read a document, search for information, maybe do several steps in a row."*
- **`9880eb93` first pass:** *"An agent might choose a tool, search for information, read a document, write something down, or handle a task with several steps."* (no API, no `state`, no `language model`)
- **`0b3c1fc1` first pass:** *"A language model gives you an answer. An agent can take steps. It might choose a tool, search for information, read a document, write something down, call an API, and keep going until it finishes a task."*
- **`c3ff972d` first pass:** *"It might choose tools, search for information, read documents, write things down, make decisions, keep track of what happened, and handle a task across multiple steps."* (no API, no `state` noun, no `language model`)

### §7.2 Corrective-pass (accepted) excerpts on at-risk terms

- **`f0e0a7bf` accepted:** *"It can make decisions, choose tools, look up information, read documents, write things down, **call other software**, and keep track of what happened before."* — API translated ✅; `language model` removed ✅
- **`9880eb93` accepted:** *"It might choose a tool, search for information, read a document, write something down, **call an API**, remember part of a task, then decide what to do next."* — API reintroduced ❌; `state` translated to *"remember part of a task"*
- **`0b3c1fc1` accepted:** *"A **language model** can tell you how it would organize a project. An agent might actually interact with the project… It might make decisions. Pick a tool. Search for information. Read documents. Write information somewhere. **Call an API**. Keep track of what happened. Do a task with more than one step."* — same terms as first pass
- **`c3ff972d` accepted:** *"A **language model** can answer a question… An agent is more like an AI system that can keep going… It can make decisions, choose tools, search for information, read documents, write things down, **call APIs**, handle a task in steps, and **keep some state** while it does it. … You might have a **language model**, memory, search, tools, databases, rules, user information, and ordinary software all bolted together like a suspiciously ambitious shed."* — API added; `language model` added ×2; `state` regressed from *"keep track of what happened"* (first pass) to *"keep some state"* (accepted)

### §7.3 At-risk terminology classification (per operator's rubric)

Distinguishing raw unexplained term vs term-with-accessible-definition vs accessible translation vs contextually understandable term:

| Occurrence | Classification |
|---|---|
| baseline `"call APIs, handle multi-step tasks, maintain state"` | **RAW UNEXPLAINED TERMS** |
| `f0e0a7bf` accepted `"call other software"` | **ACCESSIBLE TRANSLATION** |
| `f0e0a7bf` accepted `"keep track of what happened before"` | **ACCESSIBLE TRANSLATION** |
| `9880eb93` accepted `"call an API"` | **RAW UNEXPLAINED TERM** |
| `9880eb93` accepted `"remember part of a task"` | **ACCESSIBLE TRANSLATION** |
| `0b3c1fc1` accepted `"Call an API."` | **RAW UNEXPLAINED TERM** |
| `0b3c1fc1` accepted `"Keep track of what happened."` | **ACCESSIBLE TRANSLATION** |
| `0b3c1fc1` accepted `"A language model"` | **CONTEXTUALLY UNDERSTANDABLE** (paired with contrast to "agent") |
| `c3ff972d` accepted `"call APIs"` | **RAW UNEXPLAINED TERM** |
| `c3ff972d` accepted `"keep some state"` | **RAW UNEXPLAINED TERM** — regression vs `0b3c1fc1`'s translation |
| `c3ff972d` accepted dense list `"language model, memory, search, tools, databases, rules, user information, and ordinary software"` | **RAW UNEXPLAINED TERMS** — collectively scaffolded by *"suspiciously ambitious shed"* metaphor, so the *reader* can extract meaning even without individual definitions; borderline CONTEXTUALLY UNDERSTANDABLE by grouping, not by definition |

Directional finding: minimal-directive corrective passes reintroduce raw unexplained terms; the verbose CHANGE-clause corrective pass produced accessible translations.

---

## §8. Factual Basis literalness analysis (qualitative)

### §8.1 Chunk-head evidence (from sidecars)

The five retrieved knowledge chunks are byte-identical across all five compositions (§13.25.1 STRONG finding). Their heads (from `01_composition_f0e0a7bf_evidence.json::knowledge_chunks_retrieved`):

- `3c5165ea`: "…MULTI-AGENT SYSTEMS. Multiple AI agents can be placed in the same environment. They may communicate, cooperate, disagree, divide responsibilities…"
- `505acbba`: "…AI AGENTS. An AI agent is generally an AI system that can do more than produce one response. Agents may make decisions, select tools…"
- `b3c6e8ac`: "…LANGUAGE MODELS. Large language models can generate and interpret language…"
- `c24d1aa7`: "PATCH — AI BUILDING, EXPERIMENTATION & CONTENT KNOWLEDGE. PURPOSE. Patch is an AI builder, experimenter, inventor…"
- `ed18e966`: "…What Patch wants to know is what he can actually do with a system…"

The literal section headings and label vocabulary — *AI AGENTS*, *LANGUAGE MODELS*, *MULTI-AGENT SYSTEMS* — sit at the top of chunks the LLM is instructed to "Expand secondary detail from" during the corrective retry. SESSION 270 §13.24.11.3 attributed the *"call APIs"* reintroduction in `c3ff972d`'s accepted output specifically to chunk `505acbba` and the *"language model, memory, search, tools, databases…"* dense list to chunk `b3c6e8ac`.

### §8.2 Qualitative comparison

- **First-pass excerpts** show paraphrased language even when the audience directive is minimal (e.g. `9880eb93` first pass: *"handle a task with several steps"* → paraphrase of `multi-step` from chunk 505acbba; `c3ff972d` first pass: *"keep track of what happened"* → paraphrase of *"maintain state"* or an equivalent enumeration in the chunks).
- **Corrective-pass excerpts** contain closer matches to the chunk vocabulary (e.g. `c3ff972d` accepted: *"language model, memory, search, tools, databases, rules, user information, and ordinary software"* — the pattern reads as an enumeration derived from the *"LANGUAGE MODELS"* + *"AI AGENTS"* chunks combined).
- **Verbose specimen contrast**: `f0e0a7bf`'s corrective pass keeps the audience translation (*"call other software"*, *"keep track of what happened before"*) and moves AWAY from the raw chunk vocabulary — the CHANGE clause explicitly says "Adapt vocabulary accessibility" and survives the retry.

**Verdict (qualitative):** consistent with the hypothesis that corrective-pass expansion shows greater lexical/terminological resemblance to §1 Factual Basis than first-pass synthesis under minimal audience directives. Full chunk text was not fetched (DB unavailable in the audit shell — port 5433 auth failure); the chunk-head evidence + SESSION 270 §13.24.11.3 attribution + the corrective_hint's explicit "expand from the knowledge chunks" instruction are sufficient to establish qualitative directionality. **A stricter quantitative resemblance metric would require fetching the full chunk texts, which was not done in this audit.**

---

## §9. Instruction competition / precedence analysis

### §9.1 Structural placement

- Both `corrective_hint` and `audience_hint` are inside the same §5 HARD CONSTRAINTS block.
- Emission order in the assembled prompt is `PINNED OPENER → CORRECTIVE HINT → AUDIENCE DIRECTIVE` (source order in `_assemble_task_message` lines 666-685). AUDIENCE DIRECTIVE therefore holds the trailing position — often a recency advantage in autoregressive LLM prompting.

### §9.2 Mass asymmetry

- Minimal audience directives: 41 (`9880eb93`), 42 (`0b3c1fc1`), 79 (`c3ff972d`), 372 (`f0e0a7bf` verbose) characters.
- Corrective hint: 656 chars, invariant shape across all specimens.
- Under minimal directives, the corrective_hint is 8–16× the character mass of the audience directive.
- Under the verbose directive (`f0e0a7bf`), the audience directive is 57 % of the corrective hint's mass AND contains explicit HOW-to-adapt language.

### §9.3 Semantic competition

The corrective_hint contains two clauses that structurally compete with audience-vocabulary adaptation:

1. `"Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied."` — directs attention back to §1 Factual Basis raw vocabulary.
2. `"Preserve … the factual grounding from the knowledge chunks."` — reinforces the same direction.

Neither clause instructs the model to preserve prior audience-adaptive vocabulary transformations. The Writing Contract (v5, `_solo_scene_contract`, `writing_contract.py:609-728`) contains six SOLO-SCENE INVARIANTS (SINGLE ACTIVE CHARACTER, SINGLE PRESENT MOMENT, PLANS REMAIN PLANS, MEMORY AS BACKGROUND, END ON A MOMENT, PRESERVE CREATIVE FREEDOM). **None address corrective-pass invariance of prior transformations. None mention audience.**

### §9.4 Precedence-rule interaction

Per `_PRECEDENCE_RULES` rule 1: *"Factual Basis (§1) beats everything on TRUTH."* The corrective_hint explicitly re-invokes §1 for expansion material. Since §1 is what beats everything on TRUTH, the model has a structural incentive on the retry to lean into §1's literal token surface for accuracy. The audience directive, occupying §5 Hard Constraints, cannot outrank §1 on TRUTH per rule 5 (*"do NOT override Factual Basis"*). Under a longer, more instructionally-heavy corrective hint that specifically points back at §1, the audience directive's influence on term-by-term vocabulary choice is architecturally weakened even though its byte-position remains stable.

### §9.5 Sub-question — is there a global invariant somewhere requiring corrective passes to preserve first-pass transformations?

**No.** Grep across `shell/character_os/writing_contract.py` and `shell/character_os/script_synthesis.py` reveals no invariant of the form "if this is a corrective retry, preserve X from the first pass." The corrective machinery is designed to hit a duration target; it inherits the same substrate as the first call and receives a size-shortfall summary. Preservation of higher-order transformations was not an explicit design goal of the SESSION 253 duration-contract extraction.

---

## §10. Test coverage audit

Existing tests reviewed:
- `shell/apps/compositions/tests/test_session270_audience_hint.py` (17 tests, 412 lines) — SESSION 270 audience-hint plumbing.
- `shell/apps/compositions/tests/test_duration_contract_talking_head.py` — synthesize_with_duration_gate retry behaviour.
- `shell/apps/compositions/tests/test_session262_composition_observability.py` — per-attempt provenance persistence.
- `shell/apps/compositions/tests/test_writing_contract_solo_scene.py` — solo_scene shape budget interpolation.

| Claim | Coverage | Evidence |
|---|---|---|
| audience_hint reaches FIRST pass' `_assemble_task_message` | **COVERED** | `test_session270_audience_hint.py::test_assemble_task_message_hint_emitted_under_hard_constraints` (line 121); `test_build_render_brief_hint_does_not_leak_via_synthesis_path` (line 220). |
| audience_hint reaches CORRECTIVE pass' `_assemble_task_message` | **NOT COVERED** as an assertion. Architecturally implied by closure capture (§3), but no test asserts `audience_hint` is present in the retry-call kwargs of `build_render_brief`. `test_gate_retries_when_short_then_accepts` (line 240) asserts `"corrective_hint"` is in `retry_kwargs` and `"972" in retry_kwargs["corrective_hint"]`, but does not check `audience_hint`. |
| corrective_hint reaches ONLY the corrective pass, not the first | **COVERED (implicitly)** | Same test — `fake_brb.call_args_list[0]` (first call) has no `corrective_hint`, `[1]` has one. |
| Previous first-pass draft is / is not included in corrective prompt | **NOT COVERED** as an explicit assertion. Provable from source (`first_pass_brief` never appears in a prompt-assembly path). |
| Other context (system prompt, TOPIC, memory, chunks) remains invariant between passes | **NOT COVERED** as an equality assertion between first and second call. Provable from source (`_synthesize` closure passes the same variables). |
| Audience-specific SEMANTIC transformations (register / vocabulary translation / metaphor) survive the corrective retry | **NOT COVERED**. Would require end-to-end fixture-based semantic assertions or a golden-output regression — neither exists. |
| PRECEDENCE order within HARD CONSTRAINTS (opener → corrective → audience) | **PARTIALLY COVERED** | `test_assemble_task_message_hint_coexists_with_opener_and_corrective` (line 159) asserts all three block markers are present in the same prompt but does not pin their relative order beyond `AUDIENCE DIRECTIVE` appearing at all. |
| audience_hint containment (§1/§2/§3/memory do NOT carry the hint) | **COVERED** | `test_build_render_brief_hint_does_not_leak_via_synthesis_path` (line 220). |
| Corrective-pass architecture is a regeneration (no first-pass text passed to LLM) | **NOT COVERED** as an explicit assertion. Provable from source. |

**Summary:** Coverage is strong for the ambient plumbing (audience_hint delivery, containment, precedence-tier) but silent on the specific invariant relevant to Q-270-15 (audience_hint present on corrective retry) and on any semantic-preservation guarantee across passes. **No changes to tests were made** per the audit-only constraint.

---

## §11. H1–H6 hypothesis grading

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| **H1** | audience_hint is accidentally absent from corrective synthesis. | **NOT SUPPORTED / FALSIFIED** by source | Closure capture in `duration_contract.py:521-543` proves `audience_hint` is passed byte-identically on both `_synthesize` invocations. Existing test `test_build_render_brief_hint_does_not_leak_via_synthesis_path` proves the audience_hint reaches the assembled prompt on at least one call. No test asserts equality across passes — that gap is what a controlled render or unit-level assertion would close — but there is no source evidence supporting absence. |
| **H2** | audience_hint is present, but corrective_hint competes with it and causes more literal reuse of Factual Basis terminology. | **SUPPORTED** (qualitative + structural) | §5 + §8 + §9. The corrective_hint (656 chars) explicitly instructs "Expand secondary detail from the knowledge chunks", is 8–16× the mass of the minimal audience directives, and shares the same precedence tier. §1 Factual Basis outranks §5 Hard Constraints on TRUTH per rule 1. Chunks contain literal *"call APIs"* / *"LANGUAGE MODELS"* / *"AI AGENTS"* section vocabulary. Accepted-pass excerpts in §7 show closer resemblance to chunk vocabulary than first-pass excerpts. Full quantitative lexical-resemblance metric NOT computed; DB unavailable for chunk-text retrieval in this audit. |
| **H3** | corrective synthesis is a fresh regeneration rather than an edit of the audience-adapted first pass, allowing stochastic loss of prior transformations. | **SUPPORTED** (proven from source) | §6. The first-pass text is captured for observability only; it never enters the prompt of the corrective call. The corrective call receives the same substrate + a size-shortfall summary. Any transformation whose only trace was in the first-pass output is not visible on the retry. |
| **H4** | duration expansion simply requires more technical detail, making terminology recurrence statistically more likely without a mechanical prompt problem. | **PARTIALLY SUPPORTED — cannot be cleanly disentangled from H2 or H3** | The corrective_hint asks for +91 to +341 more chars across specimens; a proportional expansion could reasonably introduce more of the chunk vocabulary. But H2 provides a specific *mechanical* channel (the "expand from knowledge chunks" clause), and H3 shows the regeneration semantics allow prior audience translations to be lost even at the same length. H4 is compatible with the evidence but does not compete cleanly — the same evidence licences H2 + H3. Cannot be discriminated without an experiment that varies size-shortfall independent of instruction wording. |
| **H5** | the 2-of-3 directional pattern is too small/stochastic to localize any mechanism. | **PARTIALLY SUPPORTED — for STATISTICAL localization, but NOT for MECHANICAL localization** | The n=3 minimal-directive sample is genuinely small for a stochastic argument. HOWEVER, the mechanical evidence (H3 proven from source, H2 supported structurally) is independent of the small sample: the regeneration semantics + the explicit "expand from chunks" clause + the mass asymmetry are STATIC properties of the pipeline, not measurements. So "we cannot statistically prove the corrective retry is worse on average" is a fair reading; "we cannot mechanically identify a channel by which this class of failure can occur" is NOT — that channel is proven. |
| **H6** | some combination of the above. | **SUPPORTED** — the best reading | H1 is FALSIFIED. H2 + H3 are the primary mechanical channels; both are supported and are compatible with each other (a regenerated corrective pass that is additionally biased toward §1 by the corrective_hint text). H4 is compatible but not necessary. H5 is a legitimate warning about the specific 2-of-3 finding but does not weaken the source-level mechanical findings. |

---

## §12. Classification — audience failure vs corrective-pass invariance failure vs retry variance vs unresolved

**Classification: CORRECTIVE-PASS INVARIANCE FAILURE (bounded).**

Justification:

- The audience directive itself IS producing clean first-pass adaptation under minimal directives in 2 of 3 audience-conditioned specimens (`9880eb93`, `c3ff972d`). This falsifies "audience directive is too weak by itself" as the primary cause for these two specimens — the directive worked, then its work was lost.
- The word *failure* is used cautiously per the operator brief: accepted outputs remain broadly good (all five compositions scored 8+ PASS across the 10-criterion SESSION 270 grading). This is a reliability question about a specific transformation dimension (audience-appropriate technical vocabulary), not a claim that the pipeline is broken.
- "General retry/regeneration variance" would be a fair reading IF the mechanism were purely stochastic. Source analysis (H2 + H3) shows the regeneration is additionally biased in a specific direction — toward §1 Factual Basis vocabulary — by the corrective_hint text. So the variance is not neutral; it has a direction.
- "Unresolved" would be appropriate if H1 remained plausible. H1 is falsified from source.

**More precise wording:** the corrective-pass expansion mechanism, as currently implemented, does not carry any invariant that requires it to preserve first-pass audience-adaptive vocabulary transformations. It is architecturally a regeneration with a size-shortfall summary + an "expand from knowledge chunks" instruction, and both properties structurally weaken audience-specific vocabulary transformations under minimal directives. This is a design gap, not a bug.

---

## §13. Broader implication (bounded future question — DO NOT test now)

The operator + ChatGPT raised a broader hypothesis: if corrective synthesis can weaken audience-specific transformation, perhaps other high-level transformations could also drift during corrective retry (character voice, style, brand voice, explanation strategy, other Writing Contract constraints).

**Architectural plausibility check (source-only, no experiments):**

- Character Voice (§2) and Brand Voice (§3) live in the SYSTEM prompt and are byte-identical between passes. Their propositional content is not lost on the retry. Their *stylistic execution* (whether the model expresses character voice with the same lightness, dry wit, tempo, register) is a stochastic property of generation and IS in principle vulnerable to the same class of drift as audience vocabulary — because "stylistic execution" is also only visible in the first-pass output, and the retry is a regeneration.
- Writing Contract (§4) hard structural rules (single active character, no future-narration, one CTA) are re-asserted every call; violations are visible in the output and could be re-verified. But *soft* register guidance (register examples, anti-generic list) shapes the model similarly on both calls, so violation risk on retry is comparable to first-pass risk — not obviously heightened.
- Brand `never_say` phrases live in §3 and are re-asserted every call. Prohibited-phrase drift on the retry would be surprising unless the model chooses to violate a prohibition it did not violate on the first call — that is possible under a fresh regeneration but not more likely than on any other call.

**Verdict:** the architecture *does* make corrective retry a sufficiently fresh regeneration that the *class* of drift is theoretically plausible for any transformation whose only trace was in the first-pass output. This is worth recording as a bounded future question. **Do not test now.** Recorded as **Q-270-17 (candidate, not activated):** *"Under corrective retry, does the accepted output preserve character-voice execution qualities (register, humor rate, tempo) that the first pass established? Test would require substrate with a distinct character-voice fingerprint and a controlled duration-forcing render."*

---

## §14. What was NOT changed during this audit

Per the operator brief, none of the following were touched:

- `shell/character_os/duration_contract.py` — no changes.
- `shell/character_os/script_synthesis.py` — no changes.
- `shell/character_os/writing_contract.py` — no changes.
- `shell/apps/compositions/primitives/avatar_speech.py` — no changes.
- Corrective_hint wording — not modified.
- Audience_hint wording — not modified.
- Writing Contract — not modified (still v5).
- Any prompt template — not modified.
- Any test — not added.
- `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` — remains unset.
- Any Composition — no render fired.
- Any schema / migration — not touched.
- SPA UI — not touched.
- NarrativeMemory pool — untouched (still 14 active + 1 archived per SESSION 270 §14.4).

Only durable documentation was created (this file).

---

## §15. Decision-gate recommendation

**GATE: B — MECHANISM NARROWED BUT NOT PROVEN.**

Justification:
- H1 falsified from source (strong).
- H3 proven from source: corrective retry is a REGENERATION, not an EDIT (strong).
- H2 supported qualitatively + structurally (medium-strong): the corrective_hint explicitly redirects the model toward §1 raw vocabulary, at the same precedence tier as audience_hint but with 8–16× the mass, under a PRECEDENCE RULE that gives §1 the TRUTH tier.
- H4 remains compatible but not disentangled from H2/H3.
- H5 legitimately warns that the specific 2-of-3 sample cannot support a strong statistical claim, but does NOT weaken the source-level mechanical findings.

Whether the observed pattern is caused primarily by (a) the fresh-regeneration property (H3), (b) the corrective_hint's explicit "expand from chunks" clause (H2), or (c) both — is not yet mechanically disentangled. Both (a) and (b) are properties of the pipeline that could each independently produce the pattern, and both are readily testable.

### §15.1 Smallest next falsifiable question

Two candidates, in priority order. Both are single controlled experiments; both can be executed without expanding substrate beyond the SESSION 270 controls.

**PRIMARY CANDIDATE — Q-270-15a (recommended smallest slice):**

*"Does inserting an explicit 'preserve audience-appropriate vocabulary' clause into the AUDIENCE DIRECTIVE (leaving corrective_hint byte-stable) close the at-risk term reintroduction gap in the corrective pass under minimal audience directives?"*

This is the smallest instruction-side test. It leaves the pipeline architecture unchanged and tests only whether a term-preservation prompt clause inside the audience directive is sufficient to bind through the corrective retry. Substrate: same Universe / Episode / Patch / substrate as `9880eb93` (child) or `c3ff972d` (nontechnical adult). One render. Read from the frozen first-pass + corrective-pass fields on the Composition; grade against the §13.28 at-risk term set.

**SECONDARY CANDIDATE — Q-270-15b:**

*"Does replacing 'Expand secondary detail from the knowledge chunks' with 'Expand secondary detail while preserving the audience translations from the previous draft' (leaving audience_hint minimal, byte-stable) close the at-risk term reintroduction gap?"*

Tests the H2-specific channel. Requires wording change inside `_expansion_hint`. Substrate same as above.

**Discriminating power:** if Q-270-15a closes the gap and Q-270-15b does not, the audience-directive layer is the effective lever (H3 remains true but is mitigated). If Q-270-15b closes the gap and Q-270-15a does not, the corrective_hint wording is the effective lever (H2 confirmed). If both close it, either lever works; if neither, the regeneration semantics (H3) may need a different intervention (e.g. passing the first-pass draft to the corrective call as context).

**Either experiment is a single render. Either produces evidence sufficient for a slice-2 decision. DO NOT execute now.** Await Chris + ChatGPT authorisation.

---

## §16. Answers to the SESSION 271 return-question set

1. **What exactly happens between first and corrective synthesis?**
   The corrective retry calls `build_render_brief` again with the same spokesperson, operator_prompt, target_shape, memory_rows, and audience_hint. It adds a 656-char `corrective_hint` string that summarises the size shortfall and instructs the model to "REWRITE THE SAME NARRATIVE" longer, "Preserve the central arc, narrator perspective, and factual grounding from the knowledge chunks", and "Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied". No previous-draft text is included.

2. **Is audience_hint present on both?**
   YES, byte-identically. Proven by closure capture in `duration_contract.py::synthesize_with_duration_gate::_synthesize` (line 542) — the same enclosing-scope variable is passed on both invocations. Downstream `build_render_brief` and `_assemble_task_message` emit the AUDIENCE DIRECTIVE block on both calls.

3. **Is corrective synthesis editing the first draft or generating fresh?**
   Generating fresh. The first-pass draft text is captured for observability (`first_pass_brief`) but is never included in any prompt sent to the LLM on the corrective call.

4. **Why did technical terminology plausibly return in 2 of 3 minimal specimens?**
   Because the corrective call is a fresh regeneration under (a) a size-expansion instruction that explicitly directs attention toward §1 raw vocabulary, (b) the same audience directive as the first pass (which is 8–16× smaller than the corrective_hint under minimal directives), and (c) no pipeline invariant requiring preservation of specific vocabulary transformations made by the first pass. The audience directive continues to shape the model's output — accepted outputs remain register-strong per SESSION 270 grading — but the specific term-by-term translations the first pass invented are not persisted and can be re-decided (or not made at all) on the retry.

5. **Is Factual Basis being reused more literally?**
   Qualitatively yes — the accepted-pass excerpts in §7 show closer lexical resemblance to chunk-head vocabulary than the first-pass excerpts under minimal directives. A quantitative resemblance metric requires full chunk text (DB unavailable in this audit shell) and was NOT computed. The verbose specimen `f0e0a7bf` is the counter-case: its explicit "vocabulary accessibility" clause survived the retry and the accepted output moved further from raw chunk vocabulary (*"call other software"* vs the chunks' *"call APIs"*).

6. **What do current tests prove / not prove?**
   PROVE: audience_hint reaches at least one call's assembled prompt in the §5 HARD CONSTRAINTS block; audience_hint does not leak into §1/§2/§3/memory; corrective_hint fires on the second call and contains the correct target character count; all resolution paths (params → settings → env). DO NOT PROVE: audience_hint reaches the CORRECTIVE call specifically (implied by closure but no explicit assertion); no first-pass text is passed to the corrective call; any semantic invariance of transformations across passes.

7. **H1–H6 verdicts.**
   H1 NOT SUPPORTED / FALSIFIED (source). H2 SUPPORTED (qualitative + structural). H3 SUPPORTED (proven from source). H4 PARTIALLY SUPPORTED but not disentangled from H2/H3. H5 PARTIALLY SUPPORTED for statistical claims, NOT for mechanical localization. H6 SUPPORTED (H2 + H3 combined is the best reading).

8. **Final classification.**
   **CORRECTIVE-PASS INVARIANCE (BOUNDED).** The audience directive itself does its job on the first pass in 2 of 3 minimal-directive specimens. The corrective retry is a fresh regeneration whose instruction set redirects attention toward §1 raw vocabulary. No pipeline invariant preserves audience-adaptive vocabulary transformations across passes. This is a design gap, not a bug. Accepted outputs remain broadly good; this is a reliability question about a specific transformation dimension.

9. **Decision gate.**
   **B — MECHANISM NARROWED BUT NOT PROVEN.** H1 falsified, H3 proven, H2 supported. Discriminating H2 vs H3 (or confirming both are load-bearing) requires ONE controlled render.

10. **Smallest recommended next move.**
    Q-270-15a: single controlled render on the SESSION 270 substrate, with audience_hint carrying an explicit vocabulary-preservation clause and corrective_hint byte-stable. Compare first-pass and corrective-pass at-risk terminology against the §13.28 baseline. Alternatively Q-270-15b (edit corrective_hint) if the operator prefers to test the H2 channel directly. **DO NOT EXECUTE without explicit authorisation.**

11. **Durable doc path.**
    `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` (this file).

12. **Commit SHA + push / clean-tree state.**
    Recorded in §17 at the end of the audit slice.

---

## §17. Slice commit + push record

- Slice commit SHA: `0cb3d7c` — `docs(session-271): Q-270-15 corrective-pass audience-invariance audit (frozen-evidence, source-only)`.
- Push: `34d825f..0cb3d7c main -> main` (successful).
- Local `main == origin/main == 0cb3d7c` verified.
- Working tree at slice close: clean.

---

# SESSION 271 — SLICE 2 · Duration-Correction Design Archaeology

Slice 2 investigates *why* the corrective-pass architecture is a regeneration rather than a revision. Slice 1 proved the current behaviour mechanically; Slice 2 reconstructs, from commit history and durable design documentation, the design intent that produced it. Audit-only; no code, no prompts, no tests, no render.

**Scope guard:** where the historical record is silent, this section says "intent is not recoverable from the available evidence" rather than rationalising the current design. Where the historical record is explicit, the exact commit SHA, date, message, or doc line is cited.

---

## §18. Commit lineage of the duration gate

### §18.1 The two ancestor commits (chronological)

| # | SHA | Date | Subject | Session | Role in lineage |
|---|---|---|---|---|---|
| 1 | `7f22085` | Fri **Aug 14 16:34:28 2026** | `feat(long-form-ad): duration-driven synthesis with character-budget acceptance gate` | **SESSION 251** | **ORIGIN.** Retry semantics born inline inside `apps/compositions/starters.py::long_form_ad`. Introduced `_synthesize` closure, `_measure` helper, `_expansion_hint`, `_compression_hint`, the exact phrase `"REWRITE THE SAME NARRATIVE"`, `LongFormDurationError`, character-budget acceptance gate. Full retry pattern shipped in ONE commit. |
| 2 | `1e3757d` | between SESSION 251 & 253 | `fix(long-form-ad): return 201 with failed composition on out-of-tolerance, not 500` | SESSION 251/252 area | HTTP semantics fix — no retry-mechanism change. |
| 3 | `32b14d0` | Sat **Aug 15 00:04:39 2026** | `fix(k6): shared duration contract + talking_head duration wiring` | **SESSION 253** | **EXTRACTION.** Machinery lifted verbatim out of `long_form_ad` into new `shell/character_os/duration_contract.py`; `synthesize_with_duration_gate` is renamed public entry. Motivation from commit body: *"The dogfooded talking_head + AI-topic path had no duration selector and no acceptance gate — K6 always ran the standalone 60-100 word shape and the composition happily rendered whatever came out (57 s from a 90 s intent). Runway charged the flat 2 credits regardless of duration mismatch."* |
| 4 | `51f001a` | SESSION 253 | `fix(duration-contract): distinguish provider-cap violation from duration-tolerance overshoot` | SESSION 253 amendment A | Classification refinement. No retry-semantics change. |
| 5 | `43db23a` | SESSION 253 | `fix(duration-contract): calibrated LLM synthesis-target bias (SESSION 253 amendment B)` | SESSION 253 amendment B | Adds `K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 0.78`. Bias-only change. |
| 6 | `b1e452b` | SESSION 253 | `fix(duration-contract): persist measured post-render duration via ffprobe (SESSION 253 stage 2)` | SESSION 253 stage 2 | Post-render measurement — not retry. |
| 7 | `ae878bf` | SESSION 253 | `fix(duration-contract): recalibrate delivery-rate estimator to 15 cps (SESSION 253 stage 3)` | SESSION 253 stage 3 | CPS calibration. |
| 8 | `3860474` | SESSION 254 | `fix(duration-contract): raise K6 synthesis-target multiplier 0.78 -> 0.90 (SESSION 254)` | SESSION 254 | Bias recalibration. |
| 9 | `01f12b1` | Mon **Aug 17 17:31:45 2026** | `feat(compositions): SESSION 262 — Composition observability schema v1` | **SESSION 262** | **`first_pass_brief` / `first_pass_synthesis` INTRODUCED.** Purpose stated in commit body: *"Persists Composition-local synthesis provenance so post-hoc audits can reconstruct what happened to a render attempt from DB state alone, without terminal logs. Closes the six SESSION 259 audit blockers documented in SESSION_259_OBSERVABILITY_BACKLOG.md."* No mention of feeding first_pass back into synthesis. Multi-corrective retry explicitly deferred (see COMPOSITION_OBSERVABILITY_V1.md line 80–82). |
| 10 | `44618fc` | SESSION 269 | `feat(story-mode): SESSION 269 §15 — Episode-solo talking_head STORY MODE` | SESSION 269 | Adds `solo_scene` shape branch; retry semantics unchanged. |
| 11 | `39a4fc0` | SESSION 270 | `feat(session-270): solo-only audience_hint research plumbing + tests + §13 doc` | SESSION 270 | Adds `audience_hint` kwarg on `synthesize_with_duration_gate` / `build_render_brief` / `_assemble_task_message`; closure captures it so both passes see the same value. Retry semantics unchanged. |

### §18.2 Prior art — dialogue retry uses the same pattern (independent implementation)

`shell/character_os/dialogue_synthesis.py::_dialogue_over_length_hint` (line 922) + `_dialogue_under_length_hint` (line 977) implement the identical "Rewrite the SAME scene / preserve X / do NOT Y" pattern for the dialogue lane. It does not pass the first-pass JSON back to the LLM either. Same regeneration-not-edit shape, evolved in parallel; earliest reference in `EPISODE_VS_COMPOSITION_V1.md` line 27 mentions "corrective-hint, and retrieval snapshot on failed paths are all" transient. Not a shared abstraction — two parallel corrective mechanisms with the same design shape.

---

## §19. Original problem the duration gate solved

Reconstructed from the SESSION 251 (`7f22085`) and SESSION 253 (`32b14d0`) commit bodies verbatim.

### §19.1 SESSION 251 problem statement (from `7f22085`)

Three concrete symptoms from dogfood:

1. *"long_form_ad with use_knowledge=True [previously] set the same flag on every per-chunk `generate_avatar_speech` step, which caused K6's `build_render_brief` to fire independently for each chunk. K6 has no cross-chunk awareness — it treats each chunk as a fresh topic and synthesizes a full standalone script with its own hook, body, and CTA. The 9-chunk operator dogfood produced '9 mini-ads back to back' instead of one continuous narrative."*
2. *"Word count [was] proving a lossy proxy — 306 words fit the word budget for 120s but estimated at ~170s under the canonical chars/sec rate."* → gate had to be character-based.
3. *"Corrective hints (either direction) name concrete character ceilings — 'REWRITE ABOVE/BELOW N CHARACTERS' — with the exact character delta to add or remove. Soft 'please compress' language barely trimmed 49 chars on Penny's brief; the explicit ceiling trimmed 112."* → the phrasing was empirically tuned for one very specific behaviour: **numeric compliance**.

### §19.2 SESSION 253 problem statement (from `32b14d0`)

*"The dogfooded talking_head + AI-topic path had no duration selector and no acceptance gate — K6 always ran the standalone 60-100 word shape and the composition happily rendered whatever came out (57 s from a 90 s intent). Runway charged the flat 2 credits regardless of duration mismatch."*

### §19.3 Classification (Phase 3 options A–H)

| Option | Verdict |
|---|---|
| A. scripts routinely too short | **YES — primary driver at SESSION 251/253.** 57 s from 90 s intent; standalone 60-100 word shape leaking into duration-driven callers. |
| B. scripts routinely too long | Secondary. Compression path exists but SESSION 251 test names emphasise the undersized case as the load-bearing failure. |
| C. provider character limits | **YES — parallel driver.** `AVATAR_SPEECH_SAFE_MAX_CHARS = 1900` fenced against media-engine's 2000-char Pydantic cap. |
| D. duration estimate mismatch | **YES.** Word-count vs char-count vs seconds. Motivated the char-based gate. |
| E. long-form chunking | **YES — original SESSION 251 driver.** `long_form_ad` was firing K6 per chunk; SESSION 251 changed it to "one synth → chunk the result." |
| F. Episode talking-head duration | Not yet — Episode substrate came SESSION 262. SESSION 253 extended to standalone talking_head + AI-topic. |
| G. generic script synthesis | **YES at SESSION 253** — the extraction made the machinery shape-agnostic. |
| H. something else | Cost/credit accountability: *"Runway charged the flat 2 credits regardless of duration mismatch."* Zero-Runway-spend on out-of-tolerance drafts is called out as a load-bearing gate property. |

**Original problem, one line:** *the pipeline was silently producing scripts whose measured duration did not match the operator's requested duration, and Runway was billing for those renders anyway.* Everything else in the machinery is scaffolding around that.

---

## §20. Was revision-vs-regeneration explicitly considered?

Phase 4 options A–F, evaluated against the historical record:

| Option | Historical status | Evidence |
|---|---|---|
| **A. Fresh regeneration + corrective_hint** | **EXPLICITLY CHOSEN (implicit — the only option shipped)** | SESSION 251 commit `7f22085` implements this pattern with no alternative discussion in the commit body. |
| **B. Pass first-pass script back and ask the model to revise it** | **NO EVIDENCE IT WAS CONSIDERED** | Grep across durable docs (`docs/design/*.md`) + commit messages for "revise", "revision", "pass first draft back", "feed first-pass", "re-use first-pass" returns zero hits on the duration/corrective machinery. `EPISODE_VS_COMPOSITION_V1.md` and `AUTO_SCRIPTING_V1.md` mention `Script.revision_history` — but that is the older/parallel `Script` model's snapshot-on-regenerate list, a separate lineage. |
| **C. Programmatic expansion/compression** | **NO EVIDENCE IT WAS CONSIDERED** | Would have required deterministic text manipulation; not mentioned. |
| **D. Accept out-of-range duration** | **EXPLICITLY REJECTED** | The whole point of the gate is *not* to accept: "No Runway call fired" appears in every DurationContractError message. Zero-Runway-spend is the load-bearing guarantee. |
| **E. Multiple retries / iterative editing** | **EXPLICITLY DEFERRED** | Explicit in `COMPOSITION_OBSERVABILITY_V1.md` (line 80–82): *"Multi-corrective-pass retry (v1 remains 'one bounded corrective pass')."* Also in Q4 of that doc (line 230–248): *"The current synthesis loop is bounded to one corrective pass ... two attempts is a fixed-cardinality schema."* Repeated later in Q5 immutability discussion. |
| **F. Something else** | Chunk-based semantic revision, per-clause pruning, LLM-graded quality vs length, human-in-loop compression — none appear. | No evidence. |

**Overall Phase 4 verdict:** the ONLY design option that appears in the historical record is A. B, C, F have zero mention. D + E are recorded as explicitly rejected/deferred. The regeneration architecture emerged from a single commit (SESSION 251) that solved a specific dogfooded numeric-compliance problem; alternative retry semantics are not documented as having been surveyed.

**Absence of discussion is not proof of rejection.** The most defensible reading is: at SESSION 251, "regeneration + corrective hint" was the smallest implementation that satisfied a specific empirical failure (soft compression didn't work; explicit character ceilings did). Broader "should retry preserve first-pass semantics" was not part of the requirement.

---

## §21. Why first_pass_brief exists — and when

### §21.1 Provenance

- **When:** SESSION 262, commit `01f12b1` (Mon Aug 17 17:31:45 2026). Migration `0014` on Composition. **Ten sessions and 3 days after the retry mechanism was born; three days after `synthesize_with_duration_gate` was extracted into its own module.**
- **Why:** to close SESSION 259 audit blocker #3 (*"First-pass output lost on success. Could not tell whether v4 densification appeared on the first pass or only after the corrective retry's 'tighten' instruction was ignored."*) and #6 (*"Rejected-synthesis field carries only one attempt. When both passes fail, `Composition.rejected_synthesis` holds only the LATER (corrective-pass) response. Auditors cannot see what the model corrected FROM."*).
- **Design frame:** post-hoc observability, not synthesis input. Every claim in `COMPOSITION_OBSERVABILITY_V1.md` (design doc for the SESSION 262 slice) frames this data as *reconstruct-what-happened-from-DB-state*. Full doc scope statement (line 11–15): *"Enumerate what synthesis provenance is persisted vs transient on Composition today, identify the gaps that repeatedly blocked SESSION 259 audits, and design the smallest additive schema slice that closes those gaps without conflicting with the deferred Episode primitive."*

### §21.2 Was feeding first_pass back into synthesis considered?

Grep across `COMPOSITION_OBSERVABILITY_V1.md`, `COMPOSITION_OBSERVABILITY_SCHEMA_V1.md`, `EPISODE_VS_COMPOSITION_V1.md`, `EPISODE_LIFECYCLE_V1.md`: **zero hits.** The observability slice explicitly deferred *multi-corrective-pass retry* and treated `first_pass_synthesis` as immutable-after-write (Q5 line 258–275 of `COMPOSITION_OBSERVABILITY_V1.md`) — *"describe a specific synthesis attempt at a specific moment. Overwriting them silently would destroy the audit trail we are creating."* The immutability discipline itself embeds an audit-trail-first mental model, not a synthesis-input model.

### §21.3 Sequencing verdict (Phase 5 A/B/C)

**A. Retry architecture predates first_pass_brief.** Confirmed by commit dates: retry Aug 14 (`7f22085`), first_pass_brief Aug 17 (`01f12b1`), delta ~72 hours + ten sessions of unrelated work in between. First_pass_brief was later added purely for observability.

At SESSION 251 when retry semantics were chosen, the first-pass script existed transiently as `synth.brief` (Python local) and was OVERWRITTEN by the retry's return value. There was no persistent handle, no observability field, no schema, no test asserting its lifetime. Feeding it back would have required first defining "what is a first-pass output" as a persistent concept — which the codebase did not have.

**The availability today does change the design possibilities.** `Composition.first_pass_synthesis` is immutable-after-write and reliably populated on both dialogue and long-form / solo_scene paths. Anything the corrective call would need — the exact first-pass text, the retrieved chunks, the operator topic, the audience directive, the memory rows — is either already in the enclosing scope or already persisted on Composition. This was not true at SESSION 251. It is true now.

---

## §22. Origin of "REWRITE THE SAME NARRATIVE"

### §22.1 First appearance

Verbatim string introduced in commit `7f22085` (SESSION 251) — the same commit that created the retry mechanism. Inline in `long_form_ad`'s corrective loop:

```python
f"REWRITE THE SAME NARRATIVE ABOVE {synth_min_chars} CHARACTERS "
f"(aim for ~{synth_ideal_chars}, do not exceed {synth_max_chars})..."
f"Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks..."
```

Preserved byte-for-byte when extracted to `duration_contract.py::_expansion_hint` at SESSION 253 commit `32b14d0`. Never revised.

### §22.2 Did the model ever have the prior narrative when this phrase was introduced?

**NO.** The SESSION 251 commit `7f22085` created `_synthesize` as a closure that calls `build_render_brief(spokesperson, script, ...)` — where `script` is the OPERATOR TOPIC (the same topic on both passes). The first-pass output (`synth.brief`) was captured only to `_measure` its length and to be re-assigned by the retry. It was never included in the prompt.

So *"REWRITE THE SAME NARRATIVE"* did not describe how the mechanism worked at birth. It described how the operator was expected to conceptualise the retry: "same story, different length." The LLM never actually received the previous narrative to *rewrite* — it received the same substrate plus a size-shortfall summary and was asked to *reconstitute* a plausible previous narrative from the same inputs and then extend it.

### §22.3 Was the phrase inherited from an earlier pipeline where the LLM DID have the draft?

Investigated. **No such predecessor.** The commit that introduces the phrase is the same commit that introduces the retry. `git log -S "REWRITE THE SAME NARRATIVE" -- shell/` returns only `7f22085` and `32b14d0` (the extraction commit); no prior file used it. There is no evidence the wording was borrowed from an older revision-style mechanism.

### §22.4 Classification

**Semantically misleading in the current architecture, but not a bug.** It was chosen at birth as an *instruction to the LLM to preserve narrative continuity* — a natural-language framing that the model can follow even without seeing the previous text, by reading it as "produce a longer version of the story you would have written." The historical record shows no evidence it was ever intended as a promise that the previous draft would be in context.

---

## §23. Historical test intent (Phase 7)

Tests added in SESSION 251 (`7f22085`), `test_long_form_ad_duration_contract.py` (648 LOC, 15 tests) + `test_long_form_ad_knowledge_ordering.py` (392 LOC, 6 tests):

| Test | What it guarantees |
|---|---|
| `test_standalone_default_receives_short_form_contract` | shape wiring |
| `test_long_form_receives_narrative_contract` | shape wiring |
| `test_long_form_prompt_interpolates_target_duration_and_word_budget` | prompt shape |
| `test_long_form_prompt_interpolates_character_budget` | prompt shape |
| `test_multi_minute_long_form_never_uses_short_form_paragraph` | shape wiring |
| `test_build_render_brief_refuses_long_form_without_duration` | precondition |
| `test_knowledge_mode_synthesis_runs_exactly_once` | count |
| `test_chunks_use_synthesized_text_verbatim` | ordering |
| `test_undersized_synthesis_retries_once_then_fails` | **retry-happens + no-infinite-retry** |
| `test_oversized_synthesis_retries_once_then_fails` | **retry-happens + no-infinite-retry** |
| `test_retry_converges_into_tolerance_and_ships` | **convergence to correct length** |
| `test_word_in_budget_but_duration_over_still_rejected` | duration-first gate |
| `test_compression_retry_converges_from_over_duration` | **compression convergence** |
| `test_no_chunk_steps_created_when_duration_out_of_tolerance` | **provider safety / zero Runway spend** |
| `test_talking_head_still_uses_standalone_shape` | regression guard |
| `test_knowledge_off_long_form_ad_does_not_rewrite_script` | verbatim path |
| `test_word_budget_matches_speaking_rate` | estimator sanity |
| `test_build_render_brief_rejects_bad_shape` | validation |
| `test_use_knowledge_true_synthesizes_exactly_once` | count |
| `test_use_knowledge_true_chunks_get_use_knowledge_false` | ordering |
| `test_use_knowledge_true_chunks_split_from_synthesized_brief` | ordering |
| `test_use_knowledge_false_uses_operator_input_verbatim` | verbatim path |
| `test_use_knowledge_true_persists_synthesis_metadata_on_composition` | metadata |
| `test_use_knowledge_true_strict_rejection_raises_with_composition_id` | error shape |

**Zero tests concern preservation of first-pass content, character voice, register, vocabulary, metaphor, or any semantic property across retry.** The test suite's design intent is unambiguous: **duration compliance + retry bounded to one attempt + provider-safety + prompt/shape correctness.** That was the whole requirement.

The SESSION 262 observability tests extended this to persistence assertions (does `first_pass_synthesis` get stored?) — still no semantic-preservation assertions across the pass boundary.

---

## §24. Cost / token / provider constraints considered? (Phase 8)

| Potential reason to exclude Draft A from the corrective prompt | Classification | Evidence |
|---|---|---|
| Context-window pressure | **PLAUSIBLE BUT NOT DOCUMENTED** | The full system prompt is already ~4-8KB (§1-§4 + memory + chunks). Adding a ~1500-char first draft is negligible for gpt-5-mini / gpt-5.6-terra context windows. Not mentioned as a design constraint. |
| Input token cost | **PLAUSIBLE BUT NOT DOCUMENTED** | Would double input tokens on retry paths only. At current pricing tiers this is a tiny fraction of a cent per render. Not mentioned. |
| Output token cost | **IRRELEVANT** | Output tokens are the same either way — a full new script of target length. |
| Latency | **PLAUSIBLE BUT NOT DOCUMENTED** | Extra input tokens add negligible latency for gpt-5-mini class models. |
| Provider restrictions | **NOT DOCUMENTED** | No provider requires or prohibits including the previous output. |
| Max character limits | **CONTRADICTED BY EVIDENCE** | Media-engine's 2000-char cap is on the OUTPUT going to Runway avatar, not on the LLM input. `AVATAR_SPEECH_SAFE_MAX_CHARS` is a synth-output ceiling; not a prompt-size constraint. |
| Prompt size | **PLAUSIBLE BUT NOT DOCUMENTED** | See context-window row. |
| Duplicated factual content | **PLAUSIBLE BUT NOT DOCUMENTED** | The first draft would restate facts already in §1. Weak reason — the LLM tolerates factual reinforcement in context routinely. |
| Contamination / anchoring concerns | **PLAUSIBLE BUT NOT DOCUMENTED** | If the first draft was bad (e.g. K6.4 rejected on strict), the operator wouldn't want the model to keep its bad language. Applicable to BAD-DRAFT case; not applicable to GOOD-BUT-WRONG-LENGTH case (see §26). Not mentioned in the historical record. |
| Bad first draft should not poison second draft | **PLAUSIBLE BUT NOT DOCUMENTED** | Same as above. This is the strongest a priori reason for regeneration, but again, no doc says so. |
| Simpler deterministic test surface | **PLAUSIBLE — MATCHES SESSION 251 EMPIRICS** | The SESSION 251 commit body's emphasis on "explicit character ceilings trimmed 112 chars vs soft language 49 chars" reads as an *implementation-simplicity + empirical-effectiveness* choice: numeric compliance is testable, semantic preservation would not have been. This is the closest thing to a documented rationale — but even here the doc doesn't say "we chose regeneration because it's simpler to test." It says "explicit ceilings work; soft language doesn't." |
| Implementation complexity | **PLAUSIBLE — MATCHES SESSION 251 EMPIRICS** | The retry loop as shipped is ~40 LOC inline; a revision loop that manages both the prompt structure and the draft-inclusion decision would be materially larger. |

**Overall Phase 8 verdict:** the only historically-documentable reason for the current design is *empirical effectiveness at numeric compliance*: soft compression language failed, explicit character-ceiling language worked. Every other candidate reason is plausible but silent in the historical record. **We should not attribute a rationale that is not documented.**

---

## §25. Regeneration vs revision — honest tradeoff table (Phase 9)

Comparing CURRENT (fresh regeneration + corrective_hint) vs HYPOTHETICAL (same substrate + first-pass draft included + revise-only-for-duration instruction).

| Dimension | CURRENT (regeneration) | HYPOTHETICAL (revision) | Which wins? |
|---|---|---|---|
| Narrative continuity across passes | Stochastic — model reconstructs from substrate. In practice usually similar; SESSION 270 evidence shows story arc is stable but wording differs. | High — model has the previous text and is asked to preserve structure. | Revision |
| Audience-vocabulary transformation preservation | Weak under minimal directives — see SESSION 271 Slice 1 §7 / §11 (2 of 3 minimal-directive audience specimens reintroduce at-risk terms). | High in principle — the specific translations from the first pass are visible to the model. | Revision (for this specific problem) |
| Character-voice execution preservation | Weak under compression — see SESSION 263 §6.5 *"The corrective compression pass IS an active amplifier"* (documented for dialogue in SESSION 263 audit). Likely also weak under expansion. | High in principle — the specific voice moves in the first pass are visible. | Revision |
| Metaphor / joke preservation | Weak — an ad-lib metaphor invented in first pass may not recur on retry. SESSION 263 evidence: *"comedic invention, dropped in compression."* | High in principle — the model can be told to preserve them explicitly. | Revision |
| Factual grounding | Strong — §1 Factual Basis is present on both passes; PRECEDENCE rule 1 keeps §1 authoritative for TRUTH. | Comparable — §1 is still present on both passes. | Draw |
| Risk of preserving first-draft errors | LOW — errors do not carry over into a fresh regeneration. | ELEVATED — model may faithfully preserve a first-draft error unless told which properties to drop. Mitigable with explicit "correct any factual errors" wording. | Regeneration |
| Risk of introducing new unsupported claims | Elevated — every fresh regeneration is an opportunity to hallucinate. §1 + PRECEDENCE mitigate but do not eliminate. | Lower — the first-pass draft already fixed the claim surface; revision is more constrained. | Revision |
| Prompt / input token cost | Lower (~5-10% smaller input on retry). | Higher (adds ~800-1500 chars of first-draft text to the input on retry). Negligible in absolute terms. | Regeneration (marginal) |
| Output token cost | Same either way — same target length. | Same. | Draw |
| Latency | Marginally lower. | Marginally higher (larger input). | Regeneration (marginal) |
| Implementation complexity | Simple — a single ~40 LOC closure. | Somewhat higher — needs to decide when to include Draft A (all retries? only GOOD-BUT-WRONG-LENGTH?), needs a new prompt-composition path. | Regeneration |
| Testability | Simple — assert retry fires + correct length. Existing test surface unchanged. | Larger surface — assert draft is included, assert preservation invariants. Would need semantic-invariance assertions the codebase does not currently have. | Regeneration |
| Duration correction effectiveness | Proven — SESSION 251 empirics + years of dogfood. All five SESSION 270 renders converged on retry. | Unknown — plausibly comparable or better, but not tested. | Regeneration (only tested condition) |
| Compression behavior specifically | Documented weak point (SESSION 263 §6.5); "same K2 grounding, different reading effect." | Plausibly stronger — asks the model to *shorten* text it has in hand, which is closer to what real editing looks like. | Revision (hypothesis) |
| Expansion behavior specifically | SESSION 270 evidence: introduces raw §1 vocabulary under minimal audience directives. | Plausibly stronger — asks the model to *extend* text it has in hand rather than invent new phrasing that competes with §1. | Revision (hypothesis) |
| Provider limits | Comfortable margin either way. | Same. | Draw |
| Observability | Simple — one first_pass field + one corrective_pass field. Already schema'd (SESSION 262). | Same fields; slightly different semantics for `corrective_pass_synthesis`. Backwards compatible. | Draw |
| Determinism / stochastic variance | Elevated — regeneration is a full LLM sample. | Lower — revision starts from a fixed anchor. | Revision |
| Failure mode when Draft A itself was bad | Clean — regeneration ignores the bad draft. | Risky — model may faithfully preserve the badness. Would need the mechanism to know "Draft A is bad" and skip revision in that case. | Regeneration |

**Honest verdict:** revision is plausibly stronger on nearly every semantic-preservation dimension AND weaker on nearly every "protect against bad first draft" dimension. Neither strictly dominates. The clean split maps onto the §26 GOOD-vs-BAD distinction.

---

## §26. Good-but-wrong-length vs bad draft (Phase 10)

### §26.1 What does the current pipeline know about draft quality before retry?

Trace of `synthesize_with_duration_gate` (`duration_contract.py:521-621`):

- The retry decision is made purely on measured length: `if actual_chars < raw_min: expand; elif actual_chars > acceptance_max or provider_cap_binds: compress`.
- The K6.4 verifier fires **inside** `build_render_brief` (before the return). If verification fails in strict mode, it raises `ClaimVerifierError` and the retry loop never fires. So by construction, if the first pass reaches the retry decision, it has already passed strict K6.4 (or verifier is warn/off).
- **However:** no quality signal beyond "K6.4 didn't strict-reject" is examined. The retry logic does not know whether the first draft was strong or weak.

**The current retry does not distinguish GOOD-BUT-WRONG-LENGTH from BAD-DRAFT.** Every draft that survives K6.4 gets the same treatment: regenerate from substrate.

### §26.2 Was the distinction ever intended?

**NO EVIDENCE.** The SESSION 251 commit body describes the case where "306 words fit the budget but estimated at ~170s" — a *good draft that's mislabeled* case. But the fix was character-based gating, not draft-quality gating. No historical doc distinguishes the two failure classes.

### §26.3 Would passing Draft A back specifically for GOOD-BUT-WRONG-LENGTH be reasonable?

Architecturally, yes — the case where a draft has passed the verifier, matches character/brand/audience, and merely misses a numeric length target is exactly the case where the model has good work to preserve. Revision here would minimally disturb the successful properties while re-hitting the numeric target.

For BAD-DRAFT (structurally poor, malformed, verifier-failing before strict rejection, or otherwise clearly weak), fresh regeneration remains the safer default — you don't want the model to faithfully preserve badness.

**Bounded product implication:** any future revision experiment should scope itself to the GOOD-BUT-WRONG-LENGTH case. The current pipeline has no explicit "draft quality" signal, but "reached the duration retry loop with `verification_status ∈ {verified, skipped, trusted_passthrough}` and no other error" is a workable proxy for "good enough for revision to be safe."

---

## §27. Compression vs expansion — do they need the same answer? (Phase 11)

### §27.1 Historical composition

- SESSION 251 dogfood: **both directions** exercised. The commit body cites 306-words-fit-word-budget-but-170s-actual (**too long**) as the motivating regression AND under-target (**too short**) as the primary tested convergence case.
- SESSION 263 audit: exclusively **compression**. Both dogfooded compositions were compressed on retry. This is the only prior corpus with detailed *semantic* analysis of the corrective pass.
- SESSION 270: exclusively **expansion**. All five specimens had first passes below `raw_min`; all retries were expansion.

### §27.2 Semantic properties of the two directions

**Compression** ("here's a good long draft; make it shorter"):
- Natural human-editor operation. Model can preserve strong sentences and remove filler.
- Risk: strips connective tissue that reads as character voice (SESSION 263 §6.5 finding).
- Passing Draft A back would let the model choose *which* sentences to keep — more likely to preserve the good work.

**Expansion** ("here's a good short draft; make it longer"):
- Less natural. Model must invent new material.
- Current architecture: model is told to expand from §1 knowledge chunks. Under minimal audience directives this pulls raw §1 vocabulary (SESSION 271 Slice 1 evidence).
- Passing Draft A back might invite the model to *interleave* new material with existing sentences — closer to how a writer expands a draft in practice.

### §27.3 Verdict

**Compression and expansion may have DIFFERENT optimal strategies.** Compression especially benefits from having Draft A in context (the "which sentences to keep" decision requires seeing them). Expansion arguably benefits similarly, but the mechanism differs (interleave vs prune).

Any revision experiment should **evaluate both directions independently.** SESSION 270 evidence covers expansion only; SESSION 263 evidence covers compression only. Neither has been paired against a revision-style control.

---

## §28. Design classification (Phase 12)

**Classification: C — MINIMAL IMPLEMENTATION / LOCAL OPTIMUM (with a bounded B qualifier).**

Reasoning:

- The SESSION 251 retry mechanism was demonstrably the *smallest empirically-effective* solution to the numeric-compliance problem. The commit body explicitly quantifies why the *phrasing* was chosen (explicit character ceilings > soft language). It does NOT explicitly reason about preservation semantics vs regeneration semantics.
- Alternative retry semantics (options B, C, F in §20) do not appear anywhere in commit messages, durable docs, or comments. Absence is not proof of rejection, but the strong reading is: preservation-across-retry was *not part of the requirement*.
- SESSION 253 extraction preserved the machinery verbatim — no reconsideration of retry semantics; the extraction problem was different (giving `talking_head` + AI-topic + non-chunked callers the same gate).
- SESSION 262 added first_pass observability without reasoning about synthesis reuse; the design frame was *audit trail*.
- SESSION 263 audit **did** identify the compression amplifier problem for character voice but scoped it as a future revision opportunity (line 853), unactioned.

The "**local optimum**" classification is *not* pejorative. The design solved its problem well within its scope. SESSION 270 audience-aware performance and SESSION 263 compression-artefact audits both surfaced a limitation that the SESSION 251 design was not intended to guarantee against. That's an evolution-of-requirements story, not a design mistake.

The qualifier **B — DELIBERATE FOR ORIGINAL SCOPE** is defensible for the empirically-driven parts (character-based gating over word-based; explicit character ceilings over soft language). Those were deliberate. The regeneration-vs-revision axis was not.

**NOT chosen:**
- A (DELIBERATE DESIGN) — no historical evidence anyone consciously chose regeneration OVER revision.
- D (ACCIDENTAL / INHERITED) — the design was intentional in its scope; it just did not survey the alternative that later evidence would make interesting.
- E (INTENT NOT RECOVERABLE) — intent is partly recoverable: SESSION 251 + SESSION 253 + SESSION 262 commit bodies are explicit about their goals. The un-recoverable part is only "why not the alternative" — and even there, the strong reading is "it was not on the design surface at the time."

---

## §29. Prior art we already had — SESSION 263

`docs/design/PATCH_RIVET_RUNTIME_CONTENT_ARCHITECTURE_AUDIT_SESSION_263.md` §6.5 (dated Aug 17, 2026, dialogue lane, `_dialogue_over_length_hint`):

> *"The corrective compression pass IS an active amplifier. The first-pass versions of both dogfoods are meaningfully more watchable than the corrective versions. Compression's mechanism (strip second/third clauses, drop decorative language, keep the beat) reliably converts a Rivet turn ... into ... same K2 grounding, different reading effect."*
> *"The compression hint explicitly *preserves* 'conversational causality; the scene's arc; the ending payoff' and *removes* 'decorative language.' A Rivet turn whose 'decorative language' IS the connective tissue between K2 concepts loses exactly the tissue that made it read as conversation. Compression is doing what it was told; the K2 content is what determines what survives."*

Recommended fix (line 853): *"a compression-hint revision that preserves imperative→observation conversion under compression."* — unactioned.

**SESSION 271 Slice 2 is not the first observation of this class of failure.** The same architectural feature (regeneration-not-revision) was already exposing character-voice preservation weakness in the **dialogue lane under compression** four sessions before SESSION 270 exposed audience-vocabulary preservation weakness in the **solo_scene lane under expansion**. Two independent lanes (`duration_contract` and `dialogue_synthesis`), two failure modes (character voice, audience vocabulary), two correction directions (compression, expansion), same underlying architectural cause.

Correctly framed: this is a **general corrective-pass invariance** question that pre-dates the audience experiment. Slice 1's classification (§12 of the Slice 1 section: "CORRECTIVE-PASS INVARIANCE (bounded), design gap not a bug") is validated by the prior art.

---

## §30. Product-context reframing (Phase 15)

SESSION 270's central question — *"Can Character OS change who Patch is talking to without changing who Patch is?"* — was the trigger for finding the corrective-pass behaviour. But the underlying mechanism is not audience-specific:

- The duration correction machinery is used by every audience-agnostic solo_scene render, every long_form_ad, every dialogue_scene.
- The regeneration semantics affect every transformation whose only trace was in the first-pass output — not just audience vocabulary.
- SESSION 263 documented the compression variant for character voice, months before audience experiments.

**Therefore this finding belongs conceptually to GENERAL SCRIPT SYNTHESIS / DURATION CORRECTION, not to AUDIENCE ARCHITECTURE.** The audience experiment is what exposed the mechanism; it is not the mechanism.

If any future architectural work touches this area, the correct labelling is *"corrective-pass invariance across script synthesis"*, and any documentation should reference:
- SESSION 251/253 as design origin
- SESSION 262 as observability foundation
- SESSION 263 §6.5 as first documented character-voice manifestation (compression, dialogue)
- SESSION 270 as first documented audience-vocabulary manifestation (expansion, solo_scene)
- SESSION 271 as source-level mechanical audit + design archaeology

---

## §31. Should Q-270-15a still come next? (Phase 13)

**Verdict: NO — Q-270-15a should not come next.**

Reasoning:

- Slice 1 recommended Q-270-15a (adding an explicit vocabulary-preservation clause to the audience directive) as the smallest instruction-side test.
- Slice 2 archaeology reveals the underlying architecture is a general-purpose regeneration mechanism that predates audience awareness by 19 sessions. It has already been documented (SESSION 263) as producing character-voice preservation weakness in the dialogue lane under compression.
- Q-270-15a would test whether a stronger audience directive can compensate for regeneration semantics *only in the audience case*. It leaves the general mechanism unchallenged.
- The more informative next experiment is the one that tests the underlying architecture, because it discriminates between two hypotheses that Q-270-15a alone cannot:
  - H·A: fresh regeneration is fine; the audience directive just needs to be stronger.
  - H·B: fresh regeneration is the mechanism; preserving first-pass semantics requires giving the model the first-pass text.
- If H·B is confirmed, the mechanism generalises to character voice, metaphor, brand voice, and any other transformation whose only trace was in the first-pass output. This affects the whole product, not just the audience feature.

**Recommended path forward: Q-270-15c — Draft-A-included revision experiment.**

---

## §32. Q-270-15c — smallest falsifiable revision experiment (Phase 14, DO NOT execute)

*Design outline only; no implementation, no render.*

### §32.1 Falsifiable question

*"Does passing the first-pass draft back to the corrective retry (with an instruction to preserve successful properties and only revise for length) preserve audience-specific vocabulary transformations that the current regeneration architecture loses?"*

### §32.2 Control vs experiment

| Variable | CONTROL (current) | EXPERIMENT (revision) |
|---|---|---|
| Substrate (Universe / Episode / Patch / operator_topic / knowledge / memory / Writing Contract) | identical | identical |
| audience_hint | minimal directive (e.g. `AUDIENCE: general adults with no technical background who are new to AI agents.`) | identical |
| Corrective-pass architecture | regeneration + `_expansion_hint` (current) | first-pass draft included in prompt + revised expansion hint that explicitly instructs preservation |
| Everything else | frozen | frozen |

### §32.3 What we would measure

For each specimen (both control and experiment):

- **Duration compliance:** does the accepted pass hit the ±20% acceptance band?
- **At-risk terminology:** count of raw-unexplained occurrences of `API`, `language model`, `state` in the accepted pass (from SESSION 270 §13.28 rubric). Extend as needed with `multi-step`, `database`.
- **Factual grounding:** verifier warnings on the accepted pass. (Slice 1 evidence: verified across all 5 SESSION 270 specimens.)
- **Character-voice preservation:** presence of Patch-shape markers (workshop metaphors, dry wit, first-person present-tense in-scene voice).
- **Metaphor / joke preservation:** are any first-pass ad-lib metaphors (e.g. `c3ff972d` first pass's *"handle a task across multiple steps"*) preserved verbatim in the experiment's accepted pass?
- **New unsupported claims:** does revision introduce any facts not in §1?
- **Cost / tokens:** input tokens delta between control and experiment.
- **Number of attempts:** control uses `attempt_count = 2` by construction; experiment same. If experiment converges without retry, that itself is informative.

### §32.4 What discrimination we'd get

- Experiment closes the at-risk terminology gap AND preserves audience adaptation AND stays factually grounded → **revision architecture is directionally better; broader engineering slice becomes worth considering.**
- Experiment closes the gap but introduces unsupported claims → **revision helps preservation but weakens factual discipline; hybrid design needed.**
- Experiment preserves audience vocabulary but doesn't hit duration → **prompt-level revision instruction needs tuning; not architectural.**
- Experiment behaves the same as control on terminology → **regeneration was not the mechanism; H·A wins; return to Q-270-15a.**

### §32.5 Scope discipline

- ONE render, same substrate as SESSION 270 (`c3ff972d` or `9880eb93` — both had clean first passes with regressed corrective passes).
- Requires a small experimental branch of `synthesize_with_duration_gate` OR a temporary in-worker patch OR (safest) a separate experimental function that the operator can invoke by env var, mirroring the SESSION 270 audience-hint plumbing pattern.
- **Do not modify the production corrective_hint or `_expansion_hint`.** Any experimental machinery must be transient, env-gated, and off by default — same discipline as SESSION 270 `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT`.
- Do not bump the Writing Contract.
- **Do not execute without explicit operator authorisation.**

### §32.6 If Q-270-15c cannot be scoped this small

Fallback: an even smaller pre-experiment unit test. Confirm mechanically that a modified `_synthesize` closure accepting a `previous_draft` kwarg produces different LLM output when the draft is included vs when it isn't. That would be pure source-level exploration; no paid render.

---

## §33. What remains unknown

- Why SESSION 251 specifically chose the "REWRITE THE SAME NARRATIVE" wording (design intent), given the model never had the narrative. Best inference: natural-language framing for narrative continuity, not a promise about context. Not proven.
- Whether the SESSION 263 §6.5 compression-hint revision recommendation was actively deprioritised or simply superseded by other SESSION 264-269 priorities (memory retrieval, story mode, audience research). Not proven.
- Whether the empirical "explicit ceilings work; soft language doesn't" finding from SESSION 251 was tested only in the fresh-regeneration frame or whether soft language failed in a revision frame too. Best inference: only tested in fresh-regeneration. Not proven.
- The stochastic variance floor on regeneration for character-voice preservation across passes (SESSION 263 §6.5 evidence is qualitative; no quantitative baseline exists). Not measured.
- Whether the dialogue lane and solo_scene lane should eventually share a common corrective-pass abstraction OR remain independent (they currently share nothing but the shape of the corrective-hint text). Unresolved.

---

## §34. What was NOT changed in Slice 2

- No production code touched.
- No prompts touched.
- No tests added or modified.
- Corrective_hint wording unchanged.
- Audience_hint wording unchanged.
- Writing Contract unchanged.
- No render fired.
- `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` remains unset.
- No schema / migration touched.
- NarrativeMemory pool unchanged (still 14 active + 1 archived per SESSION 270 §14.4).
- Slice 1 findings preserved verbatim; Slice 2 appended as a clearly separated section.

---

## §35. Slice 2 commit + push record

- Slice commit SHA: `623118e` — `docs(session-271): Slice 2 — duration-correction design archaeology`.
- Push: `e66aa5e..623118e main -> main` (successful).
- Local `main == origin/main == 623118e` verified.
- Working tree at slice close: clean.

---

**End of SESSION 271 Slice 2. STOP condition reached. Design archaeology complete; no engineering slice executed. Awaiting Chris + ChatGPT review before any code change or render.**
