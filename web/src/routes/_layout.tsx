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

function SiteHeader({ compact }: { compact: boolean }) {
  return (
    <header
      className={
        compact
          ? "border-b border-border/60 bg-background/80 backdrop-blur"
          : "bg-background"
      }
    >
      <div className="container mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5">
        <Link
          to="/"
          className="flex items-baseline gap-2 tracking-tight"
          aria-label={`${BRAND.product.name} — ${BRAND.product.subtitle}`}
        >
          <span className="text-xl font-semibold leading-none text-foreground">
            {BRAND.product.name}
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground sm:inline">
            {BRAND.product.subtitle}
          </span>
        </Link>
        <ParentBrandChip />
      </div>
    </header>
  );
}

/**
 * Subtle "24/7 GLOBAL AI" chip top-right of the header.
 * Establishes the parent-company identity on every page without
 * crowding the product name. Gold accent on the company name
 * keeps it discoverable; muted prefix avoids over-signalling.
 *
 * B5 (deferred) will turn this chip into a link to a dedicated
 * `/about` parent-company route. For now it's display-only.
 */
function ParentBrandChip() {
  return (
    <div
      className="hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] sm:flex"
      data-testid="parent-brand-chip"
      title={BRAND.parent.tagline}
    >
      <span className="h-2 w-2 rounded-sm bg-accent" aria-hidden="true" />
      <span className="text-muted-foreground">a product of</span>
      <span className="font-semibold text-accent">{BRAND.parent.name}</span>
    </div>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="container mx-auto flex max-w-6xl flex-col items-baseline justify-between gap-2 px-6 py-6 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground sm:flex-row">
        <span>
          {BRAND.product.name} · {BRAND.product.subtitle}
        </span>
        <span data-testid="powered-by-footer">
          {BRAND.parent.poweredByLabel}
        </span>
      </div>
    </footer>
  );
}
