"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { getExtraction, updateExtraction } from "@/services/api/document.service";
import type { ExtractedFields } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

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

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-900">
          {data.previewTitle}
        </h2>
        <ul className="mt-4 space-y-2 text-sm text-slate-600">
          {data.previewLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">AI found these details</h2>
          <Badge tone="success">High confidence</Badge>
        </div>
        <div className="mt-5 space-y-4">
          <Input
            label="Document type"
            value={form.documentType}
            disabled={!editing}
            onChange={(event) => update("documentType", event.target.value)}
          />
          <Input
            label="Provider"
            value={form.provider}
            disabled={!editing}
            onChange={(event) => update("provider", event.target.value)}
          />
          <Input
            label="Policy number"
            value={form.policyNumber}
            disabled={!editing}
            onChange={(event) => update("policyNumber", event.target.value)}
          />
          <Input
            label="Start date"
            value={form.startDate}
            disabled={!editing}
            onChange={(event) => update("startDate", event.target.value)}
          />
          <Input
            label="Expiry date"
            value={form.expiryDate}
            disabled={!editing}
            onChange={(event) => update("expiryDate", event.target.value)}
          />
          <Input
            label="Premium"
            value={form.premium}
            disabled={!editing}
            onChange={(event) => update("premium", event.target.value)}
          />
        </div>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
          <Button variant="ghost" onClick={() => setEditing((value) => !value)}>
            {editing ? "Lock details" : "Edit details"}
          </Button>
          <Button onClick={() => void confirm()} disabled={saving}>
            {saving ? "Saving…" : "Confirm & continue"}
          </Button>
        </div>
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      </div>
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
      {query.isLoading ? (
        <p className="text-sm text-slate-500">Loading extraction…</p>
      ) : null}
      {query.error ? (
        <p className="text-sm text-rose-600">
          {query.error instanceof Error ? query.error.message : "Unable to load extraction."}
        </p>
      ) : null}
      {query.data ? <ReviewForm data={query.data} documentId={documentId} /> : null}
    </AppShell>
  );
}
