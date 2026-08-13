import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EngagementBrief, HairlineDivider } from "@/components/editorial";
import { useSession, useSignup } from "@/lib/auth/use-session";
import { ApiError } from "@/lib/api/client";

const signUpSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type SignUpForm = z.infer<typeof signUpSchema>;

export function SignUpRoute() {
  const navigate = useNavigate();
  const signup = useSignup();
  const session = useSession();
  const form = useForm<SignUpForm>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { email: "", password: "" },
  });

  // allauth returns 409 from POST /auth/signup when the session
  // cookie is already authenticated. Bounce to the app instead of
  // letting the user submit a doomed form.
  if (session.data?.isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  function extractApiMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const body = err.body as { errors?: Array<{ message?: string }> } | null;
      const first = body?.errors?.[0]?.message;
      if (first) return first;
      if (err.status === 409) {
        return "You're already signed in. Redirecting…";
      }
      return `Request failed (${err.status}).`;
    }
    return "Something went wrong. Try again.";
  }

  const onSubmit = form.handleSubmit(async (input) => {
    try {
      await signup.mutateAsync(input);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await session.refetch();
        navigate("/dashboard", { replace: true });
        return;
      }
      // surfaced via signup.error
    }
  });

  return (
    <div className="reveal flex flex-col gap-10">
      <header className="relative flex flex-col gap-4 pb-8">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.34em] text-gold">
          § — New account
        </span>
        <h1 className="font-display text-5xl leading-[0.95] tracking-tight text-cream">
          Commission your
          <br />
          <span className="italic gold-text">operating partner.</span>
        </h1>
        <p className="max-w-md text-sm text-mist">
          One workspace per account. You can rename it later. The hour
          is irrelevant.
        </p>
        <div
          className="hairline-gold absolute inset-x-0 bottom-0 h-px"
          aria-hidden="true"
        />
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
          {signup.isPending ? "Creating account…" : "Create account →"}
        </Button>
      </form>

      {/* Editorial brief — what you're signing up for. The
       * EngagementBrief primitive from V3.2. */}
      <EngagementBrief
        entries={[
          { label: "Cadence", value: "Around the clock" },
          { label: "Format", value: "Self-serve workspace" },
          { label: "Discretion", value: "Implicit" },
          { label: "Reply", value: "Immediate", emphasis: true },
        ]}
      />

      <div className="flex flex-col gap-4 pt-2">
        <HairlineDivider width="lg" tone="muted" />
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-fog">
          Already have an account?{" "}
          <Link
            to="/sign-in"
            className="font-display italic text-gold transition-colors hover:text-gold-bright"
          >
            Sign in →
          </Link>
        </p>
      </div>
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
        className="font-mono text-[10.5px] uppercase tracking-[0.28em] text-fog"
      >
        {label}
      </Label>
      <Input id={id} type={type} autoComplete={autoComplete} {...register} />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
