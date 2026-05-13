import { Link, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/lib/auth/use-session";

/**
 * Outer chrome. Editorial masthead + content well. The masthead is
 * intentionally restrained on auth pages (no nav, no clutter); the
 * dashboard's own header carries the workspace identity.
 *
 * We fire `useSession()` at the layout level so every page primes
 * the csrftoken cookie before any form submit (avoids a 403 on
 * fresh-tab signups). See SESSION 116 handoff for the full why.
 */
export function Layout() {
  useSession();
  const location = useLocation();
  const isAuthRoute =
    location.pathname.startsWith("/sign-in") ||
    location.pathname.startsWith("/sign-up");

  return (
    <div className="min-h-screen">
      <SiteHeader compact={!isAuthRoute} />
      <main
        className={
          isAuthRoute
            ? "container mx-auto flex max-w-md flex-col justify-center px-6 py-16"
            : "container mx-auto max-w-6xl px-6 py-12"
        }
      >
        <Outlet />
      </main>
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
      <div className="container mx-auto flex max-w-6xl items-baseline justify-between px-6 py-5">
        <Link
          to="/"
          className="flex items-baseline gap-2 font-display text-xl tracking-tight"
        >
          <span className="font-display text-2xl leading-none">Character</span>
          <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            OS
          </span>
        </Link>
        <span className="hidden font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground sm:inline">
          v1 · build alpha
        </span>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="container mx-auto flex max-w-6xl items-baseline justify-between px-6 py-6 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        <span>Character OS</span>
        <span>Persistent AI spokespeople</span>
      </div>
    </footer>
  );
}
