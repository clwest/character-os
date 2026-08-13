"""Bake ~3s voice sample MP3s for every Runway preset.

⚠️  DO NOT USE AGAINST TODAY'S RUNWAY API. ⚠️

**SESSION 231 finding (2026-07-23):** ``POST /v1/voices/preview``
**silently ignores** the ``{type: "runway-live-preset", presetId: X}``
voice discriminator. Empirical proof: a call with
``presetId="NOT_A_REAL_PRESET"`` returns HTTP 200 with a valid MP3,
and a call with no ``voice`` field at all returns HTTP 200 with the
same shape. The 30 preset names (vincent, luna, etc.) are only
reachable via ``POST /v1/avatars`` avatar creation — Runway's public
developer API exposes no standalone preview surface for them
(confirmed in ``media-engine/app/services/avatar_listing_client.py``
2026-05-08 probe note). Baking with this command produces 30 MP3s
that are all the same default voice with slight prosody
variations — misleading in the picker UI (violates
CUSTOMER_JOURNEY_V1 contract rule 6, "metaphor never obscures
system truth").

The full 30-preset run was executed once at SESSION 231 open
(commit ``d62b786``) and reverted the same session. See
``docs/handoffs/SESSION_231_SLICE_1B_VOICE_BAKE.md`` §"POST-COMMIT
DISCOVERY" and ``docs/research/RUNWAY_API_CAPABILITY_MAP.md``
§"Voice preview endpoint is not preset-aware" for the full trace.

**When this command becomes useful again:** if Runway ships a
preset-aware preview endpoint (e.g. ``POST /v1/voices/preview``
starts honouring the discriminator, or a dedicated
``/v1/avatar_voices/{presetId}/sample`` lands), the command shape
below is already correct — the finding is about the receiving
endpoint, not the request builder. Alternatively, the real
per-preset audio can be baked via the SESSION 230-declined "create
30 avatars, render talking_head each, ffmpeg-extract audio" path
(~750 credits, ~$7.50) — but that belongs in a new command
(``bake_voice_samples_via_avatar_render`` or similar), not this
one.

---

Original intent (kept for context):

Slice 1b of Chapter 2 (Hire Oliver). The wizard Step 3 preset picker
(shipped SESSION 230 slice 1a) exposes a per-row play button; this
command was meant to populate the actual audio files those buttons
play.

For each preset in ``SUPPORTED_VOICE_PRESETS``:
  1. Skip if ``web/public/voice-samples/{name}.mp3`` already exists
     (idempotent — a mid-run failure never re-spends on the ones
     that succeeded).
  2. ``POST /v1/voices/preview`` to Runway with a canonical
     audition line.
  3. Download the returned signed S3 MP3 to disk.

Runway credit cost is queried via ``/v1/organization`` before + after
the bake so the operator sees the true spend, not a guess. Dry-run is
the default; ``--commit`` is required to actually spend credits.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from django.core.management.base import BaseCommand, CommandError

# Local mirror of the media-engine preset list. Kept in sync with
# ``apps.spokespeople.views.SUPPORTED_VOICE_PRESETS``.
from apps.spokespeople.views import SUPPORTED_VOICE_PRESETS

# Canonical audition line (SESSION 230 handoff §"Late-session probe").
AUDITION_LINE = "Hi, I'll be your spokesperson. Nice to meet you."

# Match VO-arc convention (media-engine/app/services/audio_client.py:50).
VOICE_PREVIEW_MODEL = "eleven_multilingual_ttv_v2"

DEFAULT_RUNWAY_API_BASE = "https://api.dev.runwayml.com"
DEFAULT_RUNWAY_API_VERSION = "2024-11-06"

MAX_MP3_BYTES = 5 * 1024 * 1024  # 5 MB sanity cap per sample.


def _load_dotenv_into_environ() -> None:
    """Mirror of smoke_keyframes._load_dotenv_into_environ."""
    # commands/bake_voice_samples.py → ../../../../.. = repo root
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _samples_dir() -> Path:
    return _repo_root() / "web" / "public" / "voice-samples"


def _runway_headers(api_key: str, api_version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": api_version,
        "Content-Type": "application/json",
    }


def _fetch_credit_balance(
    api_base: str, headers: dict[str, str]
) -> float | None:
    """Best-effort read of the org's remaining credit balance.

    Mirrors the field-path search from
    ``media-engine/app/routers/runway.py::_extract_credits``. Returns
    ``None`` if the endpoint is unreachable or the field is missing.
    """
    url = f"{api_base}/v1/organization"
    # Strip Content-Type for a GET.
    get_headers = {k: v for k, v in headers.items() if k != "Content-Type"}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=get_headers)
        if resp.status_code != 200:
            return None
        payload = resp.json() if resp.content else {}
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    for path in (
        ("creditsRemaining",),
        ("credits", "remaining"),
        ("credits", "balance"),
        ("credits",),
        ("balance", "credits"),
        ("balance",),
        ("usage", "creditsRemaining"),
    ):
        cur: object = payload
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and isinstance(cur, (int, float)):
            return float(cur)
    return None


def _bake_one(
    preset: str,
    target: Path,
    api_base: str,
    headers: dict[str, str],
) -> tuple[int, float]:
    """Fire preview + download. Returns (bytes_written, duration_secs)."""
    body = {
        "model": VOICE_PREVIEW_MODEL,
        "prompt": AUDITION_LINE,
        "voice": {"type": "runway-live-preset", "presetId": preset},
    }
    url = f"{api_base}/v1/voices/preview"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise CommandError(
            f"preset={preset} preview failed: "
            f"{resp.status_code} {resp.text[:300]}"
        )
    payload = resp.json()
    signed_url = payload.get("url")
    duration = float(payload.get("durationSecs") or 0.0)
    if not signed_url:
        raise CommandError(f"preset={preset} response missing 'url': {payload}")

    tmp = target.with_suffix(target.suffix + ".tmp")
    size = 0
    try:
        with httpx.stream(
            "GET", signed_url, timeout=60.0, follow_redirects=True
        ) as stream:
            stream.raise_for_status()
            ctype = (stream.headers.get("content-type") or "").lower()
            if not ctype.startswith("audio/"):
                raise CommandError(
                    f"preset={preset} unexpected content-type: "
                    f"{ctype or '(missing)'}"
                )
            with open(tmp, "wb") as fh:
                for chunk in stream.iter_bytes():
                    size += len(chunk)
                    if size > MAX_MP3_BYTES:
                        tmp.unlink(missing_ok=True)
                        raise CommandError(
                            f"preset={preset} mp3 exceeds "
                            f"{MAX_MP3_BYTES} bytes"
                        )
                    fh.write(chunk)
        tmp.replace(target)
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise CommandError(f"preset={preset} download error: {exc!s}") from exc

    return size, duration


class Command(BaseCommand):
    help = (
        "Bake ~3s voice sample MP3s for every Runway preset. "
        "Idempotent (skips existing files). Dry-run by default."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--commit",
            action="store_true",
            help=(
                "Actually POST to Runway and write files. Without this "
                "flag, prints the plan and exits."
            ),
        )
        parser.add_argument(
            "--preset",
            action="append",
            default=[],
            metavar="NAME",
            help=(
                "Restrict to a specific preset (repeatable). Useful for "
                "the initial credit-cost probe. If omitted, targets all "
                "missing presets."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            metavar="N",
            help=(
                "Bake only the first N missing presets (alphabetical). "
                "Ignored when --preset is used."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Re-bake presets that already have a file on disk. "
                "Rare — spends credits on already-baked presets."
            ),
        )

    def handle(self, *_, **opts) -> None:
        _load_dotenv_into_environ()
        api_key = os.environ.get("RUNWAY_API_KEY", "").strip()
        force_mock = os.environ.get("RUNWAY_FORCE_MOCK", "").strip() in {
            "1", "true", "True",
        }
        api_base = os.environ.get(
            "RUNWAY_API_BASE", DEFAULT_RUNWAY_API_BASE,
        ).rstrip("/")
        api_version = os.environ.get(
            "RUNWAY_API_VERSION", DEFAULT_RUNWAY_API_VERSION,
        )

        commit: bool = opts["commit"]
        force: bool = opts["force"]
        preset_filter: list[str] = [p.strip().lower() for p in opts["preset"]]
        limit: int | None = opts["limit"]

        if commit and not api_key:
            raise CommandError(
                "RUNWAY_API_KEY not set in env or .env. Real-mode bake "
                "needs a live key — fail loud rather than silently mock."
            )
        if commit and force_mock:
            raise CommandError(
                "RUNWAY_FORCE_MOCK is set — refusing to run because this "
                "command's whole job is to hit the real Runway API. "
                "Unset RUNWAY_FORCE_MOCK and rerun."
            )

        # Resolve the target preset list.
        all_presets = sorted(SUPPORTED_VOICE_PRESETS)
        if preset_filter:
            unknown = [p for p in preset_filter if p not in SUPPORTED_VOICE_PRESETS]
            if unknown:
                raise CommandError(
                    f"unknown preset(s): {unknown}. "
                    f"known: {all_presets}"
                )
            candidates = [p for p in all_presets if p in preset_filter]
        else:
            candidates = all_presets

        samples_dir = _samples_dir()
        samples_dir.mkdir(parents=True, exist_ok=True)

        to_bake: list[str] = []
        skipped_existing: list[str] = []
        for name in candidates:
            target = samples_dir / f"{name}.mp3"
            if target.exists() and not force:
                skipped_existing.append(name)
                continue
            to_bake.append(name)

        if limit is not None and not preset_filter:
            to_bake = to_bake[:limit]

        self.stdout.write("")
        self.stdout.write("bake_voice_samples plan")
        self.stdout.write(f"  samples_dir: {samples_dir}")
        self.stdout.write(f"  api_base:    {api_base}")
        self.stdout.write(f"  audition:    {AUDITION_LINE!r}")
        self.stdout.write(f"  model:       {VOICE_PREVIEW_MODEL}")
        self.stdout.write(f"  candidates:  {len(candidates)}")
        self.stdout.write(f"  to_bake:     {len(to_bake)} → {to_bake}")
        self.stdout.write(
            f"  skipping:    {len(skipped_existing)} already on disk"
        )
        self.stdout.write("")

        if not to_bake:
            self.stdout.write(self.style.SUCCESS("nothing to do — all baked."))
            return

        if not commit:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — pass --commit to actually POST to Runway."
                )
            )
            return

        headers = _runway_headers(api_key, api_version)

        credits_before = _fetch_credit_balance(api_base, headers)
        if credits_before is None:
            self.stdout.write(
                self.style.WARNING(
                    "credits_before: unavailable (endpoint may be "
                    "restricted — spend can still be checked via the "
                    "Runway dashboard)"
                )
            )
        else:
            self.stdout.write(f"credits_before: {credits_before:,.2f}")

        started = time.time()
        succeeded: list[tuple[str, int, float]] = []
        for i, name in enumerate(to_bake, start=1):
            target = samples_dir / f"{name}.mp3"
            self.stdout.write(
                f"[{i}/{len(to_bake)}] baking {name} → {target.name} ..."
            )
            try:
                size, duration = _bake_one(name, target, api_base, headers)
            except CommandError as exc:
                self.stderr.write(self.style.ERROR(f"  failed: {exc}"))
                # Continue the loop — partial success is better than
                # blowing up after 15 successful bakes.
                continue
            self.stdout.write(f"  ok: {size:,} bytes, ~{duration:.1f}s")
            succeeded.append((name, size, duration))

        elapsed = time.time() - started
        credits_after = _fetch_credit_balance(api_base, headers)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"baked {len(succeeded)}/{len(to_bake)} presets in {elapsed:.1f}s"
        ))
        if credits_before is not None and credits_after is not None:
            delta = credits_before - credits_after
            per_call = delta / max(len(succeeded), 1)
            self.stdout.write(
                f"credit spend: {delta:,.2f} "
                f"(~{per_call:,.2f}/preset, {credits_after:,.2f} remaining)"
            )
        elif credits_after is not None:
            self.stdout.write(f"credits_after:  {credits_after:,.2f}")
        if succeeded:
            total_bytes = sum(s for _, s, _ in succeeded)
            self.stdout.write(
                f"total on disk: {total_bytes:,} bytes across "
                f"{len(succeeded)} files under {samples_dir}"
            )
