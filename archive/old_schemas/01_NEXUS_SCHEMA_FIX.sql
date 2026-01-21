-- ╔═══════════════════════════════════════════════════════════════════════════════╗
-- ║                    NEXUS SCHEMA FIX SCRIPT                                    ║
-- ║                                                                               ║
-- ║  Fixes issues from initial schema application                                 ║
-- ║  Run this AFTER the main schema to repair errors                             ║
-- ╚═══════════════════════════════════════════════════════════════════════════════╝

-- =============================================================================
-- STEP 1: Fix the agents table (INTEGER vs UUID conflict)
-- =============================================================================

-- First, let's see what the old agents table looks like and preserve any data
CREATE TABLE IF NOT EXISTS agents_backup AS SELECT * FROM agents;

-- Drop the old agents table and related constraints
DROP TABLE IF EXISTS agents CASCADE;

-- Recreate agents with UUID (the correct way)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'domain',
    domain VARCHAR(100),
    role TEXT NOT NULL DEFAULT 'General assistant',
    goal TEXT,
    backstory TEXT,
    system_prompt TEXT NOT NULL DEFAULT 'You are a helpful assistant.',
    model_preference VARCHAR(100),
    fallback_models TEXT[],
    capabilities TEXT[],
    tools TEXT[],
    supervisor_id UUID,
    is_active BOOLEAN DEFAULT true,
    allow_delegation BOOLEAN DEFAULT true,
    max_iterations INTEGER DEFAULT 10,
    temperature DECIMAL(2,1) DEFAULT 0.7,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add self-reference for supervisor
ALTER TABLE agents ADD CONSTRAINT agents_supervisor_fkey 
    FOREIGN KEY (supervisor_id) REFERENCES agents(id);

-- =============================================================================
-- STEP 2: Recreate sessions table
-- =============================================================================

DROP TABLE IF EXISTS sessions CASCADE;

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_type VARCHAR(50) DEFAULT 'chat',
    title VARCHAR(255),
    summary TEXT,
    primary_agent_id UUID REFERENCES agents(id),
    agents_involved UUID[],
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_last_message ON sessions(last_message_at DESC);

-- =============================================================================
-- STEP 3: Recreate messages table
-- =============================================================================

DROP TABLE IF EXISTS messages CASCADE;

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_id UUID REFERENCES agents(id),
    parent_message_id UUID,
    tool_calls JSONB,
    tool_results JSONB,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10,6),
    model_used VARCHAR(100),
    latency_ms INTEGER,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE messages ADD CONSTRAINT messages_parent_fkey 
    FOREIGN KEY (parent_message_id) REFERENCES messages(id);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);

-- =============================================================================
-- STEP 4: Recreate agent-related tables with correct UUID types
-- =============================================================================

-- Agent tool assignments
DROP TABLE IF EXISTS agent_tool_assignments CASCADE;
CREATE TABLE agent_tool_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    tool_id UUID REFERENCES agent_tools(id),
    is_enabled BOOLEAN DEFAULT true,
    custom_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, tool_id)
);

-- Agent handoffs
DROP TABLE IF EXISTS agent_handoffs CASCADE;
CREATE TABLE agent_handoffs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    from_agent_id UUID REFERENCES agents(id),
    to_agent_id UUID REFERENCES agents(id),
    reason TEXT NOT NULL,
    context_summary TEXT,
    context_tokens INTEGER,
    handoff_type VARCHAR(50),
    success BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent performance (daily)
DROP TABLE IF EXISTS agent_performance CASCADE;
CREATE TABLE agent_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    avg_latency_ms DECIMAL(10,2),
    p50_latency_ms INTEGER,
    p95_latency_ms INTEGER,
    p99_latency_ms INTEGER,
    avg_user_rating DECIMAL(2,1),
    total_ratings INTEGER DEFAULT 0,
    handoffs_initiated INTEGER DEFAULT 0,
    handoffs_received INTEGER DEFAULT 0,
    tools_used JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, date)
);

