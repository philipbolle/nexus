#!/usr/bin/env python3
"""
Check JSONB columns for codec issues.

This script scans all JSONB columns in the NEXUS database and checks
if they are being decoded as strings instead of dicts/lists, which indicates
missing JSONB codec registration.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add app directory to path
sys.path.insert(0, '/home/philip/nexus')

async def check_jsonb_columns():
    """Check all JSONB columns for codec issues."""
    from app.database import db

    print("🔍 Checking JSONB codec registration...")

    try:
        await db.connect()

        # Get all JSONB columns
        jsonb_columns = await db.fetch_all("""
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE data_type = 'jsonb'
            ORDER BY table_schema, table_name, column_name
        """)

        print(f"📊 Found {len(jsonb_columns)} JSONB columns")

        issues = []
        healthy_columns = []

        for col in jsonb_columns:
            schema = col['table_schema']
            table = col['table_name']
            column = col['column_name']
            full_name = f"{schema}.{table}.{column}"

            print(f"  Checking {full_name}...")

            # Test decoding with sample data
            try:
                # Get a few sample rows
                query = f"""
                    SELECT "{column}", pg_typeof("{column}") as type_name
                    FROM "{schema}"."{table}"
                    WHERE "{column}" IS NOT NULL
                    LIMIT 10
                """

                samples = await db.fetch_all(query)

                if not samples:
                    print(f"    No data to test")
                    healthy_columns.append(full_name)
                    continue

                # Analyze samples
                string_samples = 0
                dict_samples = 0
                list_samples = 0
                null_samples = 0
                invalid_samples = 0

                for sample in samples:
                    col_value = sample[column]
                    type_name = sample['type_name']

                    if col_value is None:
                        null_samples += 1
                    elif isinstance(col_value, str):
                        string_samples += 1
                        # Try to parse as JSON
                        try:
                            parsed = json.loads(col_value)
                            if isinstance(parsed, dict):
                                dict_samples += 1
                            elif isinstance(parsed, list):
                                list_samples += 1
                        except json.JSONDecodeError:
                            invalid_samples += 1
                    elif isinstance(col_value, dict):
                        dict_samples += 1
                    elif isinstance(col_value, list):
                        list_samples += 1

                print(f"    Samples: {len(samples)} total, {string_samples} strings, {dict_samples} dicts, {list_samples} lists")

                if string_samples > 0:
                    issue = {
                        "column": full_name,
                        "issue": "jsonb_decoded_as_string",
                        "severity": "warning",
                        "details": f"{string_samples} JSONB values were decoded as strings instead of dict/list",
                        "samples_tested": len(samples),
                        "string_samples": string_samples,
                        "dict_samples": dict_samples,
                        "list_samples": list_samples,
                        "invalid_json": invalid_samples
                    }
                    issues.append(issue)
                    print(f"    ⚠️  WARNING: {string_samples} values decoded as strings")
                else:
                    healthy_columns.append(full_name)
                    print(f"    ✅ Healthy")

                if invalid_samples > 0:
                    issue = {
                        "column": full_name,
                        "issue": "invalid_json_in_jsonb",
                        "severity": "error",
                        "details": f"{invalid_samples} JSONB values contain invalid JSON",
                        "samples_tested": len(samples)
                    }
                    issues.append(issue)
                    print(f"    ❌ ERROR: {invalid_samples} invalid JSON values")

            except Exception as e:
                print(f"    ❌ Error checking column: {e}")
                issues.append({
                    "column": full_name,
                    "issue": "check_failed",
                    "severity": "error",
                    "details": str(e)
                })

        # Generate report
        print("\n" + "="*60)
        print("📋 JSONB Codec Check Report")
        print("="*60)

        if issues:
            print(f"\n❌ Found {len([i for i in issues if i['severity'] == 'error'])} errors and {len([i for i in issues if i['severity'] == 'warning'])} warnings:")

            for issue in issues:
                severity_icon = "❌" if issue["severity"] == "error" else "⚠️"
                print(f"\n{severity_icon} {issue['severity'].upper()}: {issue['column']}")
                print(f"   Issue: {issue['issue']}")
                print(f"   Details: {issue['details']}")

                if "samples_tested" in issue:
                    print(f"   Samples tested: {issue['samples_tested']}")

                if issue["issue"] == "jsonb_decoded_as_string":
                    print(f"   Recommendation: Check JSONB codec registration in database.py")
                    print(f"   Fix: Ensure asyncpg has JSONB codec registered via register_json_codec()")
                elif issue["issue"] == "invalid_json_in_jsonb":
                    print(f"   Recommendation: Check data integrity in JSONB column")
                    print(f"   Fix: Validate JSON before insertion or run data cleanup")
        else:
            print("\n✅ All JSONB columns are healthy!")
            print(f"   Checked {len(healthy_columns)} columns")

        if healthy_columns:
            print(f"\n✅ Healthy columns ({len(healthy_columns)}):")
            for col in healthy_columns:
                print(f"   - {col}")

        print(f"\n📅 Report generated: {datetime.now().isoformat()}")

        # Return exit code based on issues
        if any(issue["severity"] == "error" for issue in issues):
            return 1
        elif any(issue["severity"] == "warning" for issue in issues):
            return 2
        else:
            return 0

    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await db.disconnect()

if __name__ == "__main__":
    # Run async function
    exit_code = asyncio.run(check_jsonb_columns())
    sys.exit(exit_code)