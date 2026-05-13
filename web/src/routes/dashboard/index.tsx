import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSession, useSignout } from "@/lib/auth/use-session";

/**
 * Placeholder dashboard. The real Workspace dashboard (S-09) lands
 * in SESSION 117 — see `docs/design/SPA_ARCHITECTURE.md`
 * §"First three screens" → Slice 2.
 *
 * This slice's only job is to prove the auth flow lands the user
 * somewhere authed. The "Hello, {email}" + sign-out is enough for
 * the Playwright spec to assert against.
 */
export function DashboardRoute() {
  const navigate = useNavigate();
  const session = useSession();
  const signout = useSignout();

  async function handleSignOut() {
    await signout.mutateAsync();
    navigate("/sign-in", { replace: true });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Welcome to Character OS</CardTitle>
        <CardDescription>
          You're signed in. The real dashboard lands in the next slice
          (S-09 of the design lock).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm" data-testid="auth-confirm">
          Signed in as <strong>{session.data?.user?.email ?? "(unknown)"}</strong>
        </p>
        <Button
          variant="outline"
          onClick={handleSignOut}
          disabled={signout.isPending}
        >
          {signout.isPending ? "Signing out…" : "Sign out"}
        </Button>
      </CardContent>
    </Card>
  );
}
