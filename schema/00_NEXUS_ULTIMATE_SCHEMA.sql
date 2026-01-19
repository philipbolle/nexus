-- ╔═══════════════════════════════════════════════════════════════════════════════╗
-- ║                    NEXUS ULTIMATE DATABASE SCHEMA v4.0                        ║
-- ║                                                                               ║
-- ║  The most sophisticated personal AI operating system database ever designed   ║
-- ║  100+ tables | Self-evolving | Cost-optimized | Wealth-focused               ║
-- ║                                                                               ║
-- ║  Author: Philip's NEXUS System                                               ║
-- ║  Created: January 2026                                                        ║
-- ║  Target: PostgreSQL 16 with pgvector                                         ║
-- ╚═══════════════════════════════════════════════════════════════════════════════╝

-- =============================================================================
-- SECTION 0: EXTENSIONS & CONFIGURATION
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Encryption
CREATE EXTENSION IF NOT EXISTS "vector";         -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Trigram for fuzzy search
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN indexes for JSONB

-- Set timezone
SET timezone = 'America/Chicago';

-- =============================================================================
-- SECTION 1: CORE SYSTEM TABLES (10 tables)
-- =============================================================================

-- 1.1 System Configuration
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_secret BOOLEAN DEFAULT false,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.2 System Metrics (Time-series)
CREATE TABLE system_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    cpu_percent DECIMAL(5,2),
    memory_used_mb INTEGER,
    memory_total_mb INTEGER,
    memory_percent DECIMAL(5,2),
    disk_used_gb DECIMAL(8,2),
    disk_total_gb DECIMAL(8,2),
    disk_percent DECIMAL(5,2),
    docker_containers_running INTEGER,
    docker_containers_total INTEGER,
    api_requests_last_hour INTEGER,
    api_requests_last_day INTEGER,
    active_agents INTEGER,
    cache_hit_rate DECIMAL(5,2),
    avg_response_ms DECIMAL(10,2)
) PARTITION BY RANGE (timestamp);

-- Create partitions for metrics (monthly)
CREATE TABLE system_metrics_2026_01 PARTITION OF system_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE system_metrics_2026_02 PARTITION OF system_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- 1.3 Error Logs
CREATE TABLE error_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    service VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'debug', 'info', 'warning', 'error', 'critical'
    error_type VARCHAR(100),
    error_code VARCHAR(50),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    related_agent_id UUID,
    related_session_id UUID
);

CREATE INDEX idx_error_logs_timestamp ON error_logs(timestamp DESC);
CREATE INDEX idx_error_logs_severity ON error_logs(severity);
CREATE INDEX idx_error_logs_unresolved ON error_logs(resolved) WHERE resolved = false;

-- 1.4 Audit Trail (Event Sourcing Foundation)
CREATE TABLE audit_trail (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_type VARCHAR(50) NOT NULL, -- 'create', 'update', 'delete', 'access', 'execute'
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    table_name VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    changes JSONB, -- Diff between old and new
    performed_by VARCHAR(100), -- 'user', 'agent:name', 'system'
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_audit_timestamp ON audit_trail(timestamp DESC);
CREATE INDEX idx_audit_entity ON audit_trail(entity_type, entity_id);
CREATE INDEX idx_audit_action ON audit_trail(action_type);

-- 1.5 Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel VARCHAR(50) NOT NULL, -- 'ntfy', 'email', 'sms', 'in_app'
    topic VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    tags TEXT[],
    action_url TEXT,
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    source_agent_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_pending ON notifications(scheduled_for) 
    WHERE sent_at IS NULL AND scheduled_for IS NOT NULL;

-- 1.6 User Preferences
CREATE TABLE preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    validation_schema JSONB, -- JSON Schema for validation
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category, key)
);

-- 1.7 Feature Flags
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT false,
    rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage BETWEEN 0 AND 100),
    conditions JSONB, -- Complex conditions for enabling
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.8 Scheduled Jobs
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    cron_expression VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- 'python', 'sql', 'api_call', 'agent_task'
    job_config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(20),
    last_run_duration_ms INTEGER,
    next_run_at TIMESTAMPTZ,
    failure_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.9 Job Execution History
CREATE TABLE job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES scheduled_jobs(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failed', 'timeout'
    duration_ms INTEGER,
    output TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- 1.10 Backup Logs
CREATE TABLE backup_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    backup_type VARCHAR(50) NOT NULL, -- 'full', 'incremental', 'database', 'files'
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    file_path TEXT,
    file_size_bytes BIGINT,
    compression_ratio DECIMAL(4,2),
    checksum VARCHAR(64),
    duration_seconds INTEGER,
    tables_included TEXT[],
    rows_backed_up BIGINT,
    error_message TEXT,
    verified_at TIMESTAMPTZ,
    verification_status VARCHAR(20)
);

-- =============================================================================
-- SECTION 2: AI COST OPTIMIZATION TABLES (12 tables)
-- =============================================================================

-- 2.1 AI Providers Configuration
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL, -- 'openai', 'anthropic', 'deepseek', 'groq', 'ollama'
    display_name VARCHAR(100) NOT NULL,
    api_base_url TEXT,
    is_local BOOLEAN DEFAULT false,
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 50, -- Lower = higher priority
    rate_limit_rpm INTEGER, -- Requests per minute
    rate_limit_tpd INTEGER, -- Tokens per day
    monthly_budget_usd DECIMAL(10,2),
    current_month_spend_usd DECIMAL(10,2) DEFAULT 0,
    auth_type VARCHAR(50), -- 'api_key', 'oauth', 'none'
    capabilities TEXT[], -- ['chat', 'embedding', 'vision', 'tools', 'streaming']
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.2 AI Models Configuration
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES ai_providers(id),
    model_id VARCHAR(100) NOT NULL, -- 'gpt-4o', 'claude-3-opus', etc.
    display_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'chat', 'embedding', 'completion'
    context_window INTEGER NOT NULL,
    max_output_tokens INTEGER,
    input_cost_per_mtok DECIMAL(10,6), -- Cost per million tokens
    output_cost_per_mtok DECIMAL(10,6),
    cached_input_cost_per_mtok DECIMAL(10,6), -- With prompt caching
    supports_tools BOOLEAN DEFAULT false,
    supports_vision BOOLEAN DEFAULT false,
    supports_streaming BOOLEAN DEFAULT true,
    supports_caching BOOLEAN DEFAULT false,
    cache_ttl_seconds INTEGER, -- How long prompts stay cached
    quality_score DECIMAL(3,2), -- 0-1, self-assessed quality
    speed_score DECIMAL(3,2), -- 0-1, tokens per second normalized
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider_id, model_id)
);

-- 2.3 API Usage Tracking
CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    provider_id UUID REFERENCES ai_providers(id),
    model_id UUID REFERENCES ai_models(id),
    endpoint VARCHAR(100),
    request_type VARCHAR(50), -- 'chat', 'embedding', 'completion'
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    latency_ms INTEGER,
    time_to_first_token_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_code VARCHAR(50),
    error_message TEXT,
    cache_hit BOOLEAN DEFAULT false,
    agent_id UUID,
    session_id UUID,
    query_hash VARCHAR(64), -- For deduplication
    request_metadata JSONB DEFAULT '{}'
) PARTITION BY RANGE (timestamp);

-- Partitions for API usage
CREATE TABLE api_usage_2026_01 PARTITION OF api_usage
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp DESC);
CREATE INDEX idx_api_usage_provider ON api_usage(provider_id, timestamp DESC);
CREATE INDEX idx_api_usage_agent ON api_usage(agent_id, timestamp DESC);

-- 2.4 Semantic Cache (60-70% cost reduction)
CREATE TABLE semantic_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_embedding vector(384), -- all-MiniLM-L6-v2 dimension
    response_text TEXT NOT NULL,
    response_metadata JSONB,
    model_used VARCHAR(100),
    tokens_saved INTEGER DEFAULT 0,
    cost_saved_usd DECIMAL(10,6) DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    confidence_score DECIMAL(3,2), -- How confident we are in this cache
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_semantic_cache_embedding ON semantic_cache 
    USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_semantic_cache_hash ON semantic_cache(query_hash);
CREATE INDEX idx_semantic_cache_expires ON semantic_cache(expires_at) WHERE expires_at IS NOT NULL;

-- 2.5 Embedding Cache
CREATE TABLE embedding_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    content_preview TEXT, -- First 500 chars
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    embedding_model VARCHAR(100) NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 1
);

CREATE INDEX idx_embedding_cache_hash ON embedding_cache(content_hash);

-- 2.6 Model Cascade Configuration
CREATE TABLE model_cascades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL, -- 'general', 'coding', 'analysis', 'creative'
    cascade_order UUID[] NOT NULL, -- Array of model_ids in order
    complexity_thresholds JSONB, -- When to escalate to next model
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.7 Model Cascade Decisions
CREATE TABLE cascade_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cascade_id UUID REFERENCES model_cascades(id),
    session_id UUID,
    query_preview TEXT,
    complexity_score DECIMAL(3,2),
    models_tried UUID[], -- Which models were tried
    final_model_id UUID REFERENCES ai_models(id),
    escalation_reasons TEXT[],
    total_cost_usd DECIMAL(10,6),
    cost_if_premium_only DECIMAL(10,6), -- What it would have cost
    savings_usd DECIMAL(10,6) GENERATED ALWAYS AS (cost_if_premium_only - total_cost_usd) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.8 Prompt Templates (For Caching Optimization)
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    template_text TEXT NOT NULL,
    variables TEXT[], -- Placeholder variables
    static_portion_length INTEGER, -- Chars that don't change (for caching)
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    avg_tokens INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.9 Prompt Template Versions
CREATE TABLE prompt_template_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES prompt_templates(id),
    version INTEGER NOT NULL,
    template_text TEXT NOT NULL,
    change_notes TEXT,
    performance_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(template_id, version)
);

-- 2.10 Batch Jobs (50% Cost Reduction)
CREATE TABLE batch_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    provider_id UUID REFERENCES ai_providers(id),
    model_id UUID REFERENCES ai_models(id),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    total_requests INTEGER DEFAULT 0,
    completed_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    input_file_path TEXT,
    output_file_path TEXT,
    estimated_cost_usd DECIMAL(10,4),
    actual_cost_usd DECIMAL(10,4),
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.11 Batch Job Items
CREATE TABLE batch_job_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID REFERENCES batch_jobs(id),
    custom_id VARCHAR(100),
    request_body JSONB NOT NULL,
    response_body JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.12 Cost Alerts
