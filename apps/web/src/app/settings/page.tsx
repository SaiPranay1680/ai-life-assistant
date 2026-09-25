"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteAccount } from "@/services/api/privacy.service";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [name, setName] = useState(user?.name ?? "");
  const [emailReminders, setEmailReminders] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(false);
  const [dataSharing, setDataSharing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Profile</h2>
          <div className="mt-4 space-y-4">
            <Input label="Name" value={name} onChange={(event) => setName(event.target.value)} />
            <Input label="Email" value={user?.email ?? ""} disabled />
          </div>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Privacy</h2>
          <Button
            variant="danger"
            className="mt-5"
            onClick={() => setDeleteOpen(true)}
          >
            Delete account
          </Button>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Notifications</h2>
          <label className="mt-4 flex items-center justify-between gap-4 text-sm">
            Email reminders
            <input
              type="checkbox"
              checked={emailReminders}
              onChange={(event) => setEmailReminders(event.target.checked)}
            />
          </label>
          <label className="mt-3 flex items-center justify-between gap-4 text-sm">
            Push notifications
            <input
              type="checkbox"
              checked={pushNotifications}
              onChange={(event) => setPushNotifications(event.target.checked)}
            />
          </label>
        </section>
        <Button
          variant="secondary"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          Sign out
        </Button>
      </div>
      <Modal
        open={deleteOpen}
        title="Delete account"
        onClose={() => setDeleteOpen(false)}
        showClose={false}
      >
        <div className="space-y-4">
          <p>Deleting your account will permanently remove your personal data and workspace. This action cannot be undone.</p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={async () => {
                if (!confirm('Are you sure you want to delete your account? This cannot be undone.')) return;
                setDeleting(true);
                try {
                  await deleteAccount();
                  logout();
                  router.replace('/login');
                } catch (err) {
                  // eslint-disable-next-line no-console
                  console.error('Delete failed', err);
                  setDeleting(false);
                }
              }}
              disabled={deleting}
            >
              {deleting ? 'Deleting…' : 'Delete account'}
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}
