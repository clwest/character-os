import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSignin } from "@/lib/auth/use-session";
import { ApiError } from "@/lib/api/client";

const signInSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type SignInForm = z.infer<typeof signInSchema>;

interface LocationStateLike {
  from?: string;
}

export function SignInRoute() {
  const location = useLocation();
  const navigate = useNavigate();
  const signin = useSignin();
  const from = (location.state as LocationStateLike | null)?.from ?? "/dashboard";

  const form = useForm<SignInForm>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  });

  function extractApiMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const body = err.body as { errors?: Array<{ message?: string }> } | null;
      const first = body?.errors?.[0]?.message;
      if (first) return first;
      if (err.status === 400 || err.status === 401) {
        return "Invalid email or password.";
      }
      return `Request failed (${err.status}).`;
    }
    return "Something went wrong. Try again.";
  }

  const onSubmit = form.handleSubmit(async (input) => {
    try {
      await signin.mutateAsync(input);
      navigate(from, { replace: true });
    } catch {
      // surfaced via signin.error
    }
  });

  return (
    <div className="reveal flex flex-col gap-10">
      <header className="flex flex-col gap-3 border-b border-border pb-6">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Welcome back
        </span>
        <h1 className="font-display text-5xl leading-[0.95] tracking-tight">Sign in.</h1>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <Label
            htmlFor="email"
            className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            Email
          </Label>
          <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          {form.formState.errors.email && (
            <p className="text-sm text-destructive">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label
            htmlFor="password"
            className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            Password
          </Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...form.register("password")}
          />
          {form.formState.errors.password && (
            <p className="text-sm text-destructive">
              {form.formState.errors.password.message}
            </p>
          )}
        </div>
        {signin.isError && (
          <p className="text-sm text-destructive">{extractApiMessage(signin.error)}</p>
        )}

        <Button type="submit" disabled={signin.isPending} className="mt-2">
          {signin.isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="border-t border-border pt-6 font-mono text-xs uppercase tracking-wider text-muted-foreground">
        New here?{" "}
        <Link to="/sign-up" className="font-medium text-foreground underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
