# Nexus Bug Report - 2026-01-22

## Executive Summary
Initial bug assessment during 4-hour downtime window. Focus on testing existing functionality and documenting failures.

## System Status
- **Docker Containers**: 7/7 running ✅
- **FastAPI Service**: Dead due to Pydantic validation error ❌
- **Database**: 222 tables, operational ✅
- **Redis**: Operational ✅
- **Git**: 191 uncommitted files

## Critical Bug #1: FastAPI Service Failure

### Description
FastAPI service (`nexus-api`) fails to start with Pydantic validation error.

### Error Details
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for AgentResponse
config
  Input should be a valid dictionary [type=dict_type, input_value='{}', input_type=str]
```

### Root Cause Analysis
- `AgentResponse` model expects `config` field to be a dictionary
- Actual input is string `'{}'` (JSON string instead of parsed dict)
- **DISCOVERY**: Column type is `jsonb` (correct), but data is invalid/malformed
- **ERROR**: `invalid input syntax for type json` - The input string ended unexpectedly
- **HYPOTHESIS**: Empty string `''` or malformed JSON stored instead of valid JSON `{}`
- 121 agents in database, many likely have invalid `config` values

### Impact
- All API endpoints unavailable
- Agent framework non-functional
- System partially degraded

### Priority: CRITICAL ⚠️

## Test Execution Plan

### Phase 1: API-independent tests
1. Database connectivity tests
2. Redis connectivity tests
3. Docker container health checks
4. Script functionality tests

### Phase 2: API-dependent tests (after fix)
1. Agent framework endpoints
2. Evolution system endpoints
3. Swarm communication tests
4. Email intelligence tests

## Immediate Actions

### 1. Investigate AgentResponse Model
Location: `/home/philip/nexus/app/models/agent_schemas.py`
Check `config` field type annotation and validation.

### 2. Check Database Serialization
Examine how agent config is stored/retrieved from database.

### 3. Temporary Workaround
1. **Database fix**: Convert `config` column from TEXT to JSONB
2. **Code fix**: Add JSON parsing in database layer
3. **Quick patch**: Modify `AgentResponse` to accept string and parse JSON (less ideal)

### Recommended Fix
```sql
-- Check current column type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agents' AND column_name = 'config';

-- Convert to JSONB if TEXT
ALTER TABLE agents ALTER COLUMN config TYPE JSONB USING config::jsonb;
```

## Next Steps

1. **Fix API service** - Highest priority
2. **Run comprehensive tests** - Document all failures
3. **Create prioritized bug list** - Based on severity and impact
4. **Develop fix plan** - Weekend implementation schedule

## Resolution (2026-01-22)
- **Root Cause**: asyncpg was not properly decoding JSONB columns to Python dicts/lists due to missing type codec configuration
- **Fix**: Added JSONB type codec registration in database connection pool initialization
  - Modified `/home/philip/nexus/app/database.py` to register `jsonb` and `json` codecs using `json.dumps` and `json.loads`
  - Modified `/home/philip/nexus/app/services/database.py` for consistency
- **Result**: FastAPI service now starts successfully, agent endpoints return proper dict `config` fields
- **Verification**:
  - API service starts without Pydantic validation errors
  - `/agents` endpoint returns `config` as JSON objects instead of strings
  - All connectivity tests pass

## Notes
- System otherwise healthy (containers, database, Redis)
- 191 uncommitted changes - risk of losing work
- Consider git commit before major fixes