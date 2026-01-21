-- ╔═══════════════════════════════════════════════════════════════════════════════╗
-- ║                    NEXUS EVOLUTION SYSTEM TABLES                              ║
-- ║                                                                               ║
-- ║  Tables for self-evolution system: hypothesis generation, A/B testing,        ║
-- ║  code refactoring, performance analysis, and bottleneck detection.            ║
-- ║                                                                               ║
-- ║  Author: NEXUS Evolution System                                               ║
-- ║  Created: January 2026                                                        ║
-- ║  Target: PostgreSQL 16 with pgvector                                         ║
-- ╚═══════════════════════════════════════════════════════════════════════════════╝

-- =============================================================================
-- EVOLUTION HYPOTHESES
-- =============================================================================

CREATE TABLE evolution_hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL, -- 'performance', 'cost', 'reliability', 'maintainability'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT NOT NULL,
    expected_impact VARCHAR(20) CHECK (expected_impact IN ('low', 'medium', 'high', 'critical')),
    implementation_complexity VARCHAR(20) CHECK (implementation_complexity IN ('low', 'medium', 'high', 'very_high')),
    estimated_effort_hours INTEGER CHECK (estimated_effort_hours > 0),
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    metrics_to_monitor TEXT[], -- Array of metric names to monitor
    validation_criteria TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'implemented', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- REFACTORING PROPOSALS
-- =============================================================================

CREATE TABLE refactoring_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL, -- 'code_refactor', 'prompt_optimization', 'config_tuning', 'architecture_change'
    target_file VARCHAR(500) NOT NULL,
    target_component VARCHAR(200) NOT NULL,
    rationale TEXT NOT NULL,
    expected_improvement VARCHAR(20) CHECK (expected_improvement IN ('low', 'medium', 'high', 'critical')),
    hypothesis_id UUID REFERENCES evolution_hypotheses(id) ON DELETE SET NULL,
    analysis JSONB NOT NULL,
    proposed_changes JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'applied', 'reverted', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ,
    reverted_at TIMESTAMPTZ,
    validation_results JSONB DEFAULT '{}',
    rollback_path TEXT -- Path to backup or rollback script
);

-- =============================================================================
-- EXPERIMENT ASSIGNMENTS
-- =============================================================================

CREATE TABLE experiment_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID REFERENCES agent_experiments(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL, -- Could be agent_id, session_id, user_id, etc.
    entity_type VARCHAR(50) NOT NULL, -- 'agent', 'session', 'user', 'request'
    assignment_group VARCHAR(20) NOT NULL CHECK (assignment_group IN ('control', 'treatment')),
    config JSONB DEFAULT '{}',
    assigned_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint to prevent duplicate assignments
    UNIQUE (experiment_id, entity_id, entity_type)
);

-- =============================================================================
-- EXPERIMENT STATISTICS
-- =============================================================================

CREATE TABLE experiment_stats (
    experiment_id UUID REFERENCES agent_experiments(id) ON DELETE CASCADE,
    assignment_group VARCHAR(20) NOT NULL CHECK (assignment_group IN ('control', 'treatment')),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    assignment_count INTEGER DEFAULT 0,

    -- Composite primary key
    PRIMARY KEY (experiment_id, assignment_group, date)
);

-- =============================================================================
-- EXPERIMENT METRICS
-- =============================================================================

CREATE TABLE experiment_metrics (
    id BIGSERIAL PRIMARY KEY,
    experiment_id UUID REFERENCES agent_experiments(id) ON DELETE CASCADE,
    assignment_group VARCHAR(20) NOT NULL CHECK (assignment_group IN ('control', 'treatment')),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN,
    latency_ms DECIMAL(10,2),
    cost_usd DECIMAL(10,6),
    entity_id UUID,
    entity_type VARCHAR(50),
    additional_metrics JSONB DEFAULT '{}'
);

-- =============================================================================
-- BOTTLENECK PATTERNS
-- =============================================================================

CREATE TABLE bottleneck_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(50) NOT NULL, -- 'performance', 'cost', 'reliability', 'scalability'
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    detection_count INTEGER DEFAULT 1,
    first_detected TIMESTAMPTZ DEFAULT NOW(),
    last_detected TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    pattern_signature TEXT NOT NULL, -- JSON or text signature of the pattern
    affected_components TEXT[], -- Array of affected component names
    recurring_interval INTERVAL -- If pattern recurs regularly
);

-- =============================================================================
-- EVOLUTION ANALYSIS RESULTS
-- =============================================================================

CREATE TABLE evolution_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type VARCHAR(50) NOT NULL, -- 'performance', 'cost', 'reliability', 'trend'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    metrics_analyzed INTEGER DEFAULT 0,
    bottlenecks_found INTEGER DEFAULT 0,
    recommendations_generated INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    analysis_results JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CODE QUALITY METRICS
-- =============================================================================

CREATE TABLE code_quality_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    component VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metadata JSONB DEFAULT '{}',
    UNIQUE (component, metric_name, timestamp)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- evolution_hypotheses indexes
