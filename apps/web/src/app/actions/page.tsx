"use client";

import { ActionCard, ActionRow } from "@/components/cards/ActionCard";
import { AppShell } from "@/components/layout/AppShell";
import { createReminder, dismissAction, getActions } from "@/services/api/action.service";
import type { ActionItem } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

function SuggestedActionCard({ action }: { action: ActionItem }) {
  const queryClient = useQueryClient();
  const [reminder, setReminder] = useState(action.reminderDefault);
  const [error, setError] = useState<string | null>(null);
  const reminderMutation = useMutation({
    mutationFn: () => createReminder(action.id, reminder),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["actions"] });
      await queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to create reminder."),
  });
  const dismissMutation = useMutation({
    mutationFn: () => dismissAction(action.id),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["actions"] });
      await queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to dismiss action."),
  });
  const busy = reminderMutation.isPending || dismissMutation.isPending;

  return (
    <div className="mb-6">
      <ActionCard
        action={action}
        reminder={reminder}
        onReminderChange={setReminder}
        onCreate={() => reminderMutation.mutate()}
        onDismiss={() => dismissMutation.mutate()}
        busy={busy}
      />
      {error ? <p className="mx-auto mt-4 max-w-2xl text-center text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}

export default function ActionsPage() {
  const query = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const suggested = (query.data ?? []).filter((item) => item.status === "suggested");
  const reminded = (query.data ?? []).filter((item) => item.status === "reminder_set");

  return (
    <AppShell>
      {query.isLoading ? (
        <p className="text-sm text-slate-500">Loading action…</p>
      ) : null}
      {query.isError ? (
        <p className="text-sm text-rose-600">
          {query.error instanceof Error ? query.error.message : "Unable to load actions."}
        </p>
      ) : null}
      {suggested.map((action) => (
        <SuggestedActionCard key={action.id} action={action} />
      ))}
      {reminded.length > 0 ? (
        <div className="mx-auto mt-4 max-w-2xl rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Reminders set</h2>
          <div className="mt-3 space-y-3">
            {reminded.map((action) => (
              <ActionRow key={action.id} action={action} />
            ))}
          </div>
        </div>
      ) : null}
      {!query.isLoading && !query.isError && suggested.length === 0 && reminded.length === 0 ? (
        <p className="text-sm text-slate-500">No suggested actions right now.</p>
      ) : null}
    </AppShell>
  );
}
