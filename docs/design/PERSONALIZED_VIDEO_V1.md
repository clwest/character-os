---
title: "Personalized Video (B-3) — one template + N recipients = N videos"
status: locked
proposed: 2026-05-20 (SESSION 203, slice B3.0)
locked: 2026-05-20 (SESSION 203, slice B3.0)
closed: null
companion_docs:
  - CONTENT_FORMAT_BACKLOG.md
  - VIDEO_COMPOSITION_V1.md
  - TRANSCRIPT_MINER_V1.md
  - ASSET_LIBRARY_V1.md
---

# Personalized Video — variable-substitution at render time

> **Status: PROPOSED (SESSION 203).** Second strategic-axis arc.
> Per `CONTENT_FORMAT_BACKLOG.md` §B-3 the highest-revenue
> remaining axis: variable-substituted talking-head videos at
> batch scale. Nine contract rules; ten slices B3.0-B3.9.
> Estimated 6-7 sessions to ship. Operator review + lock target:
> SESSION 203 (this session).

---

## TL;DR

The B-arc shipped per-workspace transcript mining as a unique
data play. **B-3 ships the second unique-to-this-stack
capability**: batched personalized videos. Operator writes one
script template with `{variable}` placeholders, pastes a CSV
of recipients, hits launch — system fans out N
`talking_head_polished` compositions, one per row. Each
recipient gets their own renderable asset.

This is a different SKU than one-off videos:

* **Stickier**: CSV ingestion + per-recipient analytics + CRM
  webhook integration (v2) make this the integration-anchored
  workflow operators don't churn out of.
* **Higher-margin**: per-render charge or tier-gated cap means
  revenue scales with batch size, not with logged-in seats.
* **Structurally unique**: per-workspace avatars are
  load-bearing here — generic LLM video can't deliver "Hi
  {firstName}, saw {company}…" with consistent on-brand
  spokesperson identity.

This arc ships:

1. A **template-rendering helper** — `render_template(template,
   variables)` with strict missing-key handling (no silent
   `{}` swallow).
2. A **`PersonalizedCampaign` + `PersonalizedRecipient`**
   model pair persisting the batch shape and per-recipient
   state machine (PENDING → QUEUED → COMPLETED / FAILED).
3. A **REST surface** for create / parse CSV / launch / per-
   recipient retry. Workspace-isolated; tier-gated batch size.
4. A **completion signal** that flips recipient status when
   the per-row composition finishes (mirrors B-1's
   `post_save` receiver shape).
5. A **SPA flow** at `/workspace/campaigns` — paste CSV,
   review variables, see cost forecast, launch, watch the
   recipient progress grid.

Out of scope for v1: file upload (paste-only); CRM webhook
integration; per-recipient email validation; email send / SMS
delivery (operator distributes the rendered assets out-of-band);
per-recipient analytics (open / play tracking); template
versioning; A/B variants (separate B-18 axis).

---

## Why now

Five drivers converge:

1. **B-arc validated the strategic-axis arc cadence.** The
   A-arc (SESSIONS 185-192) and B-arc (SESSION 202) both
   shipped end-to-end real-mode in one extended session each.
   B-3 is the third such arc; the scope-lock pattern is now
   proven.
2. **Highest-revenue candidate per the backlog.** Vidyard /
   Loom / Tavus all sell this category. We have the
   structurally-unique capability (per-workspace avatars) that
   generic-LLM-video competitors lack.
3. **All required primitives ship.** `talking_head_polished`
   is real-mode validated; the recipe registry composes
   cleanly; `execute_composition.delay` is the established
   fan-out primitive.
4. **Asset Library handles the output side.** Each
   per-recipient asset lands as a normal `Asset(role=TALKING_HEAD)`
   in the workspace — browsable + lineage-linkable via the
   F-arc + A-arc surfaces. No new asset infrastructure
   needed.
5. **Tier infrastructure exists.** `apps.billing.services`
   already gates by `videos_per_month`; B-3 reuses that gate
   and adds a per-batch cap dimension.

---

## Contract rules (load-bearing)

Nine rules. None overlap V1's existing 22 (V1 ×9 + V17 ×4 as
10-13 + Asset Library ×9 as 14-22) or the B-1 ×8 rules. C-arc
rules become V1 rules 31-39 if a future V-arc lock merges
them; v1 keeps them on this doc.

