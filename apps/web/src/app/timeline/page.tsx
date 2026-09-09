"use client";

import { AppShell } from "@/components/layout/AppShell";
import { getTimeline } from "@/services/api/action.service";
import { useQuery } from "@tanstack/react-query";

export default function TimelinePage() {
  const query = useQuery({ queryKey: ["timeline"], queryFn: getTimeline });

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-4">
        {query.isLoading ? (
          <p className="text-sm text-slate-500">Loading timeline…</p>
        ) : null}
        {(query.data ?? []).length === 0 && !query.isLoading ? (
          <p className="text-sm text-slate-500">No upcoming events.</p>
        ) : null}
        {(query.data ?? []).map((event) => (
          <div
            key={event.id}
            className="rounded-2xl border border-slate-200 bg-white px-5 py-4"
          >
            <p className="text-sm font-semibold text-blue-700">{event.dateLabel}</p>
            <p className="mt-1 text-slate-900">{event.title}</p>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
