import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
      // surfaced via signup.error
    }
  });

  return (
    <div className="reveal flex flex-col gap-10">
      <header className="flex flex-col gap-3 border-b border-border pb-6">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          New account
        </span>
        <h1 className="font-display text-5xl leading-[0.95] tracking-tight">
          Start your
          <br />
          workspace.
        </h1>
        <p className="text-sm text-muted-foreground">
          One workspace per account. You can rename it later.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <Field
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          register={form.register("email")}
          error={form.formState.errors.email?.message}
        />
        <Field
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          register={form.register("password")}
          error={form.formState.errors.password?.message}
        />
        {signup.isError && (
          <p className="text-sm text-destructive">{extractApiMessage(signup.error)}</p>
        )}

        <Button type="submit" disabled={signup.isPending} className="mt-2">
          {signup.isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="border-t border-border pt-6 font-mono text-xs uppercase tracking-wider text-muted-foreground">
        Already have an account?{" "}
        <Link to="/sign-in" className="font-medium text-foreground underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

function Field({
  id,
  label,
  type,
  autoComplete,
  register,
  error,
}: {
  id: string;
  label: string;
  type: string;
  autoComplete: string;
  register: ReturnType<typeof useForm<SignUpForm>>["register"] extends (...args: never[]) => infer R
    ? R
    : never;
  error?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label
        htmlFor={id}
        className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
      >
        {label}
      </Label>
      <Input id={id} type={type} autoComplete={autoComplete} {...register} />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
