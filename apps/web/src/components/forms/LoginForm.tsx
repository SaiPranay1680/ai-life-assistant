"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { isValidEmail } from "@/utils";
import { FormEvent, useState } from "react";

type AuthMode = "login" | "register" | "forgot";

export function LoginForm({
  onSubmit,
  onResetPassword,
}: {
  onSubmit: (email: string, password: string, mode: "login" | "register") => Promise<void>;
  onResetPassword: (
    email: string,
    newPassword: string,
    confirmPassword: string,
  ) => Promise<string>;
}) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    confirmPassword?: string;
    form?: string;
  }>({});
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors: typeof errors = {};
    if (!isValidEmail(email)) nextErrors.email = "Enter a valid email address.";

    if (mode === "forgot") {
      if (password.trim().length < 6) {
        nextErrors.password = "Password must be at least 6 characters.";
      }
      if (confirmPassword.trim().length < 6) {
        nextErrors.confirmPassword = "Confirm password must be at least 6 characters.";
      } else if (password !== confirmPassword) {
        nextErrors.confirmPassword = "Passwords do not match.";
      }
    } else if (password.trim().length < 6) {
      nextErrors.password = "Password must be at least 6 characters.";
    }

    setErrors(nextErrors);
    setSuccess(null);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      if (mode === "forgot") {
        const message = await onResetPassword(email, password, confirmPassword);
        setSuccess(message);
        setPassword("");
        setConfirmPassword("");
        setMode("login");
      } else {
        await onSubmit(email, password, mode);
      }
    } catch (error) {
      setErrors({
        form:
          error instanceof Error
            ? error.message
            : mode === "forgot"
              ? "Unable to reset password."
              : "Unable to sign in.",
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
        {mode === "login"
          ? "Welcome back"
          : mode === "register"
            ? "Create your account"
            : "Reset your password"}
      </h2>
      <p className="mt-2 text-sm text-slate-500">
        {mode === "login"
          ? "Sign in to see what needs your attention."
          : mode === "register"
            ? "Register to create your personal workspace."
            : "Enter your email and choose a new password."}
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
          label={mode === "forgot" ? "New password" : "Password"}
          name="password"
          type="password"
          autoComplete={mode === "forgot" ? "new-password" : "current-password"}
          placeholder="••••••••"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.password}
        />
        {mode === "forgot" ? (
          <Input
            label="Confirm new password"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            error={errors.confirmPassword}
          />
        ) : null}
      </div>
      {errors.form ? <p className="mt-3 text-sm text-rose-600">{errors.form}</p> : null}
      {success ? <p className="mt-3 text-sm text-emerald-600">{success}</p> : null}
      <Button type="submit" className="mt-6 w-full" disabled={submitting}>
        {submitting
          ? "Please wait…"
          : mode === "login"
            ? "Sign in"
            : mode === "register"
              ? "Create account"
              : "Reset password"}
      </Button>
      {mode === "login" ? (
        <button
          type="button"
          className="mt-3 w-full text-center text-sm text-slate-500 hover:text-blue-600 hover:underline"
          onClick={() => {
            setMode("forgot");
            setPassword("");
            setConfirmPassword("");
            setErrors({});
            setSuccess(null);
          }}
        >
          Forgot password?
        </button>
      ) : null}
      <button
        type="button"
        className="mt-4 w-full text-center text-sm text-blue-600 hover:underline"
        onClick={() => {
          if (mode === "forgot") {
            setMode("login");
          } else {
            setMode(mode === "login" ? "register" : "login");
          }
          setPassword("");
          setConfirmPassword("");
          setErrors({});
          setSuccess(null);
        }}
      >
        {mode === "login"
          ? "New here? Create an account"
          : mode === "register"
            ? "Already have an account? Sign in"
            : "Back to sign in"}
      </button>
      <p className="mt-5 text-center text-xs text-slate-400">
        Your personal information stays private and protected.
      </p>
    </form>
  );
}
