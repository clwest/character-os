/**
 * /workspace/campaigns/:id — Campaign detail + CSV paste + launch + grid.
 *
 * SESSION B3.7 (metadata + CSV paste).
 * SESSION B3.8 (launch modal + forecast panel + recipient grid + retry).
 *
 * Shows different affordances based on campaign.status:
 *   DRAFT — CSV paste panel + forecast panel + Launch button.
 *   LAUNCHING / IN_FLIGHT — recipient progress grid (polling every 5s).
 *   COMPLETED / PARTIAL / FAILED — grid with retry buttons on FAILED rows.
 *
 * Scope: docs/design/PERSONALIZED_VIDEO_V1.md §B3.7-B3.8.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  Trash2,
  X,
  RefreshCw,
  BookOpen,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  useCampaign,
  useParseCsv,
  useDeleteCampaign,
  useCampaignForecast,
  useLaunchCampaign,
  useRetryRecipient,
  useRecipients,
  campaignStatusTone,
  campaignStatusLabel,
  recipientStatusTone,
  blockingReasonMessage,
  type PersonalizedCampaign,
  type PersonalizedRecipient,
  type ParseCsvResponse,
  type CampaignStatus,
  type SourceScriptBlock,
} from "@/lib/api/campaigns";
import {
  verificationStatusTone,
  verificationStatusLabel,
} from "@/lib/api/scripts";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- SourceScriptPanel (BC4) --------------------------------

/**
 * Renders a compact "Derived from script" header block when
 * campaign.source_script is non-null. Positioned between the
 * page header (CampaignMetadataPanel) and the template/CSV panels.
 *
 * Contract rule 2 honored: the tooltip notes the FK is audit trail,
 * not a constraint on the template.
 */
function SourceScriptPanel({ sourceScript }: { sourceScript: SourceScriptBlock }) {
  const vTone = verificationStatusTone(sourceScript.verification_status as Parameters<typeof verificationStatusTone>[0]);
  const vLabel = verificationStatusLabel(sourceScript.verification_status as Parameters<typeof verificationStatusLabel>[0]);

  return (
    <section
      data-testid="source-script-panel"
      className="rounded-md border border-border bg-muted/20 p-4 flex items-center gap-3 flex-wrap text-sm"
    >
      <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="text-muted-foreground">Derived from script</span>
      <Link
        to={`/workspace/scripts/${sourceScript.id}`}
        data-testid="source-script-link"
        className="font-medium text-primary hover:underline underline-offset-2"
      >
        {sourceScript.name}
      </Link>
      {sourceScript.verification_status !== "" && (
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
            vTone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-400",
            vTone === "success" && "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
            vTone === "muted" && "border-border bg-muted text-muted-foreground",
            vTone === "danger" && "border-destructive/40 bg-destructive/10 text-destructive",
          )}
        >
          {vLabel}
        </span>
      )}
      <span
        data-testid="source-script-chunk-count"
        className="text-xs text-muted-foreground"
      >
        {sourceScript.chunk_count} chunk{sourceScript.chunk_count !== 1 ? "s" : ""}
      </span>
      {/* Rule 2 tooltip — audit trail annotation */}
      <span
        title="Audit trail only — template is editable after derivation (rule 2)"
        className="ml-auto text-[10px] text-muted-foreground cursor-help border-b border-dashed border-muted-foreground/40"
      >
        audit trail only
      </span>
    </section>
  );
}

// ---- Page component -----------------------------------------

/** Statuses that require the recipient grid (active + terminal). */
const GRID_STATUSES = new Set<CampaignStatus>([
  "launching",
  "in_flight",
  "completed",
  "partial",
  "failed",
]);

