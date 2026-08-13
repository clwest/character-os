/**
 * BridgeResultPanel — polished result surface for /workspace/tools (C5.2).
 *
 * Consumes a succeeded `DispatchResult` from the `useInvokeTool` mutation
 * and renders the bridge answer + a link to the persisted
 * `Asset(BRIDGE_ANSWER)` in the workspace asset library.
 *
 * Scope: docs/design/BRIDGE_TOOLS_UI_V1.md §"SPA surface" (C5.2 slot in
 * the component tree) and §"Test plan" §"C5.2 — result panel".
 *
 * Testids preserved from the C5.1 placeholder so the tools.test.tsx
 * suite keeps passing without edits:
 *   - `tools-result-panel`
 *   - `tools-result-answer`
 *   - `tools-result-asset-link`
 *
 * New C5.2 surface:
 *   - `tools-result-copy` — copy-to-clipboard button (Q-c5-4).
 *
 * Answer rendering is whitespace-preserved plain text. No markdown
 * parser is imported: scope §"Test plan" allows "markdown-lite via
 * existing utility" but the SPA has no such utility today, and adding
 * one would exceed C5.2's ¼-session budget. `whitespace-pre-wrap`
 * covers the common case (line breaks + inline formatting from the
 * engine) without inventing a dependency.
 */
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Copy, Sparkles } from "lucide-react";

import type { DispatchResult } from "@/lib/api/realtime";

interface BridgeResultPanelProps {
  result: DispatchResult;
}

export function BridgeResultPanel({ result }: BridgeResultPanelProps) {
  const payload = (result.result ?? {}) as {
    answer?: unknown;
    asset_id?: unknown;
    error?: unknown;
  };
  const answer =
    typeof payload.answer === "string" ? payload.answer : "";
  const engineError =
    typeof payload.error === "string" && payload.error.length > 0
      ? payload.error
      : "";
  const assetId =
    typeof payload.asset_id === "string" && payload.asset_id.length > 0
      ? payload.asset_id
      : null;

  const hasAnswer = answer.trim().length > 0;

  return (
    <div
      data-testid="tools-result-panel"
      className="mt-2 flex flex-col gap-3 rounded-md border border-luxe bg-background p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-fog">
          <Sparkles className="h-3.5 w-3.5" />
          Answer
        </div>
        {hasAnswer && (
          <CopyAnswerButton value={answer} />
        )}
      </div>

      {/* F-11 fix — executor timeouts / HTTP failures return
          {error, no answer}. Surface the error verbatim so the
          operator sees "timed out after 25s" instead of a mute
          "(no answer content returned)". */}
      {hasAnswer ? (
        <p
          data-testid="tools-result-answer"
          className="whitespace-pre-wrap text-sm leading-relaxed text-cream"
        >
          {answer}
        </p>
      ) : engineError ? (
        <p
          data-testid="tools-result-error"
          className="whitespace-pre-wrap text-sm leading-relaxed text-amber-400"
        >
          {engineError}
        </p>
      ) : (
        <p
          data-testid="tools-result-answer"
          className="whitespace-pre-wrap text-sm leading-relaxed text-cream"
        >
          (no answer content returned)
        </p>
      )}

      {assetId && (
        <div className="pt-1">
          <Link
            data-testid="tools-result-asset-link"
            to={`/workspace/assets/${assetId}`}
            className="text-xs text-gold hover:underline"
          >
            View in asset library →
          </Link>
        </div>
      )}
    </div>
  );
}

// ---- Copy button ------------------------------------------------
//
// shadcn "copy" pattern: mirrors the inline helper in
// routes/workspace/assets.$id.tsx (Check on success, resets after
// 2s). Kept local to avoid a broader refactor of the assets page;
// if a third consumer appears, promote to components/ui/copy-button.

function CopyAnswerButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [value]);

  return (
    <button
      type="button"
      data-testid="tools-result-copy"
      aria-label={copied ? "Copied" : "Copy answer"}
      onClick={handleCopy}
      className="inline-flex items-center gap-1 text-xs text-fog hover:text-gold transition-colors"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}
