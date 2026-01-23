#!/usr/bin/env python3
"""
Test script to verify session endpoint validation fixes.
Tests that the _load_session_from_db method returns data matching SessionResponse schema.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.sessions import SessionManager, SessionConfig, SessionStatus, SessionType
from app.database import db
import json
from datetime import datetime
from uuid import uuid4


async def test_session_format():
    """Test that session data matches SessionResponse schema."""
    print("Testing session format fixes...")

    # Initialize database connection
    await db.connect()

    # Create session manager
    session_manager = SessionManager()

    # Create a test session
    session_id = str(uuid4())
    title = "Test Session Format"
    primary_agent_id = str(uuid4())

    # Create session directly in database (bypassing create_session to test _load_session_from_db)
    test_metadata = {"test_key": "test_value", "priority": "high"}

    await db.execute(
        """
        INSERT INTO sessions
        (id, session_type, title, summary, primary_agent_id,
         agents_involved, status, metadata, total_messages, total_tokens,
         total_cost_usd, started_at, last_message_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
        session_id,
        "chat",
        title,
        "Test session summary",
        primary_agent_id,
        [primary_agent_id, str(uuid4())],
        "active",
        json.dumps(test_metadata),
        5,  # total_messages
        1500,  # total_tokens
        0.05,  # total_cost_usd
        datetime.now(),
        datetime.now()
    )

    print(f"Created test session: {session_id}")

    # Test 1: Test _load_session_from_db directly
    print("\n1. Testing _load_session_from_db method...")
    session_data = await session_manager._load_session_from_db(session_id)

    if not session_data:
        print("ERROR: Failed to load session from database")
        return False

    # Check required fields from SessionResponse schema
    required_fields = [
        "id", "session_type", "title", "summary", "primary_agent_id",
        "agents_involved", "total_messages", "total_tokens", "total_cost_usd",
        "status", "started_at", "last_message_at", "ended_at", "metadata"
    ]

    print("Checking field names and types:")
    all_good = True

    for field in required_fields:
        if field not in session_data:
            print(f"  ❌ Missing field: {field}")
            all_good = False
        else:
            value = session_data[field]
            print(f"  ✓ {field}: {type(value).__name__} = {repr(value) if not isinstance(value, (list, dict)) else f'{type(value).__name__} with {len(value)} items'}")

    # Check specific field name issues that were fixed
    print("\nChecking specific fixes:")

    # Should have session_type, not type
    if "type" in session_data:
        print("  ❌ Still has 'type' field (should be 'session_type')")
        all_good = False
    else:
        print("  ✓ No 'type' field (correct)")

    # Should have total_messages, not message_count
    if "message_count" in session_data:
        print("  ❌ Still has 'message_count' field (should be 'total_messages')")
        all_good = False
    else:
        print("  ✓ No 'message_count' field (correct)")

    # Should have started_at, not created_at
    if "created_at" in session_data:
        print("  ❌ Still has 'created_at' field (should be 'started_at')")
        all_good = False
    else:
        print("  ✓ No 'created_at' field (correct)")

    # Should not have config field
    if "config" in session_data:
        print("  ❌ Still has 'config' field (should not be in response)")
        all_good = False
    else:
        print("  ✓ No 'config' field (correct)")

    # Check metadata is dict, not string
    metadata = session_data.get("metadata")
    if isinstance(metadata, dict):
        print(f"  ✓ Metadata is dict with keys: {list(metadata.keys())}")
    else:
        print(f"  ❌ Metadata is {type(metadata).__name__}, not dict")
        all_good = False

    # Test 2: Test get_session method (which should handle both active and db sessions)
    print("\n2. Testing get_session method...")
    session_from_get = await session_manager.get_session(session_id)

    if not session_from_get:
        print("ERROR: get_session returned None")
        all_good = False
    else:
        # Check it has the same corrected fields
        if "session_type" in session_from_get and "total_messages" in session_from_get:
            print("  ✓ get_session returns corrected field names")
        else:
            print(f"  ❌ get_session missing corrected fields: session_type={session_from_get.get('session_type')}, total_messages={session_from_get.get('total_messages')}")
            all_good = False

    # Test 3: Test list_sessions for comparison
    print("\n3. Testing list_sessions format for comparison...")
    sessions_list = await session_manager.list_sessions(limit=1)

    if sessions_list:
        list_session = sessions_list[0]
        # Check that list_sessions returns the same field names
        if "session_type" in list_session and "total_messages" in list_session:
            print("  ✓ list_sessions uses correct field names")

            # Compare field names between _load_session_from_db and list_sessions
            db_fields = set(session_data.keys())
            list_fields = set(list_session.keys())

            if db_fields == list_fields:
                print("  ✓ Both methods return same field set")
            else:
                print(f"  ❌ Field sets differ:")
                print(f"     _load_session_from_db has: {sorted(db_fields)}")
                print(f"     list_sessions has: {sorted(list_fields)}")
                all_good = False
        else:
            print("  ❌ list_sessions has incorrect field names")
            all_good = False

    # Clean up
    print("\nCleaning up test session...")
    await db.execute("DELETE FROM sessions WHERE id = $1", session_id)

    await db.disconnect()

    if all_good:
        print("\n✅ All tests passed! Session format matches SessionResponse schema.")
        return True
    else:
        print("\n❌ Some tests failed. Session format doesn't match SessionResponse schema.")
        return False


async def test_active_session_format():
    """Test that active sessions are converted correctly in get_session()."""
    print("\n\nTesting active session format conversion...")

    # Initialize database connection
    await db.connect()

    # Create session manager
    session_manager = SessionManager()
    await session_manager.initialize()

    # Create an active session using the public API
    session_id = await session_manager.create_session(
        title="Active Session Test",
        primary_agent_id=str(uuid4()),
        session_type="task"
    )

    print(f"Created active session: {session_id}")

    # Get the session (should convert internal format to SessionResponse format)
    session_data = await session_manager.get_session(session_id)

    if not session_data:
        print("ERROR: Failed to get active session")
        return False

    print("Checking active session field conversion:")

    # Check for corrected field names
    checks = [
        ("session_type", "Should have session_type field"),
        ("total_messages", "Should have total_messages field"),
        ("started_at", "Should have started_at field"),
        ("summary", "Should have summary field (may be None)"),
    ]

    all_good = True
    for field, description in checks:
        if field in session_data:
            value = session_data[field]
            print(f"  ✓ {description}: {type(value).__name__} = {repr(value) if value is not None else 'None'}")
        else:
            print(f"  ❌ Missing {field}: {description}")
            all_good = False

    # Check for removed fields
    bad_fields = ["type", "message_count", "created_at", "config"]
    for field in bad_fields:
        if field in session_data:
            print(f"  ❌ Should not have {field} field in response")
            all_good = False
        else:
            print(f"  ✓ No {field} field (correct)")

    # Clean up
    print("\nCleaning up active session...")
    await session_manager.end_session(session_id, status=SessionStatus.COMPLETED)
    await session_manager.shutdown()
    await db.disconnect()

    if all_good:
        print("✅ Active session format conversion works correctly.")
        return True
    else:
        print("❌ Active session format conversion has issues.")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Session Endpoint Validation Fix Test")
    print("=" * 60)

    test1_passed = await test_session_format()
    test2_passed = await test_active_session_format()

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Test 1 (Database session format): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Test 2 (Active session conversion): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n✅ All tests passed! Session endpoints should now validate correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)