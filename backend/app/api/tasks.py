"""
ADAPT — Tasks API Endpoint

GET /api/tasks/{task_id} — Check background task status
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.models.user import User

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Check the status of a background task."""
    task_mgr = get_task_manager()
    task = task_mgr.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()