CREATE TABLE cost_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL, -- 'daily_limit', 'monthly_limit', 'spike'
    threshold_usd DECIMAL(10,2) NOT NULL,
    current_value_usd DECIMAL(10,2),
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    notification_sent BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- SECTION 3: AGENT SYSTEM TABLES (15 tables)
-- =============================================================================

-- 3.1 Agents Definition
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL, -- 'domain', 'orchestrator', 'specialist'
    domain VARCHAR(100), -- 'finance', 'health', 'wealth', etc.
    role TEXT NOT NULL,
    goal TEXT,
    backstory TEXT,
    system_prompt TEXT NOT NULL,
    model_preference UUID REFERENCES ai_models(id),
    fallback_models UUID[],
    capabilities TEXT[],
    tools TEXT[], -- Tool names this agent can use
    supervisor_id UUID REFERENCES agents(id),
    is_active BOOLEAN DEFAULT true,
    allow_delegation BOOLEAN DEFAULT true,
    max_iterations INTEGER DEFAULT 10,
    temperature DECIMAL(2,1) DEFAULT 0.7,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.2 Agent Tools
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    tool_type VARCHAR(50) NOT NULL, -- 'database', 'api', 'file', 'calculation'
    input_schema JSONB NOT NULL, -- JSON Schema
    output_schema JSONB,
    implementation_type VARCHAR(50) NOT NULL, -- 'python_function', 'api_call', 'sql'
    implementation_config JSONB NOT NULL,
    requires_confirmation BOOLEAN DEFAULT false, -- Human-in-the-loop
    is_enabled BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    avg_execution_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.3 Agent-Tool Assignments
CREATE TABLE agent_tool_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    tool_id UUID REFERENCES agent_tools(id),
    is_enabled BOOLEAN DEFAULT true,
    custom_description TEXT, -- Override for this agent
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, tool_id)
);

-- 3.4 Sessions (Conversations)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_type VARCHAR(50) DEFAULT 'chat', -- 'chat', 'task', 'automation'
    title VARCHAR(255),
    summary TEXT,
    primary_agent_id UUID REFERENCES agents(id),
    agents_involved UUID[],
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'archived'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_last_message ON sessions(last_message_at DESC);

-- 3.5 Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    agent_id UUID REFERENCES agents(id),
    parent_message_id UUID REFERENCES messages(id),
    tool_calls JSONB, -- If assistant made tool calls
    tool_results JSONB, -- If this is a tool response
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10,6),
    model_used VARCHAR(100),
    latency_ms INTEGER,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);

-- 3.6 Agent Handoffs
CREATE TABLE agent_handoffs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    from_agent_id UUID REFERENCES agents(id),
    to_agent_id UUID REFERENCES agents(id),
    reason TEXT NOT NULL,
    context_summary TEXT,
    context_tokens INTEGER,
    handoff_type VARCHAR(50), -- 'delegation', 'escalation', 'collaboration'
    success BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.7 Agent Performance (Daily Aggregates)
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
    tools_used JSONB, -- {tool_name: count}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, date)
);

-- 3.8 Agent Suggestions (Proactive)
CREATE TABLE agent_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    suggestion_type VARCHAR(50) NOT NULL, -- 'optimization', 'alert', 'reminder', 'opportunity'
    category VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT,
    supporting_data JSONB,
    priority VARCHAR(20) DEFAULT 'medium',
    urgency_score DECIMAL(3,2), -- 0-1
    impact_score DECIMAL(3,2), -- 0-1
    confidence_score DECIMAL(3,2), -- 0-1
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'implemented'
    user_response VARCHAR(20),
    user_feedback TEXT,
    implemented_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_suggestions_pending ON agent_suggestions(status, created_at DESC) 
    WHERE status = 'pending';

-- 3.9 Agent Collaborations
CREATE TABLE agent_collaborations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    initiator_agent_id UUID REFERENCES agents(id),
    collaborators UUID[] NOT NULL,
    task_description TEXT NOT NULL,
    collaboration_type VARCHAR(50), -- 'debate', 'consensus', 'divide_conquer'
    messages_exchanged INTEGER DEFAULT 0,
    outcome VARCHAR(50),
    outcome_summary TEXT,
    quality_score DECIMAL(3,2),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.10 Privacy Shield Logs
CREATE TABLE privacy_shield_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID,
    original_query_hash VARCHAR(64),
    secrets_detected JSONB, -- [{type, placeholder, position}]
    secrets_count INTEGER DEFAULT 0,
    redacted_query TEXT,
    external_provider VARCHAR(50),
    secrets_reinjected BOOLEAN DEFAULT false,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.11 Tool Executions
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    message_id UUID REFERENCES messages(id),
    agent_id UUID REFERENCES agents(id),
    tool_id UUID REFERENCES agent_tools(id),
    input_params JSONB NOT NULL,
    output_result JSONB,
    status VARCHAR(20) NOT NULL, -- 'success', 'error', 'timeout', 'cancelled'
    error_message TEXT,
    execution_time_ms INTEGER,
    required_confirmation BOOLEAN DEFAULT false,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.12 Agent Events (Event Sourcing)
CREATE TABLE agent_events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    aggregate_id UUID NOT NULL, -- Session/Task ID
    aggregate_type VARCHAR(50) NOT NULL, -- 'session', 'task', 'workflow'
    event_type VARCHAR(100) NOT NULL, -- 'QueryReceived', 'ToolInvoked', 'ResponseGenerated'
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INTEGER NOT NULL,
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, version)
);

CREATE INDEX idx_agent_events_aggregate ON agent_events(aggregate_id, version);
CREATE INDEX idx_agent_events_type ON agent_events(event_type, created_at DESC);

-- 3.13 Agent Versions (For A/B Testing)
CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    version INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    model_preference UUID REFERENCES ai_models(id),
    temperature DECIMAL(2,1),
    config_changes JSONB,
    change_notes TEXT,
    is_active BOOLEAN DEFAULT false,
    performance_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, version)
);

-- 3.14 Agent Experiments (A/B Testing)
CREATE TABLE agent_experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_id UUID REFERENCES agents(id),
    hypothesis TEXT,
    control_version_id UUID REFERENCES agent_versions(id),
    treatment_version_id UUID REFERENCES agent_versions(id),
    traffic_split JSONB DEFAULT '{"control": 0.5, "treatment": 0.5}',
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'running', 'completed', 'cancelled'
    success_metrics TEXT[],
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    min_sample_size INTEGER,
    current_sample_size INTEGER DEFAULT 0,
    results JSONB,
    winner VARCHAR(20), -- 'control', 'treatment', 'inconclusive'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.15 Experiment Observations
CREATE TABLE experiment_observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID REFERENCES agent_experiments(id),
    variant VARCHAR(20) NOT NULL, -- 'control', 'treatment'
    session_id UUID REFERENCES sessions(id),
    metrics JSONB NOT NULL, -- {metric_name: value}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 4: MEMORY SYSTEM TABLES (12 tables)
-- Inspired by Letta/MemGPT architecture
-- =============================================================================

-- 4.1 Memory Blocks (In-Context Memory)
CREATE TABLE memory_blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    block_label VARCHAR(100) NOT NULL, -- 'human', 'persona', 'task', 'context'
    content TEXT NOT NULL,
    char_limit INTEGER DEFAULT 2000,
    current_length INTEGER GENERATED ALWAYS AS (length(content)) STORED,
    version INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 50, -- Lower = more important
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, block_label)
);

-- 4.2 Long-Term Memories
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    memory_type VARCHAR(50) NOT NULL, -- 'semantic', 'episodic', 'procedural'
    content TEXT NOT NULL,
    content_embedding vector(1536),
    importance_score DECIMAL(3,2) DEFAULT 0.5,
    strength_score DECIMAL(3,2) DEFAULT 1.0,
    emotional_valence DECIMAL(3,2), -- -1 to 1
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    source_type VARCHAR(50), -- 'conversation', 'document', 'reflection', 'user_input'
    source_id UUID,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memories_embedding ON memories 
    USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memories_agent ON memories(agent_id, memory_type);
CREATE INDEX idx_memories_importance ON memories(importance_score DESC);

-- 4.3 Semantic Memories (Facts & Knowledge)
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

-- 4.4 Episodic Memories (Experiences)
CREATE TABLE episodic_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id),
    event_summary TEXT NOT NULL,
    participants TEXT[],
    outcome VARCHAR(100),
    outcome_quality DECIMAL(3,2), -- Success measure
    lessons_learned TEXT[],
    reusable_patterns JSONB,
    occurred_at TIMESTAMPTZ NOT NULL
);

-- 4.5 Procedural Memories (Skills & How-To)
CREATE TABLE procedural_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    skill_name VARCHAR(255) NOT NULL,
    trigger_conditions JSONB, -- When to apply
    steps JSONB NOT NULL, -- Ordered steps
    success_criteria TEXT,
    failure_modes TEXT[],
    performance_history JSONB, -- Track success rate
    last_used_at TIMESTAMPTZ
);

-- 4.6 Memory Relations (Knowledge Graph)
CREATE TABLE memory_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    target_memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL, -- 'supports', 'contradicts', 'extends', 'caused_by'
    strength DECIMAL(3,2) DEFAULT 0.5,
    bidirectional BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.7 Memory Access Log
CREATE TABLE memory_access_log (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID REFERENCES memories(id),
    agent_id UUID REFERENCES agents(id),
    session_id UUID REFERENCES sessions(id),
    access_type VARCHAR(50) NOT NULL, -- 'retrieve', 'update', 'create', 'reference'
    relevance_score DECIMAL(3,2),
    was_useful BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.8 Memory Consolidation Jobs
CREATE TABLE memory_consolidation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    job_type VARCHAR(50) NOT NULL, -- 'summarize', 'cluster', 'prune', 'decay'
    status VARCHAR(20) DEFAULT 'pending',
    memories_processed INTEGER DEFAULT 0,
    memories_created INTEGER DEFAULT 0,
    memories_archived INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.9 Memory Clusters
CREATE TABLE memory_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id),
    cluster_name VARCHAR(255) NOT NULL,
    cluster_summary TEXT,
    centroid_embedding vector(1536),
    member_count INTEGER DEFAULT 0,
    coherence_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.10 Memory Cluster Members
CREATE TABLE memory_cluster_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_id UUID REFERENCES memory_clusters(id) ON DELETE CASCADE,
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    distance_to_centroid DECIMAL(5,4),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(cluster_id, memory_id)
);

