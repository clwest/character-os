/**
 * SectionHeader — V3 editorial dossier-numbering primitive.
 *
 * Renders the parent site's `§ NN — Title` pattern in
 * `font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold`.
 * Per BRAND_IDENTITY_V3.md contract rule 4 (section numbering is
 * canonical). Source pattern: `/24-7-ai-global/src/app/page.tsx`
 * § 01 · § 02 · § 03 · § 04 · § 05 · § 06.
 *
 * Default semantic tag is `div` (the label sits *above* a heading,
 * not as one). Pass `as="h2"` if the consumer wants the label to
 * BE the section heading (rare; most surfaces pair this with an
 * adjacent display headline).
 */
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  /** 1-99. Auto-padded to 2 digits. */
  number: number;
  /** The section name (e.g. "The Charter", "The Suite"). */
  title: string;
  /** Override the wrapper tag. Default `div`. */
  as?: "div" | "h2" | "h3" | "p";
  /** Append extra classes to the wrapper. */
  className?: string;
}

export function SectionHeader({
  number,
  title,
  as: Tag = "div",
  className,
}: SectionHeaderProps) {
  const padded = String(Math.max(1, Math.min(99, number))).padStart(2, "0");
  return (
    <Tag
      data-testid="section-header"
      className={cn(
        "font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold",
        className,
      )}
    >
      § {padded} — {title}
    </Tag>
  );
}
