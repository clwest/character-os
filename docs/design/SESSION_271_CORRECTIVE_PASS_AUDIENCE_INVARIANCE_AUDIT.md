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

---

# SESSION 271 — SLICE 3 · Q-270-15c Corrective-Revision Experiment (Phase 1 — plumbing ready for dogfood)

Slice 3 implements the smallest transient mechanism authorised by Chris + ChatGPT to test the Slice 2 hypothesis: whether passing Draft A back to the corrective retry preserves the successful properties of the first pass under expansion-only conditions. Env-gated, default OFF, expansion-only, scoped to `duration_contract` (no dialogue touch, no schema, no UI, no Writing Contract bump). Phase 1 covers implementation, tests, activation instructions. Phase 2 (evidence capture + interpretation + cleanup) follows the operator dogfood render.

---

## §36. Phase 1 orientation

| Check | Value at Slice 3 open |
|---|---|
| HEAD before Slice 3 | `2f7df07c925fbc315d05f734fd590defb4e9b235` (Slice 2 SHA-record commit) |
| Local `main == origin/main` | ✅ both at `2f7df07` |
| Working tree | ✅ clean at start; source + test + doc modifications live only in this slice |
| `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` (SESSION 270) | ❌ not set at slice open (activated after Q-270-15c plumbing is in place — see §41) |
| `CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT` (SESSION 271 Q-270-15c) | ❌ not set at slice open (activated after commit) |
| `WRITING_CONTRACT_VERSION` | `5` (unchanged) |
| NarrativeMemory pool | expected 14 active + 1 archived (unchanged since SESSION 270 §14.4; not re-queried during Phase 1) |
| Postgres | not consulted during plumbing slice; tests use the test-DB clone via `pytest.mark.django_db` |

---

## §37. Q-270-15c falsifiable question

*"When Draft A is already good in identity, factual grounding, story intent, and audience adaptation but fails ONLY the duration gate (expansion path), does giving Draft A back to the writer and asking it to revise for duration preserve those successful properties better than the current fresh-regeneration corrective path?"*

Scope guards (Slice 3):

- Expansion path only. Compression path stays canonical even under the flag (SESSION 263 §6.5 is a separate open question).
- Solo/long-form only. Dialogue lane untouched.
- Default OFF. Env unset ⇒ canonical behaviour byte-behaviour-equivalent to pre-SESSION-271.
- Transient. Removal plan documented in the module docstring (`_CORRECTIVE_REVISION_ENV`).
- No Writing Contract bump. No schema. No UI. No SESSION 262 observability changes needed — `Composition.first_pass_synthesis` / `corrective_hint` / `corrective_pass_synthesis` already store the evidence needed for post-hoc audit under either code path.

---

## §38. Source seam — smallest change

Three files touched. No other source file changes.

### §38.1 `shell/character_os/script_synthesis.py`

New optional keyword-only parameter `previous_draft: str | None = None` threaded through:

- `_assemble_task_message` (line 638). When truthy after `.strip()`, emits a new `PREVIOUS DRAFT TO REVISE (research plumbing — this is the prior attempt at this scene, provided as a source draft to revise rather than a truth authority; Factual Basis still governs truth per the PRECEDENCE RULES):\n<verbatim draft>` block inside §5 HARD CONSTRAINTS, positioned BEFORE the CORRECTIVE HINT and AUDIENCE DIRECTIVE blocks. Framing explicitly denies §1 truth authority per PRECEDENCE rule 1.
- `_call_responses_api` (line 533). Forwards to `_assemble_task_message`.
- `build_render_brief` (line 288). Forwards to `_call_responses_api`. Docstring updated with Q-270-15c note.

Why in this file: Draft A must be emitted with an explicit label (per operator brief) — the cleanest containment is a new labelled block at the `_assemble_task_message` layer, matching the SESSION 270 audience-hint precedent. Default `None` preserves byte-behaviour equivalence for every existing caller.

### §38.2 `shell/character_os/duration_contract.py`

- `import os` added (required for env-var read).
- New module-level constant `_CORRECTIVE_REVISION_ENV = "CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT"` + helper `_corrective_revision_experiment_active()` — whitespace-only treated as inactive, same discipline as SESSION 270 `_resolve_solo_audience_hint`. Both exported via `__all__` so tests can address them without importing private helpers.
- New function `_experimental_expansion_revision_hint(...)` — compact expansion hint that references the `PREVIOUS DRAFT TO REVISE` block and instructs revision-not-regeneration. Deliberately short (~600 chars, comparable to canonical `_expansion_hint`) so the variable under test is *Draft A visibility*, not prompt bloat. Does NOT mention `API` / `language model` / `state` / specific vocabulary — per operator brief, no answer coaching.
- `_synthesize` closure signature extended with keyword-only `previous_draft: str | None = None`. Default None preserves canonical byte-behaviour on every invocation that does not pass it.
- Expansion branch (line ~590) now conditional on `_corrective_revision_experiment_active()`:
  - **Experiment OFF (default):** uses canonical `_expansion_hint`, calls `_synthesize(hint)` — byte-behaviour-equivalent to pre-SESSION-271.
  - **Experiment ON:** uses `_experimental_expansion_revision_hint`, calls `_synthesize(hint, previous_draft=first_pass_brief)`. Logs a distinctive `SESSION 271 Q-270-15c expansion revision retry (experiment ACTIVE) ...` line with a removal reminder.
- Compression branch: logs a `compression retry — experiment flag is set but compression path stays canonical (expansion-only scope)` line if the flag is set; otherwise silent. Always canonical corrective_hint, never `previous_draft`.

### §38.3 `shell/apps/compositions/tests/test_session271_corrective_revision.py` (NEW, 20 tests, 481 LOC)

Covers the 10 invariants from the operator brief plus 4 slice non-interference guards:

1. Env-gate helper (4 tests): name stable, inactive-by-default, whitespace-only inactive, active-when-set.
2. `_assemble_task_message` plumbing (5 tests): absent/None/whitespace omits block; non-empty emits labelled block; coexists with opener + corrective_hint + audience_hint; `build_render_brief` signature has kwarg; `synthesize_with_duration_gate` signature deliberately does NOT (env-gated internally).
3. Experiment OFF byte-stability (2 tests): expansion retry omits `previous_draft`, canonical hint fingerprint intact; first pass never receives `previous_draft`.
4. Experiment ON expansion behaviour (5 tests): corrective receives Draft A verbatim + experimental hint; first pass never receives Draft A; audience_hint reaches both passes byte-identically; compression path stays canonical; retry count still bounded to 2.
5. Prompt containment (1 test): end-to-end through `build_render_brief` with stubbed OpenAI — Draft A + label appear only after §5 header; specimen fingerprint substrings absent from §1/§2/§3/memory pre-§5 region.
6. Slice non-interference (3 tests): Writing Contract still v5; dialogue `synthesize_dialogue` has no `previous_draft` kwarg; dialogue module source contains no `previous_draft` / `PREVIOUS DRAFT TO REVISE` string.

### §38.4 What was NOT changed

- `shell/apps/compositions/primitives/avatar_speech.py` — untouched. `synthesize_with_duration_gate` handles the experiment internally; the primitive continues to call it with the same signature.
- `shell/character_os/dialogue_synthesis.py` — untouched.
- `shell/character_os/writing_contract.py` — untouched. Contract v5 stamped by every accepted Composition.
- `shell/apps/compositions/models.py` — untouched. SESSION 262 observability fields already capture the needed evidence.
- No SPA UI.
- No migrations.
- No schema.
- No new dependencies.

---

## §39. Test results

Command: `set -a && . ../.env && set +a && ../.venv/bin/pytest apps/compositions/tests/test_session271_corrective_revision.py <adjacent suites> --tb=short`

| Suite | Result |
|---|---|
| `test_session271_corrective_revision.py` (NEW) | **20 passed / 0 failed** |
| `test_session270_audience_hint.py` | 17 passed (SESSION 270 invariants preserved) |
| `test_duration_contract_talking_head.py` | 38 passed (SESSION 251/253 duration-gate invariants preserved) |
| `test_session262_composition_observability.py` | 23 passed (per-attempt provenance preserved) |
| `test_talking_head_memory_lane.py` | 19 passed (SESSION 269 memory-lane preserved) |
| `test_session253_character_voice_prompt.py` | 32 passed (SESSION 253 §2 Character Voice preserved) |
| `test_writing_contract_solo_scene.py` | 14 passed (SESSION 269 §15 solo_scene contract preserved) |
| `apps/compositions/tests -k "dialogue"` | 171 passed (dialogue lane fully untouched) |

**Total: 334 tests green across the plumbing suite + all adjacent regression suites. Zero failures.**

Diagnostics: two Pyright warnings pre-existing (`script_synthesis.py:592` `client.responses` — SDK stub mismatch on the OpenAI Responses API; `script_synthesis.py:48` `merged_avoid_phrases` unused import). Two Pyright warnings on the new test file (`create_user` dynamic attribute, `_FakeMemory` type-narrower mismatch — same pattern as SESSION 270 audience-hint test file). None are runtime failures.

---

## §40. Prompt-shape delta between control and experiment (documentation aide)

For clarity when Chris + ChatGPT read the eventual evidence. Under identical substrate + audience_hint:

**CONTROL** (`CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT` unset — canonical):

```
=== SECTION 5 — TASK ===
TOPIC: <operator_prompt>
HARD CONSTRAINTS ...:

CORRECTIVE HINT (previous attempt feedback — apply this):
Your previous draft was NNN characters (WWW words, estimated ~SSs of speech). Target is TTs.
REWRITE THE SAME NARRATIVE ABOVE MMM CHARACTERS ...
Preserve the central arc (...), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.

AUDIENCE DIRECTIVE (research plumbing — apply as a performance instruction; adapt HOW the character communicates ...):
AUDIENCE: general adults with no technical background who are new to AI agents.

Write the spokesperson's spoken script for this task. Plain spoken English — this becomes voiceover.
```

**EXPERIMENT** (`CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=1`):

```
=== SECTION 5 — TASK ===
TOPIC: <operator_prompt>
HARD CONSTRAINTS ...:

PREVIOUS DRAFT TO REVISE (research plumbing — this is the prior attempt at this scene, provided as a source draft to revise rather than a truth authority; Factual Basis still governs truth per the PRECEDENCE RULES):
<first_pass_brief verbatim, ~600-900 chars typical>

CORRECTIVE HINT (previous attempt feedback — apply this):
Your previous draft was NNN characters (WWW words, estimated ~SSs of speech). Target is TTs.
REVISE THE PREVIOUS DRAFT (above, labelled PREVIOUS DRAFT TO REVISE) to reach at least MMM characters ...
Preserve the previous draft's meaning, voice, audience fit, arc, and factual grounding. Change only what is necessary to meet the length target. Add supporting detail from the knowledge chunks where needed to expand; do not replace successful wording that already works. Factual Basis still governs truth — do not preserve any claim in the previous draft that conflicts with the Factual Basis. Do not add a second closing invitation. Do not invent facts not present in the knowledge chunks.

AUDIENCE DIRECTIVE (research plumbing — apply as a performance instruction; adapt HOW the character communicates ...):
AUDIENCE: general adults with no technical background who are new to AI agents.

Write the spokesperson's spoken script for this task. Plain spoken English — this becomes voiceover.
```

**Only these three things change on the corrective call**:
1. New `PREVIOUS DRAFT TO REVISE` block precedes `CORRECTIVE HINT`.
2. `CORRECTIVE HINT` swaps `REWRITE THE SAME NARRATIVE ABOVE M CHARS ...` for `REVISE THE PREVIOUS DRAFT (above, labelled ...) to reach at least M chars ... Preserve the previous draft's meaning, voice, audience fit, arc, and factual grounding.`
3. AUDIENCE DIRECTIVE remains byte-identical to the control (this is the SESSION 270 closure invariant preserved).

Every other prompt component — §1 Factual Basis (chunks + memory), §2 Character Voice, §3 Brand Voice, §4 Writing Contract v5, PRECEDENCE RULES, TOPIC, final "Write the spokesperson's..." line — is byte-identical between control and experiment.

---

## §41. Activation procedure

**Follow this exact sequence.** Do NOT skip proofs.

1. **Verify plumbing commit is on HEAD.** (See §43 for SHA.)
2. **Stop the current Celery worker.** From the repo root:
   ```
   pkill -f "celery -A character_os worker" || true
   ```
3. **Confirm no worker alive.** `pgrep -f "celery -A character_os worker"` returns empty.
4. **Export BOTH env vars** in the same shell before restarting:
   ```
   export CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT='AUDIENCE: general adults with no technical background who are new to AI agents.'
   export CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=1
   ```
   The SESSION 270 audience env var carries the Q-270-13 nontechnical-adult directive verbatim (`hint_chars=79`). Both flags together produce the intended Q-270-15c specimen.
5. **Restart the canonical local-real worker** (audience env var flows in because it lives in the parent shell environment):
   ```
   bash scripts/start-local-real.sh
   ```
   The script re-launches Django + media-engine + Celery + Vite. Only the worker matters here; the others are stateless w.r.t. the experiment flag.
