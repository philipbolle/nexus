#!/usr/bin/env python3
"""
Fix JSONB columns with codec issues.

This script identifies JSONB columns where values are stored as strings
instead of proper JSON objects, and converts them to proper JSON.
Also handles invalid JSON by setting to null or a default value.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List, Tuple
from datetime import datetime

# Add app directory to path
sys.path.insert(0, '/home/philip/nexus')

async def fix_jsonb_columns(dry_run: bool = True):
    """Fix JSONB columns with string values and invalid JSON."""
    from app.database import db

    print("🔧 Fixing JSONB column issues...")
    if dry_run:
        print("📋 DRY RUN - no changes will be made")

    try:
        await db.connect()

        # Columns identified as problematic from previous scan
        problematic_columns = [
            ("public", "agent_tools", "input_schema"),
            ("public", "manual_tasks", "source_context"),
            ("public", "settings", "value"),
            ("public", "system_config", "value"),
        ]

        # Primary key column mapping for tables without 'id' column
        primary_key_map = {
            ("public", "settings"): "key",
            # Add other tables as needed
        }

        total_fixed = 0
        total_errors = 0

        for schema, table, column in problematic_columns:
            full_name = f"{schema}.{table}.{column}"
            print(f"\n📝 Processing {full_name}...")

            # Get rows where column is a string (text)
            # Note: We need to detect if the stored value is a string
            # Since asyncpg will decode JSONB as dict/list if codec works,
            # we need to use raw SQL to check the actual storage type.
            # We'll use pg_typeof to check the runtime type.
            # Actually, if codec is broken, it will return as string.
            # Let's fetch raw text representation using ::text cast.

            pk_column = primary_key_map.get((schema, table), "id")

            query = f'''
                SELECT {pk_column}, "{column}"::text as raw_value, pg_typeof("{column}") as type_name
                FROM "{schema}"."{table}"
                WHERE "{column}" IS NOT NULL
                LIMIT 100
            '''

            rows = await db.fetch_all(query)

            if not rows:
                print(f"  No data to process")
                continue

            print(f"  Found {len(rows)} rows to examine")

            fixed_rows = 0
            error_rows = 0

            for row in rows:
                row_id = row[pk_column]
                raw_value = row['raw_value']
                type_name = row['type_name']

                # Skip if already proper JSON (type_name might be 'jsonb' but raw_value is JSON string)
                # We need to check if raw_value is a JSON string that can be parsed
                if raw_value is None:
                    continue

                # Try to parse raw_value as JSON
                try:
                    parsed = json.loads(raw_value)
                    # If parsed successfully, check if it's a dict or list
                    # (these should be stored as proper JSON objects/arrays, not JSON strings)
                    if isinstance(parsed, (dict, list)):
                        # Need to update the row to store as proper JSON
                        # (re-inserting the same value with proper codec should work)
                        if not dry_run:
                            # Update with parsed value
                            update_query = f'''
                                UPDATE "{schema}"."{table}"
                                SET "{column}" = $1::jsonb
                                WHERE {pk_column} = $2
                            '''
                            await db.execute(update_query, parsed, row_id)
                            fixed_rows += 1
                        else:
                            # Dry run: just count
                            fixed_rows += 1
                    else:
                        # Parsed as string, number, boolean, null
                        if isinstance(parsed, str) and parsed.strip().startswith(('{', '[')):
                            # Double-encoded JSON: string containing JSON object/array
                            try:
                                inner_parsed = json.loads(parsed)
                                if isinstance(inner_parsed, (dict, list)):
                                    if not dry_run:
                                        update_query = f'''
                                            UPDATE "{schema}"."{table}"
                                            SET "{column}" = $1::jsonb
                                            WHERE {pk_column} = $2
                                        '''
                                        await db.execute(update_query, inner_parsed, row_id)
                                        fixed_rows += 1
                                    else:
                                        fixed_rows += 1
                            except json.JSONDecodeError:
                                # Inner string is not valid JSON, leave as is
                                pass
                        # Other primitives (number, boolean, null) are fine as is
                        pass

                except json.JSONDecodeError:
                    # Invalid JSON - handle based on column
                    print(f"    ❌ Row {row_id}: Invalid JSON: {raw_value[:100]}...")
                    if not dry_run:
                        # For settings and system_config, we might want to set to null
                        # or keep as string? Let's set to null for safety.
                        update_query = f'''
                            UPDATE "{schema}"."{table}"
                            SET "{column}" = NULL
                            WHERE {pk_column} = $1
                        '''
                        await db.execute(update_query, row_id)
                        error_rows += 1
                    else:
                        error_rows += 1

            total_fixed += fixed_rows
            total_errors += error_rows

            print(f"  Fixed {fixed_rows} rows, {error_rows} invalid JSON rows")

        print(f"\n{'='*60}")
        print("📋 Fix Summary")
        print(f"{'='*60}")
        print(f"Total rows fixed: {total_fixed}")
        print(f"Total rows with errors (set to NULL): {total_errors}")
        print(f"Dry run: {'Yes' if dry_run else 'No'}")

        if dry_run:
            print(f"\n💡 To apply changes, run with --apply flag")
        else:
            print(f"\n✅ Changes applied successfully")

        # Return success/failure
        if total_errors > 0:
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
    import argparse

    parser = argparse.ArgumentParser(description="Fix JSONB columns with codec issues")
    parser.add_argument("--apply", action="store_true", help="Apply changes (otherwise dry run)")
    args = parser.parse_args()

    # Run async function
    exit_code = asyncio.run(fix_jsonb_columns(dry_run=not args.apply))
    sys.exit(exit_code)