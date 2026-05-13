<!--
PROVENANCE
==========
Imported 2026-05-13 (SESSION 113) from
`runway-hackathon/docs/design/UI_REDESIGN_V2.md` via `cp`. The
file was authored in the runway-hackathon repo on the same day
the character-os repo was scaffolded (SESSION 106) but never
copied across — five sessions of handoffs referenced it as
canonical anyway. SESSION 113 closes that drift.

Content below is byte-identical to the runway-hackathon source.
Do not hand-edit; if amendments are needed, decide whether to
edit in place here (character-os now owns the file) or branch
into a separate `UI_REDESIGN_V3.md` so the original sign-off
log stays intact.
-->

# Character OS — UI Redesign v2 + Monetization Design Doc

**Date:** 2026-05-13
**Author:** Claude (Opus 4.7) for Chris (chris@donkeybetz.com)
**Status:** DESIGN LOCK — locks the customer, naming, data model,
monetization, and screen inventory for the post-hackathon monetization
push. No code touched. Wireframes happen *after* this doc.
**Supersedes:** SESSION 105's triangulation questions on Campaign
Creation / Tracking / Explanation — they're answered by killing the
campaign container entirely (see §4).
**Triggered by:** *"this app might be the closest one we have to go
make money with right now and the easiest to advertise. But to do
that we need to do a massive overhaul on the entire UI."*

> This doc is the bridge between "the hackathon shipped" and "this is
> a real product." It locks the answers to the four positioning
> questions that decide every downstream screen, then defines the
> data model and screen inventory that fall out of those answers.
> Once this is signed off, the next artifact is wireframes; after
> that, the Phase 1 implementation (Django shell + scaffolding).

---

## 0. Executive summary

**Audience:** Solo creators and small-business owners who do **not**
think of themselves as marketers.

**Headline positioning:** *Type your business. Click. Get a video ad.*
Speed-against-complexity. Phase-2 upgrade (after the u-d-b agent
port): *AI Creative Director — gives you three ad ideas, you pick
one, it makes them.*

**Monetization:** Tiered subscription, no credit math exposed to the
user.

  - **Starter** — $29/mo — 10 videos/mo, 1 spokesperson.
  - **Pro** — $79/mo — 30 videos/mo, 3 spokespeople.
  - **Agency** — $199/mo — unlimited videos, unlimited spokespeople,
    multi-seat workspace.

**Activation moment:** Avatar-narrated explainer series — short
videos (20-30s each) hosted *in the product itself* and on the
marketing site. The product's own avatars introduce, demo, and
walk a new user through their first video. Dogfooded marketing.

**Naming change:** "Campaign" is dead. The unit of work is a **video**.
Business/product context lives on the **spokesperson** (was Character).
Conversation threads live on the spokesperson. Optional topic tags
on videos for future grouping; not exposed in v1 UI.

**Architecture:** Django DRF shell (auth, users, workspaces, billing,
admin) in front of the existing FastAPI media engine (Runway, ffmpeg,
voice, realtime avatar). Shared Postgres+pgvector. The FastAPI media
engine is **not** rewritten.

**Auth:** Google OAuth primary, email/password backup.

**Workspace shape:** `Workspace` is a real entity from day one even
though v1 only exposes single-tenant solo use. Multi-seat / agency
flips on without a data migration when the Agency tier ships.

---

## 1. Customer + jobs-to-be-done

### 1.1 Who they are

Two overlapping personas. Different surface details, same underlying
needs:

**Persona A — Solo Creator.** Runs a personal brand, side hustle, or
content-driven business (coach, consultant, course-seller, indie
e-commerce store, YouTuber, course creator). Comfortable on the
internet, intimidated by video production. Has a phone but no studio.
Posts on Instagram / TikTok / LinkedIn / YouTube. Spends $20-100/mo
on creator tools already. Wants their face (or a *face*) on camera
without having to *be* on camera.

**Persona B — SMB owner who doesn't call themselves a marketer.**
Runs a bakery, plumbing company, dental practice, accounting firm,
landscaping outfit, local gym, boutique. Has a Google Business
Profile and a Facebook page. Has been told "you need video" by an
influencer or a friend's kid. Has tried Canva but the video editor
made them give up. Wants ads for the holiday sale, the new hours,
the new staff member. Will pay $30-80/mo for software if it
actually saves them from hiring a videographer.

