/**
 * /settings/bootstrap-review/:runId/:fixtureId — §19 Step 9.b.1
 * per-fixture purpose list.
 *
 * Shows the seven portrait-reference purposes for one human fixture,
 * each with its reviewable-candidate count + provider-declined
 * evidence count. Every row links to the candidate picker.
 *
 * No promote/finalize controls — 9.b.1 is read-only.
 */
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import {
  HUMAN_PURPOSE_ORDER,
  useApproveFixtureVersion,
  useBootstrapFixture,
  type CanonicalMaterialization,
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

const REQUIRED_PURPOSES = new Set(["front", "neutral_rest"]);

export function BootstrapReviewFixtureRoute() {
  const { runId, fixtureId } = useParams<{
    runId: string;
    fixtureId: string;
  }>();
  const { data, isLoading, isError, error } = useBootstrapFixture(
    runId,
    fixtureId,
  );

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
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
          · {fixtureId}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{fixtureId}</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Portrait-reference purposes for this fixture. Front and
          neutral-rest are required for identity approval; the other
          five extend surface coverage.
        </p>
      </header>

      {isLoading && (
        <div className="rounded-lg border border-border bg-card px-6 py-8 text-sm text-muted-foreground">
          Loading…
        </div>
      )}

      {isError && (
        <div className="flex gap-3 rounded-lg border border-destructive/50 bg-destructive/5 px-6 py-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>Failed to load fixture: {(error as Error).message}</div>
        </div>
      )}

      {data && (
        <>
          <ProgressPanel progress={data.progress} />
          <CanonicalMaterializationTile
            materialization={data.canonical_materialization}
            runId={runId!}
            fixtureId={fixtureId!}
          />
          <ul className="mt-6 divide-y divide-border rounded-lg border border-border bg-card">
            {HUMAN_PURPOSE_ORDER.map((purpose) => {
              const summary = data.purposes.find(
                (p) => p.reference_purpose === purpose,
              );
              return (
                <li
                  key={purpose}
                  className="flex items-center justify-between px-5 py-4"
                  data-testid="purpose-row"
                  data-purpose={purpose}
                  data-status={summary?.review_status ?? "unreviewed"}
                >
                  <div>
                    <Link
                      to={`/settings/bootstrap-review/${runId}/${fixtureId}/portrait_reference/${purpose}`}
                      className="text-sm font-medium text-primary underline underline-offset-4"
                    >
                      {PURPOSE_LABEL[purpose] ?? purpose}
                    </Link>
                    <div className="mt-1 text-xs text-muted-foreground">
                      portrait_reference/{purpose}
                      {REQUIRED_PURPOSES.has(purpose)
                        ? " · required"
                        : " · optional"}
                    </div>
                  </div>
                  <div className="flex gap-6 text-right text-xs text-muted-foreground">
                    <div>
                      <div className="uppercase tracking-wide">Reviewable</div>
                      <div className="mt-0.5 text-base text-foreground">
                        {summary?.reviewable_candidate_count ?? 0}
                      </div>
                    </div>
                    <div>
                      <div className="uppercase tracking-wide">
                        Provider-declined
                      </div>
                      <div className="mt-0.5 text-base text-foreground">
                        {summary?.unsupported_evidence_count ?? 0}
                      </div>
                    </div>
                    <div>
                      <div className="uppercase tracking-wide">Status</div>
                      <div className="mt-0.5 text-base text-foreground">
                        {summary?.review_status ?? "unreviewed"}
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </main>
  );
}

function CanonicalMaterializationTile({
  materialization,
  runId,
  fixtureId,
}: {
  materialization: CanonicalMaterialization;
  runId: string;
  fixtureId: string;
}) {
  const approve = useApproveFixtureVersion();
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      await approve.mutateAsync({ runId, fixtureId });
    } catch (exc) {
      setError((exc as Error).message);
    }
  }

  const floorReady = materialization.canonical_reference_floor_satisfied;
  const versionAdmitted = materialization.canonical_version_admitted;
  const step10Ready = materialization.step10_ready;

  return (
    <section
      aria-labelledby="canonical-heading"
      className="mt-4 rounded-lg border border-border bg-card px-5 py-4"
      data-testid="canonical-materialization-tile"
      data-step10-ready={step10Ready}
      data-version-admitted={versionAdmitted}
      data-floor-satisfied={floorReady}
    >
      <h2
        id="canonical-heading"
        className="text-xs uppercase tracking-wide text-muted-foreground"
      >
        Canonical materialization
      </h2>
      <div className="mt-2 text-2xl font-semibold text-foreground">
        {step10Ready
          ? "Ready for Step 10"
          : versionAdmitted
            ? "Fixture identity admitted"
            : floorReady
              ? "Required references materialized"
              : "Materialization pending"}
      </div>
      <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
        <li>
          Required references materialized: {floorReady ? "yes" : "no"}
        </li>
        <li>
          Publication complete: {materialization.publication_complete ? "yes" : "no"}
        </li>
        <li>
          Fixture identity admitted: {versionAdmitted ? "yes" : "no"}
        </li>
        <li>Evidence integrity: {materialization.evidence_integrity ? "verified" : "drift detected"}</li>
      </ul>
      {floorReady && !versionAdmitted && (
        <button
          type="button"
          onClick={submit}
          disabled={approve.isPending}
          data-testid="admit-fixture-identity"
          className="mt-4 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {approve.isPending ? "Admitting…" : "Admit Fixture Identity"}
        </button>
      )}
      {error && (
        <p
          className="mt-2 text-[11px] text-destructive"
          data-testid="admit-fixture-error"
        >
          {error}
        </p>
      )}
    </section>
  );
}


function ProgressPanel({
  progress,
}: {
  progress: {
    purposes_dispositioned: number;
    purposes_total: number;
    review_complete: boolean;
    approval_floor_pairs: string[];
    approval_floor_satisfied_pairs: string[];
    approval_floor_satisfied: boolean;
  };
}) {
  return (
    <section
      aria-labelledby="progress-heading"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
      data-testid="progress-panel"
    >
      <div
        className="rounded-lg border border-border bg-card px-5 py-4"
        data-testid="progress-review-complete"
        data-value={progress.review_complete}
      >
        <h2
          id="progress-heading"
          className="text-xs uppercase tracking-wide text-muted-foreground"
        >
          Review completeness
        </h2>
        <div className="mt-2 text-2xl font-semibold text-foreground">
          {progress.purposes_dispositioned} of {progress.purposes_total} reviewed
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {progress.review_complete
            ? "All seven purposes have a terminal reviewer disposition."
            : "Some purposes are not yet dispositioned."}
        </div>
      </div>
      <div
        className="rounded-lg border border-border bg-card px-5 py-4"
        data-testid="progress-approval-floor"
        data-value={progress.approval_floor_satisfied}
      >
        <h2 className="text-xs uppercase tracking-wide text-muted-foreground">
          Required references
        </h2>
        <div className="mt-2 text-2xl font-semibold text-foreground">
          {progress.approval_floor_satisfied
            ? "Ready"
            : "Still missing"}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {progress.approval_floor_satisfied_pairs.length} of{" "}
          {progress.approval_floor_pairs.length} required references selected.
        </div>
      </div>
    </section>
  );
}
