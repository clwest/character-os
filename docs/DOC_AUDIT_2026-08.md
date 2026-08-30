---
title: "Doc Audit — character-os, 2026-08"
date: 2026-08-27
status: complete
head: 1faa7c3
auditor: Claude Code
protocol: ~/Donkey_Betz/DOC_AUDIT_PROTOCOL.md
program: ~/Donkey_Betz/PROGRAM_WHAT_WE_LEARNED.md
brief: ~/Donkey_Betz/TASK_doc-audit-03-character-os.md
phase_two_output:
  - ~/Donkey_Betz/LESSONS.md (appended L-015 through L-020)
  - ~/Donkey_Betz/HOW_CHRIS_WORKS.md (appended 2026-08-27 from character-os)
---

# Doc Audit — character-os, 2026-08

## Verdict

The repo's own runtime-truth doctor reports one BLOCKING drift
(`docs/CHARACTER_OS_INVENTORY.md` was 8.8 days stale; SHA
`b7f9bab` vs HEAD `1faa7c3`). The documented fix is
`python manage.py inventory` from `shell/`; the auditor ran it,
but the sandbox environment produced a misleading
migration count (0/116 vs a prior 108/108). The regen was
reverted — a doc fix that requires being in Chris's environment
is a finding for Chris, not a fix for the auditor. Everything
else in scope matches runtime, or is honestly labeled as
`status: stub` where it isn't complete. Docs describing what's
public vs private are consistent with the working tree.

## Environment

```
cd ~/Donkey_Betz/character-os
source .venv/bin/activate
cd shell    # manage.py lives here
```

This repo's `.venv` was not the scout httpx trap; the venv
exists and the CLI runs cleanly under it. The repo ships **two**
verifiers: `python manage.py doctor` (in `shell/`) and
`python manage.py inventory` (also in `shell/`, the doc-
regenerator the doctor points at). Per the session-2 protocol
update, both were run before any doc was opened.

## Claims checked

Category-based scope per the session-3 brief. Sampled canonical
claims per category rather than enumerating every file.

### Anchor pair — `docs/CHARACTER_OS_WHAT_IT_IS.md` + `docs/CHARACTER_OS_INVENTORY.md`

```
CLAIM:   "INVENTORY is regenerated; check freshness against HEAD"
COMMAND: python manage.py doctor
ACTUAL:  ✗ docs/CHARACTER_OS_INVENTORY.md
            BLOCK: git_sha='b7f9bab' != HEAD='1faa7c3' AND
            generated_at is 8.8d old (block threshold 7d)
VERDICT: DRIFT — see Not fixed, and why.
```

```
CLAIM:   "Narrative anchor last_revised 2026-07-21 SESSION 218; covers_sessions '106-218'"  (frontmatter)
COMMAND: ls docs/handoffs/ | sort | tail -1
ACTUAL:  SESSION_265_CLOSEOUT.md is the latest visible handoff.
         Commit message on HEAD references SESSION 282.
VERDICT: HISTORICAL — anchor's `last_revised` and `covers_sessions`
         are dated evidence of when the narrative was last
         hand-updated. The doc itself acknowledges the pattern:
         "Numbers move per slice — always trust INVENTORY over any
         quote here." Not drift — the doc's frontmatter dates its
         own state honestly. Bumping SESSION 218 to a higher number
         requires Chris's judgment on what narrative content also
         needs updating.
```

```
CLAIM:   Narrative uses ~ prefixes on quantitative claims (two-doc-anchor discipline)
COMMAND: grep -c "\*\*[0-9]" docs/CHARACTER_OS_WHAT_IT_IS.md
ACTUAL:  ~30 numeric assertions. Sampling: "14 Django apps + 23
         models", "173 /api/* routes", "70 migrations". None have
         ~ prefixes. But the doc immediately follows with "Numbers
         move per slice — always trust INVENTORY over any quote here"
         (WHAT_IT_IS.md line 62). The pattern is the same, executed
         differently: instead of `~` scope-markers on each number,
         one blanket "trust INVENTORY" disclaimer at the section head.
VERDICT: OK — different mechanism, same discipline. Both fair.
```

### Behaviour / pipeline / translation layer

```
CLAIM:   PIPELINE.md / BEHAVIOR_LAYER.md / TRANSLATION_LAYER.md are
         current-state runtime documents
COMMAND: grep "^status:" docs/CHARACTER_OS_PIPELINE.md \
                        docs/CHARACTER_OS_BEHAVIOR_LAYER.md \
                        docs/CHARACTER_OS_TRANSLATION_LAYER.md
ACTUAL:  PIPELINE     status: stub
         BEHAVIOR     status: stub
         TRANSLATION  status: project-owned
VERDICT: OK — two are honestly labeled as stubs
         (`status: stub` in frontmatter). A stub is not drift; it
         is the doc's own claim about its completeness. TRANSLATION
         is populated.
```

