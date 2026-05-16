/**
 * Persistent navigation rail — F2 (workspace fabric arc).
 *
 * Five-section sidebar (vertical at >=md, horizontal tab bar
 * at sm) that turns previously-isolated SPA sections into one
 * workspace. Renders only on authenticated, non-auth routes;
 * the layout decides when to mount it.
 *
 * Active section is computed from the current pathname. The
 * matching is prefix-based — `/spokespeople/<id>/...` keeps
 * the Spokespeople tab active.
 *
 * Per F0 contract rule 7, this nav set is stable: adding a
 * top-level section requires its own scope-lock event, not a
 * fabric slice. The fifth section (Images) was authorized by
 * the W11.6 scope-lock (``docs/design/MEDIA_GENERATION_V1.md``
 * §"Surface inventory": "/images route ... sibling to /recipes
 * in workspace fabric nav").
 */
import { Link, useLocation } from "react-router-dom";
import { Home, Image as ImageIcon, Users, Library, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  /** Prefixes that should highlight this section. The first
   *  entry is the canonical href. */
  matches: string[];
  label: string;
  icon: LucideIcon;
  testId: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: "/dashboard",
    matches: ["/dashboard"],
    label: "Dashboard",
    icon: Home,
    testId: "nav-dashboard",
  },
  {
    to: "/spokespeople/new",
    // Cover detail pages + the new flow + the listed-on-dashboard
    // shape. /spokespeople doesn't have its own index route yet,
    // so we keep the rail aimed at /new while highlighting any
    // /spokespeople/* visit.
    matches: ["/spokespeople"],
    label: "Spokespeople",
    icon: Users,
    testId: "nav-spokespeople",
  },
  {
    to: "/workspace/knowledge",
    matches: ["/workspace/knowledge"],
    label: "Knowledge",
    icon: Library,
    testId: "nav-knowledge",
  },
  {
    to: "/recipes",
    matches: ["/recipes", "/compositions"],
    label: "Recipes",
    icon: Sparkles,
    testId: "nav-recipes",
  },
  {
    to: "/images",
    matches: ["/images"],
    label: "Images",
    icon: ImageIcon,
    testId: "nav-images",
  },
];

export function NavRail() {
  const location = useLocation();
  const activeIndex = NAV_ITEMS.findIndex((item) =>
    item.matches.some((prefix) => location.pathname.startsWith(prefix)),
  );

  return (
    <nav
      className="md:sticky md:top-6 md:w-48 md:flex-shrink-0 md:self-start"
      aria-label="Workspace sections"
      data-testid="nav-rail"
    >
      {/* sm: horizontal scroll tabs. md+: vertical list. */}
      <ul className="flex gap-1 overflow-x-auto border-b md:flex-col md:gap-0 md:border-b-0 md:border-r md:pr-3">
        {NAV_ITEMS.map((item, idx) => {
          const Icon = item.icon;
          const active = idx === activeIndex;
          return (
            <li key={item.testId}>
              <Link
                to={item.to}
                data-testid={item.testId}
                data-active={active ? "true" : "false"}
                className={
                  "flex items-center gap-2 whitespace-nowrap px-3 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition-colors md:rounded-sm " +
                  (active
                    ? "border-b-2 border-foreground text-foreground md:border-b-0 md:border-l-2 md:border-foreground md:bg-foreground/5"
                    : "border-b-2 border-transparent text-muted-foreground hover:text-foreground md:border-b-0 md:border-l-2 md:border-transparent md:hover:border-foreground/20")
                }
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
