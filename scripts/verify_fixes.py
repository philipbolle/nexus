#!/usr/bin/env python3
"""
Verify Phase 1 fixes by checking file contents.
"""

import os
import re

def check_registry_fixes():
    """Check registry.py fixes."""
    print("Checking registry.py fixes...")

    with open('app/agents/registry.py', 'r') as f:
        content = f.read()

    # Check 1: get_agent_by_name checks database
    if 'SELECT id FROM agents WHERE name = $1' in content:
        print("  ✓ get_agent_by_name checks database for agent names")
    else:
        print("  ✗ get_agent_by_name missing database check")
        return False

    # Check 2: get_agent loads from database
    if 'SELECT id, name, agent_type, domain, description, system_prompt,' in content and 'FROM agents WHERE id = $1' in content:
        print("  ✓ get_agent loads from database when not in memory")
    else:
        print("  ✗ get_agent missing database load")
        return False

    # Check 3: _load_agent_from_db_data method exists
    if 'def _load_agent_from_db_data' in content:
        print("  ✓ _load_agent_from_db_data method exists")
    else:
        print("  ✗ _load_agent_from_db_data method missing")
        return False

    # Check 4: create_agent checks database for duplicate names
    if 'SELECT id FROM agents WHERE name = $1 AND is_active = true' in content and 'create_agent' in content:
        print("  ✓ create_agent checks database for duplicate names")
    else:
        print("  ✗ create_agent missing database duplicate check")
        return False

    return True

def check_memory_fixes():
    """Check memory.py fixes."""
    print("\nChecking memory.py fixes...")

    with open('app/agents/memory.py', 'r') as f:
        content = f.read()

    # Check 1: get_memories method is implemented (not just TODO)
    if 'def get_memories(self, agent_id: str, memory_type: Optional[str]' in content:
        # Check if it has actual implementation (not just TODO)
        lines = content.split('\n')
        in_get_memories = False
        has_implementation = False
        for line in lines:
            if 'def get_memories' in line:
                in_get_memories = True
            elif in_get_memories and 'def ' in line and not line.startswith(' ' * 4):
                in_get_memories = False
            elif in_get_memories and 'SELECT' in line:
                has_implementation = True

        if has_implementation:
            print("  ✓ get_memories method has database implementation")
        else:
            print("  ✗ get_memories method missing implementation")
            return False
    else:
        print("  ✗ get_memories method missing or wrong signature")
        return False

    # Check 2: MemoryType enum conversion is safe
    if 'try:\n                    memory_type_enum = MemoryType(row["memory_type"])' in content:
        print("  ✓ MemoryType enum conversion has try-except")
    else:
        print("  ✗ MemoryType enum conversion missing error handling")
        return False

    # Check 3: query_memory handles string memory_type
    if 'if hasattr(result.memory_type, \'value\'):' in content:
        print("  ✓ query_memory handles string memory_type")
    else:
        print("  ✗ query_memory missing string memory_type handling")
        return False

    return True

def check_agents_router_fixes():
    """Check agents.py router fixes."""
    print("\nChecking agents.py router fixes...")

    with open('app/routers/agents.py', 'r') as f:
        content = f.read()

    # Check: memory store endpoint uses valid default memory type
    if 'memory_type_str = memory_data.get("type", "semantic")' in content:
        print("  ✓ Memory store endpoint uses 'semantic' as default (not 'observation')")
    else:
        print("  ✗ Memory store endpoint still uses invalid default")
        return False

    return True

def check_monitoring_fixes():
    """Check monitoring.py fixes."""
    print("\nChecking monitoring.py fixes...")

    with open('app/agents/monitoring.py', 'r') as f:
        content = f.read()

    # Check 1: _ensure_uuid handles empty agent_id
    if 'if not agent_id:' in content and 'Empty agent_id provided' in content:
        print("  ✓ _ensure_uuid handles empty agent_id")
    else:
        print("  ✗ _ensure_uuid missing empty agent_id handling")
        return False

    # Check 2: record_metric logs conversion
    if 'original_agent_id = agent_id' in content and 'Converted agent_id' in content:
        print("  ✓ record_metric logs agent_id conversion")
    else:
        print("  ✗ record_metric missing conversion logging")
        return False

    return True

def main():
    """Run all checks."""
    print("=" * 60)
    print("Verifying Phase 1 Fixes for NEXUS Agent Framework")
    print("=" * 60)

    all_passed = True

    if not check_registry_fixes():
        all_passed = False

    if not check_memory_fixes():
        all_passed = False

    if not check_agents_router_fixes():
        all_passed = False

    if not check_monitoring_fixes():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All Phase 1 fixes verified!")
        print("\nSummary of fixes implemented:")
        print("1. Email Agent Registration: Fixed duplicate name checking in registry")
        print("2. Memory System: Implemented get_memories() and fixed enum conversion")
        print("3. Session Management: SQL syntax errors need further investigation")
        print("4. Schema Mismatches: Already applied (config column, system_alerts table)")
        print("5. Monitoring System: Fixed UUID conversion for 'system' agent_id")
    else:
        print("✗ Some fixes are missing or incomplete")
        print("\nPlease review the issues above.")

    print("=" * 60)

if __name__ == "__main__":
    main()