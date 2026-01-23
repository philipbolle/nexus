#!/usr/bin/env python3
"""
Test script for auto-yes tool.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auto_yes import AutoYes
import re

def test_pattern_matching():
    """Test that patterns match expected prompts."""
    auto_yes = AutoYes()

    test_cases = [
        ("Update current goals in .clauderc? (y/N)", "y\n"),
        ("Are you sure? (Y/n)", "y\n"),
        ("confirm?", "yes\n"),
        ("Continue?", "y\n"),
        ("yes/no", "yes\n"),
        ("press Enter to skip", "\n"),
        ("[Y/n]", "y\n"),
        ("[y/N]", "y\n"),
        ("Are you sure?", "yes\n"),
        ("Proceed?", "y\n"),
        ("OK to continue?", "y\n"),
    ]

    print("Testing pattern matching...")
    all_passed = True

    for prompt, expected_response in test_cases:
        matched = False
        for pattern, response in auto_yes.patterns:
            if re.search(pattern, prompt):
                if response == expected_response:
                    print(f"  ✓ '{prompt}' -> '{response.strip()}'")
                else:
                    print(f"  ✗ '{prompt}' -> expected '{expected_response.strip()}', got '{response.strip()}'")
                    all_passed = False
                matched = True
                break

        if not matched:
            print(f"  ✗ '{prompt}' -> NO MATCH")
            all_passed = False

    return all_passed

def test_import():
    """Test that all required modules can be imported."""
    try:
        import pexpect
        import psutil
        print("✓ All dependencies import successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def main():
    print("=== Auto-Yes Test Suite ===\n")

    # Test imports
    if not test_import():
        sys.exit(1)

    # Test pattern matching
    if not test_pattern_matching():
        sys.exit(1)

    print("\n✓ All tests passed!")
    print("\nTo run integration test:")
    print("  1. In one terminal: ./scripts/auto_yes_wrapper.sh start 1")
    print("  2. In another terminal: ./end_session.sh")
    print("  3. Auto-yes should answer the prompts automatically")

if __name__ == '__main__':
    main()