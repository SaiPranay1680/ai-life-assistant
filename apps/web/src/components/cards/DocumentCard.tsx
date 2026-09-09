import type { VaultDocument } from "@/types";

export function DocumentCard({ document }: { document: VaultDocument }) {
  return (
    <div className="grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-white px-4 py-4 sm:grid-cols-4 sm:items-center">
      <p className="font-medium text-slate-900">{document.name}</p>
      <p className="text-sm text-slate-500">{document.type}</p>
      <p className="text-sm text-slate-500">{document.importantDate}</p>
      <p className="text-sm text-slate-700 sm:text-right">{document.status}</p>
    </div>
  );
}