-- 4.11 Context Snapshots
CREATE TABLE context_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    agent_id UUID REFERENCES agents(id),
    snapshot_type VARCHAR(50), -- 'checkpoint', 'handoff', 'archive'
    memory_blocks JSONB NOT NULL,
    active_memories UUID[],
    compressed_context TEXT,
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.12 Reflection Logs (Self-Improvement)
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
-- SECTION 5: RAG PIPELINE TABLES (10 tables)
-- =============================================================================

-- 5.1 Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'upload', 'web', 'email', 'note', 'conversation'
    source_url TEXT,
    file_path TEXT,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64) UNIQUE,
    raw_content TEXT,
    processed_content TEXT,
    language VARCHAR(10) DEFAULT 'en',
    word_count INTEGER,
    page_count INTEGER,
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    para_category VARCHAR(50), -- 'project', 'area', 'resource', 'archive'
    para_parent_id UUID,
    processing_status VARCHAR(20) DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_para ON documents(para_category);

-- 5.2 Document Chunks
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    token_count INTEGER,
    char_count INTEGER GENERATED ALWAYS AS (length(content)) STORED,
    start_position INTEGER,
    end_position INTEGER,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    embedding_model VARCHAR(100),
    embedding_created_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_chunks_embedding ON document_chunks 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);

-- 5.3 Chunking Configurations
CREATE TABLE chunking_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    strategy VARCHAR(50) NOT NULL, -- 'fixed', 'semantic', 'recursive', 'sentence'
    chunk_size INTEGER NOT NULL,
    chunk_overlap INTEGER NOT NULL,
    separators TEXT[],
    is_default BOOLEAN DEFAULT false,
    performance_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.4 Retrieval Queries
CREATE TABLE retrieval_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    agent_id UUID REFERENCES agents(id),
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    query_type VARCHAR(50), -- 'semantic', 'keyword', 'hybrid'
    filters JSONB,
    top_k INTEGER DEFAULT 5,
    retrieved_chunks UUID[],
    retrieval_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.5 Retrieval Results
CREATE TABLE retrieval_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES retrieval_queries(id),
    chunk_id UUID REFERENCES document_chunks(id),
    rank INTEGER NOT NULL,
    similarity_score DECIMAL(5,4),
    bm25_score DECIMAL(8,4),
    hybrid_score DECIMAL(5,4),
    rerank_score DECIMAL(5,4),
    was_used_in_response BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.6 Retrieval Feedback
CREATE TABLE retrieval_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES retrieval_queries(id),
    chunk_id UUID REFERENCES document_chunks(id),
    feedback_type VARCHAR(50) NOT NULL, -- 'relevant', 'irrelevant', 'partially_relevant'
    feedback_source VARCHAR(50), -- 'user', 'llm_judge', 'implicit'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.7 Hybrid Search Configuration
CREATE TABLE hybrid_search_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    semantic_weight DECIMAL(3,2) DEFAULT 0.65,
    bm25_weight DECIMAL(3,2) DEFAULT 0.35,
    reranker_model VARCHAR(100),
    reranker_enabled BOOLEAN DEFAULT true,
    initial_candidates INTEGER DEFAULT 50,
    final_results INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    ndcg_score DECIMAL(4,3), -- Performance metric
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.8 Context Windows
CREATE TABLE context_windows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    agent_id UUID REFERENCES agents(id),
    window_content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    max_tokens INTEGER NOT NULL,
    utilization_percent DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN max_tokens > 0 THEN (token_count::DECIMAL / max_tokens * 100) ELSE 0 END
    ) STORED,
    compression_applied BOOLEAN DEFAULT false,
    original_token_count INTEGER,
    compression_ratio DECIMAL(4,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.9 Context Compression Logs
CREATE TABLE context_compression_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_window_id UUID REFERENCES context_windows(id),
    compression_method VARCHAR(50), -- 'LLMLingua', 'summarization', 'selective'
    original_tokens INTEGER NOT NULL,
    compressed_tokens INTEGER NOT NULL,
    compression_ratio DECIMAL(4,2) GENERATED ALWAYS AS (
        CASE WHEN original_tokens > 0 
            THEN (1 - compressed_tokens::DECIMAL / original_tokens) 
            ELSE 0 END
    ) STORED,
    quality_preserved_score DECIMAL(3,2),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5.10 Knowledge Graph Nodes
CREATE TABLE knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL, -- 'entity', 'concept', 'event', 'document'
    name VARCHAR(500) NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),
    source_documents UUID[],
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_nodes_type ON knowledge_nodes(node_type);
CREATE INDEX idx_knowledge_nodes_embedding ON knowledge_nodes 
    USING hnsw (embedding vector_cosine_ops);

-- 5.11 Knowledge Graph Edges
CREATE TABLE knowledge_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight DECIMAL(3,2) DEFAULT 1.0,
    evidence_chunks UUID[],
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_edges_source ON knowledge_edges(source_node_id);
CREATE INDEX idx_knowledge_edges_relation ON knowledge_edges(relation_type);

-- =============================================================================
-- SECTION 6: PARA KNOWLEDGE MANAGEMENT (8 tables)
-- Projects, Areas, Resources, Archives
-- =============================================================================

-- 6.1 Projects (Active Work)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT NOT NULL,
    success_criteria TEXT[],
    area_id UUID, -- Link to area
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'on_hold', 'completed', 'cancelled'
    priority INTEGER DEFAULT 50,
    start_date DATE,
    target_date DATE,
    completed_date DATE,
    completion_percentage INTEGER DEFAULT 0,
    estimated_hours INTEGER,
    actual_hours DECIMAL(8,2) DEFAULT 0,
    revenue_potential DECIMAL(12,2),
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_priority ON projects(priority, status);

-- 6.2 Areas (Ongoing Responsibilities)
CREATE TABLE areas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL, -- 'work', 'personal', 'health', 'wealth', 'relationships'
    standard_to_maintain TEXT,
    parent_area_id UUID REFERENCES areas(id),
    is_active BOOLEAN DEFAULT true,
    review_frequency VARCHAR(20), -- 'daily', 'weekly', 'monthly'
    last_reviewed_at TIMESTAMPTZ,
    health_score DECIMAL(3,2), -- 0-1, how well maintained
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update projects foreign key
ALTER TABLE projects ADD CONSTRAINT fk_project_area 
    FOREIGN KEY (area_id) REFERENCES areas(id);

-- 6.3 Resources (Reference Materials)
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) NOT NULL, -- 'topic', 'interest', 'reference', 'template'
    category VARCHAR(100),
    url TEXT,
    document_id UUID REFERENCES documents(id),
    interest_level INTEGER CHECK (interest_level BETWEEN 1 AND 5),
    usefulness_score DECIMAL(3,2),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6.4 Archives (Inactive Items)
CREATE TABLE archives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_table VARCHAR(50) NOT NULL, -- 'projects', 'resources', 'notes'
    original_id UUID NOT NULL,
    archived_data JSONB NOT NULL,
    archive_reason VARCHAR(100),
    archived_by VARCHAR(100),
    can_restore BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6.5 Notes (Progressive Summarization)
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    layer_0_original TEXT, -- Raw capture
    layer_1_bold TEXT, -- Bold passages (10-20%)
    layer_2_highlight TEXT, -- Highlighted (1-2%)
    layer_3_summary TEXT, -- Executive summary
    layer_4_remix TEXT, -- Transformed output
    current_layer INTEGER DEFAULT 0,
    para_category VARCHAR(50) NOT NULL, -- 'project', 'area', 'resource', 'archive'
    para_item_id UUID, -- Reference to specific project/area/resource
    source_type VARCHAR(50),
    source_url TEXT,
    linked_notes UUID[],
    tags TEXT[],
    is_evergreen BOOLEAN DEFAULT false,
    word_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notes_para ON notes(para_category, para_item_id);
CREATE INDEX idx_notes_tags ON notes USING GIN(tags);

-- 6.6 Note Links (Zettelkasten)
CREATE TABLE note_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    link_type VARCHAR(50), -- 'reference', 'extends', 'contradicts', 'supports'
    link_context TEXT,
    strength DECIMAL(3,2) DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_note_id, target_note_id)
);

-- 6.7 Inbox (Quick Capture)
CREATE TABLE inbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    source VARCHAR(100), -- 'voice', 'shortcut', 'email', 'web_clipper'
    capture_context JSONB,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    processed_to_table VARCHAR(50),
    processed_to_id UUID,
    priority INTEGER DEFAULT 50,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inbox_unprocessed ON inbox(created_at) WHERE processed = false;

-- 6.8 Daily/Weekly Reviews
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly', 'quarterly', 'annual'
    review_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    template_used UUID,
    wins TEXT[],
    challenges TEXT[],
    lessons TEXT[],
    next_actions JSONB,
    metrics_snapshot JSONB,
    mood_rating INTEGER CHECK (mood_rating BETWEEN 1 AND 10),
    energy_rating INTEGER CHECK (energy_rating BETWEEN 1 AND 10),
    productivity_rating INTEGER CHECK (productivity_rating BETWEEN 1 AND 10),
    notes TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(review_type, review_date)
);

-- =============================================================================
-- SECTION 7: WEALTH & FINANCE TABLES (22 tables)
-- =============================================================================

-- 7.1 Financial Accounts
CREATE TABLE fin_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- 'checking', 'savings', 'credit', 'investment', 'crypto', 'cash'
    institution VARCHAR(100),
    account_number_hash VARCHAR(64), -- Hashed for security
    routing_number_hash VARCHAR(64),
    currency VARCHAR(3) DEFAULT 'USD',
    current_balance DECIMAL(15,2) DEFAULT 0,
    available_balance DECIMAL(15,2),
    credit_limit DECIMAL(15,2),
    interest_rate DECIMAL(5,4),
    is_asset BOOLEAN DEFAULT true,
    is_liability BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.2 Transactions
