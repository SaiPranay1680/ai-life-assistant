"use client";

import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getUsers } from "@/services/api/user.service";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";

export default function UsersPage() {
  const { user } = useAuth();
  const router = useRouter();

  const query = useQuery({
    queryKey: ["users"],
    queryFn: getUsers,
    enabled: Boolean(user),
  });

  if (!user) {
    // Redirect unauthenticated users to login
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl p-6">
        <h1 className="text-xl font-semibold">Users</h1>
        {query.isLoading && <p>Loading users…</p>}
        {query.isError && <p className="text-red-600">Unable to load users.</p>}
        {query.data?.length ? (
          <div className="mt-4 space-y-2">
            {query.data.map((u) => (
              <div key={u.id} className="rounded border p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{u.name ?? u.email}</div>
                  <div className="text-sm text-slate-500">{u.email}</div>
                </div>
                <div className="text-sm text-slate-600">{u.role}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4">No users found.</p>
        )}
      </div>
    </AppShell>
  );
}
