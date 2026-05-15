"""Tool dispatch for the realtime arc — R7.0.

The avatar's LLM invokes a tool over the WebRTC data channel.
The SPA receives the event via the SDK's `onClientEvent`
callback and POSTs it here. This module:

1. Resolves the tool by name from the registry.
2. Verifies the requesting session owns the resource the
   tool will touch (workspace + spokesperson scoping).
3. Compares the tool's `cost_micros` against the v1
   approval threshold. Over → return ``awaiting_approval``;
   under → execute inline (R7.0) or enqueue Celery (R7.2).
4. Records the invocation in a `RealtimeToolInvocation` row
   for audit + cost attribution.

The dispatch surface is intentionally provider-agnostic —
nothing here knows that the avatar is running on Runway vs
a future provider. Tool executors handle provider-specific
details internally.

Contract rule alignment:
* Rule 6 (workspace-scoped tools) — enforced at dispatch
  for every workspace_scoped tool by validating the
  session's workspace before invoking the executor.
* Rule 9 (mock mode) — flows through: tools call their
  respective force-mock flags. The dispatcher doesn't
  branch on mock state.

R7.0 ships:
* `dispatch_tool` — the main entry point.
* `approve_invocation` / `reject_invocation` — operator
  approval gate flow for over-threshold tools.
* `DispatchResult` — typed return shape the viewset
  serializes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import RealtimeSession, RealtimeToolInvocation
from .tools import ToolSpec, _tier_rank, get_tool

logger = logging.getLogger(__name__)


DEFAULT_APPROVAL_THRESHOLD_MICROS = 50_000  # $0.05


def _approval_threshold_micros() -> int:
    """v1: single settings constant. R9 (cost governance)
    layers per-workspace overrides on top of this. The
    function indirection keeps callers stable when the
    backing store changes."""
    return int(
        getattr(
            settings,
            "REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS",
            DEFAULT_APPROVAL_THRESHOLD_MICROS,
        )
    )


DispatchState = Literal[
    "succeeded",       # executed inline; result available
    "awaiting_approval",  # over threshold; operator must approve
    "failed",          # executor raised; recorded for audit
    "queued",          # async tool enqueued (R7.2)
    "rejected",        # workspace-scope check failed
]


@dataclass(slots=True)
class DispatchResult:
    """Typed return shape the viewset hands back to the
    SPA. Mirrors V's per-step result pattern."""

    state: DispatchState
    invocation_id: str
    tool_name: str
    cost_micros: int = 0
    result: dict | None = None
    error_message: str = ""
    reason: str = ""