```
CLAIM:   BEHAVIOR_LAYER contains structural rules that can be tested
         (equivalent of scout §5/§10)
COMMAND: grep -c "\.py:" docs/CHARACTER_OS_BEHAVIOR_LAYER.md
ACTUAL:  0 code-path references. This is the load-bearing gap
         session-3 brief called out — Character OS is a
         chat-and-voice product, and its behavior layer is a
         template with no rules yet.
VERDICT: UNVERIFIABLE (structural gap) — the doc exists, but until
         it holds testable rules there is nothing for the audit to
         verify. Recorded here so the gap is visible to the next
         session; not fixed because filling a stub with content is
         out of scope for this session.
```

```
CLAIM:   PIPELINE.md names entry points, guards, retrieval paths
COMMAND: grep -c "\.py:" docs/CHARACTER_OS_PIPELINE.md
ACTUAL:  2 code references. Structurally the same shape as
         BEHAVIOR_LAYER — the template outline is present, the
         specific paths are not filled in. Also `status: stub`.
VERDICT: UNVERIFIABLE (structural gap) — same disposition as
         BEHAVIOR_LAYER.
```

### README + AI_ASSISTED_DEVELOPMENT + ARCHITECTURE

```
CLAIM:   README's three-canonical-flows entry-point paths all exist
COMMAND: for f in shell/apps/embeddings shell/character_os/script_synthesis.py \
              shell/character_os/claim_verifier.py \
              shell/apps/compositions/models.py shell/apps/spokespeople \
              media-engine/app/services shell/apps/compositions/recipes.py \
              shell/apps/compositions/primitives \
              web/src/routes/spokespeople/talk.tsx; do
              [ -e "$f" ] && echo "✓ $f" || echo "✗ $f"
         done
ACTUAL:  9 of 9 paths exist.
VERDICT: OK
```

```
CLAIM:   README's "20 registered recipes" + "23 registered step primitives"
COMMAND: (deferred to INVENTORY once Chris regenerates it — recipe
         count is exactly the kind of thing that moves per slice)
ACTUAL:  Not verified in this session.
VERDICT: UNVERIFIABLE from audit alone — would require reading
         `recipes.py` and `primitives/` directly. Not the
         audit's job when INVENTORY exists to hold it.
```

### PUBLIC_DOCS_MANIFEST.md

```
CLAIM:   Every listed public-tree doc exists
COMMAND: for f in <15 paths listed in manifest>; do
              [ -e "$f" ] && echo "✓ $f" || echo "✗ $f"
         done
ACTUAL:  All 15 present (case-studies 01–07, architecture GOD_FILES
         + PROVIDER_MAP, design KNOWLEDGE_LAYER + VIDEO_COMPOSITION
         + REALTIME_AVATAR + WORKSPACE_FABRIC + IDENTITY_MODEL,
         operator-decisions directory, all five CHARACTER_OS_*.md
         anchor/companion docs, README/ARCHITECTURE/AI_ASSISTED).
VERDICT: OK
```

```
CLAIM:   "handoffs — 253 session handoff files"                      (line 64)
COMMAND: ls docs/handoffs/ | wc -l
ACTUAL:  18 files in this working tree.
VERDICT: HISTORICAL — the manifest describes the PRIVATE tree
         (handoffs are gitignored, per SESSION_265_CLOSEOUT.md
         line 35: "Per repository convention, docs/handoffs/ is
         gitignored (.gitignore:86)"). The 253 count is Chris's
         canonical private-clone count; this working tree
         intentionally holds fewer. Not drift — the doc says
         "in the public tree" versus "preserved privately" and
         253 falls under the second.
```

```
CLAIM:   `00-START-NEXT-SESSION.md` and `CLAUDE.md` are private,
         not in the public tree
COMMAND: ls 00-START-NEXT-SESSION.md CLAUDE.md
ACTUAL:  Neither exists in this working tree.
VERDICT: OK — this working tree matches the manifest's public-tree
         description on that point. (Session-3 brief anticipated
         these being present; they are not, and the manifest
         explains why.)
```

### Latest session handoff — `docs/handoffs/SESSION_265_CLOSEOUT.md`

