---
title: "Session 209 — Strategic pivot + clean-slate keeper + Tier 1/2 knowledge + V3 brand arc"
date: 2026-05-20
status: complete
session: 209
previous_handoff: ./SESSION_208_BC_ARC_LANDS.md
---

# Session 209 — Strategic pivot + V3 brand arc shipped

## TL;DR

**The most consequential session since Phase 4.** Started as
BC5 dogfood; pivoted mid-session to a clean-slate rebuild
around a parent-company spokesperson, then shipped the
entire BRAND_IDENTITY_V3 arc (10 slices) in the same push.

**15 commits, ~$2.50 real-mode spend, 6 real-mode renders, 1
sub-arc subagent-delivered.** V2 superseded; V3 active. The
SPA now visually feels like the same studio as the parent
marketing site at `/Users/donkeyking/development/24-7-ai-global/`.

Numbered roughly by the time spent:

| # | Workstream | Status | Commit |
|---|---|---|---|
| 1 | Scripts list Zod contract drift fix | landed | `86f002f` |
| 2 | Nav rail expansion (5→11) + Videos library | landed | `bab6b93` |
| 3 | Runtime cleanup (~700 rows / 328 MiB) | landed | data-only |
| 4 | 24/7 Global AI keeper spokesperson (real Runway) | landed | data-only |
| 5 | Tier 1 knowledge corpus (7 KDs from products.ts) | landed | data-only |
| 6 | Tier 1 validation (RAG probes + render dogfood) | landed | calibration |
| 7 | Tier 2 ingest — 4 sibling projects, 884 chunks | landed | data-only |
| 8 | 5 Character OS pitch video variants (dogfood) | landed | data-only |
| 9 | **BRAND_IDENTITY_V3 scope lock** | landed | `f2b32be` |
| 10 | **V3.1 token swap + fonts** | landed | `801add2` |
| 11 | **V3.2 editorial primitives + preview** | landed | `ff2e9ad` |
| 12 | **V3.3 chrome (header / footer / nav)** | landed | `d3e5775` |
| 13 | **V3.4 dashboard masthead** | landed | `89c402d` |
| 14 | **V3.5 workspace routes** (18 files, subagent) | landed | `ffc40a1` |
| 15 | **V3.6 spokesperson detail + orbital portrait** | landed | `3692850` |
| 16 | **V3.7 public surfaces** (sign-in / sign-up / about) | landed | `da93d23` |
| 17 | **V3.8 voice copy pass** | landed | `087fa4b` |
| 18 | **V3.9 dogfood + close** | landed | (this commit) |

Plus 4 TRUST_CALIBRATION entries appended, 2 new design lock
docs (`SESSION_209_PLANNING.md` working scratch +
`BRAND_IDENTITY_V3.md` arc lock). BC arc partially shipped
SESSION 208 — **BC5 dogfood CANCELLED** as part of the
pivot (the Marcus + Five Good Emperors target evaporated
when the cast was wiped).

## The pivot — context

Session opened intending to close out the B-2 ↔ B-3
composition arc (BC5: real-mode dogfood of the BC1-BC4
backend + SPA work shipped SESSION 208). Stack came up
clean, post-fire cleanup audit found the SPA was missing
navigation links to several already-shipped surfaces (the
F-arc nav rail had ossified at 5 entries even though
Assets / Transcripts / Scripts / Campaigns / Bundles
shipped after that). UI cleanup pivot landed `86f002f`
and `bab6b93` (nav rail 5 → 11, Videos library, paginated
compositions endpoint, scripts list Zod contract drift fix).

Then the operator made a strategic call: **wipe the
workspace clean and rebuild around the parent-company
spokesperson.** Rationale:

1. The cast (Riggs / Sasha / Donny / Marcus) was example
   data, not product shape. Their lore was thinning;
   knowledge corpus was minimal and Marcus-specific.
2. The actual product is **Character OS as the
   spokesperson-video platform that 24/7 Global AI owns.**
   The parent-company spokesperson should be the keeper —
   one editorial identity that represents the studio
   across every render, voice, and conversation.
3. The cleanup found 19 `expiring_soon` Runway URLs and a
   broader hygiene gap that justified the wipe regardless.

Wipe scope: 13 failed/partial/draft compositions + 45
steps + 56 expired Assets + 20 orphan Assets (paired with
disk file purge — 14 MiB) + the FULL cast wipe (64
compositions + 155 steps + 13 RealtimeSessions + 324
spokespeople + 119 Assets + 74 downstream rows — ~700
rows / 328 MiB total). Per the audit-preserving V1
design, this was the largest-ever destructive operation
on the workspace.

