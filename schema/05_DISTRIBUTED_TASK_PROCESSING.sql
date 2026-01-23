-- ====================================================================
-- NEXUS Distributed Task Processing Schema
--
-- Extends the existing task system with distributed processing capabilities
-- Includes worker management, leader election, and task sharding
-- ====================================================================

-- ===== Worker Management =====

CREATE TABLE IF NOT EXISTS task_workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id VARCHAR(255) NOT NULL UNIQUE,
    worker_type VARCHAR(50) NOT NULL DEFAULT 'celery_worker',
    hostname VARCHAR(255) NOT NULL,
    pid INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'online', -- online, offline, busy, idle
    active_tasks INTEGER NOT NULL DEFAULT 0,
    max_tasks INTEGER NOT NULL DEFAULT 10,
    queue_names TEXT[] DEFAULT '{}',
    capabilities JSONB DEFAULT '{}',
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_workers_status ON task_workers(status);
CREATE INDEX IF NOT EXISTS idx_task_workers_last_heartbeat ON task_workers(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_task_workers_active_tasks ON task_workers(active_tasks);

-- Track worker registration events
CREATE TABLE IF NOT EXISTS worker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- registered, unregistered, heartbeat, scaled_up, scaled_down
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worker_events_worker_id ON worker_events(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_events_event_type ON worker_events(event_type);
CREATE INDEX IF NOT EXISTS idx_worker_events_created_at ON worker_events(created_at);

-- ===== Leader Election =====

CREATE TABLE IF NOT EXISTS leader_election (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role VARCHAR(50) NOT NULL UNIQUE, -- coordinator, scheduler, monitor
    node_id VARCHAR(255) NOT NULL,
    node_info JSONB DEFAULT '{}',
    term INTEGER NOT NULL DEFAULT 0,
    voted_for VARCHAR(255),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lease_expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 seconds',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leader_election_role ON leader_election(role);
CREATE INDEX IF NOT EXISTS idx_leader_election_lease_expires ON leader_election(lease_expires_at);

-- Leader election history
CREATE TABLE IF NOT EXISTS leader_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role VARCHAR(50) NOT NULL,
    old_leader VARCHAR(255),
    new_leader VARCHAR(255) NOT NULL,
    election_type VARCHAR(50) NOT NULL, -- normal, contested, forced
    term INTEGER NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leader_history_role ON leader_history(role);
CREATE INDEX IF NOT EXISTS idx_leader_history_created_at ON leader_history(created_at);

-- ===== Task Sharding =====

CREATE TABLE IF NOT EXISTS task_shards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shard_key VARCHAR(50) NOT NULL, -- 0-9 or other shard identifier
    worker_id VARCHAR(255) NOT NULL,
    task_count INTEGER NOT NULL DEFAULT 0,
    last_assigned TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(shard_key, worker_id)
);

CREATE INDEX IF NOT EXISTS idx_task_shards_shard_key ON task_shards(shard_key);
CREATE INDEX IF NOT EXISTS idx_task_shards_worker_id ON task_shards(worker_id);
CREATE INDEX IF NOT EXISTS idx_task_shards_task_count ON task_shards(task_count);

-- ===== Distributed Task Queue =====

-- Extend existing tasks table with distributed processing fields
-- First check if column exists, if not add
DO $$
BEGIN
    -- Add distributed processing flag
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'use_distributed') THEN
        ALTER TABLE tasks ADD COLUMN use_distributed BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add worker assignment
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'assigned_worker_id') THEN
        ALTER TABLE tasks ADD COLUMN assigned_worker_id VARCHAR(255);
    END IF;

    -- Add shard key
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'shard_key') THEN
        ALTER TABLE tasks ADD COLUMN shard_key VARCHAR(50);
    END IF;

    -- Add queue name
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'queue_name') THEN
        ALTER TABLE tasks ADD COLUMN queue_name VARCHAR(100) DEFAULT 'default';
    END IF;

    -- Add priority (higher number = higher priority)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'priority') THEN
        ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 0;
    END IF;

    -- Add retry count
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'retry_count') THEN
        ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;

    -- Add max retries
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'max_retries') THEN
        ALTER TABLE tasks ADD COLUMN max_retries INTEGER DEFAULT 3;
    END IF;

    -- Add error information
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'last_error') THEN
        ALTER TABLE tasks ADD COLUMN last_error TEXT;
    END IF;

    -- Add celery task ID
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'tasks' AND column_name = 'celery_task_id') THEN
        ALTER TABLE tasks ADD COLUMN celery_task_id VARCHAR(255);
    END IF;
END
$$;

-- Create indexes for distributed task processing
CREATE INDEX IF NOT EXISTS idx_tasks_use_distributed ON tasks(use_distributed) WHERE use_distributed = true;
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_worker_id ON tasks(assigned_worker_id);
CREATE INDEX IF NOT EXISTS idx_tasks_shard_key ON tasks(shard_key);
CREATE INDEX IF NOT EXISTS idx_tasks_queue_name ON tasks(queue_name);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_celery_task_id ON tasks(celery_task_id);

