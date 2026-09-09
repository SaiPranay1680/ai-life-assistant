"use client";

import { AppShell } from "@/components/layout/AppShell";
import { ProgressStepper, type ProcessStep } from "@/components/upload/ProgressStepper";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const titles = [
  "File uploaded",
  "Reading document",
  "Finding dates, provider and policy details",
  "Preparing suggested action",
];

function ProcessingContent() {
  const router = useRouter();
  const params = useSearchParams();
  const fileName = params.get("file") ?? "document.pdf";
  const [completeCount, setCompleteCount] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCompleteCount((current) => {
        if (current >= titles.length) return current;
        return current + 1;
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (completeCount < titles.length) return;
    const go = window.setTimeout(() => {
      router.push("/documents/review");
    }, 700);
    return () => window.clearTimeout(go);
  }, [completeCount, router]);

  const steps: ProcessStep[] = titles.map((title, index) => {
    if (index < completeCount - 1) return { title, status: "complete" };
    if (index === completeCount - 1 && completeCount < titles.length) {
      return { title, status: "in_progress" };
    }
    if (completeCount >= titles.length) return { title, status: "complete" };
    return { title, status: "waiting" };
  });

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
        <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
          {fileName}
        </span>
        <h2 className="mt-4 text-lg font-semibold text-slate-900">
          We’re reading and organizing the important details.
        </h2>
        <div className="mt-6">
          <ProgressStepper steps={steps} />
        </div>
        <p className="mt-6 text-sm text-slate-400">
          You can continue using the app. We&apos;ll notify you when review is ready.
        </p>
      </div>
    </AppShell>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
          Loading…
        </div>
      }
    >
      <ProcessingContent />
    </Suspense>
  );
}
