---
state: scaffold
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is the canonical
> answer to *what we're building*. Read it first if you haven't.
> **Runtime truth:** `docs/CHARACTER_OS_INVENTORY.md` (regenerable
> once the inventory generator wires up). Narrative docs lose to
> runtime when they disagree.
>
> **Frontmatter `state:`** above is consumed by `context-kit seed`.
> `scaffold` = freshly init'd. `seeded` = seed ran. `active` = real
> handoffs are landing. Move to `active` when SESSION 106 lands.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
`docs/design/UI_REDESIGN_V2.md` shipped at 845 lines covering
customer/JTBD, pricing tiers, naming (campaign → killed, video is
the unit), data model (Workspace → Spokesperson → Video), Django
DRF shell + FastAPI media engine architecture, 18-screen inventory,
repo strategy (this repo), and 5-phase implementation sequence.

**Phase 1 — Django shell scaffold:** STARTED 2026-05-13. The repo
exists. Monorepo skeleton is in. Context-kit anchors are in.
**Pending in Phase 1 itself:**

1. Import `runway-hackathon/backend/` into `media-engine/` via
   `git subtree` (history preserved).
2. Carry `runway-hackathon/docs/handoffs/` and `runway-hackathon/scripts/`
   into this repo.
3. Scaffold Django project at `shell/` with empty app modules
   (accounts, spokespeople, videos, conversations, memory, billing,
   agents, embeddings).
4. Smoke-test both services boot (Django on 8000, FastAPI on 8001).
5. End-of-session: write SESSION 106 handoff describing what shipped,
   overwrite this file with next priorities.

---

## What's blocking the *real* Phase 1 work

The 4 design-doc questions still open (per §8 of the design doc):

- **Q1 — Product/brand name.** Repo working name is `character-os`.
  The customer-facing brand may be different. Affects landing
  page copy and the eventual `runway-hackathon` repo deprecation
  notice.
- **Q2 — Free trial shape.** 3 free videos no-card vs. 7-day full
  access with card capture. Recommended: no-card 3-video trial,
  iterate from data.
- **Q3 — Activation video hosting.** Mux / Bunny / S3+CloudFront.
  Decide before Phase 3 so the player wrapper is built once.
- **Q6 — Freeze the old `runway-hackathon` repo?** Tag
  `v-final-pre-migration` on main; switch new feature work to this
  repo from then on. Recommended: yes, freeze.
- **Q7 — Marketing site stack.** Same Next.js as the SPA or separate?
  Defer to Phase 3.

None of these block Phase 1 scaffolding itself, but Q6 (freeze)
should be confirmed before Phase 2 (data model migration) starts.

---

## Queued investigations

- **Inventory generator.** Per the context-kit pattern, write a
  `shell/manage.py inventory` command that emits the runtime truth
  (route count, model count, URL patterns) so the docs/anchors
  can be drift-checked. Wire in Phase 1 once Django boots.
- **`scripts/check-context-kit-drift.sh`** — port from
  `runway-hackathon/scripts/`. Same script, updated to the new
  anchor doc names.

---

## AI / assistant context

- This is the first session in the new repo. Prior context lives in
  the sibling `runway-hackathon/` repo (frozen).
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section is required from SESSION 106 onward.
- `docs/TRUST_CALIBRATION.md` starts empty — first real calibration
  event lands there.
