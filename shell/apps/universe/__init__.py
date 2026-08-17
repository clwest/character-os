"""Universe substrate — the inner wall between Workspace and World.

SESSION 261 — first landed slice of the Universe substrate. See
``docs/design/UNIVERSE_SCHEMA_V1.md`` for the load-bearing contract
(with the ``on_delete=RESTRICT`` correction committed as ``75d17f5``).

Universe is opt-in and prospective:

* No auto-default Universe. Legacy Teammates keep ``universe=NULL``
  and behave exactly as they did pre-SESSION 261.
* Explicit-only canon. Universe rows are created only by operator
  action; no LLM auto-creation.
* Workspace is the outer wall (privacy / tenant). Universe is the
  inner wall (world / semantic scope inside a tenant). Cross-tenant
  is impossible; cross-Universe is impossible without an explicit
  primitive (which does NOT ship in v1).

The load-bearing invariant this app enforces alongside the FK
additions on ``Teammate`` (``apps.spokespeople``) and
``KnowledgeDocument`` (``apps.embeddings``) is:

  A Universe-scoped Teammate NEVER retrieves from a legacy
  workspace-wide (``universe=NULL``) knowledge doc, and vice
  versa. See ``UNIVERSE_SCHEMA_V1.md`` §"Retrieval truth table"
  for all nine (T.universe, D.universe, M2M) permutations.
"""