## The keeper

Created the **24/7 Global AI** spokesperson against
`/Users/donkeyking/Desktop/24:7-Global-AI.png` (1254×1254
logo). Real-mode Runway avatar bake (`f1e5cec2-...`),
Marcus's `david` voice preset, portrait persisted locally
to `_internal/avatar_portraits/`. UI cap bypassed via
shell (operator was at the SPA tier limit; programmatic
call worked cleanly).

First test render against the new keeper completed in 34s
at $0.25; second knowledge-grounded render in 75s at $0.25.
Logo-as-portrait works — Runway's avatar engine produces
an unusual-but-on-brand animation. Operator approved.

## Knowledge corpus

**Tier 1** (7 KDs, 13 chunks, ~$0.00005) — distilled
editorial summaries from
`/Users/donkeyking/development/24-7-ai-global/src/lib/products.ts`:
24/7 Global AI charter + 6 catalogued products
(PitchDeckForge, DealFlowTracker, Contract Concierge,
MentorForge, context-kit, Character OS).

**Tier 2** (29 KDs, 871 chunks, ~$0.003) — deep per-
project corpus walks for 4 of the 6 catalogued projects
(character-os, context-kit, mentorforge, contract-
concierge). PD + DF skipped — both repos contained only
Vite boilerplate READMEs at this point. Editorial summary
remains sole keeper knowledge for those two until source
docs land.

