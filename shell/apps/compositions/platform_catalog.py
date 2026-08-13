"""Platform catalog for the D-arc (B-14) publish-bundle workflow.

B14.1 (SESSION 205). The catalog is a closed enum per
``PUBLISH_BUNDLE_V1.md`` rule 7 — adding a new platform is a
code change, not a config knob.

Each platform record carries:

* ``key`` — stable lowercase identifier persisted on
  ``PublishVariant.platform_key``.
* ``display`` — operator-facing label (used in
  ``Composition.name`` per rule 8 + the SPA picker).
* ``target_ratio`` — one of ``apps.compositions``' supported
  ``reformat_clip`` ratios (1280:720 / 720:1280 / 960:960).
* ``max_duration_ms`` — platform's hard duration cap.

The values get snapshotted onto each ``PublishVariant`` row at
create time so old bundles render at the original specs even
if the catalog evolves later (rule 7 + the immutability story
in Q-d-9).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Platform:
    key: str
    display: str
    target_ratio: str
    max_duration_ms: int


# v1 catalog — five platforms (Q-d-1 lock). Adding a sixth is
# a code change + scope conversation, not a config knob.
_PLATFORMS: dict[str, Platform] = {
    "reels": Platform(
        key="reels",
        display="Instagram Reels",
        target_ratio="720:1280",
        max_duration_ms=60_000,
    ),
    "shorts": Platform(
        key="shorts",
        display="YouTube Shorts",
        target_ratio="720:1280",
        max_duration_ms=60_000,
    ),
    "tiktok": Platform(
        key="tiktok",
        display="TikTok",
        target_ratio="720:1280",
        max_duration_ms=90_000,
    ),
    "x_twitter": Platform(
        key="x_twitter",
        display="X / Twitter",
        target_ratio="1280:720",
        max_duration_ms=140_000,
    ),
    "linkedin": Platform(
        key="linkedin",
        # Q-d-2: 1280:720 (16:9) is the v1 default. Per-bundle
        # override to 960:960 deferred to a later slice.
        display="LinkedIn",
        target_ratio="1280:720",
        max_duration_ms=30_000,
    ),
}


def get_platform(key: str) -> Platform:
    """Return the Platform record for ``key``.

    Raises ``KeyError`` with a helpful message listing the
    valid keys when ``key`` isn't in the catalog.
    """
    try:
        return _PLATFORMS[key]
    except KeyError:
        raise KeyError(
            f"unknown platform key {key!r}; valid keys: "
            f"{sorted(_PLATFORMS.keys())}"
        ) from None


def all_platform_keys() -> list[str]:
    """All platform keys in catalog declaration order. Used by
    the SPA picker + REST validator."""
    return list(_PLATFORMS.keys())


def all_platforms() -> list[Platform]:
    """All platform records in catalog declaration order. Used
    by the SPA picker + the launch-time variant builder."""
    return list(_PLATFORMS.values())


# Defense-in-depth hard cap on platforms per bundle. v1 catalog
# size is 5; this is what gets enforced (the catalog count
# matters only if we ever add a sixth platform without
# re-thinking the cap). Q-d-7 lock.
MAX_PLATFORMS_PER_BUNDLE = 10


# Recipe + template_kind that publish_variant compositions
# carry. Read by ``apps.billing.services.get_usage()`` to
# exclude variants from the per-month videos cap (rule 5 +
# Q-d-4). Centralized here so a future rename doesn't drift
# between the recipe and the cap exclusion.
PUBLISH_VARIANT_TEMPLATE_KIND = "publish_variant"