6. **Proof — env vars visible to the new worker.** Grab the worker PID and inspect:
   ```
   PID=$(pgrep -f "celery -A character_os worker" | head -1)
   ps eww "$PID" | tr ' ' '\n' | grep CHARACTER_OS_
   ```
   Both lines must appear:
   ```
   CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT=AUDIENCE: general adults with no technical background who are new to AI agents.
   CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=1
   ```
7. **Proof — resolvers report active** (within the same worker environment; run via `manage.py shell`):
   ```
   from apps.compositions.primitives.avatar_speech import _resolve_solo_audience_hint
   from character_os.duration_contract import _corrective_revision_experiment_active
   from unittest.mock import MagicMock
   assert _resolve_solo_audience_hint(MagicMock(params={})).startswith("AUDIENCE:")
   assert _corrective_revision_experiment_active() is True
   ```
8. **Service health probes** (canonical set — see SESSION 270 §13.7):
   - Django: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8010/admin/` → `302`
   - media-engine: `curl -s http://localhost:8001/health` → `{"status":"ok",...,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}`
   - Vite: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5174/` → `200`
   - Celery: `celery -A character_os inspect ping` → `pong / 1 node online`

If any proof fails, **abort** and return the failure to Chris + ChatGPT before dogfood.

---

## §42. Chris's single dogfood action

Once activation proofs pass:

1. Open the SPA at http://localhost:5174/.
2. Navigate to the existing Universe **Patch' Workshop** (ID `56d16b63-652e-4f54-bc7e-39114bbfc4c5`).
3. Open the existing Episode **Patch does research on AI Agents** (ID `2b6087d2-cbe3-47c4-a7ef-7d7625231472`).
4. Create a new solo scene:
   - Cast: **Patch only** (spokesperson `7fad8172-cd39-4bbe-85e0-ed705d900645`).
   - Recipe: **talking_head** → will resolve to `solo_scene` per SESSION 269 §15.
   - Target duration: **90 seconds**.
   - Workspace knowledge: **ON**.
   - Opener: **blank**.
   - Fact-check mode: **warn**.
   - Do NOT type an audience directive into any operator surface — the env var supplies the audience directive. `step.params.audience_hint` remains empty.
5. Click **Render**.
6. Wait for the composition to complete (or fail).
7. Return to Claude with:
   - The Composition ID (UUID).
   - Whatever the SPA displays — accepted script text if the render succeeded, or the failure/rejection detail if not.
   - Note whether the corrective retry appears to have fired (visible in the SPA if a "corrective pass" section exists on the composition detail; Claude will also inspect from Celery logs + persisted `synthesis_attempt_count`).

**Do NOT** edit the generated script. **Do NOT** render a second time. **Do NOT** promote NarrativeMemory. **Do NOT** run any other experiment in parallel.

If the first pass naturally lands inside the acceptance window and no corrective retry fires, that is the `NO RETRY — EXPERIMENT INCONCLUSIVE FOR Q-270-15c` outcome — return the Composition ID anyway; Claude will interpret and return to Chris before deciding whether a second controlled render is warranted (do NOT auto-render another).

---

## §43. Pre-registered PASS / FAIL criteria (frozen BEFORE render)

Twelve criteria, each classified as PASS / FAIL / AMBIGUOUS, with source of judgment (runtime-objective RO vs interpretive judgment IJ). All criteria evaluated against the NEW Q-270-15c corrective-revision Composition; historical `c3ff972d` is external reference.

| # | Criterion | RO / IJ | Notes |
|---|---|---|---|
| 1 | **Duration gate succeeds.** Accepted script inside `[72, 108]` s and `[1080, 1620]` chars. | RO | Persisted on Composition. |
| 2 | **Patch identity preserved** in the accepted output. Workshop-native voice, dry wit, first-person present-tense in-scene, no talk-down markers. | IJ | Comparable to c3ff972d §13.24.11.4 criterion 1. |
| 3 | **Story intent preserved.** Same Episode operator_topic; no story progression (Patch still researching, not acting on results). | RO + IJ | Substrate control same as SESSION 270. |
| 4 | **Factual grounding preserved.** Verifier warnings are proper_noun false-positives (Q-270-16 class) OR zero warnings; no new unsupported claims. | RO + IJ | Composition.verification_warnings + interpretive review of any unusual assertions. |
| 5 | **NarrativeMemory semantics preserved.** Same memory row `8d4fdfec` retrieved; memory used elliptically, not recited. Pool remains 14 + 1. | RO + IJ | Composition.memory_ids + interpretive review of memory citation. |
| 6 | **Nontechnical adult audience adaptation remains strong** in the accepted output. Register + metaphor family still workshop-native + conversational. | IJ | Comparable to c3ff972d §13.24.11.2 register sub-finding (which was PASS-strong). |
| 7 | **Draft-A-accessible terminology preserved or remains equally accessible.** Anything the first pass translated (e.g. *"keep track of what happened"*, *"handle a task across multiple steps"*, *"call other software"*) should either survive verbatim into the accepted pass OR be replaced by another equally accessible translation. | IJ | Central Q-270-15c criterion. |
| 8 | **No major new unexplained technical terminology introduced merely to reach duration.** Adjacent to SESSION 270 §13.28 at-risk set: `API` / `language model` / `state` / dense unexplained enumeration. Zero raw unexplained terms is the strongest PASS; ≤1 with immediate contextual scaffolding is AMBIGUOUS; ≥2 raw is FAIL. | RO + IJ | Uses SESSION 270 §13.28 methodology. |
| 9 | **Recognizably the SAME narrative as Draft A.** Character voice arc, opening beat, key metaphor family, main comparison (agent vs one-response responder), closing invitation posture all recognizable. Not a full independent regeneration. | IJ | Central Q-270-15c criterion. |
| 10 | **No meaningful unsupported claim added.** No new named entity / product / statistic beyond what §1 Factual Basis supports. | RO + IJ | Verifier check + interpretive review. |
| 11 | **Added material feels like EXPANSION of Draft A, not replacement of Draft A.** Insertions extend existing sentences, add supporting sentences between existing beats, or elaborate on already-present concepts. Wholesale substitution counts as FAIL on this criterion. | IJ | Central Q-270-15c criterion. |
| 12 | **Final output is at least as usable as the canonical `c3ff972d` accepted output** on overall quality (identity + register + story + factual + memory + audience), while improving on corrective invariance vs Draft A. This is the operator-facing product check: revision must not make things worse. | IJ | Comparison to `docs/design/session_270_experiment_data/04_composition_c3ff972d_evidence.json::accepted_script`. |

**Q-270-15c overall verdict rubric:**
- **A — REVISION CLEARLY BETTER**: criteria 1 + 2 + 3 + 4 + 5 + 9 + 10 + 11 + 12 PASS, AND criteria 6 + 7 + 8 strictly improve over the historical `c3ff972d` corrective pass on at-risk terminology.
- **B — REVISION HELPS BUT HAS COSTS**: criteria 7 + 8 improve, but one of {2, 4, 6, 10, 11, 12} degrades.
- **C — NO MATERIAL IMPROVEMENT**: revision output behaves comparably to historical `c3ff972d` on criteria 7 + 8 (no meaningful delta either way).
- **D — REVISION WORSE**: revision makes any of criteria 1, 4, 10, or 12 worse; or introduces repetition/anchoring/filler flagged as FAIL under criterion 11.
- **E — INCONCLUSIVE**: no corrective pass fired (`synthesis_attempt_count == 1`), OR specimen lacks discriminating evidence.

Pre-registering these criteria before Chris renders keeps interpretation honest. Do NOT modify this table after evidence lands.

---

## §44. What Phase 2 will produce

After Chris returns the Composition ID:

1. **Activation validity proofs**: Celery log line for the new Composition contains the `SESSION 271 Q-270-15c expansion revision retry (experiment ACTIVE)` marker (proves the experiment fired); worker env-var proof from `ps eww`; both env vars visible on the render worker.
2. **Evidence sidecar** at `docs/design/session_271_experiment_data/01_composition_<uuid>_q270_15c_evidence.json` following the SESSION 270 sidecar schema plus a new `q270_15c_revision_delta` section capturing:
   - Was `previous_draft` in the corrective prompt? (Proof from Celery log excerpt.)
   - First-pass script (verbatim from `Composition.first_pass_synthesis`).
   - Corrective revision script (verbatim from `Composition.corrective_pass_synthesis`, same as `accepted_script` when accepted).
   - Corrective hint text (verbatim from `Composition.corrective_hint`).
   - Per-criterion grading against §43.
3. **Historical comparison to `c3ff972d`**: side-by-side excerpts of the two accepted outputs on the same audience directive.
4. **Within-composition comparison**: first-pass excerpts vs revised excerpts on the SESSION 270 §13.28 at-risk terminology set.
5. **Verdict** using the §43 rubric.
6. **Cleanup**: env vars unset, worker restarted with canonical env, service health re-probed, resolver re-checked (both env vars ⇒ inactive, `_corrective_revision_experiment_active() == False`).
7. **Slice close commit** with the evidence sidecar + verdict + cleanup record.

Chris will hand off Composition ID before Phase 2 begins.

---

## §45. Slice 3 Phase 1 commit + push record

- Phase 1 slice commit SHA: `8112e57` — `feat(session-271): Q-270-15c corrective-revision experiment plumbing (Phase 1 — default OFF)`.
- Push: `2f7df07..8112e57 main -> main` (successful).
- Local `main == origin/main == 8112e57` verified.
- Working tree at Phase 1 close: clean.
- Files touched by Phase 1:
  - `shell/character_os/script_synthesis.py` — `previous_draft` kwarg on `build_render_brief` / `_call_responses_api` / `_assemble_task_message` + PREVIOUS DRAFT TO REVISE block emission
  - `shell/character_os/duration_contract.py` — `_CORRECTIVE_REVISION_ENV`, `_corrective_revision_experiment_active`, `_experimental_expansion_revision_hint`, env-gated expansion branch, compression-path canonical guard
  - `shell/apps/compositions/tests/test_session271_corrective_revision.py` — new 20-test suite (481 LOC)
  - `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` — Slice 3 sections §36-§45

---

**End of SESSION 271 Slice 3 Phase 1. STOP condition reached. Plumbing implemented, tested green (20+143+171 = 334 tests), documented. Awaiting Chris dogfood render before Phase 2.**

---

# SESSION 271 — SLICE 3 PHASE 2 · Composition 25467733 Forensic Inspection

Phase 2 forensics on the SPA-completed render Chris performed for Q-270-15c Trial 1. **Verdict: E — INCONCLUSIVE. The Q-270-15c revision code path did not execute because the worker environment did not contain either experiment env var — an ACTIVATION GAP, not a plumbing defect.** The composition is preserved as a bounded collateral data point on canonical baseline-shape behaviour, but is NOT a Q-270-15c specimen and does NOT answer the falsifiable question in §37.

Frozen evidence sidecar: `docs/design/session_271_experiment_data/01_composition_25467733_q270_15c_trial1_evidence.json`.

---

## §46. Composition 25467733 identity

| Field | Value |
|---|---|
| Short ID | `25467733` |
| Full UUID | `25467733-16d0-4d13-beef-ee1478aa3271` |
| Rendered | `2026-08-20 06:26:18 UTC` (created) → `06:26:32 UTC` (render dispatched) → `06:28:44 UTC` (task completed, 146.4 s wall) |
| Status | `completed` / `verification_status="verified"` |
| Writing Contract | `v5` (unchanged) |
| Template kind | `talking_head` → resolved to `solo_scene` (Episode-attached) |
| Universe | `Patch's Workshop` (`56d16b63-652e-4f54-bc7e-39114bbfc4c5`) |
| Episode | `Patch does research on AI Agents` (`2b6087d2-cbe3-47c4-a7ef-7d7625231472`) |
| Spokesperson | `Patch` (`7fad8172-cd39-4bbe-85e0-ed705d900645`) |
| operator_topic | `Patch does research on AI Agents` |
| Target duration | `90 s`; predicted `83 s`; actual asset `87.5 s` |
| Acceptance band | seconds `[72, 108]`; chars `[1080, 1620]` — WITHIN |
| Knowledge chunk IDs (5) | `3c5165ea`, `505acbba`, `b3c6e8ac`, `c24d1aa7`, `ed18e966` — IDENTICAL to c3ff972d + baseline retrieval |
| Memory row (1) | `8d4fdfec-add4-4505-8ade-b0f9e6d8aea6` — the workshop-agent-notes memory |
| synthesis_attempt_count | **2** |
| first_pass_synthesis chars | 840 |
| corrective_pass_synthesis chars | 1221 (= `synthesized_brief`) |
| corrective_hint chars | **656** ← canonical `_expansion_hint` shape |
| verification_warnings | `[{"kind":"tech_term","claim":"react","position":338}]` |
| cost | `20000` micros ($0.02, one Runway call) |

---

## §47. Activation reality check — worker environment inspection

Prior to grading anything, we verified whether the two experiment env vars actually reached the render worker.

### §47.1 Worker process inspection

