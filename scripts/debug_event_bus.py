#!/usr/bin/env python3
"""
Debug script for Event Bus subscription issue.
"""

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.swarm.event_bus import SwarmEventBus
from app.agents.swarm.pubsub import SwarmPubSub
from app.database import db
from app.config import settings

async def debug_event_bus():
    """Debug event bus subscription issue."""
    print("🔍 Debugging Event Bus Subscription Issue")
    print("=" * 60)

    # Connect to database
    try:
        await db.connect()
        print("🔗 Connected to database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    try:
        # Test 1: Basic Pub/Sub
        print("\n1️⃣ Testing Redis Pub/Sub directly...")
        pubsub = SwarmPubSub()
        await pubsub.initialize()

        test_channel = f"debug_test_{uuid4().hex[:8]}"
        test_message = {"test": "direct pubsub", "timestamp": time.time()}

        received = []

        async def pubsub_listener():
            try:
                async for message in pubsub.listen():
                    print(f"  📨 PubSub received: {message}")
                    received.append(message)
                    break
            except asyncio.CancelledError:
                pass

        # Start listener
        listener_task = asyncio.create_task(pubsub_listener())
        await asyncio.sleep(0.5)

        # Subscribe to channel
        await pubsub.subscribe(test_channel)
        print(f"  📡 Subscribed to channel: {test_channel}")
        await asyncio.sleep(0.5)

        # Publish message
        recipients = await pubsub.publish(test_channel, test_message)
        print(f"  📤 Published to {test_channel}: {recipients} recipients")

        # Wait for message
        await asyncio.sleep(1)

        # Cancel listener
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

        print(f"  {'✅' if received else '❌'} Pub/Sub test: {len(received)} messages received")
        await pubsub.unsubscribe(test_channel)
        await pubsub.close()

        # Test 2: Event Bus with debug logging
        print("\n2️⃣ Testing Event Bus with debug...")
        event_bus = SwarmEventBus()
        await event_bus.initialize()

        test_event_type = f"debug_event_{uuid4().hex[:8]}"
        test_event_data = {"debug": "data", "value": 42}
        subscriber_id = f"debug_subscriber_{uuid4().hex[:8]}"

        received_events = []

        async def event_handler(event):
            print(f"  🎯 EVENT HANDLER CALLED: {event}")
            received_events.append(event)

        # Subscribe with handler
        print(f"  🔗 Subscribing to event type: {test_event_type}")
        await event_bus.subscribe(test_event_type, subscriber_id, event_handler)
        print(f"  📡 Subscribed to event type: {test_event_type}")

        # Give subscription time to establish
        await asyncio.sleep(1)

        # Publish event
        print(f"  📤 Publishing event...")
        event_id = await event_bus.publish_event(
            event_type=test_event_type,
            event_data=test_event_data,
            source_agent_id="debug_agent",
            store_in_db=False  # Don't store in DB for debug
        )
        print(f"  📤 Published event: {test_event_type} (ID: {event_id})")

        # Wait for event delivery with multiple checks
        print(f"  ⏳ Waiting for event delivery...")
        for i in range(10):
            if received_events:
                print(f"  ✅ Event received!")
                break
            print(f"  ... still waiting ({i+1}/10)")
            await asyncio.sleep(0.5)

        # Check Redis channels
        print(f"  🔍 Checking Redis channels...")
        # Try to manually listen to the channel
        debug_pubsub = SwarmPubSub()
        await debug_pubsub.initialize()

        channel = f"swarm:events:{test_event_type}"
        await debug_pubsub.subscribe(channel)

        async def debug_listener():
            try:
                async for message in debug_pubsub.listen():
                    print(f"  🔍 DEBUG: Raw Redis message on {channel}: {message}")
                    break
            except asyncio.CancelledError:
                pass

        debug_task = asyncio.create_task(debug_listener())
        await asyncio.sleep(0.5)

        # Publish another event to see if we get raw Redis message
        event_id2 = await event_bus.publish_event(
            event_type=test_event_type,
            event_data={"debug2": "test"},
            store_in_db=False
        )

        await asyncio.sleep(1)
        debug_task.cancel()
        try:
            await debug_task
        except asyncio.CancelledError:
            pass

        await debug_pubsub.unsubscribe(channel)
        await debug_pubsub.close()

        # Unsubscribe
        await event_bus.unsubscribe(test_event_type, subscriber_id)

        print(f"\n📊 Event Bus Debug Results:")
        print(f"  Events received by handler: {len(received_events)}")
        if received_events:
            print(f"  ✅ Event bus working!")
        else:
            print(f"  ❌ Event bus NOT receiving events")
            print(f"  Possible issues:")
            print(f"    - Event handler not being called")
            print(f"    - Message not reaching Redis channel")
            print(f"    - Listener task not running")

        await event_bus.close()

    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Disconnect from database
        await db.disconnect()
        print("🔗 Disconnected from database")

if __name__ == "__main__":
    asyncio.run(debug_event_bus())