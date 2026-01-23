-- ╔═══════════════════════════════════════════════════════════════════════════════╗
-- ║                    NEXUS SWARM COMMUNICATION TABLES                          ║
-- ║                                                                               ║
-- ║  Tables for elite coding swarms: Redis Pub/Sub integration, event bus,       ║
-- ║  consensus protocols (RAFT), and conflict resolution voting mechanisms.      ║
-- ║                                                                               ║
-- ║  Author: NEXUS Swarm System                                                  ║
-- ║  Created: January 2026                                                       ║
-- ║  Target: PostgreSQL 16 with pgvector                                         ║
-- ╚═══════════════════════════════════════════════════════════════════════════════╝

-- =============================================================================
-- SWARM DEFINITIONS
-- =============================================================================

-- 1. Swarms (Groups of agents working together)
CREATE TABLE swarms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    purpose VARCHAR(255),
    swarm_type VARCHAR(50) NOT NULL DEFAULT 'collaborative', -- 'collaborative', 'competitive', 'hierarchical'
    consensus_protocol VARCHAR(50) DEFAULT 'raft', -- 'raft', 'paxos', 'simple_majority'
    voting_threshold DECIMAL(3,2) DEFAULT 0.51, -- Minimum vote percentage for decisions
    max_members INTEGER DEFAULT 10,
    auto_scaling BOOLEAN DEFAULT true,
    health_check_interval_seconds INTEGER DEFAULT 30,
    leader_election_timeout_ms INTEGER DEFAULT 5000, -- For RAFT
    heartbeat_interval_ms INTEGER DEFAULT 1000, -- For RAFT
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- 2. Swarm Memberships (Agent participation in swarms)
CREATE TABLE swarm_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member', -- 'leader', 'follower', 'candidate', 'observer'
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'suspended', 'banned'
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    contribution_score DECIMAL(5,2) DEFAULT 0.0, -- Performance metric
    vote_weight DECIMAL(3,2) DEFAULT 1.0, -- Weight in voting (1.0 = equal)
    metadata JSONB DEFAULT '{}',
    UNIQUE(swarm_id, agent_id)
);

-- =============================================================================
-- CONSENSUS GROUPS (RAFT IMPLEMENTATION)
-- =============================================================================

-- 3. Consensus Groups (RAFT clusters within swarms)
CREATE TABLE consensus_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    group_name VARCHAR(100) NOT NULL,
    current_term BIGINT DEFAULT 0,
    voted_for UUID REFERENCES agents(id), -- Agent voted for in current term
    commit_index BIGINT DEFAULT 0,
    last_applied_index BIGINT DEFAULT 0,
    leader_id UUID REFERENCES agents(id), -- Current leader
    state VARCHAR(50) DEFAULT 'follower', -- 'leader', 'follower', 'candidate'
    election_timer_started_at TIMESTAMPTZ,
    heartbeat_timer_started_at TIMESTAMPTZ,
    last_heartbeat_received_at TIMESTAMPTZ,
    log_replication_lag_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(swarm_id, group_name)
);

-- 4. Consensus Log Entries (RAFT log)
CREATE TABLE consensus_log_entries (
    id BIGSERIAL PRIMARY KEY,
    consensus_group_id UUID REFERENCES consensus_groups(id) ON DELETE CASCADE,
    term BIGINT NOT NULL,
    index BIGINT NOT NULL,
    command_type VARCHAR(100) NOT NULL, -- 'task_assignment', 'config_change', 'membership'
    command_data JSONB NOT NULL,
    applied BOOLEAN DEFAULT false,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(consensus_group_id, term, index)
);

-- =============================================================================
-- VOTING & CONFLICT RESOLUTION
-- =============================================================================

-- 5. Votes (Conflict resolution voting records)
CREATE TABLE votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    consensus_group_id UUID REFERENCES consensus_groups(id) ON DELETE SET NULL,
    vote_type VARCHAR(50) NOT NULL, -- 'leader_election', 'task_assignment', 'conflict_resolution', 'config_change'
    subject VARCHAR(255) NOT NULL, -- What is being voted on
    description TEXT,
    options JSONB NOT NULL, -- Array of vote options with labels
    voting_strategy VARCHAR(50) DEFAULT 'simple_majority', -- 'simple_majority', 'super_majority', 'weighted'
    required_quorum DECIMAL(3,2) DEFAULT 0.51, -- Minimum participation
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'closed', 'cancelled', 'executed'
    created_by_agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    result JSONB, -- Winning option and metadata
    metadata JSONB DEFAULT '{}'
);

