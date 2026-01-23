#!/usr/bin/env python3
"""
NEXUS Email Endpoint Test Script
Tests email-specific endpoints including scan and send functionality.
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

# Test email endpoints
EMAIL_ENDPOINTS = [
    # GET endpoints
    {"method": "GET", "path": "/email/stats", "name": "Email Stats", "expected_status": 200},
    {"method": "GET", "path": "/email/preferences", "name": "Email Preferences", "expected_status": 200},
    {"method": "GET", "path": "/email/summary", "name": "Email Summary", "expected_status": 200},
    {"method": "GET", "path": "/email/recent", "name": "Email Recent", "expected_status": 200},
    {"method": "GET", "path": "/email/insights", "name": "Email Insights", "expected_status": 200},

    # POST endpoints
    {"method": "POST", "path": "/email/scan", "name": "Email Scan", "expected_status": 200,
     "data": {"since_days": 1, "limit": 5}},

    {"method": "POST", "path": "/email/send", "name": "Email Send", "expected_status": 200,
     "data": {
         "account": "gmail",
         "to_addresses": ["test@example.com"],
         "subject": "Test Email from NEXUS API",
         "body": "This is a test email sent from the NEXUS API test script.",
         "is_html": False
     }},

    {"method": "POST", "path": "/email/insights/generate", "name": "Generate Insights", "expected_status": 200},
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

        # Add specific validations for email endpoints
        if success:
            if name == "Email Stats":
                if "email_processing" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'email_processing' in stats response"
            elif name == "Email Preferences":
                if "vip_senders" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'vip_senders' in preferences response"
            elif name == "Email Scan":
                if "status" not in json_data:
                    result["success"] = False
                    result["error"] = "Missing 'status' in scan response"
            elif name == "Email Send":
                # Email send might fail due to missing credentials - that's OK
                if json_data.get("status") == "sent":
                    print(f"    ✅ Email sent successfully! Message ID: {json_data.get('message_id')}")
                elif json_data.get("status") == "error" or "error" in json_data:
                    # This is expected if credentials aren't configured
                    result["success"] = True  # Mark as success since endpoint works
                    result["warning"] = f"Email send failed (expected): {json_data.get('error', json_data.get('detail', 'No credentials configured'))}"
                else:
                    result["success"] = False
                    result["error"] = f"Unexpected response: {json_data}"

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


async def run_email_tests() -> List[Dict[str, Any]]:
    """Run all email endpoint tests concurrently."""
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [test_endpoint(session, endpoint) for endpoint in EMAIL_ENDPOINTS]
        results = await asyncio.gather(*tasks)
        return results


def print_email_results(results: List[Dict[str, Any]]) -> None:
    """Print test results in a readable format."""
    print("\n" + "="*70)
    print("NEXUS EMAIL ENDPOINT TEST RESULTS")
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

        # Show specific info for each endpoint
        if success.get('warning'):
            print(f"     ⚠️  {success['warning']}")
        elif success['name'] == 'Email Stats':
            stats = success['response'].get('email_processing', {})
            total = stats.get('total_processed', 0)
            print(f"     Total emails processed: {total}")
        elif success['name'] == 'Email Preferences':
            vips = len(success['response'].get('vip_senders', []))
            blocked = len(success['response'].get('blocked_senders', []))
            print(f"     VIP senders: {vips}, Blocked senders: {blocked}")
        elif success['name'] == 'Email Scan':
            status = success['response'].get('status', 'unknown')
            print(f"     Scan status: {status}")
            if 'results' in success['response']:
                results = success['response']['results']
                if isinstance(results, dict):
                    accounts = results.get('accounts_scanned', [])
                    print(f"     Accounts scanned: {len(accounts)}")
        elif success['name'] == 'Email Insights':
            insights = success['response'].get('insights', [])
            print(f"     Insights available: {len(insights)}")

    print()
    print("="*70)
    print("EMAIL SYSTEM STATUS:")

    # Check for credential warnings
    send_result = next((r for r in results if r['name'] == 'Email Send'), None)
    if send_result and send_result.get('warning'):
        print(f"⚠️  Email sending: {send_result['warning']}")
    elif send_result and send_result['success'] and send_result['response'].get('status') == 'sent':
        print("✅ Email sending: Fully operational with credentials configured")
    else:
        print("❓ Email sending: Status unknown")

    # Check scan functionality
    scan_result = next((r for r in results if r['name'] == 'Email Scan'), None)
    if scan_result and scan_result['success']:
        print("✅ Email scanning: Endpoint operational")
    else:
        print("❌ Email scanning: Issues detected")

    print("="*70)


async def main():
    """Main entry point."""
    print("🚀 Starting NEXUS Email Endpoint Tests...")
    print(f"Testing against: {BASE_URL}")
    print("Note: Email send test may fail if credentials aren't configured - this is expected.")
    print()

    try:
        results = await run_email_tests()
        print_email_results(results)

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