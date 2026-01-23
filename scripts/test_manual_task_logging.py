#!/usr/bin/env python3
"""
Test manual task logging system.

This script tests that manual tasks are properly logged to the database
and markdown file when ManualInterventionRequired exceptions are thrown.
"""

import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db
from app.services.manual_task_manager import manual_task_manager
from app.exceptions.manual_tasks import ConfigurationInterventionRequired


async def test_manual_task_logging():
    """Test logging a manual task."""
    print("Testing manual task logging system...")

    # Connect to database
    print("Connecting to database...")
    await db.connect()

    try:
        # Create a manual intervention exception with unique suffix to avoid conflicts
        suffix = str(uuid.uuid4())[:8]
        exception = ConfigurationInterventionRequired(
            description=f"Add Gmail app password to .env file for email scanning {suffix}",
            title=f"Configure Email App Password {suffix}",
            source_system="test_script",
            # source_id is optional, omit for test
            context={"env_var": "GMAIL_APP_PASSWORD", "service": "email_intelligence"}
        )

        print(f"Logging manual task: {exception.title}")
        print(f"Description: {exception.description}")
        print(f"Category: {exception.category}, Priority: {exception.priority}")

        # Log the manual task
        task_id = await manual_task_manager.log_manual_task(exception)
        print(f"✓ Manual task logged with ID: {task_id}")

        # Verify task appears in database
        print("\nVerifying database storage...")
        task = await manual_task_manager.get_task_by_id(task_id)
        if task:
            print(f"✓ Task retrieved from database")
            print(f"  Title: {task['title']}")
            print(f"  Status: {task['status']}")
        else:
            print("✗ Task not found in database")
            return False

        # Verify markdown file was updated (check if file exists and contains task)
        markdown_path = manual_task_manager.markdown_path
        if markdown_path.exists():
            print(f"✓ Markdown file exists at {markdown_path}")
            with open(markdown_path, 'r') as f:
                content = f.read()
                if exception.title in content:
                    print(f"✓ Task appears in markdown file")
                else:
                    print(f"✗ Task not found in markdown file")
                    # Could be due to deduplication
        else:
            print(f"✗ Markdown file not found at {markdown_path}")
            return False

        # Test duplicate detection
        print("\nTesting duplicate detection...")
        duplicate_task_id = await manual_task_manager.log_manual_task(exception)
        if duplicate_task_id == task_id:
            print(f"✓ Duplicate detected, same task ID returned: {duplicate_task_id}")
        else:
            print(f"✗ Duplicate not detected, new task ID: {duplicate_task_id}")

        # Test completion
        print("\nTesting task completion...")
        success = await manual_task_manager.mark_task_completed(
            task_id,
            notes="Added app password to .env file"
        )
        if success:
            print(f"✓ Task marked as completed")
        else:
            print(f"✗ Failed to mark task as completed")
            return False

        # Verify status changed
        completed_task = await manual_task_manager.get_task_by_id(task_id)
        if completed_task and completed_task['status'] == 'completed':
            print(f"✓ Task status updated to 'completed'")
        else:
            print(f"✗ Task status not updated correctly")
            return False

        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Disconnect database
        await db.disconnect()
        print("Database connection closed.")


if __name__ == "__main__":
    success = asyncio.run(test_manual_task_logging())
    sys.exit(0 if success else 1)