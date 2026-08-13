"""Canonical Identity substrate — SESSION 241 / §19 Step 2.

Source of truth: ``docs/design/visual/portrait_qualification/CANONICAL_IDENTITY_CONTRACT_V1.md``
(``ratified`` as of 2026-08-06). Every model in this module maps to
a ratified substrate concept from §15 with the §17 amendments folded
in. This module intentionally contains **no service behavior** —
authoring, approval, supersedes, and validation live in
``apps.identity.services`` (the authoritative write path per
§17.3.a), and schema resolution lives in
``apps.identity.schema_loader``.

Boundary discipline held here:

* The substrate is **provider-neutral** (§17.4.a). No Runway,
  Stability, ElevenLabs, or SDK-specific identifiers appear on any
  identity, version, reference, or bundle field. Provider provenance
  lives on ``GenerationRecord`` only.
* Human and non-human branches share this substrate (§17.2.a).
  Branch-specific structure is validated by declarative schemas
  loaded at write time — never encoded into columns.
* The bundle's domain contract exposes canonical approved
  representations (``approved_voice``, ``approved_realtime``,
  approved reference set via ``IdentityReference``). Callers ask
  for approved representations; provider details stay underneath.

The illustrative ``NormalizationProfile`` (per-identity normalization
overrides) from §15.6 is **deliberately omitted** from Step 2 —
§15.6 defers the table and round one may not need it at all.
Adding it later requires a contract amendment per §19.5.

SESSION 242 / §19 Step 3 additions (legacy backfill provenance):

* ``ImportProvenance`` — OneToOne on ``CharacterIdentityVersion``,
  landed to record the ratified ``legacy_imported`` provenance
  vocabulary (§17.10.a Amendment 2). Presence of a row = the
  version came from Step 3's one-time historical backfill.
* ``GenerationProvider.LEGACY_IMPORTED`` — provenance-only value.
  Marks synthetic ``GenerationRecord`` rows created by the legacy
  backfill. **Never treated as a qualified rendering provider,
  benchmark provider, or evidence that satisfies provider
  qualification.**
* ``CharacterIdentity`` partial unique on ``teammate`` (where
  non-null) — enforces the "one canonical identity per real
  teammate" invariant that Step 3's idempotency contract requires;
  nullable bootstrap-fixture rows continue to be allowed.
* ``CharacterIdentityVersion.spec_schema_version = 0`` — the
  ``legacy_unvalidated`` sentinel. Documented in the field's
  help_text; ``services.create_draft_version`` refuses any value
  below ``MIN_CANONICAL_SPEC_SCHEMA_VERSION``; the Step 3 import
  service is the only path that may write ``0``.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.accounts.models import Workspace
from apps.compositions.models import Asset
from apps.spokespeople.models import Teammate


# ---------------------------------------------------------------------
# SESSION 242 / §19 Step 3 — legacy backfill sentinels.
# ---------------------------------------------------------------------

#: The ``spec_schema_version`` value that marks a
#: ``CharacterIdentityVersion`` as legacy-imported / not validated
#: against any canonical branch schema. Written only by the Step 3
#: legacy-import service (``apps.identity.import_service``); any
#: normal draft-creation path must reject it (see
#: ``services.create_draft_version``).
LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION = 0

#: The lowest ``spec_schema_version`` value that indicates a spec
#: payload was validated against a real canonical branch schema.
#: Guards the normal authoring write path against accidental
#: writes that would masquerade as legacy imports.
MIN_CANONICAL_SPEC_SCHEMA_VERSION = 1

#: Snapshot schema version for ``ImportProvenance.legacy_snapshot``.
#: Bumped independently from Django migration numbering when the
#: shape of the JSON snapshot changes materially.
IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION = 1

#: Snapshot schema version for
#: ``PrequalificationProvenance.provider_response_snapshot``. Bumped
#: independently from Django migration numbering when the shape of
#: the JSON snapshot changes materially (§17.10.a Amendment 4).
PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION = 1


class CharacterIdentity(models.Model):
    """The internal substrate name for a teammate's canonical
    identity (§17.1.a). One row per identity per workspace.

    ``teammate`` is nullable during bootstrap because benchmark
    fixtures land as identities without an owning Teammate row
    (§15.1). Production identities acquired through the normal
    teammate-creation flow will always have a teammate FK.
    """

    class Kind(models.TextChoices):
        HUMAN = "human", "Human"
        NON_HUMAN = "non_human", "Non-human"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="character_identities",
    )
    teammate = models.ForeignKey(
        Teammate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="character_identities",
        help_text=(
            "The customer-facing Teammate this identity belongs to. "
            "Nullable during bootstrap — benchmark fixtures land as "
            "identities without a Teammate. Production identities "
            "carry a non-null teammate."
        ),
    )
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        help_text=(
            "Branch discriminator (§17.2.a). Selects the schema used "
            "to validate ``CharacterIdentityVersion.spec`` and the "
            "branch's declarative approval floor + surface "
            "requirements. Round-one human uses "
            "``schemas/human_identity_schema_v1.yaml``; non-human "
            "uses the non-canonical test schema until Character "
            "Presence Language authors the real one."
        ),
    )
    name = models.CharField(
        max_length=200,
        help_text="Internal / operator-facing name for the identity.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="character_identity_unique_name_per_workspace",
            ),
            # §19 Step 3 (SESSION 242) — a real Teammate maps to at
            # most one CharacterIdentity. Enforced as a Postgres
            # partial unique so bootstrap fixture identities (which
            # legitimately carry ``teammate=NULL`` per §15.1) remain
            # allowed. Makes the legacy backfill's idempotency
            # contract a database invariant rather than a service
            # discipline.
            models.UniqueConstraint(
                fields=["teammate"],
                condition=Q(teammate__isnull=False),
                name="one_character_identity_per_teammate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.kind}]"


class CharacterIdentityVersion(models.Model):
    """One row per authored revision of a ``CharacterIdentity``.

    The lifecycle is ratified in §5.2:
      draft → approved → superseded
      draft → rejected

    At most one version per identity is in ``approved`` state at
    any moment. That invariant is enforced at two layers per
    §17.3.b:

      1. Database — Postgres partial unique constraint on
         ``(identity_id) WHERE state = 'approved'`` (name:
         ``one_approved_version_per_character_identity``).
      2. Application — the identity-version write-path service
         (``apps.identity.services``) locks the parent identity
         with ``select_for_update()`` and performs supersede +
         approve inside a single ``transaction.atomic()`` block.

    The ``spec`` blob is a structured JSON document validated
    server-side by the schema selected by
    ``CharacterIdentity.kind`` (§17.3.a). Provider-specific
    identifiers, generation evidence, normalized outputs, and
    approval history are **outside** ``spec`` — they live on
    ``GenerationRecord``, ``NormalizationManifest``, and the
    version's own state/approval fields.
    """

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        SUPERSEDED = "superseded", "Superseded"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(
        CharacterIdentity,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    revision = models.PositiveIntegerField(
        help_text=(
            "Monotonically increasing within a single "
            "``CharacterIdentity``. Assigned by the write-path "
            "service, not by the caller."
        ),
    )
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.DRAFT,
    )
    spec = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured branch-specific identity payload. Validated "
            "server-side by the schema selected on the parent "
            "identity's ``kind``. Every stored payload carries an "
            "explicit ``spec_schema_version`` (§17.3.a)."
        ),
    )
    spec_schema_version = models.PositiveIntegerField(
        help_text=(
            "The schema version this payload was validated against "
            "at write time. Old payloads remain readable via "
            "explicit migration, never silently reinterpreted "
            "(§17.3.a evolution rules). "
            "Value ``0`` is the ``legacy_unvalidated`` sentinel — "
            "written only by the Step 3 legacy-import service to "
            "mark versions imported from the pre-substrate "
            "Teammate representation. Normal canonical authoring "
            "must use values >= "
            "``MIN_CANONICAL_SPEC_SCHEMA_VERSION`` (1)."
        ),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=(
            "Populated when ``state`` transitions to ``approved``. "
            "First-class field per §17.3.b — approval metadata "
            "is not a log entry."
        ),
    )
    reviewer_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["identity_id", "revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["identity", "revision"],
                name="character_identity_version_unique_revision",
            ),
            # §17.3.b — Postgres partial unique. At most one
            # approved version per identity. Zero approved is a
            # valid state (identity being drafted).
            #
            # Test environments that use SQLite do not enforce this
            # constraint. The DB in this project is Postgres end to
            # end (see ``character_os/settings.py``); integration
            # tests must run against it.
            models.UniqueConstraint(
                fields=["identity"],
                condition=Q(state="approved"),
                name="one_approved_version_per_character_identity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.identity.name} rev{self.revision} [{self.state}]"

    # ---- Provenance / qualification helpers (§19 Step 3) --------
    #
    # These properties exist so downstream code never has to
    # equate ``state == 'approved'`` with "benchmark qualified" —
    # a distinction the ratified §17.10.a vocabulary requires and
    # that the operator surfaced explicitly at SESSION 242 open.
    # They are intentionally minimal: not a new lifecycle system,
    # just an obvious safe way to read the provenance axis.

    @property
    def is_legacy_imported(self) -> bool:
        """True iff this version was created by the Step 3
        legacy-backfill service (has a paired ``ImportProvenance``
        row). ``approved`` state alone does not imply this.
        """
        # OneToOne reverse accessor raises RelatedObjectDoesNotExist
        # when the row is absent; ``hasattr`` collapses that into
        # a boolean without swallowing unrelated exceptions.
        return hasattr(self, "import_provenance")

    @property
    def is_canonical_schema_validated(self) -> bool:
        """True iff the ``spec`` payload was validated against a
        real canonical branch schema at write time. Legacy imports
        carry the ``legacy_unvalidated`` sentinel (0) and are
        therefore False here regardless of ``state``.
        """
        return self.spec_schema_version >= MIN_CANONICAL_SPEC_SCHEMA_VERSION

    @property
    def is_qualification_eligible(self) -> bool:
        """True iff this version *could* enter benchmark
        qualification scoring (§17.7) — i.e. it is not a legacy
        import and its spec is canonical-schema-validated.

        This is a coarse hint, not a formal qualification state:
        Step 8+ owns the actual benchmark-qualification lifecycle
        (§17.10.a vocabulary ``qualification_validated``). This
        property exists only to prevent Step 3 callers from
        accidentally treating imported approved versions as
        candidates for that lifecycle.
        """
        return self.is_canonical_schema_validated and not self.is_legacy_imported


# ---------------------------------------------------------------------
# 2.b — Reference relationships, generation provenance, normalization
#       manifest. All three carry cross-workspace isolation per §7.5
#       and are consumed by the write-path service in 2.d.
# ---------------------------------------------------------------------


class IdentityReferenceKind(models.TextChoices):
    """Artifact class per §17.5.a. ``purpose`` describes how the
    artifact participates in identity; purpose values are validated
    server-side against the branch purpose schema and adding a new
    purpose does not require a migration.

    Only ``portrait_reference`` is exercised in round-one benchmark;
    the other classes are declared so the substrate accepts them as
    valid kinds without accepting any purpose value yet.
    """

    PORTRAIT_REFERENCE = "portrait_reference", "Portrait reference"
    MOTION_REFERENCE = "motion_reference", "Motion reference"
    SPEECH_REFERENCE = "speech_reference", "Speech reference"
    BODY_REFERENCE = "body_reference", "Body reference"
    ENVIRONMENT_REFERENCE = "environment_reference", "Environment reference"
    EXPRESSION_REFERENCE = "expression_reference", "Expression reference"


class ReferenceState(models.TextChoices):
    """§7.4 reference-state lifecycle. Shared by ``IdentityReference``
    and the canonical voice / realtime references landed in 2.c.

    §17.10.a Amendment 4 (SESSION 243) added ``SUPERSEDED``: a
    reference that was ``APPROVED`` and has been replaced by a
    newer authoring event admitting a different reference into the
    same ``(identity_version, kind, purpose)`` slot. Distinct from
    ``REJECTED``: rejected candidates were never admitted;
    superseded rows once were and were later replaced. Preserving
    the distinction is what makes ``state='approved'`` mean
    "currently admitted for product use" per §5.6.a.
    """

    RAW = "raw", "Raw"
    NORMALIZED = "normalized", "Normalized"
    PROVISIONAL = "provisional", "Provisional"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"
    REJECTED = "rejected", "Rejected"


class IdentityReference(models.Model):
    """Typed relationship between an ``Asset`` and a
    ``CharacterIdentityVersion`` (§7).

    Reference identity is ``(kind, purpose)`` — written as
    ``<kind>/<purpose>``. ``purpose`` is a free-text field because
    valid values are enumerated in the branch-specific purpose
    schema (§17.5.a); the write-path service validates it at
    creation time. Adding a new purpose value to the schema does
    not require a Django migration.

    Cross-workspace isolation (§7.5): the referenced ``Asset`` must
    belong to the same workspace as the parent identity. Enforced
    via ``clean()`` plus a ``pre_save`` signal so the raw
    ``.save()`` path (which does not run ``clean()`` by default)
    is covered too.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.CASCADE,
        related_name="references",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="identity_references",
        help_text=(
            "PROTECT — an asset that participates in an identity "
            "cannot silently disappear via cascade. Removing an "
            "identity-anchoring asset is an explicit reviewer "
            "decision that must be recorded on the version."
        ),
    )
    kind = models.CharField(
        max_length=32,
        choices=IdentityReferenceKind.choices,
    )
    purpose = models.CharField(
        max_length=64,
        help_text=(
            "Structured purpose per §17.5.a — validated by the "
            "branch purpose schema loaded at write time. Adding a "
            "purpose value does not require a Django migration. "
            "The write-path service is the authoritative gate; "
            "invalid purposes fail there."
        ),
    )
    state = models.CharField(
        max_length=16,
        choices=ReferenceState.choices,
        default=ReferenceState.RAW,
    )
    generation_record = models.ForeignKey(
        "GenerationRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produced_references",
        help_text=(
            "The generation attempt that produced this asset, "
            "when known. Nullable for bootstrap references landed "
            "outside the generation pipeline (e.g. hand-authored "
            "fixture inputs)."
        ),
    )
    reviewer_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["identity_version_id", "kind", "purpose"]
        constraints = [
            # §17.10.a Amendment 4 (SESSION 243) — at most one
            # currently-admitted reference per
            # ``(identity_version, kind, purpose)`` slot. Postgres
            # partial unique. Enforces the co-ratified reference
            # uniqueness invariant that ``approve_reference`` moves
            # the prior occupant to ``SUPERSEDED`` before admitting a
            # new one. This constraint fires only on bypass or
            # defect; the service is the primary enforcement point.
            models.UniqueConstraint(
                fields=["identity_version", "kind", "purpose"],
                condition=Q(state="approved"),
                name="one_approved_reference_per_slot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}/{self.purpose} [{self.state}]"

    def clean(self) -> None:
        """§7.5 — the referenced ``Asset`` must belong to the same
        workspace as the identity. Cross-workspace references are a
        violation of the substrate contract, not a serializer-level
        concern.
        """
        super().clean()
        if self.identity_version_id and self.asset_id:
            identity_ws = self.identity_version.identity.workspace_id
            asset_ws = self.asset.workspace_id
            if identity_ws != asset_ws:
                raise ValidationError(
                    {
                        "asset": (
                            "Asset workspace does not match the "
                            "identity's workspace (§7.5)."
                        )
                    }
                )


class GenerationProvider(models.TextChoices):
    """Provider-namespaced identifiers for generation records
    (§15.5). New providers land as new choices when the strangler
    migration adds them (§17.9.a). Round-one benchmark providers
    are enumerated here; new values may be added in a small
    migration when Step 5+ adds provider adapters.
    """

    RUNWAY_AVATAR = "runway_avatar", "Runway (avatar)"
    RUNWAY_REALTIME = "runway_realtime", "Runway (realtime)"
    # §19 Step 5 (SESSION 244) — provenance for the Runway
    # still-portrait ``PortraitProvider`` adapter. Distinct from
    # ``RUNWAY_AVATAR`` per §17.9.a Amendment on Avatar: "avatar"
    # is a legacy endpoint term, not a domain-boundary decision;
    # still-portrait generation is its own domain operation and
    # is recorded with its own provenance value. Existing rows
    # stamped ``RUNWAY_AVATAR`` are not migrated — they retain
    # their historical meaning until their own lifecycle is
    # resolved. New Runway still-portrait adapter output uses
    # this value exclusively.
    RUNWAY_STILL_PORTRAIT = "runway_still_portrait", "Runway (still portrait)"
    # §19 Step 6 (SESSION 245) — provenance for the Runway
    # voice-authoring ``VoiceDesignProvider`` adapter. Distinct
    # from ``RUNWAY_TTS`` per §17.4.a lifecycle boundary: voice
    # authoring produces a durable ``voice_id`` (identity), TTS
    # consumes one to synthesize speech (runtime). One value
    # spans both design (from text) and clone (from reference
    # audio) because Runway itself models them as one endpoint
    # (``POST /v1/voices`` with a ``from.type`` discriminator);
    # the operation type is captured in the generation record's
    # ``prompt_snapshot``, not the provider stamp.
    RUNWAY_VOICE = "runway_voice", "Runway (voice authoring)"
    RUNWAY_TTS = "runway_tts", "Runway (TTS)"
    STABILITY_STILL = "stability_still", "Stability (still portrait)"
    ELEVENLABS_TTS = "elevenlabs_tts", "ElevenLabs (TTS)"
    MOCK = "mock", "Mock (test / benchmark scaffolding)"
    # §19 Step 3 (SESSION 242) — historical ingestion only.
    # Marks synthetic GenerationRecord rows created by the
    # legacy-backfill service so the provenance chain from
    # legacy Teammate field → substrate row is inspectable.
    # NEVER a qualified rendering provider, benchmark provider,
    # or evidence that satisfies provider qualification. Consumers
    # must filter this value out of any capability / qualification
    # decision.
    LEGACY_IMPORTED = "legacy_imported", "Legacy import (historical, unqualified)"


class DirectionHypothesis(models.TextChoices):
    """The five candidate rendering directions from Portrait
    Language plus a neutral value for identity-only generations
    (§15.5).
    """

    SOFTENED_PHOTOGRAPHIC = "softened_photographic", "Softened Photographic"
    CINEMATIC_NATURALISTIC = "cinematic_naturalistic", "Cinematic Naturalistic"
    PAINTERLY_NATURALISTIC = "painterly_naturalistic", "Painterly Naturalistic"
    CONTEMPORARY_PORTRAIT_ILLUSTRATION = (
        "contemporary_portrait_illustration",
        "Contemporary Portrait Illustration",
    )
    LIGHTLY_STYLIZED_REALISM = "lightly_stylized_realism", "Lightly Stylized Realism"
    IDENTITY_ONLY = "identity_only", "Identity-only (no direction hypothesis)"


class ExecutionMode(models.TextChoices):
    """The mode the caller requested when the generation was
    attempted (§9.4).

    Every value describes an execution-framework decision. Rows
    that record no provider execution — currently only Step 3
    legacy imports — leave ``execution_mode`` NULL rather than
    inventing a value here. NULL is the honest label for the
    absence of any execution-framework decision (§17.10.a
    Amendment 3, ratified post-SESSION 242). Origin is carried
    by ``GenerationProvider.LEGACY_IMPORTED`` + ``ImportProvenance``
    + ``spec_schema_version=0``.
    """

    FORCED_MOCK = "forced_mock", "Forced mock"
    AUTO = "auto", "Auto"
    REAL_REQUIRED = "real_required", "Real required"
    UNAVAILABLE = "unavailable", "Unavailable"


class ExecutionModeActual(models.TextChoices):
    """What actually happened (§9.4).

    Every value describes what an adapter did on a real request.
    NULL means no adapter ever ran through the framework for this
    row — see ``ExecutionMode`` docstring.
    """

    REAL = "real", "Real"
    MOCK = "mock", "Mock"
    MOCK_FALLBACK = "mock_fallback", "Mock fallback"


class GenerationApprovalState(models.TextChoices):
    """§15.5 — the generation record's own approval lifecycle.
    Distinct from ``ReferenceState`` (which lives on the reference
    row that consumes the produced asset).
    """

    PENDING = "pending", "Pending"
    ADMITTED_TO_BUNDLE = "admitted_to_bundle", "Admitted to bundle"
    REJECTED = "rejected", "Rejected"
    SUPERSEDED = "superseded", "Superseded"


class GenerationRecord(models.Model):
    """Immutable evidence of a provider generation attempt (§8).

    Immutability is enforced along the supported write paths:

    * The write-path service (2.d) creates records via
      ``.objects.create`` and never mutates the row after commit.
    * ``ModelAdmin`` exposes the row read-only (2.d).
    * A model-level defensive guard raises on any attempt to save
      an already-persisted instance (see ``save()`` below), which
      catches instance-level mutation attempts made through the
      supported ORM path.

    Direct ``QuerySet.update()`` / raw SQL bypasses are considered
    unsupported internal misuse; the contract does not require a
    DB trigger to prevent them, and 2.d's tests scope the
    immutability claim to the supported paths.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.PROTECT,
        related_name="generation_records",
        help_text=(
            "PROTECT — a version's generation history is part of "
            "the identity's evidence trail and cannot silently "
            "vanish if the version is later removed."
        ),
    )
    provider = models.CharField(
        max_length=32,
        choices=GenerationProvider.choices,
    )
    provider_model = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "Provider-side model / version identifier where the "
            "provider distinguishes models (Runway gen4_image, "
            "Stability SD3, ElevenLabs voice model). Free text so "
            "new provider model names do not require a migration."
        ),
    )
    direction_hypothesis = models.CharField(
        max_length=48,
        choices=DirectionHypothesis.choices,
        default=DirectionHypothesis.IDENTITY_ONLY,
    )
    prompt_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured snapshot of the exact input the provider "
            "received. Kept because prompts + references + "
            "provider version are the reproduction contract for "
            "the raw output asset."
        ),
    )
    seed_or_reproduction_data = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Provider-specific seed / reproduction handle where "
            "available. Nullable for providers that do not expose "
            "one."
        ),
    )
    input_reference_assets = models.ManyToManyField(
        Asset,
        related_name="fed_into_generation_records",
        through="GenerationRecordInput",
        blank=True,
        help_text=(
            "Assets fed into the provider call (identity portrait "
            "references, previously-approved anchors, etc.). "
            "Preserved so the generation is replayable."
        ),
    )
    raw_output_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="raw_output_of_generation_records",
        help_text=(
            "Provider's response as received, byte-for-byte "
            "preserved (§17.6.a two-tier evidence). Nullable when "
            "the attempt failed before producing an asset."
        ),
    )
    normalized_output_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="normalized_output_of_generation_records",
        help_text=(
            "Output of the normalization pipeline (Step 7) applied "
            "to ``raw_output_asset``. Nullable in round-one "
            "authoring paths that pre-date the pipeline."
        ),
    )
    execution_mode = models.CharField(
        max_length=24,
        choices=ExecutionMode.choices,
        null=True,
        blank=True,
        help_text=(
            "NULL iff no provider execution occurred through the "
            "execution framework for this row (currently: Step 3 "
            "legacy imports). Non-NULL for every executable "
            "provider record. See ``ExecutionMode`` docstring and "
            "§17.10.a Amendment 3 (post-SESSION 242 correction)."
        ),
    )
    execution_mode_actual = models.CharField(
        max_length=24,
        choices=ExecutionModeActual.choices,
        null=True,
        blank=True,
        help_text=(
            "Companion to ``execution_mode``. NULL iff no adapter "
            "actually ran through the framework for this row. "
            "``execution_mode`` and ``execution_mode_actual`` are "
            "always both NULL or both non-NULL (invariant enforced "
            "at ``clean()``)."
        ),
    )
    elapsed_ms = models.PositiveIntegerField(null=True, blank=True)
    approval_state = models.CharField(
        max_length=24,
        choices=GenerationApprovalState.choices,
        default=GenerationApprovalState.PENDING,
    )
    reviewer_notes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Structured reviewer observations. Appended via child "
            "records if history is needed; the parent JSON blob "
            "captures the current-state view (§15.5)."
        ),
    )
    failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}/{self.provider_model} [{self.approval_state}]"

    def clean(self) -> None:
        """§7.5 cross-workspace isolation + §19 Step 3 legacy
        pairing invariant.
        """
        super().clean()
        self._enforce_legacy_pairing_invariant()
        if not self.identity_version_id:
            return
        identity_ws_id = self.identity_version.identity.workspace_id
        for field_name in ("raw_output_asset", "normalized_output_asset"):
            asset = getattr(self, field_name, None)
            if asset is None:
                continue
            if asset.workspace_id != identity_ws_id:
                raise ValidationError(
                    {
                        field_name: (
                            "Asset workspace does not match the "
                            "identity's workspace (§7.5)."
                        )
                    }
                )

    def _enforce_legacy_pairing_invariant(self) -> None:
        """§19 Step 3 provider ↔ execution-field pairing
        (SESSION 242 shipped as `LEGACY_HISTORICAL` enum values;
        corrected post-SESSION 242 under §17.10.a Amendment 3 to
        nullable execution fields).

        The invariant enforces two facts together:

        1. ``execution_mode`` and ``execution_mode_actual`` are
           both NULL or both non-NULL. A half-null state has no
           semantics defined anywhere.
        2. ``provider == LEGACY_IMPORTED`` iff both execution
           fields are NULL.

        Rationale: execution-mode vocabulary describes an
        execution-framework decision (§9.4). Legacy imports never
        went through the framework, so the honest label is
        absence, not a synthesized enum value. Origin is carried
        by ``GenerationProvider.LEGACY_IMPORTED`` +
        ``ImportProvenance`` + ``spec_schema_version=0``, not by
        an execution enum. NULL here is a *specific* semantic:
        "no provider execution occurred." It is NOT a general
        "missing metadata" catch-all; malformed provider records
        must not silently degrade to NULL execution fields.

        ``ExecutionMode.UNAVAILABLE`` remains distinct from NULL:
        UNAVAILABLE = execution requested through the framework
        but the provider could not serve it; NULL = no request
        through the framework was ever made.
        """
        mode_is_null = self.execution_mode is None
        actual_is_null = self.execution_mode_actual is None
        if mode_is_null != actual_is_null:
            raise ValidationError(
                {
                    "execution_mode": (
                        "execution_mode and execution_mode_actual "
                        "must both be NULL or both non-NULL. Got "
                        f"execution_mode={self.execution_mode!r}, "
                        f"execution_mode_actual="
                        f"{self.execution_mode_actual!r}. A half-null "
                        "state has no defined semantics (§17.10.a "
                        "Amendment 3)."
                    )
                }
            )
        is_legacy_provider = self.provider == GenerationProvider.LEGACY_IMPORTED
        both_execution_null = mode_is_null and actual_is_null
        if is_legacy_provider == both_execution_null:
            return
        raise ValidationError(
            {
                "provider": (
                    "GenerationProvider.LEGACY_IMPORTED must pair with "
                    "NULL execution_mode AND NULL execution_mode_actual "
                    "— and vice versa. Got "
                    f"provider={self.provider!r}, "
                    f"execution_mode={self.execution_mode!r}, "
                    f"execution_mode_actual="
                    f"{self.execution_mode_actual!r}. Origin lives on "
                    "``provider`` + ``ImportProvenance``, not in the "
                    "execution enums; a non-legacy provider always has "
                    "non-NULL execution fields, and a legacy_imported "
                    "record always has NULL execution fields "
                    "(§17.10.a Amendment 3)."
                )
            }
        )

    def save(self, *args, **kwargs) -> None:
        """Defensive append-only guard. Raises on instance-level
        mutation of an already-persisted row through the supported
        ORM path. Does not (and does not claim to) prevent
        ``QuerySet.update(...)`` or raw SQL — those are unsupported
        internal misuse per Step 2's ratified scope.
        """
        if self.pk is not None and self._state.adding is False:
            existing = type(self).objects.filter(pk=self.pk).exists()
            if existing:
                raise ValidationError(
                    "GenerationRecord is append-only (§8.2). "
                    "Mutating a persisted record is not a "
                    "supported write path."
                )
        super().save(*args, **kwargs)


class GenerationRecordInput(models.Model):
    """Through table for ``GenerationRecord.input_reference_assets``.

    Explicit so future ordering / role annotations on the
    generation's input side can be added without a data migration.
    """

    generation_record = models.ForeignKey(GenerationRecord, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)
    ordinal = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generation_record", "asset"],
                name="generation_record_input_unique",
            ),
        ]
        ordering = ["generation_record_id", "ordinal"]


class NormalizationManifest(models.Model):
    """One immutable record per generation describing exactly what
    the normalization pipeline did (§10.6, §15.6).

    Determinism constraint (§10.6): given identical raw asset,
    identical pipeline version, and identical manifest, the
    normalized artifact must be byte-for-byte identical. The
    substrate holds the manifest; the pipeline (Step 7) enforces
    determinism.

    Immutability applies the same discipline as ``GenerationRecord``:
    supported write paths create-only; instance-level defensive
    guard on ``save``; admin readonly; ``QuerySet.update()`` and raw
    SQL are unsupported internal misuse.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation_record = models.OneToOneField(
        GenerationRecord,
        on_delete=models.PROTECT,
        related_name="normalization_manifest",
        help_text=(
            "One manifest per generation. OneToOne — a generation "
            "either produced a normalized output through the "
            "pipeline or it did not."
        ),
    )
    raw_output_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="normalization_manifest_raw_inputs",
        help_text=(
            "The exact raw asset the pipeline consumed. Preserved "
            "byte-for-byte so future pipeline revisions can be "
            "replayed against the same provider evidence."
        ),
    )
    normalized_output_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="normalization_manifest_outputs",
    )
    pipeline_version = models.TextField(
        help_text=(
            "Composition of enabled stage versions (§17.6.a). "
            "Free-form string — the pipeline defines its own "
            "encoding. Widened from CharField(64) → TextField per "
            "SESSION 249 9.b.3a Finding 10 when the first real "
            "frozen-manifest persistence attempt surfaced that "
            "Step 7's shipped compound encoding requires ~110 "
            "chars. The field's own docstring already promised "
            "'free-form'; the earlier length cap was an unforced "
            "discipline that the shipped encoding exceeded."
        ),
    )
    surface_profile_id = models.CharField(
        max_length=64,
        help_text=(
            "Stable identifier of the ``SurfaceProfile`` YAML that "
            "the pipeline consumed (§15.6). SurfaceProfile is data, "
            "not a Django table."
        ),
    )
    surface_profile_version = models.PositiveIntegerField()
    background_id = models.CharField(
        max_length=64,
        help_text=(
            "Identifier from the controlled background family "
            "(``schemas/background_family_v1.yaml``)."
        ),
    )
    stages_executed = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of stages with their versions.",
    )
    stages_skipped = models.JSONField(
        default=list,
        blank=True,
        help_text="Skipped stages with reason per stage.",
    )
    eye_line_adjustments = models.JSONField(default=dict, blank=True)
    crop_metadata = models.JSONField(default=dict, blank=True)
    execution_duration_ms = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"manifest for {self.generation_record_id} "
            f"pipeline={self.pipeline_version}"
        )

    def clean(self) -> None:
        """Assets must share a workspace with the identity through
        which the generation was recorded (§7.5).
        """
        super().clean()
        if not self.generation_record_id:
            return
        identity_ws_id = (
            self.generation_record.identity_version.identity.workspace_id
        )
        for field_name in ("raw_output_asset", "normalized_output_asset"):
            asset = getattr(self, field_name, None)
            if asset is None:
                continue
            if asset.workspace_id != identity_ws_id:
                raise ValidationError(
                    {
                        field_name: (
                            "Asset workspace does not match the "
                            "identity's workspace (§7.5)."
                        )
                    }
                )

    def save(self, *args, **kwargs) -> None:
        """Append-only guard along the supported ORM path. Same
        scope-limit as ``GenerationRecord.save``.
        """
        if self.pk is not None and self._state.adding is False:
            existing = type(self).objects.filter(pk=self.pk).exists()
            if existing:
                raise ValidationError(
                    "NormalizationManifest is append-only "
                    "(§10.6). Mutating a persisted record is not "
                    "a supported write path."
                )
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# 2.c — Canonical voice / realtime references + Approved
#       Representation Bundle. All three carry the ratified
#       provider-neutrality boundary from §17.4.a — the bundle's
#       domain contract exposes canonical approved representations
#       only; provider provenance stays on ``GenerationRecord``.
# ---------------------------------------------------------------------


