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
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, FileText, Search, Trash2, Sparkles, Users } from "lucide-react";

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
  useKnowledgeSearch,
  type DocumentStatus,
  type KnowledgeDocument,
  type SearchResult,
} from "@/lib/api/knowledge";
import {
  UNIVERSE_LEGACY_SENTINEL,
  useUniverse,
  useUniverses,
  type Universe,
} from "@/lib/api/universes";
import { useSpokesperson } from "@/lib/api/spokespeople";
import { parseKnowledgeHandoff } from "@/lib/knowledge/handoff";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/editorial";


// SESSION 261 — SPA-load-bearing "pick a Universe" control.
// Every knowledge upload form embeds this at the top; submit
// stays disabled until the operator picks either a Universe or
// the explicit "None (legacy)" option. Empty string = unpicked;
// UNIVERSE_LEGACY_SENTINEL = explicit legacy; UUID = Universe.
export type UniverseScopeValue = "" | typeof UNIVERSE_LEGACY_SENTINEL | string;

interface UniverseScopePickerProps {
  id?: string;
  workspaceId: string | undefined;
  value: UniverseScopeValue;
  onChange: (next: UniverseScopeValue) => void;
  disabled?: boolean;
}

/** Renders the universe scope select. Renders "Loading…" as a
 * placeholder while /api/universes/ is in flight so submits stay
 * disabled instead of silently defaulting. */
export function UniverseScopePicker({
  id = "universe-scope",
  workspaceId,
  value,
  onChange,
  disabled,
}: UniverseScopePickerProps) {
  const universes = useUniverses(workspaceId);
  const rows = universes.data ?? [];
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>World / Universe</Label>
      <select
        id={id}
        data-testid={id}
        value={value}
        onChange={(e) => onChange(e.target.value as UniverseScopeValue)}
        disabled={disabled || universes.isLoading}
        className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        required
      >
        <option value="" disabled>
          {universes.isLoading ? "Loading…" : "— Pick a scope —"}
        </option>
        <option value={UNIVERSE_LEGACY_SENTINEL}>
          None (legacy — visible to workspace-wide legacy teammates only)
        </option>
        {rows.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name}
          </option>
        ))}
      </select>
      <p className="text-xs text-muted-foreground">
        Pick a world to scope this doc to that world's characters,
        or pick "None (legacy)" to make it visible to legacy
        (pre-Universe) characters.
      </p>
    </div>
  );
}

/** Translate SPA-select value into a payload value. Sentinel →
 * null (explicit legacy). UUID stays. "" (unpicked) throws — the
 * submit button should have been disabled. */
export function universeScopeToPayload(value: UniverseScopeValue): string | null {
  if (value === "") {
    throw new Error("Universe scope must be explicitly picked");
  }
  if (value === UNIVERSE_LEGACY_SENTINEL) return null;
  return value;
}

/** Is the scope explicitly picked (either a Universe or legacy)? */
export function universeScopePicked(value: UniverseScopeValue): boolean {
  return value !== "";
}

/** SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) — translate
 * the picker state into the positive WORKSPACE fresh-create marker.
 * Returns `"workspace"` when the operator explicitly picked the
 * "None (legacy)" sentinel (that's the positive workspace-sharing
 * gesture — the option's own copy names the resulting audience);
 * returns `undefined` when the operator picked a specific Universe
 * (which becomes UNIVERSE at `_persist` via `universe=<uuid>`)
 * or when the picker is unpicked (submit should be disabled).
 *
 * Callers should spread the result into their create payload:
 * `{ ..., audience_scope: universeScopeToAudienceMarker(scope) }`.
 * The backend serializer rejects the marker if combined with
 * `spokesperson_ids` or a non-null `universe`, so this helper must
 * never be called on a payload that also includes either. */
export function universeScopeToAudienceMarker(
  value: UniverseScopeValue,
): "workspace" | undefined {
  if (value === UNIVERSE_LEGACY_SENTINEL) return "workspace";
  return undefined;
}


