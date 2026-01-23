#!/usr/bin/env python3
"""
Test the new voice-optimized chat endpoint.
Run after restarting the nexus-api service.
"""

import httpx
import json
import time
import sys

BASE_URL = "http://localhost:8080"
# Use Tailscale IP for remote testing: "http://100.68.201.55:8080"

def test_endpoint(endpoint: str, data: dict, description: str):
    """Test an endpoint and print results."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing {description}")
    print(f"Endpoint: {endpoint}")
    print(f"Request: {json.dumps(data, indent=2)}")

    start = time.time()
    try:
        response = httpx.post(url, json=data, timeout=30.0)
        latency_ms = (time.time() - start) * 1000
        response.raise_for_status()
        result = response.json()

        print(f"✅ Success - {latency_ms:.0f}ms")
        print(f"Response: {result.get('response', '')[:200]}...")
        print(f"Model used: {result.get('model_used')}")
        print(f"Tokens: {result.get('tokens_used')}")
        print(f"Cost: ${result.get('cost_usd'):.6f}")
        print(f"Cached: {result.get('cached', False)}")
        return result

    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

def main():
    print("NEXUS Voice Endpoint Test")
    print(f"Base URL: {BASE_URL}")

    # Test 1: Regular chat endpoint (original)
    test_endpoint(
        endpoint="/chat",
        data={"message": "Hello, tell me a short joke.", "model": "groq"},
        description="Regular chat endpoint (llama-3.3-70b)"
    )

    # Test 2: New voice endpoint (optimized)
    test_endpoint(
        endpoint="/chat/voice",
        data={"message": "Hello, tell me a short joke."},
        description="Voice-optimized endpoint (llama-3.1-8b-instant)"
    )

    # Test 3: Voice endpoint with session (conversation memory)
    session_id = "test_session_123"
    print(f"\n{'='*60}")
    print("Testing conversation memory with session ID...")

    # First message
    test_endpoint(
        endpoint="/chat/voice",
        data={"message": "My name is Philip."},
        description="Voice endpoint - first message"
    )

    # Follow-up (should have context)
    result = test_endpoint(
        endpoint="/chat/voice",
        data={"message": "What's my name?"},
        description="Voice endpoint - follow-up with session"
    )

    if result:
        response = result.get("response", "").lower()
        if "philip" in response:
            print("✅ Conversation memory working!")
        else:
            print("⚠️  Conversation memory may not be working")

    # Test 4: Performance comparison
    print(f"\n{'='*60}")
    print("Performance comparison (averaging 3 calls each)...")

    def benchmark(endpoint, data, name):
        latencies = []
        for i in range(3):
            start = time.time()
            try:
                response = httpx.post(f"{BASE_URL}{endpoint}", json=data, timeout=30.0)
                response.raise_for_status()
                latencies.append((time.time() - start) * 1000)
            except Exception as e:
                print(f"  Iteration {i+1} failed: {e}")
                return None
        avg = sum(latencies) / len(latencies) if latencies else 0
        print(f"  {name}: {avg:.0f}ms avg (min: {min(latencies):.0f}ms, max: {max(latencies):.0f}ms)")
        return avg

    regular_avg = benchmark("/chat", {"message": "Quick test", "model": "groq"}, "Regular endpoint")
    voice_avg = benchmark("/chat/voice", {"message": "Quick test"}, "Voice endpoint")

    if regular_avg and voice_avg:
        speedup = ((regular_avg - voice_avg) / regular_avg) * 100
        print(f"\n📈 Voice endpoint is {speedup:.1f}% faster")

    print(f"\n{'='*60}")
    print("Test complete!")

if __name__ == "__main__":
    main()