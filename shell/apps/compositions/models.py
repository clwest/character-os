"""Composition-layer models.

SESSION 142 / V1 — the data backbone of the video composition
arc. Locked in ``docs/design/VIDEO_COMPOSITION_V1.md`` §"Data
model".

Scope rules carried forward from the scope lock:

* Every ``Asset`` has a required ``workspace`` FK — it is the
  load-bearing anchor for the privacy contract
  (contract rule 1).
* Every ``Composition`` carries both ``workspace`` and
  ``spokesperson`` FKs (contract rule 2). A composition
  without a workspace is unrenderable by construction.
* ``CompositionStep`` inputs may reference Assets by id; any
  cross-workspace reference is rejected structurally at
  save time + via signal (contract rule 3, defense in
  depth — mirrors the ``KnowledgeDocument`` cross-workspace
  pattern).
* Linear ordering only in v1 (contract rule 5) — steps have
  a unique ``(composition, position)`` constraint; DAG /
  parallel branches are explicitly deferred.

V1 (this slice) ships **schema only** — the runtime that
walks the steps + fires media-engine primitives is V2.
Existing ``Video`` rows are untouched; V5 introduces the
backwards-compat shim.
"""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson


class AssetType(models.TextChoices):
    CLIP = "clip", "Video Clip"
    AUDIO = "audio", "Audio Track"
    IMAGE = "image", "Image"
    TRANSCRIPT = "transcript", "Transcript / Text"
    VOICE = "voice", "Runway Voice Resource"


class CompositionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLANNING = "planning", "Planning"
    RUNNING = "running", "Running"
    PARTIAL = "partial", "Partial (some steps failed)"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class StepStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class Asset(models.Model):
    """A generated media artifact — clip, audio, image,
    transcript, or Runway voice resource.

    Assets are workspace-scoped (contract rule 1) and may be
    attached to a Composition or stand free as a "library
    asset" reusable across compositions (``composition`` FK
    is nullable).

    ``source_spec`` is a JSON provenance record describing
    how the asset was produced — the step primitive name +
    input asset ids + params — so re-running a deterministic
    step is possible and so admins can audit how a deliverable
    came to be.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The load-bearing anchor — required, never null.
    # Same contract as ``KnowledgeDocument.workspace``.
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="assets",
    )

    asset_type = models.CharField(max_length=20, choices=AssetType.choices)

    # Where the bytes live. For clips/audio/images: local file
    # path under ``media-engine/data/_assets/`` OR an external
    # URL. For voice: the Runway voice_id (no local file).
    # For transcript: empty (content lives in inline_content).
    file_path = models.TextField(blank=True, default="")

    # Inline content for small assets (transcripts, captions).
    # Empty for binary assets.
    inline_content = models.TextField(blank=True, default="")

    # How this asset was made — JSON record. Enables provenance
    # + idempotent re-runs. Shape example:
    #   {"primitive": "generate_avatar_speech",
    #    "inputs": [{"slot": "script", "asset_id": "..."}],
    #    "params": {"avatar_id": "...", "duration": 5}}
    source_spec = models.JSONField(default=dict, blank=True)

    # Type-specific metadata. All nullable — only populated
    # when meaningful for the asset_type.
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=80, blank=True, default="")
    size_bytes = models.PositiveIntegerField(null=True, blank=True)

    # Cost provenance — what producing this asset cost in
    # micros (1 USD = 1_000_000 micros). Same unit as
    # ``KnowledgeChunk.embedding_cost_micros``.
    cost_micros = models.PositiveIntegerField(default=0)

    # Origin composition. Null = "library asset" not tied to
    # one render. CASCADE would force every composition delete
    # to wipe its assets even if reused; SET_NULL preserves
    # the asset for re-use even if its origin composition
    # disappears.
    composition = models.ForeignKey(
        "compositions.Composition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produced_assets",
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "asset_type"]),
            models.Index(fields=["composition"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.asset_type}:{self.id} ({self.workspace.name})"


class Composition(models.Model):
    """An ordered sequence of step primitives that combine
    Assets into a final deliverable Asset.

    Compositions carry **both** workspace and spokesperson
    anchors (contract rule 2). The spokesperson FK is
    ``PROTECT`` because deleting a spokesperson while their
    compositions exist would orphan the render history;
    operators delete compositions first, then the
    spokesperson.

    ``final_asset`` is null until the composition's last
    step completes. ``knowledge_chunk_ids`` carries forward
    the K6 citation logging — every composition that runs a
    knowledge-informed primitive (``generate_avatar_speech``
    via ``build_render_brief``) records which chunks fed
    the render.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Required anchors — privacy + provenance.
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="compositions",
    )
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.PROTECT,
        related_name="compositions",
    )

    # Operator-visible identity.
    name = models.CharField(max_length=200)
    template_kind = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text=(
            "Which starter composition this was forked from. "
            "Empty for custom compositions. Examples: "
            "``talking_head``, ``talking_head_with_backdrop``, "
            "``long_form_ad``."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=CompositionStatus.choices,
        default=CompositionStatus.DRAFT,
    )

    # The deliverable. Null until the final step lands. Always
    # an Asset of type ``clip`` — a composition's deliverable
    # is a video.
    final_asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # K6 carry-over — citation logging for renders informed
    # by knowledge chunks. ``[]`` when no chunks fed the
    # composition (empty knowledge, retrieval failure, etc.).
    knowledge_chunk_ids = models.JSONField(default=list, blank=True)

    # K6.4 — post-synthesis claim verifier output. Each entry
    # is a dict ``{"claim": str, "kind": str, "position": int}``
    # describing a named entity that appeared in the synthesized
    # script but had no substring match in the retrieved chunks
    # (or the allow-list extras: spokesperson name, business
    # brief, operator prompt, KNOWN_PLATFORM_TERMS).
    # ``[]`` on a clean render OR when ``K6_CLAIM_VERIFIER_MODE
    # = "off"``. Strict mode prevents the composition from
    # leaving DRAFT in the first place, so a strict-failed run
    # leaves this populated alongside ``status=FAILED``.
    verification_warnings = models.JSONField(default=list, blank=True)

    # K6.4.1 — the synthesized script that the verifier rejected
    # in Strict mode. Populated only on strict-mode rejections so
    # operators can inspect *what the LLM said* alongside the
    # ``verification_warnings`` list. Empty on clean renders,
    # Warn-mode flagged renders (where the brief flows through
    # to Runway), and Off-mode renders.
    rejected_synthesis = models.TextField(blank=True, default="")

    # Cost transparency (contract rule 7). Estimate is computed
    # before render fires; actual is summed from per-step
    # ``cost_actual_micros`` after execution.
    cost_estimate_micros = models.PositiveIntegerField(default=0)
    cost_actual_micros = models.PositiveIntegerField(default=0)

    # Mock-mode per contract rule 9 — composition-level only,
    # not mixed per-step. Captured at composition create time
    # from the env flags so the entire run is internally
    # consistent.
    mock_mode = models.BooleanField(default=False)

    error_message = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_compositions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["spokesperson", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.workspace.name})"

    def clean(self) -> None:
        """Validate that spokesperson belongs to the same
        workspace as the composition. The PROTECT on
        spokesperson + the required workspace FK don't
        prevent an operator from constructing a composition
        whose spokesperson is in a different workspace —
        ``clean()`` does."""
        super().clean()
        if self.spokesperson_id and self.workspace_id:
            if self.spokesperson.workspace_id != self.workspace_id:
                raise ValidationError(
                    f"Composition spokesperson {self.spokesperson.name!r} "
                    f"belongs to workspace {self.spokesperson.workspace_id} "
                    f"but the composition is in workspace {self.workspace_id}."
                )

        # Final asset, if set, must live in the same workspace.
        if self.final_asset_id and self.workspace_id:
            if self.final_asset.workspace_id != self.workspace_id:
                raise ValidationError(
                    "Composition final_asset must be in the same "
                    "workspace as the composition."
                )


