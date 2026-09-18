-- Migration 008: Add role column to users table and update audit_logs foreign key
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';

-- Create index on role for quick filtering
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Make audit_logs foreign key ON DELETE SET NULL so user deletion cascades cleanly
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'audit_logs_user_id_fkey'
  ) THEN
    ALTER TABLE audit_logs DROP CONSTRAINT audit_logs_user_id_fkey;
  END IF;
  
  ALTER TABLE audit_logs 
  ADD CONSTRAINT audit_logs_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
EXCEPTION
  WHEN undefined_table THEN
    NULL;
END $$;
