"""Deterministic, provider-neutral prompt builder.

**One job.** Deterministic translation from ``(fixture,
direction, purpose)`` into a single final prompt string that the
``PortraitProvider`` adapters consume verbatim.

Load-bearing rules (per SESSION 247 operator disciplines #1 and
#2):

* **Provider-neutral.** ``build_prompt`` takes NO provider
  argument. The same logical candidate MUST produce the same
  final prompt regardless of which adapter dispatches it. Any
  provider-specific transport syntax lives inside the adapter,
  not in the harness. A test enforces the absence of a provider
  parameter via ``inspect.signature``.

* **Versioned.** Every prompt carries the builder version stamp
  so prior evidence remains identifiable as produced by the
  older builder. If prompt construction changes semantically,
  bump ``PROMPT_BUILDER_VERSION`` first; do not silently mutate
  v1's output shape.

* **Not aesthetic optimization.** The builder emits the fixture
  spec verbatim (in a canonical field order) plus a stable
  header naming direction + purpose. It does NOT choose
  adjectives, tone, adaptive phrasing, or provider-specific
  hints. If the builder ever starts making phrasing choices to
  "help" a provider, cross-provider evidence becomes invalid.

* **Deterministic.** Same inputs → byte-identical output. Every
  code path is a pure function of the arguments. No dict
  iteration order, no timestamps, no environment variables.
"""
from __future__ import annotations

from typing import Any, Mapping

from .fixture_loader import LoadedFixture
from .vocabulary import (
    HumanPortraitReferencePurpose,
    IdentityBranch,
    NonHumanCanonicalReferencePurpose,
    RenderingDirectionHypothesis,
)


PROMPT_BUILDER_VERSION: str = "1"
"""Version of the prompt-builder deterministic mapping.

Bumped when:

* the emitted field order changes
* a new fixture-schema field is folded into the prompt
* the header format changes
* the direction / purpose encoding format changes

NOT bumped when:

* a fixture's *content* changes (that shows up in the fixture's
  content_hash, which is a separate fingerprint input)
* an adapter changes how it interprets the prompt

The builder version is included in every candidate's evidence
manifest AND in the run fingerprint so prior evidence stays
identifiable as v1 output even after v2 lands.
"""


# ---- Purpose category discriminator --------------------------
# From ``purpose_schema_human_v1.yaml``: 'view' purposes vary
# camera axis; 'expression' purposes vary facial state. Emitted
# as an explicit label in the prompt so provider adapters (or
# their downstream) don't have to guess.

_HUMAN_PURPOSE_CATEGORIES: dict[str, str] = {
    HumanPortraitReferencePurpose.FRONT.value: "view",
    HumanPortraitReferencePurpose.SLIGHT_LEFT.value: "view",
    HumanPortraitReferencePurpose.SLIGHT_RIGHT.value: "view",
    HumanPortraitReferencePurpose.NEUTRAL_REST.value: "expression",
    HumanPortraitReferencePurpose.LISTENING.value: "expression",
    HumanPortraitReferencePurpose.CONSIDERATION.value: "expression",
    HumanPortraitReferencePurpose.GENTLE_POSITIVE.value: "expression",
}

_NON_HUMAN_PURPOSE_CATEGORIES: dict[str, str] = {
    NonHumanCanonicalReferencePurpose.FRONT.value: "view",
}


class PromptBuilderError(Exception):
    """Raised on unknown direction, unknown purpose for branch,
    or a fixture whose payload is missing a required field the
    builder wants to emit.
    """


def _purpose_category(branch: IdentityBranch, purpose: str) -> str:
    if branch == IdentityBranch.HUMAN:
        return _HUMAN_PURPOSE_CATEGORIES.get(purpose, "unknown")
    return _NON_HUMAN_PURPOSE_CATEGORIES.get(purpose, "unknown")


