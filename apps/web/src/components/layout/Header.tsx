"use client";

import { Menu } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { ReactNode } from "react";

export function Header({
  title,
  subtitle,
  actions,
  onMenuClick,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  onMenuClick: () => void;
}) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <button
          type="button"
          className="mt-1 rounded-lg p-1 text-slate-700 lg:hidden"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <Menu className="h-6 w-6" />
        </button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 md:text-3xl">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-1 text-sm text-slate-500 md:text-base">{subtitle}</p>
          ) : null}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <Badge tone="success">Secure workspace</Badge>
        {actions}
      </div>
    </header>
  );
}