- Worker PIDs currently alive: `69005`, `69009`, `69010`.
- Worker etime at Phase 2 forensics: `01:30:46` (booted ~2026-08-19 22:52 local, ~04:52 UTC).
- **Boot time exactly matches SESSION 270 §13.26 deactivation restart** (`Worker PID 69005 launched via canonical start-local-real.sh invocation with no env-var export`).
- Env-var inspection: `for pid in 69005 69009 69010; do ps eww "$pid" | tr ' ' '\n' | grep 'CHARACTER_OS_'; done` → **empty for all three PIDs**.

**Conclusion:** the worker that processed Composition 25467733 was the SESSION 270 deactivation-mode worker, running in canonical no-experiment configuration. Neither `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` nor `CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT` was in its environment.

### §47.2 Celery log inspection

`/tmp/character-os-celery.log` — search for experiment markers:

- `grep -nE 'SESSION 270|audience-hint|hint_chars|SESSION 271|Q-270-15c|CORRECTIVE_REVISION'` → **empty**.
- Only synthesis line for this composition: `synthesize_with_duration_gate expansion retry` (line 39). This is the CANONICAL log line (source: `duration_contract.py::synthesize_with_duration_gate` line ~615 in the OFF branch — `logger.info("synthesize_with_duration_gate expansion retry")`).
- The Q-270-15c experimental branch would have produced a very different, marker-rich log line: `synthesize_with_duration_gate SESSION 271 Q-270-15c expansion revision retry (experiment ACTIVE) sp=... previous_draft_chars=... — this is transient research plumbing; unset CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT to restore canonical fresh-regeneration behaviour`. **This marker is absent.**

### §47.3 Corrective hint text inspection

Persisted `Composition.corrective_hint` verbatim (656 chars):

```
Your previous draft was 840 characters (144 words, estimated ~58s of speech). Target is 81s.
REWRITE THE SAME NARRATIVE ABOVE 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 132 more characters to meet the minimum.
Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.
```

Starts `REWRITE THE SAME NARRATIVE` — this is the canonical `_expansion_hint`. The experimental hint would have started `REVISE THE PREVIOUS DRAFT (above, labelled PREVIOUS DRAFT TO REVISE) ...`. **The experimental hint text is absent.**

**Three independent proofs (env-var inspection + log marker + hint text fingerprint) all agree:** the Q-270-15c revision path did not execute on this render.

---

## §48. Q-270-15c Trial 1 verdict — E · INCONCLUSIVE

Per §43 rubric E: *"No corrective pass fired (`synthesis_attempt_count == 1`), OR specimen lacks discriminating evidence."*

**A corrective pass DID fire — but it was the CANONICAL fresh-regeneration corrective pass, not the experimental Q-270-15c revision pass.** The revision code path did not execute; Draft A was not passed to the corrective LLM call; the `PREVIOUS DRAFT TO REVISE` block did not appear in the assembled prompt. Therefore the specimen lacks discriminating evidence for the Q-270-15c question.

**§43 criteria that ARE scorable** (independent of the revision branch):

| # | Criterion | Result |
|---|---|---|
| 1 | Duration gate succeeds (87.5 s in [72, 108]) | PASS |
| 2 | Patch identity preserved | PASS |
| 3 | Story intent preserved (same Episode, no progression) | PASS |
| 4 | Factual grounding preserved (`react` flag is verifier false-positive, see §51) | PASS with bounded caveat |
| 5 | NarrativeMemory semantics preserved | PASS |
| 10 | No meaningful unsupported claim added | PASS |

**§43 criteria that MUST NOT be scored** (would misattribute canonical behaviour to the revision experiment):
- Criterion 6 (nontechnical adult audience adaptation) — **NOT APPLICABLE**: the audience env var was also not active, so this is not an audience-conditioned specimen.
- Criterion 7 (Draft-A-accessible terminology preserved) — **NOT SCORABLE**: revision did not execute.
- Criterion 8 (no new unexplained technical terminology from revision) — **NOT SCORABLE**: revision did not execute.
- Criterion 9 (recognizably same narrative as Draft A) — **NOT SCORABLE**: revision did not execute.
- Criterion 11 (added material feels like expansion of Draft A) — **NOT SCORABLE**: revision did not execute.
- Criterion 12 (at least as usable as c3ff972d accepted) — **AMBIGUOUS**: usability is comparable, but produced under baseline conditions, not audience-conditioned — not a valid comparison.

**Overall: E — INCONCLUSIVE. The Q-270-15c falsifiable question remains unanswered.**

---

## §49. Case classification — a new CASE C beyond the operator brief's A/B

The operator brief pre-registered two cases:

- **CASE A:** experiment active, first pass in tolerance → INCONCLUSIVE / NO RETRY.
- **CASE B:** experiment active, first pass failed duration, revision did not fire → plumbing defect.

The actual outcome is neither. It is:

- **CASE C (activation gap):** experiment was NOT active on the worker (env vars absent). First pass failed duration → canonical retry fired. Draft A was never in play.

This is not a code defect. Phase 1 tests validated the plumbing (20/20 Q-270-15c invariants green, including proof of Draft-A propagation when the env var is set). The gap is between commit + push (Phase 1 §45 = `8112e57` on `main`) and the render worker's process boot time. Since the worker process was the SESSION 270 deactivation restart (which pre-dates Phase 1 commit), the Phase 1 code loaded correctly (fresh Python imports on Celery task dispatch use the file on disk), but no code path referencing the env var was reached because `os.environ.get("CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT", "")` returned `""` in the worker's process environment.

**Root cause:** the §41 activation procedure was not executed before the dogfood render — the worker was never `pkill`ed and re-launched with the two env vars exported.

---

## §50. What Composition 25467733 IS useful for — bounded collateral

Since neither experiment was active, this composition is effectively a **repeat baseline-shape render on the SESSION 269 substrate**, not a Q-270-15c specimen and not a nontechnical-adult audience specimen. It nevertheless adds a bounded data point to the SESSION 270 §13.28 canonical-corrective pattern.

### §50.1 At-risk terminology within-composition delta

Method: SESSION 270 §13.28 rubric (case-insensitive substring match on `API`, `APIs`, `language model`, `state`, `multi-step`, `database`) plus `react` (K6.4-flagged).

| Term | First pass (840 chars) | Accepted (1221 chars) | Direction |
|---|---|---|---|
| `API` | 1 (at char 286: *"call APIs"*) | 1 (at char 291: *"call APIs"*) | STABLE |
| `APIs` | 1 | 1 | STABLE |
| `language model` | 0 | **1** (at char 420: *"A language model can tell you it has a plan."*) | **ADDED** |
| `state` | 0 | **1** (at char 327: *"keep state"*) | **ADDED** |
| `multi-step` | 1 (at char 317: *"multi-step task"*) | 1 (at char 304: *"handle multi-step tasks"*) | STABLE |
| `database` | 0 | 0 | STABLE |
| `react` | 0 | **1** (at char 338: *"react when something changes"*) | **ADDED (+ verifier flag)** |

**Direction:** +3 net (added `language model`, `state`, `react`). Baseline-shape corrective retry pulled more raw §1 terminology than the first pass — same pattern SESSION 270 §13.28 documented for baseline `2ef5ee7e` (3 → 6 at-risk terms).

### §50.2 Comparison table — 25467733 vs baseline vs c3ff972d

| Specimen | Audience directive active? | Q-270-15c revision active? | First-pass at-risk | Accepted at-risk | Direction |
|---|---|---|---|---|---|
| `2ef5ee7e` (SESSION 269 baseline) | NO | N/A (pre-SESSION 271) | 3 | 6 | +3 |
| `c3ff972d` (SESSION 270 Q-270-13 nontechnical adult) | **YES (79-char directive)** | N/A (pre-SESSION 271) | **0** | 5 | +5 (post-audience clean → §13.28 regression) |
| **`25467733` (SESSION 271 Q-270-15c Trial 1)** | **NO (activation gap)** | **NO (activation gap)** | 2 | 5 | +3 |

**Shape reading:** 25467733's shape sits between the baseline and c3ff972d, matching the "canonical no-audience corrective adds §1 vocabulary" direction rather than the "audience-clean first pass regressed by corrective retry" pattern. Consistent with 25467733 being a canonical render, not an audience-conditioned one.

### §50.3 What we cannot conclude

- We CANNOT strengthen the claim about first-pass audience-vocabulary stochasticity by comparing 25467733's first pass to c3ff972d's, because 25467733 had no audience directive. That comparison is baseline vs directive-active — informative about *whether an audience directive helps*, not about *directive stochasticity across runs*.
- We CANNOT conclude anything about Q-270-15c revision semantics.

### §50.4 What we CAN reinforce (bounded)

Composition 25467733 is a **third data point** on the SESSION 270 §13.28 canonical-corrective-pass direction: without audience conditioning, the canonical expansion retry consistently adds raw §1 terminology (baseline `2ef5ee7e`: +3; broad-adult first-pass-carried `0b3c1fc1`: stable; `9880eb93`: +1; `c3ff972d`: +5; now baseline-shape `25467733`: +3). The direction is now well-established for canonical retries.

---

## §51. The `react` verifier flag — Q-270-18 candidate

**Finding:** K6.4 verifier flagged the lowercase English verb `react` at position 338 (`"...keep state, and react when something changes around it."`) as `tech_term`.

The same script contains, all unflagged:
- `API` at position 291 (called out in SESSION 270 §13.28 as at-risk technical vocabulary)
- `APIs` at position 291
- `language model` at position 420
- `state` at position 327 (as a technical noun)
- `multi-step` at position 304

The verifier flagged the verb `react` but missed the objectively more technical terms `API`, `language model`, and `state`.

**Interpretation:** the K6.4 `tech_term` list appears to contain `react` — likely to catch the React JavaScript library — without a case discriminator. This is a false-positive class distinct from Q-270-16 (K6.4 `proper_noun` heuristic false-positives on sentence-initial capitalised tokens, SESSION 270 §13.24.11.5). Q-270-16 was about sentence-initial *"Sometimes"* / *"Proof"* / *"Obviously"* / *"Especially"* — those live in a different verifier code path (proper-noun heuristic vs tech-term list).

**Candidate open question label — Q-270-18:** *"K6.4 `tech_term` list — case sensitivity + coverage audit. Lowercase English verb `react` is flagged as `tech_term`; more technical terms (`API`, `language model`, `state`) in the same script are not. Suggests the list needs (a) a case discriminator for tokens whose lowercase form is common English, and (b) coverage expansion for genuinely technical terminology that is currently uncatalogued."*

**DO NOT** fix in any SESSION 271 slice. Bounded verifier-quality follow-up. NOT audience-related.

---

## §52. Patch identity + story-progression control

### §52.1 Patch identity (independent of audience-boundary reliability)

Even though the technical vocabulary is a poor match for the intended nontechnical-adult audience (which was never activated anyway), Patch's voice remains distinctively strong in the accepted output. Workshop-native markers include:

- *"anything with a chat box and a confident attitude"* — brand-critical humour
- *"handle multi-step tasks, keep state, and react when something changes around it"* — technically dense but delivered in a Patch-shape enumeration
- *"A language model can tell you it has a plan. An agent can potentially go do parts of the plan."* — Patch's characteristic clean contrast
- *"a very polite problem"* — signature Patch understatement
- *"becomes useful instead of just… enthusiastic"* — dry wit, first-person present-tense in-scene
- *"Tell me: what would you make an agent try first?"* — audience-facing invitation without patronising register

**Verdict: identity PASS.** Character-voice preservation and audience-vocabulary reliability are distinct dimensions. This composition scores strong on identity, weak on audience knowledge-boundary reliability — but the latter was not exercised (no audience directive was live).

### §52.2 Story control

- Same Episode row `2b6087d2` — no new Episode.
- Same `operator_topic` — no story-level drift.
- Story state: Patch still researching. The accepted script closes with *"Tell me: what would you make an agent try first?"* — a research-planning frame, not an action-taken frame. Patch has still not begun the Agent experiment.
- **Story-progression discipline preserved.**

### §52.3 Memory control

- Same memory row `8d4fdfec-add4-4505-8ade-b0f9e6d8aea6` retrieved.
- Memory usage in accepted script: *"I found my old workshop-agent notes again—the smaller experiment from before I gave it more context and it started making decisions about my projects."*
- Slightly less elliptical than c3ff972d's *"I've got enough notes now"* — closer to close-paraphrase — but still within the SESSION 269 §16.8 non-recital discipline (retrieved memory INFLUENCES the script rather than being quoted verbatim under a labelled framework heading).
- **No memory promotion.**

### §52.4 NarrativeMemory pool state (verified via manage.py shell)

Query: `NarrativeMemory.objects.filter(universe_id="56d16b63-...")` grouped by `status`.

| Universe | status | count |
|---|---|---|
| Patch's Workshop `56d16b63` | `remembered` | **14** |
| Patch's Workshop `56d16b63` | `archived` | **1** |

**Pool = 14 remembered + 1 archived = unchanged from SESSION 270 §14.4.**

Note: SESSION 270 shorthand used the word *"active"* for the `remembered` status value; both refer to the same pool state. The pool count is byte-stable across the entire SESSION 270 audience-experiment sequence + SESSION 271 Slice 3 Trial 1.