1. **CSV header is the template variable contract.** Header
   row column names MUST be a strict superset of the
   `{placeholder}` names in the template. Mismatches reject
   at campaign-create time, not at render time. Missing
   variables in a recipient row reject that row, not the
   batch.

2. **Per-recipient compositions are independent.** Each
   recipient = one `Composition` row = one final `Asset`. No
   "batched composition" that fans out internally — the V-arc
   keeps its one-script-per-Composition shape (V1 rule 5).
   The batch concern lives on the `PersonalizedCampaign` row.

3. **Workspace-scoped end-to-end.** Campaign + recipients FK
   to Workspace. Cross-workspace lookups rejected at clean()
   + `pre_save` signal. Mirrors V1 rule 1.

4. **Tier-gated at TWO dimensions.** Per-batch cap (Starter=5,
   Pro=30, Agency=200) prevents one accidental click from
   blowing through the monthly quota; per-month `videos_per_month`
   limit still applies. Both checked at LAUNCH time, not at
   create time — operator can draft batches over-cap and
   trim before launching.

5. **PII storage is opt-in via the variables dict.** Recipient
   rows store `variables: JSONField`. If the operator's CSV
   has a `first_name` or `company_email` column, that's where
   it lives. v1 does no special PII handling beyond workspace
   isolation. No email validation, no PII redaction, no
   right-to-erasure UX (covered structurally by
   workspace-cascade-delete).

6. **Launch is operator-explicit.** Creating a campaign
   doesn't fire anything. The flow is:
   create → parse CSV → review recipients → see cost forecast
   → click "Launch" → confirm → fan-out. Operator can edit /
   reject recipients before launch. Once launched, a recipient
   cannot be edited — only retried.

7. **No new primitives or recipes.** v1 reuses
   `talking_head_polished`. New work is one template helper +
   one app + REST + SPA. Future per-platform fan-out (B-14
   integration) would land as a separate slice.

8. **Per-recipient failures don't block the batch.** One
   recipient's composition failing logs the error on the
   recipient row + flips status to FAILED; the rest continue
   to completion. Operator retries failed recipients
   individually.

9. **Composition naming carries provenance.** Each
   per-recipient composition's `name` follows
   `{campaign.name} — {recipient.label}` where
   `recipient.label` is `variables.get('first_name')` if
   present, else `variables.get('email')`, else `recipient #N`.
   Auditable via the F-arc lineage; the Asset Library SPA
   shows them grouped by campaign visually via name prefix.

---

## Data model additions

### `apps.campaigns.models.PersonalizedCampaign`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace` | FK Workspace | V1 rule 1 isolation |
| `spokesperson` | FK Spokesperson | the on-camera identity for all recipients in this batch |
| `name` | CharField(120) | operator-supplied |
| `template` | TextField | script with `{placeholder}` variables |
| `placeholders` | JSONField (list[str]) | parsed from template at create time; readonly thereafter |
| `status` | TextChoices | DRAFT / LAUNCHING / IN_FLIGHT / COMPLETED / PARTIAL / FAILED |
| `created_by` | FK User | |
| `launched_at` | DateTimeField, nullable | |
| `completed_at` | DateTimeField, nullable | |

State machine:

```
DRAFT ──launch──▶ LAUNCHING ──(all recipients enqueued)──▶ IN_FLIGHT
                                                                │
                       ┌────────────────────────────────────────┘
                       ▼
              (every recipient resolved)
                       │
                  ┌────┴────┐
                  ▼         ▼
              COMPLETED   PARTIAL  (or FAILED if all failed)
```

### `apps.campaigns.models.PersonalizedRecipient`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `campaign` | FK PersonalizedCampaign | CASCADE; workspace inherited via clean() |
| `variables` | JSONField (dict) | one row from the CSV; keys ⊇ campaign.placeholders |
| `label` | CharField(200) | derived for display: first_name / email / "recipient #N" |
| `status` | TextChoices | PENDING / QUEUED / RUNNING / COMPLETED / FAILED |
| `produced_composition` | FK Composition, nullable | set when launched |
| `error_message` | TextField, blank | populated on FAILED |
| `rendered_script` | TextField | the substituted script after template-render |
| `position` | PositiveInteger | row order from CSV; for stable display |
| `created_at` / `updated_at` | DateTimeField | |

Indexes: `(campaign, status)` for progress queries; `(produced_composition)` for the completion-signal reverse lookup.

### No `Composition` schema change

