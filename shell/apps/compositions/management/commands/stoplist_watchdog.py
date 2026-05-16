"""K6.4 stoplist watchdog — surface false-positive stoplist candidates.

SESSION 165. The K6.4 verifier's stoplist
(``character_os.claim_verifier._COMMON_PROPER_NOUN_FALSE_POSITIVES``)
is hand-curated. Every prior session has surfaced 1-3 new
sentence-initial false-positive words via live operator
dogfood (`Cleanest`, `Welcome`, `Modern`, `Short`, `Alright`).
This command closes that loop by scanning verifier-flagged
events from real composition + conversation rows and
reporting the most-frequently-flagged sentence-initial
tokens.

The four data sources:

* ``Composition.verification_warnings`` — Warn-mode renders.
  Position is into the synthesized brief, which is NOT
  persisted. Without text context, we report the claim +
  count only.
* ``Composition.rejected_synthesis`` — Strict-mode rejections.
  Text IS persisted; positions point into it; we can
  classify sentence-initial vs mid-sentence.
* ``ConversationMessage.verification_warnings`` — Warn-mode
  spokesperson messages. The reply text is persisted as
  ``content`` so positions are decodable.
* ``ConversationMessage.rejected_synthesis`` — Strict
  rejections. Same shape as Composition's rejected path.

Usage::

    python manage.py stoplist_watchdog [--days=30] [--limit=20]
                                       [--workspace=<slug>]

Exit code is always 0 — this is a read-only report.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Iterable

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.compositions.models import Composition
from apps.conversations.models import ConversationMessage
from character_os.claim_verifier import (
    _COMMON_PROPER_NOUN_FALSE_POSITIVES,
    is_sentence_initial,
)


class Command(BaseCommand):
    help = (
        "Scan recent verifier-flagged events for stoplist "
        "candidates — sentence-initial common words flagged as "
        "unsupported claims."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Look back this many days (default: 30).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Top N tokens to report in each category (default: 20).",
        )
        parser.add_argument(
            "--workspace",
            default=None,
            help="Restrict to a workspace by slug. Default: all.",
        )

    def handle(self, *args, **options):
        days: int = options["days"]
        limit: int = options["limit"]
        workspace_slug: str | None = options["workspace"]
        since = timezone.now() - timedelta(days=days)

        # --- gather flagged events ---------------------------------
        events: list[_FlaggedEvent] = []
        events.extend(
            _scan_compositions(since=since, workspace_slug=workspace_slug),
        )
        events.extend(
            _scan_conversation_messages(since=since, workspace_slug=workspace_slug),
        )

        # --- aggregate ---------------------------------------------
        # sentence_initial: only when we have text context
        sentence_initial: Counter[str] = Counter()
        # mid_sentence: only when we have text context (these are the
        # verifier doing its job; surface them as such)
        mid_sentence: Counter[str] = Counter()
        # context_unknown: warnings without persisted text
        context_unknown: Counter[str] = Counter()
        # last-seen index for each token
        last_seen: dict[str, str] = {}
        # already in the stoplist (lowercase) — regressions worth flagging
        regressions: Counter[str] = Counter()

        for ev in events:
            tag = ev.timestamp.date().isoformat()
            if ev.text is None:
                context_unknown[ev.claim] += 1
            else:
                if is_sentence_initial(ev.text, ev.position):
                    sentence_initial[ev.claim] += 1
                else:
                    mid_sentence[ev.claim] += 1
                if ev.claim.lower() in _COMMON_PROPER_NOUN_FALSE_POSITIVES:
                    regressions[ev.claim] += 1
            last_seen[ev.claim] = max(last_seen.get(ev.claim, ""), tag)

        # --- render report -----------------------------------------
        out = self.stdout.write
        out(f"K6.4 stoplist watchdog — scanned {len(events)} verifier-flagged event(s)")
        out(f"  window:    last {days} day(s) (since {since.date().isoformat()})")
        out(f"  workspace: {workspace_slug or '(all)'}")
        out("")

        _render_table(
            out=out,
            title="SENTENCE-INITIAL CANDIDATES (stoplist suggestions)",
            tally=sentence_initial,
            last_seen=last_seen,
            limit=limit,
            empty_note=(
                "no sentence-initial false positives in window — "
                "stoplist coverage looks healthy"
            ),
        )

        _render_table(
            out=out,
            title="MID-SENTENCE FLAGS (verifier doing its job)",
            tally=mid_sentence,
            last_seen=last_seen,
            limit=limit,
            empty_note="no mid-sentence flags — no fabrication events in window",
        )

        _render_table(
            out=out,
            title="WARN-MODE COMPOSITION FLAGS (no text context — claim only)",
            tally=context_unknown,
            last_seen=last_seen,
            limit=limit,
            empty_note=(
                "every flag in window had text context — no claim-only "
                "warn-mode composition flags"
            ),
        )

        if regressions:
            out("REGRESSIONS — tokens already in the stoplist but still flagging")
            out("(this means a casing / form variant slipped past the stoplist)")
            out("")
            for tok, n in regressions.most_common(limit):
                out(f"  {tok}  ×{n}")
            out("")

        if sentence_initial:
            suggested = ", ".join(
                f'"{tok.lower()}"' for tok, _ in sentence_initial.most_common(limit)
            )
            out("Suggested additions to _COMMON_PROPER_NOUN_FALSE_POSITIVES:")
            out(f"  {{{suggested}}}")
            out("")
            out("Apply with one edit to character_os/claim_verifier.py;")
            out("anchor the additions in a test case before committing.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FlaggedEvent:
    """One verifier warning, with optional text context."""

    __slots__ = ("claim", "kind", "position", "text", "timestamp", "source")

    def __init__(
        self,
        *,
        claim: str,
        kind: str,
        position: int,
        text: str | None,
        timestamp,
        source: str,
    ) -> None:
        self.claim = claim
        self.kind = kind
        self.position = position
        self.text = text
        self.timestamp = timestamp
        self.source = source


def _scan_compositions(
    *,
    since,
    workspace_slug: str | None,
) -> Iterable[_FlaggedEvent]:
    qs = Composition.objects.filter(updated_at__gte=since).order_by("-updated_at")
    if workspace_slug:
        qs = qs.filter(workspace__slug=workspace_slug)
    for comp in qs:
        warnings = comp.verification_warnings or []
        rejected = comp.rejected_synthesis or ""
        for w in warnings:
            claim = w.get("claim", "")
            if not claim:
                continue
            position = w.get("position", -1)
            kind = w.get("kind", "")
            # Only Strict-rejected compositions have the source text
            text = rejected if rejected else None
            yield _FlaggedEvent(
                claim=claim,
                kind=kind,
                position=position,
                text=text,
                timestamp=comp.updated_at,
                source="composition",
            )


def _scan_conversation_messages(
    *,
    since,
    workspace_slug: str | None,
) -> Iterable[_FlaggedEvent]:
    qs = (
        ConversationMessage.objects.filter(
            created_at__gte=since,
            role=ConversationMessage.Role.SPOKESPERSON,
        )
        .order_by("-created_at")
    )
    if workspace_slug:
        qs = qs.filter(thread__spokesperson__workspace__slug=workspace_slug)
    for msg in qs:
        warnings = msg.verification_warnings or []
        rejected = msg.rejected_synthesis or ""
        # Conversation has both: the reply text on .content (when
        # not rejected) and the rejected synthesis (when rejected).
        # Pick whichever is populated — the positions in the
        # warnings list point into whatever the verifier saw.
        text = rejected or msg.content or None
        for w in warnings:
            claim = w.get("claim", "")
            if not claim:
                continue
            position = w.get("position", -1)
            kind = w.get("kind", "")
            yield _FlaggedEvent(
                claim=claim,
                kind=kind,
                position=position,
                text=text,
                timestamp=msg.created_at,
                source="conversation",
            )


def _render_table(
    *,
    out,
    title: str,
    tally: Counter,
    last_seen: dict,
    limit: int,
    empty_note: str,
) -> None:
    out(f"=== {title} ===")
    if not tally:
        out(f"  {empty_note}")
        out("")
        return
    out("")
    out(f"  {'TOKEN':<24} {'COUNT':>6}  LAST SEEN")
    out(f"  {'-' * 24} {'-' * 6}  ---------")
    for tok, n in tally.most_common(limit):
        out(f"  {tok:<24} {n:>6}  {last_seen.get(tok, '?')}")
    out("")
