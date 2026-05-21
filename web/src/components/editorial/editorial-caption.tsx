/**
 * EditorialCaption — V3 "Plate NN" caption primitive.
 *
 * The parent site's hero-portrait caption pattern (page.tsx
 * lines 109-116). Microtype gold label + italic display-serif
 * body, anchored under a hairline. Used for portraits / featured
 * renders / signature artifacts that warrant editorial framing.
 *
 * Default alignment is `right` (matches the hero pattern); pass
 * `align="left"` for left-anchored placements (e.g. a Plate caption
 * pinned to a card's bottom-left).
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EditorialCaptionProps {
  /** "01" or 1 — auto-padded to 2 digits. Free-form strings ("VI") allowed for Roman-numeral plates. */
  plate: number | string;
  /** Caption body. Renders in display-italic. */
  children: ReactNode;
  /** Alignment. Default `right`. */
  align?: "left" | "right" | "center";
  /** Append extra classes to the wrapper. */
  className?: string;
}

function formatPlate(plate: number | string): string {
  if (typeof plate === "number") {
    return String(Math.max(1, Math.min(99, plate))).padStart(2, "0");
  }
  return plate;
}

const ALIGN_CLASSES: Record<NonNullable<EditorialCaptionProps["align"]>, string> = {
  left: "text-left",
  right: "text-right",
  center: "text-center",
};

export function EditorialCaption({
  plate,
  children,
  align = "right",
  className,
}: EditorialCaptionProps) {
  return (
    <div
      data-testid="editorial-caption"
      data-plate={formatPlate(plate)}
      className={cn(
        "max-w-[260px] border-t border-gold/30 pt-4",
        ALIGN_CLASSES[align],
        className,
      )}
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold/80">
        Plate {formatPlate(plate)}
      </div>
      <div className="mt-1 font-display italic text-sm leading-snug text-cream/80">
        {children}
      </div>
    </div>
  );
}
