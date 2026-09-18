CREATE TABLE IF NOT EXISTS actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  due_at DATE,
  due_label TEXT,
  priority VARCHAR(20) NOT NULL DEFAULT 'medium',
  status VARCHAR(50) NOT NULL DEFAULT 'suggested',
  confidence DOUBLE PRECISION,
  explanation TEXT,
  evidence TEXT,
  reminder_default TEXT,
  requires_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_actions_workspace_document_type UNIQUE (workspace_id, source_document_id, action_type)
);

CREATE INDEX IF NOT EXISTS idx_actions_workspace_due
  ON actions (workspace_id, due_at);
