/**
 * /settings/engine-connections — EB.4 (SESSION 218/2887 side-step).
 *
 * Operator-facing SPA panel for per-workspace EngineConnection config.
 * Wraps the DRF surface shipped in SESSION 217 (EB.3): CRUD +
 * test_ping. See docs/design/ENGINE_BRIDGE_V1.md.
 *
 * Contract rules honored on this surface:
 *   - Rule 1+2: workspace inference is server-side; the SPA never
 *     accepts or forwards a workspace_id in the create body.
 *   - Rule 4: engine_token is write-only. This UI shows only the
 *     ****last4 preview after save; the plaintext is never held in
 *     state longer than needed for the create/patch mutation call.
 *   - Rule 7: test_ping is a config check (no audit row).
 *   - Rule 8: Pro+ tier gate. Starter workspaces see an upgrade nudge.
 *
 * Env-var fallback is preserved: the resolver
 * (`shell/apps/realtime/engine_bridge.py`) still consults
 * UDB_PA_API_TOKEN when no DB row exists. This UI does not remove
 * that fallback; it just gives the operator a way to migrate onto
 * the row-based path.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Pencil,
  Radio,
  Save,
  ServerCog,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { useMe, useSubscription } from "@/lib/api/workspaces";
import {
  type EngineConnection,
  type PatchEngineConnectionInput,
  type TestPingResponse,
  useCreateEngineConnection,
  useDeleteEngineConnection,
  useEngineConnections,
  usePatchEngineConnection,
  useTestPingEngineConnection,
} from "@/lib/api/engine-connections";

// -------------------- copy tables --------------------

const PAGE_TITLE = "Engine bridge connections";
const PAGE_SUBTITLE =
  "Configure the external engine your spokespeople reach through the bridge tools (`consult_engine`, `query_spider_data`, `agent_consult`).";
const DOC_LINK_TEXT = "See ENGINE_BRIDGE_V1.md for the contract.";
const EMPTY_STATE_HINT =
  "No connection configured yet. Paste your engine URL and access token to enable the bridge tools during avatar sessions.";
const UPGRADE_NUDGE_TITLE = "Available on Pro and above";
const UPGRADE_NUDGE_BODY =
  "The engine bridge lets your spokespeople call back into your own AI stack from a live conversation. Upgrade your workspace to configure a connection.";
const STARTER_TIERS = new Set(["starter"]);

// -------------------- helpers --------------------

const PRO_OR_HIGHER = new Set(["pro", "agency"]);

function isProOrHigher(tier: string | undefined | null): boolean {
  if (!tier) return false;
  return PRO_OR_HIGHER.has(tier.toLowerCase());
}

function isStarter(tier: string | undefined | null): boolean {
  if (!tier) return false;
  return STARTER_TIERS.has(tier.toLowerCase());
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function isValidUrl(candidate: string): boolean {
  if (!candidate) return false;
  try {
    const parsed = new URL(candidate);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

// -------------------- test-ping result badge --------------------

function TestPingResultBadge({
  result,
}: {
  result: TestPingResponse | null | undefined;
}) {
  if (!result) return null;
  const ok = result.status_code !== null && result.status_code >= 200 && result.status_code < 300;
  const label = ok
    ? `Reachable — HTTP ${result.status_code} in ${result.latency_ms}ms`
    : result.error_message
      ? result.error_message
      : `HTTP ${result.status_code ?? "?"} — see preview`;
  return (
    <span
      className={
        ok
          ? "inline-flex items-center gap-1 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-500"
          : "inline-flex items-center gap-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-rose-500"
      }
      data-testid={ok ? "test-ping-ok" : "test-ping-fail"}
    >
      {ok ? <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> : <XCircle className="h-3 w-3" aria-hidden="true" />}
      {label}
    </span>
  );
}

// -------------------- create form --------------------

function CreateConnectionForm() {
  const create = useCreateEngineConnection();
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [label, setLabel] = useState("");

  const urlOk = isValidUrl(url);
  const tokenOk = token.trim().length > 0;
  const canSubmit = urlOk && tokenOk && !create.isPending;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await create
      .mutateAsync({
        engine_url: url.trim(),
        engine_token: token,
        label: label.trim(),
      })
      .then(() => {
        // Clear the plaintext token from memory as soon as the mutation
        // settles. The preview is the server's job from here on.
        setToken("");
      })
      .catch(() => {
        // Errors surface below; keep the form values so the operator
        // can correct without retyping the token.
      });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-lg border border-fog/30 bg-fog/5 p-6"
      data-testid="engine-connections-create-form"
    >
      <h2 className="mb-1 text-lg font-medium">Add a connection</h2>
      <p className="mb-4 text-sm text-fog">{EMPTY_STATE_HINT}</p>

      <label className="mb-3 block text-sm">
        <span className="mb-1 block font-medium">Engine URL</span>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://your-engine.example.com"
          required
          autoComplete="off"
          className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 font-mono text-sm"
          data-testid="engine-url-input"
        />
      </label>

      <label className="mb-3 block text-sm">
        <span className="mb-1 block font-medium">Access token</span>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Paste the engine bearer token"
          required
          autoComplete="off"
          spellCheck={false}
          className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 font-mono text-sm"
          data-testid="engine-token-input"
        />
        <span className="mt-1 block text-xs text-fog">
          Stored server-side; never returned to the browser after save.
        </span>
      </label>

      <label className="mb-4 block text-sm">
        <span className="mb-1 block font-medium">Label (optional)</span>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Prod the sibling project, staging, etc."
          maxLength={120}
          className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 text-sm"
          data-testid="engine-label-input"
        />
      </label>

      {create.error ? (
        <div className="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-500" role="alert">
          {create.error instanceof ApiError
            ? `Save failed (HTTP ${create.error.status}). ${JSON.stringify(create.error.body ?? {})}`
            : "Save failed. Please try again."}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 rounded-md border border-fog/40 bg-fog/10 px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="engine-create-submit"
      >
        {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        Save connection
      </button>
    </form>
  );
}

// -------------------- edit form (inline patch) --------------------

function EditConnectionForm({
  connection,
  onDone,
}: {
  connection: EngineConnection;
  onDone: () => void;
}) {
  const patch = usePatchEngineConnection();
  const [url, setUrl] = useState(connection.engine_url);
  const [label, setLabel] = useState(connection.label);
  const [enabled, setEnabled] = useState(connection.enabled);
  const [rotateToken, setRotateToken] = useState(false);
  const [newToken, setNewToken] = useState("");

  const urlOk = isValidUrl(url);
  const tokenOk = !rotateToken || newToken.trim().length > 0;
  const canSubmit = urlOk && tokenOk && !patch.isPending;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    const input: PatchEngineConnectionInput = {};
    if (url.trim() !== connection.engine_url) input.engine_url = url.trim();
    if (label.trim() !== connection.label) input.label = label.trim();
    if (enabled !== connection.enabled) input.enabled = enabled;
    if (rotateToken && newToken) input.engine_token = newToken;
    if (Object.keys(input).length === 0) {
      onDone();
      return;
    }
    await patch
      .mutateAsync({ id: connection.id, input })
      .then(() => {
        setNewToken("");
        onDone();
      })
      .catch(() => {
        // stay in edit mode so the operator can correct.
      });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-lg border border-fog/30 bg-fog/5 p-6"
      data-testid="engine-connections-edit-form"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium">Edit connection</h2>
        <button
          type="button"
          onClick={onDone}
          className="inline-flex items-center gap-1 text-sm text-fog hover:text-current"
          data-testid="engine-edit-cancel"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          Cancel
        </button>
      </div>

      <label className="mb-3 block text-sm">
        <span className="mb-1 block font-medium">Engine URL</span>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          autoComplete="off"
          className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 font-mono text-sm"
          data-testid="engine-url-input"
        />
      </label>

      <label className="mb-3 block text-sm">
        <span className="mb-1 block font-medium">Label</span>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          maxLength={120}
          className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 text-sm"
          data-testid="engine-label-input"
        />
      </label>

      <label className="mb-3 flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4"
          data-testid="engine-enabled-toggle"
        />
        <span>Enabled — bridge tools will resolve to this row.</span>
      </label>

      <div className="mb-3 rounded-md border border-fog/30 p-3">
        <button
          type="button"
          onClick={() => setRotateToken((v) => !v)}
          className="inline-flex items-center gap-1 text-sm font-medium"
          data-testid="engine-rotate-token-toggle"
          aria-expanded={rotateToken}
        >
          <ChevronRight
            className={`h-4 w-4 transition-transform ${rotateToken ? "rotate-90" : ""}`}
            aria-hidden="true"
          />
          Rotate token
        </button>
        {rotateToken ? (
          <div className="mt-3">
            <p className="mb-2 text-xs text-fog">
              Current token stored as <span className="font-mono">{connection.engine_token_preview || "(none)"}</span>. Leave empty and un-expand to keep it.
            </p>
            <input
              type="password"
              value={newToken}
              onChange={(e) => setNewToken(e.target.value)}
              placeholder="New access token"
              autoComplete="off"
              spellCheck={false}
              className="w-full rounded-md border border-fog/30 bg-transparent px-3 py-2 font-mono text-sm"
              data-testid="engine-new-token-input"
            />
          </div>
        ) : null}
      </div>

      {patch.error ? (
        <div className="mb-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-500" role="alert">
          {patch.error instanceof ApiError
            ? `Save failed (HTTP ${patch.error.status}). ${JSON.stringify(patch.error.body ?? {})}`
            : "Save failed. Please try again."}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 rounded-md border border-fog/40 bg-fog/10 px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="engine-edit-submit"
      >
        {patch.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        Save changes
      </button>
    </form>
  );
}

// -------------------- read-only card --------------------

function ConnectionCard({
  connection,
  onEdit,
}: {
  connection: EngineConnection;
  onEdit: () => void;
}) {
  const testPing = useTestPingEngineConnection();
  const del = useDeleteEngineConnection();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const testResult = testPing.data;

  async function onDelete() {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    await del.mutateAsync(connection.id).catch(() => {
      setConfirmingDelete(false);
    });
  }

  return (
    <div
      className="rounded-lg border border-fog/30 bg-fog/5 p-6"
      data-testid="engine-connection-card"
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium">
            {connection.label || "the sibling project engine bridge"}
          </h2>
          <p className="mt-1 flex items-center gap-2 text-sm text-fog">
            <span
              className={
                connection.enabled
                  ? "inline-flex items-center gap-1 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-500"
                  : "inline-flex items-center gap-1 rounded-md border border-fog/30 bg-fog/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-fog"
              }
              data-testid="engine-enabled-badge"
            >
              {connection.enabled ? "Enabled" : "Disabled"}
            </span>
            <span className="font-mono text-xs">{connection.engine_kind}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex items-center gap-1 rounded-md border border-fog/40 bg-fog/10 px-3 py-1.5 text-sm"
            data-testid="engine-edit-button"
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Edit
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={del.isPending}
            className="inline-flex items-center gap-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-sm text-rose-500 disabled:opacity-50"
            data-testid="engine-delete-button"
          >
            {del.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {confirmingDelete ? "Click again to confirm" : "Delete"}
          </button>
        </div>
      </div>

      <dl className="mb-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-[0.18em] text-fog">Engine URL</dt>
          <dd className="mt-1 break-all font-mono">{connection.engine_url}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.18em] text-fog">Token</dt>
          <dd className="mt-1 font-mono">{connection.engine_token_preview || "(none)"}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.18em] text-fog">Last tested</dt>
          <dd className="mt-1">{formatTimestamp(connection.last_tested_at)}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.18em] text-fog">Last status</dt>
          <dd className="mt-1 font-mono">{connection.last_test_status ?? "—"}</dd>
        </div>
      </dl>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => testPing.mutate(connection.id)}
          disabled={testPing.isPending}
          className="inline-flex items-center gap-2 rounded-md border border-fog/40 bg-fog/10 px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="engine-test-ping-button"
        >
          {testPing.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Radio className="h-4 w-4" aria-hidden="true" />
          )}
          Run test ping
        </button>
        <TestPingResultBadge result={testResult} />
      </div>

      {testResult && testResult.response_preview ? (
        <details className="mt-3 rounded-md border border-fog/30 bg-fog/5 p-3 text-xs">
          <summary className="cursor-pointer font-medium">Response preview</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono">
            {testResult.response_preview}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

// -------------------- upgrade nudge (Starter tier) --------------------

function UpgradeNudge() {
  return (
    <div
      className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-6"
      data-testid="engine-connections-upgrade-nudge"
      role="status"
    >
      <div className="mb-2 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" />
        <h2 className="text-lg font-medium">{UPGRADE_NUDGE_TITLE}</h2>
      </div>
      <p className="text-sm text-fog">{UPGRADE_NUDGE_BODY}</p>
    </div>
  );
}

// -------------------- route component --------------------

export function EngineConnectionsRoute() {
  const me = useMe();
  const subscription = useSubscription();
  const connections = useEngineConnections();
  const [editingId, setEditingId] = useState<string | null>(null);

  const tier = subscription.data?.tier;
  const starter = isStarter(tier);
  const proOrHigher = isProOrHigher(tier);

  const activeConnection = useMemo<EngineConnection | undefined>(() => {
    const rows = connections.data ?? [];
    return rows[0];
  }, [connections.data]);

  const editingConnection = editingId
    ? connections.data?.find((c) => c.id === editingId)
    : undefined;

  const loading =
    me.isLoading || subscription.isLoading || connections.isLoading;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-fog">
          <Link to="/dashboard" className="hover:text-current">
            Dashboard
          </Link>
          <ChevronRight className="h-3 w-3" aria-hidden="true" />
          <span>Settings</span>
        </div>
        <h1 className="flex items-center gap-2 text-2xl font-medium">
          <ServerCog className="h-6 w-6" aria-hidden="true" />
          {PAGE_TITLE}
        </h1>
        <p className="mt-2 text-sm text-fog">{PAGE_SUBTITLE}</p>
        <p className="mt-1 text-xs text-fog" data-testid="doc-link-hint">
          {DOC_LINK_TEXT}
        </p>
      </header>

      {loading ? (
        <div className="rounded-lg border border-fog/30 bg-fog/5 p-6">
          <div className="flex items-center gap-2 text-sm text-fog">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading connection state…
          </div>
        </div>
      ) : connections.isError ? (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-500" role="alert">
          Failed to load connections.
          {connections.error instanceof ApiError
            ? ` HTTP ${connections.error.status}.`
            : null}
        </div>
      ) : starter ? (
        <UpgradeNudge />
      ) : proOrHigher ? (
        activeConnection ? (
          editingConnection ? (
            <EditConnectionForm
              connection={editingConnection}
              onDone={() => setEditingId(null)}
            />
          ) : (
            <ConnectionCard
              connection={activeConnection}
              onEdit={() => setEditingId(activeConnection.id)}
            />
          )
        ) : (
          <CreateConnectionForm />
        )
      ) : (
        // Unknown tier or subscription not resolved yet — surface a
        // neutral "still loading" so we never render the create form
        // against a tier we haven't confirmed.
        <div className="rounded-lg border border-fog/30 bg-fog/5 p-6 text-sm text-fog">
          Workspace tier could not be resolved. Refresh the page or reach out to support.
        </div>
      )}
    </div>
  );
}