Per-recipient compositions are vanilla `talking_head_polished`.
The Asset Library A8 cross-link surface already shows
"composition → assets"; the `Composition.name` carries the
campaign provenance per rule 9. F-arc lineage works without
modification.

---

## New / extended endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/campaigns/` | create a DRAFT campaign (workspace, spokesperson, name, template). Returns the row + parsed placeholders. |
| `POST` | `/api/campaigns/<id>/parse_csv/` | body `{csv_text}`. Parses header + rows; validates against campaign.placeholders; persists `PersonalizedRecipient` rows. Returns the per-row parse result (validated count, rejected rows, per-row issues). |
| `GET` | `/api/campaigns/` | list workspace campaigns, filterable by `?status=`. Paginated. |
| `GET` | `/api/campaigns/<id>/` | detail with recipients + per-status counts. |
| `GET` | `/api/campaigns/<id>/forecast/` | cost preview: `{recipient_count, tier_limit, projected_cost_micros, batch_cap, will_throttle}`. |
| `POST` | `/api/campaigns/<id>/launch/` | tier-gates + fans out N compositions in a single transaction. Returns the updated campaign with `status=LAUNCHING`. |
| `POST` | `/api/campaigns/<id>/recipients/<rid>/retry/` | re-enqueue a FAILED recipient. Resets to QUEUED. |
| `DELETE` | `/api/campaigns/<id>/` | DRAFT-only. Cascades recipients. |

---

## Slice breakdown (10 slices, B3.0-B3.9)

| # | Slice | Effort |
|---|---|---|
| **B3.0** | This scope-lock doc | ½ session (current) |
| **B3.1** | Template helper | ½ session. `character_os/template_renderer.py`: `parse_placeholders(template) -> list[str]`, `render_template(template, vars) -> str` with strict missing-key handling. Tests cover happy path, missing vars, extra vars (allowed), nested braces, doubled-braces escape (rule? — defer to Q-c-7). |
| **B3.2** | `PersonalizedCampaign` + `PersonalizedRecipient` models + migration + signal | ½ session. New `apps.campaigns` app. Cross-workspace pre_save guard. |
| **B3.3** | CSV parser helper | ½ session. `character_os/csv_recipients.py`: take a CSV string + expected placeholders → return `{valid_rows: [...], rejected_rows: [...]}`. Tests cover quoted fields, missing columns, empty rows, BOM, header-only. |
| **B3.4** | REST: create + parse_csv + list + retrieve + delete | 1 session. `CampaignViewSet` with the read endpoints and the parse_csv action. Workspace isolation tests. |
| **B3.5** | REST: forecast + launch | 1 session. Tier-gate at LAUNCH (both per-batch and per-month). Fan-out compositions in a single atomic transaction; enqueue `execute_composition.delay()` after commit. |
| **B3.6** | Completion signal + per-recipient retry | ½ session. post_save receiver on Composition flips recipient status; campaign rollup → COMPLETED/PARTIAL. Retry endpoint resets one row to QUEUED. |
| **B3.7** | SPA: campaign list + create + CSV paste | 1 session (subagent). New `/workspace/campaigns` route. Composition is paste-CSV (no file upload v1). Validation errors shown inline per-row. |
| **B3.8** | SPA: campaign detail + launch + recipient grid | 1 session (subagent). Cost forecast modal, launch button, real-time recipient status grid (poll every 5s during IN_FLIGHT). Per-recipient retry button on FAILED rows. |
| **B3.9** | Real-mode dogfood + arc close | ½ session. Small batch (2-3 recipients) against Marcus or Sasha. Capture calibration entries. Close the arc. |

Total: ~7 sessions.

---

## In-scope clarifications

* **Template variables are flat `{name}` placeholders.** No
  conditionals, no formatters, no nested objects. Operator
  writes "Hi {first_name}, saw {company} just hit {milestone}"
  and CSV header is `first_name,company,milestone`.

* **Tier-gated batch caps live in TIER_LIMITS** as a new
  field `personalized_batch_max`. Proposed values:
  Starter=5, Pro=30, Agency=200. Resolved at B3.2.

* **Cost forecast** sums per-recipient
  `talking_head_polished` cost ($0.25 from B-arc dogfood) ×
  recipient count. Shown in the launch modal before
  confirmation.

* **Composition naming** per rule 9. The Asset Library SPA
  filter-by-name-prefix surfaces a campaign's outputs as a
  group without new infrastructure.