CREATE TABLE fin_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES fin_accounts(id),
    transaction_date DATE NOT NULL,
    posted_date DATE,
    amount DECIMAL(15,2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL, -- 'income', 'expense', 'transfer'
    category_id UUID,
    subcategory VARCHAR(100),
    merchant VARCHAR(200),
    merchant_normalized VARCHAR(200),
    description TEXT,
    notes TEXT,
    is_recurring BOOLEAN DEFAULT false,
    recurring_id UUID,
    is_split BOOLEAN DEFAULT false,
    parent_transaction_id UUID REFERENCES fin_transactions(id),
    tags TEXT[],
    receipt_path TEXT,
    location JSONB,
    is_reviewed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (transaction_date);

-- Create partitions for transactions (yearly)
CREATE TABLE fin_transactions_2025 PARTITION OF fin_transactions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE fin_transactions_2026 PARTITION OF fin_transactions
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_transactions_date ON fin_transactions(transaction_date DESC);
CREATE INDEX idx_transactions_category ON fin_transactions(category_id);
CREATE INDEX idx_transactions_account ON fin_transactions(account_id, transaction_date DESC);

-- 7.3 Transaction Categories
CREATE TABLE fin_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    parent_category_id UUID REFERENCES fin_categories(id),
    category_type VARCHAR(20) NOT NULL, -- 'income', 'expense', 'transfer'
    icon VARCHAR(50),
    color VARCHAR(7),
    is_essential BOOLEAN DEFAULT false, -- Needs vs Wants
    monthly_target DECIMAL(12,2),
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.4 Budgets
CREATE TABLE fin_budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    budget_type VARCHAR(20) NOT NULL, -- 'category', 'envelope', 'zero_based'
    period_type VARCHAR(20) NOT NULL, -- 'weekly', 'monthly', 'yearly'
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.5 Budget Items
CREATE TABLE fin_budget_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    budget_id UUID REFERENCES fin_budgets(id),
    category_id UUID REFERENCES fin_categories(id),
    budgeted_amount DECIMAL(12,2) NOT NULL,
    rollover BOOLEAN DEFAULT false,
    rollover_amount DECIMAL(12,2) DEFAULT 0,
    alert_threshold DECIMAL(3,2) DEFAULT 0.80,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(budget_id, category_id)
);

-- 7.6 Debts
CREATE TABLE fin_debts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    debt_type VARCHAR(50) NOT NULL, -- 'credit_card', 'personal', 'student', 'mortgage', 'auto'
    creditor VARCHAR(100) NOT NULL,
    original_amount DECIMAL(12,2) NOT NULL,
    current_balance DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,4) DEFAULT 0,
    minimum_payment DECIMAL(12,2),
    payment_due_day INTEGER,
    start_date DATE,
    target_payoff_date DATE,
    payoff_strategy VARCHAR(50), -- 'avalanche', 'snowball', 'custom'
    priority INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.7 Debt Payments
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
    transaction_id UUID REFERENCES fin_transactions(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.8 Recurring Transactions
CREATE TABLE fin_recurring (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    amount DECIMAL(12,2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category_id UUID REFERENCES fin_categories(id),
    account_id UUID REFERENCES fin_accounts(id),
    frequency VARCHAR(20) NOT NULL, -- 'weekly', 'biweekly', 'monthly', 'yearly'
    day_of_month INTEGER,
    day_of_week INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    last_occurrence DATE,
    next_occurrence DATE,
    auto_pay BOOLEAN DEFAULT false,
    reminder_days INTEGER DEFAULT 3,
    is_essential BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.9 Savings Goals
CREATE TABLE fin_savings_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    target_amount DECIMAL(12,2) NOT NULL,
    current_amount DECIMAL(12,2) DEFAULT 0,
    target_date DATE,
    priority INTEGER DEFAULT 50,
    goal_type VARCHAR(50), -- 'emergency', 'purchase', 'investment', 'retirement'
    linked_account_id UUID REFERENCES fin_accounts(id),
    auto_contribute BOOLEAN DEFAULT false,
    contribute_amount DECIMAL(12,2),
    contribute_frequency VARCHAR(20),
    is_achieved BOOLEAN DEFAULT false,
    achieved_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.10 Investment Portfolios
CREATE TABLE fin_portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    portfolio_type VARCHAR(50) NOT NULL, -- 'retirement', 'taxable', 'crypto', 'real_estate'
    account_id UUID REFERENCES fin_accounts(id),
    strategy VARCHAR(100),
    risk_tolerance VARCHAR(20), -- 'conservative', 'moderate', 'aggressive'
    target_allocation JSONB,
    total_value DECIMAL(15,2) DEFAULT 0,
    total_cost_basis DECIMAL(15,2) DEFAULT 0,
    total_gain_loss DECIMAL(15,2) GENERATED ALWAYS AS (total_value - total_cost_basis) STORED,
    last_rebalanced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.11 Securities/Assets
CREATE TABLE fin_securities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    security_type VARCHAR(50) NOT NULL, -- 'stock', 'etf', 'mutual_fund', 'bond', 'crypto', 'real_estate'
    exchange VARCHAR(50),
    sector VARCHAR(100),
    current_price DECIMAL(15,6),
    price_updated_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, security_type)
);

-- 7.12 Holdings
CREATE TABLE fin_holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES fin_portfolios(id),
    security_id UUID REFERENCES fin_securities(id),
    quantity DECIMAL(18,8) NOT NULL,
    average_cost_basis DECIMAL(15,6) NOT NULL,
    current_value DECIMAL(15,2),
    unrealized_gain_loss DECIMAL(15,2),
    weight_percentage DECIMAL(5,2),
    target_weight DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(portfolio_id, security_id)
);

-- 7.13 Investment Transactions
CREATE TABLE fin_investment_tx (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES fin_portfolios(id),
    security_id UUID REFERENCES fin_securities(id),
    transaction_type VARCHAR(20) NOT NULL, -- 'buy', 'sell', 'dividend', 'split', 'transfer'
    transaction_date DATE NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    price_per_unit DECIMAL(15,6) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    fees DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.14 Price History
CREATE TABLE fin_price_history (
    id BIGSERIAL PRIMARY KEY,
    security_id UUID REFERENCES fin_securities(id),
    date DATE NOT NULL,
    open_price DECIMAL(15,6),
    high_price DECIMAL(15,6),
    low_price DECIMAL(15,6),
    close_price DECIMAL(15,6) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(security_id, date)
);

-- 7.15 Net Worth Snapshots
CREATE TABLE fin_net_worth_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date DATE NOT NULL UNIQUE,
    total_assets DECIMAL(15,2) NOT NULL,
    total_liabilities DECIMAL(15,2) NOT NULL,
    net_worth DECIMAL(15,2) GENERATED ALWAYS AS (total_assets - total_liabilities) STORED,
    liquid_assets DECIMAL(15,2),
    invested_assets DECIMAL(15,2),
    real_estate_assets DECIMAL(15,2),
    other_assets DECIMAL(15,2),
    breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.16 Income Streams (Passive Income Tracking)
CREATE TABLE fin_income_streams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    stream_type VARCHAR(50) NOT NULL, -- 'salary', 'freelance', 'dividend', 'rental', 'royalty', 'affiliate', 'business'
    source VARCHAR(200),
    is_passive BOOLEAN DEFAULT false,
    expected_amount DECIMAL(12,2),
    frequency VARCHAR(20) NOT NULL,
    tax_treatment VARCHAR(50),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.17 Income Payments
CREATE TABLE fin_income_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stream_id UUID REFERENCES fin_income_streams(id),
    payment_date DATE NOT NULL,
    gross_amount DECIMAL(12,2) NOT NULL,
    taxes_withheld DECIMAL(12,2) DEFAULT 0,
    deductions DECIMAL(12,2) DEFAULT 0,
    net_amount DECIMAL(12,2) NOT NULL,
    transaction_id UUID REFERENCES fin_transactions(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.18 Subscriptions Tracker
CREATE TABLE fin_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(100),
    category VARCHAR(50),
    amount DECIMAL(10,2) NOT NULL,
    billing_frequency VARCHAR(20) NOT NULL,
    annual_cost DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE billing_frequency
            WHEN 'monthly' THEN amount * 12
            WHEN 'yearly' THEN amount
            WHEN 'weekly' THEN amount * 52
            ELSE amount
        END
    ) STORED,
    start_date DATE,
    renewal_date DATE,
    cancellation_date DATE,
    account_id UUID REFERENCES fin_accounts(id),
    is_essential BOOLEAN DEFAULT false,
    usage_rating INTEGER CHECK (usage_rating BETWEEN 1 AND 5),
    value_rating INTEGER CHECK (value_rating BETWEEN 1 AND 5),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.19 Opportunities (Wealth Building)
CREATE TABLE wealth_opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(300) NOT NULL,
    description TEXT,
    opportunity_type VARCHAR(50) NOT NULL, -- 'investment', 'business', 'side_hustle', 'career', 'arbitrage'
    source VARCHAR(100),
    source_url TEXT,
    status VARCHAR(30) DEFAULT 'identified', -- 'identified', 'researching', 'pursuing', 'closed_won', 'closed_lost'
    estimated_value DECIMAL(15,2),
    investment_required DECIMAL(15,2),
    time_required_hours INTEGER,
    probability DECIMAL(3,2),
    expected_value DECIMAL(15,2) GENERATED ALWAYS AS (estimated_value * probability) STORED,
    risk_score DECIMAL(3,2),
    thesis_fit_score DECIMAL(3,2),
    urgency VARCHAR(20),
    deadline DATE,
    decision_date DATE,
    outcome VARCHAR(50),
    actual_value DECIMAL(15,2),
    lessons_learned TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.20 Opportunity Signals
CREATE TABLE wealth_opportunity_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id UUID REFERENCES wealth_opportunities(id),
    signal_type VARCHAR(50) NOT NULL, -- 'market_trend', 'news', 'financial_indicator', 'ai_detected'
    signal_data JSONB NOT NULL,
    confidence_score DECIMAL(3,2),
    source VARCHAR(100),
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.21 Financial Goals
CREATE TABLE fin_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50) NOT NULL, -- 'debt_payoff', 'savings', 'income', 'net_worth', 'investment'
    target_value DECIMAL(15,2) NOT NULL,
    current_value DECIMAL(15,2) DEFAULT 0,
    start_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    priority INTEGER DEFAULT 50,
    status VARCHAR(20) DEFAULT 'active',
    milestones JSONB,
    linked_accounts UUID[],
    linked_debts UUID[],
    linked_goals UUID[],
    tracking_frequency VARCHAR(20) DEFAULT 'weekly',
    last_tracked_at TIMESTAMPTZ,
    achieved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7.22 Financial Projections
CREATE TABLE fin_projections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    projection_type VARCHAR(50) NOT NULL, -- 'debt_payoff', 'savings', 'net_worth', 'retirement'
    scenario_name VARCHAR(100) NOT NULL,
    assumptions JSONB NOT NULL,
    projection_data JSONB NOT NULL, -- Monthly/yearly projections
    target_date DATE,
    confidence_level DECIMAL(3,2),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    is_primary BOOLEAN DEFAULT false
);

-- =============================================================================
-- SECTION 8: PRODUCTIVITY & EFFECTIVENESS TABLES (12 tables)
-- =============================================================================

