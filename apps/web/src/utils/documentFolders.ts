import type { DocumentStatus } from "@/types";

export type DocumentFolder = {
  category: string;
  subcategory: string;
};

export const FOLDER_TAXONOMY: Record<string, string[]> = {
  Health: ["Insurance", "Appointment", "Prescription", "Records"],
  Vehicle: ["Insurance", "Driving licence", "Registration", "Records"],
  Home: ["Bills", "Warranty", "Records"],
  Identity: ["Passport", "PAN", "Aadhaar", "Records"],
  Purchases: ["Receipts", "Invoice", "Warranty"],
  Insurance: ["Policies", "Health", "Vehicle"],
  Records: ["Other"],
};

export const FOLDER_CATEGORIES = Object.keys(FOLDER_TAXONOMY);

const INBOX_STATUSES: DocumentStatus[] = ["Needs review", "Decide"];

export function isInboxDocument(status: DocumentStatus): boolean {
  return INBOX_STATUSES.includes(status);
}

export function isLibraryDocument(status: DocumentStatus): boolean {
  return !isInboxDocument(status) && status !== "Processing";
}

export function normalizeFolder(category: string, subcategory: string): DocumentFolder {
  const cat = FOLDER_TAXONOMY[category] ? category : folderFor({ name: category, type: subcategory }).category;
  const options = FOLDER_TAXONOMY[cat] ?? FOLDER_TAXONOMY.Records;
  const sub = options.includes(subcategory)
    ? subcategory
    : options.find((item) => item.toLowerCase() === subcategory.toLowerCase()) ?? options[0];
  return { category: cat, subcategory: sub };
}

export function folderFor(input: {
  name: string;
  type: string;
  purposeCategory?: string | null;
  purposeSubtype?: string | null;
  folderCategory?: string | null;
  folderSubcategory?: string | null;
}): DocumentFolder {
  if (input.folderCategory?.trim()) {
    return normalizeFolder(input.folderCategory, input.folderSubcategory ?? "");
  }
  const hay = [input.name, input.type, input.purposeCategory, input.purposeSubtype]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (/\bpassport\b/.test(hay)) return { category: "Identity", subcategory: "Passport" };
  if (/\bpan\b/.test(hay) || /\bpermanent account\b/.test(hay)) {
    return { category: "Identity", subcategory: "PAN" };
  }
  if (/\baadhaar|\baadhar\b/.test(hay)) return { category: "Identity", subcategory: "Aadhaar" };
  if (/\blicen[cs]e|\bdriving\b/.test(hay)) {
    return { category: "Vehicle", subcategory: "Driving licence" };
  }
  if (/\bhealth|medical|hospital|star health|appointment|clinic\b/.test(hay)) {
    if (/appoint/.test(hay)) return { category: "Health", subcategory: "Appointment" };
    if (/prescription|\brx\b/.test(hay)) return { category: "Health", subcategory: "Prescription" };
    return { category: "Health", subcategory: /insur|policy/.test(hay) ? "Insurance" : "Records" };
  }
  if (/\bcar\b|\bmotor\b|\bvehicle\b|\bauto\b/.test(hay)) {
    if (/regist|\brc\b/.test(hay)) return { category: "Vehicle", subcategory: "Registration" };
    return { category: "Vehicle", subcategory: /insur|policy/.test(hay) ? "Insurance" : "Records" };
  }
  if (/\bwarrant/.test(hay)) return { category: "Purchases", subcategory: "Warranty" };
  if (/\binvoice|receipt|purchase/.test(hay)) {
    return { category: "Purchases", subcategory: /invoice/.test(hay) ? "Invoice" : "Receipts" };
  }
  if (/\belectric|bescom|utility|water bill|gas bill|broadband|mobile bill|\bbill\b/.test(hay)) {
    return { category: "Home", subcategory: "Bills" };
  }
  if (/\binsur|policy/.test(hay)) return { category: "Insurance", subcategory: "Policies" };
  return { category: "Records", subcategory: "Other" };
}
