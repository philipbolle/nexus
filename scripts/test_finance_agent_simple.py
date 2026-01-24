#!/usr/bin/env python3
"""
Simple test to verify Finance Agent imports and basic structure.
"""

import sys
sys.path.insert(0, '/home/philip/nexus')

def test_imports():
    """Test that all imports work."""
    try:
        from app.agents.finance_agent import FinanceAgent, register_finance_agent
        print("✓ Successfully imported FinanceAgent and register_finance_agent")

        # Check class structure
        agent_class = FinanceAgent
        print(f"✓ FinanceAgent class: {agent_class}")
        print(f"✓ Base classes: {agent_class.__bases__}")

        # Check required methods
        required_methods = ['_on_initialize', '_on_cleanup', '_process_task', '_register_finance_tools']
        for method in required_methods:
            if hasattr(agent_class, method):
                print(f"✓ Has method: {method}")
            else:
                print(f"✗ Missing method: {method}")
                return False

        # Check registration function
        import inspect
        if inspect.iscoroutinefunction(register_finance_agent):
            print("✓ register_finance_agent is async function")
        else:
            print("✗ register_finance_agent is not async")
            return False

        print("\n✅ All imports and structure checks passed!")
        return True

    except Exception as e:
        print(f"\n❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports()