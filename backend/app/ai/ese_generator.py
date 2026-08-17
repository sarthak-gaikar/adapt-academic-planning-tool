"""
ADAPT — ESE Generator Engine

Generates comprehensive End-Semester Examination papers across all syllabus units
with multi-section structure, internal choices, and validation.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.exam_generation import (
    ESE_GENERATION_SYSTEM_PROMPT,
    ESE_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.exam import ExamBlueprint, ExamPaper, ExamQuestion
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.models.subject import Subject
from app.models.syllabus import Syllabus
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.question import QuestionBatchGenerationSchema
from app.validators.blueprint_validator import MasterBlueprintValidator

logger = get_logger("ai.ese_generator")


class ESEGenerator:
    """Generates End-Semester Examination papers."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_ese(
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

        # Default units: all units in syllabus or 1..5
        units = blueprint.units_covered or [1, 2, 3, 4, 5]

        # 2. Retrieve Comprehensive RAG Context across all units
        chunks = await self.retriever.retrieve(
            query=f"{subject.name} complete syllabus final end semester exam key topics",
            subject_id=subject_id,
            top_k=10,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=8000)

        # 3. Prompt LLM
        prompt = ESE_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            course_code=subject.course_code or "N/A",
            total_marks=blueprint.total_marks,
            units_covered=units,
            sections_summary=str(blueprint.section_structure or "Section A: Short Answer (10m), Section B: Medium (20m), Section C: Comprehensive/Design (20m)"),
            choice_config="Provide internal choices (Question A OR Question B) for Section B/C questions." if blueprint.has_internal_choice else "All questions compulsory.",
            retrieved_context=context_str,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="ESE_GENERATION",
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
                system_prompt=ESE_GENERATION_SYSTEM_PROMPT,
            )

            # Create ExamPaper
            paper_title = custom_title or f"End-Semester Examination — {subject.name}"
            paper = ExamPaper(
                subject_id=subject_id,
                blueprint_id=blueprint.id,
                generation_run_id=gen_run.id,
                exam_type="ESE",
                title=paper_title,
                instructions=custom_instructions or "1. Answer all questions from Section A.\n2. In Section B and C, answer either (a) OR (b) where choice is given.\n3. Assume suitable data if necessary.",
                total_marks=blueprint.total_marks,
                status="DRAFT",
                version=1,
            )
            self.db.add(paper)
            await self.db.flush()
            await self.db.refresh(paper)

            # Store questions & link
            paper_questions_dict = []
            total_questions = len(batch_result.questions)

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
                    unit_number=item.unit_number or (units[idx % len(units)]),
                    topic=item.topic,
                    reference_answer=item.reference_answer,
                    marking_scheme=item.marking_scheme,
                    status="DRAFT",
                )
                self.db.add(q_obj)
                await self.db.flush()
                await self.db.refresh(q_obj)

                # Assign sections: 1/3 Section A, 1/3 Section B, 1/3 Section C
                if idx <= total_questions // 3:
                    section_name = "Section A"
                    is_comp = True
                    choice_grp = None
                elif idx <= (2 * total_questions) // 3:
                    section_name = "Section B"
                    is_comp = not blueprint.has_internal_choice
                    choice_grp = f"GRP_{(idx // 2)}" if blueprint.has_internal_choice else None
                else:
                    section_name = "Section C"
                    is_comp = not blueprint.has_internal_choice
                    choice_grp = f"GRP_{(idx // 2)}" if blueprint.has_internal_choice else None

                eq = ExamQuestion(
                    exam_paper_id=paper.id,
                    question_id=q_obj.id,
                    section=section_name,
                    sequence_order=idx,
                    marks=item.marks,
                    is_compulsory=is_comp,
                    choice_group=choice_grp,
                )
                self.db.add(eq)

                paper_questions_dict.append({
                    "question_text": item.question_text,
                    "marks": item.marks,
                    "bloom_level": bloom_res.level,
                    "unit_number": item.unit_number or (units[idx % len(units)]),
                    "co_code": item.co_code,
                    "is_compulsory": is_comp,
                })

            # Deterministic Blueprint Validation
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
            logger.error(f"ESE generation failed: {e}")
            raise LLMError(f"Failed to generate ESE paper: {str(e)}")
