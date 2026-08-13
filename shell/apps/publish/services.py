"""Helper functions for the D-arc publish-bundle arc.

B14.3 (SESSION 205). Mirrors apps.campaigns.services'
``rollup_campaign_status`` + the cost helpers. Cleanly
separates "bundle status rollup" + "wall-time forecast"
+ "platform-cap defense" from the viewset's REST concerns.

Three surfaces:

* ``check_bundle_platforms(selected_platforms)`` — defense-
  in-depth platform-cap check (rule 7 — hard 10). Raises
  ``ValidationError``. The serializer's
  ``validate_selected_platforms`` does most of the work; this
  is the launch-time backstop in case rows were edited via
  admin / shell.
* ``estimate_bundle_wall_time_s(variant_count)`` — wall-time
  forecast for the SPA launch modal. Per Q-d-6: $0 cost,
  ~5s per variant on ffmpeg.
* ``rollup_bundle_status(bundle)`` — examines the variants'
  terminal-state distribution; flips the bundle to COMPLETED
  / PARTIAL / FAILED accordingly. Called by the post_save
  Composition signal (B14.3) + the retry handler.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.compositions.platform_catalog import MAX_PLATFORMS_PER_BUNDLE

if TYPE_CHECKING:
    from .models import PublishBundle


# Q-d-6 — flat estimate per variant. ffmpeg trim+reformat on
# already-downloaded source bytes runs ~5s; this is the SPA's
# launch-modal "this will take ~X seconds" hint.
_WALL_TIME_PER_VARIANT_S = 5


def check_bundle_platforms(selected_platforms: list[str]) -> None:
    """Defense-in-depth cap. The serializer caps at 10 via
    ListField(max_length=10); this re-checks at launch time
    in case a row was edited outside the REST surface.

    Raises ``ValidationError`` if violated.
    """
    if not selected_platforms:
        raise ValidationError(
            "selected_platforms cannot be empty"
        )
    if len(selected_platforms) > MAX_PLATFORMS_PER_BUNDLE:
        raise ValidationError(
            f"selected_platforms exceeds the per-bundle cap "
            f"({len(selected_platforms)} > "
            f"{MAX_PLATFORMS_PER_BUNDLE})."
        )


def estimate_bundle_wall_time_s(variant_count: int) -> int:
    """Wall-time forecast for the SPA launch modal. Rounds
    nothing; the SPA renders this as ``"~Xs"``."""
    if variant_count < 0:
        return 0
    return variant_count * _WALL_TIME_PER_VARIANT_S


def rollup_bundle_status(bundle: "PublishBundle") -> bool:
    """Examine variant terminal-state distribution; flip the
    bundle's status accordingly. Mirrors
    ``apps.campaigns.services.rollup_campaign_status``.

    Returns True when the bundle reached a new terminal state
    on this call; False when nothing changed.

    Rules:
    * Any variant still PENDING / QUEUED / RUNNING → leave
      bundle in IN_FLIGHT (or LAUNCHING).
    * All variants terminal:
      * All COMPLETED → bundle COMPLETED.
      * Some COMPLETED + some FAILED → bundle PARTIAL.
      * All FAILED → bundle FAILED.
    * ``completed_at`` set on the bundle for any terminal flip.

    Idempotent — re-running on a stable bundle is a no-op.

    Lazy import for the models — called from
    apps.publish.signals at module-load-via-ready() time so
    the model import has to happen at call time, not
    module-load time.
    """
    from .models import PublishBundle, PublishVariant

    status_counts = {
        choice: 0 for choice, _ in PublishVariant.Status.choices
    }
    for status_value in bundle.variants.values_list("status", flat=True):
        status_counts[status_value] = status_counts.get(status_value, 0) + 1

    terminal = (
        status_counts[PublishVariant.Status.COMPLETED]
        + status_counts[PublishVariant.Status.FAILED]
    )
    in_flight = (
        status_counts[PublishVariant.Status.PENDING]
        + status_counts[PublishVariant.Status.QUEUED]
        + status_counts[PublishVariant.Status.RUNNING]
    )
    total = terminal + in_flight

    if total == 0 or in_flight > 0:
        return False

    succeeded = status_counts[PublishVariant.Status.COMPLETED]
    failed = status_counts[PublishVariant.Status.FAILED]
    if succeeded == terminal:
        new_status = PublishBundle.Status.COMPLETED
    elif failed == terminal:
        new_status = PublishBundle.Status.FAILED
    else:
        new_status = PublishBundle.Status.PARTIAL

    if bundle.status == new_status:
        return False

    bundle.status = new_status
    if bundle.completed_at is None:
        bundle.completed_at = timezone.now()
    bundle.save(update_fields=["status", "completed_at", "updated_at"])
    return True
