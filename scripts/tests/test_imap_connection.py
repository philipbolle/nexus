#!/usr/bin/env python3
"""
Test IMAP connection directly.
"""

import asyncio
import sys
sys.path.append('.')

from app.services.email_client import connect_imap, fetch_emails

async def test_imap():
    print("Testing IMAP connections...")
    print("="*60)

    accounts = ["gmail", "icloud"]

    for account in accounts:
        print(f"\nTesting {account}...")

        # Test connection
        print(f"  1. Testing IMAP connection...")
        try:
            imap = connect_imap(account)
            if imap:
                print(f"     ✅ IMAP connection successful")
                # Try to logout properly
                try:
                    imap.logout()
                except:
                    pass
            else:
                print(f"     ❌ IMAP connection failed (check credentials)")
                continue
        except Exception as e:
            print(f"     ❌ IMAP connection error: {e}")
            continue

        # Test fetching emails
        print(f"  2. Testing email fetch...")
        try:
            emails = await fetch_emails(account=account, since_days=1, limit=5)
            if emails:
                print(f"     ✅ Found {len(emails)} emails")
                for i, email in enumerate(emails[:3]):  # Show first 3
                    print(f"       {i+1}. {email.sender}: {email.subject[:50]}...")
            else:
                print(f"     ⚠️  No emails found (might be no emails in last day)")
        except Exception as e:
            print(f"     ❌ Email fetch error: {e}")

    print("\n" + "="*60)
    print("Summary:")
    print("If connections fail, check:")
    print("1. App passwords are correct and not expired")
    print("2. IMAP is enabled in email account settings")
    print("3. Less secure app access is enabled (for Gmail)")
    print("4. Two-factor authentication is properly configured with app password")

async def main():
    await test_imap()

if __name__ == "__main__":
    asyncio.run(main())