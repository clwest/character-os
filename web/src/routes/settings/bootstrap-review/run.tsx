/**
 * /settings/bootstrap-review/:runId — §19 Step 9.b.1 fixture list.
 *
 * For the authorized bootstrap run, lists the four human fixtures
 * with a brief summary; each links to the fixture review page.
 */
import { Link, useParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { useBootstrapRun } from "@/lib/api/bootstrap-review";

export function BootstrapReviewRunRoute() {
  const { runId } = useParams<{ runId: string }>();
  const { data, isLoading, isError, error } = useBootstrapRun(runId);

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
          · {runId}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">Fixtures</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Select a fixture to review its seven portrait-reference
          purposes. fixture_nh1 (non-human substrate exercise) is
          intentionally excluded from human review.
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
            Failed to load run: {(error as Error).message}
          </div>
        </div>
      )}

      {data && (
        <ul className="grid gap-4 sm:grid-cols-2">
          {data.fixtures.map((fixture) => (
            <li
              key={fixture.fixture_id}
              className="rounded-lg border border-border bg-card px-5 py-4"
            >
              <Link
                to={`/settings/bootstrap-review/${runId}/${fixture.fixture_id}`}
                className="text-base font-medium text-primary underline underline-offset-4"
              >
                {fixture.fixture_id}
              </Link>
              <dl className="mt-3 space-y-1 text-xs text-muted-foreground">
                <div>
                  <dt className="uppercase tracking-wide">Branch</dt>
                  <dd className="text-foreground">{fixture.branch}</dd>
                </div>
                <div>
                  <dt className="uppercase tracking-wide">Content hash</dt>
                  <dd className="font-mono text-[11px] text-foreground">
                    {fixture.content_hash.slice(0, 16)}…
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
