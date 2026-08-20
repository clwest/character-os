"""SESSION 273 — reproduce the operator-path Add-to-cast 400.

Read-mostly. Uses DRF APIClient with force_authenticate to exercise
the exact production POST /api/episodes/<id>/cast/ handler that the
SPA calls. Wraps the call in transaction.atomic() with a hard rollback
so nothing persists to the DB. Additionally probes the direct m2m
add path (episode.cast.add(teammate)) inside its own atomic-rollback
block to isolate whether the failure is in the view or in the
Episode.cast.through signal.

Outputs a JSON sidecar with the exact 400 body, the view code
branch that produced it, and the object states at both sides of the
comparison.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Episode, EpisodeCast  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
EPISODE_ID = "77b04b6b-110d-408d-82a3-a04e5ca66417"
CHRIS_USER_ID = 883


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _describe_obj(obj, fields):
    return {
        f: (str(getattr(obj, f)) if getattr(obj, f) is not None else None)
        for f in fields
    }


def main():
    now = datetime.now(timezone.utc)
    out = {"generated_at": now.isoformat()}

    User = get_user_model()
    chris = User.objects.get(id=CHRIS_USER_ID)
    ruby = Teammate.objects.get(id=RUBY_ID)
    episode = Episode.objects.select_related("universe").get(id=EPISODE_ID)

    out["preconditions"] = {
        "ruby": {
            "id": str(ruby.id),
            "name": ruby.name,
            "workspace_id": str(ruby.workspace_id),
            "workspace_id_type": type(ruby.workspace_id).__name__,
            "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
            "universe_id_type": type(ruby.universe_id).__name__ if ruby.universe_id else None,
        },
        "episode": {
            "id": str(episode.id),
            "title": episode.title,
            "universe_id": str(episode.universe_id),
            "universe_id_type": type(episode.universe_id).__name__,
            "universe_workspace_id": str(episode.universe.workspace_id),
            "universe_workspace_id_type": type(episode.universe.workspace_id).__name__,
            "cast_count": episode.cast.count(),
            "cast_current": list(episode.cast.values_list("id", "name")),
        },
        "id_comparisons": {
            "ruby.universe_id == episode.universe_id": (
                ruby.universe_id == episode.universe_id
            ),
            "ruby.workspace_id == episode.universe.workspace_id": (
                ruby.workspace_id == episode.universe.workspace_id
            ),
            "str(ruby.universe_id) == str(episode.universe_id)": (
                str(ruby.universe_id) == str(episode.universe_id)
            ),
            "ruby.universe_id repr": repr(ruby.universe_id),
            "episode.universe_id repr": repr(episode.universe_id),
            "ruby.workspace_id repr": repr(ruby.workspace_id),
            "episode.universe.workspace_id repr": repr(episode.universe.workspace_id),
        },
    }

    # ---- PROBE 1 — DRF APIClient (full production path) ----
    # Wrap in atomic-rollback so no state persists.
    client = APIClient()
    client.force_authenticate(user=chris)

    drf_probe = {}
    try:
        with transaction.atomic():
            sid = transaction.savepoint()
            resp = client.post(
                f"/api/episodes/{EPISODE_ID}/cast/",
                data={"teammate": RUBY_ID},
                format="json",
            )
            drf_probe["status_code"] = resp.status_code
            try:
                drf_probe["body_json"] = resp.json()
            except Exception:
                drf_probe["body_json"] = None
            drf_probe["body_raw"] = resp.content.decode("utf-8", errors="replace")
            drf_probe["body_bytes"] = len(resp.content)
            drf_probe["episode_cast_after_probe"] = list(
                episode.cast.values_list("id", "name")
            )
            transaction.savepoint_rollback(sid)
    except Exception as exc:
        drf_probe["exception"] = f"{type(exc).__name__}: {exc}"
    out["probe_1_drf_client"] = drf_probe

    # ---- PROBE 2 — direct m2m add (isolate signal) ----
    m2m_probe = {}
    try:
        with transaction.atomic():
            sid = transaction.savepoint()
            episode.refresh_from_db()
            ruby.refresh_from_db()
            try:
                episode.cast.add(ruby)
                m2m_probe["result"] = "success"
                m2m_probe["cast_after"] = list(
                    episode.cast.values_list("id", "name")
                )
            except Exception as exc:
                m2m_probe["exception_type"] = type(exc).__name__
                m2m_probe["exception_str"] = str(exc)
                m2m_probe["exception_args"] = [str(a) for a in exc.args]
            transaction.savepoint_rollback(sid)
    except Exception as exc:
        m2m_probe["outer_exception"] = f"{type(exc).__name__}: {exc}"
    out["probe_2_direct_m2m_add"] = m2m_probe

    # ---- PROBE 3 — EpisodeCast.full_clean (model-level clean) ----
    clean_probe = {}
    try:
        with transaction.atomic():
            sid = transaction.savepoint()
            ep_fresh = Episode.objects.select_related("universe").get(id=EPISODE_ID)
            ruby_fresh = Teammate.objects.get(id=RUBY_ID)
            row = EpisodeCast(episode=ep_fresh, teammate=ruby_fresh)
            try:
                row.full_clean()
                clean_probe["result"] = "clean_passed"
            except Exception as exc:
                clean_probe["exception_type"] = type(exc).__name__
                clean_probe["exception_str"] = str(exc)
                try:
                    clean_probe["message_dict"] = dict(exc.message_dict)
                except Exception:
                    clean_probe["message_dict"] = None
            transaction.savepoint_rollback(sid)
    except Exception as exc:
        clean_probe["outer_exception"] = f"{type(exc).__name__}: {exc}"
    out["probe_3_full_clean"] = clean_probe

    # ---- Post-probe invariants (nothing persisted) ----
    ep_after = Episode.objects.get(id=EPISODE_ID)
    out["post_probe_state"] = {
        "episode_cast_count": ep_after.cast.count(),
        "episode_cast_members": list(ep_after.cast.values_list("id", "name")),
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "design"
        / "session_273_experiment_data"
        / "06_diag_cast_400.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print("=== id_comparisons ===")
    for k, v in out["preconditions"]["id_comparisons"].items():
        print(f"  {k}: {v}")
    print()
    print("=== probe 1: DRF APIClient POST /api/episodes/{id}/cast/ ===")
    print(f"  status_code: {drf_probe.get('status_code')}")
    print(f"  body_bytes: {drf_probe.get('body_bytes')}")
    print(f"  body_raw: {drf_probe.get('body_raw')}")
    print()
    print("=== probe 2: direct episode.cast.add(ruby) ===")
    for k, v in m2m_probe.items():
        print(f"  {k}: {v}")
    print()
    print("=== probe 3: EpisodeCast.full_clean() ===")
    for k, v in clean_probe.items():
        print(f"  {k}: {v}")
    print()
    print(f"post-probe episode cast: {out['post_probe_state']['episode_cast_members']} (must be [] — rollback verified)")


if __name__ == "__main__":
    main()
