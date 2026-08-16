"""SESSION 253 Stage 2 — media-engine post-render ffprobe.

Locks the new provenance contract on
``GET /internal/tasks/{id}/``:

* On terminal-ready polls with an output_url, media-engine
  ffprobes the URL and populates ``duration_seconds`` +
  ``duration_source="media_probe"``.
* On non-terminal polls (pending / rendering) NO ffprobe fires.
* On terminal polls where ffprobe fails (missing binary, non-
  zero rc, timeout, unparseable output), ``duration_seconds``
  stays None and ``duration_source`` stays None — shell falls
  back to its estimator with distinct provenance.
* On mock-mode terminal polls, ffprobe is skipped (mock task
  URLs point at a demo sample-lib file that would waste ~1 s
  per test without adding signal).

Zero provider calls — the ffprobe is against the MP4 URL the
provider already returned.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch, MagicMock

from app.routers.internal import (
    _probe_media_duration_from_url,
    _poll_runway_task,
)


# ---- probe helper ------------------------------------------------


class _FakeRun:
    """Stand-in for subprocess.CompletedProcess."""

    def __init__(self, *, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _mock_run(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return MagicMock(return_value=_FakeRun(
        returncode=returncode, stdout=stdout, stderr=stderr,
    ))


def test_probe_returns_measured_duration_on_success():
    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("subprocess.run", _mock_run(returncode=0, stdout="62.691\n")):
        assert _probe_media_duration_from_url("https://x") == 62.691


def test_probe_returns_none_when_ffprobe_missing():
    with patch("shutil.which", return_value=None):
        assert _probe_media_duration_from_url("https://x") is None


def test_probe_returns_none_on_non_zero_returncode():
    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("subprocess.run", _mock_run(returncode=1, stderr="Invalid data")):
        assert _probe_media_duration_from_url("https://x") is None


def test_probe_returns_none_on_unparseable_stdout():
    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("subprocess.run", _mock_run(returncode=0, stdout="not-a-number")):
        assert _probe_media_duration_from_url("https://x") is None


def test_probe_returns_none_on_timeout():
    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
        assert _probe_media_duration_from_url("https://x") is None


def test_probe_returns_none_on_os_error():
    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("subprocess.run", side_effect=OSError("EACCES")):
        assert _probe_media_duration_from_url("https://x") is None


# ---- _poll_runway_task integration ------------------------------


class _RunwayResp:
    def __init__(
        self, *, status="SUCCEEDED", output=None, progress=1.0,
        failure_reason=None, mock_mode=False, cost_credits=None,
    ):
        self.status = status
        self.output = output
        self.progress = progress
        self.failure_reason = failure_reason
        self.mock_mode = mock_mode
        # SESSION 257 — provider-billed cost forwarded through the
        # generalised task poll. Stub defaults to None because
        # pre-SESSION 257 fixtures assume Runway didn't surface
        # cost.credits; new tests explicitly opt in when needed.
        self.cost_credits = cost_credits


def _fake_settings():
    return MagicMock()


def test_poll_ffprobes_on_terminal_ready_with_output():
    """The load-bearing case: task ready + output URL present →
    ffprobe → real duration on the response."""
    runway = _RunwayResp(
        status="SUCCEEDED", output=["https://cdn/vid.mp4"], mock_mode=False,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
        return_value=62.691,
    ) as fake_probe:
        resp = _poll_runway_task("t1", _fake_settings())
    fake_probe.assert_called_once_with("https://cdn/vid.mp4")
    assert resp.status == "ready"
    assert resp.duration_seconds == 62.691
    assert resp.duration_source == "media_probe"


def test_poll_skips_ffprobe_on_non_terminal():
    """Mid-poll cycles (no output URL yet) must not fire ffprobe —
    would waste a probe per intermediate poll."""
    runway = _RunwayResp(
        status="RUNNING", output=None, progress=0.5, mock_mode=False,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
    ) as fake_probe:
        resp = _poll_runway_task("t2", _fake_settings())
    fake_probe.assert_not_called()
    assert resp.status == "rendering"
    assert resp.duration_seconds is None
    assert resp.duration_source is None


def test_poll_skips_ffprobe_on_mock_mode():
    """Mock-mode task URLs point at a demo sample-lib file; probing
    burns ~1 s per test without adding signal."""
    runway = _RunwayResp(
        status="SUCCEEDED", output=["https://demo.lib/sample.mp4"], mock_mode=True,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
    ) as fake_probe:
        resp = _poll_runway_task("t3", _fake_settings())
    fake_probe.assert_not_called()
    assert resp.status == "ready"
    assert resp.duration_seconds is None
    assert resp.duration_source is None
    assert resp.mock_mode is True


def test_poll_falls_back_on_ffprobe_failure():
    """ffprobe failure keeps duration_seconds=None + source=None
    so the shell primitive falls back to its estimator with the
    correct 'estimated' provenance marker."""
    runway = _RunwayResp(
        status="SUCCEEDED", output=["https://cdn/x.mp4"], mock_mode=False,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
        return_value=None,
    ):
        resp = _poll_runway_task("t4", _fake_settings())
    assert resp.status == "ready"
    assert resp.duration_seconds is None
    assert resp.duration_source is None


def test_poll_skips_ffprobe_on_failed_task():
    """Task in FAILED status has no output_url; nothing to probe."""
    runway = _RunwayResp(
        status="FAILED", output=None, failure_reason="upstream error",
        mock_mode=False,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
    ) as fake_probe:
        resp = _poll_runway_task("t5", _fake_settings())
    fake_probe.assert_not_called()
    assert resp.status == "failed"
    assert resp.duration_seconds is None
    assert resp.duration_source is None
    assert resp.error == "upstream error"


def test_poll_forwards_provider_cost_credits_to_response():
    """SESSION 257 — Runway's ``/v1/tasks/{id}`` returns
    ``cost.credits`` on SUCCEEDED tasks. The generalised task poll
    must forward it through so the shell primitive can persist
    provider-billed truth on ``cost_actual_micros`` instead of
    an estimator guess. Empirical verification: flat 2 credits
    across a 1.81 s → 179.64 s duration spread on
    ``/v1/avatar_videos``."""
    runway = _RunwayResp(
        status="SUCCEEDED",
        output=["https://cdn/vid.mp4"],
        mock_mode=False,
        cost_credits=2.0,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
        return_value=15.0,
    ):
        resp = _poll_runway_task("t6", _fake_settings())
    assert resp.status == "ready"
    assert resp.cost_credits == 2.0


def test_poll_cost_credits_is_none_when_provider_omits():
    """When Runway doesn't return ``cost.credits`` on the task
    (older tasks, some non-avatar endpoints), the poll response
    must forward ``None`` so shell callers fall back to their
    per-primitive estimator + stamp ``cost_source="estimated"``."""
    runway = _RunwayResp(
        status="SUCCEEDED",
        output=["https://cdn/vid.mp4"],
        mock_mode=False,
        cost_credits=None,
    )
    with patch(
        "app.routers.internal.runway_get_task", return_value=runway,
    ), patch(
        "app.routers.internal._probe_media_duration_from_url",
        return_value=15.0,
    ):
        resp = _poll_runway_task("t7", _fake_settings())
    assert resp.status == "ready"
    assert resp.cost_credits is None
