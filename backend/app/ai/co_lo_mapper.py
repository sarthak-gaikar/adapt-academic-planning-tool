"""
ADAPT — CO-LO Mapping Engine

AI-suggested CO-LO mapping using Bloom alignment and syllabus semantics.
Faculty can edit/approve mappings after AI suggestion.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.course_outcome import CourseOutcome
from app.models.generation_run import GenerationRun
from app.models.learning_outcome import LearningOutcome
from app.models.lo_co_mapping import LOCOMapping
from app.models.subject import Subject
from app.schemas.co_lo import COLOMappingResponseSchema

logger = get_logger("ai.co_lo_mapper")

CO_LO_MAPPING_SYSTEM_PROMPT = """You are an OBE curriculum mapping expert.
Map Learning Outcomes (LOs) to Course Outcomes (COs).
For each LO, identify which CO(s) it contributes to.
Assign mapping_strength: 0=No alignment, 1=Low, 2=Medium, 3=High.
Only include mappings with strength >= 1.
Base mappings on:
- Bloom level alignment (LO Bloom should be at or below CO Bloom)
- Content/topic overlap between LO unit and CO supporting units
- Pedagogical coherence
"""

CO_LO_MAPPING_USER_PROMPT = """Map these Learning Outcomes to Course Outcomes:

Subject: {subject_name}

Course Outcomes:
{cos_text}

Learning Outcomes:
{los_text}
"""


class COLOMapper:
    """Generates AI-suggested CO-LO mappings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()

    async def generate_mappings(
        self,
        subject_id: UUID,
        user_id: UUID,
    ) -> List[LOCOMapping]:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Fetch COs
        co_res = await self.db.execute(
            select(CourseOutcome)
            .where(CourseOutcome.subject_id == subject_id, CourseOutcome.status.in_(["DRAFT", "APPROVED"]))
            .order_by(CourseOutcome.co_code)
        )
        cos = co_res.scalars().all()
        if not cos:
            raise NotFoundError("Course Outcomes", f"for subject {subject.name}")

        # 3. Fetch LOs
        lo_res = await self.db.execute(
            select(LearningOutcome)
            .where(LearningOutcome.subject_id == subject_id, LearningOutcome.status.in_(["DRAFT", "APPROVED"]))
            .order_by(LearningOutcome.lo_code)
        )
        los = lo_res.scalars().all()
        if not los:
            raise NotFoundError("Learning Outcomes", f"for subject {subject.name}")

        co_dict = {co.co_code: co for co in cos}
        lo_dict = {lo.lo_code: lo for lo in los}

        cos_text = "\n".join([f"- {co.co_code}: {co.statement} (Bloom: {co.bloom_level}, Units: {co.supporting_units})" for co in cos])
        los_text = "\n".join([f"- {lo.lo_code}: {lo.statement} (Bloom: {lo.bloom_level})" for lo in los])

        prompt = CO_LO_MAPPING_USER_PROMPT.format(
            subject_name=subject.name,
            cos_text=cos_text,
            los_text=los_text,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="CO_LO_MAPPING",
            model_used="gpt-4o",
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=COLOMappingResponseSchema,
                system_prompt=CO_LO_MAPPING_SYSTEM_PROMPT,
            )

            # Clear existing draft mappings for this subject's LOs
            for lo in los:
                existing = await self.db.execute(
                    select(LOCOMapping).where(
                        LOCOMapping.lo_id == lo.id,
                        LOCOMapping.status == "DRAFT",
                    )
                )
                for old_m in existing.scalars().all():
                    await self.db.delete(old_m)
            await self.db.flush()

            created_mappings = []
            for cell in structured_res.mappings:
                lo_obj = lo_dict.get(cell.lo_code)
                co_obj = co_dict.get(cell.co_code)
                if lo_obj and co_obj and cell.mapping_strength > 0:
                    mapping = LOCOMapping(
                        lo_id=lo_obj.id,
                        co_id=co_obj.id,
                        mapping_strength=cell.mapping_strength,
                        rationale=cell.rationale,
                        status="DRAFT",
                    )
                    self.db.add(mapping)
                    created_mappings.append(mapping)

            gen_run.status = "COMPLETED"
            await self.db.commit()
            return created_mappings

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"CO-LO mapping generation failed: {e}")
            raise LLMError(f"Failed to generate CO-LO mapping: {str(e)}")
