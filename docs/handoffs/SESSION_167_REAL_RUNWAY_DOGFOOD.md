---
title: "Session 167 — real-Runway dogfood + K6.4 v2.1 CTA stoplist"
date: 2026-05-15
status: complete
session: 167
previous_handoff: ./SESSION_166_K6_4_V2_SURGICAL.md
---

# Session 167 — real-Runway dogfood

## TL;DR

First production fire of the K-arc verifier stack against
real Runway under strict mode. Two-attempt dogfood:

* **Attempt 1**: blocked at $0.00. Strict mode rejected on
  `Want` + `Reach` — both **sentence-initial CTA verbs**
  in K6's grounded reply ("Want to see this? Reach out…").
  Pipeline contract worked end-to-end (status=failed,
  cost=0, rejected_synthesis persisted, verification_status
  =rejected). But the rejection was on innocent CTA verbs,
  not real hallucinations.
* **Stoplist fix**: ~40 CTA-verb additions
  (`want, reach, need, learn, watch, click, sign, join,
  follow, subscribe, …`) anchored by a regression test.
* **Attempt 2 (post-fix)**: $0.25 real Runway render
  shipped. `verification_status="verified"`, no warnings.
  K6 under strict pressure produced grounded content about
  embeddings + vector databases + retrieval — anchored in
  the Wikipedia RAG doc chunks.

Tests: Django **713 → 714** (+1 CTA-verb regression).
Total Runway spend: **$0.25** (one verified render).

## The dogfood story

### Setup

Services restarted with K6.4 v2 code + strict mode:
* `K6_CLAIM_VERIFIER_MODE=strict`
* Real `RUNWAY_API_KEY` + `OPENAI_API_KEY`
* Target spokesperson: Donny (with the Wikipedia RAG
  doc attached from SESSION 158)
* Same operator prompt class that originally caused the
  SESSION 158 hallucination

### Attempt 1 — strict blocked, but on the wrong terms

```
PROMPT: Describe how the knowledge layer ingests pages.
Composition: 6caf0100-b63a-487d-826e-f7a1e148f0ad

Status: failed
Cost: $0.00
verification_status: 'rejected'
Error: K6.4 claim verifier rejected the synthesized
       script (2 unsupported claim(s)): 'Want', 'Reach'

verification_warnings:
  - "Want" (proper_noun, position 418)
  - "Reach" (proper_noun, position 462)

rejected_synthesis:
  "I sit with customers and watch the knowledge layer
   do its work: pages get converted into embeddings
   and stored in a vector database, chunked in sensible
   ways—fixed overlap, sentence or file-format
   chunks—so retrieval finds the right text. A
   retriever pulls relevant documents, which are fed
   into the LLM via prompt engineering; sometimes
   hybrid search adds classic text hits. The result:
   grounded, up-to-date answers. Want to see this
   process with your content? Reach out and we'll
   walk through it together."
```

Reading the rejected synthesis: **factually grounded.**
The chunks talk about embeddings, vector databases,
chunking strategies (fixed overlap, sentence, file-format),
retrieval, hybrid search — all of which appear verbatim
or as paraphrase. No Wikipedia / trafilatura / Character
OS mentions. K6 did its job under strict pressure.

The verifier rejected on `Want` and `Reach` — both at
sentence starts in the CTA closer. They're capitalized
imperative verbs that look proper-noun-shaped to the
extractor.

### Watchdog confirmation

```
python manage.py stoplist_watchdog --days=1

SENTENCE-INITIAL CANDIDATES (stoplist suggestions):
  Want                          1  2026-05-16
  Reach                         1  2026-05-16
  Drop a Wikipedia              1  2026-05-16  (stale; v2 regex fix handles it)

MID-SENTENCE FLAGS (verifier doing its job):
  Wikipedia                     1  2026-05-16

Suggested additions to _COMMON_PROPER_NOUN_FALSE_POSITIVES:
  {"want", "reach", "drop a wikipedia"}
```

The watchdog correctly classified `Want` and `Reach` as
sentence-initial candidates — exactly the case it was
built for. This is the first production-driven stoplist
expansion since the watchdog shipped.

### Stoplist fix — ~40 CTA verbs

Added the CTA-verb false-positive class to the stoplist
in `character_os/claim_verifier.py`:

```
want, wants, wanted
reach, reaches, reached
need, needs, needed
learn, learns, learned
hear, hears, heard
watch, watches, watched
listen, listens, listened
click, clicks, clicked
sign, signs, signed
join, joins, joined
follow, follows, followed
subscribe, subscribes, subscribed
ready, set, go
ping, pings, pinged
email, emails, emailed
call, calls, called
visit, visits, visited
check, checks, checked
discover, discovers, discovered
explore, explores, explored
remember, remembers, remembered
imagine, imagines, imagined
picture, pictures, pictured
consider, considers, considered
skip, skips, skipped
save, saves, saved
share, shares, shared
create, creates, created
build, builds, built
design, designs, designed
send, sends, sent
read, reads
say, says, said
leave, leaves, left
keep, keeps, kept
stay, stays, stayed
pause, pauses, paused
```