-- Agent suggestions
DROP TABLE IF EXISTS agent_suggestions CASCADE;
CREATE TABLE agent_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    suggestion_type VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT,
    supporting_data JSONB,
    priority VARCHAR(20) DEFAULT 'medium',
    urgency_score DECIMAL(3,2),
    impact_score DECIMAL(3,2),
    confidence_score DECIMAL(3,2),
    status VARCHAR(20) DEFAULT 'pending',
    user_response VARCHAR(20),
    user_feedback TEXT,
    implemented_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_suggestions_pending ON agent_suggestions(status, created_at DESC) 
    WHERE status = 'pending';

-- Agent collaborations
DROP TABLE IF EXISTS agent_collaborations CASCADE;
CREATE TABLE agent_collaborations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    initiator_agent_id UUID REFERENCES agents(id),
    collaborators UUID[] NOT NULL,
    task_description TEXT NOT NULL,
    collaboration_type VARCHAR(50),
    messages_exchanged INTEGER DEFAULT 0,
    outcome VARCHAR(50),
    outcome_summary TEXT,
    quality_score DECIMAL(3,2),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Privacy shield logs
DROP TABLE IF EXISTS privacy_shield_logs CASCADE;
CREATE TABLE privacy_shield_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    original_query_hash VARCHAR(64),
    secrets_detected JSONB,
    secrets_count INTEGER DEFAULT 0,
    redacted_query TEXT,
    external_provider VARCHAR(50),
    secrets_reinjected BOOLEAN DEFAULT false,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tool executions
DROP TABLE IF EXISTS tool_executions CASCADE;
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    message_id UUID REFERENCES messages(id),
    agent_id UUID REFERENCES agents(id),
    tool_id UUID REFERENCES agent_tools(id),
    input_params JSONB NOT NULL,
    output_result JSONB,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    required_confirmation BOOLEAN DEFAULT false,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent events (event sourcing)
DROP TABLE IF EXISTS agent_events CASCADE;
CREATE TABLE agent_events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INTEGER NOT NULL,
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, version)
);

CREATE INDEX idx_agent_events_aggregate ON agent_events(aggregate_id, version);
CREATE INDEX idx_agent_events_type ON agent_events(event_type, created_at DESC);

-- Agent versions
DROP TABLE IF EXISTS agent_versions CASCADE;
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    version INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    model_preference VARCHAR(100),
    temperature DECIMAL(2,1),
    config_changes JSONB,
    change_notes TEXT,
    is_active BOOLEAN DEFAULT false,
    performance_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, version)
);

-- Agent experiments (A/B testing)
DROP TABLE IF EXISTS agent_experiments CASCADE;
CREATE TABLE agent_experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_id UUID REFERENCES agents(id),
    hypothesis TEXT,
    control_version_id UUID REFERENCES agent_versions(id),
    treatment_version_id UUID REFERENCES agent_versions(id),
    traffic_split JSONB DEFAULT '{"control": 0.5, "treatment": 0.5}',
    status VARCHAR(20) DEFAULT 'draft',
    success_metrics TEXT[],
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    min_sample_size INTEGER,
    current_sample_size INTEGER DEFAULT 0,
    results JSONB,
    winner VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Experiment observations
DROP TABLE IF EXISTS experiment_observations CASCADE;
CREATE TABLE experiment_observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID REFERENCES agent_experiments(id),
    variant VARCHAR(20) NOT NULL,
    session_id UUID REFERENCES sessions(id),
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- STEP 5: Recreate memory system tables
-- =============================================================================

-- Memory blocks
DROP TABLE IF EXISTS memory_blocks CASCADE;
CREATE TABLE memory_blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    block_label VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    char_limit INTEGER DEFAULT 2000,
    current_length INTEGER GENERATED ALWAYS AS (length(content)) STORED,
    version INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, block_label)
);

-- Memories (without vector for now - will add when pgvector installed)
DROP TABLE IF EXISTS memories CASCADE;
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    memory_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    -- content_embedding will be added after pgvector is installed
    importance_score DECIMAL(3,2) DEFAULT 0.5,
    strength_score DECIMAL(3,2) DEFAULT 1.0,
    emotional_valence DECIMAL(3,2),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    source_type VARCHAR(50),
    source_id UUID,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memories_agent ON memories(agent_id, memory_type);
CREATE INDEX idx_memories_importance ON memories(importance_score DESC);

