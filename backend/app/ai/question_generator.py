"""
ADAPT — Question Generator Engine

Generates grounded questions using RAG, classifies Bloom levels,
checks duplicates against the existing question bank, and stores metadata.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.question_generation import (
    QUESTION_GENERATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.models.subject import Subject
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.question import (
    QuestionBatchGenerationSchema,
    QuestionGenerateRequest,
)
from app.validators.duplicate_detector import DuplicateDetector

logger = get_logger("ai.question_generator")


class QuestionGenerator:
    """Generates syllabus-grounded questions with Bloom validation and duplicate detection."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_questions(
        self,
        subject_id: UUID,
        user_id: UUID,
        request: QuestionGenerateRequest,
    ) -> List[Question]:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Retrieve relevant context via RAG
        query_parts = [subject.name]
        if request.topic:
            query_parts.append(request.topic)
        if request.unit_number:
            query_parts.append(f"Unit {request.unit_number}")
        query_str = " ".join(query_parts)

        chunks = await self.retriever.retrieve(
            query=query_str,
            subject_id=subject_id,
            unit_number=request.unit_number,
            top_k=5,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=6000)

        # 3. Prompt LLM
        prompt = QUESTION_GENERATION_USER_PROMPT.format(
            count=request.count or 3,
            subject_name=subject.name,
            unit_spec=f"Unit {request.unit_number}" if request.unit_number else "Any Unit",
            topic_spec=request.topic or "Any core topic in unit",
            co_spec=request.co_code or "Applicable CO",
            bloom_spec=request.bloom_level or "Appropriate cognitive level",
            difficulty_spec=request.difficulty or "MEDIUM",
            marks_spec=request.marks or 5,
            type_spec=request.question_type or "DESCRIPTIVE",
            custom_guidelines=f"Additional Requirements: {request.custom_guidelines}" if request.custom_guidelines else "",
            retrieved_context=context_str,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="QUESTION_GENERATION",
            model_used="gpt-4o",
            input_params=request.model_dump(),
            retrieved_documents=[str(c.chunk_id) for c in chunks],
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            batch_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=QuestionBatchGenerationSchema,
                system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
            )

            # Fetch existing questions in bank for duplicate checking
            existing_q_res = await self.db.execute(
                select(Question.question_text).where(Question.subject_id == subject_id)
            )
            existing_texts = [row[0] for row in existing_q_res.all()]

            created_questions: List[Question] = []
            for item in batch_result.questions:
                # 4. Duplicate Detection Check
                dup_result = await DuplicateDetector.check_duplicates_against_bank(
                    item.question_text, existing_texts
                )
                if dup_result.is_duplicate:
                    logger.info(f"Skipping duplicate question (sim: {dup_result.similarity_score}): {item.question_text[:60]}")
                    continue

                # 5. Bloom cognitive classification
                bloom_res = await self.bloom_classifier.classify(item.question_text)

                q_obj = Question(
                    subject_id=subject_id,
                    generation_run_id=gen_run.id,
                    question_text=item.question_text,
                    question_type=item.question_type or request.question_type or "DESCRIPTIVE",
                    marks=item.marks or request.marks or 5,
                    difficulty=item.difficulty or request.difficulty or "MEDIUM",
                    bloom_level=bloom_res.level,
                    bloom_confidence=bloom_res.confidence,
                    co_code=item.co_code or request.co_code,
                    unit_number=item.unit_number or request.unit_number,
                    topic=item.topic or request.topic,
                    reference_answer=item.reference_answer,
                    marking_scheme=item.marking_scheme,
                    source_context={"retrieved_chunk_count": len(chunks), "similarity_score": dup_result.similarity_score},
                    status="DRAFT",
                    version=1,
                )
                self.db.add(q_obj)
                created_questions.append(q_obj)
                existing_texts.append(item.question_text)

            gen_run.status = "COMPLETED"
            await self.db.commit()
            return created_questions

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"Question generation failed: {e}")
            raise LLMError(f"Failed to generate questions: {str(e)}")