export function WorkspaceKnowledgeRoute() {
  const navigate = useNavigate();
  const me = useMe();
  const workspaceId = me.data?.default_workspace?.id;
  // SESSION 277 Slice 12 (Q-277-12) — read the contextual handoff
  // params. `parsed` is `null` when the URL is bare or when any
  // required param is missing / malformed. The destination MUST
  // fail safely to the generic (non-contextual) flow in that case
  // per Slice 11 §217.
  const [searchParams] = useSearchParams();
  const parsed = parseKnowledgeHandoff(searchParams);

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
      <header className="relative flex flex-col gap-4 pb-10">
        <button
          type="button"
          className="inline-flex w-fit items-center gap-1.5 text-sm text-fog hover:text-gold transition-colors"
          onClick={() => navigate("/dashboard")}
        >
          <ChevronLeft className="h-4 w-4" />
          Back to dashboard
        </button>
        <SectionHeader number={1} title="Knowledge" />
        <h1
          data-testid="knowledge-title"
          className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl"
        >
          What your{" "}
          <span className="italic gold-text">spokespeople</span> know.
        </h1>
        <p className="max-w-2xl text-base text-mist">
          Paste markdown, upload PDFs, ingest URLs — every render and conversation
          draws from this corpus.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
      </header>

      {/* SESSION 277 Slice 12 (Q-277-12) — Contextual character-
          origin mode: when the URL carries valid character-origin
          handoff params (universe / spokesperson / origin), render
          the two-choice audience selector variant.
          SESSION 277 Slice 13 (Q-277-13-C) — World-detail origin:
          when origin=world_detail_add_knowledge, render the shared-
          World variant that preselects UNIVERSE audience and does
          not offer a character choice. Both variants live in the
          same page; the parser produces a discriminated union we
          dispatch on. When parsed is null (bare URL or invalid
          params), fall through to the pre-Slice-12 generic
          UploadPanel unchanged (compatibility path per §217). */}
      {parsed?.origin === "world_detail_add_knowledge" ? (
        // Parser guarantees universeId !== null for this origin
        // (handoff.ts §"world_detail_add_knowledge: universe is
        // REQUIRED"). The `!` here is safe because
        // parseKnowledgeHandoff returns null otherwise.
        <WorldOriginUploadPanel
          workspaceId={workspaceId}
          universeIdParam={parsed.universeId!}
        />
      ) : parsed ? (
        // Character origin: parser guarantees spokespersonId !== null.
        <CharacterOriginUploadPanel
          workspaceId={workspaceId}
          spokespersonId={parsed.spokespersonId!}
          universeIdParam={parsed.universeId}
          origin={parsed.origin}
        />
      ) : (
        <UploadPanel workspaceId={workspaceId} />
      )}

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between border-b border-luxe pb-3">
          <h2 className="font-display text-2xl tracking-tight text-cream">
            Documents
          </h2>
          {docs.length > 0 && (
            <span className="font-mono text-xs text-fog">{docs.length}</span>
          )}
        </div>

        {list.isLoading && (
          <p className="text-sm text-fog">Loading…</p>
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
            className="divide-y divide-luxe rounded-md border border-luxe bg-card"
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
    <div className="rounded-md border border-dashed border-luxe bg-card/40 p-12 text-center">
      <FileText className="mx-auto h-10 w-10 text-fog" />
      <p className="mt-4 font-display text-xl tracking-tight text-cream">No documents yet</p>
      <p className="mt-1 text-sm text-mist max-w-md mx-auto">
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
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <h2 className="font-display text-2xl tracking-tight text-cream">Add knowledge</h2>
      <p className="mt-1 text-sm text-mist">
        Pick paste for typed content, upload for PDFs, URL to ingest a
        web page snapshot, or Search to find content via the web.
      </p>

      <Tabs defaultValue="paste" className="mt-6">
        <TabsList>
          <TabsTrigger value="paste" data-testid="tab-paste">
            Paste
          </TabsTrigger>
          <TabsTrigger value="upload" data-testid="tab-upload">
            Upload PDF
          </TabsTrigger>
          <TabsTrigger value="url" data-testid="tab-url">
            URL
          </TabsTrigger>
          <TabsTrigger value="search" data-testid="tab-search">
            Search
          </TabsTrigger>
        </TabsList>

        <TabsContent value="paste" className="mt-4">
          <PasteForm workspaceId={workspaceId} />
        </TabsContent>

        <TabsContent value="upload" className="mt-4">
          <UploadForm workspaceId={workspaceId} />
        </TabsContent>

        <TabsContent value="url" className="mt-4">
          <UrlForm workspaceId={workspaceId} />
        </TabsContent>

        <TabsContent value="search" className="mt-4">
          <SearchForm workspaceId={workspaceId} />
        </TabsContent>
      </Tabs>
    </section>
  );
}


function PasteForm({ workspaceId }: { workspaceId: string | undefined }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  // SESSION 261 — explicit-scope requirement. Empty string
  // (unpicked) disables submit; sentinel or UUID enables.
  const [scope, setScope] = useState<UniverseScopeValue>("");
  const create = useCreateKnowledge(workspaceId);

  const disabled =
    !workspaceId
    || !title.trim()
    || !content.trim()
    || !universeScopePicked(scope)
    || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId || !universeScopePicked(scope)) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        universe: universeScopeToPayload(scope),
        audience_scope: universeScopeToAudienceMarker(scope),
        title: title.trim(),
        text_content: content,
      });
      setTitle("");
      setContent("");
      setScope("");
    } catch (err) {
      // Error is surfaced inline below.
      console.error("paste ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <UniverseScopePicker
        id="paste-universe-scope"
        workspaceId={workspaceId}
        value={scope}
        onChange={setScope}
      />

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
  const [scope, setScope] = useState<UniverseScopeValue>("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const create = useCreateKnowledge(workspaceId);

  const disabled =
    !workspaceId
    || !title.trim()
    || !file
    || !universeScopePicked(scope)
    || create.isPending;

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
    if (!workspaceId || !file || !universeScopePicked(scope)) return;
    try {
      const dataUri = await pdfFileToDataUri(file);
      await create.mutateAsync({
        workspace: workspaceId,
        universe: universeScopeToPayload(scope),
        audience_scope: universeScopeToAudienceMarker(scope),
        title: title.trim(),
        pdf_data_uri: dataUri,
      });
      setTitle("");
      setFile(null);
      setScope("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      console.error("pdf ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <UniverseScopePicker
        id="upload-universe-scope"
        workspaceId={workspaceId}
        value={scope}
        onChange={setScope}
      />
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


function UrlForm({ workspaceId }: { workspaceId: string | undefined }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [scope, setScope] = useState<UniverseScopeValue>("");
  const create = useCreateKnowledge(workspaceId);

  const disabled =
    !workspaceId
    || !url.trim()
    || !universeScopePicked(scope)
    || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId || !universeScopePicked(scope)) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        universe: universeScopeToPayload(scope),
        audience_scope: universeScopeToAudienceMarker(scope),
        title: title.trim() || undefined,
        source_url_input: url.trim(),
      });
      setTitle("");
      setUrl("");
      setScope("");
    } catch (err) {
      console.error("url ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <UniverseScopePicker
        id="url-universe-scope"
        workspaceId={workspaceId}
        value={scope}
        onChange={setScope}
      />
      <div className="flex flex-col gap-2">
        <Label htmlFor="url-input">URL</Label>
        <Input
          id="url-input"
          data-testid="url-input"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article-to-ingest"
          required
        />
        <p className="text-xs text-muted-foreground">
          Snapshot at ingest — content is captured as it looks now and
          isn't re-fetched. Delete + re-ingest if you need fresh.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="url-title">Title (optional)</Label>
        <Input
          id="url-title"
          data-testid="url-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Defaults to the page's title tag"
          maxLength={500}
        />
      </div>

      {create.error && (
        <p
          data-testid="url-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}

      <Button
        type="submit"
        data-testid="url-submit"
        disabled={disabled}
      >
        {create.isPending ? "Fetching + extracting…" : "Ingest URL"}
      </Button>
    </form>
  );
}


function SearchForm({ workspaceId }: { workspaceId: string | undefined }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [scope, setScope] = useState<UniverseScopeValue>("");
  const searchMut = useKnowledgeSearch();
  const create = useCreateKnowledge(workspaceId);
  const [ingestingUrl, setIngestingUrl] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const hits = await searchMut.mutateAsync(query.trim());
      setResults(hits);
    } catch (err) {
      console.error("search failed", err);
      setResults([]);
    }
  }

  async function handleIngest(result: SearchResult) {
    if (!workspaceId || !universeScopePicked(scope)) return;
    setIngestingUrl(result.url);
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        universe: universeScopeToPayload(scope),
        audience_scope: universeScopeToAudienceMarker(scope),
        title: result.title,
        source_url_input: result.url,
        via_serper: true,
      });
      // Remove the ingested result from the list so the operator
      // can see what's left.
      setResults((prev) => prev.filter((r) => r.url !== result.url));
    } catch (err) {
      console.error("serper-result ingest failed", err);
    } finally {
      setIngestingUrl(null);
    }
  }

  const canIngest = universeScopePicked(scope);

  return (
    <div className="flex flex-col gap-4">
      <UniverseScopePicker
        id="search-universe-scope"
        workspaceId={workspaceId}
        value={scope}
        onChange={setScope}
      />
      <p className="text-xs text-muted-foreground">
        Every search-ingest below scopes to the World above. Pick
        the scope first, then Search + Ingest.
      </p>
      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSearch}>
        <Input
          data-testid="search-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the web for content to ingest…"
          className="flex-1"
        />
        <Button
          type="submit"
          data-testid="search-submit"
          disabled={!query.trim() || searchMut.isPending}
        >
          <Search className="mr-2 h-4 w-4" />
          {searchMut.isPending ? "Searching…" : "Search"}
        </Button>
      </form>

      {searchMut.error && (
        <p
          data-testid="search-error"
          className="text-sm text-destructive"
        >
          {readableError(searchMut.error)}
        </p>
      )}

      {results.length > 0 && (
        <ul
          data-testid="search-results"
          className="divide-y divide-luxe rounded-md border border-luxe bg-card"
        >
          {results.map((r) => (
            <li
              key={r.url}
              data-testid={`search-result-${r.position}`}
              className="flex items-start gap-3 px-4 py-3"
            >
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium text-cream" title={r.title}>
                  {r.title}
                </p>
                <p className="truncate text-xs text-fog" title={r.url}>
                  {r.url}
                </p>
                {r.snippet && (
                  <p className="mt-1 line-clamp-2 text-xs text-mist">
                    {r.snippet}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                data-testid={`search-ingest-${r.position}`}
                disabled={ingestingUrl === r.url || !canIngest}
                onClick={() => handleIngest(r)}
              >
                {ingestingUrl === r.url ? "…" : "Ingest"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
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
          <Link
            to={`/workspace/knowledge/${doc.id}`}
            data-testid={`knowledge-row-link-${doc.id}`}
            className="truncate font-medium underline-offset-4 hover:underline"
            title={doc.title}
          >
            {doc.title}
          </Link>
        </div>
        <p className="mt-1 text-xs text-fog">
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
        tone === "neutral" && "border-luxe bg-muted text-fog",
        tone === "info" && "border-primary/40 bg-primary/10 text-primary",
        tone === "success" && "border-success/40 bg-success/10 text-success",
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


// ---- SESSION 277 Slice 12 — Contextual character-origin upload ----

/**
 * CharacterOriginUploadPanel — the Slice-12 replacement for
 * `UploadPanel` when the URL carries valid character-origin handoff
 * params. Renamed from `ContextualUploadPanel` in Slice 13 when
 * the world-detail sibling was added; behavior is byte-identical.
 *
 * The operator is presented with:
 *   1. A resolved "You just created {Character} in {World}" banner.
 *   2. An explicit two-choice audience selector:
 *      - Everyone in {World} — UNIVERSE audience.
 *      - Just {Character} — CHARACTER audience.
 *   3. The four existing ingest tabs (Paste / Upload PDF / URL /
 *      Search) rendered AFTER audience is picked, without the
 *      generic UniverseScopePicker (audience is already known).
 *
 * Payload rules (matches Slice 5 serializer §299 + Slice 12.1
 * Universe-bound CHARACTER shape):
 *   - World choice → { workspace, universe: <uuid>, ...content }
 *   - Character choice → { workspace, universe: <uuid>,
 *     spokesperson_ids: [<uuid>], ...content } — Slice 12.1
 *     hot-fix. Precedence at _persist makes spokespeople win →
 *     audience_scope=CHARACTER; the universe FK satisfies the
 *     SESSION 261 M2M invariant.
 *
 * WORKSPACE audience is intentionally NOT exposed in contextual
 * mode per Chris + ChatGPT Slice 12 product decision. The generic
 * `UploadPanel` retains its existing WORKSPACE-via-legacy-sentinel
 * gesture for the dashboard/nav-rail path.
 *
 * Failure modes → fall back to the generic `UploadPanel`:
 *   - spokesperson UUID doesn't resolve (deleted, wrong workspace).
 *   - universe UUID doesn't resolve.
 *   - spokesperson.universe doesn't match the URL universe param
 *     (stale query string).
 */

type AudienceChoice = "world" | "character";

function CharacterOriginUploadPanel({
  workspaceId,
  spokespersonId,
  universeIdParam,
  origin: _origin,
}: {
  workspaceId: string | undefined;
  spokespersonId: string;
  universeIdParam: string | null;
  origin: "character_welcome" | "character_detail_knowledge_panel";
}) {
  const spokesperson = useSpokesperson(spokespersonId);
  // Universe hook accepts undefined → disables the query cleanly.
  const universe = useUniverse(universeIdParam ?? undefined);

  const [audience, setAudience] = useState<AudienceChoice | null>(null);

  // Loading gate — wait for both resolutions before deciding whether
  // to render the contextual UI or fall back. Prevents flashing
  // through the generic panel on a valid handoff.
  if (spokesperson.isLoading || universe.isLoading) {
    return (
      <section
        data-testid="contextual-loading"
        className="rounded-md border border-luxe bg-card/60 p-6"
      >
        <p className="text-sm text-fog">Loading context…</p>
      </section>
    );
  }

  // Fail-safe validation. If ANY of the following is true, fall
  // back to the generic UploadPanel (never guess an audience):
  //   - spokesperson didn't resolve.
  //   - universe param was supplied but didn't resolve.
  //   - spokesperson.universe doesn't equal the URL param (stale).
  //   - spokesperson.universe is null (legacy teammate) AND the URL
  //     supplied a universe param (also stale).
  const spData = spokesperson.data;
  const uData = universe.data;
  const paramMatchesTeammate =
    universeIdParam == null
      ? spData?.universe == null
      : spData?.universe === universeIdParam;
  const universeResolvedIfRequested =
    universeIdParam == null ? true : uData != null;
  const invalidHandoff =
    !spData || !universeResolvedIfRequested || !paramMatchesTeammate;

  if (invalidHandoff) {
    return <UploadPanel workspaceId={workspaceId} />;
  }

  // At this point spData exists and either (universeIdParam is null
  // and sp is legacy) OR (uData resolved and matches). The
  // World-vs-character audience choice requires a resolved World
  // — if the character is legacy `universe=NULL`, fall back to the
  // generic panel because "Everyone in {World}" has no target.
  if (!uData) {
    return <UploadPanel workspaceId={workspaceId} />;
  }

  return (
    <section
      data-testid="contextual-upload"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <div className="flex items-start gap-3">
        <Sparkles className="mt-1 h-5 w-5 shrink-0 text-gold" />
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-2xl tracking-tight text-cream">
            Teach{" "}
            <span data-testid="contextual-character-name">{spData.name}</span>
          </h2>
          <p className="text-sm text-mist">
            In{" "}
            <span data-testid="contextual-world-name" className="italic gold-text">
              {uData.name}
            </span>
            . Pick who should know this before adding content.
          </p>
        </div>
      </div>

      <fieldset className="mt-6 flex flex-col gap-3" data-testid="contextual-audience">
        <legend className="text-sm font-medium text-cream">
          Who should know this?
        </legend>
        <AudienceOption
          testid="contextual-audience-world"
          checked={audience === "world"}
          onSelect={() => setAudience("world")}
          title={`Everyone in ${uData.name}`}
          hint="Shared with the characters in this World."
          icon={<Users className="h-4 w-4" />}
        />
        <AudienceOption
          testid="contextual-audience-character"
          checked={audience === "character"}
          onSelect={() => setAudience("character")}
          title={`Just ${spData.name}`}
          hint="Knowledge specific to this character."
          icon={<Sparkles className="h-4 w-4" />}
        />
      </fieldset>

      {audience && (
        <div className="mt-6" data-testid="contextual-ingest">
          <Tabs defaultValue="paste">
            <TabsList>
              <TabsTrigger value="paste" data-testid="ctx-tab-paste">
                Paste
              </TabsTrigger>
              <TabsTrigger value="upload" data-testid="ctx-tab-upload">
                Upload PDF
              </TabsTrigger>
              <TabsTrigger value="url" data-testid="ctx-tab-url">
                URL
              </TabsTrigger>
              <TabsTrigger value="search" data-testid="ctx-tab-search">
                Search
              </TabsTrigger>
            </TabsList>
            <TabsContent value="paste" className="mt-4">
              <ContextualPasteForm
                workspaceId={workspaceId}
                audience={audience}
                universe={uData}
                spokespersonId={spokespersonId}
              />
            </TabsContent>
            <TabsContent value="upload" className="mt-4">
              <ContextualUploadForm
                workspaceId={workspaceId}
                audience={audience}
                universe={uData}
                spokespersonId={spokespersonId}
              />
            </TabsContent>
            <TabsContent value="url" className="mt-4">
              <ContextualUrlForm
                workspaceId={workspaceId}
                audience={audience}
                universe={uData}
                spokespersonId={spokespersonId}
              />
            </TabsContent>
            <TabsContent value="search" className="mt-4">
              <ContextualSearchForm
                workspaceId={workspaceId}
                audience={audience}
                universe={uData}
                spokespersonId={spokespersonId}
              />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </section>
  );
}


// ---- SESSION 277 Slice 13 — World-detail origin upload panel ----

/**
 * WorldOriginUploadPanel — shared-World variant of the contextual
 * upload flow. Rendered when the destination URL carries
 * origin=world_detail_add_knowledge. Product rule (Slice 13 §256):
 * "Preserve what Character OS already knows. Ask only what it
 * genuinely doesn't know."
 *
 * The origin itself expresses UNIVERSE-audience intent — the
 * operator affirmatively clicked "Add shared knowledge" from
 * inside the World. There is no character to disambiguate and no
 * audience question to ask. This panel therefore:
 *
 *   - Resolves the World name (from `useUniverse`) — never a
 *     character.
 *   - Skips the audience selector entirely.
 *   - Renders the ingest tabs immediately, using
 *     `contextualAudiencePayload("world", ...)` to build the same
 *     `{workspace, universe: <uuid>, ...content}` payload the
 *     character-origin World branch produces (Slice 5 UNIVERSE
 *     serializer §299 / Slice 6 §110).
 *
 * Never exposes a CHARACTER audience option in this variant
 * (Slice 13 acceptance G). Never emits `audience_scope="workspace"`.
 * Fails safely to the generic `UploadPanel` when the Universe
 * doesn't resolve (Slice 13 acceptance F).
 *
 * Payload is byte-identical to Slice 12's World branch — this
 * variant differs only in UI (no selector) and in the fact that
 * `spokespersonId` is unused. The `contextualAudiencePayload`
 * helper is shared; we pass a sentinel empty string for
 * `spokespersonId` since it's never read on the World branch.
 */
function WorldOriginUploadPanel({
  workspaceId,
  universeIdParam,
}: {
  workspaceId: string | undefined;
  universeIdParam: string;
}) {
  const universe = useUniverse(universeIdParam);

  if (universe.isLoading) {
    return (
      <section
        data-testid="contextual-loading"
        className="rounded-md border border-luxe bg-card/60 p-6"
      >
        <p className="text-sm text-fog">Loading context…</p>
      </section>
    );
  }

  // Fail safely: if the Universe param doesn't resolve, fall back
  // to the generic UploadPanel. Never fabricate a World; never
  // silently substitute WORKSPACE audience (Slice 13 §259
  // acceptance F + G).
  const uData = universe.data;
  if (!uData) {
    return <UploadPanel workspaceId={workspaceId} />;
  }

  return (
    <section
      data-testid="contextual-upload"
      data-origin="world_detail_add_knowledge"
      className="rounded-md border border-luxe bg-card/60 p-6"
    >
      <div className="flex items-start gap-3">
        <Sparkles className="mt-1 h-5 w-5 shrink-0 text-gold" />
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-2xl tracking-tight text-cream">
            Add shared knowledge to{" "}
            <span
              data-testid="contextual-world-name"
              className="italic gold-text"
            >
              {uData.name}
            </span>
          </h2>
          <p className="text-sm text-mist">
            Every character in this World inherits what you add here.
            To teach a single character something private, use their
            page instead.
          </p>
        </div>
      </div>

      <div className="mt-6" data-testid="contextual-ingest">
        <Tabs defaultValue="paste">
          <TabsList>
            <TabsTrigger value="paste" data-testid="ctx-tab-paste">
              Paste
            </TabsTrigger>
            <TabsTrigger value="upload" data-testid="ctx-tab-upload">
              Upload PDF
            </TabsTrigger>
            <TabsTrigger value="url" data-testid="ctx-tab-url">
              URL
            </TabsTrigger>
            <TabsTrigger value="search" data-testid="ctx-tab-search">
              Search
            </TabsTrigger>
          </TabsList>
          <TabsContent value="paste" className="mt-4">
            <ContextualPasteForm
              workspaceId={workspaceId}
              audience="world"
              universe={uData}
              spokespersonId=""
            />
          </TabsContent>
          <TabsContent value="upload" className="mt-4">
            <ContextualUploadForm
              workspaceId={workspaceId}
              audience="world"
              universe={uData}
              spokespersonId=""
            />
          </TabsContent>
          <TabsContent value="url" className="mt-4">
            <ContextualUrlForm
              workspaceId={workspaceId}
              audience="world"
              universe={uData}
              spokespersonId=""
            />
          </TabsContent>
          <TabsContent value="search" className="mt-4">
            <ContextualSearchForm
              workspaceId={workspaceId}
              audience="world"
              universe={uData}
              spokespersonId=""
            />
          </TabsContent>
        </Tabs>
      </div>
    </section>
  );
}


function AudienceOption({
  testid,
  checked,
  onSelect,
  title,
  hint,
  icon,
}: {
  testid: string;
  checked: boolean;
  onSelect: () => void;
  title: string;
  hint: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      data-testid={testid}
      data-checked={checked ? "true" : "false"}
      onClick={onSelect}
      className={cn(
        "flex w-full items-start gap-3 rounded-md border p-4 text-left transition-colors",
        checked
          ? "border-gold bg-gold/5"
          : "border-luxe bg-card hover:border-gold/40",
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
          checked ? "border-gold bg-gold" : "border-luxe",
        )}
        aria-hidden
      />
      <span className="flex flex-col gap-1">
        <span className="flex items-center gap-2 text-sm font-medium text-cream">
          <span className="text-fog">{icon}</span>
          {title}
        </span>
        <span className="text-xs text-mist">{hint}</span>
      </span>
    </button>
  );
}


/** Build the audience-specific payload fragment. Load-bearing —
 * enforces the Slice 12 payload contract.
 *
 * - World audience → `{ universe }`.
 *   Backend interprets: `audience_scope=UNIVERSE`. The KD row
 *   lands with `universe=<uuid>` and empty M2M.
 *
 * - Character audience → `{ universe, spokesperson_ids: [uuid] }`.
 *   Both fields present is REQUIRED, not "mixed". Slice 12 hot-fix
 *   (Slice 12.1, post-Slice-12 dogfood): the backend serializer
 *   rejects `spokespeople + universe=None` for Universe-scoped
 *   characters with the error "Legacy (universe=null) docs cannot
 *   include Universe-scoped spokespeople"
 *   (`apps/embeddings/serializers.py:283-294`). The correct shape
 *   for a Universe-bound CHARACTER KD is
 *   `audience_scope=CHARACTER + universe=<uuid> + spokespeople=[sp]`
 *   with the M2M constraint `sp.universe_id == doc.universe_id`
 *   (Slice 6 §110). Serializer precedence
 *   (`apps/embeddings/ingestion.py:276`) makes `spokespeople` win
 *   over `universe` for audience_scope determination — so
 *   sending both is safe and produces CHARACTER audience with the
 *   correct Universe FK.
 *
 * - WORKSPACE is never emitted from contextual mode (Chris +
 *   ChatGPT Slice 12 product decision). */
function contextualAudiencePayload(
  audience: AudienceChoice,
  universe: Universe,
  spokespersonId: string,
): { universe: string; spokesperson_ids?: string[] } {
  if (audience === "world") return { universe: universe.id };
  return { universe: universe.id, spokesperson_ids: [spokespersonId] };
}


function ContextualPasteForm({
  workspaceId,
  audience,
  universe,
  spokespersonId,
}: {
  workspaceId: string | undefined;
  audience: AudienceChoice;
  universe: Universe;
  spokespersonId: string;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const create = useCreateKnowledge(workspaceId);
  const disabled =
    !workspaceId || !title.trim() || !content.trim() || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        ...contextualAudiencePayload(audience, universe, spokespersonId),
        title: title.trim(),
        text_content: content,
      });
      setTitle("");
      setContent("");
    } catch (err) {
      console.error("contextual paste ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-paste-title">Title</Label>
        <Input
          id="ctx-paste-title"
          data-testid="ctx-paste-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What is this knowledge?"
          maxLength={500}
          required
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-paste-content">Content</Label>
        <textarea
          id="ctx-paste-content"
          data-testid="ctx-paste-content"
          className="min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste markdown or plain text here. Headings + paragraphs preserved."
          required
        />
      </div>
      {create.error && (
        <p
          data-testid="ctx-paste-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}
      <Button
        type="submit"
        data-testid="ctx-paste-submit"
        disabled={disabled}
      >
        {create.isPending ? "Ingesting…" : "Add to knowledge"}
      </Button>
    </form>
  );
}


function ContextualUploadForm({
  workspaceId,
  audience,
  universe,
  spokespersonId,
}: {
  workspaceId: string | undefined;
  audience: AudienceChoice;
  universe: Universe;
  spokespersonId: string;
}) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const create = useCreateKnowledge(workspaceId);
  const disabled =
    !workspaceId || !title.trim() || !file || create.isPending;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0] ?? null;
    setFileError(null);
    if (picked && picked.size > 10 * 1024 * 1024) {
      setFileError("PDF must be 10 MB or less.");
      setFile(null);
      return;
    }
    setFile(picked);
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
        ...contextualAudiencePayload(audience, universe, spokespersonId),
        title: title.trim(),
        pdf_data_uri: dataUri,
      });
      setTitle("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      console.error("contextual pdf ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-upload-title">Title</Label>
        <Input
          id="ctx-upload-title"
          data-testid="ctx-upload-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="What is this PDF about?"
          maxLength={500}
          required
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-upload-file">PDF</Label>
        <input
          id="ctx-upload-file"
          data-testid="ctx-upload-file"
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
          data-testid="ctx-upload-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}
      <Button
        type="submit"
        data-testid="ctx-upload-submit"
        disabled={disabled}
      >
        {create.isPending ? "Uploading + extracting…" : "Upload PDF"}
      </Button>
    </form>
  );
}


function ContextualUrlForm({
  workspaceId,
  audience,
  universe,
  spokespersonId,
}: {
  workspaceId: string | undefined;
  audience: AudienceChoice;
  universe: Universe;
  spokespersonId: string;
}) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const create = useCreateKnowledge(workspaceId);
  const disabled =
    !workspaceId || !url.trim() || create.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        ...contextualAudiencePayload(audience, universe, spokespersonId),
        title: title.trim() || undefined,
        source_url_input: url.trim(),
      });
      setTitle("");
      setUrl("");
    } catch (err) {
      console.error("contextual url ingest failed", err);
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-url-input">URL</Label>
        <Input
          id="ctx-url-input"
          data-testid="ctx-url-input"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article-to-ingest"
          required
        />
        <p className="text-xs text-muted-foreground">
          Snapshot at ingest — content is captured as it looks now and
          isn't re-fetched. Delete + re-ingest if you need fresh.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="ctx-url-title">Title (optional)</Label>
        <Input
          id="ctx-url-title"
          data-testid="ctx-url-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Defaults to the page's title tag"
          maxLength={500}
        />
      </div>
      {create.error && (
        <p
          data-testid="ctx-url-error"
          className="text-sm text-destructive"
        >
          {readableError(create.error)}
        </p>
      )}
      <Button
        type="submit"
        data-testid="ctx-url-submit"
        disabled={disabled}
      >
        {create.isPending ? "Fetching + extracting…" : "Ingest URL"}
      </Button>
    </form>
  );
}


function ContextualSearchForm({
  workspaceId,
  audience,
  universe,
  spokespersonId,
}: {
  workspaceId: string | undefined;
  audience: AudienceChoice;
  universe: Universe;
  spokespersonId: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const searchMut = useKnowledgeSearch();
  const create = useCreateKnowledge(workspaceId);
  const [ingestingUrl, setIngestingUrl] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const hits = await searchMut.mutateAsync(query.trim());
      setResults(hits);
    } catch (err) {
      console.error("contextual search failed", err);
      setResults([]);
    }
  }

  async function handleIngest(result: SearchResult) {
    if (!workspaceId) return;
    setIngestingUrl(result.url);
    try {
      await create.mutateAsync({
        workspace: workspaceId,
        ...contextualAudiencePayload(audience, universe, spokespersonId),
        title: result.title,
        source_url_input: result.url,
        via_serper: true,
      });
      setResults((prev) => prev.filter((r) => r.url !== result.url));
    } catch (err) {
      console.error("contextual serper-result ingest failed", err);
    } finally {
      setIngestingUrl(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSearch}>
        <Input
          data-testid="ctx-search-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the web for content to ingest…"
          className="flex-1"
        />
        <Button
          type="submit"
          data-testid="ctx-search-submit"
          disabled={!query.trim() || searchMut.isPending}
        >
          <Search className="mr-2 h-4 w-4" />
          {searchMut.isPending ? "Searching…" : "Search"}
        </Button>
      </form>
      {searchMut.error && (
        <p
          data-testid="ctx-search-error"
          className="text-sm text-destructive"
        >
          {readableError(searchMut.error)}
        </p>
      )}
      {results.length > 0 && (
        <ul
          data-testid="ctx-search-results"
          className="divide-y divide-luxe rounded-md border border-luxe bg-card"
        >
          {results.map((r) => (
            <li
              key={r.url}
              data-testid={`ctx-search-result-${r.position}`}
              className="flex items-start gap-3 px-4 py-3"
            >
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium text-cream" title={r.title}>
                  {r.title}
                </p>
                <p className="truncate text-xs text-fog" title={r.url}>
                  {r.url}
                </p>
                {r.snippet && (
                  <p className="mt-1 line-clamp-2 text-xs text-mist">
                    {r.snippet}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                data-testid={`ctx-search-ingest-${r.position}`}
                disabled={ingestingUrl === r.url}
                onClick={() => handleIngest(r)}
              >
                {ingestingUrl === r.url ? "…" : "Ingest"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
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