def _validate_axes(
    fixture: LoadedFixture, direction: str, purpose: str
) -> None:
    valid_directions = {d.value for d in RenderingDirectionHypothesis}
    if direction not in valid_directions:
        raise PromptBuilderError(
            f"unknown rendering direction {direction!r}. "
            f"Ratified set: {sorted(valid_directions)}"
        )
    if fixture.branch == IdentityBranch.HUMAN:
        valid_purposes = {p.value for p in HumanPortraitReferencePurpose}
    else:
        valid_purposes = {p.value for p in NonHumanCanonicalReferencePurpose}
    if purpose not in valid_purposes:
        raise PromptBuilderError(
            f"purpose {purpose!r} is not ratified for branch "
            f"{fixture.branch.value!r}. Ratified: {sorted(valid_purposes)}"
        )


def _emit_human_identity_lines(spec: Mapping[str, Any]) -> list[str]:
    """Emit fixture-spec fields in a stable order.

    Field order below is authored deliberately. Adding a field
    requires a builder version bump. Removing a field requires a
    builder version bump. Reordering requires a builder version
    bump. The order is:

        age_presentation
        skin_tone
        hair
        facial_hair (only when present=True)
        eye
        face_shape
        gender_presentation
        canonical_outfit
        visible_disability (only when present)
        preferred_default_framing (only when present)
        lighting_baseline
        expression_baseline_notes (only when present)
    """
    lines: list[str] = []

    age = spec.get("age_presentation", {})
    lines.append(
        f"Age presentation: {int(age.get('min_years', 0))}–"
        f"{int(age.get('max_years', 0))} years."
    )
    if age.get("notes"):
        lines.append(f"Age notes: {age['notes'].strip()}")

    skin = spec.get("skin_tone", {})
    lines.append(
        f"Skin tone: {skin.get('descriptor', '').strip()} "
        f"(undertone: {skin.get('undertone', '')})."
    )
    if skin.get("tonal_range_notes"):
        lines.append(f"Skin tonal range: {skin['tonal_range_notes'].strip()}")

    hair = spec.get("hair", {})
    lines.append(
        f"Hair: length {hair.get('length', '')}, texture "
        f"{hair.get('texture', '')}, color "
        f"{hair.get('color', '').strip()}."
    )
    for opt in ("style_notes", "hairline", "part", "volume"):
        if hair.get(opt):
            lines.append(f"Hair {opt}: {str(hair[opt]).strip()}")

    facial_hair = spec.get("facial_hair", {})
    if facial_hair.get("present"):
        parts = [f"style {facial_hair.get('style', '')}"]
        if facial_hair.get("density"):
            parts.append(f"density {facial_hair['density']}")
        if facial_hair.get("color"):
            parts.append(f"color {facial_hair['color']}")
        lines.append(f"Facial hair: present; {'; '.join(parts)}.")
    else:
        lines.append("Facial hair: absent.")

    eye = spec.get("eye", {})
    line = f"Eye: color {eye.get('color', '')}, shape {eye.get('shape', '')}."
    if eye.get("notes"):
        line += f" Notes: {eye['notes'].strip()}"
    lines.append(line)

    face = spec.get("face_shape", {})
    line = f"Face shape: {face.get('descriptor', '')}."
    features = face.get("distinguishing_features") or []
    if features:
        line += " Distinguishing features: " + "; ".join(str(f).strip() for f in features) + "."
    lines.append(line)

    gender = spec.get("gender_presentation", {})
    line = f"Gender presentation: {gender.get('descriptor', '').strip()}"
    if gender.get("primary_axis"):
        line += f" (primary axis: {gender['primary_axis']})"
    line += "."
    lines.append(line)

    outfit = spec.get("canonical_outfit", {})
    line = (
        f"Canonical outfit: {outfit.get('descriptor', '').strip()} "
        f"(formality: {outfit.get('formality', '')}, material family: "
        f"{outfit.get('material_family', '')}"
    )
    if outfit.get("color_family"):
        line += f", color family: {outfit['color_family']}"
    line += ")."
    lines.append(line)

    if "visible_disability" in spec:
        vd = spec["visible_disability"] or {}
        if vd.get("descriptor"):
            lines.append(f"Visible disability: {vd['descriptor'].strip()}")

    if spec.get("preferred_default_framing"):
        lines.append(
            f"Preferred default framing: {spec['preferred_default_framing']}."
        )

    lighting = spec.get("lighting_baseline", {})
    if lighting:
        line = (
            f"Lighting baseline: color temperature "
            f"{lighting.get('color_temperature', '')}, direction "
            f"{lighting.get('direction', '')}"
        )
        if lighting.get("contrast"):
            line += f", contrast {lighting['contrast']}"
        line += "."
        lines.append(line)

    if spec.get("expression_baseline_notes"):
        lines.append(
            f"Expression baseline: {spec['expression_baseline_notes'].strip()}"
        )

    return lines


