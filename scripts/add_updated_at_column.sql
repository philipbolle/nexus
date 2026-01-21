-- Add updated_at column to agent_tools table if it doesn't exist
ALTER TABLE agent_tools ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- Set default value for existing rows
UPDATE agent_tools SET updated_at = created_at WHERE updated_at IS NULL;

-- Make column not null after setting defaults
ALTER TABLE agent_tools ALTER COLUMN updated_at SET NOT NULL;
ALTER TABLE agent_tools ALTER COLUMN updated_at SET DEFAULT NOW();