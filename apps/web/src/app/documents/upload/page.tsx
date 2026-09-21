"use client";

import { AppShell } from "@/components/layout/AppShell";
import { NotificationCard } from "@/components/cards/AttentionCard";
import { UploadBox } from "@/components/upload/UploadBox";
import { Badge } from "@/components/ui/Badge";
import { uploadDocument } from "@/services/api/document.service";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function UploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(file: File) {
    setError(null);
    setBusy(true);
    try {
      const result = await uploadDocument(file);
      router.push(
        `/documents/processing?id=${encodeURIComponent(result.id)}&file=${encodeURIComponent(result.fileName)}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <UploadBox onFile={onFile} busy={busy} />
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      {busy ? (
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full w-2/3 animate-pulse rounded-full bg-blue-600" />
        </div>
      ) : null}
      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Badge tone="info">Bills</Badge>
        <Badge tone="warning">Insurance</Badge>
        <Badge tone="success">Warranty</Badge>
        <span className="text-sm text-slate-500">Important records</span>
      </div>
      <NotificationCard
        className="mt-6"
        title="Bills, policies, and records — not a gallery"
        body="Upload a bill, insurance policy, invoice, warranty, or important record. Family photos, newspapers, and random files are not stored. Unknown documents will ask you before they are kept."
      />
    </AppShell>
  );
}
