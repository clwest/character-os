# SESSION 276 Slice 7 / Delta Stage 2 — deterministic audience backfill.
#
# Persists the audience classification rehearsed in Slice 6 (§89-§93,
# Q-276-17 CONFIRMED). This migration is DATA-ONLY; the schema was
# added in ``0007_session276_audience_scope``.
#
# Behavior at migration time:
#
#   * PREFLIGHT — abort if any KnowledgeDocument row has
#     ``is_active=False``. Stage 2 was designed and rehearsed against
#     zero-inactive-row state (Slice 4 §55, Slice 6 §87). Semantics for
#     inactive rows belong to a future signal-extension slice
#     (Q-276-18 / Stage 3).
#
#   * Rule A — every KD with ≥1 spokesperson through-row receives
#     ``audience_scope='character'``. Generic predicate — the surviving
#     explicit M2M is positive evidence of character-scoped intent.
#
#   * Rule B — the three frozen evidence-backed Universe canon UUIDs
#     receive ``audience_scope='universe'``. NOT a generic shape-based
#     predicate: assigning UNIVERSE to any ``(universe non-null, M2M
#     empty)`` row would re-create the exact ambiguity Delta was
#     introduced to eliminate. The three IDs are historical constants
#     tied to the 2026-08-21 dataset audit (Slice 4 §55.1).
#
#   * Rule C — the ten ambiguous rows (``universe=NULL, M2M=∅`` —
#     Slice 4 §55.2) are NOT touched. They remain
#     ``audience_scope=NULL`` and require explicit operator triage in a
#     later Delta stage before they can be classified.
#
# Reverse behavior:
#
#   Strict inverse — only rows that Stage 2 would have set are reverted
#   to NULL. This is guaranteed safe as the inverse of THIS migration
#   at THIS migration boundary. It is NOT intended as a future operator
#   audience-reset mechanism; if later Delta stages have set additional
#   values, running reverse-through-here would clobber them. Practical
#   guidance: reverse is only strictly-inverse pre-Stage-3.
#
# See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md``:
#   §46-§71  Direction Delta design + falsification (Slice 4)
#   §72-§85  Delta Stage 1 substrate (Slice 5)
#   §86-§98  Q-276-17 rehearsal (Slice 6)

from django.db import migrations
from django.db.models import Count


# Evidence-backed intentional Universe canon set. Frozen for this
# historical migration. Do NOT extend this list without a new audit
# slice — the whole point of Direction Delta is to stop deriving
# audience from ambiguous shape.
#
# Provenance:
#   * 8f825c98-… — Ruby / Fox & Flour Bakery House Policies & Hours.
#     Confirmed intentional canon by SESSION 275 §Slice 1 evidence
#     and Slice 4 §55.1.
#   * d8ab3d2c-… — SESSION 272 rivet-debug-ctl experimental substrate.
#     Intentional Universe-shared canon by construction (test workspace).
#   * 64c91888-… — SESSION 272 rivet-debug-exp experimental substrate.
#     Intentional Universe-shared canon by construction.
UNIVERSE_CANON_ROWS_20260821 = [
    "8f825c98-f420-4867-8700-6d4db6832d9d",
    "d8ab3d2c-cab3-41f3-91a1-bab8ba88f5b6",
    "64c91888-5534-418b-bbe2-33743f815bcf",
]

# String literals (not the runtime ``AudienceScope`` enum) so this
# historical migration cannot be broken by a future model-code rename
# or enum-value change. Values must match the ``AudienceScope.choices``
# tuple keys at the time of the 0007 schema migration.
AUDIENCE_CHARACTER = "character"
AUDIENCE_UNIVERSE = "universe"


class Stage2PreflightError(RuntimeError):
    """Raised when the Stage 2 preflight fails.

    Distinct exception type so tests + operators can identify a preflight
    failure vs. any other RuntimeError during migration.
    """


def apply_forward(apps, schema_editor):
    """Forward: preflight + Rule A + Rule B."""
    KnowledgeDocument = apps.get_model("embeddings", "KnowledgeDocument")

    # PREFLIGHT — zero inactive rows expected.
    inactive_count = KnowledgeDocument.objects.filter(is_active=False).count()
    if inactive_count > 0:
        raise Stage2PreflightError(
            f"SESSION 276 Slice 7 / Delta Stage 2 preflight failed: "
            f"found {inactive_count} inactive KnowledgeDocument row(s). "
            "Stage 2 semantics were designed and rehearsed against "
            "zero-inactive-row state (Slice 4 §55, Slice 6 §87). "
            "Semantics for inactive rows depend on the Teammate-delete "
            "signal extension (Q-276-18 / Stage 3) which stamps "
            "audience_scope='none' on orphan-archive. Halt this "
            "migration, design/deploy the signal extension first, and "
            "revisit before re-attempting Stage 2."
        )

    # Rule A — CHARACTER for every row with ≥1 spokesperson.
    KnowledgeDocument.objects.annotate(
        _sp_count=Count("spokespeople"),
    ).filter(_sp_count__gt=0).update(audience_scope=AUDIENCE_CHARACTER)

    # Rule B — UNIVERSE for the three frozen canon IDs only.
    KnowledgeDocument.objects.filter(
        pk__in=UNIVERSE_CANON_ROWS_20260821,
    ).update(audience_scope=AUDIENCE_UNIVERSE)


def apply_reverse(apps, schema_editor):
    """Reverse: strict inverse of ``apply_forward``.

    Reverses ONLY the deterministic assignments that Stage 2 would set.
    Filters on the current stamped value to avoid clobbering audience
    values set by later Delta stages. Safe pre-Stage-3; documented
    caveat for post-Stage-3 rollback.
    """
    KnowledgeDocument = apps.get_model("embeddings", "KnowledgeDocument")

    # Reverse Rule B — revert the frozen canon IDs iff they are still
    # UNIVERSE (which they will be immediately post-forward; may not be
    # if a later stage has reassigned them).
    KnowledgeDocument.objects.filter(
        pk__in=UNIVERSE_CANON_ROWS_20260821,
        audience_scope=AUDIENCE_UNIVERSE,
    ).update(audience_scope=None)

    # Reverse Rule A — revert rows to NULL only if they are currently
    # CHARACTER AND still have ≥1 spokesperson (matching the shape the
    # forward set them from). If a later stage has changed the value to
    # something other than CHARACTER, we do not touch it.
    KnowledgeDocument.objects.annotate(
        _sp_count=Count("spokespeople"),
    ).filter(
        _sp_count__gt=0, audience_scope=AUDIENCE_CHARACTER,
    ).update(audience_scope=None)


class Migration(migrations.Migration):

    dependencies = [
        ("embeddings", "0007_session276_audience_scope"),
    ]

    operations = [
        migrations.RunPython(apply_forward, apply_reverse),
    ]
