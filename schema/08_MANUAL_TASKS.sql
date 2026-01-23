-- Manual Tasks Table
-- Stores tasks that require human intervention and cannot be automated by AI agents
-- These tasks are automatically logged by agents, tools, orchestrators, and error handlers
-- when they encounter scenarios they "cannot do even with approval"

CREATE TABLE IF NOT EXISTS manual_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) CHECK (category IN ('security', 'configuration', 'purchase', 'approval', 'physical', 'legal', 'personal', 'technical', 'general')),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    source_system VARCHAR(100) NOT NULL,
    source_id UUID,
    source_context JSONB DEFAULT '{}',
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    assigned_to VARCHAR(100),
    due_date DATE,
    completed_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_hash)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_manual_tasks_status ON manual_tasks(status);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_priority ON manual_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_category ON manual_tasks(category);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_source_system ON manual_tasks(source_system);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_source_id ON manual_tasks(source_id);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_created_at ON manual_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_manual_tasks_due_date ON manual_tasks(due_date);

-- Add comment
COMMENT ON TABLE manual_tasks IS 'Tasks requiring human intervention that cannot be automated by AI agents';
COMMENT ON COLUMN manual_tasks.content_hash IS 'SHA-256 hash of title+description+category for deduplication';
COMMENT ON COLUMN manual_tasks.source_system IS 'System that created the task (agent:name, tool:name, orchestrator, error_handler, etc.)';
COMMENT ON COLUMN manual_tasks.source_id IS 'ID of the source entity (agent_id, tool_execution_id, etc.)';
COMMENT ON COLUMN manual_tasks.source_context IS 'Additional context about why task was created (JSON)';