"""Services for NarrativeMemory.

SESSION 264 Slice 2 established the embedding + provenance
resolvers. SESSION 281 Slice 281.1 adds ``suggest_memories_from_composition``
(the model-as-curator surface backing the eventual v1.5
"few ideas from what just happened" panel).

Load-bearing rules:

* **Embedding NEVER hits KnowledgeChunk / ConversationEmbedding.**
  Vectors land on ``NarrativeMemory.embedding_vector`` (this app's
  own column). Uses ``apps.embeddings.embedding_service.embed``,
  the same shared entry point ``KnowledgeChunk`` embedding uses,
  so cosine geometry matches across canon + memory retrieval.
* **Embedding failures do not roll back the promotion.** The row
  lands with ``embedding_vector=NULL``; retrieval simply excludes
  it until a re-embed lands. Operator intent (a manual "Remember
  this" click) is authoritative and must not be lost to a
  provider hiccup.
* **Idempotent.** If a row already has an embedding_vector,
  ``embed_memory`` is a no-op unless ``force=True``. Avoids paying
  for a re-embed on every promote-batch resubmit.
* **Mock-safe.** ``EMBEDDING_FORCE_MOCK=1`` env or
  ``settings.EMBEDDING_FORCE_MOCK=True`` routes through the
  deterministic hash-derived vector — same path canon-lane tests
  use.
* **Curator NEVER writes.** ``suggest_memories_from_composition``
  is a read-only surface; it MUST NOT create, edit, archive,
  supersede, or otherwise mutate any ``NarrativeMemory`` row.
  The operator's ``[Remember this]`` click remains the sole
  promotion path via ``promote_from_composition``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone as _dt_timezone
from typing import Any, Iterable

from django.core.cache import cache
from django.utils import timezone

from apps.embeddings.embedding_service import embed

from .models import NarrativeMemory

logger = logging.getLogger(__name__)


def embed_memory(memory: NarrativeMemory, *, force: bool = False) -> bool:
    """Populate ``memory.embedding_vector`` from ``memory.body``.

    Returns ``True`` if the row's embedding fields were written,
    ``False`` if the call was a no-op (already embedded and
    ``force=False``, or embedding failed and the row was left
    untouched).

    Never raises to the caller — embedding failures are logged
    and swallowed so a bad provider call cannot roll back the
    surrounding operator action (audit §9: operator authority is
    the primary signal).
    """
    if memory.embedding_vector is not None and not force:
        return False

    body = (memory.body or "").strip()
    if not body:
        # Serializer + model.clean() already reject blank bodies.
        # Defensive: don't spend money on a blank prompt.
        return False

    try:
        result = embed(body)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "narrative_memory embed_failed memory=%s reason=%s",
            memory.id, exc,
        )
        return False

    memory.embedding_vector = result.vector
    memory.embedding_model = result.model
    memory.embedding_dimension = result.dimension
    memory.embedding_cost_micros = result.cost_micros
    memory.embedded_at = timezone.now()
    memory.save(update_fields=[
        "embedding_vector",
        "embedding_model",
        "embedding_dimension",
        "embedding_cost_micros",
        "embedded_at",
        "updated_at",
    ])
    return True


def embed_memories(memories: Iterable[NarrativeMemory], *, force: bool = False) -> int:
    """Embed a batch. Returns the count that had their vectors
    written. Individual failures are logged and skipped."""
    count = 0
    for memory in memories:
        if embed_memory(memory, force=force):
            count += 1
    return count


# ============================================================
# SESSION 264 Slice 3 — Composition memory provenance resolver
# ============================================================
#
# ``CompositionSerializer.memories_used`` enriches the raw
# ``Composition.memory_ids`` JSONField (a flat list of
# ``NarrativeMemory.id`` strings written by SESSION 264 Slice 2
# at synthesis time) into a display-friendly list the SPA panel
# can render without a second network hop.
#
# Read-only. Never mutates any NarrativeMemory. Never touches
# KnowledgeDocument / KnowledgeChunk. Respects the audit's
# "Remembered != Canon" rule; this is provenance visibility,
# not promotion.
#
# Rows that have been ARCHIVED or SUPERSEDED SINCE the render
# still appear — they FED the render at the time, and hiding
# them would erase provenance. The serialized shape carries the
# current status so the SPA can render an "archived after this
# render" indicator.


def resolve_memory_ids_to_rows(
    memory_ids: list[str],
    *,
    workspace,
) -> list[dict]:
    """Resolve a flat list of ``NarrativeMemory.id`` strings into a
    display-shaped payload for the SPA composition detail page.

    Workspace-scoped defense-in-depth — the retrieval predicate
    already filters by workspace at synthesis time, but a
    cross-workspace ID smuggled into ``Composition.memory_ids``
    would be silently dropped here (never re-hydrated across the
    tenant boundary).

    Missing / archived-since-render / superseded-since-render
    rows all appear (with their current status surfaced) so the
    operator sees the honest historical provenance instead of a
    silent gap.

    Returns ``[]`` when ``memory_ids`` is empty or nothing
    resolves in-workspace.
    """
    if not memory_ids:
        return []

    ordered_ids = [str(mid) for mid in memory_ids if mid]
    if not ordered_ids:
        return []

    rows = {
        str(m.id): m
        for m in NarrativeMemory.objects
        .filter(id__in=ordered_ids, workspace=workspace)
        .select_related("episode", "universe")
        .prefetch_related("witnessed_by")
    }

    payload: list[dict] = []
    for mid in ordered_ids:
        m = rows.get(mid)
        if m is None:
            # Row deleted / never existed / cross-workspace
            # smuggle attempt — surface as a stub so the SPA
            # can render a "no longer available" indicator
            # without breaking layout.
            payload.append({
                "id": mid,
                "resolved": False,
            })
            continue

        witnesses = [
            {"id": str(w.id), "name": w.name}
            for w in m.witnessed_by.all()
        ]
        payload.append({
            "id": str(m.id),
            "resolved": True,
            "kind": m.kind,
            "body": m.body,
            "weight": m.weight,
            "status": m.status,
            "archived_at": (
                m.archived_at.isoformat() if m.archived_at else None
            ),
            "witnessed_by": witnesses,
            "episode_id": str(m.episode_id) if m.episode_id else None,
            "episode_title": m.episode.title if m.episode_id else None,
            "universe_id": str(m.universe_id) if m.universe_id else None,
            "universe_name": m.universe.name if m.universe_id else None,
            "source_composition_id": (
                str(m.source_composition_id) if m.source_composition_id else None
            ),
        })
    return payload


# ============================================================
# SESSION 281 Slice 281.1 — Model-as-curator suggestion service
# ============================================================
#
# Given a completed Composition, propose a small number of
# candidate memory bodies the operator MAY choose to promote.
# Lifts the validated Q280.9 probe behavior into production:
# same prompt shape, same provider stack, tolerant JSON parsing,
# Redis-backed 30-minute cache keyed so a new same-composition
# promotion rotates the cache naturally.
#
# Read-only. This service NEVER creates, edits, archives,
# supersedes, or otherwise mutates any NarrativeMemory row. The
# operator's [Remember this] click remains the sole promotion
# path via ``promote_from_composition`` in ``apps.memory.views``.
#
# See docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md §75-§79
# for the design + evidence trail, and
# docs/design/SESSION_281_ORIENTATION_AND_SCOPE_LOCK.md for the
# Slice 281.1 scope-lock this implements.


# Same provider stack as next_episode_suggestions v1 and Q280.9
# probe (gpt-5.6-terra via OpenAI responses.create JSON-object
# output). Kept identical so the runtime cost + prompt-adherence
# characteristics Chris + ChatGPT scored during SESSION 280 carry
# forward unchanged.
_CURATOR_MODEL = "gpt-5.6-terra"
_CURATOR_MAX_OUTPUT_TOKENS = 2000
_CURATOR_REASONING_EFFORT = "low"

# 30-minute TTL per SESSION 281 scope-lock (differs deliberately
# from the v1 story-direction service's 600s cache — curator
# output is more expensive and less time-sensitive than possible-
# next-Episode suggestions).
_CURATOR_CACHE_TTL_SECONDS = 1800

_CURATOR_DEFAULT_N = 3
_CURATOR_MIN_N = 1
_CURATOR_MAX_N = 5


class SuggestMemoriesError(RuntimeError):
    """Base class for curator service errors."""


class SuggestMemoriesUpstreamError(SuggestMemoriesError):
    """LLM provider was unreachable or returned unusable output.

    Mapped to HTTP 502 by the ``CompositionViewSet.suggested_memories``
    endpoint. Never raised for empty-substrate cases — those return
    ``candidates=[]`` at 200.
    """


@dataclass(frozen=True)
class _CuratorSubstrateSnapshot:
    """Read-only snapshot of what the LLM will see for one
    completed Composition.

    ``latest_source_memory_at`` is the cache-invalidation axis:
    the max ``created_at`` across ``NarrativeMemory`` rows whose
    ``source_composition`` is this Composition. A new
    ``[Remember this]`` on the same Composition (curator card OR
    the existing textarea) rolls this timestamp forward and
    naturally rotates the cache key.
    """

    composition_id: str
    universe_id: str
    universe_name: str
    universe_brief: str
    episode_id: str
    episode_title: str
    episode_topic: str
    cast: list[dict]
    prior_episodes: list[dict]
    existing_memories: list[dict]
    dialogue_text: str
    latest_source_memory_at: str


def _snapshot_for_curator(composition) -> _CuratorSubstrateSnapshot:
    """Read-only snapshot for the curator prompt.

    All reads scoped to the Composition's Universe. Archived
    Episodes excluded (same predicate v1 suggestion service uses).
    Existing memories filtered to REMEMBERED + not-yet-archived so
    the "do not propose duplicates" instruction has an accurate
    reference set.
    """
    from apps.spokespeople.models import Teammate
    from apps.universe.models import Episode

    from .models import NarrativeMemoryStatus

    episode = composition.episode
    universe = episode.universe if episode is not None else None

    prior_episodes_qs = (
        Episode.objects
        .filter(universe=universe, archived_at__isnull=True)
        .order_by("created_at")
        if universe is not None
        else Episode.objects.none()
    )
    prior_episodes = list(prior_episodes_qs)

    cast = (
        list(Teammate.objects.filter(universe=universe))
        if universe is not None
        else []
    )

    existing_memories_qs = (
        NarrativeMemory.objects
        .filter(
            universe=universe,
            status=NarrativeMemoryStatus.REMEMBERED,
            archived_at__isnull=True,
        )
        .order_by("created_at")
        .prefetch_related("witnessed_by")
        if universe is not None
        else NarrativeMemory.objects.none()
    )
    existing_memories = list(existing_memories_qs)

    # Cache-invalidation axis — composition-scoped per SESSION 281
    # scope-lock. A new [Remember this] on THIS composition rolls
    # this timestamp forward.
    latest_source_dt = (
        NarrativeMemory.objects
        .filter(source_composition=composition)
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    latest_source_memory_at = (
        latest_source_dt.isoformat() if latest_source_dt else ""
    )

    # Strip leading "# ..." comment header from synthesized_brief,
    # same as the Q280.9 probe (lines 197-209).
    brief_text = (composition.synthesized_brief or "").strip()
    body_lines: list[str] = []
    body_started = False
    for line in brief_text.splitlines():
        if not body_started:
            if line.startswith("#") or not line.strip():
                continue
            body_started = True
        body_lines.append(line)
    dialogue_text = "\n".join(body_lines).strip()

    return _CuratorSubstrateSnapshot(
        composition_id=str(composition.id),
        universe_id=str(universe.id) if universe is not None else "",
        universe_name=(universe.name or "") if universe is not None else "",
        universe_brief=(
            (universe.brief or "").strip() if universe is not None else ""
        ),
        episode_id=str(episode.id) if episode is not None else "",
        episode_title=(episode.title or "") if episode is not None else "",
        episode_topic=(
            (episode.operator_topic or "") if episode is not None else ""
        ),
        cast=[
            {
                "id": str(t.id),
                "name": t.name,
                "tone": t.tone_archetype or "",
                "personality_prefix": (t.personality or "")[:220],
            }
            for t in cast
        ],
        prior_episodes=[
            {
                "id": str(e.id),
                "title": e.title or "",
                "operator_topic": e.operator_topic or "",
                "is_current": (
                    episode is not None and e.id == episode.id
                ),
            }
            for e in prior_episodes
        ],
        existing_memories=[
            {
                "id": str(m.id),
                "kind": m.kind,
                "witnesses": sorted(
                    [t.name for t in m.witnessed_by.all()]
                ),
                "body": (m.body or "").strip(),
            }
            for m in existing_memories
        ],
        dialogue_text=dialogue_text,
        latest_source_memory_at=latest_source_memory_at,
    )


# System prompt — lifted verbatim from Q280.9 probe (§75.4 audit
# doc). Operator-facing phrasing; NarrativeMemory kind vocabulary
# (event / action / promise / dialogue_callback / world_detail)
# appears as the JSON output contract the LLM produces so
# ``promote_from_composition`` can accept ``kind`` unchanged
# when Slice 281.2 wires the [Remember this] card.
_CURATOR_SYSTEM_PROMPT = (
    "You are a story-development assistant helping an operator "
    "decide which details from a completed dialogue scene are "
    "worth carrying forward into their story world.\n\n"
    "The operator has just finished making a scene. Your job "
    "is to propose 3-5 short 'memory' candidates — small facts, "
    "agreements, promises, running jokes, or open questions "
    "that the operator might want to remember for future "
    "scenes in this world.\n\n"
    "The operator remains the authority. You are NOT deciding "
    "what matters — you are noticing what MAY matter and "
    "offering candidates. The operator will pick, edit, or "
    "discard.\n\n"
    "GUIDELINES:\n"
    "- Each candidate should be one sentence, phrased as a "
    "durable past event or standing rule — not as scene "
    "direction and not as advice to the operator.\n"
    "- Look for details with FUTURE STORYTELLING GRAVITY: "
    "things that could plausibly be referenced, tested, "
    "broken, called back, or paid off in a future scene.\n"
    "- Prefer paraphrased wording that captures the essence "
    "of a moment rather than a verbatim quote. Verbatim quotes "
    "are fine when the phrasing itself is the memorable thing.\n"
    "- Distinguish resolved facts (something concluded) from "
    "open loops (something unresolved). Both can be memory-"
    "worthy, but they preserve different storytelling "
    "affordances.\n"
    "- Do NOT invent facts that are not present in the "
    "dialogue. Faithfulness matters more than dramatic "
    "embellishment.\n"
    "- Do NOT propose a candidate that duplicates an existing "
    "memory already listed for this world.\n\n"
    "Each candidate should be classified by one of these "
    "narrative kinds:\n"
    "- event: a thing that happened in the world\n"
    "- action: a specific thing a character did\n"
    "- promise: a character or the world committed to a "
    "future outcome\n"
    "- dialogue_callback: a notable line or phrase worth "
    "calling back\n"
    "- world_detail: a discovered or revealed fact about the "
    "world\n\n"
    "Each candidate has associated witnesses — the characters "
    "who were present for the event. Use character names as "
    "listed in the cast. Use 'everyone' if the whole cast was "
    "present.\n\n"
    "Also provide a short 'narrative_gravity_note' explaining "
    "what future storytelling affordance the candidate "
    "preserves. This is your reasoning; the operator will "
    "read it while deciding.\n\n"
    "OUTPUT FORMAT: JSON object with a single key 'candidates' "
    "whose value is a list of 3-5 objects, each with:\n"
    "  - body: one-sentence memory text\n"
    "  - kind: one of the five kinds listed above\n"
    "  - witnesses: list of character names OR the string "
    "'everyone'\n"
    "  - narrative_gravity_note: short string explaining "
    "future affordance\n"
)


def _build_curator_task_message(
    snap: _CuratorSubstrateSnapshot, *, n: int,
) -> str:
    """Compose the task message. Mirrors Q280.9 probe layout —
    Universe brief, cast, prior Episodes (with current marked),
    existing-memory duplicate-guard set, then the just-completed
    scene's dialogue."""
    lines: list[str] = []

    lines.append(f"UNIVERSE: {snap.universe_name}")
    if snap.universe_brief:
        lines.append("")
        lines.append("WORLD BRIEF:")
        lines.append(snap.universe_brief)

    lines.append("")
    lines.append("CAST:")
    for t in snap.cast:
        parts = []
        if t["tone"]:
            parts.append(f"tone={t['tone']}")
        pers = (t["personality_prefix"] or "").strip()
        if pers:
            parts.append(f"personality={pers!r}")
        detail = "; ".join(parts) if parts else "(no voice detail)"
        lines.append(f"- {t['name']}: {detail}")

    lines.append("")
    lines.append("EPISODES SO FAR (earliest first):")
    for i, e in enumerate(snap.prior_episodes, 1):
        topic = (e["operator_topic"] or "").strip().replace("\n", " ")
        marker = " ← the just-completed scene" if e["is_current"] else ""
        lines.append(f"{i:>3}. {e['title']!r}{marker}")
        if topic and topic != e["title"]:
            lines.append(f"      topic: {topic}")

    lines.append("")
    if snap.existing_memories:
        lines.append(
            "EXISTING MEMORIES ALREADY REMEMBERED IN THIS WORLD "
            "(do NOT propose duplicates):"
        )
        for m in snap.existing_memories:
            witnesses = ",".join(m["witnesses"]) or "everyone"
            body = (m["body"] or "").strip().replace("\n", " ")
            lines.append(
                f"- (kind={m['kind']}, witnesses={witnesses}): {body}"
            )
    else:
        lines.append("EXISTING MEMORIES: (none yet)")

    lines.append("")
    lines.append("THE SCENE JUST COMPLETED:")
    lines.append(f"Episode title: {snap.episode_title}")
    lines.append(f"Episode topic: {snap.episode_topic}")
    lines.append("")
    lines.append("Dialogue:")
    lines.append(snap.dialogue_text)

    lines.append("")
    lines.append(
        f"TASK: Propose {n} candidate memories from this "
        "completed scene that the operator might want to carry "
        "forward for future scenes in this Universe. Return JSON "
        "per the output format."
    )
    return "\n".join(lines)