-- 8.1 Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    project_id UUID REFERENCES projects(id),
    area_id UUID REFERENCES areas(id),
    parent_task_id UUID REFERENCES tasks(id),
    status VARCHAR(20) DEFAULT 'todo', -- 'todo', 'in_progress', 'blocked', 'done', 'cancelled'
    priority VARCHAR(20) DEFAULT 'medium', -- 'critical', 'high', 'medium', 'low'
    energy_required VARCHAR(20), -- 'high', 'medium', 'low'
    context_tags TEXT[], -- '@phone', '@computer', '@home', '@work'
    due_date DATE,
    due_time TIME,
    start_date DATE,
    completed_at TIMESTAMPTZ,
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    delegated_to VARCHAR(100),
    recurring_id UUID,
    source VARCHAR(50), -- 'manual', 'email', 'agent', 'automation'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_status ON tasks(status, priority);
CREATE INDEX idx_tasks_due ON tasks(due_date) WHERE status NOT IN ('done', 'cancelled');
CREATE INDEX idx_tasks_project ON tasks(project_id);

-- 8.2 Task Dependencies
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) DEFAULT 'finish_to_start',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(task_id, depends_on_task_id)
);

-- 8.3 Habits
CREATE TABLE habits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    habit_type VARCHAR(20) DEFAULT 'build', -- 'build', 'break'
    frequency VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'custom'
    frequency_config JSONB, -- For custom frequencies
    target_count INTEGER DEFAULT 1,
    time_of_day VARCHAR(20), -- 'morning', 'afternoon', 'evening', 'anytime'
    reminder_time TIME,
    cue TEXT, -- Trigger/cue for the habit
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

-- 8.4 Habit Completions
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

-- 8.5 Goals (Life Goals)
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50) NOT NULL, -- 'outcome', 'process', 'identity'
    category VARCHAR(100) NOT NULL,
    timeframe VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime'
    target_value DECIMAL(15,2),
    current_value DECIMAL(15,2) DEFAULT 0,
    unit VARCHAR(50),
    measurement_method TEXT,
    start_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 50,
    parent_goal_id UUID REFERENCES goals(id),
    area_id UUID REFERENCES areas(id),
    why TEXT, -- Motivation
    obstacles TEXT[],
    strategies TEXT[],
    accountability VARCHAR(100),
    review_frequency VARCHAR(20),
    last_reviewed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8.6 Goal Progress
CREATE TABLE goal_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(id),
    recorded_date DATE NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    notes TEXT,
    evidence TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8.7 Time Investments (Tracking)
CREATE TABLE time_investments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    activity_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    project_id UUID REFERENCES projects(id),
    area_id UUID REFERENCES areas(id),
    duration_minutes INTEGER NOT NULL,
    start_time TIME,
    end_time TIME,
    energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 10),
    focus_level INTEGER CHECK (focus_level BETWEEN 1 AND 10),
    value_rating INTEGER CHECK (value_rating BETWEEN 1 AND 5), -- Was this time well spent?
    is_deep_work BOOLEAN DEFAULT false,
    is_reactive BOOLEAN DEFAULT false, -- vs proactive
    interruptions INTEGER DEFAULT 0,
    notes TEXT,
    source VARCHAR(50) DEFAULT 'manual', -- 'manual', 'toggl', 'rescuetime', 'automated'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_time_investments_date ON time_investments(date DESC);

-- 8.8 Compound Time Savings
CREATE TABLE compound_time_savings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_name VARCHAR(255) NOT NULL,
    description TEXT,
    time_saved_per_occurrence_minutes INTEGER NOT NULL,
    occurrence_frequency VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    occurrences_per_period INTEGER DEFAULT 1,
    is_recurring BOOLEAN DEFAULT true,
    start_date DATE NOT NULL,
    end_date DATE,
    automation_id UUID, -- If automated
    hourly_value DECIMAL(10,2) DEFAULT 50.00, -- Value of time
    -- Calculated fields would be done in views
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8.9 Energy Logs (Biological Prime Time)
CREATE TABLE energy_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    energy_level INTEGER NOT NULL CHECK (energy_level BETWEEN 1 AND 10),
    focus_level INTEGER CHECK (focus_level BETWEEN 1 AND 10),
    motivation_level INTEGER CHECK (motivation_level BETWEEN 1 AND 10),
    stress_level INTEGER CHECK (stress_level BETWEEN 1 AND 10),
    hours_since_wake DECIMAL(4,2),
    hours_since_meal DECIMAL(4,2),
    caffeine_intake_mg INTEGER DEFAULT 0,
    current_activity VARCHAR(255),
    location VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8.10 Focus Sessions (Pomodoro/Deep Work)
CREATE TABLE focus_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id),
    project_id UUID REFERENCES projects(id),
    session_type VARCHAR(20) NOT NULL, -- 'pomodoro', 'deep_work', 'time_block'
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

-- 8.11 Decisions Journal
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_date DATE NOT NULL,
    title VARCHAR(500) NOT NULL,
    situation_context TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    decision_type VARCHAR(50), -- 'one_way_door', 'two_way_door', 'reversible'
    importance VARCHAR(20), -- 'critical', 'significant', 'routine'
    time_pressure VARCHAR(20), -- 'urgent', 'near_term', 'no_rush'
    alternatives_considered JSONB,
    chosen_alternative TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    expected_outcome TEXT NOT NULL,
    confidence_level INTEGER CHECK (confidence_level BETWEEN 0 AND 100),
    second_order_consequences TEXT[],
    third_order_consequences TEXT[],
    worst_case_scenario TEXT,
    best_case_scenario TEXT,
    opportunity_cost TEXT,
    resources_required JSONB,
    stakeholders TEXT[],
    physical_state VARCHAR(50),
    mental_state VARCHAR(50),
    emotional_state VARCHAR(50),
    biases_considered TEXT[],
    reversibility VARCHAR(50),
    review_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8.12 Decision Outcomes
CREATE TABLE decision_outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID REFERENCES decisions(id),
    review_date DATE NOT NULL,
    actual_outcome TEXT NOT NULL,
    outcome_rating INTEGER CHECK (outcome_rating BETWEEN 1 AND 10),
    was_prediction_accurate BOOLEAN,
    accuracy_notes TEXT,
    unexpected_consequences TEXT[],
    lessons_learned TEXT[] NOT NULL,
    would_decide_differently BOOLEAN,
    what_would_change TEXT,
    applied_to_future BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 9: HEALTH TABLES (12 tables) - Minimal but Complete
-- =============================================================================

-- 9.1 Health Daily Metrics
CREATE TABLE health_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    weight_lbs DECIMAL(5,1),
    body_fat_pct DECIMAL(4,1),
    sleep_hours DECIMAL(3,1),
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 1 AND 10),
    deep_sleep_hours DECIMAL(3,1),
    rem_sleep_hours DECIMAL(3,1),
    bedtime TIME,
    wake_time TIME,
    energy_avg INTEGER CHECK (energy_avg BETWEEN 1 AND 10),
    mood_avg INTEGER CHECK (mood_avg BETWEEN 1 AND 10),
    stress_avg INTEGER CHECK (stress_avg BETWEEN 1 AND 10),
    water_oz INTEGER,
    steps INTEGER,
    active_minutes INTEGER,
    active_calories INTEGER,
    resting_heart_rate INTEGER,
    hrv_ms INTEGER,
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    notes TEXT,
    data_sources TEXT[], -- 'apple_watch', 'manual', 'withings'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.2 Workouts
CREATE TABLE health_workouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    workout_type VARCHAR(50) NOT NULL, -- 'strength', 'cardio', 'flexibility', 'sports'
    name VARCHAR(200),
    duration_minutes INTEGER,
    calories_burned INTEGER,
    avg_heart_rate INTEGER,
    max_heart_rate INTEGER,
    intensity VARCHAR(20), -- 'low', 'moderate', 'high', 'max'
    perceived_exertion INTEGER CHECK (perceived_exertion BETWEEN 1 AND 10),
    notes TEXT,
    source VARCHAR(50) DEFAULT 'manual',
    source_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.3 Workout Exercises
CREATE TABLE health_workout_exercises (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workout_id UUID REFERENCES health_workouts(id),
    exercise_name VARCHAR(200) NOT NULL,
    exercise_order INTEGER,
    sets INTEGER,
    reps INTEGER,
    weight_lbs DECIMAL(6,1),
    duration_seconds INTEGER,
    distance_miles DECIMAL(6,2),
    rest_seconds INTEGER,
    notes TEXT
);

-- 9.4 Nutrition Log
CREATE TABLE health_nutrition (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    meal_type VARCHAR(20) NOT NULL, -- 'breakfast', 'lunch', 'dinner', 'snack'
    meal_time TIME,
    food_name VARCHAR(300) NOT NULL,
    brand VARCHAR(100),
    serving_size VARCHAR(100),
    servings DECIMAL(4,2) DEFAULT 1,
    calories INTEGER,
    protein_g DECIMAL(6,1),
    carbs_g DECIMAL(6,1),
    fat_g DECIMAL(6,1),
    fiber_g DECIMAL(6,1),
    sugar_g DECIMAL(6,1),
    sodium_mg INTEGER,
    is_inflammatory BOOLEAN DEFAULT false,
    is_whole_food BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.5 Supplements
CREATE TABLE health_supplements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    form VARCHAR(50), -- 'capsule', 'tablet', 'powder', 'liquid'
    dosage_amount DECIMAL(10,2),
    dosage_unit VARCHAR(20),
    purpose TEXT,
    timing VARCHAR(50), -- 'morning', 'evening', 'with_food', 'empty_stomach'
    frequency VARCHAR(50) DEFAULT 'daily',
    current_stock INTEGER DEFAULT 0,
    reorder_threshold INTEGER DEFAULT 10,
    cost_per_unit DECIMAL(8,2),
    purchase_url TEXT,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.6 Supplement Intake Log
CREATE TABLE health_supplement_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplement_id UUID REFERENCES health_supplements(id),
    taken_at TIMESTAMPTZ DEFAULT NOW(),
    dosage_amount DECIMAL(10,2),
    with_food BOOLEAN,
    notes TEXT
);