CREATE INDEX idx_evolution_hypotheses_status ON evolution_hypotheses(status);
CREATE INDEX idx_evolution_hypotheses_type ON evolution_hypotheses(type);
CREATE INDEX idx_evolution_hypotheses_created_at ON evolution_hypotheses(created_at DESC);

-- refactoring_proposals indexes
CREATE INDEX idx_refactoring_proposals_hypothesis_id ON refactoring_proposals(hypothesis_id);
CREATE INDEX idx_refactoring_proposals_status ON refactoring_proposals(status);
CREATE INDEX idx_refactoring_proposals_created_at ON refactoring_proposals(created_at DESC);

-- experiment_assignments indexes
CREATE INDEX idx_experiment_assignments_experiment_id ON experiment_assignments(experiment_id);
CREATE INDEX idx_experiment_assignments_entity ON experiment_assignments(entity_id, entity_type);
CREATE INDEX idx_experiment_assignments_assigned_at ON experiment_assignments(assigned_at DESC);

-- experiment_stats indexes
CREATE INDEX idx_experiment_stats_date ON experiment_stats(date DESC);

-- experiment_metrics indexes
CREATE INDEX idx_experiment_metrics_experiment_group ON experiment_metrics(experiment_id, assignment_group);
CREATE INDEX idx_experiment_metrics_timestamp ON experiment_metrics(timestamp DESC);
CREATE INDEX idx_experiment_metrics_success ON experiment_metrics(success);

-- bottleneck_patterns indexes
CREATE INDEX idx_bottleneck_patterns_severity ON bottleneck_patterns(severity);
CREATE INDEX idx_bottleneck_patterns_resolved ON bottleneck_patterns(resolved);
CREATE INDEX idx_bottleneck_patterns_last_detected ON bottleneck_patterns(last_detected DESC);

-- evolution_analysis indexes
CREATE INDEX idx_evolution_analysis_type ON evolution_analysis(analysis_type);
CREATE INDEX idx_evolution_analysis_created_at ON evolution_analysis(created_at DESC);
CREATE INDEX idx_evolution_analysis_date_range ON evolution_analysis(start_date, end_date);

-- code_quality_metrics indexes
CREATE INDEX idx_code_quality_metrics_component ON code_quality_metrics(component);
CREATE INDEX idx_code_quality_metrics_timestamp ON code_quality_metrics(timestamp DESC);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================================================

-- Create function to update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to evolution_hypotheses
DROP TRIGGER IF EXISTS update_evolution_hypotheses_updated_at ON evolution_hypotheses;
CREATE TRIGGER update_evolution_hypotheses_updated_at
    BEFORE UPDATE ON evolution_hypotheses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS FOR EVOLUTION SYSTEM (created after tables exist)
-- =============================================================================

-- View for active hypotheses with related data
CREATE OR REPLACE VIEW active_hypotheses AS
SELECT
    h.id,
    h.type,
    h.title,
    h.status,
    h.expected_impact,
    h.implementation_complexity,
    h.estimated_effort_hours,
    h.risk_level,
    h.created_at,
    COUNT(DISTINCT r.id) as related_refactorings,
    COUNT(DISTINCT e.id) as related_experiments
FROM evolution_hypotheses h
LEFT JOIN refactoring_proposals r ON r.hypothesis_id = h.id
LEFT JOIN agent_experiments e ON e.hypothesis = h.id::text
WHERE h.status IN ('pending', 'approved')
GROUP BY h.id;

-- View for experiment performance comparison (requires experiment_metrics)
CREATE OR REPLACE VIEW experiment_performance_comparison AS
SELECT
    e.id as experiment_id,
    e.name as experiment_name,
    e.status,
    e.start_time,
    e.end_time,
    COALESCE(control_metrics.request_count, 0) as control_requests,
    COALESCE(treatment_metrics.request_count, 0) as treatment_requests,
    COALESCE(control_metrics.success_rate, 0) as control_success_rate,
    COALESCE(treatment_metrics.success_rate, 0) as treatment_success_rate,
    COALESCE(control_metrics.avg_latency, 0) as control_avg_latency,
    COALESCE(treatment_metrics.avg_latency, 0) as treatment_avg_latency,
    COALESCE(control_metrics.total_cost, 0) as control_total_cost,
    COALESCE(treatment_metrics.total_cost, 0) as treatment_total_cost
FROM agent_experiments e
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) as request_count,
        AVG(success::int) as success_rate,
        AVG(latency_ms) as avg_latency,
        SUM(cost_usd) as total_cost
    FROM experiment_metrics
    WHERE experiment_id = e.id AND assignment_group = 'control'
    GROUP BY experiment_id, assignment_group
) control_metrics ON true
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) as request_count,
        AVG(success::int) as success_rate,
        AVG(latency_ms) as avg_latency,
        SUM(cost_usd) as total_cost
    FROM experiment_metrics
    WHERE experiment_id = e.id AND assignment_group = 'treatment'
    GROUP BY experiment_id, assignment_group
) treatment_metrics ON true
WHERE e.status IN ('running', 'completed');

-- =============================================================================
-- GRANT PERMISSIONS (Adjust based on your security requirements)
-- =============================================================================

-- Example: GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nexus_app;