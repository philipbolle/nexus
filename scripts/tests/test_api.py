#!/usr/bin/env python3
"""
NEXUS API Test Script
Tests all FastAPI endpoints and reports status.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 30  # seconds

# Endpoints to test with expected HTTP status codes
ENDPOINTS = [
    # Core endpoints
    {"method": "GET", "path": "/", "name": "Root", "expected_status": 200},
    {"method": "GET", "path": "/health", "name": "Health", "expected_status": 200},
    {"method": "GET", "path": "/status", "name": "Status", "expected_status": 200},

    # Chat endpoints
    {"method": "POST", "path": "/chat", "name": "Chat", "expected_status": 200,
     "data": {"message": "Test message from API test script"}},

    # Finance endpoints
    {"method": "GET", "path": "/finance/budget-status", "name": "Budget Status", "expected_status": 200},
    {"method": "GET", "path": "/finance/debt/progress", "name": "Debt Progress", "expected_status": 200},

    # Email endpoints
    {"method": "GET", "path": "/email/stats", "name": "Email Stats", "expected_status": 200},
    {"method": "GET", "path": "/email/preferences", "name": "Email Preferences", "expected_status": 200},
    {"method": "GET", "path": "/email/summary", "name": "Email Summary", "expected_status": 200},
    {"method": "GET", "path": "/email/recent", "name": "Email Recent", "expected_status": 200},

    # Test POST endpoints with dummy data
    {"method": "POST", "path": "/finance/expense", "name": "Log Expense", "expected_status": 200,
     "data": {"amount": 1.00, "category": "Test", "description": "API test", "merchant": "Test Merchant"}},
]


async def test_endpoint(session: aiohttp.ClientSession, endpoint: Dict) -> Dict[str, Any]:
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint['path']}"
    name = endpoint['name']
    expected = endpoint['expected_status']

    try:
        if endpoint['method'] == 'GET':
            async with session.get(url, timeout=TIMEOUT) as response:
                status = response.status
                text = await response.text()
        elif endpoint['method'] == 'POST':
            data = endpoint.get('data', {})
            async with session.post(url, json=data, timeout=TIMEOUT) as response:
                status = response.status
                text = await response.text()
        else:
            return {
                "name": name,
                "url": url,
                "path": endpoint['path'],
                "method": endpoint['method'],
                "success": False,
                "error": f"Unsupported method: {endpoint['method']}"
            }

        # Parse JSON if possible
        try:
            json_data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            json_data = {"raw_response": text[:200] + "..." if len(text) > 200 else text}

        success = status == expected
        result = {
            "name": name,
            "url": url,
            "path": endpoint['path'],
            "method": endpoint['method'],
            "expected_status": expected,
            "actual_status": status,
            "success": success,
            "response": json_data if success or status < 500 else {},
            "error": None if success else f"Expected {expected}, got {status}"
        }

        # Add specific validations for certain endpoints
        if success:
            if name == "Health":
                if json_data.get("status") != "healthy":
                    result["success"] = False
                    result["error"] = f"Health status not 'healthy': {json_data.get('status')}"
            elif name == "Status":
                if "services" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'services' in status response"
            elif name == "Budget Status":
                if "month" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'month' in budget status"
            elif name == "Debt Progress":
                if "total_original" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'total_original' in debt progress"
            elif name == "Chat":
                if "response" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'response' in chat response"

        return result

    except asyncio.TimeoutError:
        return {
            "name": name,
            "url": url,
            "path": endpoint['path'],
            "method": endpoint['method'],
            "success": False,
            "error": f"Timeout after {TIMEOUT} seconds"
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "path": endpoint['path'],
            "method": endpoint['method'],
            "success": False,
            "error": f"Exception: {str(e)}"
        }


async def run_all_tests() -> List[Dict[str, Any]]:
    """Run all endpoint tests concurrently."""
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [test_endpoint(session, endpoint) for endpoint in ENDPOINTS]
        results = await asyncio.gather(*tasks)
        return results


def print_results(results: List[Dict[str, Any]]) -> None:
    """Print test results in a readable format."""
    print("\n" + "="*70)
    print("NEXUS API TEST RESULTS")
    print("="*70)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Endpoints tested: {len(results)}")
    print()

    successes = [r for r in results if r['success']]
    failures = [r for r in results if not r['success']]

    print(f"✅ PASSED: {len(successes)}")
    print(f"❌ FAILED: {len(failures)}")
    print()

    if failures:
        print("FAILED TESTS:")
        print("-" * 40)
        for fail in failures:
            print(f"  ❌ {fail['name']}")
            print(f"     URL: {fail['method']} {fail['url']}")
            print(f"     Error: {fail['error']}")
            if fail.get('response'):
                resp_str = json.dumps(fail['response'], indent=2)
                if len(resp_str) > 200:
                    resp_str = resp_str[:200] + "..."
                print(f"     Response: {resp_str}")
            print()

    print("PASSED TESTS:")
    print("-" * 40)
    for success in successes:
        print(f"  ✅ {success['name']} ({success['method']} {success['path']})")
        if success['name'] == 'Status':
            services = success['response'].get('services', [])
            for svc in services:
                status = "✅" if svc.get('status') == 'healthy' else "❌"
                print(f"     {status} {svc.get('name')}: {svc.get('status')}")
        elif success['name'] == 'Debt Progress':
            total = success['response'].get('total_current', 0)
            print(f"     Total debt: ${total}")
        elif success['name'] == 'Budget Status':
            spent = success['response'].get('total_spent', 0)
            print(f"     Total spent this month: ${spent}")
        elif success['name'] == 'Chat':
            model = success['response'].get('model_used', 'unknown')
            cost = success['response'].get('cost_usd', 0)
            print(f"     Model: {model}, Cost: ${cost:.6f}")

    print()
    print("="*70)
    print("SUMMARY:")

    # Overall status
    if len(failures) == 0:
        print("🎉 ALL TESTS PASSED! NEXUS API is fully operational.")
    elif len(failures) <= 2:
        print("⚠️  Most tests passed. Check failed endpoints above.")
    else:
        print("❌ Multiple tests failed. API may have issues.")

    # Database status check
    status_result = next((r for r in results if r['name'] == 'Status'), None)
    if status_result and status_result['success']:
        db_tables = status_result['response'].get('database_tables', 0)
        print(f"📊 Database tables: {db_tables}")

    print("="*70)


async def main():
    """Main entry point."""
    print("🚀 Starting NEXUS API comprehensive test...")
    print(f"Testing against: {BASE_URL}")
    print()

    try:
        results = await run_all_tests()
        print_results(results)

        # Exit code based on test results
        failures = [r for r in results if not r['success']]
        sys.exit(0 if len(failures) == 0 else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())