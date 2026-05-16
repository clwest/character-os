/**
 * K6.4 v1.2 — verification_status badge.
 *
 * Shared across the composition detail page + conversation
 * message bubbles so the four-state semantic stays visually
 * consistent. Empty status (pre-v1.2 row or USER message)
 * renders nothing.
 *
 * State → visual mapping anchors on
 * `apps.compositions.models.VerificationStatus` semantics:
 *
 * - `verified`               — emerald check; the verifier
 *                              ran cleanly (or with warnings
 *                              the operator chose to ship).
 * - `trusted_passthrough`    — muted info icon; no LLM ran,
 *                              operator text flowed through.
 * - `skipped`                — amber/muted; verifier was
 *                              `off`; no checking happened.
 * - `rejected`               — red; strict mode blocked.
 */
import { AlertTriangle, CheckCircle2, Circle, ShieldOff } from "lucide-react";

export type VerificationStatus =
  | ""
  | "verified"
  | "trusted_passthrough"
  | "skipped"
  | "rejected";

interface VerificationStatusBadgeProps {
  status: VerificationStatus | string;
  size?: "sm" | "md";
  className?: string;
}

const STATE_LABELS: Record<Exclude<VerificationStatus, "">, string> = {
  verified: "Verified",
  trusted_passthrough: "Operator-typed",
  skipped: "Verifier off",
  rejected: "Strict — rejected",
};

const STATE_STYLES: Record<Exclude<VerificationStatus, "">, string> = {
  verified:
    "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
  trusted_passthrough:
    "border-muted-foreground/30 bg-muted/30 text-muted-foreground",
  skipped:
    "border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-300",
  rejected:
    "border-destructive/40 bg-destructive/5 text-destructive",
};

export function VerificationStatusBadge({
  status,
  size = "sm",
  className = "",
}: VerificationStatusBadgeProps) {
  if (!status || !(status in STATE_LABELS)) return null;
  const known = status as Exclude<VerificationStatus, "">;
  const Icon =
    known === "verified"
      ? CheckCircle2
      : known === "rejected"
        ? ShieldOff
        : known === "skipped"
          ? AlertTriangle
          : Circle;
  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";
  const textSize = size === "sm" ? "text-[10px]" : "text-xs";
  return (
    <span
      className={
        `inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono ${textSize} uppercase tracking-[0.18em] ${STATE_STYLES[known]} ${className}`
      }
      data-testid={`verification-status-${known}`}
      title={`K6.4 verification: ${STATE_LABELS[known]}`}
    >
      <Icon className={iconSize} />
      {STATE_LABELS[known]}
    </span>
  );
}
