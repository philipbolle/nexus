#!/usr/bin/env python3
"""
Simple test for orchestrator engine task decomposition.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_orchestrator_decomposition():
    """Test basic task decomposition."""
    print("=== Testing Orchestrator Task Decomposition ===\n")

    try:
        from app.agents.orchestrator import OrchestratorEngine, DecompositionStrategy

        # Create orchestrator instance (doesn't need full initialization for decomposition)
        orchestrator = OrchestratorEngine()

        # Test task decomposition
        task = "Build a web scraper that extracts product data from e-commerce sites"
        print(f"Test task: {task}\n")

        # Test hierarchical decomposition
        decomposition = await orchestrator.decompose_task(
            task,
            strategy=DecompositionStrategy.HIERARCHICAL
        )

        print(f"Decomposition successful!")
        print(f"Task ID: {decomposition.task_id}")
        print(f"Strategy: {decomposition.strategy.value}")
        print(f"Number of subtasks: {len(decomposition.subtasks)}")
        print(f"Estimated total complexity: {decomposition.estimated_total_complexity}")
        print(f"Max parallelism: {decomposition.max_parallelism}")
        print(f"Critical path: {decomposition.critical_path}")

        print("\nSubtasks:")
        for i, subtask in enumerate(decomposition.subtasks):
            print(f"  {i+1}. {subtask.id}: {subtask.description}")
            print(f"     Capabilities: {subtask.required_capabilities}")
            print(f"     Complexity: {subtask.estimated_complexity}")
            print(f"     Dependencies: {subtask.dependencies}")

        # Test delegation plan creation (requires registry, might fail)
        print("\n\n=== Testing Delegation Plan (requires agent registry) ===")
        try:
            # Initialize registry (might fail if database not connected)
            # We'll skip this for now as it's not critical for decomposition test
            print("Skipping delegation plan test (requires full initialization)")
        except Exception as e:
            print(f"Delegation plan test skipped: {e}")

        print("\n=== Test Completed ===")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔧 Testing Orchestrator Engine")
    print("=" * 60)

    success = await test_orchestrator_decomposition()

    print("=" * 60)
    if success:
        print("✅ Orchestrator decomposition test PASSED")
    else:
        print("❌ Orchestrator decomposition test FAILED")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)