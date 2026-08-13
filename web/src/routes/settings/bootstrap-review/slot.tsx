/**
 * /settings/bootstrap-review/:runId/:fixtureId/:kind/:purpose —
 * §19 Step 9.b.2 candidate picker + append-only decisions
 * (SESSION 249).
 *
 * 9.b.1 was read-only. 9.b.2 adds:
 *   * "Select this candidate" per reviewable card
 *   * "No candidate approved this round" as a first-class disposition
 *   * Current-decision banner at the top of the slot
 *   * Amendment flow that requires a non-blank reason
 *   * Expandable decision history (immutable append-only records)
 *
 * NO promotion / approve-version / materialize controls. That's
 * 9.b.3+. NO scoring / ranking / recommendation vocabulary anywhere.
 */
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ChevronDown, ChevronRight, History } from "lucide-react";
import {
  artifactUrl,
  useBootstrapSlot,
  useCreateDecision,
  usePromoteSlot,
  type Candidate,
  type CurrentPromotion,
  type ReviewDecision,
  type UnsupportedGroup,
} from "@/lib/api/bootstrap-review";

const PURPOSE_LABEL: Record<string, string> = {
  front: "Front",
  slight_left: "Slight left",
  slight_right: "Slight right",
  neutral_rest: "Neutral rest",
  listening: "Listening",
  consideration: "Consideration",
  gentle_positive: "Gentle positive",
};

const DISPOSITION_LABEL: Record<string, string> = {
  selected: "Selected",
  no_candidate_approved: "No candidate approved this round",
};

