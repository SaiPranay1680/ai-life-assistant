"use client";

import { OtpInput } from "@/components/forms/OtpInput";
import { AuthSplit } from "@/components/layout/AuthSplit";
import { Button } from "@/components/ui/Button";
import { requestPasswordReset, verifyResetOtp } from "@/services/api/auth.service";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

const EMAIL_KEY = "ala-reset-email";
const TOKEN_KEY = "ala-reset-token";

export default function VerifyResetOtpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(600);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const stored = window.sessionStorage.getItem(EMAIL_KEY);
    if (!stored) {
      router.replace("/forgot-password");
      return;
    }
    setEmail(stored);
    const expires = Number(window.sessionStorage.getItem("ala-reset-expires") ?? 600);
    setSecondsLeft(Number.isFinite(expires) ? expires : 600);
  }, [router]);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = window.setInterval(() => setSecondsLeft((value) => Math.max(value - 1, 0)), 1000);
    return () => window.clearInterval(timer);
  }, [secondsLeft]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (otp.length !== 6) {
      setError("Enter the 6-digit code from your email.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await verifyResetOtp(email, otp);
      window.sessionStorage.setItem(TOKEN_KEY, result.reset_token);
      router.push("/reset-password");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to verify that code.");
    } finally {
      setSubmitting(false);
    }
  }

  async function resend() {
    setError("");
    setInfo("");
    try {
      const result = await requestPasswordReset(email);
      setSecondsLeft(result.expires_in_seconds ?? 600);
      setInfo(result.message);
      setOtp("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send a new code.");
    }
  }

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = String(secondsLeft % 60).padStart(2, "0");

  return (
    <AuthSplit>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <h2 className="text-2xl font-semibold text-slate-900">Enter your OTP</h2>
        <p className="mt-2 text-sm text-slate-500">
          We sent a six-digit code to {email || "your email"}. It expires in {minutes}:{seconds}.
        </p>
        <div className="mt-8">
          <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
        </div>
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        {info ? <p className="mt-3 text-sm text-emerald-600">{info}</p> : null}
        <Button type="submit" className="mt-6 w-full" disabled={submitting}>
          {submitting ? "Checking…" : "Verify OTP"}
        </Button>
        <button
          type="button"
          className="mt-4 w-full text-sm text-blue-600 hover:underline disabled:text-slate-400"
          onClick={resend}
          disabled={secondsLeft > 540}
        >
          Resend OTP
        </button>
        <Link href="/forgot-password" className="mt-3 block text-center text-sm text-slate-500 hover:underline">
          Use a different email
        </Link>
      </form>
    </AuthSplit>
  );
}
