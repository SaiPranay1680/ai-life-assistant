CREATE TABLE IF NOT EXISTS auth_otp_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email CITEXT NOT NULL,
  otp_hash TEXT NOT NULL,
  otp_type TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT auth_otp_codes_type_check
    CHECK (otp_type IN ('PASSWORD_RESET', 'ACCOUNT_VERIFICATION'))
);

CREATE INDEX IF NOT EXISTS idx_auth_otp_user_type_created
  ON auth_otp_codes (user_id, otp_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_otp_email_type
  ON auth_otp_codes (email, otp_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_otp_active
  ON auth_otp_codes (user_id, otp_type, used_at, expires_at);
