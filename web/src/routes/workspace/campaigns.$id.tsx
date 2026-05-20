/**
 * /workspace/campaigns/:id — Campaign detail + CSV paste UX.
 *
 * SESSION B3.7 (minimal). Shows:
 *   - Campaign metadata: name, spokesperson, status badge, placeholders,
 *     template preview.
 *   - Paste CSV textarea + "Parse CSV" button.
 *   - Parse result: valid count badge, rejected rows (expandable),
 *     recipient preview table.
 *   - "Re-parse" to replace with a new CSV.
 *   - Delete campaign (DRAFT-only).
 *
 * B3.8 will extend this file with the Launch button + cost forecast
 * modal + recipient progress grid + retry per-recipient.
 *
 * Scope: docs/design/PERSONALIZED_VIDEO_V1.md §B3.7.
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
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  useCampaign,
  useParseCsv,
  useDeleteCampaign,
  campaignStatusTone,
  campaignStatusLabel,
  type PersonalizedCampaign,
  type PersonalizedRecipient,
  type ParseCsvResponse,
} from "@/lib/api/campaigns";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ---- Page component -----------------------------------------

export function CampaignDetailRoute() {
  const { id } = useParams<{ id: string }>();
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

  return (
    <div
      data-testid="campaign-detail"
      className="flex flex-col gap-8 max-w-3xl"
    >
      <BackLink />
      <CampaignMetadataPanel campaign={campaign.data} />
      {id && <CsvPanel campaignId={id} campaign={campaign.data} />}
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
