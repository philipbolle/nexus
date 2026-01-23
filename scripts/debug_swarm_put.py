#!/usr/bin/env python3
"""
Debug script for PUT endpoint bug in swarm router using live API.
"""
import asyncio
import sys
import traceback
import httpx
import uuid

API_BASE = "http://localhost:8080"

def random_name(prefix="debug"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

async def debug_put():
    """Test PUT endpoint with metadata."""
    async with httpx.AsyncClient() as client:
        swarm_name = random_name("test")
        # First create a swarm
        print(f"Creating test swarm '{swarm_name}'...")
        create_response = await client.post(
            f"{API_BASE}/swarm/",
            json={
                "name": swarm_name,
                "purpose": "debugging",
                "metadata": {"initial": True}
            }
        )
        print(f"Create response status: {create_response.status_code}")
        if create_response.status_code != 200:
            print(f"Create error: {create_response.text}")
            return False

        swarm_data = create_response.json()
        swarm_id = swarm_data["id"]
        print(f"Created swarm ID: {swarm_id}")
        print(f"Initial metadata: {swarm_data.get('metadata')}")

        # Now update metadata
        print("\nUpdating swarm metadata...")
        update_response = await client.put(
            f"{API_BASE}/swarm/{swarm_id}",
            json={
                "metadata": {"updated": True, "test": 123}
            }
        )
        print(f"Update response status: {update_response.status_code}")
        if update_response.status_code != 200:
            print(f"Update error: {update_response.text}")
            # Try to get more details
            try:
                error_detail = update_response.json()
                print(f"Error detail: {error_detail}")
            except:
                pass
            # Log the error from API logs maybe
            print("Checking API logs...")
            with open('/tmp/nexus_api.log', 'r') as f:
                lines = f.readlines()[-20:]
                for line in lines:
                    if 'ERROR' in line or 'Exception' in line:
                        print(f"Log: {line.strip()}")
            return False

        updated_data = update_response.json()
        print(f"Updated metadata: {updated_data.get('metadata')}")

        # Verify metadata is dict
        metadata = updated_data.get("metadata")
        if isinstance(metadata, dict):
            print("✅ Metadata is dict after update")
        else:
            print(f"❌ Metadata type after update: {type(metadata)}")
            return False

        # Also fetch swarm to confirm
        print("\nFetching swarm to verify...")
        get_response = await client.get(f"{API_BASE}/swarm/{swarm_id}")
        if get_response.status_code == 200:
            get_data = get_response.json()
            print(f"GET metadata: {get_data.get('metadata')}")
            if isinstance(get_data.get('metadata'), dict):
                print("✅ GET returns dict metadata")
            else:
                print(f"❌ GET metadata type: {type(get_data.get('metadata'))}")
                return False
        else:
            print(f"GET failed: {get_response.text}")
            return False

        # Cleanup: deactivate swarm
        await client.delete(f"{API_BASE}/swarm/{swarm_id}")
        return True

async def debug_put_with_null_metadata():
    """Test PUT with metadata=None (should not update)."""
    async with httpx.AsyncClient() as client:
        swarm_name = random_name("nulltest")
        # Create swarm
        print(f"\n--- Test with null metadata ({swarm_name}) ---")
        create_response = await client.post(
            f"{API_BASE}/swarm/",
            json={
                "name": swarm_name,
                "purpose": "debugging",
                "metadata": {"initial": True}
            }
        )
        swarm_id = create_response.json()["id"]

        # Update with metadata=None (should not change metadata field)
        update_response = await client.put(
            f"{API_BASE}/swarm/{swarm_id}",
            json={
                "name": "updated_name",
                "metadata": None
            }
        )
        print(f"Update with null metadata status: {update_response.status_code}")
        if update_response.status_code == 200:
            updated = update_response.json()
            print(f"Updated name: {updated.get('name')}")
            print(f"Metadata after null update: {updated.get('metadata')}")
            # Metadata should still be {"initial": True}
            if updated.get('metadata') == {"initial": True}:
                print("✅ Metadata unchanged when metadata=None")
            else:
                print(f"❌ Metadata changed unexpectedly: {updated.get('metadata')}")
        else:
            print(f"Update failed: {update_response.text}")
            return False
        # Cleanup
        await client.delete(f"{API_BASE}/swarm/{swarm_id}")
        return True

async def main():
    """Run debug tests."""
    print("🔧 Debugging PUT endpoint bug in swarm router (live API)")
    print("=" * 60)

    try:
        success = await debug_put()
        if success:
            print("\n✅ PUT endpoint test passed")
        else:
            print("\n❌ PUT endpoint test failed")
            return 1

        success2 = await debug_put_with_null_metadata()
        if success2:
            print("\n✅ Null metadata test passed")
        else:
            print("\n❌ Null metadata test failed")
            return 1

        print("\n✨ All debug tests passed!")
        return 0

    except Exception as e:
        print(f"\n💥 Unhandled exception: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))