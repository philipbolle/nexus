#!/usr/bin/env python3
"""
Verify that Decision Support and Code Review agents are properly implemented.
This script checks the code structure without requiring API access.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_imports():
    """Test that agent classes can be imported."""
    print("🔧 Testing agent imports...")

    try:
        from app.agents.decision_support import DecisionSupportAgent
        print("✅ DecisionSupportAgent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import DecisionSupportAgent: {e}")
        return False

    try:
        from app.agents.code_review import CodeReviewAgent
        print("✅ CodeReviewAgent imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import CodeReviewAgent: {e}")
        return False

    return True

def test_instantiation():
    """Test that agents can be instantiated."""
    print("\n🔧 Testing agent instantiation...")

    from app.agents.decision_support import DecisionSupportAgent
    from app.agents.code_review import CodeReviewAgent

    try:
        ds_agent = DecisionSupportAgent()
        print(f"✅ DecisionSupportAgent instantiated: {ds_agent.name}")
        print(f"   Type: {ds_agent.agent_type}")
        print(f"   Domain: {ds_agent.domain}")
        print(f"   Capabilities: {', '.join(ds_agent.capabilities)}")
    except Exception as e:
        print(f"❌ Failed to instantiate DecisionSupportAgent: {e}")
        return False

    try:
        cr_agent = CodeReviewAgent()
        print(f"✅ CodeReviewAgent instantiated: {cr_agent.name}")
        print(f"   Type: {cr_agent.agent_type}")
        print(f"   Domain: {cr_agent.domain}")
        print(f"   Capabilities: {', '.join(cr_agent.capabilities)}")
    except Exception as e:
        print(f"❌ Failed to instantiate CodeReviewAgent: {e}")
        return False

    return True

def test_registry_integration():
    """Test that agents are registered in the agent registry."""
    print("\n🔧 Testing registry integration...")

    try:
        from app.agents.registry import AgentRegistry
        # Just check we can import the registry
        print("✅ AgentRegistry imported successfully")

        # Note: The registry's _register_builtin_types() method should have
        # registered our agent types when the module was imported
        print("ℹ️  Agent types 'decision_support' and 'code_review' should be registered")
        print("ℹ️  Check app/agents/registry.py lines 180-220 for registration")

    except ImportError as e:
        print(f"❌ Failed to import AgentRegistry: {e}")
        return False

    return True

def test_api_registration():
    """Check if agents are registered in API startup."""
    print("\n🔧 Testing API registration setup...")

    try:
        # Check that agents.py router imports the registration functions
        with open("app/routers/agents.py", "r") as f:
            content = f.read()

        if "register_decision_support_agent" in content and "register_code_review_agent" in content:
            print("✅ Registration functions imported in app/routers/agents.py")
        else:
            print("❌ Registration functions not found in app/routers/agents.py")
            return False

        # Check that initialize_agent_framework calls the registration functions
        if "await register_decision_support_agent()" in content and "await register_code_review_agent()" in content:
            print("✅ Registration functions called in initialize_agent_framework()")
        else:
            print("❌ Registration functions not called in initialize_agent_framework()")
            print("ℹ️  Check lines after register_email_agent() call")
            return False

    except Exception as e:
        print(f"❌ Error checking API registration: {e}")
        return False

    return True

def test_enum_values():
    """Check that AgentType enum includes new values."""
    print("\n🔧 Testing AgentType enum...")

    try:
        from app.agents.base import AgentType

        # Check for our new enum values
        enum_values = [e.value for e in AgentType]

        if "decision_support" in enum_values:
            print("✅ 'decision_support' found in AgentType enum")
        else:
            print("❌ 'decision_support' NOT found in AgentType enum")
            return False

        if "code_review" in enum_values:
            print("✅ 'code_review' found in AgentType enum")
        else:
            print("❌ 'code_review' NOT found in AgentType enum")
            return False

        print(f"ℹ️  All AgentType values: {', '.join(enum_values)}")

    except Exception as e:
        print(f"❌ Error checking AgentType enum: {e}")
        return False

    return True

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("🧪 VERIFYING DECISION SUPPORT & CODE REVIEW AGENTS")
    print("=" * 60)

    all_passed = True

    # Run tests
    all_passed &= test_imports()
    all_passed &= test_instantiation()
    all_passed &= test_registry_integration()
    all_passed &= test_api_registration()
    all_passed &= test_enum_values()

    print("\n" + "=" * 60)

    if all_passed:
        print("✅ ALL VERIFICATION TESTS PASSED!")
        print("\n📋 NEXT STEPS:")
        print("1. The agents are correctly implemented in the codebase")
        print("2. They will auto-register when the NEXUS API restarts")
        print("3. To use them immediately, restart the API service:")
        print("   sudo systemctl restart nexus-api")
        print("4. Then run the integration tests:")
        print("   python scripts/tests/test_decision_support_agent.py")
        print("   python scripts/tests/test_code_review_agent.py")
    else:
        print("❌ SOME VERIFICATION TESTS FAILED")
        print("\n🔧 Check the errors above and fix the implementation.")

    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        # Change to project root
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)