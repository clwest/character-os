# SESSION 273 — Product Orientation and Next-Direction Recommendation

**Status:** Documentation-only orientation slice. No source, schema, KnowledgeDocument, persona, NarrativeMemory, Composition, or runtime changes. No candidate direction pre-committed. Chris chooses SESSION 273's actual direction after reviewing this doc.

**Prior context this doc builds on:**
- `docs/design/SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md` §22 (CLOSEOUT — CORRECT_ANCHOR verified in production; knowledge shape demoted to bounded/secondary)
- `docs/design/SESSION_273_HANDOFF.md` (starting brief; no work pre-scheduled)

---

## §1. REPOSITORY / RUNTIME ORIENTATION

### §1.1 Repository state (verified at open of SESSION 273)

| Check | Value |
| --- | --- |
| Branch | `main` |
| Local HEAD | `eda6c95a615265ea0d64ccc066d072ca7c515d5e` |
| `main == origin/main` | ✓ |
| Working tree | clean |
| Last commit | `eda6c95 docs(session-272): record CLOSEOUT commit SHA 0c17b7d in both docs` |
| SESSION 272 CLOSEOUT commit | `0c17b7d` |

### §1.2 Runtime state (verified at open)

| Service | Expected | Observed |
| --- | --- | --- |
| Django `:8010/admin/` | 302 | 302 ✓ |
| Media-engine `:8001/health` | ok/all-mocks-false | `{"status":"ok","service":"adspark-studio","openai_mock":false,"runway_mock":false,"image_gen_mock":false,"any_mock":false,"llm_provider":"openai","llm_model":"gpt-4o-mini"}` ✓ |
| Vite `:5174/` | 200 | 200 (via `localhost`; IPv6 bind) ✓ |
| Django worker PID | listening | pid 12705 ✓ |
| Media-engine PID | listening | pid 12677 ✓ |
| SPA PID | listening | pid 12699 ✓ |
| Experiment env vars (`CHARACTER_OS_*_EXPERIMENT`) | 0 | 0 ✓ |
| Provider mocks | all false | all false ✓ |

Runtime matches SESSION 272 closeout invariants. Nothing has drifted between sessions.

### §1.3 Session 272 evidence pointers (for context; not being re-run)

- `_expansion_hint` production sample sha256: `fccb006dac0c9461d646a7cf552fc56de2acdcd85d01ef9daea746a8e4566dbd`
- Slice G production dogfood Composition: `8cb9e115-d7a9-4af5-ba86-746a5e5bbcc1`
- Nine frozen evidence sidecars under `docs/design/session_272_experiment_data/`

---

## §2. OPERATOR-REACHABLE PRODUCT MAP

Applying the strict distinction:

- **SOURCE IMPLEMENTED** — code exists in the repo.
- **TESTED** — has automated coverage.
- **LIVE VISIBLE** — wired in a URL/router and rendered by a running service (not a dead file).
- **OPERATOR REACHABLE** — a real operator can find and use it via the SPA, not just via `curl` / DB / management command.

Everything below is stated at the *operator-reachable* level unless otherwise noted.

### §2.1 Core substrate — all four levels

| Capability | Source | Tested | Live | Operator-Reachable | Notes |
| --- | --- | --- | --- | --- | --- |
| Universe (create / list / detail / episodes-per-universe) | ✓ | ✓ | ✓ | ✓ | SPA route `/workspace/universes`, `/workspace/universes/:id`. Structural (Universe deletion RESTRICTs children). |
| Character / Teammate / Spokesperson | ✓ | ✓ | ✓ | ✓ | 4-step wizard: identity → portrait → voice → confirm at `/spokespeople/new`. Detail edit at `/spokespeople/:id`. |
| Episode (create / list / detail / cast) | ✓ | ✓ | ✓ | ✓ | `/workspace/universes/:id/episodes`, `/workspace/episodes/:id`. Episode pre-fills composition form with cast + topic (SESSION 262). |
| KnowledgeDocument (upload / list / chunks / universe scope) | ✓ | ✓ | ✓ | ✓ | `/workspace/knowledge`. YouTube extractor exists but silent-failure hazard (memory `project_youtube_ingest_silent_failure`). |
| NarrativeMemory (browse / promote / retrieve) | ✓ | ✓ | ✓ | ✓ | `/workspace/memories` browser + `Promote` button on composition detail. Retrieval is silent (invisible to operator except via consequence). |
| Composition (create / status poll / detail / final asset) | ✓ | ✓ | ✓ | ✓ | `/recipes/:kind` form → auto-nav to `/compositions/:id` status page. |
| Publish bundle (fan-out N platform variants; $0 marginal cost) | ✓ | ✓ | ✓ | ✓ | `/workspace/bundles`, `/workspace/bundles/new`. B14 shipped SESSION 205. |
| Asset library (raw + generated) | ✓ | ✓ | ✓ | ✓ | `/workspace/assets`, `/workspace/videos`. Role taxonomy (TALKING_HEAD / BACKDROP / B_ROLL / COMPOSITE_OUTPUT / etc.). |
| Image generation (Stability, portrait templates) | ✓ | ✓ | ✓ | ✓ | `/images` gallery + spokesperson wizard integration. |
| Campaigns (personalized-video fan-out to recipient list) | ✓ | ✓ | ✓ | ✓ | `/workspace/campaigns`, `/workspace/campaigns/new`. Manual launch only — no scheduler. |
| Team seats / multi-workspace | ✓ | ✓ | ✓ | ✓ | Tier-gated (STARTER=1, PRO=1, AGENCY=5). Existing but never dogfooded end-to-end. |

### §2.2 Recipes actually reachable through `/recipes`

18 live recipes registered in `LIVE_RECIPE_KINDS` (media-engine dispatch table). Grouped:

- **Talking-head family:** `talking_head`, `long_form_ad`, `talking_head_with_backdrop`, `talking_head_polished`, `reels_format`
- **Dialogue:** `dialogue_scene` (2 to N speakers via alternating turns)
- **Cinematic / visual:** `cinematic_visual`, `cinematic_visual_extended`, `storyboard_ad`, `storyboard_voiced`, `image_overlay` (primitive, invoked by composite recipes)
- **Publishing / repurpose:** `recut_teaser`, `publish_variant`
- **Audio-first:** `voice_design`, `multi_lang_dub`, `broll_splice`, `music_bed_pass`
- **Cohost / layouts:** `cohost_layout`, `pip_layout`, `backdrop_layout`

