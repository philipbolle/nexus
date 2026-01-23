#!/usr/bin/env python3
"""
Minimal swarm communication test.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.swarm.pubsub import SwarmPubSub
from app.database import db

async def test_minimal():
    print("Testing minimal swarm communication...")

    # Connect to database
    await db.connect()
    print("Connected to database")

    # Test Pub/Sub
    pubsub = SwarmPubSub()
    await pubsub.initialize()
    print("Pub/Sub initialized")

    # Test publish
    await pubsub.publish("test_channel", {"test": "message"})
    print("Message published")

    await pubsub.close()
    await db.disconnect()
    print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_minimal())