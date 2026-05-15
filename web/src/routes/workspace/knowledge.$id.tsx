/**
 * /workspace/knowledge/:id — knowledge document detail.
 *
 * SESSION 140 / K4.1. The list view at /workspace/knowledge
 * shows title + chunk count + status — useful for a glance,
 * useless for answering "did the right content land?" This
 * detail view fills the gap:
 *
 * - Title + status pill + source URL (clickable for URL docs)
 * - Provenance metadata (author, date, hostname, fetched +
 *   extracted character counts)
 * - Per-chunk list with index, size, and the actual text —
 *   what the retrieval surface will return at render time.
 *
 * Per-row spokesperson attach/detach lives on the spokesperson
 * detail page (K5 panel); this view focuses on content audit.
 */
import { useNavigate, useParams, Link } from "react-router-dom";
import { ChevronLeft, ExternalLink, Trash2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  statusTone,
  useDeleteKnowledge,
  useKnowledgeCompositions,
  useKnowledgeDocument,
  type DocumentStatus,
  type KnowledgeChunk,
  type KnowledgeDocument,
  type KnowledgeUsedByItem,
} from "@/lib/api/knowledge";
import { cn } from "@/lib/utils";


export function KnowledgeDocumentDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const doc = useKnowledgeDocument(id, {
    // Poll while still processing — same shape as the list
    // view's polling so the chunks appear as soon as embeddings
    // finish.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "processing" ? 3000 : false;
    },
  });
  const del = useDeleteKnowledge(doc.data?.workspace);
  // F7 — load the reverse composition list. Hook fires only
  // when an id is available; the panel hides when the list
  // is empty so unused docs don't dangle a section header.
  const usedBy = useKnowledgeCompositions(id);

  if (doc.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }
  if (doc.isError || !doc.data) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <p className="text-sm text-destructive">
          {doc.error?.message ?? "Document not found."}
        </p>
      </div>
    );
  }

  const data = doc.data;

  async function handleDelete() {
    if (!confirm(`Delete "${data.title}"? Chunks stay searchable in admin only.`)) {
      return;
    }
    await del.mutateAsync(data.id);
    navigate("/workspace/knowledge");
  }

  return (
    <div className="flex flex-col gap-10" data-testid="knowledge-detail">
      <BackLink />

      <header className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <h1
            data-testid="knowledge-detail-title"
            className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
          >
            {data.title}
          </h1>
          <StatusPill status={data.status} />
        </div>

        <Metadata doc={data} />

        {data.status === "failed" && data.error_message && (
          <p className="rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            {data.error_message}
          </p>
        )}

        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="knowledge-detail-delete"
            onClick={handleDelete}
            disabled={del.isPending}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {del.isPending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </header>

      <ChunksSection chunks={data.chunks} status={data.status} />

      {usedBy.data && usedBy.data.length > 0 && (
        <UsedByCompositionsPanel items={usedBy.data} />
      )}
    </div>
  );
}