class CanonicalVoiceReference(models.Model):
    """Per-identity-version canonical voice reference (§11, §15.3).

    Callers ask for "the approved voice for this identity" and
    receive a ``CanonicalVoiceReference``. Provider details
    (Runway voice_id, ElevenLabs voice model, seed, reference
    audio) live inside ``generation_record`` per §17.4.a, not on
    this row. Provider resolution happens at the adapter boundary.

    Changing the approved voice is an identity revision (§11.3,
    §5.4), not a runtime provider swap; that discipline is
    enforced by the write-path service (2.d).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.CASCADE,
        related_name="canonical_voice_references",
    )
    generation_record = models.ForeignKey(
        GenerationRecord,
        on_delete=models.PROTECT,
        related_name="canonical_voice_references",
        help_text=(
            "The generation attempt that produced this voice. All "
            "provider-specific values live inside the referenced "
            "record's ``prompt_snapshot`` / "
            "``seed_or_reproduction_data``, not on this row."
        ),
    )
    state = models.CharField(
        max_length=16,
        choices=ReferenceState.choices,
        default=ReferenceState.RAW,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-approved_at", "id"]

    def __str__(self) -> str:
        return f"voice ref for {self.identity_version_id} [{self.state}]"


class CanonicalRealtimeReference(models.Model):
    """Per-identity-version canonical realtime reference (§11, §15.3).

    Same provider-neutrality discipline as
    ``CanonicalVoiceReference``. Runway avatar IDs and any future
    realtime-provider identifiers stay inside the generation
    record's provenance fields.

    Note (§17.10.a): the legacy ``Teammate.runway_avatar_id`` is
    barred from the permanent canonical schema. Realtime
    representation authoring lifecycle is deferred to §17.9.a
    resolution; this model exists as the substrate slot the
    ratified representation will fill.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.CASCADE,
        related_name="canonical_realtime_references",
    )
    generation_record = models.ForeignKey(
        GenerationRecord,
        on_delete=models.PROTECT,
        related_name="canonical_realtime_references",
    )
    state = models.CharField(
        max_length=16,
        choices=ReferenceState.choices,
        default=ReferenceState.RAW,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-approved_at", "id"]

    def __str__(self) -> str:
        return f"realtime ref for {self.identity_version_id} [{self.state}]"


class ApprovedRepresentationBundle(models.Model):
    """Per-identity-version approved trio (§6, §15.3).

    The bundle binds one identity version to the specific
    canonical voice + realtime references + approved reference-view
    set that a reviewer has admitted together (§6.2). Reverting one
    field to a prior value would silently reconstruct a trio that
    was never reviewed as a whole — the bundle is what prevents
    that.

    Provider-neutrality boundary (§17.4.a): callers ask for
    ``approved_voice`` and ``approved_realtime`` and receive
    canonical references. They must never need to know Runway,
    ElevenLabs, Stability, or provider-specific IDs at the bundle
    boundary. Provider details stay underneath the canonical
    reference on ``GenerationRecord``.

    ``NormalizationProfile`` (per-identity normalization overrides)
    is deliberately absent from Step 2. §15.6 defers the table;
    round-one may not need it at all. Re-introducing the concept
    requires a contract amendment per §19.5.

    Approved reference-view assets (portrait references) are
    attached via ``IdentityReference`` records against the same
    identity version — not embedded on this bundle (§15.3).
    """

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        SUPERSEDED = "superseded", "Superseded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.CASCADE,
        related_name="representation_bundles",
    )
    approved_voice = models.ForeignKey(
        CanonicalVoiceReference,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bundles",
        help_text=(
            "The canonical voice reference bound into this bundle. "
            "Nullable during draft assembly; must be non-null when "
            "the bundle transitions to ``approved`` (enforced by "
            "the write-path service in 2.d)."
        ),
    )
    approved_realtime = models.ForeignKey(
        CanonicalRealtimeReference,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bundles",
        help_text=(
            "The canonical realtime reference bound into this "
            "bundle. Nullable during draft assembly; may remain "
            "null when the identity does not surface a realtime "
            "representation."
        ),
    )
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.DRAFT,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewer_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-approved_at", "id"]
        constraints = [
            # §17.10.a Amendment 4 (SESSION 243) — at most one
            # currently-admitted bundle per identity version. Zero
            # approved bundles on a version is a valid state (bundle
            # in draft assembly, or version pre-bundle). Postgres
            # partial unique; the write-path services
            # (``services.approve_bundle`` +
            # ``services.approve_prequalification_version`` cascade)
            # transactionally supersede the previous occupant before
            # inserting the new one, so this constraint fires only on
            # bypass or defect.
            models.UniqueConstraint(
                fields=["identity_version"],
                condition=Q(state="approved"),
                name="one_approved_bundle_per_identity_version",
            ),
        ]

    def __str__(self) -> str:
        return f"bundle for {self.identity_version_id} [{self.state}]"


