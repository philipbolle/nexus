#!/usr/bin/env python3
"""
Diagnose why distributed tasks routes are not accessible.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app

print("🔍 App routes:")
for route in app.routes:
    if hasattr(route, "path"):
        path = route.path
        methods = route.methods if hasattr(route, "methods") else ["GET"]
        print(f"  {path} - {methods}")

print("\n🔍 Checking distributed tasks router inclusion...")
# Check if router is included
for route in app.routes:
    if hasattr(route, "path") and "/distributed-tasks" in route.path:
        print(f"Found distributed tasks route: {route.path}")
        # Check if route is from the router we imported
        if hasattr(route, "endpoint"):
            print(f"  Endpoint: {route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else route.endpoint}")

print("\n🔍 Testing import of distributed_tasks router directly...")
from app.routers.distributed_tasks import router
print(f"Router prefix: {router.prefix}")
print(f"Router routes count: {len(router.routes)}")

print("\n🔍 Checking if router is in app.router.routes...")
# The router should be mounted
for r in app.router.routes:
    if hasattr(r, "path") and "/distributed-tasks" in r.path:
        print(f"  Mounted: {r.path}")

print("\n🔍 Checking app.include_router...")
# Check app.state for included routers
print("Done.")