import { Outlet } from "react-router-dom";
import { useSession } from "@/lib/auth/use-session";

// Outer chrome. v1: minimal — header + content. The dashboard layout
// inside RequireAuth will add nav + user menu in a later slice
// (SESSION 117). For now we just give the routes a centered
// container so the auth forms aren't pinned to the top-left.
//
// We fire `useSession()` at the layout level — even on public routes
// like /sign-up and /sign-in — for two reasons:
//   1. Django's CSRF middleware sets the `csrftoken` cookie on any
//      response; pinging a Django-backed GET before the user submits
//      a form is what makes the subsequent POST's X-CSRFToken header
//      valid. Without this, a fresh tab hitting /sign-up directly
//      gets a 403 on submit.
//   2. The result is cached forever (staleTime: Infinity); it's free
//      for sibling components to read.
export function Layout() {
  useSession();
  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto max-w-3xl py-12">
        <Outlet />
      </main>
    </div>
  );
}
