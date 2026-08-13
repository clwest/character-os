"""Benchmark harness vocabulary — direction hypotheses + reference purposes.

Frozen enumerations that mirror the ratified vocabulary in
``docs/design/visual/portrait_qualification/schemas/`` and
``.../scoring/scoring.schema.json``. Runtime authority: the
constants below. On-disk authority: the ratified schemas. Drift
tests in ``test_vocabulary.py`` assert the two agree.

Load-bearing distinction (operator-locked in SESSION 247):

    ``<direction>`` in the ratified fixture-run path
    (``runs/<benchmark_run_id>/<direction>/<provider>/…``)
    means **rendering direction hypothesis**, one of the six
    values enumerated in the scoring schema.

    **Reference purpose** — ``front`` / ``slight_left`` /
    ``neutral_rest`` / etc — is a **separate candidate
    dimension**. It MUST NOT be overloaded into the
    ``<direction>`` segment of the run tree.

The two live on different axes of the matrix module; this file
enumerates both.
"""
from __future__ import annotations

from enum import Enum


class IdentityBranch(str, Enum):
    """Character identity branches. Mirrors
    ``CharacterIdentity.Kind`` on the Django substrate.

    * ``human`` — validated against
      ``schemas/human_identity_schema_v1.yaml``.
    * ``non_human`` — validated against the non-canonical
      ``schemas/non_human_test_schema_v1.yaml`` (substrate
      exercise only per §17.2.b).
    """

    HUMAN = "human"
    NON_HUMAN = "non_human"


class RenderingDirectionHypothesis(str, Enum):
    """The six rendering-direction hypotheses ratified in
    ``scoring/scoring.schema.json`` (§17.7.a).

    These are the *values* that appear in the ``<direction>``
    segment of the fixture-run directory tree. Aesthetic
    territory-selection question. NOT a reference-view axis.

    ``identity_only`` is the direction-neutral baseline —
    "generate the identity without committing to a rendering
    territory yet." Included per Portrait Territory Study V1.
    """

    SOFTENED_PHOTOGRAPHIC = "softened_photographic"
    CINEMATIC_NATURALISTIC = "cinematic_naturalistic"
    PAINTERLY_NATURALISTIC = "painterly_naturalistic"
    CONTEMPORARY_PORTRAIT_ILLUSTRATION = "contemporary_portrait_illustration"
    LIGHTLY_STYLIZED_REALISM = "lightly_stylized_realism"
    IDENTITY_ONLY = "identity_only"


class HumanPortraitReferencePurpose(str, Enum):
    """Purpose values under the human branch's
    ``portrait_reference`` kind, per
    ``schemas/purpose_schema_human_v1.yaml``.

    Categorized (in the schema) into ``view`` — camera-axis
    variants — and ``expression`` — facial-state variants. The
    category discriminator is documentation, not a substrate
    branch; both categories are flat values here.
    """

    FRONT = "front"
    SLIGHT_LEFT = "slight_left"
    SLIGHT_RIGHT = "slight_right"
    NEUTRAL_REST = "neutral_rest"
    LISTENING = "listening"
    CONSIDERATION = "consideration"
    GENTLE_POSITIVE = "gentle_positive"


class NonHumanCanonicalReferencePurpose(str, Enum):
    """Purpose values under the non-human branch's non-canonical
    ``canonical_reference`` kind. Deliberately minimal per
    §17.2.b: one value, substrate exercise only.
    """

    FRONT = "front"


class ReferenceKind(str, Enum):
    """The reference-kind label written into every candidate's
    evidence + used as an axis alongside purpose.

    Round-one authoring uses one kind per branch:

    * ``portrait_reference`` — the human branch's kind for round-
      one still-portrait imagery.
    * ``canonical_reference`` — the non-human branch's non-
      canonical placeholder kind.

    Kept as a first-class value on every candidate so Step 9
    consumers can reconstruct the ``kind`` field of a future
    ``IdentityReference`` row without reinterpretation
    (per operator discipline F-8.1).
    """

    PORTRAIT_REFERENCE = "portrait_reference"
    CANONICAL_REFERENCE = "canonical_reference"


# ---- Branch → (kind, purposes) map ---------------------------
# Read by the matrix expander when deciding which cells exist
# per fixture branch. Static so tests can pin the ratified
# vocabulary and any silent drift trips a mismatch immediately.


BRANCH_TO_KIND: dict[IdentityBranch, ReferenceKind] = {
    IdentityBranch.HUMAN: ReferenceKind.PORTRAIT_REFERENCE,
    IdentityBranch.NON_HUMAN: ReferenceKind.CANONICAL_REFERENCE,
}


BRANCH_TO_PURPOSES: dict[IdentityBranch, tuple[str, ...]] = {
    IdentityBranch.HUMAN: tuple(p.value for p in HumanPortraitReferencePurpose),
    IdentityBranch.NON_HUMAN: tuple(p.value for p in NonHumanCanonicalReferencePurpose),
}


def purposes_for_branch(branch: IdentityBranch) -> tuple[str, ...]:
    """Return the ratified purposes for a branch as a stable
    tuple. Order is authoring-sequence per the schema files,
    preserved so evidence fingerprints don't churn on set-order
    variance.
    """
    return BRANCH_TO_PURPOSES[branch]


def kind_for_branch(branch: IdentityBranch) -> ReferenceKind:
    """Return the ratified reference kind for a branch."""
    return BRANCH_TO_KIND[branch]


# ---- Provider vocabulary --------------------------------------
# Mirrors ``PortraitProviderName`` in the portrait_provider
# package. Duplicated as strings to keep this module dependency-
# light (the matrix module imports the Protocol; the vocabulary
# module does not).


PROVIDER_MOCK: str = "mock"
PROVIDER_STABILITY_STILL: str = "stability_still"
PROVIDER_RUNWAY_STILL_PORTRAIT: str = "runway_still_portrait"


RATIFIED_PROVIDERS: tuple[str, ...] = (
    PROVIDER_MOCK,
    PROVIDER_STABILITY_STILL,
    PROVIDER_RUNWAY_STILL_PORTRAIT,
)


# ---- Fixture set ---------------------------------------------
# Ratified in §17.8.a. Immutable — adding a fixture requires the
# adaptive-expansion gate per FIXTURE_AUTHORING_GUIDE_V1.md.


RATIFIED_FIXTURES: tuple[str, ...] = (
    "fixture_h1",
    "fixture_h2",
    "fixture_h3",
    "fixture_h4",
    "fixture_nh1",
)


# ---- Surface-profile identifiers -----------------------------
# Mirrors the ratified profile YAMLs at
# ``schemas/surface_profiles/``. Explicit here so a matrix-level
# consumer can iterate profiles without loading the YAML.


RATIFIED_SURFACE_PROFILES: tuple[str, ...] = (
    "compact",
    "presence",
    "studio",
    "conversation",
    "team_card",
)


__all__ = [
    "BRANCH_TO_KIND",
    "BRANCH_TO_PURPOSES",
    "HumanPortraitReferencePurpose",
    "IdentityBranch",
    "NonHumanCanonicalReferencePurpose",
    "PROVIDER_MOCK",
    "PROVIDER_RUNWAY_STILL_PORTRAIT",
    "PROVIDER_STABILITY_STILL",
    "RATIFIED_FIXTURES",
    "RATIFIED_PROVIDERS",
    "RATIFIED_SURFACE_PROFILES",
    "ReferenceKind",
    "RenderingDirectionHypothesis",
    "kind_for_branch",
    "purposes_for_branch",
]
