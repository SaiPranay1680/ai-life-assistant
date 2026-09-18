CREATE TABLE IF NOT EXISTS reminders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  fire_at TIMESTAMPTZ NOT NULL,
  channel VARCHAR(50) NOT NULL DEFAULT 'in_app',
  offset_label TEXT,
  idempotency_key TEXT NOT NULL,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_reminders_workspace_fire
  ON reminders (workspace_id, fire_at);

ALTER TABLE actions ADD COLUMN IF NOT EXISTS confirmed_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE actions ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
