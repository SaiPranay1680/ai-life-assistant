import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils";
import {
  formatDue,
  formatInr,
  type TimelineRow,
  type TimelineStatus,
} from "@/utils/timeline";
import {
  AlertTriangle,
  CalendarDays,
  Car,
  ChevronLeft,
  ChevronRight,
  Info,
  Receipt,
  Shield,
  Smartphone,
  Wifi,
  Zap,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";

const ICONS: Record<TimelineRow["icon"], LucideIcon> = {
  zap: Zap,
  phone: Smartphone,
  shield: Shield,
  wifi: Wifi,
  car: Car,
  calendar: CalendarDays,
  receipt: Receipt,
};

const ICON_TONE: Record<TimelineRow["icon"], string> = {
  zap: "bg-amber-100 text-amber-600",
  phone: "bg-sky-100 text-sky-600",
  shield: "bg-indigo-100 text-indigo-600",
  wifi: "bg-emerald-100 text-emerald-600",
  car: "bg-sky-100 text-sky-600",
  calendar: "bg-violet-100 text-violet-600",
  receipt: "bg-slate-100 text-slate-600",
};

function statusTone(status: TimelineStatus): "danger" | "warning" | "success" | "info" | "neutral" {
  if (status === "Overdue" || status === "Due soon") return "danger";
  if (status === "Paid") return "success";
  if (status === "Upcoming") return "info";
  return "neutral";
}

function RowIcon({ name }: { name: TimelineRow["icon"] }) {
  const Icon = ICONS[name];
  return (
    <span className={cn("inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", ICON_TONE[name])} aria-hidden="true">
      <Icon className="h-4 w-4" />
    </span>
  );
}

function MarkPaidButton({
  onClick,
  busy,
}: {
  onClick: () => void;
  busy?: boolean;
}) {
  return (
    <Button
      type="button"
      className="min-h-8 rounded-full px-3 py-1.5 text-xs"
      disabled={busy}
      onClick={onClick}
    >
      {busy ? "Saving…" : "Mark paid"}
    </Button>
  );
}

export function MonthSwitcher({
  label,
  onPrev,
  onNext,
}: {
  label: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white p-1 shadow-sm">
      <button
        type="button"
        aria-label="Previous month"
        onClick={onPrev}
        className="inline-flex h-9 w-9 items-center justify-center rounded-full text-slate-600 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <p className="min-w-[9.5rem] text-center text-sm font-semibold text-slate-900">{label}</p>
      <button
        type="button"
        aria-label="Next month"
        onClick={onNext}
        className="inline-flex h-9 w-9 items-center justify-center rounded-full text-slate-600 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ExpectedTotal({ amount, monthLabel }: { amount: number; monthLabel: string }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-sm">
      <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-600" aria-hidden="true">
        <Receipt className="h-5 w-5" />
      </span>
      <div>
        <p className="text-xs font-medium text-slate-500">Expected this month</p>
        <p className="text-xl font-semibold tracking-tight text-slate-900">{formatInr(amount)}</p>
        <p className="mt-1 max-w-xs text-xs leading-5 text-slate-400">
          Confirmed repeating bills and premiums due in {monthLabel}. Overdue from earlier months is listed separately.
        </p>
      </div>
    </div>
  );
}

export function OverdueSection({
  rows,
  busyId,
  onPaid,
}: {
  rows: TimelineRow[];
  busyId?: string | null;
  onPaid: (row: TimelineRow) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <section className="rounded-2xl border border-rose-100 bg-rose-50/80 p-4" aria-labelledby="overdue-heading">
      <div className="mb-3 flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 text-rose-500" aria-hidden="true" />
        <div>
          <h2 id="overdue-heading" className="text-sm font-semibold text-rose-800">
            Overdue
          </h2>
          <p className="text-xs text-rose-700">These were due in a previous month. Mark them paid once settled.</p>
        </div>
      </div>
      <ul className="space-y-2">
        {rows.map((row) => (
          <li
            key={row.id}
            className="flex flex-col gap-3 rounded-xl bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex min-w-0 items-center gap-3">
              <RowIcon name={row.icon} />
              <div className="min-w-0">
                <p className="truncate font-semibold text-slate-900">{row.title}</p>
                <p className="text-xs text-slate-500">
                  {row.cadence}
                  <span className="text-rose-600">
                    {" "}
                    · Overdue · was {row.due ? formatDue(row.due, row.dueLabel) : row.dueLabel}
                  </span>
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-end">
              <p className="text-sm font-semibold text-rose-600">{formatInr(row.amount)}</p>
              <MarkPaidButton busy={busyId === row.id} onClick={() => onPaid(row)} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TableShell({
  caption,
  columns,
  gridClass,
  children,
}: {
  caption: string;
  columns: string[];
  gridClass: string;
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden">
      <div role="table" aria-label={caption}>
        <div role="row" className={cn("hidden gap-3 border-b border-slate-100 px-3 py-2 text-xs text-slate-400 sm:grid", gridClass)}>
          {columns.map((column, index) => (
            <div key={column} role="columnheader" className={index === columns.length - 1 ? "text-right" : "min-w-0"}>
              {column}
            </div>
          ))}
        </div>
        <div role="rowgroup" className="divide-y divide-slate-100">
          {children}
        </div>
      </div>
    </div>
  );
}

export function MoneyOutSection({
  rows,
  monthLabel,
  busyId,
  onPaid,
}: {
  rows: TimelineRow[];
  monthLabel: string;
  busyId?: string | null;
  onPaid: (row: TimelineRow) => void;
}) {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm" aria-labelledby="money-heading">
      <div className="mb-4 flex items-start gap-2">
        <span className="mt-0.5 text-sky-600" aria-hidden="true">
          <Receipt className="h-4 w-4" />
        </span>
        <div>
          <h2 id="money-heading" className="text-sm font-semibold text-slate-900">
            This month — Money out
          </h2>
          <p className="text-xs text-slate-500">Bills and payments due in {monthLabel}.</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl bg-slate-50 px-4 py-6 text-sm text-slate-500">No bills or premiums due this month.</p>
      ) : (
        <TableShell
          caption={`Bills due in ${monthLabel}`}
          columns={["Item", "Cadence", "Amount", "Due date", "Status", "Action"]}
          gridClass="grid-cols-[minmax(0,1.6fr)_0.7fr_0.8fr_0.9fr_0.8fr_0.8fr]"
        >
          {rows.map((row) => (
            <div
              key={row.id}
              role="row"
              className="grid grid-cols-1 gap-2 px-3 py-3 sm:grid-cols-[minmax(0,1.6fr)_0.7fr_0.8fr_0.9fr_0.8fr_0.8fr] sm:items-center sm:gap-3"
            >
              <div role="cell" className="flex min-w-0 items-center gap-3">
                <RowIcon name={row.icon} />
                <span className="truncate text-sm font-semibold text-slate-900">{row.title}</span>
              </div>
              <div role="cell" className="text-sm text-slate-500">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Cadence</span>
                {row.cadence}
              </div>
              <div role="cell" className="text-sm font-medium text-slate-800">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Amount</span>
                {formatInr(row.amount)}
              </div>
              <div role="cell" className="text-sm text-slate-500">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Due date</span>
                {row.dueLabel}
              </div>
              <div role="cell">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Status</span>
                <Badge tone={statusTone(row.status)}>{row.status}</Badge>
              </div>
              <div role="cell" className="sm:text-right">
                {row.status === "Paid" ? (
                  <span className="text-sm text-slate-300">—</span>
                ) : (
                  <MarkPaidButton busy={busyId === row.id} onClick={() => onPaid(row)} />
                )}
              </div>
            </div>
          ))}
        </TableShell>
      )}
    </section>
  );
}

export function LifeSection({
  rows,
  onOpen,
}: {
  rows: TimelineRow[];
  onOpen: (row: TimelineRow) => void;
}) {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm" aria-labelledby="life-heading">
      <div className="mb-4 flex items-start gap-2">
        <span className="mt-0.5 text-violet-600" aria-hidden="true">
          <CalendarDays className="h-4 w-4" />
        </span>
        <div>
          <h2 id="life-heading" className="text-sm font-semibold text-slate-900">
            Renewals & appointments
          </h2>
          <p className="text-xs text-slate-500">Upcoming renewals and important appointments.</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl bg-slate-50 px-4 py-6 text-sm text-slate-500">No renewals or appointments this month.</p>
      ) : (
        <TableShell
          caption="Renewals and appointments"
          columns={["Item", "Type", "Date", "Status", "Action"]}
          gridClass="grid-cols-[minmax(0,1.8fr)_0.7fr_0.9fr_0.8fr_0.8fr]"
        >
          {rows.map((row) => (
            <div
              key={row.id}
              role="row"
              className="grid grid-cols-1 gap-2 px-3 py-3 sm:grid-cols-[minmax(0,1.8fr)_0.7fr_0.9fr_0.8fr_0.8fr] sm:items-center sm:gap-3"
            >
              <div role="cell" className="flex min-w-0 items-center gap-3">
                <RowIcon name={row.icon} />
                <span className="truncate text-sm font-semibold text-slate-900">{row.title}</span>
              </div>
              <div role="cell" className="text-sm text-slate-500">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Type</span>
                {row.cadence}
              </div>
              <div role="cell" className="text-sm text-slate-500">
                <span className="mr-2 text-xs text-slate-400 sm:hidden">Date</span>
                {row.dueLabel}
              </div>
              <div role="cell">
                <Badge tone={statusTone(row.status)}>{row.status}</Badge>
              </div>
              <div role="cell" className="sm:text-right">
                <button
                  type="button"
                  className="text-sm font-medium text-blue-600 hover:text-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  onClick={() => onOpen(row)}
                >
                  View details
                </button>
              </div>
            </div>
          ))}
        </TableShell>
      )}
    </section>
  );
}

export function TimelineNote() {
  return (
    <p className="flex items-start gap-2 text-xs leading-5 text-slate-500">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-500" aria-hidden="true" />
      Timeline does not auto-pay. You mark Paid. Next month a new occurrence appears for monthly items.
    </p>
  );
}

export function TimelineSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
      <div className="h-48 animate-pulse rounded-2xl bg-slate-100" />
      <div className="h-40 animate-pulse rounded-2xl bg-slate-100" />
    </div>
  );
}