* **Per-recipient retry uses the existing `retry_step`
  pattern** from the B-arc / V-arc — recipient row reset to
  QUEUED, composition re-enqueued via `execute_composition.delay`.

---

## Out of scope (v1)

* **File upload** for CSV. v1 is paste-text-only per the
  backlog risk note + the B-1 v1 precedent (operator-pasted
  inputs are good enough for v1; file upload UX is a
  separate slice).
* **CRM webhook integration** (Salesforce, HubSpot push).
  v2 axis with its own auth + rate-limit surface.
* **Email validation / format checking** in the CSV. The
  operator writes whatever they want; we render whatever
  they pasted.
* **Email send / SMS delivery** of rendered videos. Operator
  distributes the assets via their own channels. The arc
  produces the videos; it doesn't ship them.
* **Per-recipient analytics** (open / play / completion
  tracking). Per-asset tracking lands in a separate arc
  once a distribution surface exists.
* **Template versioning.** Edit-after-launch is forbidden —
  operator creates a new campaign for v2 of a template.
* **A/B variants per recipient.** Separate B-18 axis.
* **Per-platform fan-out** (each recipient → Reels +
  Square + Horizontal). B-14 axis can compose with B-3 in
  v2.
* **Live preview** of the substituted script before launch.
  Operator can read one rendered_script via the recipient
  detail view; no real-time substitution preview.

---

## Open questions (resolve in slices)

* **Q-c-1**: Default batch-size tier caps. **Proposed**:
  Starter=5, Pro=30, Agency=200. Aligns with per-month
  videos cap (5 lets a Starter try the feature; 200 is a
  meaningful B2B blast). Resolve at B3.2.

* **Q-c-2**: Cost forecast helper — reuse R9's
  `estimate_session_cost_micros` shape or write a new
  per-recipient one? **Proposed**: write a new
  `apps.campaigns.cost` module mirroring R9's structure.
  R9's helper is realtime-session-specific; sharing would
  couple the two arcs unnecessarily. Resolve at B3.5.

* **Q-c-3**: CSV ingest format — comma-only, tab-allowed,
  Excel paste? **Proposed**: standard CSV via Python's
  `csv` module with `dialect='excel'`. Operator paste of
  TSV would need a separate dialect; defer to v2. Resolve
  at B3.3.

* **Q-c-4**: Email field special-casing. **Proposed**:
  none in v1 — emails are just another `{variable}`. Email
  validation is per-template; v2 might surface a "this
  template includes an email field" checkbox that opts in
  to validation. Resolve at B3.3.

* **Q-c-5**: Composition name format. **Proposed**:
  `{campaign.name} — {recipient.label}` per rule 9.
  Recipient.label derived as `first_name` → `email` →
  `recipient #N`. Resolve at B3.2.

* **Q-c-6**: Per-recipient retry semantics. **Proposed**:
  one click resets the recipient row to QUEUED + creates a
  NEW Composition (the old failed composition stays in the
  workspace as audit). Operator can delete the failed
  composition separately if needed. Resolve at B3.6.

* **Q-c-7**: Doubled-brace escape in templates
  (`{{literal}}` to mean a literal `{`)? **Proposed**: yes,
  follow Python's `str.format()` convention. Trivial to
  support via the standard library. Resolve at B3.1.

* **Q-c-8**: What does an empty CSV look like (just header
  row)? **Proposed**: campaign stays in DRAFT with
  recipient_count=0; launch returns 400 "no recipients to
  launch". Resolve at B3.3 + B3.5.

* **Q-c-9**: Campaign delete behavior. **Proposed**: DRAFT
  campaigns delete-with-cascade. LAUNCHING / IN_FLIGHT
  campaigns refuse delete (compositions are mid-flight).
  COMPLETED / PARTIAL / FAILED campaigns are soft-deletable
  (cascade recipients + nullify Composition.source_campaign
  if we add such an FK; for v1 just cascade the recipient
  rows, leave compositions intact for audit). Resolve at
  B3.4.

---

## Change log

* **2026-05-20 (SESSION 203, slice B3.0)** — Initial scope
  proposal. Second strategic-axis arc after the B-arc close.
  Nine contract rules; ten slices B3.0-B3.9 sequenced.

* **2026-05-20 (SESSION 203, B3.0 LOCKED)** — Operator signed
  off as-proposed. All 9 contract rules accepted without
  revision. All 9 open questions accepted with proposed
  resolutions. Status flips proposed → locked. B3.1
  (template helper) opens immediately.
