"""
ADAPT — Answer Key Generator Engine

Generates structured model solutions and marking rubrics for Exam Papers or Assignments.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider
from app.ai.prompts.answer_key_generation import (
    ANSWER_KEY_SYSTEM_PROMPT,
    ANSWER_KEY_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.answer_key import AnswerKey
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.exam import ExamPaper, ExamQuestion
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.schemas.answer_key import AnswerKeyResponseSchema

logger = get_logger("ai.answer_key_generator")


class AnswerKeyGenerator:
    """Generates official answer keys and marking rubrics."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()

    async def generate_exam_answer_key(
        self,
        exam_paper_id: UUID,
        user_id: UUID,
    ) -> AnswerKey:
        # Fetch ExamPaper
        res = await self.db.execute(select(ExamPaper).where(ExamPaper.id == exam_paper_id))
        paper = res.scalar_one_or_none()
        if not paper:
            raise NotFoundError("ExamPaper", str(exam_paper_id))

        # Fetch questions
        eq_res = await self.db.execute(
            select(ExamQuestion, Question)
            .join(Question, ExamQuestion.question_id == Question.id)
            .where(ExamQuestion.exam_paper_id == exam_paper_id)
            .order_by(ExamQuestion.sequence_order)
        )
        rows = eq_res.all()
        if not rows:
            raise NotFoundError("Questions", f"for exam paper {exam_paper_id}")

        q_list_text = []
        for eq, q in rows:
            q_list_text.append(
                f"Q{eq.sequence_order} [{eq.marks} marks] ({eq.section or 'Section A'}):\n"
                f"{q.question_text}\n"
                f"Question ID: {q.id}\n"
            )
        questions_text = "\n\n".join(q_list_text)

        prompt = ANSWER_KEY_USER_PROMPT.format(
            title=paper.title,
            exam_type=paper.exam_type,
            total_marks=paper.total_marks,
            questions_text=questions_text,
        )

        gen_run = GenerationRun(
            subject_id=paper.subject_id,
            triggered_by=user_id,
            operation="ANSWER_KEY_GENERATION",
            model_used="gpt-4o",
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=AnswerKeyResponseSchema,
                system_prompt=ANSWER_KEY_SYSTEM_PROMPT,
            )

            # Check existing answer key
            existing = await self.db.execute(
                select(AnswerKey).where(AnswerKey.exam_paper_id == exam_paper_id)
            )
            old_ak = existing.scalar_one_or_none()
            if old_ak:
                await self.db.delete(old_ak)
                await self.db.flush()

            answers_data = [a.model_dump() for a in structured_res.answers]
            ak = AnswerKey(
                exam_paper_id=paper.id,
                generation_run_id=gen_run.id,
                answers=answers_data,
                status="DRAFT",
                version=1,
            )
            self.db.add(ak)

            gen_run.status = "COMPLETED"
            await self.db.commit()
            return ak

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"Answer key generation failed: {e}")
            raise LLMError(f"Failed to generate answer key: {str(e)}")
