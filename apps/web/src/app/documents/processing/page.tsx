"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ProgressStepper, type ProcessStep } from "@/components/upload/ProgressStepper";
import { useAuth } from "@/hooks/useAuth";
import { getDocument } from "@/services/api/document.service";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

const pendingStatuses = new Set(["uploaded", "queued", "processing", "ocr_required"]);
const reviewStatuses = new Set(["ready_for_review", "reviewed", "needs_review", "needs_decision"]);

function ProcessingContent() {
  const params = useSearchParams();
  const documentId = params.get("id") ?? "";
  const { user, ready } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["document-processing", user?.id, documentId],
    queryFn: () => getDocument(documentId),
    enabled: ready && Boolean(user) && Boolean(documentId),
    refetchInterval: (current) => {
      if (current.state.status === "error") return false;
      const status = current.state.data?.processing_status;
      return !status || pendingStatuses.has(status) ? 2000 : false;
    },
  });
  const status = query.data?.processing_status;
  const reviewReady = Boolean(status && reviewStatuses.has(status));

  useEffect(() => {
    if (!reviewReady || !user) return;
    void queryClient.invalidateQueries({ queryKey: ["documents"] });
    void queryClient.invalidateQueries({ queryKey: ["extraction", documentId] });
    router.replace(`/documents/review?id=${encodeURIComponent(documentId)}`);
  }, [reviewReady, user, documentId, queryClient, router]);

  const failed = status === "failed";
  const rejected = status === "rejected";
  const unknownStatus = Boolean(status && !pendingStatuses.has(status) && !reviewReady && !failed && !rejected);
  const processing = status === "processing" || status === "ocr_required";
  const steps: ProcessStep[] = [
    { title: "Document uploaded and checked", status: "complete" },
    { title: "Waiting for processing", status: processing || reviewReady ? "complete" : "in_progress" },
    { title: "Reading text and extracting details", status: reviewReady ? "complete" : processing ? "in_progress" : "waiting" },
    { title: "Ready for your review", status: reviewReady ? "complete" : "waiting" },
  ];

  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 md:p-8">
      <h2 className="break-words text-lg font-semibold text-slate-900">
        {query.data?.original_filename || params.get("file") || "Document processing"}
      </h2>
      {!documentId ? (
        <p role="alert" className="mt-4 text-sm text-rose-600">Missing document id. Open a document from the vault or upload a file.</p>
      ) : query.isError ? (
        <div role="alert" className="mt-4 space-y-4">
          <p className="text-sm text-rose-600">{query.error.message || "Unable to check document status."}</p>
          <Button variant="secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? "Checking..." : "Check status again"}
          </Button>
        </div>
      ) : failed ? (
        <p role="alert" className="mt-4 text-sm text-rose-600">
          We could not process this document. You can view or delete the uploaded file in your document vault, then upload a clearer copy.
        </p>
      ) : rejected ? (
        <div role="alert" className="mt-4 space-y-4">
          <p className="text-sm text-rose-600">
            {query.data?.purpose_reason || "This file is not a bill, policy, or record we can store."}
          </p>
          <Link href="/documents/upload" className="text-sm font-medium text-blue-600 hover:underline">
            Upload a supported document
          </Link>
        </div>
      ) : unknownStatus ? (
        <p role="alert" className="mt-4 text-sm text-amber-700">This document has an unexpected processing status. Check it in your document vault.</p>
      ) : !query.data ? (
        <p role="status" className="mt-4 text-sm text-slate-500">Checking document status...</p>
      ) : (
        <div className="mt-6">
          <ProgressStepper steps={steps} />
          <p role="status" className="mt-6 text-sm text-slate-500">
            {reviewReady
              ? "Your document is ready. Opening review..."
              : processing
                ? "Reading your document. Scanned files may take a little longer."
                : "Your document is queued and waiting for the processing worker."}
          </p>
          <p className="mt-2 text-sm text-slate-500">You can leave this page and return to the document vault later.</p>
        </div>
      )}
      <div className="mt-6 flex gap-4 text-sm font-medium text-blue-600">
        <Link href="/documents" className="hover:underline">Go to document vault</Link>
        {!documentId || failed || rejected ? <Link href="/documents/upload" className="hover:underline">Upload a document</Link> : null}
      </div>
    </div>
  );
}

export default function ProcessingPage() {
  return (
    <AppShell>
      <Suspense fallback={<p role="status" className="text-sm text-slate-500">Loading document status...</p>}>
        <ProcessingContent />
      </Suspense>
    </AppShell>
  );
}
