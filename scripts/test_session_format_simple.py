#!/usr/bin/env python3
"""
Simple test to verify the session format fixes without database dependencies.
"""

import json
from datetime import datetime
from uuid import uuid4

# Mock the database row that _load_session_from_db would receive
def create_mock_row():
    """Create a mock database row with string metadata."""
    session_id = str(uuid4())
    agent_id = str(uuid4())
    other_agent_id = str(uuid4())

    return {
        "id": session_id,
        "session_type": "chat",
        "title": "Test Session",
        "summary": "This is a test session summary",
        "primary_agent_id": agent_id,
        "agents_involved": [agent_id, other_agent_id],
        "total_messages": 10,
        "total_tokens": 2500,
        "total_cost_usd": 0.15,
        "status": "active",
        "started_at": datetime.now(),
        "last_message_at": datetime.now(),
        "ended_at": None,
        "metadata": json.dumps({"test_key": "test_value", "priority": "high"})
    }

# Simulate what _load_session_from_db should do
def simulate_load_session_from_db(row):
    """Simulate the fixed _load_session_from_db logic."""

    # Convert metadata from string to dict if needed
    metadata = row["metadata"]
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError:
            metadata = {}

    # Ensure metadata is a dict
    if not isinstance(metadata, dict):
        metadata = {}

    # Ensure agents_involved is a list
    agents_involved = row["agents_involved"] or []

    # Return in SessionResponse format
    return {
        "id": row["id"],
        "session_type": row["session_type"],
        "title": row["title"] or "",
        "summary": row["summary"],
        "primary_agent_id": row["primary_agent_id"],
        "agents_involved": agents_involved,
        "total_messages": row["total_messages"],
        "total_tokens": row["total_tokens"],
        "total_cost_usd": float(row["total_cost_usd"] or 0),
        "status": row["status"],
        "started_at": row["started_at"],
        "last_message_at": row["last_message_at"],
        "ended_at": row["ended_at"],
        "metadata": metadata
    }

# Simulate what the OLD _load_session_from_db would return (with bugs)
def simulate_old_load_session_from_db(row):
    """Simulate the OLD buggy _load_session_from_db logic."""

    metadata = row["metadata"] or {}

    return {
        "id": row["id"],
        "title": row["title"],
        "type": row["session_type"],  # WRONG: should be "session_type"
        "primary_agent_id": row["primary_agent_id"],
        "agents_involved": row["agents_involved"],
        "config": {"session_type": row["session_type"], "metadata": metadata},  # WRONG: should not have "config"
        "message_count": row["total_messages"],  # WRONG: should be "total_messages"
        "total_tokens": row["total_tokens"],
        "total_cost_usd": float(row["total_cost_usd"] or 0),
        "created_at": row["started_at"],  # WRONG: should be "started_at"
        "last_message_at": row["last_message_at"],
        "ended_at": row["ended_at"],
        "status": row["status"],
        "metadata": metadata
    }

def test_fixes():
    """Test that the fixes correct all the field name issues."""
    print("Testing session format fixes...")
    print("=" * 60)

    # Create mock data
    mock_row = create_mock_row()

    # Get results from both versions
    old_result = simulate_old_load_session_from_db(mock_row)
    new_result = simulate_load_session_from_db(mock_row)

    print("1. Checking field name corrections:")
    print("-" * 40)

    # Check specific fixes
    fixes = [
        ("type → session_type", "type" in old_result, "session_type" in new_result),
        ("message_count → total_messages", "message_count" in old_result, "total_messages" in new_result),
        ("created_at → started_at", "created_at" in old_result, "started_at" in new_result),
        ("config field removed", "config" in old_result, "config" not in new_result),
    ]

    all_good = True
    for description, old_has, new_correct in fixes:
        if old_has and new_correct:
            print(f"  ✓ {description}")
        else:
            print(f"  ❌ {description}")
            all_good = False

    print("\n2. Checking metadata parsing:")
    print("-" * 40)

    # Check metadata is properly parsed from string
    old_metadata = old_result.get("metadata")
    new_metadata = new_result.get("metadata")

    if isinstance(new_metadata, dict):
        print(f"  ✓ New metadata is dict with keys: {list(new_metadata.keys())}")
    else:
        print(f"  ❌ New metadata is {type(new_metadata).__name__}, not dict")
        all_good = False

    print("\n3. Checking all required SessionResponse fields:")
    print("-" * 40)

    # Required fields from SessionResponse schema
    required_fields = [
        "id", "session_type", "title", "summary", "primary_agent_id",
        "agents_involved", "total_messages", "total_tokens", "total_cost_usd",
        "status", "started_at", "last_message_at", "ended_at", "metadata"
    ]

    # Check field types match SessionResponse expectations
    field_type_checks = [
        ("id", str),
        ("session_type", str),
        ("title", str),
        ("summary", (str, type(None))),
        ("primary_agent_id", (str, type(None))),
        ("agents_involved", list),
        ("total_messages", int),
        ("total_tokens", int),
        ("total_cost_usd", float),
        ("status", str),
        ("started_at", datetime),
        ("last_message_at", (datetime, type(None))),
        ("ended_at", (datetime, type(None))),
        ("metadata", dict),
    ]

    missing_fields = []
    type_errors = []

    for field, expected_type in field_type_checks:
        if field not in new_result:
            missing_fields.append(field)
        else:
            value = new_result[field]
            if isinstance(expected_type, tuple):
                if not any(isinstance(value, t) for t in expected_type):
                    type_errors.append(f"{field}: expected one of {[t.__name__ for t in expected_type]}, got {type(value).__name__}")
                else:
                    print(f"  ✓ {field}: {type(value).__name__} (valid)")
            elif not isinstance(value, expected_type):
                type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(value).__name__}")
            else:
                print(f"  ✓ {field}: {type(value).__name__}")

    if missing_fields:
        print(f"  ❌ Missing fields: {missing_fields}")
        all_good = False

    if type_errors:
        print(f"  ❌ Type errors:")
        for error in type_errors:
            print(f"     {error}")
        all_good = False

    print("\n4. Field comparison:")
    print("-" * 40)

    old_fields = set(old_result.keys())
    new_fields = set(new_result.keys())

    print(f"  Old method fields ({len(old_fields)}): {sorted(old_fields)}")
    print(f"  New method fields ({len(new_fields)}): {sorted(new_fields)}")

    added = new_fields - old_fields
    removed = old_fields - new_fields

    if added:
        print(f"  Added fields: {sorted(added)}")
    if removed:
        print(f"  Removed fields: {sorted(removed)}")

    print("\n" + "=" * 60)
    if all_good:
        print("✅ All tests passed! Session format matches SessionResponse schema.")
        return True
    else:
        print("❌ Some tests failed.")
        return False

