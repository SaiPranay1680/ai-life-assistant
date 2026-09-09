import { cn } from "@/utils";
import type { AttentionCard as AttentionCardType } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const toneMap = {
  danger: "danger",
  warning: "warning",
  success: "success",
} as const;

export function AttentionCard({ card }: { card: AttentionCardType }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-900">{card.title}</h3>
        <Badge tone={toneMap[card.badgeTone]}>{card.badge}</Badge>
      </div>
      <p className="mt-3 text-sm font-medium text-slate-800">{card.headline}</p>
      <p className="mt-2 text-sm text-slate-500">{card.meta}</p>
    </Card>
  );
}

export function NotificationCard({
  title,
  body,
  className,
}: {
  title: string;
  body: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl bg-emerald-50 p-4", className)}>
      <p className="font-semibold text-emerald-800">{title}</p>
      <p className="mt-1 text-sm text-emerald-700">{body}</p>
    </div>
  );
}