-- 6. Vote Responses (Individual agent votes)
CREATE TABLE vote_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vote_id UUID REFERENCES votes(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    option_selected VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- Agent's confidence in vote
    rationale TEXT,
    voted_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(vote_id, agent_id)
);

-- =============================================================================
-- SWARM MESSAGING (Redis Pub/Sub persistent storage)
-- =============================================================================

-- 7. Swarm Messages (Persistent message store)
CREATE TABLE swarm_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    sender_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    recipient_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    channel VARCHAR(255) NOT NULL, -- Redis Pub/Sub channel
    message_type VARCHAR(50) NOT NULL, -- 'direct', 'broadcast', 'multicast', 'event'
    content JSONB NOT NULL,
    priority INTEGER DEFAULT 1, -- 1-5, higher = more urgent
    ttl_seconds INTEGER DEFAULT 3600, -- Time-to-live for Redis caching
    delivered BOOLEAN DEFAULT false,
    delivered_at TIMESTAMPTZ,
    read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Swarm Events (Event bus persistent storage)
CREATE TABLE swarm_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- 'agent_joined', 'task_completed', 'conflict_detected', 'consensus_reached'
    event_data JSONB NOT NULL,
    source_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    propagation_path UUID[], -- Chain of agents that have propagated this event
    processed_by_agents UUID[], -- Agents that have processed this event
    is_global BOOLEAN DEFAULT false, -- Whether event is swarm-wide
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SWARM PERFORMANCE METRICS
-- =============================================================================

-- 9. Swarm Performance (Aggregate metrics)
CREATE TABLE swarm_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id UUID REFERENCES swarms(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_messages INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    consensus_decisions INTEGER DEFAULT 0,
    conflicts_detected INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    avg_decision_time_ms DECIMAL(10,2),
    message_delivery_success_rate DECIMAL(5,2),
    consensus_success_rate DECIMAL(5,2),
    member_activity_rate DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(swarm_id, date)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX idx_swarm_memberships_agent ON swarm_memberships(agent_id, status);
CREATE INDEX idx_swarm_memberships_swarm ON swarm_memberships(swarm_id, status);
CREATE INDEX idx_consensus_groups_leader ON consensus_groups(leader_id) WHERE leader_id IS NOT NULL;
CREATE INDEX idx_consensus_groups_state ON consensus_groups(state);
CREATE INDEX idx_consensus_log_entries_applied ON consensus_log_entries(applied) WHERE applied = false;
CREATE INDEX idx_votes_status ON votes(status, expires_at) WHERE status = 'open';
CREATE INDEX idx_vote_responses_agent ON vote_responses(agent_id, voted_at DESC);
CREATE INDEX idx_swarm_messages_channel ON swarm_messages(channel, created_at DESC);
CREATE INDEX idx_swarm_messages_recipient ON swarm_messages(recipient_agent_id, created_at DESC) WHERE recipient_agent_id IS NOT NULL;
CREATE INDEX idx_swarm_messages_delivered ON swarm_messages(delivered, created_at) WHERE delivered = false;
CREATE INDEX idx_swarm_events_type ON swarm_events(event_type, occurred_at DESC);
CREATE INDEX idx_swarm_events_swarm ON swarm_events(swarm_id, occurred_at DESC);
CREATE INDEX idx_swarm_events_global ON swarm_events(is_global, occurred_at DESC) WHERE is_global = true;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE swarms IS 'Groups of agents that can communicate and coordinate via swarm protocols';
COMMENT ON TABLE swarm_memberships IS 'Agent participation in swarms with roles and status';
COMMENT ON TABLE consensus_groups IS 'RAFT consensus groups within swarms for distributed decision-making';
COMMENT ON TABLE consensus_log_entries IS 'RAFT log entries for consensus replication';
COMMENT ON TABLE votes IS 'Voting records for conflict resolution and decision-making';
COMMENT ON TABLE vote_responses IS 'Individual agent votes on voting proposals';
COMMENT ON TABLE swarm_messages IS 'Persistent storage for Redis Pub/Sub messages';
COMMENT ON TABLE swarm_events IS 'Event bus persistent storage for swarm-wide events';
COMMENT ON TABLE swarm_performance IS 'Daily performance metrics for swarms';

-- =============================================================================
-- END OF SWARM COMMUNICATION SCHEMA
-- =============================================================================