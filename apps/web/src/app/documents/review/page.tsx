"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { decideDocumentPurpose, getExtraction, updateExtraction } from "@/services/api/document.service";
import type { ExtractedFields } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function labelsFor(documentType: string) {
  const type = documentType.toLowerCase();
  if (type.includes("bill")) {
    return {
      documentType: "Document type",
      provider: "Provider",
      policyNumber: "Account number",
      startDate: "Start date",
      expiryDate: "Due date",
      premium: "Amount due",
    };
  }
  if (type.includes("insurance")) {
    return {
      documentType: "Document type",
      provider: "Insurer",
      policyNumber: "Policy number",
      startDate: "Start date",
      expiryDate: "Expiry date",
      premium: "Premium",
    };
  }
  if (type.includes("purchase") || type.includes("invoice")) {
    return {
      documentType: "Document type",
      provider: "Merchant",
      policyNumber: "Invoice number",
      startDate: "Invoice date",
      expiryDate: "Due date",
      premium: "Amount",
    };
  }
  if (type.includes("warranty")) {
    return {
      documentType: "Document type",
      provider: "Provider",
      policyNumber: "Serial number",
      startDate: "Start date",
      expiryDate: "Expiry date",
      premium: "Amount",
    };
  }
  return {
    documentType: "Document type",
    provider: "Provider",
    policyNumber: "Reference number",
    startDate: "Start date",
    expiryDate: "End date",
    premium: "Amount",
  };
}

function displayValue(value: string) {
  return value.trim() ? value : "—";
}

function ReviewForm({ data, documentId }: { data: ExtractedFields; documentId: string }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    documentType: data.documentType,
    provider: data.provider,
    policyNumber: data.policyNumber,
    startDate: data.startDate ?? "",
    expiryDate: data.expiryDate,
    premium: data.premium,
  });
  const labels = labelsFor(form.documentType || data.documentType);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function confirm() {
    setError(null);
    setSaving(true);
    try {
      await updateExtraction(documentId, form);
      router.push("/actions");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save extraction.");
    } finally {
      setSaving(false);
    }
  }

  async function decide(decision: "keep" | "discard") {
    setError(null);
    setSaving(true);
    try {
      await decideDocumentPurpose(documentId, decision);
      router.push(decision === "keep" ? "/actions" : "/documents/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save that choice.");
    } finally {
      setSaving(false);
    }
  }

  const rejected =
    data.processingStatus === "rejected" ||
    data.purposeStatus === "rejected" ||
    data.purposeStatus === "not_useful";
  const needsDecision = data.processingStatus === "needs_decision";

  if (rejected) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-lg font-semibold text-slate-900">Document not stored</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {data.purposeReason || "This file is not a bill, policy, invoice, or important record."}
        </p>
        <div className="mt-6">
          <Button onClick={() => router.push("/documents/upload")}>Upload another document</Button>
        </div>
      </div>
    );
  }

  if (needsDecision) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">{data.previewTitle}</p>
        <h2 className="mt-2 text-lg font-semibold text-slate-900">Keep this file?</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {data.purposeReason || "This does not look like a bill, insurance policy, invoice, or warranty."}
        </p>
        <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="ghost" onClick={() => void decide("discard")} disabled={saving}>
            Don’t store
          </Button>
          <Button onClick={() => void decide("keep")} disabled={saving}>
            {saving ? "Saving…" : "Keep as a record"}
          </Button>
        </div>
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      </div>
    );
  }

  const fields: { key: keyof typeof form; label: string }[] = [
    { key: "documentType", label: labels.documentType },
    { key: "provider", label: labels.provider },
    { key: "policyNumber", label: labels.policyNumber },
    { key: "startDate", label: labels.startDate },
    { key: "expiryDate", label: labels.expiryDate },
    { key: "premium", label: labels.premium },
  ];

  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-8">
      {data.previewTitle ? (
        <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">{data.previewTitle}</p>
      ) : null}
      <h2 className="mt-2 text-lg font-semibold text-slate-900">Extracted details</h2>
      <div className="mt-6 space-y-4">
        {fields.map((field) => (
          <Input
            key={field.key}
            label={field.label}
            value={editing ? form[field.key] : displayValue(form[field.key])}
            disabled={!editing}
            onChange={(event) => update(field.key, event.target.value)}
          />
        ))}
      </div>
      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={() => setEditing((value) => !value)}>
          {editing ? "Done editing" : "Edit"}
        </Button>
        <Button onClick={() => void confirm()} disabled={saving}>
          {saving ? "Saving…" : "Confirm"}
        </Button>
      </div>
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense
      fallback={
        <p className="flex min-h-screen items-center justify-center text-sm text-slate-500">
          Loading…
        </p>
      }
    >
      <ReviewContent />
    </Suspense>
  );
}

function ReviewContent() {
  const params = useSearchParams();
  const documentId = params.get("id") ?? "";
  const query = useQuery({
    queryKey: ["extraction", documentId],
    queryFn: () => getExtraction(documentId),
    enabled: Boolean(documentId),
  });

  return (
    <AppShell>
      {!documentId ? (
        <p className="text-sm text-rose-600">Missing document id. Upload the file again.</p>
      ) : null}
      {query.isLoading ? <p className="text-sm text-slate-500">Loading details…</p> : null}
      {query.error ? (
        <p className="text-sm text-rose-600">
          {query.error instanceof Error ? query.error.message : "Unable to load extraction."}
        </p>
      ) : null}
      {query.data ? <ReviewForm data={query.data} documentId={documentId} /> : null}
    </AppShell>
  );
}
