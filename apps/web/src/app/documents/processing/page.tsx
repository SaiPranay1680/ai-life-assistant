"use client";

import { AppShell } from "@/components/layout/AppShell";
import { ProgressStepper, type ProcessStep } from "@/components/upload/ProgressStepper";
import { getDocument } from "@/services/api/document.service";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const titles = [
  "File uploaded",
  "Reading document",
  "Finding dates, provider and policy details",
  "Preparing suggested action",
];

function completeCountFromStatus(status: string | null): number {
  if (status === "ready_for_review" || status === "ocr_required" || status === "failed") return titles.length;
  if (status === "processing") return 2;
  if (status === "uploaded" || status === "queued") return 1;
  return 1;
}

function ProcessingContent() {
  const router = useRouter();
  const params = useSearchParams();
  const fileName = params.get("file") ?? "document.pdf";
  const documentId = params.get("id");
  const [completeCount, setCompleteCount] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setError("Missing document id. Upload the file again.");
      return;
    }
    let cancelled = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const document = await getDocument(documentId);
        if (cancelled) return;
        setCompleteCount(completeCountFromStatus(document.processing_status));
        if (
          document.processing_status === "ready_for_review" ||
          document.processing_status === "ocr_required" ||
          document.processing_status === "failed"
        ) {
          router.push(`/documents/review?id=${encodeURIComponent(documentId)}`);
          return;
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unable to read document status.");
      }
      if (!cancelled) {
        timer = window.setTimeout(() => {
          void poll();
        }, 800);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [documentId, router]);

  const steps: ProcessStep[] = titles.map((title, index) => {
    if (index < completeCount - 1) return { title, status: "complete" };
    if (index === completeCount - 1 && completeCount < titles.length) {
      return { title, status: "in_progress" };
    }
    if (completeCount >= titles.length) return { title, status: "complete" };
    return { title, status: "waiting" };
  });

  return (
<<<<<<< Updated upstream
    <AppShell>
      <div className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
        <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
          {fileName}
        </span>
        <h2 className="mt-4 text-lg font-semibold text-slate-900">
          We’re reading and organizing the important details.
        </h2>
        {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
=======
    <div className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 md:p-8">
      <h2 className="break-words text-lg font-semibold text-slate-900">
        {query.data?.original_filename || params.get("file") || "Document processing"}
      </h2>
      {!documentId ? (
        <p role="alert" className="mt-4 text-sm text-rose-600">Missing document. Please upload the file again.</p>
      ) : query.isError ? (
        <div role="alert" className="mt-4 space-y-4">
          <p className="text-sm text-rose-600">{query.error.message || "Unable to check document status."}</p>
          <Button variant="secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? "Checking..." : "Check status again"}
          </Button>
        </div>
      ) : failed ? (
        <p role="alert" className="mt-4 text-sm text-rose-600">
          Unable to process this document. Try uploading another.
        </p>
      ) : rejected ? (
        <div role="alert" className="mt-4 space-y-4">
          <p className="text-sm text-rose-600">Invalid document. Try uploading another.</p>
          <Link href="/documents/upload" className="text-sm font-medium text-blue-600 hover:underline">
            Upload another
          </Link>
        </div>
      ) : unknownStatus ? (
        <p role="alert" className="mt-4 text-sm text-amber-700">Unable to process this document. Check it in Documents.</p>
      ) : !query.data ? (
        <p role="status" className="mt-4 text-sm text-slate-500">Checking document status...</p>
      ) : (
>>>>>>> Stashed changes
        <div className="mt-6">
          <ProgressStepper steps={steps} />
        </div>
<<<<<<< Updated upstream
        <p className="mt-6 text-sm text-slate-400">
          You can continue using the app. We&apos;ll notify you when review is ready.
        </p>
=======
      )}
      <div className="mt-6 flex gap-4 text-sm font-medium text-blue-600">
        <Link href="/documents" className="hover:underline">Go to document vault</Link>
        {!documentId || failed || rejected ? <Link href="/documents/upload" className="hover:underline">Upload another</Link> : null}
>>>>>>> Stashed changes
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
