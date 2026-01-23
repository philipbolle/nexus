#!/usr/bin/env python3
"""
Comprehensive Email System Test Report
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

async def test_endpoint(session, method, path, name, data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{path}"
    try:
        if method == 'GET':
            async with session.get(url) as response:
                status = response.status
                text = await response.text()
        elif method == 'POST':
            async with session.post(url, json=data) as response:
                status = response.status
                text = await response.text()

        try:
            json_data = json.loads(text) if text else {}
        except:
            json_data = {"raw": text[:200]}

        return {
            "name": name,
            "status": status,
            "success": 200 <= status < 300,
            "data": json_data
        }
    except Exception as e:
        return {"name": name, "success": False, "error": str(e)}

async def generate_report():
    print("NEXUS Email System Test Report")
    print("="*70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {BASE_URL}")
    print()

    async with aiohttp.ClientSession() as session:
        # Test all email endpoints
        endpoints = [
            ("GET", "/email/stats", "Email Statistics"),
            ("GET", "/email/preferences", "Email Preferences"),
            ("GET", "/email/summary", "Email Summary"),
            ("GET", "/email/recent", "Recent Emails"),
            ("GET", "/email/insights", "Email Insights"),
            ("POST", "/email/scan", "Email Scan", {"since_days": 1, "limit": 5}),
            ("POST", "/email/insights/generate", "Generate Insights"),
        ]

        results = []
        for endpoint in endpoints:
            if len(endpoint) == 4:
                method, path, name, data = endpoint
            else:
                method, path, name = endpoint
                data = None

            result = await test_endpoint(session, method, path, name, data)
            results.append(result)

        # Analyze results
        print("1. ENDPOINT AVAILABILITY")
        print("-" * 40)

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        print(f"✅ Working endpoints: {len(successful)}/{len(results)}")
        print(f"❌ Failed endpoints: {len(failed)}/{len(results)}")

        if failed:
            print("\nFailed endpoints:")
            for fail in failed:
                error_msg = fail.get('error', f'HTTP {fail.get("status")}')
                print(f"  - {fail['name']}: {error_msg}")

        print("\n2. EMAIL SCAN FUNCTIONALITY")
        print("-" * 40)

        scan_result = next((r for r in results if r["name"] == "Email Scan"), None)
        if scan_result and scan_result["success"]:
            scan_data = scan_result["data"]
            status = scan_data.get("status", "unknown")
            print(f"Scan status: {status}")

            if "results" in scan_data:
                results_data = scan_data["results"]
                accounts = results_data.get("accounts_scanned", [])
                if accounts:
                    print(f"Accounts scanned: {', '.join(accounts)}")
                    print("✅ Email scanning is operational")
                else:
                    print("⚠️  Scan completed but no accounts were scanned")
            else:
                print("ℹ️  Scan endpoint responded but no detailed results")
        else:
            print("❌ Email scan endpoint failed")

        print("\n3. DATABASE INTEGRATION")
        print("-" * 40)

        stats_result = next((r for r in results if r["name"] == "Email Statistics"), None)
        if stats_result and stats_result["success"]:
            stats_data = stats_result["data"]
            print("✅ Email statistics endpoint working")

            # Check for data in response
            if stats_data.get("email_processing"):
                print("ℹ️  Email processing data available")
            else:
                print("⚠️  No email processing data returned")
        else:
            print("❌ Email statistics endpoint failed")

        print("\n4. CREDENTIALS & CONNECTIVITY")
        print("-" * 40)

        # Check .env for credentials
        try:
            with open('.env', 'r') as f:
                env_content = f.read()

            has_gmail = 'GMAIL_EMAIL=' in env_content and 'GMAIL_APP_PASSWORD=' in env_content
            has_icloud = 'ICLOUD_EMAIL=' in env_content and 'ICLOUD_APP_PASSWORD=' in env_content

            print(f"Gmail credentials: {'✅ Configured' if has_gmail else '❌ Not configured'}")
            print(f"iCloud credentials: {'✅ Configured' if has_icloud else '❌ Not configured'}")

            if not has_gmail and not has_icloud:
                print("⚠️  No email credentials configured - scanning won't work")
            elif has_gmail or has_icloud:
                print("✅ At least one email account is configured")

        except FileNotFoundError:
            print("❌ .env file not found")
        except Exception as e:
            print(f"❌ Error checking .env: {e}")

        print("\n5. NEW EMAIL SEND ENDPOINT")
        print("-" * 40)

        # Test the new /email/send endpoint
        send_result = await test_endpoint(
            session, "POST", "/email/send", "Email Send",
            {
                "account": "gmail",
                "to_addresses": ["test@example.com"],
                "subject": "Test Email",
                "body": "Test body",
                "is_html": False
            }
        )

        if send_result["status"] == 404:
            print("❌ /email/send endpoint not found (404)")
            print("   This endpoint was added recently but the API service needs to be restarted")
            print("   Run: sudo systemctl restart nexus-api")
        elif send_result["success"]:
            print("✅ /email/send endpoint is working")
            if send_result["data"].get("status") == "sent":
                print("   Email sending is fully operational with credentials")
            else:
                print(f"   Endpoint responded: {send_result['data']}")
        else:
            error_msg = send_result.get('error', f'HTTP {send_result.get("status")}')
            print(f"❌ /email/send endpoint failed: {error_msg}")

        print("\n6. SUMMARY & RECOMMENDATIONS")
        print("-" * 40)

        total_tests = len(results) + 1  # +1 for the send endpoint test
        passed_tests = len(successful) + (1 if send_result.get("success") else 0)

        print(f"Overall test score: {passed_tests}/{total_tests}")

        if passed_tests == total_tests:
            print("🎉 Excellent! All email system components are working.")
        elif passed_tests >= total_tests * 0.7:
            print("⚠️  Good! Most components are working, but some issues need attention.")
        else:
            print("❌ Needs work! Multiple components are failing.")

        print("\nRecommended actions:")
        if any(f["name"] == "Email Scan" for f in failed):
            print("  - Fix email scan endpoint (check IMAP credentials and connection)")

        if send_result["status"] == 404:
            print("  - Restart the API service to enable the new /email/send endpoint")
            print("    Command: sudo systemctl restart nexus-api")

        if not (has_gmail or has_icloud):
            print("  - Configure email credentials in .env file")

        print("\n" + "="*70)
        print("Test completed.")

async def main():
    await generate_report()

if __name__ == "__main__":
    asyncio.run(main())