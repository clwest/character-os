# AI-Assisted Development Disclosure

Character OS is a solo-authored, AI-assisted project. This
document exists so a reader can decide what the repo does and
does not evidence about the engineer's ownership.

## The honest version

Chris West:

- Defined the product philosophy — the ratified Operator
  Decisions in `docs/design/operator-decisions/` (Presence
  Authoring; Creator Fidelity; Artifact History; Name Primacy).
- Wrote the scope-lock design docs for every major arc
  (Knowledge `K1-K10`, Video Composition `V0-V15`, Realtime
  Avatar `R0-R10`, Workspace Fabric `F0-F10`) before any
  implementation began. Each lock names its contract rules
  (typically 7-10 per arc) and is referenced in code.
- Chose the domain shape — `Workspace → Teammate → {Composition,
  RealtimeSession, ConversationThread, Script,
  PersonalizedCampaign}` + canonical `Asset` and
  `KnowledgeDocument`/`Chunk` — and imposed the tenancy contract
  that runs through every model.
- Directed provider selection (Runway as primary video/realtime;
  OpenAI as primary LLM; Stability reframed for scenes/b-roll
  only after the SESSION 171 lip-sync incident; ElevenLabs as
  voice fallback).
- Ran the dogfood cycles that produced every correction listed
  in the case studies (`docs/case-studies/`). Every one is real
  operator experience against real providers, not synthetic
  testing.
- Enforced discipline around isolation, cost governance,
  provider drift verification, and grounding of LLM output.

Claude Code (Sonnet 4.5, 4.6, and Opus 4.7 across the project's
lifetime):

- Wrote most of the implementation code under the scope-lock
  contracts.
- Produced the initial drafts of tests, migrations, and
  API/serializer boilerplate.
- Assisted with authoring documentation.

The commit-authored proportion of hand-written vs AI-generated
code cannot be recovered from git — every commit is under Chris's
name. What can be recovered is the pattern: scope-lock docs
predate implementation, TRUST_CALIBRATION.md logs the AI's
miscalibrations, and dogfood-driven corrections appear in the
handoff history.

## Concrete examples where AI direction mattered

These are all real events, drawn from the internal handoff
history. Fuller writeups live in
[`docs/case-studies/`](docs/case-studies/).

### 1. Stability portrait mis-lip-sync (SESSION 171)

Ported the Stability image provider. Chris ran a dogfood cycle
with a real spokesperson (Marcus, mascot template) and noticed
that Runway avatars baked from Stability portraits mis-lip-synced.
The AI proposal was to keep Stability as a portrait provider
alongside Runway. Chris rejected that and imposed a guardrail:
Stability is reframed for scenes and b-roll only; Runway
`gen4_image` is the sole avatar portrait source.
See [`docs/case-studies/01-stability-portrait-lipsync.md`](docs/case-studies/01-stability-portrait-lipsync.md).

### 2. Personality ÷ business_brief split (SESSION 175)

Operator insight during dogfood: HOW-it-speaks and WHAT-the-
business-does are conceptually different. AI had produced a
single `personality` field. Chris directed a split, an in-place
migration, and downstream re-threading through the K6 script
synthesis prompt so business_brief could vary without re-baking
voice. Not a refactor for aesthetics — a semantic separation
driven by dogfood behavior.

### 3. YouTube ingest silent-failure (SESSION 175)

The knowledge ingest pipeline was accepting YouTube URLs and
returning "processed" without capturing anything. AI had built
the ingest around `trafilatura`, which returns empty for video
pages. Chris caught it, added a detect-reject at the per-host
extractor layer, then added a proper `youtube-transcript-api`
path. Now a first-class knowledge source.

### 4. K6.4 claim-verifier false-positive stoplist (SESSION 173,
   175)

The claim verifier flagged `"Think Antoninus"` and
`"Respect HTML"` as ungrounded claims when they were CTA verbs +
common action objects. Chris's directive: don't lower the
verifier's precision; expand the sentence-opener stoplist. The
stoplist became append-only calibration state that new patterns
feed into without re-deploy.

### 5. Runtime-truth doctor (SESSION 159, 222)

Four anchor docs had silently aged across 50+ sessions because
only one had per-session restamp. Chris imposed a discipline:
docs carrying `status: regenerated` frontmatter get scanned by a
`manage.py doctor` command that fails CI-style if the doc's SHA
drifts from the code it describes. AI had proposed manual
review; Chris directed the SHA-stamped programmatic check.

### 6. Allauth `RATE_LIMITS = False` (SESSION 131)

Playwright tests hit allauth's signup rate limit. AI proposed
`ACCOUNT_RATE_LIMITS = {}` with high confidence. The library's
actual behavior is that `{}` falls through to defaults; the
correct disable is `False`. Chris tested in a REPL, caught the
miscalibration, and logged it in `TRUST_CALIBRATION.md` as an
"AI-assumed shape ≠ library-actual shape" pattern to watch for.

### 7. R7 sub-slicing (SESSION 149)

R7 (realtime tool dispatch) was originally scope-locked as a
single slice. AI planning proposed shipping the whole thing.
After SESSION 148 the operator had calibrated on "one slice per
session"; R7 was too large. Chris directed a sub-slice into
R7.0 (foundation), R7.1 (sync tools), R7.2 (async tools), R7.3
(memory attach). Each sub-slice shipped in its own session with
its own tests. Foundation-first discipline was preserved.

## What the repository does and does not evidence

Evidences:

- Ability to define product philosophy and impose it on
  implementation.
- Ability to identify AI miscalibrations and correct them
  before they become durable.
- Willingness to reject AI-proposed solutions when dogfood
  contradicts them.
- Discipline around scope-locking, contract rules, and
  runtime-truth doctors.
- Full-system architecture across three services, one database,
  four AI providers, and a WebRTC frontend.

Does not evidence:

- Hand-authorship of most implementation code.
- Team collaboration on a shared codebase.
- Code review by peers.
- Production operations at scale.

## Why this matters

The strongest hiring signal in an AI-assisted project is not
volume of code — it is the pattern of correction, calibration,
and taste. The scope-lock docs predating implementation, the
TRUST_CALIBRATION ledger, and the case-study evidence are the
places to look for that signal.

The weaker signal — and the reason this disclosure exists — is
raw LOC. A skeptical reader who assumes AI-assisted work is
"cheating" will discount most of the ~187k production LOC. The
honest response is: yes, a lot of that is Claude's tokens. The
engineering is in what Claude was told to do and what got
rejected before it stayed.
