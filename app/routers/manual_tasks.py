"""
Manual Tasks API Router

Endpoints for managing manual tasks that require human intervention.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID

from ..services.manual_task_manager import manual_task_manager
from ..models.schemas import ManualTaskResponse, ManualTaskUpdate, ManualTaskList

router = APIRouter(prefix="/manual-tasks", tags=["manual-tasks"])


@router.get("/", response_model=ManualTaskList)
async def list_tasks(
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    status: Optional[str] = Query(None, description="Filter by status"),
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum tasks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ManualTaskList:
    """
    List manual tasks with optional filtering.

    Returns tasks sorted by priority (critical first) then creation date.
    """
    try:
        # For now, get all pending tasks (filtering not yet implemented in manager)
        # We'll implement filtering in the service later
        tasks = await manual_task_manager.get_pending_tasks(category=category)

        # Convert to response format
        # TODO: Implement proper filtering and pagination in service
        task_responses = []
        for task in tasks:
            # Map database fields to response schema
            task_responses.append(ManualTaskResponse(
                id=task["id"],
                title=task["title"],
                description=task["description"],
                category=task["category"],
                priority=task["priority"],
                source_system=task["source_system"],
                source_id=task.get("source_id"),
                source_context=task.get("source_context"),
                assigned_to=None,  # Not in current query
                due_date=None,     # Not in current query
                resolution_notes=None,
                content_hash="",   # Not in current query
                status="pending",
                created_at=task["created_at"],
                updated_at=task["created_at"],  # TODO: Add updated_at to query
                completed_at=None
            ))

        # Counts (simplified for now)
        pending_count = len(task_responses)
        completed_count = 0

        return ManualTaskList(
            tasks=task_responses,
            total=len(task_responses),
            pending_count=pending_count,
            completed_count=completed_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list manual tasks: {str(e)}"
        )


@router.get("/{task_id}", response_model=ManualTaskResponse)
async def get_task(task_id: UUID) -> ManualTaskResponse:
    """
    Get a specific manual task by ID.
    """
    try:
        task = await manual_task_manager.get_task_by_id(str(task_id))
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manual task {task_id} not found"
            )

        # Map database fields to response schema
        return ManualTaskResponse(
            id=task["id"],
            title=task["title"],
            description=task["description"],
            category=task["category"],
            priority=task["priority"],
            source_system=task["source_system"],
            source_id=task.get("source_id"),
            source_context=task.get("source_context"),
            assigned_to=task.get("assigned_to"),
            due_date=task.get("due_date"),
            resolution_notes=task.get("resolution_notes"),
            content_hash=task["content_hash"],
            status=task["status"],
            created_at=task["created_at"],
            updated_at=task.get("updated_at", task["created_at"]),
            completed_at=task.get("completed_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get manual task: {str(e)}"
        )


@router.post("/{task_id}/complete", response_model=ManualTaskResponse)
async def complete_task(
    task_id: UUID,
    update: ManualTaskUpdate
) -> ManualTaskResponse:
    """
    Mark a manual task as completed.

    Requires resolution_notes in the update body.
    """
    try:
        # Validate that task exists
        task = await manual_task_manager.get_task_by_id(str(task_id))
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manual task {task_id} not found"
            )

        # Update task status to completed
        success = await manual_task_manager.mark_task_completed(
            str(task_id),
            notes=update.resolution_notes
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to mark task {task_id} as completed"
            )

        # Get updated task
        updated_task = await manual_task_manager.get_task_by_id(str(task_id))
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve updated task {task_id}"
            )

        # Map database fields to response schema
        return ManualTaskResponse(
            id=updated_task["id"],
            title=updated_task["title"],
            description=updated_task["description"],
            category=updated_task["category"],
            priority=updated_task["priority"],
            source_system=updated_task["source_system"],
            source_id=updated_task.get("source_id"),
            source_context=updated_task.get("source_context"),
            assigned_to=updated_task.get("assigned_to"),
            due_date=updated_task.get("due_date"),
            resolution_notes=updated_task.get("resolution_notes"),
            content_hash=updated_task["content_hash"],
            status=updated_task["status"],
            created_at=updated_task["created_at"],
            updated_at=updated_task.get("updated_at", updated_task["created_at"]),
            completed_at=updated_task.get("completed_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete manual task: {str(e)}"
        )


@router.post("/sync-markdown", status_code=status.HTTP_200_OK)
async def sync_markdown() -> dict:
    """
    Force synchronization of manual tasks to markdown file.

    This regenerates the philip-tasks markdown file from the database.
    Useful after manual database updates or file corruption.
    """
    try:
        success = await manual_task_manager.sync_markdown_from_database()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync markdown file"
            )

        return {"status": "success", "message": "Markdown file synchronized"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync markdown file: {str(e)}"
        )