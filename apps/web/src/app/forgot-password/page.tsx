"use client";

import { AuthSplit } from "@/components/layout/AuthSplit";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { requestPasswordReset } from "@/services/api/auth.service";
import { isValidEmail } from "@/utils";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

const EMAIL_KEY = "ala-reset-email";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isValidEmail(email)) {
      setError("Enter a valid email address.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const result = await requestPasswordReset(email.trim());
      window.sessionStorage.setItem(EMAIL_KEY, email.trim().toLowerCase());
      window.sessionStorage.setItem("ala-reset-expires", String(result.expires_in_seconds ?? 600));
      router.push("/verify-reset-otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send a password reset code.");
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
        <h2 className="text-2xl font-semibold text-slate-900">Forgot password?</h2>
        <p className="mt-2 text-sm text-slate-500">
          Enter your registered email. If an account exists, we will send a six-digit OTP.
        </p>
        <div className="mt-8">
          <Input
            label="Email address"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        <Button type="submit" className="mt-6 w-full" disabled={submitting}>
          {submitting ? "Sending…" : "Send OTP"}
        </Button>
        <Link href="/login" className="mt-4 block text-center text-sm text-blue-600 hover:underline">
          Back to sign in
        </Link>
      </form>
    </AuthSplit>
  );
}
