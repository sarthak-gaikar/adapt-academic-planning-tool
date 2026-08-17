"""
ADAPT — Background Task Manager

In-process async task runner for long-running AI operations.
Tracks task status in-memory for the MVP; can be replaced with Celery/Redis later.
"""

import asyncio
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional

from app.core.logging import get_logger

logger = get_logger("tasks")


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskInfo:
    """Metadata about a running or completed background task."""

    def __init__(self, task_id: str, operation: str):
        self.task_id = task_id
        self.operation = operation
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: float = 0.0
        self.message: str = ""
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "operation": self.operation,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TaskManager:
    """
    Manages background async tasks.

    MVP implementation uses in-process asyncio tasks with an in-memory store.
    For production, swap with Celery + Redis without changing the interface.
    """

    def __init__(self, max_concurrent: int = 5):
        self._tasks: Dict[str, TaskInfo] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def submit(
        self,
        operation: str,
        coroutine_fn: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Submit a coroutine for background execution. Returns task_id."""
        task_id = str(uuid.uuid4())
        info = TaskInfo(task_id, operation)
        self._tasks[task_id] = info

        asyncio.create_task(self._run(task_id, coroutine_fn, *args, **kwargs))
        logger.info(f"Task {task_id} submitted: {operation}")
        return task_id

    async def _run(
        self,
        task_id: str,
        coroutine_fn: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ):
        """Execute the task with concurrency control."""
        info = self._tasks[task_id]
        async with self._semaphore:
            info.status = TaskStatus.RUNNING
            info.started_at = datetime.now(timezone.utc)
            logger.info(f"Task {task_id} started: {info.operation}")

            try:
                result = await coroutine_fn(info, *args, **kwargs)
                info.result = result
                info.status = TaskStatus.COMPLETED
                info.progress = 100.0
                info.completed_at = datetime.now(timezone.utc)
                logger.info(f"Task {task_id} completed: {info.operation}")
            except Exception as e:
                info.status = TaskStatus.FAILED
                info.error = str(e)
                info.completed_at = datetime.now(timezone.utc)
                logger.error(
                    f"Task {task_id} failed: {info.operation} — {e}\n"
                    f"{traceback.format_exc()}"
                )

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task info by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get all tracked tasks."""
        return self._tasks

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove completed/failed tasks older than max_age_hours."""
        now = datetime.now(timezone.utc)
        to_remove = []
        for task_id, info in self._tasks.items():
            if info.completed_at and (now - info.completed_at).total_seconds() > max_age_hours * 3600:
                to_remove.append(task_id)
        for task_id in to_remove:
            del self._tasks[task_id]


# Global singleton — initialized in main.py startup
task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global task_manager
    if task_manager is None:
        from app.config import get_settings
        task_manager = TaskManager(max_concurrent=get_settings().max_concurrent_tasks)
    return task_manager