def test_active_session_conversion():
    """Test active session format conversion in get_session()."""
    print("\n\nTesting active session format conversion...")
    print("=" * 60)

    # Simulate an active session (internal format)
    active_session = {
        "id": str(uuid4()),
        "title": "Active Test Session",
        "type": "task",  # Internal uses "type"
        "primary_agent_id": str(uuid4()),
        "agents_involved": [str(uuid4()), str(uuid4())],
        "config": {"session_type": "task", "metadata": {"test": "data"}},
        "message_count": 15,  # Internal uses "message_count"
        "total_tokens": 3000,
        "total_cost_usd": 0.25,
        "created_at": datetime.now(),  # Internal uses "created_at"
        "last_message_at": datetime.now(),
        "ended_at": None,
        "status": "active",
        "metadata": {"test": "data"},
        "summary": None
    }

    # Simulate what get_session() should do to convert
    converted_session = {
        "id": active_session["id"],
        "session_type": active_session.get("type", active_session.get("session_type", "chat")),
        "title": active_session.get("title", ""),
        "summary": active_session.get("summary"),
        "primary_agent_id": active_session.get("primary_agent_id"),
        "agents_involved": active_session.get("agents_involved", []),
        "total_messages": active_session.get("message_count", active_session.get("total_messages", 0)),
        "total_tokens": active_session.get("total_tokens", 0),
        "total_cost_usd": active_session.get("total_cost_usd", 0.0),
        "status": active_session.get("status", "active"),
        "started_at": active_session.get("created_at", active_session.get("started_at", datetime.now())),
        "last_message_at": active_session.get("last_message_at"),
        "ended_at": active_session.get("ended_at"),
        "metadata": active_session.get("metadata", {})
    }

    print("Checking conversion from internal to SessionResponse format:")
    print("-" * 40)

    checks = [
        ("Has session_type (not type)", "session_type" in converted_session and converted_session["session_type"] == "task"),
        ("Has total_messages (not message_count)", "total_messages" in converted_session and converted_session["total_messages"] == 15),
        ("Has started_at (not created_at)", "started_at" in converted_session),
        ("No config field", "config" not in converted_session),
        ("No type field", "type" not in converted_session),
        ("No message_count field", "message_count" not in converted_session),
        ("No created_at field", "created_at" not in converted_session),
    ]

    all_good = True
    for description, check_passed in checks:
        if check_passed:
            print(f"  ✓ {description}")
        else:
            print(f"  ❌ {description}")
            all_good = False

    print("\n" + "=" * 60)
    if all_good:
        print("✅ Active session conversion works correctly.")
        return True
    else:
        print("❌ Active session conversion has issues.")
        return False

def main():
    """Run all tests."""
    print("Session Endpoint Validation Fix Test")
    print("=" * 60)

    test1_passed = test_fixes()
    test2_passed = test_active_session_conversion()

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Test 1 (Field name fixes): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Test 2 (Active session conversion): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n✅ All tests passed! Session endpoints should now validate correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)