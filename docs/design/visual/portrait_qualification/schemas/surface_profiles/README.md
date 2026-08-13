# Surface Profiles

Ratified in
[`CANONICAL_IDENTITY_CONTRACT_V1.md`](../../CANONICAL_IDENTITY_CONTRACT_V1.md)
§10.8 and §17.6.a — surface profiles are **declarative data**
consumed by the normalization pipeline at run time, not
embedded layout logic.

Each profile defines: crop ratios, eye position, margins,
output resolution, framing behavior.

## Round-one profiles

Five profiles authored for round-one benchmark:

| Profile file | Framing family (Portrait Language §4) | Product surfaces that consume it |
|---|---|---|
| [`compact.yaml`](compact.yaml) | Compact identity portrait | Piece Detail byline; other small identity markers |
| [`presence.yaml`](presence.yaml) | Presence portrait | Home; My Team detail |
| [`studio.yaml`](studio.yaml) | Conversational portrait | Studio teammate presence pane |
| [`conversation.yaml`](conversation.yaml) | Conversational portrait | Live Conversation |
| [`team_card.yaml`](team_card.yaml) | Compact identity portrait | My Team list cards |

**Framing families are locked** by Portrait Language §4.
**Surface profiles are the machine-readable form** of those
framing families plus per-surface variation (resolution,
tonal environment class). Studio and Conversation share the
conversational-portrait framing but differ in tonal
environment (Conversation runs darker per Portrait Language §8).

## Product-surface → profile mapping

The `human_identity_schema_v1.yaml` `surface_requirements`
section names product surfaces (Home, Presence, Studio,
Live_Conversation, My_Team_Detail, My_Team_Card,
Piece_Detail_Byline). Each product surface consumes one
profile. The mapping:

- `Home` → `presence`
- `Presence` → `presence`
- `Studio` → `studio`
- `Live_Conversation` → `conversation`
- `My_Team_Detail` → `presence`
- `My_Team_Card` → `team_card`
- `Piece_Detail_Byline` → `compact`

## Rules

- **Profiles are data, not code.** Adding a profile is a new
  file; adjusting a profile is a config change. No pipeline
  code change is required for either.
- **Every profile carries a stable identifier** so
  Normalization Manifests remain reproducible across benchmark
  rounds (§10.6 determinism constraint).
- **Every profile carries a version integer.** Changing a
  profile's parameters bumps the version. Old manifests
  reference the version they were produced against; the
  original values remain interpretable.
- **Profile identity is `<profile_id>@<version>`.** Manifests
  record the exact pair.

## What profiles do NOT specify

- Colors — that is Portrait Language §8 tonal / background
  discipline, applied by later normalization stages (deferred
  in round one per §17.6.a).
- Aesthetic register — that is Portrait Territory Study V2,
  downstream of round-one benchmark.
- Font, iconography, or product chrome — surface profiles
  scope to the teammate's framing within a rendered portrait,
  not to the UI around it.
