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
  role?: "user" | "admin";
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

export type ExtractedFields = {
  documentType: string;
  provider: string;
  policyNumber: string;
  startDate: string;
  expiryDate: string;
  premium: string;
  previewTitle: string;
  previewLines: string[];
};
