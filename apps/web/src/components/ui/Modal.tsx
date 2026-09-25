"use client";

import { Button } from "@/components/ui/Button";
import type { ReactNode } from "react";

export function Modal({
  open,
  title,
  children,
  onClose,
  showClose = true,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  showClose?: boolean;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <div className="mt-3 text-sm text-slate-600">{children}</div>
        {showClose ? (
          <div className="mt-5 flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
