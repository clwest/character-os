"""Cross-workspace M2M validation for ``KnowledgeDocument``.

The privacy contract (``docs/design/KNOWLEDGE_LAYER.md``
§"Contract rules" 1) requires that every spokesperson on a
document's M2M belongs to that document's workspace.
``KnowledgeDocument.clean()`` catches model-form validation
flows; this signal catches the post-save attach flow
(``doc.spokespeople.add(sp)``) which doesn't trigger
``clean()``.

The signal fires on ``pre_add`` only — checking before the
attach commits means we can ``raise`` to abort, leaving the
M2M in a consistent state. ``post_add`` would already have
written the join row before we could veto it.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from apps.spokespeople.models import Teammate

from .models import KnowledgeDocument

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=KnowledgeDocument.spokespeople.through)
def reject_cross_workspace_spokesperson(
    sender,
    instance,
    action,
    reverse,
    pk_set,
    **kwargs,
) -> None:
    """Veto any ``doc.spokespeople.add(sp)`` where ``sp`` is in
    a different workspace than ``doc``."""
    if action != "pre_add":
        return
    if not pk_set:
        return

    if reverse:
        # ``sp.knowledge_documents.add(doc)`` — instance is the
        # Teammate, pk_set holds KnowledgeDocument ids.
        sp = instance
        bad_doc_ids = list(
            KnowledgeDocument.objects.filter(pk__in=pk_set)
            .exclude(workspace_id=sp.workspace_id)
            .values_list("pk", flat=True)
        )
        if bad_doc_ids:
            raise ValidationError(
                "Cannot attach spokesperson "
                f"{sp.name!r} (workspace={sp.workspace_id}) to "
                f"knowledge documents from another workspace: "
                f"{bad_doc_ids}"
            )
        return

    # Forward: ``doc.spokespeople.add(sp)`` — instance is the
    # KnowledgeDocument, pk_set holds Teammate ids.
    doc = instance
    bad_sp_ids = list(
        Teammate.objects.filter(pk__in=pk_set)
        .exclude(workspace_id=doc.workspace_id)
        .values_list("pk", flat=True)
    )
    if bad_sp_ids:
        raise ValidationError(
            f"Cannot attach spokespeople from another workspace to "
            f"knowledge document {doc.title!r} "
            f"(workspace={doc.workspace_id}). Bad spokespeople: "
            f"{bad_sp_ids}"
        )


# ---------------------------------------------------------------------
# SESSION 261 — Universe M2M invariant.
#
# Peer receiver (NOT a modification of the workspace one — cleaner
# separation of concerns; two @receiver decorators on the same
# signal + sender both fire in registration order). Both signals
# fire on pre_add; the workspace receiver fires first (outer wall).
# See UNIVERSE_SCHEMA_V1.md §"apps/embeddings/signals.py — extension".
# ---------------------------------------------------------------------


@receiver(m2m_changed, sender=KnowledgeDocument.spokespeople.through)
def reject_cross_universe_spokesperson(
    sender,
    instance,
    action,
    reverse,
    pk_set,
    **kwargs,
) -> None:
    """Veto ``doc.spokespeople.add(sp)`` when the pair violates
    the Universe M2M invariant.

    Rejected pairings (per UNIVERSE_SCHEMA_V1.md §"clean() /
    m2m_changed / signal contract"):

    * ``doc.universe = U_X`` and ``sp.universe = U_Y`` (X != Y).
    * ``doc.universe = U_X`` and ``sp.universe = NULL``.
    * ``doc.universe = NULL`` and ``sp.universe = U_X``.

    Allowed:

    * ``doc.universe = NULL`` and ``sp.universe = NULL`` (legacy).
    * ``doc.universe = U_X`` and ``sp.universe = U_X`` (matching).
    """
    if action != "pre_add":
        return
    if not pk_set:
        return

    if reverse:
        # ``sp.knowledge_documents.add(doc)`` — instance is the
        # Teammate, pk_set holds KnowledgeDocument ids.
        sp = instance
        sp_universe = sp.universe_id
        bad_doc_ids = list(
            KnowledgeDocument.objects.filter(pk__in=pk_set)
            .exclude(universe_id=sp_universe)
            .values_list("pk", flat=True)
        )
        if bad_doc_ids:
            raise ValidationError(
                f"Cannot attach spokesperson {sp.name!r} "
                f"(universe={sp_universe}) to knowledge documents from "
                f"a different Universe: {bad_doc_ids}"
            )
        return

    # Forward: ``doc.spokespeople.add(sp)``.
    doc = instance
    doc_universe = doc.universe_id
    bad_sp_ids = list(
        Teammate.objects.filter(pk__in=pk_set)
        .exclude(universe_id=doc_universe)
        .values_list("pk", flat=True)
    )
    if bad_sp_ids:
        raise ValidationError(
            f"Cannot attach spokespeople from another Universe to "
            f"knowledge document {doc.title!r} "
            f"(universe={doc_universe}). Bad spokespeople: "
            f"{bad_sp_ids}"
        )
