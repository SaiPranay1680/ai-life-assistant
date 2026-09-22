import { cn } from "@/utils";
import {
  CalendarDays,
  Car,
  ChevronRight,
  CreditCard,
  FileText,
  Fingerprint,
  FolderOpen,
  Heart,
  Home,
  IdCard,
  Pill,
  Receipt,
  Shield,
  ShoppingCart,
  type LucideIcon,
} from "lucide-react";

const FOLDER_STYLE: Record<string, { icon: LucideIcon; tone: string; filled?: boolean }> = {
  Health: { icon: Heart, tone: "bg-rose-100 text-rose-600", filled: true },
  Vehicle: { icon: Car, tone: "bg-sky-100 text-sky-600", filled: true },
  Home: { icon: Home, tone: "bg-amber-100 text-amber-600", filled: true },
  Identity: { icon: IdCard, tone: "bg-violet-100 text-violet-600" },
  Purchases: { icon: ShoppingCart, tone: "bg-teal-100 text-teal-600", filled: true },
  Insurance: { icon: Shield, tone: "bg-indigo-100 text-indigo-600", filled: true },
  Records: { icon: FolderOpen, tone: "bg-slate-200 text-slate-700" },
  Appointment: { icon: CalendarDays, tone: "bg-sky-100 text-sky-600" },
  Prescription: { icon: Pill, tone: "bg-fuchsia-100 text-fuchsia-600", filled: true },
  "Driving licence": { icon: IdCard, tone: "bg-sky-100 text-sky-600" },
  Registration: { icon: FileText, tone: "bg-sky-100 text-sky-600" },
  Bills: { icon: Receipt, tone: "bg-amber-100 text-amber-600" },
  Warranty: { icon: Shield, tone: "bg-emerald-100 text-emerald-600", filled: true },
  Passport: { icon: Fingerprint, tone: "bg-violet-100 text-violet-600" },
  PAN: { icon: CreditCard, tone: "bg-violet-100 text-violet-600" },
  Aadhaar: { icon: Fingerprint, tone: "bg-violet-100 text-violet-600" },
  Receipts: { icon: Receipt, tone: "bg-teal-100 text-teal-600" },
  Invoice: { icon: FileText, tone: "bg-teal-100 text-teal-600" },
  Policies: { icon: Shield, tone: "bg-indigo-100 text-indigo-600", filled: true },
  Other: { icon: FolderOpen, tone: "bg-slate-200 text-slate-700" },
};

export function FolderCard({
  title,
  count,
  onOpen,
}: {
  title: string;
  count: number;
  onOpen: () => void;
}) {
  const style = FOLDER_STYLE[title] ?? FOLDER_STYLE.Records;
  const Icon = style.icon;
  const countLabel = `${count} ${count === 1 ? "file" : "files"}`;

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Open ${title} folder, ${countLabel}`}
      className="rounded-2xl border border-slate-100 bg-white p-5 text-left shadow-sm transition hover:border-blue-200 hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <span
        className={cn("inline-flex h-12 w-12 items-center justify-center rounded-2xl", style.tone)}
        aria-hidden="true"
      >
        <Icon className={cn("h-6 w-6", style.filled && "fill-current")} strokeWidth={2.25} />
      </span>
      <span className="mt-4 block">
        <span className="flex items-center justify-between gap-3">
          <span className="truncate text-base font-semibold text-slate-900">{title}</span>
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
        </span>
        <span className="mt-1 block text-sm text-slate-400">{countLabel}</span>
      </span>
    </button>
  );
}