-- 9.7 Health Symptoms
CREATE TABLE health_symptoms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    symptom VARCHAR(200) NOT NULL,
    body_location VARCHAR(100),
    severity INTEGER CHECK (severity BETWEEN 1 AND 10),
    duration_hours DECIMAL(5,1),
    start_time TIME,
    possible_triggers TEXT[],
    relieved_by TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.8 Esophagitis Triggers (Philip's specific condition)
CREATE TABLE health_esophagitis_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    trigger_food VARCHAR(200),
    trigger_behavior VARCHAR(200), -- 'eating_late', 'lying_down', etc.
    reaction_severity INTEGER CHECK (reaction_severity BETWEEN 1 AND 10),
    time_to_reaction_hours DECIMAL(4,1),
    symptoms TEXT[],
    relief_method TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.9 Lung Health (Ex-smoker tracking)
CREATE TABLE health_lung_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    days_smoke_free INTEGER, -- Auto-calculated from quit date
    coughing_frequency VARCHAR(20), -- 'none', 'occasional', 'frequent'
    mucus_production VARCHAR(20),
    shortness_of_breath VARCHAR(20),
    exercise_tolerance VARCHAR(50),
    peak_flow INTEGER, -- L/min if measured
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.10 Medical Records
CREATE TABLE health_medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_date DATE NOT NULL,
    record_type VARCHAR(50) NOT NULL, -- 'appointment', 'test', 'procedure', 'prescription'
    provider VARCHAR(200),
    facility VARCHAR(200),
    reason TEXT,
    diagnosis TEXT,
    treatment TEXT,
    medications JSONB,
    test_results JSONB,
    follow_up_date DATE,
    follow_up_notes TEXT,
    documents TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.11 Medications
CREATE TABLE health_medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    prescriber VARCHAR(200),
    pharmacy VARCHAR(200),
    purpose TEXT,
    start_date DATE,
    end_date DATE,
    refills_remaining INTEGER,
    next_refill_date DATE,
    side_effects_experienced TEXT[],
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9.12 Health Goals
CREATE TABLE health_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID REFERENCES goals(id),
    health_category VARCHAR(50) NOT NULL, -- 'weight', 'fitness', 'nutrition', 'sleep', 'condition'
    metric_name VARCHAR(100) NOT NULL,
    baseline_value DECIMAL(10,2),
    target_value DECIMAL(10,2) NOT NULL,
    current_value DECIMAL(10,2),
    unit VARCHAR(50),
    tracking_frequency VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 10: CAR & VEHICLE TABLES (8 tables) - Minimal
-- =============================================================================

-- 10.1 Vehicles
CREATE TABLE car_vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    trim VARCHAR(50),
    vin VARCHAR(17),
    license_plate VARCHAR(20),
    color VARCHAR(30),
    purchase_date DATE,
    purchase_price DECIMAL(10,2),
    purchase_mileage INTEGER,
    current_mileage INTEGER,
    estimated_value DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.2 Mileage Logs
CREATE TABLE car_mileage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    date DATE NOT NULL,
    odometer INTEGER NOT NULL,
    trip_purpose VARCHAR(200),
    trip_miles DECIMAL(7,1),
    is_business BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.3 Fuel Logs
CREATE TABLE car_fuel_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    date DATE NOT NULL,
    odometer INTEGER,
    gallons DECIMAL(6,3) NOT NULL,
    price_per_gallon DECIMAL(5,3) NOT NULL,
    total_cost DECIMAL(8,2) NOT NULL,
    station VARCHAR(200),
    fuel_type VARCHAR(20) DEFAULT 'regular',
    full_tank BOOLEAN DEFAULT true,
    mpg_calculated DECIMAL(5,1),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.4 Maintenance Schedule
CREATE TABLE car_maintenance_schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    service_type VARCHAR(200) NOT NULL,
    description TEXT,
    interval_miles INTEGER,
    interval_months INTEGER,
    last_performed_date DATE,
    last_performed_mileage INTEGER,
    next_due_date DATE,
    next_due_mileage INTEGER,
    estimated_cost DECIMAL(8,2),
    priority VARCHAR(20) DEFAULT 'normal',
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.5 Maintenance History
CREATE TABLE car_maintenance_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    schedule_id UUID REFERENCES car_maintenance_schedule(id),
    service_date DATE NOT NULL,
    mileage INTEGER NOT NULL,
    service_type VARCHAR(200) NOT NULL,
    description TEXT,
    provider VARCHAR(200),
    parts_cost DECIMAL(8,2) DEFAULT 0,
    labor_cost DECIMAL(8,2) DEFAULT 0,
    total_cost DECIMAL(8,2) NOT NULL,
    warranty_covered BOOLEAN DEFAULT false,
    receipt_path TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.6 Vehicle Insurance
CREATE TABLE car_insurance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    provider VARCHAR(200) NOT NULL,
    policy_number VARCHAR(100),
    coverage_type VARCHAR(100),
    monthly_premium DECIMAL(8,2),
    deductible DECIMAL(8,2),
    liability_limit VARCHAR(100),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    agent_name VARCHAR(200),
    agent_phone VARCHAR(20),
    documents TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.7 Vehicle Registration
CREATE TABLE car_registration (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES car_vehicles(id),
    registration_type VARCHAR(50) NOT NULL, -- 'registration', 'inspection', 'emissions'
    expiry_date DATE NOT NULL,
    cost DECIMAL(8,2),
    renewal_reminder_days INTEGER DEFAULT 30,
    completed BOOLEAN DEFAULT false,
    completed_date DATE,
    documents TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10.8 Vehicle Expenses Summary (Materialized View)
-- Will be created as a view in the views section

-- =============================================================================
-- SECTION 11: LEARNING & SKILLS TABLES (10 tables)
-- =============================================================================

-- 11.1 Learning Sessions
CREATE TABLE learn_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    topic VARCHAR(200) NOT NULL,
    subtopic VARCHAR(200),
    curriculum_id UUID,
    duration_minutes INTEGER NOT NULL,
    method VARCHAR(50), -- 'reading', 'video', 'practice', 'project', 'course'
    resource_url TEXT,
    resource_title VARCHAR(500),
    focus_rating INTEGER CHECK (focus_rating BETWEEN 1 AND 10),
    comprehension_rating INTEGER CHECK (comprehension_rating BETWEEN 1 AND 10),
    difficulty_rating INTEGER CHECK (difficulty_rating BETWEEN 1 AND 10),
    notes TEXT,
    key_concepts TEXT[],
    questions TEXT[],
    errors_encountered TEXT[],
    commands_practiced TEXT[],
    code_written TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.2 Session Analysis (AI Generated)
CREATE TABLE learn_session_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES learn_sessions(id),
    weak_areas TEXT[],
    strong_areas TEXT[],
    suggested_next_topics TEXT[],
    difficulty_assessment VARCHAR(50),
    progress_notes TEXT,
    recommended_resources JSONB,
    estimated_proficiency DECIMAL(3,2),
    ai_model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.3 Curriculum/Roadmap
CREATE TABLE learn_curriculum (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path_name VARCHAR(200) NOT NULL, -- 'Programming to Autonomous Systems'
    topic VARCHAR(200) NOT NULL,
    subtopics JSONB,
    order_index INTEGER NOT NULL,
    estimated_hours INTEGER,
    status VARCHAR(20) DEFAULT 'not_started',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    proficiency_level INTEGER CHECK (proficiency_level BETWEEN 1 AND 10),
    prerequisites UUID[],
    resources JSONB,
    milestones JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(path_name, order_index)
);

-- 11.4 Skills Inventory
CREATE TABLE learn_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    proficiency_level INTEGER CHECK (proficiency_level BETWEEN 1 AND 10),
    proficiency_evidence TEXT,
    market_value_score DECIMAL(3,2), -- 0-1, how valuable in job market
    last_practiced DATE,
    total_hours DECIMAL(10,1) DEFAULT 0,
    decay_rate DECIMAL(3,2), -- How fast skill fades without practice
    related_skills UUID[],
    certifications TEXT[],
    portfolio_items TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.5 Skill Progress
CREATE TABLE learn_skill_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id UUID REFERENCES learn_skills(id),
    date DATE NOT NULL,
    proficiency_level INTEGER,
    hours_invested DECIMAL(6,1),
    milestone_reached VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.6 Learning Resources
CREATE TABLE learn_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    url TEXT,
    resource_type VARCHAR(50), -- 'video', 'article', 'course', 'book', 'documentation', 'tutorial'
    platform VARCHAR(100),
    author VARCHAR(200),
    topic VARCHAR(200),
    difficulty VARCHAR(20),
    estimated_hours DECIMAL(6,1),
    status VARCHAR(20) DEFAULT 'saved', -- 'saved', 'in_progress', 'completed', 'archived'
    progress_percent INTEGER DEFAULT 0,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    review TEXT,
    tags TEXT[],
    cost DECIMAL(8,2) DEFAULT 0,
    is_free BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.7 Quiz Questions
CREATE TABLE learn_quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic VARCHAR(200) NOT NULL,
    subtopic VARCHAR(200),
    question TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'multiple_choice',
    options JSONB,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    difficulty INTEGER CHECK (difficulty BETWEEN 1 AND 5),
    source_session_id UUID REFERENCES learn_sessions(id),
    times_asked INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    last_asked_at TIMESTAMPTZ,
    next_review_at TIMESTAMPTZ, -- Spaced repetition
    ease_factor DECIMAL(4,2) DEFAULT 2.5, -- SM-2 algorithm
    interval_days INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.8 Quiz Attempts
CREATE TABLE learn_quiz_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    topic VARCHAR(200),
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    score_percent DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN total_questions > 0 
            THEN (correct_answers::DECIMAL / total_questions * 100) 
            ELSE 0 END
    ) STORED,
    time_taken_seconds INTEGER,
    questions_answered JSONB, -- [{question_id, answer, correct, time_ms}]
    weak_areas TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.9 Neural Academy Podcasts
CREATE TABLE learn_podcasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    episode_number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    topic VARCHAR(200) NOT NULL,
    subtopic VARCHAR(200),
    script TEXT,
    script_word_count INTEGER,
    duration_seconds INTEGER,
    file_path TEXT,
    file_size_mb DECIMAL(8,2),
    voice_model VARCHAR(100),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    based_on_sessions UUID[],
    weak_areas_addressed TEXT[],
    listened BOOLEAN DEFAULT false,
    listened_at TIMESTAMPTZ,
    listen_progress_seconds INTEGER DEFAULT 0,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11.10 Learning Streaks
CREATE TABLE learn_streaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    streak_type VARCHAR(50) NOT NULL, -- 'daily_learning', 'quiz', 'podcast'
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    streak_start_date DATE,
    last_activity_date DATE,
    total_days_active INTEGER DEFAULT 0,
    milestones_reached JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 12: CONTACTS & COMMUNICATION (6 tables) - Minimal CRM
-- =============================================================================

-- 12.1 Contacts
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200) NOT NULL,
    nickname VARCHAR(100),
    relationship_type VARCHAR(50), -- 'family', 'friend', 'professional', 'acquaintance'
    company VARCHAR(200),
    job_title VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(30),
    address JSONB,
    birthday DATE,
    notes TEXT,
    how_met TEXT,
    met_date DATE,
    last_contact_date DATE,
    contact_frequency_days INTEGER, -- How often to reach out
    importance INTEGER CHECK (importance BETWEEN 1 AND 10),
    tags TEXT[],
    social_links JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12.2 Contact Interactions
