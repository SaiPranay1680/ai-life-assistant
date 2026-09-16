"use client";

import { LoginForm } from "@/components/forms/LoginForm";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
  const { login, register, resetPassword, user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && user) router.replace("/dashboard");
  }, [ready, user, router]);

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="flex items-center bg-[#0b1b33] px-10 py-16 text-white md:px-16">
        <div className="max-w-md">
          <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
            AI Life Assistant
          </h1>
          <p className="mt-4 text-lg text-slate-200">
            Know what matters. Know what to do next.
          </p>
          <p className="mt-10 text-sm tracking-wide text-blue-200">
            Upload → Understand → Action → Reminder
          </p>
        </div>
      </section>
      <section className="flex items-center justify-center bg-slate-50 px-6 py-16">
        <LoginForm
          onSubmit={async (email, password, mode) => {
            if (mode === "register") {
              await register(email, password);
            } else {
              await login(email, password);
            }
            router.push("/dashboard");
          }}
          onResetPassword={async (email, newPassword, confirmPassword) => {
            return resetPassword(email, newPassword, confirmPassword);
          }}
        />
      </section>
    </div>
  );
}