# ---------------------------------------------------------------------
# 3.a — Legacy-import provenance (SESSION 242).
#       One row per legacy-imported CharacterIdentityVersion.
#       Presence of a row IS the ``legacy_imported`` marker from
#       §17.10.a Amendment 2's ratified provenance vocabulary.
# ---------------------------------------------------------------------


class ImportProvenance(models.Model):
    """Recorded evidence that a ``CharacterIdentityVersion`` was
    created by the Step 3 legacy-backfill service — not by the
    authoritative Step 2 write path.

    Distinct from ``state``: an imported version can be
    ``state='approved'`` (currently admitted for product use) yet
    is **not** benchmark-qualified, provider-qualified, Portrait
    Language compliant, or schema-validated. That semantic gap is
    the reason this table exists. Any consumer that needs to
    filter on "legacy-imported" queries this table (or reads the
    ``CharacterIdentityVersion.is_legacy_imported`` property).

    Frozen at write. This row is append-only historical evidence;
    the model does not carry an update path and admin should not
    expose it as editable when it is registered (Step 3 leaves
    admin unregistered, matching the Step 2 discipline for
    evidence records).

    OneToOne with the version: each version is legacy-imported or
    it is not. The paired unique index makes accidental duplicate
    provenance rows a database-level impossibility.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.OneToOneField(
        CharacterIdentityVersion,
        on_delete=models.PROTECT,
        related_name="import_provenance",
        help_text=(
            "PROTECT — an imported version's provenance cannot "
            "silently vanish if the version is later removed. If "
            "an operator needs to undo an import, that is a "
            "deliberate operator-directed operation (out of Step 3 "
            "scope)."
        ),
    )
    import_source = models.CharField(
        max_length=64,
        default="apps.spokespeople.Teammate",
        help_text=(
            "Names the origin model. Round-one imports all come "
            "from ``apps.spokespeople.Teammate``; the field exists "
            "so future imports from a different source do not "
            "require a new provenance table."
        ),
    )
    source_teammate_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "Snapshot of the source Teammate's primary key at "
            "import time. Nullable because the Teammate row may "
            "later be deleted; the provenance row must survive."
        ),
    )
    import_run_id = models.UUIDField(
        help_text=(
            "Groups every provenance row written in a single "
            "management-command invocation. Bare UUID (not a FK) "
            "— Step 3 deliberately does not add an ImportRun table."
        ),
    )
    migration_version = models.CharField(
        max_length=64,
        help_text=(
            "Which substrate migration was active at import time "
            "(e.g. ``identity.0002``). Recorded so future readers "
            "can reason about the schema shape at import."
        ),
    )
    snapshot_schema_version = models.PositiveIntegerField(
        help_text=(
            "Version of the ``legacy_snapshot`` JSON shape. "
            "Bumped independently from Django migration numbering "
            "when the snapshot shape changes materially."
        ),
    )
    legacy_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Frozen snapshot of the imported Teammate's identity-"
            "relevant fields at import time. Scoped to the three "
            "legacy identity fields (``runway_avatar_id``, "
            "``portrait_path``, ``voice_id``) plus the identity-"
            "page text fields that describe how the operator was "
            "authoring the teammate. Never mutated after write."
        ),
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self) -> str:
        return f"legacy_imported version {self.identity_version_id}"

    def clean(self) -> None:
        """§17.10.a Amendment 4 mutual exclusion: a version cannot
        carry both ``ImportProvenance`` and ``PrequalificationProvenance``.
        Defensive second layer beneath the authoritative service
        write paths (``import_service`` for this table;
        ``services.record_prequalification_representation`` for the
        peer). The authoritative service is the primary enforcement
        point per the amendment's ratified discipline.
        """
        super().clean()
        if not self.identity_version_id:
            return
        peer_present = PrequalificationProvenance.objects.filter(
            identity_version_id=self.identity_version_id,
        ).exists()
        if peer_present:
            raise ValidationError(
                {
                    "identity_version": (
                        "Version already carries PrequalificationProvenance; "
                        "ImportProvenance is mutually exclusive with it "
                        "per §17.10.a Amendment 4."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        """Append-only guard along the supported ORM path. Same
        scope-limit as ``GenerationRecord.save`` /
        ``NormalizationManifest.save`` — instance-level mutation
        of a persisted row is refused; ``QuerySet.update()`` /
        raw SQL are unsupported internal misuse per Step 3's
        ratified scope.
        """
        if self.pk is not None and self._state.adding is False:
            existing = type(self).objects.filter(pk=self.pk).exists()
            if existing:
                raise ValidationError(
                    "ImportProvenance is append-only (§19 Step 3). "
                    "Mutating a persisted record is not a "
                    "supported write path."
                )
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------
# 4.a — Prequalification-authored provenance (SESSION 243).
#       One row per prequalification-authored CharacterIdentityVersion.
#       Presence of a row IS the ``prequalification_authored`` marker
#       from §17.10.a Amendment 4's ratified provenance vocabulary.
#       Sibling to ImportProvenance; mutually exclusive with it.
# ---------------------------------------------------------------------


class PrequalificationSourceCall(models.TextChoices):
    """Bounded discriminator identifying which production authoring
    flow triggered a prequalification-authored write (§17.10.a
    Amendment 4). Adding a new value requires a small migration when
    Step 4.d migrates a new call site.

    New values are landed when the paired write site migrates in
    Step 4.d. The Step 4.a landing enumerates the call sites already
    identified in the SESSION 243 audit of live production mirror
    writes.
    """

    WIZARD_CREATE = "wizard_create", "Wizard: create teammate"
    WIZARD_REBAKE = "wizard_rebake", "Wizard: rebake avatar"
    CLONE_VOICE_PRESET = "clone_voice_preset", "Voice: clone preset path"
    CLONE_VOICE_CLONE = "clone_voice_clone", "Voice: clone from audio"
    CHANGE_VOICE = "change_voice", "Voice: change preset"
    REFRESH_PORTRAIT = "refresh_portrait", "Portrait: refresh URL"
    SEED_CAST = "seed_cast", "Command: seed_cast"
    REFRESH_PORTRAIT_BATCH = "refresh_portrait_batch", "Command: refresh_portraits"
    PERSIST_PORTRAIT_BATCH = (
        "persist_portrait_batch",
        "Command: persist_spokesperson_portraits",
    )
    SMOKE_VOICE_APPLY = "smoke_voice_apply", "Command: smoke_voice apply"
    SMOKE_VOICE_RESTORE = "smoke_voice_restore", "Command: smoke_voice restore"


class PrequalificationProvenance(models.Model):
    """Recorded evidence that a ``CharacterIdentityVersion`` was
    created by a post-Step-4 production authoring flow that predates
    the qualified authoring path (§17.10.a Amendment 4, ratified
    2026-08-07).

    Distinct from ``ImportProvenance`` on origin semantics:

    * ``ImportProvenance`` — Step 3 one-time backfill from
      pre-substrate ``Teammate`` rows.
    * ``PrequalificationProvenance`` — post-Step-4 canonical write
      from a live production authoring flow (wizard create / rebake,
      change_voice, refresh_portrait, batch commands, smoke
      instrumentation).

    Distinct from ``state``: an authored version can be
    ``state='approved'`` (currently admitted for product use per
    §5.6.a) yet is **not** benchmark-qualified,
    Portrait-Language-qualified, or schema-validated. Presence of
    this row is exactly the semantic gap.

    Provider-neutrality boundary (§17.4.a) holds through this row:
    provider-side response evidence lives in the paired
    ``GenerationRecord.prompt_snapshot`` /
    ``seed_or_reproduction_data`` per the Amendment 4 provider-output
    convention. This model does not encode provider names, provider
    IDs, or provider-specific reproduction handles.

    Frozen at write. Append-only.

    OneToOne with the version. Mutual exclusion with
    ``ImportProvenance`` enforced primarily by the authoritative
    services and secondarily by ``clean()`` here + on
    ``ImportProvenance``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity_version = models.OneToOneField(
        CharacterIdentityVersion,
        on_delete=models.PROTECT,
        related_name="prequalification_provenance",
        help_text=(
            "PROTECT — a prequalification-authored version's "
            "provenance cannot silently vanish if the version is "
            "later removed. Explicit rollback of a specific "
            "authoring event is an operator-directed operation "
            "(out of Step 4 scope)."
        ),
    )
    source_call = models.CharField(
        max_length=48,
        choices=PrequalificationSourceCall.choices,
        help_text=(
            "Bounded discriminator identifying which live production "
            "authoring flow triggered this write (§17.10.a Amendment "
            "4). Recorded so the provenance chain from "
            "call site → substrate row is inspectable during the "
            "growth window."
        ),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=(
            "The user that triggered the authoring event, when "
            "known. Nullable because management-command / "
            "automated flows may legitimately have no interactive "
            "user (``seed_cast``, batch refresh, smoke "
            "instrumentation). A synthetic 'system user' is not "
            "invented merely to satisfy this FK."
        ),
    )
    authored_at = models.DateTimeField(auto_now_add=True)
    snapshot_schema_version = models.PositiveIntegerField(
        help_text=(
            "Version of the ``provider_response_snapshot`` JSON "
            "shape. Bumped independently from Django migration "
            "numbering when the snapshot shape changes materially."
        ),
    )
    provider_response_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Scope-limited snapshot of the provider-response evidence "
            "that produced this authoring event, mirroring the Step 3 "
            "scope-limited-snapshot discipline. Detailed provider "
            "output (voice_id, avatar_id, thumbnail_url, mock_mode, "
            "status) also lives on the paired ``GenerationRecord``; "
            "this JSONB carries a compact summary + any additional "
            "audit fields not naturally represented on "
            "``GenerationRecord``. Never mutated after write."
        ),
    )

    class Meta:
        ordering = ["-authored_at"]

    def __str__(self) -> str:
        return (
            f"prequalification_authored version "
            f"{self.identity_version_id} ({self.source_call})"
        )

    def clean(self) -> None:
        """§17.10.a Amendment 4 mutual exclusion: a version cannot
        carry both ``ImportProvenance`` and ``PrequalificationProvenance``.
        Defensive second layer beneath the authoritative service
        write paths.
        """
        super().clean()
        if not self.identity_version_id:
            return
        peer_present = ImportProvenance.objects.filter(
            identity_version_id=self.identity_version_id,
        ).exists()
        if peer_present:
            raise ValidationError(
                {
                    "identity_version": (
                        "Version already carries ImportProvenance; "
                        "PrequalificationProvenance is mutually exclusive "
                        "with it per §17.10.a Amendment 4."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        """Append-only guard along the supported ORM path. Same
        scope-limit as ``ImportProvenance.save`` — instance-level
        mutation of a persisted row is refused; ``QuerySet.update()``
        / raw SQL are unsupported internal misuse per §17.10.a
        Amendment 4's ratified scope.
        """
        if self.pk is not None and self._state.adding is False:
            existing = type(self).objects.filter(pk=self.pk).exists()
            if existing:
                raise ValidationError(
                    "PrequalificationProvenance is append-only "
                    "(§17.10.a Amendment 4). Mutating a persisted "
                    "record is not a supported write path."
                )
        super().save(*args, **kwargs)
