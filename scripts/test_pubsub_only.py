#!/usr/bin/env python3
"""
Test Redis Pub/Sub only.
"""

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.swarm.pubsub import SwarmPubSub
from app.database import db

async def test():
    await db.connect()
    print("Connected to database")

    pubsub = SwarmPubSub()
    await pubsub.initialize()

    test_channel = f"test_channel_{uuid4().hex[:8]}"
    test_message = {"type": "test", "data": "Hello from test", "timestamp": time.time()}

    received_messages = []

    # Subscribe to channel
    await pubsub.subscribe(test_channel)
    print(f"Subscribed to channel: {test_channel}")

    # Start listening in background
    async def listen_for_messages():
        try:
            async for message in pubsub.listen():
                print(f"Received: {message}")
                received_messages.append(message)
                break
        except asyncio.CancelledError:
            pass

    listener_task = asyncio.create_task(listen_for_messages())

    # Give listener time to start
    await asyncio.sleep(0.5)

    # Publish message
    await pubsub.publish(test_channel, test_message)
    print(f"Published message to {test_channel}")

    # Wait for message to be delivered
    await asyncio.sleep(1)

    # Cancel listener
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    # Unsubscribe
    await pubsub.unsubscribe(test_channel)

    # Check if message was received
    if len(received_messages) > 0:
        print(f"✅ Redis Pub/Sub test passed ({len(received_messages)} messages received)")
    else:
        print(f"❌ Redis Pub/Sub test failed - no messages received")

    await pubsub.close()
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test())