-- Semantic memories
DROP TABLE IF EXISTS semantic_memories CASCADE;
CREATE TABLE semantic_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source_citations TEXT[],
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT true
);

-- Episodic memories
DROP TABLE IF EXISTS episodic_memories CASCADE;
CREATE TABLE episodic_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id),
    event_summary TEXT NOT NULL,
    participants TEXT[],
    outcome VARCHAR(100),
    outcome_quality DECIMAL(3,2),
    lessons_learned TEXT[],
    reusable_patterns JSONB,
    occurred_at TIMESTAMPTZ NOT NULL
);

-- Procedural memories
DROP TABLE IF EXISTS procedural_memories CASCADE;
CREATE TABLE procedural_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    skill_name VARCHAR(255) NOT NULL,
    trigger_conditions JSONB,
    steps JSONB NOT NULL,
    success_criteria TEXT,
    failure_modes TEXT[],
    performance_history JSONB,
    last_used_at TIMESTAMPTZ
);

-- Memory relations
DROP TABLE IF EXISTS memory_relations CASCADE;
CREATE TABLE memory_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    target_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,
    strength DECIMAL(3,2) DEFAULT 0.5,
    bidirectional BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory access log
DROP TABLE IF EXISTS memory_access_log CASCADE;
CREATE TABLE memory_access_log (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID REFERENCES memories(id),
    agent_id UUID REFERENCES agents(id),
    session_id UUID REFERENCES sessions(id),
    access_type VARCHAR(50) NOT NULL,
    relevance_score DECIMAL(3,2),
    was_useful BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory consolidation jobs
DROP TABLE IF EXISTS memory_consolidation_jobs CASCADE;
CREATE TABLE memory_consolidation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    memories_processed INTEGER DEFAULT 0,
    memories_created INTEGER DEFAULT 0,
    memories_archived INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory clusters (without vector for now)
DROP TABLE IF EXISTS memory_clusters CASCADE;
CREATE TABLE memory_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    cluster_name VARCHAR(255) NOT NULL,
    cluster_summary TEXT,
    -- centroid_embedding will be added after pgvector
    member_count INTEGER DEFAULT 0,
    coherence_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory cluster members
DROP TABLE IF EXISTS memory_cluster_members CASCADE;
CREATE TABLE memory_cluster_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_id UUID REFERENCES memory_clusters(id) ON DELETE CASCADE,
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    distance_to_centroid DECIMAL(5,4),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cluster_id, memory_id)
);

-- Context snapshots
DROP TABLE IF EXISTS context_snapshots CASCADE;
CREATE TABLE context_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    agent_id UUID REFERENCES agents(id),
    snapshot_type VARCHAR(50),
    memory_blocks JSONB NOT NULL,
    active_memories UUID[],
    compressed_context TEXT,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reflection logs
DROP TABLE IF EXISTS reflection_logs CASCADE;
CREATE TABLE reflection_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    session_id UUID REFERENCES sessions(id),
    task_description TEXT,
    trajectory_summary TEXT,
    success BOOLEAN,
    feedback TEXT,
    reflection TEXT NOT NULL,
    lessons_extracted TEXT[],
    improvement_actions JSONB,
    applied_to_memories UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- STEP 6: Fix financial tables
-- =============================================================================

-- Fix fin_transactions (partitioning issue)
DROP TABLE IF EXISTS fin_transactions CASCADE;
DROP TABLE IF EXISTS fin_transactions_2025 CASCADE;
DROP TABLE IF EXISTS fin_transactions_2026 CASCADE;

CREATE TABLE fin_transactions (
    id UUID NOT NULL,
    account_id UUID REFERENCES fin_accounts(id),
    transaction_date DATE NOT NULL,
    posted_date DATE,
    amount DECIMAL(15,2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category_id UUID REFERENCES fin_categories(id),
    subcategory VARCHAR(100),
    merchant VARCHAR(200),
    merchant_normalized VARCHAR(200),
    description TEXT,
    notes TEXT,
    is_recurring BOOLEAN DEFAULT false,
    recurring_id UUID,
    is_split BOOLEAN DEFAULT false,
    parent_transaction_id UUID,
    tags TEXT[],
    receipt_path TEXT,
    location JSONB,
    is_reviewed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, transaction_date)
) PARTITION BY RANGE (transaction_date);