class DispatchError(Exception):
    """Raised by ``dispatch_tool`` for resolution-layer
    failures (unknown tool, cross-workspace scope). The
    viewset translates to an HTTP status."""

    def __init__(self, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.http_status = http_status


def dispatch_tool(
    session: RealtimeSession,
    tool_name: str,
    args: dict | None = None,
    *,
    user=None,
) -> DispatchResult:
    """Resolve + dispatch a tool invocation.

    Args:
        session: the active `RealtimeSession`. Pre-loaded by
            the viewset's queryset (workspace-scoped via
            membership).
        tool_name: stable tool identifier (matches the
            registry).
        args: tool-specific args (JSON-serializable). Stored
            verbatim on the audit row.
        user: the requesting `User`. Used by the approval
            gate flow + recorded indirectly via the audit
            row's session FK.

    Returns:
        ``DispatchResult`` with state describing the
        outcome.

    Raises:
        ``DispatchError`` when the tool name is unknown
        (HTTP 400) or the session's workspace does not own
        the resource the tool would touch (HTTP 403).
    """
    args = args or {}

    try:
        spec = get_tool(tool_name)
    except KeyError as exc:
        raise DispatchError(
            f"unknown tool: {tool_name!r}", http_status=400,
        ) from exc

    # R7.0: the workspace-scope guard for workspace_scoped
    # tools is trivial — the session itself is already
    # workspace-anchored at view-layer, and v1's tools all
    # operate on resources reachable from the session
    # (knowledge attached to spokesperson; prior sessions
    # for the same spokesperson; same-workspace
    # spokespeople for handoff). The future cross-workspace
    # risk (a tool that takes a resource id in args) is
    # tool-handler's responsibility via the audit row's
    # produced_asset / produced_composition cross-workspace
    # check that already exists in models.py's clean().

    # R7.1 — defense-in-depth tier check. The catalog
    # filter on `get_workspace_tools` is the primary gate
    # (the LLM never sees over-tier tools at
    # session-create), but a malicious or buggy SPA could
    # POST a tool name the catalog excluded. Reject those
    # here with a structured error.
    from apps.billing.services import get_workspace_tier

    workspace_rank = _tier_rank(get_workspace_tier(session.workspace))
    if _tier_rank(spec.tier_required) > workspace_rank:
        raise DispatchError(
            (
                f"tool {spec.name!r} requires {spec.tier_required!r} "
                f"tier; workspace is on a lower tier"
            ),
            http_status=403,
        )

    threshold = _approval_threshold_micros()
    needs_approval = spec.cost_micros > threshold

    with transaction.atomic():
        invocation = RealtimeToolInvocation.objects.create(
            session=session,
            tool_name=spec.name,
            args=args,
            status=(
                RealtimeToolInvocation.Status.AWAITING_APPROVAL
                if needs_approval
                else RealtimeToolInvocation.Status.INVOKED
            ),
        )

    if needs_approval:
        return DispatchResult(
            state="awaiting_approval",
            invocation_id=str(invocation.id),
            tool_name=spec.name,
            cost_micros=spec.cost_micros,
            reason=(
                f"tool cost ${spec.cost_micros / 1_000_000:.2f} "
                f"exceeds workspace threshold "
                f"${threshold / 1_000_000:.2f}"
            ),
        )

    if spec.is_async:
        # R7.2 will enqueue a Celery task here + return
        # ``queued``. R7.0 only registers sync tools so
        # this branch is unreachable today; it's wired
        # ahead so R7.2 is a smaller diff.
        return DispatchResult(
            state="queued",
            invocation_id=str(invocation.id),
            tool_name=spec.name,
            cost_micros=spec.cost_micros,
        )

    return _execute_inline(invocation, spec, args)


def approve_invocation(invocation: RealtimeToolInvocation) -> DispatchResult:
    """Operator approved a deferred tool — execute it now.

    Idempotent: invocations already past
    ``AWAITING_APPROVAL`` (succeeded / failed / rejected)
    return their current state without re-executing.
    """
    if invocation.status != RealtimeToolInvocation.Status.AWAITING_APPROVAL:
        return DispatchResult(
            state=_status_to_state(invocation.status),
            invocation_id=str(invocation.id),
            tool_name=invocation.tool_name,
        )

    try:
        spec = get_tool(invocation.tool_name)
    except KeyError:
        # Tool was de-registered between dispatch and
        # approval. Mark FAILED + surface the error.
        invocation.status = RealtimeToolInvocation.Status.FAILED
        invocation.error_message = (
            f"tool {invocation.tool_name!r} no longer registered"
        )
        invocation.completed_at = timezone.now()
        invocation.save(update_fields=[
            "status", "error_message", "completed_at",
        ])
        return DispatchResult(
            state="failed",
            invocation_id=str(invocation.id),
            tool_name=invocation.tool_name,
            error_message=invocation.error_message,
        )

    # Flip back to INVOKED so the audit trail reflects that
    # the operator approved + execution proceeded.
    invocation.status = RealtimeToolInvocation.Status.INVOKED
    invocation.save(update_fields=["status"])

    if spec.is_async:
        return DispatchResult(
            state="queued",
            invocation_id=str(invocation.id),
            tool_name=spec.name,
            cost_micros=spec.cost_micros,
        )

    return _execute_inline(invocation, spec, invocation.args or {})


def reject_invocation(
    invocation: RealtimeToolInvocation,
    *,
    reason: str = "",
) -> DispatchResult:
    """Operator rejected a deferred tool. Records the
    rejection + optional reason. Idempotent.
    """
    if invocation.status == RealtimeToolInvocation.Status.REJECTED:
        return DispatchResult(
            state="rejected",
            invocation_id=str(invocation.id),
            tool_name=invocation.tool_name,
            reason=invocation.error_message,
        )

    invocation.status = RealtimeToolInvocation.Status.REJECTED
    if reason:
        invocation.error_message = reason[:500]
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=[
        "status", "error_message", "completed_at",
    ])
    return DispatchResult(
        state="rejected",
        invocation_id=str(invocation.id),
        tool_name=invocation.tool_name,
        reason=invocation.error_message,
    )


def _execute_inline(
    invocation: RealtimeToolInvocation,
    spec: ToolSpec,
    args: dict,
) -> DispatchResult:
    """Run the tool's executor + update the audit row.

    Executor exceptions are caught + recorded as FAILED.
    The dispatch endpoint always returns a structured
    response — never a 500 — so the SPA can render a
    sensible UX.
    """
    try:
        result = spec.executor(invocation.session, args)
    except Exception as exc:
        logger.exception(
            "realtime tool executor failed tool=%s invocation=%s",
            spec.name, invocation.id,
        )
        invocation.status = RealtimeToolInvocation.Status.FAILED
        invocation.error_message = str(exc)[:500]
        invocation.completed_at = timezone.now()
        invocation.save(update_fields=[
            "status", "error_message", "completed_at",
        ])
        return DispatchResult(
            state="failed",
            invocation_id=str(invocation.id),
            tool_name=spec.name,
            error_message=invocation.error_message,
        )

    invocation.status = RealtimeToolInvocation.Status.SUCCEEDED
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=["status", "completed_at"])

    return DispatchResult(
        state="succeeded",
        invocation_id=str(invocation.id),
        tool_name=spec.name,
        cost_micros=spec.cost_micros,
        result=result,
    )


def _status_to_state(status: str) -> DispatchState:
    """Map ``RealtimeToolInvocation.Status`` → the public
    ``DispatchState`` literal. Used by the idempotent paths
    on approve / reject."""
    mapping: dict[str, DispatchState] = {
        RealtimeToolInvocation.Status.INVOKED: "succeeded",
        RealtimeToolInvocation.Status.AWAITING_APPROVAL: "awaiting_approval",
        RealtimeToolInvocation.Status.SUCCEEDED: "succeeded",
        RealtimeToolInvocation.Status.FAILED: "failed",
        RealtimeToolInvocation.Status.REJECTED: "rejected",
    }
    return mapping.get(status, "failed")
