import actions from "@/data/actions.json";
import dashboard from "@/data/dashboard.json";
import timeline from "@/data/timeline.json";
import type { ActionItem, AttentionCard, TimelineEvent } from "@/types";
import { wait } from "@/utils";

export async function getActions(): Promise<ActionItem[]> {
  await wait(250);
  return actions as ActionItem[];
}

export async function getAttentionCards(): Promise<AttentionCard[]> {
  await wait(200);
  return dashboard.attention as AttentionCard[];
}

export async function getTimeline(): Promise<TimelineEvent[]> {
  await wait(200);
  return timeline as TimelineEvent[];
}

export async function createReminder(actionId: string, reminder: string) {
  await wait(400);
  return { actionId, reminder, status: "reminder_set" as const };
}