def _call_curator_openai(
    *, system_prompt: str, task_message: str,
) -> tuple[str, int, int]:
    """Single Responses-API call with JSON-object output. Same
    shape as ``next_episode_suggestions._call_openai`` and the
    Q280.9 probe. Wraps all provider errors in
    ``SuggestMemoriesUpstreamError``."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SuggestMemoriesUpstreamError(
            "OPENAI_API_KEY is not configured"
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=_CURATOR_MODEL,
            input=f"{system_prompt}\n\nUser: {task_message}",
            max_output_tokens=_CURATOR_MAX_OUTPUT_TOKENS,
            reasoning={"effort": _CURATOR_REASONING_EFFORT},
            text={"format": {"type": "json_object"}},
        )
    except Exception as exc:
        raise SuggestMemoriesUpstreamError(
            f"LLM provider call failed: {exc}"
        ) from exc

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


# Kind vocabulary accepted from the LLM. Kept in sync with
# ``NarrativeMemoryKind`` via the ``_curator_valid_kinds`` helper
# so if the enum grows we do not silently drop candidates. The
# helper is called lazily to avoid an import-time enum access at
# module load.
def _curator_valid_kinds() -> frozenset[str]:
    from .models import NarrativeMemoryKind

    return frozenset(k.value for k in NarrativeMemoryKind)


def _parse_curator_candidates(raw: str, *, n: int) -> list[dict[str, Any]]:
    """Parse the LLM's JSON output into a list of candidate dicts.

    Tolerant enough to survive minor drift:

    * Requires top-level ``{"candidates": [...]}`` shape.
    * Drops entries without a non-empty ``body``.
    * Drops entries whose ``kind`` is not in
      ``NarrativeMemoryKind`` (so the caller can pass ``kind``
      unchanged to ``promote_from_composition`` later).
    * Accepts ``witnesses`` as list-of-strings; a lone string
      ``"everyone"`` becomes ``[]`` (matches the whole-cast
      convention on the promote path).
    * ``narrative_gravity_note`` is optional; missing → empty string.
    * Trims to at most ``n`` candidates. Never pads.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SuggestMemoriesUpstreamError(
            f"LLM returned invalid JSON: {exc}"
        ) from exc

    raw_list = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(raw_list, list):
        raise SuggestMemoriesUpstreamError(
            "LLM response missing 'candidates' array"
        )

    valid_kinds = _curator_valid_kinds()
    out: list[dict[str, Any]] = []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        body = str(entry.get("body") or "").strip()
        if not body:
            continue
        kind = str(entry.get("kind") or "").strip().lower()
        if kind not in valid_kinds:
            continue

        witnesses_raw = entry.get("witnesses")
        witnesses: list[str] = []
        if isinstance(witnesses_raw, str):
            token = witnesses_raw.strip().lower()
            if token and token != "everyone":
                witnesses = [witnesses_raw.strip()]
        elif isinstance(witnesses_raw, list):
            for w in witnesses_raw:
                if not isinstance(w, str):
                    continue
                w_clean = w.strip()
                if not w_clean or w_clean.lower() == "everyone":
                    continue
                witnesses.append(w_clean)

        note = str(entry.get("narrative_gravity_note") or "").strip()

        out.append({
            "body": body,
            "kind": kind,
            "witnesses": witnesses,
            "narrative_gravity_note": note,
        })
        if len(out) >= n:
            break
    return out


