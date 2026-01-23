#!/usr/bin/env python3
"""
Check if SMTP columns exist in database.
"""

import asyncio
import sys
sys.path.append('.')

from app.database import db

async def check_columns():
    print("Checking database for SMTP columns...")
    print("="*60)

    try:
        # First check if we can connect
        await db.connect()
        print("✅ Database connection successful")

        # Check SMTP columns in email_accounts table
        query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'email_accounts'
            AND column_name LIKE 'smtp%'
            ORDER BY column_name
        """

        columns = await db.fetch_all(query)

        if columns:
            print(f"\n✅ Found {len(columns)} SMTP columns in email_accounts table:")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

            # Check if any accounts have SMTP configured
            smtp_query = """
                SELECT email, smtp_server, smtp_port
                FROM email_accounts
                WHERE smtp_server IS NOT NULL
                LIMIT 5
            """
            smtp_accounts = await db.fetch_all(smtp_query)

            if smtp_accounts:
                print(f"\n✅ Found {len(smtp_accounts)} accounts with SMTP configured:")
                for acc in smtp_accounts:
                    print(f"   - {acc['email']}: {acc['smtp_server']}:{acc['smtp_port']}")
            else:
                print("\n⚠️  No accounts have SMTP configured yet")
                print("   SMTP configuration needs to be added to email_accounts table")

        else:
            print("\n❌ No SMTP columns found in email_accounts table")
            print("   The schema migration may not have been applied")

        # Check total tables
        tables_query = "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'public'"
        tables_result = await db.fetch_one(tables_query)
        print(f"\n📊 Total tables in database: {tables_result['count']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

async def main():
    await check_columns()

if __name__ == "__main__":
    asyncio.run(main())