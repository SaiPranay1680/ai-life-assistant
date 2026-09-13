"use client";

import {
  CalendarClock,
  FolderOpen,
  Inbox,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  Settings,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/utils";
import { useAuth } from "@/hooks/useAuth";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents/upload", label: "Smart Inbox", icon: Inbox },
  { href: "/actions", label: "Actions", icon: ListChecks },
  { href: "/documents", label: "Documents", icon: FolderOpen },
  { href: "/assistant", label: "AI Assistant", icon: MessageSquare },
  { href: "/timeline", label: "Timeline", icon: CalendarClock },
  { href: "/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  if (href === "/documents") {
    return pathname === "/documents";
  }
  if (href === "/documents/upload") {
    return pathname.startsWith("/documents/upload") ||
      pathname.startsWith("/documents/processing") ||
      pathname.startsWith("/documents/review");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={onClose}
        />
      ) : null}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#0b1b33] text-white transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-start justify-between px-6 pt-7">
          <div>
            <p className="text-xl font-bold tracking-wide">LIFE AI</p>
            <p className="mt-1 text-xs text-slate-400">
              Personal Action Intelligence
            </p>
          </div>
          <button type="button" className="lg:hidden" onClick={onClose}>
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="mt-8 flex-1 space-y-1 px-3">
          {items.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                  active
                    ? "bg-[#1d4ed8]/80 text-white"
                    : "text-slate-300 hover:bg-white/10 hover:text-white",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 px-6 py-5">
          <p className="text-sm font-medium">{user?.name ?? "Guest"}</p>
          <p className="truncate text-xs text-slate-400">{user?.email}</p>
          {user ? (
            <button
              type="button"
              className="mt-3 text-xs text-slate-400 hover:text-white hover:underline"
              onClick={() => {
                logout();
                onClose();
                router.replace("/login");
              }}
            >
              Sign out
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );
}
