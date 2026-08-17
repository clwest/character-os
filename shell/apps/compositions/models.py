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
from apps.spokespeople.models import Teammate


class AssetType(models.TextChoices):
    CLIP = "clip", "Video Clip"
    AUDIO = "audio", "Audio Track"
    IMAGE = "image", "Image"
    TRANSCRIPT = "transcript", "Transcript / Text"
    VOICE = "voice", "Runway Voice Resource"


class AssetRole(models.TextChoices):
    """Asset Library v1 (SESSION 185) — intent-level taxonomy.

    Distinct from ``AssetType`` (medium) and
    ``source_spec.primitive_kind`` (production method).
    Role captures *what the asset is meant for* — talking-head
    foreground vs scene backdrop vs experimental sandbox output.
    Scope: ``docs/design/ASSET_LIBRARY_V1.md`` §Taxonomy.

    Twelve values (BRIDGE_ANSWER added at S2887 side-step C3). New
    roles require a migration + scope discussion (V1 contract rule 14).
    """

    TALKING_HEAD = "talking_head", "Talking Head"
    BACKDROP = "backdrop", "Backdrop"
    COMPOSITE_OUTPUT = "composite_output", "Composite Output"
    POLISH_OUTPUT = "polish_output", "Polish Output"
    REFERENCE_IMAGE = "reference_image", "Reference Image"
    B_ROLL = "b_roll", "B-Roll"
    TRANSCRIPT = "transcript", "Transcript"
    AUDIO_TRACK = "audio_track", "Audio Track"
    VOICEOVER_AUDIO = "voiceover_audio", "Voiceover Audio"
    RAW_UPLOAD = "raw_upload", "Raw Upload"
    EXPERIMENT = "experiment", "Experiment / Sandbox"
    # S2887 C3 — durable persistence for engine-bridge answers.
    # consult_engine / query_spider_data / agent_consult each create
    # an Asset(BRIDGE_ANSWER) on success, so the answer survives past
    # session end and is discoverable via the workspace asset library.
    # See engine-bridge scope note in `shell/apps/realtime/engine_bridge.py`.
    BRIDGE_ANSWER = "bridge_answer", "Engine Bridge Answer"


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


