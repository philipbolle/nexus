#!/usr/bin/env python3
"""
Test Event Bus only.
"""

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.swarm.event_bus import SwarmEventBus
from app.database import db

async def test():
    await db.connect()
    print("Connected to database")

    event_bus = SwarmEventBus()
    await event_bus.initialize()

    test_event_type = f"test_event_{uuid4().hex[:8]}"
    test_event_data = {"test": "data", "value": 42}
    subscriber_id = f"test_subscriber_{uuid4().hex[:8]}"

    received_events = []

    async def event_handler(event):
        print(f"📨 Event received: {event['event_type']} = {event['event_data']}")
        received_events.append(event)

    # Subscribe to event type with handler
    await event_bus.subscribe(test_event_type, subscriber_id, event_handler)
    print(f"📡 Subscribed to event type: {test_event_type}")

    # Publish event
    event_id = await event_bus.publish_event(test_event_type, test_event_data)
    print(f"📤 Published event: {test_event_type} (ID: {event_id})")

    # Wait for event to be delivered
    await asyncio.sleep(1)

    # Unsubscribe
    await event_bus.unsubscribe(test_event_type, subscriber_id)

    # Check if event was received
    if len(received_events) > 0:
        print(f"✅ Event Bus test passed ({len(received_events)} events received)")
    else:
        print(f"❌ Event Bus test failed - no events received")

    await event_bus.close()
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test())