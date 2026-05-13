import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "./use-session";

interface RequireAuthProps {
  children: React.ReactNode;
}

/**
 * Router guard. Three states map to three render branches per
 * `docs/design/SPA_ARCHITECTURE.md` §"Auth state machine":
 *
 *   loading         → render a tiny skeleton
 *   unauthenticated → redirect to /sign-in (preserve the intended
 *                     destination in router state so post-login
 *                     bounces back)
 *   authenticated   → render the wrapped tree
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const { data, isLoading, isError } = useSession();
  const location = useLocation();

  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;
  }

  if (isError || !data?.isAuthenticated) {
    return <Navigate to="/sign-in" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
