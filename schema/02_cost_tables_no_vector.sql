-- Cost Optimization Tables (without vector extension for now)
-- ============================================================================

-- Cost Optimization Tables Extracted from 00_NEXUS_ULTIMATE_SCHEMA.sql
-- ============================================================================

CREATE TABLE semantic_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_embedding real[], -- all-MiniLM-L6-v2 dimension
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

CREATE TABLE embedding_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    content_preview TEXT, -- First 500 chars
    embedding real[], -- OpenAI text-embedding-3-small dimension
    embedding_model VARCHAR(100) NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 1
);

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

CREATE TABLE api_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    provider_id UUID,
    model_id UUID,
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

CREATE TABLE batch_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    provider_id UUID,
    model_id UUID,
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

