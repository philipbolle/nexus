-- Add config column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}';

-- Update existing rows to have empty config
UPDATE agents SET config = '{}' WHERE config IS NULL;