export function BootstrapReviewSlotRoute() {
  const { runId, fixtureId, kind, purpose } = useParams<{
    runId: string;
    fixtureId: string;
    kind: string;
    purpose: string;
  }>();
  const slotQuery = useBootstrapSlot(runId, fixtureId, kind, purpose);
  const createDecision = useCreateDecision();

  const currentDecision = slotQuery.data?.current_decision ?? null;
  const history = slotQuery.data?.decision_history ?? [];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-6">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          <Link
            to="/settings/bootstrap-review"
            className="underline underline-offset-4"
          >
            Bootstrap runs
          </Link>{" "}
          ·{" "}
          <Link
            to={`/settings/bootstrap-review/${runId}`}
            className="underline underline-offset-4"
          >
            {runId}
          </Link>{" "}
          ·{" "}
          <Link
            to={`/settings/bootstrap-review/${runId}/${fixtureId}`}
            className="underline underline-offset-4"
          >
            {fixtureId}
          </Link>{" "}
          · {kind}/{purpose}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">
          {PURPOSE_LABEL[purpose ?? ""] ?? `${kind}/${purpose}`}
        </h1>
      </header>

      {slotQuery.isLoading && (
        <div className="rounded-lg border border-border bg-card px-6 py-8 text-sm text-muted-foreground">
          Loading candidates…
        </div>
      )}

      {slotQuery.isError && (
        <div className="flex gap-3 rounded-lg border border-destructive/50 bg-destructive/5 px-6 py-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>Failed to load slot: {(slotQuery.error as Error).message}</div>
        </div>
      )}

      {slotQuery.data && (
        <>
          <CurrentDecisionBanner
            currentDecision={currentDecision}
            reviewableCandidates={slotQuery.data.reviewable_candidates}
          />

          <PromotionPanel
            currentDecision={currentDecision}
            currentPromotion={slotQuery.data.current_promotion}
            runId={runId!}
            fixtureId={fixtureId!}
            referenceKind={kind!}
            referencePurpose={purpose!}
          />

          <NoCandidateApprovedControl
            runId={runId!}
            fixtureId={fixtureId!}
            referenceKind={kind!}
            referencePurpose={purpose!}
            currentDecision={currentDecision}
            createDecision={createDecision}
          />

          <section
            aria-labelledby="reviewable-heading"
            data-testid="reviewable-section"
            className="mt-8"
          >
            <h2
              id="reviewable-heading"
              className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
            >
              Reviewable candidates ({slotQuery.data.reviewable_candidates.length})
            </h2>
            <ul className="mt-4 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {slotQuery.data.reviewable_candidates.map((candidate) => (
                <li key={candidate.frozen_candidate_id}>
                  <CandidateCard
                    candidate={candidate}
                    runId={runId!}
                    fixtureId={fixtureId!}
                    referenceKind={kind!}
                    referencePurpose={purpose!}
                    currentDecision={currentDecision}
                    createDecision={createDecision}
                  />
                </li>
              ))}
            </ul>
          </section>

          <section
            aria-labelledby="history-heading"
            className="mt-10"
            data-testid="history-section"
          >
            <DecisionHistory history={history} />
          </section>

          <section
            aria-labelledby="unsupported-heading"
            className="mt-10"
            data-testid="unsupported-section"
          >
            <h2
              id="unsupported-heading"
              className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
            >
              Provider-declined evidence ({slotQuery.data.unsupported_evidence.length}{" "}
              cells)
            </h2>
            <p className="mt-2 text-xs text-muted-foreground">
              Evidence of provider capability boundaries — a factual
              record of what the provider was asked to produce and
              declined. Not a reviewer decision. Grouped by
              (provider · error class); every cell remains
              inspectable via its frozen candidate identity.
            </p>
            <ul className="mt-4 space-y-3">
              {slotQuery.data.unsupported_summary.map((group) => (
                <UnsupportedGroupCard
                  key={`${group.provider}::${group.error_class}::${group.error_message}`}
                  group={group}
                />
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------
// Current-decision banner
// ---------------------------------------------------------------------

function CurrentDecisionBanner({
  currentDecision,
  reviewableCandidates,
}: {
  currentDecision: ReviewDecision;
  reviewableCandidates: Candidate[];
}) {
  if (!currentDecision) {
    return (
      <div
        className="rounded-lg border border-dashed border-border bg-card px-5 py-4 text-sm text-muted-foreground"
        data-testid="current-decision-banner"
        data-status="unreviewed"
      >
        This slot has no reviewer disposition yet. Select a candidate below or
        record "No candidate approved this round."
      </div>
    );
  }
  const selectedCandidate = reviewableCandidates.find(
    (c) => c.frozen_candidate_id === currentDecision.frozen_candidate_id,
  );
  return (
    <div
      className="rounded-lg border border-primary/40 bg-primary/5 px-5 py-4 text-sm"
      data-testid="current-decision-banner"
      data-status={currentDecision.disposition}
    >
      <div className="font-medium text-foreground">
        Current: {DISPOSITION_LABEL[currentDecision.disposition]}
        {selectedCandidate && (
          <>
            {" — "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              {selectedCandidate.direction_hypothesis} · {selectedCandidate.surface_profile}
            </code>
          </>
        )}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        Recorded {new Date(currentDecision.decided_at_utc).toLocaleString()} ·
        reviewer #{currentDecision.reviewer_user_id}
        {currentDecision.amendment_reason && (
          <>
            {" · amended: "}
            <span className="italic">{currentDecision.amendment_reason}</span>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------
// No-candidate-approved control
// ---------------------------------------------------------------------

function NoCandidateApprovedControl({
  runId,
  fixtureId,
  referenceKind,
  referencePurpose,
  currentDecision,
  createDecision,
}: {
  runId: string;
  fixtureId: string;
  referenceKind: string;
  referencePurpose: string;
  currentDecision: ReviewDecision;
  createDecision: ReturnType<typeof useCreateDecision>;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const isAmendment = currentDecision !== null;
  const alreadyNoCandidate =
    currentDecision?.disposition === "no_candidate_approved";

  async function submit() {
    setError(null);
    if (isAmendment && !reason.trim()) {
      setError("Amendment reason is required.");
      return;
    }
    try {
      await createDecision.mutateAsync({
        runId,
        fixtureId,
        referenceKind,
        referencePurpose,
        decisionId: crypto.randomUUID(),
        disposition: "no_candidate_approved",
        frozenCandidateId: null,
        supersedesDecisionId: currentDecision?.decision_id ?? null,
        amendmentReason: isAmendment ? reason.trim() : null,
      });
      setReason("");
    } catch (exc) {
      setError((exc as Error).message);
    }
  }

  return (
    <section
      aria-labelledby="no-candidate-heading"
      className="mt-4 rounded-lg border border-border bg-card px-5 py-4"
      data-testid="no-candidate-control"
    >
      <h2
        id="no-candidate-heading"
        className="text-sm font-semibold text-foreground"
      >
        No candidate approved this round
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Explicit human disposition. Not the same as provider capability
        boundaries below.
      </p>
      {isAmendment && (
        <textarea
          data-testid="no-candidate-reason"
          className="mt-3 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Amendment reason (required)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
        />
      )}
      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          data-testid="no-candidate-submit"
          disabled={alreadyNoCandidate || createDecision.isPending}
          onClick={submit}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50"
        >
          {alreadyNoCandidate
            ? "Already recorded"
            : isAmendment
              ? "Record amendment"
              : "Record decision"}
        </button>
        {error && (
          <span className="text-xs text-destructive" data-testid="no-candidate-error">
            {error}
          </span>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------
// Candidate card (Select button integrated per card)
// ---------------------------------------------------------------------

function CandidateCard({
  candidate,
  runId,
  fixtureId,
  referenceKind,
  referencePurpose,
  currentDecision,
  createDecision,
}: {
  candidate: Candidate;
  runId: string;
  fixtureId: string;
  referenceKind: string;
  referencePurpose: string;
  currentDecision: ReviewDecision;
  createDecision: ReturnType<typeof useCreateDecision>;
}) {
  const [rawShown, setRawShown] = useState(false);
  const [manifestShown, setManifestShown] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const normalizedSrc = artifactUrl(
    candidate.frozen_candidate_id,
    "normalized.png",
  );
  const rawSrc = artifactUrl(candidate.frozen_candidate_id, "raw.png");

  const isCurrentlySelected =
    currentDecision?.disposition === "selected" &&
    currentDecision.frozen_candidate_id === candidate.frozen_candidate_id;
  const isAmendment = currentDecision !== null;

  async function submit() {
    setError(null);
    if (isCurrentlySelected) return;
    if (isAmendment && !reason.trim()) {
      setError("Amendment reason is required.");
      return;
    }
    try {
      await createDecision.mutateAsync({
        runId,
        fixtureId,
        referenceKind,
        referencePurpose,
        decisionId: crypto.randomUUID(),
        disposition: "selected",
        frozenCandidateId: candidate.frozen_candidate_id,
        supersedesDecisionId: currentDecision?.decision_id ?? null,
        amendmentReason: isAmendment ? reason.trim() : null,
      });
      setReason("");
    } catch (exc) {
      setError((exc as Error).message);
    }
  }

  return (
    <article
      className={`rounded-lg border p-4 ${
        isCurrentlySelected
          ? "border-primary bg-primary/5"
          : "border-border bg-card"
      }`}
      data-testid="candidate-card"
      data-fcid={candidate.frozen_candidate_id}
      data-selected={isCurrentlySelected}
    >
      <img
        src={normalizedSrc}
        alt={`Normalized ${candidate.direction_hypothesis} ${candidate.surface_profile}`}
        className="aspect-square w-full rounded-md bg-muted object-cover"
        data-testid="normalized-image"
      />
      {rawShown && (
        <img
          src={rawSrc}
          alt={`Raw ${candidate.direction_hypothesis} ${candidate.surface_profile}`}
          className="mt-3 aspect-square w-full rounded-md bg-muted object-cover"
          data-testid="raw-image"
        />
      )}

      <dl className="mt-3 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        <dt className="uppercase tracking-wide">Direction</dt>
        <dd className="text-foreground">{candidate.direction_hypothesis}</dd>
        <dt className="uppercase tracking-wide">Surface profile</dt>
        <dd className="text-foreground">{candidate.surface_profile}</dd>
        <dt className="uppercase tracking-wide">Provider</dt>
        <dd className="text-foreground">
          {candidate.provider} ({candidate.provider_stage.provider_model})
        </dd>
        <dt className="uppercase tracking-wide">Elapsed</dt>
        <dd className="text-foreground">
          {candidate.provider_stage.elapsed_ms ?? "—"} ms
        </dd>
      </dl>

      {candidate.factual_normalization_notices.length > 0 && (
        <ul
          className="mt-3 space-y-1 text-[11px] text-amber-700 dark:text-amber-300"
          data-testid="normalization-notices"
        >
          {candidate.factual_normalization_notices.map((notice, i) => (
            <li key={i}>· {notice}</li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setRawShown((v) => !v)}
          className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-muted"
          data-testid="toggle-raw"
        >
          {rawShown ? "Hide raw" : "Show raw"}
        </button>
        <button
          type="button"
          onClick={() => setManifestShown((v) => !v)}
          className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-muted"
          data-testid="toggle-manifest"
        >
          {manifestShown ? "Hide manifest" : "Show manifest"}
          {manifestShown ? (
            <ChevronDown className="ml-1 inline h-3 w-3" />
          ) : (
            <ChevronRight className="ml-1 inline h-3 w-3" />
          )}
        </button>
      </div>

      {manifestShown && <ManifestPanel candidate={candidate} />}

      {/* 9.b.2 — Select button + amendment reason input. */}
      <div className="mt-4 border-t border-border pt-3">
        {isAmendment && !isCurrentlySelected && (
          <textarea
            data-testid="select-reason"
            className="mb-2 w-full rounded-md border border-border bg-background px-3 py-2 text-xs"
            placeholder="Amendment reason (required)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
          />
        )}
        <button
          type="button"
          onClick={submit}
          disabled={isCurrentlySelected || createDecision.isPending}
          data-testid="select-candidate"
          className="w-full rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isCurrentlySelected
            ? "Currently selected"
            : isAmendment
              ? "Amend to this candidate"
              : "Select this candidate"}
        </button>
        {error && (
          <p
            className="mt-2 text-[11px] text-destructive"
            data-testid="select-error"
          >
            {error}
          </p>
        )}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------
// Manifest panel + unsupported group + history — same shape as 9.b.1
// ---------------------------------------------------------------------

function ManifestPanel({ candidate }: { candidate: Candidate }) {
  return (
    <div
      className="mt-3 rounded-md border border-border bg-muted/50 p-3 text-[11px]"
      data-testid="manifest-panel"
    >
      <dl className="grid grid-cols-2 gap-1">
        <dt className="uppercase tracking-wide text-muted-foreground">
          Pipeline
        </dt>
        <dd className="break-all text-foreground">
          {candidate.normalization_stage.pipeline_version ?? "—"}
        </dd>
        <dt className="uppercase tracking-wide text-muted-foreground">
          Background
        </dt>
        <dd className="text-foreground">
          {candidate.normalization_stage.background_id ?? "—"}
        </dd>
        <dt className="uppercase tracking-wide text-muted-foreground">
          Raw sha256
        </dt>
        <dd className="break-all font-mono text-foreground">
          {candidate.raw_artifact?.sha256_hex ?? "—"}
        </dd>
        <dt className="uppercase tracking-wide text-muted-foreground">
          Normalized sha256
        </dt>
        <dd className="break-all font-mono text-foreground">
          {candidate.normalized_artifact?.sha256_hex ?? "—"}
        </dd>
      </dl>
      <p className="mt-2 text-[10px] text-muted-foreground">
        Full manifest JSON:{" "}
        <a
          href={artifactUrl(candidate.frozen_candidate_id, "manifest.json")}
          className="underline underline-offset-2"
          target="_blank"
          rel="noreferrer"
        >
          open ↗
        </a>
      </p>
    </div>
  );
}

function UnsupportedGroupCard({ group }: { group: UnsupportedGroup }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li
      className="rounded-md border border-border bg-card px-4 py-3 text-xs"
      data-testid="unsupported-group"
      data-provider={group.provider}
      data-error-class={group.error_class}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start justify-between text-left"
      >
        <div>
          <div className="font-medium text-foreground">
            {group.provider} · {group.error_class} ({group.count} cell
            {group.count === 1 ? "" : "s"})
          </div>
          <div className="mt-1 text-muted-foreground">
            {group.error_message}
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        )}
      </button>
      {expanded && (
        <ul className="mt-3 space-y-1 text-[11px] text-muted-foreground">
          {group.members.map((member) => (
            <li key={member.frozen_candidate_id}>
              <span className="text-foreground">
                {member.direction} · {member.surface_profile}
              </span>{" "}
              <span className="font-mono text-[10px]">
                ({member.frozen_candidate_id.slice(-40)}…)
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------
// Promotion panel (9.b.3b)
// ---------------------------------------------------------------------

function PromotionPanel({
  currentDecision,
  currentPromotion,
  runId,
  fixtureId,
  referenceKind,
  referencePurpose,
}: {
  currentDecision: ReviewDecision;
  currentPromotion: CurrentPromotion;
  runId: string;
  fixtureId: string;
  referenceKind: string;
  referencePurpose: string;
}) {
  const promote = usePromoteSlot();
  const [error, setError] = useState<string | null>(null);

  if (!currentDecision) return null;
  if (currentDecision.disposition !== "selected") {
    // no_candidate_approved is journal-driven; nothing operator-visible
    // to promote at 9.b.3b.
    return null;
  }

  async function submit() {
    setError(null);
    try {
      await promote.mutateAsync({
        runId,
        fixtureId,
        referenceKind,
        referencePurpose,
      });
    } catch (exc) {
      setError((exc as Error).message);
    }
  }

  // Published — show revision state.
  if (currentPromotion && currentPromotion.publication_status === "published") {
    return (
      <section
        aria-labelledby="promotion-heading"
        className="mt-4 rounded-lg border border-primary/40 bg-primary/5 px-5 py-4"
        data-testid="promotion-panel"
        data-status="published"
      >
        <h2
          id="promotion-heading"
          className="text-sm font-semibold text-foreground"
        >
          Published Revision {String(currentPromotion.slot_revision).padStart(3, "0")}
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Canonical bootstrap reference written to{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-[10px]">
            fixtures/{fixtureId}/bootstrap/references/{referenceKind}/
            {referencePurpose}/
            {String(currentPromotion.slot_revision).padStart(3, "0")}/
          </code>
        </p>
      </section>
    );
  }

  // Publication pending (post-Phase-4 crash recovery required).
  if (
    currentPromotion &&
    currentPromotion.publication_status === "publication_pending"
  ) {
    return (
      <section
        aria-labelledby="promotion-heading"
        className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/5 px-5 py-4"
        data-testid="promotion-panel"
        data-status="publication_pending"
      >
        <h2
          id="promotion-heading"
          className="text-sm font-semibold text-foreground"
        >
          Publication recovery required
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          The canonical substrate rows committed for this reference,
          but the filesystem revision folder did not publish. Retry
          promotion to finish publication — idempotent via the existing
          PromotionAudit row (no duplicate substrate writes).
        </p>
        <button
          type="button"
          onClick={submit}
          disabled={promote.isPending}
          data-testid="retry-publication"
          className="mt-3 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50"
        >
          {promote.isPending ? "Retrying…" : "Retry publication"}
        </button>
        {error && (
          <p className="mt-2 text-[11px] text-destructive" data-testid="promotion-error">
            {error}
          </p>
        )}
      </section>
    );
  }

  // Not yet promoted — offer Promote.
  return (
    <section
      aria-labelledby="promotion-heading"
      className="mt-4 rounded-lg border border-border bg-card px-5 py-4"
      data-testid="promotion-panel"
      data-status="not_promoted"
    >
      <h2
        id="promotion-heading"
        className="text-sm font-semibold text-foreground"
      >
        Ready to promote
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Materializes canonical Assets + GenerationRecord + NormalizationManifest
        + IdentityReference, then publishes an immutable revision folder under
        bootstrap/references/.
      </p>
      <button
        type="button"
        onClick={submit}
        disabled={promote.isPending}
        data-testid="promote-to-reference"
        className="mt-3 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {promote.isPending ? "Promoting…" : "Promote to Bootstrap Reference"}
      </button>
      {error && (
        <p className="mt-2 text-[11px] text-destructive" data-testid="promotion-error">
          {error}
        </p>
      )}
    </section>
  );
}


function DecisionHistory({ history }: { history: ReviewDecision[] }) {
  const [expanded, setExpanded] = useState(false);
  const relevant = useMemo(
    () => history.filter((d): d is NonNullable<ReviewDecision> => d !== null),
    [history],
  );
  if (relevant.length === 0) return null;
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground"
        data-testid="history-toggle"
      >
        <History className="h-3.5 w-3.5" />
        Decision history ({relevant.length})
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>
      {expanded && (
        <ol
          className="mt-3 space-y-2 text-xs"
          data-testid="history-list"
        >
          {relevant.map((decision, index) => (
            <li
              key={decision.decision_id}
              className="rounded-md border border-border bg-card px-3 py-2"
              data-testid="history-entry"
            >
              <div className="font-medium text-foreground">
                Revision {index + 1}: {DISPOSITION_LABEL[decision.disposition]}
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                {new Date(decision.decided_at_utc).toLocaleString()} · reviewer
                #{decision.reviewer_user_id}
              </div>
              {decision.frozen_candidate_id && (
                <div
                  className="mt-1 truncate font-mono text-[10px] text-muted-foreground"
                  title={decision.frozen_candidate_id}
                >
                  {decision.frozen_candidate_id}
                </div>
              )}
              {decision.amendment_reason && (
                <div className="mt-1 text-[11px] italic text-muted-foreground">
                  Reason: {decision.amendment_reason}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
