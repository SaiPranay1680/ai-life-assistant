import { cn } from "@/utils";
import type { HTMLAttributes, ReactNode } from "react";

export function Card({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200/80 bg-white shadow-sm",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