-- Create partitions
CREATE TABLE fin_transactions_2025 PARTITION OF fin_transactions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE fin_transactions_2026 PARTITION OF fin_transactions
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE fin_transactions_2027 PARTITION OF fin_transactions
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE INDEX idx_fin_transactions_date ON fin_transactions(transaction_date DESC);
CREATE INDEX idx_fin_transactions_account ON fin_transactions(account_id, transaction_date DESC);
CREATE INDEX idx_fin_transactions_category ON fin_transactions(category_id);

-- Fix fin_debt_payments
DROP TABLE IF EXISTS fin_debt_payments CASCADE;
CREATE TABLE fin_debt_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    debt_id UUID REFERENCES fin_debts(id),
    payment_date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    principal_amount DECIMAL(12,2),
    interest_amount DECIMAL(12,2),
    extra_payment DECIMAL(12,2) DEFAULT 0,
    payment_method VARCHAR(50),
    confirmation_number VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- STEP 7: Fix other tables with UUID/INTEGER conflicts
-- =============================================================================

-- Fix tasks table
DROP TABLE IF EXISTS tasks CASCADE;
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    project_id UUID REFERENCES projects(id),
    area_id UUID REFERENCES areas(id),
    parent_task_id UUID,
    status VARCHAR(20) DEFAULT 'todo',
    priority VARCHAR(20) DEFAULT 'medium',
    energy_required VARCHAR(20),
    context_tags TEXT[],
    due_date DATE,
    due_time TIME,
    start_date DATE,
    completed_at TIMESTAMPTZ,
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    delegated_to VARCHAR(100),
    recurring_id UUID,
    source VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tasks ADD CONSTRAINT tasks_parent_fkey 
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id);

CREATE INDEX idx_tasks_status ON tasks(status, priority);
CREATE INDEX idx_tasks_due ON tasks(due_date) WHERE status NOT IN ('done', 'cancelled');
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_context ON tasks USING GIN(context_tags);

-- Task dependencies
DROP TABLE IF EXISTS task_dependencies CASCADE;
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) DEFAULT 'finish_to_start',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(task_id, depends_on_task_id)
);

-- Fix goals table
DROP TABLE IF EXISTS goals CASCADE;
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    target_value DECIMAL(15,2),
    current_value DECIMAL(15,2) DEFAULT 0,
    unit VARCHAR(50),
    measurement_method TEXT,
    start_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 50,
    parent_goal_id UUID,
    area_id UUID REFERENCES areas(id),
    why TEXT,
    obstacles TEXT[],
    strategies TEXT[],
    accountability VARCHAR(100),
    review_frequency VARCHAR(20),
    last_reviewed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE goals ADD CONSTRAINT goals_parent_fkey 
    FOREIGN KEY (parent_goal_id) REFERENCES goals(id);

CREATE INDEX idx_goals_status ON goals(status, priority);

-- Goal progress
DROP TABLE IF EXISTS goal_progress CASCADE;
CREATE TABLE goal_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(id),
    recorded_date DATE NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    notes TEXT,
    evidence TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fix habits table
DROP TABLE IF EXISTS habits CASCADE;
CREATE TABLE habits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    habit_type VARCHAR(20) DEFAULT 'build',
    frequency VARCHAR(20) NOT NULL,
    frequency_config JSONB,
    target_count INTEGER DEFAULT 1,
    time_of_day VARCHAR(20),
    reminder_time TIME,
    cue TEXT,
    reward TEXT,
    area_id UUID REFERENCES areas(id),
    streak_current INTEGER DEFAULT 0,
    streak_longest INTEGER DEFAULT 0,
    streak_started_at DATE,
    total_completions INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Habit completions
DROP TABLE IF EXISTS habit_completions CASCADE;
CREATE TABLE habit_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id UUID REFERENCES habits(id),
    completion_date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    quality_rating INTEGER CHECK (quality_rating BETWEEN 1 AND 5),
    notes TEXT,
    skipped BOOLEAN DEFAULT false,
    skip_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(habit_id, completion_date)
);

