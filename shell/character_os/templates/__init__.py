"""Teammate templates — named starter shapes for the wizard's
Step 1 tile picker (W10).

Per `docs/design/CREATE_SPOKESPERSON_WIZARD.md` §"Templates", a small
set of named spokespeople gives new operators a starting point that
isn't a blank wizard. The mechanism ships here; the *content*
(names, briefs, defaults) is operator-collaborative and is
expected to be refined as real operators use the product.

Public surface re-exported from the package:

  - ``TEMPLATES`` — ordered tuple of ``SpokespersonTemplate`` records.
  - ``get_template(key)`` — lookup by slug; None if unknown.
"""
from __future__ import annotations

from .teammate_templates import (
    TEMPLATES,
    SpokespersonTemplate,
    get_template,
)

__all__ = [
    "TEMPLATES",
    "SpokespersonTemplate",
    "get_template",
]