CREATE TABLE contact_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES contacts(id),
    interaction_date DATE NOT NULL,
    interaction_type VARCHAR(50), -- 'call', 'text', 'email', 'in_person', 'video'
    direction VARCHAR(20), -- 'inbound', 'outbound'
    duration_minutes INTEGER,
    summary TEXT,
    sentiment VARCHAR(20), -- 'positive', 'neutral', 'negative'
    topics_discussed TEXT[],
    follow_up_needed BOOLEAN DEFAULT false,
    follow_up_date DATE,
    follow_up_action TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12.3 Email Accounts
CREATE TABLE email_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_address VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL, -- 'gmail', 'icloud', 'outlook'
    display_name VARCHAR(200),
    is_primary BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    sync_enabled BOOLEAN DEFAULT true,
    folders_to_sync TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12.4 Emails
CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES email_accounts(id),
    message_id VARCHAR(255) UNIQUE,
    thread_id VARCHAR(255),
    from_address VARCHAR(255),
    from_name VARCHAR(200),
    to_addresses TEXT[],
    cc_addresses TEXT[],
    subject VARCHAR(1000),
    snippet TEXT,
    body_text TEXT,
    body_html TEXT,
    received_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    is_read BOOLEAN DEFAULT false,
    is_starred BOOLEAN DEFAULT false,
    is_important BOOLEAN DEFAULT false,
    labels TEXT[],
    folder VARCHAR(100),
    has_attachments BOOLEAN DEFAULT false,
    attachment_count INTEGER DEFAULT 0,
    ai_summary TEXT,
    ai_category VARCHAR(100),
    ai_priority VARCHAR(20),
    requires_action BOOLEAN DEFAULT false,
    action_status VARCHAR(20),
    action_due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_emails_received ON emails(received_at DESC);
CREATE INDEX idx_emails_unread ON emails(is_read, received_at DESC) WHERE is_read = false;

-- 12.5 Email Drafts
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES email_accounts(id),
    to_addresses TEXT[] NOT NULL,
    cc_addresses TEXT[],
    bcc_addresses TEXT[],
    subject VARCHAR(1000) NOT NULL,
    body_text TEXT NOT NULL,
    body_html TEXT,
    reply_to_id UUID REFERENCES emails(id),
    created_by VARCHAR(100), -- 'user', 'agent:email_agent'
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'pending_approval', 'approved', 'sent', 'cancelled'
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(100),
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12.6 Communication Templates
CREATE TABLE communication_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    template_type VARCHAR(50) NOT NULL, -- 'email', 'text', 'message'
    category VARCHAR(100),
    subject VARCHAR(500),
    body TEXT NOT NULL,
    variables TEXT[],
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 13: WORK & CAREER TABLES (6 tables) - Minimal (Goal is to quit!)
-- =============================================================================

-- 13.1 Employers
CREATE TABLE work_employers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    industry VARCHAR(100),
    address JSONB,
    phone VARCHAR(30),
    supervisor_name VARCHAR(200),
    supervisor_contact VARCHAR(255),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT true,
    hourly_rate DECIMAL(8,2),
    pay_frequency VARCHAR(20), -- 'weekly', 'biweekly', 'monthly'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13.2 Work Shifts
