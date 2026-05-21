/**
 * /dev/brand-v3 — V3 editorial primitives showcase.
 *
 * Reference page for the V3.2 component library. Every editorial
 * primitive renders in context with sample copy lifted from the
 * parent site (`/24-7-ai-global/src/app/page.tsx`). No real data,
 * no backend calls — purely a visual + a11y reference.
 *
 * Naming convention: file lives under `_dev/` (the same prefix
 * `_layout.tsx` uses) to signal "tooling, not product surface."
 */
import {
  DoctrineQuote,
  EditorialCaption,
  EngagementBrief,
  HairlineDivider,
  SectionHeader,
} from "@/components/editorial";

export function BrandV3PreviewRoute() {
  return (
    <main
      data-testid="brand-v3-preview"
      className="min-h-screen bg-ink text-cream"
    >
      <div className="mx-auto max-w-[1100px] px-6 py-16 lg:px-10 lg:py-24">
        {/* Page header */}
        <header className="flex flex-col gap-3">
          <SectionHeader number={0} title="Brand Identity V3 — Primitives" />
          <h1
            className="font-display text-5xl leading-[0.95] tracking-tight md:text-6xl"
            style={
              { fontVariationSettings: '"opsz" 96, "SOFT" 30, "WONK" 1' } as React.CSSProperties
            }
          >
            Always <span className="italic">on.</span>{" "}
            Always <span className="italic gold-text">smart.</span>
          </h1>
          <p className="max-w-xl text-mist">
            Reusable editorial primitives ported from{" "}
            <code className="font-mono text-xs">/24-7-ai-global/</code>.
            Reference page for SESSION 209's V3.2 token + component slice.
          </p>
          <HairlineDivider width="xl" className="mt-4" />
        </header>

        {/* SectionHeader showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={1} title="SectionHeader" />
          <h2 className="font-display text-3xl tracking-tight">
            Editorial dossier numbering.
          </h2>
          <p className="max-w-xl text-mist text-sm leading-relaxed">
            Numbers auto-pad to two digits. Tracking-[0.34em] is
            load-bearing — the editorial register depends on it.
          </p>
          <div className="grid gap-3 rounded border border-luxe bg-night/40 p-6">
            <SectionHeader number={1} title="The Charter" />
            <SectionHeader number={2} title="The Suite" />
            <SectionHeader number={12} title="The Lab" />
          </div>
        </section>

        {/* HairlineDivider showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={2} title="HairlineDivider" />
          <h2 className="font-display text-3xl tracking-tight">
            Gold separators in five widths.
          </h2>
          <div className="flex flex-col gap-5 rounded border border-luxe bg-night/40 p-6">
            <div className="flex items-center gap-4">
              <HairlineDivider width="xs" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                xs · w-6
              </span>
            </div>
            <div className="flex items-center gap-4">
              <HairlineDivider width="sm" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                sm · w-8
              </span>
            </div>
            <div className="flex items-center gap-4">
              <HairlineDivider width="md" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                md · w-12 (default)
              </span>
            </div>
            <div className="flex items-center gap-4">
              <HairlineDivider width="lg" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                lg · w-16
              </span>
            </div>
            <div className="flex items-center gap-4">
              <HairlineDivider width="xl" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                xl · w-32
              </span>
            </div>
            <div className="flex flex-col gap-2">
              <HairlineDivider width="full" variant="gradient" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                full · gradient (fades in and out on both ends)
              </span>
            </div>
            <div className="flex items-center gap-4">
              <HairlineDivider width="md" tone="muted" />
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                md · muted (gold/40 — for cite footers)
              </span>
            </div>
          </div>
        </section>

        {/* EditorialCaption showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={3} title="EditorialCaption" />
          <h2 className="font-display text-3xl tracking-tight">
            Plate <span className="italic">NN</span> caption.
          </h2>
          <div className="grid grid-cols-1 gap-6 rounded border border-luxe bg-night/40 p-6 md:grid-cols-2">
            <div className="flex flex-col items-end">
              <EditorialCaption plate={1}>
                The proprietor of 24/7 Global AI. Pocket watch by
                appointment; the hour is irrelevant.
              </EditorialCaption>
              <span className="mt-3 font-mono text-xs uppercase tracking-[0.22em] text-fog">
                plate={"{1}"} · default right-aligned
              </span>
            </div>
            <div className="flex flex-col">
              <EditorialCaption plate="VI" align="left">
                Character OS — Lab VI. Type your business. Click. Get a
                video ad.
              </EditorialCaption>
              <span className="mt-3 font-mono text-xs uppercase tracking-[0.22em] text-fog">
                plate="VI" · left-aligned · Roman-numeral
              </span>
            </div>
          </div>
        </section>

        {/* DoctrineQuote showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={4} title="DoctrineQuote" />
          <h2 className="font-display text-3xl tracking-tight">
            Manifesto pull-quote.
          </h2>
          <div className="rounded border border-luxe bg-night/40 p-10 md:p-16">
            <DoctrineQuote source="The 24/7 Doctrine · 2026 Edition">
              The future belongs to those who put their{" "}
              <em className="italic">decisions</em> on autopilot and
              reserve their <em className="italic gold-text">judgment</em>{" "}
              for what only a human can do.
            </DoctrineQuote>
          </div>
        </section>

        {/* EngagementBrief showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={5} title="EngagementBrief" />
          <h2 className="font-display text-3xl tracking-tight">
            Editorial dossier card.
          </h2>
          <p className="max-w-xl text-mist text-sm leading-relaxed">
            Microtype gold title above a definition list. Last row's
            emphasis is the brief's signature hook ("Reply · By morning").
          </p>
          <div className="rounded border border-luxe bg-night/40 p-8">
            <EngagementBrief
              entries={[
                { label: "Cadence", value: "Quarterly · ongoing" },
                { label: "Format", value: "Embedded studio" },
                { label: "Discretion", value: "Implicit" },
                { label: "Reply", value: "By morning", emphasis: true },
              ]}
            />
          </div>
        </section>

        {/* Utilities showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={6} title="Inline utilities" />
          <h2 className="font-display text-3xl tracking-tight">
            <span className="gold-text">.gold-text</span> ·{" "}
            <span className="gold-stroke">.gold-stroke</span>
          </h2>
          <div className="flex flex-col gap-6 rounded border border-luxe bg-night/40 p-6">
            <div className="flex items-baseline gap-6">
              <span className="font-display text-5xl">
                Always <span className="italic gold-text">smart.</span>
              </span>
              <code className="font-mono text-xs text-fog">.gold-text</code>
            </div>
            <div className="flex items-baseline gap-6">
              <span className="font-display text-5xl">
                Always <span className="italic gold-stroke">global.</span>
              </span>
              <code className="font-mono text-xs text-fog">.gold-stroke</code>
            </div>
            <div className="luxe-shadow rounded border border-luxe bg-midnight/60 p-6">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
                .luxe-shadow
              </p>
              <p className="mt-2 text-cream/80">
                Card with inset gold rim + ambient glow + deep direct.
              </p>
            </div>
          </div>
        </section>

        {/* Animations showcase */}
        <section className="mt-20 flex flex-col gap-6">
          <SectionHeader number={7} title="Animations" />
          <h2 className="font-display text-3xl tracking-tight">
            Six keyframes.
          </h2>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded border border-luxe bg-gold/10 md:grid-cols-3">
            <AnimDemo label="animate-rise" cls="animate-rise" />
            <AnimDemo
              label="animate-orbit"
              cls="animate-orbit"
              shape="orbit"
            />
            <AnimDemo
              label="animate-shimmer"
              cls="animate-shimmer"
              shape="shimmer"
            />
            <AnimDemo
              label="animate-pulse-soft"
              cls="animate-pulse-soft"
              shape="pulse"
            />
            <AnimDemo
              label="animate-orbit-slow"
              cls="animate-orbit-slow"
              shape="orbit"
            />
            <AnimDemo
              label="animate-orbit-fast"
              cls="animate-orbit-fast"
              shape="orbit"
            />
          </div>
        </section>

        <footer className="mt-32 border-t border-luxe pt-8">
          <div className="flex flex-col items-baseline justify-between gap-3 font-mono text-[10px] uppercase tracking-[0.22em] text-fog md:flex-row">
            <span>Brand Identity V3 — Primitives · SESSION 209</span>
            <span>
              Source ·{" "}
              <code className="text-gold/80">
                /Users/donkeyking/development/24-7-ai-global/
              </code>
            </span>
          </div>
        </footer>
      </div>
    </main>
  );
}

