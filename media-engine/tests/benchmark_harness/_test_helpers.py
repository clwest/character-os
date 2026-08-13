"""Shared helpers for 8.b runner + evidence tests.

* ``seed_tmp_fixtures`` — copies ratified fixture directories into
  ``tmp_path`` so tests write evidence into isolated trees without
  polluting the real ``docs/design/visual/portrait_qualification/
  fixtures/`` subtree.

* ``LargeMockProvider`` — a stub PortraitProvider that returns a
  large-enough PNG (2400×2400) so a cell exercised against it can
  legitimately reach normalization SUCCESS. Used only in tests
  where we need proof-of-life for the SUCCESS path shape (the
  ratified Mock adapter's 256×256 output is too small to survive
  any ratified surface_profile's declared output dimensions).
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from app.services.benchmark_harness import default_fixtures_root
from app.services.normalization.png import encode_png
from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderCapabilities,
    ProviderUnavailableError,
)


def seed_tmp_fixtures(tmp_root: Path, fixture_ids: list[str]) -> Path:
    """Copy the ratified fixture directories into ``tmp_root`` so
    a test can write evidence there.

    Returns the ``fixtures_root`` inside ``tmp_root`` (the same
    directory where fixture copies live)."""
    src_root = default_fixtures_root()
    dst_root = tmp_root / "fixtures"
    dst_root.mkdir(parents=True, exist_ok=True)
    for fid in fixture_ids:
        src = src_root / fid
        dst = dst_root / fid
        if not src.is_dir():
            raise RuntimeError(f"ratified fixture missing on disk: {src}")
        shutil.copytree(src, dst)
    return dst_root


class LargeMockProvider:
    """Stub ``PortraitProvider`` returning a 2400×2400 RGBA PNG.

    Large enough to survive every ratified surface_profile's
    normalization. Used ONLY in tests where the SUCCESS-path
    evidence shape needs to be proved.

    Emits provenance identical to the real Mock adapter (provider
    name = MOCK, execution_mode_actual = MOCK) so the test still
    exercises the ratified non-qualifying discipline.
    """

    def __init__(self, provider_name: PortraitProviderName = PortraitProviderName.MOCK) -> None:
        self._provider_name = provider_name

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            raise ProviderUnavailableError(
                "LargeMockProvider does not implement REAL_REQUIRED."
            )
        # Deterministic-enough bytes: hash of prompt gives a stable
        # RGBA fill so two runs with the same prompt produce
        # identical bytes.
        from PIL import Image
        import hashlib
        seed = hashlib.sha256(
            (spec.prompt + "|" + (spec.deterministic_seed or "")).encode("utf-8")
        ).digest()
        color = (seed[0], seed[1], seed[2], 255)
        img = Image.new("RGBA", (2400, 2400), color)
        raw_bytes = encode_png(img)
        start = time.monotonic()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PortraitResult(
            image_bytes=raw_bytes,
            provider=self._provider_name,
            provider_model=spec.provider_model or "large-mock",
            execution_mode_actual=ExecutionModeActual.MOCK,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
            },
            elapsed_ms=elapsed_ms,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=self._provider_name,
            provider_model="large-mock",
            supported_models=("large-mock",),
            supported_aspect_ratios=("1:1", "3:4", "4:5", "4:3", "9:16", "16:9", "1280:720"),
            max_prompt_length=None,
            is_deterministic=True,
            execution_modes_supported=frozenset(
                {ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO}
            ),
        )

    def provider_name(self) -> PortraitProviderName:
        return self._provider_name


def large_mock_provider_factory(name: str, settings) -> LargeMockProvider:
    """Test hook for the runner's ``provider_factory``. Ignores
    ``name`` and returns a LargeMockProvider stamped with the
    requested provider's name (so provenance still discriminates
    per-cell)."""
    from app.services.portrait_provider import PortraitProviderName

    return LargeMockProvider(provider_name=PortraitProviderName(name))
