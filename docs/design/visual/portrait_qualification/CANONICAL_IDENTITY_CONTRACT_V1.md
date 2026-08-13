---
title: "Character OS — Canonical Identity Contract"
status: ratified
generated: 2026-08-06
last_revised: 2026-08-06 (§17 fully ratified, walkthrough complete)
companion_docs: ["../PORTRAIT_LANGUAGE_V1_2026-08-06.md", "../PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md", "../VISUAL_TERRITORY_DECISION_V1_2026-08-06.md", "README.md"]
---

# Canonical Identity Contract

## v1 — the durable anchor every render must derive from

> **This document is an implementation contract, not a visual-design
> document.** It sits between the design lock
> ([`PORTRAIT_LANGUAGE_V1_2026-08-06.md`](../PORTRAIT_LANGUAGE_V1_2026-08-06.md))
> and any code, migration, or provider integration that follows. Its
> job is to translate design constraints into an implementable schema,
> lifecycle, and provider-boundary shape — and to expose the decisions
> that must be resolved before any of that becomes production code.
>
> **Nothing in this document is ratified.** It is a draft posted for
> contract-review before any model, migration, or provider adapter is
> written. Unresolved decisions are surfaced in
> [§17](#17-unresolved-decisions-requiring-operator-resolution).

---

## 1. Purpose and scope

### 1.1 What this contract is for

The portrait provider qualification benchmark defined in
[`PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md`](../PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md)
requires empirical evidence that a candidate rendering direction can
preserve a specific teammate's identity across still portraits, idle
motion, narration, live conversation, and transitions between those
surfaces. Two of the benchmark's required exit gates —
**consistency under regeneration** (§3.7) and **cross-modal
continuity** (§3.1) — presuppose that "the same teammate" is a
verifiable thing rather than an operator aspiration.

Today it is an aspiration. The current `Spokesperson` model carries a
single `portrait_path` string, a free-text `visual_subject`, an
opaque `runway_avatar_id`, and a `voice_id` string. Nothing in that
shape allows one render to be verifiably "the same person" as
another render, whether across providers, across surfaces, or across
regenerations.

This contract defines the **durable identity anchor** every render
must derive from, and the boundary shapes at which providers and
normalization interact with that anchor. It defines only what must
exist for benchmark evidence to be comparable and reproducible.

### 1.2 What this contract is not

- Not an aesthetic specification. Aesthetic register is deferred to
  Portrait Territory Study V2, which folds benchmark evidence.
- Not a UI or wizard specification. Customer-facing collection of
  identity data is out of scope until the benchmark tells us which
  inputs are actually load-bearing.
- Not a code specification. Field lists in
  [§15](#15-proposed-persistence-shape) are illustrative of the shape
  a future migration would take, not prescriptive names.
- Not a Django-model-first decision. Where evidence, scoring, or
  reviewer notes can live in the repository as versioned files
  without becoming production data, they should.

### 1.3 Companion documents and precedence

When this contract conflicts with a companion document:

- **Portrait Language V1 wins** on identity, framing, gaze,
  expression, motion, lighting, diversity, and provider-qualification
  discipline. This contract is Portrait Language's implementation
  translation; it does not overrule Portrait Language.
- **Portrait Territory Study V1 wins** on benchmark structure, exit
  criteria, weighted evaluation categories, and sequenced decision
  path. This contract is silent on the aesthetic outcome of that
  study.
- **The Character OS runtime inventory
  (`docs/CHARACTER_OS_INVENTORY.md`) wins** over any description of
  current state written here. If this contract's description of the
  current `Spokesperson` shape is stale, the inventory is right.
- **This contract wins** over incidental narrative in older handoffs
  and in `CLAUDE.md` about how identity should be persisted, because
  no earlier document decided the question.

---

## 2. Domain ownership decision

### 2.1 The tension

The current codebase names the customer's teammate object
**`Spokesperson`** (Django `apps/spokespeople/models.py`). The
redesigned customer-facing product model uses **Teammate** — the
term appears throughout the seven canonical screen specs and the
Product IA document. Portrait Language additionally reserves a
**non-human teammate** branch (§19) governed by a future Character
Presence Language.

Three plausible ownership shapes exist:

1. **Identity attached directly to `Spokesperson`.** Simplest;
   inherits legacy naming. Couples identity to a term the product
   surface has moved away from and forces non-human teammates
   through a class named after a human role.
2. **A new internal `TeammateIdentity` entity referenced by
   `Spokesperson` (and by any future rename).** Decouples identity
   from the current row's naming. Allows the outer object to be
   renamed later without touching identity storage. Human-only if
   the type stays literal to its name.
3. **A more general `CharacterIdentity` capable of supporting human
   and non-human teammates via a branch discriminator.** Matches
   Portrait Language §19's future-preservation clause. Neutral to
   the eventual customer-facing term.

### 2.2 Recommendation

**Option 3 — `CharacterIdentity` with a `kind` discriminator.**
Rationale:

- The product's customer-facing name (Teammate) is a UI/copy
  decision. The identity substrate should not encode a UI term any
  more than a database schema should encode a button label.
- Portrait Language explicitly preserves non-human teammates as a
  first-class branch, not a lesser mode. Naming the identity object
  after "teammate" leaves the door open; naming it after
  `Spokesperson` closes it.
- The name **CharacterIdentity** aligns with the product's own
  name (Character OS) at the domain layer. Customer-facing surfaces
  continue to say "teammate."
- `Spokesperson` remains the outer row that owns workspace scoping,
  status, business brief, and product metadata. It holds a
  reference to a `CharacterIdentity`, not the identity itself.
  This inverts today's shape (identity fields are on
  `Spokesperson`) without forcing a rename of the outer object
  during this phase.

### 2.3 Consequences

- Rename `Spokesperson` → `Teammate` becomes a separate,
  independent decision — this contract neither requires it nor
  blocks it.
- Identity can migrate later without a rename of the customer's
  product object.
- Non-human teammates fit natively.
- The illustrative schema in [§15](#15-proposed-persistence-shape)
  uses `CharacterIdentity` as the substrate name. If the operator
  prefers `TeammateIdentity` or another name, only the noun
  changes; the shape does not.

### 2.4 Question surfaced for operator

> Ratify **`CharacterIdentity`** as the identity substrate name, or
> propose an alternative. Also decide whether `Spokesperson` is to
> be renamed to `Teammate` in a separate track — the identity
> contract is neutral to that decision but the operator should not
> discover the naming conflict at migration time.

---

## 3. Human and non-human identity branches

### 3.1 Discriminator

Every `CharacterIdentity` carries a required `kind` value:

- **`human`** — governed by Portrait Language V1.
- **`non_human`** — governed by a future Character Presence Language.
  Portrait Language §19 preserves this branch as first-class and
  forbids treating it as a novelty tier.

Additional values may be introduced later. `kind` is the only field
whose presence and validity is universal across every identity.

### 3.2 Branch-specific specification payload

Human-specific facial fields (facial geometry, skin tone, eye shape,
facial hair, and so on) **must not become required columns on every
identity row.** An identity for a non-human teammate has no
"skin tone." Modeling those fields as universally-required columns
either lies (by holding nulls that mean "N/A") or forces non-human
teammates through a human-shaped grid.

The specification payload is therefore **typed by branch**:

- Every identity carries a `spec` blob (structured document, not a
  loose JSON dumping ground) validated against a
  schema selected by `kind`.
- The **human spec schema** enumerates the fields Portrait Language
  §3 mandates for humans, subject to the classification in
  [§4](#4-field-classification).
- The **non-human spec schema** is a separate schema, described
  only in outline here (see §3.4). It is authored alongside the
  Character Presence Language when that document lands.

Whether the `spec` blob lives as JSON in a single database column
or as a table-per-branch is deferred to
[§15](#15-proposed-persistence-shape). The contract requires only
that **the schema is discriminated by `kind` and that human-shaped
fields do not exist on non-human identities.**

### 3.3 Non-human identity — what is preserved

Even for non-human teammates, the following identity concerns
survive from Portrait Language and must have a home in the
non-human schema, once written:

- Identity continuity across surfaces (whatever "the same character"
  means for the specific non-human).
- Voice linkage (a non-human teammate may still speak).
- Approved reference view set (the visual anchor form varies by
  character type; the concept of "approved canonical references"
  does not).
- Motion discipline (presence without performance still applies).
- Fallback behavior when a render degrades (still-plus-voice
  fallback still applies).

### 3.4 What this contract defers to the Character Presence Language

- The exact field list of the non-human spec schema.
- The classification of non-human spec fields (see §4) beyond the
  observation that non-humans still have facts, presentation
  preferences, rendering constraints, and asset-backed references.
- Whether a non-human identity may reuse the human approved-reference
  view roles (front / slight-left / slight-right / expression) or
  requires its own set.

The contract commits only to the branch structure. It does not
attempt to author the non-human specification.

**Ownership vs. immutability (ratified [§17.2.a](#172-non-human-branch-authorship)).**
Deferral is **permanent ownership**, not permanent immutability of
this document. Once Character Presence Language is approved, this
contract may receive a compatibility amendment that documents the
new schema and the references it introduces, but this contract
must not become the source of truth for non-human visual rules.
The non-human spec schema itself is authored in Character Presence
Language, not here.

---

## 4. Field classification

Portrait Language §3 names eleven concepts. Not every concept becomes
a database column. Some are enduring facts about who this
teammate is; some are preferences about how to render them; some
are derived observations captured during a specific generation; some
are relationships to assets that live elsewhere. Mechanically
turning every named concept into a nullable field on one wide row
would produce an unfocused schema that is hard to validate, hard to
version, and hard to reason about at review time.

The contract classifies every candidate field into one of the
following seven categories. Each field in the human spec schema (see
[§7](#7-canonical-identity-fields-illustrative-human-branch)) must be
tagged with exactly one classification.

### 4.1 The seven classifications

**Canonical identity fact.** A durable statement about who this
teammate is. Changes to a canonical identity fact require a new
identity version (see [§5](#5-identity-lifecycle-and-versioning)).
Example: canonical hair characteristics.

**Presentation preference.** How this teammate should be rendered
when the provider offers a choice. Preferences may be updated in
place without a new identity version, but they are recorded on the
version they apply to. Example: preferred framing default among the
three framing families in Portrait Language §4.

**Rendering constraint.** A rule the render must satisfy that is
not itself a fact about the teammate. Constraints derive from
Portrait Language and Portrait Territory Study rather than from
per-teammate authorship. Example: "beauty-filter smoothing
forbidden" applies to every human identity.

**Provider-specific provenance.** Data that describes how a specific
provider produced a specific output. Never on the identity itself.
Belongs on generation records (see
[§8](#8-generation-attempt-provenance)). Example: Runway avatar
identifier, Stability seed value.

**Derived normalization value.** A value produced by the
normalization layer (see
[§10](#10-normalization-boundary-payload)) from raw provider output
plus the identity spec. Belongs on the normalized output record,
not on the identity. Example: recorded eye-line offset for a
specific approved-reference view.

**Asset-backed reference.** A pointer to an `Asset` row (still image,
audio clip, or other binary artifact) whose role in identity is
recorded via a typed reference relationship (see
[§7](#7-asset-and-reference-view-relationships)). Never a URL string
on the identity row. Example: the approved front-facing canonical
portrait.

**Runtime-only state.** Values that exist only during a live
interaction and are not persisted with the identity. Example: the
current gaze target during an active realtime session.

### 4.2 How the classification prevents schema drift

- Fields tagged **canonical identity fact** and **presentation
  preference** are the only ones that need columns (or blob members)
  on the identity spec itself.
- Fields tagged **rendering constraint** live in policy or in
  provider adapters, not on the identity.
- Fields tagged **provider-specific provenance** live on generation
  records. Never on the identity.
- Fields tagged **derived normalization value** live on the
  normalized output record, referencing back to the identity
  version.
- Fields tagged **asset-backed reference** live on a reference
  relationship record whose type is enumerated (see
  [§7](#7-asset-and-reference-view-relationships)).
- Fields tagged **runtime-only state** never touch the persistence
  layer.

If a proposed field cannot be honestly tagged with exactly one
classification, it is not ready to be persisted.

---

## 5. Identity lifecycle and versioning

### 5.1 Why versioning is not optional

An identity is not a single mutable record. Reasons:

- A teammate may exist in a **draft state** during authoring (before
  the initial approved reference set exists) and in an **approved
  state** afterward. Both must be representable.
- After approval, an operator may want to **update** the identity
  (change hair, change canonical outfit, refresh the reference set).
  Silently rewriting the row invalidates every prior generated
  artifact by making it "no longer of this identity" without
  recording that it was of the prior identity.
- Provider qualification will generate many attempts, many rejected,
  a few approved. The identity must be able to point at "what
  succeeded" without losing the record of what was tried.
- If the eventual selected aesthetic direction changes, the identity
  version at the time of a piece of published customer work needs
  to remain queryable so the work can be re-rendered against the
  original identity if needed.

### 5.2 Version states

Every identity version carries one of:

- **`draft`** — under authoring. The spec exists, no approved
  reference views yet, or approval is pending.
- **`approved`** — the reviewer boundary has cleared this version
  and its reference set. Renders may derive from it. Exactly one
  version per identity is the **current approved** version at a
  given time.
- **`superseded`** — was `approved`; a newer version has become the
  current approved. The superseded version is preserved so prior
  work can be traced to the identity that produced it.
- **`rejected`** — was `draft`; reviewer boundary rejected the
  version. Preserved as evidence of what was tried and why.

### 5.3 Version identity

An identity version is identified by:

- The parent `CharacterIdentity` id.
- A monotonically-increasing revision integer within that identity.
- Its state.
- Its `spec` blob (immutable once the version leaves `draft`).
- A timestamp of creation and, when applicable, of state
  transitions.
- The reviewer boundary decision record (see
  [§6](#6-approved-representation-bundle)).

### 5.4 What triggers a new version

New version required (immutable spec):

- Any change to a field tagged **canonical identity fact**.
- Any change to the approved reference view set.
- Any change to the approved voice binding.
- Any change to the approved realtime representation.

New version not required (mutable in place, but recorded against the
version):

- Any change to a field tagged **presentation preference**.

### 5.5 Rendering derives from a specific version

Every generation record (see [§8](#8-generation-attempt-provenance))
and every normalized output (see
[§10](#10-normalization-boundary-payload)) references **the identity
version** it was produced against, not just the identity id. This is
how prior work stays anchored to the identity as of the time it was
produced.

### 5.6 What the current approved version means

At any moment, an identity has **at most one current approved
version**. Product surfaces that render a teammate resolve through:

1. The teammate's identity.
2. The identity's current approved version.
3. The version's approved representation bundle (see
   [§6](#6-approved-representation-bundle)).

If no approved version exists, the teammate is in an unrenderable
state and the product must present the pre-approval fallback
described in Portrait Language §15.

### 5.6.a State semantics — currently admitted, not qualified

**Ratified — 2026-08-07 (SESSION 243).** `state='approved'` on
`CharacterIdentityVersion`, `ApprovedRepresentationBundle`,
`IdentityReference`, `CanonicalVoiceReference`, and
`CanonicalRealtimeReference` means **currently admitted for product
use.**

It does **not** mean:

- Portrait Language qualified.
- Benchmark qualified.
- Schema validated against the branch schema's `spec_payload_schema`.
- Reviewer-approved under the final qualification discipline (which
  does not yet exist in code).

Those are separate axes carried by:

- `ImportProvenance` presence (per
  [§17.10.a](#1710-existing-spokesperson-field-disposition)
  Amendment 2) — the version was landed by Step 3's one-time
  legacy backfill.
- `PrequalificationProvenance` presence (per
  [§17.10.a](#1710-existing-spokesperson-field-disposition)
  Amendment 4) — the version was landed by a post-Step-4 canonical
  authoring flow that predates the qualified authoring path.
- `CharacterIdentityVersion.spec_schema_version` — `0` is the
  `legacy_unvalidated` sentinel (used by both provenance
  categories above); values `>= MIN_CANONICAL_SPEC_SCHEMA_VERSION`
  indicate branch-schema-validated authoring at write time.
- A future explicit qualification status
  ([§17.10.a](#1710-existing-spokesperson-field-disposition)
  Amendment 2 vocabulary `qualification_validated`), to be landed in
  Steps 8+.

Downstream readers requiring qualification must consult the
available provenance / schema-validation state and, once landed,
the explicit qualification status. `state='approved'` alone is
**never** sufficient evidence of qualification.

This ratifies the operational convention already landed in SESSION 242
(Step 3): Step 3 legacy imports land at `state='approved'` without any
qualification claim, distinguishing "currently admitted" from
"qualified" via provenance rather than via state. That convention is
the correct semantic; this ratification makes it first-class contract
text so future readers do not silently narrow `APPROVED` back to
"qualified" and re-introduce the semantic drift Step 3 already
resolved.

**Interaction with [§5.4](#54-what-triggers-a-new-version):** §5.4's
"new version required" rules are unchanged. `APPROVED` semantics
apply to whichever version is currently the current-approved one at
each moment. Every representation-set change still creates a new
version per §5.4; the new version enters at `APPROVED` (currently
admitted for product use) while the prior one becomes `SUPERSEDED`.

---

## 6. Approved representation bundle

### 6.1 Why a bundle exists

Voice, portrait, and realtime avatar do not inherently "belong"
together at the provider level. A voice_id is a string. A
runway_avatar_id is a string. A stability seed is an integer. Any
combination could be composed; the product binds them because
together they represent one teammate.

If the binding lives only as three sibling fields on the identity
row, several failure modes appear:

- Updating the voice does not update the portrait or realtime avatar,
  and there is no record that the trio has now been changed.
- A rendering surface can pick and choose between the fields it wants
  and skip validation that the combination has ever been approved
  together.
- Reverting one field to a prior value silently reconstructs a trio
  that was never reviewed as a whole.

The **approved representation bundle** solves this by making the
approved combination itself a first-class record.

### 6.2 What a bundle binds

An approved representation bundle references:

- **An identity version.** The bundle is scoped to one version.
- **An approved portrait reference set.** One or more approved
  reference-view assets (see
  [§7](#7-asset-and-reference-view-relationships)).
- **An approved voice.** A **canonical voice reference** scoped
  to the workspace and verified to belong to it. The bundle
  references the canonical voice; provider details (which
  provider designed the voice, provider-side identifier, seed,
  reference audio) live on the voice reference's own
  provenance record, not on the bundle. The rest of the
  platform asks for "the approved voice" — never for a
  provider-specific ID.
- **An approved realtime representation.** A **canonical
  realtime reference** scoped to the workspace and verified to
  be in a rendering-ready state. Same provider-neutral shape as
  the approved voice: the bundle references the canonical
  realtime representation; provider details live on that
  reference's provenance record.
- **A normalization profile.** The record of which normalization
  parameters apply when rendering this bundle. See
  [§10](#10-normalization-boundary-payload).

**Provider-neutrality (ratified [§17.4.a](#174-voice-design-provider-abstraction)).**
The bundle never exposes provider fields to callers. Orchestration,
product surfaces, and the SPA ask for the approved voice or the
approved realtime representation — the response is opaque with
respect to which provider designed or hosts it. Provider details
are provenance, not API contract.

### 6.3 What a bundle does not do

The bundle **does not attempt to prove aesthetic identity** in code.
It does not compute a similarity metric between the portrait and
the realtime avatar and reject the bundle if the metric is low.
Aesthetic approval is a human decision recorded on the bundle, not
an automated check.

Model-layer validation on the bundle verifies only:

- Every referenced asset and provider identifier belongs to the
  same workspace as the identity.
- Every referenced asset is in a non-deleted, approved state where
  applicable.
- The bundle is scoped to a single identity version.
- The identity version is in `draft` (bundle under construction) or
  `approved` (bundle in service).

### 6.4 Manual-review boundary

Approval of a bundle is a human decision. Automated tooling may
surface:

- Facial-drift indicators between the bundle's portrait references.
- Color-consistency and lighting-consistency observations across
  the reference set.
- Missing-view warnings if the reference set does not cover the
  framing families it will be used against.
- Artifact-likelihood flags in raw provider output.

None of these signals may auto-approve a bundle. The manual-review
boundary is where the product's most fragile visual promise
(Portrait Language §1) is actually kept.

### 6.5 Bundle versioning

Bundles are immutable once approved. Editing a bundle means creating
a new bundle within (or promoting to) a new identity version. The
prior bundle is preserved for traceability of earlier renders.

### 6.6 Surface availability is declarative (ratified [§17.5.b](#175-reference-kind-enumeration-for-the-first-pass))

**Identity approval and surface availability are separate
concepts.** An identity is approved because it is coherent (its
`required_for_identity` floor is met at `state=approved`). A
surface is available because sufficient references exist to serve
it.

Both are defined **declaratively in the identity branch schema**,
not in transition or bundle code:

- `required_for_identity` — the list of `<kind>/<purpose>` pairs
  that must be present at `state=approved` on the identity
  version for it to promote from `draft` to `approved`. The
  transition service validates against this list. No `<kind>/<purpose>`
  is hardcoded in the service.
- `surface_requirements` — a map from surface name (Home /
  Presence / Studio / Live Conversation / …) to the list of
  `<kind>/<purpose>` pairs required to render on that surface.
  The bundle evaluator computes supported surfaces from this
  map applied to the identity version's approved reference set.

Product surfaces query the bundle for *"do you support surface
X?"* before rendering. Surfaces the bundle does not support fall
back to the Portrait Language §15 preservation-of-trust fallbacks
(still portrait + voice) rather than rendering with missing
references.

The human identity schema (initial `required_for_identity` +
`surface_requirements`) lands under
`docs/design/visual/portrait_qualification/schemas/` when the
fixture-authorship work in [§17.8](#178-fixture-authorship) is
opened.

---

## 7. Asset and reference-view relationships

### 7.1 Why one asset role is not enough

The parent audit proposed a single `Asset.role =
CANONICAL_PORTRAIT_REFERENCE`. That is a necessary but insufficient
step. The reference set carries **meaning** — which view an asset
represents, whether it is a raw provider output or a normalized
output, whether it has been approved into the canonical set or
retained as evidence of a rejected attempt. Collapsing all of that
into one role loses the meaning the benchmark needs to trace.

### 7.2 Typed reference-view relationships

Instead of extending the `Asset.role` enum indefinitely, introduce a
**reference relationship record** that pairs an existing `Asset` with
its identity-relevant meaning. Each record carries:

- The identity version it belongs to.
- The `Asset` it references.
- A **reference kind** (enumerated below).
- A **reference state** (approved / provisional / rejected / raw /
  normalized).
- A generation-record reference when the asset came from a specific
  provider attempt (see [§8](#8-generation-attempt-provenance)).
- Human review notes.

The `Asset` table itself does not need per-kind roles; it continues
to carry the medium (image / audio / clip / transcript / voice) and
whatever ownership metadata already exists. The reference
relationship carries the identity-facing meaning.

### 7.3 Reference kinds and purposes (ratified [§17.5.a](#175-reference-kind-enumeration-for-the-first-pass))

Every reference relationship carries a `kind` (what this artifact
fundamentally is) and a `purpose` (how this artifact participates
in identity). Splitting kind from purpose preserves clean
separation and keeps the substrate branch-neutral while allowing
future artifact classes to appear without collapsing into a
single generic bucket.

**Initial `kind` enumeration (human branch, round one):**

- `portrait_reference` — still portrait imagery. The only kind
  authored in round one.
- `motion_reference` — short identity motion clips *(future).*
- `speech_reference` — lip-sync calibration clips *(future).*
- `body_reference` — full-body or gesture references *(future).*
- `environment_reference` — lighting-calibration references
  *(future).*
- `expression_reference` — reserved for the case where an
  expression genuinely becomes its own artifact class rather
  than a purpose value under `portrait_reference`.

**Initial `purpose` enumeration (human branch, applied to
`portrait_reference` in round one):**

- `front` — approved front-facing canonical portrait.
- `slight_left` — approved off-axis view.
- `slight_right` — the mirror of `slight_left`.
- `neutral_rest` — resting expression baseline (Portrait
  Language §6).
- `listening` — listening-state reference.
- `consideration` — consideration-state reference.
- `gentle_positive` — gentle-positive-response reference.

**Reference identity notation.** A specific reference is written
`<kind>/<purpose>` — for example `portrait_reference/front` or
`portrait_reference/neutral_rest`. This notation is the shared
vocabulary between the substrate, the identity schema's
`required_for_identity` list, and the schema's
`surface_requirements` map.

**Purpose validation.** `purpose` is a structured value validated
server-side by a purpose-schema selected by the parent identity's
`kind`. Adding a purpose value does not require a Django
migration. Invalid purposes fail validation immediately at the
authoritative write path (same discipline as the `spec` blob per
[§17.3.a](#173-persistence-granularity)).

**Non-human `kind` and `purpose` enumerations.** Deferred to
Character Presence Language per
[§17.2.a](#172-non-human-branch-authorship). The substrate accepts
new values without schema restructuring.

**Round-one non-human fixture** may use a manually-authored
minimal purpose-schema clearly labeled non-canonical, per
[§17.2.b](#172-non-human-branch-authorship).

### 7.4 Reference states

- **`raw`** — provider output as received, before normalization.
  Preserved so normalization can be re-run.
- **`normalized`** — output of the normalization layer applied to a
  raw asset plus the identity version.
- **`provisional`** — a normalized asset that has passed automated
  checks and is awaiting human review.
- **`approved`** — a provisional asset that a human reviewer has
  admitted to the canonical set.
- **`rejected`** — an asset (raw, normalized, or provisional) that
  was reviewed and refused. Preserved so the reason is
  discoverable.

### 7.5 Ownership rules

Every asset referenced by a reference-relationship record must
belong to the same workspace as the identity version. Cross-
workspace references are a violation and must be enforced at the
model boundary, not left to serializer discipline.

---

## 8. Generation-attempt provenance

### 8.1 Why provenance is not a JSON field

The parent audit proposed folding provenance into a single JSON
field on the identity. That fails because:

- Multiple generations produce multiple records; one field cannot
  represent them cleanly.
- Retries, approvals, rejections, and supersessions all need
  status; a JSON field turns status into a stringly-typed convention
  every reader has to re-parse.
- Provenance must be queryable: "show me every Stability attempt
  against fixture X in the Softened Photographic direction." A
  JSON field forces that into full scans.
- Benchmark evidence is auditable evidence. It should be structured.

### 8.2 The generation record

Every provider call that produces (or attempts to produce) an
identity-relevant artifact is recorded as a **generation record**.
The record is immutable once written and carries:

- **Identity version** the attempt was made against.
- **Provider** (an enumerated identifier: `runway_avatar`,
  `runway_realtime`, `stability_still`, `elevenlabs_tts`,
  `runway_tts`, and so on).
- **Provider model / version** where the provider distinguishes
  models (Runway `gen4_image` / `gen4_turbo` / voice-design
  version; Stability `SD3` / `Core` / `Ultra`; ElevenLabs voice
  model).
- **Direction hypothesis** — which of the five candidate rendering
  directions this attempt is exploring (Softened Photographic,
  Cinematic Naturalistic, Painterly Naturalistic, Contemporary
  Portrait Illustration, Lightly Stylized Realism, or a benchmark-
  neutral value for identity-only generations).
- **Prompt / specification snapshot** — the exact input the provider
  received, captured at the boundary and versioned. Not the input
  the operator typed; the input the provider was given after
  identity translation.
- **Seed or reproduction data** when the provider exposes it
  (Stability seed values, Runway model version pins where
  available).
- **Input reference assets** — every reference asset the provider
  received as conditioning input.
- **Raw output asset** reference.
- **Normalized output asset** reference (populated once
  normalization runs).
- **Execution mode** — the recorded mode from
  [§9.4](#94-execution-mode-recording). No benchmark evidence
  captured under `forced_mock` may be treated as provider
  evidence.
- **Created time** and **elapsed time**.
- **Approval state** — one of `pending`, `admitted_to_bundle`,
  `rejected`, or `superseded`.
- **Reviewer evidence** — the human reviewer's notes, structured
  where possible (which weighted category from Portrait Territory
  Study §4 the record informs).
- **Failure or rejection reason** — either a provider-side error
  captured verbatim, or the reviewer's rejection rationale, or
  both.

### 8.3 Where generation records live during benchmark

During the benchmark phase, generation records should live in the
repository as versioned files under
`docs/design/visual/portrait_qualification/evidence/…` before any
Django model is built. The reason is captured in
[§17](#17-unresolved-decisions-requiring-operator-resolution): the
evaluation instrument itself must prove which fields reviewers
actually use before those fields calcify into database columns.

The provider-boundary contract in
[§9](#9-provider-boundary-payload) requires the payload to be
recorded, but does not require the recording layer to be a database
row from day one.

---

## 9. Provider-boundary payload

### 9.1 The boundary

Every provider adapter — still-portrait generation, avatar
creation, realtime session creation, TTS synthesis, voice design —
receives its inputs from an **identity-anchored payload** produced
by the calling layer. The payload's shape is the contract; the
adapter's job is to translate the payload into whatever the
provider's API expects.

Without a fixed boundary shape, every adapter grows its own
conventions and identity data leaks or drifts at translation time.

### 9.2 What every payload carries

- **Identity version reference** (never just an identity id — see
  [§5.5](#55-rendering-derives-from-a-specific-version)).
- **Approved reference view set** relevant to the request.
- **Presentation preferences** relevant to the request.
- **Rendering constraints** enforced by the calling layer (framing
  family, prohibited expression treatments, motion tier).
- **Execution mode** requested (see
  [§9.4](#94-execution-mode-recording)).
- **Target surface profile** where applicable — Home, Studio,
  My Team list, Live Conversation, etc. — because framing and
  normalization vary by surface.

### 9.3 Distinct provider operations

Provider abstractions should compose around the identity contract
rather than collapse unrelated lifecycles into one method. Ratified
shape:

- **`PortraitProvider`** (ratified in
  [§17.9.a](#179-provider-adapter-migration-path); new abstraction
  wrapping the existing Stability and Runway still-portrait paths).
  - `generate_static_portrait(payload) -> raw output asset`.
  - `generate_variation(payload, from_reference) -> raw output
    asset`.
  - `regenerate_from_identity(payload, prior_generation_record) ->
    raw output asset`.
  - `inspect_capabilities() -> capability record` (see
    [§9.5](#95-capability-introspection-is-factual)).
- **Realtime-representation authoring** (formerly proposed as
  `AvatarProvider`) — **deferred**. The
  [§17.9.a](#179-provider-adapter-migration-path) ratification
  explicitly declined to ratify a standalone `AvatarProvider`
  Protocol on the basis that "avatar creation" is a legacy
  endpoint term, not a resolved domain boundary. The operation
  may represent several distinct lifecycles (realtime
  representation from an approved identity; portrait enrollment
  with a realtime provider; reusable character identifier
  production; still portrait; motion-capable representation).
  Before any Protocol is named, the canonical identity contract
  must define input, produced artifact, ownership (authoring vs.
  delivery), provider portability, bundle participation, and
  whether the lifecycle belongs under `RealtimeProvider` or a
  distinct representation-authoring abstraction. Temporary
  architectural term for discussion:
  `RealtimeRepresentationProvider`. Not ratified. Not built.
  Question tracked in [§18](#18-explicitly-deferred-fields-and-decisions).
- **`RealtimeProvider`** (existing abstraction, unchanged in scope).
  Realtime session creation belongs here.
- **`TextToSpeechProvider`** (existing abstraction, unchanged in
  scope).
- **`VoiceDesignProvider`** (ratified as its own Protocol in
  [§17.4.a](#174-voice-design-provider-abstraction)).

The point is that **realtime, still, voice design, and TTS have
distinct lifecycles** and should not be collapsed into one
Protocol whose surface hides those distinctions. The former
"avatar" bucket must be resolved before the next Protocol is
named.

### 9.4 Execution-mode recording

Every adapter must accept and honor one of the following execution
modes, and every generation record must record the mode that
produced its output:

- **`forced_mock`** — mock adapter is used regardless of provider
  key availability. For CI, offline development, and reproducible
  fixtures. Output is never benchmark evidence.
- **`auto`** — real provider used if credentials and reachability
  are present; falls back to mock on failure. Falling back must
  record `execution_mode_actual = mock_fallback` on the generation
  record so evidence is never mistaken for real output.
- **`real_required`** — real provider used; fails hard if not
  available. The only mode that produces benchmark-usable evidence.
- **`unavailable`** — declared when the provider is known not to
  serve this request (for example, capability introspection
  reports no support). Records the attempt without executing.

Existing environment flags (`RUNWAY_FORCE_MOCK`,
`VOICEOVER_TTS_FORCE_MOCK`) map onto `forced_mock`. Stability's
current key-presence-only behavior maps onto `auto` but with no
explicit forced-mock switch — that switch needs to exist for
`forced_mock` to be honestly available on the Stability path.

### 9.5 Capability introspection is factual

Every provider adapter exposes `inspect_capabilities()` returning a
record of what the provider **can technically do**. Examples:

- Static generation (yes/no).
- Reference-image conditioning (yes/no; formats accepted).
- Deterministic seed support (yes/no).
- Variation generation from a prior output (yes/no).
- Transparent background support (yes/no).
- Pose control (yes/no; degrees of freedom).
- Lighting control (yes/no; parameters exposed).
- Supported output dimensions.
- Latency class (order-of-magnitude, empirically measured, not
  vendor-claimed).

The capability record **must not** claim territory suitability. A
provider does not "support Cinematic Naturalistic" as a boolean.
Whether a provider serves a rendering direction is benchmark
evidence, produced from real outputs evaluated against Portrait
Territory Study exit criteria, and lives on generation records and
scoring artifacts — not on the provider adapter.

### 9.6 Sequencing note — do not add drift verification prematurely

The R10 protocol-drift verifier in
`media-engine/tests/test_r10_provider_drift.py` is the right
long-term guard. It is the wrong first step: freezing an
untested abstraction is worse than not enforcing it.

Recommended order:

1. Define the `PortraitProvider` contract (this document).
2. Implement one real adapter and one mock adapter behind it.
3. Validate the abstraction with real outputs against real
   fixtures.
4. Finalize the Protocol based on what proved necessary.
5. Extend R10 to cover the finalized Protocol.

Skipping step 3 codifies whatever this document happened to
anticipate, which is not the same as codifying what turned out to
matter.

---

## 10. Normalization-boundary payload

### 10.1 Contract before implementation

Portrait Language §8 requires a "same-room" lighting, tonal, and
shadow discipline across every surface. That requires a
normalization step between raw provider output and surface render.
No such step exists today.

The first implementation of that step may be minimal or partly
manual. The **contract** must be stable regardless.

### 10.2 Input shape

Every call into the normalization layer carries:

- **Identity version reference.**
- **The raw provider output asset.**
- **The originating generation record.**
- **The target surface profile** (Home / Studio / My Team list card /
  My Team detail / Piece Detail byline / Live Conversation / small
  byline).
- **The approved reference set** for the identity version, or the
  provisional reference set if the identity is still in `draft`.
- **The lighting baseline** recorded on the identity version.

### 10.3 Output shape

Every normalization call produces **three artifacts, all
immutable**:

- **Raw Provider Output** asset — the provider's response as
  returned, byte-for-byte preserved. Never overwritten.
- **Normalized Output** asset — the result of the pipeline
  applied to the raw output. A new `Asset` row referenced back
  to the raw asset.
- **Normalization Manifest** — a structured record of exactly
  what the pipeline did. See §10.6.

Plus the following inline fields on the generation-record side:

- **Crop metadata** — the crop and framing profile applied.
- **Eye-line metadata** — where the eye line falls in the
  normalized output for framing-family stability (Portrait
  Language §4).
- **Tonal adjustments** applied *(recorded as `not_applied` in
  round one per [§17.6.a](#176-normalization-scope-for-first-implementation)).*
- **Background treatment** applied — the identifier of the
  background from Portrait Language §18's controlled family.
- **Quality checks** run and their results.
- **Pass / fail result** overall.
- **Detected identity drift** — signals that the normalized
  output differs from the approved reference set beyond
  thresholds, if measurable *(recorded as `not_computed` in
  round one).* Signals only; not an approval decision.

### 10.4 Manual-review boundary preserved

As with the approved representation bundle, no automated identity-
similarity metric approves an asset on its own. Normalization may
flag; it does not admit. Admission to the approved reference set
runs through the reviewer boundary defined in
[§6.4](#64-manual-review-boundary).

### 10.5 Minimal first implementation is acceptable

A first implementation that crops, applies surface-specific
framing, normalizes eye-line, and applies a background from the
controlled family is enough to unblock benchmark evidence. What
it must not do is pretend that "normalization is solved" — the
output record shape must accommodate every field in §10.3 from
day one, even if early runs leave later fields as `not_applied` /
`not_computed`.

Round-one scope and deferrals are locked in
[§17.6.a](#176-normalization-scope-for-first-implementation).

### 10.6 Normalization Manifest (ratified [§17.6.a](#176-normalization-scope-for-first-implementation))

Every normalization pass emits a **Normalization Manifest** — a
deterministic, structured record of exactly what happened. Along
with the raw and normalized artifacts, the manifest is the
third required output of every generation.

**Manifest fields:**

- crop profile used
- framing profile
- background identifier
- eye-line adjustments
- pipeline version (a composition of enabled stage versions)
- normalization stages executed (ordered, with per-stage
  version)
- normalization stages skipped (with reason)
- execution duration
- surface-profile identifier consumed

**Determinism constraint (load-bearing):**

Normalization must be **deterministic**. Given identical raw
asset + identical pipeline version + identical manifest, the
resulting normalized artifact must be **byte-for-byte
identical**. Normalization must never introduce randomness. If
randomness exists, provider comparisons become impossible —
reviewers cannot distinguish provider variation from pipeline
variation.

**Reproducibility guarantee:**

Future pipeline revisions can regenerate the normalized artifact
from the raw asset plus the manifest. The raw asset remains the
canonical evidence; the normalized artifact is one interpretation
of it. Losing the raw asset loses the ability to re-interpret
evidence against a better pipeline later.

### 10.7 Stage architecture (ratified [§17.6.a](#176-normalization-scope-for-first-implementation))

The pipeline is composed of **ordered, independently
enable/disable/versioned stages**:

1. crop
2. framing
3. eye-line normalization
4. background replacement
5. tonal normalization *(round-one deferred)*
6. lighting normalization *(round-one deferred)*
7. shadow normalization *(round-one deferred)*

Each stage carries its own version identifier. The pipeline
version recorded on the manifest is a composition of the enabled
stages' versions. Adding a stage, enabling a previously deferred
stage, or bumping a stage's version produces a new pipeline
version — all prior normalized artifacts remain valid evidence
of what the earlier pipeline version produced.

This architecture allows future benchmark rounds to answer
questions like *"did lighting normalization actually improve
reviewer trust?"* by comparing scores across pipeline versions
without rebuilding the pipeline from scratch.

### 10.8 Surface profiles are data (ratified [§17.6.a](#176-normalization-scope-for-first-implementation))

Surface profiles — **Compact, Presence, Studio, Conversation,
Team Card** (initial set) — are declarative configuration, not
embedded layout logic. Each profile defines:

- crop ratios
- eye position
- margins
- output resolution
- framing behavior

The pipeline consumes a profile at normalization time. Adding a
new surface or adjusting a profile's parameters is a
configuration change, not a code change — same declarative
discipline as
[§17.5.b](#175-reference-kind-enumeration-for-the-first-pass)'s
`surface_requirements`.

Surface profiles live under
`docs/design/visual/portrait_qualification/schemas/` alongside
the identity branch schema. Both are versioned and referenced by
manifest, generation record, and bundle capability computation.

### 10.9 Production vs. benchmark policy

Retention policy differs by mode:

- **Benchmark:** preserve raw + normalized + manifest for every
  generation. Every artifact is evidence.
- **Production:** may cache only the normalized asset for
  serving while retaining the raw asset for provenance and
  future regeneration.

This is a deployment policy choice, not a pipeline limitation.
The pipeline always produces all three artifacts; the retention
layer decides how long each is held. Round-one operates in
benchmark mode across the board.

---

## 11. Voice and realtime representation linkage

### 11.1 What is being linked

An approved representation bundle (see
[§6](#6-approved-representation-bundle)) binds:

- The approved reference view set (via reference relationships).
- The approved voice.
- The approved realtime representation.
- The applicable normalization profile.

**Voice** is a **canonical voice reference** owned by the
identity. Provider-side details (which provider designed it,
provider-side identifier, seed, reference audio) live on the
voice reference's own provenance record. Callers ask the bundle
for the approved voice and receive an opaque canonical reference;
they never receive or branch on a provider-specific identifier.

**Realtime representation** is a **canonical realtime reference**
owned by the identity. The avatar identifier that participates
in a WebRTC session (today, a Runway `avatar_id`) lives inside
the realtime reference's provenance record — not on the bundle,
not on `Spokesperson` (soon `Teammate` per
[§17.1.b](#171-naming)), not on the identity itself. Product
surfaces launch a realtime session by dereferencing the bundle
through the provider-abstraction layer, which internally resolves
to the provider-side identifier only at the adapter boundary.

**Ratified in [§17.4.a](#174-voice-design-provider-abstraction).**
Provider-neutrality at the bundle boundary is a load-bearing
architectural requirement. Nothing outside the adapter layer may
contain provider-specific assumptions.

### 11.2 Linkage is by workspace-scoped reference, not by embedding

The identity does not store the voice or the avatar; it stores a
verified reference to them. The verification runs at
representation-bundle time:

- The voice id belongs to the identity's workspace.
- The voice id is in a valid state upstream (not deleted).
- The realtime avatar id belongs to the identity's workspace.
- The realtime avatar id is in a rendering-ready state upstream.

Failed verification blocks bundle approval. This is the model-
level check the parent audit proposed as a `clean()` on
`Spokesperson`; moving it onto the bundle keeps the identity itself
free of aesthetic-identity assertions the model layer cannot honestly
make.

### 11.3 Rebinding

A voice change, a realtime avatar rebake, or a normalization profile
change requires a new bundle. If the change is significant enough to
invalidate the approved reference set, it also requires a new
identity version (see
[§5.4](#54-what-triggers-a-new-version)). Whether an operator update
crosses that threshold is a review-time decision, not an automated
one.

---

## 12. Workspace and ownership rules

Every record introduced by this contract is workspace-scoped by
inheritance from the identity's workspace:

- `CharacterIdentity.workspace` (required, set at creation).
- Every identity version belongs to one identity and inherits its
  workspace.
- Every approved representation bundle belongs to one identity
  version and inherits its workspace.
- Every reference relationship record belongs to one identity
  version and inherits its workspace. The referenced `Asset` must
  belong to the same workspace (see
  [§7.5](#75-ownership-rules)).
- Every generation record belongs to one identity version and
  inherits its workspace. Every referenced input asset and every
  produced output asset must belong to the same workspace.

Cross-workspace references are enforced as model-boundary
violations (matching the R1 pattern for `RealtimeSession`).

Deleting a workspace cascades identity, versions, bundles,
reference relationships, and generation records. Assets follow the
existing workspace-deletion policy — this contract does not change
it.

---

## 13. Bootstrap flow for the first canonical references

### 13.1 The bootstrap problem

Consistency-under-regeneration testing requires an approved reference
set to regenerate against. The first approved reference set has to
come from somewhere. It cannot come from prior approved output
because there is no prior approved output on day one.

The bootstrap flow is therefore:

1. **Authored identity specification.** An operator authors the
   identity spec for a fixture (see [§14.4](#144-fixture-set)) —
   the human-readable identity facts, presentation preferences,
   and lighting baseline. This lands as a draft identity version.
2. **Initial multi-provider generation.** Each provider adapter,
   in `real_required` mode, produces a batch of candidate portraits
   for the fixture across the reference kinds the human branch
   defines (front, slight-left, slight-right, expression baselines).
3. **Human selection.** The reviewer boundary selects, per reference
   kind, the candidate that best represents the identity as
   authored. Rejected candidates are preserved as rejected
   generation records.
4. **Canonical reference approval.** Selected candidates are
   normalized and promoted to `approved` reference relationships on
   the draft identity version.
5. **Bundle approval.** With the approved reference set in place, a
   voice and a realtime representation are bound and reviewed. On
   approval, the identity version transitions from `draft` to
   `approved` and the bundle becomes the current approved bundle.
6. **Regeneration benchmark.** With an approved reference set in
   place, `regenerate_from_identity` calls now have something to
   regenerate against. Consistency-under-regeneration testing
   (Portrait Territory Study §3.7) becomes possible.

### 13.2 Bootstrap is fixture-first, not customer-first

The bootstrap flow above runs against benchmark identity fixtures
(see [§14.4](#144-fixture-set)), not against real customer
teammates. Customer teammates continue to render through the
existing `Spokesperson` path during benchmark. Only after Portrait
Territory Study V2 selects a direction and the identity contract
proves stable does the flow move onto real customer teammates —
that migration is out of scope for this document.

### 13.3 Fixture directory semantics (ratified [§17.8.a](#178-fixture-authorship))

The bootstrap flow lands artifacts under the ratified fixture
directory layout, which separates authored identity from
generated evidence:

- Steps 1–2 of §13.1 produce `identity.yaml` and `rationale.md`.
  A fixture is **authorable** at this point.
- Steps 3–5 produce candidate outputs under
  `runs/<bootstrap_run_id>/…`. Human review selects from these
  candidates.
- Selected candidates are copied or linked from `runs/…` into
  `bootstrap/references/`. A fixture becomes **qualification-
  ready** once `bootstrap/references/` is populated with the
  approved set.
- Step 6 (regeneration benchmark) writes evidence under
  `runs/<round_one_run_id>/…`, using `bootstrap/references/` as
  the identity anchor.

Full directory layout is enumerated in
[§17.8.a](#178-fixture-authorship). Every benchmark run lives
under its own `benchmark_run_id` subtree; later rounds never
overwrite earlier evidence.

---

## 14. Benchmark scope guardrails

### 14.1 Wizard changes are not pre-benchmark work

The parent audit noted the current wizard collects 7 of the 11
Portrait Language concepts. That gap is real but not urgent.
Provider qualification must not be blocked on customer-onboarding
redesign, and the redesigned onboarding must not be authored before
the benchmark tells the design team which inputs actually matter.

Wizard changes happen only after:

- Portrait Territory Study V2 selects a rendering territory.
- The identity contract proves which fields the selected territory
  requires as customer input versus which are pre-authored, defaulted,
  or derived.

Until then, the wizard is unchanged and the benchmark runs against
fixtures.

### 14.2 Evaluation instrument stays repository-first (ratified [§17.7.a](#177-evaluation-instrument-shape))

The Portrait Territory Study §4 weighted evaluation categories
(Critical, Important, Nice-to-have) must be recorded reproducibly.
Do not create a production Django model for scoring on day one.

**The scoring schema is a contract, not merely a document.**
Under `docs/design/visual/portrait_qualification/scoring/`:

- `SCORING_SCHEMA_V1.md` — human-readable explanation of every
  scoring field and how weighted categories map.
- `scoring.schema.json` — machine-validatable JSON Schema.
  Reviewer records that fail validation are rejected at intake.
- `scoring-template.yaml` — canonical reviewer template. Every
  new scoring record starts from this template.

**Every scoring record includes immutable metadata**
recorded once at record creation: benchmark round, scoring
schema version, pipeline version (from the §10.6 manifest),
normalization version, fixture version, provider, rendering
direction, execution mode (from §9.4), reviewer, timestamp.
This preserves comparability across future rounds even after
the pipeline, schema, or fixtures evolve.

**Evidence is append-only.** Reviewer scores never overwrite
previous reviews. Amendments append with a recorded reason.
This applies to all evidence types — scores, observations,
disagreement notes.

**Reviewer discipline (per [§17.7.b](#177-evaluation-instrument-shape)):**
Chris is the sole scoring reviewer for round one. Claude
provides structured observations (their own record type in the
schema — `observation`, not `score`). Operator-vs-observation
disagreements are recorded, not resolved. External review is
engaged only at final territory selection.

A Django model may follow only when the benchmark workflow has
proven:

- Which scoring fields reviewers actually use.
- Which evidence needs to be queryable across many rows.
- Whether multiple reviewers per fixture is the norm or the
  exception.
- How reviewer disagreements are resolved *(round one records
  disagreements as evidence; a Django model must not silently
  pick a resolution strategy the workflow has not authorized).*
- Which artifacts are permanent product data (identity, approved
  bundles) versus temporary research evidence (rejected attempts
  from a discarded direction).

### 14.3 Manual review is the final gate

No automated identity-similarity metric approves a teammate on its
own. Automated signals may accompany the reviewer boundary but do
not replace it. Portrait Language §16 makes provider qualification a
validation exercise; validation is a human act on evidence, not a
metric threshold.

### 14.4 Fixture set (ratified [§17.8.a](#178-fixture-authorship))

Benchmark against a **fixed set of identity fixtures**, not against
"Alex" alone. Portrait Territory Study §3.8 requires demographic
robustness across varied age, skin tone, facial structure, hair
texture, gender presentation, cultural presentation, asymmetry,
teeth, and visible disability where deliberately selected.

**Round-one fixture set (canonical, five fixtures):**

- `fixture_h1` — straightforward human baseline
- `fixture_h2` — facial-hair coverage (mouth + hair identity-
  critical region compounds around facial-hair rendering)
- `fixture_h3` — deliberately difficult identity case (chosen
  to expose provider drift, not by accident)
- `fixture_h4` — demographic and feature contrast (skin tone,
  hair texture, gender presentation deliberately varied from
  the earlier fixtures)
- `fixture_nh1` — non-human substrate exercise, unscored
  aesthetically per [§17.2.b](#172-non-human-branch-authorship)

**Adaptive expansion:** allowed only when documented evidence
identifies a specific blind spot. Do not add fixtures merely to
make the set feel comprehensive.

**Same-payload rule:** every provider and rendering direction
receives the **same versioned fixture payload**. A fixture tuned
per provider is not a fixture; cross-provider comparison
requires identical inputs.

**Directory layout** for each fixture is ratified in
[§17.8.a Amendment 1](#178-fixture-authorship): fixture
definition, bootstrap references, and per-run evidence are
separated so later benchmark rounds cannot overwrite or confuse
earlier evidence. Full layout in the ratification block.

**Naming rule:** branch-prefixed coded identifiers only
(`fixture_h1`, `fixture_nh1`). Numbering reflects authorship
sequence, never quality or priority. Personal names are
prohibited as identifiers. Full rules in
[§17.8.b](#178-fixture-authorship).

Exact fixture authorship, prerequisite artifacts, and the
authoring guide are enumerated in
[§17.8.a](#178-fixture-authorship). Fixture authorship is the
last blocking piece before benchmark round one can open.

---

## 15. Proposed persistence shape

> **Illustrative only.** No migrations. No production code. Field
> names are drawn from Portrait Language and this contract but are
> not committed to. The point of this section is to show that the
> contract can be persisted at reasonable schema cost — not to
> prescribe columns.

### 15.1 Substrate

```
CharacterIdentity
  id                              uuid, pk
  workspace                       fk, required, workspace-scoped
  spokesperson                    fk, nullable during bootstrap
  kind                            enum { human, non_human }
  name                            string (internal / operator-facing)
  created_at                      timestamp
  archived_at                     timestamp, nullable
```

`spokesperson` is nullable during the benchmark phase because
identity fixtures may exist without an owning `Spokesperson` row.
In production, non-null for every customer teammate.

### 15.2 Versioning

```
CharacterIdentityVersion
  id                              uuid, pk
  identity                        fk -> CharacterIdentity
  revision                        integer, monotonic within identity
  state                           enum { draft, approved, superseded, rejected }
  spec                            structured document, schema per kind
  created_at                      timestamp
  approved_at                     timestamp, nullable
  superseded_at                   timestamp, nullable
  reviewer_notes                  text, nullable
  unique(identity, revision)
```

Exactly one version per identity is in `approved` state at a time.
Enforced via a Postgres partial unique constraint
(`UNIQUE (character_identity_id) WHERE state = 'approved'`) plus an
application-level transition service — ratified in
[§17.3.b](#173-persistence-granularity).

`spec` is a JSONB column carrying a structured document validated
server-side against the schema selected by the parent identity's
`kind` — ratified in [§17.3.a](#173-persistence-granularity).
Every payload carries an explicit `spec_schema_version`; all
writes go through an authoritative service, not through
`Model.save()` overrides.

### 15.3 Approved representation bundle

**Ratified [§17.4.a](#174-voice-design-provider-abstraction):**
the bundle is provider-neutral. Provider fields do not live on the
bundle; they live on separate canonical voice / realtime reference
records that carry their own provenance.

```
ApprovedRepresentationBundle
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  approved_voice                  fk -> CanonicalVoiceReference
  approved_realtime               fk -> CanonicalRealtimeReference
  normalization_profile           fk -> NormalizationProfile
  state                           enum { draft, approved, superseded }
  approved_at                     timestamp, nullable
  approved_by                     fk -> User, nullable
  reviewer_notes                  text, nullable

CanonicalVoiceReference
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  generation_record               fk -> GenerationRecord
  # provider details live inside the generation_record:
  #   provider, provider_model, provider_id, seed, reference audio, ...
  state                           enum { raw, provisional, approved, rejected }
  approved_at                     timestamp, nullable
  reviewer_notes                  text, nullable

CanonicalRealtimeReference
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  generation_record               fk -> GenerationRecord
  # provider details live inside the generation_record:
  #   provider, provider_model, provider_id, avatar-creation params, ...
  state                           enum { raw, provisional, approved, rejected }
  approved_at                     timestamp, nullable
  reviewer_notes                  text, nullable
```

Approved reference-view assets (portrait references) are attached
via `IdentityReference` records (§15.4), not embedded here.

Callers dereference the bundle by asking for `approved_voice` and
`approved_realtime` and receive canonical references. Provider
resolution happens only at the adapter boundary, using the
provenance recorded on each reference's linked `GenerationRecord`.
Nothing outside the adapter layer sees a provider-specific
identifier.

The exact class names above (`CanonicalVoiceReference`,
`CanonicalRealtimeReference`) are illustrative. The load-bearing
shape is: bundle references a canonical asset; provider provenance
lives on the asset's generation record; the bundle field is opaque
to callers.

### 15.4 Reference relationships

```
IdentityReference
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  asset                           fk -> Asset
  kind                            enum (artifact class, per §7.3)
  purpose                         structured value validated by
                                  branch-specific purpose schema
                                  (per §7.3 and §17.5.a)
  state                           enum { raw, normalized, provisional, approved, rejected }
  generation_record               fk -> GenerationRecord, nullable
  reviewer_notes                  text, nullable
  created_at                      timestamp

# Reference identity is (kind, purpose) — written as
# <kind>/<purpose>, e.g. portrait_reference/front.
# purpose validation is served by a purpose-schema selected on the
# parent identity's kind. Adding purpose values does not require a
# Django migration; invalid purposes fail at the authoritative
# write path.
```

### 15.5 Generation record

```
GenerationRecord
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  provider                        enum
  provider_model                  string
  direction_hypothesis            enum (five candidate directions plus 'identity_only')
  prompt_snapshot                 structured document
  seed_or_reproduction_data       structured document, nullable
  input_reference_assets          m2m -> Asset (through side table)
  raw_output_asset                fk -> Asset, nullable
  normalized_output_asset         fk -> Asset, nullable
  execution_mode                  enum { forced_mock, auto, real_required, unavailable }, nullable
  execution_mode_actual           enum { real, mock, mock_fallback }, nullable
  # Both fields NULL iff no provider execution ever went through
  # the framework for this row (currently: legacy imports).
  # Both non-NULL for every executable provider record. Half-null
  # is refused. See §17.10.a Amendment 3.
  created_at                      timestamp
  elapsed_ms                      integer, nullable
  approval_state                  enum { pending, admitted_to_bundle, rejected, superseded }
  reviewer_notes                  structured document
  failure_reason                  text, nullable
```

Immutable once written. Reviewer notes may be appended via child
records if history is needed; the parent record is not edited.

### 15.6 Normalization records (ratified [§17.6.a](#176-normalization-scope-for-first-implementation))

The earlier draft's single `NormalizationProfile` table split into
three concepts once the ratified pipeline discipline landed:

**SurfaceProfile — declarative configuration (data, not a
per-identity DB row):**

```
# lives under docs/design/visual/portrait_qualification/schemas/
# Not a Django table. Loaded at pipeline time.

SurfaceProfile (per surface: Compact / Presence / Studio /
                              Conversation / Team Card / …)
  id                              stable string identifier
  version                         integer
  crop_ratios                     structured document
  eye_position                    structured document
  margins                         structured document
  output_resolution               structured document
  framing_behavior                structured document
```

**NormalizationManifest — one immutable record per generation:**

```
NormalizationManifest
  id                              uuid, pk
  generation_record               fk -> GenerationRecord
  raw_output_asset                fk -> Asset  (byte-for-byte
                                                preserved)
  normalized_output_asset         fk -> Asset  (deterministic
                                                output of the
                                                pipeline)
  pipeline_version                string (composition of enabled
                                          stage versions)
  surface_profile_id              string  (SurfaceProfile id)
  surface_profile_version         integer
  background_id                   string  (from Portrait Language
                                           §18 controlled family)
  stages_executed                 structured document (ordered,
                                                       per-stage
                                                       version)
  stages_skipped                  structured document (with reason
                                                      per stage)
  eye_line_adjustments            structured document
  crop_metadata                   structured document
  execution_duration_ms           integer
  created_at                      timestamp

# Immutable once written. Determinism constraint (§10.6): given
# the same raw asset + pipeline version + manifest, the
# normalized asset must be byte-for-byte identical.
```

**Per-identity NormalizationProfile — optional overrides
(deferred; may not exist in round one):**

```
# Optional. Only exists when an identity needs per-surface
# overrides on top of the shared SurfaceProfile data.
# Round one does not require this table; it may be introduced
# later if benchmark evidence shows per-identity tuning is
# needed. Kept in the illustrative shape as a placeholder.

NormalizationProfile (optional, deferred)
  id                              uuid, pk
  identity_version                fk -> CharacterIdentityVersion
  surface_profile_id              string  (SurfaceProfile id
                                           being overridden)
  overrides                       structured document
  created_at                      timestamp
```

**Retention policy:** in benchmark mode all three artifacts (raw,
normalized, manifest) are retained. Production mode may cache
only the normalized asset while retaining raw for provenance —
policy choice, not a pipeline change (see §10.9).

### 15.7 Compatibility mirrors on `Teammate` (ratified [§17.10.a](#1710-existing-spokesperson-field-disposition))

During the benchmark and migration window, three legacy fields
remain on the (renamed) `Teammate` model as **temporary
compatibility mirrors**:

- `Teammate.runway_avatar_id`
- `Teammate.portrait_path`
- `Teammate.voice_id`

**These are not identity state.** They are a one-way mirror of
the canonical substrate:

- The canonical identity substrate is the sole write authority.
- The substrate's write path updates the mirrors in the same
  transaction whenever the approved representation changes.
- Nothing writes the mirrors independently.
- Synchronization direction is canonical → mirror only. Never
  the reverse.
- A missing canonical value produces `null` on the mirror.
  Stale mirror values are never preserved past a canonical
  removal.

A compatibility-consistency verifier asserts mirror ↔ canonical
equality across every `Teammate`. Drift fails tests and appears
in audit tooling. The mirrors and the mirror-write logic are
removed in a dedicated cleanup migration once the §17.10.a exit
conditions all hold. Full sequence and exit conditions in the
§17.10.a ratification block.

### 15.8 What this shape deliberately does not add

- No `identity_hash` or aesthetic-similarity fingerprint field. The
  contract does not attempt to prove identity via a hash.
- No `provenance_json` field on the identity. Provenance lives on
  generation records.
- No `voice_face_compatible` boolean on the identity. Compatibility
  lives on the bundle as a reviewed decision.
- No universal facial columns (`face_geometry`, `skin_tone`,
  `eye_shape`) on `CharacterIdentity`. Human-only fields live in
  the human `spec` schema, not on the substrate.

---

## 16. Architecture and lifecycle diagrams

### 16.1 Substrate relationships (static shape)

```
                       Workspace
                          │
                          │ (1..N)
                          ▼
                   CharacterIdentity
                     │  kind: human | non_human
                     │
                     │ (1..N)
                     ▼
           CharacterIdentityVersion
                     │  state: draft | approved | superseded | rejected
                     │  spec (per-kind schema)
                     │
       ┌─────────────┼─────────────────────┬─────────────────────┐
       │             │                     │                     │
       ▼             ▼                     ▼                     ▼
IdentityReference  ApprovedRepresentation  GenerationRecord   NormalizationProfile
       │             Bundle                      │                (per surface)
       │               │                         │
       ▼               ▼                         ▼
     Asset       (voice id + realtime id      (raw + normalized
                 + normalization profile       output assets,
                 + approved ref set via        reviewer evidence)
                 IdentityReference records)

All records inherit workspace from CharacterIdentity.workspace.
Every Asset referenced belongs to the same workspace.
```

### 16.2 Identity lifecycle

```
                    (operator authors spec)
                              │
                              ▼
                       ┌──────────────┐
                       │    draft     │
                       └──────┬───────┘
                              │
                              │  reviewer boundary
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
         ┌─────────────┐             ┌─────────────┐
         │  rejected   │             │  approved   │
         └─────────────┘             └──────┬──────┘
                                            │
                                            │  spec change
                                            │  (canonical fact update)
                                            │
                                            ▼
                                     new draft version
                                            │
                                            │  reviewer boundary
                                            │
                                            ▼
                                    approved → previous
                                    approved becomes
                                    superseded
```

### 16.3 Bootstrap flow (fixture → first approved bundle)

```
authored spec (draft version)
          │
          ▼
initial multi-provider generation
   (real_required mode across every provider adapter)
          │
          ▼
raw outputs recorded as generation records
   (approval_state: pending)
          │
          ▼
normalization applied to raw outputs
   (normalized output assets recorded)
          │
          ▼
reviewer selects per reference kind
   (front / slight_left / slight_right / expressions)
          │
          ├─→ selected → provisional → approved reference relationship
          │
          └─→ not selected → rejected reference relationship
                             (retained as evidence)
          │
          ▼
voice binding + realtime avatar binding reviewed
          │
          ▼
approved representation bundle
          │
          ▼
identity version: draft → approved
          │
          ▼
regenerate_from_identity now has an anchor
   (Portrait Territory Study §3.7 becomes testable)
```

### 16.4 Provider-boundary flow (single generation)

```
caller (benchmark harness or product surface)
          │
          │  identity version + surface profile + reference kind
          ▼
identity-anchored payload builder
          │  attaches: approved reference set,
          │            presentation preferences,
          │            rendering constraints,
          │            execution mode
          ▼
provider adapter (PortraitProvider / AvatarProvider / etc.)
          │
          │  translates payload → provider API call
          ▼
provider (Stability / Runway / ElevenLabs / …)
          │
          │  returns raw output
          ▼
generation record written (immutable)
          │
          ▼
normalization layer
          │
          │  applies profile, records derived values
          ▼
normalized output asset + normalization output record
          │
          ▼
reviewer boundary → provisional → approved (or rejected)
          │
          ▼
if admitted: reference relationship updated / added to bundle
```

---

## 17. Unresolved decisions requiring operator resolution

Every item below is a decision the contract deliberately does not
make. Each should be resolved before implementation begins so the
resolution is a first-class ratification event, not a discovered
default.

### 17.1 Naming

- **17.1.a** Ratify **`CharacterIdentity`** as the identity substrate
  name (see [§2.2](#22-recommendation)), or select an alternative.
- **17.1.b** Independently decide whether `Spokesperson` is to be
  renamed to `Teammate` (the redesigned customer-facing term). The
  identity contract is neutral to this decision; the operator
  should not discover the naming conflict at migration time.

#### RATIFIED 2026-08-06 — 17.1.a

**Accepted:** `CharacterIdentity` as the internal substrate name.
Customer-facing language remains **teammate**.

Downstream naming discipline (avoid unnecessary repetition where
context is already clear):

- `CharacterIdentity`
- `CharacterIdentityVersion`
- `IdentityReference` *(replaces the working name
  `IdentityReferenceRelationship` used elsewhere in earlier drafts
  of this document; the substrate concept — a typed relationship
  between an `Asset` and an identity version — is unchanged)*
- `ApprovedRepresentationBundle`
- `GenerationRecord`
- `NormalizationProfile`

**Additional constraint:** `CharacterIdentity` must not determine
customer-facing API path or URL vocabulary yet. The URL question is
deferred to when the first API surface is actually exposed; the
substrate name does not force the URL.

#### RATIFIED 2026-08-06 — 17.1.b

**Accepted:** rename `Spokesperson` → `Teammate` as a focused
pre-substrate refactor session, separate from identity-schema
implementation.

Constraints on the rename session:

- Rename the active domain model and forward-looking code from
  `Spokesperson` to `Teammate`.
- Preserve historical handoffs and records as originally written.
- Do not combine the rename with substantive identity-schema
  changes.
- Preserve database data and relationships through explicit rename
  migrations.
- Prefer preserving the existing database table initially if
  changing it adds unnecessary migration risk; the Python / domain
  name is the load-bearing correction.
- Keep `/api/spokespeople/` temporarily as a compatibility route
  if changing it would force a broad coordinated frontend
  migration.
- Introduce `/api/teammates/` deliberately, with a documented
  deprecation path for the legacy route.
- Update active tests, serializers, services, admin, permissions,
  SPA code, current documentation, and repository guidance.
- Do not use broad blind replacements that could alter historical
  text, provider terminology, or unrelated uses of "spokesperson."
- Run the full backend and frontend suites before the rename is
  considered complete.

**Sequence lock (records the operator's ratified ordering):**

1. Complete and verify the focused `Spokesperson` → `Teammate`
   refactor.
2. Update this contract's forward-looking references from
   `spokesperson` to `teammate` (illustrative schema in
   [§15.1](#151-substrate) currently reads `spokesperson fk`; that
   line updates as sequence step 2, after the code rename lands).
3. Proceed with the ratified `CharacterIdentity` substrate design.
4. Keep customer-facing copy on `teammate` and internal identity
   terminology on `CharacterIdentity`.

**Deliberately not preempted in this contract edit:** the
`spokesperson fk` reference in [§15.1](#151-substrate) and any
other `spokesperson` mention in illustrative material remain
unchanged until sequence step 2, so the contract does not silently
get ahead of the code refactor.

### 17.2 Non-human branch authorship

- **17.2.a** Confirm that the non-human spec schema is authored
  alongside the future Character Presence Language and not in this
  contract. This document commits only to the branch discriminator
  and the workspace scoping.
- **17.2.b** Decide whether the first fixture set includes a
  non-human teammate for benchmark round one, or whether non-human
  benchmark is deferred to a later round with the human branch
  benchmarking first alone.

#### RATIFIED 2026-08-06 — 17.2.a

**Accepted:** ownership of the non-human spec schema is
permanently held by the future Character Presence Language, not
by this contract.

**Wording clarification:** "permanent deferral" refers to
**ownership**, not to the immutability of this document. When
Character Presence Language is approved, this contract may
receive a compatibility amendment documenting the new schema and
the references it introduces, but this contract must not become
the source of truth for non-human visual rules.

**Cross-branch substrate requirements this contract permanently
locks (apply to both `human` and `non_human`):**

- `CharacterIdentity.kind` supports `human` and `non_human`.
- Both branches are workspace-scoped.
- Both support identity versioning.
- Both support approved references, generation records,
  representation bundles, voice linkage, provenance, fallbacks,
  and provider boundaries.
- Branch-specific specifications are validated by their own
  schemas.
- Human identity uses the Portrait Language contract.
- Non-human identity will use the future Character Presence
  Language contract.

**Prohibition:** do not invent a provisional non-human appearance
schema inside this contract.

#### RATIFIED 2026-08-06 — 17.2.b

**Accepted:** one non-human fixture in benchmark round one, for
**substrate-exercise purposes only.** It must not influence human
portrait-territory selection.

**The non-human fixture validates only:**

- Branch discrimination and schema routing.
- Workspace ownership and isolation.
- Identity-version lifecycle.
- Generation-record compatibility.
- Approved-reference relationships.
- Provider-boundary handling.
- Normalization-boundary handling where applicable.
- Representation-bundle compatibility.
- Graceful handling of fields that are human-only.
- Absence of hidden assumptions about faces, outfits, skin, eye
  lines, or human anatomy.

**Evidence-format constraint:** aesthetic dimensions on the
non-human fixture must be marked

```
not_applicable_unscored
```

Do not leave them blank, assign zeroes, or include them in
aggregate calculations. The scoring schema (see
[§17.7](#177-evaluation-instrument-shape)) must support this
marker as a first-class value.

**Additional constraints on the round-one non-human fixture:**

- Do not create placeholder non-human reference kinds merely to
  make the fixture pass unless a genuinely branch-neutral kind
  is already justified.
- Prefer branch-neutral relationship concepts such as
  `canonical_reference` with structured purpose metadata over
  prematurely naming non-human-specific reference kinds. This
  preference informs the ratification of
  [§17.5](#175-reference-kind-enumeration-for-the-first-pass)
  and does not preempt it.
- The fixture may use a manually-authored **minimal test schema**
  specifically for contract validation. That schema must be
  clearly labeled non-canonical and must not become the future
  Character Presence Language by accident.
- Provider failures caused by unsupported non-human inputs must
  be recorded as **capability evidence**, not treated
  automatically as identity-substrate failures.
- No conclusions about the correct non-human rendering territory
  may be drawn from this round.

### 17.3 Persistence granularity

- **17.3.a** Choose between a JSONB `spec` column with server-side
  schema validation versus a discriminated per-branch table
  (`HumanCharacterSpec`, `NonHumanCharacterSpec`). Trade-offs:
  JSONB is faster to iterate, harder to query typed; discriminated
  tables are the reverse.
- **17.3.b** Choose between enforcing "at most one approved version
  per identity" via a partial unique index versus an application-
  level invariant. Partial indexes require Postgres; application
  invariants require careful transactional handling.

#### RATIFIED 2026-08-06 — 17.3.a

**Accepted:** JSONB `spec` column on `CharacterIdentityVersion`,
validated server-side using a schema selected by
`CharacterIdentity.kind`.

**Requirements:**

- Every stored payload must include an explicit
  `spec_schema_version`.
- Validation must occur through **one authoritative write path**.
  Direct unvalidated writes to `spec` are not permitted.
- The validated schema — not the database blob — is the source
  of truth for allowed structure.
- Human and non-human branches use **separate validators**.
- Adding the future non-human schema must not require
  restructuring the identity tables.
- Do not add speculative typed columns solely to make the data
  easier to inspect in Django admin.
- Add targeted Postgres expression or GIN indexes **only when a
  proven query requires them**. No premature indexing.
- Old schema versions must remain readable.
- Schema upgrades must use an explicit migration strategy. Do not
  silently reinterpret old payloads as the newest schema.
- Provider-specific values, generation evidence, normalized
  outputs, and approval history must remain **outside** `spec`.
  Those concerns live on `GenerationRecord`, on the normalized
  output record, and on the version's state / approval fields —
  never inside the identity spec blob.

**Correction to the recommendation's write-path proposal:**

Do not rely primarily on overriding `Model.save()` for
validation. That path can be bypassed by bulk operations and
tends to mix persistence with domain behavior.

**Authoritative write-path stack (in order of authority):**

1. **Typed schema validation.** The validator selected by `kind`
   is the first gate. No payload reaches persistence unvalidated.
2. **A dedicated identity-version service (or command) for
   creation and mutation.** The service is the authoritative
   caller. All create / update operations on identity versions
   route through it.
3. **Model-level defensive validation** where practical (for
   example, a `full_clean()`-style call inside the service, or a
   pre-save signal that re-runs the validator as belt-and-
   suspenders).
4. **Tests proving unsupported write paths cannot introduce
   invalid payloads.** Explicit tests that attempt direct ORM
   writes, `bulk_create`, `bulk_update`, and admin-form paths
   with malformed payloads — and confirm each is rejected or
   blocked.

The **service layer is authoritative**; model validation is an
additional guard.

#### RATIFIED 2026-08-06 — 17.3.b

**Accepted both:**

- A Postgres **partial unique constraint** enforcing at most one
  approved version per `CharacterIdentity`.
- An **application-level transition service** that performs
  state changes transactionally and returns domain-specific
  errors.

The database is the final invariant. The service is the
authoritative caller.

**Constraint semantics:**

```sql
UNIQUE (character_identity_id) WHERE state = 'approved'
```

Use a **stable, explicit constraint name** (recommended:
`one_approved_version_per_character_identity`). The name appears
in migration output and in domain-exception mapping, so
stability matters.

**Transition-service requirements:**

- Lock the parent `CharacterIdentity` row with
  `select_for_update()` before reading current state.
- Validate the requested state transition (only permitted state
  transitions from §5.2 are allowed).
- Supersede the currently approved version and approve the new
  version within **one `transaction.atomic()` block**.
- Be **idempotent** when asked to approve the already-approved
  version.
- Reject approval of an invalid, incomplete, or unqualified
  version **before** touching the current approved version.
- Avoid temporarily leaving the identity without an approved
  version if the second transition fails. Ordering and atomicity
  handle this: the supersede + approve must succeed as one
  transaction or roll back as one.
- Convert constraint violations into a **stable domain
  exception** (recommended: `IdentityVersionApprovalError` with
  a discriminating `.code` field).
- Record **who or what approved the version and when**. Approval
  metadata is a first-class field on the version, not a log
  entry.
- **Never use `bulk_update()` for approval transitions.**

**Postgres-backed integration tests required:**

- Concurrent approval attempts against the same identity.
- Re-approving the current version (idempotency check).
- Replacing an approved version (supersede + approve one round-
  trip).
- Transaction rollback during replacement (partial failure must
  not corrupt state).
- Direct ORM writes attempting to create duplicate approved
  versions (constraint holds even outside the service).
- Identities with no approved version, which remain valid during
  initial drafting (the constraint permits zero, not just one).

Test environments that use SQLite do not enforce the partial
unique constraint. Integration tests for this invariant must run
against Postgres.

### 17.4 Voice-design provider abstraction

- **17.4.a** Decide whether voice design (V10 primitive) stays under
  `TextToSpeechProvider` or splits into a `VoiceDesignProvider`.
  Voice design produces a `voice_id`; TTS synthesizes speech from
  one. They are related lifecycles but not the same.

#### RATIFIED 2026-08-06 — 17.4.a

**Accepted:** introduce `VoiceDesignProvider` as its own Protocol
with registry, mock implementation, capability introspection,
provenance recording, execution-mode tracking, and future provider
independence.

**Rationale (recorded):** lifecycle separation is the important
architectural boundary. Voice design is identity authoring. TTS
is runtime rendering. Different responsibilities, independently
replaceable.

**Architectural requirements:**

1. **`VoiceDesignProvider` owns identity creation only.** Its
   responsibility ends once it returns a canonical voice
   artifact (voice reference plus provenance). It **never**
   synthesizes speech.
2. **`TextToSpeechProvider` consumes approved voices only.** TTS
   never knows how a voice was created. It receives an approved
   voice reference and text, nothing more.
3. **Approved representation bundles remain provider-neutral.**
   Bundles reference a **canonical voice asset**, with provider
   provenance attached separately. The rest of the platform
   asks for **"approved voice"** — not "Runway voice,"
   "ElevenLabs voice," or provider-specific IDs. Provider
   details belong inside provenance and generation records.
4. **Capability reporting must remain factual.** Capability
   discovery answers questions like: supports voice cloning,
   supports designed voices, accepted audio formats, minimum
   sample duration, latency class, execution modes. It **never**
   claims subjective quality (no "better," "more natural,"
   "more expressive").
5. **Voice identity belongs to `CharacterIdentity`.** The
   approved voice is part of the teammate's identity. Changing
   the approved voice is an identity revision, not a runtime
   provider swap. Regeneration history, approval history,
   provenance, and benchmark evidence remain attached to the
   identity.
6. **Provider independence remains mandatory.** Nothing outside
   the adapter layer contains provider-specific assumptions.
   The orchestration layer never branches on
   `if provider == "runway"` or similar. Capability inspection
   determines behavior.
7. **Mock behavior mirrors the rest of the provider architecture.**
   `VoiceDesignProvider` receives: `FORCE_MOCK` support,
   deterministic mock IDs, execution-mode recording, provider
   provenance, drift verification — using exactly the same
   conventions as `PortraitProvider`, `RealtimeProvider`, and
   `TextToSpeechProvider`.
8. **Future compatibility.** The Protocol must be flexible
   enough to support providers that return more than a single
   voice ID. Future providers may return multiple candidate
   voices, editable voice projects, versioned voices,
   multilingual voices, or emotion-capable voices. The Protocol
   exposes these through **structured capability metadata**
   rather than requiring interface redesign.
9. **Identity consistency.** The `CharacterIdentity` approval
   process verifies that the approved portrait, approved voice,
   and approved representation bundle **all reference the same
   identity revision**. Voice approval is not an independent
   concept from portrait approval. They become approved
   together as one representation bundle.
10. **Drift verification.** Once the Protocol stabilizes, extend
    the R10 verifier per the §9.6 sequencing note. Every
    concrete `VoiceDesignProvider` implementation must satisfy
    the Protocol with zero adapter-specific exceptions.

**Substrate consequences folded into the contract:**

- §6.2 amended: bundle now references a "canonical voice
  asset" rather than a provider-side identifier.
- §11 amended: voice and realtime representation references
  described as opaque canonical references, not provider IDs.
- §15.3 amended: illustrative bundle shape adjusted to move
  provider fields out of the bundle and onto separate voice-
  reference and realtime-reference records that carry their own
  provider provenance.

### 17.5 Reference kind enumeration for the first pass

- **17.5.a** Confirm the seven human reference kinds in
  [§7.3](#73-reference-kinds-initial-enumeration) as the initial
  enumeration. Add, remove, or defer any of them.
- **17.5.b** Decide whether the initial approved bundle requires
  every kind present or whether a minimum subset suffices for
  `draft → approved` promotion.

#### RATIFIED 2026-08-06 — 17.5.a

**Accepted with amendment:** redesign to structured `kind` +
`purpose`, but do **not** collapse everything into a single
`canonical_reference` top-level kind.

**Amendment (architectural longevity):** `kind` describes the
artifact class; `purpose` describes how the artifact participates
in identity.

- **`kind` = what this artifact fundamentally is.**
- **`purpose` = how this artifact participates in identity.**

**Initial `kind` enumeration (human branch):**

- `portrait_reference` — still portrait imagery.
- `motion_reference` — short identity motion clips *(future
  artifact class; may not be authored in round one).*
- `speech_reference` — lip-sync calibration clips *(future).*
- `body_reference` — full-body or gesture references *(future).*
- `environment_reference` — lighting-calibration references
  *(future).*
- `expression_reference` — reserved for the case where an
  expression genuinely becomes its own artifact class rather
  than a purpose value under `portrait_reference`.

**Initial `purpose` enumeration (human branch, applied to
`portrait_reference` in round one):**

- `front`
- `slight_left`
- `slight_right`
- `neutral_rest`
- `listening`
- `consideration`
- `gentle_positive`

**Rationale for splitting kind from purpose:** if everything
begins life as `canonical_reference`, the meaning of `kind`
disappears and every future evolution gets pushed into `purpose`.
That is usually a sign the abstraction boundary is one layer too
high. Splitting kind and purpose preserves clean separation while
remaining branch-neutral.

**Locked requirements (inherited from §17.3.a discipline):**

- `purpose` is schema-validated.
- Schemas are branch-specific (human schema, non-human schema).
- Adding a new purpose value does not require a Django
  migration.
- Invalid purposes fail validation immediately at the
  authoritative write path.

**Notation convention:** reference identity is written as
`<kind>/<purpose>` — for example `portrait_reference/front`,
`portrait_reference/neutral_rest`. This notation appears in the
declarative approval floor and surface requirement schemas ratified
in §17.5.b below.

#### RATIFIED 2026-08-06 — 17.5.b

**Accepted with amendment:** minimum approval floor plus separate
bundle-level surface availability — but **both** definitions must
be **declarative data, not hardcoded transition logic.**

**Amendment (declarative floor + surface requirements):**

The approval floor and per-surface requirements live in the
identity branch schema, not in the transition service's Python
code. The transition service asks: *"does this identity satisfy
the schema's required approval floor?"* — it does not embed
which references are required.

**Illustrative human-branch schema (round one):**

```
Human Identity Schema v1

required_for_identity:
  - portrait_reference/front
  - portrait_reference/neutral_rest

surface_requirements:
  Home:
    - portrait_reference/front
  Presence:
    - portrait_reference/front
    - portrait_reference/neutral_rest
  Studio:
    - portrait_reference/front
    - portrait_reference/listening
  Live Conversation:
    - portrait_reference/front
    - portrait_reference/slight_left
    - portrait_reference/slight_right
    - portrait_reference/neutral_rest
    - portrait_reference/listening
    - portrait_reference/consideration
    - portrait_reference/gentle_positive
```

The transition service validates approval against
`required_for_identity`. The bundle evaluator computes supported
surfaces by asking, per surface in `surface_requirements`:
*"are all listed references present at `state=approved` on this
identity version?"*

**Advantages recorded:**

- Future schema versions evolve without changing transition
  code.
- Non-human branches define their own approval floors naturally.
- Benchmark fixtures can target schema versions explicitly.
- Approval behavior is declarative rather than procedural.
- Product, Portrait Language, and Engineering stay aligned
  without hidden logic.

**Substrate consequences folded into the contract:**

- §7 amended: reference relationships carry `kind` +
  `purpose`; kinds and purposes are the structured pair defined
  above.
- §15.4 amended: `IdentityReference` gains a `purpose` field;
  `kind` becomes the artifact-class enum.
- §6 amended: bundle references the identity version and the
  approved canonical voice and realtime references; supported
  surfaces are computed from the schema's `surface_requirements`
  applied to the identity version's approved reference set.
- New location required: the human identity schema (with
  `required_for_identity` and `surface_requirements`) lands
  under
  `docs/design/visual/portrait_qualification/schemas/` — a new
  subdirectory whose scaffolding responsibility is picked up
  when §17.8 fixture authorship is opened.

### 17.6 Normalization scope for first implementation

- **17.6.a** Decide the minimum viable normalization pipeline for
  the first benchmark run — for example, crop + background alone,
  deferring tonal and lighting normalization to a later revision.
  The contract accepts a minimal first implementation as long as
  the output-shape contract in [§10.3](#103-output-shape) is
  respected.

#### RATIFIED 2026-08-06 — 17.6.a

**Accepted (round-one normalization scope):**

- canonical crop
- surface-specific framing
- eye-line normalization
- background replacement using the controlled background family
  (Portrait Language §18)

**Explicitly deferred (require later benchmark evidence before
adoption):**

- color grading
- white balance correction
- exposure normalization
- relighting
- shadow synthesis
- skin-tone normalization
- any AI-assisted "beautification"

**Two-tier evidence (strongly accepted):**

Every benchmark generation produces **two immutable artifacts:**

- **Raw Provider Output** — the provider's response as returned,
  byte-for-byte preserved.
- **Normalized Output** — the result of the round-one pipeline
  applied to the raw output.

The normalized artifact **never overwrites** the raw artifact.
Preserving both enables reproducibility and lets future pipeline
revisions be replayed against the exact same provider artifact.

**Amendment — Normalization Manifest (new required artifact):**

Every benchmark generation produces a third artifact alongside
raw and normalized outputs — a **Normalization Manifest**
describing exactly what transformations occurred:

- crop profile used
- framing profile
- background identifier
- eye-line adjustments
- pipeline version
- normalization stages executed
- normalization stages skipped
- execution duration

The manifest makes normalization completely reproducible: future
pipeline revisions can regenerate the normalized artifact from
the raw asset plus the manifest.

**Determinism constraint (load-bearing):**

Normalization must be **deterministic**. Given:

- identical raw asset
- identical pipeline version
- identical manifest

the resulting normalized artifact must be **byte-for-byte
identical**. Normalization must never introduce randomness. If
randomness exists, provider comparisons become impossible because
reviewers cannot tell whether differences originated from the
provider or the normalization layer.

**Provider output is the canonical evidence.** Normalization is
an interpretation of that evidence. Benchmark decisions must
never lose access to the original provider artifact. This
protects against unintentionally optimizing the normalization
pipeline until every provider appears equally good.

**Stage architecture (independently measurable):**

The pipeline is composed of **ordered, independently
enable/disable/versioned stages**:

1. crop
2. framing
3. eye-line normalization
4. background replacement
5. tonal normalization *(future, deferred above)*
6. lighting normalization *(future, deferred above)*
7. shadow normalization *(future, deferred above)*

Each stage carries its own version. The pipeline version is a
composition of enabled stage versions. This allows later
benchmark rounds to answer questions like *"did lighting
normalization actually improve reviewer trust?"* without
rebuilding the pipeline.

**Surface profiles are data, not code:**

Surface profiles — **Compact, Presence, Studio, Conversation,
Team Card** (initial set) — are declarative configuration, not
embedded layout logic. Each profile defines:

- crop ratios
- eye position
- margins
- output resolution
- framing behavior

Normalization consumes a profile at pipeline time. Adding a new
surface or adjusting a profile's parameters does not require a
code change — same declarative discipline as
[§17.5.b](#175-reference-kind-enumeration-for-the-first-pass)'s
`surface_requirements`.

**Production vs. benchmark policy:**

- **Benchmark:** preserve raw + normalized + manifest for every
  generation.
- **Production:** may cache only the normalized asset for serving
  while retaining the raw asset for provenance and future
  regeneration. This is a deployment policy, not a pipeline
  limitation.

**Substrate consequences folded into the contract:**

- §10 amended: normalization boundary now includes the manifest,
  the determinism constraint, the stage architecture, and the
  data-driven surface profile discipline.
- §15.6 amended: illustrative shape split — `SurfaceProfile`
  becomes declarative data (not a per-identity row), a new
  `NormalizationManifest` record is added per generation, and
  the earlier per-identity `NormalizationProfile` is scoped
  down to optional per-identity overrides (may not be needed in
  round one at all).

### 17.7 Evaluation-instrument shape

- **17.7.a** Ratify the repository-first evidence and scoring
  approach in [§14.2](#142-evaluation-instrument-stays-repository-first).
  The alternative — building a Django model immediately for
  scoring — is not recommended but is available if the operator
  has reasons this contract does not know about.
- **17.7.b** Decide how many reviewers per fixture are required for
  a scoring result to count. Portrait Territory Study §7 does not
  prescribe this. Reviewer count directly affects benchmark
  duration.

#### RATIFIED 2026-08-06 — 17.7.a

**Accepted:** repository-first evidence and scoring, with the
scoring schema treated as a **contract**, not merely a document.

**Amendment — schema-as-contract (three artifacts, not one):**

Under `docs/design/visual/portrait_qualification/scoring/`:

- `SCORING_SCHEMA_V1.md` — human-readable explanation. Explains
  what each scoring field means, how weighted categories map,
  and how reviewers should interpret ambiguous cases.
- `scoring.schema.json` — machine-validatable JSON Schema.
  Enforces structure automatically. Reviewer records that fail
  validation are rejected at intake.
- `scoring-template.yaml` — canonical reviewer template. Every
  new scoring record starts from this template.

Advantages recorded:

- Reviewer records validate automatically.
- Aggregation scripts become simpler.
- Malformed evidence is caught immediately.
- Future import into Django (if it ever happens) becomes
  deterministic.

**Amendment — immutable metadata on every scoring record:**

Every scoring record includes the following required metadata,
recorded once at record creation and never mutated:

- benchmark round / version
- scoring schema version
- pipeline version (from §10.6 manifest)
- normalization version (composition of enabled stage versions)
- fixture version
- provider
- rendering direction
- execution mode (from §9.4)
- reviewer
- timestamp

This preserves comparability across future benchmark rounds even
after the pipeline, schema, or fixtures evolve. Comparing scores
from a v1 pipeline against a v2 pipeline without knowing the
pipeline version each was produced against would be meaningless;
this metadata prevents that mistake.

**Amendment — evidence is append-only:**

Reviewer scores never overwrite previous reviews. If a reviewer
changes their opinion:

- The original score record remains, untouched.
- An amended score is appended as a new record.
- The reason for revision is recorded on the amendment.

Benchmark evidence is historical data. History does not
disappear. This applies to all evidence types — scores,
observations, disagreement notes, reviewer amendments — not
only to primary scores.

**Substrate consequences folded into the contract:**

- §14.2 amended: reflects the three-artifact schema-as-contract
  shape, immutable metadata requirement, and append-only
  discipline.

#### RATIFIED 2026-08-06 — 17.7.b

**Accepted:** Chris remains the sole scoring reviewer. Claude
provides **structured observations only** and does not assign
scores. External human review is reserved for the final
territory-selection decision.

**Amendment — Claude observations must be structured, not
free-form:**

Every Claude observation record uses this structured shape:

- **Observed Artifact** — which artifact the observation
  concerns (generation record id, asset id, manifest id).
- **Observed Behavior** — what was noticed, in factual language.
- **Potential Concern** — what benchmark discipline this
  potentially violates or supports.
- **Supporting Evidence** — pointers into the artifact
  (timestamps for motion, regions for stills, transcript spans
  for speech).
- **Confidence** — how strongly the observation is asserted.
  Ranges from `low` to `high` with an explicit qualifier.
- **Affected Benchmark Dimension(s)** — which Portrait Territory
  Study §3 dimensions the observation informs.

Free-form commentary is not acceptable. Structured observations
are searchable, reusable, and — critically — avoid accidental
scoring language.

**Amendment — formal disagreement mechanism:**

If Claude repeatedly highlights an issue that the reviewer
scores differently, **nothing changes automatically.** The
scoring record simply notes:

> *Operator differed from structured observations.*

That disagreement itself becomes benchmark evidence.

If later rounds consistently show the same disagreement pattern,
it may indicate either:

- reviewer bias, or
- observation heuristics that need refinement.

Neither side silently overwrites the other. The disagreement is
data to be examined at territory-selection time.

**Amendment — external reviewer scope:**

External human review is engaged **only** at the final territory-
selection stage — the moment when round-one evidence is folded
into Portrait Territory Study V2. Per-fixture scoring remains
solo throughout round one. The benchmark itself stays
lightweight; the architectural decision receives an additional
human perspective before becoming canonical.

**Substrate consequences folded into the contract:**

- No substrate schema changes required for §17.7.b — the
  scoring schema (per §17.7.a) already treats `reviewer` as a
  required field and can represent multi-reviewer records
  without change. Observation records get their own record type
  in the scoring schema (`observation` vs. `score`); disagreement
  notes get theirs (`operator_differed_from_observation`).

### 17.8 Fixture authorship

- **17.8.a** Approve the fixture-set shape in
  [§14.4](#144-fixture-set) and authorize a companion document to
  author the initial fixture set. Fixture authorship is out of
  scope for this contract but blocking for benchmark round one.
- **17.8.b** Decide whether fixture identities are named
  distinctively (`fixture_maren`, `fixture_dee`) or numerically
  (`fixture_01`) to avoid accidentally treating any fixture as a
  candidate "Alex."

#### RATIFIED 2026-08-06 — 17.8.a

**Accepted:** five bounded round-one fixtures, per-fixture
directories with a catalog README, required
`FIXTURE_AUTHORING_GUIDE_V1.md`.

**Round-one fixture set (canonical):**

- `fixture_h1` — straightforward human baseline
- `fixture_h2` — facial-hair coverage
- `fixture_h3` — deliberately difficult identity case
- `fixture_h4` — demographic and feature contrast
- `fixture_nh1` — non-human substrate exercise, unscored
  aesthetically (per [§17.2.b](#172-non-human-branch-authorship))

**Adaptive expansion rule:** allowed **only** when documented
evidence identifies a specific blind spot. Do not add fixtures
merely to make the set feel comprehensive.

**Amendment 1 — Separate fixture definition from generated
evidence:**

Fixture definitions and benchmark evidence must not mix in one
namespace. Later benchmark rounds must not overwrite or confuse
evidence from earlier pipeline or provider versions.

**Ratified directory shape:**

```
fixtures/
  README.md
  FIXTURE_AUTHORING_GUIDE_V1.md
  fixture_h1/
    identity.yaml
    rationale.md
    bootstrap/
      references/
    runs/
      <benchmark_run_id>/
        <direction>/
          <provider>/
            raw/
            normalized/
            manifests/
            observations/
            scores/
  fixture_h2/
    ...
  fixture_nh1/
    ...
```

Semantics:

- **`identity.yaml` + `rationale.md`** — the canonical, stable
  fixture definition. Immutable once benchmark evidence
  references it (per §17.8.b canonical-identifier rule).
  Amendable through a versioned amendment procedure defined in
  the authoring guide.
- **`bootstrap/references/`** — the approved reference set
  produced by the bootstrap flow (see amendment 2 below).
  Populated after bootstrap human review completes, not before.
- **`runs/<benchmark_run_id>/…`** — per-run evidence. One
  subdirectory per benchmark round. Each run's evidence stays
  siloed under its own `benchmark_run_id`, preserving
  reproducibility across pipeline evolution.

**Amendment 2 — Do not require approved references before
fixture bootstrap:**

A fixture is **authorable** before approved references exist. It
is **not qualification-ready** until bootstrap references have
been approved.

**Bootstrap-reference procedure (ratified sequence):**

1. `identity.yaml` and `rationale.md` are authored.
2. `bootstrap/references/` directory exists but is empty.
3. Initial providers generate candidate references (their
   outputs land in `runs/<bootstrap_run_id>/…`).
4. Human review selects the approved bootstrap reference set
   from the candidates.
5. Approved references are copied or linked from the
   `runs/…` evidence tree into `bootstrap/references/`.
6. Regeneration and cross-provider testing then use the
   approved bootstrap set as the identity anchor.

Steps 1–2 are fixture authoring. Steps 3–5 are bootstrap.
Step 6 is round-one benchmark work.

**Prerequisite sequence (must land before fixture authoring
begins):**

1. Human identity schema (`required_for_identity`,
   `surface_requirements`) under `schemas/` — per
   [§17.5.b](#175-reference-kind-enumeration-for-the-first-pass).
2. Minimal non-canonical non-human test schema under `schemas/`,
   clearly labeled non-canonical — per
   [§17.2.b](#172-non-human-branch-authorship).
3. Controlled background family (Portrait Language §18) under
   `schemas/` or `backgrounds/` — per
   [§17.6.a](#176-normalization-scope-for-first-implementation).
4. Human-readable scoring schema
   (`scoring/SCORING_SCHEMA_V1.md`) — per
   [§17.7.a](#177-evaluation-instrument-shape).
5. Machine-readable scoring schema
   (`scoring/scoring.schema.json`) and canonical template
   (`scoring/scoring-template.yaml`) — per
   [§17.7.a](#177-evaluation-instrument-shape).
6. `FIXTURE_AUTHORING_GUIDE_V1.md` under `fixtures/`.

**The authoring guide must define:**

- fixture purpose
- schema validation
- diversity intent
- difficult-case selection rules
- likeness and consent constraints (Portrait Language §20)
- bootstrap-reference procedure
- versioning
- amendment rules
- when adaptive expansion is justified
- **prohibition on tuning a fixture differently for individual
  providers**

**Load-bearing rule:** every provider and rendering direction
must receive the **same versioned fixture payload**. A fixture
tuned per provider is not a fixture; it is a provider-specific
generation and is disqualified as cross-provider evidence.

#### RATIFIED 2026-08-06 — 17.8.b

**Accepted:** branch-prefixed coded identifiers — `fixture_h1`,
`fixture_h2`, `fixture_h3`, `fixture_h4`, `fixture_nh1`.

**Identifier rules:**

- Identifiers are **canonical and immutable** once benchmark
  evidence references them.
- **No personal names** may be used as identifiers.
- Human-readable descriptive labels may appear in
  `rationale.md`, but they must:
  - Remain fictional or purely descriptive.
  - Avoid referencing real acquaintances.
  - Avoid implying that any fixture is the future default Alex.
  - Not be included in provider prompts unless the fixture
    schema explicitly requires a name.
  - **Never replace the canonical fixture ID** in manifests,
    scores, observations, or generation records.

**Numbering rule (additional):** fixture numbering must **not**
imply quality, priority, or candidacy. The catalog `README.md`
must state explicitly that ordering reflects authorship
sequence only.

**Substrate consequences folded into the contract:**

- §14.4 amended: fixture set enumerated with canonical
  identifiers and the round-one adaptive-expansion rule.
- §13 amended: bootstrap flow annotated with the ratified
  directory layout and the "authorable before references"
  semantics.
- `README.md` at the qualification directory root updated to
  reflect the ratified fixture-directory structure.

### 17.9 Provider-adapter migration path

- **17.9.a** Decide whether existing Stability and Runway still-
  portrait call sites are migrated to the new `PortraitProvider`
  abstraction in one refactor or grown alongside it, with the
  current direct-call paths retained until the new abstraction is
  validated. The R2 realtime abstraction was built alongside the
  existing paths; the same pattern likely applies here.

#### RATIFIED 2026-08-06 — 17.9.a

**Accepted:** grow-alongside strategy, executed as a **strangler
pattern** — not as permanent duplication.

The benchmark harness uses the new provider abstractions
exclusively. Existing production endpoints and consumers remain
stable until the abstractions have been validated with real
outputs. Duplication is bounded, not indefinite.

**Strangler sequence:**

1. Introduce the new Protocol and adapters beside the existing
   services.
2. Use them exclusively in the benchmark harness.
3. Validate them against real provider outputs.
4. Stabilize the Protocol.
5. Migrate each existing internal endpoint to **delegate through
   the new adapter while preserving its current HTTP contract.**
6. Migrate external consumers only when an API change provides
   genuine product value.
7. Remove the old direct provider service code after every call
   site delegates through the abstraction.

This preserves customer-facing stability without permanently
duplicating provider logic.

**Ratified: `PortraitProvider`.**

Land `PortraitProvider` with:

- one real Stability adapter
- one real Runway still-portrait adapter, **where the operation
  genuinely represents still-portrait generation**
- one deterministic mock adapter
- factual capability inspection (per
  [§9.5](#95-capability-introspection-is-factual))
- execution-mode and provenance recording (per
  [§9.4](#94-execution-mode-recording),
  [§8.2](#82-the-generation-record))

**Freeze rule for existing direct paths:**

- No new consumers may attach to the direct-call paths during
  the growth window.
- No new provider-specific behavior may be added to the direct-
  call paths.
- Bug fixes only until migrated.

**Amendment — `AvatarProvider` is NOT ratified yet.**

Do not introduce a standalone `AvatarProvider` Protocol solely
because `/internal/avatars/` currently exists in the codebase.
The word "avatar" is a legacy endpoint term, not a domain
boundary decision.

"Avatar creation" may actually represent several distinct domain
operations:

- creating a realtime representation from an approved identity
- enrolling a portrait with a realtime provider
- producing a provider-specific reusable character identifier
- generating a still portrait
- preparing a motion-capable representation

These lifecycles must not be collapsed or named from the current
endpoint alone.

Before introducing that Protocol, the canonical identity contract
must first define the operation:

- what input it consumes
- what durable artifact it produces
- whether it belongs to identity authoring or realtime delivery
- whether the result is provider-portable
- how it participates in `ApprovedRepresentationBundle`
- whether its lifecycle belongs under `RealtimeProvider` or a
  distinct representation-authoring abstraction

**Temporary architectural terminology:** use
`RealtimeRepresentationProvider` in discussion if a separate
abstraction is ultimately required. Do not let the legacy word
`avatar` determine the permanent domain boundary. The
temporary name is a placeholder, not a ratified name.

This deferred question is added to the deferred items in
[§18](#18-explicitly-deferred-fields-and-decisions).

**Post-validation migration slices (ordered):**

1. Stability still-portrait endpoint delegates through
   `PortraitProvider`.
2. Runway still-portrait endpoint delegates through
   `PortraitProvider`, **if confirmed to be the same lifecycle**.
3. Realtime representation creation migrates through its
   ratified abstraction (deferred; see §18 addition below).
4. Django broker continues using compatible HTTP endpoints.
5. SPA API changes occur separately, only where terminology or
   product flow requires them.
6. Direct provider clients become adapter-internal only.
7. Dead compatibility paths are removed.
8. Drift verification (R10 extension) is added after the
   Protocols stabilize.

Each slice must preserve:

- request and response compatibility unless intentionally
  versioned
- workspace isolation
- execution-mode reporting
- provider provenance
- mock behavior
- existing production tests

**Exit condition for the growth window (measurable):**

The parallel period closes only when **every one** of the
following holds:

- every active consumer uses or delegates through a ratified
  provider abstraction
- no provider-specific call exists outside an adapter
- real-provider integration tests pass
- mock and execution-mode tests pass
- direct-call usage searches return zero active call sites
- cleanup removal has landed separately
- drift verification covers the stabilized Protocol

Until all seven conditions hold, the growth window is still
open.

**Substrate consequences folded into the contract:**

- §9.3 amended: `PortraitProvider` ratified; the entry for
  `AvatarProvider` replaced with a deferred-decision note
  pointing to §17.9.a ratification and to §18.
- §18 amended: two new deferred items added — the avatar-
  creation lifecycle question (blocking on the eventual
  representation-authoring Protocol name and scope), and the
  growth-window exit conditions as an operational milestone.

### 17.10 Existing Spokesperson field disposition

- **17.10.a** Decide whether `Spokesperson.runway_avatar_id`,
  `Spokesperson.portrait_path`, and `Spokesperson.voice_id` remain
  in service during the benchmark phase (as compatibility fields)
  or are removed at the time the identity substrate lands.
  Removing early forces every product surface to migrate together;
  keeping them risks the two paths drifting.

#### RATIFIED 2026-08-06 — 17.10.a

**Accepted:** the three existing fields on the (renamed)
`Teammate` model remain during the benchmark and migration
window as **temporary compatibility mirrors**:

- `Teammate.runway_avatar_id`
- `Teammate.portrait_path`
- `Teammate.voice_id`

**The canonical identity substrate becomes the source of truth
immediately.** The compatibility fields exist only to preserve
current consumers while the strangler migration proceeds. They
are **not independent identity state.**

**Authoritative-write rule:**

All identity changes flow through the canonical identity and
approved-representation-bundle services. Those services update
the compatibility mirrors in the same transaction whenever the
approved representation changes. No new code may treat these
fields as writable domain state.

**Enforcement discipline (layered, not `save()` alone):**

Django permits bypass paths (`QuerySet.update()`, bulk operations,
direct SQL, migration code). Enforcement uses:

1. Canonical identity services as the only supported write API.
2. Existing mutation call sites migrated immediately to those
   services when the substrate lands.
3. Tests grep / audit known write paths.
4. Model-level defensive guards where practical.
5. Database permissions or triggers **only if** runtime
   evidence shows accidental writes remain a problem.

The goal is a controlled migration, not elaborate machinery
around fields scheduled for deletion.

**Amendment 1 — Mirror state must be measurable:**

A **compatibility-consistency verifier** runs during the growth
window. For each `Teammate`, it asserts:

```
compatibility mirrors == values derived from the current
                         approved representation bundle
```

Per-field comparisons:

- mirror `portrait_path` ↔ canonical approved portrait
  representation
- mirror `voice_id` ↔ canonical approved voice representation
- mirror `runway_avatar_id` ↔ canonical approved realtime
  representation, while that legacy concept still exists

Any mismatch is **drift**. Drift must:

- fail tests
- appear in qualification / audit tooling
- **never** silently choose the mirror value over the canonical
  substrate

**Synchronization direction is one-way. Canonical → mirror only.
Never mirror → canonical.** Bidirectional synchronization would
turn the compatibility layer into a second source of truth,
which is exactly what this ratification prevents.

**Amendment 2 — Bootstrap and null semantics:**

Substrate landing creates a transitional case: existing
teammates already have legacy field values but no canonical
identity substrate yet. Explicit backfill rule required.

When the substrate migration lands:

1. Existing legacy values are imported into a bootstrap
   `CharacterIdentityVersion`.
2. Their provenance is marked explicitly as legacy / imported.
3. No historical provider facts are invented if they are
   unknown.
4. Existing `portrait_path`, `voice_id`, and realtime
   identifiers become compatibility mirrors of that imported
   state.
5. The imported identity is **not** automatically considered
   benchmark-qualified merely because production previously
   used it.

**Provenance / status vocabulary** (recorded on canonical
records where appropriate):

- `legacy_imported`
- `approved`
- `qualification_validated`

Distinguishing these prevents legacy-imported identities from
silently inheriting the trust reserved for benchmark-qualified
ones.

**Null semantics (deterministic):**

A missing canonical value produces a deterministic mirror
value — the mirror does not preserve a stale value when the
canonical approved representation intentionally removes or
replaces that capability:

- canonical portrait absent → mirror `portrait_path = null`
- canonical voice absent → mirror `voice_id = null`
- canonical realtime representation absent → mirror
  `runway_avatar_id = null`

**Realtime identifier caveat (cross-cutting with §17.9):**

`runway_avatar_id` carries a legacy provider-specific concept
whose permanent abstraction is not yet ratified (per
[§17.9.a](#179-provider-adapter-migration-path)). Therefore:

- Preserve it as a compatibility mirror.
- Backfill / import it as legacy provider provenance.
- **Do not encode `runway_avatar_id` into the permanent
  `CharacterIdentity` schema.** The permanent schema is
  provider-neutral per [§17.4.a](#174-voice-design-provider-abstraction);
  encoding a Runway-specific field into it would violate that
  ratification.
- **Do not let the existence of `runway_avatar_id` force the
  future realtime-representation model.** Its lifecycle is
  still deferred to the resolution required by §17.9.a and
  tracked in [§18](#18-explicitly-deferred-fields-and-decisions).

Once the realtime representation lifecycle is properly defined,
the compatibility mirror derives from that ratified
representation.

**Ratified migration sequence (10 steps):**

1. `Spokesperson` → `Teammate` rename lands separately (per
   [§17.1.b](#171-naming)).
2. Canonical identity substrate lands.
3. Existing legacy identity fields are backfilled into
   canonical identity records with `legacy_imported`
   provenance.
4. Compatibility mirror writes become canonical → legacy only.
5. Benchmark harness uses canonical identity exclusively.
6. Existing mutation call sites move to canonical services.
7. Existing read consumers migrate one slice at a time.
8. Compatibility verifier proves mirrors remain synchronized
   throughout migration.
9. Searches / tests prove zero active direct reads and writes
   remain.
10. Remove the three compatibility fields and mirror logic in
    a dedicated cleanup migration.

**Exit conditions (compatibility period closes only when all
hold):**

- Canonical identity is the sole write authority.
- All existing identity data has been backfilled.
- No active code writes the compatibility fields.
- No active consumer reads them.
- Mirror-consistency verification passes.
- SPA, broker, realtime, TTS, admin, and relevant tests use
  canonical representations.
- Repository searches show zero active call sites outside
  historical migrations and docs.
- Cleanup removal lands separately.

**Prohibition against permanent denormalized-cache repurposing:**

Do not keep these fields permanently as denormalized caches
unless runtime profiling later establishes a real performance
requirement. If that ever happens, it becomes a **new explicit
architecture decision** rather than inertia from this
migration.

**Substrate consequences folded into the contract:**

- §15 amended with a small note (§15.9) recording the
  compatibility-mirror discipline on `Teammate` during the
  growth window.

**Amendment 3 — Legacy imports carry NULL execution fields
(post-SESSION 242 correction):**

`ExecutionMode` and `ExecutionModeActual` describe
execution-framework decisions (§9.4). Every non-legacy value in
those enums is either a mode a caller requested or an outcome
an adapter produced. Legacy imports never went through the
execution framework — no caller requested a mode, no adapter
ran — so representing them with a synthesized enum value would
misuse the field.

SESSION 242 (§19 Step 3 delivery) originally added
`ExecutionMode.LEGACY_HISTORICAL` and
`ExecutionModeActual.LEGACY_HISTORICAL` as an accommodation for
this case. Those additions were surfaced-not-ratified in the
SESSION 242 handoff. Operator review of the SESSION 242 landed
implementation concluded that the accommodation belonged in
provenance vocabulary rather than execution vocabulary and
should be resolved before Step 4 opens against a substrate whose
execution metadata is trusted by the compatibility-consistency
verifier.

Ratified resolution:

- `GenerationRecord.execution_mode` and
  `GenerationRecord.execution_mode_actual` are **nullable**.
- **NULL means "no provider execution occurred through the
  execution framework for this row."** NULL is the honest
  label for the absence of any framework decision. It is
  **not** a general "missing metadata" catch-all — a
  malformed provider record must never silently degrade to
  NULL execution fields.
- **Pairing invariant:** `provider = legacy_imported` iff both
  execution fields are NULL. Equivalently: any executable
  provider record has both execution fields non-NULL; a
  legacy-imported record has both NULL. A half-null state
  (one populated, one NULL) has no defined semantics and is
  refused at model-level `clean()` (fires through the
  pre_save signal).
- `LEGACY_HISTORICAL` is **removed** from both enums. Origin
  for legacy imports is carried by three orthogonal markers
  that already existed after SESSION 242:
  `GenerationProvider.LEGACY_IMPORTED` +
  `ImportProvenance` (OneToOne with
  `CharacterIdentityVersion`) +
  `spec_schema_version = 0`.
- **`ExecutionMode.UNAVAILABLE` remains distinct from NULL.**
  `UNAVAILABLE` = an execution-framework decision recorded
  from an attempted call the provider could not serve;
  `NULL` = no execution-framework attempt ever occurred.
  These are materially different histories and both the
  test suite and the pairing invariant enforce the
  separation.

This amendment closes the SESSION 242 flag; it does not
reverse a prior ratification, because the SESSION 242 enum
additions were never ratified.

Migration shape: `identity/0003_execution_mode_nullable`.
Both execution fields become nullable; any surviving row with
persisted string value `legacy_historical` (should be zero
under Step 3 semantics, since the correction lands before Step
3 has been run against production data) migrates forward to
NULL. Reverse migration restores the literal string
`legacy_historical` on `provider = legacy_imported` rows and
returns the columns to NOT NULL.

**Amendment 4 — Prequalification-authored provenance for
pre-Step-5 production authoring (ratified 2026-08-07,
SESSION 243):**

The compatibility-mirror discipline (Amendment 1) requires a
canonical destination for every production write that would
otherwise land on `Teammate.portrait_path`, `Teammate.voice_id`, or
`Teammate.runway_avatar_id`. Existing production authoring flows
(`perform_create`, `clone_voice`, `change_voice`, `rebake_avatar`,
`refresh_portrait`, `seed_cast`, batch refresh/persist commands)
predate `PortraitProvider`, `VoiceDesignProvider`, the normalization
pipeline (§17.6.a), and the branch schema's declarative approval
floor (§17.5.b). Under Amendment 1 they must migrate to canonical
services at Step 4; under the ratified qualification path they
cannot yet produce a schema-valid, floor-satisfied version.

A fourth ratified provenance category resolves this:

**`prequalification_authored`** — this canonical identity
representation was authored by the running product through an
existing production authoring flow before portrait qualification /
normalization requirements were available or satisfied.

**Provenance vocabulary distinctions (extends Amendment 2):**

| Category | Meaning | Physical marker |
|---|---|---|
| `legacy_imported` | Copied from pre-substrate `Teammate` rows by the Step 3 one-time backfill. | `ImportProvenance` OneToOne row present. |
| `prequalification_authored` | New canonical state created after Step 4 through an existing production authoring flow. | `PrequalificationProvenance` OneToOne row present. |
| (unmarked, future) | Authored through the full qualified path landing in Steps 5–10. | Neither provenance row present + `spec_schema_version >= MIN_CANONICAL_SPEC_SCHEMA_VERSION` + branch-schema approval floor satisfied. |

**Mutual exclusion:** a `CharacterIdentityVersion` carries at most
one of `ImportProvenance` or `PrequalificationProvenance`. Enforced
primarily at the authoritative service layer and by regression
tests; a model-level `clean()` defensive assertion is permitted as a
second layer. Cross-table triggers are not required and not landed.

**Shared discipline (mirrors Amendment 2 points 3–5):**

1. Neither `legacy_imported` nor `prequalification_authored` is
   automatically benchmark-qualified. Qualification remains a
   separate axis per §5.6.a.
2. Both use `spec_schema_version = 0` because neither claims
   schema validation. `MIN_CANONICAL_SPEC_SCHEMA_VERSION` remains
   the bar for `services.create_draft_version` / `update_draft_spec`;
   the Step 4 prequalification-authoring service and Step 3's
   `import_service` are the only paths permitted to write `0`.
3. Both may bypass the branch schema's `required_for_identity`
   approval floor. The bypass is a discrete service
   (`approve_prequalification_version` for Step 4;
   `import_service._create_bootstrap_version` for Step 3), never a
   mode-flag on the qualified `services.approve_version` path, so
   the qualified approval floor cannot be weakened by accident.
4. Both preserve provider neutrality per §17.4.a. Provider-specific
   identifiers live inside `GenerationRecord` provenance/evidence
   fields; canonical rows (`CharacterIdentity`,
   `CharacterIdentityVersion`, `CanonicalVoiceReference`,
   `CanonicalRealtimeReference`, `ApprovedRepresentationBundle`,
   `IdentityReference`) carry no provider-specific columns.

**Distinction from `legacy_imported` on evidence semantics:**

- `GenerationRecord.provider` for a prequalification-authored write
  carries the **real** provider that produced the artifact
  (`RUNWAY_AVATAR`, `RUNWAY_TTS`, `STABILITY_STILL`,
  `ELEVENLABS_TTS`, `MOCK`, or any adapter-abstracted future
  provider). `LEGACY_IMPORTED` remains reserved for Step 3
  synthetic records.
- `GenerationRecord.execution_mode` and `execution_mode_actual`
  are **non-NULL** for prequalification-authored records because a
  real provider execution occurred through the direct-call path
  (typically `REAL_REQUIRED / REAL`, or `FORCED_MOCK / MOCK` when
  the media engine is in mock mode). This preserves the
  Amendment 3 pairing invariant: only `LEGACY_IMPORTED` records
  carry NULL execution fields.
- Provider-response payloads are recorded factually into the
  `GenerationRecord` evidence fields per the "Provider-output
  convention" below. Never fabricated.

**Versioning consequences (per §5.4, ratified):**

Every prequalification-authoring event creates a new
`CharacterIdentityVersion` per §5.4 — any change to the approved
reference view set, approved voice binding, or approved realtime
representation requires a new version. Consequently:

- `perform_create` → first `CharacterIdentityVersion` (draft →
  approved, spec empty).
- `clone_voice` / `change_voice` → new version (previous approved →
  superseded), same empty spec, different bundle.
- `refresh_portrait` → new version.
- `rebake_avatar` → new version.
- `seed_cast`, `refresh_portraits`, `persist_spokesperson_portraits`
  batch commands → one new version per teammate per event.

Version count per teammate grows linearly with authoring events.
This is honest under §5.5 (every generation record and normalized
output remains anchored to the specific version it was produced
against). The prequalification-authoring service is **not**
idempotent by content — the caller controls when an authoring event
fires; identical inputs on two consecutive calls produce two
versions, only the newer of which is currently approved.

Prequalification-authoring service **must carry forward** the
current approved version's canonical state that the caller is not
touching. A `change_voice` event that supplies only a new voice
input creates a new version whose bundle re-references the same
canonical portrait reference (a new `IdentityReference` row pointing
at the same `Asset` + `GenerationRecord`) and the same canonical
realtime reference (a new `CanonicalRealtimeReference` row pointing
at the same `GenerationRecord`). Otherwise the new version would
present NULL portrait/realtime and the mirror sync would collapse
those fields to `""` — visible drift for an operation that didn't
change them. Carry-forward is a service-layer detail, not a
schema addition.

**Prequalification canonical-authoring service shape:**

```
record_prequalification_representation(
    teammate: Teammate,
    *,
    source_call: str,
    author: User | None,
    portrait: PortraitRepresentation | None,
    voice: VoiceRepresentation | None,
    realtime: RealtimeRepresentation | None,
) -> CharacterIdentityVersion
```

Where each `*Representation` value object carries the provider
result (provider name, provider ID, response fields, mock_mode,
status). Orchestration steps A–I run inside one
`transaction.atomic()`:

A. If `teammate.character_identities.first()` is None, create a
   `CharacterIdentity(kind=human, teammate=teammate,
   name=teammate.name, workspace=teammate.workspace)`. Human is the
   only branch existing production authoring supports; non-human is
   out of Step 4 scope.
B. Create a new draft `CharacterIdentityVersion(spec={},
   spec_schema_version=0)` under `select_for_update()` on the
   parent identity, revision auto-assigned per §17.3.b.
C. Land `PrequalificationProvenance` on the version.
D. For each provided representation, create a `GenerationRecord`
   with the real provider enum, real execution fields, and the
   provider-output convention below.
E. Portrait input → synthetic `Asset(role=REFERENCE_IMAGE,
   file_path=<url or data URI>, workspace=teammate.workspace)` +
   `approve_reference(...)` at
   `(kind=portrait_reference, purpose='front')`. Voice input →
   `CanonicalVoiceReference(state=approved)`. Realtime input →
   `CanonicalRealtimeReference(state=approved)`. For any
   representation slot the caller did not touch, carry forward the
   current approved version's canonical reference by creating a
   new anchor row on the new version pointing at the same
   underlying `Asset` + `GenerationRecord` (evidence is immutable
   and shared; anchor rows are per-version and cheap).
F. Assemble a draft `ApprovedRepresentationBundle` on the new
   version referencing the version's approved voice + realtime
   canonical references (each nullable — bundle without voice or
   without realtime is legal per §15.3).
G. `approve_bundle(...)` promotes the bundle to APPROVED under the
   partial unique constraint `UNIQUE (identity_version_id) WHERE
   state='approved'`. Bundle-approval invariant requires a
   `portrait_reference/front` at `state='approved'` on the same
   version (step E guarantees this either fresh or carried
   forward).
H. `approve_prequalification_version(...)` promotes the version to
   APPROVED — a service **distinct** from
   `services.approve_version`, which reads and enforces the branch
   schema's `required_for_identity` floor. The prequalification
   variant bypasses the floor and is reachable **only** when the
   version has `PrequalificationProvenance` (`ImportProvenance` is
   handled separately by `import_service`). The prior approved
   version on the same identity is superseded transactionally per
   §17.3.b. **State-transition cascade:** when a version transitions
   `APPROVED → SUPERSEDED`, the service also transitions the prior
   version's approved child rows (its `ApprovedRepresentationBundle`,
   its `IdentityReference` rows at `state='approved'`, and its
   `CanonicalVoiceReference` / `CanonicalRealtimeReference` rows at
   `state='approved'`) to `SUPERSEDED` in the same transaction. This
   preserves the §5.6.a invariant that `state='approved'` means
   "currently admitted for product use" — a child row on a
   superseded version cannot be currently admitted.
I. `sync_teammate_mirrors(teammate)` writes the three compatibility
   mirrors from the newly-approved bundle's canonical values.
   Failure at any step A–I rolls back the entire authoring event;
   the mirrors are never inconsistent with canonical state after
   commit.

Existing product write sites (`perform_create`, `clone_voice`,
`change_voice`, `rebake_avatar`, `refresh_portrait`, `seed_cast`,
`refresh_portraits`, `persist_spokesperson_portraits`,
`smoke_voice`) migrate at Step 4.d to invoke this service. The
provider call itself stays exactly where it is today — the change
is where the result is persisted, not how it is obtained. No
provider abstraction (`PortraitProvider`, `VoiceDesignProvider`,
`RealtimeRepresentationProvider`) is introduced; those remain
Steps 5–7 / Step 12 work.

**Reference uniqueness invariant (co-ratified):**

For any `CharacterIdentityVersion`, at most one `IdentityReference`
may be at `state='approved'` for a given `(kind, purpose)` pair.
Enforced by:

1. A new `approve_reference(reference, *, approver)` service that
   locks the parent identity with `select_for_update()`, finds any
   currently APPROVED reference occupying the same slot, moves it
   to `SUPERSEDED` (new `ReferenceState` value — see below), then
   approves the incoming reference in the same transaction.
2. A Postgres partial unique constraint
   `UNIQUE (identity_version_id, kind, purpose) WHERE
   state='approved'` on `IdentityReference`. `purpose` is a
   `CharField(max_length=64)` (schema-validated by the branch
   purpose schema, not JSONB), so the partial unique is feasible
   without schema changes to the field. Constraint is the final
   guard against races and bypass.

`ReferenceState` gains a `SUPERSEDED` value: was `APPROVED`; a
newer authoring event admitted a replacement into the same
`(kind, purpose)` slot. Distinct from `REJECTED` (candidate was
not admitted). Enum becomes:
`{RAW, NORMALIZED, PROVISIONAL, APPROVED, SUPERSEDED, REJECTED}`.
Landed as an additive migration (no data rewrite; existing rows
stay in their current state).

**Bundle-approval invariant:**

Postgres partial unique constraint `UNIQUE (identity_version_id)
WHERE state='approved'` on `ApprovedRepresentationBundle`.
`approve_bundle` service transactionally supersedes any prior
approved bundle on the same version before approving the new one.
The bundle service remains generic: it does **not** hardcode
"human portrait_reference/front required" into its logic. Callers
that need such a precondition (currently only
`record_prequalification_representation`) enforce it themselves
before invoking `approve_bundle`. When the branch schema declares
bundle-approval requirements declaratively, `approve_bundle` will
consume them per §17.5.b's declarative discipline — not through
Python-embedded rules.

**Provider-output convention:**

`GenerationRecord.prompt_snapshot` is the request/input evidence
document (what was sent to the provider). Provider response
values live on `seed_or_reproduction_data` (reproduction handle)
and on new documented keys inside `prompt_snapshot` when the
response is not a reproduction handle but is factual evidence
worth preserving. To keep the compatibility adapter's extraction
rule simple and to preserve existing Step 3 conventions:

- Portrait: `Asset.file_path` carries the URI/URL. No separate
  provider-ID key is needed for the mirror. Provider response
  fields (thumbnail_url, template, prompt) recorded under
  `prompt_snapshot["provider_response"]` for audit only.
- Voice: `prompt_snapshot["provider_voice_id"]` — the string the
  provider returned. Additional response fields
  (`preview_url`, `mock_mode`, `status`) under
  `prompt_snapshot["provider_response"]`.
- Realtime: `prompt_snapshot["provider_realtime_id"]` — the
  string the provider returned. Additional response fields under
  `prompt_snapshot["provider_response"]`.

For `LEGACY_IMPORTED` records, Step 3's landed convention is
preserved: `prompt_snapshot["legacy_value"]` carries the imported
mirror value. The compatibility adapter reads `legacy_value` for
`LEGACY_IMPORTED` records and `provider_voice_id` /
`provider_realtime_id` for all other providers.

**Voice-preset handling:** existing named voice presets (e.g.
`"vincent"`, `"clara"`) that are Runway-owned voice capabilities
route as `provider = RUNWAY_TTS` with
`prompt_snapshot["voice_kind"] = "preset"` and the preset value
in `prompt_snapshot["provider_voice_id"]`. This is honest
provenance: Runway is the provider even when Character OS
exposes the voice as a named option. The Step 4.d migration
verifies every existing preset is Runway-owned (inspect
`SUPPORTED_VOICE_PRESETS` config); any preset not routed through
Runway would surface as a call-site anomaly and be resolved
before that particular call site migrates.

**Compatibility null representation:**

The three compatibility fields (`Teammate.portrait_path`,
`Teammate.voice_id`, `Teammate.runway_avatar_id`) are physically
non-nullable in the landed schema (`CharField` /
`TextField` with `blank=True, default=""`). This preserves the
pre-substrate SPA read contract, which already treats `""` as
absence. During the strangler window, canonical derivation uses
`None` internally and `sync_teammate_mirrors` encodes
`None → ""`. Canonical rows themselves carry proper SQL NULL
where their model schema permits. This does not change canonical
null semantics; it records the physical compatibility encoding
for the growth window. The fields are deleted at Step 13 alongside
the mirror-write logic (§17.10.a exit conditions); no
`null=True` migration is performed on them in Step 4.

**Direct-write allowlist (post-Step-4.d):**

Zero production growth-window exceptions for the three mirror
fields. Expected physical assignment sites:

- `apps/identity/compat.py::sync_teammate_mirrors` — the single
  legitimate production writer.
- Historical migration code where legitimately frozen.
- Test fixtures under `apps/*/tests/`.

`apps/identity/import_service.py` reads the pre-substrate mirror
values to create canonical state; it does not write mirrors and
is therefore not on the mirror-write allowlist.
`apps/identity/services.py` calls
`compat.sync_teammate_mirrors(...)` from inside its transitional
services; it does not assign mirror fields directly and is also
not on the write allowlist. A grep-based regression test at Step
4.f asserts this.

**Consistency-verifier semantics (co-ratified):**

`verify_teammate_mirrors(teammate)` classifies each teammate's
per-field state as `match`, `drift`, or `not_applicable`. Full
orphan / null matrix:

| Canonical state | Mirror value | Result |
|---|---|---|
| No `CharacterIdentity` | all three mirrors `""` | `not_applicable / no_identity_authored` |
| No `CharacterIdentity` | any mirror populated | `drift / orphaned_compatibility_state` |
| `CharacterIdentity` + no current approved version | mirrors `""` | `match` (canonical absent, mirror absent) |
| `CharacterIdentity` + no current approved version | any mirror populated | `drift / stale_compatibility_state` |
| approved version + canonical value absent for a field | mirror `""` for that field | `match` |
| approved version + canonical value absent for a field | mirror populated for that field | `drift` |
| approved version + canonical value populated | mirror equals canonical (post-strip) | `match` |
| approved version + canonical value populated | mirror differs / empty | `drift` |

`not_applicable` is reserved for the "no identity authored yet"
shape only. Prequalification-authored realtime references are
**not** N/A — they carry factual provider IDs recorded during
authoring; the compatibility adapter extracts them and the
verifier compares. `not_applicable` is not a fallback for
"could not derive"; that is `drift`.

The verifier is strictly read-only in Step 4. Detection is not
repair. A separate management command
`python manage.py verify_identity_mirrors [--workspace UUID]
[--json] [--fail-on-drift]` provides audit output. Doctor
integration is deferred; the runtime-truth doctor (SESSION 222)
checks documentation drift and is not the correct integration
point for data/state drift.

**Migrations landed in Step 4.a (contract-required):**

- `identity/0004_prequalification_provenance` — new
  `PrequalificationProvenance` model + `SUPERSEDED` value added
  to `ReferenceState` enum.
- `identity/0005_bundle_approval_partial_unique` — Postgres
  partial unique on `ApprovedRepresentationBundle
  (identity_version_id) WHERE state='approved'`.
- `identity/0006_reference_approval_partial_unique` — Postgres
  partial unique on `IdentityReference (identity_version_id,
  kind, purpose) WHERE state='approved'`.

No schema changes to `Teammate` compatibility fields, no schema
changes to `CharacterIdentity` / `CharacterIdentityVersion` /
`GenerationRecord` / `NormalizationManifest` / `ImportProvenance`
/ canonical reference models.

**Exit conditions unchanged:** Amendment 4 does not amend the
§17.10.a exit conditions. Removing the three compatibility
fields (Step 13) still requires: canonical identity is the sole
write authority; all existing identity data has been backfilled;
no active code writes the compatibility fields; no active
consumer reads them; mirror-consistency verification passes; SPA,
broker, realtime, TTS, admin, and relevant tests use canonical
representations; repository searches show zero active call sites
outside historical migrations and docs; cleanup removal lands
separately.

**Not a reversal of prior ratification.** Amendment 4 extends the
provenance vocabulary already ratified by Amendment 2 (which
named `legacy_imported`, `approved`, `qualification_validated`).
`prequalification_authored` is a fourth ratified term coordinated
with the same discipline — separate evidence table, no execution
enum abuse, no reviewer_notes as authority, no provider name as
provenance discriminator.

Distinct from
[§17](#17-unresolved-decisions-requiring-operator-resolution) — the
items below are deferred deliberately, without an operator decision
required at this stage.

- **Realtime-representation authoring lifecycle.** Per
  [§17.9.a](#179-provider-adapter-migration-path), the operation
  currently exposed as `/internal/avatars/` is not yet a resolved
  domain boundary. Before any successor Protocol is named
  (temporary architectural term: `RealtimeRepresentationProvider`),
  the following must be defined in the canonical identity
  contract: what input the operation consumes; what durable
  artifact it produces; whether it belongs to identity authoring
  or realtime delivery; whether the result is provider-portable;
  how it participates in `ApprovedRepresentationBundle`; whether
  its lifecycle belongs under `RealtimeProvider` or a distinct
  representation-authoring abstraction. The temporary name is a
  placeholder for discussion only.
- **Growth-window exit conditions.** Per
  [§17.9.a](#179-provider-adapter-migration-path), the parallel-
  paths window closes only when every consumer delegates through
  a ratified abstraction, no provider-specific call exists
  outside an adapter, integration and mock tests pass, direct-
  call usage searches return zero, cleanup removal has landed,
  and drift verification covers the stabilized Protocol. This is
  an operational milestone, not a decision — recording it as
  deferred here so no future session mistakes the growth window
  for permanent architecture.
- **Aesthetic register.** Portrait Territory Study V2 decides.
- **Default Alex casting.** Downstream of Portrait Territory Study V2.
- **Typography and Color and Light choices.** Blocked per
  SESSION 238.
- **Customer-facing wizard input collection.** See
  [§14.1](#141-wizard-changes-are-not-pre-benchmark-work).
- **Customer-uploaded reference face handling.** Portrait Language
  §20 rules; contract-level implementation of consent, ownership,
  and celebrity/child likeness enforcement deferred.
- **Cultural localization of face pool.** Portrait Language §12;
  scoped to a future document.
- **Customer motion preference (Still / Subtle / Full).** Portrait
  Language §23; the contract shape does not preclude it but does
  not implement it.
- **Small-size portrait treatments** (avatar-sized notification
  imagery). Portrait Language §25 defers; contract does not add.
- **Character Presence Language for non-human teammates.** Portrait
  Language §19; the branch discriminator here is the extent of
  this contract's non-human coverage.

---

## 19. Implementation gate

§17 is fully ratified as of 2026-08-06. All ten decision groups
(17.1 through 17.10) have been resolved with recorded amendments.
The contract's status flips from `draft` to `ratified`.

Implementation may begin **only after** the prerequisite
documents below have landed. Implementation itself proceeds in
the ratified ordered sequence below. Nothing in §17's
ratifications authorizes skipping prerequisites or resequencing
implementation slices.

### 19.1 Prerequisite documents (must land before any code)

These are documents, not code. They land under
`docs/design/visual/portrait_qualification/` per the ratified
directory structure. All are required before the first line of
implementation code is written.

1. **Human identity branch schema** under
   `schemas/human_identity_schema_v1.yaml` — includes
   `required_for_identity` and `surface_requirements` per
   [§17.5.b](#175-reference-kind-enumeration-for-the-first-pass).
2. **Human `portrait_reference` purpose schema** under
   `schemas/purpose_schema_human_v1.yaml` — the initial
   enumeration of purpose values validated per branch, per
   [§17.5.a](#175-reference-kind-enumeration-for-the-first-pass).
3. **Non-canonical non-human test schema** under `schemas/`,
   clearly labeled non-canonical per
   [§17.2.b](#172-non-human-branch-authorship).
4. **Surface profile definitions** under
   `schemas/surface_profiles/` — Compact, Presence, Studio,
   Conversation, Team Card — as declarative data per
   [§17.6.a](#176-normalization-scope-for-first-implementation).
5. **Controlled background family** under `schemas/` (or
   `backgrounds/`) — from Portrait Language §18, per
   [§17.6.a](#176-normalization-scope-for-first-implementation).
6. **Scoring schema-as-contract** under `scoring/` — three
   artifacts: `SCORING_SCHEMA_V1.md` (human-readable),
   `scoring.schema.json` (machine validation),
   `scoring-template.yaml` (canonical reviewer template),
   per [§17.7.a](#177-evaluation-instrument-shape).
7. **Fixture authoring guide** at
   `fixtures/FIXTURE_AUTHORING_GUIDE_V1.md` per
   [§17.8.a](#178-fixture-authorship).
8. **Fixture catalog README** at `fixtures/README.md` per
   [§17.8.a](#178-fixture-authorship) — stating explicitly
   that ordering reflects authorship sequence only.
9. **The five fixtures themselves** under
   `fixtures/fixture_h1/…` through `fixtures/fixture_nh1/…` —
   each with `identity.yaml` and `rationale.md`. `bootstrap/`
   and `runs/` subdirectories exist but are populated only
   during bootstrap (per
   [§17.8.a Amendment 2](#178-fixture-authorship)).

### 19.2 Deferred decisions that remain open

Two items deferred by §17.9.a remain unresolved and do not
block round one:

- **Realtime-representation authoring lifecycle** (§17.9.a
  amendment): must be resolved before any `AvatarProvider` /
  `RealtimeRepresentationProvider` Protocol is named. Tracked
  in [§18](#18-explicitly-deferred-fields-and-decisions).
- **Growth-window exit conditions** (§17.9.a + §17.10.a):
  operational milestones, not decisions. Tracked in
  [§18](#18-explicitly-deferred-fields-and-decisions).

### 19.3 Ratified implementation sequence

Prerequisites land first (§19.1). Then code proceeds in this
ordered sequence. Slices do not run in parallel unless
explicitly noted.

1. **`Spokesperson` → `Teammate` rename** as a focused,
   separate refactor per
   [§17.1.b](#171-naming). Not combined with substrate
   changes.
2. **Canonical identity substrate lands** — models for
   `CharacterIdentity`, `CharacterIdentityVersion`,
   `ApprovedRepresentationBundle`, `IdentityReference`,
   `GenerationRecord`, `NormalizationManifest`,
   `CanonicalVoiceReference`, `CanonicalRealtimeReference`.
   Postgres partial unique constraint per
   [§17.3.b](#173-persistence-granularity). Identity-version
   service (authoritative write path) per
   [§17.3.a](#173-persistence-granularity) and
   [§17.3.b](#173-persistence-granularity).
3. **Legacy identity fields backfilled** into canonical
   identity records with `legacy_imported` provenance per
   [§17.10.a Amendment 2](#1710-existing-spokesperson-field-disposition).
   Legacy imports are not benchmark-qualified.
4. **Compatibility mirror discipline activated** — canonical
   → mirror one-way sync in the identity-version service.
   Compatibility-consistency verifier lands. Existing mutation
   call sites migrate immediately to canonical services per
   [§17.10.a Amendment 1](#1710-existing-spokesperson-field-disposition).
5. **`PortraitProvider` Protocol lands** with Stability,
   Runway still-portrait, and Mock adapters per
   [§17.9.a](#179-provider-adapter-migration-path). Direct-
   call paths frozen (no new consumers).
   **✓ SHIPPED — SESSION 244** across four commits:
   - `e90c5f6` — pre-5.a: `GenerationProvider.RUNWAY_STILL_PORTRAIT`
     enum extension (data-only migration, isolated for
     historical clarity per §17.9.a Amendment on Avatar).
   - `bdedff3` — 5.a: three-method Protocol + `PortraitSpec` /
     `PortraitResult` / `ProviderCapabilities` dataclasses +
     Mock adapter + R10-style drift verifier +
     capabilities-factual denylist test. 30 tests.
   - `93ccffd` — 5.b: Stability adapter wrapping
     `stability_request_with_retry` (bypasses the legacy
     `generate_stability_portrait` composition service).
     `STABILITY_FORCE_MOCK` env var. 33 new tests; real-provider
     smoke passed against live Stability core.
   - `1aa4595` — 5.c: Runway still-portrait adapter wrapping
     `_portrait_task_attempt` + `_download_image_to_disk`
     (bypasses the legacy `generate_portrait` composition
     entry). Registry closed at v1 (Mock + Stability + Runway).
     41 new tests; real-provider smoke passed against live
     Runway `gen4_image`.
   - Closure verification (SESSION 244) added 22 cross-adapter
     parity tests in `test_cross_adapter_parity.py` — the
     5.d-scope work folded into Step 5 close after registry
     ratcheting satisfied it incrementally through 5.b and
     5.c. Not a separate implementation commit.
   **Architectural finding recorded during 5.b/5.c**:
   `PortraitProvider` sits **below** product-specific prompt
   composition and **above** provider transport. The existing
   top-level services (`generate_stability_portrait`,
   `generate_portrait`) combine wizard composition with
   transport; wrapping them would make the abstraction inherit
   old product assumptions. Stability proved the correct
   boundary at `stability_request_with_retry`; Runway proved
   the equivalent at `_portrait_task_attempt` +
   `_download_image_to_disk`. Recorded explicitly so a future
   refactor does not accidentally wrap the composition
   services and reverse this boundary.
   **Real-provider validation** (implementation-validation only,
   NOT portrait-qualification evidence):
   - Stability: real API contract validated against live
     `core` endpoint (6 real calls, 5.b + closure smoke).
   - Runway: real API contract validated against live
     `gen4_image` endpoint (1 real call, 5.c smoke).
   - Approximate cumulative validation spend: ~$0.25.
   - Neither result is portrait-territory or qualification
     evidence.
6. **`VoiceDesignProvider` Protocol lands** with Runway and
   Mock adapters per
   [§17.4.a](#174-voice-design-provider-abstraction).
   **✓ SHIPPED — SESSION 245** across three commits:
   - `c75978c` — pre-6.a:
     `GenerationProvider.RUNWAY_VOICE` enum extension (data-only
     migration `0008_step6_runway_voice_provider.py`), isolated
     for historical clarity — same discipline as the pre-5.a
     Runway still-portrait enum landing.
   - `998215c` — 6.a: three-method Protocol + `VoiceDesignSpec` /
     `VoiceCloneSpec` / `VoiceAuthoringResult` /
     `VoiceProviderCapabilities` dataclasses + `MockVoiceProvider`
     adapter + R10-style drift verifier +
     capabilities-factual denylist + TTS-boundary AST test that
     proves `voice_provider` and `tts_provider` packages have
     zero import-graph coupling and zero method-surface
     overlap. 56 tests. Registry ratchet 6.a: Mock-only.
   - `771c4d2` — 6.b: `RunwayVoiceProvider` adapter wrapping
     `runway_design_voice_transport` (renamed from
     `_design_voice_real` in `audio_client.py`) and
     `runway_clone_voice_transport` (renamed from
     `_create_voice_real` in `voice_clone_client.py`).
     Registry ratchets Mock + Runway. Cross-adapter mock-parity
     anchor: identical specs produce identical `voice_id` on
     both adapters when `spec.provider_model=None`. 41 new
     tests; real-provider smoke passed against live Runway
     `POST /v1/voices` (both `from.type=text` and
     `from.type=audio`).
   **Architectural finding recorded during 6.b**:
   `VoiceDesignProvider` sits **below** product-specific
   composition and **above** provider transport — same layering
   as `PortraitProvider`. The frozen
   `/internal/voices/design/` route handler inlines its own
   parallel duplicate of `runway_design_voice_transport`
   (verbatim Runway POST + poll logic); the duplication is
   Step 11 cleanup debt, not touched in Step 6. `design_brand_voice()`
   composes campaign business logic + file I/O above transport;
   wrapping it would reverse the boundary. The adapter wraps
   the shared transport primitives directly.
   **Central architectural question answered**:
   voice design and voice cloning genuinely belong behind one
   `VoiceDesignProvider` abstraction. Evidence: Runway itself
   models both operations at `POST /v1/voices` with a
   `from.type` discriminator (`"text"` vs `"audio"`); both
   returned the same 36-character `voice_id` + `previewUrl`
   result shape on the live smoke; both use identical polling
   machinery; both are voice-identity authoring per §17.4.a;
   §17.4.a explicitly names `supports_design` AND
   `supports_clone` as capability flags anticipating
   one-Protocol-two-methods. `VoiceOperation.DESIGN` / `CLONE`
   preserved on the result for downstream provenance filtering.
   **Real-provider validation** (implementation-validation
   only, NOT voice-qualification evidence):
   - Design: 1 real call against `/v1/voices` (`from.type=text`);
     36-char voice_id returned; preview_url populated; 22.2 s
     elapsed. Well under the 90 s adapter deadline.
   - Clone: 1 real call against `/v1/voices` (`from.type=audio`);
     36-char voice_id returned; preview_url populated;
     `final_status=READY`; 4.6 s elapsed. Reference audio was
     a ~241 KB MP3 synthesized locally via macOS `say` + ffmpeg
     (Apple TTS → MP3, non-personal — never a real human's
     voice, per the ratification carry-in).
   - Two zero-cost real-key discipline probes: `FORCED_MOCK`
     with a real key rejects real dispatch before wire; too-
     short description raises before wire.
   - TTS interoperability check (bonus per the SESSION 245
     ratification): both real TTS paths definitively
     unreachable today for reasons OUTSIDE Step 6 scope.
     (a) `RunwayTtsProvider.synthesize` sends a body Runway
     rejects with HTTP 400 (`Validation of body failed...
     expected string, received undefined` for the `promptText`
     field — pre-existing bug in the shipped TTS provider).
     (b) `ElevenLabsTtsProvider.synthesize`, exercised after
     `ELEVENLABS_API_KEY` was added mid-session, rejects the
     Runway-designed voice_id with HTTP 400 `invalid_uid`
     (`"An invalid ID has been received"`) — empirically
     contradicting the stale documentation claim in
     `elevenlabs.py` that Runway voice_ids round-trip through
     ElevenLabs. Recorded as findings F-6.b-2 (Runway TTS 400)
     and F-6.b-3 (ElevenLabs invalid_uid) in the SESSION 245
     handoff. **The interoperability failure does NOT collapse
     the §17.4.a boundary — it strengthens it.** `voice_id`
     values are provider-scoped identifiers; cross-provider
     consumption requires explicit translation that is NOT
     part of `VoiceDesignProvider`'s contract. The Protocol
     stands unchanged. The interop test is marked xfail so a
     future repair session flips it to XPASS as the natural
     "unblocked" signal.
   - Approximate cumulative Step 6 implementation-validation
     spend: ~$0.10–$0.15 (2 real Runway design calls including
     the mid-session re-run, 1 real Runway clone call, and 2
     zero-cost discipline probes; ElevenLabs 400s were
     rejected pre-generation so no ElevenLabs spend).
     Combined with Step 5's ~$0.25 (Stability + Runway
     still-portrait), running implementation-validation spend
     across §19.3 provider work: ~$0.35–$0.40.
   - Neither result is voice-qualification evidence.
7. **Normalization pipeline lands** — crop + surface-specific
   framing + eye-line normalization + background replacement,
   with the manifest, determinism constraint, stage
   architecture, and surface-profile-as-data discipline per
   [§17.6.a](#176-normalization-scope-for-first-implementation).
   **✓ SHIPPED — SESSION 246** across five commits + closure:
   - `ae86b6a` — pre-7.a: YAML loaders + Pillow/PyYAML pins.
     31 tests.
   - `2bcd9ee` — 7.a: pipeline harness + Stage Protocol +
     NoOpStage + drift verifier + determinism anchor. +49
     tests.
   - `abb05bf` — 7.b: CropStage(v1) + FramingStage(v1),
     center-only aspect crop, integer cross-multiply,
     LANCZOS downscale, refuse upscale. +88 tests. Locked
     the manifest evidence discipline (declared-vs-honored
     for subject_scale / min_edge_padding / framing_behavior;
     factual language only).
   - `83ddc7a` — 7.c: rembg session extraction (shared with
     V16) + `procedural_v1` block ratified into
     `background_family_v1.yaml` for all 5 backgrounds +
     CropStage v1→v2 (eye-line folded into deterministic
     crop-origin under source-center proxy, per SESSION 246
     `γ` disposition after inspection surfaced that a
     standalone EyeLineStage after Framing had zero legal
     headroom) + BackgroundReplacementStage(v1). +69 tests.
   - Closure commit (this): +20 tests
     (`test_step7_closure.py` cross-stage invariants +
     `test_real_input_smoke.py` opt-in real-input smoke).
     §19.3 row marked ✓ SHIPPED; INVENTORY regenerated;
     handoff written.
   **Architectural correction recorded during 7.c**:
   Pre-inspection, Step 7's ratified chain included a
   standalone `EyeLineStage` after `FramingStage`. Inspection
   surfaced that eye-line positioning after Framing has zero
   legal headroom under the no-padding invariant — every
   requested shift clamps to 0, making the class decorative
   for all five profiles. Rather than ship a class whose only
   pixel behavior is a permanent no-op, the operator ratified
   folding eye-line positioning into CropStage. `CropStage`
   bumped v1 → v2. The `eye_line_adjustments` manifest field
   is populated from CropStage(v2)'s nested evidence.
   Load-bearing methodology point: implementation moved
   because runtime evidence proved the earlier decomposition
   could not work under already-ratified invariants — not
   because the requirement changed.
   **Default v1 chain**: `CropStage(v2) → FramingStage(v1) →
   BackgroundReplacementStage(v1)`. NoOpStage stays registered
   as a harness exerciser and is explicitly excluded from the
   default chain.
   **Closure question answered YES** with executable
   invariants pinned in `test_step7_closure.py`: 5 profiles ×
   5 backgrounds matrix (25 cells) all produce byte-identical
   output on repeat runs at declared dimensions; raw input
   bytes preserved; procedural fill traceable only to YAML;
   rembg deterministic on `u2net_human_seg`; no provider
   assumption in the pipeline boundary; no aesthetic or
   detection language in evidence; upscale refused; padding
   refused; background-replacement failure never masquerades
   as success.
   **Real-input implementation smoke (opt-in via
   `NORMALIZATION_REAL_INPUT_SMOKE=1`)** validated the v1
   chain against a retained real 1280x720 Runway
   `gen4_image` portrait. Compact + team_card (both 1:1)
   succeed end-to-end; presence + studio + conversation
   raise the ratified `input_smaller_than_output` at
   FramingStage (Runway 1280x720 → 4:5 or 3:4 crop is too
   small for the portrait-oriented profiles' declared
   outputs). Recorded as a first-class Step 8/10 finding:
   Runway's current 1280x720-only image output cannot feed
   portrait-oriented profiles without either an upscale
   policy decision or a wider Runway aspect option shipping
   upstream.
   **Round-one deferrals preserved** (Step 8/10 evidence):
   * `subject_scale`, `min_edge_padding`,
     `framing_behavior.includes/excludes` remain
     declared-but-not-honored with factual
     `requires_real_subject_geometry` blockers.
   * Eye-line clamps to centered origin for square inputs
     under Compact / Team_Card (no vertical headroom);
     manifest records `eye_line_clamped_vertical=true` with
     factual `eye_line_clamp_reason`.
   * Procedural backgrounds are solid RGB fills; grain /
     texture / gradient authoring deferred per
     `background_family_v1.yaml`'s `assets_authored_separately`
     rule.
   * The five RGB triples are provisional
     `implementation_provisional`+
     `round_one_normalization_only` — NOT a Color and Light
     V1 palette selection.
   * All seven ratified-deferred stages (tonal / lighting /
     shadow / relighting / white-balance / exposure /
     skin-tone / beautification) explicitly negated as
     factual False flags in BackgroundReplacementStage's
     evidence.
8. **Benchmark harness** uses the canonical substrate,
   `PortraitProvider`, and the normalization pipeline
   exclusively. Bootstrap flow produces initial reference
   candidates per [§13](#13-bootstrap-flow-for-the-first-canonical-references)
   and the ratified fixture directory layout per
   [§17.8.a](#178-fixture-authorship).
   **✓ SHIPPED — SESSION 247.** Sub-sliced 8.a / 8.b / 8.c
   per operator ratification at Step 8 open (foundation +
   runner+writer + executable-evidence closure). Step 8's
   ratified boundary interprets "uses the canonical substrate"
   as **file-first evidence** (F-8.1 ratification): fixture
   identity payloads conform to the canonical schema and
   emitted evidence is sufficient for Step 9 to promote
   selected candidates into `GenerationRecord` /
   `IdentityReference` / `NormalizationManifest` rows without
   reinterpretation, but Step 8 itself does NOT write those
   substrate rows. `<direction>` in the ratified fixture-run
   path means **rendering direction hypothesis** verbatim per
   the scoring contract; reference kind/purpose is a separate
   candidate dimension (F-8.2).
   **✓ SHIPPED — 8.a** *(this commit)*: benchmark harness
   foundation. New `media-engine/app/services/benchmark_harness/`
   package with:
   * `vocabulary.py` — `RenderingDirectionHypothesis` (6
     values, mirrored verbatim from
     `scoring/scoring.schema.json`),
     `HumanPortraitReferencePurpose` (7 values, mirrored from
     `purpose_schema_human_v1.yaml`),
     `NonHumanCanonicalReferencePurpose` (1 value, mirrored
     from the non-canonical test schema), `IdentityBranch`,
     `ReferenceKind`, `BRANCH_TO_KIND` / `BRANCH_TO_PURPOSES`
     maps, `RATIFIED_FIXTURES` / `RATIFIED_PROVIDERS` /
     `RATIFIED_SURFACE_PROFILES` frozen tuples. Drift tests
     assert vocabulary agrees with on-disk ratified schemas.
   * `fixture_loader.py` — loads
     `fixture_h{1..4}/fixture_nh1` `identity.yaml` +
     `rationale.md`, validates against the ratified branch
     schema via `jsonschema.validate` (added `jsonschema>=4.0`
     to media-engine reqs), refuses payloads whose
     `spec_schema_version` disagrees with the branch schema's
     `schema_version` (no silent reinterpretation), computes
     an immutable `content_hash` (sha256 of canonically-
     serialized `(fixture_id, branch, version, spec, rationale)`).
   * `matrix.py` — `CellKey` (fixture, direction, kind,
     purpose, provider, profile) frozen dataclass with total
     ordering for stable enumeration; `MatrixAxes` with a
     `ratified_round_one()` static constructor; `expand_matrix`
     that scopes purposes per branch (cross-branch purpose
     combinations never appear). `BACKGROUND_IS_DERIVED_FROM_PROFILE`
     constant explicitly documents that background is derived
     from the surface profile's `tonal_environment_class` via
     `resolve_background_for_profile` — NOT an independent
     matrix axis (per operator discipline #3). Test enforces
     the constant + `CellKey` carries no `background_id`
     field.
   * `prompt_builder.py` — `PROMPT_BUILDER_VERSION = "1"`;
     `build_prompt(fixture, direction, purpose) -> str`.
     **Provider-neutral by signature** — no provider argument
     (operator discipline #2). Deterministic emission of
     fixture-spec fields in a canonical order + stable
     `[direction, reference kind/purpose, category]` trailer.
     Test suite asserts: byte-determinism across repeat calls;
     output changes with direction / purpose / fixture; every
     prompt carries the builder version stamp; signature has
     exactly `(fixture, direction, purpose)` — no provider
     parameter; no ratified provider name appears in any
     generated prompt; no aesthetic / detection language leaks.
   * `run_identity.py` — split of `run_id` (unique per
     invocation, embeds UTC timestamp +
     `bootstrap_<ts>_<fp12>` prefix) and `run_fingerprint`
     (deterministic sha256 hex of fixture content hashes +
     axes + provider models + profile versions +
     background-family schema hash + per-profile pipeline
     versions + prompt-builder version + execution mode +
     harness schema version). Fingerprint inputs explicitly
     EXCLUDE timestamps, random UUIDs, and filesystem paths
     (operator discipline #5). Test suite asserts: fingerprint
     stable across wall-time changes; stable across
     fixture-tuple reorderings; stable across filesystem
     re-loads; changes when execution_mode / prompt-builder
     version / pipeline version / background-family hash /
     provider model overrides / provider set / fixture
     content changes; run_id shape correct for bootstrap +
     round variants; execution_mode `unavailable` rejected.
   * `version.py` — `HARNESS_SCHEMA_VERSION = 1`.
   * 66 new tests in `media-engine/tests/benchmark_harness/`.
     Full media-engine collection: 804 pass + 16 skip (+66 vs.
     Step 7 close baseline of 738/16). Django `check` clean;
     `makemigrations --check --dry-run` reports "No changes
     detected"; `manage.py doctor` clean.
   * 8.a landing preserves every 8.a/b/c guardrail: NO
     provider execution (that's 8.b), NO evidence writing
     (also 8.b), NO substrate writes (Step 9), NO
     `bootstrap/references/` population (Step 9), NO scoring
     vocabulary emitted, NO consumer migration (Step 11).
   **✓ SHIPPED — 8.b** *(this commit)*: runner + atomic
   evidence writer + provider dispatcher + CLI. Executes the
   requested matrix through `PortraitProvider` +
   `NormalizationPipeline` and writes immutable two-tier
   evidence under the ratified §17.8.a fixture-runs layout.
   NO qualification decisions. New modules in
   `media-engine/app/services/benchmark_harness/`:
   * `evidence_paths.py` — locks the ratified §17.8.a
     bucketing (raw / normalized / manifests / observations /
     scores). Adds one new bucket `candidates/<cell_id>.json`
     for the single canonical evidence-record locator per cell
     + one new top-level directory `fixtures/_runs/<run_id>/`
     for the cross-fixture `run_summary.json`. Cell filename
     encoding `<fixture_id>__<reference_kind>__<reference_purpose>__<surface_profile>`
     documented; direction + provider are directory components
     per the ratified layout so they are not repeated in the
     filename. Observations bucket is created as an empty
     `.step8_empty_observations` marker so a future consumer
     can distinguish "no observations at Step 8" from "bucket
     never existed."
   * `evidence_writer.py` — append-only atomic writer. Refuses
     to overwrite an existing `run_id` at construction time
     (per operator discipline #4). Atomic writes via temp file
     + `os.replace` on the same filesystem. SHA-256 hashes
     every binary and JSON artifact (per operator discipline
     #6). Canonical JSON serialization (sorted keys, compact,
     `default=str`) so evidence written by two runs with
     identical payloads is byte-identical.
   * `provider_dispatcher.py` — `dispatch_cell(cell, fixture,
     surface_profile, run_fingerprint, cell_id, execution_mode,
     provider_model_override, settings, provider_factory)`.
     Never raises `PortraitProviderError` — every failure lands
     as a stable outcome from the ratified taxonomy (`success`,
     `provider_unavailable`, `provider_request_failed`,
     `unsupported_provider_capability`, `harness_error`).
     Deterministic mock seed derived from `sha256(run_fingerprint
     + cell_id)` so same-fingerprint runs produce byte-identical
     mock provider output per cell. Capabilities snapshot
     recorded even on failure paths.
   * `runner.py` — `run_matrix(fixtures, axes, execution_mode,
     provider_models, fixtures_root, settings, provider_factory,
     now)`. Loads surface profiles + background family;
     computes per-profile `pipeline_version`; mints the run
     identity (8.a's split of `run_id` + `run_fingerprint`);
     constructs the `EvidenceWriter` (append-only refusal
     fires here BEFORE providers run); iterates the expanded
     matrix; for each cell: dispatches provider, writes raw
     evidence FIRST (byte-for-byte, before normalization
     touches anything), creates the empty observations
     marker, runs `NormalizationPipeline` (default v1 chain
     — Crop v2 → Framing → BgReplacement), on norm-success
     writes normalized + manifest, on norm-failure preserves
     raw + records stable failure code (`input_smaller_than_output`
     for the Runway 1280x720 case per SESSION 246 finding),
     writes the canonical `candidate.json` locator. On a
     filesystem-level fatal failure (`OSError` / `IOError`)
     records remaining cells as `not_attempted_due_to_fatal_run_error`
     in the run summary and re-raises. Every other per-cell
     failure keeps the run going (per operator discipline #1).
     Run summary at `fixtures/_runs/<run_id>/run_summary.json`
     records: reproducibility axes, per-profile pipeline
     versions, fixture content hashes, background family
     schema hash, execution_mode (with a `contains_real_execution`
     flag + a factually-worded notice that mock runs are
     non-qualification per SESSION 244 constraint 7), a neutral
     `qualification_status: "not_evaluated"` guard (per
     operator discipline #10), planned cell keys + final
     status, counts by outcome/provider/profile/direction.
   * `cli.py` — `python -m app.services.benchmark_harness.cli`.
     Default `--execution-mode=forced_mock` (CI-safe). Real
     modes require explicit opt-in and print a stderr notice
     naming the operator-discipline anchor (per operator
     discipline #6).
   * `__init__.py` — re-exports all 8.b public surface.
   * Candidate JSON shape carries every operator-mandated
     Step-9 promotion field: `harness_schema_version`,
     `prompt_builder_version`, run identity, cell key,
     fixture_content_hash, identity branch/schema_version,
     `not_applicable_unscored` marker (`true` for
     fixture_nh1), provider stage (outcome, provider,
     provider_model, requested + actual execution_mode,
     capabilities snapshot, exact final prompt +
     prompt_snapshot, elapsed_ms, error {class, message}),
     raw artifact (path + sha256_hex + byte_count),
     normalization stage (attempted, outcome, pipeline_version,
     surface_profile_id/version, background_id, failure
     {stage_name, stable_code, message}, normalized artifact,
     manifest artifact, embedded manifest_payload for
     mechanical ingestion), written_at_utc.
   * 49 new tests in `media-engine/tests/benchmark_harness/`
     (evidence_paths, evidence_writer, runner mock matrix,
     runner success path via stub provider, provider-neutral
     prompt at runner level, execution-mode visibility,
     import boundary AST guard, no-qualification-vocabulary
     scan across every emitted evidence surface, Runway
     1280x720-shape via stub — proves the generic runner
     handles portrait-oriented refusal without Runway
     special-casing). Full media-engine collection: **853 pass
     + 16 skip** (+49 vs. 8.a close baseline of 804/16 = +115
     total 8.b harness tests). Django `check` clean;
     `makemigrations --check --dry-run` reports "No changes
     detected"; `manage.py doctor` clean.
   * 8.b preserves every 8.b/c guardrail: NO substrate writes;
     NO `bootstrap/references/` population; NO `scores/`
     writes; NO consumer migration; NO scoring vocabulary
     emitted (audit test covers every emitted surface); NO
     Runway special-casing (source-text scan enforces); NO
     real-provider spend in test suite (opt-in real modes are
     gated behind explicit CLI flag). Central Step 8 question
     partly answered in mock-only mode; final closure lives at
     8.c along with replay contract + full-matrix determinism
     + handoff.
   **✓ SHIPPED — 8.c** *(this commit)*: replay contract +
   closure invariants. New `replay.py` module ships the
   `replay_same_raw_input(source_run_id, fixtures_root,
   target_run_id?, now?)` API — reads every candidate from a
   prior immutable run, verifies raw SHA-256 against candidate
   record, re-runs the current default v1 NormalizationPipeline
   against the same raw bytes, writes replay evidence into a
   new run_id under the same §17.8.a layout, **never mutates
   the source run**. Deliberately narrow: reads raw evidence
   only; never calls PortraitProvider (that would be the Step
   10 concept `regenerate_provider_output`).
   Compatibility branching on `pipeline_version`:
   * **Match** → normalized bytes MUST be byte-identical;
     divergence raises `ReplayError` (Step 7 determinism
     regression, not a replay defect).
   * **Mismatch** → factual `pipeline_version_differs` note
     recorded on the replay candidate; both source + replay
     evidence preserved; not called a failure.
   Source integrity: refuses (`SourceRawHashMismatch`) when
   the raw file's on-disk hash disagrees with the recorded
   candidate hash; refuses (`SourceEvidenceMalformed`) when a
   candidate.json is missing required fields or the raw file
   claimed by candidate is gone; refuses (`SourceRunNotFound`)
   when no top-level `run_summary.json` exists for the source
   run_id.
   32 new tests (+147 total 8.a+8.b+8.c) covering:
   * `test_step8_closure.py` — pins cell status taxonomy;
     two-tier evidence invariant across success / provider-
     success-norm-fail / provider-failure cases; ratified
     bucketing preserved in both success + failure cases;
     `scores/` never created anywhere; both candidate + run
     summary carry `HARNESS_SCHEMA_VERSION`; provider
     capabilities snapshot canonically stable across runs;
     strengthened AST boundary guard (no legacy portrait
     services, no MediaEngineClient, no Django, no scoring,
     no bootstrap-review, and load-bearing NEW: no direct
     Pillow / rembg / opencv / onnx / numpy — harness
     ORCHESTRATES, never becomes another image-processing
     layer); no Step-9 state vocabulary in any emitted
     evidence (recursive JSON scan across every `.json` file
     under fixtures_root); `fixture_nh1` flows through same
     machinery with `not_applicable_unscored` marker
     preserved; ratified Mock's 256x256 output produces
     honest `input_smaller_than_output` normalization refusal.
   * `test_replay_same_raw_input.py` — happy-path byte-
     identical replay; source-run-not-found; source raw
     tamper; source raw missing; malformed candidate;
     pipeline-version mismatch records factual note without
     raising; provider-failure-source records
     `source_raw_absent`; normalization-failed-source
     reproduces same stable failure code; replay summary
     shape; replay append-only refusal on target_run_id
     collision.
   * `test_full_mock_reproducibility.py` — two independent
     runs with identical configuration but different wall
     times produce (a) same fingerprint + different run_id
     and (b) byte-identical deterministic components (cell
     set, prompts, cell_ids, raw hashes, normalized hashes,
     stable failure codes, capabilities snapshot, fixture
     hashes, manifest payload ex-timing) while observational
     fields (run_id, timestamps, elapsed_ms) differ. Locks
     operator discipline #4.
   * `test_fatal_run_matrix_completeness.py` — deliberate
     mid-matrix `os.replace` failure trips the runner's
     fatal-run bailout; completed cells preserved; remaining
     cells recorded as `not_attempted_due_to_fatal_run_error`
     in run_summary; `success + failed + not_attempted ==
     planned` invariant holds; fatal_run_error surfaces as
     `RuntimeError` from `run_matrix` after the partial
     summary lands. Locks operator discipline #5.
   Full media-engine collection: **885 pass + 16 skip** (+32
   vs. 8.b close baseline of 853/16). Django `check` clean;
   `makemigrations --check --dry-run` reports "No changes
   detected"; `manage.py doctor` clean.
   **Central Step 8 closure question answered YES** with
   executable evidence citations mapped to every operator-
   mandated invariant. See
   SESSION 247 handoff (internal handoff, preserved privately)
   §"The central closure question" for the 15+18 test-anchor
   list.
   **Methodology finding preserved for Step 10**: a "failed
   normalization" cell can still be successful benchmark
   evidence. The harness measures system boundaries; it does
   not redefine success as "every cell produced a final
   image." Provider bytes surviving a normalization refusal
   is exactly the shape of evidence needed to inform Step 10
   territory-selection decisions (upscale policy vs Runway
   aspect option vs Stability routing for portrait-oriented
   profiles).
   **$0.00 real-provider spend** across 8.a + 8.b + 8.c —
   every test uses ratified Mock or one of two test-only
   stubs. Real bootstrap execution is a deliberate operator
   action after the harness ships, not a Step 8 completion
   requirement.
9. **Bootstrap** — the sequence that produces the first
   approved reference set per fixture. Formally split into
   two independently gated sub-slices per SESSION 248
   operator ratification (see Revision History entry for
   2026-08-08). The split is anchored in the already-ratified
   §17.8.a Amendment 2 sequence, which enumerates initial
   provider generation (step 3), human review (step 4), and
   `bootstrap/references/` population (step 5) as three
   distinct sub-steps.

   * **9.a — Real bootstrap generation + immutable evidence
     freeze.** Operator-authorized real-provider run through
     the shipped Step 8 harness at `--execution-mode=real_required`.
     Produces `fixtures/<fixture_id>/runs/<bootstrap_run_id>/…`
     + `fixtures/_runs/<bootstrap_run_id>/run_summary.json`
     per §17.8.a Amendment 1. Writes zero substrate rows.
     Populates zero references. Makes zero human selections.
     **✓ SHIPPED — SESSION 248.** One controlled REAL_REQUIRED
     run against the ratified round-one fixture set
     (fixtures h1-h4; identity_only + softened_photographic;
     all seven human portrait_reference purposes; Stability +
     Runway; all five surface profiles). 560 planned cells,
     168 real Stability successes, 392 client-side
     `unsupported_provider_capability` refusals (280 Runway
     across all profiles under `1280:720`-only capability
     declaration; 112 Stability × studio/conversation under
     the `3:4`-absent capability declaration), 0 provider
     failures, 0 normalization failures, 0 retries. Zero
     Django substrate rows written. Evidence tree hash-
     verified (504 SHA-256 matches, 0 mismatches, 0 missing
     artifacts). run_id `bootstrap_20260808T044853Z_7eb392992e0f`,
     fingerprint `7eb392992e0fcc4a45767f4f6f8d85aedc44ef73e49ae19f46d7cfde603b3d0e`.
     Full handoff: SESSION 248 (internal handoff, preserved privately).

     **Methodological finding preserved for 9.b** (contract-
     load-bearing): a provider/profile cell that produces no
     reviewable image because the provider truthfully refuses
     the requested capability is still valid benchmark /
     bootstrap evidence. Step 9.b must render that absence as
     factual evidence; it must not reinterpret it as reviewer
     rejection. Anchored by §14.4 same-payload rule +
     §17.8.a Amendment 2 discipline 12 + the Step 8
     methodology finding preserved in SESSION 247.

     **Two bounded follow-up findings recorded (NOT repaired
     during 9.a closure):** Mock adapter `_aspect_to_dims`
     missing `4:5` mapping (surfaced during preflight dry-run
     only; does not affect REAL_REQUIRED); Runway + Stability
     current aspect-capability declarations leave three
     (provider × profile) combinations with zero reviewable
     candidates (Runway × any profile; Stability × studio;
     Stability × conversation) — routing / upscale / provider-
     widening resolutions are 9.b / Step 10 territory.

   * **9.b — Human review + selection + `bootstrap/references/`
     population + substrate persistence.** Admits per-fixture
     reference sets from the frozen 9.a evidence tree.
     Approved references land in
     `fixtures/<fixture_id>/bootstrap/references/`. Each
     fixture becomes qualification-ready. First substrate-
     writing slice in the §19.3 sequence: `CharacterIdentityVersion`
     (draft per §5.6.a), `IdentityReference` (approved per
     §13.1 step 4), `NormalizationManifest` (per approved
     reference), `GenerationRecord` (per 9.b scope-lock
     cardinality decision). Rejection audit preserved per
     §14.2 append-only discipline. **✓ SHIPPED — SESSION 249.**
     Five sub-slices (9.b.0 app skeleton + `bootstrap-fixtures`
     workspace + `IsOperator` gate; 9.b.1 read-only frozen-evidence
     browser + SHA-256-verified artifact streaming; 9.b.2
     append-only human-decisions journal at
     `bootstrap/review/<decision_id>.jsonl`; 9.b.3a canonical
     promotion service + `PromotionAudit` +
     `BootstrapEvidenceIndex` + resume command; 9.b.3b operator
     promotion surface + `bootstrap_review_gate` + Step-9 closure)
     landed the operator surface end-to-end. Load-bearing E2E test
     `shell/apps/bootstrap_review/tests/test_e2e_all_fixtures.py`
     walks all 4 human fixtures through review → promote →
     admit-version via the HTTP surface; asserts 4
     `CharacterIdentity` rows + 4 APPROVED
     `CharacterIdentityVersion` rows + 8 APPROVED
     `IdentityReference` rows + 8 `PromotionAudit` rows with
     `evidence_published_at_utc` set + revision folders with
     `.materialization_complete` sentinels; asserts
     `bootstrap_review_gate --all-fixtures` exits 0; asserts
     `fixture_nh1` excluded (no `CharacterIdentity`); asserts
     frozen 9.a subtree `git status --porcelain` empty after the
     full walk. Zero `ApprovedRepresentationBundle` rows — F3
     ratified that bundle is NOT required for bootstrap
     `approve_version` (bundle formation is Steps 12+ per §17.9.a
     deferred realtime lifecycle). Ten load-bearing findings
     (F1–F10) folded into the shipped architecture — canonical
     `frozen_candidate_id` replacing globally-non-unique
     `cell_id`; append-only revision-numbered folders with
     immutable `source.json`; review-completeness vs
     approval-floor distinction surfaced as two progress tiles;
     journal is git-tracked authoritative evidence;
     `PromotionAudit unique(decision_id)` + `BootstrapEvidenceIndex
     unique(frozen_candidate_id)` for race-safe dedup;
     `no_candidate_approved` amendments materialize via
     journal-driven canonical supersede (no `PromotionAudit` row);
     `NormalizationManifest.pipeline_version` widened
     `CharField(64)` → `TextField` to accept Step 7's shipped
     110-char compound encoding. Test totals at 9.b.3b close:
     `apps/bootstrap_review/` pytest 289 pass + 1 skip; full
     Django suite 2074 pass + 15 pre-existing failures; SPA
     vitest 562 pass across 38 files. Full handoff:
     SESSION 249 (internal handoff, preserved privately).
     Commit sequence: 9.b.0 `acdf53b`, 9.b.1 `7616743`, 9.b.2
     `032de53`, 9.b.3a `03e3f2a` + `03d7606` + `1a680af` +
     `e9e9905` + `20b4e52`, 9.b.3b `1e30ec5` (+ 5 paired
     `docs(inventory)` regen commits).
10. **Benchmark round one** runs. Evidence lands under
    `fixtures/<fixture_id>/runs/<benchmark_run_id>/…` per
    [§17.8.a Amendment 1](#178-fixture-authorship). Scoring
    records land under `scoring/` per
    [§17.7.a](#177-evaluation-instrument-shape). Chris scores;
    Claude records structured observations; disagreements are
    recorded, not resolved (§17.7.b).
11. **Existing read consumers migrate** slice-by-slice from
    the compatibility mirrors to the canonical substrate per
    [§17.9.a](#179-provider-adapter-migration-path) migration
    slices.
12. **Realtime-representation authoring lifecycle resolved**
    (§17.9.a deferred item). Protocol named and adapters
    landed. Realtime consumers migrate.
13. **Growth window closes** when every §17.10.a exit
    condition holds. Compatibility mirrors and mirror-write
    logic removed in a dedicated cleanup migration.
14. **R10 drift verifier extended** to cover
    `PortraitProvider`, `VoiceDesignProvider`, and the
    resolved realtime-representation Protocol per
    [§9.6](#96-sequencing-note--do-not-add-drift-verification-prematurely).
15. **Territory-selection cross-check** engaged with an
    external human reviewer per
    [§17.7.b](#177-evaluation-instrument-shape). Round-one
    evidence folded into Portrait Territory Study V2.

### 19.4 What still cannot be started

Blocked until Portrait Territory Study V2 lands (downstream of
step 15):

- Typography Study V1
- Color and Light Study V1
- Home Visual Canonical V1
- Onboarding visual proposal
- Default Alex casting
- Customer-facing wizard redesign per
  [§14.1](#141-wizard-changes-are-not-pre-benchmark-work)

The SESSION 238 blocker list survives this contract.

### 19.5 Amendment procedure

This contract is `ratified`, not `frozen`. Amendments require:

- The proposed change is written as an amendment to the
  affected §17 block (or as a new §17 group if it introduces
  a new decision surface).
- The amendment cross-references the ratification it changes.
- The revision history entry records what changed and why.
- The status field remains `ratified`; only frozen contracts
  reject amendments outright.

Structural rewrites that would invalidate the ten §17
ratifications require a new contract version
(`CANONICAL_IDENTITY_CONTRACT_V2.md`), not an amendment.

---

## Revision History

**ratified — 2026-08-08 (SESSION 249 close).** §19.3 row 9.b
flipped from `QUEUED — separately gated` to
`✓ SHIPPED — SESSION 249`. Step 10 status unchanged (remains
QUEUED and separately gated per §17.8.a Amendment 1 immutability
+ §17.7.a scoring contract). Five sub-slices landed the
operator surface end-to-end in one session (9.b.0 workspace +
gate; 9.b.1 read-only frozen-evidence browser; 9.b.2 append-only
human-decisions journal; 9.b.3a canonical promotion +
`PromotionAudit` + `BootstrapEvidenceIndex` + resume; 9.b.3b
operator promotion surface + `bootstrap_review_gate` + closure).
Load-bearing E2E test walks all 4 human fixtures through
review → promote → admit-version via the HTTP surface only;
asserts canonical substrate row counts (4 CharacterIdentity /
4 APPROVED CharacterIdentityVersion / 8 APPROVED
IdentityReference / 8 PromotionAudit), filesystem revision
folders with sentinels, gate-command exit 0, `fixture_nh1`
exclusion, and frozen 9.a subtree git-clean after the full
walk. Ten architectural findings folded during the arc: F1
canonical `frozen_candidate_id` replacing globally-non-unique
`cell_id`; F2 append-only revision folders with immutable
`source.json` (no `.prior/` scheme); F3 confirmation that
`ApprovedRepresentationBundle` is NOT required for bootstrap
`approve_version` (bundle formation is Steps 12+); F4
review-completeness (7-of-7 terminal dispositions) distinct
from approval-floor satisfaction (front + neutral_rest APPROVED);
F5 "staging" terminology retired for "promotion" / "revision
folder" / "canonical materialization"; F6 reviewer journal is
git-tracked authoritative evidence (sole durable record for
`no_candidate_approved` decisions); F7 `PromotionAudit
unique(decision_id)` for retry idempotency, not
`unique(frozen_candidate_id)`; F8 `BootstrapEvidenceIndex
unique(frozen_candidate_id)` for race-safe dedup at the DB
layer; F9 `no_candidate_approved` amendments materialize via
journal-driven canonical supersede (no `PromotionAudit` row) via
new substrate helper `services.supersede_reference_at_slot`;
F10 `NormalizationManifest.pipeline_version` widened
`CharField(64)` → `TextField` to accept Step 7's shipped
110-character compound encoding
(`pipeline_v1:crop@2|framing@1|background_replacement@1|profile:<pid>@1:<hash>|bg_family:v1:<hash>`).
Migrations added: `bootstrap_review/0002_promotion_audit_and_evidence_index`,
`identity/0009_normalization_pipeline_version_text`. Test totals:
apps/bootstrap_review/ 289 pass + 1 skip; full Django 2074 pass
+ 15 pre-existing failures (`realtime` / `scripts` /
`spokespeople`; verified pre-existing at 9.b.0 baseline);
SPA vitest 562 pass across 38 files. Zero `ApprovedRepresentationBundle`
writes. Zero `scores/` writes. Zero mutation of frozen 9.a
evidence (asserted by E2E test on every run). Zero
`PortraitProvider` / `benchmark` imports (asserted by 9.b.0's
AST boundary guard which auto-covers every new bootstrap_review
module). Full closure detail:
SESSION 249 handoff (internal handoff, preserved privately).

- Not a contract amendment. Row 9.b's ratified semantics are
  unchanged; only its status flips QUEUED → SHIPPED.
- Step 10 remains QUEUED. Do NOT open without explicit
  operator authorization. Step 10 lands benchmark round-one
  execution + first `scoring/` writes per §17.7.a; Chris
  scores; Claude records structured observations;
  disagreements are recorded per §17.7.b, not resolved.
- Retroactive documentation reconciliation. The five feature
  commits + five paired `docs(inventory)` regen commits
  landed in-session on 2026-08-08 and were pushed to
  `origin/main` at `093c4bd`. The Revision History entry,
  §19.3 row 9.b status flip, the internal SESSION 249 handoff (preserved privately)
  closure handoff, and start-here advance were folded into a
  post-close documentation-only reconciliation commit (also
  2026-08-08) after the drift was surfaced at the next
  session's orientation gate. Reconciliation touched zero
  code / migrations / tests / frozen evidence / promoted
  references.

**ratified — 2026-08-08 (SESSION 248).** §19.3 row 9 formally
split into 9.a (Real bootstrap generation + immutable evidence
freeze) and 9.b (Human review + selection + `bootstrap/references/`
population + substrate persistence). The split is documentary,
not structural — §17.8.a Amendment 2's already-ratified
sub-sequence (steps 3-5) is the underlying authority. Operator
ratified OPTION B after a two-stage architecture review that
established: (a) the two sub-slices have different actors,
different completion criteria, different mutability semantics,
and different codebases; (b) the shipped SESSION 247 harness
already enforces the boundary mechanically via an AST-level
Django-import guard and a CLI docstring line explicitly
disclaiming Step 9 responsibility; (c) sub-slicing is precedent
per V15.0-V15.4, R7.0-R7.3, R8.0-R8.2, and 8.a-8.c. 9.a
shipped this session under REAL_REQUIRED — one controlled run
producing 560 planned cells / 168 real Stability successes /
392 client-side `unsupported_provider_capability` refusals /
0 provider failures / 0 normalization failures / 0 Django
substrate writes / 0 `bootstrap/references/` writes /
`qualification_status: not_evaluated`. 9.b remains QUEUED and
separately gated.

- Not a reversal of any prior ratification. Extends §19.3
  sequencing discipline to reflect the operator's ratification
  of sub-slice discipline for a slice whose sub-responsibilities
  have distinct closure invariants.
- Not a scope extension. 9.a + 9.b together carry exactly the
  work §19.3 row 9 already scoped; the split changes only the
  gating cadence.
- Methodological finding **contract-load-bearing** for 9.b: a
  provider/profile cell whose provider truthfully refuses the
  requested capability is valid bootstrap evidence. 9.b must
  render that absence as factual evidence; it must not
  reinterpret it as reviewer rejection.

**ratified — 2026-08-07 (SESSION 243 open).** §5.6.a added
(state-semantics ratification) + §17.10.a gained **Amendment 4**
(prequalification-authored provenance) — landed together as the
prerequisite contract shape for §19 Step 4's compatibility mirror
discipline activation. Operator ratification recorded in the
SESSION 243 open message.

- **§5.6.a — State semantics.** `state='approved'` on identity /
  reference / bundle / voice / realtime rows means "currently
  admitted for product use," not "qualified." Qualification is a
  separate axis carried by `ImportProvenance` /
  `PrequalificationProvenance` presence, `spec_schema_version`, and
  a future explicit qualification status. Ratifies the operational
  convention already landed by Step 3 (SESSION 242).
- **§17.10.a Amendment 4 — Prequalification-authored provenance.**
  New provenance category for post-Step-4 canonical writes from
  existing production authoring flows that predate provider
  abstractions, the normalization pipeline, and the branch schema's
  approval floor. New `PrequalificationProvenance` model, sibling to
  `ImportProvenance` with mutual exclusion. Real provider enum on
  `GenerationRecord` + non-NULL execution fields (preserves
  Amendment 3 invariant; only `LEGACY_IMPORTED` records carry NULL
  execution). New services: `approve_bundle`, `supersede_bundle`,
  `approve_reference` (with `SUPERSEDED` state added to
  `ReferenceState`), `approve_prequalification_version`,
  `record_prequalification_representation`. Three new Postgres
  partial unique constraints: one on
  `ApprovedRepresentationBundle`, one on `IdentityReference`
  `(identity_version, kind, purpose) WHERE state='approved'`, plus
  the new provenance table's OneToOne guarantee. Compatibility
  adapter reads `prompt_snapshot["legacy_value"]` for legacy
  imports and `prompt_snapshot["provider_voice_id"]` /
  `["provider_realtime_id"]` for prequalification-authored records.
  Compatibility null convention: mirrors physically stay `""` for
  the growth window; `None → ""` sync encoding. Full orphan matrix
  for the consistency verifier. Direct-write allowlist post-Step-4
  narrows to `apps/identity/compat.py` + historical migrations +
  tests.
- Amendment 4 does **not** amend §17.10.a exit conditions or §5.4
  ("what triggers a new version"). Every representation-set change
  still creates a new version per §5.4; prequalification authoring
  events land as new versions with empty spec.
- Not a reversal of any prior ratification. Extends Amendment 2's
  provenance vocabulary.

**ratified — 2026-08-07 (post-SESSION 242 correction).** §17.10.a
gained **Amendment 3** — legacy imports carry NULL execution
fields, not the SESSION 242 `LEGACY_HISTORICAL` enum values.

- The SESSION 242 `ExecutionMode.LEGACY_HISTORICAL` and
  `ExecutionModeActual.LEGACY_HISTORICAL` enum additions were
  surfaced in the SESSION 242 handoff as a contract-fidelity
  flag (never ratified). Operator review of the landed
  implementation determined the accommodation belonged in
  provenance vocabulary rather than execution vocabulary and
  had to be resolved before Step 4's compatibility-consistency
  verifier landed against a substrate whose execution metadata
  it trusts.
- Amendment 3 makes both execution fields nullable and defines
  NULL as the specific semantic "no provider execution occurred
  through the execution framework for this row." Legacy imports
  carry NULL / NULL. Executable provider records carry both
  fields non-NULL. Half-null is refused.
- `LEGACY_HISTORICAL` removed from both enums. Origin is carried
  by `GenerationProvider.LEGACY_IMPORTED` + `ImportProvenance`
  + `spec_schema_version = 0` (three orthogonal markers that
  already existed after SESSION 242).
- `ExecutionMode.UNAVAILABLE` remains distinct from NULL —
  test suite locks the semantic separation.
- Migration `identity/0003_execution_mode_nullable` lands the
  change forward + defines the reverse operation using string
  literals (`'legacy_historical'`, `'legacy_imported'`) rather
  than enum references, so reversal does not depend on the
  removed enum members being present in current source.
- **Not a reversal of prior ratification.** SESSION 242's enum
  additions were surfaced-not-ratified; this amendment closes
  the outstanding flag and establishes the permanent shape
  before §19 Step 4 opens.

**draft — 2026-08-06 (amended, same day).** §17.1, §17.2, and
§17.3 ratified in walkthrough. Latest amendments (§17.3):

- §17.3.a ratified: JSONB `spec` column on
  `CharacterIdentityVersion`, schema-validated by `kind`.
  Explicit `spec_schema_version` required. Human and non-human
  branches use separate validators. Provider-specific values,
  generation evidence, normalized outputs, and approval history
  stay outside `spec`. Authoritative write-path stack corrected
  from the recommendation: typed schema validation → dedicated
  identity-version service → model-level defensive validation →
  tests proving unsupported write paths cannot introduce
  invalid payloads. Service layer is authoritative; model
  validation is an additional guard. No reliance on
  `Model.save()` as the primary funnel.
- §17.3.b ratified: partial unique constraint + transition
  service (both). Constraint semantics:
  `UNIQUE (character_identity_id) WHERE state = 'approved'` with
  stable name. Transition service must lock with
  `select_for_update()`, run supersede + approve in one
  `transaction.atomic()`, be idempotent on re-approval of
  current, reject invalid transitions before touching current
  approved, convert constraint violations into a stable domain
  exception, record who/what/when approved, and never use
  `bulk_update()`. Postgres integration tests enumerated.
- §15.2 amended: substrate description updated to reflect the
  ratified JSONB storage and partial-constraint enforcement.
  No longer marked "deferred."

Earlier amendments in this revision (§17.10 — closes §17):

- §17.10.a ratified with two amendments. Three legacy fields
  (`runway_avatar_id`, `portrait_path`, `voice_id`) become
  **temporary compatibility mirrors** on the (renamed)
  `Teammate` model during the strangler migration window.
  Canonical substrate is the source of truth immediately;
  mirrors are not independent identity state.
- **Authoritative-write rule** with layered enforcement (not
  `save()` alone): canonical services as sole write API;
  existing mutation call sites migrated immediately; tests
  audit known write paths; model-level defensive guards where
  practical; DB permissions/triggers only if evidence warrants.
- **Amendment 1 — mirror state must be measurable.**
  Compatibility-consistency verifier asserts mirror ↔
  canonical equality per `Teammate`. Drift fails tests and
  appears in audit tooling. **Sync is canonical → mirror only.
  Never bidirectional.**
- **Amendment 2 — bootstrap and null semantics.** Existing
  legacy values imported into a bootstrap
  `CharacterIdentityVersion` with `legacy_imported` provenance;
  no historical provider facts invented; legacy imports are
  not benchmark-qualified. Provenance vocabulary distinguishes
  `legacy_imported` / `approved` / `qualification_validated`.
  Missing canonical value → null mirror; stale mirrors are
  never preserved past canonical removal.
- **Realtime identifier caveat:** `runway_avatar_id` preserved
  as compatibility mirror only; not encoded into the permanent
  `CharacterIdentity` schema; not permitted to force the
  future realtime-representation model. Cross-references
  §17.9.a's deferred realtime-representation authoring
  lifecycle.
- 10-step migration sequence ratified. 8 exit conditions
  enumerated. Prohibition against permanent denormalized-cache
  repurposing recorded.
- Substrate consequence applied: §15 gained §15.7 recording
  the compatibility-mirror discipline. §15 numbering fixed
  (15.6 → 15.7 → 15.8).
- **§17 CLOSED.** All ten decision groups (17.1 through
  17.10) resolved with recorded amendments.
- Frontmatter status flipped from `draft` to `ratified`.
- §19 rewritten as the actual **implementation gate** —
  prerequisite documents (§19.1), deferred items still open
  (§19.2), 15-step ratified implementation sequence (§19.3),
  work still blocked downstream of Portrait Territory Study
  V2 (§19.4), amendment procedure (§19.5).

Earlier amendments in this revision (§17.9):

- §17.9.a ratified with a critical amendment. **Grow-alongside
  accepted as a strangler pattern**, not permanent duplication.
  Seven-step strangler sequence recorded (introduce →
  benchmark-use → validate → stabilize → endpoint delegates →
  external consumer migration → cleanup). Freeze rule for
  existing direct paths: no new consumers, no new provider-
  specific behavior, bug fixes only until migrated.
- **`PortraitProvider` ratified** with Stability, Runway still-
  portrait, and Mock adapters; factual capability inspection;
  execution-mode and provenance recording.
- **`AvatarProvider` NOT ratified.** The word "avatar" is a
  legacy endpoint term, not a domain boundary. Multiple
  distinct lifecycles may live under it (realtime
  representation, portrait enrollment, character identifier,
  still generation, motion representation). Canonical identity
  contract must first resolve input / artifact / ownership /
  portability / bundle participation / lifecycle location.
  Temporary architectural term for discussion:
  `RealtimeRepresentationProvider`. Not a ratified name.
- Post-validation migration slices enumerated (8 slices, each
  preserving request/response compatibility, workspace
  isolation, execution-mode reporting, provider provenance,
  mock behavior, existing tests).
- Growth-window exit conditions enumerated (7 measurable
  conditions; all must hold to close the window).
- §9.3 amended: `PortraitProvider` marked ratified;
  `AvatarProvider` entry replaced with a deferred-decision
  block explicitly recording that the realtime-representation
  authoring lifecycle is unresolved; `VoiceDesignProvider`
  cross-reference added to §17.4.a.
- §18 amended: two new deferred items added — the realtime-
  representation authoring lifecycle question, and the growth-
  window exit conditions as an operational milestone.

Earlier amendments in this revision (§17.8):

- §17.8.a ratified with two amendments. Canonical round-one
  fixture set locked at **five fixtures**: `fixture_h1`
  (baseline), `fixture_h2` (facial hair), `fixture_h3`
  (deliberately difficult), `fixture_h4` (demographic contrast),
  `fixture_nh1` (non-human substrate exercise). Adaptive
  expansion allowed only when documented evidence identifies a
  specific blind spot.
- **Amendment 1: fixture definition separated from generated
  evidence.** Ratified directory shape:
  `fixtures/<fixture_id>/{identity.yaml, rationale.md,
  bootstrap/references/, runs/<benchmark_run_id>/<direction>/<provider>/{raw,normalized,manifests,observations,scores}/}`.
  Prevents later benchmark rounds from overwriting or confusing
  earlier evidence.
- **Amendment 2: fixtures are authorable before approved
  references exist.** A fixture becomes qualification-ready
  only after bootstrap references have been approved. Sequence:
  author identity + rationale → generate candidates under runs/
  → human review selects → approved copies land in
  bootstrap/references/ → regeneration and cross-provider
  testing use the approved set.
- Prerequisite artifacts enumerated (must land before fixture
  authoring): human identity schema, non-canonical non-human
  test schema, controlled background family, human + machine
  scoring schemas, scoring template, authoring guide.
- Load-bearing rule recorded: every provider and rendering
  direction receives the **same versioned fixture payload**. A
  fixture tuned per provider is disqualified as cross-provider
  evidence.
- §17.8.b ratified: branch-prefixed coded identifiers only
  (`fixture_h1`, `fixture_nh1`). Canonical and immutable once
  benchmark evidence references them. No personal names as
  identifiers. Descriptive labels permitted in `rationale.md`
  only under strict rules (fictional/descriptive, no real
  acquaintances, no implied Alex candidacy, not in provider
  prompts unless required, never replace canonical ID in
  evidence records). Numbering must not imply quality; catalog
  README states ordering reflects authorship sequence only.
- Substrate consequences applied: §14.4 fixture-set section
  updated with canonical identifiers and adaptive-expansion
  rule; §13.3 added recording the ratified directory semantics
  and bootstrap-flow directory landings; qualification-directory
  `README.md` prospective structure updated to reflect the
  ratified fixture, schemas, and scoring layouts.

Earlier amendments in this revision (§17.7):

- §17.7.a ratified with amendments. Repository-first scoring
  accepted, with the schema treated as a **contract**: three
  companion artifacts under
  `docs/design/visual/portrait_qualification/scoring/` — a
  human-readable `SCORING_SCHEMA_V1.md`, a machine-validatable
  `scoring.schema.json`, and a canonical `scoring-template.yaml`.
  Every scoring record carries immutable metadata (benchmark
  round, schema version, pipeline version, normalization
  version, fixture version, provider, direction, execution
  mode, reviewer, timestamp) so records remain comparable
  across future benchmark rounds. Evidence is append-only:
  amendments append with a recorded reason; history never
  disappears.
- §17.7.b ratified with amendments. Chris is sole scoring
  reviewer for round one. Claude provides structured
  observations (Observed Artifact / Observed Behavior /
  Potential Concern / Supporting Evidence / Confidence /
  Affected Benchmark Dimension(s)) — never free-form
  commentary, never scores. Operator-vs-observation
  disagreements are recorded, not resolved; consistent
  disagreement patterns become their own examinable evidence.
  External human review reserved for the final territory-
  selection decision only.
- §14.2 amended: reflects the three-artifact schema-as-contract
  shape, the immutable metadata requirement, the append-only
  discipline, and the reviewer discipline.

Earlier amendments in this revision (§17.6):

- §17.6.a ratified with amendments. Round-one normalization
  scope: canonical crop + surface-specific framing + eye-line
  normalization + background replacement from Portrait Language
  §18's controlled family. Explicitly deferred until later
  benchmark evidence justifies them: color grading, white
  balance, exposure, relighting, shadow synthesis, skin-tone
  normalization, AI beautification.
- Two-tier evidence strongly accepted: raw provider output and
  normalized output are both preserved as immutable artifacts;
  normalized never overwrites raw.
- **New required artifact — Normalization Manifest:** every
  generation emits a structured record of exactly what the
  pipeline did (crop profile, framing, background id, eye-line
  adjustments, pipeline version, stages executed, stages
  skipped, execution duration). Enables full reproducibility
  from raw + manifest.
- **Determinism constraint (load-bearing):** identical raw +
  pipeline version + manifest → byte-for-byte identical
  normalized artifact. No randomness. Randomness would make
  provider comparisons impossible.
- **Provider output as canonical evidence:** normalization is
  interpretation, not truth. Never lose access to the original
  provider artifact.
- **Stage architecture:** ordered pipeline stages, each
  independently enable/disable/versioned. Enables questions
  like *"did lighting normalization actually improve reviewer
  trust?"* without pipeline rebuild.
- **Surface profiles as data:** Compact / Presence / Studio /
  Conversation / Team Card defined declaratively (crop ratios,
  eye position, margins, output resolution, framing behavior).
  Pipeline consumes profiles; adjustments are config, not code.
- **Production vs. benchmark policy:** benchmark preserves all
  three artifacts; production may cache only normalized while
  retaining raw. Retention layer decides; pipeline always
  produces all three.
- Substrate consequences applied: §10 gained sections 10.6
  (manifest), 10.7 (stage architecture), 10.8 (surface profiles
  as data), 10.9 (production policy). §15.6 restructured — the
  earlier single `NormalizationProfile` table split into
  `SurfaceProfile` (declarative data, not a DB table),
  `NormalizationManifest` (per-generation immutable record),
  and an optional deferred per-identity `NormalizationProfile`
  for future per-identity overrides.

Earlier amendments in this revision (§17.5):

- §17.5.a ratified with amendment: reference relationships carry
  a **`kind` + `purpose`** structured pair, not a single flat
  enum. Amendment: `kind` describes the artifact class
  (`portrait_reference`, `motion_reference`, `speech_reference`,
  `body_reference`, `environment_reference`, `expression_reference`);
  `purpose` describes how the artifact participates in identity
  (`front`, `slight_left`, `slight_right`, `neutral_rest`,
  `listening`, `consideration`, `gentle_positive`). Not
  everything collapses under `canonical_reference` — that would
  push all future evolution into `purpose` and lose the meaning
  of `kind`. Purpose values are branch-schema-validated;
  adding purpose values does not require a Django migration;
  invalid purposes fail immediately at the authoritative write
  path. Reference identity notation locked as `<kind>/<purpose>`.
- §17.5.b ratified with amendment: minimum approval floor plus
  separate bundle-level surface availability — both defined
  **declaratively in the identity branch schema**, not
  hardcoded in transition or bundle code. Schema declares
  `required_for_identity` and `surface_requirements`. Human
  schema initial values recorded illustratively (round-one
  floor: `portrait_reference/front` + `portrait_reference/neutral_rest`;
  Home / Presence / Studio / Live Conversation surface
  requirements sketched). Human schema lands under
  `docs/design/visual/portrait_qualification/schemas/` when
  §17.8 fixture authorship is opened.
- §7.3 amended: rewritten as "Reference kinds and purposes"
  reflecting the structured pair and notation convention.
- §15.4 amended: `IdentityReference` illustrative shape gains
  a `purpose` field alongside `kind`.
- §6.6 added: surface availability is declarative — the bundle
  evaluator computes supported surfaces from the schema's
  `surface_requirements`, not from special cases in code.

Earlier amendments in this revision (§17.4):

- §17.4.a ratified: `VoiceDesignProvider` accepted as its own
  Protocol with registry, mock implementation, capability
  introspection, provenance recording, execution-mode tracking,
  and future provider independence. Ten architectural
  requirements recorded verbatim, load-bearing among them:
  bundles are provider-neutral (callers ask for "approved
  voice," never for a provider ID); capability reporting
  factual not subjective; identity consistency verified across
  portrait + voice + bundle at the same revision; no
  provider-specific branching outside the adapter layer.
  Substrate consequences applied: §6.2, §11, §15.3 amended to
  move provider details out of the bundle onto separate
  canonical-voice-reference and canonical-realtime-reference
  records that carry their own provenance via
  `GenerationRecord`.

Earlier amendments in this revision (§17.2):

- §17.2.a ratified: ownership of the non-human spec schema is
  permanently held by the future Character Presence Language.
  Deferral is ownership-permanent, not document-immutable — a
  future compatibility amendment is allowed but this contract
  must not become the source of truth for non-human visual
  rules. Cross-branch substrate requirements listed explicitly.
- §17.2.b ratified: one non-human fixture in benchmark round
  one, for substrate-exercise purposes only. Aesthetic
  dimensions marked `not_applicable_unscored`. Branch-neutral
  reference-kind preference recorded (informs §17.5).
  Provider failures on non-human inputs recorded as capability
  evidence, not substrate failures. No non-human rendering-
  territory conclusions permitted from this round.
- §3.4 amended: ownership-vs-immutability clarification added
  per §17.2.a ratification.
- §14.4 amended: non-human fixture bullet cross-references
  §17.2.b ratification so readers landing at the fixture list
  do not miss the round-one constraints.

Earlier amendments in this revision (§17.1):

- §17.1.a ratified: `CharacterIdentity` is the internal substrate
  name; customer-facing language remains `teammate`; downstream
  naming discipline established (`CharacterIdentity`,
  `CharacterIdentityVersion`, `IdentityReference`,
  `ApprovedRepresentationBundle`, `GenerationRecord`,
  `NormalizationProfile`); substrate name does not determine
  customer-facing API or URL vocabulary.
- §17.1.b ratified: `Spokesperson` → `Teammate` rename accepted as
  a focused pre-substrate refactor session, with the constraint
  set the operator specified (preserve historical text, preserve
  DB tables initially, `/api/spokespeople/` as compat route,
  `/api/teammates/` introduced deliberately). Sequence locked:
  rename first, then update this contract's forward-looking
  `spokesperson` references, then implement the substrate.
- Contract-scope naming applied in this edit: model formerly
  described as `IdentityReferenceRelationship` renamed to
  `IdentityReference` in §15.4 and §16.1. Concept unchanged.
- Not preempted in this edit (deliberately): the `spokesperson fk`
  reference in §15.1 remains until sequence step 2 of the ratified
  17.1.b sequence.

Remaining §17 groups (17.2 through 17.10) unresolved.

**draft — 2026-08-06.** First draft. Written as a corrective
follow-up to the SESSION 238 audit that recommended a substrate-
first sequence without a contract-review pass first. Reflects the
operator's 18 corrections dated 2026-08-06:

- Contract-review pass required before any model or migration.
- Field classification (seven categories) prevents wide-schema
  drift from mechanically materializing every Portrait Language
  concept as a column.
- Provider provenance separated from identity substrate.
- Domain ownership decision surfaced (`CharacterIdentity` over
  attaching directly to `Spokesperson`).
- Non-human compatibility treated as a blocking schema requirement
  via a branch discriminator.
- Voice-to-portrait binding moved off model `clean()` and onto an
  approved representation bundle.
- Identity versioning made explicit with four states.
- Reference-view semantics carried on a typed relationship record
  rather than in an exploding `Asset.role` enum.
- Normalization defined as a contract with an input and output
  shape, not as an image-processing implementation.
- Capability introspection restricted to factual technical
  capabilities; territory suitability moved to benchmark evidence.
- Provider abstractions split by lifecycle (portrait / avatar /
  realtime / TTS) rather than collapsed under one method.
- Execution-mode recording introduced (`forced_mock` / `auto` /
  `real_required` / `unavailable`) as a universal provider-boundary
  concept.
- Protocol-drift enforcement sequenced after abstraction
  stabilization, not before.
- Wizard redesign explicitly excluded from pre-benchmark work.
- Evaluation instrument scoped to repository-first artifacts before
  any Django scoring model.
- Benchmark fixture set expanded beyond a single "Alex" including
  facial-hair, non-human, and a deliberately difficult case.
- Bootstrap flow for the first approved reference set made
  explicit.
- Manual-review boundary preserved as the only path to canonical
  approval; automated similarity metrics restricted to signaling.

Unresolved decisions are enumerated in
[§17](#17-unresolved-decisions-requiring-operator-resolution).
