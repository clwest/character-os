"""Benchmark harness schema version.

Bumped when the harness's evidence shape changes in a way that
would make prior-round evidence non-comparable via the current
codepath. Included in ``run_fingerprint`` so the fingerprint
picks up harness-level changes even if pipeline / prompt-builder
versions are unchanged.

* v1 — SESSION 247 §19 Step 8.a. Establishes vocabulary,
  fixture-loader, prompt-builder v1, matrix axes, and
  ``RunIdentity`` split of unique-run-id versus reproducibility-
  fingerprint.
"""
from __future__ import annotations

HARNESS_SCHEMA_VERSION: int = 1
