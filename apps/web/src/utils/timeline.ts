import type { ActionItem, ActionType } from "@/types";

export type Cadence = "Monthly" | "Quarterly" | "Yearly" | "One-off";
export type TimelineStatus = "Overdue" | "Due soon" | "Upcoming" | "Paid";
export type TimelineKind = "money" | "life";

export type TimelineRow = {
  id: string;
  title: string;
  cadence: Cadence;
  amount: number | null;
  due: Date | null;
  dueLabel: string;
  status: TimelineStatus;
  kind: TimelineKind;
  icon: "zap" | "phone" | "shield" | "wifi" | "car" | "calendar" | "receipt";
  action: ActionItem;
};

function parseDue(action: ActionItem): Date | null {
  const iso = (action.dueDate || "").trim();
  if (iso && iso !== "—") {
    const date = new Date(`${iso.slice(0, 10)}T00:00:00`);
    if (!Number.isNaN(date.getTime())) return date;
  }
  const label = action.dueLabel || "";
  const numeric = label.match(/^(\d{1,2})[\/\- ](\d{1,2})[\/\- ](\d{4})/);
  if (numeric) {
    const date = new Date(Number(numeric[3]), Number(numeric[2]) - 1, Number(numeric[1]));
    if (!Number.isNaN(date.getTime())) return date;
  }
  const months = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec";
  const named = label.match(new RegExp(`(\\d{1,2})\\s+(${months})[a-z]*\\.?\\s+(\\d{4})`, "i"));
  if (named) {
    const month = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].indexOf(
      named[2].slice(0, 3).toLowerCase(),
    );
    const date = new Date(Number(named[3]), month, Number(named[1]));
    if (!Number.isNaN(date.getTime())) return date;
  }
  return null;
}

export function parseAmount(reason: string): number | null {
  const match =
    reason.match(/(?:₹|inr|rs\.?)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)/i) ||
    reason.match(/(?:amount|premium)\s+(?:₹|inr|rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)/i);
  if (!match) return null;
  const value = Number(match[1].replace(/,/g, ""));
  return Number.isFinite(value) ? value : null;
}

export function formatInr(amount: number | null): string {
  if (amount == null || Number.isNaN(amount)) return "—";
  const fraction = amount % 1 === 0 ? 0 : 2;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: fraction,
    minimumFractionDigits: fraction,
  }).format(amount);
}

export function formatDue(date: Date | null, fallback: string): string {
  if (!date) return fallback && fallback !== "—" ? fallback : "—";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

function cadenceFor(action: ActionItem, hay: string): Cadence {
  if (/\bquarter/i.test(hay)) return "Quarterly";
  if (/\bmonth|postpaid|electric|broadband|utility|mobile bill/i.test(hay) || action.actionType === "PAY") {
    return "Monthly";
  }
  if (/\byear|insur|policy|renew/i.test(hay) || action.actionType === "RENEW") return "Yearly";
  return "One-off";
}

function iconFor(hay: string): TimelineRow["icon"] {
  if (/electric|bescom|power/i.test(hay)) return "zap";
  if (/mobile|postpaid|phone/i.test(hay)) return "phone";
  if (/broadband|wifi|internet|fibre|fiber/i.test(hay)) return "wifi";
  if (/car|motor|vehicle/i.test(hay)) return "car";
  if (/appoint|clinic|hospital|doctor/i.test(hay)) return "calendar";
  if (/insur|health|policy|star/i.test(hay)) return "shield";
  return "receipt";
}

export function displayItemName(title: string): string {
  let name = title
    .replace(/^(pay|renew|review|register|follow up on|keep)\s+/i, "")
    .replace(/\s+on file$/i, "")
    .replace(/\s+warranty$/i, " warranty")
    .replace(/\s+purchase$/i, "")
    .trim();
  if (!name) return title;
  if (name === name.toUpperCase()) {
    name = name
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase())
      .replace(/\s+Bill$/i, "")
      .trim();
  }
  return name || title;
}

function statusFor(action: ActionItem, due: Date | null, today: Date): TimelineStatus {
  if (action.status === "completed") return "Paid";
  if (!due) return "Upcoming";
  const startToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (due < startToday) return "Overdue";
  const soon = new Date(startToday);
  soon.setDate(soon.getDate() + 7);
  if (due <= soon) return "Due soon";
  return "Upcoming";
}

function kindFor(type: ActionType | string | undefined, hay: string, amount: number | null): TimelineKind {
  if (type === "PAY") return "money";
  if (type === "RENEW" && amount != null) return "money";
  if (/appoint|clinic/i.test(hay)) return "life";
  if (type === "RENEW" || type === "REVIEW" || type === "FOLLOW_UP" || type === "REGISTER") return "life";
  return "life";
}

export function toTimelineRow(action: ActionItem, today = new Date()): TimelineRow | null {
  if (action.status === "dismissed") return null;
  if (action.actionType === "KEEP_FOR_RECORDS") return null;
  const due = parseDue(action);
  if (!due && action.status !== "completed") return null;
  const hay = `${action.title} ${action.reason} ${action.actionType ?? ""}`;
  const amount = parseAmount(action.reason);
  return {
    id: action.id,
    title: displayItemName(action.title),
    cadence: cadenceFor(action, hay),
    amount,
    due,
    dueLabel: formatDue(due, action.dueLabel),
    status: statusFor(action, due, today),
    kind: kindFor(action.actionType, hay, amount),
    icon: iconFor(hay),
    action,
  };
}

export function inMonth(row: TimelineRow, year: number, month: number): boolean {
  if (!row.due) return false;
  if (row.cadence === "Yearly") return row.due.getMonth() === month;
  return row.due.getFullYear() === year && row.due.getMonth() === month;
}

export function buildTimeline(actions: ActionItem[], year: number, month: number, today = new Date()) {
  const rows = actions.map((action) => toTimelineRow(action, today)).filter((row): row is TimelineRow => Boolean(row));
  const monthStart = new Date(year, month, 1);
  const overdue = rows
    .filter((row) => row.status !== "Paid" && row.due && row.due < monthStart)
    .sort((a, b) => (a.due && b.due ? a.due.getTime() - b.due.getTime() : 0));
  const monthRows = rows.filter((row) => inMonth(row, year, month) && !(row.due && row.due < monthStart && row.status !== "Paid"));
  const money = monthRows
    .filter((row) => row.kind === "money")
    .sort((a, b) => (a.due && b.due ? a.due.getTime() - b.due.getTime() : 0));
  const life = monthRows
    .filter((row) => row.kind === "life")
    .sort((a, b) => (a.due && b.due ? a.due.getTime() - b.due.getTime() : 0));
  const expected = money.filter((row) => row.status !== "Paid").reduce((sum, row) => sum + (row.amount ?? 0), 0);
  return { overdue, money, life, expected };
}

export function monthLabel(year: number, month: number): string {
  return new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" }).format(new Date(year, month, 1));
}
