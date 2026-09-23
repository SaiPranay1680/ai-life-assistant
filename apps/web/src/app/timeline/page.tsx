"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import {
  ExpectedTotal,
  LifeSection,
  MoneyOutSection,
  MonthSwitcher,
  OverdueSection,
  TimelineNote,
  TimelineSkeleton,
} from "@/components/timeline/TimelineBoard";
import { completeAction, confirmAction, getActions } from "@/services/api/action.service";
import { buildTimeline, monthLabel, type TimelineRow } from "@/utils/timeline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

export default function TimelinePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const query = useQuery({ queryKey: ["actions"], queryFn: getActions });
  const label = monthLabel(cursor.year, cursor.month);

  const model = useMemo(
    () => buildTimeline(query.data ?? [], cursor.year, cursor.month, now),
    [query.data, cursor.year, cursor.month],
  );

  const paidMutation = useMutation({
    mutationFn: async (row: TimelineRow) => {
      if (row.action.status === "suggested") {
        await confirmAction(row.id);
      }
      return completeAction(row.id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["actions"] });
      await queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  function shiftMonth(delta: number) {
    setCursor((current) => {
      const date = new Date(current.year, current.month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });
  }

  function onPaid(row: TimelineRow) {
    if (!window.confirm(`Mark ${row.title} as paid?`)) return;
    paidMutation.mutate(row);
  }

  const empty =
    !query.isLoading &&
    !query.isError &&
    model.overdue.length === 0 &&
    model.money.length === 0 &&
    model.life.length === 0;

  return (
    <AppShell>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <MonthSwitcher label={label} onPrev={() => shiftMonth(-1)} onNext={() => shiftMonth(1)} />
        <ExpectedTotal amount={model.expected} monthLabel={label} />
      </div>

      {query.isLoading ? <div className="mt-6"><TimelineSkeleton /></div> : null}

      {query.isError ? (
        <div className="mt-6 rounded-2xl border border-rose-100 bg-white p-6">
          <p role="alert" className="text-sm text-rose-600">
            {query.error instanceof Error ? query.error.message : "Unable to load timeline."}
          </p>
          <Button className="mt-3" variant="secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
            Try again
          </Button>
        </div>
      ) : null}

      {!query.isLoading && !query.isError ? (
        <div className="mt-6 space-y-5">
          {empty ? (
            <p className="rounded-2xl border border-slate-100 bg-white p-6 text-sm text-slate-500">
              No dated bills or appointments this month. Confirm a document to see it here.
            </p>
          ) : (
            <>
              <OverdueSection rows={model.overdue} busyId={paidMutation.isPending ? paidMutation.variables?.id : null} onPaid={onPaid} />
              <MoneyOutSection
                rows={model.money}
                monthLabel={label}
                busyId={paidMutation.isPending ? paidMutation.variables?.id : null}
                onPaid={onPaid}
              />
              <LifeSection rows={model.life} onOpen={() => router.push("/actions")} />
            </>
          )}
          <TimelineNote />
        </div>
      ) : null}

      {paidMutation.isError ? (
        <p role="alert" className="mt-4 text-sm text-rose-600">
          {paidMutation.error instanceof Error ? paidMutation.error.message : "Unable to mark this as paid."}
        </p>
      ) : null}
    </AppShell>
  );
}
