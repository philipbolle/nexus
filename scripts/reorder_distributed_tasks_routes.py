#!/usr/bin/env python3
"""
Reorder routes in distributed_tasks.py to fix FastAPI route precedence issue.

Moves parameterized routes @router.get("/{task_id}") and @router.post("/{task_id}/cancel")
to the end of the file so they don't catch static routes like /health, /stats, etc.
"""

import re
from pathlib import Path

file_path = Path(__file__).parent.parent / "app" / "routers" / "distributed_tasks.py"

with open(file_path, 'r') as f:
    content = f.read()

# Find the two problematic routes
# Pattern: @router.get("/{task_id}") ... until next @router or end of file
# We'll use a simpler approach: split by @router

lines = content.split('\n')

# Find start and end indices for each route
route_starts = []
for i, line in enumerate(lines):
    if line.strip().startswith('@router'):
        route_starts.append(i)

# Group routes by their start lines
routes = []
for i in range(len(route_starts)):
    start = route_starts[i]
    end = route_starts[i+1] if i+1 < len(route_starts) else len(lines)
    route_lines = lines[start:end]
    routes.append((start, end, route_lines))

# Identify which routes to move to end
task_id_routes = []
other_routes = []

for start, end, route_lines in routes:
    route_text = '\n'.join(route_lines)
    if '@router.get("/{task_id}")' in route_text or '@router.post("/{task_id}/cancel")' in route_text:
        task_id_routes.append((start, end, route_lines))
    else:
        other_routes.append((start, end, route_lines))

print(f"Found {len(routes)} total routes")
print(f"  {len(task_id_routes)} parameterized task_id routes to move to end")
print(f"  {len(other_routes)} other routes")

# Reconstruct lines in correct order
new_lines = []
for start, end, route_lines in other_routes:
    new_lines.extend(route_lines)
    new_lines.append('')  # Add blank line between routes

# Add the task_id routes at the end
for start, end, route_lines in task_id_routes:
    new_lines.extend(route_lines)
    new_lines.append('')

# Remove trailing blank lines
while new_lines and new_lines[-1] == '':
    new_lines.pop()

# Ensure we preserve the header (everything before first route)
first_route_start = min([start for start, end, route_lines in routes])
header_lines = lines[:first_route_start]

# Combine header + reordered routes
final_lines = header_lines + new_lines

# Write back
with open(file_path, 'w') as f:
    f.write('\n'.join(final_lines))

print(f"✓ Routes reordered successfully in {file_path}")
print("  Parameterized routes moved to end to fix route precedence.")