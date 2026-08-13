/**
 * BridgeUpgradeNudge — Starter-tier gate panel for /workspace/tools (C5.3).
 *
 * Rendered in place of the bridge tool form when the current workspace
 * subscription is Starter tier. The resolver-side gate
 * (`resolve_engine_connection` in EB.2) is the load-bearing enforcement
 * per EB rule 8; this component is the operator-facing surface that
 * both explains why the form is hidden AND acts as the primary upsell
 * discovery point for the engine-bridge feature.
 *
 * Scope: docs/design/BRIDGE_TOOLS_UI_V1.md §"SPA surface" (C5.3 slot in
 * the component tree). The scope-doc component-tree diagram names
 * `/settings/billing` as the CTA target; no such route exists in the
 * SPA today. The link points at `/settings/engine-connections` instead
 * — the same page EB.4 shipped for connection configuration, which
 * carries its own tier-scoped upgrade copy. When a real billing surface
 * lands, update this href in one place.
 *
 * Testid `tools-upgrade-nudge` is preserved from the C5.1 inline
 * placeholder so the tools.test.tsx tier-gate suite keeps passing
 * untouched.
 */
import { Link } from "react-router-dom";

export function BridgeUpgradeNudge() {
  return (
    <div
      data-testid="tools-upgrade-nudge"
      className="rounded-md border border-luxe bg-card p-6"
    >
      <h2 className="font-display text-2xl tracking-tight text-cream">
        Engine bridge is a Pro feature
      </h2>
      <p className="mt-2 text-sm text-mist">
        Bridge tools let your spokespeople answer questions using your own
        configured engine. Upgrade your workspace to unlock the three
        bridge tools + the connection settings panel.
      </p>
      <Link
        data-testid="tools-upgrade-nudge-cta"
        to="/settings/engine-connections"
        className="mt-4 inline-flex items-center gap-1.5 text-sm text-gold hover:underline"
      >
        View engine settings →
      </Link>
    </div>
  );
}
