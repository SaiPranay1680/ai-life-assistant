"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { getExtraction, updateExtraction } from "@/services/api/document.service";
import type { ExtractedFields, ExtractedValue } from "@/types";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

type FieldDef = { key: string; label: string };

const UTILITY_BILL_FIELDS: FieldDef[] = [
  { key: "provider", label: "Provider" },
  { key: "bill_number", label: "Bill number" },
  { key: "customer_id", label: "Customer ID" },
  { key: "billing_period_start", label: "Billing period start" },
  { key: "billing_period_end", label: "Billing period end" },
  { key: "due_date", label: "Due date" },
  { key: "amount_due", label: "Amount due" },
  { key: "service_address", label: "Service address" },
];

const PURCHASE_RECEIPT_FIELDS: FieldDef[] = [
  { key: "merchant", label: "Merchant" },
  { key: "receipt_number", label: "Receipt number" },
  { key: "purchase_date", label: "Purchase date" },
  { key: "subtotal", label: "Subtotal" },
  { key: "tax", label: "Tax" },
  { key: "total", label: "Total" },
  { key: "payment_method", label: "Payment method" },
];

const WARRANTY_FIELDS: FieldDef[] = [
  { key: "product", label: "Product" },
  { key: "brand", label: "Brand" },
  { key: "model", label: "Model" },
  { key: "serial_number", label: "Serial number" },
  { key: "warranty_provider", label: "Warranty provider" },
  { key: "purchase_date", label: "Purchase date" },
  { key: "warranty_start", label: "Warranty start" },
  { key: "warranty_expiry", label: "Warranty expiry" },
  { key: "warranty_duration", label: "Warranty duration" },
];

const LEGACY_FIELDS: FieldDef[] = [
  { key: "provider", label: "Provider" },
  { key: "policyNumber", label: "Policy number" },
  { key: "startDate", label: "Start date" },
  { key: "expiryDate", label: "Expiry date" },
  { key: "premium", label: "Premium" },
];

function valueText(value: ExtractedValue | null | undefined): string {
  if (!value) return "";
  return (value.raw || value.normalized || "").trim();
}

function structuredTypeId(data: ExtractedFields): string {
  const fromStructured = data.structuredExtraction?.document_type;
  if (fromStructured && typeof fromStructured === "object" && !Array.isArray(fromStructured)) {
    const id = (fromStructured.normalized || fromStructured.raw || "").toLowerCase();
    if (id) return id.replace(/\s+/g, "_");
  }
  const label = (data.documentType || "").toLowerCase();
  if (label.includes("bill") || label.includes("utility")) return "utility_bill";
  if (label.includes("health") && label.includes("insurance")) return "health_insurance";
  if (
    (label.includes("car") || label.includes("motor") || label.includes("auto")) &&
    label.includes("insurance")
  ) {
    return "car_insurance";
  }
  if (label.includes("insurance")) return "insurance";
  if (label.includes("purchase") || label.includes("receipt")) return "purchase_receipt";
  if (label.includes("warranty")) return "warranty";
  return "generic";
}

function fieldDefsFor(typeId: string): FieldDef[] {
  if (typeId === "utility_bill") return UTILITY_BILL_FIELDS;
  if (typeId === "purchase_receipt") return PURCHASE_RECEIPT_FIELDS;
  if (typeId === "warranty") return WARRANTY_FIELDS;
  return LEGACY_FIELDS;
}

function usesStructuredForm(typeId: string): boolean {
  return typeId === "utility_bill" || typeId === "purchase_receipt" || typeId === "warranty";
}

function formatPurchaseItems(data: ExtractedFields): string[] {
  const items = data.structuredExtraction?.items;
  if (!Array.isArray(items) || items.length === 0) return [];
  return items.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      return `Item ${index + 1}`;
    }
    const row = item as Record<string, ExtractedValue | null | undefined>;
    const name = valueText(row.name) || `Item ${index + 1}`;
    const qty = valueText(row.quantity) || "1";
    const amount = valueText(row.amount) || valueText(row.unit_price) || valueText(row.total);
    return amount ? `${name} — Qty ${qty} — ${amount}` : `${name} — Qty ${qty}`;
  });
}

function initialForm(data: ExtractedFields): Record<string, string> {
  const typeId = structuredTypeId(data);
  const form: Record<string, string> = {
    documentType: data.documentType,
  };
  if (usesStructuredForm(typeId) && data.structuredExtraction) {
    for (const field of fieldDefsFor(typeId)) {
      const raw = data.structuredExtraction[field.key];
      form[field.key] =
        raw && typeof raw === "object" && !Array.isArray(raw) ? valueText(raw) : "";
    }
    return form;
  }
  form.provider = data.provider;
  form.policyNumber = data.policyNumber;
  form.startDate = data.startDate ?? "";
  form.expiryDate = data.expiryDate;
  form.premium = data.premium;
  return form;
}

function ReviewForm({ data, documentId }: { data: ExtractedFields; documentId: string }) {
  const router = useRouter();
  const typeId = useMemo(() => structuredTypeId(data), [data]);
  const fieldDefs = fieldDefsFor(typeId);
  const itemLines = useMemo(
    () => (typeId === "purchase_receipt" ? formatPurchaseItems(data) : []),
    [data, typeId],
  );
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(() => initialForm(data));

  function update(field: string, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function confirm() {
    setError(null);
    setSaving(true);
    try {
      if (usesStructuredForm(typeId)) {
        const structuredFields: Record<string, string> = {};
        for (const field of fieldDefs) {
          structuredFields[field.key] = form[field.key] ?? "";
        }
        const fallbackType =
          typeId === "purchase_receipt"
            ? "Purchase"
            : typeId === "warranty"
              ? "Warranty"
              : "Bill";
        await updateExtraction(documentId, {
          documentType: form.documentType || fallbackType,
          provider:
            form.warranty_provider ?? form.merchant ?? form.provider ?? "",
          structuredFields,
        });
      } else {
        await updateExtraction(documentId, {
          documentType: form.documentType,
          provider: form.provider ?? "",
          policyNumber: form.policyNumber ?? "",
          startDate: form.startDate ?? "",
          expiryDate: form.expiryDate ?? "",
          premium: form.premium ?? "",
        });
      }
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
          {fieldDefs.map((field) => (
            <Input
              key={field.key}
              label={field.label}
              value={form[field.key] ?? ""}
              disabled={!editing}
              onChange={(event) => update(field.key, event.target.value)}
            />
          ))}
          {itemLines.length > 0 ? (
            <div>
              <p className="mb-2 text-sm font-medium text-slate-700">Items</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {itemLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
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
