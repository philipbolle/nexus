"""
Manual Task Manager Service

Central service for logging tasks that require human intervention and cannot be
automated by AI agents, even with user approval. Handles database storage,
markdown file synchronization, deduplication, and integration with existing
monitoring and alerting systems.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import filelock

from ..database import db
from ..exceptions.manual_tasks import ManualInterventionRequired
from ..config import settings

logger = logging.getLogger(__name__)


class ManualTaskManager:
    """
    Manages manual tasks requiring human intervention.

    Features:
    - Database storage with deduplication via content hashing
    - Markdown file synchronization with thread-safe file locking
    - Integration with existing monitoring and alerting systems
    - Categorization and prioritization of manual tasks
    """

    def __init__(self, markdown_path: Optional[str] = None):
        """
        Initialize the manual task manager.

        Args:
            markdown_path: Path to the philip-tasks markdown file.
                           Defaults to "philip-tasks" in project root.
        """
        self.markdown_path = Path(
            markdown_path or getattr(settings, "manual_tasks_file_path", "philip-tasks")
        )
        self._lock = asyncio.Lock()
        self._file_lock = filelock.FileLock(str(self.markdown_path) + ".lock")
        logger.info(f"ManualTaskManager initialized with markdown path: {self.markdown_path}")

    async def log_manual_task(self, exception: ManualInterventionRequired) -> str:
        """
        Log a manual task from an exception.

        Args:
            exception: ManualInterventionRequired exception with task details

        Returns:
            Task ID (database UUID)
        """
        # Generate content hash for deduplication
        content_hash = self._generate_content_hash(
            exception.title,
            exception.description,
            exception.category
        )

        # Check for duplicates (skip if identical task already pending)
        existing = await self._check_duplicate(content_hash)
        if existing:
            logger.info(f"Duplicate manual task detected: {exception.title} (ID: {existing})")
            return existing

        # Store in database
        task_id = await self._store_in_database(exception, content_hash)

        # Update markdown file
        await self._update_markdown_file(task_id, exception)

        # Log success
        logger.info(
            f"Logged manual task: {exception.title} (ID: {task_id}, "
            f"Category: {exception.category}, Priority: {exception.priority})"
        )

        # TODO: Integrate with monitoring system for alerts
        # await self._notify_new_task(task_id, exception)

        return task_id

    def _generate_content_hash(self, title: str, description: str, category: str) -> str:
        """
        Generate SHA-256 hash for deduplication.

        Args:
            title: Task title
            description: Task description
            category: Task category

        Returns:
            SHA-256 hash string
        """
        content = f"{title}:{description}:{category}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _check_duplicate(self, content_hash: str) -> Optional[str]:
        """
        Check if task with same content already exists and is pending.

        Args:
            content_hash: SHA-256 hash of task content

        Returns:
            Task ID if duplicate exists, None otherwise
        """
        try:
            result = await db.fetch_one(
                """
                SELECT id FROM manual_tasks
                WHERE content_hash = $1 AND status IN ('pending', 'in_progress')
                """,
                content_hash
            )
            return result["id"] if result else None
        except Exception as e:
            logger.error(f"Error checking for duplicate task: {e}")
            return None

    async def _store_in_database(self, exception: ManualInterventionRequired, content_hash: str) -> str:
        """
        Store task in manual_tasks database table.

        Args:
            exception: ManualInterventionRequired exception
            content_hash: SHA-256 hash for deduplication

        Returns:
            Task ID (database UUID)
        """
        try:
            task_id = await db.fetch_val(
                """
                INSERT INTO manual_tasks
                (title, description, category, priority, source_system, source_id,
                 source_context, content_hash, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW())
                RETURNING id
                """,
                exception.title,
                exception.description,
                exception.category,
                exception.priority,
                exception.source_system,
                exception.source_id,
                json.dumps(exception.context),
                content_hash
            )
            logger.debug(f"Stored manual task in database: {exception.title} (ID: {task_id})")
            return task_id
        except Exception as e:
            logger.error(f"Failed to store manual task in database: {e}")
            # Re-raise to allow caller to handle the error
            raise

    async def _update_markdown_file(self, task_id: str, exception: ManualInterventionRequired) -> None:
        """
        Update the philip-tasks markdown file with new task.

        Args:
            task_id: Database task ID
            exception: ManualInterventionRequired exception
        """
        async with self._lock:
            try:
                with self._file_lock:
                    # Read existing content
                    if self.markdown_path.exists():
                        with open(self.markdown_path, 'r') as f:
                            content = f.read()
                    else:
                        # Initialize with header if file doesn't exist
                        content = "# Philip Tasks - Manual Intervention Required\n\n"
                        content += "Tasks that absolutely cannot be automated by AI agents, even with user approval.\n"
                        content += "These tasks are automatically logged by NEXUS systems when they encounter\n"
                        content += "scenarios they cannot handle.\n\n"

                    # Parse and update content
                    updated_content = self._insert_task_into_markdown(
                        content, task_id, exception
                    )

                    # Write back
                    with open(self.markdown_path, 'w') as f:
                        f.write(updated_content)

                    logger.debug(f"Updated markdown file with task: {exception.title}")
            except filelock.Timeout:
                logger.warning(f"File lock timeout for {self.markdown_path}, skipping markdown update")
            except Exception as e:
                logger.error(f"Failed to update markdown file: {e}")

    def _insert_task_into_markdown(self, content: str, task_id: str, exception: ManualInterventionRequired) -> str:
        """
        Insert task into markdown at appropriate section.

        Args:
            content: Current markdown content
            task_id: Database task ID
            exception: ManualInterventionRequired exception

        Returns:
            Updated markdown content
        """
        lines = content.split('\n')
        category_header = f"## {exception.category.title()} Tasks"
        task_entry = self._format_task_entry(task_id, exception)

        # Find or create category section
        category_start = -1
        for i, line in enumerate(lines):
            if line.strip() == category_header:
                category_start = i
                break

        if category_start == -1:
            # Category doesn't exist, create it at the end
            lines.append("")
            lines.append(category_header)
            lines.append("")
            lines.append(task_entry)
            lines.append("")
        else:
            # Insert task after category header
            # Find where to insert (after header and any existing tasks)
            insert_pos = category_start + 1
            while insert_pos < len(lines) and lines[insert_pos].strip() != "" and not lines[insert_pos].startswith("##"):
                insert_pos += 1

            # Insert task
            lines.insert(insert_pos, task_entry)
            if insert_pos < len(lines) and lines[insert_pos] != "":
                lines.insert(insert_pos, "")

        return '\n'.join(lines)

    def _format_task_entry(self, task_id: str, exception: ManualInterventionRequired) -> str:
        """
        Format a single task entry for markdown.

        Args:
            task_id: Database task ID
            exception: ManualInterventionRequired exception

        Returns:
            Formatted markdown task entry
        """
        priority_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(exception.priority, "⚪")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry = f"1. **{priority_emoji} [{exception.priority.upper()}] {exception.title}**\n"
        entry += f"   - **ID**: `{task_id}`\n"
        entry += f"   - **Created**: {timestamp}\n"
        entry += f"   - **Source**: {exception.source_system}\n"
        if exception.source_id:
            entry += f"   - **Source ID**: `{exception.source_id}`\n"
        entry += f"   - **Description**: {exception.description}\n"

        # Add context if present
        if exception.context:
            entry += f"   - **Context**: `{json.dumps(exception.context, indent=2)}`\n"

        return entry

    async def mark_task_completed(self, task_id: str, notes: Optional[str] = None) -> bool:
        """
        Mark a manual task as completed.

        Args:
            task_id: Database task ID
            notes: Optional resolution notes

        Returns:
            True if successful, False otherwise
        """
        try:
            await db.execute(
                """
                UPDATE manual_tasks
                SET status = 'completed',
                    completed_at = NOW(),
                    resolution_notes = $2,
                    updated_at = NOW()
                WHERE id = $1
                """,
                task_id,
                notes
            )

            # Update markdown file to remove or mark as completed
            await self._update_markdown_completion(task_id)

            logger.info(f"Marked manual task as completed: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as completed: {e}")
            return False

    async def _update_markdown_completion(self, task_id: str) -> None:
        """
        Update markdown file to reflect task completion.

        Args:
            task_id: Database task ID
        """
        try:
            # Regenerate markdown file from database (only pending tasks remain)
            await self.sync_markdown_from_database()
            logger.debug(f"Markdown file updated after completion of task {task_id}")
        except Exception as e:
            logger.error(f"Failed to update markdown file after task completion: {e}")
            # Non-critical error - task is still marked completed in database

    async def get_pending_tasks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get pending manual tasks.

        Args:
            category: Optional category filter

        Returns:
            List of pending tasks
        """
        try:
            query = """
                SELECT id, title, description, category, priority,
                       source_system, source_id, created_at, updated_at, source_context
                FROM manual_tasks
                WHERE status = 'pending'
            """
            params = []

            if category:
                query += " AND category = $1"
                params.append(category)

            query += " ORDER BY "
            query += "CASE priority "
            query += "WHEN 'critical' THEN 1 "
            query += "WHEN 'high' THEN 2 "
            query += "WHEN 'medium' THEN 3 "
            query += "WHEN 'low' THEN 4 END, "
            query += "created_at"

            tasks = await db.fetch_all(query, *params)
            return [dict(task) for task in tasks]
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []

    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get manual task by ID.

        Args:
            task_id: Database task ID

        Returns:
            Task details or None if not found
        """
        try:
            task = await db.fetch_one(
                """
                SELECT * FROM manual_tasks WHERE id = $1
                """,
                task_id
            )
            return dict(task) if task else None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def sync_markdown_from_database(self) -> bool:
        """
        Regenerate markdown file from database (full sync).

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                with self._file_lock:
                    # Get all pending tasks grouped by category
                    tasks = await db.fetch_all(
                        """
                        SELECT id, title, description, category, priority,
                               source_system, source_id, created_at, updated_at, source_context
                        FROM manual_tasks
                        WHERE status = 'pending'
                        ORDER BY category,
                                 CASE priority
                                     WHEN 'critical' THEN 1
                                     WHEN 'high' THEN 2
                                     WHEN 'medium' THEN 3
                                     WHEN 'low' THEN 4 END,
                                 created_at
                        """
                    )

                    # Generate markdown content
                    content = self._generate_full_markdown(tasks)

                    # Write to file
                    with open(self.markdown_path, 'w') as f:
                        f.write(content)

                    logger.info(f"Regenerated markdown file with {len(tasks)} pending tasks")
                    return True
            except Exception as e:
                logger.error(f"Failed to sync markdown from database: {e}")
                return False

    def _generate_full_markdown(self, tasks: List[Any]) -> str:
        """
        Generate complete markdown content from task list.

        Args:
            tasks: List of task records from database

        Returns:
            Complete markdown content
        """
        # Header
        content = "# Philip Tasks - Manual Intervention Required\n\n"
        content += "Tasks that absolutely cannot be automated by AI agents, even with user approval.\n"
        content += "These tasks are automatically logged by NEXUS systems when they encounter\n"
        content += "scenarios they cannot handle.\n\n"

        content += "**Last Updated**: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"

        # Group tasks by category
        tasks_by_category: Dict[str, List[Any]] = {}
        for task in tasks:
            category = task["category"]
            if category not in tasks_by_category:
                tasks_by_category[category] = []
            tasks_by_category[category].append(task)

        # Generate sections
        for category, category_tasks in tasks_by_category.items():
            content += f"## {category.title()} Tasks\n\n"

            for i, task in enumerate(category_tasks, 1):
                priority_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(task["priority"], "⚪")

                timestamp = task["created_at"].strftime("%Y-%m-%d %H:%M")

                content += f"{i}. **{priority_emoji} [{task['priority'].upper()}] {task['title']}**\n"
                content += f"   - **ID**: `{task['id']}`\n"
                content += f"   - **Created**: {timestamp}\n"
                content += f"   - **Source**: {task['source_system']}\n"
                if task["source_id"]:
                    content += f"   - **Source ID**: `{task['source_id']}`\n"
                content += f"   - **Description**: {task['description']}\n"

                # Add context if present
                if task.get("source_context"):
                    try:
                        context = json.loads(task["source_context"])
                        if context:
                            content += f"   - **Context**: `{json.dumps(context, indent=2)}`\n"
                    except:
                        pass

                content += "\n"

            content += "\n"

        # Add completed tasks section (optional - could be added later)
        # content += "## Completed Tasks\n\n"
        # content += "*No completed tasks to display*\n\n"

        return content


# Global instance for easy import
manual_task_manager = ManualTaskManager()