### 1.2 What they don't have

- Patience for jargon. The words "persona," "audience segment,"
  "campaign," "creative brief," "tone of voice" make them bounce.
- Time. They're between customers, between classes, after dinner.
  A 10-minute onboarding wizard is a 10-minute reason to close the
  tab.
- A script. They cannot write an ad script. They can describe their
  business in plain language.
- Trust in AI tools. They've been burned by hallucinated nonsense.
  They want to *see the output* before they trust the workflow.

### 1.3 Jobs to be done

Listed in priority order. Every screen in §5 traces back to one of
these.

1. **JTBD-1 — "Make a video about my business that I can post today."**
   The 80% case. They open the app, describe their business in one
   paragraph, click a button, get a watchable video in <2 minutes.
2. **JTBD-2 — "Make a video about something specific that's
   happening right now."** Holiday sale, new product launch, new
   staff hire, schedule change, market update. Same flow as JTBD-1
   but with a per-video brief overriding the spokesperson's
   defaults.
3. **JTBD-3 — "Make a version of my video that fits where I'm
   posting it."** Vertical for Reels/TikTok, horizontal for
   YouTube, captioned for sound-off scroll feeds. (Already largely
   shipped — Reels export + caption pipeline exist.)
4. **JTBD-4 — "Make a series of videos that all feel like the same
   brand."** Brand consistency across multiple videos without the
   user having to specify it each time. This is where the
   *spokesperson-holds-context* model pays off.

### 1.4 Anti-personas

We are NOT building for:

- Marketing agencies producing ads for *other* people's brands.
  (Different workflow — multi-client, white-label, approval flows.
  Agency tier is a future option, not the launch audience.)
- Enterprises needing brand compliance, legal review, multi-stakeholder
  approval. (Wrong sales motion entirely — bottoms-up SaaS, not
  enterprise sales.)
