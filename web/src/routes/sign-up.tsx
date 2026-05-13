import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
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
import { useSignup } from "@/lib/auth/use-session";
import { ApiError } from "@/lib/api/client";

const signUpSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type SignUpForm = z.infer<typeof signUpSchema>;

export function SignUpRoute() {
  const navigate = useNavigate();
  const signup = useSignup();
  const form = useForm<SignUpForm>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { email: "", password: "" },
  });

  function extractApiMessage(err: unknown): string {
    if (err instanceof ApiError) {
      // allauth returns `{ status, errors: [{ message, code, param? }] }`.
      const body = err.body as { errors?: Array<{ message?: string }> } | null;
      const first = body?.errors?.[0]?.message;
      if (first) return first;
      return `Request failed (${err.status}).`;
    }
    return "Something went wrong. Try again.";
  }

  const onSubmit = form.handleSubmit(async (input) => {
    try {
      await signup.mutateAsync(input);
      navigate("/dashboard", { replace: true });
    } catch {
      // mutation error is surfaced via signup.error; no extra handling needed
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>
          One workspace per account. You can rename it later.
        </CardDescription>
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
              autoComplete="new-password"
              {...form.register("password")}
            />
            {form.formState.errors.password && (
              <p className="text-sm text-destructive">
                {form.formState.errors.password.message}
              </p>
            )}
          </div>
          {signup.isError && (
            <p className="text-sm text-destructive">
              {extractApiMessage(signup.error)}
            </p>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" disabled={signup.isPending} className="w-full">
            {signup.isPending ? "Creating account…" : "Create account"}
          </Button>
          <p className="text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/sign-in" className="underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
