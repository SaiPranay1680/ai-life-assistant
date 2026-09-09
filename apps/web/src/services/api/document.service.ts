import documents from "@/data/documents.json";
import extraction from "@/data/extraction.json";
import type { ExtractedFields, VaultDocument } from "@/types";
import { wait } from "@/utils";

export async function getDocuments(): Promise<VaultDocument[]> {
  await wait(250);
  return documents as VaultDocument[];
}

export async function uploadDocument(file: File): Promise<{ fileName: string }> {
  await wait(400);
  const allowed = ["application/pdf", "image/jpeg", "image/png", "image/jpg"];
  if (!allowed.includes(file.type) && !/\.(pdf|jpe?g|png)$/i.test(file.name)) {
    throw new Error("Only PDF, JPG or PNG files are allowed.");
  }
  if (file.size > 20 * 1024 * 1024) {
    throw new Error("File must be 20 MB or smaller.");
  }
  return { fileName: file.name };
}

export async function getExtraction(): Promise<ExtractedFields> {
  await wait(200);
  return extraction as ExtractedFields;
}
