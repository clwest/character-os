"""B-2 / E-arc — Script draft synthesis.

Slice B2.2 (SESSION 206). Per
``docs/design/AUTO_SCRIPTING_V1.md`` contract rule 2:
"Drafting flows through one named function" — every code path
that populates a ``Script`` row's draft fields goes through
``draft_script()`` here. No code outside this module wires the
synthesis primitives directly into a Script.

This module is a thin Script-row-shaped adapter over K6's
existing ``character_os.script_synthesis.build_render_brief``
pipeline (K2 retrieve → gpt-5 Responses API → K6.4 claim
verifier). The K6 pipeline is the load-bearing work; this
module remaps result-field names + handles the strict-mode
``ClaimVerifierError`` so the Script row can persist with
``verification_status='blocked'`` instead of raising into the
caller.

Per in-scope clarification: K6's in-primitive synthesis stays
unchanged. ``character_os.script_synthesis.build_render_brief``
is still the entry point for the legacy
``apps.compositions.primitives.avatar_speech`` caller; B-2
introduces a *second* surface here that targets pre-render
Script-row writes.

The split is intentional:

* **B-2 callers** (`ScriptViewSet`, future async-redraft Celery
  tasks) call ``draft_script`` → ``ScriptDraftResult`` → assign
  to Script row fields → save.
* **Legacy K6 callers** (`generate_avatar_speech` primitive,
  V6 shim `apps.videos.views`) call ``build_render_brief`` →
  ``ScriptResult`` → send brief to Runway → record chunk_ids on
  Composition.

Both paths share the underlying synthesis call; only the result
shape differs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from character_os.claim_verifier import ClaimVerifierError
from character_os.script_synthesis import build_render_brief

if TYPE_CHECKING:
    from apps.scripts.models import Script
    from apps.spokespeople.models import Spokesperson


@dataclass(slots=True)
class ScriptDraftResult:
    """Script-row-shaped synthesis result.

    Field names mirror ``Script`` model fields so a caller can
    assign attribute-by-attribute:

        result = draft_script(sp, prompt)
        script.draft_text = result.draft_text
        script.knowledge_chunk_ids = result.knowledge_chunk_ids
        ...

    ``verification_status`` mirrors ``Script.VerificationStatus``
    choices: ``verified`` / ``warned`` / ``skipped`` /
    ``trusted_passthrough`` / ``blocked`` (set when strict-mode
    verifier rejected the synthesized text).
    """

    draft_text: str
    knowledge_chunk_ids: list[str] = field(default_factory=list)
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    verification_status: str = ""
    verification_warnings: list[dict] = field(default_factory=list)


def draft_script(
    spokesperson: "Spokesperson",
    prompt: str,
    *,
    opener: str | None = None,
    verifier_mode: str | None = None,
) -> ScriptDraftResult:
    """Synthesize a draft from spokesperson + prompt.

    Delegates to K6's ``build_render_brief`` for the K2 retrieve
    → gpt-5 → verifier pipeline, then remaps the result into a
    Script-row-shaped dataclass.

    Strict verifier mode raises ``ClaimVerifierError`` inside
    ``build_render_brief``; we catch it here and return a
    ``blocked`` result. The Script row gets persisted (rule 4 —
    "Rejecting a hallucinated claim at $0.001 draft cost is
    strictly cheaper than rejecting on a rendered $0.25 Asset"),
    so the operator can see the flags + the LLM's actual text
    in the SPA without firing a render.

    Args:
        spokesperson: the speaker. ``spokesperson.workspace`` is
            the retrieval scope (rule 1).
        prompt: operator's topic / RAG query / brief.
        opener: optional K6.6 verbatim first line pin.
        verifier_mode: optional per-script override of
            ``settings.K6_CLAIM_VERIFIER_MODE``.

    Returns:
        ``ScriptDraftResult`` — never raises. The
        ``verification_status`` field tells the caller whether
        the draft was rejected.
    """
    try:
        result = build_render_brief(
            spokesperson,
            prompt,
            opener=opener,
            verifier_mode=verifier_mode,
        )
    except ClaimVerifierError as exc:
        # Strict mode rejected. Capture what the LLM produced so
        # the operator can inspect the offending text + flags in
        # the SPA. ``knowledge_chunk_ids`` left empty because
        # ClaimVerifierError doesn't carry them; B2.3's REST
        # surface can re-resolve from logs if needed.
        return ScriptDraftResult(
            draft_text=exc.synthesized_text or prompt,
            knowledge_chunk_ids=[],
            used_knowledge=False,
            model="",
            verification_status="blocked",
            verification_warnings=[u.to_dict() for u in exc.unsupported],
        )

    return ScriptDraftResult(
        draft_text=result.brief,
        knowledge_chunk_ids=[str(cid) for cid in result.chunk_ids],
        used_knowledge=result.used_knowledge,
        model=result.model,
        tokens_input=result.tokens_input,
        tokens_output=result.tokens_output,
        verification_status=result.verification_status,
        verification_warnings=list(result.verification_warnings),
    )


def snapshot_to_revision_history(script: "Script") -> None:
    """Capture the script's current draft state into
    ``script.revision_history``.

    Called by B2.3's regenerate endpoint *before* re-firing
    ``draft_script`` so the about-to-be-overwritten draft is
    preserved for audit. The caller is responsible for saving
    the model after this returns; mutation is in-place.

    Per rule 10 — ``revision_history`` entries are append-only
    audit; never mutated after they land. Chronological order
    (oldest first); SPA reverses for display.

    Idempotent on empty scripts: if ``draft_text`` is empty
    *and* no prior history exists *and* no model was set, the
    snapshot is skipped (there's nothing meaningful to capture
    yet — the row was just created and not drafted).
    """
    from django.utils import timezone

    # Skip the snapshot when there's nothing worth preserving.
    # A row that's never been drafted has no model + empty
    # draft_text; capturing that as revision 1 would just be
    # noise in the audit log.
    if not script.draft_text and not script.model and not script.revision_history:
        return

    entry = {
        "ts": timezone.now().isoformat(),
        "draft_text": script.draft_text,
        "prompt": script.prompt,
        "opener": script.opener,
        "knowledge_chunk_ids": list(script.knowledge_chunk_ids or []),
        "model": script.model,
        "verification_status": script.verification_status,
        "verification_warnings": list(script.verification_warnings or []),
        "tokens_input": script.tokens_input,
        "tokens_output": script.tokens_output,
    }
    # Chronological order — append. Prior entries unchanged.
    script.revision_history = list(script.revision_history or []) + [entry]


def apply_draft_to_script(
    script: "Script",
    result: ScriptDraftResult,
) -> None:
    """Copy a ``ScriptDraftResult`` onto a ``Script`` row.

    Convenience helper for the common case in B2.3's REST
    surface — every viewset action that fires ``draft_script``
    needs the same field-by-field assignment. The caller saves
    afterward.

    Does NOT touch ``status`` / ``approved_at`` — those are
    state-machine fields owned by the viewset (rule 10).
    """
    script.draft_text = result.draft_text
    script.knowledge_chunk_ids = result.knowledge_chunk_ids
    script.model = result.model
    script.tokens_input = result.tokens_input
    script.tokens_output = result.tokens_output
    script.verification_status = result.verification_status
    script.verification_warnings = result.verification_warnings
