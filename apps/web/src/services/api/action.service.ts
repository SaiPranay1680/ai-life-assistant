import axios from "axios";
import type { ActionItem, AttentionCard, TimelineEvent } from "@/types";
import { apiClient } from "./client";

type ApiAction = {
  id: string;
  title: string;
  action_type: string;
  due_label: string;
  due_date: string;
  priority: ActionItem["priority"];
  reason: string;
  evidence: string;
  reminder_default: string;
  status: ActionItem["status"];
};

function apiError(error: unknown, fallback: string): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
  }
  return error instanceof Error ? error : new Error(fallback);
}

function toAction(row: ApiAction): ActionItem {
  return {
    id: row.id,
    title: row.title,
    dueLabel: row.due_label,
    dueDate: row.due_date,
    priority: row.priority,
    reason: row.reason,
    reminderDefault: row.reminder_default,
    status: row.status,
    actionType: row.action_type,
    evidence: row.evidence,
  };
}

export async function getActions(): Promise<ActionItem[]> {
  try {
    const { data } = await apiClient.get<ApiAction[]>("/actions");
    return data.map(toAction);
  } catch (error) {
    throw apiError(error, "Unable to load actions.");
  }
}

export function toAttentionCard(action: ActionItem): AttentionCard {
  const badges: Record<string, string> = {
    PAY: "Due soon",
    RENEW: "Renew",
    REVIEW: "Review",
    REGISTER: "Register",
    FOLLOW_UP: "Follow up",
    KEEP_FOR_RECORDS: "Keep",
  };
  return {
    id: action.id,
    title: action.title,
    badge: badges[action.actionType ?? ""] || "Action",
    badgeTone: action.priority === "high" ? "danger" : action.priority === "low" ? "success" : "warning",
    headline: action.reason,
    meta: action.dueLabel && action.dueLabel !== "—" ? action.dueLabel : action.evidence || "From a confirmed document",
  };
}

export async function getTimeline(): Promise<TimelineEvent[]> {
  const actions = await getActions();
  return actions
    .filter((action) => action.dueLabel && action.dueLabel !== "—")
    .map((action) => ({
      id: action.id,
      dateLabel: action.dueLabel,
      title: action.title,
    }));
}

export async function createReminder(actionId: string, reminder: string) {
  try {
    const { data } = await apiClient.post<ApiAction>(`/actions/${actionId}/reminders`, { reminder });
    return toAction(data);
  } catch (error) {
    throw apiError(error, "Unable to create reminder.");
  }
}

export async function dismissAction(actionId: string) {
  try {
    const { data } = await apiClient.post<ApiAction>(`/actions/${actionId}/dismiss`);
    return toAction(data);
  } catch (error) {
    throw apiError(error, "Unable to dismiss action.");
  }
}
