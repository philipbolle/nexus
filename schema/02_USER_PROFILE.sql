-- NEXUS User Profile Schema
-- Extends the system with comprehensive user profiling and personalization

-- ============================================================================
-- USER PROFILES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE,  -- For future multi-user support
    email VARCHAR(255) UNIQUE,     -- Primary email

    -- Personal Information
    full_name VARCHAR(200),
    preferred_name VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'America/Chicago',
    location JSONB DEFAULT '{"city": "", "state": "", "country": "", "coordinates": null}'::jsonb,
    date_of_birth DATE,
    avatar_url TEXT,
    bio TEXT,

    -- Work Information
    work_status VARCHAR(50),  -- employed, self-employed, student, etc.
    employer_name VARCHAR(200),
    job_title VARCHAR(200),
    work_schedule JSONB,  -- {shift_type: "night", hours_per_week: 40, ...}

    -- Health Information (high-level)
    health_conditions JSONB DEFAULT '[]'::jsonb,  -- Array of condition names
    medications JSONB DEFAULT '[]'::jsonb,        -- Array of medication names
    health_goals JSONB DEFAULT '[]'::jsonb,       -- Array of health goals

    -- Financial Overview
    financial_status JSONB DEFAULT '{}'::jsonb,   -- {total_debt: 9700, monthly_income: ..., ...}

    -- Vehicle Information
    vehicles JSONB DEFAULT '[]'::jsonb,           -- Array of vehicle objects

    -- Preferences (quick-access, detailed preferences in preferences table)
    preferences JSONB DEFAULT '{}'::jsonb,        -- Top-level preferences

    -- Communication Style Preferences
    communication_style JSONB DEFAULT '{
        "formality": "casual",
        "detail_level": "balanced",
        "response_length": "concise",
        "use_emojis": true,
        "notification_preferences": {"email": false, "push": true, "sound": true}
    }'::jsonb,

    -- Learning & Adaptation
    learned_preferences JSONB DEFAULT '{}'::jsonb,  -- Preferences learned from interactions
    adaptation_score FLOAT DEFAULT 0.0,             -- How well system adapts to user

    -- System Metadata
    is_active BOOLEAN DEFAULT true,
    is_primary_user BOOLEAN DEFAULT false,  -- For single-user systems, mark primary
    last_active_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_location CHECK (location ? 'city' AND location ? 'country'),
    CONSTRAINT valid_communication_style CHECK (communication_style ? 'formality' AND communication_style ? 'detail_level')
);

-- ============================================================================
-- USER PREFERENCES EXTENSION
-- ============================================================================

-- Add user_id to preferences table for user-specific preferences
ALTER TABLE preferences
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'global' CHECK (scope IN ('global', 'user', 'agent', 'session')),
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS inherited_from UUID;

-- Create index for user-specific preference lookups
CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_preferences_scope ON preferences(scope);

-- Update unique constraint to include user_id for user-scoped preferences
ALTER TABLE preferences DROP CONSTRAINT IF EXISTS preferences_category_key_key;
ALTER TABLE preferences ADD CONSTRAINT preferences_category_key_user_unique
    UNIQUE(category, key, user_id)
    WHERE user_id IS NOT NULL;

-- Add global uniqueness for global preferences
ALTER TABLE preferences ADD CONSTRAINT preferences_category_key_global_unique
    UNIQUE(category, key)
    WHERE user_id IS NULL;

-- ============================================================================
-- USER MEMORY OWNERSHIP
-- ============================================================================

-- Add user_id to memories table to associate memories with users
ALTER TABLE memories
ADD COLUMN IF NOT EXISTS user_id UUID;

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);

-- Add user_id to memory_blocks table
ALTER TABLE memory_blocks
ADD COLUMN IF NOT EXISTS user_id UUID;

CREATE INDEX IF NOT EXISTS idx_memory_blocks_user_id ON memory_blocks(user_id);

-- ============================================================================
-- USER CONTEXT ENHANCEMENT
-- ============================================================================

-- Enhance user_context table with more fields if it exists
DO $$
BEGIN
    -- Check if user_context table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_context') THEN
        -- Add user profile reference if not exists
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'user_context' AND column_name = 'user_profile_id') THEN
            ALTER TABLE user_context ADD COLUMN user_profile_id UUID REFERENCES user_profiles(id);
        END IF;

        -- Add context type for better organization
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'user_context' AND column_name = 'context_type') THEN
            ALTER TABLE user_context ADD COLUMN context_type VARCHAR(50) DEFAULT 'general';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- DEFAULT USER PROFILE CREATION
-- ============================================================================

-- Create default user profile for Philip (single-user system)
INSERT INTO user_profiles (
    username,
    email,
    full_name,
    preferred_name,
    timezone,
    location,
    work_status,
    employer_name,
    work_schedule,
    financial_status,
    vehicles,
    is_primary_user,
    communication_style
) VALUES (
    'philip',
    NULL, -- Email can be added later
    'Philip',
    'Philip',
    'America/Chicago',
    '{"city": "Texas", "country": "USA"}'::jsonb,
    'employed',
    'BMR Janitorial Services',
    '{"shift_type": "night", "hours_per_week": 40}'::jsonb,
    '{"total_debt": 9700, "debt_goal": "payoff", "budget_tight": true}'::jsonb,
    '[{"year": 2011, "make": "Hyundai", "model": "Sonata", "nickname": "Sonata"}]'::jsonb,
    true,
    '{"formality": "casual", "detail_level": "balanced", "response_length": "concise", "use_emojis": true, "notification_preferences": {"email": false, "push": true, "sound": true}}'::jsonb
) ON CONFLICT (username) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    timezone = EXCLUDED.timezone,
    location = EXCLUDED.location,
    work_status = EXCLUDED.work_status,
    employer_name = EXCLUDED.employer_name,
    work_schedule = EXCLUDED.work_schedule,
    financial_status = EXCLUDED.financial_status,
    vehicles = EXCLUDED.vehicles,
    communication_style = EXCLUDED.communication_style,
    updated_at = NOW();

