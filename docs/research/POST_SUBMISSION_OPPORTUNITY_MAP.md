# Post-Submission Opportunity Map — Avatar Broadening + Parked Work

**Date:** 2026-05-12
**Author:** Claude (Opus 4.7) for Chris (chris@donkeybetz.com)
**Status:** RESEARCH ONLY — no product code touched. Survey of everything
parked, scoped-but-not-shipped, and unexplored adjacent to Character OS's
current avatar surface.
**Triggered by:** *"Is there anything we can do to broaden the use of the
Avatars and things like that? I am having some thoughts on things we
might be able to do but I wanna make sure there's nothing else we are
missing out before we start mapping out everything (We might take most
of this app and merge it into another app)."*

> This doc complements `RUNWAY_API_CAPABILITY_MAP.md` (which catalogued
> the Runway API itself in 2026-05-08 terms) by surveying **product
> opportunities** layered on top of the now-shipped avatar primitive.
> Use this as the menu when deciding what to fold into a larger app
> or build next as a standalone slice.

---

## 0. Executive summary

Character OS today uses **6 of ~25 Runway endpoints** and exposes the
avatar primitive through **4 ad modes + 1 realtime conversation
surface**. That's a solid hackathon scope but a narrow product
surface — the avatar primitive can serve a much wider set of
outputs, use cases, distribution shapes, and platform roles.

Four groups of opportunity:

1. **Parked work** — concrete PRs already scoped where plumbing
   landed but the user-facing slice didn't (PR EA, PR EO-a-2 / b / c
   / d, PgVectorMemoryStore).
2. **Unused Runway capabilities** — endpoints with documented product
   value we haven't touched (Aleph `video_to_video`, `text_to_speech`
   standalone, `voice_dubbing` as ad narration, Act-Two
   `character_performance`, `documents` for richer RAG, `avatar_usage`
   for billing telemetry).
3. **Adjacent output formats and use cases** — new shapes the same
   avatar primitive could power without inventing new Runway calls
   (personalized greetings, customer support, sales pitch at scale,
   coaching, internal comms, etc.).
4. **Platform plays** — structural moves where Character OS becomes
   the substrate inside a larger app rather than a standalone
   product (SDK, marketplace, identity layer for agentic AI, BYOA
   SaaS, B2B for agencies, personal-use pivot).

Sections §1–§7 below are the inventory. §8 is the decision frame for
"merge into another app."

---

## 1. Parked PRs with concrete scope

### PR EA — Single-pass Long Ad via `speech.type=audio` + external TTS

Source: `docs/research/SPEECH_TYPE_AUDIO_FINDINGS.md` (2026-05-10)

