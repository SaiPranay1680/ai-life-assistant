"use client";

import {
  CalendarClock,
  FolderOpen,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  MessageSquare,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/utils";
import { useAuth } from "@/hooks/useAuth";

const baseItems = [
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
  const items = user?.role === "admin"
    ? [{ href: "/admin", label: "Admin Dashboard", icon: ShieldCheck }, ...baseItems]
    : baseItems;

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
          "fixed inset-y-0 left-0 z-40 flex h-dvh w-64 shrink-0 flex-col bg-[#0b1b33] text-white transition-transform lg:static lg:h-full lg:translate-x-0",
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
        <nav className="mt-8 min-h-0 flex-1 space-y-1 overflow-y-auto px-3">
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
        <div className="mt-auto shrink-0 border-t border-white/10 px-6 py-5">
          <p className="text-sm font-medium">{user?.name ?? "Guest"}</p>
          <p className="truncate text-xs text-slate-400">{user?.email}</p>
          {user ? (
            <button
              type="button"
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-red-500/40 bg-red-600/15 px-3 py-2.5 text-sm font-semibold text-red-100 shadow-lg shadow-red-950/20 transition-all duration-200 hover:bg-red-600/25 hover:text-white hover:shadow-red-900/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              onClick={() => {
                logout();
                onClose();
                router.replace("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );
}
