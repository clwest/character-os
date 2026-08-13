"""§19 Step 9.b bootstrap-review API-surface boundary regression.

At 9.b.3a this file forbade every promotion endpoint. 9.b.3b
legitimately introduces exactly two:

* ``POST .../slots/<kind>/<purpose>/promote/`` (name:
  ``bootstrap-review-slot-promote``)
* ``POST .../fixtures/<fixture>/approve-version/`` (name:
  ``bootstrap-review-fixture-approve-version``)

This test now enumerates the AUTHORIZED URL names and asserts:

* Every existing URL is in the authorized set.
* Everything else (finalize, admit, scoring, ranking, step10
  endpoints, etc.) remains forbidden.

Any future promotion-related endpoint requires an explicit update
here so the API-surface transition remains visible in review.
"""
from __future__ import annotations

import re

from django.urls import URLPattern, URLResolver, get_resolver


# Every bootstrap-review URL name currently authorized. The set is
# closed — new names require an explicit code-review update here.
AUTHORIZED_BOOTSTRAP_URL_NAMES: frozenset[str] = frozenset(
    {
        # 9.b.0 — health.
        "bootstrap-review-health",
        # 9.b.1 — read-only browser.
        "bootstrap-review-runs-list",
        "bootstrap-review-run-detail",
        "bootstrap-review-fixture-detail",
        "bootstrap-review-slot-detail",
        "bootstrap-review-artifact-raw",
        "bootstrap-review-artifact-normalized",
        "bootstrap-review-artifact-manifest",
        "bootstrap-review-artifact-candidate",
        # 9.b.2 — reviewer decisions (append-only journal).
        "bootstrap-review-slot-decisions",
        # 9.b.3b — canonical promotion + version admission.
        "bootstrap-review-slot-promote",
        "bootstrap-review-fixture-approve-version",
    }
)

# Vocabulary that must NEVER appear in a bootstrap-review URL under
# 9.b.3b closure. Guards against accidental introduction of Step 10
# scoring / ranking / benchmark endpoints, silent admission paths,
# or aesthetic-review surfaces.
_FORBIDDEN_URL_FRAGMENTS = [
    re.compile(r"/scores/"),
    re.compile(r"/scoring/"),
    re.compile(r"/rank"),
    re.compile(r"/benchmark"),
    re.compile(r"/qualified/"),
    re.compile(r"/qualify/"),
    re.compile(r"/ai-recommend"),
    re.compile(r"/auto-select"),
    re.compile(r"/finalize/"),
]


def _iter_bootstrap_urls(patterns):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            for sub in _iter_bootstrap_urls(entry.url_patterns):
                yield sub
        elif isinstance(entry, URLPattern):
            path_str = str(entry.pattern)
            if "bootstrap-review" in path_str:
                yield path_str, entry.name


def test_every_bootstrap_review_url_is_authorized():
    resolver = get_resolver()
    matches: list[tuple[str, str | None]] = []
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            for sub in _iter_bootstrap_urls(entry.url_patterns):
                matches.append(sub)
        elif isinstance(entry, URLPattern):
            path_str = str(entry.pattern)
            if "bootstrap-review" in path_str:
                matches.append((path_str, entry.name))

    unauthorized: list[tuple[str, str | None]] = []
    for path_str, name in matches:
        if name not in AUTHORIZED_BOOTSTRAP_URL_NAMES:
            unauthorized.append((path_str, name))
    assert unauthorized == [], (
        f"bootstrap-review URLs must be enumerated in AUTHORIZED_BOOTSTRAP_URL_NAMES; "
        f"found undeclared: {unauthorized}"
    )


def test_authorized_names_are_all_registered():
    """Belt-and-suspenders — every name in the authorized set must
    resolve to a real URL. Catches accidental deletions.
    """
    resolver = get_resolver()
    registered_names: set[str] = set()
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            for _path_str, name in _iter_bootstrap_urls(entry.url_patterns):
                if name is not None:
                    registered_names.add(name)
    missing = AUTHORIZED_BOOTSTRAP_URL_NAMES - registered_names
    assert missing == set(), (
        f"URL names authorized in the test but not registered in urls.py: {missing}"
    )


def test_no_forbidden_url_fragments_present():
    resolver = get_resolver()
    matches: list[tuple[str, str | None]] = []
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            for sub in _iter_bootstrap_urls(entry.url_patterns):
                matches.append(sub)
    violators: list[tuple[str, str | None]] = []
    for path_str, name in matches:
        for pattern in _FORBIDDEN_URL_FRAGMENTS:
            if pattern.search(path_str):
                violators.append((path_str, name))
                break
    assert violators == [], (
        f"9.b.3b forbids Step-10 scoring/ranking/benchmark endpoint "
        f"vocabulary; found: {violators}"
    )
