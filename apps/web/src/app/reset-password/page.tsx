"use client";

import { AuthSplit } from "@/components/layout/AuthSplit";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { resetPassword } from "@/services/api/auth.service";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

const TOKEN_KEY = "ala-reset-token";
const EMAIL_KEY = "ala-reset-email";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const stored = window.sessionStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/forgot-password");
      return;
    }
    setToken(stored);
  }, [router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const message = await resetPassword(token, password, confirmPassword);
      window.sessionStorage.removeItem(TOKEN_KEY);
      window.sessionStorage.removeItem(EMAIL_KEY);
      setSuccess(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthSplit>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <h2 className="text-2xl font-semibold text-slate-900">Create a new password</h2>
        <p className="mt-2 text-sm text-slate-500">Choose a new password, then sign in with it.</p>
        <div className="mt-8 space-y-4">
          <Input
            label="New password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Input
            label="Confirm new password"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </div>
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        {success ? <p className="mt-3 text-sm text-emerald-600">{success}</p> : null}
        {success ? (
          <Link href="/login">
            <Button type="button" className="mt-6 w-full">
              Return to login
            </Button>
          </Link>
        ) : (
          <Button type="submit" className="mt-6 w-full" disabled={submitting}>
            {submitting ? "Saving…" : "Save new password"}
          </Button>
        )}
      </form>
    </AuthSplit>
  );
}
