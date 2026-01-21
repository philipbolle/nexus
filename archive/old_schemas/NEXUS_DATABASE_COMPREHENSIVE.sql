-- ============================================================================
-- NEXUS COMPREHENSIVE DATABASE SCHEMA v2.0
-- Philip's Autonomous AI Operating System
-- 50+ Tables for Complete Life Management
-- ============================================================================

-- ============================================================================
-- CORE SYSTEM TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    model_preference VARCHAR(50) DEFAULT 'deepseek',
    capabilities TEXT[],
    priority INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0',
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_id INTEGER REFERENCES agents(id),
    context_extracted JSONB,
    source VARCHAR(50) DEFAULT 'iphone',
    tokens_used INTEGER,
    model_used VARCHAR(100),
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_context (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(100),
    learned_from_conversation_id INTEGER REFERENCES conversations(id),
    confirmed_by_user BOOLEAN DEFAULT false,
    conflicts_with INTEGER REFERENCES user_context(id),
    importance INTEGER DEFAULT 5,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS agent_collaborations (
    id SERIAL PRIMARY KEY,
    initiator_agent_id INTEGER REFERENCES agents(id),
    collaborator_agent_id INTEGER REFERENCES agents(id),
    conversation_id INTEGER REFERENCES conversations(id),
    task_description TEXT,
    shared_context JSONB,
    outcome VARCHAR(50),
    insights_gained TEXT[],
    duration_seconds INTEGER,
    success_rating INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_learnings (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    learning_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    trigger_conversation_id INTEGER REFERENCES conversations(id),
    applied BOOLEAN DEFAULT false,
    applied_at TIMESTAMP,
    effectiveness_rating INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_performance (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    average_latency_ms DECIMAL(10, 2),
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10, 4),
    user_satisfaction_avg DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, date)
);

CREATE TABLE IF NOT EXISTS agent_suggestions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    suggestion_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    user_response VARCHAR(20),
    implemented_at TIMESTAMP,
    effectiveness_rating INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- FINANCE DOMAIN (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    institution VARCHAR(100),
    account_number_last4 VARCHAR(4),
    balance DECIMAL(12, 2) DEFAULT 0,
    available_balance DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT true,
    interest_rate DECIMAL(5, 2),
    minimum_balance DECIMAL(12, 2),
    overdraft_protection BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    amount DECIMAL(12, 2) NOT NULL,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    merchant VARCHAR(100),
    description TEXT,
    date DATE NOT NULL,
    time TIME,
    is_recurring BOOLEAN DEFAULT false,
    recurring_id INTEGER,
    tags TEXT[],
    receipt_url TEXT,
    location POINT,
    logged_via VARCHAR(50) DEFAULT 'manual',
    agent_notes TEXT,
    is_necessary BOOLEAN,
    emotional_trigger TEXT,
    could_have_saved DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budgets (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    monthly_limit DECIMAL(12, 2) NOT NULL,
    weekly_limit DECIMAL(12, 2),
    rollover BOOLEAN DEFAULT false,
    rollover_amount DECIMAL(12, 2) DEFAULT 0,
    alert_threshold DECIMAL(3, 2) DEFAULT 0.80,
    alert_enabled BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS debts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    creditor VARCHAR(100) NOT NULL,
    original_amount DECIMAL(12, 2) NOT NULL,
    current_balance DECIMAL(12, 2) NOT NULL,
    interest_rate DECIMAL(5, 2) DEFAULT 0,
    minimum_payment DECIMAL(12, 2),
    due_day INTEGER,
    start_date DATE,
    target_payoff_date DATE,
    actual_payoff_date DATE,
    payment_plan_type VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS debt_payments (
    id SERIAL PRIMARY KEY,
    debt_id INTEGER REFERENCES debts(id),
    amount DECIMAL(12, 2) NOT NULL,
    principal DECIMAL(12, 2),
    interest DECIMAL(12, 2),
    date DATE NOT NULL,
    method VARCHAR(50),
    confirmation VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recurring_bills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    frequency VARCHAR(20) NOT NULL,
    due_day INTEGER,
    account_id INTEGER REFERENCES accounts(id),
    auto_pay BOOLEAN DEFAULT false,
    reminder_days INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT true,
    last_payment_date DATE,
    next_payment_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(12, 2) NOT NULL,
    current_amount DECIMAL(12, 2) DEFAULT 0,
    target_date DATE,
    priority INTEGER DEFAULT 5,
    category VARCHAR(50),
    monthly_contribution DECIMAL(12, 2),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS income_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    amount DECIMAL(12, 2),
    frequency VARCHAR(20),
    account_id INTEGER REFERENCES accounts(id),
    is_active BOOLEAN DEFAULT true,
    tax_rate DECIMAL(5, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_snapshots (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_assets DECIMAL(12, 2),
    total_liabilities DECIMAL(12, 2),
    net_worth DECIMAL(12, 2),
    liquid_cash DECIMAL(12, 2),
    investments DECIMAL(12, 2),
    monthly_income DECIMAL(12, 2),
    monthly_expenses DECIMAL(12, 2),
    savings_rate DECIMAL(5, 2),
    debt_to_income_ratio DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- HEALTH DOMAIN (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS health_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    weight_lbs DECIMAL(5, 1),
    body_fat_pct DECIMAL(4, 1),
    muscle_mass_lbs DECIMAL(5, 1),
    bmi DECIMAL(4, 1),
    sleep_hours DECIMAL(3, 1),
    sleep_quality INTEGER,
    sleep_deep_hours DECIMAL(3, 1),
    sleep_rem_hours DECIMAL(3, 1),
    energy_level INTEGER,
    mood INTEGER,
    stress_level INTEGER,
    anxiety_level INTEGER,
    water_oz INTEGER,
    steps INTEGER,
    active_calories INTEGER,
    resting_calories INTEGER,
    resting_heart_rate INTEGER,
    hrv_ms INTEGER,
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    oxygen_saturation INTEGER,
    temperature_f DECIMAL(4, 1),
    notes TEXT,
    data_source VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(100),
    duration_minutes INTEGER,
    calories_burned INTEGER,
    heart_rate_avg INTEGER,
    heart_rate_max INTEGER,
    intensity VARCHAR(20),
    perceived_exertion INTEGER,
    notes TEXT,
    source VARCHAR(50) DEFAULT 'manual',
    source_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workout_exercises (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER REFERENCES workouts(id),
    exercise_name VARCHAR(100) NOT NULL,
    sets INTEGER,
    reps INTEGER,
    weight_lbs DECIMAL(5, 1),
    duration_seconds INTEGER,
    distance_miles DECIMAL(5, 2),
    rest_seconds INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS supplements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    dosage VARCHAR(50),
    unit VARCHAR(20),
    purpose TEXT,
    timing VARCHAR(50),
    frequency VARCHAR(50) DEFAULT 'daily',
    current_stock INTEGER DEFAULT 0,
    reorder_threshold INTEGER DEFAULT 10,
    cost_per_unit DECIMAL(6, 2),
    supplier VARCHAR(100),
    last_purchased DATE,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplement_logs (
    id SERIAL PRIMARY KEY,
    supplement_id INTEGER REFERENCES supplements(id),
    taken_at TIMESTAMP DEFAULT NOW(),
    dosage VARCHAR(50),
    skipped BOOLEAN DEFAULT false,
    skip_reason TEXT,
    side_effects TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS nutrition (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    meal_time TIME,
    meal_type VARCHAR(20) NOT NULL,
    food_name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    serving_size VARCHAR(50),
    servings DECIMAL(4, 2) DEFAULT 1,
    calories INTEGER,
    protein_g DECIMAL(5, 1),
    carbs_g DECIMAL(5, 1),
    fat_g DECIMAL(5, 1),
    fiber_g DECIMAL(5, 1),
    sodium_mg INTEGER,
    sugar_g DECIMAL(5, 1),
    cholesterol_mg INTEGER,
    is_inflammatory BOOLEAN DEFAULT false,
    inflammatory_score INTEGER,
    cost_usd DECIMAL(6, 2),
    location VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_symptoms (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time TIME,
    symptom VARCHAR(100) NOT NULL,
    severity INTEGER,
    duration_hours DECIMAL(4, 1),
    body_location VARCHAR(100),
    possible_triggers TEXT[],
    taken_medication TEXT[],
    improvement_notes TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medical_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    type VARCHAR(50) NOT NULL,
    provider VARCHAR(100),
    specialty VARCHAR(100),
    diagnosis TEXT,
    treatment TEXT,
    medications TEXT[],
    test_results JSONB,
    follow_up_date DATE,
    documents TEXT[],
    cost DECIMAL(10, 2),
    insurance_covered DECIMAL(10, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS esophagitis_triggers (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time TIME,
    trigger_food VARCHAR(100),
    trigger_drink VARCHAR(100),
    other_trigger VARCHAR(100),
    reaction_severity INTEGER,
    time_to_reaction_hours DECIMAL(4, 1),
    duration_hours DECIMAL(4, 1),
    relief_method TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lung_health (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    peak_flow INTEGER,
    coughing_frequency VARCHAR(20),
    mucus_production VARCHAR(20),
    mucus_color VARCHAR(50),
    shortness_of_breath VARCHAR(20),
    exercise_tolerance VARCHAR(50),
    wheezing BOOLEAN DEFAULT false,
    chest_tightness INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CAR DOMAIN (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    vin VARCHAR(17),
    license_plate VARCHAR(20),
    color VARCHAR(30),
    purchase_date DATE,
    purchase_price DECIMAL(10, 2),
    current_mileage INTEGER,
    current_value DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mileage_logs (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    odometer INTEGER NOT NULL,
    date DATE NOT NULL,
    time TIME,
    trip_purpose VARCHAR(100),
    trip_miles DECIMAL(6, 1),
    start_location VARCHAR(200),
    end_location VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fuel_logs (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    date DATE NOT NULL,
    odometer INTEGER,
    gallons DECIMAL(5, 2) NOT NULL,
    price_per_gallon DECIMAL(4, 2) NOT NULL,
    total_cost DECIMAL(6, 2) NOT NULL,
    station VARCHAR(100),
    station_location VARCHAR(200),
    fuel_type VARCHAR(20) DEFAULT 'regular',
    full_tank BOOLEAN DEFAULT true,
    mpg_calculated DECIMAL(4, 1),
    trip_miles DECIMAL(6, 1),
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maintenance_schedule (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    service_type VARCHAR(100) NOT NULL,
    interval_miles INTEGER,
    interval_months INTEGER,
    last_performed_date DATE,
    last_performed_mileage INTEGER,
    next_due_date DATE,
    next_due_mileage INTEGER,
    estimated_cost DECIMAL(8, 2),
    priority VARCHAR(20) DEFAULT 'normal',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maintenance_history (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    schedule_id INTEGER REFERENCES maintenance_schedule(id),
    date DATE NOT NULL,
    mileage INTEGER NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    description TEXT,
    provider VARCHAR(100),
    location VARCHAR(200),
    cost DECIMAL(8, 2),
    parts_cost DECIMAL(8, 2),
    labor_cost DECIMAL(8, 2),
    warranty BOOLEAN DEFAULT false,
    warranty_expires DATE,
    receipt_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vehicle_insurance (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    provider VARCHAR(100) NOT NULL,
    policy_number VARCHAR(50),
    coverage_type VARCHAR(50),
    monthly_premium DECIMAL(8, 2),
    deductible DECIMAL(8, 2),
    coverage_limits JSONB,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    documents TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vehicle_registration (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id),
    type VARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    cost DECIMAL(6, 2),
    renewal_reminder_days INTEGER DEFAULT 30,
    completed BOOLEAN DEFAULT false,
    completed_date DATE,
    confirmation VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- LEARNING DOMAIN (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS learning_sessions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    topic VARCHAR(100) NOT NULL,
    subtopic VARCHAR(100),
    duration_minutes INTEGER NOT NULL,
    method VARCHAR(50),
    resource VARCHAR(255),
    resource_url TEXT,
    focus_rating INTEGER,
    comprehension_rating INTEGER,
    enjoyment_rating INTEGER,
    notes TEXT,
    commands_practiced TEXT[],
    errors_encountered TEXT[],
    questions TEXT[],
    breakthroughs TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_analysis (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES learning_sessions(id),
    weak_areas TEXT[],
    strong_areas TEXT[],
    suggested_topics TEXT[],
    difficulty_assessment VARCHAR(20),
    progress_notes TEXT,
    ai_model VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS curriculum (
    id SERIAL PRIMARY KEY,
    path_name VARCHAR(100) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    subtopics JSONB,
    order_index INTEGER NOT NULL,
    estimated_hours INTEGER,
    status VARCHAR(20) DEFAULT 'not_started',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    proficiency_level INTEGER,
    prerequisites INTEGER[],
    resources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS podcasts (
    id SERIAL PRIMARY KEY,
    episode_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    script TEXT,
    duration_seconds INTEGER,
    file_path VARCHAR(255),
    file_size_mb DECIMAL(6, 2),
    generated_at TIMESTAMP DEFAULT NOW(),
    listened BOOLEAN DEFAULT false,
    listened_at TIMESTAMP,
    rating INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'multiple_choice',
    options JSONB,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    difficulty INTEGER,
    source_session_id INTEGER REFERENCES learning_sessions(id),
    times_asked INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    topic VARCHAR(100),
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    time_taken_seconds INTEGER,
    questions_answered JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    proficiency INTEGER,
    last_practiced DATE,
    total_hours DECIMAL(8, 1) DEFAULT 0,
    certification VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_resources (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    url TEXT,
    type VARCHAR(50),
    topic VARCHAR(100),
    status VARCHAR(20) DEFAULT 'saved',
    rating INTEGER,
    notes TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- PLANNING DOMAIN (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    target_value DECIMAL(12, 2),
    current_value DECIMAL(12, 2) DEFAULT 0,
    unit VARCHAR(50),
    start_date DATE,
    target_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 5,
    parent_goal_id INTEGER REFERENCES goals(id),
    motivation TEXT,
    obstacles TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goal_progress (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER REFERENCES goals(id),
    date DATE NOT NULL,
    value DECIMAL(12, 2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'medium',
    due_date DATE,
    due_time TIME,
    status VARCHAR(20) DEFAULT 'pending',
    goal_id INTEGER REFERENCES goals(id),
    recurring_pattern VARCHAR(50),
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    tags TEXT[],
    dependencies INTEGER[],
    completed_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    frequency VARCHAR(20) NOT NULL,
    target_count INTEGER DEFAULT 1,
    time_of_day VARCHAR(20),
    reminder_time TIME,
    streak_current INTEGER DEFAULT 0,
    streak_longest INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habit_completions (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER REFERENCES habits(id),
    date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(habit_id, date)
);

-- ============================================================================
-- WORK DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS work_shifts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    hours_worked DECIMAL(4, 2),
    hourly_rate DECIMAL(6, 2),
    gross_pay DECIMAL(8, 2),
    shift_type VARCHAR(50),
    location VARCHAR(100),
    supervisor VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pay_periods (
    id SERIAL PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    gross_pay DECIMAL(10, 2),
    net_pay DECIMAL(10, 2),
    taxes_withheld DECIMAL(8, 2),
    deductions JSONB,
    pay_date DATE,
    payment_method VARCHAR(50),
    confirmation VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS time_off (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hours DECIMAL(5, 2),
    status VARCHAR(20) DEFAULT 'pending',
    approved_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- COMMUNICATION DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    birthday DATE,
    notes TEXT,
    last_contact DATE,
    contact_frequency VARCHAR(20),
    importance INTEGER,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contact_interactions (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    date DATE NOT NULL,
    type VARCHAR(50),
    duration_minutes INTEGER,
    notes TEXT,
    sentiment VARCHAR(20),
    follow_up_needed BOOLEAN DEFAULT false,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    account VARCHAR(100) NOT NULL,
    message_id VARCHAR(255) UNIQUE,
    thread_id VARCHAR(255),
    from_address VARCHAR(255),
    to_addresses TEXT[],
    subject VARCHAR(500),
    body_preview TEXT,
    received_at TIMESTAMP,
    is_read BOOLEAN DEFAULT false,
    is_important BOOLEAN DEFAULT false,
    labels TEXT[],
    category VARCHAR(50),
    ai_summary TEXT,
    requires_action BOOLEAN DEFAULT false,
    action_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_drafts (
    id SERIAL PRIMARY KEY,
    account VARCHAR(100) NOT NULL,
    to_addresses TEXT[] NOT NULL,
    cc_addresses TEXT[],
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    reply_to_id INTEGER REFERENCES emails(id),
    created_by_agent VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending_approval',
    approved_at TIMESTAMP,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- SYSTEM MONITORING (Comprehensive)
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    endpoint VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    latency_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    query_hash VARCHAR(64),
    agent_id INTEGER REFERENCES agents(id),
    conversation_id INTEGER REFERENCES conversations(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    channel VARCHAR(50) NOT NULL,
    topic VARCHAR(100),
    title VARCHAR(255),
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'default',
    tags TEXT[],
    click_url TEXT,
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered BOOLEAN DEFAULT false,
    clicked BOOLEAN DEFAULT false,
    agent_id INTEGER REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    cpu_percent DECIMAL(5, 2),
    memory_used_mb INTEGER,
    memory_total_mb INTEGER,
    disk_used_gb DECIMAL(6, 2),
    disk_total_gb DECIMAL(6, 2),
    docker_containers_running INTEGER,
    api_requests_last_hour INTEGER,
    active_agents INTEGER,
    uptime_seconds INTEGER
);

CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    service VARCHAR(50) NOT NULL,
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    context JSONB,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);

CREATE TABLE IF NOT EXISTS backup_logs (
    id SERIAL PRIMARY KEY,
    backup_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    file_path TEXT,
    file_size_mb DECIMAL(10, 2),
    duration_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    action_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    performed_by VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS privacy_shield_logs (
    id SERIAL PRIMARY KEY,
    original_query_hash VARCHAR(64),
    secrets_detected TEXT[],
    redacted_query TEXT,
    external_provider VARCHAR(50),
    secrets_reinjected BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50),
    is_system BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- CREDENTIALS (Encrypted)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    username_encrypted BYTEA,
    password_encrypted BYTEA,
    url TEXT,
    notes_encrypted BYTEA,
    totp_secret_encrypted BYTEA,
    last_used TIMESTAMP,
    last_changed TIMESTAMP,
    expiry_date DATE,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES (Performance Optimization)
-- ============================================================================

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_agent ON conversations(agent_id);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX idx_user_context_category ON user_context(category, key);
CREATE INDEX idx_user_context_source ON user_context(source);
CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_health_daily_date ON health_daily(date DESC);
CREATE INDEX idx_workouts_date ON workouts(date DESC);
CREATE INDEX idx_nutrition_date ON nutrition(date DESC);
CREATE INDEX idx_mileage_logs_date ON mileage_logs(date DESC);
CREATE INDEX idx_learning_sessions_date ON learning_sessions(date DESC);
CREATE INDEX idx_api_usage_created ON api_usage(created_at DESC);
CREATE INDEX idx_api_usage_provider ON api_usage(provider, model);
CREATE INDEX idx_agent_performance_date ON agent_performance(date DESC);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_goals_status ON goals(status);

-- ============================================================================
-- VIEWS (Common Queries)
-- ============================================================================

CREATE OR REPLACE VIEW v_budget_status AS
SELECT 
    b.category,
    b.monthly_limit,
    COALESCE(SUM(t.amount), 0) AS spent,
    b.monthly_limit - COALESCE(SUM(t.amount), 0) AS remaining,
    ROUND((COALESCE(SUM(t.amount), 0) / b.monthly_limit * 100)::numeric, 1) AS percent_used,
    CASE 
        WHEN COALESCE(SUM(t.amount), 0) / b.monthly_limit >= 1.0 THEN 'over'
        WHEN COALESCE(SUM(t.amount), 0) / b.monthly_limit >= b.alert_threshold THEN 'warning'
        ELSE 'ok'
    END AS status
FROM budgets b
LEFT JOIN transactions t ON t.category = b.category 
    AND t.type = 'expense'
    AND DATE_TRUNC('month', t.date) = DATE_TRUNC('month', CURRENT_DATE)
WHERE b.is_active = true
GROUP BY b.id, b.category, b.monthly_limit, b.alert_threshold;

CREATE OR REPLACE VIEW v_maintenance_due AS
SELECT 
    v.make || ' ' || v.model || ' ' || v.year AS vehicle,
    v.current_mileage,
    ms.service_type,
    ms.next_due_date,
    ms.next_due_mileage,
    ms.estimated_cost,
    CASE 
        WHEN ms.next_due_date <= CURRENT_DATE THEN 'overdue'
        WHEN ms.next_due_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'due_soon'
        WHEN v.current_mileage >= ms.next_due_mileage THEN 'overdue'
        WHEN v.current_mileage >= ms.next_due_mileage - 500 THEN 'due_soon'
        ELSE 'ok'
    END AS status
FROM maintenance_schedule ms
JOIN vehicles v ON v.id = ms.vehicle_id
WHERE v.is_active = true
ORDER BY ms.next_due_date;

CREATE OR REPLACE VIEW v_daily_api_costs AS
SELECT 
    DATE(created_at) AS date,
    provider,
    model,
    COUNT(*) AS requests,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(cost_usd) AS total_cost,
    AVG(latency_ms) AS avg_latency
FROM api_usage
GROUP BY DATE(created_at), provider, model
ORDER BY date DESC, total_cost DESC;

CREATE OR REPLACE VIEW v_agent_leaderboard AS
SELECT 
    a.display_name,
    COUNT(c.id) AS total_conversations,
    AVG(c.tokens_used) AS avg_tokens,
    SUM(c.cost_usd) AS total_cost,
    AVG(CASE WHEN ap.user_satisfaction_avg IS NOT NULL THEN ap.user_satisfaction_avg ELSE 5 END) AS avg_satisfaction
FROM agents a
LEFT JOIN conversations c ON a.id = c.agent_id
LEFT JOIN agent_performance ap ON a.id = ap.agent_id
WHERE a.is_active = true
GROUP BY a.id, a.display_name
ORDER BY total_conversations DESC;

CREATE OR REPLACE VIEW v_health_trends AS
SELECT 
    date,
    weight_lbs,
    AVG(weight_lbs) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS weight_7day_avg,
    sleep_hours,
    AVG(sleep_hours) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS sleep_7day_avg,
    energy_level,
    mood,
    steps,
    resting_heart_rate,
    hrv_ms
FROM health_daily
ORDER BY date DESC
LIMIT 90;

CREATE OR REPLACE VIEW v_learning_progress AS
SELECT 
    c.path_name,
    c.topic,
    c.status,
    c.proficiency_level,
    COALESCE(SUM(ls.duration_minutes), 0) AS total_minutes,
    COUNT(ls.id) AS session_count,
    AVG(ls.comprehension_rating) AS avg_comprehension
FROM curriculum c
LEFT JOIN learning_sessions ls ON ls.topic = c.topic
GROUP BY c.id, c.path_name, c.topic, c.status, c.proficiency_level, c.order_index
ORDER BY c.path_name, c.order_index;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

INSERT INTO accounts (name, type, institution) VALUES
('Chime', 'checking', 'Chime'),
('Apple Cash', 'cash', 'Apple'),
('Cash App', 'cash', 'Cash App')
ON CONFLICT DO NOTHING;

INSERT INTO debts (name, creditor, original_amount, current_balance, minimum_payment) VALUES
('Mom Loan', 'Mom', 9700, 9700, 300)
ON CONFLICT DO NOTHING;

INSERT INTO budgets (category, monthly_limit) VALUES
('Food', 400),
('Gas', 200),
('Entertainment', 100),
('Debt Payment', 400),
('NEXUS', 150)
ON CONFLICT DO NOTHING;

INSERT INTO vehicles (make, model, year, current_mileage) VALUES
('Hyundai', 'Sonata', 2011, 0)
ON CONFLICT DO NOTHING;

INSERT INTO supplements (name, dosage, purpose, timing) VALUES
('NAC', '600mg', 'Lung health', 'morning'),
('Vitamin D3', '5000 IU', 'General health', 'morning'),
('Magnesium Glycinate', '400mg', 'Sleep recovery', 'evening'),
('Algae Oil', '1 capsule', 'Omega-3', 'morning'),
('Creatine', '5g', 'Performance', 'morning')
ON CONFLICT DO NOTHING;

INSERT INTO agents (name, display_name, description, capabilities, system_prompt) VALUES
('router', 'Router Agent', 'Orchestrates all queries and routes to appropriate agents', 
 ARRAY['routing', 'orchestration', 'multi-agent'],
 'You are the Router Agent. You classify user intent and select the appropriate specialist agent(s) to handle each query. You can orchestrate multi-agent collaboration when needed.'),

('finance', 'Finance Agent', 'Manages money, budgets, debt tracking, and financial analysis', 
 ARRAY['transactions', 'budgets', 'debt', 'analysis', 'forecasting'],
 'You are the Finance Agent. You help Philip manage his finances, track expenses, monitor budgets, and work toward paying off his $9,700 debt to his mom. Be honest about spending patterns and suggest optimizations.'),

('health', 'Health Agent', 'Tracks health metrics, nutrition, supplements, and wellness', 
 ARRAY['logging', 'nutrition', 'supplements', 'patterns', 'recommendations'],
 'You are the Health Agent. You help Philip optimize his health and track his recovery from 10 years of smoking. Focus on anti-inflammatory diet, supplement adherence, and longevity optimization.'),

('car', 'Car Agent', 'Vehicle maintenance, fuel tracking, and cost management', 
 ARRAY['mileage', 'maintenance', 'fuel', 'costs', 'reminders'],
 'You are the Car Agent. You manage Philip''s 2011 Hyundai Sonata maintenance, track mileage and fuel efficiency, and ensure registration is renewed before 09/19/2025.'),

('learning', 'Learning Agent', 'Education management, curriculum tracking, and skill development', 
 ARRAY['sessions', 'curriculum', 'progress', 'podcasts', 'quizzes'],
 'You are the Learning Agent. You help Philip master programming and build NEXUS. Track study sessions, generate personalized podcasts, create quizzes, and analyze learning effectiveness.'),

('planning', 'Planning Agent', 'Goals, tasks, habits, and time management', 
 ARRAY['goals', 'tasks', 'scheduling', 'habits', 'priorities'],
 'You are the Planning Agent. You help Philip achieve his goals: pay off debt, build NEXUS, optimize health, and eventually quit his night shift job. Manage tasks and track progress.'),

('system', 'System Agent', 'NEXUS health monitoring, optimization, and cost tracking', 
 ARRAY['monitoring', 'optimization', 'costs', 'performance', 'alerts'],
 'You are the System Agent. You monitor NEXUS infrastructure, track API costs, analyze agent performance, and suggest system optimizations.')
ON CONFLICT (name) DO NOTHING;

INSERT INTO settings (key, value, description, category) VALUES
('version', '"2.0"', 'NEXUS version', 'system'),
('timezone', '"America/Chicago"', 'System timezone', 'system'),
('currency', '"USD"', 'Default currency', 'finance'),
('notification_topic', '"nexus-philip"', 'ntfy topic for notifications', 'system')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF COMPREHENSIVE SCHEMA
-- ============================================================================
