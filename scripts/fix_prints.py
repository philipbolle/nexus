#!/usr/bin/env python3
"""
Replace debug print statements with logger.debug in event_bus.py
"""
import re
import sys

file_path = "/home/philip/nexus/app/agents/swarm/event_bus.py"

with open(file_path, 'r') as f:
    content = f.read()

# Pattern to match print(f"DEBUG: ...", file=sys.stderr)
pattern = r'print\(f"DEBUG: ([^"]+)", file=sys\.stderr\)'

def replace_match(match):
    message = match.group(1)
    # Escape any backslashes in the message
    message = message.replace('\\', '\\\\')
    return f'logger.debug(f"{message}")'

new_content = re.sub(pattern, replace_match, content)

# Also handle prints with {variables} inside the f-string
# More complex pattern: print\(f"DEBUG: ([^"]+)"(?:, file=sys\.stderr)\)?
# Actually, we need to handle the whole line.
# Let's do a simpler line-by-line approach
lines = new_content.split('\n')
new_lines = []
for line in lines:
    if 'print(f"DEBUG:' in line and 'file=sys.stderr' in line:
        # Extract the message part between DEBUG: and ", file
        match = re.search(r'print\(f"DEBUG: ([^"]+)", file=sys\.stderr\)', line)
        if match:
            message = match.group(1)
            new_line = line.replace(match.group(0), f'logger.debug(f"{message}")')
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

with open(file_path, 'w') as f:
    f.write(new_content)

print(f"Fixed {file_path}")