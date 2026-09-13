"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { isValidEmail } from "@/utils";
import { FormEvent, useState } from "react";

export function LoginForm({
  onSubmit,
}: {
  onSubmit: (email: string, password: string, mode: "login" | "register") => Promise<void>;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>(
    {},
  );
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors: typeof errors = {};
    if (!isValidEmail(email)) nextErrors.email = "Enter a valid email address.";
    if (password.trim().length < 6) {
      nextErrors.password = "Password must be at least 6 characters.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      await onSubmit(email, password, mode);
    } catch (error) {
      setErrors({
        form: error instanceof Error ? error.message : "Unable to sign in.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"
    >
      <h2 className="text-2xl font-semibold text-slate-900">
        {mode === "login" ? "Welcome back" : "Create your account"}
      </h2>
      <p className="mt-2 text-sm text-slate-500">
        {mode === "login"
          ? "Sign in to see what needs your attention."
          : "Register to create your personal workspace."}
      </p>
      <div className="mt-8 space-y-4">
        <Input
          label="Email address"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="name@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={errors.email}
        />
        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.password}
        />
      </div>
      {errors.form ? <p className="mt-3 text-sm text-rose-600">{errors.form}</p> : null}
      <Button type="submit" className="mt-6 w-full" disabled={submitting}>
        {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
      </Button>
      <button
        type="button"
        className="mt-4 w-full text-center text-sm text-blue-600 hover:underline"
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setErrors({});
        }}
      >
        {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
      </button>
      <p className="mt-5 text-center text-xs text-slate-400">
        Your personal information stays private and protected.
      </p>
    </form>
  );
}
