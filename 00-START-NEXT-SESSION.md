---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`
> (5 verbs shipped after SESSION 125).
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** TBD (write in SESSION 137).
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_136_CAST_WENT_LIVE.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11) + cast went live in
real-mode (SESSION 136). Cast members exist as real Spokesperson
rows in admin@mail.com's workspace, all four bound to real Runway
avatars with their preset voices.

**Phase 4 (loosely renamed):** Knowledge layer. SESSION 137 is
the scope-lock conversation; no code lands until the shape is
agreed.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Content | Cast refinement (animals + hoodies)        | DONE (SESSION 135) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| W12 | Legacy single-form retirement                 | Whenever (now ungated) |
| W11.1 | Edit-spokesperson modal                      | Queued |
| K0 | Knowledge layer scope-lock                      | NEXT (SESSION 137) |

**Cast roster in workspace `admins-workspace`:**

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

All four have bound Runway avatars + Cloudfront-hosted portrait
URLs + correct voice presets. They can render videos *right now*,
but they have nothing to talk about — which is exactly the next
problem.

---

## SESSION 137 — Knowledge layer scope-lock conversation

**Don't start coding.** This session is a design conversation
that produces a scope-lock doc, same pattern as the wizard arc
opened with `CREATE_SPOKESPERSON_WIZARD.md` in SESSION 123.

### The framing problem

The four cast members have `business_brief` strings that describe
HOW they sound (Riggs's substantive founder voice, Sasha's cool-
composed sales, Donny's slow attentive listening, Maya's patient
scaffolded teaching). They do NOT have anything that describes
WHAT they know about Character OS specifically. Every render
would be the LLM hallucinating product details from the prompt
+ the spokesperson's tone.

A real spokesperson carries an internal mental model of the
product they represent. We need that.

### Already in the data layer (Phase 1 scaffold, all stubs)

  - `apps/memory/` — empty app, name suggests per-character
    persistent memory
  - `apps/embeddings/` — empty app, name suggests vector storage
  - `apps/conversations/` — `ConversationThread` model exists,
    no UI yet (Maya's tutor mode is the eventual surface)

### Prior art to read before the conversation

u-d-b (the project we've been porting in tiers) has a real
RAG / memory layer. Tier 2 prompt helpers (`DynamicPromptBuilder`)
was queued — likely related. **First thing to do in SESSION 137:**
spend ~30 min reading `unified-donkey-betz/core/memory/` and
`unified-donkey-betz/core/embeddings/` (or wherever the
equivalent modules live) to surface what's already designed.
The scope-lock conversation will be more grounded with the prior
art on the table.

### Five design axes — converge in conversation, lock in doc

1. **Unit of knowledge.** Document uploads (PDFs, markdown,
   transcripts)? Structured facts (FAQ entries, feature lists)?
   Conversational ingestion ("talk to your spokesperson to teach
   them")? Pasted URLs that get crawled? All / hybrid?

2. **Scope: per-spokesperson, per-workspace, or both?** Riggs and
   Sasha both need to know what Character OS *is* (workspace
   level), but each pulls different angles for their job (per-
   spokesperson framing on the same corpus). Two extremes:
   - Pure per-spokesperson: each cast member has their own
     corpus; no shared workspace knowledge
   - Pure per-workspace: one corpus, each spokesperson filters /
     reframes via their `tone_archetype`
   - Hybrid: shared workspace corpus + per-spokesperson overlays

3. **How does knowledge reach the render?**
   - RAG: vector search at render-time, inject top-k chunks into
     the prompt
   - LLM-summarise-at-ingest: compress corpus into per-render
     briefs at ingest time; render just reads the summary
   - Operator-curated: operator picks which knowledge entries
     apply per video (no automation)

4. **Operator management surface.** Where does the operator
   ingest / edit / review knowledge?
   - Dedicated tab on the spokesperson detail page
   - Workspace-level "facts" surface (separate route)
   - Inline during render ("attach context to this video")
   - All of the above?

5. **Maya's tutor-mode tie-in.** Maya's brief explicitly
   mentions "answers the question when the student is stuck" —
   the `ConversationThread` surface that implies needs knowledge
   too. Same store as render knowledge? Different store? Shared
   retrieval logic? The decision shapes whether the knowledge
   layer is render-flow-only or a deeper product surface.

### Deliverable for SESSION 137

`docs/design/KNOWLEDGE_LAYER.md` — scope-lock doc covering:

- The 5 axes, locked
- Data model (which Phase 1 apps get fleshed out, new models if
  needed)
- Backend API surface (probably `/internal/embeddings/` +
  `/api/spokespeople/{id}/knowledge/*`)
- SPA surface
- Migration / database considerations (pgvector? Currently
  sqlite; this may force the Postgres migration that's been
  queued since Phase 2)
- Slice breakdown (probably 6-12 slices like the wizard)
- Out of scope

After scope-lock signs off, slices land like the wizard arc did:
one at a time, with handoffs, with gates clean each time.

### What's NOT SESSION 137

- Any code in `apps/memory/`, `apps/embeddings/`, or
  `apps/conversations/` beyond reading what's there
- Reading u-d-b's modules counts as research, not implementation
- Writing the scope-lock doc IS the deliverable

---

## Queued investigations (priority-ordered)

1. **Knowledge layer scope-lock** (SESSION 137; the framing arc).
2. **`RUNWAY_FORCE_MOCK=1` env override** — tiny config change
   in `media-engine/app/config.py`. Fixes the e2e-breaks-in-
   real-mode workaround (`mv .env .env.real`). Worth landing
   *before* the knowledge arc generates new specs.
3. **Voice preset audit** — happens naturally when first real-
   mode renders land.
4. **First marketing video** — happens naturally once knowledge
   layer ships.
5. **W11.1 — Edit-spokesperson modal.**
6. **W12 — Legacy form retirement.**
7. **Cast sync command** — pull updates from
   `spokesperson_templates.py` into existing rows.
8. **Tier 2 prompt helpers** — may be subsumed by the knowledge
   layer arc; revisit after scope-lock.
9. **Stuck-row janitor** — operational hardening.
10. **Additional video kinds** — cinematic / dialogue / long_ad.
11. **Act-Two performance capture.**
12. **`lesson` video kind** — pairs with conversational tutor.
13. **Real Google OAuth + dj-stripe.**
14. **Allauth legacy-settings cleanup.**
15. **smoke_voice / smoke_avatar transaction discipline.**
16. **Drift verifier** (`verify_doc_claims --only-drift`).
17. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Real-mode vs. mock-mode:** the media-engine reads
`<repo-root>/.env` for `RUNWAY_API_KEY`. With the key present
(real-mode), Runway calls take 15-30s each — fine for CLI use
(`seed_cast`, manual wizard runs) but breaks the e2e suite which
expects sub-second responses. Workaround for tests:

```bash
mv .env .env.real           # stash real .env
# restart media-engine in mock mode
mv .env.real .env           # restore when done
```

Queued #2 in this START doc is a `RUNWAY_FORCE_MOCK=1` override
that'll fix this properly.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest character_os/prompts/        # 46 tests

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e            # full lifecycle ~46s (30 specs), single-shot
```

Cast management CLIs:

```bash
# Generate cast portrait PNGs to disk for preview
python manage.py generate_cast
python manage.py generate_cast --key maya

# Seed the cast as Spokesperson rows + bind avatars
python manage.py seed_cast --workspace-slug admins-workspace
python manage.py seed_cast --workspace-slug admins-workspace --key maya --force
```

---

## AI / assistant context

- Last session: SESSION 136 — cast went live in real-mode. Four
  cast members in admin@mail.com's workspace with bound Runway
  avatars + portrait URLs + voice presets. Three small bug fixes
  surfaced: client timeout 10s → 60s, portrait_path
  silently-blank bug (was wizard-wide, not just cast),
  `.gitignore` widened to `.env.*`.
- **Calibration carried forward:** the operator caught the next
  framing problem before we wasted credits on hollow marketing
  videos. "Step back, what do they talk about?" is the right
  question after "they exist." Apply the same instinct in the
  knowledge arc — design before code.
- **The knowledge layer is multi-session.** Don't try to ship
  it in one. Wizard arc was 11 slices. Knowledge layer likely
  similar scale.
- **Read u-d-b first.** Phase 1 deliberately scaffolded
  `apps/memory/` + `apps/embeddings/` for this moment. There's
  likely prior art worth porting rather than designing from
  scratch.
- **Don't start coding without scope-lock.** Same pattern as
  the wizard. The conversation IS the work.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
