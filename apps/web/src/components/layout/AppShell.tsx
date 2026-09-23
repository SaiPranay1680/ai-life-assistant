"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { useAuth } from "@/hooks/useAuth";
import { usePathname, useRouter } from "next/navigation";
import { firstName, greetingForNow } from "@/utils";
import { useEffect, useState, type ReactNode } from "react";

const titles: Record<string, { title: string; subtitle?: string }> = {
  "/dashboard": {
    title: "Good morning, Anita",
    subtitle: "Here's what needs your attention today.",
  },
  "/admin": {
    title: "Admin Dashboard",
    subtitle: "System-wide overview, users, and database activity.",
  },
  "/documents/upload": {
    title: "Smart Inbox",
    subtitle:
      "Upload a document, then review only what still needs your attention.",
  },
  "/documents/processing": {
    title: "Understanding your document",
  },
  "/documents/review": {
    title: "Review details",
    subtitle: "Confirm the category and extracted information to continue.",
  },
  "/documents": {
    title: "Documents",
    subtitle: "Browse files by category. Open a file to view it in a new tab.",
  },
  "/actions": {
    title: "Actions",
    subtitle: "Confirm, track, and complete suggested work",
  },
  "/assistant": {
    title: "AI Assistant",
    subtitle: "Ask questions using your own documents and actions.",
  },
  "/timeline": {
    title: "Timeline",
    subtitle: "This month's bills, renewals, and appointments. Mark paid when you settle them.",
  },
  "/settings": {
    title: "Settings",
    subtitle: "Profile, privacy and notifications.",
  },
};

function metaFor(pathname: string) {
  if (titles[pathname]) return titles[pathname];
  const match = Object.keys(titles).find((key) => pathname.startsWith(key));
  return match ? titles[match] : { title: "LIFE AI" };
}

export function AppShell({
  children,
  actions,
}: {
  children: ReactNode;
  actions?: ReactNode;
}) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const meta = metaFor(pathname);

  useEffect(() => {
    if (ready && !user) {
      router.replace("/login");
    }
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading workspace…
      </div>
    );
  }

  const displayName = user.name?.trim() ? firstName(user.name.trim()) : "there";
  const title =
    pathname === "/dashboard"
      ? `${greetingForNow()}, ${displayName}`
      : pathname === "/admin"
        ? "Admin Dashboard"
        : meta.title;

  return (
    <div className="flex h-dvh overflow-hidden bg-[#f4f7fb]">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="shrink-0 px-4 py-6 md:px-8">
          <Header
            title={title}
            subtitle={meta.subtitle}
            actions={actions}
            onMenuClick={() => setOpen(true)}
          />
        </div>
        <main className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 md:px-8">{children}</main>
      </div>
    </div>
  );
}
