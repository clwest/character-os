/**
 * HairlineDivider — V3 editorial divider primitive.
 *
 * The parent site's `<span className="h-px w-12 bg-gold/60" />`
 * pattern, plus a gradient variant (`hairline-gold` utility from
 * globals.css). Used as section transitions, masthead underlines,
 * doctrine-quote separators.
 *
 * Source patterns:
 * - solid:   <span className="h-px w-12 bg-gold/60" />
 * - solid wide: <div className="h-px w-32 bg-gold/40" />
 * - gradient (full-width or wide): <div className="h-px hairline-gold" />
 */
import { cn } from "@/lib/utils";

interface HairlineDividerProps {
  /** Width preset. `full` makes it span its container. Default `md`. */
  width?: "xs" | "sm" | "md" | "lg" | "xl" | "full";
  /** Solid bar or gradient fade-in/out. Default `solid`. */
  variant?: "solid" | "gradient";
  /** Gold opacity. `bright` (60%) for default; `muted` (40%) for footer / cite. */
  tone?: "bright" | "muted";
  /** Override the wrapper tag. Default `span` (inline-block). */
  as?: "span" | "div";
  /** Append extra classes. */
  className?: string;
}

const WIDTH_CLASSES: Record<NonNullable<HairlineDividerProps["width"]>, string> = {
  xs: "w-6",
  sm: "w-8",
  md: "w-12",
  lg: "w-16",
  xl: "w-32",
  full: "w-full",
};

export function HairlineDivider({
  width = "md",
  variant = "solid",
  tone = "bright",
  as: Tag = "span",
  className,
}: HairlineDividerProps) {
  const widthClass = WIDTH_CLASSES[width];
  const fillClass =
    variant === "gradient"
      ? "hairline-gold"
      : tone === "bright"
        ? "bg-gold/60"
        : "bg-gold/40";
  return (
    <Tag
      data-testid="hairline-divider"
      data-variant={variant}
      data-tone={tone}
      aria-hidden="true"
      className={cn("block h-px", widthClass, fillClass, className)}
    />
  );
}
