/**
 * /about — parent company narrative.
 *
 * B5 (SESSION 178) — first dedicated 24/7 GLOBAL AI surface in
 * the SPA. Mirrors `docs/247_GLOBAL_AI_OVERVIEW.md` (parent
 * narrative) using the existing `BRAND.parent` config so no
 * copy is duplicated. ParentBrandChip in the header links here.
 *
 * Per BRAND_ECOSYSTEM_V1 contract rule 3, every string flows
 * through the brand layer — no hardcoded company strings.
 */
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { parentBrand, productFamily } from "@/lib/brand";

export function AboutRoute() {
  return (
    <div className="flex flex-col gap-12 py-6" data-testid="about-route">
      <Hero />
      <ProductFamilyPanel />
      <ContactPanel />
    </div>
  );
}

function Hero() {
  return (
    <header className="flex flex-col gap-6" data-testid="about-hero">
      <div className="flex items-center gap-3">
        <span
          className="h-3 w-3 rounded-sm bg-accent"
          aria-hidden="true"
        />
        <span className="font-mono text-[11px] uppercase tracking-[0.28em] text-accent">
          {parentBrand.tagline}
        </span>
      </div>
      <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
        {parentBrand.name}
      </h1>
      <p className="max-w-2xl text-lg text-muted-foreground">
        {parentBrand.description}
      </p>
      <p className="max-w-3xl text-base text-foreground">
        {parentBrand.positioning}
      </p>
    </header>
  );
}

function ProductFamilyPanel() {
  return (
    <section className="flex flex-col gap-4" data-testid="about-products">
      <header className="flex items-baseline justify-between border-b border-border pb-2">
        <h2 className="text-xl font-semibold tracking-tight">
          Product family
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
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
      className="flex items-center justify-between gap-4 border-b border-border/60 py-4 last:border-b-0"
      data-testid={`about-product-${product.slug}`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline gap-3">
          <span
            className={
              "text-lg font-semibold" +
              (isLive ? " text-foreground" : " text-muted-foreground")
            }
          >
            {product.name}
          </span>
          <StatusPill status={product.status} />
        </div>
        <p className="text-sm text-muted-foreground">{product.subtitle}</p>
      </div>
      {isLive && (
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition-colors hover:text-accent-bright"
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
    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
      Reserved
    </span>
  );
}

function ContactPanel() {
  return (
    <section
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-8"
      data-testid="about-contact"
    >
      <header>
        <h2 className="text-xl font-semibold tracking-tight">Contact</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          For partnership, enterprise evaluation, or platform inquiries.
        </p>
      </header>
      <dl className="grid grid-cols-1 gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
        <div className="flex flex-col gap-0.5">
          <dt className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Name
          </dt>
          <dd className="text-foreground">{parentBrand.contact.name}</dd>
          <dd className="text-sm text-muted-foreground">
            {parentBrand.contact.title}
          </dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Email
          </dt>
          <dd>
            <a
              href={`mailto:${parentBrand.contact.email}`}
              className="text-accent transition-colors hover:text-accent-bright"
            >
              {parentBrand.contact.email}
            </a>
          </dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Website
          </dt>
          <dd>
            <a
              href={parentBrand.website.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent transition-colors hover:text-accent-bright"
            >
              {parentBrand.website.label}
            </a>
          </dd>
        </div>
        <div className="flex flex-col gap-0.5">
          <dt className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Phone
          </dt>
          <dd className="text-foreground">{parentBrand.contact.phone}</dd>
        </div>
      </dl>
      <div className="mt-2 border-t border-border/60 pt-4">
        <Link
          to="/signature"
          className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-accent"
          data-testid="about-signature-link"
        >
          Email signature template
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </section>
  );
}
