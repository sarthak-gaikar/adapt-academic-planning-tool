"""
ADAPT — Learning Outcome Generator Engine

Generates per-unit Learning Outcomes grounded in syllabus content and approved COs.
Enforces Bloom ordering within each unit using deterministic validation.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.lo_generation import (
    LO_GENERATION_SYSTEM_PROMPT,
    LO_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.course_outcome import CourseOutcome
from app.models.generation_run import GenerationRun
from app.models.learning_outcome import LearningOutcome
from app.models.lo_co_mapping import LOCOMapping
from app.models.subject import Subject
from app.models.syllabus import Syllabus, SyllabusUnit
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.learning_outcome import LOGenerationRequest, LOGenerationResponseSchema
from app.validators.bloom_order_validator import (
    BloomOrderValidator,
    bloom_to_order,
)

logger = get_logger("ai.lo_generator")


class LOGenerator:
    """Generates per-unit Learning Outcomes with Bloom ordering enforcement."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_los(
        self,
        subject_id: UUID,
        user_id: UUID,
        request: Optional[LOGenerationRequest] = None,
    ) -> List[LearningOutcome]:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Fetch Structured Syllabus
        syl_res = await self.db.execute(
            select(Syllabus)
            .where(Syllabus.subject_id == subject_id)
            .order_by(Syllabus.version.desc())
            .limit(1)
        )
        syllabus = syl_res.scalar_one_or_none()
        if not syllabus or not syllabus.structured_data:
            raise NotFoundError("Syllabus", f"for subject {subject.name}")

        # 3. Fetch SyllabusUnit ORM objects for FK references
        unit_res = await self.db.execute(
            select(SyllabusUnit)
            .where(SyllabusUnit.syllabus_id == syllabus.id)
            .order_by(SyllabusUnit.unit_number)
        )
        units_orm = {u.unit_number: u for u in unit_res.scalars().all()}

        # 4. Fetch approved/draft COs
        co_res = await self.db.execute(
            select(CourseOutcome)
            .where(
                CourseOutcome.subject_id == subject_id,
                CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
            )
            .order_by(CourseOutcome.co_code)
        )
        cos = co_res.scalars().all()
        cos_summary = "\n".join(
            [f"- {co.co_code}: {co.statement} (Bloom: {co.bloom_level})" for co in cos]
        ) or "No COs available yet."
        co_dict = {co.co_code: co for co in cos}

        # Determine target units
        req = request or LOGenerationRequest()
        units_data = syllabus.structured_data.get("units", [])
        if req.unit_numbers:
            units_data = [u for u in units_data if u.get("unit_number") in req.unit_numbers]

        if not units_data:
            raise NotFoundError("Units", f"No matching units found in syllabus for subject {subject.name}")

        # 5. Build unit details string for prompt
        unit_details_parts = []
        for u in units_data:
            t_names = [t.get("name", "") for t in u.get("topics", [])]
            subtopics_detail = ""
            for t in u.get("topics", []):
                subs = t.get("subtopics", [])
                if subs:
                    subtopics_detail += f"\n    - {t.get('name')}: {', '.join(subs[:5])}"
            unit_details_parts.append(
                f"Unit {u.get('unit_number')}: {u.get('title')} ({u.get('hours', 0)} hrs)\n"
                f"  Topics: {', '.join(t_names)}{subtopics_detail}"
            )
        unit_details_str = "\n\n".join(unit_details_parts)

        # 6. Retrieve RAG context per operation type
        chunks = await self.retriever.retrieve(
            query=f"Learning outcomes OBE Bloom taxonomy {subject.name} unit topics",
            subject_id=subject_id,
            top_k=6,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=6000)

        # 7. Build prompt
        prompt = LO_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            course_code=subject.course_code or "N/A",
            unit_details=unit_details_str,
            cos_summary=cos_summary,
            retrieved_context=context_str,
            num_los_per_unit=req.num_los_per_unit or "3 to 5",
            additional_guidelines=f"Faculty Notes: {req.guidelines}" if req.guidelines else "",
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="LO_GENERATION",
            model_used="gpt-4o",
            input_params={
                "unit_numbers": req.unit_numbers,
                "num_los_per_unit": req.num_los_per_unit,
            },
            retrieved_documents=[str(c.chunk_id) for c in chunks],
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=LOGenerationResponseSchema,
                system_prompt=LO_GENERATION_SYSTEM_PROMPT,
            )

            # Archive existing draft LOs for target units
            target_unit_ids = [
                units_orm[u.get("unit_number")].id
                for u in units_data
                if u.get("unit_number") in units_orm
            ]
            if target_unit_ids:
                existing_los = await self.db.execute(
                    select(LearningOutcome).where(
                        LearningOutcome.subject_id == subject_id,
                        LearningOutcome.unit_id.in_(target_unit_ids),
                        LearningOutcome.status == "DRAFT",
                    )
                )
                for old_lo in existing_los.scalars().all():
                    old_lo.status = "ARCHIVED"

            # 8. Classify Bloom levels and group by unit
            lo_items_by_unit: Dict[int, List[Dict]] = defaultdict(list)
            for item in structured_res.learning_outcomes:
                bloom_res = await self.bloom_classifier.classify(item.statement)
                lo_items_by_unit[item.unit_number].append({
                    "lo_code": item.lo_code,
                    "unit_number": item.unit_number,
                    "statement": item.statement,
                    "bloom_level": bloom_res.level,
                    "bloom_order": bloom_res.level_number,
                    "bloom_confidence": bloom_res.confidence,
                    "mapped_cos": item.mapped_cos,
                    "rationale": item.rationale,
                })

            # 9. Deterministic Bloom Order Validation per unit
            bloom_validation_results = {}
            for unit_num, unit_los in lo_items_by_unit.items():
                validation = BloomOrderValidator.validate_ordering(unit_los)
                if not validation.is_valid:
                    logger.info(
                        f"Unit {unit_num} LO Bloom ordering invalid. Reordering."
                    )
                    sorted_los, reorder_result = BloomOrderValidator.reorder_items(
                        unit_los,
                        bloom_key="bloom_level",
                        code_key="lo_code",
                        code_prefix=f"LO{unit_num}.",
                    )
                    # Update bloom_order
                    for lo_item in sorted_los:
                        lo_item["bloom_order"] = bloom_to_order(lo_item["bloom_level"])
                    lo_items_by_unit[unit_num] = sorted_los
                    bloom_validation_results[unit_num] = reorder_result.to_dict()
                else:
                    bloom_validation_results[unit_num] = validation.to_dict()

            # 10. Create LO records and CO mappings
            created_los: List[LearningOutcome] = []
            for unit_num, unit_los in lo_items_by_unit.items():
                unit_orm = units_orm.get(unit_num)
                if not unit_orm:
                    logger.warning(f"No SyllabusUnit found for unit_number {unit_num}, skipping.")
                    continue

                for lo_item in unit_los:
                    lo = LearningOutcome(
                        subject_id=subject_id,
                        unit_id=unit_orm.id,
                        generation_run_id=gen_run.id,
                        lo_code=lo_item["lo_code"],
                        statement=lo_item["statement"],
                        bloom_level=lo_item["bloom_level"],
                        bloom_order=lo_item["bloom_order"],
                        bloom_confidence=lo_item["bloom_confidence"],
                        rationale=lo_item["rationale"],
                        status="DRAFT",
                        version=1,
                    )
                    self.db.add(lo)
                    await self.db.flush()
                    await self.db.refresh(lo)
                    created_los.append(lo)

                    # Create CO mappings
                    for co_code in lo_item.get("mapped_cos", []):
                        co_obj = co_dict.get(co_code)
                        if co_obj:
                            mapping = LOCOMapping(
                                lo_id=lo.id,
                                co_id=co_obj.id,
                                mapping_strength=2,  # Default medium
                                rationale=f"AI-suggested mapping: {lo.lo_code} → {co_code}",
                                status="DRAFT",
                            )
                            self.db.add(mapping)

            gen_run.status = "COMPLETED"
            gen_run.validation_result = {
                "bloom_ordering_per_unit": bloom_validation_results,
                "total_los_generated": len(created_los),
            }
            await self.db.commit()
            return created_los

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"LO generation failed: {e}")
            raise LLMError(f"Failed to generate learning outcomes: {str(e)}")
