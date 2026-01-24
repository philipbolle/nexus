#!/usr/bin/env python3
"""
Fix agent_tools.input_schema JSONB column.
"""

import asyncio
import json
import sys

sys.path.insert(0, '/home/philip/nexus')

async def fix_agent_tools():
    from app.database import db

    print("Fixing agent_tools.input_schema JSONB column...")

    await db.connect()

    try:
        # Get rows where input_schema is stored as a string (JSON string)
        # Use ::text to get raw representation
        rows = await db.fetch_all('''
            SELECT id, input_schema::text as raw_value
            FROM agent_tools
            WHERE input_schema IS NOT NULL
        ''')

        print(f"Found {len(rows)} rows")

        fixed = 0
        for row in rows:
            row_id = row['id']
            raw_value = row['raw_value']

            if raw_value is None:
                continue

            # Check if it's a JSON object/array string
            if raw_value.strip().startswith(('{', '[')):
                try:
                    parsed = json.loads(raw_value)
                    # Update with parsed JSON
                    await db.execute(
                        'UPDATE agent_tools SET input_schema = $1::jsonb WHERE id = $2',
                        parsed, row_id
                    )
                    fixed += 1
                    print(f"  Fixed row {row_id}")
                except json.JSONDecodeError:
                    print(f"  Invalid JSON in row {row_id}: {raw_value[:100]}")
            else:
                # Not a JSON string, leave as is
                pass

        print(f"Fixed {fixed} rows")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(fix_agent_tools())