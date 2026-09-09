"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DocumentCard } from "@/components/cards/DocumentCard";
import { Button } from "@/components/ui/Button";
import { getDocuments } from "@/services/api/document.service";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

export default function DocumentsPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const query = useQuery({ queryKey: ["documents"], queryFn: getDocuments });
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return (query.data ?? []).filter((doc) =>
      `${doc.name} ${doc.type} ${doc.importantDate} ${doc.status}`
        .toLowerCase()
        .includes(term),
    );
  }, [q, query.data]);

  return (
    <AppShell>
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" />
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Search documents, providers, dates..."
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pr-3 pl-10 text-sm"
          />
        </label>
        <Button onClick={() => router.push("/documents/upload")}>
          <Plus className="h-4 w-4" />
          Upload
        </Button>
      </div>
      <div className="mt-6 hidden grid-cols-4 px-4 text-xs font-medium tracking-wide text-slate-400 uppercase sm:grid">
        <span>Document</span>
        <span>Type</span>
        <span>Important date</span>
        <span className="text-right">Status</span>
      </div>
      <div className="mt-2 space-y-2">
        {query.isLoading ? (
          <p className="text-sm text-slate-500">Loading documents…</p>
        ) : null}
        {!query.isLoading && filtered.length === 0 ? (
          <p className="rounded-xl bg-white p-6 text-sm text-slate-500">
            No documents match your search.
          </p>
        ) : (
          filtered.map((document) => (
            <DocumentCard key={document.id} document={document} />
          ))
        )}
      </div>
    </AppShell>
  );
}
