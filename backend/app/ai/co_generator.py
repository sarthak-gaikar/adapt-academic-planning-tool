"""
ADAPT — Course Outcome Generator Engine

Grounded generation of OBE Course Outcomes using structured syllabus and RAG context.
Enforces deterministic Bloom ordering after LLM generation.
"""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.co_generation import (
    CO_GENERATION_SYSTEM_PROMPT,
    CO_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.course_outcome import CourseOutcome
from app.models.generation_run import GenerationRun
from app.models.subject import Subject
from app.models.syllabus import Syllabus, SyllabusUnit, Topic
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.course_outcome import COGenerationRequest, COGenerationResponseSchema
from app.validators.bloom_order_validator import BloomOrderValidator, bloom_to_order

logger = get_logger("ai.co_generator")


class COGenerator:
    """Generates measurable Course Outcomes grounded in syllabus RAG context."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_cos(
        self,
        subject_id: UUID,
        user_id: UUID,
        request: Optional[COGenerationRequest] = None,
    ) -> List[CourseOutcome]:
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

        units_summary_lines = []
        for u in syllabus.structured_data.get("units", []):
            top_names = [t.get("name", "") for t in u.get("topics", [])]
            units_summary_lines.append(
                f"- Unit {u.get('unit_number')}: {u.get('title')} ({u.get('hours', 0)} hrs) -> Topics: {', '.join(top_names[:5])}"
            )
        units_summary = "\n".join(units_summary_lines)

        # 3. Retrieve Context via RAG
        chunks = await self.retriever.retrieve(
            query=f"Course objectives syllabus outcomes {subject.name}",
            subject_id=subject_id,
            top_k=4,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=5000)

        # 4. Prompt LLM
        req = request or COGenerationRequest()
        prompt = CO_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            course_code=subject.course_code or "N/A",
            credits=subject.credits or "N/A",
            teaching_hours=subject.teaching_hours or "N/A",
            syllabus_units_summary=units_summary,
            retrieved_context=context_str,
            num_cos=req.num_cos or 6,
            additional_guidelines=f"Faculty Notes: {req.guidelines}" if req.guidelines else "",
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="CO_GENERATION",
            model_used="gpt-4o",
            input_params={"num_cos": req.num_cos, "guidelines": req.guidelines},
            retrieved_documents=[str(c.chunk_id) for c in chunks],
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=COGenerationResponseSchema,
                system_prompt=CO_GENERATION_SYSTEM_PROMPT,
            )

            # Archive existing draft COs
            existing_cos = await self.db.execute(
                select(CourseOutcome).where(
                    CourseOutcome.subject_id == subject_id,
                    CourseOutcome.status == "DRAFT",
                )
            )
            for old_co in existing_cos.scalars().all():
                old_co.status = "ARCHIVED"

            # 5. Classify Bloom levels and build items for validation
            co_items = []
            for item in structured_res.course_outcomes:
                bloom_res = await self.bloom_classifier.classify(item.statement)
                co_items.append({
                    "co_code": item.co_code,
                    "statement": item.statement,
                    "bloom_level": bloom_res.level,
                    "bloom_order": bloom_res.level_number,
                    "bloom_confidence": bloom_res.confidence,
                    "bloom_model_used": bloom_res.model_used,
                    "supporting_units": item.supporting_units,
                    "rationale": item.rationale,
                })

            # 6. Deterministic Bloom Order Validation
            validation_result = BloomOrderValidator.validate_cos(co_items)

            if not validation_result.is_valid:
                # Reorder COs to enforce increasing Bloom order
                logger.info(
                    f"CO Bloom ordering invalid ({validation_result.errors}). "
                    f"Reordering deterministically."
                )
                co_items, reorder_result = BloomOrderValidator.reorder_cos(co_items)
                # Update bloom_order after reordering
                for item in co_items:
                    item["bloom_order"] = bloom_to_order(item["bloom_level"])

            # 7. Create CO records with validated ordering
            created_cos = []
            for item in co_items:
                co = CourseOutcome(
                    subject_id=subject_id,
                    generation_run_id=gen_run.id,
                    co_code=item["co_code"],
                    statement=item["statement"],
                    bloom_level=item["bloom_level"],
                    bloom_order=item["bloom_order"],
                    bloom_confidence=item["bloom_confidence"],
                    bloom_model_used=item["bloom_model_used"],
                    supporting_units=item["supporting_units"],
                    rationale=item["rationale"],
                    status="DRAFT",
                    version=1,
                )
                self.db.add(co)
                created_cos.append(co)

            gen_run.status = "COMPLETED"
            gen_run.validation_result = {
                "bloom_ordering": validation_result.to_dict(),
                "was_reordered": not validation_result.is_valid,
            }
            await self.db.commit()
            return created_cos

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"CO generation failed: {e}")
            raise LLMError(f"Failed to generate course outcomes: {str(e)}")