-- ===== Task Queue Monitoring =====

CREATE TABLE IF NOT EXISTS task_queue_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name VARCHAR(100) NOT NULL,
    worker_count INTEGER NOT NULL DEFAULT 0,
    queued_tasks INTEGER NOT NULL DEFAULT 0,
    active_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    avg_processing_time_ms INTEGER,
    max_queue_depth INTEGER NOT NULL DEFAULT 0,
    sampled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_queue_stats_queue_name ON task_queue_stats(queue_name);
CREATE INDEX IF NOT EXISTS idx_task_queue_stats_sampled_at ON task_queue_stats(sampled_at);

-- ===== Scaling Decisions =====

CREATE TABLE IF NOT EXISTS scaling_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_type VARCHAR(50) NOT NULL, -- scale_up, scale_down, maintain
    queue_name VARCHAR(100) NOT NULL,
    current_workers INTEGER NOT NULL,
    target_workers INTEGER NOT NULL,
    reason TEXT NOT NULL,
    metrics JSONB DEFAULT '{}',
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scaling_decisions_decision_type ON scaling_decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_scaling_decisions_queue_name ON scaling_decisions(queue_name);
CREATE INDEX IF NOT EXISTS idx_scaling_decisions_applied ON scaling_decisions(applied);
CREATE INDEX IF NOT EXISTS idx_scaling_decisions_created_at ON scaling_decisions(created_at);

-- ===== Performance Metrics =====

CREATE TABLE IF NOT EXISTS distributed_task_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL, -- task_completion, worker_utilization, queue_depth, scaling_event
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    labels JSONB DEFAULT '{}',
    sampled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_distributed_task_metrics_metric_type ON distributed_task_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_distributed_task_metrics_metric_name ON distributed_task_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_distributed_task_metrics_sampled_at ON distributed_task_metrics(sampled_at);

-- ===== Functions and Triggers =====

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to new tables
CREATE TRIGGER update_task_workers_updated_at
    BEFORE UPDATE ON task_workers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leader_election_updated_at
    BEFORE UPDATE ON leader_election
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_shards_updated_at
    BEFORE UPDATE ON task_shards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up stale workers
CREATE OR REPLACE FUNCTION cleanup_stale_workers()
RETURNS INTEGER AS $$
DECLARE
    stale_count INTEGER;
BEGIN
    WITH updated AS (
        UPDATE task_workers
        SET status = 'offline'
        WHERE last_heartbeat < NOW() - INTERVAL '5 minutes'
        AND status != 'offline'
        RETURNING id
    )
    SELECT COUNT(*) INTO stale_count FROM updated;

    RETURN stale_count;
END;
$$ language 'plpgsql';

-- Function to get queue depth
CREATE OR REPLACE FUNCTION get_queue_depth(queue_name_param VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    depth INTEGER;
BEGIN
    SELECT COUNT(*) INTO depth
    FROM tasks
    WHERE queue_name = queue_name_param
    AND status IN ('pending', 'queued', 'retrying')
    AND use_distributed = true;

    RETURN depth;
END;
$$ language 'plpgsql';

-- ===== Initial Data =====

-- Insert default coordinator role (no leader initially)
INSERT INTO leader_election (role, node_id, term, lease_expires_at)
VALUES ('coordinator', '', 0, NOW())
ON CONFLICT (role) DO NOTHING;

INSERT INTO leader_election (role, node_id, term, lease_expires_at)
VALUES ('scheduler', '', 0, NOW())
ON CONFLICT (role) DO NOTHING;

INSERT INTO leader_election (role, node_id, term, lease_expires_at)
VALUES ('monitor', '', 0, NOW())
ON CONFLICT (role) DO NOTHING;

-- ===== Comments =====

COMMENT ON TABLE task_workers IS 'Registered workers for distributed task processing';
COMMENT ON TABLE worker_events IS 'Worker lifecycle events for auditing';
COMMENT ON TABLE leader_election IS 'Leader election state for distributed coordination';
COMMENT ON TABLE leader_history IS 'History of leader elections';
COMMENT ON TABLE task_shards IS 'Task sharding assignments for load distribution';
COMMENT ON TABLE task_queue_stats IS 'Queue statistics for monitoring and scaling decisions';
COMMENT ON TABLE scaling_decisions IS 'Scaling decisions made by the auto-scaler';
COMMENT ON TABLE distributed_task_metrics IS 'Performance metrics for distributed task processing';

-- ====================================================================
-- Schema Version
-- ====================================================================

INSERT INTO schema_version (version, description, applied_at)
VALUES ('5.0', 'Distributed Task Processing Schema', NOW())
ON CONFLICT (version) DO UPDATE SET applied_at = NOW(), description = EXCLUDED.description;