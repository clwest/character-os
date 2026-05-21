/**
 * /about — parent company narrative.
 *
 * B5 (SESSION 178) — first dedicated 24/7 GLOBAL AI surface in
 * the SPA. Mirrors `docs/247_GLOBAL_AI_OVERVIEW.md` (parent
 * narrative) using the existing `BRAND.parent` config so no
 * copy is duplicated. ParentBrandChip in the header links here.
 *
 * V3.7 (SESSION 209) — full editorial register applied per
 * BRAND_IDENTITY_V3. Section-dossier numbering, italic-gold
 * accents on the hero, hairline-gold dividers, DoctrineQuote
 * for the positioning line, EngagementBrief for the contact.
 *
 * Per BRAND_ECOSYSTEM_V1 contract rule 3, every string flows
 * through the brand layer — no hardcoded company strings.
 */
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { parentBrand, productFamily } from "@/lib/brand";
import {
  DoctrineQuote,
  EngagementBrief,
  HairlineDivider,
  SectionHeader,
} from "@/components/editorial";

export function AboutRoute() {
  return (
    <div className="flex flex-col gap-16 py-6" data-testid="about-route">
      <Hero />
      <Doctrine />
      <ProductFamilyPanel />
      <ContactPanel />
    </div>
  );
}

function Hero() {
  return (
    <header
      className="relative flex flex-col gap-4 pb-10"
      data-testid="about-hero"
    >
      <div className="flex items-center gap-3">
        <span
          className="h-1.5 w-1.5 rounded-full bg-gold shadow-[0_0_8px_2px_rgba(201,169,97,0.4)]"
          aria-hidden="true"
        />
        <span className="font-mono text-[11px] uppercase tracking-[0.34em] text-gold">
          {parentBrand.tagline}
        </span>
      </div>
      <h1 className="font-display text-5xl leading-[0.95] tracking-tight text-cream md:text-6xl">
        {parentBrand.name.split(" ").map((word, i, arr) =>
          i === arr.length - 1 ? (
            <span key={i} className="italic gold-text">
              {word}
            </span>
          ) : (
            <span key={i}>{word} </span>
          ),
        )}
      </h1>
      <p className="max-w-2xl font-display text-lg leading-relaxed text-mist md:text-xl">
        {parentBrand.description}
      </p>
      <p className="max-w-3xl text-base leading-relaxed text-cream/90">
        {parentBrand.positioning}
      </p>
      <div
        className="hairline-gold absolute inset-x-0 bottom-0 h-px"
        aria-hidden="true"
      />
    </header>
  );
}

function Doctrine() {
  return (
    <section className="flex flex-col gap-6 py-6" data-testid="about-doctrine">
      <SectionHeader number={1} title="The Position" />
      <DoctrineQuote source="The 24/7 Doctrine · 2026 Edition">
        The future belongs to those who put their{" "}
        <em className="italic">decisions</em> on autopilot and reserve
        their <em className="italic gold-text">judgment</em> for what
        only a human can do.
      </DoctrineQuote>
    </section>
  );
}

function ProductFamilyPanel() {
  return (
    <section className="flex flex-col gap-5" data-testid="about-products">
      <SectionHeader number={2} title="Product family" />
      <header className="flex items-baseline justify-between border-b border-luxe pb-3">
        <h2 className="font-display text-2xl tracking-tight text-cream md:text-3xl">
          What we're <span className="italic gold-text">building.</span>
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-fog">
          {productFamily.filter((p) => p.status === "live").length} live ·{" "}
          {productFamily.filter((p) => p.status === "reserved").length} reserved
        </span>
      </header>
      <ul className="flex flex-col">
        {productFamily.map((p) => (
          <ProductRow key={p.slug} product={p} />
        ))}
      </ul>
    </section>
  );
}

function ProductRow({
  product,
}: {
  product: (typeof productFamily)[number];
}) {
  const isLive = product.status === "live";
  return (
    <li
      className="flex items-center justify-between gap-4 border-b border-luxe py-4 transition-colors last:border-b-0 hover:bg-gold/5"
      data-testid={`about-product-${product.slug}`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline gap-3">
          <span
            className={
              "font-display text-lg" +
              (isLive ? " text-cream" : " text-fog")
            }
          >
            {product.name}
          </span>
          <StatusPill status={product.status} />
        </div>
        <p className="text-sm text-mist">{product.subtitle}</p>
      </div>
      {isLive && (
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-gold transition-colors hover:text-gold-bright"
        >
          Open
          <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </li>
  );
}

function StatusPill({ status }: { status: "live" | "reserved" }) {
  if (status === "live") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-success/15 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.22em] text-success">
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-success"
          aria-hidden="true"
        />
        Live
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full border border-luxe bg-card px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.22em] text-fog">
      Reserved
    </span>
  );
}

function ContactPanel() {
  return (
    <section className="flex flex-col gap-5" data-testid="about-contact">
      <SectionHeader number={3} title="Engage" />
      <div className="grid gap-8 md:grid-cols-12">
        <div className="md:col-span-7">
          <h2 className="font-display text-3xl tracking-tight text-cream md:text-4xl">
            Send a <span className="italic gold-text">brief.</span>
          </h2>
          <p className="mt-4 max-w-md text-base leading-relaxed text-mist">
            For partnership, enterprise evaluation, or platform
            inquiries. We take on a limited number of engagements.
          </p>
          <dl className="mt-8 grid grid-cols-1 gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <dt className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
                Name
              </dt>
              <dd className="font-display italic text-cream/90">
                {parentBrand.contact.name}
              </dd>
              <dd className="font-mono text-[10px] uppercase tracking-[0.22em] text-fog">
                {parentBrand.contact.title}
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
                Email
              </dt>
              <dd>
                <a
                  href={`mailto:${parentBrand.contact.email}`}
                  className="font-display italic text-gold transition-colors hover:text-gold-bright"
                >
                  {parentBrand.contact.email}
                </a>
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
                Website
              </dt>
              <dd>
                <a
                  href={parentBrand.website.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-display italic text-gold transition-colors hover:text-gold-bright"
                >
                  {parentBrand.website.label}
                </a>
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
                Phone
              </dt>
              <dd className="font-display italic text-cream/90">
                {parentBrand.contact.phone}
              </dd>
            </div>
          </dl>
          <div className="mt-8 flex items-center gap-3">
            <HairlineDivider width="md" tone="muted" />
            <Link
              to="/signature"
              className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
              data-testid="about-signature-link"
            >
              Email signature template
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
        <aside className="md:col-span-5">
          <EngagementBrief
            entries={[
              { label: "Cadence", value: "Quarterly · ongoing" },
              { label: "Format", value: "Embedded studio" },
              { label: "Discretion", value: "Implicit" },
              { label: "Reply", value: "By morning", emphasis: true },
            ]}
          />
        </aside>
      </div>
    </section>
  );
}
