/**
 * /workspace/knowledge — workspace knowledge dashboard.
 *
 * SESSION 138 / K4. The system-of-record surface for
 * KnowledgeDocument. Paste + PDF upload here; per-spokesperson
 * filtering lands as a filtered view in K5 (spokesperson detail
 * "Knowledge" tab).
 *
 * Status polling: list query refetches every 3s while any
 * document is in pending/processing. Snaps to no-poll once all
 * docs are settled.
 */
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, FileText, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMe } from "@/lib/api/workspaces";
import {
  pdfFileToDataUri,
  statusTone,
  useCreateKnowledge,
  useDeleteKnowledge,
  useKnowledgeList,
  type DocumentStatus,
  type KnowledgeDocument,
} from "@/lib/api/knowledge";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";


export function WorkspaceKnowledgeRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  const workspaceName = me.data?.default_workspace?.name;

  const list = useKnowledgeList(workspaceId, {
    refetchInterval: (query) => {
      // Poll while any doc is mid-pipeline. Stop polling once
      // every visible row is settled (processed or failed).
      const docs = query.state.data ?? [];
      const inFlight = docs.some(
        (d) => d.status === "pending" || d.status === "processing",
      );
      return inFlight ? 3000 : false;
    },
  });

  const docs = list.data ?? [];

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <h1
          data-testid="knowledge-title"
          className="font-display text-4xl leading-tight tracking-tight md:text-5xl"
        >
          Knowledge
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          What {workspaceName ?? "your workspace"}'s spokespeople know about your
          business. Paste markdown, upload PDFs — every render and conversation
          draws from this corpus.
        </p>
      </header>

      <UploadPanel workspaceId={workspaceId} />

      <section className="flex flex-col gap-4">
        <h2 className="font-display text-2xl tracking-tight">
          Documents{docs.length > 0 ? ` (${docs.length})` : ""}
        </h2>

        {list.isLoading && (
          <p className="text-sm text-muted-foreground">Loading…</p>
        )}
        {list.error && (
          <p className="text-sm text-destructive">
            Failed to load: {list.error.message}
          </p>
        )}
        {!list.isLoading && docs.length === 0 && (
          <EmptyState />
        )}
        {docs.length > 0 && (
          <ul
            data-testid="knowledge-list"
            className="divide-y divide-border rounded-md border border-border bg-card"
          >
            {docs.map((doc) => (
              <KnowledgeRow
                key={doc.id}
                doc={doc}
                workspaceId={workspaceId}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}


function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-border p-12 text-center">
      <FileText className="mx-auto h-10 w-10 text-muted-foreground" />
      <p className="mt-4 text-base font-medium">No documents yet</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Paste content or upload a PDF above. Every spokesperson in the
        workspace will be able to draw from it.
      </p>
    </div>
  );
}


function UploadPanel({ workspaceId }: { workspaceId: string | undefined }) {
  return (
    <section
      data-testid="knowledge-upload"
      className="rounded-md border border-border bg-card p-6"
    >
      <h2 className="font-display text-2xl tracking-tight">Add knowledge</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Pick paste for typed content, upload for PDFs. URL ingestion and
        web-search discovery are coming.
      </p>

      <Tabs defaultValue="paste" className="mt-6">
        <TabsList>
          <TabsTrigger value="paste" data-testid="tab-paste">
            Paste
          </TabsTrigger>
          <TabsTrigger value="upload" data-testid="tab-upload">
            Upload PDF
          </TabsTrigger>
        </TabsList>

        <TabsContent value="paste" className="mt-4">
          <PasteForm workspaceId={workspaceId} />
        </TabsContent>

        <TabsContent value="upload" className="mt-4">
          <UploadForm workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </section>
  );
}


function PasteForm({ workspaceId }: { workspaceId: string | undefined }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const create = useCreateKnowledge(workspaceId);

  const disabled = !workspaceId || !title.trim() || !content.trim() || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        title: title.trim(),
        text_content: content,
      });
      setTitle("");
      setContent("");
    } catch (err) {
      // Error is surfaced inline below.
      console.error("paste ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="paste-title">Title</Label>
        <Input
          id="paste-title"
          data-testid="paste-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What is this knowledge?"
          maxLength={500}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="paste-content">Content</Label>
        <textarea
          id="paste-content"
          data-testid="paste-content"
          className="min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste markdown or plain text here. Headings + paragraphs preserved."
          required
        />
      </div>

      {create.error && (
        <p
          data-testid="paste-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}

      <Button
        type="submit"
        data-testid="paste-submit"
        disabled={disabled}
      >
        {create.isPending ? "Ingesting…" : "Add to knowledge"}
      </Button>
    </form>
  );
}


function UploadForm({ workspaceId }: { workspaceId: string | undefined }) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const create = useCreateKnowledge(workspaceId);

  const disabled = !workspaceId || !title.trim() || !file || create.isPending;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0] ?? null;
    setFileError(null);
    if (picked && picked.size > 10 * 1024 * 1024) {
      setFileError("PDF must be 10 MB or less.");
      setFile(null);
      return;
    }
    setFile(picked);
    // Pre-fill title from the filename minus the extension.
    if (picked && !title) {
      setTitle(picked.name.replace(/\.pdf$/i, ""));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId || !file) return;
    try {
      const dataUri = await pdfFileToDataUri(file);
      await create.mutateAsync({
        workspace: workspaceId,
        title: title.trim(),
        pdf_data_uri: dataUri,
      });
      setTitle("");
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      console.error("pdf ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="upload-title">Title</Label>
        <Input
          id="upload-title"
          data-testid="upload-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What is this PDF about?"
          maxLength={500}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="upload-file">PDF</Label>
        <input
          id="upload-file"
          data-testid="upload-file"
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          className="text-sm file:mr-3 file:rounded-sm file:border file:border-border file:bg-background file:px-3 file:py-1.5 file:text-sm hover:file:bg-accent"
        />
        {file && (
          <p className="text-xs text-muted-foreground">
            Selected: {file.name} ({Math.round(file.size / 1024)} KB)
          </p>
        )}
        {fileError && (
          <p className="text-xs text-destructive">{fileError}</p>
        )}
      </div>

      {create.error && (
        <p
          data-testid="upload-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}

      <Button
        type="submit"
        data-testid="upload-submit"
        disabled={disabled}
      >
        {create.isPending ? "Uploading + extracting…" : "Upload PDF"}
      </Button>
    </form>
  );
}


function KnowledgeRow({
  doc,
  workspaceId,
}: {
  doc: KnowledgeDocument;
  workspaceId: string | undefined;
}) {
  const del = useDeleteKnowledge(workspaceId);

  async function handleDelete() {
    if (!confirm(`Delete "${doc.title}"? Chunks stay searchable in admin only.`)) {
      return;
    }
    await del.mutateAsync(doc.id);
  }

  return (
    <li
      data-testid={`knowledge-row-${doc.id}`}
      className="flex items-center gap-4 px-5 py-4"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="truncate font-medium" title={doc.title}>
            {doc.title}
          </p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {labelForType(doc.document_type)} · {doc.chunk_count} chunk
          {doc.chunk_count === 1 ? "" : "s"} · {labelForIngestedVia(doc.ingested_via)}
        </p>
        {doc.status === "failed" && doc.error_message && (
          <p className="mt-1 text-xs text-destructive">
            {doc.error_message}
          </p>
        )}
      </div>

      <StatusPill status={doc.status} />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-testid={`knowledge-delete-${doc.id}`}
        onClick={handleDelete}
        disabled={del.isPending}
        aria-label={`Delete ${doc.title}`}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </li>
  );
}


function StatusPill({ status }: { status: DocumentStatus }) {
  const tone = statusTone(status);
  return (
    <span
      data-testid="knowledge-status"
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
      return "Text";
    case "markdown":
      return "Markdown";
    case "pdf":
      return "PDF";
    case "url":
      return "Web page";
  }
}

function labelForIngestedVia(via: KnowledgeDocument["ingested_via"]): string {
  switch (via) {
    case "paste":
      return "Pasted";
    case "upload":
      return "Uploaded";
    case "serper":
      return "Searched";
    case "seed":
      return "Seeded";
  }
}


function readableError(err: unknown): string {
  if (err instanceof ApiError) {
    const body = err.body;
    if (typeof body === "object" && body !== null) {
      // DRF validation errors are usually `{field: [messages]}`.
      const messages: string[] = [];
      for (const [k, v] of Object.entries(body)) {
        if (Array.isArray(v)) {
          messages.push(...v.map((m) => `${k}: ${String(m)}`));
        } else if (typeof v === "string") {
          messages.push(`${k}: ${v}`);
        }
      }
      if (messages.length > 0) return messages.join("\n");
    }
    return err.message;
  }
  return String(err);
}