-- Health goals
DROP TABLE IF EXISTS health_goals CASCADE;
CREATE TABLE health_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(id),
    health_category VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    baseline_value DECIMAL(10,2),
    target_value DECIMAL(10,2) NOT NULL,
    current_value DECIMAL(10,2),
    unit VARCHAR(50),
    tracking_frequency VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Focus sessions
DROP TABLE IF EXISTS focus_sessions CASCADE;
CREATE TABLE focus_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id),
    project_id UUID REFERENCES projects(id),
    session_type VARCHAR(20) NOT NULL,
    planned_duration_minutes INTEGER NOT NULL,
    actual_duration_minutes INTEGER,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    completed BOOLEAN DEFAULT false,
    interruptions INTEGER DEFAULT 0,
    interruption_notes TEXT,
    focus_score INTEGER CHECK (focus_score BETWEEN 1 AND 10),
    energy_before INTEGER,
    energy_after INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- STEP 8: Recreate important views
-- =============================================================================

-- Drop existing views that have errors
DROP VIEW IF EXISTS v_budget_status CASCADE;
DROP VIEW IF EXISTS v_debt_progress CASCADE;
DROP VIEW IF EXISTS v_agent_leaderboard CASCADE;
DROP VIEW IF EXISTS v_health_trends CASCADE;
DROP VIEW IF EXISTS v_financial_runway CASCADE;

-- Budget status view
CREATE VIEW v_budget_status AS
SELECT 
    bi.id,
    b.name AS budget_name,
    fc.name AS category_name,
    bi.budgeted_amount,
    COALESCE(SUM(ft.amount), 0) AS spent,
    bi.budgeted_amount - COALESCE(SUM(ft.amount), 0) AS remaining,
    ROUND((COALESCE(SUM(ft.amount), 0) / NULLIF(bi.budgeted_amount, 0) * 100)::numeric, 1) AS percent_used,
    bi.alert_threshold * 100 AS alert_threshold_percent,
    CASE 
        WHEN COALESCE(SUM(ft.amount), 0) >= bi.budgeted_amount THEN 'over_budget'
        WHEN COALESCE(SUM(ft.amount), 0) >= bi.budgeted_amount * bi.alert_threshold THEN 'warning'
        ELSE 'on_track'
    END AS status
FROM fin_budget_items bi
JOIN fin_budgets b ON b.id = bi.budget_id
JOIN fin_categories fc ON fc.id = bi.category_id
LEFT JOIN fin_transactions ft ON ft.category_id = bi.category_id 
    AND ft.transaction_type = 'expense'
    AND DATE_TRUNC('month', ft.transaction_date) = DATE_TRUNC('month', CURRENT_DATE)
WHERE b.is_active = true
GROUP BY bi.id, b.name, fc.name, bi.budgeted_amount, bi.alert_threshold;

-- Debt progress view
CREATE VIEW v_debt_progress AS
SELECT 
    d.id,
    d.name,
    d.creditor,
    d.original_amount,
    d.current_balance,
    d.original_amount - d.current_balance AS total_paid,
    ROUND(((d.original_amount - d.current_balance) / d.original_amount * 100)::numeric, 1) AS percent_paid,
    d.minimum_payment,
    d.interest_rate,
    d.target_payoff_date,
    COUNT(dp.id) AS payments_made,
    COALESCE(SUM(dp.amount), 0) AS total_payments,
    MAX(dp.payment_date) AS last_payment_date
FROM fin_debts d
LEFT JOIN fin_debt_payments dp ON dp.debt_id = d.id
WHERE d.is_active = true
GROUP BY d.id, d.name, d.creditor, d.original_amount, d.current_balance, 
         d.minimum_payment, d.interest_rate, d.target_payoff_date;

-- Agent leaderboard view
CREATE VIEW v_agent_leaderboard AS
SELECT 
    a.name,
    a.display_name,
    a.domain,
    COALESCE(SUM(ap.total_requests), 0) AS total_requests,
    ROUND(COALESCE(AVG(ap.avg_user_rating), 0)::numeric, 2) AS avg_rating,
    COALESCE(SUM(ap.total_cost_usd), 0) AS total_cost,
    CASE 
        WHEN SUM(ap.total_requests) > 0 
        THEN ROUND((SUM(ap.successful_requests)::numeric / SUM(ap.total_requests) * 100), 1)
        ELSE 0 
    END AS success_rate,
    ROUND(COALESCE(AVG(ap.avg_latency_ms), 0)::numeric, 0) AS avg_latency_ms