def _curator_cache_key(
    snap: _CuratorSubstrateSnapshot, *, n: int,
) -> str:
    """Cache key sensitive to composition ID + latest same-composition
    memory + requested n. Per SESSION 281 scope-lock: a new
    ``[Remember this]`` on this composition rotates ``latest_source_memory_at``
    which rotates the key.
    """
    payload = (
        f"{snap.composition_id}|{snap.latest_source_memory_at}|{n}"
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"suggested_memories:{snap.composition_id}:{digest}"


def suggest_memories_from_composition(
    composition,
    *,
    n: int = _CURATOR_DEFAULT_N,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Return candidate NarrativeMemory bodies from a completed
    Composition — the SESSION 281 Slice 281.1 curator surface.

    Read-only. Never creates, edits, archives, supersedes, or
    otherwise mutates any ``NarrativeMemory`` row. The operator's
    ``[Remember this]`` click remains the sole promotion path via
    ``promote_from_composition`` in ``apps.memory.views``.

    Parameters:

    * ``composition`` — the ``Composition`` model instance.
    * ``n`` — number of candidates to request. Clamped to
      ``[1, 5]``; out-of-range values silently reset to the
      default (matches the v1 tolerant-query-param behavior).
    * ``use_cache`` — when ``False`` bypasses the Redis cache.

    Returns a dict::

        {
          "candidates": [
            {"body": str, "kind": str, "witnesses": list[str],
             "narrative_gravity_note": str},
            ...
          ],
          "substrate_summary": {
            "prior_episodes_used": int,
            "existing_memories_used": int,
            "cast_count": int,
            "dialogue_chars": int,
          },
          "generated_at": ISO-8601 UTC str,
          "model": str,
          "cache": {"hit": bool, "ttl_seconds": int},
          "tokens_input": int,   # omitted on cache hit
          "tokens_output": int,  # omitted on cache hit
        }

    Empty-substrate short-circuit: if the composition is not
    ``COMPLETED``, or has no realized dialogue in
    ``synthesized_brief``, returns ``candidates=[]`` at the
    normal envelope without calling the LLM.

    Raises ``SuggestMemoriesUpstreamError`` on provider error or
    unparseable response — callers map to HTTP 502.
    """
    from apps.compositions.models import CompositionStatus

    if n < _CURATOR_MIN_N or n > _CURATOR_MAX_N:
        n = _CURATOR_DEFAULT_N

    snap = _snapshot_for_curator(composition)

    substrate_summary = {
        "prior_episodes_used": len(snap.prior_episodes),
        "existing_memories_used": len(snap.existing_memories),
        "cast_count": len(snap.cast),
        "dialogue_chars": len(snap.dialogue_text),
    }

    empty_envelope = {
        "candidates": [],
        "substrate_summary": substrate_summary,
        "generated_at": datetime.now(_dt_timezone.utc).isoformat(),
        "model": _CURATOR_MODEL,
        "cache": {"hit": False, "ttl_seconds": _CURATOR_CACHE_TTL_SECONDS},
    }

    # Short-circuit: non-completed / no realized dialogue / no
    # attached Episode → return empty candidates, no LLM call, no
    # cache write. The SPA (Slice 281.2) will hide the panel in
    # these states rather than render an empty card list.
    if composition.status != CompositionStatus.COMPLETED:
        return empty_envelope
    if not snap.dialogue_text:
        return empty_envelope
    if not snap.episode_id or not snap.universe_id:
        return empty_envelope

    key = _curator_cache_key(snap, n=n)

    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            # Immutable cache-hit response — copy so a hit flag flip
            # here doesn't mutate the stored payload.
            cached_copy = dict(cached)
            cached_copy["cache"] = {
                "hit": True,
                "ttl_seconds": _CURATOR_CACHE_TTL_SECONDS,
            }
            return cached_copy

    task_message = _build_curator_task_message(snap, n=n)
    raw, tokens_in, tokens_out = _call_curator_openai(
        system_prompt=_CURATOR_SYSTEM_PROMPT,
        task_message=task_message,
    )
    candidates = _parse_curator_candidates(raw, n=n)

    payload = {
        "candidates": candidates,
        "substrate_summary": substrate_summary,
        "generated_at": datetime.now(_dt_timezone.utc).isoformat(),
        "model": _CURATOR_MODEL,
        "cache": {"hit": False, "ttl_seconds": _CURATOR_CACHE_TTL_SECONDS},
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
    }

    if use_cache and candidates:
        cache.set(key, payload, timeout=_CURATOR_CACHE_TTL_SECONDS)

    return payload
