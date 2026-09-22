export type Priority = "high" | "medium" | "low";

export type DocumentType =
  | "Bill"
  | "Insurance"
  | "Purchase"
  | "Warranty"
  | "Important document";

export type DocumentStatus =
  | "Action created"
  | "Reminder set"
  | "Warranty active"
  | "No action"
  | "Processing"
  | "Needs review"
  | "Reviewed";

export type User = {
  id: string;
  name: string;
  email: string;
};

export type AttentionCard = {
  id: string;
  title: string;
  badge: string;
  badgeTone: "danger" | "warning" | "success";
  headline: string;
  meta: string;
};

export type ActionItem = {
  id: string;
  title: string;
  dueLabel: string;
  dueDate: string;
  priority: Priority;
  reason: string;
  reminderDefault: string;
  status: "suggested" | "reminder_set" | "dismissed";
  actionType?: string;
  evidence?: string;
};

export type VaultDocument = {
  id: string;
  name: string;
  type: DocumentType;
  importantDate: string;
  status: DocumentStatus;
  category: string;
  subcategory: string;
};

export type TimelineEvent = {
  id: string;
  dateLabel: string;
  title: string;
};

export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  sources?: string[];
};

<<<<<<< Updated upstream
=======
export type ExtractedValue = {
  raw?: string | null;
  normalized?: string | null;
  confidence?: number | null;
  evidence?: Array<{ page_number: number; snippet: string }>;
};

export type StructuredExtraction = {
  document_type?: ExtractedValue | null;
  [key: string]: ExtractedValue | ExtractedValue[] | null | undefined;
};

export type ExtractedField = {
  name: string;
  value: string;
  evidence: string;
  page: number;
  confidence: number;
  label?: string;
};

>>>>>>> Stashed changes
export type ExtractedFields = {
  documentType: string;
  provider: string;
  policyNumber: string;
  startDate: string;
  expiryDate: string;
  premium: string;
  previewTitle: string;
  previewLines: string[];
<<<<<<< Updated upstream
=======
  processingStatus?: string;
  structuredExtraction?: StructuredExtraction | null;
  purposeStatus?: string;
  purposeReason?: string;
  purposeCategory?: string;
  folderCategory?: string;
  folderSubcategory?: string;
  fields?: ExtractedField[];
>>>>>>> Stashed changes
};
