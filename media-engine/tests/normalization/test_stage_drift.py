"""Stage-registry drift verifier (7.a — R10-style).

Mirrors the discipline of ``tests/portrait_provider/test_protocol_drift.py``
and ``tests/test_r10_provider_drift.py``: enumerate the stages
package on disk, assert that every module both (a) implements
the ``Stage`` Protocol and (b) is registered in
``_registered_stage_names``. Adding a new stage without wiring
it up trips the audit.

The registry ratchets slice-by-slice per SESSION 246 discipline:

* 7.a — ``(noop,)``
* 7.b — ``(noop, crop, framing)``
* 7.c — ``(noop, crop, framing, eye_line, background_replacement)``

Each slice bumps the parametrization + registry expectation
together, so a slice cannot land without the drift-check
proving the registration matches the on-disk state.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest

from app.services.normalization import Stage, get_stage
from app.services.normalization import stages as stages_pkg
from app.services.normalization.stages import _registered_stage_names


# ---- Registry ratchet ------------------------------------------


REGISTERED_NAMES_AT_7C = (
    "noop",
    "crop",
    "framing",
    "background_replacement",
)


def test_registry_names_are_exactly_the_7c_expected_set() -> None:
    """Registry ratchet: 7.a shipped NoOp-only. 7.b added
    ``crop`` + ``framing``. 7.c adds ``background_replacement``.
    NO ``eye_line`` entry — per SESSION 246 7.c architectural
    correction, eye-line positioning folded into CropStage
    (v1 → v2). Each ratchet forces the drift test to move with
    the slice.
    """
    assert _registered_stage_names() == REGISTERED_NAMES_AT_7C


@pytest.mark.parametrize("name", REGISTERED_NAMES_AT_7C)
def test_every_registered_name_resolves_to_a_stage_instance(name: str) -> None:
    stage = get_stage(name)
    assert isinstance(stage, Stage)


@pytest.mark.parametrize("name", REGISTERED_NAMES_AT_7C)
def test_every_registered_name_stage_name_matches_registration(
    name: str,
) -> None:
    """The stage's own ``stage_name`` class-level constant must
    match its registration key — a mismatch would silently ship
    manifest evidence attributed to the wrong stage.
    """
    stage = get_stage(name)
    assert stage.stage_name == name


# ---- Package enumeration --------------------------------------


def _walk_stage_modules() -> list[str]:
    """Enumerate every non-underscore-prefixed module in the
    stages package. Modules starting with ``_`` are internal
    helpers (there are none today; the convention is codified
    here so a future helper does not accidentally register as a
    stage).
    """
    pkg_file = stages_pkg.__file__
    assert pkg_file is not None, "stages package has no __file__ attribute"
    pkg_dir = Path(pkg_file).parent
    names: list[str] = []
    for m in pkgutil.iter_modules([str(pkg_dir)]):
        if m.ispkg:
            continue
        if m.name.startswith("_"):
            continue
        names.append(m.name)
    return names


def test_every_stage_module_is_registered() -> None:
    """Adding a new stage file without wiring it into
    ``get_stage`` and ``_registered_stage_names`` fires here.
    The registry is the ratcheted source of truth; the
    on-disk enumeration is a defence against forgetting.
    """
    on_disk = set(_walk_stage_modules())
    registered = set(_registered_stage_names())
    missing = on_disk - registered
    assert not missing, (
        f"stages on disk but not registered: {sorted(missing)}. "
        f"Register them in stages/__init__.py get_stage + "
        f"_registered_stage_names, and ratchet the drift test."
    )


def test_every_stage_module_exposes_exactly_one_stage_class() -> None:
    """One module = one stage. Prevents an accidental helper
    class in a stage module from being picked up as a
    registrable stage.
    """
    for module_name in _walk_stage_modules():
        mod = importlib.import_module(
            f"app.services.normalization.stages.{module_name}"
        )
        stage_classes = [
            obj for _, obj in inspect.getmembers(mod, inspect.isclass)
            if obj.__module__ == mod.__name__
            and isinstance(getattr(obj, "stage_name", None), str)
            and isinstance(getattr(obj, "stage_version", None), int)
        ]
        assert len(stage_classes) == 1, (
            f"stages/{module_name}.py exposes {len(stage_classes)} "
            f"stage class(es); expected exactly one."
        )


def test_unknown_stage_name_raises_loudly() -> None:
    from app.services.normalization import StageError

    with pytest.raises(StageError, match="unknown stage"):
        get_stage("stage_that_definitely_does_not_exist")


# ---- ClassVar contract ----------------------------------------


@pytest.mark.parametrize("name", REGISTERED_NAMES_AT_7C)
def test_stage_name_and_version_are_class_level_not_instance(name: str) -> None:
    """``pipeline_version`` composition and drift enumeration
    both reach for these attributes on the class object without
    instantiation. If a future stage author accidentally moves
    ``stage_name`` into ``__init__``, callers that never
    instantiate would break silently.
    """
    stage = get_stage(name)
    cls = type(stage)
    assert isinstance(cls.stage_name, str)
    assert isinstance(cls.stage_version, int)
    assert cls.stage_version >= 1
