#!/usr/bin/env python3
"""
Test web search integration in NEXUS intelligent chat.
"""

import asyncio
import httpx
import json
import sys

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

async def test_web_search():
    """Test intelligent chat with web search query."""
    print("Testing web search integration...")

    # Query that should trigger web search
    test_queries = [
        "Search the web for latest AI developments",
        "What is the current weather in Tokyo?",
        "Look up who invented Python programming language",
        "Find information about quantum computing",
    ]

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            print("-" * 40)

            try:
                response = await client.post(
                    f"{BASE_URL}/chat/intelligent",
                    json={"message": query, "model": None},
                    params={"use_context": True}
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Status: {response.status_code}")
                    print(f"📤 Response length: {len(data.get('response', ''))} chars")
                    print(f"🤖 Model used: {data.get('model_used', 'unknown')}")
                    print(f"💰 Cost: ${data.get('cost_usd', 0):.6f}")
                    print(f"⚡ Latency: {data.get('latency_ms', 0)}ms")
                    print(f"💾 Cached: {data.get('cached', False)}")

                    # Show first 500 chars of response
                    resp_text = data.get('response', '')
                    if len(resp_text) > 500:
                        print(f"\n📄 Response preview:\n{resp_text[:500]}...")
                    else:
                        print(f"\n📄 Response:\n{resp_text}")
                else:
                    print(f"❌ Failed: {response.status_code}")
                    print(f"Error: {response.text}")

            except Exception as e:
                print(f"❌ Exception: {e}")
                import traceback
                traceback.print_exc()

async def main():
    print("🚀 NEXUS Web Search Integration Test")
    print("=" * 60)
    await test_web_search()
    print("\n" + "=" * 60)
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main())