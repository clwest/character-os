# Case Study 01 — Stability portraits broke Runway lip-sync

**Date:** SESSION 171 (mid-arc).
**Systems:** media-engine image providers, Runway avatar bake.

## Problem

The initial plan was to keep Stability AI (SD3) as a portrait
provider alongside Runway `gen4_image`. Stability is cheaper
and produces excellent stylized portraits.

Operator dogfood on a real spokesperson (Marcus, mascot
template) revealed that avatars baked from Stability portraits
mis-lip-synced. The mouth region drifted during speech in a way
that Runway-portrait avatars never did.

## Evidence

The failure was visible, not measurable. A ~15s test clip:

- Runway `gen4_image` portrait → baked avatar → clean sync.
- Stability SD3 portrait → baked avatar → visible dental
  artifacts, mouth-region tracking drift, particularly on
  bilabial and dental consonants.

Same script, same voice, same avatar rig.

## Root cause

Runway's avatar rig is trained on `gen4_image` face geometry.
The rig assumes specific facial landmark placement that
Stability's SD3 model does not reliably produce. Stability
portraits are photorealistic but off-manifold from Runway's
training data.

This is not a Stability bug. It is a compatibility issue that
would not surface without cross-provider dogfood.

## Decision

Reject the AI's proposal to keep Stability as a portrait
provider. Reframe Stability's role:

- **Retained:** scene generation, b-roll, product imagery,
  library assets — anywhere the output does not feed the Runway
  avatar rig.
- **Removed:** avatar portrait source. Runway `gen4_image` is
  now the sole avatar portrait provider.

## Implementation change

- Provider-role guardrails codified in `MediaEngineClient` +
  primitives routing.
- Portrait rebake action (`POST /api/spokespeople/{id}/rebake_portrait/`)
  gated to Runway `gen4_image` for anything that will feed the
  avatar rig.
- Stability provider remained in
  `media-engine/app/services/stability_ai_service.py`, invoked
  from scene / b-roll / product primitives.

## Verification

Operator re-baked Marcus with Runway `gen4_image` end-to-end.
Sync artifacts cleared. SESSION 158 real-Runway spend later
confirmed the calibration held across multiple spokespersons
(Sasha + `clara` voice: publishable; Donny + `drew` voice:
dental artifacts on Donny — attributed to the voice, not the
portrait).

## Lasting rule

**Provider role-fit matters more than provider quality.** A
"better" image provider whose output is off-manifold from a
downstream model's training distribution will produce worse
end-to-end results than a middling provider that is on-manifold.

This shows up in
[`docs/architecture/PROVIDER_MAP.md`](../architecture/PROVIDER_MAP.md)
as an explicit Runway-only rule for avatar portraits.