**Cross-project linkage probe** returned 0.29 distance —
better than any single-project probe — because the
MentorForge product summary explicitly references the
suite ("Exports to PitchDeck · DealFlow · Contract
Concierge"). **Implication for future Tier 1 work: keep
cross-references explicit in elevator-pitch copy.**

Final lifetime corpus state at SESSION 209 close: **37
KDs, 884 chunks, ~$0.0037 embedding spend.**

## The V3 brand arc

The discovery moment: when the operator pointed at the
parent marketing site, the AI found
`/Users/donkeyking/development/24-7-ai-global/` —
**not** a doc consolidator (as initially assumed) but the
actual marketing website (Next.js 16 + React 19 +
Tailwind 4 + Vercel). Six products catalogued. Distinctive
editorial dark-luxe brand language: ink + gold palette,
Bodoni Moda display serif, "§ NN — Section Name" section
dossier numbering, "Plate NN" caption pattern, "Reply by
morning" engagement voice, orbital ring animations.

V2 ("premium enterprise dark + gold") had to flex.

V3 scope-locked as the 9-implementation-slice arc V3.0 —
V3.9. Estimated 4-5 sessions. **Shipped in one extended
session** thanks to:

- Tight scope-lock doc with 10 load-bearing contract
  rules upfront.
- Canonical source ported verbatim (the parent site IS
  V3's source of truth — no invention).
- V3.5 subagent delivery (18 routes in one prompt).
- The CSS-var indirection pattern that lets `data-brand`
  swap palette + fonts atomically.

**Total V3 commits: 10. Total V3 LOC: ~2,500 added /
~700 removed. CSS bundle: 36 KB → 40.6 KB.**

### V3 slice ledger

Detail in `docs/design/BRAND_IDENTITY_V3.md` change log.

- **V3.0** scope lock (`f2b32be`)
- **V3.1** tokens.css `[data-brand="v3"]` block,
  globals.css keyframes + utility classes (gold-text,
  gold-stroke, luxe-shadow, hairline-gold, grid-globe,
  radial-spot, noise), tailwind.config raw colors +
  animations, index.html font links (`801add2`)
- **V3.2** five editorial primitives (`SectionHeader`,
  `HairlineDivider`, `EditorialCaption`, `DoctrineQuote`,
  `EngagementBrief`) + `/dev/brand-v3` preview + 21 tests
  (`ff2e9ad`)
- **V3.3** Site chrome — SiteHeader brand-mark split,
  ParentBrandChip italic-gold, SiteFooter, NavRail
  gold-active / fog-inactive (`d3e5775`)
- **V3.4** Dashboard masthead — `§ 01 — Workspace`,
  hairline-gold, PrimaryAction luxe-shadow + italic-gold
  "Ship." (`89c402d`)
- **V3.5** 18 workspace routes + 3 test fixtures
  (subagent-delivered, react-web-delivery) — Recipes,
  Knowledge, Videos, Assets, Transcripts, Scripts,
  Campaigns, Bundles (`ffc40a1`)
- **V3.6** Spokesperson detail (orbital portrait
  treatment ported from parent hero), new, talk, recipe
  form internal card (`3692850`)
- **V3.7** Public surfaces — sign-in italic-gold "in.",
  sign-up "Commission your **operating partner.**" with
  first EngagementBrief outside preview, about.tsx full
  restructure with first DoctrineQuote outside preview
  (`da93d23`)
- **V3.8** Voice copy pass — dashboard / videos empty
  states gain italic-display register; "Commission a
  spokesperson →" replaces "Provision spokesperson"
  (parent-site verb match); editorial " →" CTAs
  (`087fa4b`)
- **V3.9** Real-mode dogfood + this handoff (current
  commit)

## TRUST_CALIBRATION findings (4 appended this session)

1. **Expired-asset accumulation has no purge mechanism.**
   56 expired Runway URLs accumulated unnoticed. V1's
   audit-preserving design implicitly assumed manual
   hygiene; SPA doesn't surface the rot. Follow-ups
   queued: Celery Beat sweep, storage-health filter on
   Videos library, "Bake to local" preserve-before-
   expire action.

2. **`use_knowledge=True` doesn't propagate
   knowledge_chunk_ids to the Composition row (any
   recipe).** Bug surfaced first via `talking_head`
   then widened to all knowledge-grounded recipes
   when fired without a Script-row lineage source.
   Chunks land on the final Asset's
   `source_spec.knowledge_chunk_ids` but never
   aggregate to `Composition.knowledge_chunk_ids`.
   SPA citation surfaces (F-arc brief-mode panel,
   BC4 lineage, verifier panel) fail for single-step
   renders. Fix queued for SESSION 210 (~20-30 LOC,
   generic post-completion aggregator).

3. **K6 brief expansion replaces the operator script.**
   When `use_knowledge=True`, K6's `build_render_brief`
   treats the script as a TOPIC and produces a
   brand-voiced expansion (120-char input became
   557-char rendered output in the first dogfood).
   Operationally surprising — operators write a tight
   one-liner expecting it to be the spoken text.
   Fix queued: recipe form copy pass to label as
   "Topic" on grounded variants + surface estimated
   duration after synthesis.

4. **Outro/intro card text has no auto-wrap.** 94-char
   CTA outro clipped on both sides ("mail jessica" /
   "cam"). `_build_card_filter` centers text without
   wrapping. Workaround: pre-wrap with `\n` line breaks.
   Fix queued: add `textwrap.wrap` in
   `media-engine/app/routers/internal.py:_build_card_filter`,
   ~10 LOC.

**"Real-mode finds bugs in every arc" streak: 9-for-9
going into V3.9.** The V3 dogfood validated the styling
doesn't regress the composition pipeline — the editorial
register is purely visual, the backend was untouched.

## Real-mode spend

| Workstream | Cost |
|---|---|
| Avatar creation (Runway monthly cap, no charge) | $0 |
| Tier 1 embedding (text-embedding-3-small) | ~$0.00005 |
| Tier 1 validation render (`talking_head` + knowledge) | $0.25 |
| Tier 2 embedding (29 KDs, 871 chunks) | ~$0.003 |
| First test render (`talking_head`, deleted in wipe) | $0.25 |
| 5 Character OS pitch video variants ($0.25 each) | $1.25 |
| V3.9 dogfood render | $0.25 |
| **Total** | **~$2.00** |

## Doc state at SESSION 209 close

- `docs/design/BRAND_IDENTITY_V3.md` — V3 arc lock with
  full change log (10 slice entries).
- `docs/design/BRAND_IDENTITY_V2.md` — superseded;
  preserved with deprecation banner.
- `docs/SESSION_209_PLANNING.md` — working scratch.
  Retire after distillation into this handoff. Contains
  detail not preserved here (per-slice copy decisions,
  scope creep avoidance notes, etc).
- `docs/TRUST_CALIBRATION.md` — 4 new entries (44 total).
- `00-START-NEXT-SESSION.md` — to be rewritten in the
  next handoff commit.

## Workspace state at SESSION 209 close

- **1 spokesperson:** 24/7 Global AI (`d3d0fb14-...`).
- **37 KnowledgeDocuments** (7 Tier 1 + 29 Tier 2 + 1
  trafilatura research carryover).
- **884 embedded knowledge chunks.**
- **6 compositions** (the 5 brand-on Character OS pitch
  variants + 1 V3.9 dogfood — total spend $1.50 visible
  in Videos library after the V3.9 render completes).
- **0 RealtimeSessions / 0 raw_uploads / 0 transcripts /
  0 campaigns / 0 bundles / 0 scripts.**

## Test counts

| Suite | Pre-session | Post-session |
|---|---|---|
| Django (backend) | 1343 | 1343 (no backend changes) |
| Media-engine | 214 | 214 |
| SPA vitest | 426 | 455 (+29: V3.2 primitives + V3.4-V3.8 fixture adjustments) |

## SESSION 210 priorities

Pending Tier-2 doc updates (write next commit):

1. **`talking_head` chunk_ids propagation patch** (½
   slice, ~20-30 LOC) — generic post-completion
   aggregator that walks produced assets'
   `source_spec.knowledge_chunk_ids` and writes to
   `Composition.knowledge_chunk_ids`. Mirrors
   `talking_head_polished`'s BC2 carry-up. Affects
   all knowledge-grounded recipes, not just
   `talking_head`. Tests for both starters.

2. **Brief-replaces-script SPA copy pass** (½ slice) —
   recipe form labels: "Script" → "Topic" on grounded
   variants. Surface estimated duration after synthesis
   (pre-render, not from script length).

3. **Outro/intro card auto-wrap** (½ slice) —
   media-engine `_build_card_filter` gains
   `textwrap.wrap` with max_chars tuned to canvas
   width + font size.

4. **Storage-health filter on Videos library** (½ slice).

5. **Expired-asset Celery Beat sweep** (½ slice).

6. **VO-arc scope lock** (½ session) — post-hoc
   voiceover insertion at specific time offsets.

After those polish slices, the next big arcs:

- **Asset upload UI** (1-2 sessions) — unblocks several
  v2 slices.
- **Composition arc candidates** (B-2 ↔ B-14, B-1 ↔ B-3,
  B-3 ↔ B-14) — each ~½ regular arc.

## Calibration moments worth carrying

- **Subagent delivery on tight contract briefs is now
  3-for-3** (B2.5 + BC4 + V3.5). Pattern that works:
  exhaustive contract upfront (file list, per-file
  checklist, class-swap dictionary, hard constraints,
  verification steps). The V3.5 brief was the largest
  yet (18 files) and shipped clean.

- **A canonical external source dramatically compresses
  arc cycle time.** V3 was estimated 4-5 sessions;
  shipped in 1. The parent marketing site at
  `/24-7-ai-global/` was V3's source-of-truth and V3
  ported verbatim rather than designing from scratch.
  Generalizes: when an arc has a canonical reference
  implementation, the scope-lock should explicitly
  name it and the contract should be "match the
  reference," not "design something new."

- **The CSS-var indirection for fonts + colors lets
  `data-brand` swap brand identities atomically.** V1
  is preserved under `[data-brand="v1"]`, V2 under
  `[data-brand="v2"]`, V3 under `[data-brand="v3"]`.
  Flipping the html attribute swaps the entire visual
  identity with no redeploy. Worth carrying forward —
  multi-tenant per-workspace branding becomes a
  data-brand swap, not an architectural change.

- **Cross-product references in editorial-summary copy
  retrieve better than deep design docs.** Tier 2's
  cross-product probe (0.29) beat every single-project
  probe. Implication for future Tier 1 seed copy: keep
  product summaries explicitly cross-referenced ("MF
  exports to PD · DF · CC").

- **Real-mode finds bugs in every arc — streak now
  9-for-9.** V3 dogfood validated the styling didn't
  regress the pipeline; no new V3-arc-specific bug
  emerged because V3 was purely visual. The streak
  continues across composition / knowledge / realtime
  arcs.

- **Operator-driven UI dogfood + AI-driven log tailing
  remains the right division** per existing memory.
  This session ran ~3 hours of editorial-register work
  with the operator clicking through SPA changes in
  real-time while the AI handled commits and chrome.

- **"Editorial dark-luxe" as a register choice
  consistently exceeded expectations.** Multiple
  operator confirmations during the slice run ("it
  looks amazing"). Validates the V3 pivot decision.
  Going forward, brand decisions should lean editorial
  not generic-SaaS where the parent narrative supports
  it.
