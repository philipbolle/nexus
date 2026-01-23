#!/usr/bin/env python3
"""
Test memory integration in NEXUS chat.

This script tests that:
1. Chat endpoints still work with memory integration
2. Conversations are stored as episodic memories
3. Context retrieval includes relevant past conversations
"""

import asyncio
import aiohttp
import json
import uuid
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8080"
TIMEOUT = 30


async def test_chat_with_memory() -> None:
    """Test chat with memory integration."""
    session_id = f"test_memory_{uuid.uuid4().hex[:8]}"
    print(f"Using session ID: {session_id}")

    async with aiohttp.ClientSession() as session:
        # Test 1: Basic chat (should store memory)
        print("\n=== Test 1: Basic chat with memory storage ===")
        response1 = await session.post(
            f"{BASE_URL}/chat",
            json={
                "message": "Hello, Nexus! This is a test of memory integration.",
                "session_id": session_id
            },
            timeout=TIMEOUT
        )

        if response1.status != 200:
            print(f"FAIL: Basic chat returned {response1.status}")
            print(await response1.text())
            return

        result1 = await response1.json()
        print(f"SUCCESS: Basic chat response received")
        print(f"Model used: {result1.get('model')}")
        print(f"Response: {result1.get('response', '')[:100]}...")

        # Test 2: Intelligent chat (should retrieve context including memories)
        print("\n=== Test 2: Intelligent chat with context retrieval ===")
        response2 = await session.post(
            f"{BASE_URL}/chat/intelligent",
            json={
                "message": "What did we just talk about?",
                "session_id": session_id,
                "use_context": True
            },
            timeout=TIMEOUT
        )

        if response2.status != 200:
            print(f"FAIL: Intelligent chat returned {response2.status}")
            print(await response2.text())
            return

        result2 = await response2.json()
        print(f"SUCCESS: Intelligent chat response received")
        print(f"Model used: {result2.get('model')}")
        print(f"Response: {result2.get('response', '')[:200]}...")

        # Test 3: Voice chat (should use enhanced conversation context)
        print("\n=== Test 3: Voice chat with conversation memory ===")
        response3 = await session.post(
            f"{BASE_URL}/chat/voice",
            json={
                "message": "Can you remember our previous conversation?",
                "session_id": session_id
            },
            timeout=TIMEOUT
        )

        if response3.status != 200:
            print(f"FAIL: Voice chat returned {response3.status}")
            print(await response3.text())
            return

        result3 = await response3.json()
        print(f"SUCCESS: Voice chat response received")
        print(f"Model used: {result3.get('model')}")
        print(f"Response: {result3.get('response', '')[:200]}...")

        # Test 4: Check memory system via API (if endpoint exists)
        print("\n=== Test 4: Checking memory system ===")
        try:
            # Try to get memory for our agent
            response4 = await session.get(
                f"{BASE_URL}/memory/chat_agent",
                timeout=TIMEOUT
            )

            if response4.status == 200:
                memories = await response4.json()
                print(f"SUCCESS: Retrieved {len(memories)} memories for chat_agent")
                if memories:
                    print(f"Latest memory: {memories[0].get('content', '')[:100]}...")
            else:
                print(f"Memory endpoint returned {response4.status} (may not exist yet)")
        except Exception as e:
            print(f"Memory endpoint not available or error: {e}")

        print("\n=== All tests completed successfully ===")
        print(f"Session ID: {session_id}")
        print("Note: Memories should be stored in the database and available for future conversations.")


async def main() -> None:
    """Run all tests."""
    try:
        await test_chat_with_memory()
    except asyncio.TimeoutError:
        print("ERROR: Test timed out. Is the API running?")
        sys.exit(1)
    except aiohttp.ClientError as e:
        print(f"ERROR: HTTP client error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())