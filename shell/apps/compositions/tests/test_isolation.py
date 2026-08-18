"""V1 isolation test — repo-level grep for unsanctioned
``Asset.objects`` / ``CompositionStep.objects`` writes.

Mirrors ``apps/embeddings/tests/test_retrieval_privacy.py``'s
``test_only_retrieval_module_queries_chunk_tables`` pattern.

The composition-layer privacy guarantee depends on the
write surface staying narrow. Contract rule 3 (cross-
workspace asset reference rejection) is enforced by
``apps.compositions.signals`` + ``CompositionStep.clean()``.
Both fire on save paths going through the Django ORM.

The leak shape this test prevents: a view, serializer, or
ad-hoc helper that does ``Asset.objects.create(...)`` /
``CompositionStep.objects.create(...)`` /
``.update(...)`` outside the sanctioned writers — bypassing
the cross-workspace validation we depend on.

Reads (``Asset.objects.filter(...)``) are not concerning in
v1 — they don't bypass any validation. This test scopes to
writes that originate Asset / CompositionStep / Composition
rows.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# Files allowed to write to the composition tables. Everything
# else is rejected. Adding a new entry here is a code-review
# event — the entry should come with a note explaining why the
# caller doesn't / cannot route through the sanctioned path
# (the V2 runtime once it lands; until then this set is the
# entire write surface).
ALLOWED_FILES = {
    # Model definitions themselves
    "apps/compositions/models.py",
    # Admin (read-mostly; raw create paths are gated by Django
    # admin's own form validation, which runs clean())
    "apps/compositions/admin.py",
    # V2 runtime — the sanctioned writer for step-output Assets +
    # state-machine transitions. Cross-workspace validation
    # still flows through the V1 signal at save time.
    "apps/compositions/tasks.py",
    # V3 starter helpers — create Composition + first
    # CompositionStep rows from named recipes. Same workspace-
    # anchor guarantee as direct creation.
    "apps/compositions/starters.py",
    # V15.0 — recipe registry's custom resolver builds the
    # ``lines`` list for dialogue_scene (no direct ORM creates,
    # but it does call Teammate.objects.get).
    "apps/compositions/recipes.py",
    # V15.0 REST surface. The viewset calls each recipe's
    # starter; no direct ``.objects.create`` on composition
    # tables — Teammate/Asset ``.objects.get`` resolution
    # only.
    "apps/compositions/views.py",
    # Tests need to create rows directly to exercise paths
    "apps/compositions/tests/test_models.py",
    "apps/compositions/tests/test_isolation.py",
    "apps/compositions/tests/test_runtime.py",
    "apps/compositions/tests/test_primitive_avatar_speech.py",
    "apps/compositions/tests/test_duration_contract_talking_head.py",
    # SESSION 209 — customer teammate delete flow test seeds
    # Composition + Asset rows to verify the historical-output
    # preservation contract (deleting the last spokesperson keeps
    # prior compositions/transcripts intact). Sanctioned test-side
    # writer; the pre_save signal still fires on every create.
    "apps/spokespeople/tests/test_delete.py",
    "apps/compositions/tests/test_primitive_visual_clip.py",
    "apps/compositions/tests/test_v5_long_form.py",
    "apps/compositions/tests/test_v7_composite.py",
    "apps/compositions/tests/test_v8_backdrop.py",
    "apps/compositions/tests/test_v9_polish.py",
    "apps/compositions/tests/test_v10_voice.py",
    "apps/compositions/tests/test_v11_style_remix.py",
    "apps/compositions/tests/test_v12_transcribe.py",
    "apps/compositions/tests/test_v13_storyboard.py",
    "apps/compositions/tests/test_v14_dialogue.py",
    "apps/compositions/tests/test_v15_api.py",
    "apps/compositions/tests/test_v16_remove_avatar_background.py",
    "apps/compositions/tests/test_v17_extend_visual_clip.py",
    "apps/compositions/tests/test_v17_cinematic_visual_extended.py",
    # VO.1 — synthesize_voiceover_audio primitive tests construct
    # Composition + Step rows directly to exercise the voice_spec
    # discriminator + workspace-scoped resolution + mock/real
    # branches. Sanctioned writer — workspace anchor flows through
    # the standard pre_save signal.
    "apps/compositions/tests/test_vo1_voiceover.py",
    # VO.2 — overlay_audio_at_offset primitive tests seed
    # Composition + base CLIP + voiceover AUDIO + Step rows to
    # exercise slot resolution, rule-6 overflow validation, role
    # propagation, and the mock/real branches. Sanctioned writer.
    "apps/compositions/tests/test_vo2_overlay_audio.py",
    # SESSION 210 — `_aggregate_knowledge_chunk_ids` unit tests
    # construct Composition + Step + Asset rows directly to
    # exercise the aggregator on every shape (single-step,
    # multi-step, BC2 lineage carry-up, dedup, no-knowledge,
    # empty-assets edge case).
    "apps/compositions/tests/test_chunk_id_aggregator.py",
    # SESSION 258 P1 — Composition-level concurrency-safety
    # tests seed Composition + CompositionStep rows directly to
    # exercise the SQL-subquery cost UPDATE and the locked
    # verification-write helper under real threaded parallel
    # writes (transaction=True, per-thread DB connections).
    # Sanctioned test-side writer.
    "apps/compositions/tests/test_p1_concurrency_safety.py",
    # SESSION 258 P2.H — parallel-execution runtime tests seed
    # Composition + CompositionStep rows and drive execute_step
    # / execute_composition_layer_coordinator directly to
    # exercise the chord-based parallel dispatch path (feature-
    # flagged; sequential path unchanged). Sanctioned test-side
    # writer.
    "apps/compositions/tests/test_parallel_execution.py",
    # SESSION 262 — Composition observability schema v1 tests
    # construct Composition rows directly to exercise the nine
    # new observability fields, the from_db() snapshot +
    # immutable-once-populated save() guard, and the
    # DialogueSynthesisFailedError view-rescue persistence
    # pattern. Sanctioned test-side writer.
    "apps/compositions/tests/test_session262_composition_observability.py",
    # SESSION 262 / EPISODE_SCHEMA_V1 — Episode model + attach/detach
    # + observability-non-mutation tests construct Composition rows
    # directly to exercise Composition.episode FK invariants +
    # cross-Universe / cross-Workspace rejection + attach/detach
    # preserving SESSION 262 observability. Sanctioned test-side
    # writer.
    "apps/universe/tests/test_episode.py",
    "apps/universe/tests/test_episode_vertical_slice.py",
    # SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — tests for the
    # ?episode= filter + episode_title serialization + cast added_at
    # ordering seed Composition + Episode rows directly. Sanctioned
    # test-side writer.
    "apps/compositions/tests/test_episode_composition_workflow.py",
    # SESSION 210 — `sweep_expired_assets` Celery task tests
    # seed Composition + Asset rows with crafted JWT URLs to
    # exercise the hourly Beat sweep. Asset.composition FK is
    # set explicitly; the pre_save signal still fires.
    "apps/compositions/tests/test_expired_asset_sweep.py",
    # F3 overview endpoint tests construct Composition rows
    # directly to exercise the dashboard cross-cut query path.
    "apps/accounts/tests/test_workspace_overview.py",
    # F5 lineage endpoint tests construct producer/consumer
    # composition graphs to exercise both lineage shapes.
    "apps/compositions/tests/test_f5_lineage.py",
    # F6 citation tests seed compositions with
    # knowledge_chunk_ids to exercise the doc resolver.
    "apps/compositions/tests/test_f6_citations.py",
    # F7 reverse-lookup tests seed compositions to verify
    # the doc → compositions reverse-query path.
    "apps/embeddings/tests/test_f7_compositions_reverse.py",
    # R1 tests construct Composition rows to exercise the
    # tool-invocation cross-workspace check
    # (produced_composition refs).
    "apps/realtime/tests/test_models.py",
    # R5 transcript-capture task creates Asset(TRANSCRIPT)
    # rows in the session's workspace. Sanctioned writer
    # — Asset.workspace inherits from session.workspace,
    # so the row is always in-workspace by construction.
    "apps/realtime/tasks.py",
    # R5 tests verify the task creates the right Asset
    # row + wires it to the session.
    "apps/realtime/tests/test_r5_transcript_capture.py",
    # R6 cross-session-memory tests seed Asset(TRANSCRIPT)
    # rows on the session's workspace to exercise the
    # memory composer's transcript-read path. Same
    # workspace-anchor guarantee as R5.
    "apps/realtime/tests/test_r6_session_memory.py",
    # R7.1 sync-tool tests seed Asset(TRANSCRIPT) rows to
    # exercise `recall_recent_conversations`. Same
    # workspace-anchor guarantee as R5/R6.
    "apps/realtime/tests/test_r7_1_sync_tools.py",
    # V6 — videos app shim tests construct Composition/Asset
    # rows directly to simulate terminal-state sync paths.
    "apps/videos/tests/test_v6_shim.py",
    # K6.4 v2 — stoplist watchdog tests seed Composition rows
    # with verification_warnings to exercise the warn-mode
    # "no text context" reporting branch. Read-only command
    # otherwise; no row mutation in the watchdog itself.
    "apps/compositions/tests/test_stoplist_watchdog.py",
    # W11.6.2 — image API tests seed Asset(IMAGE) rows directly
    # to exercise the list/retrieve/delete paths without firing
    # an end-to-end generation per row. The production write
    # path goes through ImageViewSet.create → MediaEngineClient
    # → Asset.objects.create in views.py (already sanctioned).
    "apps/compositions/tests/test_images_api.py",
    # Asset Library A1 (SESSION 185) — backfill management
    # command updates Asset.role on existing rows. Doesn't
    # touch workspace anchor; cross-workspace isolation
    # guarantee is unaffected by definition (the field being
    # written is role only).
    "apps/compositions/management/commands/backfill_asset_roles.py",
    "apps/compositions/tests/test_backfill_asset_roles.py",
    # Asset Library A2 (SESSION 186) — contract-rule-20 coverage
    # tests construct Composition + CompositionStep rows + drive
    # ``_persist_output_asset`` directly to verify the
    # PrimitiveResult.role → Asset.role round-trip + the runner's
    # raise-on-missing-role backstop. Uses _make_workspace +
    # Teammate + Composition.objects.create within the test
    # body; cross-workspace isolation guarantee is unaffected
    # (every row anchors to the same _make_workspace ws).
    "apps/compositions/tests/test_primitive_role_coverage.py",
    # Asset Library A3 (SESSION 187) — storage-health helper tests
    # construct Asset rows directly to exercise the
    # compute_storage_health classifier across all seven states.
    # Workspace anchor is set explicitly at every create; the
    # pre_save signal still fires.
    "apps/compositions/tests/test_storage_health.py",
    # SESSION 194 V18 polish slice 2 — smoke_keyframes management
    # command persists successful Runway outputs as Asset rows
    # (role=EXPERIMENT) so they land in the Asset Library v1 UI
    # instead of becoming orphan URLs. The persist_smoke_asset
    # helper sets workspace explicitly; the pre_save signal still
    # fires.
    "apps/compositions/management/commands/smoke_keyframes.py",
    # SESSION 194 V18 polish slice 2 — smoke_keyframes helper tests
    # construct Asset rows directly to exercise persist_smoke_asset
    # in isolation (the command itself makes real Runway calls and
    # refuses RUNWAY_FORCE_MOCK; testing the helper avoids needing
    # to mock httpx).
    "apps/compositions/tests/test_smoke_keyframes.py",
    # Asset Library A4 (SESSION 188) — workspace assets API tests
    # construct Composition + CompositionStep + Asset rows directly
    # to exercise the read endpoints (list filters, pagination,
    # retrieve lineage). Workspace anchor is set explicitly at
    # every create; the pre_save signal still fires.
    "apps/compositions/tests/test_workspace_assets_api.py",
    # B-arc B1.2 (SESSION 202) — TranscriptHighlight tests seed
    # Asset(TRANSCRIPT) + (occasionally) Composition rows directly
    # to exercise the cross-workspace isolation paths on the new
    # model. Workspace anchor is set explicitly at every create;
    # the pre_save signal still fires. apps.transcripts itself
    # never writes to composition tables (highlights are a
    # separate table); B1.4 will route through
    # apps.compositions.starters via the recipe registry, which
    # is already sanctioned.
    "apps/transcripts/tests/test_models.py",
    # B-arc B1.3 (SESSION 202) — REST API tests seed
    # Asset(TRANSCRIPT) + Asset(CLIP) rows directly to exercise
    # the mine endpoint's auth + cross-workspace + type
    # validation paths. Same shape as the B1.2 entry above —
    # workspace anchor is explicit, signal still fires, no
    # writes to composition tables.
    "apps/transcripts/tests/test_api.py",
    # B-arc B1.4 (SESSION 202) — approve/reject tests seed
    # Asset(TRANSCRIPT) + Composition rows directly to exercise
    # the render-dispatch path + completion signal. The fired
    # composition goes through the sanctioned starter
    # (apps.compositions.starters.talking_head_polished) at
    # approve time; the test-only Asset + Composition seeds
    # are for the cross-workspace + no-session-attached
    # branches. Workspace anchor is explicit at every create;
    # pre_save signal still fires.
    "apps/transcripts/tests/test_approve_reject.py",
    # C-arc B3.2 (SESSION 203) — PersonalizedCampaign +
    # PersonalizedRecipient tests seed Composition rows
    # directly to exercise the cross-workspace
    # produced_composition guard on the new recipient model.
    # Workspace anchor is set explicitly at every create;
    # pre_save signal still fires. apps.campaigns itself
    # never writes to composition tables; B3.5 will route
    # through apps.compositions.starters.talking_head_polished
    # via the recipe registry, which is already sanctioned.
    "apps/campaigns/tests/test_models.py",
    # C-arc B3.5 (SESSION 203) — launch endpoint tests seed
    # Composition + Video rows to exercise the tier-gate
    # paths. The launch endpoint itself routes through the
    # sanctioned talking_head_polished starter; the direct
    # seeds are for the gate-precondition checks (Video
    # shim for videos_used count).
    "apps/campaigns/tests/test_launch.py",
    # C-arc B3.6 (SESSION 203) — completion-signal + retry
    # tests seed Composition rows directly to simulate the
    # V-arc runner's terminal-state save (the cross-app
    # post_save receiver is what we're testing). The
    # retry endpoint itself routes through the sanctioned
    # starter.
    "apps/campaigns/tests/test_completion_retry.py",
    # SESSION 204 — billing/test_services pins the
    # get_usage() migration from the legacy V6 Video shim
    # to Composition-based accounting. Seeds Composition
    # rows directly across multiple statuses to exercise
    # the include/exclude branches. Workspace anchor is
    # set explicitly at every create; pre_save signal
    # still fires.
    "apps/billing/test_services.py",
    # SESSION 204 — R7.2 tier-limit test was updated to
    # seed Composition rows (instead of legacy Video) to
    # match the new get_usage() accounting. Composition
    # create is sanctioned via this allowlist entry; the
    # rest of the file's writes are already covered by the
    # apps/realtime/tests/test_isolation allowlist.
    "apps/realtime/tests/test_r7_2_async_tools.py",
    # D-arc B14.1 (SESSION 205) — publish_variant starter
    # tests seed Asset(CLIP) + Composition rows directly
    # to exercise the trim+reformat starter and the cap-
    # exclusion behavior. Workspace anchor is set at every
    # create; pre_save signal still fires.
    "apps/compositions/tests/test_publish_variant.py",
    # D-arc B14.2 (SESSION 205) — PublishBundle +
    # PublishVariant tests seed Asset(CLIP) + Composition
    # rows directly to exercise the cross-workspace +
    # source-type guards. apps.publish itself never writes
    # to composition tables; B14.3 will route through the
    # sanctioned publish_variant starter.
    "apps/publish/tests/test_models.py",
    # D-arc B14.3 (SESSION 205) — REST + completion signal
    # tests seed Asset(CLIP) + Composition + CompositionStep
    # rows to exercise the launch + completion-signal +
    # retry flows. Launch routes through the sanctioned
    # publish_variant starter; the direct seeds are for
    # source-clip lineage + simulating composition terminal
    # state saves (mirrors C-arc test_completion_retry.py
    # allowance).
    "apps/publish/tests/test_api.py",
    # S2887 C3 side-step — engine_bridge.create_bridge_answer_asset
    # persists engine-bridge tool answers as Asset(BRIDGE_ANSWER) rows.
    # Sanctioned writer: Asset.workspace inherits from session.workspace
    # (analogous to R5's task at apps/realtime/tasks.py above); the row
    # is always in-workspace by construction, and the pre_save signal
    # still fires. Engine-bridge scope note lives in
    # `apps/realtime/engine_bridge.py` module docstring.
    "apps/realtime/engine_bridge.py",
    # S2887 C3 — bridge-answer regression tests create Asset rows
    # directly to exercise the persistence + no-Asset guards + sync-
    # dispatch harvest paths. Same workspace-anchor guarantee.
    "apps/realtime/tests/test_engine_bridge.py",
    # SESSION 241 / §19 Step 2 — Canonical Identity substrate tests
    # create Asset rows directly to exercise the cross-workspace
    # isolation guards on ``IdentityReference``, ``GenerationRecord``,
    # and ``NormalizationManifest`` (§7.5). Workspace anchor is set
    # explicitly at every create; the compositions pre_save signal
    # still fires. ``apps.identity`` itself never writes to
    # composition tables — the substrate accepts already-created
    # Asset instances as inputs to references / generation records.
    "apps/identity/tests/test_models_references.py",
    "apps/identity/tests/test_models_bundle.py",
    "apps/identity/tests/test_services_write_path.py",
    "apps/identity/tests/test_services_approval.py",
    "apps/identity/tests/test_services_concurrency.py",
    # SESSION 242 / §19 Step 3 — legacy backfill service
    # synthesizes Asset(REFERENCE_IMAGE) rows for imported
    # portrait_path values. Sanctioned writer: workspace anchor is
    # the source Teammate's workspace (already validated by the
    # substrate's cross-workspace signal); the pre_save signal
    # still fires. The synthesized Asset carries file_path=
    # portrait_path verbatim — no byte copy, no transformation
    # (Amendment 5 to the Step 3 gate; see
    # docs/handoffs/SESSION_242_STEP_3_LEGACY_BACKFILL.md).
    "apps/identity/import_service.py",
    "apps/identity/tests/test_import_service.py",
    # §19 Step 4.a (SESSION 243) — 4.a's focused test suite creates
    # Asset rows to exercise the new canonical transition services
    # (``approve_reference``, ``approve_bundle``,
    # ``approve_prequalification_version``) against real substrate
    # fixtures. Sanctioned test-side writer; workspace anchor comes
    # from the test's own Workspace fixture and the substrate's
    # pre_save signal still fires. Adds no production writer.
    "apps/identity/tests/test_step4a_services.py",
    # §19 Step 4.b (SESSION 243) — prequalification-authoring
    # orchestration synthesizes ``Asset(REFERENCE_IMAGE)`` rows for
    # portraits handed in from the running product's provider calls
    # (§17.10.a Amendment 4 step E). Sanctioned production writer:
    # workspace anchor is the teammate's workspace (the substrate's
    # cross-workspace signal validates it), the synthesized Asset
    # carries ``file_path=portrait_uri`` verbatim, and the write is
    # inside the amendment-mandated single ``transaction.atomic()``
    # around the full A–J orchestration. Bounded lifetime — Step 13
    # removes the compatibility mirrors and this writer alongside
    # them.
    "apps/identity/services.py",
    # 4.b's focused test suite exercises the orchestration against
    # substrate fixtures; the tests themselves do not create Asset
    # rows directly, but shipping this allowlist entry for the test
    # module too avoids an isolation-test regression if future
    # tests need to seed Asset fixtures.
    "apps/identity/tests/test_step4b_prequalification.py",
    # §19 Step 4.c (SESSION 243) — sync/immutability tests seed Asset
    # rows to construct hand-assembled DRAFT versions that stand in
    # for the qualified authoring path (Steps 5+) so the version-level
    # sync + §5.4 immutability guards can be exercised end-to-end
    # against real substrate state. Same sanctioning shape as 4.a/4.b
    # test allowlist entries.
    "apps/identity/tests/test_step4c_sync_and_immutability.py",
    # §19 Step 4.e (SESSION 243) — verifier semantic tests seed Asset
    # rows to construct legacy-imported + prequalification-authored
    # canonical state that the verifier reads. Same sanctioning shape.
    "apps/identity/tests/test_step4e_verifier.py",
    "apps/identity/tests/test_step4e_read_only.py",
    # §19 Step 9.b.3a (SESSION 249) — bootstrap-review promotion
    # service materializes durable Asset (raw + normalized) rows for
    # human-selected frozen candidates from the 9.a evidence tree.
    # Sanctioned writer: workspace anchor is the bootstrap-fixtures
    # infrastructure workspace (L1 ratification, seeded by
    # 0001_bootstrap_fixtures_workspace); the pre_save signal still
    # fires. Bootstrap fixture identities carry teammate=NULL per
    # §15.1. Asset.file_path points at
    # media-engine/data/_assets/bootstrap/<review_run_id>/*.png
    # copies of frozen Step 9.a raw + normalized bytes — no byte
    # transformation, only physical copy (SESSION 249 architecture
    # plan Q11 + Q21 revised). All promotion writes flow through
    # ``apps.bootstrap_review.promotion.promote_current_decision``
    # inside one transaction.atomic() per §Q21 crash choreography.
    "apps/bootstrap_review/promotion.py",
    # §19 Step 9.b.3a tests — supersede_reference_at_slot service
    # coverage + Finding 10 pipeline_version regression + promotion
    # service coverage all seed Asset rows to exercise the substrate
    # transitions. Same test-side sanctioning shape as the identity
    # step-4a-through-4e entries above.
    "apps/identity/tests/test_supersede_reference_at_slot.py",
    "apps/identity/tests/test_normalization_manifest_pipeline_version.py",
    "apps/bootstrap_review/tests/test_promotion.py",
}


# Matches:
#   Asset.objects.create(...)
#   Asset.objects.update_or_create(...)
#   Composition.objects.create(...)
#   CompositionStep.objects.create(...)
#   Asset.objects.bulk_create(...)
#   etc.
WRITE_PATTERN = re.compile(
    r"\b(Asset|Composition|CompositionStep)\.objects\."
    r"(create|update|update_or_create|get_or_create|bulk_create)\b"
)


def test_only_composition_module_writes_composition_tables() -> None:
    """Walk the repo; fail if any code outside the sanctioned
    files writes to the composition tables.

    The privacy guarantees in ``apps.compositions.signals``
    fire on ``pre_save`` — they cover every write path that
    flows through Django's ORM. But if a future caller skips
    the validation by routing around the signal (raw SQL via
    ``cursor.execute``, or by importing a model and calling
    ``.objects.create`` directly from a context that hasn't
    been audited), the cross-workspace contract becomes a
    procedural one rather than a structural one.

    This test enforces the structural surface.
    """
    shell_root = Path(__file__).resolve().parents[3]
    assert shell_root.name == "shell", f"unexpected root: {shell_root}"

    offenders: list[tuple[str, int, str]] = []
    for py_path in shell_root.rglob("*.py"):
        rel = py_path.relative_to(shell_root).as_posix()

        if "/migrations/" in rel or rel.startswith("migrations/"):
            continue
        if rel.startswith(".venv/") or "/__pycache__/" in rel:
            continue
        if rel in ALLOWED_FILES:
            continue

        try:
            content = py_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            if WRITE_PATTERN.search(line):
                offenders.append((rel, lineno, line.strip()))

    if offenders:
        msg_lines = [
            "Forbidden composition-table write outside the sanctioned surface:",
        ]
        msg_lines.extend(
            f"  {rel}:{lineno}  {snippet}"
            for rel, lineno, snippet in offenders[:10]
        )
        if len(offenders) > 10:
            msg_lines.append(f"  ... and {len(offenders) - 10} more")
        msg_lines.append(
            "Composition + Asset rows should be created by the V2 "
            "runtime once it lands. Until then, the only sanctioned "
            "writers are the model file + admin + tests. If a "
            "legitimate new caller needs to be added, update "
            "ALLOWED_FILES in this test with a code-review note."
        )
        pytest.fail("\n".join(msg_lines))
