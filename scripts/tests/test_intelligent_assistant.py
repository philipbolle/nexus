#!/usr/bin/env python3
"""
Test the NEXUS Intelligent Assistant (Jarvis-like capabilities).

Tests the new intelligent endpoints that provide context-aware responses
using all NEXUS data sources.

Run this after restarting the nexus-api service.
"""

import asyncio
import sys
import os
import uuid

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import db
from app.services.intelligent_context import (
    retrieve_intelligent_context,
    RetrievedContext,
    store_conversation
)
from app.services.ai import intelligent_chat

async def test_context_retrieval():
    """Test the intelligent context retrieval system."""
    print("\n" + "="*60)
    print("Testing Intelligent Context Retrieval")
    print("="*60)

    test_queries = [
        "How much have I spent this month?",
        "What's my current budget status?",
        "Any important emails recently?",
        "How are my agents performing?",
        "What's the system status?",
        "Tell me a joke"  # Should return minimal context
    ]

    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 40)

        try:
            context = await retrieve_intelligent_context(query, timeout_seconds=2.0)
            formatted = context.format_for_ai()

            print(f"✅ Retrieved context ({len(formatted)} chars)")
            if formatted and formatted != "No relevant data found.":
                # Show first 200 chars of context
                preview = formatted[:200] + "..." if len(formatted) > 200 else formatted
                print(f"Context preview: {preview}")

            print(f"Domains retrieved:")
            if context.finance_data:
                print(f"  • Finance: {len(context.finance_data)} items")
            if context.email_data:
                print(f"  • Email: {len(context.email_data)} items")
            if context.agent_data:
                print(f"  • Agents: {len(context.agent_data)} items")
            if context.system_data:
                print(f"  • System: {len(context.system_data)} items")
            if context.conversation_history:
                print(f"  • Conversation: {len(context.conversation_history)} messages")
            if context.errors:
                print(f"  • Errors: {len(context.errors)}")

        except Exception as e:
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()

async def test_intelligent_chat():
    """Test the intelligent chat function."""
    print("\n" + "="*60)
    print("Testing Intelligent Chat (Jarvis-like)")
    print("="*60)

    test_messages = [
        ("What's my current financial situation?", True),
        ("How much have I spent on food this month?", True),
        ("Any system errors I should know about?", True),
        ("Tell me about my active agents", True),
        ("What's the meaning of life?", False),  # Should work without context
    ]

    for message, use_context in test_messages:
        print(f"\n💬 Message: '{message}'")
        print(f"   Use context: {use_context}")
        print("-" * 40)

        try:
            response = await intelligent_chat(
                message=message,
                session_id=str(uuid.uuid4()),  # Generate a proper UUID
                use_context=use_context
            )

            print(f"✅ Response received in {response.latency_ms}ms")
            print(f"Model: {response.model}")
            print(f"Provider: {response.provider}")
            print(f"Tokens: {response.input_tokens + response.output_tokens}")
            print(f"Cost: ${response.cost_usd:.6f}")
            print(f"Cached: {response.cached}")

            # Show first 150 chars of response
            preview = response.content[:150] + "..." if len(response.content) > 150 else response.content
            print(f"Response: {preview}")

        except Exception as e:
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()

async def test_conversation_storage():
    """Test conversation storage for learning."""
    print("\n" + "="*60)
    print("Testing Conversation Storage (Learning)")
    print("="*60)

    session_id = str(uuid.uuid4())
    user_message = "Test message for learning system"
    ai_response = "Test response from AI"

    try:
        success = await store_conversation(
            session_id=session_id,
            user_message=user_message,
            ai_response=ai_response,
            metadata={"test": True}
        )

        if success:
            print(f"✅ Successfully stored conversation for session {session_id[:8]}...")
        else:
            print("❌ Failed to store conversation")

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

async def test_endpoint_urls():
    """Print the new endpoint URLs for testing."""
    print("\n" + "="*60)
    print("New Intelligent Endpoints Available")
    print("="*60)

    base_url = "http://localhost:8080"
    endpoints = [
        ("POST /chat/intelligent", "Jarvis-like intelligent chat with full context"),
        ("POST /chat/voice", "Voice-optimized chat (fast, short responses)"),
        ("POST /chat", "Original chat endpoint"),
    ]

    for endpoint, description in endpoints:
        print(f"\n{endpoint}")
        print(f"  {description}")
        print(f"  URL: {base_url}{endpoint.split()[1]}")

    print("\n" + "="*60)
    print("Sample curl commands:")
    print("="*60)

    print("""
# Test intelligent endpoint:
curl -X POST http://localhost:8080/chat/intelligent \\
  -H "Content-Type: application/json" \\
  -d '{"message": "How much have I spent this month?"}'

# Test voice endpoint:
curl -X POST http://localhost:8080/chat/voice \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Tell me a joke"}'

# Test with session (for conversation memory):
curl -X POST "http://localhost:8080/chat/intelligent?session_id=test_session_123" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "What's my budget status?"}'
""")

async def main():
    """Run all tests."""
    print("🧠 NEXUS Intelligent Assistant Test Suite")
    print("Testing Jarvis-like capabilities with full NEXUS context")

    try:
        # Initialize database connection
        print("\n🔌 Initializing database connection...")
        await db.connect()
        print("✅ Database connected")

        # Test 1: Context retrieval
        await test_context_retrieval()

        # Test 2: Intelligent chat
        await test_intelligent_chat()

        # Test 3: Conversation storage
        await test_conversation_storage()

        # Test 4: Show endpoints
        await test_endpoint_urls()

        # Cleanup
        await db.disconnect()
        print("✅ Database disconnected")

        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Restart the nexus-api service to load new code")
        print("2. Test the endpoints with curl or the iPhone shortcut")
        print("3. Update iPhone shortcut to use /chat/intelligent for smart queries")
        print("4. Monitor performance and adjust timeouts as needed")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

        # Try to disconnect if connected
        try:
            await db.disconnect()
        except:
            pass

        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)