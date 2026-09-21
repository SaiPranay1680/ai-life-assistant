import axios from "axios";
import type { DocumentType, DocumentStatus, ExtractedFields, VaultDocument } from "@/types";
import { apiClient } from "./client";

type ApiDocument = {
  id: string;
  original_filename: string;
  document_type: string | null;
  processing_status: string;
  important_date?: string | null;
  purpose_status?: string | null;
  purpose_reason?: string | null;
  purpose_category?: string | null;
  created_at: string | null;
};

function apiError(error: unknown, fallback: string): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
  }
  return error instanceof Error ? error : new Error(fallback);
}

function mapType(value: string | null): DocumentType {
  const key = (value ?? "").toLowerCase();
  if (key.includes("bill") && !key.includes("insurance")) return "Bill";
  if (key.includes("health") && (key.includes("insurance") || key.includes("policy"))) {
    return "Health Insurance";
  }
  if (
    (key.includes("car") || key.includes("motor") || key.includes("auto") || key.includes("vehicle")) &&
    (key.includes("insurance") || key.includes("policy"))
  ) {
    return "Car Insurance";
  }
  if (key.includes("insurance")) return "Insurance";
  if (key.includes("purchase") || key.includes("invoice") || key.includes("receipt")) return "Purchase";
  if (key.includes("warranty")) return "Warranty";
  if (key.includes("other")) return "Other";
  return "Important document";
}

function mapStatus(value: string): DocumentStatus {
  if (value === "ready_for_review" || value === "needs_review" || value === "ocr_required") return "Needs review";
  if (value === "needs_decision") return "Decide";
  if (value === "rejected") return "Rejected";
  if (value === "reviewed") return "Reviewed";
  if (value === "failed") return "Needs review";
  if (value === "uploaded" || value === "queued" || value === "processing") return "Processing";
  return "Processing";
}

function toVault(doc: ApiDocument): VaultDocument {
  return {
    id: doc.id,
    name: doc.original_filename,
    type: mapType(doc.document_type),
    importantDate: doc.important_date?.trim() ? doc.important_date : "—",
    status: mapStatus(doc.processing_status),
  };
}

export async function getDocuments(): Promise<VaultDocument[]> {
  try {
    const { data } = await apiClient.get<ApiDocument[]>("/documents");
    return data.map(toVault);
  } catch (error) {
    throw apiError(error, "Unable to load documents.");
  }
}

export async function uploadDocument(file: File): Promise<{ fileName: string; id: string }> {
  const allowed = ["application/pdf", "image/jpeg", "image/png", "image/jpg"];
  if (!allowed.includes(file.type) && !/\.(pdf|jpe?g|png)$/i.test(file.name)) {
    throw new Error("Only PDF, JPG or PNG files are allowed.");
  }
  if (file.size > 20 * 1024 * 1024) {
    throw new Error("File must be 20 MB or smaller.");
  }
  if (/jpe?g|png/i.test(file.type || file.name) && file.size > 10 * 1024 * 1024) {
    throw new Error("Photos and scans must be 10 MB or smaller.");
  }

  const body = new FormData();
  body.append("file", file);
  try {
    const { data } = await apiClient.post<{ id: string; status: string; original_filename: string }>(
      "/documents",
      body,
    );
    return { fileName: data.original_filename, id: data.id };
  } catch (error) {
    throw apiError(error, "Upload failed.");
  }
}

export async function getDocument(id: string): Promise<ApiDocument> {
  try {
    const { data } = await apiClient.get<ApiDocument>(`/documents/${id}`, { timeout: 120000 });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to load document.");
  }
}

export async function getExtraction(documentId: string): Promise<ExtractedFields> {
  try {
    const { data } = await apiClient.get<ExtractedFields>(`/documents/${documentId}/extraction`, {
      timeout: 120000,
    });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to load extraction.");
  }
}

export async function updateExtraction(
  documentId: string,
  fields: {
    documentType: string;
    provider?: string;
    policyNumber?: string;
    startDate?: string;
    expiryDate?: string;
    premium?: string;
    structuredFields?: Record<string, string>;
  },
): Promise<ExtractedFields> {
  try {
    const { data } = await apiClient.patch<ExtractedFields>(`/documents/${documentId}/extraction`, fields);
    return data;
  } catch (error) {
    throw apiError(error, "Unable to save extraction.");
  }
}

export async function decideDocumentPurpose(
  documentId: string,
  decision: "keep" | "discard",
): Promise<ExtractedFields> {
  try {
    const { data } = await apiClient.post<ExtractedFields>(`/documents/${documentId}/purpose`, { decision });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to save that choice.");
  }
}

export async function viewDocumentFile(id: string, fileName: string): Promise<void> {
  try {
    const response = await apiClient.get(`/documents/${id}/file`, {
      responseType: "blob",
      timeout: 120000,
    });
    const mime = String(response.headers["content-type"] || response.data?.type || "application/octet-stream").split(";")[0];
    const blob = new Blob([response.data], { type: mime });
    const url = window.URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    throw apiError(error, `Unable to open ${fileName}.`);
  }
}

export async function deleteDocument(id: string): Promise<void> {
  try {
    await apiClient.delete(`/documents/${id}`);
  } catch (error) {
    throw apiError(error, "Unable to delete document.");
  }
}