class CompositionStep(models.Model):
    """One step in a Composition's ordered sequence.

    Each step invokes one step primitive (named in the
    ``primitive`` field — see ``VIDEO_COMPOSITION_V1.md``
    §"Step primitives" for the v1 set of 16 primitive names).
    The runtime that V2 introduces walks steps in
    ``position`` order, fires the matching media-engine
    endpoint, and persists the output Asset reference back
    onto the step.

    ``inputs`` and ``params`` are JSON for runtime
    flexibility — each primitive defines its own input slot
    + param shape. Schema validation lives in
    ``apps/compositions/primitives/<name>.py`` (introduced
    per-primitive starting V3); the model itself accepts
    any JSON to keep V1 strictly a schema slice.

    ``inputs`` shape:
        [
            {"slot": "script", "asset_id": "<uuid>"},          # workspace asset
            {"slot": "backdrop", "from_step_position": 0},     # earlier step's output
        ]
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    composition = models.ForeignKey(
        Composition,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    # 0-indexed position in the composition's step list.
    # Unique within a composition (contract rule 5 — linear
    # ordering only).
    position = models.PositiveIntegerField()

    # Which primitive this step invokes. Free-form string in
    # v1 — the registry of valid primitives lives in
    # ``apps/compositions/primitives/__init__.py`` (V3+).
    primitive = models.CharField(max_length=80)

    # Inputs: list of {slot, asset_id|from_step_position}.
    # Cross-workspace asset references are rejected by the
    # signal in ``apps.compositions.signals``.
    inputs = models.JSONField(default=list, blank=True)

    # Params: primitive-specific JSON. Schema enforced
    # per-primitive starting V3.
    params = models.JSONField(default=dict, blank=True)

    # Output of this step — populated by the executor when
    # the step succeeds. Null until then.
    output_asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produced_by_step",
    )

    status = models.CharField(
        max_length=20,
        choices=StepStatus.choices,
        default=StepStatus.PENDING,
    )

    # Telemetry — contract rule 7 (cost) + general execution
    # diagnostics.
    cost_estimate_micros = models.PositiveIntegerField(default=0)
    cost_actual_micros = models.PositiveIntegerField(default=0)
    elapsed_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Media-engine task id, when the primitive is async (e.g.
    # ``generate_avatar_speech`` → /v1/avatar_videos → poll).
    # Empty for synchronous primitives (ffmpeg local).
    media_engine_task_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["composition", "position"],
                name="composition_step_unique_position",
            ),
        ]
        indexes = [
            models.Index(fields=["composition", "position"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["composition", "position"]

    def __str__(self) -> str:
        return f"{self.composition.name} #{self.position}: {self.primitive}"

    def referenced_asset_ids(self) -> list[uuid.UUID]:
        """Pull every ``asset_id`` out of ``inputs``. Used by
        the cross-workspace validator + cost estimator."""
        ids: list[uuid.UUID] = []
        if not isinstance(self.inputs, list):
            return ids
        for entry in self.inputs:
            if not isinstance(entry, dict):
                continue
            asset_id = entry.get("asset_id")
            if asset_id:
                try:
                    ids.append(uuid.UUID(str(asset_id)))
                except (ValueError, TypeError):
                    # Malformed id — let the signal raise on
                    # save with a clearer error than what
                    # uuid.UUID would surface.
                    continue
        return ids

    def clean(self) -> None:
        """Reject cross-workspace asset references. The signal
        in ``apps.compositions.signals`` provides the same
        guarantee on the DB-save path (defense in depth —
        ``clean()`` covers form flows + explicit
        ``full_clean()`` calls; the signal covers raw
        ``.save()`` calls).
        """
        super().clean()
        if not self.composition_id:
            return
        # Re-fetch the composition here rather than via
        # ``self.composition`` so this works for unsaved
        # ``CompositionStep`` instances during a form clean.
        composition_workspace_id = (
            Composition.objects.filter(pk=self.composition_id)
            .values_list("workspace_id", flat=True)
            .first()
        )
        if not composition_workspace_id:
            return

        asset_ids = self.referenced_asset_ids()
        if not asset_ids:
            return

        bad = list(
            Asset.objects.filter(pk__in=asset_ids)
            .exclude(workspace_id=composition_workspace_id)
            .values_list("pk", flat=True)
        )
        if bad:
            raise ValidationError(
                f"CompositionStep cannot reference assets from another "
                f"workspace. Composition workspace: "
                f"{composition_workspace_id}. Bad asset ids: {bad}"
            )