// ---- Local helpers ----------------------------------------------

function AnimDemo({
  label,
  cls,
  shape = "rise",
}: {
  label: string;
  cls: string;
  shape?: "rise" | "orbit" | "shimmer" | "pulse";
}) {
  if (shape === "orbit") {
    return (
      <div className="flex h-32 items-center justify-center bg-ink">
        <div className="relative h-16 w-16">
          <div className="absolute inset-0 rounded-full border border-gold/30" />
          <div className={`absolute inset-0 ${cls}`}>
            <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">
              <div className="h-2 w-2 rounded-full bg-gold shadow-[0_0_24px_4px_rgba(201,169,97,0.6)]" />
            </div>
          </div>
        </div>
        <span className="ml-4 font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
          {label}
        </span>
      </div>
    );
  }
  if (shape === "shimmer" || shape === "pulse") {
    return (
      <div className="flex h-32 items-center justify-center bg-ink">
        <div className={`h-8 w-32 rounded bg-gold ${cls}`} />
        <span className="ml-4 font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
          {label}
        </span>
      </div>
    );
  }
  // rise (one-shot — re-trigger by keying the element if you want a loop)
  return (
    <div className="flex h-32 items-center justify-center bg-ink">
      <div className={`flex flex-col items-center gap-1 ${cls}`}>
        <div className="h-2 w-12 rounded bg-gold" />
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
          {label}
        </span>
      </div>
    </div>
  );
}
