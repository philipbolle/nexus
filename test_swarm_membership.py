#!/usr/bin/env python3
"""
Test swarm membership API schema issue.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_swarm_membership_schema():
    """Test the SwarmMembershipResponse schema."""
    from app.models.schemas import SwarmMembershipResponse
    from uuid import uuid4

    print("Testing SwarmMembershipResponse schema...")

    # Create a sample response that matches what the database returns
    sample_data = {
        "id": str(uuid4()),
        "swarm_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "agent_name": "Test Agent",
        "agent_type": "domain",
        "role": "member",
        "status": "active",
        "last_seen_at": "2024-01-22T12:00:00Z",
        "metadata": {},
        "joined_at": "2024-01-22T12:00:00Z",
        "contribution_score": 0.0,  # This field is in database but not in schema
        "vote_weight": 1.0  # This field is in database but not in schema
    }

    print(f"Sample data keys: {list(sample_data.keys())}")

    # Check what fields are in the schema
    schema_fields = SwarmMembershipResponse.__fields__.keys()
    print(f"Schema fields: {list(schema_fields)}")

    # Check which fields are missing from schema
    missing_in_schema = [k for k in sample_data.keys() if k not in schema_fields]
    print(f"Fields in data but not in schema: {missing_in_schema}")

    # Try to create the model
    try:
        response = SwarmMembershipResponse(**sample_data)
        print(f"✅ Schema validation passed")
        print(f"Response model: {response}")
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")

        # Try without the extra fields
        filtered_data = {k: v for k, v in sample_data.items() if k in schema_fields}
        print(f"\nTrying with filtered data (only schema fields)...")
        try:
            response = SwarmMembershipResponse(**filtered_data)
            print(f"✅ Filtered schema validation passed")
        except Exception as e2:
            print(f"❌ Even filtered validation failed: {e2}")

if __name__ == "__main__":
    asyncio.run(test_swarm_membership_schema())