export function CampaignDetailRoute() {
  const { id } = useParams<{ id: string }>();
  // useCampaign now self-polls every 5 s when status is
  // launching / in_flight and stops on terminal state.
  const campaign = useCampaign(id);

  if (campaign.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <LoadingSkeleton />
      </div>
    );
  }

  if (campaign.isError) {
    const err = campaign.error as { status?: number; message?: string } | null;
    const is404 = err?.status === 404;
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        {is404 ? (
          <NotFound />
        ) : (
          <ErrorPanel
            message={err?.message ?? "Failed to load campaign."}
            onRetry={() => campaign.refetch()}
          />
        )}
      </div>
    );
  }

  if (!campaign.data) return null;

  const c = campaign.data;
  const isDraft = c.status === "draft";
  const showGrid = GRID_STATUSES.has(c.status);
  const isTerminal =
    c.status === "completed" || c.status === "partial" || c.status === "failed";

  return (
    <div
      data-testid="campaign-detail"
      className="flex flex-col gap-8 max-w-3xl"
    >
      <BackLink />
      <CampaignMetadataPanel campaign={c} />

      {/* BC4: source_script header block — shown when campaign derives from a Script */}
      {c.source_script != null && (
        <SourceScriptPanel sourceScript={c.source_script} />
      )}

      {/* Terminal status banner */}
      {isTerminal && <TerminalBanner campaign={c} />}

      {/* DRAFT: CSV paste + forecast + launch */}
      {isDraft && id && (
        <>
          <CsvPanel campaignId={id} campaign={c} />
          <ForecastPanel campaignId={id} campaign={c} />
        </>
      )}

      {/* Active + terminal: recipient progress grid */}
      {showGrid && id && (
        <RecipientGrid
          campaignId={id}
          campaign={c}
          refetchCampaign={() => void campaign.refetch()}
        />
      )}
    </div>
  );
}

// ---- CampaignMetadataPanel ----------------------------------

