---
title: "Character Os — What It Actually Is"
status: stub
generated: 2026-05-13
companion_doc: CHARACTER_OS_INVENTORY.md
---

# Character Os — What It Actually Is

> **Read-order note:** this doc is the conceptual companion to
> [`CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md). The inventory
> is runtime-derived and regenerable — it tells you *what exists right now*.
> This doc tells you *what it all is, why it exists, and how it fits together*.
> When a number disagrees between the two, INVENTORY wins.

---

## TL;DR — One Sentence

<Replace this: one-sentence pitch. What Character Os is, who it's for, what it does.>

**Scale:** <rough LOC / service count / worker count — approximations only>.

---

## Table of Contents

1. [The Core Idea](#the-core-idea)
2. [The Layered Architecture](#the-layered-architecture)
3. [The Unique Stuff](#the-unique-stuff)
4. [Current State Honesty](#current-state-honesty)
5. [How to Navigate](#how-to-navigate)
6. [Glossary](#glossary)

---

## The Core Idea

<3–6 sentences at the level a non-technical reader could follow. Distinguish
what Character Os IS from what it isn't.>

---

## The Layered Architecture

### Layer 1 — <Data / Ingestion / etc>

<One paragraph.>

| Component | Count | Purpose |
|---|---|---|

### Layer 2 — <Reasoning / Logic / etc>

<One paragraph.>

### Layer 3 — <Interface / API / UI>

<One paragraph.>

---

## The Unique Stuff

<What makes Character Os distinctive vs. off-the-shelf alternatives. Bullets.
Aim for 5–10 genuine differentiators. If you can't find 5, this doc is
premature — just use the inventory until the differentiators emerge.>

### 1. <Unique capability #1>
<2–4 sentences.>

### 2. <Unique capability #2>

### 3. <Unique capability #3>

---

## Current State Honesty

### Working well (as of 2026-05-13)
- <Subsystem A>

### Stale or drifting
- <What's known-broken>
- <Where docs lag>

### Known issues queued for follow-up
- <Bug / task + severity>

**Live drift report:** `python manage.py verify_doc_claims --only-drift` (once wired up).

---

## How to Navigate

### The docs to know

1. [`docs/CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md) — runtime truth, regenerable.
2. [`docs/CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) — this doc.
3. [`CLAUDE.md`](../CLAUDE.md) — AI session entry point.
4. [`00-START-NEXT-SESSION.md`](../00-START-NEXT-SESSION.md) — current priorities.
5. [`docs/topics/`](topics/) — subsystem deep-dives.
6. [`docs/handoffs/`](handoffs/) — session-by-session build history.
7. [`docs/docs-pattern/`](docs-pattern/) — the meta-framework itself.

### Commands to remember

```bash
python manage.py generate_platform_inventory    # or your stack's equivalent
python manage.py verify_doc_claims --only-drift
python manage.py build_docs_index
```

---

## Glossary

| Term | Meaning |
|---|---|
| **Character Os** | <one-line definition> |

<Alphabetize. Add every term that's platform-specific jargon.>

---

*Last revised: 2026-05-13. When this doc drifts from reality, regenerate
`CHARACTER_OS_INVENTORY.md` first — that's always authoritative.*
