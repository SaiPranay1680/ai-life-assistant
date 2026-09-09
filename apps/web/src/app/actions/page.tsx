"use client";

import { ActionCard } from "@/components/cards/ActionCard";
import { AppShell } from "@/components/layout/AppShell";
import { createReminder, getActions } from "@/services/api/action.service";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

export default function ActionsPage() {
  const query = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const action = query.data?.[1] ?? query.data?.[0];
  const [reminder, setReminder] = useState("Remind me 30 days before");
  const [message, setMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createReminder(action?.id ?? "", reminder),
    onSuccess: () => setMessage("Reminder created. We'll notify you in time."),
  });

  return (
    <AppShell>
      {query.isLoading ? (
        <p className="text-sm text-slate-500">Loading action…</p>
      ) : null}
      {action ? (
        <ActionCard
          action={action}
          reminder={reminder}
          onReminderChange={setReminder}
          onCreate={() => mutation.mutate()}
          onDismiss={() => setMessage("Action dismissed. You can find it later in Documents.")}
          busy={mutation.isPending}
        />
      ) : (
        !query.isLoading && (
          <p className="text-sm text-slate-500">No suggested actions right now.</p>
        )
      )}
      {message ? (
        <p className="mx-auto mt-4 max-w-2xl text-center text-sm text-emerald-700">
          {message}
        </p>
      ) : null}
    </AppShell>
  );
}