def _emit_non_human_identity_lines(spec: Mapping[str, Any]) -> list[str]:
    """Emit non-human fixture-spec fields verbatim.

    The non-canonical test schema exposes: ``descriptor_text``,
    ``character_type``, ``substrate_exercise_notes`` (optional).
    Emitted verbatim in that order. No aesthetic interpretation.
    """
    lines: list[str] = []
    lines.append(f"Character type: {spec.get('character_type', '')}.")
    if spec.get("descriptor_text"):
        lines.append(f"Descriptor: {spec['descriptor_text'].strip()}")
    if spec.get("substrate_exercise_notes"):
        lines.append(
            f"Substrate-exercise notes: "
            f"{spec['substrate_exercise_notes'].strip()}"
        )
    return lines


def build_prompt(
    fixture: LoadedFixture,
    direction: str,
    purpose: str,
) -> str:
    """Return the deterministic, provider-neutral final prompt
    for one candidate cell.

    ``direction`` must be a value of
    ``RenderingDirectionHypothesis``. ``purpose`` must be
    ratified for ``fixture.branch``. Both are strings (not
    enum members) so the caller can pass values loaded from a
    matrix without eager enum lookup at every call site.

    Signature does NOT include a provider parameter. The same
    ``(fixture, direction, purpose)`` triple produces one
    prompt for all providers.

    Output shape (v1):

        [character-os benchmark prompt builder v1]
        [prompt for cell fixture=<id> branch=<branch> direction=<d> reference=<kind>/<purpose> category=<cat>]

        Identity fixture (branch=<branch>, version=<v>):
        <identity lines, one per canonical field, stable order>

        Rendering direction hypothesis: <direction>.
        Reference kind: <kind>. Reference purpose: <purpose> (category: <cat>).
        [end prompt]
    """
    _validate_axes(fixture, direction, purpose)
    branch = fixture.branch
    kind = "portrait_reference" if branch == IdentityBranch.HUMAN else "canonical_reference"
    category = _purpose_category(branch, purpose)

    header = (
        f"[character-os benchmark prompt builder v{PROMPT_BUILDER_VERSION}]\n"
        f"[prompt for cell fixture={fixture.fixture_id} "
        f"branch={branch.value} direction={direction} "
        f"reference={kind}/{purpose} category={category}]"
    )

    identity_header = (
        f"Identity fixture (branch={branch.value}, "
        f"version={fixture.fixture_version}):"
    )
    if branch == IdentityBranch.HUMAN:
        identity_lines = _emit_human_identity_lines(fixture.spec_payload)
    else:
        identity_lines = _emit_non_human_identity_lines(fixture.spec_payload)

    trailer = (
        f"Rendering direction hypothesis: {direction}.\n"
        f"Reference kind: {kind}. "
        f"Reference purpose: {purpose} (category: {category}).\n"
        f"[end prompt]"
    )

    body = "\n".join([header, "", identity_header, *identity_lines, "", trailer])
    return body


__all__ = [
    "PROMPT_BUILDER_VERSION",
    "PromptBuilderError",
    "build_prompt",
]
