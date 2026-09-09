"use client";

import { AppShell } from "@/components/layout/AppShell";
import { AttentionCard } from "@/components/cards/AttentionCard";
import { ActionRow } from "@/components/cards/ActionCard";
import { Button } from "@/components/ui/Button";
import { getActions, getAttentionCards } from "@/services/api/action.service";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const router = useRouter();
  const attentionQuery = useQuery({
    queryKey: ["attention"],
    queryFn: getAttentionCards,
  });
  const actionsQuery = useQuery({
    queryKey: ["actions"],
    queryFn: getActions,
  });

  return (
    <AppShell
      actions={
        <Button onClick={() => router.push("/documents/upload")}>
          <Plus className="h-4 w-4" />
          Upload document
        </Button>
      }
    >
      {attentionQuery.isLoading || actionsQuery.isLoading ? (
        <p className="text-sm text-slate-500">Loading dashboard…</p>
      ) : null}
      {attentionQuery.isError ? (
        <p className="text-sm text-rose-600">Could not load attention cards.</p>
      ) : null}
      <section className="grid gap-4 md:grid-cols-3">
        {(attentionQuery.data ?? []).map((card) => (
          <AttentionCard key={card.id} card={card} />
        ))}
      </section>
      <section className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-2">
          <h2 className="text-lg font-semibold text-slate-900">Upcoming actions</h2>
          <div className="mt-4 space-y-3">
            {(actionsQuery.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-500">No upcoming actions.</p>
            ) : (
              (actionsQuery.data ?? []).map((action) => (
                <ActionRow key={action.id} action={action} />
              ))
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
