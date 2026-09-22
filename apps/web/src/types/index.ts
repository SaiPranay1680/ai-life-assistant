export type Priority = "high" | "medium" | "low";

export type DocumentType =
  | "Bill"
  | "Insurance"
  | "Car Insurance"
  | "Health Insurance"
  | "Purchase"
  | "Warranty"
  | "Important document"
  | "Other";

export type DocumentStatus =
  | "Action created"
  | "Reminder set"
  | "Warranty active"
  | "No action"
  | "Processing"
  | "Needs review"
  | "Reviewed"
  | "Rejected"
  | "Decide";

export type User = {
  id: string;
  name: string;
  email: string;
  role?: "user" | "admin";
  emailVerified?: boolean;
};

export type AttentionCard = {
  id: string;
  title: string;
  badge: string;
  badgeTone: "danger" | "warning" | "success";
  headline: string;
  meta: string;
};

export type ActionType =
  | "PAY"
  | "RENEW"
  | "REGISTER"
  | "REVIEW"
  | "FOLLOW_UP"
  | "KEEP_FOR_RECORDS";

export type ActionStatus =
  | "suggested"
  | "confirmed"
  | "in_progress"
  | "completed"
  | "dismissed";

export type ActionItem = {
  id: string;
  title: string;
  dueLabel: string;
  dueDate: string;
  priority: Priority;
  reason: string;
  reminderDefault: string;
  status: ActionStatus;
  actionType?: ActionType | string;
  evidence?: string;
  confirmedBy?: string | null;
  confirmedAt?: string | null;
  completedAt?: string | null;
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

export type ExtractedFields = {
  documentType: string;
  provider: string;
  policyNumber: string;
  startDate: string;
  expiryDate: string;
  premium: string;
  previewTitle: string;
  previewLines: string[];
  processingStatus?: string;
  structuredExtraction?: StructuredExtraction | null;
  purposeStatus?: string;
  purposeReason?: string;
  purposeCategory?: string;
  folderCategory?: string;
  folderSubcategory?: string;
  fields?: ExtractedField[];
};
