-- Migration 007: Add name column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT;

-- Backfill existing users' name from user_profiles display_name if available
UPDATE users u
SET name = up.display_name
FROM user_profiles up
WHERE u.id = up.user_id AND (u.name IS NULL OR u.name = '') AND up.display_name IS NOT NULL;
