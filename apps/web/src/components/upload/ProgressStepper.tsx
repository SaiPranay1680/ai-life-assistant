import { cn } from "@/utils";

export type ProcessStep = {
  title: string;
  status: "complete" | "in_progress" | "waiting";
};

const statusLabel = {
  complete: "Complete",
  in_progress: "In progress",
  waiting: "Waiting",
};

export function ProgressStepper({ steps }: { steps: ProcessStep[] }) {
  return (
    <ol className="space-y-4">
      {steps.map((step, index) => (
        <li key={step.title} className="flex items-start gap-3">
          <span
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
              step.status === "complete" && "bg-emerald-100 text-emerald-700",
              step.status === "in_progress" && "bg-blue-100 text-blue-700",
              step.status === "waiting" && "bg-slate-100 text-slate-500",
            )}
          >
            {index + 1}
          </span>
          <div className="pt-0.5">
            <p className="font-medium text-slate-900">{step.title}</p>
            <p
              className={cn(
                "text-sm",
                step.status === "complete" && "text-emerald-600",
                step.status === "in_progress" && "text-blue-600",
                step.status === "waiting" && "text-slate-400",
              )}
            >
              {statusLabel[step.status]}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
