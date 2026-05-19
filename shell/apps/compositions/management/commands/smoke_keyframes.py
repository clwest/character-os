"""SESSION 184 / Q-v17-3 — V17.3 anchor-model smoke comparison.

One-off Django management command that fires the SAME Hook + Payoff
keyframe pair through BOTH ``veo3.1_fast`` and ``gen3a_turbo`` so
the operator can eyeball which Runway-accessible model becomes
V17.3's anchor.

Surfaced by the SESSION 184 slice-3 live-doc check: Runway's
auto-generated SDK reveals that the V17 proposal's claim of
"keyframes on gen4_turbo" is wrong — gen4_turbo only accepts
``position: "first"``. The only models in Runway's /v1/image_to_video
that accept BOTH ``first`` and ``last`` are:

* ``gen3a_turbo`` — older Gen-3 Turbo; cheap; ratio constrained
  to 768:1280 or 1280:768 (no 16:9 720p).
* ``veo3.1_fast`` — Google Veo brokered through Runway; modern;
  supports 1280:720; 4/6/8s clips; per-call cost unknown.

This smoke command bypasses the media-engine entirely — direct
Runway HTTPS calls via httpx. No new internal endpoints, no
primitives, no recipes; this is a smoke test informing V17.3's
design lock, not a feature.

USAGE
=====

Operator passes two HTTPS image URLs (e.g. Runway CDN URLs from
prior V13 ``generate_image`` renders). The command fires both
models with the same keyframe pair + prompt + duration, polls
each to terminal, prints the output URLs side-by-side. The
operator opens both clips in a browser and picks the winner.

    python manage.py smoke_keyframes \\
        --hook-image-url https://... \\
        --payoff-image-url https://... \\
        --dry-run             # preview plan + cost, skip Runway

    python manage.py smoke_keyframes \\
        --hook-image-url https://... \\
        --payoff-image-url https://...
                              # fires real Runway calls (~$1.70-$2.90)

Costs (best-public estimates — confirm before lock-in):

* ``veo3.1_fast`` @ 6s — ~$1.20-$2.40
* ``gen3a_turbo`` @ 5s — ~$0.50
* TOTAL                 — ~$1.70-$2.90 worst case

Hard-coded defaults are picked so each model runs at its sweet
spot (mid-range duration, native-ish ratio). ``--dry-run`` first
to confirm.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
from django.core.management.base import BaseCommand, CommandError

# Same env-var names + API base as media-engine/app/config.py.
_RUNWAY_API_BASE = "https://api.dev.runwayml.com"
_RUNWAY_API_VERSION = "2024-11-06"

# Per-model defaults — picked from the Runway SDK
# ``image_to_video_create_params.py`` allowed values.
#
# gen3a_turbo : ratio ∈ {"768:1280", "1280:768"}; duration ∈ {5, 10}
# veo3.1_fast : ratio includes 1280:720; duration ∈ {4, 6, 8}
#
# Picked: shortest landscape-ish output that exercises the
# first+last keyframe interpolation. Keep both clips ~5-6s so
# spend stays under $3 worst-case.
_MODEL_DEFAULTS = {
    "veo3.1_fast": {
        "ratio": "1280:720",
        "duration": 6,
        # No prompt_text required by the schema, but Veo benefits
        # from it; keep the same prompt across models for parity.
        "needs_prompt_text": False,
    },
    "gen3a_turbo": {
        "ratio": "1280:768",  # closest to 16:9 (5:3 ≈ 1.67:1)
        "duration": 5,
        # gen3a_turbo's schema marks prompt_text as Required.
        "needs_prompt_text": True,
    },
}

# Polling — same cadence as the existing internal poll routes.
_POLL_INTERVAL_S = 3.0
_POLL_DEADLINE_S = 6 * 60  # 6 minutes, mirrors avatar_speech primitive


def _load_dotenv_into_environ() -> None:
    """Tiny inline .env parser — no python-dotenv dep. Reads
    KEY=VALUE lines from <repo-root>/.env (relative to this file)
    and pushes them into os.environ if not already set. The shell
    venv's settings.py uses raw os.environ, so this fills the
    same gap python-dotenv would."""
    # commands/smoke_keyframes.py → ../../../../.. = repo root
    repo_root = Path(__file__).resolve().parents[5]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _runway_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": _RUNWAY_API_VERSION,
        "Content-Type": "application/json",
    }


def _build_body(
    *,
    model: str,
    hook_url: str,
    payoff_url: str,
    prompt_text: str,
) -> dict:
    """Build the Runway /v1/image_to_video body for the given
    model. promptImage is the position-tagged array shape
    (the only shape that exercises first+last keyframes)."""
    defaults = _MODEL_DEFAULTS[model]
    body: dict = {
        "model": model,
        "promptImage": [
            {"position": "first", "uri": hook_url},
            {"position": "last", "uri": payoff_url},
        ],
        "ratio": defaults["ratio"],
        "duration": defaults["duration"],
    }
    # gen3a_turbo requires prompt_text; veo3.1_fast accepts it.
    body["promptText"] = prompt_text
    return body


def _poll_until_terminal(
    *,
    api_key: str,
    task_id: str,
    model: str,
    stdout,
) -> dict:
    """Poll /v1/tasks/{task_id} until status ∈ {SUCCEEDED, FAILED,
    CANCELED} or the 6-minute deadline lapses."""
    url = f"{_RUNWAY_API_BASE}/v1/tasks/{task_id}"
    headers = _runway_headers(api_key)
    deadline = time.monotonic() + _POLL_DEADLINE_S
    last_progress = -1.0
    with httpx.Client(timeout=30.0) as client:
        while time.monotonic() < deadline:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            status_value = str(payload.get("status", "")).upper()
            progress = payload.get("progress")
            if isinstance(progress, (int, float)) and progress != last_progress:
                stdout.write(
                    f"   {model}: status={status_value} progress={progress:.2f}"
                )
                last_progress = float(progress)
            if status_value in {"SUCCEEDED", "FAILED", "CANCELED"}:
                return payload
            time.sleep(_POLL_INTERVAL_S)
    raise CommandError(
        f"{model} task {task_id} did not reach terminal state "
        f"within {_POLL_DEADLINE_S}s"
    )


def _extract_output_url(payload: dict) -> str | None:
    """Runway returns output as either a list of URLs or a dict
    keyed by output kind. Mirror media-engine's runway_client.py
    parsing."""
    field = payload.get("output") or []
    if isinstance(field, dict):
        for value in field.values():
            if isinstance(value, str) and value:
                return value
    elif isinstance(field, list):
        for value in field:
            if isinstance(value, str) and value:
                return value
    return None


class Command(BaseCommand):
    help = (
        "SESSION 184 / Q-v17-3 — fire the same keyframe pair through "
        "veo3.1_fast + gen3a_turbo so the operator can pick V17.3's "
        "anchor model. Direct Runway calls; no media-engine, no DB writes."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--hook-image-url", required=True,
            help="HTTPS URL of the first-frame keyframe image.",
        )
        parser.add_argument(
            "--payoff-image-url", required=True,
            help="HTTPS URL of the last-frame keyframe image.",
        )
        parser.add_argument(
            "--prompt", default=(
                "Smooth cinematic camera movement from first frame to "
                "last frame, continuous motion, consistent subject identity."
            ),
            help=(
                "Motion prompt describing the trajectory between Hook "
                "and Payoff. Sent identically to both models for parity."
            ),
        )
        parser.add_argument(
            "--models", default="veo3.1_fast,gen3a_turbo",
            help=(
                "Comma-list of Runway model strings to compare. Default "
                "is the two first+last keyframe-capable Runway models."
            ),
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print the plan + cost estimate, skip Runway calls.",
        )

    def handle(self, *args, **opts) -> None:
        _load_dotenv_into_environ()
        api_key = os.environ.get("RUNWAY_API_KEY", "").strip()
        force_mock = os.environ.get("RUNWAY_FORCE_MOCK", "").strip() in {"1", "true", "True"}

        if not api_key and not opts["dry_run"]:
            raise CommandError(
                "RUNWAY_API_KEY not set in env or .env. Real-mode "
                "smoke needs a live key — fail loud rather than "
                "silently mock."
            )
        if force_mock:
            raise CommandError(
                "RUNWAY_FORCE_MOCK is set — refusing to run because "
                "the whole point of this smoke is real-mode A/B. "
                "Unset RUNWAY_FORCE_MOCK and rerun."
            )

        hook_url = opts["hook_image_url"].strip()
        payoff_url = opts["payoff_image_url"].strip()
        if not hook_url.startswith(("https://", "http://")):
            raise CommandError("--hook-image-url must be a fully-qualified URL")
        if not payoff_url.startswith(("https://", "http://")):
            raise CommandError("--payoff-image-url must be a fully-qualified URL")

        prompt = opts["prompt"].strip()
        models = [m.strip() for m in opts["models"].split(",") if m.strip()]
        unknown = [m for m in models if m not in _MODEL_DEFAULTS]
        if unknown:
            raise CommandError(
                f"unknown model(s) {unknown}; defaults registered for "
                f"{sorted(_MODEL_DEFAULTS.keys())}"
            )

        self.stdout.write("=" * 72)
        self.stdout.write("smoke_keyframes — Q-v17-3 V17.3 anchor-model comparison")
        self.stdout.write("=" * 72)
        self.stdout.write(f"Hook   : {hook_url}")
        self.stdout.write(f"Payoff : {payoff_url}")
        self.stdout.write(f"Prompt : {prompt}")
        self.stdout.write("")
        self.stdout.write("Plan:")
        for model in models:
            d = _MODEL_DEFAULTS[model]
            self.stdout.write(
                f"  {model:14} ratio={d['ratio']:10} duration={d['duration']}s"
            )
        self.stdout.write("")
        self.stdout.write(
            "Cost (best-public estimates — confirm against your "
            "Runway billing after the run):"
        )
        self.stdout.write("  veo3.1_fast  @ 6s — ~$1.20-$2.40")
        self.stdout.write("  gen3a_turbo  @ 5s — ~$0.50")
        self.stdout.write("  TOTAL              — ~$1.70-$2.90 worst case")
        self.stdout.write("")

        if opts["dry_run"]:
            self.stdout.write(
                self.style.WARNING("--dry-run set; skipping Runway calls.")
            )
            return

        self.stdout.write(self.style.NOTICE("Firing real Runway calls..."))
        self.stdout.write("")

        results: dict[str, dict] = {}
        for model in models:
            body = _build_body(
                model=model,
                hook_url=hook_url,
                payoff_url=payoff_url,
                prompt_text=prompt,
            )
            self.stdout.write(f"→ {model}: POST /v1/image_to_video")
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(
                        f"{_RUNWAY_API_BASE}/v1/image_to_video",
                        headers=_runway_headers(api_key),
                        json=body,
                    )
                if resp.status_code != 200:
                    self.stderr.write(
                        f"   {model}: HTTP {resp.status_code} — {resp.text[:300]}"
                    )
                    results[model] = {
                        "error": f"HTTP {resp.status_code}",
                        "body": resp.text[:400],
                    }
                    continue
                created = resp.json()
            except httpx.HTTPError as exc:
                self.stderr.write(f"   {model}: http error — {exc}")
                results[model] = {"error": str(exc)}
                continue

            task_id = created.get("id")
            if not task_id:
                self.stderr.write(
                    f"   {model}: response missing task id — {created!r}"
                )
                results[model] = {"error": "no task id"}
                continue

            self.stdout.write(f"   {model}: task_id={task_id}")
            payload = _poll_until_terminal(
                api_key=api_key,
                task_id=task_id,
                model=model,
                stdout=self.stdout,
            )
            terminal_status = str(payload.get("status", "")).upper()
            output_url = _extract_output_url(payload)
            results[model] = {
                "task_id": task_id,
                "status": terminal_status,
                "output_url": output_url,
                "failure_reason": payload.get("failure") or payload.get("error"),
            }
            if terminal_status == "SUCCEEDED" and output_url:
                self.stdout.write(self.style.SUCCESS(
                    f"   {model}: SUCCEEDED → {output_url}"
                ))
            else:
                self.stderr.write(
                    f"   {model}: {terminal_status} "
                    f"reason={results[model].get('failure_reason')!r}"
                )
            self.stdout.write("")

        # Final summary table — operator-facing.
        self.stdout.write("=" * 72)
        self.stdout.write("RESULTS")
        self.stdout.write("=" * 72)
        any_ok = False
        for model in models:
            row = results.get(model, {})
            url = row.get("output_url")
            if url:
                any_ok = True
                self.stdout.write(f"{model:14} → {url}")
            else:
                self.stdout.write(
                    f"{model:14} → FAILED ({row.get('error') or row.get('failure_reason') or row.get('status')})"
                )
        self.stdout.write("")
        if any_ok:
            self.stdout.write(self.style.SUCCESS(
                "Open the URLs side-by-side in a browser, decide which "
                "becomes V17.3's anchor model, and SESSION 184 slice 3 "
                "can lock-in design."
            ))
        else:
            self.stderr.write(self.style.ERROR(
                "Both calls failed — fix the auth/keyframe-URL issue "
                "and rerun. No V17.3 design lock until at least one "
                "model produces a watchable clip."
            ))
            sys.exit(1)
