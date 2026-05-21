import { Link, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/lib/auth/use-session";
import { NavRail } from "@/components/nav-rail";
import { BRAND } from "@/lib/brand";

/**
 * Outer chrome. B2 (SESSION 178) — wired through the brand
 * layer: product name from `BRAND.product`, parent identity
 * from `BRAND.parent`. No hardcoded company / product strings
 * per BRAND_ECOSYSTEM_V1 contract rule 3.
 *
 * Auth pages stay minimal — no rail, no main padding shift.
 * Authenticated pages render the rail as a vertical sidebar
 * at >=md and a horizontal tab bar at sm.
 *
 * We fire `useSession()` at the layout level so every page
 * primes the csrftoken cookie before any form submit (avoids
 * a 403 on fresh-tab signups). See SESSION 116 handoff for
 * the full why.
 */
export function Layout() {
  const session = useSession();
  const location = useLocation();
  const isAuthRoute =
    location.pathname.startsWith("/sign-in") ||
    location.pathname.startsWith("/sign-up");
  const showRail = !isAuthRoute && Boolean(session.data?.isAuthenticated);

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader compact={!isAuthRoute} />
      {showRail ? (
        <div className="container mx-auto max-w-6xl flex-1 px-6 py-8">
          <div className="flex flex-col gap-6 md:flex-row md:gap-10">
            <NavRail />
            <main className="min-w-0 flex-1">
              <Outlet />
            </main>
          </div>
        </div>
      ) : (
        <main
          className={
            isAuthRoute
              ? "container mx-auto flex max-w-md flex-1 flex-col justify-center px-6 py-16"
              : "container mx-auto max-w-6xl flex-1 px-6 py-12"
          }
        >
          <Outlet />
        </main>
      )}
      <SiteFooter />
    </div>
  );
}

/**
 * SiteHeader — V3.3 (SESSION 209) dark-luxe variant.
 *
 * Editorial register: italic-gold accent on the product mark,
 * tighter microtype subtitle, hairline-gold divider replacing
 * the generic border. ParentBrandChip restyled with the
 * italic-gold mark on the parent name (`24/7 ` + italic-gold
 * `Global AI`). `compact` retained for auth-route minimalism
 * but both modes now use the V3 register.
 */
function SiteHeader({ compact }: { compact: boolean }) {
  return (
    <header
      className={
        compact
          ? "relative bg-ink/80 backdrop-blur"
          : "relative bg-ink"
      }
    >
      <div className="container mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5">
        <Link
          to="/"
          className="group flex items-baseline gap-3 tracking-tight"
          aria-label={`${BRAND.product.name} — ${BRAND.product.subtitle}`}
        >
          <span className="font-display text-2xl leading-none text-cream">
            Character
            <span className="ml-1 italic text-gold transition-colors group-hover:text-gold-bright">
              OS
            </span>
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.28em] text-fog sm:inline">
            {BRAND.product.subtitle}
          </span>
        </Link>
        <ParentBrandChip />
      </div>
      {/* Hairline-gold divider — replaces the generic border-b
       * with the editorial fade-in/out gradient. */}
      <div className="hairline-gold absolute inset-x-0 bottom-0 h-px" aria-hidden="true" />
    </header>
  );
}

/**
 * Parent-company chip — V3.3 dark-luxe variant.
 *
 * Editorial register: "a product of" in fog microtype, the parent
 * name in italic-gold display. Hover brightens to gold-bright.
 */
function ParentBrandChip() {
  return (
    <Link
      to="/about"
      className="hidden items-center gap-2 rounded-sm font-mono text-[10px] uppercase tracking-[0.28em] transition-colors sm:flex sm:px-2 sm:py-1 hover:bg-gold/5"
      data-testid="parent-brand-chip"
      title={BRAND.parent.tagline}
    >
      <span
        className="h-1.5 w-1.5 rounded-full bg-gold shadow-[0_0_8px_2px_rgba(201,169,97,0.4)]"
        aria-hidden="true"
      />
      <span className="text-fog">a product of</span>
      <span className="font-display italic text-gold transition-colors group-hover:text-gold-bright">
        {BRAND.parent.name}
      </span>
    </Link>
  );
}

/**
 * SiteFooter — V3.3 dark-luxe variant.
 *
 * Editorial register: hairline-gold above the band (replaces
 * the generic border-t), microtype keys in fog with mid-dot
 * separators, parent-brand poweredBy in italic-gold display.
 */
function SiteFooter() {
  return (
    <footer className="relative bg-ink/95">
      <div className="hairline-gold absolute inset-x-0 top-0 h-px" aria-hidden="true" />
      <div className="container mx-auto flex max-w-6xl flex-col items-baseline justify-between gap-2 px-6 py-6 font-mono text-[10px] uppercase tracking-[0.28em] text-fog sm:flex-row">
        <span>
          {BRAND.product.name}
          <span className="mx-2 text-gold/40">·</span>
          {BRAND.product.subtitle}
        </span>
        <span
          data-testid="powered-by-footer"
          className="font-display italic text-gold/80 normal-case tracking-normal text-sm"
        >
          {BRAND.parent.poweredByLabel}
        </span>
      </div>
    </footer>
  );
}
