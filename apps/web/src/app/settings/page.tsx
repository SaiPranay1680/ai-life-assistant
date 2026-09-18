"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useAuth } from "@/hooks/useAuth";
import { downloadWorkspaceExport } from "@/services/api/privacy.service";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [name, setName] = useState(user?.name ?? "");
  const [emailReminders, setEmailReminders] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(false);
  const [dataSharing, setDataSharing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

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
          <label className="mt-4 flex items-center justify-between gap-4 text-sm">
            Data sharing for product improvement
            <input
              type="checkbox"
              checked={dataSharing}
              onChange={(event) => setDataSharing(event.target.checked)}
            />
          </label>
          <Button
            variant="danger"
            className="mt-5"
            onClick={() => setDeleteOpen(true)}
          >
            Delete account
          </Button>
          <Button
            variant="secondary"
            className="mt-3"
            disabled={exporting}
            onClick={() => {
              setExportError(null);
              setExporting(true);
              void downloadWorkspaceExport()
                .catch((error) => setExportError(error instanceof Error ? error.message : "Unable to export data."))
                .finally(() => setExporting(false));
            }}
          >
            {exporting ? "Preparing export…" : "Download my data"}
          </Button>
          {exportError ? <p className="mt-3 text-sm text-rose-600">{exportError}</p> : null}
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
      >
        Account deletion will be available when the backend privacy APIs are connected.
        No personal data is removed from this mock environment.
      </Modal>
    </AppShell>
  );
}
