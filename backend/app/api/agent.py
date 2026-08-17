"""
ADAPT — Supervisor Agent Natural Language API

POST /api/agent/execute — Execute natural language faculty command
"""

from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.supervisor import SupervisorAgent
from app.api.deps import get_current_user
from app.core.background_tasks import get_task_manager
from app.database import async_session_factory, get_db
from app.models.subject import Subject
from app.models.user import User

router = APIRouter(prefix="/api/agent", tags=["Supervisor Agent"])


class AgentRequest(BaseModel):
    subject_id: UUID
    prompt: str = Field(..., description="Natural language faculty request")


async def _run_bg_agent_command(task_info, subject_id: UUID, user_id: UUID, prompt: str):
    async with async_session_factory() as session:
        agent = SupervisorAgent(session)
        return await agent.execute_faculty_request(subject_id, user_id, prompt)


@router.post("/execute", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def execute_agent_command(
    req: AgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a natural-language faculty command to the Supervisor Agent."""
    res = await db.execute(select(Subject).where(Subject.id == req.subject_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    task_mgr = get_task_manager()
    task_id = task_mgr.submit(
        f"Supervisor Agent: '{req.prompt[:50]}...'",
        _run_bg_agent_command,
        req.subject_id,
        current_user.id,
        req.prompt,
    )
    return {"task_id": task_id, "message": "Agent request submitted for execution."}
