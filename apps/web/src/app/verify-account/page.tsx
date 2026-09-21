"use client";

import { OtpInput } from "@/components/forms/OtpInput";
import { AuthSplit } from "@/components/layout/AuthSplit";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { sendVerificationOtp, verifyAccount } from "@/services/api/auth.service";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

export default function VerifyAccountPage() {
  const router = useRouter();
  const { user, ready, refreshUser } = useAuth();
  const [otp, setOtp] = useState("");
  const [secondsLeft, setSecondsLeft] = useState(600);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = window.setInterval(() => setSecondsLeft((value) => Math.max(value - 1, 0)), 1000);
    return () => window.clearInterval(timer);
  }, [secondsLeft]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    if (otp.length !== 6) {
      setError("Enter the 6-digit code from your email.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await verifyAccount(user.email, otp);
      await refreshUser();
      setSuccess(true);
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
      const result = await sendVerificationOtp();
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
        <h2 className="text-2xl font-semibold text-slate-900">Verify your account</h2>
        <p className="mt-2 text-sm text-slate-500">
          Enter the six-digit code we sent to {user?.email ?? "your email"}. It expires in {minutes}:{seconds}.
        </p>
        {success ? (
          <>
            <p className="mt-6 text-sm text-emerald-600">Your account is verified.</p>
            <Button type="button" className="mt-6 w-full" onClick={() => router.push("/dashboard")}>
              Continue to dashboard
            </Button>
          </>
        ) : (
          <>
            <div className="mt-8">
              <OtpInput value={otp} onChange={setOtp} disabled={submitting} />
            </div>
            {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
            {info ? <p className="mt-3 text-sm text-emerald-600">{info}</p> : null}
            <Button type="submit" className="mt-6 w-full" disabled={submitting}>
              {submitting ? "Checking…" : "Verify account"}
            </Button>
            <button
              type="button"
              className="mt-4 w-full text-sm text-blue-600 hover:underline"
              onClick={resend}
            >
              Resend OTP
            </button>
          </>
        )}
      </form>
    </AuthSplit>
  );
}
