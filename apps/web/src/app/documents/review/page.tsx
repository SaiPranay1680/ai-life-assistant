"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { getExtraction } from "@/services/api/document.service";
import type { ExtractedFields } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

function ReviewForm({ data }: { data: ExtractedFields }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    documentType: data.documentType,
    provider: data.provider,
    policyNumber: data.policyNumber,
    expiryDate: data.expiryDate,
    premium: data.premium,
  });

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
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
          <Button onClick={() => router.push("/actions")}>Confirm & continue</Button>
        </div>
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const query = useQuery({ queryKey: ["extraction"], queryFn: getExtraction });

  return (
    <AppShell>
      {query.isLoading ? (
        <p className="text-sm text-slate-500">Loading extraction…</p>
      ) : null}
      {query.data ? <ReviewForm data={query.data} /> : null}
    </AppShell>
  );
}