CREATE TABLE work_shifts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employer_id UUID REFERENCES work_employers(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hours_worked DECIMAL(5,2),
    break_minutes INTEGER DEFAULT 0,
    hourly_rate DECIMAL(8,2),
    gross_pay DECIMAL(10,2),
    shift_type VARCHAR(50), -- 'regular', 'overtime', 'holiday'
    overtime_hours DECIMAL(4,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13.3 Pay Periods
CREATE TABLE work_pay_periods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employer_id UUID REFERENCES work_employers(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    gross_pay DECIMAL(10,2),
    net_pay DECIMAL(10,2),
    taxes_withheld DECIMAL(10,2),
    deductions JSONB,
    pay_date DATE,
    pay_stub_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13.4 Time Off
CREATE TABLE work_time_off (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employer_id UUID REFERENCES work_employers(id),
    request_type VARCHAR(50) NOT NULL, -- 'vacation', 'sick', 'personal', 'unpaid'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hours DECIMAL(6,2),
    status VARCHAR(20) DEFAULT 'pending',
    approved_by VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13.5 Career Goals (Escape Plan!)
CREATE TABLE work_career_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_type VARCHAR(50) NOT NULL, -- 'quit_job', 'new_role', 'freelance', 'business'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_date DATE,
    income_required DECIMAL(12,2), -- Income needed to achieve this
    current_progress_percent INTEGER DEFAULT 0,
    milestones JSONB,
    blockers TEXT[],
    action_items JSONB,
    status VARCHAR(20) DEFAULT 'planning',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13.6 Side Income Tracking
CREATE TABLE work_side_income (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(200) NOT NULL,
    income_type VARCHAR(50) NOT NULL, -- 'freelance', 'consulting', 'product', 'affiliate'
    date DATE NOT NULL,
    gross_amount DECIMAL(12,2) NOT NULL,
    expenses DECIMAL(12,2) DEFAULT 0,
    net_amount DECIMAL(12,2) GENERATED ALWAYS AS (gross_amount - expenses) STORED,
    hours_worked DECIMAL(6,2),
    effective_hourly_rate DECIMAL(8,2),
    client VARCHAR(200),
    project VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 14: CREDENTIALS & SECURITY (4 tables)
-- =============================================================================

-- 14.1 Encrypted Credentials
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    service_url TEXT,
    username_encrypted BYTEA,
    password_encrypted BYTEA,
    email_encrypted BYTEA,
    notes_encrypted BYTEA,
    totp_secret_encrypted BYTEA,
    recovery_codes_encrypted BYTEA,
    password_strength INTEGER,
    last_used_at TIMESTAMPTZ,
    last_changed_at TIMESTAMPTZ,
    change_reminder_days INTEGER DEFAULT 90,
    expiry_date DATE,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14.2 API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    key_encrypted BYTEA NOT NULL,
    key_prefix VARCHAR(20), -- First few chars for identification
    environment VARCHAR(20) DEFAULT 'production', -- 'production', 'development', 'test'
    rate_limit VARCHAR(100),
    monthly_limit VARCHAR(100),
    current_usage INTEGER DEFAULT 0,
    expires_at DATE,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14.3 Important Documents
CREATE TABLE important_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_type VARCHAR(100) NOT NULL, -- 'id', 'passport', 'license', 'birth_certificate', 'tax'
    document_name VARCHAR(255) NOT NULL,
    issuing_authority VARCHAR(200),
    document_number_encrypted BYTEA,
    issue_date DATE,
    expiry_date DATE,
    renewal_reminder_days INTEGER DEFAULT 30,
    file_path TEXT,
    notes TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14.4 Security Events
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL, -- 'login', 'password_change', 'api_access', 'suspicious'
    severity VARCHAR(20) NOT NULL,
    source_ip INET,
    user_agent TEXT,
    description TEXT NOT NULL,
    details JSONB,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SECTION 15: MATERIALIZED VIEWS & ANALYTICS
-- =============================================================================

-- 15.1 Daily API Cost Summary
CREATE MATERIALIZED VIEW mv_daily_api_costs AS
SELECT 
    DATE(timestamp) AS date,
    provider_id,
    model_id,
    COUNT(*) AS request_count,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(cached_tokens) AS total_cached_tokens,
    SUM(cost_usd) AS total_cost,
    AVG(latency_ms) AS avg_latency_ms,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_requests
FROM api_usage
GROUP BY DATE(timestamp), provider_id, model_id;

CREATE UNIQUE INDEX idx_mv_daily_api_costs ON mv_daily_api_costs(date, provider_id, model_id);

-- 15.2 Budget Status View
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

-- 15.3 Debt Payoff Progress
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
GROUP BY d.id;

-- 15.4 Learning Progress Summary
CREATE VIEW v_learning_progress AS
SELECT 
    c.path_name,
    c.topic,
    c.order_index,
    c.status,
    c.proficiency_level,
    c.estimated_hours,
    COALESCE(SUM(ls.duration_minutes) / 60.0, 0) AS actual_hours,
    COUNT(ls.id) AS session_count,
    MAX(ls.date) AS last_session_date,
    AVG(ls.comprehension_rating) AS avg_comprehension
FROM learn_curriculum c
LEFT JOIN learn_sessions ls ON ls.topic = c.topic
GROUP BY c.id, c.path_name, c.topic, c.order_index, c.status, 
         c.proficiency_level, c.estimated_hours
ORDER BY c.path_name, c.order_index;

-- 15.5 Agent Performance Leaderboard
CREATE VIEW v_agent_leaderboard AS
SELECT 
    a.name,
    a.display_name,
    a.domain,
    SUM(ap.total_requests) AS total_requests,
    ROUND(AVG(ap.avg_user_rating)::numeric, 2) AS avg_rating,
    SUM(ap.total_cost_usd) AS total_cost,
    ROUND((SUM(ap.successful_requests)::numeric / NULLIF(SUM(ap.total_requests), 0) * 100), 1) AS success_rate,
    ROUND(AVG(ap.avg_latency_ms)::numeric, 0) AS avg_latency_ms,
    SUM(ap.handoffs_initiated) AS handoffs_out,
    SUM(ap.handoffs_received) AS handoffs_in
FROM agents a
LEFT JOIN agent_performance ap ON a.id = ap.agent_id
WHERE ap.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY a.id, a.name, a.display_name, a.domain
ORDER BY total_requests DESC;

-- 15.6 Health Trends
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

-- 15.7 Financial Runway
CREATE VIEW v_financial_runway AS
WITH monthly_expenses AS (
    SELECT 
        AVG(total) AS avg_monthly_expenses
    FROM (
        SELECT 
            DATE_TRUNC('month', transaction_date) AS month,
            SUM(amount) AS total
        FROM fin_transactions
        WHERE transaction_type = 'expense'
        AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY DATE_TRUNC('month', transaction_date)
    ) monthly
),
liquid_assets AS (
    SELECT SUM(current_balance) AS total_liquid
    FROM fin_accounts
    WHERE account_type IN ('checking', 'savings', 'cash')
    AND is_active = true
)
SELECT 
    la.total_liquid AS liquid_assets,
    me.avg_monthly_expenses,
    ROUND((la.total_liquid / NULLIF(me.avg_monthly_expenses, 0))::numeric, 1) AS runway_months
FROM liquid_assets la, monthly_expenses me;

-- 15.8 Compound Time Savings Total
CREATE VIEW v_compound_savings AS
SELECT 
    SUM(
        CASE occurrence_frequency
            WHEN 'daily' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 365
            WHEN 'weekly' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 52
            WHEN 'monthly' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 12
        END
    ) AS annual_minutes_saved,
    SUM(
        CASE occurrence_frequency
            WHEN 'daily' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 365 * hourly_value / 60
            WHEN 'weekly' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 52 * hourly_value / 60
            WHEN 'monthly' THEN time_saved_per_occurrence_minutes * occurrences_per_period * 12 * hourly_value / 60
        END
    ) AS annual_value_created
FROM compound_time_savings
WHERE is_recurring = true
AND (end_date IS NULL OR end_date > CURRENT_DATE);

-- 15.9 Car Total Cost of Ownership
CREATE VIEW v_car_tco AS
SELECT 
    v.id,
    v.make || ' ' || v.model || ' ' || v.year AS vehicle,
    v.current_mileage,
    COALESCE(SUM(f.total_cost), 0) AS total_fuel_cost,
    COALESCE(SUM(m.total_cost), 0) AS total_maintenance_cost,
    COALESCE(MAX(i.monthly_premium) * 12, 0) AS annual_insurance_cost,
    COALESCE(SUM(f.total_cost), 0) + COALESCE(SUM(m.total_cost), 0) AS total_operating_cost,
    ROUND(AVG(f.mpg_calculated)::numeric, 1) AS avg_mpg
FROM car_vehicles v
LEFT JOIN car_fuel_logs f ON f.vehicle_id = v.id
LEFT JOIN car_maintenance_history m ON m.vehicle_id = v.id
LEFT JOIN car_insurance i ON i.vehicle_id = v.id AND i.is_active = true
WHERE v.is_active = true
GROUP BY v.id, v.make, v.model, v.year, v.current_mileage;

-- =============================================================================
-- SECTION 16: INDEXES FOR OPTIMIZATION
-- =============================================================================

-- Additional performance indexes
CREATE INDEX idx_sessions_agent ON sessions(primary_agent_id);
CREATE INDEX idx_messages_agent ON messages(agent_id);
CREATE INDEX idx_memories_type ON memories(memory_type, agent_id);
CREATE INDEX idx_tasks_status_due ON tasks(status, due_date) WHERE status NOT IN ('done', 'cancelled');
CREATE INDEX idx_goals_status ON goals(status, priority);
CREATE INDEX idx_fin_transactions_merchant ON fin_transactions(merchant_normalized);
CREATE INDEX idx_documents_category ON documents(para_category, processing_status);
CREATE INDEX idx_notes_updated ON notes(updated_at DESC);
CREATE INDEX idx_learn_sessions_date ON learn_sessions(date DESC);
CREATE INDEX idx_health_daily_date ON health_daily(date DESC);

-- GIN indexes for JSONB and array columns
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX idx_tasks_context_tags ON tasks USING GIN(context_tags);
CREATE INDEX idx_notes_tags ON notes USING GIN(tags);

-- =============================================================================
-- SECTION 17: INITIAL DATA SEEDING
-- =============================================================================

-- Insert Philip's context
INSERT INTO system_config (key, value, category, description) VALUES
('user.name', '"Philip"', 'user', 'User name'),
('user.timezone', '"America/Chicago"', 'user', 'User timezone'),
('user.location', '{"city": "Texas", "country": "USA"}', 'user', 'User location'),
('system.version', '"4.0.0"', 'system', 'NEXUS version'),
('system.build_date', '"2026-01-18"', 'system', 'Schema creation date'),
('ai.default_model', '"deepseek-v3"', 'ai', 'Default AI model'),
('ai.monthly_budget', '3.00', 'ai', 'Monthly AI spending budget'),
('ai.cascade_enabled', 'true', 'ai', 'Enable model cascading');

-- Insert default AI providers
INSERT INTO ai_providers (name, display_name, is_local, priority, capabilities) VALUES
('ollama', 'Ollama (Local)', true, 10, ARRAY['chat', 'embedding']),
('groq', 'Groq', false, 20, ARRAY['chat', 'streaming']),
('google', 'Google AI Studio', false, 30, ARRAY['chat', 'vision']),
('deepseek', 'DeepSeek', false, 40, ARRAY['chat', 'tools', 'streaming']),
('anthropic', 'Anthropic', false, 100, ARRAY['chat', 'tools', 'vision', 'streaming']);

-- Insert Philip's vehicle (2011 Hyundai Sonata)
INSERT INTO car_vehicles (make, model, year, is_active) VALUES
('Hyundai', 'Sonata', 2011, true);

-- Insert Philip's employer
INSERT INTO work_employers (name, is_current, start_date) VALUES
('BMR Janitorial Services', true, '2024-01-01');

-- Insert default areas (PARA)
INSERT INTO areas (name, category, description) VALUES
('Work', 'work', 'Current employment at BMR'),
('NEXUS Development', 'work', 'Building the AI operating system'),
('Health', 'health', 'Physical and mental wellbeing'),
('Wealth Building', 'wealth', 'Financial independence journey'),
('Learning', 'personal', 'Programming and AI skills'),
('Relationships', 'relationships', 'Family and social connections');

-- Insert default expense categories
INSERT INTO fin_categories (name, category_type, is_essential) VALUES
('Food & Groceries', 'expense', true),
('Gas & Transportation', 'expense', true),
('Entertainment', 'expense', false),
('Debt Payment', 'expense', true),
('NEXUS Operating', 'expense', true),
('Subscriptions', 'expense', false),
('Healthcare', 'expense', true),
('Car Maintenance', 'expense', true),
('Salary', 'income', true),
('Side Income', 'income', false);

-- Insert mom's debt
INSERT INTO fin_debts (name, debt_type, creditor, original_amount, current_balance, is_active)
VALUES ('Mom Loan', 'personal', 'Mom', 9700.00, 9700.00, true);

-- Insert default chunking config
INSERT INTO chunking_configs (name, strategy, chunk_size, chunk_overlap, is_default) VALUES
('semantic_default', 'semantic', 512, 50, true),
('fixed_small', 'fixed', 256, 25, false),
('fixed_large', 'fixed', 1024, 100, false);

-- Insert hybrid search config
INSERT INTO hybrid_search_config (name, semantic_weight, bm25_weight, is_active) VALUES
('default', 0.65, 0.35, true);

-- Insert default model cascade
INSERT INTO model_cascades (name, description, task_type, cascade_order, is_enabled) VALUES
('general', 'Default cascade for general queries', 'general', ARRAY[]::UUID[], true);

-- =============================================================================
-- SECTION 18: FUNCTIONS & TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fin_accounts_updated_at BEFORE UPDATE ON fin_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_habits_updated_at BEFORE UPDATE ON habits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate streak
CREATE OR REPLACE FUNCTION update_habit_streak()
RETURNS TRIGGER AS $$
DECLARE
    last_completion DATE;
    current_streak INTEGER;
BEGIN
    -- Get last completion date before today
    SELECT completion_date INTO last_completion
    FROM habit_completions
    WHERE habit_id = NEW.habit_id
    AND completion_date < NEW.completion_date
    ORDER BY completion_date DESC
    LIMIT 1;
    
    -- Get current streak
    SELECT streak_current INTO current_streak
    FROM habits
    WHERE id = NEW.habit_id;
    
    -- Update streak
    IF last_completion IS NULL OR NEW.completion_date - last_completion > 1 THEN
        -- Streak broken or new habit
        UPDATE habits 
        SET streak_current = 1,
            streak_started_at = NEW.completion_date,
            total_completions = total_completions + 1
        WHERE id = NEW.habit_id;
    ELSE
        -- Continue streak
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

-- Function to log audit trail
CREATE OR REPLACE FUNCTION log_audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_trail (action_type, entity_type, entity_id, table_name, new_values, performed_by)
        VALUES ('create', TG_TABLE_NAME, NEW.id, TG_TABLE_NAME, to_jsonb(NEW), 'system');
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_trail (action_type, entity_type, entity_id, table_name, old_values, new_values, performed_by)
        VALUES ('update', TG_TABLE_NAME, NEW.id, TG_TABLE_NAME, to_jsonb(OLD), to_jsonb(NEW), 'system');
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_trail (action_type, entity_type, entity_id, table_name, old_values, performed_by)
        VALUES ('delete', TG_TABLE_NAME, OLD.id, TG_TABLE_NAME, to_jsonb(OLD), 'system');
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- Apply audit triggers to important tables
CREATE TRIGGER audit_fin_transactions AFTER INSERT OR UPDATE OR DELETE ON fin_transactions
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();
CREATE TRIGGER audit_fin_debts AFTER INSERT OR UPDATE OR DELETE ON fin_debts
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();
CREATE TRIGGER audit_credentials AFTER INSERT OR UPDATE OR DELETE ON credentials
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

-- =============================================================================
-- SECTION 19: REFRESH MATERIALIZED VIEWS (Scheduled)
-- =============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_api_costs;
    -- Add more materialized views as needed
END;
$$ language 'plpgsql';

-- =============================================================================
-- SUMMARY: 115 TABLES CREATED
-- =============================================================================
/*
SECTION 1: Core System (10 tables)
SECTION 2: AI Cost Optimization (12 tables)
SECTION 3: Agent System (15 tables)
SECTION 4: Memory System (12 tables)
SECTION 5: RAG Pipeline (11 tables)
SECTION 6: PARA Knowledge (8 tables)
SECTION 7: Wealth & Finance (22 tables)
SECTION 8: Productivity (12 tables)
SECTION 9: Health (12 tables)
SECTION 10: Car & Vehicle (7 tables)
SECTION 11: Learning (10 tables)
SECTION 12: Contacts (6 tables)
SECTION 13: Work & Career (6 tables)
SECTION 14: Credentials (4 tables)

TOTAL: 147 tables/views/materialized views

Key Features:
- pgvector for embeddings (1536 dimensions)
- Partitioned tables for time-series data
- Event sourcing for agent actions
- Comprehensive audit trail
- Self-updating timestamps
- Streak calculations for habits
- Financial projections and runway
- Cost optimization tracking
- A/B testing infrastructure
- Memory consolidation
- Knowledge graph support
*/