FROM agents a
LEFT JOIN agent_performance ap ON a.id = ap.agent_id
    AND ap.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY a.id, a.name, a.display_name, a.domain
ORDER BY total_requests DESC;

-- Health trends view
CREATE VIEW v_health_trends AS
SELECT 
    date,
    weight_lbs,
    AVG(weight_lbs) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS weight_7day_avg,
    sleep_hours,
    AVG(sleep_hours) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS sleep_7day_avg,
    energy_avg,
    AVG(energy_avg) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS energy_7day_avg,
    steps,
    AVG(steps) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS steps_7day_avg,
    hrv_ms,
    resting_heart_rate
FROM health_daily
ORDER BY date DESC
LIMIT 90;

-- =============================================================================
-- STEP 9: Recreate triggers
-- =============================================================================

-- Recreate habit streak trigger
DROP TRIGGER IF EXISTS trigger_update_habit_streak ON habit_completions;

CREATE OR REPLACE FUNCTION update_habit_streak()
RETURNS TRIGGER AS $$
DECLARE
    last_completion DATE;
    current_streak INTEGER;
BEGIN
    SELECT completion_date INTO last_completion
    FROM habit_completions
    WHERE habit_id = NEW.habit_id
    AND completion_date < NEW.completion_date
    ORDER BY completion_date DESC
    LIMIT 1;
    
    SELECT streak_current INTO current_streak
    FROM habits
    WHERE id = NEW.habit_id;
    
    IF last_completion IS NULL OR NEW.completion_date - last_completion > 1 THEN
        UPDATE habits 
        SET streak_current = 1,
            streak_started_at = NEW.completion_date,
            total_completions = total_completions + 1
        WHERE id = NEW.habit_id;
    ELSE
        UPDATE habits 
        SET streak_current = streak_current + 1,
            streak_longest = GREATEST(streak_longest, streak_current + 1),
            total_completions = total_completions + 1
        WHERE id = NEW.habit_id;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_habit_streak
    AFTER INSERT ON habit_completions
    FOR EACH ROW EXECUTE FUNCTION update_habit_streak();

-- Audit trigger for financial transactions
DROP TRIGGER IF EXISTS audit_fin_transactions ON fin_transactions;

CREATE TRIGGER audit_fin_transactions 
    AFTER INSERT OR UPDATE OR DELETE ON fin_transactions
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

-- =============================================================================
-- STEP 10: Insert default agents
-- =============================================================================

INSERT INTO agents (name, display_name, agent_type, domain, role, system_prompt) VALUES
('router', 'Router Agent', 'orchestrator', 'system', 'Routes queries to appropriate agents', 'You are the NEXUS Router. Classify queries and route to the best agent.'),
('wealth', 'Wealth Agent', 'domain', 'wealth', 'Tracks opportunities and wealth building', 'You help Philip build wealth through opportunity detection and passive income tracking.'),
('finance', 'Finance Agent', 'domain', 'finance', 'Manages all financial tracking', 'You manage Philip''s finances: expenses, budgets, debt payoff, and savings.'),
('learning', 'Learning Agent', 'domain', 'learning', 'Tracks learning and skill development', 'You help Philip learn programming and track his skill development.'),
('health', 'Health Agent', 'domain', 'health', 'Tracks health metrics', 'You track Philip''s health: sleep, exercise, nutrition, and conditions.'),
('planning', 'Planning Agent', 'domain', 'planning', 'Manages tasks and goals', 'You help Philip plan: tasks, goals, habits, and time management.'),
('memory', 'Memory Agent', 'domain', 'system', 'Manages long-term memory', 'You manage NEXUS memory: storing, retrieving, and consolidating memories.'),
('system', 'System Agent', 'domain', 'system', 'Monitors NEXUS health', 'You monitor NEXUS system health and optimize performance.');

-- =============================================================================
-- DONE! Verify the fix
-- =============================================================================

-- Count tables
SELECT 'Total tables: ' || COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