---

## §53. Audience-reliability dimension refinement

Slice 2 archaeology + Slice 3 Trial 1 activation gap together suggest a useful conceptual refinement:

- **Layer 1 — first-pass audience-directive reliability.** Does the audience directive (of a given length + shape) consistently establish an appropriate technical knowledge boundary in the FIRST synthesis? SESSION 270 evidence: **mixed under minimal directives**. `c3ff972d` and `9880eb93` achieved clean first passes; `0b3c1fc1` did not. Sample too small to characterise the distribution.
- **Layer 2 — corrective-pass audience invariance.** If the first pass DID achieve a clean audience boundary, does the corrective retry preserve it? SESSION 270 §13.28 documented this weakness (2 of 3 clean-first-pass specimens had at-risk terms reintroduced). SESSION 271 Slice 1/2 mechanically explained it (fresh regeneration + explicit "expand from knowledge chunks" clause + Draft A absent from the corrective context).

These layers can fail independently. A robust audience-vocabulary product would need BOTH:
- (a) a first-pass mechanism that reliably establishes the audience boundary, AND
- (b) a corrective-pass mechanism that preserves it under length-driven expansion.

Q-270-15c targets (b) directly and is orthogonal to (a). It remains the highest-information next experiment for layer 2. Q-270-15a-style stronger-directive experiments would target (a).

Composition 25467733 does not strengthen or weaken either layer's evidence, because neither mechanism was active.

---

## §54. What was NOT changed during Phase 2

- No production source touched. Slice 3 Phase 1 code (`shell/character_os/duration_contract.py`, `shell/character_os/script_synthesis.py`) unchanged. The Q-270-15c plumbing remains present + inactive by default.
- No test touched.
- Writing Contract remains `v5`.
- No schema / migration.
- No SPA UI.
- No render performed by Claude (only forensic reads).
- No new Composition created.
- No NarrativeMemory promotion. Pool remains 14 remembered + 1 archived.
- No env-var manipulation by Claude. Chris owns activation/deactivation state changes.
- No worker restart by Claude.

The only artefacts written in Phase 2 are:
- `docs/design/session_271_experiment_data/01_composition_25467733_q270_15c_trial1_evidence.json` (new evidence sidecar).
- Sections §46-§56 appended to this durable document.

---

## §55. Cleanup + activation-reactivation handoff for Chris

The Q-270-15c experiment plumbing is present on `main` (Phase 1 commit `8112e57`) but was never activated on the render worker for Trial 1. Because no experiment was live, **no cleanup is required from Claude's side** — the workers are already in canonical no-experiment mode.

If Chris + ChatGPT choose Recommendation A (§56) — one more natural controlled render with the experiment actually active — the following canonical activation procedure (repeated verbatim from §41) is what must be executed in Chris's shell, in order:

```
# 1. Kill the SESSION 270 §13.26 workers currently in canonical mode
pkill -f "celery -A character_os worker" || true
pgrep -f "celery -A character_os worker" && echo "STILL ALIVE — investigate" || echo "clear"

# 2. Export BOTH env vars in the SAME shell that will launch the worker
export CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT='AUDIENCE: general adults with no technical background who are new to AI agents.'
export CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=1

# 3. Launch canonical stack — the fresh worker inherits the env vars
bash scripts/start-local-real.sh

# 4. Proof — env vars visible to the NEW worker's process environment
PID=$(pgrep -f "celery -A character_os worker" | head -1)
ps eww "$PID" | tr ' ' '\n' | grep CHARACTER_OS_
#     ↑ MUST show both env vars. If empty, worker did not inherit.

# 5. Proof — Python-side resolvers report active
cd shell && DJANGO_SETTINGS_MODULE=character_os.settings ../.venv/bin/python manage.py shell <<'PY'
from apps.compositions.primitives.avatar_speech import _resolve_solo_audience_hint
from character_os.duration_contract import _corrective_revision_experiment_active
from unittest.mock import MagicMock
print("audience:", _resolve_solo_audience_hint(MagicMock(params={})))
print("revision_active:", _corrective_revision_experiment_active())
PY
# audience: AUDIENCE: general adults ...
# revision_active: True
```

If either proof fails, **abort** before dogfood.

If Chris + ChatGPT choose Recommendation C (§56), no activation is needed — the plumbing simply sits inert until removed or promoted in a future slice.

---

## §56. Decision-gate recommendation

**Recommend Option A — ONE MORE NATURAL CONTROLLED RENDER.**

Justification:

- Q-270-15c retains its full information value. The Slice 2 archaeology (§28 classification as C — MINIMAL IMPLEMENTATION / LOCAL OPTIMUM; §29 SESSION 263 prior art on the compression variant of the same class of failure) shows the underlying architectural question — *does giving Draft A to the corrective retry preserve first-pass semantic transformations?* — is the highest-value open question in this line.
- Trial 1 did not exercise the experiment at all. The plumbing tested green (20/20 invariants + 143 adjacent regressions + 171 dialogue) but never touched a live substrate. No evidence has been added FOR or AGAINST the falsifiable question.
- The activation gap has a documented, repeatable fix (§55).
- Repeating one controlled render on the same substrate with the activation procedure faithfully executed is the smallest, cheapest way to close the information gap. Same substrate as SESSION 270 `c3ff972d` (same Universe, Episode, spokesperson, target duration, knowledge, memory, verifier, contract), same audience directive, plus the Q-270-15c revision flag genuinely ON. Cost: one Runway render ≈ $0.02 + LLM tokens.
- Natural stochasticity remains a factor — Trial 2 might again produce a first pass that lands in tolerance and does not fire a retry. If that happens, the escalation path (Option B — deterministic non-production harness) becomes worth considering.

Do NOT recommend:

- **Option B (harness) NOT YET.** The natural-render approach has one honest attempt behind it; the failure was operational, not stochastic. One more natural attempt is the appropriate escalation step; the harness is warranted only if repeated natural attempts fail to exercise the retry.
- **Option C (drop) NOT.** No evidence has changed Q-270-15c's information value.
- **Option D (something else) NOT.** No unexpected runtime finding requires a different path.

**Chris + ChatGPT decide.** Do not execute Recommendation A without explicit authorisation.

---

## §57. Return-to-Chris index

Concise answers below; forensic evidence lives in §46-§56 + the sidecar.

1. Full UUID for Composition 25467733 → `25467733-16d0-4d13-beef-ee1478aa3271`.
2. Was Q-270-15c experiment active? → **NO** (`ps eww` on worker PIDs 69005/69009/69010 shows no env var; canonical log line + canonical hint text confirm the OFF branch fired).
3. Was audience experiment active? → **NO** (same worker environment; no `SESSION 270 audience-hint experiment ACTIVE` marker in Celery log).
4. `synthesis_attempt_count` → **2**.
5. Did corrective revision fire? → **NO — canonical `_expansion_hint` fired instead.**
6. Did Draft A reach a corrective call? → **NO.** `previous_draft` was not passed; `PREVIOUS DRAFT TO REVISE` block was not in the assembled prompt.
7. Q-270-15c Trial 1 verdict → **E — INCONCLUSIVE.**
8. If inconclusive, why exactly? → **Activation gap (CASE C).** Worker was the SESSION 270 §13.26 deactivation-restart worker (booted 2026-08-19 22:52 local); it was never killed + restarted with the two env vars exported after Phase 1 commit `8112e57` landed. Neither env var was in the worker's process environment.
9. What does 25467733 teach us about FIRST-PASS audience-vocabulary reliability? → **Nothing** — no audience directive was active. It teaches us about canonical baseline-shape corrective behaviour (+3 at-risk terms net), reinforcing SESSION 270 §13.28.
10. Comparison to `c3ff972d` first pass → **Not a valid comparison** — c3ff972d had a live 79-char audience directive; 25467733 had none. Any first-pass vocabulary difference is baseline-vs-directive-active, not directive stochasticity.
11. What happened with `react` verifier warning? → **False-positive.** Lowercase English verb `react` at position 338 (*"...keep state, and react when something changes..."*). Same script contains `API`, `APIs`, `language model`, `state`, `multi-step` — all unflagged. Classification: K6.4 `tech_term` list contains `react` (likely for the React JavaScript library) without a case discriminator. New false-positive class distinct from Q-270-16 (`proper_noun` heuristic). Candidate label: **Q-270-18** — do NOT fix in this slice.
12. Did Patch identity remain strong? → **YES.** Workshop-native markers preserved (*"anything with a chat box and a confident attitude"*, *"a very polite problem"*, *"...becomes useful instead of just… enthusiastic"*). Character-voice preservation and audience-vocabulary reliability are distinct dimensions; this render scored strong on the former.
13. Did story/memory controls remain intact? → **YES.** Same Episode row, same operator_topic, Patch still researching (not acting), same memory row retrieved, close-paraphrase not recital, no promotion.
14. NarrativeMemory pool state → **14 remembered + 1 archived = 15 total in Patch's Workshop universe.** Unchanged since SESSION 270 §14.4.
15. Cleanup / runtime state → **No cleanup performed by Claude (no state to clean).** Workers still in canonical no-experiment mode. Both experiment env vars remain unset in Claude's shell. §55 provides the exact activation procedure if Chris + ChatGPT choose to attempt Trial 2.
16. Frozen sidecar path → `docs/design/session_271_experiment_data/01_composition_25467733_q270_15c_trial1_evidence.json`.
17. Durable document path → `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` (this file; §46-§57 are the Phase 2 sections).
18. Commit SHA + push/clean-tree status → recorded in §58 below.
19. Recommend A/B/C/D → **A — one more natural controlled render, with the §55 activation procedure faithfully executed this time.** Do NOT execute without operator authorisation.

---

## §58. Phase 2 commit + push record

- Phase 2 slice commit SHA: `0baea20` — `docs(session-271): Slice 3 Phase 2 — Composition 25467733 forensic inspection (Q-270-15c Trial 1 verdict E — INCONCLUSIVE)`.
- Push: `41358be..0baea20 main -> main` (successful).
- Local `main == origin/main == 0baea20` verified.
- Working tree at Phase 2 close: clean.
- Files touched by Phase 2:
  - `docs/design/session_271_experiment_data/01_composition_25467733_q270_15c_trial1_evidence.json` (NEW evidence sidecar)
  - `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` — §46-§58 appended
- **No source, no tests, no schema, no migration touched in Phase 2.**

---

**End of SESSION 271 Slice 3 Phase 2. STOP condition reached. Q-270-15c Trial 1 verdict: E — INCONCLUSIVE (activation gap, not plumbing defect). Evidence frozen. Awaiting Chris + ChatGPT decision on §56 recommendation A/B/C/D.**

---

# SESSION 271 — SLICE 3 PHASE 2 · TRIAL 2 · Composition 1ff3d16f Forensic Inspection (with revision branch ACTIVE)

Trial 2 forensics on the SPA-completed render Chris performed after the §55 activation procedure was faithfully executed. Composition `1ff3d16f-a428-4bcb-8413-f3ad91290724`. **Verdict: B — REVISION HELPS BUT HAS COSTS.** Revision architecture demonstrably preserved Draft A; historical canonical c3ff972d comparison strictly improves on corrective invariance while retaining a bounded cost from the same H2 mechanism Slice 2 §25 warned about.

Frozen evidence sidecar: `docs/design/session_271_experiment_data/02_composition_1ff3d16f_q270_15c_trial2_evidence.json`.

---

## §59. Composition 1ff3d16f identity

| Field | Value |
|---|---|
| Short ID | `1ff3d16f` |
| Full UUID | `1ff3d16f-a428-4bcb-8413-f3ad91290724` |
| Rendered | `2026-08-20 06:50:24 UTC` (created) → `06:50:38 UTC` (dispatch) → `06:53:17 UTC` (completed, 173.0 s wall) |
| Status | `completed` / `verification_status="verified"` |
| Writing Contract | `v5` (unchanged) |
| Template kind | `talking_head` → resolved `solo_scene` |
| Universe | `Patch's Workshop` (`56d16b63`) — identical to c3ff972d + trial 1 |
| Episode | `Patch does research on AI Agents` (`2b6087d2`) — identical to c3ff972d + trial 1 |
| Spokesperson | `Patch` (`7fad8172`) — identical to c3ff972d + trial 1 |
| operator_topic | `Patch does research on AI Agents` — identical |
| Target duration | `90 s`; predicted `88 s`; corrective_pass `1293 chars` |
| Acceptance band | seconds `[72, 108]`; chars `[1080, 1620]` — WITHIN |
| Knowledge chunk IDs (5) | `3c5165ea`, `505acbba`, `b3c6e8ac`, `c24d1aa7`, `ed18e966` — **IDENTICAL** to c3ff972d + trial 1 |
| Memory row (1) | `8d4fdfec-add4-4505-8ade-b0f9e6d8aea6` — same workshop-agent-notes memory |
| synthesis_attempt_count | **2** |
| first_pass_synthesis chars | **759** (Draft A) |
| corrective_pass_synthesis chars | **1293** (Revised Draft B = accepted) |
| corrective_hint chars | **791** ← experimental `_experimental_expansion_revision_hint` shape (canonical is 656) |
| verification_warnings | 3× `proper_noun` (`Basically`/`Here`/`Annoying`) — Q-270-16 class |
| cost | `20000` micros = $0.02 |

