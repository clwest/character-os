"""SESSION 266 — §7.11 precondition verification.

Reads environment + Django settings + retrieval signature. Prints
one line per check and a final PASS/FAIL summary. Aborts (exit 1)
if any precondition fails. Does NOT mutate any state.

Run from shell/:
    set -a && source ../.env && set +a && \
    ../.venv/bin/python manage.py shell < \
    ../docs/design/session_266_experiment_data/00_preconditions.py
"""
import inspect
import json
import os
import sys
from datetime import datetime, timezone

import django  # noqa: F401 — ensure django initialised
from django.conf import settings

results: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {name}: {detail}")
    results.append({"name": name, "ok": ok, "detail": detail})


# 1. EMBEDDING_FORCE_MOCK unset (settings + env)
settings_ef = getattr(settings, "EMBEDDING_FORCE_MOCK", None)
env_ef = os.environ.get("EMBEDDING_FORCE_MOCK", "").strip().lower()
check(
    "EMBEDDING_FORCE_MOCK unset",
    (not settings_ef) and env_ef in {"", "0", "false", "no", "off"},
    f"settings={settings_ef!r} env={env_ef!r}",
)

# 2. DIALOGUE_SYNTHESIS_FORCE_MOCK unset
settings_df = getattr(settings, "DIALOGUE_SYNTHESIS_FORCE_MOCK", None)
env_df = os.environ.get("DIALOGUE_SYNTHESIS_FORCE_MOCK", "").strip().lower()
check(
    "DIALOGUE_SYNTHESIS_FORCE_MOCK unset",
    (not settings_df) and env_df in {"", "0", "false", "no", "off"},
    f"settings={settings_df!r} env={env_df!r}",
)

# 3. OPENAI_API_KEY present
key = os.environ.get("OPENAI_API_KEY", "")
check(
    "OPENAI_API_KEY present",
    bool(key) and len(key) > 20,
    f"len={len(key)}",
)

# 4. retrieve_universe_memory default top_k=1
from apps.embeddings.retrieval import retrieve_universe_memory  # noqa: E402
sig = inspect.signature(retrieve_universe_memory)
top_k_default = sig.parameters["top_k"].default
check(
    "retrieve_universe_memory top_k default == 1",
    top_k_default == 1,
    f"got {top_k_default!r}",
)

# 5. embedding_service is real
from apps.embeddings.embedding_service import (  # noqa: E402
    _is_force_mock,
    _is_real_mode_possible,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)
force_mock = _is_force_mock()
real_possible = _is_real_mode_possible()
check(
    "embedding_service _is_force_mock() == False",
    not force_mock,
    f"got {force_mock!r}",
)
check(
    "embedding_service _is_real_mode_possible() == True",
    real_possible,
    f"got {real_possible!r}",
)
check(
    "EMBEDDING_MODEL == text-embedding-3-small",
    EMBEDDING_MODEL == "text-embedding-3-small",
    f"got {EMBEDDING_MODEL!r}",
)
check(
    "EMBEDDING_DIMENSION == 1536",
    EMBEDDING_DIMENSION == 1536,
    f"got {EMBEDDING_DIMENSION!r}",
)

# 6. dialogue model is Terra
from character_os import dialogue_synthesis as ds  # noqa: E402
check(
    "DIALOGUE_MODEL contains 'gpt-5' or 'terra'",
    "gpt-5" in ds.DIALOGUE_MODEL.lower() or "terra" in ds.DIALOGUE_MODEL.lower(),
    f"DIALOGUE_MODEL={ds.DIALOGUE_MODEL!r}",
)
check(
    "WRITING_CONTRACT_VERSION == 4",
    ds.WRITING_CONTRACT_VERSION == 4,
    f"got {ds.WRITING_CONTRACT_VERSION!r}",
)

summary = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "all_pass": all(r["ok"] for r in results),
    "results": results,
    "dialogue_model": ds.DIALOGUE_MODEL,
    "writing_contract_version": ds.WRITING_CONTRACT_VERSION,
    "embedding_model": EMBEDDING_MODEL,
    "embedding_dimension": EMBEDDING_DIMENSION,
    "retrieve_universe_memory_default_top_k": top_k_default,
}

with open(
    "../docs/design/session_266_experiment_data/00_preconditions.json",
    "w",
) as fh:
    json.dump(summary, fh, indent=2)

print()
print("=" * 70)
if summary["all_pass"]:
    print("ALL PRECONDITIONS PASS")
else:
    print("PRECONDITION FAILURES — HALT")
    sys.exit(1)
