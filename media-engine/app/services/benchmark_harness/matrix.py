"""Benchmark harness matrix — the five candidate cell axes.

A **candidate cell** is one point in the benchmark's evaluation
space. Every cell has a stable identity built from five axes:

    (fixture_id, direction, reference_purpose, provider, surface_profile)

Load-bearing rules (per SESSION 247 operator discipline #3):

* Background is **not** a matrix axis. Per
  ``docs/design/visual/portrait_qualification/schemas/background_family_v1.yaml``
  and ``resolve_background_for_profile`` in the normalization
  package, the background is **derived from the surface profile's
  ``tonal_environment_class``**. Reviewer overrides may sweep
  backgrounds explicitly at Step 10 evidence time; the round-one
  bootstrap harness does not sweep background as an independent
  axis. This constant is asserted by a test so a future change
  cannot silently promote background to an axis:

      BACKGROUND_IS_DERIVED_FROM_PROFILE: True

* Every axis is explicitly enumerated at expand time — no hidden
  loops. If a caller wants a bounded run matrix, they pass narrow
  axis tuples; the expander enumerates their Cartesian product
  deterministically.

* Cell keys are hashable, comparable, and stable across runs with
  identical inputs. Consumed by the run-identity fingerprint via
  the axis descriptors, and by evidence-file paths at 8.b.

* Purpose applicability is branch-scoped. A ``fixture_h*`` cell
  cannot carry a non-human ``canonical_reference`` purpose; a
  ``fixture_nh1`` cell cannot carry a human ``portrait_reference``
  purpose. Applicability check lives in ``expand_matrix``; an
  invalid combination is silently skipped (documented) rather
  than raising, because the caller may intentionally pass the
  full purpose set + full fixture set and let the expander do
  the right thing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .fixture_loader import LoadedFixture
from .vocabulary import (
    BRANCH_TO_KIND,
    BRANCH_TO_PURPOSES,
    IdentityBranch,
    RATIFIED_FIXTURES,
    RATIFIED_PROVIDERS,
    RATIFIED_SURFACE_PROFILES,
    RenderingDirectionHypothesis,
)


# ---- The load-bearing constant (asserted by test) ------------

BACKGROUND_IS_DERIVED_FROM_PROFILE: bool = True
"""If ever set to False, the harness is claiming background as an
independent matrix axis. That would be a scope change against
``background_family_v1.yaml``'s reviewer_override model — do NOT
flip this without an operator ratification event."""


# ---- Cell key -------------------------------------------------


@dataclass(frozen=True, slots=True, order=True)
class CellKey:
    """One point in the benchmark matrix.

    Order-comparable so ``sorted(cells)`` produces a stable
    total order without ever using dict / set / hash iteration
    (which are only deterministic within a single Python run).

    All fields are string values (enum ``.value``s where
    applicable). Stringly-typed on purpose — the cell key is a
    stable identity used in file paths + fingerprints, and the
    enum classes are validated at construction time via
    ``build_cell_key``.
    """

    fixture_id: str
    direction: str
    reference_kind: str
    reference_purpose: str
    provider: str
    surface_profile: str

    def to_stable_dict(self) -> dict[str, str]:
        """Return a ``{axis: value}`` dict with stable key
        ordering. Used by evidence writers + fingerprint input."""
        return {
            "fixture_id": self.fixture_id,
            "direction": self.direction,
            "reference_kind": self.reference_kind,
            "reference_purpose": self.reference_purpose,
            "provider": self.provider,
            "surface_profile": self.surface_profile,
        }


# ---- Axis dataclass -------------------------------------------


@dataclass(frozen=True, slots=True)
class MatrixAxes:
    """The frozen axis descriptors that define a matrix expansion.

    Every field is a tuple of strings so callers can bound the
    matrix (e.g. one fixture + one provider) without ever passing
    a mutable container.
    """

    fixture_ids: tuple[str, ...]
    directions: tuple[str, ...]
    purposes_by_branch: dict[IdentityBranch, tuple[str, ...]]
    providers: tuple[str, ...]
    surface_profiles: tuple[str, ...]

    @staticmethod
    def ratified_round_one() -> "MatrixAxes":
        """Return the full ratified round-one matrix. Every
        cardinal axis at its ratified value; every branch's
        purpose set at its full authored width. Kept as a
        static constructor so tests can pin the ratified matrix.
        """
        return MatrixAxes(
            fixture_ids=RATIFIED_FIXTURES,
            directions=tuple(d.value for d in RenderingDirectionHypothesis),
            purposes_by_branch={
                branch: tuple(BRANCH_TO_PURPOSES[branch])
                for branch in IdentityBranch
            },
            providers=RATIFIED_PROVIDERS,
            surface_profiles=RATIFIED_SURFACE_PROFILES,
        )


# ---- Expansion ------------------------------------------------


def expand_matrix(
    axes: MatrixAxes,
    fixtures: Sequence[LoadedFixture],
) -> tuple[CellKey, ...]:
    """Expand ``axes`` × ``fixtures`` into a deterministically
    ordered sequence of ``CellKey``s.

    Branch discipline: purposes are filtered per fixture branch.
    A fixture in the human branch enumerates the axes'
    ``purposes_by_branch[HUMAN]`` values; a non-human fixture
    enumerates the non-human purposes. Cross-branch combinations
    are never produced.

    Non-axis inputs (background) never appear in the returned
    keys. See ``BACKGROUND_IS_DERIVED_FROM_PROFILE``.

    The returned tuple is sorted by ``CellKey`` natural order so
    the same axes always produce the same sequence.
    """
    fixture_by_id = {f.fixture_id: f for f in fixtures}

    unknown = [fx for fx in axes.fixture_ids if fx not in fixture_by_id]
    if unknown:
        raise ValueError(
            f"matrix references fixture_ids not present in the loaded "
            f"fixture set: {unknown}"
        )

    cells: list[CellKey] = []
    for fixture_id in axes.fixture_ids:
        fx = fixture_by_id[fixture_id]
        branch_purposes = axes.purposes_by_branch.get(fx.branch, ())
        kind = BRANCH_TO_KIND[fx.branch].value
        # Filter to purposes that are BOTH in the caller's set
        # AND ratified for the fixture's branch — silent skip of
        # cross-branch combinations, per module docstring.
        ratified_for_branch = BRANCH_TO_PURPOSES[fx.branch]
        applicable_purposes = tuple(
            p for p in branch_purposes if p in ratified_for_branch
        )
        for direction in axes.directions:
            for purpose in applicable_purposes:
                for provider in axes.providers:
                    for profile in axes.surface_profiles:
                        cells.append(
                            CellKey(
                                fixture_id=fixture_id,
                                direction=direction,
                                reference_kind=kind,
                                reference_purpose=purpose,
                                provider=provider,
                                surface_profile=profile,
                            )
                        )
    return tuple(sorted(cells))


def axes_fingerprint_input(axes: MatrixAxes) -> dict[str, object]:
    """A stable, JSON-serializable dict of the matrix axes for
    inclusion in the run fingerprint. Purpose keys are branch
    values (strings), tuples are converted to lists (JSON has no
    tuple type), and enum values are surfaced as strings.
    """
    return {
        "fixture_ids": list(axes.fixture_ids),
        "directions": list(axes.directions),
        "purposes_by_branch": {
            branch.value: list(purposes)
            for branch, purposes in sorted(
                axes.purposes_by_branch.items(),
                key=lambda kv: kv[0].value,
            )
        },
        "providers": list(axes.providers),
        "surface_profiles": list(axes.surface_profiles),
    }


__all__ = [
    "BACKGROUND_IS_DERIVED_FROM_PROFILE",
    "CellKey",
    "MatrixAxes",
    "axes_fingerprint_input",
    "expand_matrix",
]
