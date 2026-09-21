import { Badge } from "@/components/ui/Badge";
import type { ActionItem, ActionStatus, Priority } from "@/types";

const priorityTone: Record<Priority, "danger" | "warning" | "success"> = {
  high: "danger",
  medium: "warning",
  low: "success",
};

const typeLabel: Record<string, string> = {
  PAY: "Pay",
  RENEW: "Renew",
  REVIEW: "Review",
  REGISTER: "Register",
  FOLLOW_UP: "Follow up",
  KEEP_FOR_RECORDS: "Keep",
};

const statusLabel: Record<ActionStatus, string> = {
  suggested: "Suggested",
  confirmed: "Confirmed",
  in_progress: "In progress",
  completed: "Completed",
  dismissed: "Dismissed",
};

const statusTone: Record<ActionStatus, "warning" | "success" | "danger" | "neutral"> = {
  suggested: "warning",
  confirmed: "success",
  in_progress: "warning",
  completed: "success",
  dismissed: "neutral",
};

export function ActionRow({
  action,
  onStart,
  onComplete,
  onDismiss,
  busy,
}: {
  action: ActionItem;
  onStart?: () => void;
  onComplete?: () => void;
  onDismiss?: () => void;
  busy?: boolean;
}) {
  const showStart = action.status === "confirmed" && onStart;
  const showComplete =
    (action.status === "confirmed" || action.status === "in_progress") && onComplete;
  const showDismiss =
    (action.status === "confirmed" || action.status === "in_progress") && onDismiss;

  return (
    <div className="flex flex-col gap-3 rounded-xl bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-slate-900">{action.title}</p>
          <Badge tone={statusTone[action.status]}>{statusLabel[action.status]}</Badge>
        </div>
        <p className="text-sm text-slate-500">{action.dueLabel}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={priorityTone[action.priority]}>
          {action.priority.charAt(0).toUpperCase() + action.priority.slice(1)}
        </Badge>
        {showStart ? (
          <button
            type="button"
            disabled={busy}
            onClick={onStart}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 disabled:opacity-50"
          >
            Start
          </button>
        ) : null}
        {showComplete ? (
          <button
            type="button"
            disabled={busy}
            onClick={onComplete}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300"
          >
            Complete
          </button>
        ) : null}
        {showDismiss ? (
          <button
            type="button"
            disabled={busy}
            onClick={onDismiss}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 disabled:opacity-50"
          >
            Dismiss
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function ActionCard({
  action,
  reminder,
  onReminderChange,
  onConfirm,
  onRemind,
  onDismiss,
  busy,
}: {
  action: ActionItem;
  reminder: string;
  onReminderChange: (value: string) => void;
  onConfirm: () => void;
  onRemind: () => void;
  onDismiss: () => void;
  busy?: boolean;
}) {
  return (
    <div className="mx-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex rounded-full bg-orange-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-orange-700">
          {typeLabel[action.actionType ?? ""] || "Action"}
        </span>
        <Badge tone={statusTone[action.status]}>{statusLabel[action.status]}</Badge>
      </div>
      <h2 className="mt-4 text-2xl font-semibold text-slate-900">{action.title}</h2>
      <p className="mt-2 text-slate-500">{action.reason}</p>
      <div className="mt-5 rounded-xl bg-blue-50 p-4">
        <p className="text-sm font-semibold text-blue-800">Why this was suggested</p>
        <p className="mt-1 text-sm text-blue-900">
          {action.evidence || "Suggested from the details you confirmed."}
        </p>
        <p className="mt-2 text-xs text-slate-500">AI confidence: High</p>
      </div>
      <label className="mt-6 block text-sm font-medium text-slate-600">
        Reminder
        <select
          value={reminder}
          onChange={(event) => onReminderChange(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-900"
        >
          <option>Remind me 30 days before</option>
          <option>Remind me 14 days before</option>
          <option>Remind me 7 days before</option>
          <option>Remind me 3 days before</option>
        </select>
      </label>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-between">
        <button
          type="button"
          disabled={busy}
          onClick={onDismiss}
          className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-800 disabled:opacity-50"
        >
          Not needed
        </button>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-2.5 text-sm font-semibold text-blue-800 hover:bg-blue-100 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Confirm"}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onRemind}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300"
          >
            {busy ? "Saving…" : "Confirm & remind"}
          </button>
        </div>
      </div>
    </div>
  );
}
