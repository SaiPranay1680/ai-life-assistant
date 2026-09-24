"use client";

import { AppShell } from "@/components/layout/AppShell";
import { NotificationCard } from "@/components/cards/AttentionCard";
import { DocumentRow, DocumentTable, TablePagination } from "@/components/cards/DocumentTable";
import { UploadBox } from "@/components/upload/UploadBox";
import { Modal } from "@/components/ui/Modal";
import { apiClient } from "@/services/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { deleteDocument, getDocuments, uploadDocument, viewDocumentFile } from "@/services/api/document.service";
import type { VaultDocument } from "@/types";
import { isInboxDocument } from "@/utils/documentFolders";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

const PAGE_SIZE = 5;

export default function UploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [passwordDocId, setPasswordDocId] = useState<string | null>(null);
  const [passwordValue, setPasswordValue] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["documents"], queryFn: getDocuments });

  const inbox = useMemo(
    () => (query.data ?? []).filter((doc) => isInboxDocument(doc.status)),
    [query.data],
  );

  const pending = useMemo(() => {
    const term = q.trim().toLowerCase();
    return inbox.filter((doc) => {
      if (!term) return true;
      return `${doc.name} ${doc.type} ${doc.status} ${doc.category} ${doc.subcategory}`
        .toLowerCase()
        .includes(term);
    });
  }, [inbox, q]);

  const totalPages = Math.max(1, Math.ceil(pending.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = pending.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  async function onFile(file: File) {
    setError(null);
    setBusy(true);
    try {
      const result = await uploadDocument(file);
      if (result.status === "PASSWORD_REQUIRED") {
        setPasswordDocId(result.id);
        setPasswordModalOpen(true);
        return;
      }
      router.push(
        `/documents/processing?id=${encodeURIComponent(result.id)}&file=${encodeURIComponent(result.fileName)}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitPassword() {
    if (!passwordDocId) return;
    setPasswordError(null);
    setBusy(true);
    try {
      const { data, error } = await (async () => {
        try {
          const resp = await apiClient.post(`/documents/${encodeURIComponent(passwordDocId)}/decrypt`, { password: passwordValue });
          return { data: resp.data };
        } catch (e: unknown) {
          return { error: e };
        }
      })();
      if (error) {
        const msg = (error as any)?.response?.data?.detail || "Unable to decrypt PDF. Please try again.";
        setPasswordError(msg);
        return;
      }
      setPasswordModalOpen(false);
      setPasswordValue("");
      setPasswordDocId(null);
      // navigate to processing
      router.push(`/documents/processing?id=${encodeURIComponent(data.id || passwordDocId)}&file=`);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Unable to decrypt PDF.");
    } finally {
      setBusy(false);
    }
  }

  function openFile(document: VaultDocument) {
    void viewDocumentFile(document.id, document.name).catch((caught) => {
      window.alert(caught instanceof Error ? caught.message : "Unable to open this file.");
    });
  }

  function removeFile(document: VaultDocument) {
    if (!window.confirm(`Delete ${document.name}?`)) return;
    void deleteDocument(document.id)
      .then(() => query.refetch())
      .catch((caught) => {
        window.alert(caught instanceof Error ? caught.message : "Unable to delete this document.");
      });
  }

  return (
    <AppShell>
      <UploadBox onFile={onFile} busy={busy} />
      <Modal open={passwordModalOpen} title="Password required" onClose={() => setPasswordModalOpen(false)}>
        <p className="text-sm text-slate-600">This PDF is password-protected. Enter the PDF password to continue.</p>
        <label className="mt-3 block">
          <input
            type="password"
            value={passwordValue}
            onChange={(e) => setPasswordValue(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-3 pl-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 mt-2"
          />
        </label>
        {passwordError ? <p className="mt-2 text-sm text-rose-600">{passwordError}</p> : null}
        <div className="mt-4 flex justify-end">
          <button className="btn btn-secondary mr-2" onClick={() => setPasswordModalOpen(false)} type="button">
            Cancel
          </button>
          <button className="btn btn-primary" onClick={submitPassword} type="button" disabled={busy}>
            Submit
          </button>
        </div>
      </Modal>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-rose-600">
          {error}
        </p>
      ) : null}
      {busy ? (
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
          <div className="h-full w-2/3 animate-pulse rounded-full bg-blue-600" />
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Badge tone="info">Bills</Badge>
        <Badge tone="warning">Insurance</Badge>
        <Badge tone="success">Warranty</Badge>
        <span className="text-sm text-slate-500">Important records</span>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start">
        <NotificationCard
          title="Supported documents"
          body="Upload bills, policies, invoices, warranties, or official records. After you confirm a file, it moves into Documents by category."
        />
        <aside className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">Search inbox</p>
          <label className="relative mt-3 block">
            <span className="sr-only">Search inbox by name, type, or category</span>
            <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" aria-hidden="true" />
            <input
              value={q}
              onChange={(event) => {
                setQ(event.target.value);
                setPage(1);
              }}
              placeholder="Name, type, category..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-3 pl-10 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
        </aside>
      </div>

      <section className="mt-8" aria-labelledby="waiting-heading">
        <h2 id="waiting-heading" className="mb-3 text-base font-semibold text-slate-900">
          Waiting for review
        </h2>
        {query.isLoading ? <p className="text-sm text-slate-500">Loading inbox…</p> : null}
        {query.isError ? (
          <div className="rounded-2xl border border-rose-100 bg-white p-6">
            <p role="alert" className="text-sm text-rose-600">
              {query.error instanceof Error ? query.error.message : "Unable to load inbox."}
            </p>
            <Button className="mt-3" variant="secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
              Try again
            </Button>
          </div>
        ) : null}
        {!query.isLoading && !query.isError && pageItems.length === 0 ? (
          <p className="rounded-2xl border border-slate-100 bg-white p-6 text-sm text-slate-500">
            {q.trim()
              ? "No matching documents in this inbox view."
              : "Nothing is waiting for review. Confirmed files are in Documents."}
          </p>
        ) : null}
        {!query.isLoading && !query.isError && pageItems.length > 0 ? (
          <DocumentTable
            caption="Documents waiting for review"
            columns={["File name", "Type", "Important date", "Status", "Actions"]}
          >
            {pageItems.map((document) => (
              <DocumentRow
                key={document.id}
                mode="inbox"
                document={document}
                onView={() => openFile(document)}
                onReview={() => router.push(`/documents/review?id=${encodeURIComponent(document.id)}`)}
                onDelete={() => removeFile(document)}
              />
            ))}
          </DocumentTable>
        ) : null}
        {!query.isLoading && !query.isError && pending.length > 0 ? (
          <TablePagination
            label="Inbox pagination"
            page={currentPage}
            totalPages={totalPages}
            onPage={setPage}
          />
        ) : null}
      </section>
    </AppShell>
  );
}
