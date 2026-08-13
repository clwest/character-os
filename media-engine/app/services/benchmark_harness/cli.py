"""Benchmark harness CLI.

Invocation:

    python -m app.services.benchmark_harness.cli \\
        [--fixtures fixture_h1,fixture_h2,...] \\
        [--directions identity_only,cinematic_naturalistic,...] \\
        [--providers mock,stability_still,runway_still_portrait] \\
        [--profiles compact,team_card,presence,studio,conversation] \\
        [--purposes-human front,neutral_rest,...] \\
        [--purposes-non-human front] \\
        [--execution-mode forced_mock|auto|real_required] \\
        [--fixtures-root <path>]

Default:

* execution-mode = ``forced_mock`` (CI-safe; produces no provider
  spend; evidence is marked non-qualification per operator
  discipline #6).
* every other axis defaults to the ratified round-one set.

Real-provider execution:

* ``--execution-mode real_required`` requires explicit opt-in.
  No silent fallback to mock — adapter raises
  ``ProviderUnavailableError`` if no API key.
* ``--execution-mode auto`` prints a warning: adapter routing
  to real happens when API keys are present, and API-key
  presence WILL cause paid execution. Mock fallback stays
  invisible in the ``auto`` path — the harness evidence
  records ``execution_mode_actual`` per cell.

Never open Step 9 from the CLI.
"""
from __future__ import annotations

import argparse
import sys

from .fixture_loader import default_fixtures_root, load_fixture
from .matrix import MatrixAxes
from .run_identity import ALLOWED_EXECUTION_MODES
from .runner import run_matrix
from .vocabulary import (
    BRANCH_TO_PURPOSES,
    IdentityBranch,
    RATIFIED_FIXTURES,
    RATIFIED_PROVIDERS,
    RATIFIED_SURFACE_PROFILES,
    RenderingDirectionHypothesis,
)


def _split(csv: str) -> tuple[str, ...]:
    """Split comma-separated CLI values into a tuple. Empty
    entries and whitespace are trimmed."""
    return tuple(v.strip() for v in csv.split(",") if v.strip())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.benchmark_harness.cli",
        description=(
            "Character OS portrait-qualification benchmark harness. "
            "Produces immutable file-based two-tier evidence per "
            "§17.8.a. Does NOT open Step 9 (bootstrap human review) "
            "or Step 10 (per-fixture scoring)."
        ),
    )
    parser.add_argument(
        "--fixtures",
        default=",".join(RATIFIED_FIXTURES),
        help="Comma-separated fixture_ids. Default: all ratified.",
    )
    parser.add_argument(
        "--directions",
        default=",".join(d.value for d in RenderingDirectionHypothesis),
        help=(
            "Comma-separated rendering-direction hypothesis values. "
            "Default: all six ratified."
        ),
    )
    parser.add_argument(
        "--providers",
        default=",".join(RATIFIED_PROVIDERS),
        help="Comma-separated provider names. Default: all ratified.",
    )
    parser.add_argument(
        "--profiles",
        default=",".join(RATIFIED_SURFACE_PROFILES),
        help=(
            "Comma-separated surface_profile identifiers. Default: all ratified."
        ),
    )
    parser.add_argument(
        "--purposes-human",
        default=",".join(BRANCH_TO_PURPOSES[IdentityBranch.HUMAN]),
        help=(
            "Comma-separated human portrait_reference purposes. Default: "
            "all seven ratified."
        ),
    )
    parser.add_argument(
        "--purposes-non-human",
        default=",".join(BRANCH_TO_PURPOSES[IdentityBranch.NON_HUMAN]),
        help=(
            "Comma-separated non-human canonical_reference purposes. Default: "
            "the single ratified 'front' value."
        ),
    )
    parser.add_argument(
        "--execution-mode",
        default="forced_mock",
        choices=list(ALLOWED_EXECUTION_MODES),
        help=(
            "Provider execution mode. Default: forced_mock (CI-safe). "
            "real_required requires operator opt-in and may cause paid "
            "execution. auto is permitted but the harness prints a "
            "warning."
        ),
    )
    parser.add_argument(
        "--fixtures-root",
        default=None,
        help=(
            "Override for the fixtures directory (both read + write "
            "root). Defaults to the ratified location under docs/."
        ),
    )
    return parser


def _emit_execution_mode_notice(mode: str) -> None:
    """Operator discipline #6: real-execution modes must be
    visible from the CLI, not silent."""
    if mode == "forced_mock":
        sys.stderr.write(
            "[benchmark_harness] execution_mode=forced_mock — harness "
            "mechanics only. Evidence is NON-QUALIFICATION per SESSION "
            "244 constraint 7 + SESSION 247 operator discipline #6.\n"
        )
    elif mode == "auto":
        sys.stderr.write(
            "[benchmark_harness] execution_mode=auto — API-key presence "
            "WILL cause paid execution for real-capable adapters. "
            "Per-cell evidence records execution_mode_actual; only "
            "records with actual=real are qualification-capable.\n"
        )
    elif mode == "real_required":
        sys.stderr.write(
            "[benchmark_harness] execution_mode=real_required — real "
            "provider execution. Adapters WILL raise ProviderUnavailableError "
            "on missing keys (no silent mock fallback). Evidence records "
            "per-cell provider outcomes.\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    _emit_execution_mode_notice(args.execution_mode)

    from pathlib import Path

    fixtures_root = (
        Path(args.fixtures_root).resolve()
        if args.fixtures_root is not None
        else default_fixtures_root()
    )

    fixture_ids = _split(args.fixtures)
    fixtures = [
        load_fixture(fx, fixtures_root=fixtures_root)
        for fx in fixture_ids
    ]

    axes = MatrixAxes(
        fixture_ids=fixture_ids,
        directions=_split(args.directions),
        purposes_by_branch={
            IdentityBranch.HUMAN: _split(args.purposes_human),
            IdentityBranch.NON_HUMAN: _split(args.purposes_non_human),
        },
        providers=_split(args.providers),
        surface_profiles=_split(args.profiles),
    )

    try:
        result = run_matrix(
            fixtures=fixtures,
            axes=axes,
            execution_mode=args.execution_mode,
            fixtures_root=fixtures_root,
        )
    except Exception as exc:
        sys.stderr.write(
            f"[benchmark_harness] run failed: {type(exc).__name__}: {exc!s}\n"
        )
        return 2

    sys.stdout.write(
        f"[benchmark_harness] run_id={result.run_identity.run_id}\n"
        f"[benchmark_harness] run_fingerprint={result.run_identity.run_fingerprint}\n"
        f"[benchmark_harness] planned_cells={sum(result.counts_by_outcome.values())}\n"
        f"[benchmark_harness] outcomes={dict(result.counts_by_outcome)}\n"
        f"[benchmark_harness] summary={result.layout.run_summary_path}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