class VerificationStatus(models.TextChoices):
    """K6.4 v1.2 — outcome of the post-synthesis claim verifier
    for one render. Captured on ``Composition.verification_status``
    and ``ConversationMessage.verification_status``.

    The four states distinguish *what the verifier actually did*
    so an empty ``verification_warnings`` list isn't ambiguous
    between "verified clean" and "verifier didn't run." Closes
    the SESSION 161 calibration gap (TRUST_CALIBRATION entry
    "Near-miss: bypass case looks identical to clean render").

    State semantics:

    * ``VERIFIED`` — synthesis ran AND verifier ran in
      strict/warn mode. The render is grounded by the
      verifier's contract. ``verification_warnings`` may be
      empty (clean) OR populated (Warn mode flags).
    * ``TRUSTED_PASSTHROUGH`` — synthesis path degraded (no
      chunks, no OpenAI key, retrieval failure, mock mode) so
      no LLM produced text. The operator's prompt flowed
      through verbatim; trusted by definition.
    * ``SKIPPED`` — verifier mode was ``"off"``. The LLM ran
      but no verification occurred; operator may have invented
      content.
    * ``REJECTED`` — strict mode caught unsupported claims and
      blocked the render. ``rejected_synthesis`` carries what
      the LLM produced; ``status`` on the parent row will
      typically be ``FAILED`` for compositions.
    """
    VERIFIED = "verified", "Verified"
    TRUSTED_PASSTHROUGH = "trusted_passthrough", "Trusted Passthrough"
    SKIPPED = "skipped", "Skipped"
    REJECTED = "rejected", "Rejected"


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

    # Asset Library v1 (SESSION 185, A0) — intent taxonomy.
    # Stamped at primitive-emit time by A2 (rule 15). Existing
    # rows default to ``RAW_UPLOAD`` until the A1 backfill
    # management command maps them by ``source_spec.primitive_kind``.
    # Indexed via the Meta.indexes entry below for the workspace+role
    # filter on ``GET /api/workspace/assets/`` (A4).
    role = models.CharField(
        max_length=24,
        choices=AssetRole.choices,
        default=AssetRole.RAW_UPLOAD,
        help_text=(
            "Intent-level role (talking head, backdrop, composite output, "
            "polish output, reference image, b-roll, transcript, audio "
            "track, voiceover audio, raw upload, experiment). Distinct "
            "from asset_type (medium) and source_spec.primitive_kind "
            "(production method)."
        ),
    )

    # W11.6.5.1 (SESSION 174) — operator-facing label. Pickers
    # (asset_picker dropdowns on recipe forms, image library
    # grid, detail modal) prefer this over the filename / data-
    # URI fallback. Auto-populated from the subject for images
    # created via W11.6.2 ImageViewSet; empty default for
    # existing pre-W11.6.5.1 rows + non-image surfaces that
    # don't have a natural human label yet (those can be
    # backfilled later as separate slices).
    title = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text=(
            "Operator-facing label surfaced in pickers. "
            "Auto-populated from the image subject for images "
            "generated via /api/images/; clips + audio "
            "currently leave empty + fall back to filename "
            "labels in the SPA."
        ),
    )

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

    # W11.6.1 (Media Generation V1) — image-specific provenance.
    # All fields are optional; populated only when the asset is an
    # ``image`` produced via ``POST /api/images/``. Existing
    # ``clip`` / ``audio`` / ``transcript`` / ``voice`` rows leave
    # them empty. Scope: ``docs/design/MEDIA_GENERATION_V1.md``
    # §"Surface inventory".
    purpose = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=(
            "Image purpose: avatar / scene / broll / product / ad. "
            "Empty for non-image assets."
        ),
    )
    model = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text=(
            "Stability model name (sd3-large / ultra / core / etc.) "
            "for image assets. Empty for non-image assets."
        ),
    )
    style_preset = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text=(
            "Selected style preset slug from "
            "``media-engine/app/services/style_library.py``. Empty "
            "when no preset was applied (or for non-image assets)."
        ),
    )
    prompt = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Composed prompt actually sent to Stability. Empty for "
            "non-image assets. Preserved verbatim for regenerate / "
            "library detail views."
        ),
    )
    # W11.6.4 — original operator subject (pre-composition). The
    # composed ``prompt`` above is what Stability saw; ``subject``
    # is what the operator typed. We keep both so the SPA's
    # Regenerate CTA can re-fire with the original subject (sending
    # the composed prompt as a new subject would double-apply
    # the purpose framing and template prefix).
    subject = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Operator's original subject text, before prompt "
            "composition. Empty for non-image assets and for "
            "pre-W11.6.4 image rows."
        ),
    )
    negative_prompt = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Composed negative prompt sent to Stability. Empty for "
            "non-image assets or when the default for the chosen "
            "purpose was used."
        ),
    )
    aspect_ratio = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text=(
            "Output ratio (1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 21:9). "
            "Empty for non-image assets."
        ),
    )
    # Optional linkage — set when the image was generated *for* a
    # specific spokesperson (e.g. b-roll for one of their videos).
    # SET_NULL because the image survives independently; deleting
    # a spokesperson should not nuke library assets attributed to
    # them.
    spokesperson = models.ForeignKey(
        "spokespeople.Teammate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_assets",
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
            # W11.6.1 — filterable on purpose for the library view.
            models.Index(fields=["workspace", "purpose"]),
            # Asset Library v1 (SESSION 185, A0) — workspace+role
            # is the primary filter for GET /api/workspace/assets/.
            models.Index(fields=["workspace", "role"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.asset_type}:{self.id} ({self.workspace.name})"


class Composition(models.Model):
    """An ordered sequence of step primitives that combine
    Assets into a final deliverable Asset.

    Compositions carry **both** workspace and spokesperson
    anchors (contract rule 2). ``workspace`` is the load-
    bearing anchor and stays required + CASCADE. ``spokesperson``
    is nullable + SET_NULL as of SESSION 251 to preserve historical
    render history when a customer deletes a teammate; before that
    it was PROTECT and would 500 any teammate delete. Workspace
    isolation is preserved via the workspace FK on the row itself.

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
        Teammate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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

    # K6.4 v1.2 — closes the SESSION 161 bypass-case audit gap.
    # See ``VerificationStatus`` for the four-state semantics.
    # Empty default keeps pre-v1.2 rows distinguishable from
    # post-v1.2 explicit statuses.
    verification_status = models.CharField(
        max_length=24,
        choices=VerificationStatus.choices,
        blank=True,
        default="",
    )

    # K6.6 (SESSION 168) — what K6 actually synthesized for a
    # *successful* render. ``rejected_synthesis`` captures the
    # strict-mode-rejected case; this field captures the
    # rendered-to-Runway case. Together they give the operator
    # a complete record of what the model said, regardless of
    # whether the verifier passed or blocked.
    #
    # Populated only when K6 actually synthesized (real-mode +
    # OpenAI key + chunks). Empty for:
    # * Force-mock renders (no LLM call)
    # * Degraded paths (no chunks / no key / retrieval failure)
    # * Operator-typed scripts (use_knowledge=False)
    # * Pre-K6.6 compositions
    #
    # Closes the audit gap surfaced SESSION 168: operator
    # feedback on rendered video quality had no place to land
    # because the synthesized text wasn't persisted on
    # successful renders.
    synthesized_brief = models.TextField(blank=True, default="")

    # SESSION 253 — which version of ``character_os.writing_contract``
    # shaped this composition's synthesized script. 0 = pre-contract
    # (rows from before SESSION 253 or any code path that never
    # went through K6 synthesis). Positive integers correspond to
    # ``WRITING_CONTRACT_VERSION`` at the time of synthesis so
    # future audits can trace which rule set produced a given
    # script.
    writing_contract_version = models.PositiveSmallIntegerField(default=0)

    # ------------------------------------------------------------------
    # SESSION 262 — Composition observability v1.
    # Scope-lock: ``docs/design/COMPOSITION_OBSERVABILITY_V1.md``.
    # Nine additive fields that make Composition-level synthesis
    # provenance reconstructible from DB state alone. Immutability
    # of these fields once written is enforced in ``save()`` below
    # via a ``from_db()`` snapshot; the field types themselves are
    # additive-nullable-or-empty-default so legacy rows behave as
    # today. ``EPISODE_SCHEMA_V1`` will add a Universe-scoped story
    # layer that owns ``operator_topic`` at the narrative level;
    # this per-attempt copy remains authoritative for the render
    # attempt in every case
    # (``EPISODE_LIFECYCLE_V1.md §Where-operator_topic-lives``).
    operator_topic = models.TextField(blank=True, default="")
    target_duration_seconds = models.PositiveSmallIntegerField(
        null=True, blank=True,
    )
    synthesis_attempt_count = models.PositiveSmallIntegerField(default=0)
    first_pass_synthesis = models.TextField(blank=True, default="")
    corrective_hint = models.TextField(blank=True, default="")
    corrective_pass_synthesis = models.TextField(blank=True, default="")
    validation_failure_reason = models.TextField(blank=True, default="")
    synthesis_predicted_seconds = models.FloatField(null=True, blank=True)
    render_dispatched_at = models.DateTimeField(null=True, blank=True)

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

    # SESSION 262 — observability provenance fields that must not be
    # silently rewritten after their first non-default persistence.
    # Enforced by ``save()``/``from_db()`` below against a snapshot of
    # the DB values at load time; legitimate lifecycle writes
    # (``status`` / ``error_message`` / ``final_asset`` / ``cost_*`` /
    # ``verification_*`` / ``synthesized_brief`` / ``rejected_synthesis`` /
    # ``knowledge_chunk_ids`` / ``writing_contract_version``) are NOT
    # in this set and remain freely mutable per their existing
    # lifecycles. See ``docs/design/COMPOSITION_OBSERVABILITY_V1.md``
    # §Q5.
    _IMMUTABLE_OBSERVABILITY_FIELDS = (
        "operator_topic",
        "target_duration_seconds",
        "synthesis_attempt_count",
        "first_pass_synthesis",
        "corrective_hint",
        "corrective_pass_synthesis",
        "validation_failure_reason",
        "synthesis_predicted_seconds",
        "render_dispatched_at",
    )

    @classmethod
    def from_db(cls, db, field_names, values):
        """Snapshot the persisted values of the immutable observability
        fields so ``save()`` can detect silent overwrites. New rows
        (never loaded from the DB) have no snapshot and may set any
        value at first write.

        Reads values directly from the ``(field_names, values)`` tuple
        Django passes in — avoids triggering a deferred-field refresh
        (which would recurse back through ``from_db``) when a caller
        loaded the row with ``.only(...)`` / ``.defer(...)`` /
        ``.values_list(...)`` and one of the observability fields was
        deferred. Deferred fields simply do not appear in the snapshot;
        if the caller later touches one, the ORM's normal fetch path
        loads it fresh and ``save()`` then compares against a snapshot
        that never had it — no violation possible.
        """
        instance = super().from_db(db, field_names, values)
        loaded_by_name = dict(zip(field_names, values))
        instance._loaded_observability = {
            f: loaded_by_name[f]
            for f in cls._IMMUTABLE_OBSERVABILITY_FIELDS
            if f in loaded_by_name
        }
        return instance

    @staticmethod
    def _observability_value_is_populated(field_name: str, value) -> bool:
        """A field counts as "already written" (i.e. immutable from
        here on) when its persisted value is anything other than the
        additive-default the schema landed with. Text fields default
        ``""``; ``synthesis_attempt_count`` defaults ``0``; the other
        int / float / datetime fields default ``None``. Keeping this
        check aligned with the migration defaults means the very first
        real write is always accepted; subsequent divergence is
        rejected."""
        if value is None:
            return False
        if isinstance(value, str) and value == "":
            return False
        if field_name == "synthesis_attempt_count" and value == 0:
            return False
        return True

    def save(self, *args, **kwargs):
        """SESSION 262 — enforce observability-field immutability.

        The check fires only when:
          * this instance was loaded from the DB (``from_db`` populated
            ``_loaded_observability``), AND
          * either ``update_fields`` was NOT passed (full save touches
            every field) OR the immutable field IS in ``update_fields``,
            AND
          * the previously-persisted value was populated (not the
            schema default), AND
          * the current in-memory value differs from the persisted one.

        No-op saves (same value) never raise. Legitimate lifecycle
        writes that use ``save(update_fields=[...])`` and exclude the
        observability fields never trigger the check. First writes on
        new (unsaved) rows always succeed.
        """
        loaded = getattr(self, "_loaded_observability", None)
        if loaded:
            update_fields = kwargs.get("update_fields")
            for fname in self._IMMUTABLE_OBSERVABILITY_FIELDS:
                # Only check fields whose value we actually snapshotted
                # at load time. Deferred fields (loaded via
                # ``.only()`` / ``.defer()``) intentionally sit outside
                # the check because we cannot know their persisted value
                # without an ORM fetch that would compete with the
                # caller's chosen loading pattern.
                if fname not in loaded:
                    continue
                if update_fields is not None and fname not in update_fields:
                    continue
                prev = loaded[fname]
                current = getattr(self, fname, None)
                if (
                    self._observability_value_is_populated(fname, prev)
                    and prev != current
                ):
                    raise ValidationError(
                        f"Composition.{fname} is immutable once populated "
                        f"(SESSION 262 observability provenance): "
                        f"persisted={prev!r} attempted={current!r}"
                    )
        super().save(*args, **kwargs)
        # Refresh the snapshot to the newly-persisted state so a
        # second save on the same instance sees the just-written
        # values as the new baseline. Prevents the "same-value save"
        # after a fresh write from being rejected on a subsequent
        # change attempt. Uses ``self.__dict__.get`` to avoid
        # triggering deferred-field refresh on any field the caller
        # didn't touch.
        for f in self._IMMUTABLE_OBSERVABILITY_FIELDS:
            if f in self.__dict__:
                if loaded is None:
                    self._loaded_observability = {}
                    loaded = self._loaded_observability
                loaded[f] = self.__dict__[f]

    def mark_render_dispatched(self) -> None:
        """SESSION 262 — record the first-provider-dispatch moment.

        Called by render primitives (``avatar_speech``, ``visual_clip``)
        right before their media-engine client call. Idempotent: the
        second and subsequent calls on the same composition are no-ops
        because ``render_dispatched_at`` is immutable once populated.

        Uses ``save(update_fields=[...])`` so the ``save()`` override's
        immutability check permits this specific write (the field is
        currently NULL) and skips checking any other observability
        fields. Also refreshes the in-memory instance so the caller
        sees the persisted timestamp.
        """
        if self.render_dispatched_at is not None:
            return
        from django.utils import timezone as _tz
        self.render_dispatched_at = _tz.now()
        self.save(update_fields=["render_dispatched_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.name} ({self.workspace.name})"

    def clean(self) -> None:
        """Validate that spokesperson belongs to the same
        workspace as the composition. The required workspace
        FK does not prevent an operator from constructing a
        composition whose spokesperson is in a different
        workspace — ``clean()`` does. Post-SESSION 251
        ``spokesperson`` is nullable (SET_NULL on teammate
        delete); the ``spokesperson_id`` gate keeps this check
        safe against historical rows whose teammate has since
        been deleted."""
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