function CampaignMetadataPanel({ campaign }: { campaign: PersonalizedCampaign }) {
  const navigate = useNavigate();
  const deleteMutation = useDeleteCampaign();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const tone = campaignStatusTone(campaign.status);
  const label = campaignStatusLabel(campaign.status);
  const isDraft = campaign.status === "draft";

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleteError(null);
    try {
      await deleteMutation.mutateAsync(campaign.id);
      navigate("/workspace/campaigns");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? String(
              (err.body as Record<string, unknown> | null)?.detail ??
                err.message,
            )
          : err instanceof Error
            ? err.message
            : "Delete failed.";
      setDeleteError(msg);
      setConfirmDelete(false);
    }
  }

  return (
    <section
      data-testid="campaign-metadata"
      className="rounded-md border border-border bg-card p-6 flex flex-col gap-5"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h1
            data-testid="campaign-detail-name"
            className="font-display text-3xl leading-tight tracking-tight"
          >
            {campaign.name}
          </h1>
          <p className="text-sm text-muted-foreground">
            Spokesperson: <strong>{campaign.spokesperson_name}</strong>
          </p>
        </div>
        <StatusBadge tone={tone} label={label} />
      </div>

      {/* Recipient count summary */}
      <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
        <span>
          <strong className="text-foreground">{campaign.recipient_counts.total}</strong> recipients
        </span>
        {campaign.recipient_counts.pending > 0 && (
          <span>{campaign.recipient_counts.pending} pending</span>
        )}
        {campaign.recipient_counts.completed > 0 && (
          <span className="text-emerald-400">
            {campaign.recipient_counts.completed} completed
          </span>
        )}
        {campaign.recipient_counts.failed > 0 && (
          <span className="text-destructive">
            {campaign.recipient_counts.failed} failed
          </span>
        )}
      </div>

      {/* Placeholders */}
      {campaign.placeholders.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Template variables
          </p>
          <div className="flex flex-wrap gap-1.5">
            {campaign.placeholders.map((p) => (
              <span
                key={p}
                data-testid={`placeholder-chip-${p}`}
                className="inline-flex items-center rounded-sm border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                {"{"}
                {p}
                {"}"}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Template preview */}
      <div className="flex flex-col gap-1.5">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Script template
        </p>
        <pre
          data-testid="campaign-template-preview"
          className="whitespace-pre-wrap font-mono text-xs leading-relaxed border border-border rounded-md bg-muted/30 p-3 max-h-40 overflow-y-auto"
        >
          {campaign.template}
        </pre>
      </div>

      {/* Delete campaign — DRAFT-only */}
      {isDraft && (
        <div className="flex flex-col gap-2 pt-2 border-t border-border">
          {deleteError && (
            <p
              data-testid="delete-campaign-error"
              className="text-xs text-destructive"
            >
              {deleteError}
            </p>
          )}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              data-testid="delete-campaign-btn"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
              className="h-8 px-3 text-xs gap-1.5"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="h-3 w-3" />
                  {confirmDelete ? "Confirm delete" : "Delete campaign"}
                </>
              )}
            </Button>
            {confirmDelete && !deleteMutation.isPending && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-3 text-xs"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            )}
            {confirmDelete && (
              <p className="text-xs text-muted-foreground">
                This will permanently delete the campaign and all recipients.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ---- CsvPanel -----------------------------------------------

function CsvPanel({
  campaignId,
  campaign,
}: {
  campaignId: string;
  campaign: PersonalizedCampaign;
}) {
  const [csvText, setCsvText] = useState("");
  const [parseResult, setParseResult] = useState<ParseCsvResponse | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const parseCsv = useParseCsv(campaignId);

  const isDraft = campaign.status === "draft";
  const hasRecipients = campaign.recipient_counts.total > 0;

  async function handleParse(e: React.FormEvent) {
    e.preventDefault();
    setParseError(null);
    setParseResult(null);
    try {
      const result = await parseCsv.mutateAsync(csvText);
      setParseResult(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        const body = err.body as Record<string, unknown> | null;
        // header_error 400 — the backend may return the shape as-is
        // (parseCsvResponseSchema is tolerant).
        const headerErr = body?.header_error as string | undefined;
        if (headerErr) {
          setParseResult(body as unknown as ParseCsvResponse);
        } else {
          const detail = body?.detail != null ? String(body.detail) : null;
          const csvErr = body?.csv_text != null
            ? String(Array.isArray(body.csv_text) ? body.csv_text[0] : body.csv_text)
            : null;
          setParseError(
            csvErr ?? detail ?? "Parse failed — check your CSV and try again.",
          );
        }
      } else {
        setParseError(
          err instanceof Error ? err.message : "An unexpected error occurred.",
        );
      }
    }
  }

  if (!isDraft) {
    return (
      <section
        data-testid="csv-panel-locked"
        className="rounded-md border border-border bg-card p-6 flex flex-col gap-3"
      >
        <h2 className="font-display text-xl tracking-tight">Recipients</h2>
        <p className="text-sm text-muted-foreground">
          This campaign is{" "}
          <strong>{campaignStatusLabel(campaign.status)}</strong> — recipients
          are locked after launch.
        </p>
        <p className="text-sm text-muted-foreground">
          {campaign.recipient_counts.total} recipient
          {campaign.recipient_counts.total !== 1 ? "s" : ""} in this campaign.
        </p>
      </section>
    );
  }

  return (
    <section
      data-testid="csv-panel"
      className="rounded-md border border-border bg-card p-6 flex flex-col gap-5"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-xl tracking-tight">
          {hasRecipients ? "Re-paste CSV" : "Paste recipients CSV"}
        </h2>
        <p className="text-sm text-muted-foreground">
          Header row must include:{" "}
          {campaign.placeholders.length > 0 ? (
            campaign.placeholders.map((p, i) => (
              <span key={p}>
                {i > 0 && ", "}
                <code className="font-mono text-[11px]">{p}</code>
              </span>
            ))
          ) : (
            <span>no placeholders detected yet</span>
          )}
          . Each subsequent row is one recipient. Pasting replaces all
          existing recipients.
        </p>
      </div>

      <form
        data-testid="csv-paste-form"
        onSubmit={(e) => void handleParse(e)}
        className="flex flex-col gap-3"
      >
        <textarea
          id="csv-text"
          data-testid="csv-textarea"
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          rows={8}
          placeholder={`first_name,company,milestone\nAlice,Acme,Series B\nBob,Globex,1M ARR`}
          disabled={parseCsv.isPending}
          className={cn(
            "w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs",
            "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
            "resize-y disabled:cursor-not-allowed disabled:opacity-50",
          )}
        />
        <Button
          type="submit"
          data-testid="parse-csv-btn"
          disabled={parseCsv.isPending || csvText.trim().length === 0}
        >
          {parseCsv.isPending ? (
            <>
              <Loader2
                data-testid="parse-csv-spinner"
                className="mr-2 h-4 w-4 animate-spin"
              />
              Parsing…
            </>
          ) : hasRecipients ? (
            "Re-parse CSV"
          ) : (
            "Parse CSV"
          )}
        </Button>
      </form>

      {/* Inline general error */}
      {parseError && (
        <div
          data-testid="parse-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{parseError}</p>
        </div>
      )}

      {/* Parse result */}
      {parseResult && <ParseResultPanel result={parseResult} />}
    </section>
  );
}

// ---- ParseResultPanel ---------------------------------------

function ParseResultPanel({ result }: { result: ParseCsvResponse }) {
  const [rejectedOpen, setRejectedOpen] = useState(false);

  // Header-level error (backend returned 400 with header_error).
  if (result.header_error) {
    return (
      <div
        data-testid="parse-header-error"
        className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4"
      >
        <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-destructive">
            CSV header error
          </p>
          <p className="text-sm text-destructive">{result.header_error}</p>
          <p className="text-xs text-destructive/80 mt-1">
            Fix your CSV header and paste again. No recipients were saved.
          </p>
        </div>
      </div>
    );
  }

  const recipients = result.recipients ?? [];

  return (
    <div
      data-testid="parse-result"
      className="flex flex-col gap-4"
    >
      {/* Summary badges */}
      <div className="flex flex-wrap items-center gap-3">
        <span
          data-testid="valid-count-badge"
          className="inline-flex items-center rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400"
        >
          {result.valid_count} valid
        </span>
        {result.rejected_count > 0 && (
          <button
            type="button"
            data-testid="rejected-count-badge"
            onClick={() => setRejectedOpen((o) => !o)}
            className="inline-flex items-center gap-1 rounded-sm border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400"
          >
            {result.rejected_count} rejected
            {rejectedOpen ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </button>
        )}
      </div>

      {/* Rejected rows expandable */}
      {rejectedOpen && result.rejected_rows.length > 0 && (
        <div
          data-testid="rejected-rows-section"
          className="rounded-md border border-amber-500/30 bg-amber-500/5 p-4 flex flex-col gap-2"
        >
          <p className="text-xs font-medium text-amber-400 uppercase tracking-wider">
            Rejected rows
          </p>
          <ul className="flex flex-col gap-2">
            {result.rejected_rows.map((row) => (
              <li
                key={row.row_number}
                data-testid={`rejected-row-${row.row_number}`}
                className="flex flex-col gap-0.5"
              >
                <span className="text-xs font-medium text-amber-400">
                  Row {row.row_number}
                </span>
                <span className="text-xs text-amber-300/80">{row.error}</span>
                {row.raw && (
                  <code className="text-[10px] font-mono text-muted-foreground">
                    {row.raw.slice(0, 120)}
                    {row.raw.length > 120 ? "…" : ""}
                  </code>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Valid recipients preview table */}
      {recipients.length > 0 && (
        <div
          data-testid="recipients-preview"
          className="flex flex-col gap-2"
        >
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Recipients ({recipients.length})
          </p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-xs">
              <thead className="border-b border-border bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                    Label
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                    Variables
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recipients.slice(0, 20).map((r) => (
                  <RecipientPreviewRow key={r.id} recipient={r} />
                ))}
              </tbody>
            </table>
            {recipients.length > 20 && (
              <p className="px-3 py-2 text-xs text-muted-foreground border-t border-border">
                … and {recipients.length - 20} more
              </p>
            )}
          </div>
        </div>
      )}

      {result.valid_count === 0 && result.rejected_count === 0 && (
        <p
          data-testid="parse-no-rows"
          className="text-sm text-muted-foreground"
        >
          No rows found. Make sure your CSV includes a header row and at
          least one data row.
        </p>
      )}
    </div>
  );
}

// ---- RecipientPreviewRow ------------------------------------

function RecipientPreviewRow({
  recipient,
}: {
  recipient: PersonalizedRecipient;
}) {
  return (
    <tr
      data-testid={`recipient-preview-row-${recipient.id}`}
      className="hover:bg-muted/20 transition-colors"
    >
      <td className="px-3 py-2 font-medium">{recipient.label}</td>
      <td className="px-3 py-2 font-mono text-muted-foreground">
        {Object.entries(recipient.variables)
          .slice(0, 4)
          .map(([k, v]) => `${k}=${String(v).slice(0, 20)}`)
          .join(", ")}
        {Object.keys(recipient.variables).length > 4 ? "…" : ""}
      </td>
    </tr>
  );
}

// ---- ForecastPanel (B3.8) -----------------------------------

function ForecastPanel({
  campaignId,
  campaign,
}: {
  campaignId: string;
  campaign: PersonalizedCampaign;
}) {
  const forecast = useCampaignForecast(campaignId);
  const launch = useLaunchCampaign(campaignId);
  const [modalOpen, setModalOpen] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launched, setLaunched] = useState(false);
  const [launchResult, setLaunchResult] = useState<{
    queued_count: number;
    failed_at_render_count: number;
  } | null>(null);

  const f = forecast.data;
  const hasRecipients = campaign.recipient_counts.total > 0;

  // Per-recipient cost is $0.25 (PER_RECIPIENT_COST_MICROS=250_000).
  const costDollars = f
    ? (f.projected_cost_micros / 1_000_000).toFixed(2)
    : null;

  async function handleLaunchConfirm() {
    setLaunchError(null);
    try {
      const result = await launch.mutateAsync();
      setLaunchResult({
        queued_count: result.queued_count,
        failed_at_render_count: result.failed_at_render_count,
      });
      setLaunched(true);
      setModalOpen(false);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 402 || err.status === 400)) {
        const body = err.body as Record<string, unknown> | null;
        // Structured 402 payload: { code, message } or { detail }.
        const msg =
          typeof body?.message === "string"
            ? body.message
            : typeof body?.detail === "string"
              ? body.detail
              : "Launch failed — check your tier limits and try again.";
        setLaunchError(msg);
      } else {
        setLaunchError(
          err instanceof Error ? err.message : "An unexpected error occurred.",
        );
      }
      setModalOpen(false);
    }
  }

  if (!hasRecipients) {
    // No recipients yet — forecast panel is not yet useful.
    return null;
  }

  return (
    <section
      data-testid="forecast-panel"
      className="rounded-md border border-border bg-card p-6 flex flex-col gap-4"
    >
      <h2 className="font-display text-xl tracking-tight">Launch</h2>

      {/* Cost preview */}
      {forecast.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Calculating cost…
        </div>
      )}
      {f && (
        <div
          data-testid="forecast-summary"
          className="flex flex-col gap-2 text-sm"
        >
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
            <span>
              <strong className="text-foreground">{f.recipient_count}</strong> recipient
              {f.recipient_count !== 1 ? "s" : ""}
            </span>
            <span>
              $0.25 each → <strong className="text-foreground">${costDollars}</strong> total
            </span>
            {f.batch_cap !== null && (
              <span
                data-testid="batch-cap-badge"
                className={cn(
                  "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium",
                  f.recipient_count > f.batch_cap
                    ? "border-destructive/40 bg-destructive/10 text-destructive"
                    : "border-border bg-muted text-muted-foreground",
                )}
              >
                batch cap: {f.batch_cap}
              </span>
            )}
            {f.videos_remaining !== null && (
              <span
                data-testid="videos-remaining-badge"
                className={cn(
                  "text-xs",
                  f.videos_remaining < f.recipient_count
                    ? "text-destructive"
                    : "text-muted-foreground",
                )}
              >
                {f.videos_remaining} video
                {f.videos_remaining !== 1 ? "s" : ""} left this month
              </span>
            )}
          </div>

          {/* Blocking reason */}
          {!f.ready_to_launch && f.blocking_reason && (
            <div
              data-testid="blocking-reason"
              className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
              <p className="text-sm text-amber-300">
                {blockingReasonMessage(f.blocking_reason.code)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Launch error (after 402 etc.) */}
      {launchError && (
        <div
          data-testid="launch-error"
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
          <p className="text-sm text-destructive">{launchError}</p>
        </div>
      )}

      {/* Post-launch success notice */}
      {launched && launchResult && (
        <div
          data-testid="launch-success-banner"
          className="flex items-start gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3"
        >
          <p className="text-sm text-emerald-400">
            {launchResult.queued_count} render
            {launchResult.queued_count !== 1 ? "s" : ""} queued.
            {launchResult.failed_at_render_count > 0 &&
              ` ${launchResult.failed_at_render_count} failed at render — see grid below.`}
          </p>
        </div>
      )}

      {/* Launch button */}
      <Button
        type="button"
        data-testid="launch-btn"
        disabled={
          !f?.ready_to_launch ||
          launch.isPending ||
          forecast.isLoading ||
          launched
        }
        onClick={() => setModalOpen(true)}
        className="w-fit"
      >
        {launch.isPending ? (
          <>
            <Loader2
              data-testid="launch-spinner"
              className="mr-2 h-4 w-4 animate-spin"
            />
            Launching…
          </>
        ) : (
          "Launch batch"
        )}
      </Button>

      {/* Launch confirmation modal */}
      {modalOpen && f && (
        <LaunchModal
          campaign={campaign}
          forecast={f}
          costDollars={costDollars ?? "0.00"}
          isPending={launch.isPending}
          onConfirm={() => void handleLaunchConfirm()}
          onCancel={() => setModalOpen(false)}
        />
      )}
    </section>
  );
}

// ---- LaunchModal (B3.8) — inline, no Radix dep --------------

function LaunchModal({
  campaign,
  forecast,
  costDollars,
  isPending,
  onConfirm,
  onCancel,
}: {
  campaign: PersonalizedCampaign;
  forecast: import("@/lib/api/campaigns").CampaignForecast;
  costDollars: string;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    // Backdrop
    <div
      data-testid="launch-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        // Close only on backdrop click, not modal content click.
        if (e.target === e.currentTarget && !isPending) onCancel();
      }}
    >
      <div
        data-testid="launch-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="launch-modal-heading"
        className="relative w-full max-w-md rounded-lg border border-border bg-card shadow-xl p-6 flex flex-col gap-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        {!isPending && (
          <button
            type="button"
            aria-label="Close"
            data-testid="launch-modal-close"
            onClick={onCancel}
            className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        <h2
          id="launch-modal-heading"
          data-testid="launch-modal-heading"
          className="font-display text-xl tracking-tight"
        >
          Launch {forecast.recipient_count} personalized video
          {forecast.recipient_count !== 1 ? "s" : ""}?
        </h2>

        <div className="flex flex-col gap-2 text-sm text-muted-foreground">
          <p>
            Spokesperson:{" "}
            <strong className="text-foreground">{campaign.spokesperson_name}</strong>
          </p>
          <p>
            Recipients:{" "}
            <strong className="text-foreground">{forecast.recipient_count}</strong>
          </p>
          <p>
            Estimated cost:{" "}
            <strong className="text-foreground">${costDollars}</strong> ($0.25 per
            render)
          </p>
          <p className="text-xs text-muted-foreground/80 mt-1">
            This will start rendering immediately and count against your monthly
            video allowance. Once launched, recipients cannot be edited — only
            retried if they fail.
          </p>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <Button
            type="button"
            data-testid="launch-modal-confirm"
            disabled={isPending}
            onClick={onConfirm}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Launching…
              </>
            ) : (
              "Yes, launch"
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            data-testid="launch-modal-cancel"
            disabled={isPending}
            onClick={onCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---- TerminalBanner (B3.8) ----------------------------------

function TerminalBanner({ campaign }: { campaign: PersonalizedCampaign }) {
  const { completed, failed, total } = campaign.recipient_counts;
  const status = campaign.status;

  const text =
    status === "completed"
      ? `Completed — ${completed} of ${total} rendered successfully.`
      : status === "partial"
        ? `Partial — ${completed} succeeded, ${failed} failed.`
        : `Failed — all ${total} recipient${total !== 1 ? "s" : ""} failed to render.`;

  const tone =
    status === "completed"
      ? "success"
      : status === "partial"
        ? "amber"
        : "danger";

  return (
    <div
      data-testid="terminal-banner"
      className={cn(
        "rounded-md border p-4 text-sm font-medium",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <span data-testid="terminal-banner-text">{text}</span>
        {(status === "completed" || status === "partial") && (
          <a
            data-testid="browse-assets-link"
            href="/workspace/assets"
            className="text-xs font-normal underline underline-offset-2 opacity-80 hover:opacity-100"
          >
            Browse produced assets
          </a>
        )}
      </div>
    </div>
  );
}

// ---- RecipientGrid (B3.8) -----------------------------------

function RecipientGrid({
  campaignId,
  campaign,
  refetchCampaign,
}: {
  campaignId: string;
  campaign: PersonalizedCampaign;
  refetchCampaign: () => void;
}) {
  const recipients = useRecipients(campaignId);
  const rows = recipients.data ?? [];
  const counts = campaign.recipient_counts;
  const activeCount = counts.queued + counts.running;
  const isActive =
    campaign.status === "launching" || campaign.status === "in_flight";

  return (
    <section
      data-testid="recipient-grid"
      className="rounded-md border border-border bg-card p-6 flex flex-col gap-5"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-xl tracking-tight">Recipients</h2>

        {/* Progress summary */}
        {isActive && (
          <div
            data-testid="progress-summary"
            className="flex flex-col gap-2"
          >
            <p className="text-sm text-muted-foreground">
              <span className="text-foreground font-medium">
                {counts.completed} of {counts.total}
              </span>{" "}
              rendered
              {activeCount > 0 && ` · ${activeCount} in progress`}
            </p>
            {counts.total > 0 && (
              <div
                data-testid="progress-bar"
                className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
              >
                <div
                  className="h-full rounded-full bg-amber-400 transition-all"
                  style={{
                    width: `${Math.round((counts.completed / counts.total) * 100)}%`,
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {recipients.isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading recipients…
        </div>
      )}

      {rows.length > 0 && (
        <div className="flex flex-col divide-y divide-border">
          {rows.map((r) => (
            <RecipientRow
              key={r.id}
              recipient={r}
              campaignId={campaignId}
              campaign={campaign}
              refetchCampaign={refetchCampaign}
            />
          ))}
        </div>
      )}

      {!recipients.isLoading && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">No recipients found.</p>
      )}
    </section>
  );
}

// ---- RecipientRow (B3.8) ------------------------------------

function RecipientRow({
  recipient,
  campaignId,
  campaign,
  refetchCampaign,
}: {
  recipient: PersonalizedRecipient;
  campaignId: string;
  campaign: PersonalizedCampaign;
  refetchCampaign: () => void;
}) {
  const [confirmRetry, setConfirmRetry] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const retry = useRetryRecipient(campaignId);

  const tone = recipientStatusTone(recipient.status);
  const isTerminal =
    campaign.status === "completed" ||
    campaign.status === "partial" ||
    campaign.status === "failed";
  const canRetry = isTerminal && recipient.status === "failed";

  // Variables preview: up to 3 key=value pairs truncated.
  const varPreview = Object.entries(recipient.variables)
    .slice(0, 3)
    .map(([k, v]) => `${k}=${String(v).slice(0, 20)}`)
    .join(" • ");
  const hasMoreVars = Object.keys(recipient.variables).length > 3;

  async function handleRetry() {
    if (!confirmRetry) {
      setConfirmRetry(true);
      return;
    }
    setRetryError(null);
    try {
      await retry.mutateAsync(recipient.id);
      setConfirmRetry(false);
      refetchCampaign();
    } catch (err) {
      setRetryError(
        err instanceof Error ? err.message : "Retry failed.",
      );
      setConfirmRetry(false);
    }
  }

  return (
    <div
      data-testid={`recipient-row-${recipient.id}`}
      className="py-4 flex flex-col gap-2"
    >
      <div className="flex items-center gap-3 flex-wrap">
        {/* Status badge */}
        <RecipientStatusBadge tone={tone} status={recipient.status} />

        {/* Label */}
        <span
          data-testid={`recipient-label-${recipient.id}`}
          className="font-medium text-sm"
        >
          {recipient.label}
        </span>

        {/* Variables preview */}
        <span
          data-testid={`recipient-vars-${recipient.id}`}
          className="text-xs text-muted-foreground font-mono"
        >
          {varPreview}
          {hasMoreVars ? "…" : ""}
        </span>

        {/* Composition link */}
        {recipient.produced_composition_id && recipient.status === "completed" && (
          <a
            data-testid={`recipient-composition-link-${recipient.id}`}
            href={`/compositions/${recipient.produced_composition_id}`}
            className="ml-auto text-xs text-primary hover:underline whitespace-nowrap"
          >
            View composition →
          </a>
        )}
      </div>

      {/* Error message */}
      {recipient.status === "failed" && recipient.error_message && (
        <p
          data-testid={`recipient-error-${recipient.id}`}
          className="text-xs text-destructive pl-1"
        >
          {recipient.error_message}
        </p>
      )}

      {/* Retry affordance (terminal campaigns only, failed recipients) */}
      {canRetry && (
        <div className="flex items-center gap-3 pl-1">
          {retryError && (
            <p
              data-testid={`recipient-retry-error-${recipient.id}`}
              className="text-xs text-destructive"
            >
              {retryError}
            </p>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid={`retry-btn-${recipient.id}`}
            disabled={retry.isPending}
            onClick={() => void handleRetry()}
            className="h-7 px-2.5 text-xs gap-1.5"
          >
            {retry.isPending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Retrying…
              </>
            ) : (
              <>
                <RefreshCw className="h-3 w-3" />
                {confirmRetry ? "Confirm retry" : "Retry"}
              </>
            )}
          </Button>
          {confirmRetry && !retry.isPending && (
            <>
              <p className="text-xs text-muted-foreground">
                A new render will fire for this recipient.
              </p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2.5 text-xs"
                onClick={() => setConfirmRetry(false)}
              >
                Cancel
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ---- RecipientStatusBadge -----------------------------------

function RecipientStatusBadge({
  tone,
  status,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  status: string;
}) {
  return (
    <span
      data-testid={`recipient-status-badge-${status}`}
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {status}
    </span>
  );
}

// ---- StatusBadge helper (mirrors campaigns.tsx) --------------

function StatusBadge({
  tone,
  label,
}: {
  tone: "muted" | "amber" | "success" | "danger";
  label: string;
}) {
  return (
    <span
      data-testid="campaign-status-badge"
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tone === "amber" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-400",
        tone === "success" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
        tone === "muted" && "border-border bg-muted text-muted-foreground",
        tone === "danger" &&
          "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {label}
    </span>
  );
}

// ---- Loading / error / not-found states ----------------------

function BackLink() {
  return (
    <Link
      to="/workspace/campaigns"
      data-testid="back-to-campaigns"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to Campaigns
    </Link>
  );
}

function LoadingSkeleton() {
  return (
    <div
      data-testid="campaign-detail-skeleton"
      className="flex flex-col gap-6 animate-pulse"
    >
      <div className="h-10 w-64 rounded bg-muted" />
      <div className="h-48 w-full rounded-md bg-muted" />
      <div className="h-40 w-full rounded-md bg-muted" />
    </div>
  );
}

function NotFound() {
  return (
    <div
      data-testid="campaign-not-found"
      className="rounded-md border border-dashed border-border p-12 text-center"
    >
      <p className="text-base font-medium">Campaign not found</p>
      <p className="mt-1 text-sm text-muted-foreground">
        This campaign may have been deleted or belongs to a different workspace.
      </p>
      <Button
        asChild
        variant="outline"
        size="sm"
        className="mt-4"
        data-testid="not-found-back"
      >
        <Link to="/workspace/campaigns">Back to Campaigns</Link>
      </Button>
    </div>
  );
}

function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      data-testid="campaign-detail-error"
      className="rounded-md border border-destructive/40 bg-destructive/10 p-6 text-center"
    >
      <p className="text-sm text-destructive">{message}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-3"
        data-testid="campaign-detail-retry"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}
