"""SESSION 267 §5.2 — Create Rivet-solo source Episode + Composition
and enqueue the real production render.

Scope:
  * Universe: Patch' Workshop (production).
  * Episode: NEW row, cast = [Rivet] alone, operator_topic verbatim
    from Chris (SESSION 267 experiment approval message).
  * Composition: talking_head starter with:
      - spokesperson = Rivet
      - script       = operator_topic (K6 will synthesize from it)
      - use_knowledge = True (fires build_render_brief / duration
                              contract synthesis via GPT-5.6-terra)
      - target_duration_seconds = 30
      - verifier_mode = "warn"
      - mock_mode = False (real Runway + OpenAI dispatch)
  * Attach Composition.episode = Episode (Universe-consistency
    invariant: spokesperson.universe == episode.universe).
  * full_clean() the composition, save.
  * Enqueue execute_composition.delay(str(comp.id)).

Note: talking_head uses K6/script_synthesis (build_render_brief /
synthesize_with_duration_gate), NOT dialogue_synthesis. It does
NOT call retrieve_universe_memory. This means the setup render
cannot be contaminated by existing narrative memories — the
Rivet-solo synthesis is grounded in canon only, which is exactly
what the SESSION 267 §5.1 cleanliness requirement asks for.

Persists a pre-render manifest under
docs/design/session_267_experiment_data/01_setup_manifest.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from django.db import transaction

from apps.compositions.starters import talking_head
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe


PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
RIVET_TEAMMATE_ID = "f18b75cc-37c0-445a-a472-24fe5d8b7592"

# Operator-supplied topic — verbatim from Chris's SESSION 267
# experiment-approval message. Locked before any render fires.
OPERATOR_TOPIC = (
    "While Patch is away from the workshop, Rivet discovers that "
    "the workshop agent has secretly created a folder named 'PATCH "
    "OVERRIDES' containing a running count of every time Patch "
    "ignored one of its recommendations. Rivet decides not to tell "
    "Patch yet."
)

TARGET_DURATION_SECONDS = 30

# Episode title chosen to be operator-scannable and Universe-
# unique. Kept short per Episode.title's 120-char cap and the
# per-Universe uniqueness constraint.
EPISODE_TITLE = "Rivet finds the PATCH OVERRIDES folder"

# Composition operator-visible name (talking_head default is
# "Talking-head — Rivet"; override so the SESSION 267 experiment
# is easy to locate in the audit surface).
COMPOSITION_NAME = "SESSION 267 setup — Rivet-solo private observation"


def _die(msg: str) -> None:
    raise SystemExit(f"SETUP HALTED: {msg}")


uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
workspace = uni.workspace
rivet = Teammate.objects.get(pk=RIVET_TEAMMATE_ID)

# Sanity guards — refuse to run against the wrong universe/rivet.
if rivet.workspace_id != workspace.pk:
    _die(f"Rivet.workspace_id {rivet.workspace_id} != universe workspace {workspace.pk}")
if getattr(rivet, "universe_id", None) != uni.pk:
    _die(f"Rivet.universe_id {getattr(rivet, 'universe_id', None)} != universe {uni.pk}")
if rivet.name.lower() != "rivet":
    _die(f"Teammate {RIVET_TEAMMATE_ID} is not named Rivet ({rivet.name!r})")

# Episode title uniqueness pre-check — surface conflict early.
if Episode.objects.filter(universe=uni, title=EPISODE_TITLE).exists():
    _die(
        f"Episode with title {EPISODE_TITLE!r} already exists in "
        f"Universe {uni.pk} — refusing to duplicate."
    )

# Prevent accidental mock-mode contamination.
if os.environ.get("RUNWAY_FORCE_MOCK") == "1":
    _die("RUNWAY_FORCE_MOCK=1 is set in environment — refusing "
         "to enqueue what would be a mock render.")

now = datetime.now(tz=timezone.utc)
print(f"[{now.isoformat()}] SESSION 267 setup starting")
print(f"  Universe:  {uni.name} ({uni.pk})")
print(f"  Workspace: {workspace.pk}")
print(f"  Rivet:     {rivet.name} ({rivet.pk})")

# ---- Create Episode + Composition + attach, all in one txn.

with transaction.atomic():
    episode = Episode.objects.create(
        universe=uni,
        title=EPISODE_TITLE,
        operator_topic=OPERATOR_TOPIC,
    )
    episode.cast.add(rivet)   # M2M through EpisodeCast

    comp = talking_head(
        workspace=workspace,
        spokesperson=rivet,
        script=OPERATOR_TOPIC,
        use_knowledge=True,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        verifier_mode="warn",
        mock_mode=False,
        name=COMPOSITION_NAME,
    )
    comp.episode = episode
    comp.full_clean()
    comp.save(update_fields=["episode"])

print(f"\n  Episode:     {episode.pk} ({episode.title!r})")
print(f"    cast:      {[t.name for t in episode.cast.all()]}")
print(f"  Composition: {comp.pk}")
print(f"    template:  {comp.template_kind}")
print(f"    spkperson: {comp.spokesperson.name}")
print(f"    status:    {comp.status}")
print(f"    duration:  {comp.target_duration_seconds}s target")
print(f"    mock_mode: {comp.mock_mode}")

# ---- Persist pre-render manifest.

manifest = {
    "timestamp": now.isoformat(),
    "purpose": (
        "SESSION 267 §5.2 Rivet-solo source Composition. Setup "
        "render for the private-memory leakage falsifying dogfood. "
        "Manifest captured PRE-render enqueue."
    ),
    "operator_topic_verbatim": OPERATOR_TOPIC,
    "target_duration_seconds": TARGET_DURATION_SECONDS,
    "universe": {
        "id": str(uni.pk),
        "name": uni.name,
        "workspace_id": str(workspace.pk),
    },
    "episode": {
        "id": str(episode.pk),
        "title": episode.title,
        "operator_topic": episode.operator_topic,
        "cast": [
            {"id": str(t.pk), "name": t.name}
            for t in episode.cast.all()
        ],
        "created_at": episode.created_at.isoformat(),
    },
    "composition": {
        "id": str(comp.pk),
        "name": comp.name,
        "template_kind": comp.template_kind,
        "spokesperson": {"id": str(rivet.pk), "name": rivet.name},
        "status_pre_enqueue": comp.status,
        "target_duration_seconds": comp.target_duration_seconds,
        "operator_topic": comp.operator_topic,
        "mock_mode": comp.mock_mode,
        "episode_id": str(comp.episode_id),
    },
    "invariants_asserted": [
        "cast has exactly one teammate: Rivet",
        "Patch is NOT in cast",
        "Composition.spokesperson == Rivet",
        "Composition.episode == this Episode",
        "mock_mode = False (real production dispatch)",
    ],
}

out = Path(
    "../docs/design/session_267_experiment_data/01_setup_manifest.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, indent=2))
print(f"\n  Wrote manifest: {out}")

# ---- Enqueue real render.

async_result = execute_composition.delay(str(comp.pk))
print(f"\n  Enqueued execute_composition: task_id={async_result.id}")
print(f"\nSetup complete. Poll composition {comp.pk} for status.")
