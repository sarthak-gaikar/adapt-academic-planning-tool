"""
ADAPT — Unified Exam Generator Engine

Single code path for both MSE and ESE paper generation.
Differences are handled through configurable blueprints and strategies:
  - ExamType determines default sections, choices, and RAG doc types
  - Blueprint validation runs BEFORE LLM call (marks arithmetic)
  - System RAG retrieval includes sample papers for style reference
  - Request-scoped files are optionally retrieved
  - Duplicate detection runs against existing approved question bank
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.unified_exam_prompts import (
    UNIFIED_EXAM_SYSTEM_PROMPT,
    UNIFIED_EXAM_USER_PROMPT,
    MSE_DEFAULT_SECTIONS,
    ESE_DEFAULT_SECTIONS,
)
from app.core.exceptions import LLMError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.course_outcome import CourseOutcome
from app.models.exam import ExamBlueprint, ExamPaper, ExamQuestion
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.models.subject import Subject
from app.rag.context_assembler import ContextAssembler
from app.rag.request_documents import RequestDocumentManager
from app.rag.retriever import VectorRetriever
from app.schemas.question import QuestionBatchGenerationSchema
from app.validators.blueprint_validator import MasterBlueprintValidator
from app.validators.duplicate_detector import DuplicateDetector

logger = get_logger("ai.exam_generator")


class ExamType(str, Enum):
    MSE = "MSE"
    ESE = "ESE"


# Exam-type-specific configuration
EXAM_CONFIGS = {
    ExamType.MSE: {
        "full_name": "Mid-Semester Examination (MSE)",
        "default_total_marks": 30,
        "default_units": [1, 2, 3],
        "default_sections": MSE_DEFAULT_SECTIONS,
        "has_internal_choice": False,
        "system_doc_types": ["MSE_SAMPLE"],
        "default_instructions": (
            "1. All questions are compulsory.\n"
            "2. Figures to the right indicate full marks.\n"
            "3. Assume suitable data if necessary."
        ),
    },
    ExamType.ESE: {
        "full_name": "End-Semester Examination (ESE)",
        "default_total_marks": 50,
        "default_units": [1, 2, 3, 4, 5],
        "default_sections": ESE_DEFAULT_SECTIONS,
        "has_internal_choice": True,
        "system_doc_types": ["ESE_SAMPLE"],
        "default_instructions": (
            "1. Answer all questions from Section A.\n"
            "2. In Section B and C, answer either (a) OR (b) where choice is given.\n"
            "3. Figures to the right indicate full marks.\n"
            "4. Assume suitable data if necessary."
        ),
    },
}


class UnifiedExamGenerator:
    """Generates MSE and ESE papers through a single configurable pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_paper(
        self,
        subject_id: UUID,
        user_id: UUID,
        exam_type: str,
        unit_ids: List[int],
        total_marks: int,
        question_counts: Dict[int, int],
        additional_file_paths: Optional[List[str]] = None,
        custom_title: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> ExamPaper:
        """
        Unified paper generation for both MSE and ESE.
        
        Args:
            subject_id: Target subject UUID
            user_id: Faculty user UUID
            exam_type: "MSE" or "ESE"
            unit_ids: List of unit numbers to include
            total_marks: Requested total marks
            question_counts: Dict of {marks: count}, e.g. {2: 5, 5: 2, 10: 1}
            additional_file_paths: Optional paths to request-scoped reference files
            custom_title: Optional paper title override
            custom_instructions: Optional instructions override
        """
        etype = ExamType(exam_type)
        config = EXAM_CONFIGS[etype]

        # 1. Pre-validate blueprint arithmetic
        is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
            total_marks=total_marks,
            question_counts=question_counts,
        )
        if not is_valid:
            raise ValidationError(
                message=msg,
                details={"requested_total": total_marks, "calculated_total": calc_total},
            )

        # 2. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 3. Create or find blueprint
        blueprint = ExamBlueprint(
            subject_id=subject_id,
            created_by=user_id,
            exam_type=exam_type,
            total_marks=total_marks,
            units_covered=unit_ids,
            difficulty_distribution={"EASY": 20, "MEDIUM": 60, "HARD": 20},
            bloom_distribution={"Remember": 10, "Understand": 25, "Apply": 35, "Analyze": 20, "Evaluate": 10},
            has_internal_choice=config["has_internal_choice"],
            status="APPROVED",
        )
        self.db.add(blueprint)
        await self.db.flush()
        await self.db.refresh(blueprint)

        # 4. Create GenerationRun
        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation=f"{exam_type}_GENERATION",
            model_used="gemini-2.5-flash",
            input_params={
                "exam_type": exam_type,
                "total_marks": total_marks,
                "unit_ids": unit_ids,
                "question_counts": question_counts,
                "has_additional_files": bool(additional_file_paths),
            },
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()
        await self.db.refresh(gen_run)

        try:
            # 5. Ingest request-scoped files if provided
            if additional_file_paths:
                req_doc_mgr = RequestDocumentManager(self.db)
                await req_doc_mgr.ingest_request_files(
                    file_paths=additional_file_paths,
                    generation_run_id=str(gen_run.id),
                    subject_id=subject_id,
                )

            # 6. Retrieve grounding context with hierarchy
            chunks = await self.retriever.retrieve_for_operation(
                operation=f"{exam_type}_GENERATION",
                subject_id=subject_id,
                subject_name=subject.name,
                unit_numbers=unit_ids,
                generation_run_id=str(gen_run.id) if additional_file_paths else None,
                top_k=10,
            )

            # Separate system vs subject context for the prompt
            system_chunks = [c for c in chunks if c.source_scope == "SYSTEM"]
            subject_chunks = [c for c in chunks if c.source_scope != "SYSTEM"]
            request_chunks = [c for c in chunks if c.source_scope == "REQUEST"]

            syllabus_context = ContextAssembler.assemble_context(subject_chunks, max_characters=6000)
            sample_context = ContextAssembler.assemble_context(system_chunks, max_characters=3000) if system_chunks else "No institutional sample papers available."
            additional_context = ContextAssembler.assemble_context(request_chunks, max_characters=2000) if request_chunks else "No additional reference material provided."

            # Record retrieved documents
            gen_run.retrieved_documents = [str(c.chunk_id) for c in chunks]

            # 7. Fetch COs for context
            co_res = await self.db.execute(
                select(CourseOutcome).where(
                    CourseOutcome.subject_id == subject_id,
                    CourseOutcome.status.in_(["DRAFT", "APPROVED"]),
                ).order_by(CourseOutcome.co_code)
            )
            cos = co_res.scalars().all()
            co_context = "\n".join([f"- {co.co_code}: {co.statement}" for co in cos]) or "CO1 to CO5"

            # 8. Build mark config summary
            mark_config_summary = "\n".join([
                f"  - {count} question(s) × {marks} marks = {marks * count} marks"
                for marks, count in sorted(question_counts.items())
            ])
            mark_config_detail = mark_config_summary + f"\n  Total: {calc_total} marks"

            # 9. Build prompt
            system_prompt = UNIFIED_EXAM_SYSTEM_PROMPT.format(
                exam_type_full=config["full_name"],
                total_marks=total_marks,
                mark_config_summary=mark_config_summary,
                units_covered=unit_ids,
            )
            user_prompt = UNIFIED_EXAM_USER_PROMPT.format(
                exam_type_full=config["full_name"],
                exam_type=exam_type,
                subject_name=subject.name,
                course_code=subject.course_code or "N/A",
                total_marks=total_marks,
                units_covered=unit_ids,
                mark_config_detail=mark_config_detail,
                section_structure=custom_instructions or config["default_sections"],
                syllabus_context=syllabus_context,
                sample_context=sample_context,
                co_context=co_context,
                additional_context=additional_context,
            )

            # 10. Generate via LLM
            batch_result = await self.llm.generate_structured(
                prompt=user_prompt,
                schema=QuestionBatchGenerationSchema,
                system_prompt=system_prompt,
            )

            # 11. Create ExamPaper record
            paper_title = custom_title or f"{config['full_name']} — {subject.name}"
            paper = ExamPaper(
                subject_id=subject_id,
                blueprint_id=blueprint.id,
                generation_run_id=gen_run.id,
                exam_type=exam_type,
                title=paper_title,
                instructions=custom_instructions or config["default_instructions"],
                total_marks=total_marks,
                status="DRAFT",
                version=1,
            )
            self.db.add(paper)
            await self.db.flush()
            await self.db.refresh(paper)

            # 12. Duplicate detection setup
            existing_q_res = await self.db.execute(
                select(Question.question_text).where(
                    Question.subject_id == subject_id,
                    Question.status.in_(["DRAFT", "APPROVED"]),
                )
            )
            existing_texts = [row[0] for row in existing_q_res.all()]

            # 13. Save questions & create ExamQuestion links
            paper_questions_dict = []
            total_questions = len(batch_result.questions)

            for idx, item in enumerate(batch_result.questions, 1):
                # Duplicate check
                dup_result = await DuplicateDetector.check_duplicates_against_bank(
                    item.question_text, existing_texts
                )
                if dup_result.is_duplicate:
                    logger.info(f"Skipping duplicate exam question (sim: {dup_result.similarity_score})")
                    continue

                # Bloom classification
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
                    unit_number=item.unit_number or unit_ids[0],
                    topic=item.topic,
                    reference_answer=item.reference_answer,
                    marking_scheme=item.marking_scheme,
                    status="DRAFT",
                )
                self.db.add(q_obj)
                await self.db.flush()
                await self.db.refresh(q_obj)

                # Assign section based on marks level and exam type
                section_name, is_comp, choice_grp = self._assign_section(
                    idx, total_questions, item.marks, etype, config
                )

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
                existing_texts.append(item.question_text)

                paper_questions_dict.append({
                    "question_text": item.question_text,
                    "marks": item.marks,
                    "bloom_level": bloom_res.level,
                    "unit_number": item.unit_number or unit_ids[0],
                    "co_code": item.co_code,
                    "is_compulsory": is_comp,
                })

            # 14. Deterministic validation
            mark_configs_list = [
                {"marks": m, "count": c} for m, c in question_counts.items()
            ]
            val_report = MasterBlueprintValidator.validate_exam_paper(
                questions=paper_questions_dict,
                total_marks=total_marks,
                units_covered=unit_ids,
                target_bloom=blueprint.bloom_distribution,
                mark_configs=mark_configs_list,
            )
            paper.validation_report = val_report

            gen_run.status = "COMPLETED"
            gen_run.validation_result = val_report
            await self.db.commit()

            logger.info(
                f"Unified {exam_type} generation complete: "
                f"{len(paper_questions_dict)} questions, {total_marks}m, "
                f"validation score: {val_report.get('score', 'N/A')}%"
            )
            return paper

        except ValidationError:
            raise  # Re-raise validation errors as-is
        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"{exam_type} generation failed: {e}")
            raise LLMError(f"Failed to generate {exam_type} paper: {str(e)}")

    @staticmethod
    def _assign_section(
        idx: int,
        total: int,
        marks: int,
        exam_type: ExamType,
        config: dict,
    ) -> tuple:
        """Assign section, compulsory flag, and choice group based on question properties."""
        if exam_type == ExamType.MSE:
            # MSE: Section A (short ≤2m), Section B (long ≥5m)
            if marks <= 2:
                return "Section A", True, None
            else:
                return "Section B", True, None
        else:
            # ESE: Section A (2m), Section B (5m), Section C (10m+)
            if marks <= 2:
                return "Section A", True, None
            elif marks <= 5:
                has_choice = config.get("has_internal_choice", False)
                choice_grp = f"GRP_{(idx // 2)}" if has_choice else None
                return "Section B", not has_choice, choice_grp
            else:
                has_choice = config.get("has_internal_choice", False)
                choice_grp = f"GRP_{(idx // 2)}" if has_choice else None
                return "Section C", not has_choice, choice_grp