**What's shipped:**
- **PR DY** — Probe. Confirmed Runway accepts `speech.type=audio` at
  **42s** (lip-sync clean, -0.04s drift, single 200 OK against
  Riggs's avatar). The "1-15s typical" doc note only applies to the
  text path.
- **PR DZ-a** — Probe. Confirmed `/v1/voices/preview` is NOT TTS —
  it's an ElevenLabs voice-DESIGN audition. No Runway endpoint TTSes
  arbitrary text in a specific bound voice.
- **PR DZ-b** — Plumbing. `build_avatar_video_body(avatar_id, *,
  chunk_text, audio_source)` extracted as a pure helper with 3 unit
  tests. Audio branch wired but unused.

**What remains (PR EA):**
- TTS source decision — three options:
  - **OpenAI `tts-1-hd`** (~$0.015/Long Ad, 6 voices, existing
    OpenAI key plumbing) — *recommended*
  - **ElevenLabs direct** (better timbre match, ~$0.06/Long Ad, new
    SDK + key)
  - **Runway round-trip** — burns 2× credits, defeats the purpose
- ~250 LoC across 6 files: new `Character.tts_voice` field, new
  `services/openai_tts_client.py`, new `generate_long_ad_v2`,
  settings feature flag `long_ad_mode`, frontend `tts_voice`
  picker, backend tests.
- **Open question to probe before shipping default:** does
  `gwm1_avatars` accept >60s audio? PR DY only verified 42s. Adds
  ~$1 in real-mode test credits.

**Note on what this does and doesn't unlock:**
- ✅ Unlocks: any future TTS-driven feature (personalized greetings
  at scale, voicemail, multi-language narration via the same `tts_voice`
  field but routed through `voice_dubbing`)
- ⚠️ Does NOT meaningfully extend video duration vs. today's
  chunk-and-stitch (PR DO already gets to ~60s). Win is *simplification*
  and *consistency*, not *length*.

### PR EO sub-slices (from SESSION 105)

These are the open campaign-workspace redesign threads. All have
concrete scope; none have been shipped past EO-a.

| Slice | What it ships | Backend changes |
|---|---|---|
| **EO-a-2** | Mode picker as the prominent first action in the campaign workspace (currently buried in `<CampaignLanes>`). | Frontend only |
| **EO-b** | Llama-generated thread titles fired in background after every `POST /realtime-transcript`. | `title: Optional[str]` on `TranscriptHistoryEntry` |
| **EO-c** | `memory_status` + per-thread Resume button + resume endpoint that synchronously captures the thread + injects a "RESUMING: <topic>" cue late in the personality. | `memory_status` field + new endpoint |
| **EO-d** | Cast badges on dialogue scene tiles ("Donny + Riggs"). | `character_ids: list[str]` on `OutputRecord` |
| **Campaign create/track UX rework** | Today's open complaint — modal flow + state pills + clearer onboarding. Three triangulation questions parked in SESSION 105. | Frontend only |

---

## 2. Unused Runway endpoints with real product value

Active endpoint coverage: 6/25 capabilities. The high-value gaps:

| Endpoint | What it unlocks | Effort | Demo value |
|---|---|---|---|
| **`video_to_video` (Aleph)** | One-click style-variant remix of a saved campaign. A/B testing across visual styles without re-rendering from scratch. | medium | high |
| **`voice_dubbing` (as ad narration)** | Same avatar, 29 languages. Today we ship dubs as sibling samples, not as the narration. Promoting them to *the* narration is the multilingual wedge. | medium | high |
| **`text_to_speech` standalone** | Pure narration audio from text + voice. The TTS source PR EA needs anyway. Pairs with ffmpeg amix for full audio bed. | low | high |
| **`speech_to_speech`** | Operator records narration in their own voice, transforms to brand voice. Lowers the bar for personal use cases. | low | medium |
| **`voice_isolation`** | Strip background noise from voice samples before cloning. Quality lift on the existing clone flow. | low | low |
| **`sound_effect`** | Generate SFX from text. Pairs with TTS for full audio bed (intro stinger, transition whoosh, outro). | low | medium |
| **`documents` (broader use)** | Beyond memory: PDFs, brand guidelines, product specs, FAQ libraries. Avatar grounds every answer in operator-curated docs, not just conversation memory. | low | medium |
| **`avatar_conversations` DELETE** | Operator can clean up old transcripts. Read path already wired (PR AJ). | trivial | low |
| **`avatar_usage`** | Per-account quota telemetry. Powers pricing/billing tier ("you have X minutes left this month"). | low | low |
| **`uploads`** | Server-side asset upload for large user files. Today we use data URIs (~5 MB practical cap). | low | low |
| **`task` DELETE (cancel)** | Cancel a running render. Higher value for the multi-minute Long Ad pipeline than for 5-10s clips. | low | low |
| **Multi-ref image generation** | Up to 16 reference images instead of 1. Brand-guidelines + product-shot + style-board grounding. One-prop change in the existing image call. | trivial | medium |
| **`character_performance` (Act-Two)** | Drive an avatar with a recorded performance video. **VALIDATED 2026-05-12 PR EX** — works end-to-end, BUT requires HUMAN face geometry on the character portrait. Mascot/anthropomorphic characters fail face detection. See PR EX writeup in SESSION 105 for full details + the empirical signal it produced for the merge thesis. | medium | **HIGH** (only ~for human-character lineups) |
| **`workflows`** | Run pre-published Runway Workflows. Closer to no-code marketplace than developer API; uncertain fit. | unknown | unclear |

---

## 3. Avatar output formats we haven't built

Same avatar primitive (`/v1/avatar_videos`), new shapes:

| Format | What it'd look like | Effort | Anchor capability |
|---|---|---|---|
| **Personalized greetings at scale** | Operator uploads CSV of `{name, company}` → 100 avatar clips that each say *"Hi Sarah, I noticed Acme just raised…"*. Per-row TTS → `avatar_videos`. | low | TTS + batch |
| **Avatar slideshow / explainer** | Slides + avatar inset speaking, picture-in-picture. ffmpeg overlay on existing avatar output. | low | ffmpeg |
| **Vertical-first Reels with avatar inset** | B-roll plays full-screen, avatar talks in a circular inset bottom-left. Different from current Reels (full-screen letterbox). | low | ffmpeg |
| **Long-form podcast / interview** | Two avatars trading 20+ lines, music bed, intro/outro. Extends Dialogue Scene. | low | dialogue + sound_effect |
| **Avatar voicemail / video DM** | Type a message → avatar delivers it as 30s MP4 → shareable link. No real-time, no rendering wait at view time. | low | avatar_videos |
| **Avatar-narrated newsletters** | RSS feed or text input → weekly summary video. Cron-fired. | medium | TTS + scheduling |
| **Live ticker / news anchor** | Daily news brief, RSS → script → avatar video. Same anchor every day; brand-builds via repetition. | medium | TTS + scheduling |
| **Training / course modules** | Multi-segment lesson with chapters, navigation, quiz interruptions. | medium | dialogue + UI work |

---

## 4. Use cases we haven't targeted

Same avatar primitive, different personas. Each could be its own product.

| Persona | What they'd buy | Anchor capability |
|---|---|---|
| **Customer support teams** | Avatar answers FAQs, RAG-grounded on product docs. *We already have memory + RAG + 9-tool loop.* | realtime + documents |
| **Sales teams** | Avatar delivers personalized pitch per prospect, pulling from CRM. Same rep across thousands of meetings. | avatar_videos + variable substitution |
| **Educators / coaches** | Course narration, language tutoring, fitness coaching. Riggs Rally archetype scales. | avatar_videos + memory |
| **Founders / executives** | Internal comms when traveling. All-hands video sent while on a plane. | avatar_videos |
| **Therapists / journaling apps** | Daily check-in companion with cross-session memory. *Our memory architecture maps perfectly.* | realtime + memory |
| **Real estate agents** | Same agent narrates every listing tour. Personalized closing for each property. | avatar_videos batch |
| **Restaurants / local businesses** | Owner avatar greets website visitors, answers hours/menu questions, takes simple voice reservations. | realtime |
| **HR onboarding** | Welcome video for every new hire, named, with their team context. | avatar_videos batch |
| **Lawyers / legal intake** | First-line intake avatar. Triages, captures details, hands off. | realtime + memory + tools |

---

## 5. Distribution / integration shapes

Where the avatar lives, beyond the Character OS web app.

| Surface | Why | Effort |
|---|---|---|
| **Slack / Teams bot** | `/avatar tell-the-team about Q4` → posts a generated video to channel. Massive SMB adoption. | medium |
| **Zoom / Meet plugin** | Avatar joins a meeting on behalf of an absent host. Realtime session piped into a virtual camera. Tricky but feasible. | high |
| **Shopify / Webflow / WordPress plugin** | Embed avatar greeter on product pages. AI-driven engagement without devs. | medium |
| **CRM integration** (Salesforce, HubSpot) | Lead lands → auto-fire personalized pitch video, attach to record. | medium |
| **Browser extension** | "Have my avatar react to this article / generate a thread about it." Content creator workflow. | medium |
| **API for developers** | Character OS as substrate — like Twilio for SMS, but for avatar-led content. Other apps consume it. | medium |
| **Discord bot** | Community engagement avatar, hosted events, giveaway runner. | low |
| **iMessage / WhatsApp Business** | Avatar-led automated responses with realtime fallback to human. | high |

---

## 6. Platform plays — Character OS as substrate

Structural moves where Character OS stops being a standalone product
and becomes the engine underneath something else.

1. **Character OS as a developer SDK.** Other apps embed our
   avatar + memory + conversation infrastructure. They bring users;
   we provide the AI persona layer. Per-seat or per-minute pricing.
2. **Character OS as the persistent identity layer for agentic AI.**
   Every AI agent should have a face, voice, name, and memory — we
   have all four. Position it as the missing layer between *agent
   frameworks* (LangChain, AutoGPT, AGENT SDK) and *user-facing AI
   products*.
3. **BYOA — "Bring Your Own Avatar" SaaS.** Users upload their own
   portraits + voice samples → get a complete spokesperson identity
   they can deploy anywhere. Lower price point, broader audience
   than "agencies building brand spokespersons."
4. **Avatar marketplace.** Pre-built archetypes (CEO, Coach, Doctor,
   Teacher, Founder, Mascot) others rent. Revenue-share with the
   creator who designed them.
5. **B2B Avatar SaaS for agencies.** Agencies sell branded
   spokespersons to small businesses. Character OS is the
   back-office; agencies handle client relationships and creative
   direction.
6. **Character OS for personal use.** Stop targeting brands
   entirely — let any individual create a digital twin for personal
   communication. Voicemail, video diaries, family updates,
   accessibility-driven outputs. Different market, totally different
   pricing.

---

## 7. Architecture upgrade paths

Technical capabilities that unlock product moves listed above.

| Upgrade | Status | What it enables |
|---|---|---|
| **PgVectorMemoryStore (memory Phase 3)** | Interface in place; ~1 new class + Postgres + pgvector + Ollama embeddings | Semantic recall ("what did we discuss about pricing?" finds matching threads even if "pricing" wasn't in the title). Required for any production-scale memory. |
| **`QueryWeightedComposer`** | Sketched in SESSION 105 | Memory composer that ranks entries by semantic similarity instead of pure recency. Pairs with PgVector. |
| **`ExternalFeedSource`** | Interface in place; never wired | Operator's other apps push memory entries in. CRM notes → spokesperson memory. Slack threads → memory. |
| **External TTS provider** (OpenAI / ElevenLabs) | Not wired | Required for PR EA, personalized greetings, all batch avatar generation. |
| **Postgres / SQLite migration** | All storage is JSON files today | Fine for hackathon, friction for production scale. PgVectorMemoryStore is the wedge. |
| **Background job queue** | Today: synchronous request-response or fire-and-forget threads | Required for batch generation (1000 personalized greetings, scheduled newsletters, cron-fired briefs). Could be Celery, RQ, or built on FastAPI's BackgroundTasks. |
| **Multi-tenant data model** | Single-operator today | Required for any SaaS path. Adds `organization_id` to every record, scopes JsonStore reads, builds an auth layer. |
| **Auth / billing layer** | None today | Required for any external-customer-facing surface. Stripe + Clerk-shaped solutions are days, not weeks. |

---

## 8. Decision frame — "merge into another app"

The operator flagged: *"We might take most of this app and merge it
into another app."*

What gets merged depends entirely on the target app's existing
shape. Five archetypes and the natural bridges:

| Target app type | Natural bridges from Character OS |
|---|---|
| **Sales / outreach / CRM** | Personalized greetings, sales pitch avatars at scale, CRM integration, lead-triggered video generation. Memory tracks per-prospect history. |
| **Content creation / agency tools** | Avatar-narrated newsletters, A/B style remix (Aleph), slideshow explainers, multilingual dubs as primary narration. |
| **Education / coaching / training** | Realtime + memory loop is 80% of the product. The layer on top is course structure, progress tracking, completion certs. |
| **Community / Discord-shaped / social** | Avatar bots, hosted events, community moderation, AMA recordings, member-onboarding videos. |
| **Sports analytics / domain-specific data product** | Avatar-led video summaries (plays/games/highlights), multi-language coverage, RSS-fed daily briefs, personalized analyst commentary. |
| **Personal assistant / journaling / wellness** | Cross-session memory + realtime is the killer combo. Therapist/coach use case directly maps to existing architecture. |

**Three questions to answer before mapping:**

1. **What does the target app already do that Character OS doesn't?**
   Identifies the *receiving* product surface.
2. **What does Character OS bring that the target app *can't easily
   add itself*?** Memory + realtime + 9-tool agentic loop + Resolve
   integration are the harder-to-replicate pieces. Pure avatar
   rendering is a thin Runway wrapper anyone could rebuild.
3. **Is the merge "Character OS becomes a feature" or "Character OS
   becomes the spine"?** Determines architecture: feature = thin
   embed, spine = the target app's data model wraps ours.

---

## 9. Runway findings worth remembering

From earlier research, easy to forget:

1. **`client_event` is one-way.** The avatar's tool invocation
   reaches the dispatcher; the result *cannot* be returned to the
   avatar's LLM. PR EM-h mitigated by forcing narration *before*
   invocation. If Runway ships `server_event` / `tool_result`, our
   4 fire-and-forget tools become bidirectional automatically.
2. **Phoneme-driven lip-sync.** PR DY confirmed lip-sync works on
   *any* clean audio source, not just Runway's bound voice. macOS
   `say` audio lip-synced cleanly against Riggs's avatar. → External
   TTS is safe; brand voice is decorative, not load-bearing.
3. **`/v1/voices/preview` is voice-DESIGN audition only.** Not TTS.
   Confirmed in PR DZ-a.
4. **Realtime is WebRTC, 5-min hard cap, mic required, cam optional.**
   The 9-tool agentic loop runs over the `client_event` channel.
5. **`@runwayml/avatars-react` SDK handles the WebRTC handshake.**
   No need to run STUN/TURN ourselves.

---

## 10. Quick-start when picking up

1. Read this doc end-to-end with the user.
2. Identify which target app the merge is into (§8 question 1).
3. Pick the bridge category (§8 table).
4. Cross-reference against §1 (parked PRs) and §3-§4 (output
   formats / use cases) to identify what's *already partially built*
   for that bridge.
5. Map a minimum-viable merge slice + the parked-work follow-up
   roadmap.

If the target app isn't picked yet: the highest-leverage standalone
moves from this doc are:

- **PR EA** — Single-pass Long Ad via OpenAI TTS. Small, unblocks
  every batch / personalized / scheduled avatar feature.
- **`voice_dubbing` as ad narration** — Same Donny, 29 languages.
  Biggest enterprise wedge.
- **PR EO-b/c** (thread titles + Resume) — Makes the persistent
  spokesperson pitch *feel* persistent.
- **Aleph `video_to_video`** — One-click style A/B for any saved
  campaign.

Pick whichever lines up with the merge target. Or pick none and
focus on the UI redesign arc (today's open thread) before adding
more surface area.
