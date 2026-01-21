#!/usr/bin/env python3
"""
Test agent framework imports to identify issues.
"""

import sys
import traceback

print("Testing agent framework imports...")
print("="*60)

# Try to import agent framework components
modules_to_test = [
    "app.agents.registry",
    "app.agents.base",
    "app.agents.tools",
    "app.agents.sessions",
    "app.agents.orchestrator",
    "app.agents.memory",
    "app.agents.monitoring",
    "app.models.agent_schemas",
    "app.routers.agents",
    "app.routers.evolution"
]

for module_name in modules_to_test:
    print(f"\nTesting import: {module_name}")
    try:
        __import__(module_name)
        print(f"  ✅ Success")
    except ImportError as e:
        print(f"  ❌ ImportError: {e}")
        # Print more details for specific errors
        if "AgentType" in str(e) or "AgentStatus" in str(e):
            print(f"     This suggests missing base classes in app.agents.base")
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
        traceback.print_exc()

print("\n" + "="*60)
print("Testing router imports from main.py perspective...")
print("="*60)

# Test the imports that main.py does
try:
    from app.routers import agents, evolution
    print("✅ Successfully imported agents router")
    print("✅ Successfully imported evolution router")

    # Check if routers have endpoints
    print(f"\nAgents router prefix: {agents.router.prefix if hasattr(agents.router, 'prefix') else 'No prefix'}")
    print(f"Agents router tags: {agents.router.tags if hasattr(agents.router, 'tags') else 'No tags'}")

    print(f"\nEvolution router prefix: {evolution.router.prefix if hasattr(evolution.router, 'prefix') else 'No prefix'}")
    print(f"Evolution router tags: {evolution.router.tags if hasattr(evolution.router, 'tags') else 'No tags'}")

except ImportError as e:
    print(f"❌ ImportError: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("Testing if agent schemas can be instantiated...")
print("="*60)

try:
    from app.models.agent_schemas import AgentCreate, AgentType
    print("✅ Successfully imported AgentCreate")

    # Try to create a test agent schema
    test_agent = AgentCreate(
        name="test-agent",
        agent_type=AgentType.GENERAL,
        description="Test agent",
        system_prompt="Test",
        capabilities=["test"],
        domain="testing",
        config={}
    )
    print(f"✅ Successfully created AgentCreate instance: {test_agent.name}")

except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Error creating schema: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("Summary:")
print("="*60)
print("If imports fail, the agent framework may not be fully implemented.")
print("Check for missing files or incomplete implementations in:")
print("  - app/agents/ directory")
print("  - app/models/agent_schemas.py")
print("  - app/routers/agents.py")
print("  - app/routers/evolution.py")