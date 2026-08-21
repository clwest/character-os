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

---

## §13. SLICE α — FRESH UNIVERSE + RUBY ATTACH + RETRIEVAL VERIFICATION + PROPOSED KD

**Status:** Slice α of the Ruby fresh-domain dogfood — authorized by Chris after §11 audit closed. No render, no Composition, no Episode, no NarrativeMemory. **The proposed KnowledgeDocument in §13.4 has NOT been ingested** — it is awaiting Chris's approval before upload through `/workspace/knowledge`. No source code changed. No persona / voice / avatar / brand fields modified on Ruby. No existing KnowledgeDocument touched. No retrieval logic changed.

**Executor script:** `scripts/session273_slice_alpha_universe_attach.py` (idempotent: creates the Universe once, attaches Ruby once, captures pre- and post-attach retrieval snapshots).

**Evidence sidecar:** `docs/design/session_273_experiment_data/02_slice_alpha_universe_attach.json` (17,822 bytes).

**Proposed KD sidecar (NOT INGESTED):** `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md` (7,165 bytes).

### §13.1 Universe creation result

| Field | Value |
| --- | --- |
| Universe ID | **`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`** |
| Name | `Fox & Flour Bakery` |
| Slug (auto-derived) | `fox-flour-bakery` |
| Workspace | `4ce5486d-35a4-4bee-8745-38004adb33bc` (Chris's workspace) |
| `created_by` | user `883` (chris@donkeybetz.com — workspace owner) |
| `created_at` | 2026-08-20 22:43:36 UTC |
| `description` | *(empty — not consumed by K6 synthesis; management-surface field only)* |
| `archived_at` | `None` (active) |

Universe was created through the same ORM path the `UniverseViewSet.perform_create` API uses (`shell/apps/universe/views.py:67`). The API's only additional step (`serializer.save(created_by=user)`) was preserved by passing `created_by=chris` at construction. Slug auto-derivation happened inside `Universe.save()` per `UniverseSchema V1`.

Workspace universe count went from **1 → 2** (was: `Patch' Workshop` `56d16b63` only; now also `Fox & Flour Bakery` `1a0af807-…`). No other Workspace, Teammate, KnowledgeDocument, or Episode was created or modified during Universe creation.

### §13.2 Ruby attachment result

| Field | Pre-attach | Post-attach |
| --- | --- | --- |
| `Teammate.id` | `5875a7b4-cf39-433d-89b3-4e34a89a5208` | *(unchanged)* |
| `Teammate.universe_id` | `None` | **`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`** |
| `Teammate.universe.name` | *(none)* | `Fox & Flour Bakery` |
| `Teammate.updated_at` | 2026-07-23 20:24:27 UTC | 2026-08-20 22:44:22 UTC |
| Attach action | — | `attached` |
| Fields written | — | `universe`, `updated_at` (via `save(update_fields=[…])`) |

Ruby's persona (`business_brief`, `personality`, `character_point_of_view`, `voice_signature_phrases`, `voice_avoid_phrases`, `always_emphasize`, `never_say`, `who_you_help`, `what_you_sell`, `tone_archetype`, `voice_energy` / `humor` / `directness`), avatar (`runway_avatar_id`, `runway_avatar_status`, `portrait_path`), voice (`voice_id`), and brand (`visual_subject`, `visual_template`) fields were **NOT** touched — the save() explicitly whitelisted `universe` + `updated_at`.

`Teammate.clean()` was invoked (via `full_clean()`) and passed. The workspace-mismatch guard fired correctly (both universe and teammate live in workspace `4ce5486d-…`).

**Implementation note (not a code change):** on the first script invocation, `Teammate.full_clean()` produced a false workspace mismatch because `Universe.workspace_id` (freshly built) was a `str` while `Teammate.workspace_id` (from DB) was a `UUID`. The script now re-fetches the Universe from DB before the attach, restoring identical types. This is a scripting concern only — no production behavior implication.

### §13.3 Retrieval-envelope verification

Seven probe queries were run through `retrieve_for_teammate(ruby, query, top_k=5)` — three bakery-native and four community-adjacent — pre-attach and post-attach.

**Pre-attach retrieval (Ruby.universe_id = None):**

Retrieval branch `document.universe IS NULL` fired. Every probe query returned five chunks; the **cumulative distinct document set was 8 of the 9 unbound workspace-only KDs** documented in §11.5. Only `90ad200c` Riggs did not score high enough on any query to appear in a top-5.

| Query kind | Query | Top-5 doc titles |
| --- | --- | --- |
| bakery-native | *sourdough starter feeding schedule* | Bookstore Events · TANK · Tulsi · Children's Reading · Tulsi |
| bakery-native | *custom celebration cakes we accept how many days ahead* | Bookstore Events · TANK ×4 |
| bakery-native | *seasonal pastries autumn menu ingredients* | Bookstore Events · About Hearth & Hollow · Supporting Local Authors · TANK · Tulsi |
| community-adjacent | *welcoming first-time customers who feel intimidated* | TANK ×5 |
| community-adjacent | *supporting local suppliers small business partners* | Supporting Local Authors · About Hearth & Hollow · TANK ×2 · Tulsi |
| community-adjacent | *seasonal community events for families* | Bookstore Events · Supporting Local Authors · Children's Reading · About Hearth & Hollow · TANK |
| community-adjacent | *helping regulars find something new to try* | Helping Customers Find Their Next Read · How We Recommend Books · Children's Reading · About Hearth & Hollow · Supporting Local Authors |

**Every bakery-native query pulled zero bakery content and instead surfaced TANK (automotive financing), Tulsi (public-purpose identity), and Hearth & Hollow Books chunks.** This upgrades §11.5's "leakage risk" from theoretical to demonstrated: a Ruby render TODAY (pre-attach) would have fed §1 FACTUAL BASIS with irrelevant character corpora, regardless of topic.

**Post-attach retrieval (Ruby.universe_id = `1a0af807-…`):**

Retrieval branch `document.universe_id = 1a0af807-…` fired. **Zero chunks returned for every query** — because the Fox & Flour Bakery Universe currently has zero KnowledgeDocuments. This is the correct empty state: no leakage from unbound workspace KDs is structurally possible from here forward.

| Metric | Pre-attach | Post-attach |
| --- | --- | --- |
| Distinct docs retrieved across all 7 probes | 8 (all unbound workspace-only) | 0 |
| Unbound workspace-only KDs leaked | 8 of 9 | **0** |
| `ISOLATION_VERIFIED` (post-attach unbound-leaked == 0) | — | **True** |

Retrieval isolation is verified mechanically. When §13.4's KnowledgeDocument is ingested into the Fox & Flour Universe, retrieval will return only its chunks (subject to cosine ranking + top-k) and cannot fall back to any other character's corpus.

Memory lane already confirmed empty (`retrieve_universe_memory` returns `[]` for a Universe with zero remembered memories — the Fox & Flour Universe has zero `NarrativeMemory` rows).

### §13.4 Proposed KnowledgeDocument — CONTENT FOR CHRIS APPROVAL

**Status: NOT INGESTED.** Full text is committed to `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md`. Upload will only occur after Chris authorizes the content.

Authoring principles applied per §11.10:

- **Included** naturally: breads / sourdough (~1 section), pastries, celebration cakes, ingredients / sourcing, bakery routines, seasonal offerings, customer experience, Ruby's reason for operating.
- **Not included:** paired canonical + accessible paraphrase (Option D — §11.10 explicit avoidance), deliberate density manipulation, deliberate synonym rotation to avoid natural repeated terminology, corporate-KB scale, YouTube ingest content.
- **Not modified on Ruby:** persona, business_brief, personality, voice fields, portrait, `who_you_help`, `what_you_sell`, `character_point_of_view`, `voice_signature_phrases`, `always_emphasize`, `never_say`.

Length: **7,165 bytes** — moderate. Enough for several plausible Episodes; small enough that a real neighborhood bakery owner could realistically have written it in one sitting.

Sections included (8):
1. Breads & sourdough — house country loaf, rotating breads, pricing / day-old policy.
2. Pastries — 3 AM bake, rotating case, don't-hold-over policy.
3. Celebration cakes — lead times, base styles, fillings, deposits, pickup-only.
4. Ingredients & sourcing — Colorado mill, family creamery, pastured eggs, farmers-market fruit, single-origin chocolate.
5. Bakery routines — Wed–Sun open, Mon/Tue prep, bake schedule, staff assignments.
6. Seasonal offerings — spring / summer / autumn / winter rotations plus preorder holidays.
7. Customer experience — counter seats, regulars book, staff rule for basic questions, waitlist referral policy.
8. Ruby's reason for operating — origin story, deliberate smallness, why she said no to expansion.

Deliberate naturalness choices worth flagging:
- **"Sourdough" appears repeatedly in §1** (house loaf, feeding, country sourdough, dark-chocolate sourdough). Not paraphrased. Real bakery language.
- **Ingredient origins are named specifically** (Colorado mill, single-origin West Coast chocolate) — factual anchors K6.4 could verify.
- **Prices are absent** — the KD says "priced by weight" without dollar amounts, so pricing claims cannot be invented from this doc.
- **Chris and Ruby's grandmother are the only named humans** — the KD names no real staff, no real farms, no real chocolate maker (avoids inventing external identities).
- **Ruby's personal motive** (§8) is intentionally understated — brief backstory, no dramatic arcs, gives Episodes a genuine reason but doesn't railroad the character.

The full proposed content is in the sidecar file above.

### §13.5 Anything unexpected

1. **The retrieval leak was not merely theoretical.** §11.5 predicted 9 unbound workspace-only KDs *could* be visible to Ruby. Slice α proved 8 of them *actually surface in the top-5* on bakery queries — including on the exact "sourdough starter" query that should be the most bakery-native possible. A pre-attach Ruby render on any topic would have fed §1 FACTUAL BASIS with TANK financing / Tulsi / bookstore chunks. Post-attach it cannot. This is the strongest single validation of §11.5's mitigation guidance.
2. **`Teammate.full_clean()` type mismatch on freshly built Universe.** On the first attach attempt, `Universe.workspace_id` was still a `str` from the constructor kwarg while `Teammate.workspace_id` was a `UUID` from DB. `Teammate.clean()`'s `!=` comparison then falsely fired the workspace-mismatch guard even though both IDs were the same UUID string. The script now re-fetches the Universe from DB before the attach; production API paths don't hit this because `perform_create → serializer.save()` refreshes the instance. Not a bug in production; noted as a scripting concern.
3. **The Universe existed on script re-invocation because attempt #2 had already saved it.** The idempotence check (`Universe.objects.filter(workspace, name).first()`) correctly reused it on the successful run — so `created_now=False` in the sidecar is accurate for the third invocation, but the Universe was in fact created *during Slice α* (on the second attempt at 22:43:36 UTC). No duplicate Universe rows.

### §13.6 Explicit non-changes during Slice α

- No render dispatched. No Composition created. No provider (Runway / OpenAI / Stability / ElevenLabs) called.
- No Episode created.
- No NarrativeMemory created or promoted.
- No KnowledgeDocument created, ingested, edited, or reassigned. The proposed KD in §13.4 is *file-only*, awaiting Chris's approval.
- No spokesperson m2m mutation on any of the 9 unbound workspace KDs (Riggs / TANK / Tulsi / 6 Hearth & Hollow docs still m2m-empty; leak reported, not fixed).
- Patch's Workshop Universe (`56d16b63`), its 3 Universe-scoped KDs, its 15 NarrativeMemory rows, its 27 Episodes, and all Patch/Rivet substrate remain untouched.
- Ruby's `business_brief`, `personality`, `who_you_help`, `what_you_sell`, `desired_feeling`, `tone_archetype`, `character_point_of_view`, `always_emphasize`, `never_say`, `voice_signature_phrases`, `voice_avoid_phrases`, `voice_energy / humor / directness`, `runway_avatar_id`, `voice_id`, `visual_subject`, `visual_template`, `portrait_path` are all byte-identical to their §11 audit values.
- Mason (`28b9a7ea-…`) untouched. Mason.universe_id still `None`. Mason's one failed composition `6f2132f5` untouched.
- No source code changed. No Django migration. No SPA change. No writing-contract change. No retrieval-logic change. `_expansion_hint` and `_compression_hint` unchanged.
- No experiment env vars set. No provider mocks toggled. Runtime unchanged.

### §13.7 What Slice α leaves ready for Slice β (informational — do NOT begin without authorization)

Once Chris approves the KD content in §13.4:
1. Ingest the KD via the SPA `/workspace/knowledge` upload (real ingestion path, so chunking / embedding fires the way an operator would use it), scoped to Universe `1a0af807-…`.
2. Verify with a single retrieval probe that the new KD is retrievable in the Fox & Flour Universe and that no other-character KDs come back.
3. Slice β proper (first `talking_head` render, real-mode, real `audience_hint`, no retries) then begins as a separately-authorized micro-slice.

Slice β is **not** authorized by this document and is not being started here.

### §13.8 §13 return values

- **Universe:** `Fox & Flour Bakery` — `1a0af807-dd6a-47cd-bfaa-3d088f1c105f` — created in workspace `4ce5486d-…`, slug `fox-flour-bakery`, created_by chris@donkeybetz.com.
- **Ruby attachment:** Ruby `5875a7b4-…` now has `universe_id = 1a0af807-…`. Verified via `refresh_from_db()`. Persona / avatar / voice fields byte-identical to §11 audit.
- **Retrieval isolation:** VERIFIED. Pre-attach: 8 unbound workspace-only KDs leaked into Ruby's top-5 across every probe query (including the bakery-native ones). Post-attach: 0 chunks returned across all 7 probe queries. No unbound KD can leak by construction until a KD is ingested into the Fox & Flour Universe.
- **Proposed KnowledgeDocument:** committed to `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md` for Chris's review. NOT INGESTED.
- **Anything unexpected:** the retrieval leak was demonstrated much more strongly than §11.5 predicted (bakery-native queries pulled TANK financing); minor scripting type-coercion issue on `Teammate.full_clean()` that is not a production concern.
- **Confirmation of non-execution:** zero renders, zero Compositions, zero NarrativeMemory rows, zero Episodes, zero KnowledgeDocuments, zero source changes, zero persona edits.
- **§13 commit SHA:** recorded in §14 at commit time.
- **Repo/runtime health:** `main == origin/main` after commit; Django 302, media-engine ok/all-mocks-false, Vite 200; no experiment env vars; `_expansion_hint` CORRECT_ANCHOR preserved.

---

## §14. §13 COMMIT PROVENANCE

- §13 Slice α commit: **`5175c1b`** — `feat(session-273): §13 Slice α — Fox & Flour Universe + Ruby attach + retrieval verify + proposed KD`
- Pushed to `origin/main`.
- Slice α executor script: `scripts/session273_slice_alpha_universe_attach.py`
- Slice α evidence sidecar: `docs/design/session_273_experiment_data/02_slice_alpha_universe_attach.json` (17,822 bytes)
- Proposed KD sidecar (NOT INGESTED at §13; INGESTED at §15 after Chris approval): `docs/design/session_273_experiment_data/03_slice_alpha_proposed_knowledge_document.md` (7,165 bytes)

---

## §15. SLICE α COMPLETION — KD INGEST + RETRIEVAL VERIFICATION

**Status:** Slice α completed. Chris approved the KD content AS-IS at §13.4. The approved KD is now ingested into the Fox & Flour Bakery Universe. A single natural bakery-native retrieval probe on Ruby returned five chunks — all from the new KD, none from the 9 unbound workspace-only KDs, none from Patch's Workshop's 3 Universe-scoped KDs. **Slice β has NOT begun.**

**Executor script:** `scripts/session273_slice_alpha_ingest_kd.py` (idempotent — content-hash dedup means re-invocation reuses the existing KD).

**Evidence sidecar:** `docs/design/session_273_experiment_data/04_slice_alpha_kd_ingest_and_retrieval.json` (6,436 bytes).

### §15.1 Content-preparation note (transparency)

The approved KD file `03_slice_alpha_proposed_knowledge_document.md` begins with a review-artifact blockquote:

```
> **Status:** PROPOSED — NOT INGESTED. Awaiting Chris approval before
> upload through `/workspace/knowledge` in the Fox & Flour Bakery
> Universe (`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`).
>
> Authored per SESSION 273 §11.10: natural, plausible content …
```

That blockquote is a status marker on the review artifact itself, not KD content. Ingesting it verbatim would insert the literal string *"NOT INGESTED. Awaiting Chris approval before upload"* into the Fox & Flour knowledge corpus — nonsense that contradicts the ingestion itself.

Following the natural operator behavior in the SPA (paste body into text-content, enter title separately), the script split the file into three parts and used the first two:

- **Title** — the top-level `# Fox & Flour Bakery — Working Knowledge` line.
- **Body ingested** — everything from `## Breads & sourdough` through the end of §"Ruby's reason for operating" — **6,599 chars**, byte-identical to the approved content.
- **Discarded** — the `> Status: … approval …` blockquote (review meta, 4 lines) and the immediately-following `---` horizontal rule.

Every sentence of Chris's approved bakery content is preserved verbatim. No sentence was revised, polished, expanded, shortened, paraphrased, or reordered. The sidecar records both the discarded blockquote and the ingested body's first/last 120 characters so this decision is transparent and auditable.

### §15.2 KnowledgeDocument creation result

| Field | Value |
| --- | --- |
| KD ID | **`74e7f18f-5b77-459c-bc36-b4ab617d8aca`** |
| Title | `Fox & Flour Bakery — Working Knowledge` |
| `document_type` | `markdown` (auto-derived; body starts with `## `) |
| `ingested_via` | `paste` |
| `workspace_id` | `4ce5486d-…` |
| `universe_id` | **`1a0af807-…` (Fox & Flour Bakery)** ✓ |
| `is_active` | `True` |
| `spokespeople` M2M | empty (empty-M2M = Universe-scoped broadcast; Ruby is the only teammate in this Universe) |
| `status` (final) | **`processed`** |
| `content_hash` | (persisted; see sidecar) |
| `created_at` | 2026-08-20 22:54:40 UTC |
| `created_by` | user `883` (chris@donkeybetz.com) |
| First run `deduped` | `False` (fresh ingest) |
| Second run `deduped` | `True` (content-hash match — script re-invocation) |

Production code path: `KnowledgeDocumentSerializer.create` (`shell/apps/embeddings/serializers.py:271`) branches on `text_content` to `ingestion.ingest_text` (`shell/apps/embeddings/ingestion.py:173`), then dispatches `embed_document.delay(...)` (`shell/apps/embeddings/tasks.py`). This script called those same two functions directly with the same argument shape the serializer produces from the SPA POST — no `curl`/HTTP round-trip needed, same effect.

### §15.3 Chunking / embedding result

| Metric | Value |
| --- | --- |
| Total chunks | **10** |
| Chunks with `embedding_vector IS NOT NULL` | **10** |
| Coverage | 100% |
| Poll history | single poll — Celery had already completed by the time the script polled (real worker running) |
| Final `status` on `KnowledgeDocument` | `processed` |

The embedding path fired asynchronously through the real Celery worker. Elapsed poll time was effectively 0 s on the second invocation because embedding completed during the first (crashed) invocation. First invocation logs also show the KD reached `processed` cleanly before the (unrelated, contamination-check-only) UUID-parsing bug crashed the script — see §15.6.

### §15.4 Retrieval probe

**Query (verbatim):** `"how far in advance do we need to book a custom celebration cake"`

**Rationale for this probe:** It is a natural, plausible operator question grounded specifically in the KD's §"Celebration cakes" section (which states the lead times). This is the same shape of question Chris would type when drafting a real Episode. Not an adversarial probe; not a probe designed to force ranking evidence.

**Result:** 5 chunks returned, all from doc `74e7f18f-…` in Universe `1a0af807-…`.

| Rank | Chunk | Distance | Content preview |
| --- | --- | --- | --- |
| 1 | `cc0c4259` | **0.4143** | *"lead time is a minimum of five days for standard tiered cakes and ten days for sculpted or heavily decorated cakes; peak seasons (spring weddings, December holidays) push those windows…"* |
| 2 | `5f169561` | 0.4506 | *"…Preorder holidays (Thanksgiving, Christmas Eve, Easter) have a published cutoff two weeks ahead and no walk-in same-day availability for the specialty items…"* |
| 3 | `18f9eb09` | 0.4843 | *"…Pastries are not held over. What doesn't sell by close is either marked half-price in the last hour or donated the same evening…"* (transition into Celebration cakes) |
| 4 | `1754ac81` | 0.5503 | *"…50% deposit is taken at booking. Deposits are non-refundable inside of 72 hours before pickup. Fox & Flour does not deliver cakes; all orders are pickup only…"* |
| 5 | `659524ac` | 0.5878 | *"…Her lead baker covers Thursday and Saturday. There are two counter staff and one part-time decorator…"* (transition into Seasonal offerings) |

**Top result is a direct textual match on the probe question** — the lead-time rule (5 / 10 days) is retrieved as chunk #1. The second-highest is the related holiday preorder-cutoff clause. The retrieval envelope is coherent with the operator's question.

Every chunk is from the newly-ingested Fox & Flour KnowledgeDocument, in the Fox & Flour Universe.

### §15.5 Contamination-absence verification

| Check | Expected | Observed |
| --- | --- | --- |
| Retrieved document count | 1 (the new KD only) | **1** ✓ |
| Retrieved Universe scope | `{1a0af807-…}` only | `{1a0af807-…}` ✓ |
| Unbound workspace-only KDs leaked (9 candidates from §11.5 / §13.3) | none | **`[]`** ✓ |
| Other-Universe KDs leaked (3 Patch's Workshop docs — `f309469c`, `218eb0d8`, `fd0ba2ca`) | none | **`[]`** ✓ |
| Only Fox & Flour Universe present in results | True | **True** ✓ |
| Only the new KD returned (no legacy universe-null match) | True | **True** ✓ |

The pre-attach retrieval leakage documented in §13.3 (8 of 9 unbound KDs surfacing in Ruby's top-5 across every probe) is now **structurally absent**. Post-ingest, retrieval sees exactly one KD's chunks — the intended one.

Memory lane: `retrieve_universe_memory` still returns `[]` for Ruby (the Fox & Flour Universe has zero `NarrativeMemory` rows; that is expected and intended for the pre-first-render state).

### §15.6 Anything unexpected

1. **Retrieval quality is strong on first probe.** The top chunk is a direct textual match — no ambiguity, no misranking. This is a positive surprise for a wizard-default character with minimal persona fields; retrieval quality on this bakery content is not dependent on Ruby having a rich persona.
2. **Second invocation hit the content-hash dedup path.** Both runs of the script tried to create the KD; the second returned `deduped=True` and reused the row from the first run. This is idempotence working as designed. No duplicate row was created.
3. **Non-fatal scripting bug on first invocation.** The script's contamination-check phase originally hard-coded a truncated UUID `56d16b63` for Patch's Workshop and Django rejected the invalid UUID literal — the exception raised **after** the KD had already been created and embedded (the ingest / embed / poll / probe phases all completed cleanly first). The fix replaces the hardcoded prefix with a live queryset (`workspace KDs excluding the new Universe`). No production behavior implication; scripting concern only. Documented for auditability.
4. **`document_type` auto-derived to `markdown`** because the ingested body starts with `## Breads & sourdough`. This matches the DRF serializer heuristic (`text.startswith("#") or "\n## " in text`). Chunking then respects markdown boundaries — visible in the chunk previews where breaks fall on `##` section headers.
5. **First discovered chunk boundary crossed a section boundary.** Chunk #3 begins mid-Pastries (*"spots rotate) — Scones on the weekend only"*) and ends inside Celebration cakes. Chunk #5 begins mid-Bakery routines and ends inside Seasonal offerings. This is the text-splitter's window overlap doing its job — chunks intentionally overlap to preserve context — not a bug. No special handling required.

### §15.7 Explicit non-changes during §15

- No Episode created.
- No Composition created. No render dispatched. No provider (Runway / OpenAI / Stability / ElevenLabs) called for content generation. (OpenAI *was* called for embedding the 10 chunks — that is the intended `embed_document` path.)
- No NarrativeMemory created or promoted.
- No PublishBundle created.
- No modification to Ruby's `business_brief`, `personality`, `who_you_help`, `what_you_sell`, `desired_feeling`, `tone_archetype`, `character_point_of_view`, `always_emphasize`, `never_say`, `voice_signature_phrases`, `voice_avoid_phrases`, `voice_energy / humor / directness`, `runway_avatar_id`, `voice_id`, `visual_subject`, `visual_template`, `portrait_path`. Persona hashes recomputed post-ingest match §13.2 values (see sidecar `ruby_persona_hashes_after_ingest`).
- Ruby.universe_id remains `1a0af807-…` (unchanged from Slice α §13.2).
- Mason untouched (`universe_id=None`, `updated_at=2026-07-23`).
- Patch's Workshop Universe, its 3 Universe-scoped KDs, its 15 NarrativeMemory rows, its 27 Episodes untouched.
- No source code, migration, writing-contract, retrieval-logic, or synthesis-code change.
- No spokesperson m2m mutation on any of the 9 unbound workspace KDs (leak reported, not fixed).
- No experiment env vars set. No provider mocks toggled. Runtime unchanged.
- No retrieval retries or ranking tuning. The single probe result stands as-is.

### §15.8 §15 return values

- **KnowledgeDocument:** id `74e7f18f-5b77-459c-bc36-b4ab617d8aca`, title *"Fox & Flour Bakery — Working Knowledge"*.
- **Universe attachment:** `universe_id = 1a0af807-dd6a-47cd-bfaa-3d088f1c105f` (Fox & Flour Bakery) ✓.
- **Chunking / embedding:** 10 chunks, 10 embedded (100% coverage), status `processed`.
- **Retrieval probe (verbatim):** `"how far in advance do we need to book a custom celebration cake"`.
- **Retrieved chunks:** 5, all from doc `74e7f18f-…` in Universe `1a0af807-…`. Top chunk (dist 0.4143) is a direct textual match on the lead-time rule.
- **Contamination absence:** confirmed — zero unbound-workspace-only KD leakage, zero other-Universe KD leakage, only Fox & Flour Universe present, only the new KD returned.
- **Anything unexpected:** retrieval quality high on first probe (positive); one non-fatal contamination-check scripting bug that fired after ingest completed (documented); dedup path confirmed on re-invocation.
- **§15 commit SHA:** recorded in §16 at commit time.
- **Slice β status:** **NOT BEGUN.** No Episode, Composition, render, NarrativeMemory, or PublishBundle exists or has been attempted. Slice α is complete.

---

## §16. §15 COMMIT PROVENANCE

- §15 Slice α completion commit: **`70e3113`** — `feat(session-273): §15 Slice α completion — approved Fox & Flour KD ingested + retrieval verified`
- Pushed to `origin/main`.
- Slice α ingest executor script: `scripts/session273_slice_alpha_ingest_kd.py`
- Slice α ingest + retrieval evidence sidecar: `docs/design/session_273_experiment_data/04_slice_alpha_kd_ingest_and_retrieval.json` (6,436 bytes)

---

## §17. SLICE α CLOSEOUT — CHRIS-EDITED KD + 3-PROBE VERIFICATION + SHARED-KNOWLEDGE FINDING

**Status:** Slice α CLOSED. Chris confirmed the KD in the SPA and added a **spokesperson m2m assignment: Ruby only**. This section verifies the resulting DB state mechanically, runs three natural retrieval probes across kinds (bakery-native / community-adjacent / operational-detail), documents a newly-surfaced **shared/global knowledge product finding**, and confirms Slice β has not begun.

**Read-only executor:** `scripts/session273_slice_alpha_closeout_verify.py` — inspects existing state, runs 3 retrieval probes, records everything. Does not mutate.

**Evidence sidecar:** `docs/design/session_273_experiment_data/05_slice_alpha_closeout_verification.json` (1,487,193 bytes).

### §17.1 How Chris's UI action landed in the DB

Chris used the SPA `/workspace/knowledge` editor to attach Ruby as spokesperson on the already-ingested KD. Mechanical evidence:

| Field | Value | Change from §15? |
| --- | --- | --- |
| KD `id` | `74e7f18f-5b77-459c-bc36-b4ab617d8aca` | same — no new row |
| Title | `Fox & Flour Bakery — Working Knowledge` | unchanged |
| `content_hash` | `7a0e4bd2551f…` | unchanged (body byte-identical to §15 ingest) |
| Chunks total / embedded | 10 / 10 | unchanged |
| `document_type` | `markdown` | unchanged |
| `ingested_via` | `paste` | unchanged |
| `universe_id` | `1a0af807-…` (Fox & Flour Bakery) | unchanged |
| `is_active` | `True` | unchanged |
| `status` | `processed` | unchanged |
| `updated_at` | 2026-08-20 22:54:46 UTC | unchanged (m2m table writes do not bump parent `updated_at` — Django default) |
| **`m2m spokespeople`** | **`[Ruby (5875a7b4-…)]`** | **CHANGED** (was empty at §15) |

Workspace KD count went 16 → 17 at §15 ingest, and remains 17 after Chris's UI edit — the m2m add did not create a duplicate KD row. No re-ingest happened; the content, chunks, and embeddings from §15 remain in place. This is the correct SPA behavior for the "attach an existing KD to a character" flow.

### §17.2 KD verification (mechanical)

All six invariants pass:

| Check | Expected | Observed |
| --- | --- | --- |
| Universe is Fox & Flour | `1a0af807-…` | ✓ |
| Workspace is Chris's | `4ce5486d-…` | ✓ |
| m2m spokespeople count | 1 | 1 ✓ |
| m2m spokespeople = Ruby only | `[5875a7b4-…]` | `[5875a7b4-…]` ✓ |
| Status = `processed` | True | True ✓ |
| Chunks fully embedded | 10 / 10 | 10 / 10 ✓ |
| Is active | True | True ✓ |

**Content match with §13.4 approved specimen:** the `content_hash` recorded here (`7a0e4bd2551f…`) equals the hash captured at §15 ingest. `raw_content` and `processed_content` char counts also match §15's captured values. Chris's UI edit did not touch the body; every sentence approved in §13.4 remains verbatim in the ingested KD.

### §17.3 Ruby persona invariance

Ruby persona/voice/avatar/brand fields recorded via SHA-256 to allow durable cross-process comparison:

- `Ruby.universe_id` = `1a0af807-…` (Fox & Flour) — unchanged since §13.2 attach.
- `Ruby.updated_at` = 2026-08-20 22:44:22 UTC — unchanged since §13.2 attach (Chris's KD-edit action did not touch Ruby).
- `business_brief` opens with `"Ruby owns Fox & Flour Bakery, a neighborhood artisan bakery known for naturally …"` — byte-identical to §11.2 audit.
- `personality` opens with `"Warm, cheerful, and genuinely caring. Ruby loves helping people find the perfect treat …"` — byte-identical to §11.2.
- `who_you_help` / `what_you_sell` / `desired_feeling` / `character_point_of_view` / `always_emphasize` / `never_say` / `voice_signature_phrases` / `voice_avoid_phrases` — all still empty (SHA-256 of empty string).
- `portrait_path`, `runway_avatar_id`, `voice_id`, `visual_subject`, `visual_template` — all unchanged.

Ruby is byte-identical to her pre-SESSION-273 wizard-default state except for the two explicitly authorized changes: `universe_id` set at §13.2, and the reverse m2m appearance (Ruby now shows up on `KnowledgeDocument.spokespeople` for the new KD).

### §17.4 Retrieval probes (verbatim)

Three probes were run through `retrieve_for_teammate(ruby, query, top_k=5)`. Every probe returned exactly 5 chunks — all from the single Fox & Flour KD (`74e7f18f-…`) in the Fox & Flour Universe (`1a0af807-…`). No probe was retried; no query was tuned to make results attractive.

**Probe 1 — bakery-native.**
Query: `"how do we handle the sourdough starter feeding routine for the country loaf"`

| # | dist | Chunk preview |
| --- | --- | --- |
| 1 | **0.4098** | *"## Breads & sourdough — Sourdough is the foundation of Fox & Flour. Ruby maintains two active starters that live in the walk-in fridge and get fed the night before each bake day…"* |
| 2 | 0.5719 | *"…dark-chocolate-and-sour-cherry sourdough that goes out on Fridays only. A soft brioche is baked twice weekly…"* |
| 3 | 0.6353 | *"…'artisan' as a buzzword. She prefers to name the actual farm or mill when a customer asks. The bakery's habit is: if it's on the menu, Ruby can tell you where it came from…"* |
| 4 | 0.6424 | Bakery routines transition to Seasonal offerings |
| 5 | 0.6530 | 50% deposit + Ingredients transition |

Top chunk is a direct textual match on the sourdough-starter-feeding rule.

**Probe 2 — customer/community-adjacent.**
Query: `"how do you help a first-time customer who feels intimidated by the case"`

| # | dist | Chunk preview |
| --- | --- | --- |
| 1 | 0.7202 | *"…Preorder holidays (Thanksgiving, Christmas Eve, Easter) have a published cutoff two weeks ahead and no walk-in same-day availability for the specialty items… ## Customer…"* |
| 2 | 0.7372 | *"…a small waitlist for celebration cakes during peak weeks. When the shop can't take a booking, the counter staff recommend one of two other independent bakers in town who…"* |
| 3 | 0.7844 | Staff / Seasonal offerings header |
| 4 | 0.7866 | Celebration-cake lead time |
| 5 | 0.7910 | *"…than to a distant owner who never smelled the ovens. The name comes from an old family nickname (Ruby's grandmother called her 'little fox')…"* |

Distances are notably higher than probes 1 and 3 (~0.72–0.79). This is the fuzziest of the three probes and the KD's answer (the §Customer experience section: *"no question about the menu is too basic to answer patiently"*) does not appear in the top-5 — retrieval is pulling on the Universe-context adjacent chunks (referrals, ownership motive) that share embedding-space semantics with the query. Not a failure; not a distinction the operator can currently see. This is the kind of retrieval fuzziness that only shows up when a probe is genuinely adjacent-to-content rather than directly-supported.

*Note:* the pre-attach evidence at §13.3 pulled the Hearth & Hollow bookstore corpus on almost every community-adjacent probe. Post-attach, the same query kind now returns only Fox & Flour content — even where the match is fuzzy, contamination is structurally absent.

**Probe 3 — operational-detail.**
Query: `"what is the deposit and cancellation policy on custom celebration cakes"`

| # | dist | Chunk preview |
| --- | --- | --- |
| 1 | **0.4075** | *"lead time is a minimum of five days for standard tiered cakes and ten days for sculpted or heavily decorated cakes; peak seasons (spring weddings, December holidays) push…"* |
| 2 | 0.4907 | Pastries → Celebration cakes transition |
| 3 | **0.4912** | *"50% deposit is taken at booking. Deposits are non-refundable inside of 72 hours before pickup. Fox & Flour does not deliver cakes; all orders are pickup only. ## Ingredients…"* |
| 4 | 0.5760 | Holiday preorder cutoffs |
| 5 | 0.5877 | Sourdough varieties |

Direct policy match at chunk #3 (`50% deposit… non-refundable inside of 72 hours`). Chunk #1 pulls the closely-related lead-time rule.

### §17.5 Isolation verdict

Aggregate across all 3 probes (15 chunks total):

| Check | Expected | Observed |
| --- | --- | --- |
| Distinct retrieved doc ids | `{74e7f18f-…}` | `{74e7f18f-…}` ✓ |
| Distinct retrieved Universe scopes | `{1a0af807-…}` | `{1a0af807-…}` ✓ |
| Unbound workspace-only KDs leaked (§11.5's 9 candidates) | `[]` | `[]` ✓ |
| Other-Universe KDs leaked (Patch's Workshop's 3 Universe-scoped) | `[]` | `[]` ✓ |
| Ruby-ineligible KDs leaked (m2m to a non-Ruby teammate) | `[]` | `[]` ✓ |
| Only the Fox & Flour KD returned | True | **True** ✓ |

**A. Ruby retrieves Fox & Flour knowledge:** yes.
**B. Every returned KD belongs to the Fox & Flour Universe:** yes.
**C. Returned KD is spokesperson-eligible for Ruby:** yes — m2m spokespeople = `[Ruby]`; the retrieval filter matches on `document.spokespeople = spokesperson` branch (not the `isnull=True` broadcast branch, because m2m is non-empty).
**D. None of the previously demonstrated unbound workspace KDs leak:** confirmed structurally impossible from Universe-scoped retrieval.
**E. No Patch/Rivet/TANK/Tulsi/Hearth & Hollow/Mike/Penny/etc. material appears:** confirmed zero across 3 probes × 5 chunks.

### §17.6 NEW PRODUCT FINDING — shared / global knowledge behavior is uncharacterized

**What Chris observed while creating the Ruby KD:** the SPA offers a spokesperson-assignment field on the KnowledgeDocument. His operator-mental-model, developed from the UI, is:

- Knowledge **assigned to a character** → character-specific knowledge.
- Knowledge with **no character assignment** → effectively "shared" or "global" knowledge, retrievable by any character whose scoping matches.

**What §11 / §13 evidence already tells us mechanically** (this is not new experiment work; it is what the code + prior probes already prove):

- Retrieval filter (`shell/apps/embeddings/retrieval.py:159–226`):
  - Workspace filter: unconditional (contract rule 3).
  - Universe filter: `document.universe_id = teammate.universe_id` — or `document.universe IS NULL` when teammate has no Universe.
  - Spokesperson filter: `document.spokespeople IS NULL (empty m2m) OR document.spokespeople = teammate`.
- **§13.3 demonstrated** that 8 of 9 workspace-only KDs (Universe=NULL, spokespeople=empty) were retrieval-visible to Ruby before her Universe attachment — including pulling Hearth & Hollow bookstore chunks on bakery-native queries. That is "shared / global knowledge" behaving as a broadcast tier.
- **§13 attach + §17 verification** proved that scoping Ruby into a Universe **and** binding her KD to her via m2m fully isolates her retrieval envelope. Chris's approach is the strongest-isolation variant.

**What has NOT been dogfooded** — the SESSION 273 finding to preserve:

We have **code-level eligibility** and **accidental-leakage evidence** for "shared / global knowledge", but we have **not intentionally characterized** its behavior across characters + Universes. Every question below is currently unanswered by dogfood evidence:

1. **What are the operator-visible knowledge classes today?**
   1. Workspace-global: `universe = None`, `spokespeople = empty` — broadcast within workspace to any teammate with `universe_id = None`.
   2. Workspace character-specific: `universe = None`, `spokespeople = {A}` — visible only to A (and only while A also has `universe_id = None`).
   3. Universe-shared: `universe = U`, `spokespeople = empty` — broadcast within Universe U.
   4. Universe character-specific: `universe = U`, `spokespeople = {A}` — visible only to A within Universe U. **(This is the class Ruby's Fox & Flour KD occupies.)**
2. **Who can retrieve each class?** Code answers this (see filter above), but the operator's mental model from the UI does not yet reliably distinguish "assigned" vs "shared".
3. **What happens when shared and character-specific knowledge both match on the same query?** Retrieval is cosine-ranked with a hard `top_k=5` — an unbound shared doc that scores 0.42 can and does outrank a character-scoped doc that scores 0.51. Not evidence-verified in a controlled setup.
4. **Does character-specific knowledge receive any retrieval priority?** No, by inspection of `retrieval.py:216` — the two branches are OR'd in the same queryset, then ranked purely by cosine distance. No priority boost.
5. **Can unrelated shared knowledge outrank relevant character-specific knowledge?** §13.3 already suggests yes: on the bakery-native `"sourdough starter feeding schedule"` probe, an unbound Bookstore Events chunk beat unbound-TANK chunks — and no character-specific bakery content existed to compare. The class-competition regime is untested when *both* are present.
6. **Does `top_k` cause starvation/competition?** Not tested. If a workspace has 50 shared docs and 1 character-specific doc, does the character doc reliably surface at top_k=5? Unknown.
7. **How does this behave with multiple characters in one Universe?** Not tested — Fox & Flour has one character (Ruby); Patch's Workshop has multiple but no unbound shared KDs.
8. **How does it behave across separate Universes?** Universe isolation is proven at §17.5, but the shared-tier behavior across Universe boundaries is not.
9. **Is "unassigned" the correct operator-facing term if it actually means shared?** The current UI labels the field neutrally. Operator intuition may or may not align with retrieval semantics. Not investigated.
10. **Would the UI benefit from explicit copy like** *"Shared with everyone in this Universe"* / *"Shared workspace knowledge"* / *"Only Ruby will retrieve this"*? Not investigated.

**Future falsifiable question** (frozen; not scheduled; not started):

> How does unassigned/shared knowledge behave across multiple characters and Universes when character-specific knowledge is also present? Do the four classes above produce the retrieval semantics the operator expects from the UI, or is the "unassigned = shared" convention hiding surprises?

**Explicit non-actions during §17:**

- No retrieval code changed.
- No Knowledge UI changed.
- No existing KD reassigned or unassigned.
- No new "shared knowledge" experiment run.
- No cross-character or cross-Universe retrieval probe attempted (Fox & Flour intentionally has only Ruby; no second character exists in that Universe to probe against).
- No proposal on operator-facing copy.
- No SESSION 273 scope creep — this finding is preserved for a *future* session decision, not this one.

**Dogfood principle re-affirmed:** Ruby's KD stays Universe-scoped + Ruby-scoped for her first render. We do not want a shared/global tier interacting with her first-render evidence. Any shared-knowledge dogfood must happen on a separate substrate (fresh character(s), fresh Universe, controlled) — never opportunistically piggybacked on the Ruby dogfood.

### §17.7 Workspace state after §17

| Metric | Pre-§17 | Post-§17 | Δ |
| --- | --- | --- | --- |
| Total workspace KDs | 17 | 17 | 0 |
| Total workspace NarrativeMemory | 15 | 15 | 0 |
| Total workspace Universes | 2 | 2 | 0 |
| Total workspace Episodes | 27 | 27 | 0 |
| Total workspace Compositions | 135 | 135 | 0 |
| Ruby.universe_id | `1a0af807-…` | `1a0af807-…` | unchanged |
| Ruby.updated_at | 2026-08-20 22:44:22 | 2026-08-20 22:44:22 | unchanged |
| Mason.universe_id | `None` | `None` | unchanged |
| Mason.updated_at | 2026-07-23 17:43:20 | 2026-07-23 17:43:20 | unchanged |
| KD `74e7f18f` m2m spokespeople | `[]` (post-§15 pre-Chris-edit) | `[Ruby]` (Chris SPA edit) | +1 (authorized) |

### §17.8 Explicit non-changes during §17

- No render dispatched. No Composition created.
- No Episode created.
- No NarrativeMemory created or promoted.
- No PublishBundle created.
- No modification to Ruby's persona, voice, avatar, brand, or `universe_id`.
- Mason untouched.
- Patch's Workshop Universe, its 3 Universe-scoped KDs, its 15 NarrativeMemory, its 27 Episodes untouched.
- No source code / migration / writing-contract / retrieval / synthesis / K6.4 change.
- No spokesperson m2m mutation on any of the 9 unbound workspace KDs.
- No retrieval retries. No query tuning after seeing results.
- The KD `74e7f18f` was **not** re-ingested, deleted, edited, or reassigned by this section. The only mutation between §15 and §17 was Chris's authorized SPA action to add Ruby to `spokespeople` m2m.
- No experiment env vars set. No provider mocks toggled. Runtime unchanged.

### §17.9 §17 return values

- **KD ID / title:** `74e7f18f-5b77-459c-bc36-b4ab617d8aca` — `Fox & Flour Bakery — Working Knowledge`.
- **Universe assignment:** `1a0af807-dd6a-47cd-bfaa-3d088f1c105f` (Fox & Flour Bakery).
- **Spokesperson assignment:** `[Ruby (5875a7b4-…)]` — Ruby only, as Chris configured.
- **Chunks / embedding:** 10 / 10 (100%), status `processed`, content_hash unchanged from §15.
- **Retrieval probes + results:** 3 probes (bakery-native / community-adjacent / operational-detail) × top_k=5 = 15 chunks; every chunk from `74e7f18f-…` in Universe `1a0af807-…`. Top-1 distances 0.4098 / 0.7202 / 0.4075 respectively.
- **Isolation verdict:** VERIFIED — zero unbound workspace-only leakage, zero other-Universe leakage, zero Ruby-ineligible leakage, only the Fox & Flour KD returned.
- **Shared/global-knowledge finding:** documented at §17.6 as a **NEW SESSION 273 product finding**. Not experimentally characterized; future falsifiable question frozen for a later session. Ruby's dogfood is intentionally kept clear of the shared-tier regime.
- **Anything unexpected:** the community-adjacent probe has substantially higher distances (~0.72–0.79) than the other two probes, and pulled Universe-context adjacent chunks (referrals, ownership motive) rather than the §Customer experience section's direct answer. This is a fuzziness observation, not a defect — preserved as-is per the "if something surprising happens, preserve it and STOP rather than fixing it" rule. No probe was retried; no query was tuned.
- **§17 commit SHA:** recorded in §18 at commit time.
- **Repo / runtime health:** clean tree; `main == origin/main`; Django 302 / media-engine ok-all-mocks-false / Vite 200; no experiment env vars.
- **Slice β status:** **NOT BEGUN.** Compositions=135 (unchanged), Episodes=27 (unchanged), NarrativeMemory=15 (unchanged), no PublishBundle created. No render has been dispatched for Ruby. Slice α is CLOSED.

---

## §18. §17 COMMIT PROVENANCE

- §17 Slice α closeout commit: **`8171b5b`** — `feat(session-273): §17 Slice α CLOSEOUT — Chris SPA Ruby-m2m + 3-probe verify + shared-knowledge product finding`
- Pushed to `origin/main`.
- Slice α closeout verification script (read-only): `scripts/session273_slice_alpha_closeout_verify.py`
- Slice α closeout evidence sidecar: `docs/design/session_273_experiment_data/05_slice_alpha_closeout_verification.json` (1,487,193 bytes)

---

## §19. CAST-ADD 400 DIAGNOSTIC — NOT REPRODUCED; NO PRODUCTION FIX LANDED

**Status:** Chris reported that clicking "Add to cast" in the Episode detail page (Fox & Flour Episode `77b04b6b`, adding Ruby) returned HTTP 400. This section documents the diagnostic that ran against the exact substrate — Chris's user account, real Ruby, real Fox & Flour Episode — and **failed to reproduce the failure**. Every proof point examined shows the backend cast-add path is healthy for this exact case. **No production code was changed. No fix was landed.**

**Evidence sidecar:** `docs/design/session_273_experiment_data/06_diag_cast_400.json` (2,917 bytes).
**Diagnostic script (read-only; atomic-rollback):** `scripts/session273_diag_cast_400.py`.

### §19.1 Preconditions verified

| Object | Field | Value | Python type |
| --- | --- | --- | --- |
| Ruby | `id` | `5875a7b4-cf39-433d-89b3-4e34a89a5208` | UUID |
| Ruby | `workspace_id` | `4ce5486d-…` | **UUID** |
| Ruby | `universe_id` | `1a0af807-…` | **UUID** |
| Episode `77b04b6b` | `universe_id` | `1a0af807-…` | **UUID** |
| Episode `77b04b6b` | `universe.workspace_id` | `4ce5486d-…` | **UUID** |
| Episode `77b04b6b` | cast (pre-diag) | `[]` (empty) | — |

ID comparisons: `ruby.universe_id == episode.universe_id` → **True**; `ruby.workspace_id == episode.universe.workspace_id` → **True**. No UUID-vs-string type mismatch — both sides are `uuid.UUID` objects loaded from the DB. **This is not the §13.2 scripting hazard.**

### §19.2 Three-probe reproduction (all in `transaction.atomic()` + savepoint_rollback — nothing persists)

**Probe 1 — DRF `APIClient.post(…)` with `force_authenticate(chris)`:**
- URL: `/api/episodes/77b04b6b-…/cast/`
- Payload: `{"teammate": "5875a7b4-…"}` (format=json)
- **Status: 201 Created**. Response body (440 bytes) is a full Episode payload including `cast: [{id: 5875a7b4-…, name: "Ruby"}]`.

**Probe 2 — direct `episode.cast.add(ruby)` (isolates the `m2m_changed pre_add` signal):**
- **Result: success.** `episode.cast.all()` now includes Ruby.

**Probe 3 — `EpisodeCast(episode, teammate).full_clean()` (isolates model-level `clean()`):**
- **Result: clean_passed.**

All three layers of defense-in-depth (view / signal / model.clean) accept this exact combination. Rollback verified: post-probe `episode.cast` is empty as before.

### §19.3 Existing regression coverage

`shell/apps/universe/tests/test_episode.py` already covers the operator scenario:

| Test | Scenario | Status |
| --- | --- | --- |
| `test_9_cross_workspace_cast_rejected` | Cross-workspace teammate → 400 | **PASS** |
| `test_10_cross_universe_cast_rejected` | Cross-Universe teammate → 400 | **PASS** |
| `test_11_legacy_teammate_cast_rejected` | Teammate with `universe=NULL` → 400 | **PASS** |
| `test_13_cast_add_via_api_201` | Same-Universe teammate via API → 201 | **PASS** |

The positive-path test is byte-shape-identical to what the SPA does (`APIClient.post("/api/episodes/<id>/cast/", {"teammate": str(pk)}, format="json")`). Not a regression from an incomplete prior fix.

### §19.4 Server log for the reported window contains ZERO cast POST attempts

`/tmp/character-os-django.log` covers 22:56–23:28 UTC. In that window the log contains:

- 1× `POST /api/knowledge/74e7f18f-…/attach/` → 200 (Chris attaching Ruby m2m to the KD — from §17)
- 1× `POST /api/episodes/` → **201** (Chris creating Fox & Flour Episode `77b04b6b`)
- 3× `POST /api/episodes/` → **400** (75 bytes each — the `episode_unique_title_per_universe` `UniqueTogetherValidator` error diagnosed in the previous turn; Chris retrying Episode-create with the same title)
- Zero `POST /api/episodes/…/cast/` attempts

No `403`, no `500`, no cast-endpoint traffic of any kind. Given the Vite proxy config (`web/vite.config.ts`) proxies `/api/*` to Django at `:8010` with `cookieDomainRewrite: ""`, a successful click in the SPA would appear in this log. It does not.

### §19.5 Two hypotheses consistent with the evidence

**Hypothesis A (most likely on current evidence):** The "cast-add 400" report is a misattribution of the still-recurring `POST /api/episodes/ → 400` (unique-title constraint from the previous turn). Chris may have interpreted the earlier failure as a cast-add failure, since both surface on the same Episode detail page workflow and both return HTTP 400.

**Hypothesis B:** Chris did click "Add to cast" but the SPA's `handleAddCast` short-circuited on `if (!castPick) return;` (no teammate selected in the dropdown), producing no HTTP request. The picker's disabled state should prevent this visually, but if Ruby's option was not selected before clicking, the request never fires — and no 400 is possible because no request is made.

Either hypothesis explains the absence of cast-add traffic in the log while being consistent with Chris's user-facing impression.

### §19.6 What would change my conclusion

Chris opening browser DevTools **Network** tab, clicking Add-to-cast, and sharing:
1. The exact request URL
2. The exact request body
3. The exact response status
4. The exact response body

If the request appears and the response is genuinely 400, I will re-open this section with the new evidence. Until then, inventing a fix would violate the "smallest real fix" rule and would risk weakening the signal / clean / constraint defense-in-depth for a phantom bug.

### §19.7 Prior-cast-bug context (searched; not found)

Grep across the tree for prior cast fixes surfaces only the SESSION 262 introduction of `m2m_changed pre_add` signal-based validation (`shell/apps/universe/signals.py`) and the SESSION 269 §12 atomic `cast_ids` at Episode-create (`EpisodeSerializer.create`). Both come with tests. There is no half-fixed prior cast bug this could be a regression of.

### §19.8 Explicit non-changes during §19

- No production code changed (no view, no serializer, no signal, no model, no SPA component, no migration).
- No test file changed.
- No EpisodeCast row created outside a transaction that rolled back. **Post-diagnostic `Episode.cast.count() = 0` for Episode `77b04b6b`** — same as pre-diagnostic.
- No Ruby persona / voice / avatar / brand / universe / m2m modification.
- No KnowledgeDocument mutation.
- No Composition, Episode (new), NarrativeMemory, PublishBundle created.
- No experiment env vars set. No provider mocks toggled. Runtime unchanged. `_expansion_hint` CORRECT_ANCHOR preserved.
- No manual DB shell insert of EpisodeCast — as Chris explicitly forbade.

### §19.9 §19 return values

- **Exact 400 error:** none captured; the only 400s in the server log are `POST /api/episodes/` with body `{"non_field_errors":["The fields universe, title must make a unique set."]}` (75 bytes — the Episode-create duplicate-title constraint, previously diagnosed). Zero `POST /api/episodes/…/cast/` 400s in the reported window.
- **Root cause:** on current evidence, no defect exists in the cast-add path. Backend accepts the exact Ruby-into-Fox&Flour cast add across three independent layers (view / signal / model.clean).
- **Regression from prior fix?** No — cast tests 9–14 all pass; there is no half-fixed prior cast bug.
- **Files changed:** none.
- **Tests:** 4 relevant existing cast tests pass (`test_9`, `test_10`, `test_11`, `test_13`). No new test written because no failure was reproduced.
- **Commit SHA:** (this section commits diagnostic evidence + doc only; no code fix.)
- **Runtime health:** clean; `main == origin/main`; Django 302 / media-engine ok-all-mocks-false / Vite 200; no experiment env vars.
- **Exact action Chris should retry:**
  1. Open browser DevTools → Network tab (Preserve log ON).
  2. Navigate to `/workspace/episodes/77b04b6b-110d-408d-82a3-a04e5ca66417`.
  3. Scroll to §2 Cast → select **Ruby** in the dropdown → click **Add to cast**.
  4. In the Network tab, find the `POST /api/episodes/…/cast/` row.
  5. Report back: request URL · request body · response status · response body.

---

## §20. §19 COMMIT PROVENANCE

- §19 diagnostic-evidence commit: **`9e34844`** — `docs(session-273): §19 cast-add 400 diagnostic — NOT REPRODUCED; no fix landed`
- Pushed to `origin/main`.
- Diagnostic script (read-only, atomic-rollback): `scripts/session273_diag_cast_400.py`
- Diagnostic evidence sidecar: `docs/design/session_273_experiment_data/06_diag_cast_400.json` (2,917 bytes)

---

## §21. CAST-ADD 404 FOLLOW-UP — SPA URL-SHAPE HYPOTHESIS; NO FIX LANDED

**Status:** Chris now reports HTTP 404 from the same "Add to cast" action. Diagnostic ran against the same substrate. **Zero 404s in the entire Django access log** (`/tmp/character-os-django.log`, 246 lines, full session window 22:56 – 23:38 UTC — `grep -iE "404|Not Found"` returns empty). Chris's browser 404 did not reach Django. This section documents the URL-shape truth table and the strongest single hypothesis, but **does not land a production fix** until Chris shares the exact DevTools Network row so hypothesis becomes evidence.

**Evidence sidecar:** `docs/design/session_273_experiment_data/07_diag_cast_404.json` (2,996 bytes).
**Diagnostic script:** `scripts/session273_diag_cast_404.py` (read-only, atomic-rollback).

### §21.1 Live-observation preflight (before any restart / fix)

| Service | PID | ELAPSED | Command tail |
| --- | --- | --- | --- |
| Media-engine (`:8001`) | 12677 | 02:24:42 | `uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning` |
| Vite (`:5174`) | 12699 | 02:24:42 | `node vite.js` |
| Django (`:8010`) | 12705 | 02:24:42 | `manage.py runserver 0.0.0.0:8010` |

All three services started together (`start-local-real.sh`) 2 h 24 min before this section. Source-file mtimes on the relevant SPA + Django files predate service start:

| File | Last-modified |
| --- | --- |
| `web/src/lib/api/episodes.ts` | Aug 19 10:05 |
| `web/src/routes/workspace/episodes.$id.tsx` | Aug 19 10:06 |
| `web/vite.config.ts` | Aug 16 17:53 |
| `shell/apps/universe/views.py` | Aug 17 17:53 |

`git log -1` on those files → commit `06ba7721` (2026-08-19 10:22). Both Vite and Django are running current-HEAD code. **Restart is not a candidate fix.** Vite HMR would have reloaded any mid-session edits anyway.

Vite proxy (`web/vite.config.ts`) still forwards `/api` → `http://localhost:8010` with `cookieDomainRewrite: ""` and `changeOrigin: true`. Any browser request whose path begins `/api/*` is proxied to Django. If Django receives the request, it appears in `/tmp/character-os-django.log`. **Zero cast POSTs and zero 404s appear in that log.**

### §21.2 URL-shape truth table — what each candidate malformed URL returns

Nine probes fired via DRF `APIClient` force-authenticated as Chris, each inside `transaction.atomic()` + `savepoint_rollback` (nothing persists):

| Probe | Method + URL | Status | Body (first ≤200 bytes) |
| --- | --- | --- | --- |
| canonical | POST `/api/episodes/77b04b6b-…/cast/` | **201** | full Episode payload with `cast:[{Ruby}]` |
| **id_literal_undefined** | POST `/api/episodes/undefined/cast/` | **404** | **`{"detail":"Not found."}` (23 bytes)** |
| id_literal_null | POST `/api/episodes/null/cast/` | **404** | `{"detail":"Not found."}` (23 bytes) |
| post_to_cast_remove_url | POST `/api/episodes/77b04b6b-…/cast/5875a7b4-…/` | 405 | `{"detail":"Method \"POST\" not allowed."}` (41 bytes) |
| missing_api_prefix | POST `/episodes/77b04b6b-…/cast/` | 404 | Django HTML "Page not found" (4,157 bytes) |
| missing_teammate_key | POST `/api/episodes/77b04b6b-…/cast/` with `{}` | 400 | `{"teammate":"required"}` (23 bytes) |
| bad_uuid_shape | POST `/api/episodes/not-a-uuid/cast/` | 404 | `{"detail":"Not found."}` (23 bytes) |
| wrong_episode_uuid | POST `/api/episodes/00000000-…/cast/` | 404 | `{"detail":"No Episode matches the given query."}` (48 bytes) |
| sanity_get_episode | GET `/api/episodes/77b04b6b-…/` | 200 | Episode payload (381 bytes) |

Three candidate SPA malformations produce 404 with the DRF-standard `{"detail":"Not found."}` body:
- `id_literal_undefined` (JS template literal `${undefined}` → path segment `"undefined"`)
- `id_literal_null` (same idea, `${null}`)
- `bad_uuid_shape` (any string DRF's UUID router rejects)

If Chris's `apiJson` wrapper (see `web/src/lib/api/client.ts:76–78`) received one of these, the operator-visible message via `alert(err.message)` would be **`"POST /api/episodes/undefined/cast/ → 404"`** or **`"POST /api/episodes/null/cast/ → 404"`** or **`"POST /api/episodes/not-a-uuid/cast/ → 404"`**.

### §21.3 Strongest single hypothesis on current evidence

**`episodeId` is `undefined` at the moment the mutation fires** in `useAddCastMember` (`web/src/lib/api/episodes.ts:217–232`):

```typescript
export function useAddCastMember(episodeId: string | undefined) {
  // ...
  mutationFn: async (teammateId: string) =>
    apiJson<Episode>(
      `/api/episodes/${episodeId}/cast/`,   // ← ${undefined} → "undefined"
      { method: "POST", body: { teammate: teammateId } },
      (json) => episodeSchema.parse(json),
    ),
```

If `episodeId` is `undefined` when the closure is created (before React re-renders with the URL param), the URL becomes the literal string `/api/episodes/undefined/cast/`. Django then returns exactly `404 {"detail":"Not found."}` (23 bytes) — matches the truth table.

**This hypothesis is contradicted by one observation:** the Django access log contains zero requests to `/api/episodes/undefined/cast/` (or any 404). If the SPA had actually sent this request, it would have been proxied by Vite (which is proxying `/api/*` correctly) and logged by Django. So one of the following must also be true:
1. Chris's retry happened but the SPA short-circuited before issuing the fetch (e.g., a client-side guard, an early `return`, or a React Query mutation state that never fired).
2. The 404 Chris sees is a browser-cached response or a UI-only render that never corresponded to a live HTTP request.
3. Chris's retry hit a URL that returns a 404 from something other than Django (e.g., a static asset), and the mental attribution to the cast button is misplaced.

### §21.4 Restart / rebuild required?

**No.** PIDs + mtimes prove services are running current-HEAD code. Vite HMR keeps the SPA bundle current. Nothing about a restart would change any observed behavior.

### §21.5 Smallest defensive candidate (NOT LANDED)

If Chris's next reproduction confirms `/api/episodes/undefined/cast/` in DevTools Network, the smallest correct fix is a **client-side guard** in `useAddCastMember` (and `useRemoveCastMember`, and any peer mutation that shares this template-literal URL pattern) that throws a typed `ApiError` **before** issuing the fetch when `episodeId` is `undefined` / empty. This is a defensive fix — never construct a URL that can't be valid.

Plus a Vitest regression test asserting:
- Calling `useAddCastMember(undefined).mutate(rubyId)` produces a synchronous / thrown error rather than an HTTP request to `.../undefined/cast/`.
- Calling `useAddCastMember(realEpisodeId).mutate(rubyId)` produces `POST /api/episodes/<realEpisodeId>/cast/` with body `{teammate: rubyId}`.

This fix does **not** weaken backend validation, does **not** special-case Ruby / Fox & Flour, and would work for arbitrary future Universes and characters. It would improve the operator-visible error text from "→ 404" to something like "cast add requested with no episode context — refresh the page and try again".

**BUT** the fix does not explain **why** `episodeId` is undefined at the moment of click. That still needs Chris's DevTools evidence to root-cause. Landing the defensive guard without root-causing risks masking a real underlying bug.

### §21.6 Why no fix landed in this section

- Django access log evidence contradicts the SPA-URL-undefined hypothesis (zero cast POSTs, zero 404s reaching Django).
- The "smallest real fix" rule requires proving the failure mode before writing code. My probes show what Django *would* return for each candidate URL — they do not prove which URL Chris's SPA is sending.
- Landing a defensive guard without root-causing risks:
  - Silently masking a genuine navigation / state-management bug in the SPA
  - Producing a "better error message" that never surfaces in Chris's flow because the request path never reaches the guard for the reason we've hypothesised
  - Adding SPA test scaffolding that documents a scenario that may not actually occur

### §21.7 Exact action Chris should retry

Open browser **DevTools → Network** (☑️ Preserve log · ☑️ Fetch/XHR filter), then:

1. Reload `/workspace/episodes/77b04b6b-110d-408d-82a3-a04e5ca66417` (fresh mount).
2. Scroll to §2 Cast → select **Ruby** in the dropdown → click **Add to cast**.
3. In DevTools Network, find the POST row (if any).
4. Copy back:
   - Exact request URL (full path — expected `/api/episodes/77b04b6b-…/cast/`)
   - Exact request payload JSON
   - Response status (200 · 201 · 400 · 404 · 405 · other)
   - Response body

If **no row appears** at all, that means the SPA never issued the fetch — the failure is client-side and I'll trace `handleAddCast` / `useAddCastMember` state. If a row appears with a 404 whose URL contains `undefined` / `null` / a malformed UUID, §21.5's defensive fix becomes evidence-backed and lands next turn. If a row appears with a different status or unexpected URL, that shape drives the next diagnostic.

### §21.8 Explicit non-changes during §21

- No production code changed (no view, no serializer, no signal, no model, no SPA component, no migration).
- No test file changed.
- No EpisodeCast row created — all probes ran in `transaction.atomic()` + `savepoint_rollback`. `Episode 77b04b6b.cast.count() = 0` — same as pre-diagnostic.
- No service restarted.
- No Ruby persona / voice / avatar / KD / Universe modification.
- No Composition, Episode (new), NarrativeMemory, PublishBundle created.
- No experiment env vars set. No provider mocks toggled. `_expansion_hint` CORRECT_ANCHOR preserved.
- No manual DB / shell insertion of cast row.

### §21.9 §21 return values

- **Exact browser request URL/method:** not captured — Django log contains **zero** cast POSTs and **zero** 404s across the entire session; Chris's browser 404 did not reach Django. Awaiting DevTools evidence.
- **Exact 404 body:** hypothesized as DRF's `{"detail":"Not found."}` (23 bytes) if URL contains `undefined` / `null` / non-UUID; not confirmed against Chris's real request.
- **Which service returned it:** unknown — not Django (zero 404s in log); not Vite HMR (would render index.html for unknown SPA routes, not 404); possibly a browser-level failure or a UI-render of a stale mutation error.
- **Root cause:** unknown; strongest hypothesis on backend evidence is SPA URL-templating a null/undefined episodeId. Not confirmed.
- **Restart required?** No — running-code matches HEAD.
- **Files changed:** none (diagnostic evidence + this doc section only).
- **Tests:** existing cast tests (9 / 10 / 11 / 13 / 14) still pass; no new test written — inventing a test for the specific SPA state-management bug requires knowing the state.
- **Commit SHA:** recorded in §22 at commit time.
- **What Chris should retry:** §21.7 above — reproduce with DevTools open and share the exact Network row.

---

## §22. §21 COMMIT PROVENANCE

- §21 diagnostic-only commit: **`be86e33`** — `docs(session-273): §21 cast-add 404 follow-up — URL-shape truth table; no fix landed`
- Pushed to `origin/main`.
- Diagnostic script (read-only, atomic-rollback): `scripts/session273_diag_cast_404.py`
- Diagnostic evidence sidecar: `docs/design/session_273_experiment_data/07_diag_cast_404.json` (2,996 bytes)

---

## §23. RUBY SLICE β FIRST-RENDER FAILURE — DURATION CONTRACT / CORRECTIVE EXPANSION DIAGNOSTIC

**Status:** Slice β opened with a real Runway-mode render attempt on Ruby. Corrective expansion **fired with CORRECT_ANCHOR** and correctly refused to dispatch to the provider when the corrected script was still under the acceptance minimum. **No Runway call fired. Zero cost. No code defect.** This is a fresh-substrate finding that refines SESSION 272 §22.4's assumption about corrective expansion.

**Failed Composition preserved intact:** `35eace56-4611-4a0d-abdd-be5d764bb4b8`. Not retried, not deleted, not requeued.

**Evidence sidecar:** `docs/design/session_273_experiment_data/08_slice_beta_ruby_failed_composition.json` (5,576 bytes).
**Freeze script (read-only):** `scripts/session273_slice_beta_freeze.py`.

### §23.1 Failed Composition — all observability fields

| Field | Value |
| --- | --- |
| Composition ID | **`35eace56-4611-4a0d-abdd-be5d764bb4b8`** |
| status | `failed` |
| template_kind | `talking_head` |
| spokesperson | Ruby (`5875a7b4-…`) |
| episode | `77b04b6b-…` (Fox & Flour: *"Why our sourdough takes its time"*) |
| operator_topic | *"Why our sourdough takes its time"* |
| audience_hint | *""* (empty) |
| target_duration_seconds | **90** |
| writing_contract_version | **6** ✓ |
| **synthesis_attempt_count** | **2** ← corrective pass DID fire |
| **synthesis_predicted_seconds** | **61.0** |
| validation_failure_reason | `duration_contract:too_short` |
| render_dispatched_at | **`None`** ← Runway never called |
| cost_actual_micros | **0** ← zero cost |
| final_asset_id | `None` |
| knowledge_chunk_ids | `[]` — empty by design (only populated from produced-Asset `source_spec`; no Asset produced because K6 rejected) |
| memory_ids | `[]` — Fox & Flour has zero `NarrativeMemory` |
| verification_status | `rejected` |
| verification_warnings | *(empty)* |
| mock_mode | `False` |
| created_at | 2026-08-20 23:48:53 UTC |
| error_message (verbatim) | *"step 0 (generate_avatar_speech): PrimitiveError: Duration contract failed (too_short): generated script is approximately 61s (893 chars / 163 words), below the allowed 72-second minimum for a 90-second target (accept band 72-108s, 1080-1620 chars). No Runway call fired."* |

**Per-pass measurements:**

| Script | Chars | Words | Predicted secs (at 15 cps) |
| --- | --- | --- | --- |
| `first_pass_synthesis` | **594** | 106 | ~39.6 |
| `corrective_pass_synthesis` | **893** | 163 | **~61.0** |
| `synthesized_brief` (accepted brief) | **0** | 0 | — (nothing accepted) |
| `rejected_synthesis` (mirrors corrective) | 893 | 163 | ~61.0 |

**Corrective hint text (verbatim from `Composition.corrective_hint`):**

> `Your previous draft was 594 characters (106 words, estimated ~41s of speech). Target is 81s.`
> `EXPAND YOUR SCRIPT TO AT LEAST 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 378 more characters to meet the minimum.`
> `Preserve the central arc (opening → development → payoff → single closing invitation), the narrator perspective, and the factual grounding from the knowledge chunks. Expand secondary detail from the knowledge chunks — describe more of the sensory / emotional beats already implied. Do NOT restart with a new opening. Do NOT add a second call to action. Do NOT invent facts not present in the knowledge chunks.`

- ✓ contains **`EXPAND YOUR SCRIPT`** — SESSION 272 CORRECT_ANCHOR active
- ✓ does NOT contain `REWRITE THE SAME NARRATIVE ABOVE`

**Side-effect invariants (verified post-failure):**
- Ruby.universe_id = `1a0af807-…` (Fox & Flour) — unchanged
- Ruby.updated_at = 2026-08-20 22:44:22 — unchanged since §13.2 attach
- Episode `77b04b6b` cast = `[Ruby]` — unchanged
- KD `74e7f18f` universe = Fox & Flour, m2m = `[Ruby]`, content_hash unchanged
- NarrativeMemory in Fox & Flour = **0** (nothing was promoted or auto-created)
- No Asset created since composition timestamp

### §23.2 Duration-contract comparison across layers (target = 90 s)

Contracts derived directly from source-of-truth constants at `shell/character_os/script_synthesis.py:120–200`, `shell/character_os/duration_contract.py:82–150`, `shell/apps/compositions/primitives/avatar_speech.py:292`:

| Layer | Min chars | Ideal chars | Max chars | Min secs | Max secs | Ruby actual | Verdict on 893 chars |
| --- | --- | --- | --- | --- | --- | --- | --- |
| K6 synth-target budget (81s = 90 × 0.90 calibration bias) | 972 | 1215 | 1458 | (internal) | (internal) | 594 · 893 | first: below · corrective: **below hint min (972)** |
| K6 acceptance/rejection (raw 90s) | **1080** | 1350 | **1620** | **72** | **108** | 893 | **REJECTS — raises `DurationContractError(REASON_TOO_SHORT)`** |
| Primitive `generate_avatar_speech` acceptance | **1080** | — | **1620** | **72** | **108** | (never reached) | would reject |

**All three layers agree.** Same `_AVATAR_SPEECH_CHARS_PER_SECOND = 15`, same `_DURATION_TOLERANCE = 0.20`. The primitive uses `AVATAR_SPEECH_SAFE_MAX_CHARS = 1900` as `max_script_chars` on the K6 gate; the K6 gate IS the primitive's acceptance surface. There is no separate primitive-vs-K6 contract — they are the same call path.

### §23.3 What actually happened, step by step

1. Operator requested a 90 s talking_head via `/recipes/talking_head?episode=77b04b6b-…`.
2. `avatar_speech` primitive called `synthesize_with_duration_gate(target_duration_seconds=90, max_script_chars=1900)`.
3. `calibrated_synthesis_target(90) = round(90 × 0.90) = 81`. K6 was asked to aim for 81 s (biased downward per SESSION 253/254 calibration to compensate for gpt-5's habitual overshoot).
4. **First-pass K6 output: 594 chars / 106 words / ~41 s.** Below the 90 s acceptance min of 1080 chars → expansion corrective triggers.
5. Corrective hint constructed via `_expansion_hint` (`duration_contract.py:394`). Opens with **`EXPAND YOUR SCRIPT TO AT LEAST 972 CHARACTERS`** — CORRECT_ANCHOR active per SESSION 272 Slice F.
6. **Second-pass K6 output: 893 chars / 163 words / ~61 s.** Still below the 90 s acceptance min of 1080 chars.
7. Acceptance gate raises `DurationContractError(REASON_TOO_SHORT, actual_chars=893, effective_min=1080, effective_max=1620)`.
8. `avatar_speech` primitive catches the exception, persists **all nine SESSION 262 observability fields** onto the Composition (`first_pass_synthesis`, `corrective_hint`, `corrective_pass_synthesis`, `synthesis_attempt_count`, `synthesis_predicted_seconds`, `validation_failure_reason`, `rejected_synthesis`, `verification_status="rejected"`, `error_message`), then re-raises as `PrimitiveError`.
9. Composition step fails. Composition marked `failed`. **No Runway `/v1/avatar_videos` call fired. Zero cost.**

The system worked exactly as designed. The design intentionally allows **ONE** bounded corrective pass to prevent runaway LLM cost; when the second attempt also fails, the composition fails permanently rather than looping.

### §23.4 Why the LLM produced only 893 chars

The **corrective-pass output references KD content not present in `business_brief`:**

- *"walk-in fridge"* → in KD §Breads & sourdough only
- *"two active starters"* → in KD only
- *"15% whole wheat"* → in KD only (Ruby's business_brief says *"naturally leavened sourdough"* generically)
- *"deck oven"* → in KD only
- *"dark, blistered crust"* → in KD only

So retrieval DID fire and the model DID access the Fox & Flour KD. (Note: `Composition.knowledge_chunk_ids` remained `[]` because that field is only populated from produced-Asset `source_spec` — no Asset was produced. This is by design; not a bug.)

The LLM had good source material and still stopped at 893 chars vs the 972-char hint minimum (short by 79 chars, ~8%). Candidate explanations (not investigated further this slice):

| Candidate | Evidence supporting | Evidence against |
| --- | --- | --- |
| Sparse retrieved factual basis | — | Corrective clearly uses KD content beyond business_brief |
| K6.4 verifier removed material | — | `verification_warnings: []` — no rejections |
| Model constrained against elaboration | — | Hint explicitly asks for more |
| audience_hint compressed the response | — | `audience_hint: ""` (empty; no compression pressure) |
| **Minimal persona reduces character-native elaboration** | Ruby: `character_point_of_view`, `voice_signature_phrases`, `voice_avoid_phrases`, `always_emphasize`, `never_say`, `who_you_help`, `what_you_sell`, `desired_feeling` **all empty**. Compare Rivet Slice G §22.4 — richly populated persona produced +540 chars corrective expansion (623 → 1163). Ruby produced +299 (594 → 893). | — |
| Corrective hint synth-min (972) is below primitive acceptance-min (1080) — LLM aims at hint, not acceptance | Hint explicitly says "at least 972"; LLM stopped at 893 which is even below that | This is the SESSION 253/254 calibration bias (0.90); K6 aims low so its overshoot lands at operator target. Rivet's Slice G worked under the same calibration. |
| Output-token ceiling / other model constraint | — | No evidence in logs; 893 is well under any token cap |

**Strongest hypothesis on current evidence: minimal-persona × fresh-KD combination.** Not proven, but consistent with the Rivet-vs-Ruby comparison.

### §23.5 SESSION 272 §22.4 assumption — refinement, not contradiction

SESSION 272 §22.4 concluded (from Slice G real production Rivet render at 90 s):
> *"Corrective expansion is now a net-positive character-native-elaboration tool, not a canonical-regression risk. Long-form scripts can lean on corrective expansion instead of fighting it."*

Ruby's specimen adds this qualification (does not overturn):

> *Corrective expansion reaches the acceptance minimum reliably when the character carries rich persona fields (`character_point_of_view`, `voice_signature_phrases`, and/or `voice_avoid_phrases`) for the LLM to elaborate with. On a **wizard-default character** (only `business_brief` + `personality` + `tone_archetype` populated) at a 90 s target, a single bounded corrective pass may produce output that still falls short of the acceptance minimum. The gate correctly rejects; no Runway call fires; no cost is incurred. The failure is a **legitimate signal about substrate readiness for 90 s targets**, not a code defect and not a regression of the CORRECT_ANCHOR fix.*

Rivet-vs-Ruby comparison at target = 90 s:

| Metric | Rivet Slice G (SESSION 272 §22.4) | Ruby Slice β (this section) |
| --- | --- | --- |
| First-pass chars | 623 | 594 |
| Corrective-pass chars | **1163** (accepted, in band 1080–1620) | **893** (rejected, below 1080) |
| Expansion delta | **+540** | +299 |
| Final Composition status | COMPLETED | **failed** (zero cost) |
| Character persona shape | rich (signature phrases, POV, avoid list) | wizard-default (persona = personality + tone only) |
| KD | saturated (`218eb0d8` used in ≥5 renders) | fresh (`74e7f18f`, first render) |

### §23.6 Root cause + smallest fix

**Root cause:** LLM under-produced on the corrective pass (893 vs 972 hint minimum). The system correctly refused to dispatch. **Zero code defect.**

**Smallest fix: NONE landed.** No production code, test, migration, or SPA change made. Rationale:

- All three duration-contract layers agree (K6 synth · K6 acceptance · primitive acceptance — same code path, same constants).
- Corrective expansion fired.
- CORRECT_ANCHOR is present and correct.
- Design allows **ONE** bounded corrective pass; second failure is permanent by intent (bounded cost).
- Existing tests already cover this exact invariant: `test_gate_still_short_after_retry_raises` (`test_duration_contract_talking_head.py:294`) asserts that a two-undersize sequence raises `DurationContractError(REASON_TOO_SHORT)`. All 14 relevant existing tests pass.
- Changing any of `_DURATION_TOLERANCE` (0.20), `K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER` (0.90), or `_AVATAR_SPEECH_CHARS_PER_SECOND` (15) to make Ruby's 893 chars accept would violate Chris's Rule 7 constraints ("no weakening duration validation; no increasing tolerance just to accept 893 chars; no silently changing a 90s request into 60s"). Increasing the corrective-pass count (from 1 to 2) would violate the bounded-cost design without evidence that a third attempt would converge.

### §23.7 Regression coverage — sufficient, no new tests needed

The exact invariant Ruby's failure exercised is already tested:

| Test | Scenario | Status |
| --- | --- | --- |
| `test_gate_still_short_after_retry_raises` | 2 sequential undersize outputs → `DurationContractError(REASON_TOO_SHORT)` raised, gate refuses dispatch | **PASS** (verifies Ruby's exact path) |
| `test_avatar_speech_safe_max_chars_locked_at_1900` | Cap pinned at 1900 | **PASS** |
| `test_avatar_speech_delivery_rate_locked_at_15_cps` | CPS pinned at 15 | **PASS** |
| `test_90s_duration_math_reflects_15_cps` | Ruby's exact target math | **PASS** |
| `test_calibrated_synthesis_target_90s_is_81s` | 90 s → 81 s synth target | **PASS** |
| `test_synth_target_never_leaks_into_prompt_target_arg` | Synth-target does not leak into operator error surfaces | **PASS** |
| 8× SESSION 272 Slice F pins (`test_session272_slice_f_expansion_hint_anchor.py`) | CORRECT_ANCHOR preserved | **PASS** |

**Total: 14 tests, 14 PASS in 3.63 s.** The layer invariant Chris named ("anything synthesis accepts for dispatch must satisfy the primitive's duration contract for the same target") is structurally guaranteed — the primitive delegates directly to K6's gate; there is no separate primitive-side acceptance check. A test would be a tautology on the current code path.

### §23.8 Provider-call proof / cost proof

- `Composition.render_dispatched_at` = `None` — no step reached the media-engine dispatch phase.
- `Composition.cost_actual_micros` = **0**.
- `CompositionStep` for step 0 (`generate_avatar_speech`) marked `failed` with `error_message` matching the K6 rejection; `media_engine_task_id` not set; `output_asset_id` not set.
- No `Asset` created for Ruby since Composition timestamp.
- Media-engine log (`/tmp/character-os-media.log`, tail-checked) shows no new POST during the failed render window.
- Runway API log (via media-engine forwarding) shows no `/v1/avatar_videos` request in the render window.
- **Zero Runway credits consumed. Zero OpenAI cost persisted on Composition (though 2 K6 completions did fire; not currently persisted on `Composition.cost_actual_micros` per §5 observability-gap finding).**

### §23.9 Explicit non-changes during §23

- No production code changed (no `duration_contract.py`, no `script_synthesis.py`, no `avatar_speech.py`, no starters, no view, no serializer, no signal, no model, no SPA component, no migration).
- No test file added or edited.
- Failed Composition `35eace56-…` **preserved intact** — not deleted, not retried, not requeued, not edited.
- No new Composition created.
- No render dispatched.
- No NarrativeMemory created or promoted.
- No PublishBundle created.
- No Ruby persona / voice / avatar / brand / universe / m2m modification.
- No KnowledgeDocument mutation.
- No Episode mutation.
- Mason untouched.
- Patch's Workshop substrate untouched.
- No writing-contract version change (WCV still 6).
- No `_expansion_hint` / `_compression_hint` edit — CORRECT_ANCHOR preserved.
- No experiment env var set. No provider mock toggled. Runtime unchanged.
- No manual DB shell insertion.

### §23.10 §23 return values

- **Failed Composition UUID:** `35eace56-4611-4a0d-abdd-be5d764bb4b8`.
- **First-pass chars / words / predicted seconds:** **594 / 106 / ~41 s**.
- **`synthesis_attempt_count`:** **2**.
- **Did corrective expansion fire?** **YES** — `_expansion_hint` invoked with `synth_target=81, synth_min=972, synth_ideal=1215, synth_max=1458`.
- **Corrective-pass chars / words / predicted seconds:** **893 / 163 / ~61 s**.
- **Exact relevant `corrective_hint`:** *"EXPAND YOUR SCRIPT TO AT LEAST 972 CHARACTERS (aim for ~1215, do not exceed 1458). You currently need at least 378 more characters to meet the minimum."* (Full text in §23.1; contains `EXPAND YOUR SCRIPT`, does not contain `REWRITE THE SAME NARRATIVE ABOVE` — CORRECT_ANCHOR active.)
- **Why 893 chars "reached" `generate_avatar_speech`:** it did NOT reach the primitive's dispatch. K6's acceptance gate raised `DurationContractError(REASON_TOO_SHORT)` after the corrective pass. The `avatar_speech` primitive caught the exception, persisted observability, and re-raised as `PrimitiveError`. Zero Runway call.
- **Synthesis vs primitive duration-contract comparison:** IDENTICAL — same constants, same code path, no mismatch (§23.2 table).
- **Root cause:** LLM under-production on corrective pass. Strongest hypothesis: minimal-persona × fresh-KD (Ruby has 8 empty persona fields vs Rivet's rich signature phrases / POV / avoid list; Ruby's KD is on its first render vs Rivet's saturated `218eb0d8`).
- **Contradicts / refines SESSION 272?** **REFINES**, does not contradict. §22.4 held Rivet-on-90s; Ruby-on-90s shows the assumption is substrate-conditional. §23.5 records the refinement.
- **Smallest fix landed:** **NONE.** No code defect. System worked as designed. Existing 14 tests cover the invariant.
- **Regression tests:** all 14 relevant tests pass (§23.7). No new tests needed.
- **Provider-call count / proof no Runway spend:** zero Runway `/v1/avatar_videos` calls (§23.8).
- **`cost_actual_micros`:** **0**.
- **Files changed:** `docs/design/SESSION_273_PRODUCT_ORIENTATION_AND_NEXT_DIRECTION.md`, `docs/design/session_273_experiment_data/08_slice_beta_ruby_failed_composition.json`, `scripts/session273_slice_beta_freeze.py`. No production code, test, SPA, or migration edited.
- **§23 commit SHA:** recorded in §24 at commit time.
- **Exact action Chris should take next:** operator's decision. Options (evidence-supported, none pre-committed):
  1. **Retry the same 90 s render.** LLM output has variance; the same substrate may converge on the next attempt.
  2. **Reduce target to 60 s.** Halves the required char minimum (720 chars @ 60 s vs 1080 @ 90 s). Ruby's 594-char first pass is already inside a 60 s acceptance band (48–72 s). Fresh dogfood evidence for how the same character behaves at a smaller target.
  3. **Enrich Ruby's persona.** Populate `character_point_of_view`, one or two `voice_signature_phrases`, an `always_emphasize` clause — matches how Rivet is authored. Then retry 90 s. This tests the hypothesis in §23.4 directly and is reversible.
  4. **Enrich the Fox & Flour KD.** Add a second KD (still Universe-scoped + Ruby-scoped) with more of Ruby's operator-perspective content. Chris authors, not me.
  5. **Preserve the failed Composition as-is** and move on to a different substrate (Mason companion, or a different topic on Ruby). SESSION 272 pattern of freezing failed specimens applies.

---

## §24. §23 COMMIT PROVENANCE

- §23 diagnostic + assumption-refinement commit: (recorded at commit time — see git log)
- Freeze script (read-only): `scripts/session273_slice_beta_freeze.py`
- Failed-Composition evidence sidecar: `docs/design/session_273_experiment_data/08_slice_beta_ruby_failed_composition.json` (5,576 bytes)
