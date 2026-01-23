#!/usr/bin/env python3
"""
Test currently working email endpoints (without /send since service needs restart).
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

async def test_endpoint(method, path, name, data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{path}"

    try:
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(url, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            elif method == 'POST':
                async with session.post(url, json=data, timeout=TIMEOUT) as response:
                    status = response.status
                    text = await response.text()
            else:
                return {"name": name, "success": False, "error": f"Unsupported method: {method}"}

            # Parse JSON
            try:
                json_data = json.loads(text) if text else {}
            except:
                json_data = {"raw": text[:200]}

            return {
                "name": name,
                "method": method,
                "path": path,
                "status": status,
                "success": 200 <= status < 300,
                "data": json_data
            }

    except Exception as e:
        return {"name": name, "success": False, "error": str(e)}

async def main():
    print("Testing NEXUS Email Endpoints")
    print("="*60)

    # Test endpoints that should be working
    tests = [
        ("GET", "/email/stats", "Email Stats"),
        ("GET", "/email/preferences", "Email Preferences"),
        ("GET", "/email/summary", "Email Summary"),
        ("GET", "/email/recent", "Email Recent"),
        ("GET", "/email/insights", "Email Insights"),
        ("POST", "/email/scan", "Email Scan", {"since_days": 1, "limit": 5}),
        ("POST", "/email/insights/generate", "Generate Insights"),
    ]

    results = []
    for test in tests:
        if len(test) == 4:
            method, path, name, data = test
        else:
            method, path, name = test
            data = None

        print(f"Testing {name} ({method} {path})...")
        result = await test_endpoint(method, path, name, data)
        results.append(result)

        if result["success"]:
            print(f"  ✅ Success (Status: {result['status']})")
            # Show some data for certain endpoints
            if name == "Email Stats":
                stats = result['data'].get('email_processing', {})
                print(f"     Total processed: {stats.get('total_processed', 'N/A')}")
            elif name == "Email Scan":
                status = result['data'].get('status', 'unknown')
                print(f"     Scan status: {status}")
        else:
            error_msg = result.get('error', f'Status: {result.get("status")}')
            print(f"  ❌ Failed: {error_msg}")

    print("\n" + "="*60)
    print("Summary:")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")

    if failed:
        print("\nFailed tests:")
        for fail in failed:
            error_msg = fail.get('error', f'Status {fail.get("status")}')
        print(f"  - {fail['name']}: {error_msg}")

    # Test IMAP connection (indirectly through scan)
    print("\n" + "="*60)
    print("IMAP Connection Test:")

    scan_result = next((r for r in results if r["name"] == "Email Scan"), None)
    if scan_result and scan_result["success"]:
        scan_data = scan_result["data"]
        if scan_data.get("status") == "completed":
            results_data = scan_data.get("results", {})
            accounts = results_data.get("accounts_scanned", [])
            if accounts:
                print(f"✅ IMAP connections successful for accounts: {', '.join(accounts)}")
            else:
                print("⚠️  Scan completed but no accounts were scanned (credentials may not be configured)")
        else:
            print(f"⚠️  Scan returned status: {scan_data.get('status')}")
    else:
        print("❌ Could not test IMAP connection (scan endpoint failed)")

    # Check for credential configuration
    print("\n" + "="*60)
    print("Credential Status:")

    # Check .env file for email credentials (without showing actual passwords)
    try:
        with open('.env', 'r') as f:
            env_content = f.read()

        has_gmail_email = 'GMAIL_EMAIL=' in env_content
        has_gmail_password = 'GMAIL_APP_PASSWORD=' in env_content
        has_icloud_email = 'ICLOUD_EMAIL=' in env_content
        has_icloud_password = 'ICLOUD_APP_PASSWORD=' in env_content

        print(f"Gmail credentials: {'✅ Configured' if has_gmail_email and has_gmail_password else '❌ Not configured'}")
        print(f"iCloud credentials: {'✅ Configured' if has_icloud_email and has_icloud_password else '❌ Not configured'}")

        if not (has_gmail_email and has_gmail_password) and not (has_icloud_email and has_icloud_password):
            print("\n⚠️  No email credentials configured. Email scanning will not work.")
            print("   To configure, add to .env file:")
            print("   GMAIL_EMAIL=your-email@gmail.com")
            print("   GMAIL_APP_PASSWORD=your-app-password")
            print("   ICLOUD_EMAIL=your-email@icloud.com")
            print("   ICLOUD_APP_PASSWORD=your-app-password")

    except FileNotFoundError:
        print("❌ .env file not found")
    except Exception as e:
        print(f"❌ Error checking .env: {e}")

if __name__ == "__main__":
    asyncio.run(main())