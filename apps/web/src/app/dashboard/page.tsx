"use client";

import { AppShell } from "@/components/layout/AppShell";
import { AttentionCard } from "@/components/cards/AttentionCard";
import { ActionRow } from "@/components/cards/ActionCard";
import { Button } from "@/components/ui/Button";
import { getActions, toAttentionCard } from "@/services/api/action.service";
import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const actionsQuery = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
  });
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: refreshUser,
  });

  useEffect(() => {
    void meQuery.refetch();
    // Load verification status from the API once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const verified = Boolean(meQuery.data?.emailVerified ?? user?.emailVerified);
  const actions = (actionsQuery.data ?? []).filter(
    (item) => item.status === "suggested" || item.status === "confirmed" || item.status === "in_progress",
  );
  const cards = actions.slice(0, 3).map(toAttentionCard);

  return (
    <AppShell
      actions={
        <Button onClick={() => router.push("/documents/upload")}>
          <Plus className="h-4 w-4" />
          Upload document
        </Button>
      }
    >
      {actionsQuery.isLoading ? (
        <p className="text-sm text-slate-500">Loading dashboard…</p>
      ) : null}
      {actionsQuery.isError ? (
        <p className="text-sm text-rose-600">
          {actionsQuery.error instanceof Error ? actionsQuery.error.message : "Could not load actions."}
        </p>
      ) : null}
      <section
        className={`mb-6 rounded-2xl border p-4 ${
          verified ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
        }`}
      >
        {verified ? (
          <p className="text-sm font-semibold text-emerald-800">Account Verified</p>
        ) : (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-amber-900">Account Not Verified</p>
              <p className="text-sm text-amber-800">Verify your email to keep your account secure.</p>
            </div>
            <Button type="button" onClick={() => router.push("/verify-account")}>
              Verify Account
            </Button>
          </div>
        )}
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <AttentionCard key={card.id} card={card} />
        ))}
      </section>
      {!actionsQuery.isLoading && !actionsQuery.isError && cards.length === 0 ? (
        <p className="text-sm text-slate-500">
          Nothing needs attention yet. Upload a document, confirm the details, then suggested actions appear here.
        </p>
      ) : null}
      <section className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-2">
          <h2 className="text-lg font-semibold text-slate-900">Upcoming actions</h2>
          <div className="mt-4 space-y-3">
            {actions.length === 0 ? (
              <p className="text-sm text-slate-500">No upcoming actions.</p>
            ) : (
              actions.map((action) => <ActionRow key={action.id} action={action} />)
            )}
          </div>
        </div>
        <div className="rounded-2xl bg-[#0b1b33] p-5 text-white">
          <h2 className="text-lg font-semibold">Ask your Life Assistant</h2>
          <ul className="mt-4 space-y-3 text-sm text-slate-200">
            <li>“What needs my attention this month?”</li>
            <li>“Which policy expires next?”</li>
            <li>“Show my upcoming bills.”</li>
          </ul>
          <Link
            href="/assistant"
            className="mt-6 inline-flex rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Open AI Assistant
          </Link>
        </div>
      </section>
    </AppShell>
  );
}
