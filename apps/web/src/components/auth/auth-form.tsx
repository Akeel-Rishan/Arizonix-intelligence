"use client";

import Link from "next/link";
import { useActionState, useId, useState, type FormEvent } from "react";
import { useFormStatus } from "react-dom";

import type { AuthActionState } from "@/app/(auth)/actions";

function SubmitButton({ label, pendingLabel }: { label: string; pendingLabel: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      className="mt-2 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-cyan-700 px-5 text-sm font-semibold text-white outline-none hover:bg-cyan-800 focus-visible:ring-2 focus-visible:ring-cyan-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:bg-slate-400"
      disabled={pending}
      type="submit"
    >
      {pending ? pendingLabel : label}
    </button>
  );
}

export function AuthForm({
  action,
  mode,
  next,
}: {
  action: (state: AuthActionState, formData: FormData) => Promise<AuthActionState>;
  mode: "login" | "signup";
  next: string;
}) {
  const [state, formAction] = useActionState(action, {});
  const [showPassword, setShowPassword] = useState(false);
  const [clientErrors, setClientErrors] = useState<NonNullable<AuthActionState["fieldErrors"]>>({});
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const emailErrorId = useId();
  const passwordErrorId = useId();
  const confirmationErrorId = useId();
  const passwordsDiffer = mode === "signup" && confirmation.length > 0 && password !== confirmation;
  const errors = { ...state.fieldErrors, ...clientErrors };

  const validateBeforeSubmit = (event: FormEvent<HTMLFormElement>) => {
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const submittedPassword = String(formData.get("password") ?? "");
    const submittedConfirmation = String(formData.get("confirmation") ?? "");
    const nextErrors: NonNullable<AuthActionState["fieldErrors"]> = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (submittedPassword.length < 8) {
      nextErrors.password = "Password must be at least 8 characters.";
    }
    if (mode === "signup" && submittedPassword !== submittedConfirmation) {
      nextErrors.confirmation = "Passwords do not match.";
    }
    setClientErrors(nextErrors);
    if (Object.keys(nextErrors).length) event.preventDefault();
  };

  return (
    <form action={formAction} className="space-y-5" noValidate onSubmit={validateBeforeSubmit}>
      <input name="next" type="hidden" value={next} />
      {state.message ? (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
        >
          {state.message}
        </div>
      ) : null}
      <div>
        <label className="text-sm font-semibold text-slate-800" htmlFor="email">
          Email address
        </label>
        <input
          aria-describedby={errors.email ? emailErrorId : undefined}
          aria-invalid={Boolean(errors.email)}
          autoComplete="email"
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-950 outline-none focus:border-cyan-700 focus:ring-2 focus:ring-cyan-200"
          defaultValue={state.values?.email}
          id="email"
          name="email"
          required
          type="email"
        />
        {errors.email ? (
          <p className="mt-1 text-sm text-rose-700" id={emailErrorId}>
            {errors.email}
          </p>
        ) : null}
      </div>
      <div>
        <div className="flex items-center justify-between gap-3">
          <label className="text-sm font-semibold text-slate-800" htmlFor="password">
            Password
          </label>
          <button
            className="rounded text-sm font-medium text-cyan-800 outline-none focus-visible:ring-2 focus-visible:ring-cyan-600"
            onClick={() => setShowPassword((visible) => !visible)}
            type="button"
          >
            {showPassword ? "Hide password" : "Show password"}
          </button>
        </div>
        <input
          aria-describedby={errors.password ? passwordErrorId : undefined}
          aria-invalid={Boolean(errors.password)}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-950 outline-none focus:border-cyan-700 focus:ring-2 focus:ring-cyan-200"
          id="password"
          minLength={8}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type={showPassword ? "text" : "password"}
        />
        {errors.password ? (
          <p className="mt-1 text-sm text-rose-700" id={passwordErrorId}>
            {errors.password}
          </p>
        ) : mode === "signup" ? (
          <p className="mt-1 text-xs leading-5 text-slate-500">Use at least 8 characters.</p>
        ) : null}
      </div>
      {mode === "signup" ? (
        <div>
          <label className="text-sm font-semibold text-slate-800" htmlFor="password-confirmation">
            Confirm password
          </label>
          <input
            aria-describedby={
              passwordsDiffer || errors.confirmation ? confirmationErrorId : undefined
            }
            aria-invalid={passwordsDiffer || Boolean(errors.confirmation)}
            autoComplete="new-password"
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 text-base text-slate-950 outline-none focus:border-cyan-700 focus:ring-2 focus:ring-cyan-200"
            id="password-confirmation"
            minLength={8}
            name="confirmation"
            onChange={(event) => setConfirmation(event.target.value)}
            required
            type={showPassword ? "text" : "password"}
          />
          {passwordsDiffer || errors.confirmation ? (
            <p className="mt-1 text-sm text-rose-700" id={confirmationErrorId}>
              {errors.confirmation ?? "Passwords do not match."}
            </p>
          ) : null}
        </div>
      ) : null}
      <SubmitButton
        label={mode === "login" ? "Sign in" : "Create account"}
        pendingLabel={mode === "login" ? "Signing in…" : "Creating account…"}
      />
      <p className="text-center text-sm text-slate-600">
        {mode === "login" ? "Need an account?" : "Already have an account?"}{" "}
        <Link
          className="font-semibold text-cyan-800 underline-offset-4 hover:underline"
          href={`${mode === "login" ? "/signup" : "/login"}?next=${encodeURIComponent(next)}`}
        >
          {mode === "login" ? "Sign up" : "Sign in"}
        </Link>
      </p>
    </form>
  );
}
