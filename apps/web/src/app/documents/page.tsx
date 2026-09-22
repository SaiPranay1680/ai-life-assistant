"use client";

import { AppShell } from "@/components/layout/AppShell";
import { FolderCard } from "@/components/cards/FolderCard";
import { DocumentRow, DocumentTable, TablePagination } from "@/components/cards/DocumentTable";
import { Button } from "@/components/ui/Button";
import { deleteDocument, getDocuments, viewDocumentFile } from "@/services/api/document.service";
import type { VaultDocument } from "@/types";
import { FOLDER_CATEGORIES, FOLDER_TAXONOMY, isLibraryDocument } from "@/utils/documentFolders";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

const PAGE_SIZE = 5;

function withExtras(canonical: string[], counts: Map<string, number>) {
  const extras = [...counts.keys()]
    .filter((name) => name && !canonical.includes(name) && (counts.get(name) ?? 0) > 0)
    .sort((a, b) => a.localeCompare(b));
  return [...canonical, ...extras];
}

function LibraryContent() {
  const router = useRouter();
  const params = useSearchParams();
  const category = params.get("category") ?? "";
  const subcategory = params.get("sub") ?? "";
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["documents"], queryFn: getDocuments });

  const library = useMemo(
    () => (query.data ?? []).filter((doc) => isLibraryDocument(doc.status)),
    [query.data],
  );

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return library.filter((doc) => {
      if (category && doc.category !== category) return false;
      if (subcategory && doc.subcategory !== subcategory) return false;
      if (!term) return true;
      return `${doc.name} ${doc.type} ${doc.category} ${doc.subcategory} ${doc.importantDate}`
        .toLowerCase()
        .includes(term);
    });
  }, [library, q, category, subcategory]);

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const name of FOLDER_CATEGORIES) counts.set(name, 0);
    for (const doc of library) {
      counts.set(doc.category, (counts.get(doc.category) ?? 0) + 1);
    }
    return counts;
  }, [library]);

  const knownSubs = FOLDER_TAXONOMY[category];
  const subcategoryNames = knownSubs ?? [];
  const subcategoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const name of subcategoryNames) counts.set(name, 0);
    for (const doc of library) {
      if (doc.category !== category) continue;
      counts.set(doc.subcategory, (counts.get(doc.subcategory) ?? 0) + 1);
    }
    return counts;
  }, [library, category, subcategoryNames]);

  const searching = q.trim().length > 0;
  const showRootFolders = !searching && !category;
  const showSubfolders = !searching && Boolean(category) && !subcategory && Boolean(knownSubs);
  const showFiles = searching || Boolean(subcategory) || (Boolean(category) && !knownSubs);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const ready = !query.isLoading && !query.isError;

  const searchPlaceholder = subcategory
    ? `Search files in ${subcategory}...`
    : category
      ? `Search files in ${category}...`
      : "Search files, health, vehicle, bills...";

  function go(nextCategory = "", nextSub = "") {
    setPage(1);
    setQ("");
    const search = new URLSearchParams();
    if (nextCategory) search.set("category", nextCategory);
    if (nextSub) search.set("sub", nextSub);
    const queryString = search.toString();
    router.push(queryString ? `/documents?${queryString}` : "/documents");
  }

  function openFile(document: VaultDocument) {
    void viewDocumentFile(document.id, document.name).catch((error) => {
      window.alert(error instanceof Error ? error.message : "Unable to open this file.");
    });
  }

  function removeFile(document: VaultDocument) {
    if (!window.confirm(`Delete ${document.name}?`)) return;
    void deleteDocument(document.id)
      .then(() => query.refetch())
      .catch((error) => {
        window.alert(error instanceof Error ? error.message : "Unable to delete this document.");
      });
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {category || searching ? (
          <nav className="flex min-w-0 flex-wrap items-center gap-1 text-sm text-slate-500" aria-label="Breadcrumb">
            <ol className="flex min-w-0 flex-wrap items-center gap-1">
              <li>
                <button
                  type="button"
                  className="rounded text-slate-500 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  onClick={() => go()}
                >
                  All folders
                </button>
              </li>
              {category ? (
                <li className="flex items-center gap-1">
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  {subcategory || searching ? (
                    <button
                      type="button"
                      className="rounded text-slate-500 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                      onClick={() => go(category)}
                    >
                      {category}
                    </button>
                  ) : (
                    <span className="font-medium text-slate-800" aria-current="page">
                      {category}
                    </span>
                  )}
                </li>
              ) : null}
              {subcategory ? (
                <li className="flex items-center gap-1">
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="font-medium text-slate-800" aria-current="page">
                    {subcategory}
                  </span>
                </li>
              ) : null}
              {searching && !subcategory ? (
                <li className="flex items-center gap-1">
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="font-medium text-slate-800" aria-current="page">
                    Search
                  </span>
                </li>
              ) : null}
            </ol>
          </nav>
        ) : (
          <p className="text-sm text-slate-500">
            {library.length} confirmed {library.length === 1 ? "file" : "files"} across{" "}
            {FOLDER_CATEGORIES.length} folders
          </p>
        )}
        <label className="relative block w-full sm:max-w-sm">
          <span className="sr-only">{searchPlaceholder}</span>
          <Search className="pointer-events-none absolute top-3 left-3 h-4 w-4 text-slate-400" aria-hidden="true" />
          <input
            value={q}
            onChange={(event) => {
              setQ(event.target.value);
              setPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full rounded-full border border-slate-200 bg-white py-2.5 pr-3 pl-10 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
      </div>

      {query.isLoading ? <p className="mt-6 text-sm text-slate-500">Loading documents…</p> : null}
      {query.isError ? (
        <div className="mt-6 rounded-2xl border border-rose-100 bg-white p-6">
          <p role="alert" className="text-sm text-rose-600">
            {query.error instanceof Error ? query.error.message : "Unable to load documents."}
          </p>
          <Button className="mt-3" variant="secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
            Try again
          </Button>
        </div>
      ) : null}

      {ready && showRootFolders ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {withExtras(FOLDER_CATEGORIES, categoryCounts).map((name) => (
            <FolderCard
              key={name}
              title={name}
              count={categoryCounts.get(name) ?? 0}
              onOpen={() => go(name)}
            />
          ))}
        </div>
      ) : null}

      {ready && showSubfolders ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {withExtras(subcategoryNames, subcategoryCounts).map((name) => (
            <FolderCard
              key={`${category}-${name}`}
              title={name}
              count={subcategoryCounts.get(name) ?? 0}
              onOpen={() => go(category, name)}
            />
          ))}
        </div>
      ) : null}

      {ready && showFiles ? (
        <div className="mt-6">
          {pageItems.length === 0 ? (
            <p className="rounded-2xl border border-slate-100 bg-white p-6 text-sm text-slate-500">
              {searching ? "No files match this search." : "No files in this folder."}
            </p>
          ) : (
            <DocumentTable
              caption={
                subcategory
                  ? `Files in ${category} ${subcategory}`
                  : category
                    ? `Files in ${category}`
                    : "Matching documents"
              }
              columns={["File name", "Type", "Important date", "Status", "Actions"]}
            >
              {pageItems.map((document) => (
                <DocumentRow
                  key={document.id}
                  mode="library"
                  document={document}
                  typeLabel={document.subcategory || document.type}
                  onView={() => openFile(document)}
                  onDelete={() => removeFile(document)}
                />
              ))}
            </DocumentTable>
          )}
          {filtered.length > 0 ? (
            <TablePagination
              label="Documents pagination"
              page={currentPage}
              totalPages={totalPages}
              onPage={setPage}
            />
          ) : null}
        </div>
      ) : null}
    </AppShell>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense
      fallback={
        <p className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading…</p>
      }
    >
      <LibraryContent />
    </Suspense>
  );
}
