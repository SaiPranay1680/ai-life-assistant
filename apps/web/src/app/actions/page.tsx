"use client";

import { ActionCard, ActionRow } from "@/components/cards/ActionCard";
import { AppShell } from "@/components/layout/AppShell";
import {
  completeAction,
  confirmAction,
  createReminder,
  dismissAction,
  getActions,
  startAction,
} from "@/services/api/action.service";
import type { ActionItem } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

function useInvalidateActions() {
  const queryClient = useQueryClient();
  return async () => {
    await queryClient.invalidateQueries({ queryKey: ["actions"] });
    await queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };
}

function SuggestedActionCard({ action }: { action: ActionItem }) {
  const invalidate = useInvalidateActions();
  const [reminder, setReminder] = useState(action.reminderDefault);
  const [error, setError] = useState<string | null>(null);

  const confirmMutation = useMutation({
    mutationFn: () => confirmAction(action.id),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to confirm action."),
  });
  const reminderMutation = useMutation({
    mutationFn: () => createReminder(action.id, reminder),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to create reminder."),
  });
  const dismissMutation = useMutation({
    mutationFn: () => dismissAction(action.id),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to dismiss action."),
  });
  const busy =
    confirmMutation.isPending || reminderMutation.isPending || dismissMutation.isPending;

  return (
    <div className="mb-6">
      <ActionCard
        action={action}
        reminder={reminder}
        onReminderChange={setReminder}
        onConfirm={() => confirmMutation.mutate()}
        onRemind={() => reminderMutation.mutate()}
        onDismiss={() => dismissMutation.mutate()}
        busy={busy}
      />
      {error ? <p className="mx-auto mt-4 max-w-2xl text-center text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}

function ActiveActionRow({ action }: { action: ActionItem }) {
  const invalidate = useInvalidateActions();
  const [error, setError] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: () => startAction(action.id),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to start action."),
  });
  const completeMutation = useMutation({
    mutationFn: () => completeAction(action.id),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to complete action."),
  });
  const dismissMutation = useMutation({
    mutationFn: () => dismissAction(action.id),
    onSuccess: async () => {
      setError(null);
      await invalidate();
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Unable to dismiss action."),
  });
  const busy = startMutation.isPending || completeMutation.isPending || dismissMutation.isPending;

  return (
    <div>
      <ActionRow
        action={action}
        onStart={() => startMutation.mutate()}
        onComplete={() => completeMutation.mutate()}
        onDismiss={() => dismissMutation.mutate()}
        busy={busy}
      />
      {error ? <p className="mt-2 text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}

function Section({
  title,
  children,
  empty,
}: {
  title: string;
  children: ReactNode;
  empty?: boolean;
}) {
  if (empty) return null;
  return (
    <div className="mx-auto mt-4 max-w-2xl rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <div className="mt-3 space-y-3">{children}</div>
    </div>
  );
}

export default function ActionsPage() {
  const query = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const items = query.data ?? [];
  const suggested = items.filter((item) => item.status === "suggested");
  const confirmed = items.filter((item) => item.status === "confirmed");
  const inProgress = items.filter((item) => item.status === "in_progress");
  const completed = items.filter((item) => item.status === "completed");
  const hasAny =
    suggested.length > 0 || confirmed.length > 0 || inProgress.length > 0 || completed.length > 0;

  return (
    <AppShell>
      {query.isLoading ? <p className="text-sm text-slate-500">Loading actions…</p> : null}
      {query.isError ? (
        <p className="text-sm text-rose-600">
          {query.error instanceof Error ? query.error.message : "Unable to load actions."}
        </p>
      ) : null}
      {suggested.map((action) => (
        <SuggestedActionCard key={action.id} action={action} />
      ))}
      <Section title="Confirmed" empty={confirmed.length === 0}>
        {confirmed.map((action) => (
          <ActiveActionRow key={action.id} action={action} />
        ))}
      </Section>
      <Section title="In progress" empty={inProgress.length === 0}>
        {inProgress.map((action) => (
          <ActiveActionRow key={action.id} action={action} />
        ))}
      </Section>
      <Section title="Completed" empty={completed.length === 0}>
        {completed.map((action) => (
          <ActionRow key={action.id} action={action} />
        ))}
      </Section>
      {!query.isLoading && !query.isError && !hasAny ? (
        <p className="text-sm text-slate-500">No suggested actions right now.</p>
      ) : null}
    </AppShell>
  );
}
