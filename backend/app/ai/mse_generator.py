"""
ADAPT — MSE Generator Engine

Generates Mid-Semester Examination papers adhering to blueprints and runs deterministic validation.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.exam_generation import (
    MSE_GENERATION_SYSTEM_PROMPT,
    MSE_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.exam import ExamBlueprint, ExamPaper, ExamQuestion
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.models.subject import Subject
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.question import QuestionBatchGenerationSchema
from app.validators.blueprint_validator import MasterBlueprintValidator

logger = get_logger("ai.mse_generator")


class MSEGenerator:
    """Generates Mid-Semester Examination papers."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_mse(
        self,
        subject_id: UUID,
        blueprint_id: UUID,
        user_id: UUID,
        custom_title: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> ExamPaper:
        # 1. Fetch Subject & Blueprint
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        bp_res = await self.db.execute(select(ExamBlueprint).where(ExamBlueprint.id == blueprint_id))
        blueprint = bp_res.scalar_one_or_none()
        if not blueprint:
            raise NotFoundError("ExamBlueprint", str(blueprint_id))

        units = blueprint.units_covered or [1, 2, 3]

        # 2. Retrieve Grounding Context for MSE units
        chunks = await self.retriever.retrieve(
            query=f"{subject.name} Units {' '.join(str(u) for u in units)} mid term exam concepts",
            subject_id=subject_id,
            top_k=8,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=7000)

        # 3. Prompt LLM
        prompt = MSE_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            course_code=subject.course_code or "N/A",
            total_marks=blueprint.total_marks,
            units_covered=units,
            difficulty_dist=blueprint.difficulty_distribution or {"EASY": 30, "MEDIUM": 50, "HARD": 20},
            bloom_dist=blueprint.bloom_distribution or {"Remember": 10, "Understand": 30, "Apply": 40, "Analyze": 20},
            sections_summary=str(blueprint.section_structure or "Section A (Short: 10m), Section B (Long: 20m)"),
            retrieved_context=context_str,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="MSE_GENERATION",
            model_used="gpt-4o",
            input_params={"blueprint_id": str(blueprint.id), "total_marks": blueprint.total_marks},
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            batch_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=QuestionBatchGenerationSchema,
                system_prompt=MSE_GENERATION_SYSTEM_PROMPT,
            )

            # Create ExamPaper record
            paper_title = custom_title or f"Mid-Semester Examination — {subject.name}"
            paper = ExamPaper(
                subject_id=subject_id,
                blueprint_id=blueprint.id,
                generation_run_id=gen_run.id,
                exam_type="MSE",
                title=paper_title,
                instructions=custom_instructions or "1. All questions in Section A are compulsory.\n2. Figures to the right indicate full marks.",
                total_marks=blueprint.total_marks,
                status="DRAFT",
                version=1,
            )
            self.db.add(paper)
            await self.db.flush()
            await self.db.refresh(paper)

            # Save questions & create ExamQuestion links
            paper_questions_dict = []
            for idx, item in enumerate(batch_result.questions, 1):
                bloom_res = await self.bloom_classifier.classify(item.question_text)

                q_obj = Question(
                    subject_id=subject_id,
                    generation_run_id=gen_run.id,
                    question_text=item.question_text,
                    question_type=item.question_type or "DESCRIPTIVE",
                    marks=item.marks,
                    difficulty=item.difficulty or "MEDIUM",
                    bloom_level=bloom_res.level,
                    bloom_confidence=bloom_res.confidence,
                    co_code=item.co_code,
                    unit_number=item.unit_number or units[0],
                    topic=item.topic,
                    reference_answer=item.reference_answer,
                    marking_scheme=item.marking_scheme,
                    status="DRAFT",
                )
                self.db.add(q_obj)
                await self.db.flush()
                await self.db.refresh(q_obj)

                section_name = "Section A" if idx <= len(batch_result.questions) // 2 else "Section B"
                eq = ExamQuestion(
                    exam_paper_id=paper.id,
                    question_id=q_obj.id,
                    section=section_name,
                    sequence_order=idx,
                    marks=item.marks,
                    is_compulsory=True,
                )
                self.db.add(eq)

                paper_questions_dict.append({
                    "question_text": item.question_text,
                    "marks": item.marks,
                    "bloom_level": bloom_res.level,
                    "unit_number": item.unit_number or units[0],
                    "co_code": item.co_code,
                    "is_compulsory": True,
                })

            # Run deterministic blueprint validation
            val_report = MasterBlueprintValidator.validate_exam_paper(
                questions=paper_questions_dict,
                total_marks=blueprint.total_marks,
                units_covered=units,
                target_bloom=blueprint.bloom_distribution,
            )
            paper.validation_report = val_report

            gen_run.status = "COMPLETED"
            gen_run.validation_result = val_report
            await self.db.commit()
            return paper

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"MSE generation failed: {e}")
            raise LLMError(f"Failed to generate MSE paper: {str(e)}")
