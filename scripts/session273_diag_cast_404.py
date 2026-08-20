"""SESSION 273 §21 — probe candidate wrong URLs the SPA might be sending.

Read-mostly. Runs each probe via APIClient force-authenticated as Chris
inside transaction.atomic() with savepoint_rollback so nothing persists.
Purpose: identify which URL shape produces the 404 Chris is seeing.
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


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
EPISODE_ID = "77b04b6b-110d-408d-82a3-a04e5ca66417"
CHRIS_USER_ID = 883


def main():
    User = get_user_model()
    chris = User.objects.get(id=CHRIS_USER_ID)
    client = APIClient()
    client.force_authenticate(user=chris)

    probes = [
        ("canonical", f"/api/episodes/{EPISODE_ID}/cast/", "POST", {"teammate": RUBY_ID}),
        ("id_literal_undefined", "/api/episodes/undefined/cast/", "POST", {"teammate": RUBY_ID}),
        ("id_literal_null", "/api/episodes/null/cast/", "POST", {"teammate": RUBY_ID}),
        ("post_to_cast_remove_url", f"/api/episodes/{EPISODE_ID}/cast/{RUBY_ID}/", "POST", {}),
        ("missing_api_prefix", f"/episodes/{EPISODE_ID}/cast/", "POST", {"teammate": RUBY_ID}),
        ("missing_teammate_key", f"/api/episodes/{EPISODE_ID}/cast/", "POST", {}),
        ("bad_uuid_shape", f"/api/episodes/not-a-uuid/cast/", "POST", {"teammate": RUBY_ID}),
        ("wrong_episode_uuid", "/api/episodes/00000000-0000-0000-0000-000000000000/cast/", "POST", {"teammate": RUBY_ID}),
        ("sanity_get_episode", f"/api/episodes/{EPISODE_ID}/", "GET", None),
    ]

    results = []
    for label, url, method, body in probes:
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                if method == "POST":
                    resp = client.post(url, data=body or {}, format="json")
                else:
                    resp = client.get(url)
                body_bytes = len(resp.content)
                snippet = resp.content[:200].decode("utf-8", errors="replace")
                r = {
                    "label": label,
                    "method": method,
                    "url": url,
                    "status_code": resp.status_code,
                    "body_bytes": body_bytes,
                    "body_snippet": snippet,
                }
            except Exception as exc:
                r = {
                    "label": label,
                    "method": method,
                    "url": url,
                    "exception_type": type(exc).__name__,
                    "exception_str": str(exc)[:300],
                }
            transaction.savepoint_rollback(sid)
            results.append(r)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ruby_id": RUBY_ID,
        "episode_id": EPISODE_ID,
        "user_id": CHRIS_USER_ID,
        "probes": results,
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs" / "design" / "session_273_experiment_data"
        / "07_diag_cast_404.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    for r in results:
        if "status_code" in r:
            print(f"{r['label']:28s} {r['method']} {r['url']}")
            print(f"  -> {r['status_code']}  bytes={r['body_bytes']}  body={r['body_snippet'][:120]!r}")
        else:
            print(f"{r['label']:28s} {r['method']} {r['url']}")
            print(f"  RAISED {r['exception_type']}: {r['exception_str'][:180]}")


if __name__ == "__main__":
    main()
