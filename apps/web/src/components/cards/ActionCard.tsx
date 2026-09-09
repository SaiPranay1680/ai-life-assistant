import { Badge } from "@/components/ui/Badge";
import type { ActionItem, Priority } from "@/types";

const priorityTone: Record<Priority, "danger" | "warning" | "success"> = {
  high: "danger",
  medium: "warning",
  low: "success",
};

export function ActionRow({ action }: { action: ActionItem }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-slate-50 px-4 py-3">
      <div>
        <p className="font-medium text-slate-900">{action.title}</p>
        <p className="text-sm text-slate-500">{action.dueLabel}</p>
      </div>
      <Badge tone={priorityTone[action.priority]}>
        {action.priority.charAt(0).toUpperCase() + action.priority.slice(1)}
      </Badge>
    </div>
  );
}

export function ActionCard({
  action,
  reminder,
  onReminderChange,
  onCreate,
  onDismiss,
  busy,
}: {
  action: ActionItem;
  reminder: string;
  onReminderChange: (value: string) => void;
  onCreate: () => void;
  onDismiss: () => void;
  busy?: boolean;
}) {
  return (
    <div className="mx-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
      <span className="inline-flex rounded-full bg-orange-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-orange-700">
        Renew
      </span>
      <h2 className="mt-4 text-2xl font-semibold text-slate-900">{action.title}</h2>
      <p className="mt-2 text-slate-500">{action.reason}</p>
      <div className="mt-5 rounded-xl bg-blue-50 p-4">
        <p className="text-sm font-semibold text-blue-800">Why this was suggested</p>
        <p className="mt-1 text-sm text-blue-900">
          Source: car-insurance-policy.pdf • Expiry Date field • Page 1
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
      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-800"
        >
          Not needed
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCreate}
          className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300"
        >
          {busy ? "Saving…" : "Create reminder"}
        </button>
      </div>
    </div>
  );
}
