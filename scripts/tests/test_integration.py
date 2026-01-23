#!/usr/bin/env python3
"""
Integration test for auto-yes tool using a pseudo-terminal.
"""

import pexpect
import time
import sys
import os
import signal

def test_auto_yes():
    """Test auto-yes by spawning a shell and sending prompts."""
    print("Starting integration test...")

    # Spawn a new bash shell
    child = pexpect.spawn('bash', encoding='utf-8', timeout=5)

    # Start auto-yes in the background with short timeout
    child.sendline('cd /home/philip/nexus')
    child.expect(r'\$')

    child.sendline('python3 scripts/auto_yes.py --timeout 1 &')
    child.expect(r'\$')

    # Wait a moment for auto-yes to start
    time.sleep(1)

    # Send a test prompt
    child.sendline('echo "Test prompt: Update? (y/N)" && read -r response && echo "Response: $response"')

    # The auto-yes should answer 'y'
    try:
        child.expect('Response: y', timeout=3)
        print("✓ Auto-yes answered prompt correctly")
    except pexpect.TIMEOUT:
        print("✗ Auto-yes did not answer prompt")
        child.close()
        return False

    # Test Enter to skip
    child.sendline('echo "press Enter to skip" && read -r response2 && echo "Response2: $response2"')
    try:
        child.expect('Response2: ', timeout=3)
        print("✓ Auto-yes pressed Enter for skip prompt")
    except pexpect.TIMEOUT:
        print("✗ Auto-yes did not handle Enter prompt")
        child.close()
        return False

    child.close()
    return True

if __name__ == '__main__':
    if test_auto_yes():
        print("\n✅ Integration test passed!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)