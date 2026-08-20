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

- SESSION 273 orientation doc commit: (recorded at commit time — see git log)

---

**End of SESSION 273 orientation document. No code changed. No direction pre-committed. Chris decides SESSION 273's actual work item after reading this and §22 of the SESSION 272 audit.**
