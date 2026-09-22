import { DocumentRow } from "@/components/cards/DocumentTable";
import type { VaultDocument } from "@/types";

export function DocumentCard({
  document,
  mode = "inbox",
  typeLabel,
  onView,
  onReview,
  onDelete,
}: {
  document: VaultDocument;
  mode?: "inbox" | "library";
  typeLabel?: string;
  onView: () => void;
  onReview?: () => void;
  onDelete: () => void;
}) {
  return (
    <DocumentRow
      document={document}
      mode={mode}
      typeLabel={typeLabel}
      onView={onView}
      onReview={onReview}
      onDelete={onDelete}
    />
  );
}