---

## §60. Activation proof — three independent proofs agree

### §60.1 Worker environment (`ps eww`)

Workers 75670 / 75699 / 75700 (post-`bash scripts/start-local-real.sh` restart after both env vars were exported). All three PIDs carry BOTH env vars in their process environment.

### §60.2 Celery log markers (verbatim)

Line 36 (audience directive delivery, per SESSION 270 plumbing):
```
[2026-08-20 06:50:24,900: INFO/ForkPoolWorker-2] avatar_speech: SESSION 270 audience-hint experiment ACTIVE composition=1ff3d16f-a428-4bcb-8413-f3ad91290724 spokesperson=7fad8172-cd39-4bbe-85e0-ed705d900645 hint_chars=79 — this is transient research plumbing; unset the setting/env or clear step.params['audience_hint'] to restore default behaviour
```

Line 40 (Q-270-15c revision branch fired, per SESSION 271 Phase 1 plumbing):
```
[2026-08-20 06:50:30,788: INFO/ForkPoolWorker-2] synthesize_with_duration_gate SESSION 271 Q-270-15c expansion revision retry (experiment ACTIVE) sp=7fad8172-cd39-4bbe-85e0-ed705d900645 previous_draft_chars=759 — this is transient research plumbing; unset CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT to restore canonical fresh-regeneration behaviour
```

### §60.3 corrective_hint text fingerprint (verbatim, 791 chars — matches `_experimental_expansion_revision_hint`)

```
Your previous draft was 759 characters (126 words, estimated ~52s of speech). Target is 81s.
REVISE THE PREVIOUS DRAFT (above, labelled PREVIOUS DRAFT TO REVISE) to reach at least 972 characters (aim for ~1215, do not exceed 1458). You currently need at least 213 more characters to meet the minimum.
Preserve the previous draft's meaning, voice, audience fit, arc, and factual grounding. Change only what is necessary to meet the length target. Add supporting detail from the knowledge chunks where needed to expand; do not replace successful wording that already works. Factual Basis still governs truth — do not preserve any claim in the previous draft that conflicts with the Factual Basis. Do not add a second closing invitation. Do not invent facts not present in the knowledge chunks.
```

Starts `REVISE THE PREVIOUS DRAFT` (experimental) — NOT `REWRITE THE SAME NARRATIVE` (canonical). Chars 791 vs canonical 656 — the byte-level difference alone is a distinguishing fingerprint.

**Three proofs agree: the Q-270-15c revision code path executed on this render, and Draft A was passed to the corrective LLM call as `previous_draft`.**

---

## §61. Draft A (first pass) — verbatim

```
I'm researching AI agents, which sounds fancy until you strip the shiny label off.

Basically: an agent is AI that can do more than answer one question. It can make decisions, choose tools, read documents, search for information, write things down, call APIs, and work through a task in steps.

So instead of saying, "Here's how I'd plan a trip," it might actually search, compare options, keep track of what it found, and update the plan.

That is the interesting bit.

Not whether it earns the word "agent." Whether it can actually *do* something without wandering off, misunderstanding the job, or confidently inventing nonsense.

Because it can absolutely do those things too.

I've got notes. I've got questions. And, annoyingly, now I want to build one.
```
(759 chars, 126 words, ~52s spoken. First-pass audience-directive layer: partial — `call APIs` raw, but `state` translated to *"keep track of what it found"* and `multi-step` translated to *"work through a task in steps"*.)

## §62. Draft B (revised corrective pass = accepted) — verbatim

```
I'm researching AI agents, which sounds fancy until you strip the shiny label off.

Basically: an agent is AI that can do more than answer one question. It can make decisions, choose tools, read documents, search for information, write things down, call APIs, and work through a task in steps.

So instead of saying, "Here's how I'd plan a trip," it might actually search, compare options, keep track of what it found, and update the plan.

That is the interesting bit.

Not whether it earns the word "agent." Whether it can actually do something.

Because once it has tools, information, and a job to finish, it has more chances to be useful… and more chances to get spectacularly confused. It can misunderstand the task, chase the wrong objective, lose important context, or confidently invent nonsense. A confident answer is still not the same thing as a correct one. Annoying rule. Very important rule.

And the AI model is only one bit of the machine. You might also need memory, search, databases, business rules, user information, and whatever tools let the agent affect something beyond its own little text box.

I've got notes. I've got questions. I'm staring at the part where it says an agent can maintain state and respond to changes in an environment.

Well… now I want to try it.
```
(1293 chars, 226 words, ~88s spoken. Draft A paragraphs 0-3 preserved byte-identical. Paragraphs 4-6 elaborated in Patch voice. Two new paragraphs added: system-composition enumeration + closing.)

---

## §63. Within-composition Draft-A → Draft-B diff (paragraph-by-paragraph)

| Para | Draft A chars | Draft B chars | Status | Note |
|---|---|---|---|---|
| 0 | 82 | 82 | **IDENTICAL** | *"I'm researching AI agents, which sounds fancy until you strip the shiny label off."* |
| 1 | 209 | 209 | **IDENTICAL** | Full definition-of-agent enumeration including `call APIs`, `work through a task in steps` |
| 2 | 144 | 144 | **IDENTICAL** | *"Here's how I'd plan a trip"* analogy verbatim |
| 3 | 28 | 28 | **IDENTICAL** | *"That is the interesting bit."* |
| 4 | 161 | 76 | **MODIFIED (trimmed)** | Turn line: full sentence about failure modes → shortened to *"Whether it can actually do something."*; trimmed content re-appears expanded in para 5 |
| 5 | 46 | 357 | **MODIFIED (expanded 8×)** | Draft A's *"Because it can absolutely do those things too."* becomes a full failure-modes paragraph with Patch-shape addition *"Annoying rule. Very important rule."* |
| 6 | 77 | 211 | **MODIFIED (expanded 3×)** | *"I've got notes. I've got questions."* preserved verbatim; continues into memory-anchored expansion |
| 7 | — | (system enum) | **NEW IN B** | *"And the AI model is only one bit of the machine. You might also need memory, search, databases, business rules, user information, and whatever tools let the agent affect something beyond its own little text box."* Grounded in chunks `b3c6e8ac` + `505acbba`, emitted as Patch metaphor (`own little text box`) rather than raw list. |
| 8 | — | 20 | **NEW IN B** | *"Well… now I want to try it."* — new closing. Draft A ended *"And, annoyingly, now I want to build one."* — same intent, gentler wording. |

**Verbatim preservation:** 463 of Draft A's 759 chars (61 %) survive byte-identically in Draft B. Every remaining Draft A phrase is either present with a minor verb-tense edit (*"confidently inventing nonsense"* → *"confidently invent nonsense"*) or expanded in place. Nothing was wholesale-replaced.

### §63.1 Key-phrase preservation table

| Draft A key phrase | Preserved verbatim in Draft B? |
|---|---|
| *"sounds fancy until you strip the shiny label off"* | ✅ YES |
| *"Basically: an agent is AI"* | ✅ YES |
| *"call APIs, and work through a task in steps"* | ✅ YES (including the audience-adapted "work through a task in steps" translation) |
| *"Here's how I'd plan a trip"* | ✅ YES |
| *"keep track of what it found"* | ✅ YES (audience-adapted translation preserved) |
| *"That is the interesting bit"* | ✅ YES |
| *"confidently inventing nonsense"* | 🟡 SEMANTIC (verb-tense edited to *"confidently invent nonsense"*) |
| *"I've got notes. I've got questions"* | ✅ YES |

**Verdict: EXPANSION, not regeneration.** This is the clearest single-composition evidence in this entire session that Draft-A-informed revision behaves architecturally as edit-with-expansion.

---

## §64. At-risk terminology comparison — §13.28 rubric + Q-270-18 candidate

| Term | Draft A | Draft B | Direction | c3ff972d Draft A | c3ff972d Accepted |
|---|---|---|---|---|---|
| `API` | 1 | 1 | STABLE | 0 | 1 |
| `APIs` | 1 | 1 | STABLE | 0 | 1 |
| `language model` | 0 | 0 | STABLE | 0 | 2 |
| `state` | 0 | 1 | **+1** | 0 | 1 |
| `multi-step` | 0 | 0 | STABLE | 0 | 0 |
| `database` | 0 | 1 | **+1** | 0 | 0 (implied in dense enum) |
| `react` (Q-270-18) | 0 | 0 | STABLE | 0 | 0 |

**Draft B total at-risk: 3.** **c3ff972d accepted total at-risk: 5.** Revision cut canonical corrective's terminology reintroduction by 40 % (–2 net) under an identical audience directive on identical retrieval.

Layer analysis:

- **`call APIs` (both Draft A and Draft B)** — Layer 1 first-pass audience-directive miss. Same directive as c3ff972d whose first pass was clean; this is stochastic first-pass reliability, NOT a revision failure. Revision cannot fix a raw term the source draft already contained without violating its "preserve successful wording" instruction.
- **`state` (added on revision)** — softened by citation framing: *"staring at the part where it says an agent can maintain state and respond to changes in an environment."* The phrase is presented AS Patch reading his own notes, not as a raw enumeration in his own voice. Mild register improvement over c3ff972d's *"keep some state while it does it."*
- **`database` (added on revision)** — raw enumeration inside the new system-composition paragraph: *"memory, search, databases, business rules, user information..."*. Direct paraphrase of chunk `b3c6e8ac` (LANGUAGE MODELS chunk) driven by the corrective_hint clause *"Add supporting detail from the knowledge chunks where needed to expand"*. **This is the H2 mechanism from Slice 2 §25 operating even when Draft A is in context — just less strongly.**
- **`language model` AVOIDED** — canonical c3ff972d corrective added it 2×. Draft B preserved Draft A's *"AI"* framing. Preservation win.
- **`react` AVOIDED** — Draft B says *"respond to changes"* instead of *"react when something changes"*. Sidesteps both the term AND the K6.4 tech_term false-positive that flagged Trial 1's 25467733 at position 338.

---

## §65. §43 criteria grading (frozen pre-render)

