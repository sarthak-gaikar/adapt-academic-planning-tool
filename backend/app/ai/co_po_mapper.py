"""
ADAPT — CO-PO Mapping Engine

Generates NBA-aligned suggested correlation matrix between active COs and POs.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider
from app.ai.prompts.co_po_mapping import (
    CO_PO_MAPPING_SYSTEM_PROMPT,
    CO_PO_MAPPING_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.co_po_mapping import COPOMapping
from app.models.course_outcome import CourseOutcome
from app.models.generation_run import GenerationRun
from app.models.program_outcome import ProgramOutcome
from app.models.subject import Subject
from app.schemas.co_po import COPOMappingResponseSchema

logger = get_logger("ai.co_po_mapper")


class COPOMapper:
    """Computes CO-PO mapping correlations with justifications."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()

    async def generate_mappings(
        self,
        subject_id: UUID,
        user_id: UUID,
    ) -> List[COPOMapping]:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Fetch Active COs
        co_res = await self.db.execute(
            select(CourseOutcome)
            .where(
                CourseOutcome.subject_id == subject_id,
                CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
            )
            .order_by(CourseOutcome.co_code)
        )
        cos = co_res.scalars().all()
        if not cos:
            raise NotFoundError("Course Outcomes", f"for subject {subject.name}. Please generate COs first.")

        # 3. Fetch POs
        po_res = await self.db.execute(
            select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
        )
        pos = po_res.scalars().all()
        if not pos:
            # Seed POs if empty
            await self._seed_default_pos()
            po_res = await self.db.execute(
                select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
            )
            pos = po_res.scalars().all()

        co_dict = {co.co_code: co for co in cos}
        po_dict = {po.po_code: po for po in pos}

        cos_text = "\n".join([f"- {co.co_code}: {co.statement} (Bloom: {co.bloom_level})" for co in cos])
        pos_text = "\n".join([f"- {po.po_code}: {po.statement}" for po in pos])

        prompt = CO_PO_MAPPING_USER_PROMPT.format(
            subject_name=subject.name,
            cos_text=cos_text,
            pos_text=pos_text,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="CO_PO_MAPPING",
            model_used="gpt-4o",
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=COPOMappingResponseSchema,
                system_prompt=CO_PO_MAPPING_SYSTEM_PROMPT,
            )

            # Clear existing draft mappings for this subject
            existing = await self.db.execute(
                select(COPOMapping).where(
                    COPOMapping.subject_id == subject_id,
                    COPOMapping.status == "DRAFT",
                )
            )
            for old_m in existing.scalars().all():
                await self.db.delete(old_m)
            await self.db.flush()

            created_mappings = []
            for cell in structured_res.mappings:
                co_obj = co_dict.get(cell.co_code)
                po_obj = po_dict.get(cell.po_code)
                if co_obj and po_obj:
                    mapping = COPOMapping(
                        subject_id=subject_id,
                        co_id=co_obj.id,
                        po_id=po_obj.id,
                        suggested_level=cell.suggested_level,
                        approved_level=cell.suggested_level, # Default approved to suggested until edited
                        rationale=cell.rationale,
                        status="DRAFT",
                    )
                    self.db.add(mapping)
                    created_mappings.append(mapping)

            # Ensure all CO x PO pairs exist (fill 0 for missing)
            for co_code, co_obj in co_dict.items():
                for po_code, po_obj in po_dict.items():
                    already_created = any(
                        m.co_id == co_obj.id and m.po_id == po_obj.id for m in created_mappings
                    )
                    if not already_created:
                        fallback_m = COPOMapping(
                            subject_id=subject_id,
                            co_id=co_obj.id,
                            po_id=po_obj.id,
                            suggested_level=0,
                            approved_level=0,
                            rationale="No direct alignment",
                            status="DRAFT",
                        )
                        self.db.add(fallback_m)
                        created_mappings.append(fallback_m)

            gen_run.status = "COMPLETED"
            await self.db.commit()
            return created_mappings

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"CO-PO mapping generation failed: {e}")
            raise LLMError(f"Failed to generate CO-PO mapping: {str(e)}")

    async def _seed_default_pos(self):
        """Seeds default PO1-PO12 + PSO1-PSO2 into ProgramOutcome table."""
        import json
        from pathlib import Path
        path = Path("data/knowledge_base/program_outcomes.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                po_list = json.load(f)
                for item in po_list:
                    po = ProgramOutcome(
                        po_code=item["po_code"],
                        statement=item["statement"],
                        category=item.get("category", "PO"),
                        is_active=True,
                    )
                    self.db.add(po)
            await self.db.flush()
