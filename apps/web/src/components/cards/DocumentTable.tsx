import { cn } from "@/utils";
import type { DocumentStatus, VaultDocument } from "@/types";
import { FileText } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

function statusTone(status: DocumentStatus): "info" | "warning" | "success" | "neutral" {
  if (status === "Processing") return "info";
  if (status === "Needs review") return "warning";
  if (status === "Reviewed" || status === "Reminder set" || status === "Action created") return "success";
  return "neutral";
}

function fileIconClass(name: string): string {
  if (/\.pdf$/i.test(name)) return "bg-rose-50 text-rose-600";
  if (/\.(png|jpe?g|webp)$/i.test(name)) return "bg-sky-50 text-sky-600";
  return "bg-slate-100 text-slate-600";
}

export function DocumentTable({
  caption,
  columns,
  children,
}: {
  caption: string;
  columns: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
      <div role="table" aria-label={caption}>
        <div
          role="row"
          className="hidden grid-cols-[minmax(0,2.2fr)_minmax(0,0.9fr)_minmax(0,1fr)_minmax(0,0.9fr)_minmax(0,1.1fr)] gap-4 border-b border-slate-100 px-4 py-3 text-sm text-slate-400 sm:grid"
        >
          {columns.map((column, index) => (
            <div
              key={column}
              role="columnheader"
              className={index === columns.length - 1 ? "text-right" : "min-w-0"}
            >
              {column}
            </div>
          ))}
        </div>
        <div role="rowgroup" className="divide-y divide-slate-100">
          {children}
        </div>
      </div>
    </div>
  );
}

function Cell({
  label,
  children,
  className,
}: {
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div role="cell" className={cn("min-w-0", className)}>
      {label ? <span className="mr-2 text-xs text-slate-400 sm:hidden">{label}</span> : null}
      {children}
    </div>
  );
}

export function DocumentRow({
  document,
  typeLabel,
  mode = "inbox",
  onView,
  onReview,
  onDelete,
}: {
  document: VaultDocument;
  typeLabel?: string;
  mode?: "inbox" | "library";
  onView: () => void;
  onReview?: () => void;
  onDelete: () => void;
}) {
  const showReview = mode === "inbox" && onReview;
  const displayType = typeLabel ?? document.type;

  return (
    <div
      role="row"
      className="grid grid-cols-1 gap-2 px-4 py-3.5 sm:grid-cols-[minmax(0,2.2fr)_minmax(0,0.9fr)_minmax(0,1fr)_minmax(0,0.9fr)_minmax(0,1.1fr)] sm:items-center sm:gap-4"
    >
      <Cell>
        <button
          type="button"
          onClick={onView}
          className="flex w-full min-w-0 max-w-full items-center gap-3 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          title={`Open ${document.name}`}
        >
          <span
            className={cn(
              "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
              fileIconClass(document.name),
            )}
            aria-hidden="true"
          >
            <FileText className="h-4 w-4" />
          </span>
          <span className="filename-scroll flex-1 text-sm font-semibold text-slate-900">
            {document.name}
          </span>
        </button>
      </Cell>
      <Cell label="Type">
        <p className="truncate text-sm text-slate-500" title={displayType}>
          {displayType}
        </p>
      </Cell>
      <Cell label="Important date">
        <p className="truncate text-sm text-slate-500">{document.importantDate || "—"}</p>
      </Cell>
      <Cell label="Status">
        <Badge tone={statusTone(document.status)}>{document.status}</Badge>
      </Cell>
      <Cell className="sm:text-right">
        <div className="flex flex-wrap gap-3 sm:justify-end">
          <button
            type="button"
            className="rounded text-sm font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            onClick={onView}
          >
            View
          </button>
          {showReview ? (
            <button
              type="button"
              className="rounded text-sm font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              onClick={onReview}
            >
              Review
            </button>
          ) : null}
          <button
            type="button"
            className="rounded text-sm font-medium text-rose-500 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
            onClick={onDelete}
          >
            Delete
          </button>
        </div>
      </Cell>
    </div>
  );
}

export function TablePagination({
  label,
  page,
  totalPages,
  onPage,
}: {
  label: string;
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <nav className="mt-4 flex items-center justify-center gap-4" aria-label={label}>
      <Button variant="ghost" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous
      </Button>
      <p className="text-sm text-slate-500" aria-live="polite">
        Page {page} of {totalPages}
      </p>
      <Button variant="ghost" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
        Next
      </Button>
    </nav>
  );
}