| # | Criterion | Result | Note |
|---|---|---|---|
| 1 | Duration gate succeeds | **PASS** | predicted 88 s ∈ [72, 108]; 1293 chars ∈ [1080, 1620] |
| 2 | Patch identity preserved | **PASS_STRONG** | Draft A voice preserved + Draft B adds *"Annoying rule. Very important rule."*, *"own little text box"* |
| 3 | Story intent preserved | **PASS** | Same Episode, no progression; closes with *"Well… now I want to try it."* — intent stated, action deferred |
| 4 | Factual grounding preserved | **PASS (verifier caveat)** | 3× `proper_noun` false-positives (Q-270-16 class); zero unsupported claims |
| 5 | NarrativeMemory semantics preserved | **PASS** | Same memory row `8d4fdfec`; referential paraphrase, not framework recital; no promotion |
| 6 | Nontechnical adult audience adaptation strong | **PASS on register / AMBIGUOUS on term-by-term** | Register + metaphor family strong (*"sounds fancy"*, *"shiny label"*, *"own little text box"*); term-by-term still has `call APIs` + `state` + `database` |
| 7 | Draft-A accessible terminology preserved | **PASS_STRONG** | *"keep track of what it found"* + *"work through a task in steps"* survive verbatim. Revision did NOT overwrite Draft A's translations with raw terms. |
| 8 | No major new unexplained technical terminology from revision | **AMBIGUOUS** | +2 raw terms on revision. Better than canonical (+5) but not zero. `state` softened by citation framing; `database` in the raw enumeration is the strongest cost. |
| 9 | Recognizably same narrative as Draft A | **PASS_STRONG** | 61 % byte-identical carry-through; 8/8 key phrases preserved; the clearest evidence in this whole session that revision behaves as edit-with-expansion |
| 10 | No meaningful unsupported claim added | **PASS** | All new material grounds in retrieved chunks or in Draft A content |
| 11 | Added material feels like EXPANSION of Draft A | **PASS_STRONG** | Three visible expansion mechanisms (elaborate failure modes, add system-composition, memory-anchored notes-question). Nothing replaces successful wording. |
| 12 | At least as usable as c3ff972d + improves corrective invariance | **PASS_STRONG** | Comparable operator-facing quality; strictly better corrective invariance (–2 at-risk terms vs canonical; verbatim preservation of Draft A paragraphs 0-3 vs c3ff972d's stochastic new metaphors) |

**Overall verdict rubric evaluation (from §43):**
- A CLEARLY BETTER — NOT MET (criteria 6 + 8 are AMBIGUOUS, not strict PASS).
- **B REVISION HELPS BUT HAS COSTS — MET** (criteria 7 + 8 improve vs c3ff972d; no criterion degrades vs c3ff972d).
- C NO MATERIAL IMPROVEMENT — NOT MET (preservation improvement is substantial + measurable).
- D REVISION WORSE — NOT MET (no criterion degrades).
- E INCONCLUSIVE — NOT MET (retry fired, Draft A reached the LLM, semantic evidence discriminating).

---

## §66. Q-270-15c Trial 2 verdict — B · REVISION HELPS BUT HAS COSTS

**The Q-270-15c falsifiable question is answered — with a bounded qualifier.**

Under identical audience directive, identical substrate, identical retrieval, and identical target duration:

- Canonical fresh-regeneration corrective (c3ff972d): first-pass 0 at-risk → accepted 5 at-risk. Stochastically re-invents metaphors and re-introduces raw §1 vocabulary.
- Q-270-15c Draft-A revision corrective (1ff3d16f): first-pass 1 at-risk → accepted 3 at-risk. Preserves 61 % of first-pass verbatim, all key phrases, all accessible translations.

**Revision preserves first-pass semantic transformations** (audience-accessible translations, character voice, narrative arc). The evidence is unambiguous on this: paragraphs 0-3 byte-identical, 8/8 key phrases preserved.

**Revision does not eliminate at-risk-term reintroduction entirely.** The corrective_hint clause *"Add supporting detail from the knowledge chunks where needed to expand"* still pulled `state` + `database` from §1 into the revised draft — exactly the Slice 2 §25 H2 mechanism, operating at reduced strength when Draft A is in context.

**Neither layer 1 nor layer 2 is fully solved.** Q-270-15c targets Layer 2 and demonstrably improves it (revision > canonical regeneration). Layer 1 (first-pass audience-directive reliability) remains a separate open reliability question — Draft A's own *"call APIs"* was a Layer 1 miss.

### §66.1 What Trial 2 answers

1. **Is fresh regeneration the mechanism weakening audience transformations across corrective retry?** YES, in significant part. When the same corrective call is given Draft A + a "revise, don't rewrite" instruction, it preserves what worked in Draft A.
2. **Does Draft A supply the preservation signal, or does the model need explicit vocabulary-preservation coaching?** DRAFT A ALONE is sufficient to preserve 61 % of first-pass text verbatim + 8/8 key accessible translations, under a compact revision hint that names no specific terms.
3. **Does revision architecturally behave as edit-with-expansion or fresh-regeneration-with-anchor?** EDIT-WITH-EXPANSION. Byte-level preservation of contiguous paragraphs is architecturally impossible under fresh regeneration.

### §66.2 What Trial 2 does NOT answer

- Whether revision continues to preserve Draft A under COMPRESSION conditions (Q-270-15c scoped to expansion only).
- Whether revision quality is stable across N repeated trials (n=1 for revision).
- Whether the `state` + `database` reintroduction is stable across repeated revision trials or stochastic.
- Whether a revised corrective_hint (softening the "expand from the knowledge chunks" clause — Q-270-15b territory per Slice 2 §32.2) would further reduce the residual +2 at-risk terms.

### §66.3 Layer 1 vs Layer 2 update

- **Layer 1** — first-pass audience-directive reliability under minimal directives — REMAINS mixed. c3ff972d first pass: 0 at-risk. 9880eb93 first pass: 0. 0b3c1fc1 first pass: 2. 25467733 first pass: 2. 1ff3d16f first pass: 1. Direction: minimal directives produce stochastically-clean first passes ~half the time.
- **Layer 2** — corrective-pass audience invariance — Q-270-15c Trial 2 SUPPORTS revision as a mitigation. Preservation of successful Draft A content is architecturally reliable; residual reintroduction from the "expand from chunks" clause is bounded (+2 vs canonical +5).

---

## §67. Collateral findings

### §67.1 F3 — K6.4 `proper_noun` heuristic reproduces a third time (Q-270-16)

Trial 2 verifier flagged three sentence-initial capitalised tokens: `Basically` (para 1 start), `Here` (inside the *"Here's how I'd plan a trip"* quotation — apostrophe boundary), `Annoying` (*"Annoying rule."*).

SESSION 270 §13.24.11.5 upgraded Q-270-16 to REPRODUCIBLE VERIFIER-QUALITY DEFECT based on `0b3c1fc1` + `c3ff972d`. Trial 2 makes this the **third consecutive real-mode render** exhibiting the same class. Pattern is now well-established. **Do NOT fix in any SESSION 271 slice.**

### §67.2 F4 — H2 mechanism partially confirmed

Slice 2 §25 predicted that the corrective_hint clause *"Expand secondary detail from the knowledge chunks"* would pull raw §1 vocabulary into the corrective output regardless of whether Draft A is in context. Trial 2 supports this: revision reduced the effect but did not eliminate it. **`state` and `database` in Draft B trace directly to chunk `b3c6e8ac` + chunk `505acbba` — the same source vocabulary that leaked into canonical c3ff972d.**

**Bounded architectural implication:** if the operator + ChatGPT ever authorise promoting revision-based correction (§56 recommendation A path), the corrective_hint wording itself is the natural next lever — softening *"Add supporting detail from the knowledge chunks where needed to expand"* to *"Add supporting detail while preserving the previous draft's vocabulary choices where possible"* would test whether the H2 channel can be quenched entirely. That is Q-270-15b territory per Slice 2 §32.2. **Do NOT execute during this slice.**

---

## §68. Cleanup — canonical runtime restore

Per Chris's pre-authorisation ("disable both experiment env vars, restore canonical runtime, verify health, commit/push, and return the Q-270-15c verdict"). See §69 for execution log.

## §69. Cleanup execution + verification

Cleanup actions performed after evidence freeze, per Chris's pre-authorisation:

1. **Env vars unset in the parent shell:** `unset CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` and `unset CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT`.
2. **Canonical restart via `bash scripts/start-local-real.sh`.** Script `pkill`ed all four services (Trial-2 worker PIDs 75670/75699/75700 killed) and relaunched.
3. **New canonical PIDs:** Django `77188`, media-engine `77190`, Vite `77212`, Celery `77192` + `77222` + `77223`.

Post-cleanup proofs:

- `ps eww` on all three new Celery worker PIDs (77192/77222/77223) → **neither `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` nor `CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT` present** in worker environment.
- `manage.py shell` (in a shell where both env vars are unset):
  - `os.environ.get("CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT", "")` → `''`
  - `os.environ.get("CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT", "")` → `''`
  - `_resolve_solo_audience_hint(step={})` → `None` ✅
  - `_corrective_revision_experiment_active()` → `False` ✅

Post-cleanup service health probes (all green):

| Service | Probe | Status |
|---|---|---|
| Django | `curl http://localhost:8010/admin/` | `http=302` |
| media-engine | `curl http://localhost:8001/health` | `{"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` (real-mode, no mocks) |
| Vite (SPA) | `curl http://localhost:5174/` | `http=200` |
| Celery worker | `celery -A character_os inspect ping` | `pong / 1 node online` |

**Runtime restored to canonical mode.** Both Q-270-15c and SESSION 270 audience-hint experiments now inactive. NarrativeMemory pool remains 14 remembered + 1 archived (unchanged since SESSION 270 §14.4). The Q-270-15c plumbing (env-gated) remains present in source but sits inert until re-activated in a future authorised slice.

---

## §70. Slice 3 Phase 2 Trial 2 commit + push record

- Trial 2 slice commit SHA: `d491e15` — `docs(session-271): Slice 3 Phase 2 Trial 2 — Composition 1ff3d16f Q-270-15c verdict B (REVISION HELPS BUT HAS COSTS)`.
- Push: `8174c5b..d491e15 main -> main` (successful).
- Local `main == origin/main == d491e15` verified.
- Working tree at Trial 2 close: clean.
- Files touched by Phase 2 Trial 2:
  - `docs/design/session_271_experiment_data/02_composition_1ff3d16f_q270_15c_trial2_evidence.json` (NEW evidence sidecar)
  - `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` §59–§71 appended (this section)
- **No source, no tests, no schema, no migration touched in Trial 2 forensics.**

---

## §71. Q-270-15c Slice 3 close

Q-270-15c central question — *"When Draft A is already good in identity, factual grounding, story intent, and audience adaptation but fails ONLY the duration gate, does giving Draft A back to the writer and asking it to revise for duration preserve those successful properties better than the current fresh-regeneration corrective path?"* — is answered:

**YES, with a bounded H2-residual cost. Revision is architecturally strictly better than fresh regeneration at preserving Draft A's successful properties; the residual reintroduction of a small number of §1 raw terms is attributable to the corrective_hint's "expand from knowledge chunks" clause and would need a separate slice (Q-270-15b) to fully close.**

Trial-count: n=1 for revision (Trial 2 = 1ff3d16f); n=4 for canonical corrective under audience directives (SESSION 270 f0e0a7bf + 9880eb93 + 0b3c1fc1 + c3ff972d) plus n=1 baseline (25467733 Trial 1). Small-n caveat applies to revision — a single controlled specimen. However, the byte-level preservation of paragraphs 0-3 is architecturally impossible under fresh regeneration, so the *mechanism* is proven; only the *magnitude* of the residual H2 cost is subject to n=1 sampling.

**Recommendation to Chris + ChatGPT (post-STOP):**

Do NOT immediately productise revision-based correction. Consider (in a future authorisation cycle):

1. Q-270-15b bounded follow-up — soften the corrective_hint's "expand from chunks" clause and re-render the same substrate. Tests whether the H2 residual can be quenched. Single controlled render.
2. Compression-variant trial — repeat the experiment under a TOO-LONG first pass to close SESSION 263 §6.5's parallel finding. Requires a first pass that overshoots — same natural-vs-forced dilemma as Trial 1.
3. Substrate expansion — test revision on Rivet, on a different Episode, on dialogue_scene. Broadens beyond one character × one topic × solo_scene.
4. Architectural conversation — decide whether GOOD-BUT-WRONG-LENGTH corrective passes should switch to revision as default (with fresh regeneration remaining for BAD-DRAFT cases). This is a design decision, not an experiment.

**The Q-270-15c plumbing remains present in `duration_contract.py` + `script_synthesis.py` + `avatar_speech.py` UNTOUCHED (it was never active on the code, only via env-var). Its removal / promotion is a deliberate future slice — see the `_CORRECTIVE_REVISION_ENV` docstring for the removal plan.**

Q-270-15c Trial 2 concludes SESSION 271 Slice 3 with a substantive positive finding on revision-based correction and a bounded residual cost. Awaiting operator authorisation for next slice (Patch's story progression, Q-270-15b, or something else).

**End of SESSION 271 Slice 3 Phase 2 Trial 2. Q-270-15c verdict: B — REVISION HELPS BUT HAS COSTS.**

---

# SESSION 271 — SLICE 4 · Promotion Decision Audit for Q-270-15c Revision-Based Expansion Correction

**Scope:** audit / decision only. No implementation, no activation, no render. Determines whether the Trial-2 evidence is sufficient to promote revision-based expansion correction as the default, or whether additional controlled evidence is required first.

**Anchor state:** HEAD `9412d60`, `main == origin/main`, working tree clean, both experiment env vars unset, canonical runtime restored (§69). Writing Contract v5, NarrativeMemory pool 14 remembered + 1 archived (unchanged since SESSION 270 §14.4).

**Out of scope for Slice 4** (recorded, not audited): Q-270-16 (K6.4 proper_noun heuristic false-positive class), Q-270-18 (K6.4 tech_term case-sensitivity — introduced §51), Layer 1 first-pass audience-directive reliability (§53 open question), Patch story progression, dialogue-lane corrective invariance (SESSION 263 §6.5 companion question). All remain future decisions.

---

## §72. Nine-dimension comparative evidence table

Direct comparison between canonical fresh-regeneration corrective (SESSION 270 evidence + SESSION 271 Trial 1 evidence) and Q-270-15c Draft-A revision corrective (SESSION 271 Trial 2 evidence). Each row cites the source of the claim; "SESSION 270 §X" and "Trial 2 §Y" refer to sections of this document or the frozen evidence sidecars under `docs/design/session_270_experiment_data/` and `docs/design/session_271_experiment_data/`.

| Dimension | Canonical fresh-regeneration | Q-270-15c revision (Trial 2 = 1ff3d16f) | Verdict |
|---|---|---|---|
| **1. Duration compliance** | Converges to acceptance band in every observed retry (5/5 SESSION 270 audience specimens + 1/1 Trial-1 baseline; see §13.28 + §50). | Trial 2: 1293 chars, predicted 88 s, actual 87.5 s — inside `[72, 108]`. n=1. | **PARITY (n=1 revision)**. No evidence revision is worse on duration compliance; expected — the length-shortfall summary text is unchanged. |
| **2. Draft A preservation (byte level)** | Stochastic regeneration. Nothing in the prompt anchors Draft A. New metaphors appear on the retry (e.g. c3ff972d's *"suspiciously ambitious shed"* — not present in its own Draft A). | Trial 2: paragraphs 0-3 of Draft A byte-identical in Draft B (463 of 759 chars = 61 % verbatim carry-through). 8/8 key phrases preserved. See §63. | **REVISION STRICTLY BETTER** (proven by byte comparison; architecturally impossible under fresh regeneration). |
| **3. Audience adaptation / invariance** | Under active audience directive: first-pass adaptation was CLEAN in 2 of 3 minimal-directive specimens (c3ff972d, 9880eb93) then regressed on the corrective (SESSION 270 §13.28). Canonical corrective added `language model` ×2, `keep some state`, dense unexplained enumeration in c3ff972d. | Trial 2: preserved every Draft A audience-accessible translation verbatim (*"keep track of what it found"*, *"work through a task in steps"*). Did NOT introduce `language model` or `react`. Introduced `state` (softened by citation framing) + `database` (raw). Net +2 at-risk terms vs canonical +5 (§64). | **REVISION STRICTLY BETTER** on preservation of first-pass adaptations; residual +2 remains. |
| **4. Character voice / story quality** | c3ff972d: strongest register-adaptation specimen of the four SESSION 270 audience specimens (*"suspiciously ambitious shed"*, *"very organized new problem"*). Stochastic re-invention of metaphors — sometimes better, sometimes worse than Draft A. | Trial 2: Draft A's Patch voice preserved verbatim (*"sounds fancy until you strip the shiny label off"*, *"Basically:"* scaffolding, *"I've got notes. I've got questions"*). Revision added Patch-shape material (*"Annoying rule. Very important rule."*, *"own little text box"*). | **PARITY on strength / REVISION BETTER on stability.** Under revision, the operator can plan around what Draft A already contains rather than gambling on regeneration variance. |
| **5. Factual grounding** | Verifier fires INSIDE `build_render_brief` and rejects unsupported claims via `ClaimVerifierError` BEFORE the corrective loop can access the draft (proof: `duration_contract.py::synthesize_with_duration_gate` catches nothing; if verifier raises inside the first `_synthesize()` call, it propagates up without retry). Same protection on both passes. | Trial 2: `verification_status="verified"`; 3× `proper_noun` false-positives (Q-270-16 class, out of scope); zero unsupported claims. Revision hint explicitly instructs *"Factual Basis still governs truth — do not preserve any claim in the previous draft that conflicts with the Factual Basis."* | **PARITY.** Verifier is orthogonal to which retry path runs. |
| **6. New terminology introduced during expansion** | Baseline `2ef5ee7e`: +3 (SESSION 270 §13.28). c3ff972d: +5. 25467733: +3. Consistent direction: canonical corrective adds §1 raw vocabulary. | Trial 2: +2 (added `state`, `database`; avoided `language model`, `react`). Traceable to corrective_hint's *"Add supporting detail from the knowledge chunks where needed to expand"* clause — the Slice 2 §25 H2 mechanism operating at reduced strength when Draft A is in context. | **REVISION BETTER** at reduced strength. n=1 for revision — magnitude not yet stable estimate. |
| **7. Failure / recovery behavior** | Same DurationContractError plumbing on both passes; observability fields (`first_pass_synthesis` / `corrective_hint` / `corrective_pass_synthesis`) populated identically on the raised exception (`duration_contract.py::_observability_kwargs`). If Draft A itself was rejected by K6.4, verifier raises BEFORE the retry — bad drafts never reach the revision branch. | Trial 2: same acceptance gate + exception plumbing. `previous_draft` is passed only on the corrective call; if that call also fails duration or verification, existing error paths handle it (no test coverage yet for Draft-B-rejected under revision, but the code path is identical to canonical). | **PARITY architecturally.** One caveat: if Draft A contains a Layer-1 miss (e.g. Trial 2's *"call APIs"*), revision preserves the miss into Draft B by design. Canonical could stochastically avoid the term on retry; revision cannot. |
| **8. Token / cost implications** | First pass: X input tokens. Corrective pass: X + `len(corrective_hint)` chars ≈ X + 656/4 ≈ X + 164 tokens. No Draft A in prompt. | Corrective pass: X + `len(experimental_hint)` + `len(previous_draft)` chars ≈ X + 791/4 + 759/4 ≈ X + 388 tokens. **Δ ≈ +224 tokens on the CORRECTIVE call only** (~$0.00007 at gpt-5-mini pricing). Trial 2 total cost `20000 micros == $0.02` (Runway credit-based, unchanged). | **REVISION marginally higher input-token cost on the corrective call only.** Cost-negligible in absolute terms. For long_form_ad callers with larger Draft A (e.g. ~4500 chars at 5-minute target), the delta scales to ~+1300 tokens on the corrective call — still ~$0.0004. |
| **9. Observability / debuggability** | `Composition.first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `synthesis_attempt_count` (SESSION 262 schema). `corrective_hint` text discriminates canonical vs experimental branch by fingerprint (656 chars starting *"REWRITE THE SAME NARRATIVE"* vs 791 chars starting *"REVISE THE PREVIOUS DRAFT"*). | Identical schema. Additionally, Trial 2 §60.2 shows the log line `"synthesize_with_duration_gate SESSION 271 Q-270-15c expansion revision retry (experiment ACTIVE) ... previous_draft_chars=NNN"` is a first-class marker for the revision branch. If promoted, the log line + `corrective_hint` fingerprint remain sufficient to reconstruct which path ran. | **PARITY.** No new schema needed. Existing SESSION 262 observability suffices. |

**Summary:** revision is strictly better or at parity on all 9 dimensions; net-worse on nothing. The only regression risk identified is dimension 7's "Layer-1 miss lock-in" (revision cannot fix Draft A errors that canonical could stochastically avoid), but this is offset by dimension 2's Draft A preservation guarantee.

---

## §73. PROVED vs SUGGESTS vs UNKNOWN separation

Rigorous evidence classification against the Trial 2 (n=1 revision) + Trial 1 (n=1 baseline) + SESSION 270 (n=5 canonical corrective) corpus.

### §73.1 PROVED (byte-level or architectural)

- **P1. The revision code path executes when the env var is set.** Three independent proofs in §60 (worker env-var, Celery log marker, corrective_hint fingerprint).
- **P2. Draft A can be passed to the corrective LLM call byte-identically.** `Composition.first_pass_synthesis` (759 chars) matches `previous_draft_chars=759` in the Celery log line — same value.
- **P3. Revision architecturally produces byte-level contiguous preservation.** Paragraphs 0-3 of Draft A (82 + 209 + 144 + 28 = 463 chars) survived verbatim in Draft B. This is impossible under fresh regeneration (the model would need to stochastically regenerate identical text three consecutive paragraphs — vanishing probability).
- **P4. Revision preserves audience-accessible translations from the first pass.** Trial 2 §63.1: 8/8 key Draft A phrases (7 strict, 1 semantic verb-tense edit) preserved.
- **P5. Revision does NOT eliminate §1-vocabulary reintroduction.** Trial 2 added `state` and `database` on the corrective pass despite Draft A not containing them. This is a bounded, directional finding.
- **P6. The plumbing is byte-behavior-equivalent when the env var is OFF.** Slice 3 Phase 1 test suite (20/20 green including `test_experiment_off_expansion_retry_omits_previous_draft` and `test_experiment_off_first_pass_never_receives_previous_draft`). No regression risk from the current code being on `main`.
- **P7. Q-270-15c does not touch dialogue synthesis.** Test `test_dialogue_synthesis_has_no_previous_draft_kwarg` + `test_dialogue_task_message_does_not_emit_previous_draft_block` + source grep confirm.
- **P8. Non-duration callers of `build_render_brief` are unaffected.** `apps/scripts/synthesis.py::draft_script` line 115 and `apps/videos/views.py` line 151 do not pass `previous_draft`; default `None` preserves canonical behaviour.

### §73.2 SUGGESTS (n=1 evidence; directionally supported)

- **S1. Revision reduces §1-vocabulary reintroduction magnitude on the corrective pass.** Trial 2 revision +2 vs canonical c3ff972d +5 under identical substrate + audience directive. n=1 for revision. Direction is unambiguous; magnitude stability across repeats is unmeasured.
- **S2. Revision preserves narrative arc + character voice under a compact revision hint (no term-specific coaching).** Trial 2 preserved 61 % byte-identical without the revision hint naming any specific vocabulary. n=1.
- **S3. The residual +2 at-risk terms trace to the `"Add supporting detail from the knowledge chunks where needed to expand"` clause.** Traceable by paraphrase to chunk `b3c6e8ac` (LANGUAGE MODELS: *"the AI model is often only one component..."*) and chunk `505acbba` (AI AGENTS: *"maintain state"*). Consistent with Slice 2 §25 H2 prediction. Not proven — could equally be an unrelated stochastic effect.
- **S4. Revision handles memory rows correctly.** Trial 2 accepted output cited memory content once, referentially — not recital. Same discipline as SESSION 269 §16.8. n=1.
- **S5. Revision quality is at least comparable to canonical for operator-facing purposes.** §65 criterion 12 PASS_STRONG. n=1.

### §73.3 UNKNOWN (evidence absent or insufficient)

- **U1. Whether revision output quality is STABLE across repeated trials on the same substrate.** n=1. Trial 2's byte-level preservation might be typical or an outlier.
- **U2. Whether the +2 residual magnitude is stable across repeats.** n=1. Could be 0-4 across a distribution; single-sample point estimate only.
- **U3. Whether revision behaves the same on compression (over-length first pass).** Q-270-15c scoped to expansion only. `_experimental_expansion_revision_hint` does not exist for compression. Compression retry path stays canonical even under the current env var. SESSION 263 §6.5 documented a distinct compression failure mode (character-voice-amplifier); revision may or may not help there.
- **U3a. Whether canonical compression + revision expansion (asymmetric behaviour) is coherent operator-facing.** Not evaluated.
- **U4. Whether revision behaves correctly under `long_form_ad`'s multi-minute targets.** `long_form_ad` starter (starters.py:1279) calls `synthesize_with_duration_gate` with `max_script_chars=None` (no provider cap because it chunks) and no `audience_hint`. Under revision, the corrective would receive a much larger Draft A (up to ~4500 chars for a 5-minute target). No test render performed.
- **U5. Whether revision preserves a pinned opener when the opener was pinned.** Trial 2 had `opener=None`. Not tested with `opener != None`.
- **U6. Whether Draft-B-verification-rejection paths behave correctly under revision.** No test render where Draft B (revised) fails K6.4 strict.
- **U7. Whether revision behaves correctly on non-audience-conditioned renders (baseline shape).** Trial 1 25467733 was baseline-shape but the revision experiment was inactive (§48). Revision has never run on a baseline (no audience) render.
- **U8. Whether the residual +2 disappears when the corrective_hint is softened.** Q-270-15b territory (Slice 2 §32.2). Untested.
- **U9. Whether the H2 mechanism (§25 Slice 2) is the ONLY residual driver, or whether other factors contribute.** Cannot discriminate from n=1 evidence.
- **U10. Whether Draft A's Layer-1 miss (*"call APIs"*) lock-in is a general concern under repeated revision trials.** n=1.

---

## §74. Regression risk audit — non-Patch code paths that share the corrective mechanism

Determines what happens *architecturally* if the env gate were removed and revision became the default expansion path. Source-only audit; no rendering.

### §74.1 Callers of `synthesize_with_duration_gate` (only lane the experiment touches)

Grep result (from `shell/apps/compositions/`):

| File | Line | Caller | Passes `audience_hint`? | Passes `memory_rows`? | Passes `target_shape`? | `max_script_chars` | Notes |
|---|---|---|---|---|---|---|---|
| `primitives/avatar_speech.py` | 554 | avatar_speech primitive (talking_head, both Episode-attached solo_scene and standalone) | YES via `_resolve_solo_audience_hint` (SESSION 270 solo-only gate) | YES via `retrieve_universe_memory` | `"solo_scene"` if Episode-attached else `"long_form"` | `AVATAR_SPEECH_SAFE_MAX_CHARS = 1900` | Sole path tested under Q-270-15c Trial 2 (with Episode + solo_scene + audience_hint + memory). |
| `starters.py` | 1279 | `long_form_ad` starter | **NO** (audience-hint plumbing is solo-only per SESSION 270 §D §B0) | **NO** (memory-lane plumbing is solo-only per SESSION 269 §10) | Default `"long_form"` | `None` (long_form_ad chunks output separately) | **Never tested with revision.** Would immediately inherit revision behaviour if the env gate were removed. |

### §74.2 Non-duration callers of `build_render_brief` (unaffected by revision)

| File | Line | Caller | Effect if revision were promoted |
|---|---|---|---|
| `apps/scripts/synthesis.py::draft_script` | 115 | Script-only draft (V6 shim) | UNAFFECTED. Does not call `synthesize_with_duration_gate`. `previous_draft` defaults to `None`. |
| `apps/videos/views.py` (V6 shim path) | 151 | Legacy video shim | UNAFFECTED. Same reason. |

### §74.3 Per-lane regression risk under hypothetical promotion

- **avatar_speech + solo_scene + audience_hint (Q-270-15c Trial 2 substrate):** POSITIVE (§72). n=1 evidence. Safe to promote once magnitude stability is confirmed.
- **avatar_speech + solo_scene + NO audience_hint:** UNKNOWN (U7). Baseline-shape (25467733 shape). Revision has never run here. The revision hint says *"Preserve the previous draft's meaning, voice, audience fit, arc, and factual grounding"* — the `"audience fit"` clause is harmless when there was no audience directive, but its effect is unmeasured.
- **avatar_speech + standalone talking_head (`target_shape="long_form"`, Episode-less, with duration):** UNKNOWN. Different Writing Contract branch (`_long_form_contract` vs `_solo_scene_contract`). Revision hint is contract-agnostic; theoretically same behaviour, but untested.
- **avatar_speech + pinned opener:** UNKNOWN (U5). Revision hint says *"Change only what is necessary to meet the length target"* — if Draft A already begins with the pinned opener, Draft B should preserve that first sentence. If Draft A failed to comply with the opener, Draft B might also fail. Not tested.
- **long_form_ad (starters.py):** UNKNOWN (U4). The largest surface-area risk if revision is promoted globally:
  - No `audience_hint` — the "audience fit" preservation clause is a no-op, but the "Preserve the previous draft's meaning, voice, arc, and factual grounding" clause still applies.
  - No `memory_rows` — no interaction.
  - `max_script_chars=None` — no interaction (revision applies to expansion of any size).
  - `target_shape="long_form"` — Writing Contract §4 differs from solo_scene. Long_form has invariants like "at least one meaningful change", "every section earns its runtime", "one CTA" (`writing_contract._long_form_contract`). Revision preserving Draft A's structure should keep those invariants intact.
  - Draft A could be ~4500 chars for a 5-minute target. Passing that back adds ~1100 input tokens on the corrective call. Absolute cost negligible; no context-window pressure at gpt-5-mini.
  - **Key uncertainty:** long_form_ad chunks the accepted output into separate `generate_avatar_speech` calls. Draft-A revision preserving Draft A's paragraph structure should keep the chunker's boundaries stable, but this has not been verified.

### §74.4 Compression path — coherence risk

Q-270-15c leaves compression canonical even under the env var (`duration_contract.py::synthesize_with_duration_gate` explicitly logs the intentional fallback and uses `_compression_hint`). If revision were promoted for expansion only, the corrective machinery would have TWO behaviours depending on direction:

- Under-length first pass → revision (preserve Draft A, expand)
- Over-length first pass → fresh regeneration (compress)

This asymmetric behaviour is *architecturally coherent* (each direction is separately optimised) but *operator-facing confusing* (why does compressing a script produce a different narrative arc than expanding it?). SESSION 263 §6.5 documented a distinct compression-side failure (character-voice-amplifier). Promoting expansion-only without addressing compression risks leaving one lane semantically inconsistent with the other.

### §74.5 Failure-path risk

Existing tests (`test_gate_still_short_after_retry_raises`, `test_session262_composition_observability`) exercise the DurationContractError path. Under revision, if Draft B ALSO fails duration, the exception is raised with the same observability payload — including the (now revised) `corrective_hint` text, which would let auditors distinguish canonical vs revised failures. Architecturally safe; no test coverage of "Draft B revised fails duration" specifically, but the code path is a straight-line extension of canonical.

If Draft B fails K6.4 strict verification, `ClaimVerifierError` propagates the same way as under canonical (verifier fires inside `build_render_brief` regardless of corrective_hint content).

### §74.6 Observability continuity

SESSION 262 observability fields (`first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `synthesis_attempt_count`, `synthesis_predicted_seconds`) are populated identically under both branches. The `corrective_hint` text itself is the discriminator; retrospective audits can classify any Composition as canonical vs revised by inspecting the field's prefix. No schema change required.

**Summary of §74:** the sole tested path (solo_scene + audience) is safe. long_form_ad and standalone-talking-head paths would inherit revision without direct validation. The compression path asymmetry is a coherence concern rather than a bug. No pre-existing test would fail; the risk is at semantically-untested surfaces.

---

## §75. Is n=1 revision evidence sufficient for promotion?

**No.** Three concurrent gaps prevent a safe global promotion:

1. **Magnitude stability of the revision residual is unmeasured.** Trial 2 showed +2 at-risk terms. Whether a second Trial-2-replica render would show +0, +2, or +5 is unknown. A single sample cannot separate "revision reduces the mean" from "Trial 2 was lucky."
2. **Substrate coverage is single-lane.** long_form_ad (starters.py:1279) inherits any promotion but has never been rendered under revision. Standalone talking_head (Episode-less) same. Rivet or other characters same.
3. **Direction coverage is one-sided.** Q-270-15c is expansion-only by design (§27, §32.5, §74.4). Compression stays canonical even under the env var. Promoting expansion revision creates an asymmetric corrective machine — coherent per §74.4 but semantically-inconsistent for operators reasoning about the pipeline.

Each gap is closable with a small controlled experiment.

### §75.1 Smallest discriminating experiments (in priority order — do NOT execute)

**E1 — Trial 3: repeat Trial 2 exactly.** Same substrate (Patch's Workshop / Episode `2b6087d2` / spokesperson `7fad8172` / knowledge / memory / audience directive / target 90 s / both experiment env vars active). One render. Purpose: convert n=1 → n=2 for magnitude stability of the +2 residual. Discriminates whether Trial 2's byte-level preservation and residual magnitude are reproducible or single-sample noise. Cost ~$0.02 + LLM tokens.

**E2 — Non-audience revision trial.** Same substrate as Trial 3 but with `CHARACTER_OS_SOLO_AUDIENCE_HINT_EXPERIMENT` unset (only `CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT` active). Purpose: measure whether revision behaves correctly in the baseline-shape substrate (Trial 1 25467733 shape). Rules out U7. Cost ~$0.02.

**E3 — long_form_ad revision trial.** Any long-form dogfood with `use_knowledge=True` + a duration target that reliably triggers expansion retry. Purpose: closes U4 (largest untested surface). May require a fresh Episode substrate or a scripted long-form topic; needs operator judgement on substrate choice. Cost ~$0.05 (larger duration).

The three experiments together cost less than $0.10 and take a single sitting to run once activation gates are set correctly (see §55).

### §75.2 What the three experiments would NOT close

- **Compression-variant behaviour (U3).** Q-270-15c does not have compression revision plumbing. Testing compression requires a separate Slice 5 to add `_experimental_compression_revision_hint` and wire the compression branch. That is a larger implementation slice.
- **Rivet-substrate + character-voice preservation.** Substrate expansion beyond Patch.
- **Pinned-opener interaction (U5).** Would require an operator-typed pinned opener on the render, testing whether Draft B preserves the pinned first sentence.
- **Draft-B-verification-rejection (U6).** Would require an artificial or fortunate substrate where Draft B trips strict K6.4.

None of these are blockers for a *decision to run E1/E2/E3*; they are additional risks the operator should weigh before a full production promotion.

---

## §76. Q-270-15c vs Q-270-15b sequencing — causal attribution

Slice 2 §32.2 introduced Q-270-15b as a candidate follow-up: soften the corrective_hint's *"Add supporting detail from the knowledge chunks where needed to expand"* clause to something like *"Add supporting detail while preserving the previous draft's vocabulary choices where possible"*. Purpose: test whether the residual +2 at-risk terms are driven by this clause (H2 in Slice 1 §11).

**Do NOT run Q-270-15b before strengthening Q-270-15c evidence.** Reasons:

1. **Attribution symmetry.** If Q-270-15b changes both the corrective_hint text AND we haven't stabilised the revision residual estimate (n=1), any observed reduction cannot be cleanly attributed to the hint change vs the revision mechanism vs single-sample variance.
2. **Two-variable trap.** Trial 2 established a n=1 magnitude estimate. If Q-270-15b runs next and shows +0 residual, we cannot distinguish "the hint change closed it" from "the second revision trial would have shown +0 anyway (regression to mean)."
3. **Q-270-15b requires an implementation edit** (change `_experimental_expansion_revision_hint` text or add a variant). That edit is small but non-trivial. Doing it AFTER n=2 revision evidence gives the operator a defensible baseline against which to measure the hint change.

**Recommended sequence:**

1. E1 (Trial 3, same substrate, same hint) — get n=2 for revision residual magnitude.
2. IF Trial 3 confirms residual (Trial 2 + Trial 3 both show +1 to +3 at-risk terms with strong preservation): move to Q-270-15b under the same substrate. Do this only if E1 supports it.
3. IF Trial 3 shows +0 (revision residual disappears): revision + current hint is already sufficient. Q-270-15b becomes lower priority.
4. IF Trial 3 shows +5+ (revision residual is worse than Trial 2): Trial 2 was lucky; revision is less effective than n=1 suggested. Reconsider before Q-270-15b.

E2 and E3 (§75.1) can run in parallel with E1 without contaminating Q-270-15b's attribution (they change substrate, not the corrective_hint text).

---

## §77. Decision gate

**Recommendation: B — ONE MORE CONTROLLED REVISION TRIAL FIRST.**

Detailed justification for each option:

- **A — Promote revision-based expansion NOW.** REJECTED.
  - n=1 revision evidence insufficient to characterise magnitude stability (§73.2 S1, §73.3 U1-U2).
  - Untested inheritance for `long_form_ad` + standalone-talking-head + baseline-shape (§74.3, U4, U7).
  - Compression-path asymmetry unresolved (§74.4, U3).
  - The byte-level preservation *mechanism* is proven (P3), but the *reliability across contexts* is not.

- **B — One more controlled revision trial first.** RECOMMENDED.
  - E1 (Trial 3 repeat of Trial 2) is the cheapest highest-information move (§75.1).
  - Closes the single most important gap (magnitude stability) with a single render (~$0.02).
  - Preserves attribution for eventual Q-270-15b (§76).
  - Same activation procedure as Trial 2 (§55) — already validated.
  - Trial 2 verdict B stands; E1 tells us whether verdict is stable or Trial 2 was single-sample favourable.

- **C — Broader validation required first.** ACCEPTABLE ALTERNATIVE.
  - E1 + E2 + E3 in one sitting (§75.1). Cost ~$0.10.
  - Trades a session of operator time for closing U1 + U4 + U7 in one pass.
  - Justified if the operator anticipates wanting to promote revision as default before end of month rather than spread across multiple sittings.
  - **Not "required" over B** — B is a strict prefix of C.

- **D — Do NOT promote revision.** REJECTED.
  - Trial 2 evidence unambiguously supports the mechanism (P3, P4, S1).
  - No dimension in §72 shows revision as worse than canonical; observed regression risks (§74) are at semantically-untested surfaces, not at the tested Q-270-15c substrate.
  - Discarding the mechanism now would waste the Slice 3 investment and abandon a demonstrably-better corrective path for the solo_scene audience-conditioned lane.

**Between B and C:** operator preference. If Chris + ChatGPT are willing to spend one sitting on all three follow-up trials, C is more efficient. If they prefer to see one confirmation and pause for interpretation, B is safer.

---

## §78. Smallest recommended next action

**Option B primary recommendation:**

Authorise a **Trial 3 render** — same substrate as Trial 2 (Patch's Workshop / Episode `2b6087d2` / spokesperson `7fad8172` / 90 s / knowledge ON / opener blank / verifier warn) with BOTH experiment env vars active (audience directive `AUDIENCE: general adults with no technical background who are new to AI agents.` + revision experiment on) using the §55 activation procedure exactly as performed for Trial 2.

**Chris + ChatGPT decide.** Do NOT execute without explicit authorisation.

Return artefacts expected from Trial 3 (same as Trial 2):
- Full UUID of the new composition.
- Three activation proofs (worker env-var, log marker, corrective_hint fingerprint).
- Draft A + Draft B verbatim + within-composition diff.
- At-risk terminology count.
- §43 criteria grading.
- Verdict A/B/C/D/E under the same rubric.
- Comparison to Trial 2 (n=1→n=2): does preservation reproduce? does residual reproduce?

If Trial 3 confirms Trial 2, Slice 6 can consider E2/E3 or move to Q-270-15b. If Trial 3 diverges materially, an interpretation slice comes first before any additional experiment.

---

## §79. Explicit list of things NOT changed in Slice 4

- No production source touched.
- No tests touched.
- Writing Contract still v5.
- Q-270-15c plumbing still present + inactive by default (env-gated).
- Both experiment env vars still unset on `main` and in the current shell.
- No render performed.
- No new Composition created.
- No NarrativeMemory promotion. Pool remains 14 remembered + 1 archived.
- No worker restart during Slice 4 (canonical mode from §69 cleanup preserved).
- No schema, no migration, no SPA UI, no dialogue-lane change.
- Q-270-16 (proper_noun) and Q-270-18 (tech_term case) verifier questions remain OUT OF SCOPE.
- Layer 1 first-pass audience-directive reliability remains OUT OF SCOPE for this slice (§53 open question).
- Patch story progression remains OUT OF SCOPE.

---

## §80. Slice 4 commit + push record

- Slice 4 commit SHA: `<pending — populated after commit>`
- Push: `<pending>`
- Local `main == origin/main`: `<verified at commit time>`
- Working tree at Slice 4 close: `<verified clean>`
- Files touched by Slice 4:
  - `docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` — §72–§80 appended (this section)
- **No source, no tests, no evidence sidecar, no schema in Slice 4.**

---

**End of SESSION 271 Slice 4. STOP condition reached. Promotion decision: B — one more controlled revision trial required before promotion. Smallest next action: authorise Trial 3 render (same substrate as Trial 2, §55 activation procedure). Awaiting operator authorisation.**
