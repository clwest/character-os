/**
 * DoctrineQuote — V3 editorial pull-quote primitive.
 *
 * The parent site's § 05 "The Position" block: oversized gold-
 * italic quote marks flanking a centered display-serif line,
 * with a hairline + microtype citation below. Source pattern:
 * `/24-7-ai-global/src/app/page.tsx` lines 410-424.
 *
 * Reserved for editorial moments — manifestos, brand-defining
 * quotes, season-opening doctrine. Don't overuse; the visual
 * weight depends on rarity.
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { HairlineDivider } from "./hairline-divider";

interface DoctrineQuoteProps {
  /** Quote body. Renders in display-serif at large sizes. */
  children: ReactNode;
  /** Citation line below the hairline (e.g. "The 24/7 Doctrine · 2026 Edition"). */
  source?: string;
  /** Override the size cap. Default `lg` (5xl on md+). `sm` for inline use. */
  size?: "sm" | "md" | "lg";
  /** Append extra classes to the wrapper. */
  className?: string;
}

const BODY_SIZE: Record<NonNullable<DoctrineQuoteProps["size"]>, string> = {
  sm: "text-xl md:text-2xl leading-snug",
  md: "text-2xl md:text-4xl leading-[1.2]",
  lg: "text-3xl md:text-5xl leading-[1.15]",
};

const MARK_SIZE: Record<NonNullable<DoctrineQuoteProps["size"]>, string> = {
  sm: "text-3xl",
  md: "text-5xl",
  lg: "text-6xl",
};

export function DoctrineQuote({
  children,
  source,
  size = "lg",
  className,
}: DoctrineQuoteProps) {
  return (
    <blockquote
      data-testid="doctrine-quote"
      className={cn("text-center", className)}
    >
      <p
        className={cn(
          "font-display tracking-tight text-balance",
          BODY_SIZE[size],
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "mr-2 align-top font-display italic text-gold/60",
            MARK_SIZE[size],
          )}
        >
          &ldquo;
        </span>
        {children}
        <span
          aria-hidden="true"
          className={cn(
            "ml-2 align-bottom font-display italic text-gold/60",
            MARK_SIZE[size],
          )}
        >
          &rdquo;
        </span>
      </p>
      {source && (
        <footer className="mt-10 flex flex-col items-center gap-2">
          <HairlineDivider width="lg" tone="muted" />
          <cite
            data-testid="doctrine-quote-source"
            className="not-italic font-mono text-[11px] uppercase tracking-[0.34em] text-mist/80"
          >
            {source}
          </cite>
        </footer>
      )}
    </blockquote>
  );
}