function UsedByCompositionsPanel({ items }: { items: KnowledgeUsedByItem[] }) {
  return (
    <section
      className="flex flex-col gap-3 rounded-md border bg-card p-5 shadow-paper"
      data-testid="knowledge-used-by-compositions"
    >
      <div className="flex items-center justify-between border-b pb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-display text-base tracking-tight">
            Used by {items.length} composition{items.length === 1 ? "" : "s"}
          </h2>
        </div>
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((item) => (
          <li key={item.composition_id}>
            <Link
              to={`/compositions/${item.composition_id}`}
              data-testid={`knowledge-used-by-${item.composition_id}`}
              className="flex items-baseline justify-between gap-3 rounded-sm border bg-muted/30 px-3 py-2 transition-colors hover:border-foreground"
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-sm">{item.composition_name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {item.template_kind} · {item.spokesperson_name}
                </span>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {item.chunk_count} chunk{item.chunk_count === 1 ? "" : "s"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}


function BackLink() {
  return (
    <Link
      to="/workspace/knowledge"
      data-testid="back-to-knowledge"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft className="h-4 w-4" />
      Back to knowledge
    </Link>
  );
}


function Metadata({ doc }: { doc: KnowledgeDocument }) {
  const meta = doc.source_metadata;
  const rows: { label: string; value: React.ReactNode }[] = [
    { label: "Type", value: labelForType(doc.document_type) },
    { label: "Ingested via", value: labelForVia(doc.ingested_via) },
    { label: "Chunks", value: doc.chunk_count },
  ];
  if (doc.source_url) {
    rows.push({
      label: "Source URL",
      value: (
        <a
          href={doc.source_url}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="knowledge-source-url"
          className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
        >
          {doc.source_url}
          <ExternalLink className="h-3 w-3" />
        </a>
      ),
    });
  }
  if (meta.hostname) {
    rows.push({ label: "Hostname", value: String(meta.hostname) });
  }
  if (meta.author) {
    rows.push({ label: "Author", value: String(meta.author) });
  }
  if (meta.date) {
    rows.push({ label: "Date", value: String(meta.date) });
  }
  if (meta.extracted_chars) {
    rows.push({
      label: "Extracted",
      value: `${Number(meta.extracted_chars).toLocaleString()} chars`,
    });
  }
  if (meta.fetched_chars) {
    rows.push({
      label: "Fetched",
      value: `${Number(meta.fetched_chars).toLocaleString()} chars`,
    });
  }
  if (meta.pdf_page_count) {
    rows.push({ label: "PDF pages", value: String(meta.pdf_page_count) });
  }
  rows.push({
    label: "Created",
    value: new Date(doc.created_at).toLocaleString(),
  });

  return (
    <dl
      data-testid="knowledge-detail-metadata"
      className="grid grid-cols-1 gap-x-8 gap-y-2 rounded-md border border-border bg-card p-5 text-sm md:grid-cols-[10rem_1fr]"
    >
      {rows.map((row) => (
        <div key={row.label} className="contents">
          <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {row.label}
          </dt>
          <dd className="break-words">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}


function ChunksSection({
  chunks,
  status,
}: {
  chunks: KnowledgeChunk[] | undefined;
  status: DocumentStatus;
}) {
  if (status === "pending" || status === "processing") {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-2xl tracking-tight">Chunks</h2>
        <p className="text-sm text-muted-foreground">
          Embedding in progress — chunks will appear when the document
          finishes processing.
        </p>
      </section>
    );
  }
  if (!chunks || chunks.length === 0) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-2xl tracking-tight">Chunks</h2>
        <p className="text-sm text-muted-foreground">
          No chunks. The document may have failed to embed — check the
          error message above.
        </p>
      </section>
    );
  }
  return (
    <section className="flex flex-col gap-4">
      <h2 className="font-display text-2xl tracking-tight">
        Chunks
        <span className="ml-2 font-mono text-sm text-muted-foreground">
          {chunks.length}
        </span>
      </h2>
      <ol
        data-testid="knowledge-chunks"
        className="flex flex-col gap-3"
      >
        {chunks.map((chunk) => (
          <li
            key={chunk.id}
            data-testid={`knowledge-chunk-${chunk.chunk_index}`}
            className="rounded-md border border-border bg-card p-5"
          >
            <div className="mb-2 flex items-center gap-3 text-xs text-muted-foreground">
              <span className="font-mono font-medium text-foreground">
                #{chunk.chunk_index}
              </span>
              <span>{chunk.chunk_size.toLocaleString()} chars</span>
              {chunk.overlap_size > 0 && (
                <span>· {chunk.overlap_size} char overlap</span>
              )}
              <span>· {chunk.embedding_model}</span>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {chunk.chunk_text}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}


function StatusPill({ status }: { status: DocumentStatus }) {
  const tone = statusTone(status);
  return (
    <span
      data-testid="knowledge-detail-status"
      data-status={status}
      className={cn(
        "inline-flex shrink-0 items-center rounded-sm border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider",
        tone === "neutral" && "border-border bg-muted text-muted-foreground",
        tone === "info" && "border-primary/40 bg-primary/10 text-primary",
        tone === "success" && "border-emerald-500/40 bg-emerald-500/10 text-emerald-700",
        tone === "danger" && "border-destructive/40 bg-destructive/10 text-destructive",
      )}
    >
      {status}
    </span>
  );
}


function labelForType(t: KnowledgeDocument["document_type"]): string {
  switch (t) {
    case "text":
      return "Plain text";
    case "markdown":
      return "Markdown";
    case "pdf":
      return "PDF";
    case "url":
      return "Web page";
  }
}

function labelForVia(via: KnowledgeDocument["ingested_via"]): string {
  switch (via) {
    case "paste":
      return "Pasted";
    case "upload":
      return "Uploaded";
    case "serper":
      return "Web search";
    case "seed":
      return "Seeded";
  }
}