```
CLAIM:   "Everything committed to main and pushed to origin.
         Working tree clean at the last recorded parity check."   (line 30)
COMMAND: git status --porcelain
ACTUAL:  clean (before this audit's transient inventory regen,
         which was reverted)
VERDICT: OK
```

```
CLAIM:   "Per repository convention, docs/handoffs/ is gitignored
         (.gitignore:86)"                                          (line 35)
COMMAND: grep -n "handoffs" .gitignore
ACTUAL:  docs/handoffs/ is listed on .gitignore line 86.
VERDICT: OK
```

### Root pyproject.toml testpaths — a small drift

```
CLAIM:   testpaths = ["shell/tests", "media-engine/tests"]        (pyproject.toml)
COMMAND: ls shell/tests media-engine/tests
ACTUAL:  shell/tests does NOT exist. Tests live at
         shell/apps/*/tests/ and shell/character_os/*/tests/.
         media-engine/tests DOES exist.
VERDICT: DRIFT — but in a config file, not a doc. Per protocol,
         "may not: configuration". Flag only.
```

### Provider layer preflights — session-1 pattern check

```
CLAIM:   (session-3 brief) "check whether the provider layer has
         preflight construction checks (like scout's
         _check_openai_sdk_capable) or whether it relies on stubs
         alone"
COMMAND: grep -rn "check_.*_capable\|SDKTooOld\|preflight" media-engine/app/services/ shell/character_os/ 2>&1 | head
ACTUAL:  No results for the exact scout-shape preflight pattern.
         `docs/architecture/PROVIDER_MAP.md` (per manifest) is
         where mock gates are documented; not audited here.
VERDICT: UNVERIFIABLE from this session's scope. Flagging as a
         watch item for the character-os team, not a fix. The
         "stub-cannot-verify-boundary" lesson (LESSONS L-002)
         applies — worth pattern-checking in a slice.
```

## Drift found

1. **Inventory 8.8 days stale.** Doctor calls it BLOCKING. Doc says
   `git_sha: b7f9bab`, HEAD is `1faa7c3`, `generated_at:
   2026-08-19T04:44:16Z`. Documented fix is `python manage.py
   inventory` from `shell/`. Attempted and reverted — see below.
2. **pyproject.toml `testpaths = ["shell/tests", ...]`** —
   `shell/tests` does not exist. Config-side, out of scope for
   doc fixes; flagged.

## Fixed in this pass

Nothing. Attempted `python manage.py inventory` regeneration
in `shell/`; the sandbox environment produced a `Migrations
(applied / total) | 0 / 116` line where Chris's environment
likely reports `108+/116`. The regen would have replaced one
stale doc with a differently-inaccurate doc, so it was
reverted. Working tree is clean at audit end.

The revert is a deliberate application of scout's lesson: "a
doc fix that requires being in the operator's environment is a
finding for the operator, not a fix for the auditor." The
audit protocol's "may fix a current-state number that runtime
contradicts" applies only when the auditor's runtime IS the
authoritative runtime — which for a Postgres-app-in-a-monorepo
audit is not the case.

## Not fixed, and why

- **`docs/CHARACTER_OS_INVENTORY.md` — 8.8 days stale.** Regen
  requires Chris's dev DB to produce accurate migration and
  route counts. Recommend: Chris runs
  `cd shell && source ../.venv/bin/activate && python manage.py
  inventory` at his convenience, then `python manage.py doctor`
  to confirm clean. Estimated cost: under a minute.
- **`docs/CHARACTER_OS_WHAT_IT_IS.md`** `last_revised: SESSION
  218` and `covers_sessions: "106-218"` — the anchor is 47
  sessions behind visible handoffs (SESSION 265) and 64 behind
  the commit-message reference (SESSION 282). Bumping the date
  without updating the narrative would misrepresent what has
  been reviewed. Narrative refresh is Chris's judgment. The
  doc's own "trust INVENTORY over any quote here" statement
  covers the numeric drift; the structural claims still hold.
- **`docs/CHARACTER_OS_PIPELINE.md` and BEHAVIOR_LAYER.md
  `status: stub`.** Filling a stub is out of scope. Both are
  labeled honestly. The stubs have been stubs since
  SESSION 175 (2026-05-17), which is 3+ months. Recommend
  Chris either populates or explicitly retitles them as
  "template" if they aren't going to be populated.
- **`pyproject.toml` testpaths mismatch.** Config edit, out of
  scope. Flagged as a finding for a real slice.

## Missing conventions

