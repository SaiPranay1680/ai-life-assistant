import type { VaultDocument } from "@/types";

export function DocumentCard({
  document,
  onView,
  onReview,
  onDelete,
}: {
  document: VaultDocument;
  onView: () => void;
  onReview: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-white px-4 py-4 sm:grid-cols-5 sm:items-center">
      <p className="font-medium text-slate-900">{document.name}</p>
      <p className="text-sm text-slate-500">{document.type}</p>
      <p className="text-sm text-slate-500">{document.importantDate}</p>
      <p className="text-sm text-slate-700">{document.status}</p>
      <div className="flex flex-wrap gap-2 sm:justify-end">
        <button type="button" className="text-sm font-medium text-blue-600 hover:underline" onClick={onView}>
          View
        </button>
        <button type="button" className="text-sm font-medium text-blue-600 hover:underline" onClick={onReview}>
          Review
        </button>
        <button type="button" className="text-sm font-medium text-rose-600 hover:underline" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  );
}
