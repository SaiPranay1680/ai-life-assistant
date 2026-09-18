"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import {
  deleteAdminUser,
  getAdminStats,
  getAdminUsers,
  updateAdminUser,
  type AdminStats,
  type AdminUser,
} from "@/services/api/admin.service";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PencilLine, ShieldAlert, Trash2, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function UserRow({
  user,
  onDelete,
  onSave,
}: {
  user: AdminUser;
  onDelete: (userId: string) => Promise<void>;
  onSave: (userId: string, changes: Record<string, string | boolean | null>) => Promise<void>;
}) {
  const [draft, setDraft] = useState({
    name: user.name ?? "",
    email: user.email,
    role: user.role,
    is_active: user.is_active,
    email_verified: user.email_verified,
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await onSave(user.id, draft);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-t border-slate-200 align-top text-sm text-slate-700">
      <td className="px-3 py-3">
        <input
          value={draft.name}
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm outline-none focus:border-blue-500"
        />
      </td>
      <td className="px-3 py-3">
        <input
          type="email"
          value={draft.email}
          onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm outline-none focus:border-blue-500"
        />
      </td>
      <td className="px-3 py-3">
        <select
          value={draft.role}
          onChange={(event) =>
            setDraft((current) => ({ ...current, role: event.target.value as "user" | "admin" }))
          }
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm outline-none focus:border-blue-500"
        >
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </td>
      <td className="px-3 py-3">
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={draft.is_active}
            onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))}
          />
          Active
        </label>
      </td>
      <td className="px-3 py-3">
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={draft.email_verified}
            onChange={(event) => setDraft((current) => ({ ...current, email_verified: event.target.checked }))}
          />
          Verified
        </label>
      </td>
      <td className="px-3 py-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={save} disabled={saving}>
            <PencilLine className="h-4 w-4" />
            {saving ? "Saving..." : "Save"}
          </Button>
          <Button variant="secondary" onClick={() => onDelete(user.id)} className="text-rose-600">
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </td>
    </tr>
  );
}

export default function AdminPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (ready && (!user || user.role !== "admin")) {
      router.replace("/dashboard");
    }
  }, [ready, router, user]);

  const statsQuery = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    enabled: ready && user?.role === "admin",
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: getAdminUsers,
    enabled: ready && user?.role === "admin",
  });

  const stats = statsQuery.data as AdminStats | undefined;

  const updateMutation = useMutation({
    mutationFn: ({ userId, changes }: { userId: string; changes: Record<string, string | boolean | null> }) =>
      updateAdminUser(userId, {
        name: changes.name !== undefined ? (String(changes.name).trim() || null) : undefined,
        email: changes.email !== undefined ? String(changes.email).trim() || null : undefined,
        role: changes.role !== undefined ? (changes.role as "user" | "admin") : undefined,
        is_active: changes.is_active !== undefined ? Boolean(changes.is_active) : undefined,
        email_verified: changes.email_verified !== undefined ? Boolean(changes.email_verified) : undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteAdminUser(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
  });

  if (!ready || !user) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading admin dashboard…</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total users" value={stats?.total_users ?? 0} />
          <StatCard label="Active users" value={stats?.active_users ?? 0} />
          <StatCard label="Admin users" value={stats?.admin_users ?? 0} />
          <StatCard label="Documents" value={stats?.total_documents ?? 0} />
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-900">System overview</h2>
            </div>
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              <li>Database connected: {stats?.database_connected ? "Yes" : "No"}</li>
              <li>Regular users: {stats?.regular_users ?? 0}</li>
              <li>Total actions: {stats?.total_actions ?? 0}</li>
              <li>Total reminders: {stats?.total_reminders ?? 0}</li>
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-2">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-5 w-5 text-amber-600" />
              <h2 className="text-lg font-semibold text-slate-900">Database tables</h2>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {(stats?.tables ?? []).slice(0, 12).map((table) => (
                <div key={table.table_name} className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {table.table_name}
                  </p>
                  <p className="mt-2 text-base font-semibold text-slate-900">{table.row_count}</p>
                  <p className="text-xs text-slate-500">{table.total_size ?? "0 bytes"}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-900">Users</h2>
            <span className="text-sm text-slate-500">{usersQuery.data?.length ?? 0} records</span>
          </div>

          {usersQuery.isLoading ? (
            <p className="text-sm text-slate-500">Loading users…</p>
          ) : null}
          {usersQuery.isError ? (
            <p className="text-sm text-rose-600">
              {usersQuery.error instanceof Error ? usersQuery.error.message : "Unable to load users."}
            </p>
          ) : null}

          {!usersQuery.isLoading && !usersQuery.isError && usersQuery.data ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-3">Name</th>
                    <th className="px-3 py-3">Email</th>
                    <th className="px-3 py-3">Role</th>
                    <th className="px-3 py-3">Active</th>
                    <th className="px-3 py-3">Verified</th>
                    <th className="px-3 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {usersQuery.data.map((record) => (
                    <UserRow
                      key={record.id}
                      user={record}
                      onDelete={async (userId) => {
                        await deleteMutation.mutateAsync(userId);
                      }}
                      onSave={async (userId, changes) => {
                        await updateMutation.mutateAsync({ userId, changes });
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