-- ============================================================================
-- MIGRATE EXISTING USER DATA FROM SYSTEM_CONFIG
-- ============================================================================

-- Function to migrate user data from system_config to user_profiles
CREATE OR REPLACE FUNCTION migrate_user_data_from_system_config()
RETURNS void AS $$
DECLARE
    user_name TEXT;
    user_timezone TEXT;
    user_location JSONB;
    user_profile_id UUID;
BEGIN
    -- Get existing user data from system_config
    SELECT value::TEXT INTO user_name
    FROM system_config WHERE key = 'user.name';

    SELECT value::TEXT INTO user_timezone
    FROM system_config WHERE key = 'user.timezone';

    SELECT value::JSONB INTO user_location
    FROM system_config WHERE key = 'user.location';

    -- Get or create user profile
    SELECT id INTO user_profile_id FROM user_profiles WHERE username = 'philip';

    IF user_profile_id IS NULL THEN
        INSERT INTO user_profiles (username, full_name, timezone, location, is_primary_user)
        VALUES ('philip',
                COALESCE(user_name, 'Philip'),
                COALESCE(user_timezone, 'America/Chicago'),
                COALESCE(user_location, '{"city": "Texas", "country": "USA"}'::jsonb),
                true)
        RETURNING id INTO user_profile_id;
    ELSE
        -- Update existing profile with system_config data
        UPDATE user_profiles SET
            full_name = COALESCE(user_name, full_name),
            timezone = COALESCE(user_timezone, timezone),
            location = COALESCE(user_location, location),
            updated_at = NOW()
        WHERE id = user_profile_id;
    END IF;

    RAISE NOTICE 'Migrated user data from system_config to user_profiles (profile_id: %)', user_profile_id;
END;
$$ LANGUAGE plpgsql;

-- Execute migration
SELECT migrate_user_data_from_system_config();

-- Drop the migration function after use
DROP FUNCTION migrate_user_data_from_system_config();

-- ============================================================================
-- VIEWS FOR EASY ACCESS
-- ============================================================================

-- View for complete user profile with preferences
CREATE OR REPLACE VIEW v_user_profile_complete AS
SELECT
    up.*,
    (
        SELECT jsonb_object_agg(
            p.category || '.' || p.key,
            p.value
        )
        FROM preferences p
        WHERE p.user_id = up.id OR (p.user_id IS NULL AND p.scope = 'global')
        AND p.scope IN ('global', 'user')
    ) as all_preferences,
    (
        SELECT COUNT(*) FROM memories m WHERE m.user_id = up.id
    ) as memory_count,
    (
        SELECT COUNT(*) FROM memory_blocks mb WHERE mb.user_id = up.id
    ) as memory_block_count
FROM user_profiles up
WHERE up.is_primary_user = true OR up.is_active = true;

-- View for user communication preferences
CREATE OR REPLACE VIEW v_user_communication_prefs AS
SELECT
    up.id,
    up.username,
    up.preferred_name,
    up.communication_style->>'formality' as formality,
    up.communication_style->>'detail_level' as detail_level,
    up.communication_style->>'response_length' as response_length,
    (up.communication_style->>'use_emojis')::boolean as use_emojis,
    up.communication_style->'notification_preferences' as notification_prefs
FROM user_profiles up
WHERE up.is_active = true;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_profiles_is_primary ON user_profiles(is_primary_user) WHERE is_primary_user = true;
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_communication_style ON user_profiles USING GIN (communication_style);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE user_profiles IS 'Comprehensive user profiles for personalization and adaptation';
COMMENT ON COLUMN user_profiles.preferences IS 'Quick-access preferences (detailed preferences in preferences table)';
COMMENT ON COLUMN user_profiles.communication_style IS 'User communication preferences for AI interactions';
COMMENT ON COLUMN user_profiles.learned_preferences IS 'Preferences learned from user interactions over time';
COMMENT ON COLUMN user_profiles.adaptation_score IS 'Score from 0-1 indicating how well system adapts to user (higher = better adaptation)';

COMMENT ON TABLE preferences IS 'Extended preferences table with user-scoping support';
COMMENT ON COLUMN preferences.user_id IS 'User ID for user-specific preferences (NULL for global preferences)';
COMMENT ON COLUMN preferences.scope IS 'Scope: global, user, agent, session';
COMMENT ON COLUMN preferences.priority IS 'Priority for conflict resolution (higher = more important)';
COMMENT ON COLUMN preferences.inherited_from IS 'Reference to preference this was inherited from';

COMMENT ON VIEW v_user_profile_complete IS 'Complete user profile with aggregated preferences and memory counts';
COMMENT ON VIEW v_user_communication_prefs IS 'User communication preferences for AI personalization';