- **The `role:` frontmatter proposal** (written in session 2 at
  `~/Donkey_Betz/context-kit/docs/proposals/doc-role-frontmatter.md`)
  would have shortened two specific decisions in this audit:
  (a) `CHARACTER_OS_WHAT_IT_IS.md`'s frontmatter `last_revised:
  2026-07-21` and `covers_sessions: "106-218"` — is that
  current-state (should be bumped) or append-only marker (do
  not touch)? (b) `docs/handoffs/SESSION_265_CLOSEOUT.md` — the
  latest handoff acts current-state for continuity but is
  categorically append-only. Both would flip to explicit
  labels with the proposed convention.
- **A `status:` value convention.** This repo uses `status:
  populated`, `status: regenerated`, `status: stub`, `status:
  closed`, `status: project-owned`. All meaningful, none
  centrally documented. Context-kit's doctor could enforce a
  known vocabulary if the two repos agreed on one.

## For the Drive STATUS doc

```
character-os — status 2026-08-27
  HEAD 1faa7c3 (SESSION 282 closeout SHA daf9fa9), main, 384
  commits.
  Runtime-truth doctor (in-repo, python manage.py doctor) reports
  1 BLOCKING drift: docs/CHARACTER_OS_INVENTORY.md is 8.8 days
  stale (git_sha b7f9bab vs HEAD 1faa7c3). Documented fix is
  `python manage.py inventory` from shell/; Chris to run in his
  own env (sandbox's migration count is misleading).
  Narrative anchor CHARACTER_OS_WHAT_IT_IS.md `last_revised:
  SESSION 218` — 47 sessions behind visible handoffs (SESSION
  265) and 64 behind SESSION 282. Anchor self-labels "trust
  INVENTORY over any quote here"; numeric drift covered,
  narrative refresh remains Chris's judgment.
  PIPELINE.md + BEHAVIOR_LAYER.md remain `status: stub` from
  SESSION 175 (2026-05-17) — three-month standing gap.
  BEHAVIOR_LAYER's absence matters more than PIPELINE's: this
  is a chat + voice product with no behavior-layer contract
  yet.
  README's canonical-flow paths (9 checked) all present.
  PUBLIC_DOCS_MANIFEST's 15 public-tree paths (7 case studies,
  2 architecture, 6 design + anchors) all present.
  This working tree is the public/portfolio layout —
  00-START-NEXT-SESSION.md and CLAUDE.md are not here by
  design (gitignored in the public tree; manifest documents
  this).
  Phase two: LESSONS.md extended L-015 → L-020 with entries
  from the case-studies and SESSION 265 dogfood. HOW_CHRIS_
  WORKS.md appended with corroboration of the "runtime beats
  narrative" pattern from an independent third project — v0
  entry promoted.
  Category-based scope worked. Cheaper than file-by-file and
  did not lose safety. Session 4 brief for freedom-ford
  extends it further; UDB brief will assume it.
```

## Category-based scope — honest read

**Cheaper.** The file-by-file enumeration in sessions 1 and 2
was ~35 minutes per repo of "verify this claim in this file";
category-based here was ~25 minutes for a repo with 4× the
docs. The saved time went into reading two case studies deeply
enough to lift them into `LESSONS.md`.

**Not noisier — cleaner.** Every category maps to a specific
kind of failure mode (anchor drift, contract-clause under-
verification, entry-point paths going stale, manifest getting
out of sync with the actual tree). Naming the failure mode
first, then reading the file, produced sharper verdicts.

**One risk.** A file that falls between categories (in this
repo, the design docs — some are current-state contracts,
some are historical case-lock docs) still requires a
per-file judgment call. Session 4 brief for freedom-ford
handles this with a "hybrid" — name the categories, and if
any file's category is genuinely ambiguous, enumerate it
individually.

**Keep the category shape. Add per-repo enumeration only for
ambiguous files.** Report at end of every future session
whether category-based worked.

## Phase two — was it worth the phase-one cost?

Yes, again. Sharper density this time than session 2 because
the case studies are already lesson-shaped (they were written
for external readers) — six new LESSONS entries in ~15
minutes of reading. The single strongest new lesson
(L-016, "silence is a bug") is one that scout's field reviews
approach but never quite state in one line; character-os's
`03-youtube-ingest-silent-fail.md` states it cleanly.

Sessions 1–3 have now produced 20 transferable lessons from
3 repos in ~4 hours of combined audit + mine time. The next
four repos are likely to add fewer (norman-handyman is
smaller; donkey-betz-public is one commit; freedom-ford
has never been audited so it may add a lot; UDB will add
either a lot or almost none depending on how much reads as
"already-known lesson"). The bar for a new entry rises as
LESSONS grows — say so explicitly in the next brief.
