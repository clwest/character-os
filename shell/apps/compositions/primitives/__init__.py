"""Step primitive registry for the composition runtime.

SESSION 142 / V2. Each primitive in the registry is a unit of
work the composition runtime can dispatch to. v1 ships two
mock primitives (``mock_passthrough``, ``mock_failure``)
which exercise the runtime state machine without burning
Runway credits. V3+ adds the real primitives (one per slice)
matching the 16 names locked in
``docs/design/VIDEO_COMPOSITION_V1.md`` §"Step primitives".

A primitive is any object with three callables:

* ``execute(step, resolved_inputs, mock_mode) -> PrimitiveResult``
* ``estimate_cost(params: dict) -> int``  (cost in micros)
* (optional) ``estimate_duration_ms(params: dict) -> int``

The runtime in ``apps.compositions.tasks`` looks the
primitive up by ``CompositionStep.primitive`` (free-form
string), dispatches ``execute``, persists the output as an
``Asset`` row, and advances the step + composition status
state machines.

Adding a primitive is *only* this — a class with the two
methods + a registry entry. No conditional branches in the
runtime; no enum updates; no schema changes.
"""
from __future__ import annotations

from typing import Protocol, Type

from .avatar_speech import GenerateAvatarSpeechPrimitive
from .mock import (
    MockFailurePrimitive,
    MockPassthroughPrimitive,
    MockSlowPrimitive,
    PrimitiveError,
    PrimitiveResult,
)
from .visual_clip import GenerateVisualClipPrimitive


class Primitive(Protocol):
    """The minimum interface a step primitive must expose."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:  # noqa: D401
        """Run the primitive. Return a PrimitiveResult on
        success; raise ``PrimitiveError`` on failure."""
        ...

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Return estimated cost in micros (1 USD = 1_000_000
        micros). Pure function — no I/O."""
        ...


class UnknownPrimitiveError(Exception):
    """Raised when ``CompositionStep.primitive`` doesn't match
    a registered primitive name. The runtime catches this and
    marks the step ``FAILED`` with an actionable error
    message."""


# The registry. Adding an entry is the entire on-ramp for a
# new step primitive.
_REGISTRY: dict[str, Type[Primitive]] = {
    "mock_passthrough": MockPassthroughPrimitive,
    "mock_failure": MockFailurePrimitive,
    "mock_slow": MockSlowPrimitive,
    "generate_avatar_speech": GenerateAvatarSpeechPrimitive,  # V3
    "generate_visual_clip": GenerateVisualClipPrimitive,  # V4
    # V5+: "split_script": SplitScriptPrimitive,
    # V5+: "concat_clips": ConcatClipsPrimitive,
    # ...etc through V14
}


def get_primitive(name: str) -> Type[Primitive]:
    """Look up a primitive by name. Raises
    ``UnknownPrimitiveError`` for an unknown name so the
    runtime can surface a clean step-failure message."""
    primitive = _REGISTRY.get(name)
    if primitive is None:
        raise UnknownPrimitiveError(
            f"No primitive registered for {name!r}. "
            f"Registered: {sorted(_REGISTRY.keys())}"
        )
    return primitive


def registered_primitives() -> list[str]:
    """All currently-registered primitive names. Used by admin
    + by composition-builder UIs in V15."""
    return sorted(_REGISTRY.keys())


__all__ = [
    "Primitive",
    "PrimitiveError",
    "PrimitiveResult",
    "UnknownPrimitiveError",
    "get_primitive",
    "registered_primitives",
]
