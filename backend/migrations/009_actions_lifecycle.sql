-- Action lifecycle: add completed_at and constrain allowed types/statuses.

ALTER TABLE actions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Normalize any unexpected legacy statuses before adding checks.
UPDATE actions
SET status = 'suggested'
WHERE status IS NULL
   OR status NOT IN ('suggested', 'confirmed', 'in_progress', 'completed', 'dismissed');

UPDATE actions
SET action_type = 'KEEP_FOR_RECORDS'
WHERE action_type IS NULL
   OR action_type NOT IN (
     'PAY', 'RENEW', 'REGISTER', 'REVIEW', 'FOLLOW_UP', 'KEEP_FOR_RECORDS'
   );

ALTER TABLE actions DROP CONSTRAINT IF EXISTS ck_actions_status;
ALTER TABLE actions
  ADD CONSTRAINT ck_actions_status
  CHECK (status IN ('suggested', 'confirmed', 'in_progress', 'completed', 'dismissed'));

ALTER TABLE actions DROP CONSTRAINT IF EXISTS ck_actions_action_type;
ALTER TABLE actions
  ADD CONSTRAINT ck_actions_action_type
  CHECK (action_type IN (
    'PAY', 'RENEW', 'REGISTER', 'REVIEW', 'FOLLOW_UP', 'KEEP_FOR_RECORDS'
  ));

CREATE INDEX IF NOT EXISTS idx_actions_workspace_status
  ON actions (workspace_id, status);