- Power users who want a non-linear video editor. (Wrong product
  category — that's Descript or Final Cut.)
- Anyone whose first thought is "but what model is it using?"
  (Wrong audience — we hide the model layer.)

---

## 2. Pricing + monetization shape

### 2.1 The tiers

| Tier | Price | Videos/mo | Spokespeople | Seats | Headline benefit |
|---|---|---|---|---|---|
| **Starter** | $29/mo | 10 | 1 | 1 | "Make your first video in 2 minutes." |
| **Pro** | $79/mo | 30 | 3 | 1 | "Multiple brands, more output, advanced features." |
| **Agency** | $199/mo | unlimited | unlimited | 5 included, $30/seat after | "Manage clients, share spokespeople, team access." |

**Free trial:** 3 videos, no credit card. Email signup required.
Card capture on first paid generation. (Optional alt: 7-day free
trial with card. Defer this decision until we have conversion data
from the no-card flow.)

**Annual discount:** 2 months free on annual billing. Industry-standard
psychological anchor.

### 2.2 What the user sees vs. what we run

The user never sees:

- Runway credits
- OpenAI token counts
- Storage MB
- Model names (gen4_turbo, gpt-4, etc.)
- Render queue position

The user sees:

- "8 of 10 videos this month" (with date the counter resets)
- "Upgrade to Pro" CTAs when they hit the wall
- One badge per spokesperson (Ready / Setup needed)
- A render status spinner ("Making your video — about 90 seconds.")

### 2.3 Unit economics sanity check

Internal numbers to validate the tier pricing covers cost. (Numbers
are estimates — refine before launch from actual usage data.)

Per video (Spokesperson Ad, 30s):

- `/v1/avatar_videos` Runway call: ~5 credits ≈ $0.50 at current
  Runway pricing.
- OpenAI scriptwriting (if used): ~$0.02.
- Storage: ~$0.001/video/month.
- ffmpeg compute: ~$0.005/video.

Cost per video ≈ $0.55. At Starter, 10 videos = $5.50 cost on $29
revenue → 81% gross margin (before infra overhead). At Pro, 30
videos = $16.50 on $79 → 79% margin. Unlimited tier needs a
soft-limit honor system or a real cap; ship Agency with a "fair
use" guideline and revisit if anyone abuses it.

### 2.4 Why no credits / pay-as-you-go

Specifically for this audience:

- Non-marketers find credit math anxiety-inducing. "How many credits
  is this ad?" is a question they should never have to think about.
- Subscription billing is predictable for the user, predictable for
  our cash flow.
- Per-credit pricing reads as nickel-and-diming on the AppSumo /
  ProductHunt aesthetic the launch will live in.
- Tier-based limits are *also* a soft upsell — when the user hits 10
  videos and wants an 11th, they get a "Pro is $79/mo" CTA instead
  of a "Buy 10 more credits for $9.99" friction screen. Pro converts
  better than the credit topup.

---

## 3. Headline feature + activation

### 3.1 Launch headline

> **"Type your business. Click. Get a video ad."**

Subhead: *Real video ads with an AI spokesperson — no studio, no
script, no editor. Make your first one in 2 minutes.*

The screen-recording demo on the landing page literally shows the
30-second flow: open app → type "I run a bakery in Denver" →
click → 60s spinner → playable video. **The proof IS the demo.**

### 3.2 Phase 2 headline upgrade (post-u-d-b port)

> **"AI Creative Director — three ad ideas, one click to make them."**

Subhead: *Describe your business once. The AI Creative Director
proposes three ad concepts. Pick one — your AI spokesperson makes
the video.*

The tier names don't change; only the landing-page demo upgrades.
Existing customers get the upgrade for free as a feature
announcement. New customers see a more differentiated value prop on
day one.

### 3.3 Activation video series (the dogfood play)

A short series of avatar-narrated videos (20-30s each) made *with
the product*, hosted on:

- The marketing site landing page (one rotating featured video).
- The signup confirmation page.
- The first-run empty state inside the app.
- The help menu (browsable library).

Initial scope — 4 launch videos:

1. **"What is this thing?"** — Riggs (or whoever lands as the
   product mascot spokesperson) explains in 20s what the app does.
2. **"How do I make my first video?"** — Sasha walks through the
   create-spokesperson + first-video flow.
3. **"Why would I want this?"** — A non-marketer SMB owner-shaped
   spokesperson talks about the bakery/plumber use cases.
4. **"What's an AI spokesperson?"** — Demystifying the concept for
   audiences who haven't seen it before.

Each video uses the actual product's avatars, voice, and rendering
pipeline. The dogfood proof point is the marketing.

### 3.4 First-run experience inside the app

After signup → email confirm → first login:

1. Welcome screen. One sentence + one button.
2. Plays "What is this thing?" (Activation video #1) inline.
3. "Create your first spokesperson" — three pre-built options to
   pick from (Riggs / Sasha / Donny as starter templates) OR
   "Start from scratch."
4. "Tell us about your business" — one paragraph textarea. Optional
   "Show me examples" link expands sample one-liners.
5. "Make your first video" — one button. Click, watch the spinner,
   playback the result.

Total clicks from landed-on-landing-page to first video playing:
**6**. That number is the activation success metric.

---

## 4. Data model + naming

### 4.1 The new mental model

```
User (Django auth.User)
 │
 └─ Workspace                            ← real entity from day one
     │   • name, slug, owner_user_id
     │   • subscription (Stripe FK)
     │   • seat_count
     │
     ├─ Memberships (User ↔ Workspace)   ← multi-seat ready, single seat in v1
     │
     ├─ Spokesperson                     ← was Character. The unit of brand identity.
     │   • name, portrait, voice, avatar_id
     │   • business_brief (one paragraph — was campaign.brief_prompt)
     │   • personality, tone
     │   • status (ready, setup_needed)
     │   │
     │   ├─ Conversation Threads         ← realtime chats with this spokesperson
     │   │   • messages, transcripts, memory document
     │   │
     │   └─ Videos                       ← was OutputRecord. The unit of work.
     │       • title, brief (one-line override of spokesperson default)
     │       • kind (spokesperson_ad / dialogue_scene / cinematic / etc.)
     │       • output_path, duration, status
     │       • created_at, tags[]        ← tags hidden in v1 UI but persisted
     │       └─ Variants (vertical, captioned, dubbed, remix, ...) ← derived outputs
```

### 4.2 What just died

The **Campaign** entity in its current form. Specifically:

- The `Campaign` model in `backend/app/models.py`.
- The `campaigns.json` file storage.
- All routes under `/api/campaigns/{id}/...` except the ones that
  semantically belong on a spokesperson or a video — those get
  ported, not deleted.
- `CampaignWorkspace.jsx` and its lane subcomponents.
- The mode-picker-first creation flow.
- The "Campaigns" tab in the Identity workspace.

### 4.3 What got promoted up to Spokesperson

These were per-campaign fields; they're now per-spokesperson:

- `business` / `business_brief`
- `product` (becomes "what you sell" — also moves up)
- `audience` (folded into the broader spokesperson context)
- `tone`
- `realtime_transcript_history` → moves to a Conversation Thread sibling
- `memory_document` → moves to spokesperson level

### 4.4 What got pushed down to Video

These were per-campaign but actually per-output in disguise:

- The per-video script / one-line brief ("a promo for my Black
  Friday sale")
- The selected_mode (now implicit per video — choose at create time)
- The output kind (already per-output)

### 4.5 Migration path

In-place data migration when Phase 2 ships:

1. For each existing `campaigns.json` entry:
   - If the campaign has a `character_id`, promote
     business/product/audience/tone fields up to that character's
     spokesperson record.
   - For each `OutputRecord` under the campaign, create a `Video`
     record with the campaign's selected_concept as the brief.
   - Tag all videos from one campaign with the campaign's id as a
     hidden migration tag (so legacy grouping is recoverable but
     not exposed).
2. Conversation threads: move under the spokesperson; if the
   campaign was tied to one character, threads stay coherent.
3. Drop the `campaigns.json` file after verified migration.

This is destructive — a one-way migration. Worth a backup of
`backend/data/` before running.

### 4.6 The naming sweep

Codebase rename pass. Not just user-facing copy — actual code
identifiers:

| Old | New | Scope |
|---|---|---|
| `Campaign` (model) | (deleted) | backend |
| `campaign_id` | (gone or replaced with `spokesperson_id` / `video_id`) | backend + frontend |
| `Character` (model) | `Spokesperson` | both |
| `OutputRecord` | `Video` | both |
| "Campaign Workspace" | "Spokesperson Workspace" | UI copy |
| "Campaigns" tab | "Videos" or simply removed | UI copy |
| `selected_mode` | (per-video, set at create) | backend |
| `brief_prompt` | `business_brief` (on spokesperson) / `brief` (on video) | backend |

This is a big diff. Will need a coordinated commit + a backup
branch.

---

## 5. Screen inventory

The full list of screens the v2 UI needs. Each is one chunk of
wireframe work. Order is approximate user journey.

### 5.1 Public / pre-signup

- **S-01 — Landing page.** Headline + one-paragraph subhead + 30s
  screen-recording demo + activation video carousel + tier table +
  signup CTA + signin link.
- **S-02 — Pricing page.** Full tier comparison + FAQ + signup CTA.
- **S-03 — Signup screen.** Google OAuth (primary, big button) +
  email/password collapse. Workspace name autosuggested from
  Google profile.
- **S-04 — Signin screen.** Same as S-03 but for returning users.

### 5.2 First-run onboarding (post-signup, pre-first-video)

- **S-05 — Welcome / "what is this?"** Plays activation video #1
  inline. One CTA: "Create your first spokesperson."
- **S-06 — Create first spokesperson.** Three template picks
  (Riggs / Sasha / Donny) OR start from scratch. Defaults
  prefilled so the "make first video" path is reachable in 1-2
  more clicks.
- **S-07 — Tell us about your business.** One paragraph textarea
  on the spokesperson. Optional "Show examples" link expands
  sample text.
- **S-08 — Make your first video.** Big CTA. Spinner. Result
  playback. "Make another" / "Share" CTAs.

### 5.3 Main app

- **S-09 — Home dashboard.** All spokespeople as tiles + recent
  videos + "Make a video" primary CTA + usage meter ("8 of 10
  videos this month"). The first screen returning users see.
- **S-10 — Spokesperson workspace.** Single spokesperson detail
  view. Shows: identity (portrait + voice + business brief),
  videos library, conversation threads, memory. Edit affordances
  inline. Settings disclosure for advanced stuff.
- **S-11 — Video detail.** Single video playback + brief + variants
  (reels / dubbed / remix / captioned) + share/download/regenerate.
- **S-12 — Make video modal/flow.** From the dashboard or
  spokesperson workspace. One-line brief input → optional mode
  picker (default: spokesperson ad) → generate. No 6-step wizard.
- **S-13 — Realtime conversation.** Existing surface, attached to
  spokesperson. Conversations grouped by date or thread title.
- **S-14 — Spokesperson library / cross-spokesperson video gallery.**
  Optional in v1. Flat list with filter chips by spokesperson. Add
  if Pro tier customers complain about siloed-per-spokesperson
  galleries.

### 5.4 Account / billing

- **S-15 — Account settings.** Profile, email, password change,
  Google account link/unlink, delete account.
- **S-16 — Workspace settings.** Workspace name, members (Pro/Agency
  only), default spokesperson.
- **S-17 — Billing.** Current plan, usage meter, upgrade/downgrade,
  invoice history, payment method.
- **S-18 — Upgrade modal.** Triggered by limit walls. Tier
  comparison + CTA.

### 5.5 Activation video library

- **S-19 — Help / activation videos.** Browsable library of the
  avatar-narrated explainer videos. Hosted in-app, not just on the
  marketing site. Each video deep-links to the relevant feature.

### 5.6 Admin (Django-side, internal)

- **A-01 — User management.** Django admin default + custom views
  for support cases (impersonate, refund, extend trial).
- **A-02 — Workspace inspector.** See workspace state, recent
  renders, usage, support notes.
- **A-03 — Activation analytics.** Time-to-first-video, video
  completion rate, churn signals.

### 5.7 Not in v1

Explicitly deferred:

- Multi-seat agency UI (data model supports it; the screens to
  manage seats / invite team members come later).
- Cross-spokesperson "all videos" gallery (S-14 might land if asked).
- Video editor / non-linear timeline.
- Custom branding / white-label.
- API access for power users.
- Affiliate / referral programs.
- The AI Creative Director (it's the Phase 2 headline upgrade —
  designed-for, not built in v1).

---

## 6. Architecture decisions locked

### 6.1 Stack

- **Django + DRF** — `runway-character-os-shell` (new repo).
  Owns: auth, users, workspaces, memberships, subscriptions,
  spokespeople, videos, conversations, memory, admin, billing.
  Postgres + pgvector primary database. Celery + Redis for
  background jobs once spiders/agents port in.
- **FastAPI media engine** — current `runway-hackathon` repo,
  recast as an internal microservice. Owns: Runway API integration,
  ffmpeg orchestration, realtime avatar sessions, voice cloning,
  scene composites. Stateless from the Django shell's perspective —
  it receives a job, returns a result.
- **Frontend** — new React+Vite SPA hosted at the customer-facing
  domain. Talks to Django DRF for everything except live media
  streaming. May share components with the current
  `runway-hackathon` frontend during the transition, but the new
  SPA is the launch vehicle.

### 6.2 Boundary between Django and FastAPI

Django owns persistence. When the user clicks "make a video":

1. Frontend → Django: `POST /api/videos/` with brief + spokesperson_id.
2. Django creates a `Video` record with status `pending`.
3. Django enqueues a Celery task that calls FastAPI media engine.
4. FastAPI does the Runway/ffmpeg work, returns the result path.
5. Celery task updates Django's `Video` record with status,
   duration, output_path.
6. Frontend polls (or websockets) Django for status updates.

The FastAPI media engine never writes to the Django database
directly. Single source of truth.

### 6.3 Why this split survives scrutiny

- **Customer-facing surface is Django-native:** auth, billing,
  multi-tenancy, admin support tooling — all the boring-but-critical
  monetization plumbing.
- **Specialized async media pipeline stays FastAPI:** ~100 sessions
  of hard-won FastAPI patterns (async Runway polling, parallel
  ffmpeg chunking, websocket realtime avatar) survive untouched.
- **u-d-b port lands cleanly:** spiders/agents/embeddings/memory
  feel native in Django + Celery + pgvector, which is what u-d-b
  is.
- **Independent deploy + scale:** the media engine can scale on a
  GPU-friendly host while the shell scales on cheap web tier.

### 6.4 Auth

- **Google OAuth** via `django-allauth`. Primary, big-button on
  signup/signin.
- **Email/password** as backup, behind a "Or use email" disclosure.
- **Magic links** — *not* in v1. The audience finds them weird.
  Defer.

### 6.5 Billing

- **Stripe Subscriptions** via `dj-stripe`.
- Webhook handler updates `Workspace.subscription` status.
- Limit enforcement (videos/mo, spokespeople count) happens in
  Django middleware at the route level before FastAPI is even
  called.

### 6.6 Workspace model

- `Workspace` is its own model from day one.
- `Membership` (User ↔ Workspace through-model) supports many-to-many
  with a role field (owner / admin / editor / viewer). In v1 every
  workspace has exactly one membership and it's the owner. The
  table exists; the seat-management UI doesn't.
- Spokespeople and videos foreign-key to Workspace, not directly
  to User. Future-proofs every query for the agency tier.

### 6.7 Repository strategy

Locked 2026-05-13. The launch product gets a **new repo** named
`character-os` (placeholder — will rename if/when the product
rebrands, per Q1). Monorepo structure. The current
`runway-hackathon` repo and `unified-donkey-betz` are *donor*
repos, not merge targets.

#### 6.7.1 Why a new repo (not reuse `runway-hackathon`)

- `runway-hackathon` is named for the event, not the product.
  Customer-facing repo url, README, and CI labels need a clean
  identity from day one.
- Clean `git log` root for the new product. Investors / hires /
  future-you reading the git history shouldn't have to wade
  through 105 hackathon-era sessions to find the launch.
- Lets `runway-hackathon` stay frozen as the operator's daily-use
  pre-migration tool (per Q6) without polluting it with
  half-built Django shell code during Phase 1-2.

#### 6.7.2 Why monorepo (not multi-repo)

- Solo operator. Coordination overhead of multi-repo (synced
  versions, cross-repo PRs, separate CIs, separate context-kits)
  doesn't pay back.
- Most meaningful changes during Phase 1-3 span boundaries —
  a new model needs a Django migration + a FastAPI consumer
  update + a React form. Atomic commit across all three is the
  right ergonomic.
- Shared `docs/` and a single CLAUDE.md keep the context-kit
  story unified.
- Multi-repo can always be a later split if any one service
  outgrows the others. Hard to reverse the other direction.

#### 6.7.3 Target structure

```
character-os/                       ← new repo, working name
├── shell/                          ← Django DRF — customer-facing service
│   ├── manage.py
│   ├── pyproject.toml
│   ├── character_os/               ← Django project settings
│   └── apps/
│       ├── accounts/               ← User, Workspace, Membership, auth
│       ├── spokespeople/           ← Spokesperson model + endpoints
│       ├── videos/                 ← Video model + endpoints
│       ├── conversations/          ← Realtime thread persistence
│       ├── memory/                 ← Ported from runway-hackathon PR EM
│       ├── billing/                ← dj-stripe + tier middleware
│       ├── agents/                 ← Selective port from u-d-b (4-5 modules)
│       └── embeddings/             ← pgvector + selective u-d-b port
├── media-engine/                   ← git subtree of runway-hackathon/backend/
│   ├── app/                        ← Existing FastAPI app, history preserved
│   ├── data/                       ← Stays gitignored as today
│   └── pyproject.toml
├── web/                            ← New React+Vite SPA (replaces the old frontend)
├── infra/                          ← docker-compose, deploy configs, env templates
├── docs/                           ← Merged from runway-hackathon/docs/ + new
│   ├── design/                     ← This doc lives here
│   ├── handoffs/                   ← Continues from SESSION 105
│   └── research/                   ← Carried over
├── scripts/                        ← Merged + new (start-local-real.sh, etc.)
├── CLAUDE.md                       ← Refreshed for the new repo layout
└── README.md
```

#### 6.7.4 Donor repos — what comes in, what stays behind

**From `runway-hackathon` →** the backend lands at `media-engine/`
with history preserved via `git subtree add` (no `--squash`). The
`docs/` directory carries over into `docs/`. The `scripts/`
directory carries over. The frontend at `frontend/` is **left
behind** — the new SPA at `web/` starts fresh against the v2
design (cherry-picking individual components only when worth
porting).

**From `unified-donkey-betz` →** *selective port only*, not a
merge. The target modules:

1. `self_awareness/embeddings.py` patterns → `shell/apps/embeddings/`.
2. `agents/creative_director_agent.py` → `shell/apps/agents/`.
3. `agents/brand_identity_agent.py` → `shell/apps/agents/`.
4. `agents/content_strategy_agent.py` → `shell/apps/agents/`.
5. One trend spider as a template (operator picks which) →
   `shell/apps/agents/spiders/`.
6. `style_memory/` patterns → folded into `shell/apps/memory/`.

Everything else in u-d-b — the 71 other agents, 54 other spiders,
the sports analytics core, the `dashboard/`, the
`ai_opportunities/`, etc. — stays behind. u-d-b remains read-only
inspection per the existing CLAUDE.md rule.

#### 6.7.5 The migration commit sequence

Step-by-step for Phase 0 → Phase 1 transition. Not yet executed;
locked here as the plan.

1. **Local-only repo creation.** `mkdir character-os && cd
   character-os && git init`. Push to GitHub later, after the
   structure is verified.
2. **Scaffold the empty monorepo.** Top-level `README.md`,
   `CLAUDE.md`, `pyproject.toml` for the monorepo workspace,
   empty `shell/` `media-engine/` `web/` directories.
3. **Import FastAPI with history.** From inside the new repo:
   ```
   git remote add runway-hackathon \
     /Users/donkeyking/development/runway-hackathon
   git subtree add --prefix=media-engine \
     runway-hackathon main
   ```
   Verify: `cd media-engine && python -m app.main` boots.
4. **Carry the docs.** Same `git subtree` pattern for `docs/`,
   or simpler — `cp -r ../runway-hackathon/docs/* docs/`
   followed by a single docs-carryover commit. Either preserves
   the content; subtree preserves authorship.
5. **Carry the scripts.** Likewise.
6. **Scaffold Django shell skeleton.** `django-admin startproject
   character_os shell/`, create the empty `apps/` modules, wire
   up settings.
7. **First boot.** Run the Django dev server (`shell/manage.py
   runserver`) and the FastAPI media engine (`media-engine/python
   -m app.main`) in two terminals. Verify they can both run on
   different ports (8000 Django, 8001 FastAPI).
8. **Push to GitHub** as a new private repo `character-os`.
   Public-ize later when launching.
9. **Freeze `runway-hackathon`.** Tag `v-final-pre-migration` on
   `main`. Update `runway-hackathon/CLAUDE.md` with a
   "DEPRECATED — see character-os repo" notice. Operator's
   daily-use of the old app keeps working from that tag for as
   long as needed during the transition.

#### 6.7.6 What this strategy does NOT do

- Does not delete the `runway-hackathon` repo. Keep it indefinitely
  as the historical record + emergency fallback.
- Does not pre-port u-d-b code in Phase 1. u-d-b cherry-picks
  happen in Phase 4, after the shell exists and we know what
  shape the agents need to fit into.
- Does not commit to GitHub remote names / org names yet. Local
  repo first; remote decisions when push time arrives.
- Does not commit to a final product/brand name. `character-os`
  is the working repo name; the user-facing product name lives
  in env-driven copy and is changeable per Q1 without renaming
  the repo.

---

## 7. Implementation phases

This doc locks design. Actual sequencing of the build:

**Phase 0 — Pre-flight.** This doc + wireframes + Stripe account
setup + domain decision. Output: clickable Figma + a "yes ship it"
from the operator.

**Phase 1 — Django DRF shell scaffold.** New repo. Stand up:

- User + Workspace + Membership models, migrations.
- Google OAuth + email/password auth.
- Stripe Subscriptions + tier limits middleware.
- Admin scaffold.
- Empty stubs for Spokesperson + Video models (no media yet).
- Internal API for talking to FastAPI media engine (HTTP, JSON).

Output: a deployable Django app where a user can sign up, see an
empty dashboard, and have a billing entry.

**Phase 2 — Migrate the media data model.**

- Move Character → Spokesperson (rename + relocate to Django).
- Move OutputRecord → Video.
- Drop Campaign entity.
- Migration script: existing `campaigns.json` → new Django records.
- FastAPI media engine: become stateless, receive job specs from
  Django.

Output: existing rendered videos surface in the new shell; new
renders work end-to-end through Django → Celery → FastAPI.

**Phase 3 — Build the new UI.**

- Wireframes → components → screens per §5.
- New SPA wired to Django DRF.
- Activation video series shot using the product on existing
  spokespeople.
- Landing page + pricing page + signup flow.

Output: a launchable customer-facing product.

**Phase 4 — u-d-b feature port.**

- Embeddings + semantic search over Video library.
- Creative Director / Brand Identity agents.
- One trend spider (not 55).
- Memory enhancements from u-d-b's `style_memory`.

Output: Phase 2 headline upgrade ("AI Creative Director") landing
on the marketing site.

**Phase 5 — Agency tier UI.**

- Seat management.
- Spokesperson sharing.
- Per-client workspace switching.

Output: agency tier reachable.

---

## 8. Open questions

Things this doc *didn't* answer that need a decision before Phase 1
starts:

- **Q1 — Domain / brand name.** Is the launch product called
  "Character OS"? "Runway Studio"? Something else? Affects landing
  page, marketing copy, and the new Django repo name.
- **Q2 — Free trial shape.** 3 free videos with no card vs. 7-day
  full access with card capture. Recommended: start with no-card
  3-video trial; instrument conversion; iterate.
- **Q3 — Where do the activation videos get hosted physically?**
  Mux? Bunny.net? S3 + CloudFront? Vercel hosting? Decide before
  Phase 3 so the player wrapper is built once.
- **Q4 — Stripe Tax / VAT handling.** International customers will
  appear on day one. Stripe Tax is the easy answer; budget the
  cost.
- **Q5 — Mobile.** Phase 1 is desktop-web only. Where does mobile
  responsiveness sit in the priority list? Recommendation:
  responsive web from Phase 3, native apps deferred indefinitely.
- **Q6 — Existing operator workflow during the transition.** Until
  Phase 2 lands, the current `runway-hackathon` app keeps running
  for the operator's daily use. Do we freeze feature work on it,
  or keep iterating? Recommendation: freeze new features, only
  bug-fix, focus all energy on the shell + migration.
- **Q7 — Marketing site stack.** Same Next.js as the SPA, or a
  separate static stack (Astro / Vercel-Next-static / framer)?
  Decide before Phase 3.

---

## 9. Success metrics

What "Phase 3 shipped successfully" looks like, measured at 30 days
post-launch:

- **Activation:** ≥50% of signups complete their first video.
- **Time to first video:** median ≤4 minutes from signup.
- **D1 retention:** ≥30% of signups return the next day.
- **Free → paid conversion:** ≥3% of free-trial users convert.
- **Tier mix:** Starter 60% / Pro 35% / Agency 5% (rough guess for
  baseline — refine after data).
- **NPS:** ≥30 from in-app prompt after the 3rd video.

These are aspirational starting numbers; the *actual* targets get
set after a week of real data. The point of writing them now is to
make sure the analytics scaffolding gets built in Phase 1, not
bolted on later.

---

## 10. What this doc does NOT cover

Out of scope intentionally — to be addressed in their own docs once
this one is locked:

- **Wireframes.** Next artifact — `docs/design/UI_REDESIGN_V2_WIREFRAMES.md`
  or Figma link.
- **Brand identity / visual design system.** Colors, typography,
  component library, illustration style. Separate doc.
- **Marketing copy.** Headline polish, tier descriptions, FAQ text.
  Separate doc.
- **Legal.** Terms, privacy, AUP, content moderation policy.
  Separate doc, blocking before payments turn on.
- **Content moderation / abuse prevention.** Avatar deepfake risks,
  scam-ad detection. Material risk; separate doc.
- **Internationalization.** English-only at launch; i18n deferred.

---

## 11. Sign-off log

| Date | Decision | Sign-off |
|---|---|---|
| 2026-05-13 | Audience: solo creators + non-marketer SMB owners. | chris@donkeybetz.com |
| 2026-05-13 | Activation: avatar-narrated explainer series. | chris@donkeybetz.com |
| 2026-05-13 | Monetization: tiered subscription, no credit math. | chris@donkeybetz.com |
| 2026-05-13 | Headline (v1): speed positioning. | chris@donkeybetz.com |
| 2026-05-13 | Kill the campaign container; video is the unit. | chris@donkeybetz.com |
| 2026-05-13 | Workspace as real entity from day one. | chris@donkeybetz.com |
| 2026-05-13 | Google OAuth primary, email/password backup. | chris@donkeybetz.com |
| 2026-05-13 | Topic tags in data model, hidden in v1 UI. | chris@donkeybetz.com |
| 2026-05-13 | Django DRF shell + FastAPI media engine split. | chris@donkeybetz.com |
| 2026-05-13 | New `character-os` repo, monorepo, FastAPI imported via subtree, u-d-b selective port only. | chris@donkeybetz.com |
