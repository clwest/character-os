/**
 * /settings/bootstrap-review — §19 Step 9.b.1 runs index (SESSION 249).
 *
 * Landing surface for the bootstrap human-review workflow. Lists
 * bootstrap runs that 9.b.1 is authorized to browse (currently one
 * — the frozen 9.a real-provider run).
 *
 * Read-only. No decision controls anywhere on this route or the
 * ones it links to. Operator-gated at the backend via IsOperator.
 */
import { Link } from "react-router-dom";
import { AlertCircle, DatabaseZap } from "lucide-react";
import { useBootstrapRuns } from "@/lib/api/bootstrap-review";

export function BootstrapReviewRoute() {
  const { data, isLoading, isError, error } = useBootstrapRuns();

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-6">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          Operator surface · §19 Step 9.b
        </p>
        <h1 className="mt-2 text-2xl font-semibold">Bootstrap review — runs</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Frozen bootstrap runs available for human review. Read-only in
          Step 9.b.1; selections + promotion arrive in 9.b.3 + 9.b.4.
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
          <div>
            Failed to load bootstrap runs: {(error as Error).message}
          </div>
        </div>
      )}

      {data && (
        <ul className="space-y-4">
          {data.runs.map((run) => (
            <li
              key={run.run_id}
              className="rounded-lg border border-border bg-card px-6 py-5"
            >
              <div className="flex items-start gap-4">
                <DatabaseZap className="mt-1 h-5 w-5 text-muted-foreground" />
                <div className="flex-1">
                  <Link
                    to={`/settings/bootstrap-review/${run.run_id}`}
                    className="text-base font-medium text-primary underline underline-offset-4"
                  >
                    {run.run_id}
                  </Link>
                  <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-xs text-muted-foreground sm:grid-cols-2">
                    <div>
                      <dt className="uppercase tracking-wide">Run kind</dt>
                      <dd className="mt-0.5 text-foreground">{run.run_kind}</dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">
                        Qualification status
                      </dt>
                      <dd className="mt-0.5 text-foreground">
                        {run.qualification_status}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">
                        Execution mode
                      </dt>
                      <dd className="mt-0.5 text-foreground">
                        {run.execution_mode.requested ?? "—"}{" "}
                        {run.execution_mode.contains_real_execution
                          ? "· real"
                          : "· mock"}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">Planned cells</dt>
                      <dd className="mt-0.5 text-foreground">
                        {run.counts.planned ?? "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">
                        Real successes
                      </dt>
                      <dd className="mt-0.5 text-foreground">
                        {run.counts.by_outcome.success ?? 0}
                      </dd>
                    </div>
                    <div>
                      <dt className="uppercase tracking-wide">
                        Provider-declined
                      </dt>
                      <dd className="mt-0.5 text-foreground">
                        {run.counts.by_outcome.unsupported_provider_capability ??
                          0}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
