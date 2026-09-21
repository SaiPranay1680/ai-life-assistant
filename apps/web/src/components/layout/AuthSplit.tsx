"use client";

import type { ReactNode } from "react";

export function AuthSplit({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="flex items-center bg-[#0b1b33] px-10 py-16 text-white md:px-16">
        <div className="max-w-md">
          <h1 className="text-4xl font-semibold leading-tight md:text-5xl">AI Life Assistant</h1>
          <p className="mt-4 text-lg text-slate-200">Know what matters. Know what to do next.</p>
          <p className="mt-10 text-sm tracking-wide text-blue-200">Upload → Understand → Action → Reminder</p>
        </div>
      </section>
      <section className="flex items-center justify-center bg-slate-50 px-6 py-16">{children}</section>
    </div>
  );
}
