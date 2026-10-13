"""
ADAPT — AAP Generator Engine

Generates semester-long Academic Activity Plans and runs deterministic constraint validation.

The institutional AAP Format document is retrieved from the system RAG knowledge base
and used as context. The actual output structure is enforced by the structured template
(AAPPlanDataSchema) — RAG provides style/format awareness, not free-form output.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider
from app.ai.prompts.aap_generation import (
    AAP_GENERATION_SYSTEM_PROMPT,
    AAP_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.aap import AAPPlan
from app.models.course_outcome import CourseOutcome
from app.models.generation_run import GenerationRun
from app.models.subject import Subject
from app.models.syllabus import Syllabus
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.aap import AAPGenerationRequest, AAPPlanDataSchema
from app.validators.aap_validator import AAPValidator

logger = get_logger("ai.aap_generator")

# Augmented system prompt with instruction to use retrieved AAP format
AAP_SYSTEM_PROMPT_WITH_RAG = AAP_GENERATION_SYSTEM_PROMPT + """

You have been provided with the institution's official AAP Format document.
Use it to understand the expected column structure, terminology, and formatting conventions.
The output MUST follow the institution's AAP structure — do not invent a different format.
"""

# Augmented user prompt that injects AAP format context
AAP_USER_PROMPT_WITH_RAG = """=== INSTITUTIONAL AAP FORMAT REFERENCE ===
{aap_format_context}
=== END AAP FORMAT ===

""" + AAP_GENERATION_USER_PROMPT


class AAPGenerator:
    """Generates and validates Academic Activity Plans.
    
    Retrieves the institutional AAP Format from system RAG knowledge base to use
    as authoritative context. The actual output structure is enforced by
    AAPPlanDataSchema — the schema is the template; RAG provides style awareness.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)

    async def generate_aap(
        self,
        subject_id: UUID,
        user_id: UUID,
        request: Optional[AAPGenerationRequest] = None,
    ) -> AAPPlan:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Fetch Syllabus
        syl_res = await self.db.execute(
            select(Syllabus)
            .where(Syllabus.subject_id == subject_id)
            .order_by(Syllabus.version.desc())
            .limit(1)
        )
        syllabus = syl_res.scalar_one_or_none()
        if not syllabus or not syllabus.structured_data:
            raise NotFoundError("Syllabus", f"for subject {subject.name}")

        units_data = syllabus.structured_data.get("units", [])
        expected_units = [u.get("unit_number", idx + 1) for idx, u in enumerate(units_data)]

        units_summary_lines = []
        for u in units_data:
            t_names = [t.get("name", "") for t in u.get("topics", [])]
            units_summary_lines.append(
                f"Unit {u.get('unit_number')}: {u.get('title')} ({u.get('hours', 0)} hrs)\n"
                f"  Topics: {', '.join(t_names)}"
            )
        units_summary = "\n\n".join(units_summary_lines)

        # 3. Fetch COs
        co_res = await self.db.execute(
            select(CourseOutcome)
            .where(
                CourseOutcome.subject_id == subject_id,
                CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
            )
            .order_by(CourseOutcome.co_code)
        )
        cos = co_res.scalars().all()
        cos_summary = "\n".join([f"- {co.co_code}: {co.statement}" for co in cos]) or "CO1 to CO5"
        valid_cos = [co.co_code for co in cos] or ["CO1", "CO2", "CO3", "CO4", "CO5"]

        # 4. Retrieve AAP Format from system RAG knowledge base
        aap_format_context = "No institutional AAP format document available in knowledge base."
        aap_chunks_retrieved = []
        try:
            query = f"AAP academic activity plan format template weekly schedule {subject.name}"
            aap_chunks = await self.retriever.retrieve_system(
                query=query,
                document_types=["AAP_FORMAT"],
                top_k=5,
                min_score=0.0,
            )
            if aap_chunks:
                aap_format_context = ContextAssembler.assemble_context(
                    aap_chunks, max_characters=4000
                )
                aap_chunks_retrieved = aap_chunks
                logger.info(
                    f"AAP generator: Retrieved {len(aap_chunks)} AAP format chunks "
                    f"(max score: {max(c.score for c in aap_chunks):.3f})"
                )
            else:
                logger.warning("AAP generator: No AAP format chunks found in system KB")
        except Exception as e:
            logger.warning(f"AAP generator: Could not retrieve AAP format: {e}")

        req = request or AAPGenerationRequest()
        total_weeks = req.total_weeks or 15
        total_hours = subject.teaching_hours or (total_weeks * (req.hours_per_week or 3))

        # Use augmented prompt with RAG context if available
        base_user_prompt = AAP_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            course_code=subject.course_code or "N/A",
            total_weeks=total_weeks,
            total_hours=total_hours,
            hours_per_week=req.hours_per_week or 3,
            syllabus_units_summary=units_summary,
            cos_summary=cos_summary,
        )

        if aap_chunks_retrieved:
            # Prepend AAP format context to user prompt
            prompt = f"=== INSTITUTIONAL AAP FORMAT REFERENCE ===\n{aap_format_context}\n=== END AAP FORMAT ===\n\n{base_user_prompt}"
            system_prompt = AAP_SYSTEM_PROMPT_WITH_RAG
        else:
            prompt = base_user_prompt
            system_prompt = AAP_GENERATION_SYSTEM_PROMPT

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="AAP_GENERATION",
            model_used="gemini-2.5-flash",
            input_params={
                "total_weeks": total_weeks,
                "total_hours": total_hours,
                "aap_format_chunks_retrieved": len(aap_chunks_retrieved),
            },
            retrieved_documents=[str(c.chunk_id) for c in aap_chunks_retrieved],
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            plan_data = await self.llm.generate_structured(
                prompt=prompt,
                schema=AAPPlanDataSchema,
                system_prompt=system_prompt,
            )

            # 5. Run Deterministic Validation (template enforces structure)
            val_report = AAPValidator.validate(
                plan=plan_data,
                expected_total_hours=total_hours,
                expected_units=expected_units,
                valid_cos=valid_cos,
            )

            # Archive previous DRAFT AAP plans
            existing = await self.db.execute(
                select(AAPPlan).where(
                    AAPPlan.subject_id == subject_id,
                    AAPPlan.status == "DRAFT",
                )
            )
            for old_p in existing.scalars().all():
                old_p.status = "ARCHIVED"

            aap_obj = AAPPlan(
                subject_id=subject_id,
                generation_run_id=gen_run.id,
                template_config=req.template_config or {"columns": ["Week", "Unit", "Topics", "Method", "CO", "Hours", "Activity"]},
                plan_data=plan_data.model_dump(),
                total_weeks=plan_data.total_weeks,
                total_hours=sum(w.planned_hours for w in plan_data.weeks),
                status="DRAFT",
                version=1,
                validation_report=val_report,
            )
            self.db.add(aap_obj)

            gen_run.status = "COMPLETED"
            gen_run.validation_result = val_report
            await self.db.commit()
            return aap_obj

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"AAP generation failed: {e}")
            raise LLMError(f"Failed to generate AAP: {str(e)}")