Anchored by
`test_stoplist_cta_verbs_k6_4_v2_dogfood` which fires a
synthetic CTA-prose paragraph and asserts none of the
imperative verbs flag.

### Attempt 2 — real Runway render shipped

Same operator prompt, same Donny, same RAG doc, same
strict mode — second fire after the stoplist update:

```
Composition: eaca4f5f-2c64-4f4e-992b-39ad0269a1eb
Status: completed
Cost: $0.25
verification_status: 'verified'
verification_warnings: []

Final asset URL:
  https://dnznrvs05pmza.cloudfront.net/873c5835-abfd-4eb3-a6d5-ab856de9cfd6.mp4?_jwt=...
```

**Real Runway render. Real $0.25 spend. verification_status
correctly tagged 'verified'.** The full K-arc verifier
stack works end-to-end against real production loads.

### Side-effect: trafilatura environmental fix

Running the full test suite during gate-checking surfaced:
```
ModuleNotFoundError: No module named 'trafilatura'
```

The package was pinned in `pyproject.toml` (`>=1.10`) but
uninstalled from the venv at some point — probably during
a Python upgrade. Reinstalled via
`pip install "trafilatura>=1.10" "lxml_html_clean>=0.4"`.
Full suite back to 714/714.

## Calibration moments worth carrying

### 1. Strict mode reveals over-rejection cleanly when synthesis is grounded

The dogfood's surprise was that K6 *didn't* hallucinate
this time — it produced clean grounded content. v2's
stoplist + extractor improvements paid off in shaping the
synthesis. But the verifier still rejected, on innocent
CTA verbs.

This is actually the *ideal* failure mode: a verifier
that flags too aggressively is fixable with stoplist
additions; a verifier that misses real hallucinations is
fixable only with extractor / semantic upgrades. K6.4 v2
shifted the failure surface from "missing real
hallucinations" (v1) to "false-positive on CTA closers"
(v2). The latter is the easier problem.

**Carry-forward**: when a verifier / classifier ships,
expect the failure mode to *shift* with each iteration,
not just shrink. v1's failures were misses; v2's failures
are false positives. v3's failures will be something else
(semantic paraphrases?). Each iteration is doing its job;
the new failure class is the next iteration's input.
**Generalisation**: in classifier pipelines, "fixed
failure mode" isn't a destination — it's a moving target
that follows the easiest remaining bug. Plan for ongoing
calibration, not a final-state shipment.

### 2. The watchdog paid for itself on its first production fire

K6.4 v2 + the watchdog shipped in SESSIONS 165-166. SESSION
167's first real-Runway dogfood surfaced two new false
positives (`Want`, `Reach`). Running
`python manage.py stoplist_watchdog --days=1` immediately
classified them as sentence-initial candidates + emitted
a copy-pasteable Python set literal. Total operator effort
to identify: ~10 seconds. Without the watchdog, this would
have been: read the error message → diff against existing
stoplist → guess at the right additions → repeat. ~5-10
minutes.

**Carry-forward**: tooling that closes the
"observe → identify → patch" loop pays off the moment the
next observation event arrives. The watchdog's design
(SESSION 165) was speculative; SESSION 167's dogfood
event validates it.

## Files changed in this commit

* `shell/character_os/claim_verifier.py` — ~40 CTA-verb
  additions to `_COMMON_PROPER_NOUN_FALSE_POSITIVES`.
* `shell/apps/compositions/tests/test_claim_verifier.py`
  — `test_stoplist_cta_verbs_k6_4_v2_dogfood` regression.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4 v2.1 ship
  notes.
* `docs/TRUST_CALIBRATION.md` — two new entries.
* `00-START-NEXT-SESSION.md` — overwritten for
  SESSION 168.
* `docs/handoffs/SESSION_167_REAL_RUNWAY_DOGFOOD.md` —
  this file.

## What's next (SESSION 168)

The K-arc verifier stack has been validated end-to-end
against real production loads. The verifier shipped a
real Runway render under strict mode at $0.25 with
verification_status=verified — the canonical success
state. Open paths:

1. **More real-Runway exposure** — `talking_head_polished`
   retake of Sasha (V9 captions + intro/outro), or
   `long_form_ad` smoke (V5 launch differentiator).
2. **K6.4 v3 — embedding-similarity fallback** for
   paraphrases. Holds until the operator finds a
   paraphrase miss worth fixing.
3. **Older backlog** — F8.1, K7.x YouTube ingest, K6.3
   brief length cap (15 min), K7.1 cost telemetry,
   W11.1 edit-spokesperson modal.

---

*Handoff written end-of-SESSION 167. Anchors re-stamped
via `context-kit handoff write 167`. One real Runway
asset (Composition `eaca4f5f-...`) shipped at
verification_status=verified.*
