"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
<<<<<<< Updated upstream
import { getExtraction, updateExtraction } from "@/services/api/document.service";
import type { ExtractedFields } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
=======
import { decideDocumentPurpose, getExtraction, updateExtraction } from "@/services/api/document.service";
import type { ExtractedField, ExtractedFields } from "@/types";
import { FOLDER_CATEGORIES, FOLDER_TAXONOMY, folderFor } from "@/utils/documentFolders";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

function humanize(key: string): string {
  return key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function reviewFields(data: ExtractedFields): ExtractedField[] {
  const type = (data.documentType || "").toLowerCase();
  const hideProvider = type.includes("insurance");
  const fromApi = (data.fields ?? []).filter((field) => {
    if (!field.value.trim() || field.name === "currency") return false;
    if (field.name === "folder_category" || field.name === "folder_subcategory") return false;
    if (hideProvider && (field.name === "provider" || field.label?.toLowerCase() === "provider")) {
      return false;
    }
    return true;
  });
  const unique: ExtractedField[] = [];
  const seen = new Set<string>();
  for (const field of fromApi) {
    const fingerprint = `${(field.label || field.name).toLowerCase()}|${field.value.replace(/\s+/g, "").toLowerCase()}`;
    if (seen.has(fingerprint)) continue;
    seen.add(fingerprint);
    unique.push(field);
  }
  if (unique.length > 0) return unique;
  const fallback: Array<[string, string]> = [
    ["policyNumber", data.policyNumber],
    ["startDate", data.startDate ?? ""],
    ["expiryDate", data.expiryDate],
    ["premium", data.premium],
  ];
  if (!hideProvider) fallback.unshift(["provider", data.provider]);
  return fallback
    .filter(([, value]) => value.trim())
    .map(([name, value]) => ({
      name,
      value,
      evidence: "",
      page: 1,
      confidence: 0,
      label: humanize(name),
    }));
}

function initialForm(data: ExtractedFields, fields: ExtractedField[]): Record<string, string> {
  const guessed = folderFor({
    name: data.previewTitle,
    type: data.documentType,
    purposeCategory: data.purposeCategory,
    folderCategory: data.folderCategory,
    folderSubcategory: data.folderSubcategory,
  });
  const form: Record<string, string> = {
    documentType: data.documentType,
    folderCategory: guessed.category,
    folderSubcategory: guessed.subcategory,
  };
  for (const field of fields) {
    form[field.name] = field.value;
  }
  return form;
}
>>>>>>> Stashed changes

function confidenceTone(fields: ExtractedField[]): { label: string; tone: "success" | "warning" | "danger" } {
  if (fields.length === 0) return { label: "Needs a look", tone: "warning" };
  const average = fields.reduce((sum, field) => sum + (field.confidence || 0), 0) / fields.length;
  if (average >= 0.85) return { label: "High confidence", tone: "success" };
  if (average >= 0.6) return { label: "Check these values", tone: "warning" };
  return { label: "Low confidence", tone: "danger" };
}

function ReviewForm({ data, documentId }: { data: ExtractedFields; documentId: string }) {
  const router = useRouter();
<<<<<<< Updated upstream
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
=======
  const fields = useMemo(() => reviewFields(data), [data]);
  const badge = useMemo(() => confidenceTone(fields), [fields]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(() => initialForm(data, fields));
>>>>>>> Stashed changes

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function confirm() {
    setError(null);
    setSaving(true);
    try {
<<<<<<< Updated upstream
      await updateExtraction(documentId, form);
=======
      const structuredFields: Record<string, string> = {};
      for (const field of fields) {
        structuredFields[field.name] = form[field.name] ?? "";
      }
      await updateExtraction(documentId, {
        documentType: form.documentType,
        provider: form.provider ?? form.merchant ?? form.warranty_provider ?? data.provider ?? "",
        policyNumber: form.policyNumber ?? form.policy_number ?? form.service_number ?? "",
        startDate: form.startDate ?? form.effective_date ?? form.purchase_date ?? "",
        expiryDate: form.expiryDate ?? form.expiry_date ?? form.due_date ?? form.warranty_expiry ?? "",
        premium: form.premium ?? form.amount_due ?? form.total ?? "",
        structuredFields,
        folderCategory: form.folderCategory,
        folderSubcategory: form.folderSubcategory,
      });
>>>>>>> Stashed changes
      router.push("/actions");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save extraction.");
    } finally {
      setSaving(false);
    }
  }

<<<<<<< Updated upstream
=======
  async function decide(decision: "keep" | "discard") {
    setError(null);
    setSaving(true);
    try {
      await decideDocumentPurpose(documentId, decision);
      router.push(decision === "keep" ? "/actions" : "/documents/upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save this choice.");
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
        <h2 className="text-lg font-semibold text-slate-900">Invalid document</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">Try uploading another file.</p>
        <div className="mt-6">
          <Button onClick={() => router.push("/documents/upload")}>Upload another</Button>
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
          Document type is unclear. Keep it or upload another.
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

>>>>>>> Stashed changes
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
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-900">What you need to know</h2>
          <Badge tone={badge.tone}>{badge.label}</Badge>
        </div>
        <div className="mt-5 space-y-4">
          <label className="block text-left">
            <span className="mb-1.5 block text-sm font-semibold text-slate-800">Category</span>
            <select
              value={form.folderCategory ?? "Records"}
              onChange={(event) => {
                const next = event.target.value;
                const options = FOLDER_TAXONOMY[next] ?? FOLDER_TAXONOMY.Records;
                setForm((current) => ({
                  ...current,
                  folderCategory: next,
                  folderSubcategory: options.includes(current.folderSubcategory)
                    ? current.folderSubcategory
                    : options[0],
                }));
              }}
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >
              {FOLDER_CATEGORIES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-slate-400">
              Auto-filled from the document. Change it if this is wrong.
            </span>
          </label>
          <label className="block text-left">
            <span className="mb-1.5 block text-sm font-semibold text-slate-800">Subcategory</span>
            <select
              value={form.folderSubcategory ?? ""}
              onChange={(event) => update("folderSubcategory", event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >
              {(FOLDER_TAXONOMY[form.folderCategory] ?? FOLDER_TAXONOMY.Records).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <Input
            label="Document type"
            value={form.documentType}
            disabled={!editing}
            onChange={(event) => update("documentType", event.target.value)}
          />
<<<<<<< Updated upstream
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
=======
          {fields.map((field) => (
            <div key={field.name}>
              <Input
                label={field.label || humanize(field.name)}
                value={form[field.name] ?? ""}
                disabled={!editing}
                onChange={(event) => update(field.name, event.target.value)}
              />
              {!editing && field.evidence ? (
                <p className="mt-1 text-xs text-slate-400">From the document: {field.evidence}</p>
              ) : null}
            </div>
          ))}
>>>>>>> Stashed changes
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
        <p className="text-sm text-rose-600">Missing document. Please upload the file again.</p>
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