### §2.3 Substrate present in source but NOT operator-reachable

| Capability | Level attained | Gap |
| --- | --- | --- |
| Writing Contract v6 | LIVE (auto-applied every K6 synthesis) | No SPA surface to inspect or version-diff |
| Retrieval lane (universe canon + memory) | LIVE (internal synthesis) | No SPA surface shows retrieved chunks, distances, or memory scores |
| Nine SESSION 262 + SESSION 271 observability fields on `Composition` (`operator_topic`, `synthesis_attempt_count`, `first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `validation_failure_reason`, `synthesis_predicted_seconds`, `render_dispatched_at`, `audience_hint`) | LIVE (immutable-after-first-write, persisted on every render) | Zero SPA visibility. To inspect why a render behaved as it did, operator must open `/admin/` or drop to `manage.py shell` (this is exactly what SESSION 272 slices had to do to gather evidence). |
| Celery beat / recurring tasks | LIVE (`sweep_expired_assets` hourly) | No SPA queue depth / worker health / task history view |
| Realtime avatar (Runway conversational, HeyGen push-to-speak, D-ID) | SOURCE only (schema for `RealtimeSession`; no provider integration; no composition primitive) | Placeholder route `/conversations/:id` exists but not wired |
| Composition remix / batch endpoints | LIVE (backend) | No SPA affordance on composition detail |
| OpenAI token cost tracking | Captured mid-flight in `DialogueResult.tokens_input/output` | Discarded at starter time; not persisted on Composition. Per-render OpenAI cost is not knowable. |
| Retry cost history | Overwritten (SESSION 264 §4.2) | Prior-attempt cost lost when a step retries. |
| Scheduled / recurring publish | NOT IMPLEMENTED | No `PublishBundle` cron; campaigns are operator-launched manually. |
| Cost dashboard per-render | Tier usage meter exists (`/api/billing/subscription/`) | No per-composition or per-day cost breakdown in the UI. |
| Cutaway / B-roll splice into a live talking_head | Backdrop is a separate recipe; `broll_splice` recipe exists but is not composable into `talking_head` at operator level | If the story requires seeing an object mid-scene, operator must build a composite manually. |

### §2.4 NavRail — what Chris actually sees today (11 sections)

`Dashboard · Spokespeople · Knowledge · Transcripts · Scripts · Recipes · Campaigns · Bundles · Videos · Assets · Images`

The Universe/Worlds tile lives on the Dashboard, not the NavRail. `Memories` panel is exposed on `/workspace/memories` and on the Composition detail.

### §2.5 Golden path — idea to finished 90s talking_head video (today, best case)

Assuming the operator already has a Spokesperson and at least one KnowledgeDocument:

1. `/dashboard` → click **Open recipe gallery**
2. `/recipes` → click **Talking Head**
3. `/recipes/talking_head?spokesperson=<id>` — fill topic, tone, optional `audience_hint`, submit
4. Auto-nav to `/compositions/<id>` — poll while status = RUNNING; usually ~60–120 s
5. On COMPLETED: `final_asset` renders inline; **Download** and **Copy link** available
6. (Optional) → `/workspace/bundles/new` → assemble a `PublishBundle` for platform variants

Total: ~8 clicks + wait. This is the shortest currently-supported operator path from a new idea to a distributable clip.

---

## §3. PRACTICAL PRODUCT CONSEQUENCES OF SESSIONS 269–272

Translating the last four sessions into "what can Chris safely dogfood now that he could not confidently dogfood before":

### §3.1 SESSION 269 — Episode-attached solo scenes work

- A `talking_head` can be created inside an Episode (Story Mode) with cast pre-filled from the Episode.
- Composition inherits Episode topic + cast; operator does not have to restate them.
- Practical consequence: **serial episodic content by one character is now a real path**, not a one-off render pattern.

### §3.2 SESSION 270 — Audience-conditioned character performance

- Character OS can adapt *how* a character addresses a listener without changing *who* the character is.
- Verified across four audience-conditioned real-mode renders on tightly-controlled substrate.
- Practical consequence: **audience-scoped talking heads on the same knowledge are safe to attempt**.

### §3.3 SESSION 271 — Writing Contract v6 + `Composition.audience_hint`

- The AUDIENCE-AWARE COMMUNICATION invariant lives in `_solo_scene_contract`.
- `Composition.audience_hint` is persisted and immutable-after-first-write.
- Talking-head recipe form accepts an optional audience_hint text field. Dialogue form does not.
- Practical consequence: **the accessibility layer is character-agnostic** — any teammate benefits automatically for `solo_scene`.

### §3.4 SESSION 272 — CORRECT_ANCHOR fix + knowledge-shape audit

- `_expansion_hint` no longer contains the false-anchor `REWRITE THE SAME NARRATIVE ABOVE`.
- Slice E n=5 evidence: 75% attractor-family reduction.
- Slice G production dogfood (Composition `8cb9e115`): zero attractor leakage even when the strongest attractor was verbatim in the retrieved chunk; Rivet identity *strengthened* by corrective expansion.
- Practical consequence: **duration-driven corrective expansion is now a net-positive character-native-elaboration tool**, not a canonical-regression risk. Long-form scripts can lean on corrective expansion instead of fighting it.

### §3.5 What Chris can safely dogfood now (that he could not before)

- Two-character dialogue Episodes in existing Universes (dialogue_scene + Episode + NarrativeMemory retrieval — no scene-level anti-flatten still needed).
- Long-form solo_scene renders that rely on corrective expansion to reach target duration.
- Audience-shifted talking heads (technical vs beginner vs stakeholder) on identical knowledge.
- Fresh characters in fresh domains, without a knowledge-shape rewrite being a prerequisite.
- Publishing a completed talking_head via `PublishBundle` fan-out.

### §3.6 What has NOT changed / still limits Chris

- Composition observability fields are captured but invisible in the UI.
- Realtime conversational avatars are still schema-only.
- No B-roll or cutaway insertion into a live talking_head from the operator surface.
- No scheduling / no queue dashboard.
- Per-render cost breakdown is not surfaced.
- YouTube ingest silent-failure hazard remains (memory `project_youtube_ingest_silent_failure`).

---

## §4. UNRESOLVED PRODUCT & STORY THREADS

Presented as *inventory*, not as prioritized work.

### §4.A Patch begins an Agent experiment (existing narrative arc)

- Patch has repeatedly researched AI agents and stopped at the point of wanting to try one (5+ historical renders).
- Current Character OS machinery *does* naturally support the next beat: an Episode where Patch actually starts the experiment, likely with Rivet as scene partner.
- Substrate assessment: **saturated.** Memory `project_patch_ai_agents_substrate_saturated` flags this substrate as informationally exhausted for architecture-level experiments. Another Patch/AI-Agents render has diminishing signal.
- Story-continuity assessment: high. Chris and viewers get the payoff of a long-running arc.
- Distinction matters: dogfooding this **for the story** is genuinely valuable; dogfooding this **as a diagnostic experiment** is not.

### §4.B Character expansion inside Patch's Workshop (Ruby / Mason / other)

- Adding a third character to Patch's Workshop tests: multi-character continuity across renders, private-memory epistemics (does a NarrativeMemory anchored to Rivet leak into Ruby's script?), relationship formation over multiple episodes, audience adaptation across different character voices, and Universe-history coherence.
- Machinery: 4-step Spokesperson wizard exists. Cast can be added via `/workspace/universes/:id`. No new code.
- Substrate assessment: **partially fresh** (new character, saturated domain).

### §4.C Fresh character / new-business dogfood (bakery fox, coffee-shop bear, etc.)

- Tests whether SESSION 270–272 generalizes beyond Patch/Rivet — i.e., whether Writing Contract v6, CORRECT_ANCHOR, audience_hint, Episode + solo_scene, and NarrativeMemory promotion work on a domain that is not AI/software/reproducibility.
- Substrate assessment: **fully fresh** (satisfies substrate-hygiene rule from SESSION 272 §22.5).
- Operator commitment: create Universe + Spokesperson + at least one KnowledgeDocument + one Episode + one render. Estimated 30–60 minutes of operator time; zero code.
- Falsifiable — either the golden path works cleanly, or it exposes friction that saturated Patch/Rivet substrate has been hiding.

### §4.D Visual storytelling / cutaway / B-roll operator reachability

- Backend: `cinematic_visual`, `cinematic_visual_extended`, `storyboard_ad`, `storyboard_voiced`, `broll_splice`, `image_overlay`, backdrop chains — all live.
- Operator: recipe gallery exposes cinematic recipes; `image_overlay` is a primitive not a standalone recipe; there is no operator affordance to inject a B-roll cutaway *into a live talking_head render*.
- Real gap: not "we don't have visuals" — it's "we have visuals but they don't compose into the primary talking-head flow at the operator level".

### §4.E Real content / distribution / team throughput

- `PublishBundle` fan-out works ($0 marginal cost — ffmpeg only).
- Team seats (Agency=5) exist but have not been dogfooded end-to-end.
- No scheduler, no unified queue dashboard, no per-render cost UI.
- OpenAI token cost NOT persisted on Composition (discarded at starter time). Retry cost overwrites prior-attempt cost.
- Distance from "several character teams producing multiple daily videos": **architecturally close, operationally not there**. Ship-blockers: scheduler + queue view + real cost visibility.

### §4.F Other repository-derived opportunities

- **Composition observability panel** — the 9 SESSION 262 + SESSION 271 fields are captured on every render but zero of them are visible in the SPA. The evidence Chris used SESSION 272 to prove CORRECT_ANCHOR was gathered manually via `manage.py shell`, because the SPA has no view of it. This is the single largest source-vs-operator-reachable gap in the repo today.
- **Compression-hint analog fix** — `_compression_hint` still contains `REWRITE THE SAME NARRATIVE BELOW` (same class of false anchor as pre-Slice-F `_expansion_hint`). Not experimentally evaluated. Sha256 for regression pin: `78e40309734620471aa3858269312d600fe9de8f4cd7b1d9f9e670a95e9bf3dd`.
- **Q-270-16 verifier false positives** — sentence-initial capitalized adverbs (`Well`, `Very`, `Briefly`, `Carefully`) misclassified as proper nouns. Slice G added `Briefly` + `Carefully` to Composition `8cb9e115.verification_warnings` as durable evidence. Standalone verifier-quality slice.
- **YouTube ingest silent-failure** (memory `project_youtube_ingest_silent_failure`) — reports "processed" but trafilatura captures nothing; needs detect-reject + per-host extractor.
- **REPO RED Shape β** — REPO RED KnowledgeDocument `ee7b7e5c` mixes canned quotes, anti-scripts, content-strategy directives, and audience prescriptions with factual claims. Distinct authoring pathology from what CORRECT_ANCHOR addressed. Preserved as future architectural concern.

---

## §5. OPERATOR-EXPERIENCE OBSERVATIONS (evidence-backed friction)

- **Backend capability routinely exceeds SPA reachability.** Composition observability, retrieval scoring, Writing Contract version diff, remix / batch, realtime avatar, scheduled publish. Everything necessary to see and control renders exists in Django models and API endpoints; almost none of it is rendered.
- **`audience_hint` asymmetry.** Talking-head form exposes it; dialogue-scene form does not. WCV6 lives in `_solo_scene_contract` only. Multi-character scenes cannot yet be audience-shifted through the operator surface.
- **`audience_hint` is inferrable but asked.** In an Episode-attached solo scene, the audience is often already implicit in the Episode topic. The system asks anyway.
- **NavRail is 11 items long.** Universe/Worlds sits on the Dashboard tile, not the NavRail. New operators may miss the Worlds surface entirely.
- **Composition detail is a status page, not an inspection page.** Chris can watch a render finish, but if it went sideways he cannot see `first_pass_synthesis`, `corrective_hint`, or `verification_warnings` without leaving the SPA.
- **Throughput observability is nonexistent.** No queue depth, no worker health, no daily-cost line, no "yesterday I rendered N videos costing $X". The tier meter (`videos_used / limit`) is the only surface.
- **The knowledge-ingestion path silent-fails on YouTube URLs.** Real hazard for a Chris workflow that starts from a YouTube video.

None of these are proposals; they are observations of friction that show up in the current operator path.

---

## §6. CANDIDATE DIRECTION MATRIX

Presented in no particular order. Ranking below in §7.

| # | Candidate | Product value | Learning value | Operator value | Impl cost | Rabbit-hole risk | Dogfood-first possible? | Substrate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Patch begins an Agent experiment (dialogue Episode with Rivet) | Medium (story payoff) | Low (same substrate) | Medium | Zero (no code) | Low | ✓ | SATURATED |
| 2 | Add a third character (Ruby / Mason) to Patch's Workshop | Medium-High | High (multi-char continuity untested) | Medium | Zero code; 30–60 m operator | Low-Medium | ✓ | Partially fresh |
| 3 | Fresh character / new business dogfood (bakery fox etc.) | High (generalization proof) | Very High | Medium (30–60 m operator) | Zero code | Low | ✓ | **FULLY FRESH** |
| 4 | Operator affordance for cutaway / B-roll splice into talking_head | Medium | Medium | Medium | Medium (SPA + starter wiring) | Medium (visual regression) | Partial (existing recipes can dogfood component; full flow needs code) | Untested-substrate visual |
| 5 | Multi-team throughput surface (scheduler + queue + per-day cost) | High (long-term) | Low | High | High | High | ✗ (requires build) | Existing capability |
| 6 | Composition observability panel — surface the 9 captured fields | High (unlocks self-serve audit) | High (turns future sessions from shell-based forensics into SPA-based inspection) | High | Medium (SPA only; all data already persisted) | Low | ✗ (requires build) | Existing capability |
| 7 | Compression-hint analog fix (`_compression_hint` false-anchor) | Medium | Medium | Low | Low (Slice E analog + dogfood) | Low | Partial | Untested-path replicate |
| 8 | Q-270-16 verifier false-positive fix | Low | Low | Low | Low | Low | ✗ | Existing capability |
| 9 | YouTube ingest silent-failure fix | Medium | Low | Medium | Medium | Low | ✗ | Existing capability |

**Interpretation:**

- The three candidates that satisfy *dogfood before code* AND are cheap-to-attempt are #1, #2, #3.
- Of those three, #3 (fresh character / fresh business) has the highest learning value and the lowest substrate risk (fully fresh substrate, satisfies SESSION 272 §22.5 hygiene).
- #6 (Composition observability panel) is the highest-leverage *build* candidate — but it should not preempt a dogfood if a dogfood can produce evidence first.
- #5 is expensive and open-ended; the throughput question deserves a real product decision before code.
- #7, #8, #9 are small hardening slices — reasonable to schedule but not the natural SESSION 273 headline.

---

## §7. RECOMMENDED NEXT FALSIFIABLE QUESTION

**Recommendation (dogfood first, no code first):**

> Does the current Character OS — Universe creation, 4-step Spokesperson wizard, KnowledgeDocument upload, Episode creation, `talking_head` with `audience_hint`, Writing Contract v6, CORRECT_ANCHOR, NarrativeMemory promotion, and PublishBundle — work end-to-end for a *completely new character in a completely new business* built from zero by the operator? Or does the fresh substrate expose friction / gaps that saturated Patch–Rivet substrate has been hiding?

### Why this beats the alternatives

- **Dogfood-first.** No code required before the question can be asked. The whole point of SESSION 269–272 was to make this path safe; SESSION 273 is the natural moment to prove it.
- **Fresh substrate.** Satisfies SESSION 272 §22.5 hygiene. Every SESSION 272 substrate assumption is quarantined.
- **Falsifiable.** Either the golden path (§2.5) completes cleanly on a fresh Universe + Spokesperson + Knowledge + Episode + render + publish bundle, or it produces evidence about a specific gap. Both outcomes are informative.
- **Beats #1 (Patch Agent experiment):** Story-valuable but substrate is saturated; no diagnostic-experiment value.
- **Beats #2 (third-character Workshop):** Cheaper substrate hygiene than #1 but still shares the Workshop domain; fresh-domain evidence has strictly higher generalization value.
- **Beats #6 (observability panel):** #6 is the correct *build* answer to "we cannot audit our own renders", but building it now would preempt a legitimate dogfood question that costs no code. If the fresh-substrate dogfood surfaces a render-audit need, #6 becomes better-informed.
- **Beats #5 (throughput surface):** Throughput surface is high-ROI long-term but ~week-scale build; deserves a real product decision, not an incidental slice.
- **Beats #4 (B-roll operator affordance):** Real visual gap, but the dogfood tests it naturally — if the fresh business needs to *show* a product / action / location, the friction shows up on the render itself.
- **Beats #7 (compression-hint):** Small hardening; better run after Chris confirms next arc, so bounded scope is easier to plan.

### If the dogfood answers "yes, the fresh-substrate path works cleanly"

Then Chris has evidence that the SESSION 270–272 arc has genuinely generalized. Natural follow-ups:
- Second fresh character in the same fresh business (relationship formation on fresh substrate).
- Composition observability panel (#6) — turn future dogfoods from shell-forensics into SPA-inspection.

### If the dogfood answers "no, it exposes friction X"

Then the friction is now the highest-signal work item, and Chris has real evidence for scoping it — rather than SESSION 273 pre-committing to a build in the dark.

**Chris should choose one small fresh-business scope before the dogfood begins** — a character concept, a business domain, a small starting knowledge corpus. That scope decision is intentionally left to Chris, not this document.

---

## §8. EXPLICIT NON-CHANGES DURING THIS SLICE

- No source code changed.
- No Django migrations added.
- No `_expansion_hint` / `_compression_hint` / synthesis / retrieval / K6 changes.
- No Writing Contract version bump.
- No KnowledgeDocument, Teammate, Episode, Composition, NarrativeMemory, PublishBundle, or Asset rows created or modified.
- No SPA components edited.
- No provider mock toggled.
- No experiment env vars set.
- `Q-270-15c` gate remains OFF and untouched.
- `Q-270-16` remains open and unscheduled.
- SESSION 272's CORRECT_ANCHOR production fix is preserved byte-for-byte (verified via `_expansion_hint` sha256 in §1.3).
- No SESSION 273 direction pre-committed. Chris chooses.

---

## §9. ORIENTATION EVIDENCE COMMIT

- Commit SHA: recorded in §10 at commit time.
- Runtime health: unchanged from SESSION 272 CLOSEOUT (§1.2).
- Repo health: `main == origin/main`, clean tree.

---

## §10. COMMIT PROVENANCE

- SESSION 273 orientation doc commit: **`96ad5d7`** — `docs(session-273): product orientation + next-direction recommendation`
- Pushed to `origin/main` at close of orientation slice.

---

**End of SESSION 273 orientation document. No code changed. No direction pre-committed. Chris decides SESSION 273's actual work item after reading this and §22 of the SESSION 272 audit.**

---

## §11. PRE-DOGFOOD RUBY / MASON SUBSTRATE AUDIT

**Status:** Audit-only. No Ruby / Mason / Universe / KnowledgeDocument / Episode / Composition / NarrativeMemory data was created, modified, or promoted during this section. No source, schema, or runtime changes.

**Motive:** SESSION 273's §7 recommendation was a fresh-substrate dogfood (new character + new business). Chris then remembered that two existing characters — **Ruby** (fox / bakery) and **Mason** (bear / coffee) — may already satisfy the fresh-domain requirement without creating another character from scratch. This section is the mechanical evidence check.

**Raw evidence sidecar:** `docs/design/session_273_experiment_data/01_ruby_mason_substrate_audit.json` (1,489,060 bytes; JSON dump of both Teammate records + full workspace retrieval env; produced by `scripts/session273_substrate_audit.py`, which is a read-only Django script).

### §11.1 Both characters resolved

| Field | Ruby | Mason |
| --- | --- | --- |
| Full UUID | `5875a7b4-cf39-433d-89b3-4e34a89a5208` | `28b9a7ea-8230-4463-8b0d-4ebfabfe11ec` |
| Name | Ruby | Mason |
| Workspace | `4ce5486d-35a4-4bee-8745-38004adb33bc` | (same) |
| `universe_id` | `None` | `None` |
| Status | `ready` | `ready` |
| Created | 2026-07-23 20:23:57 UTC | 2026-07-23 17:42:41 UTC |
| Updated | 2026-07-23 20:24:27 UTC | 2026-07-23 17:43:20 UTC |
| Seconds create → last update | 30.1 | 39.6 |
| `runway_avatar_id` | `771a012d-…` (`ready`) | `1443cca1-…` (`ready`) |
| `voice_id` | `georgia` | `david` |
| `visual_subject` | Anthropomorphic red fox / master baker / neighborhood bakery owner | (bear / coffee-shop owner — persisted; see sidecar) |

**Modification-after-creation window:** both characters were last written within ~40 s of creation — consistent with wizard finalization (portrait + voice completing). Neither has been substantively edited since 2026-07-23. Both were created **~26 days before** SESSION 269 opened. That timing is favorable for a "generalization" test: their identity/persona was authored *before* Sessions 269–272 taught us anything, so they cannot have been tuned in response to those lessons.

**Both are in the SAME workspace as canonical Patch's Workshop.** This is critical (see §11.5).

### §11.2 Identity / persona fields

| Field | Ruby | Mason |
| --- | --- | --- |
| `business_brief` | **330 chars** — Fox & Flour Bakery: sourdough / handcrafted pastries / seasonal desserts / custom celebration cakes / locally sourced / small-batch / community gathering | **408 chars** — Mountain Peak Coffee Roasters (Fort Collins, CO): ethically sourced single-origin + blends / small batches / online + farmers markets + wholesale / brewing equipment / gift subscriptions / seasonal blends |
| `who_you_help` | **empty** | **empty** |
| `what_you_sell` | **empty** | **empty** |
| `desired_feeling` | **empty** | **empty** |
| `tone_archetype` | `friend` | `friend` |
| `personality` | 338 chars — Warm/cheerful/caring, loves fresh bread from oven, knowledgeable without technical | 243 chars — Friendly/knowledgeable/approachable, explains coffee without elitism |
| `character_point_of_view` | **empty** | **empty** |
| `voice_signature_phrases` | **empty** | **empty** |
| `voice_avoid_phrases` | **empty** | **empty** |
| `always_emphasize` | **empty** | **empty** |
| `never_say` | **empty** | **empty** |
| `voice_energy / humor / directness` | defaults | defaults |
| `portrait_path` | present (avatar prepared) | present |

Both are **wizard-default characters** — only the required fields (name, business_brief, personality, tone, portrait, voice) are populated. The rich persona fields Rivet and Patch carry (`character_point_of_view`, `voice_signature_phrases`, `voice_avoid_phrases`, `always_emphasize`, `never_say`) are **not present**. This regime is *more representative* of a real new operator's first render than the highly-authored Patch/Rivet substrate — a distinct virtue for the SESSION 273 generalization question.

### §11.3 Where business_brief participates in synthesis

Traced through `character_os.script_synthesis._build_factual_basis_section` (`shell/character_os/script_synthesis.py:773–841`):

> §1 FACTUAL BASIS — "The ONLY sources capable of supporting factual claims. Every factual claim in the script must trace back to content in this section."
>
> Contents:
> - `BUSINESS SHAPE: {business_brief}`
> - `AUDIENCE: {who_you_help}` (skipped if empty)
> - `OFFERING: {what_you_sell}` (skipped if empty)
> - `KNOWLEDGE CHUNKS: …` (retrieved from `retrieve_for_teammate`)
> - `--- EPISODE / NARRATIVE MEMORY …` (SESSION 269 §10; solo talking_head with Universe-scoped memory)
>
> §2 CHARACTER VOICE (built by `_build_character_voice_section`) is explicitly labelled *"NOT facts. Never verified against K6.4."* and contains `personality`, `character_point_of_view`, `tone_archetype`, voice axes, and `voice_signature_phrases`.

**Conclusion:** `business_brief` is treated by K6 as **factual grounding**, not persona. Every "sourdough / seasonal desserts / custom celebration cakes / locally sourced" claim in Ruby's brief will be verifier-eligible. Ruby therefore has "no KnowledgeDocument" **but is not knowledge-empty** — she carries ~330 chars of factual grounding built into her identity. Mason likewise carries ~408 chars of coffee-shop facts (including a specific geography — Fort Collins, Colorado).

`personality` (Ruby's warmth, Mason's approachability) enters §2 only and is exempt from K6.4 verification.

**Boundary summary for both:** identity/persona → §2 (voice); `business_brief` → §1 (fact); `who_you_help` / `what_you_sell` → §1 (fact) *if populated* (both are empty). This is not a bug — it's the design (`W11.y SESSION 175 — personality / business_brief split`; personality = HOW the avatar speaks, business_brief = WHAT the business is).

### §11.4 Relationship / Universe / story audit

| Attachment | Ruby | Mason |
| --- | --- | --- |
| Universe (`teammate.universe_id`) | `None` | `None` |
| `EpisodeCast` rows | 0 | 0 |
| Episodes | 0 | 0 |
| Compositions where `spokesperson=t` | **0** | **1** (see §11.6) |
| `NarrativeMemory` via `source_composition.spokesperson` | 0 | 0 |
| Witnessed `NarrativeMemory` (`t.witnessed_narrative_memories`) | 0 | 0 |
| `PersonalizedCampaign` rows | 0 | 0 |
| `related_assets` (portrait/voice bake artifacts excluded from render lineage) | 0 | 0 |
| Direct `KnowledgeDocument` m2m (`t.knowledge_documents`) | 0 | 0 |
| Universe-scoped `KnowledgeDocument` (via `teammate.universe`) | 0 (Universe is `None`) | 0 (Universe is `None`) |

**Both are story-empty**: no Universe attachment, no Episode participation, no NarrativeMemory involvement, no campaigns, no directly-attached knowledge. Mason has one composition scar (§11.6).

### §11.5 Hidden retrieval contamination — the load-bearing finding

Because both characters live in the same workspace as Patch's Workshop, and because `retrieve_for_teammate` (`shell/apps/embeddings/retrieval.py:159`) branches on `spokesperson.universe_id`, the retrieval envelope for a Ruby-or-Mason render **is not the empty set that "no KDs" implies**.

**Retrieval logic — verbatim from source:**

```python
if spokesperson.universe_id is None:
    qs = qs.filter(document__universe__isnull=True)
else:
    qs = qs.filter(document__universe_id=spokesperson.universe_id)

qs = qs.filter(
    Q(document__spokespeople__isnull=True)
    | Q(document__spokespeople=spokesperson)
)
```

Applied to the workspace `4ce5486d-…` today, **16 total KnowledgeDocuments** exist:

- **3** are Universe-scoped to `Patch' Workshop` (`56d16b63`) — invisible to Ruby/Mason because `spokesperson.universe_id is None ⇒ document.universe IS NULL`.
- **13** are workspace-only (`universe IS NULL`) — candidate for retrieval. Of those:

| Doc | Title | Spokesperson m2m | Visible to Ruby/Mason? |
| --- | --- | --- | --- |
| `90ad200c` | Riggs | *(empty)* | ✗ **YES — leakage risk** |
| `ee7b7e5c` | REPO RED — AUTOMOTIVE FINANCING & SOCIAL CONTENT KNOWLEDGE | bound to Repo Red | no |
| `8c6f0c14` | TANK — AUTOMOTIVE FINANCING CONTENT KNOWLEDGE | *(empty)* | ✗ **YES — leakage risk** |
| `56fcdb9a` | Surgo Financing | bound to Mike | no |
| `520e350c` | Surgo_Automotive_Mike_Knowledge_Base | bound to Mike | no |
| `e284edc9` | Penny Riverstone Knowledge Base | bound to Penny | no |
| `7ecde40b` | Tulsi — Core Identity and Public Purpose | *(empty)* | ✗ **YES — leakage risk** |
| `0088f31f` | Helping Customers Find Their Next Read | *(empty)* | ✗ **YES — leakage risk** |
| `c408656d` | Supporting Local Authors | *(empty)* | ✗ **YES — leakage risk** |
| `7f41d8e3` | Bookstore Events | *(empty)* | ✗ **YES — leakage risk** |
| `b58efd31` | Children's Reading | *(empty)* | ✗ **YES — leakage risk** |
| `e37ea174` | How We Recommend Books | *(empty)* | ✗ **YES — leakage risk** |
| `aa90d895` | About Hearth & Hollow Books | *(empty)* | ✗ **YES — leakage risk** |

**Nine unbound workspace-only KDs are retrieval-visible to Ruby/Mason today.** Six of them are one coherent bookstore-character corpus ("Hearth & Hollow Books" — Helping Customers Find Their Next Read / Supporting Local Authors / Bookstore Events / Children's Reading / How We Recommend Books / About Hearth & Hollow Books). For a bakery topic like "sourdough starter" or "custom celebration cakes", cosine similarity should score them low. But for community-adjacent topics ("welcoming customers", "seasonal events", "local suppliers", "recommendations") the bookstore corpus could actually score competitively. This is *hidden retrieval contamination* — a rendered Ruby or Mason clip today could quote another character's KD verbatim through the retrieval lane.

**Memory lane:** `retrieve_universe_memory` returns `[]` immediately when `universe is None` (`retrieval.py:484`). Ruby/Mason renders **would retrieve zero NarrativeMemory** by construction — the 15 workspace memories are all Universe-scoped to Patch's Workshop.

**Mitigation available at operator level:** attach Ruby / Mason to a *fresh* Universe before their first render. That flips retrieval to `document.universe = <new_universe>` and structurally excludes every unbound workspace KD in a single move. No data-mutation on other characters required. This matches SESSION 261 Universe-attach discipline and is required anyway for Episode participation (`EpisodeCast.clean()` rejects teammates with no Universe).

### §11.6 Mason's one prior composition — bounded, zero-effect

| Field | Value |
| --- | --- |
| `id` | `6f2132f5-1f5d-482d-be0d-d870a155b81f` |
| `template_kind` | `auto_script` |
| `status` | `failed` |
| `name` / `operator_topic` | `Good Morning` / `''` |
| `writing_contract_version` | `0` (no contract applied — pre-dispatch failure) |
| `mock_mode` | `False` |
| `render_dispatched_at` | `None` |
| `cost_actual_micros` | `0` |
| `memory_ids` | `[]` |
| `knowledge_chunk_ids` | `[]` |
| `synthesized_brief` length | 34 chars |
| `final_asset_id` | `None` |
| `error_message` | *"Task did not execute because the background worker was offline. Recreate the composition to retry."* |
| `created_at` | 2026-08-07 14:33:23 UTC |

**Zero substrate consequences.** The composition never reached synthesis, never called a provider, never persisted an Asset, never created a memory, never consumed a knowledge chunk. It is a scar row — historically preserved but with no propagating effect on any other object. Mason's substrate is *not* meaningfully contaminated by it. Documented as baseline.

### §11.7 Contamination classification

**RUBY — Category A (FULLY CLEAN FRESH-DOMAIN SUBSTRATE).**
Zero composition history, zero cast, zero memory, zero campaign, zero asset. Wizard-authored identity from 2026-07-23. Fresh business (bakery) that is domain-independent from Patch/Rivet/Mike/Penny/Repo Red/Hearth & Hollow. The 9-KD workspace retrieval leak (§11.5) is fixed at operator level by attaching to a fresh Universe before the first render.

**MASON — Category B (CLEAN ENOUGH WITH DOCUMENTED BASELINE).**
Identical clean profile to Ruby *except* for the one failed pre-dispatch composition (§11.6). That row had zero downstream effect. Documented, freezable as baseline. Same retrieval-leak mitigation applies. Domain-independent (Fort Collins specialty coffee).

**Important nuance repeated:** the fact that both characters predate SESSION 269 is *strengthening*, not contaminating. Their identity/persona was not authored in response to what Sessions 269–272 taught — so a successful render on them is stronger evidence of generalization than a character invented today.

### §11.8 Ruby vs Mason comparison

| Dimension | Ruby | Mason |
| --- | --- | --- |
| Freshness | Category A (no history) | Category B (1 zero-effect failed row) |
| Domain independence from Patch/Rivet | Bakery — fully independent | Specialty coffee — fully independent |
| Character-configuration completeness | Wizard-default (business_brief + personality + tone + portrait + voice) | Wizard-default (same shape) |
| `business_brief` length as §1 factual grounding | 330 chars, no geography | 408 chars, specific geography (Fort Collins, CO) |
| Retrieval leak (unbound workspace KDs visible today) | 9 KDs — same 9 as Mason | 9 KDs — same 9 as Ruby |
| Prior render history | zero | one, zero-effect (§11.6) |
| Universe attachment needed before Episode | yes | yes |
| Portrait / voice ready to render | yes (`ready` / `ready`) | yes (`ready` / `ready`) |
| Ability to exercise `talking_head` + `audience_hint` | ✓ | ✓ |
| Ability to exercise WCV6 | ✓ | ✓ |
| Ability to exercise CORRECT_ANCHOR (if corrective expansion fires) | ✓ | ✓ |
| Ability to exercise NarrativeMemory (post first render) | ✓ | ✓ |
| Ability to exercise Episode + PublishBundle | ✓ (after Universe attach) | ✓ (after Universe attach) |
| Ability to exercise dialogue_scene | ✗ (no partner) | ✗ (no partner) |
| Natural visual-storytelling potential (§4.D of orientation) | HIGH — bakery craft has natural B-roll (dough / oven / decoration) | MEDIUM — coffee craft has some visual craft (roasting / brewing) but less varied |
| Operator effort to bring to first render (Universe + KD + Episode + render) | ~30–60 min | ~30–60 min |
| Failure interpretability | maximally clean baseline | one baseline scar to explicitly discount |

**Recommendation: RUBY primary; MASON as sequential companion if Ruby's render succeeds cleanly.**

Reasoning:
- Both are equally suitable in aptitude and independence. Ruby edges out on maximum-cleanliness (zero prior comp) and marginally-richer visual-story potential.
- A **single dogfood** on a single character can never distinguish "SESSION 270–272 generalizes" from "we got lucky on one character". The strongest possible evidence is *Ruby succeeds → Mason succeeds independently*.
- Doing both sequentially (not in parallel) preserves the ability to abort or redesign after Ruby if she surfaces a real problem — avoiding the SESSION 272 pattern of committing to a multi-slice arc before seeing evidence.
- If Chris only has appetite for one, do Ruby.
- **NEITHER — CREATE NEW** is not recommended: Ruby/Mason already satisfy the fresh-domain requirement, and using them costs less operator time than creating a third fresh character.

### §11.9 Proposed dogfood protocol (design — DO NOT EXECUTE without Chris authorizing)

**Design principle:** each stage runs as its own micro-slice; the render either succeeds cleanly or produces evidence that shapes the next stage. No stage is forced to fire subsystems it doesn't need. Do NOT try to exercise everything in one render.

**Slice α — Ruby Universe + KnowledgeDocument attach (operator work only).**
1. Create a fresh Universe: `Fox & Flour Bakery` in workspace `4ce5486d-…`. Blank memory / no cast.
2. Attach Ruby to the new Universe (`teammate.universe_id = <new_id>`). This is a Universe-attach mutation on the *Ruby* row — allowed only inside Slice α once Chris authorizes; SESSION 273's §11 audit itself does not perform it.
3. Author **one** KnowledgeDocument in the Universe. See §11.10 for content guidance. Ingest through the SPA (`/workspace/knowledge`) so the ingestion path is exercised the way a real operator would use it.

**Slice β — Ruby's first `talking_head` render (dogfood).**
1. Create an Episode in the Universe. Give it a topic Chris genuinely wants Ruby to talk about (any real bakery topic — the point of the dogfood is authenticity, not diagnostic control).
2. From `/recipes/talking_head?episode=<id>` fill: `audience_hint` (a real listener descriptor — e.g., "first-time customers who walk in curious but don't know sourdough from a boule"). Requested duration 60–90 s.
3. Render **real-mode**. All mocks off. Media-engine hitting real Runway / OpenAI.
4. Do NOT retry, mock, or tune if the first render surfaces something interesting. Preserve the specimen.

**What to observe (not steer):**
- Does `retrieve_for_teammate` return the Ruby KD chunks? Any leakage from the 9 unbound workspace KDs?
- Does Writing Contract v6 land (`writing_contract_version == 6`)?
- Does `audience_hint` persist on the Composition and register in synthesis?
- Does corrective expansion fire (`synthesis_attempt_count == 2`)? If yes: does the `corrective_hint` contain `EXPAND YOUR SCRIPT` (CORRECT_ANCHOR active) and NOT `REWRITE THE SAME NARRATIVE ABOVE`?
- Does the accepted brief cite bakery facts from `business_brief` (§1 FACTUAL BASIS pathway)?
- Does the verifier flag anything (`verification_warnings`)? Any Q-270-16 false positives? Any true factual claim rejections?
- Is the accepted brief in-character (per Ruby's minimal `personality`)? Does the absence of `character_point_of_view` / `voice_signature_phrases` produce noticeably-generic output vs Patch/Rivet?

**Slice γ (only if Slice β completes cleanly) — NarrativeMemory decision + optional second render.**
- Review Composition detail. Is there anything worth promoting to NarrativeMemory (e.g., "Ruby introduced herself and Fox & Flour to first-time customers")? Promote or decline explicitly.
- If a second Episode is warranted for continuity (a story beat that would use the first render as backstory), render it — with or without promoted memory.

**Slice δ (only if δ is authorized) — PublishBundle.**
- Assemble a small `PublishBundle` for platform variants from the first (and optionally second) render. Confirm the bundle flow closes the loop from idea → distributable clips.

**Slice ε — Mason companion.**
- Only after Ruby's arc produces a clean render or a well-understood failure, repeat Slices α–γ independently for Mason.
- If Ruby exposes a specific gap, decide whether Mason's arc should be identical (independent replication) or intentionally probing (targeted at the exposed gap).

### §11.10 Knowledge-document authoring guidance (design — DO NOT AUTHOR YET)

The intent is a KnowledgeDocument shaped like what a real bakery owner would upload — not a document engineered around SESSION 272 findings.

**Include** (author naturally, no length target):
- What Fox & Flour sells (bread, pastries, celebration cakes) with enough specifics for genuine talking-head anchors.
- Something about sourcing / suppliers if Ruby would credibly say it.
- A few operating rhythms (baking schedule, farmers-market days, seasonal shifts) if realistic.
- Any origin / personal-motive material the character would talk about naturally.

**Explicitly AVOID** (to prevent pre-baking SESSION 272 lessons into the specimen):
- Do NOT author *paired canonical + accessible paraphrase* per section (Option D). Slice C at n=5 did not replicate its effect; using it here would leak that experiment into the generalization test.
- Do NOT deliberately reduce dense-enumeration density; author normally. Lexical gravity was demoted to bounded/secondary in SESSION 272 §22.2.
- Do NOT hand-optimize sentence phrasing to avoid strong attractors like *"where the behavior first becomes incorrect"*. That's Rivet-domain phrasing; if Ruby's domain has natural attractors, they belong in the doc as-authored.
- Do NOT pre-populate `who_you_help` / `what_you_sell` on Ruby to give §1 extra grounding. Leaving them empty tests the minimum-config real-world path.
- Do NOT backfill `character_point_of_view` / `voice_signature_phrases` / `always_emphasize` / `never_say` on Ruby. Same reason.
- Do NOT ingest YouTube URLs during Slice α (`project_youtube_ingest_silent_failure` memory — silent-failure hazard).

**Explicitly optional:**
- Whether the doc should include a short "how Ruby usually talks about our sourdough" paragraph (persona-adjacent factual content). Leave to Chris; either choice is a valid test.

### §11.11 Explicit non-changes during §11

- No Ruby modification (fields, avatar, voice, universe, m2m).
- No Mason modification.
- No new Universe created.
- No new KnowledgeDocument created or ingested.
- No new Episode created.
- No new Composition created; no render dispatched.
- No new NarrativeMemory created or promoted.
- No spokesperson m2m mutation on any of the 9 unbound workspace KDs (leak is *reported*, not fixed).
- No source code change; no Django migration.
- No SPA change.
- No runtime restart; no worker restart.
- No experiment env var set; no provider mock toggled.
- Mason's failed composition `6f2132f5` remains untouched.
- All 16 workspace KDs remain as-authored.
- All 15 NarrativeMemory rows remain as-authored.
- Patch/Rivet substrate remains untouched.

### §11.12 §11 return values

- **Ruby full UUID:** `5875a7b4-cf39-433d-89b3-4e34a89a5208` — **Category A: FULLY CLEAN FRESH-DOMAIN SUBSTRATE**.
- **Mason full UUID:** `28b9a7ea-8230-4463-8b0d-4ebfabfe11ec` — **Category B: CLEAN ENOUGH WITH DOCUMENTED BASELINE** (one failed pre-dispatch composition; zero downstream effect).
- **Hidden retrieval contamination?** YES for both — 9 unbound workspace-only KnowledgeDocuments (Riggs, Tank, Tulsi, and six Hearth & Hollow Books docs) are cosine-visible to any Ruby/Mason render today. Cleanly mitigated by attaching each character to a fresh Universe before their first render.
- **Prior story/render history?** Ruby: none. Mason: one failed pre-dispatch composition (2026-08-07, `auto_script`, `wcv=0`), zero substrate propagation.
- **How does business_brief participate in synthesis?** As §1 FACTUAL BASIS grounding — subject to K6.4 verification. Not persona. Persona lives in §2 CHARACTER VOICE (`personality`, `character_point_of_view`, voice axes, signature phrases) and is verifier-exempt. Both characters carry factual bakery/coffee-shop grounding through `business_brief` (Ruby 330 chars; Mason 408 chars) with no supplementary `who_you_help` / `what_you_sell` populated.
- **Recommended substrate: RUBY** primary, **MASON** as sequential companion if Ruby's render succeeds.
- **Why:** Ruby is maximally clean, wizard-default (best test of the minimum-config real-world path), pre-SESSION-269 identity (cannot be post-hoc tuned), bakery domain visually rich enough to keep the fresh-substrate visual-story option open. Mason is functionally identical but carries one zero-effect scar. Doing them sequentially (not in parallel) preserves the ability to redesign after Ruby's evidence. NEITHER-CREATE-NEW rejected because Ruby/Mason already satisfy fresh-domain independence at lower operator cost than a third character.
- **Smallest proposed dogfood sequence:** Slice α (Universe + Ruby-attach + one authored KD) → Slice β (first `talking_head` render with real `audience_hint`, real-mode) → Slice γ (memory-promotion decision + optional second render) → Slice δ (PublishBundle, optional) → Slice ε (Mason companion if Ruby succeeds). Each slice is separately authorizable; nothing is precommitted.
- **§11 commit SHA:** recorded in §12 at commit time.
- **Repo/runtime health:** unchanged from §1. `main == origin/main`; clean working tree; Django 302 / media-engine ok-all-mocks-false / Vite 200; no experiment env vars set; CORRECT_ANCHOR `_expansion_hint` preserved.

---

## §12. §11 COMMIT PROVENANCE

- §11 audit commit: **`e07f1c6`** — `docs(session-273): §11 pre-dogfood Ruby/Mason substrate audit`
- Pushed to `origin/main`.
- Evidence sidecar: `docs/design/session_273_experiment_data/01_ruby_mason_substrate_audit.json` (1,489,060 bytes)
- Audit script: `scripts/session273_substrate_audit.py` (read-only)
