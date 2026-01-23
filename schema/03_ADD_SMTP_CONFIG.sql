-- =============================================================================
-- Migration: Add SMTP Configuration to Email Accounts
-- Date: 2026-01-21
-- Purpose: Enable email sending capabilities for email accounts
-- =============================================================================

BEGIN;

-- Add SMTP configuration columns to email_accounts table
ALTER TABLE email_accounts
ADD COLUMN IF NOT EXISTS smtp_server VARCHAR(255),
ADD COLUMN IF NOT EXISTS smtp_port INTEGER DEFAULT 587,
ADD COLUMN IF NOT EXISTS smtp_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS smtp_password TEXT,
ADD COLUMN IF NOT EXISTS smtp_use_tls BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS smtp_use_ssl BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS smtp_auth_method VARCHAR(50) DEFAULT 'password';

-- Add index for faster lookups of active accounts with SMTP configured
CREATE INDEX IF NOT EXISTS idx_email_accounts_active_smtp
ON email_accounts(is_active, smtp_server)
WHERE is_active = true AND smtp_server IS NOT NULL;

-- Update the schema version in system_config
INSERT INTO system_config (key, value, category, description)
VALUES ('schema_version', '"3.1"'::jsonb, 'system', 'Schema version with SMTP configuration')
ON CONFLICT (key) DO UPDATE
SET value = '"3.1"'::jsonb,
    updated_at = NOW();

COMMIT;

-- =============================================================================
-- Verification Queries
-- =============================================================================

/*
-- Verify columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'email_accounts'
ORDER BY ordinal_position;

-- Verify index was created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'email_accounts'
AND indexname = 'idx_email_accounts_active_smtp';

-- Verify default values
SELECT
    column_name,
    column_default,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'email_accounts'
AND column_name LIKE 'smtp%'
ORDER BY ordinal_position;
*/