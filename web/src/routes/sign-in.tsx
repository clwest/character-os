import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
      if (err.status === 400 || err.status === 401) return "Invalid email or password.";
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
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Welcome back.</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              {...form.register("email")}
            />
            {form.formState.errors.email && (
              <p className="text-sm text-destructive">
                {form.formState.errors.email.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
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
            <p className="text-sm text-destructive">
              {extractApiMessage(signin.error)}
            </p>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" disabled={signin.isPending} className="w-full">
            {signin.isPending ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-sm text-muted-foreground">
            New here?{" "}
            <Link to="/sign-up" className="underline">
              Create an account
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
