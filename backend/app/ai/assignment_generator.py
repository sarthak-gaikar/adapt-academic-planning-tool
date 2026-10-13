"""
ADAPT — Assignment Generator Engine

Generates structured assignments, assembles questions, and links AssignmentQuestion records.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.bloom_classifier import LLMBloomClassifier
from app.ai.factory import get_llm_provider
from app.ai.prompts.assignment_generation import (
    ASSIGNMENT_GENERATION_SYSTEM_PROMPT,
    ASSIGNMENT_GENERATION_USER_PROMPT,
)
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.generation_run import GenerationRun
from app.models.question import Question
from app.models.subject import Subject
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.assignment import AssignmentGenerateRequest, AssignmentGenerationSchema

logger = get_logger("ai.assignment_generator")


class AssignmentGenerator:
    """Generates structured assignments with balanced question marks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)
        self.bloom_classifier = LLMBloomClassifier()

    async def generate_assignment(
        self,
        subject_id: UUID,
        user_id: UUID,
        request: AssignmentGenerateRequest,
    ) -> Assignment:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Derive Marks & Question Counts
        total_marks = request.calculated_total_marks
        num_questions = request.calculated_total_questions
        counts_dict = request.question_counts_int

        if counts_dict:
            breakdown_lines = [
                f"- {count} question(s) of {marks} marks each ({count * marks} marks)"
                for marks, count in sorted(counts_dict.items())
            ]
            breakdown_spec = "\n".join(breakdown_lines)
        else:
            breakdown_spec = f"- {num_questions} questions totaling {total_marks} marks"

        if request.title and request.title.strip():
            title_instruction = f"- Preferred Title (you may refine): {request.title.strip()}"
        else:
            title_instruction = "- Assignment Title: Choose an engaging, descriptive, academic title summarizing the questions and topics generated (e.g. 'Assignment: Text Classification and Language Models')."

        # 3. Retrieve Grounding Context
        query_terms = [subject.name]
        if request.title:
            query_terms.append(request.title)
        if request.units:
            query_terms.append(f"Units {' '.join(str(u) for u in request.units)}")
        chunks = await self.retriever.retrieve(
            query=" ".join(query_terms),
            subject_id=subject_id,
            top_k=6,
        )
        context_str = ContextAssembler.assemble_context(chunks, max_characters=6000)

        # 4. Prompt LLM
        prompt = ASSIGNMENT_GENERATION_USER_PROMPT.format(
            subject_name=subject.name,
            total_marks=total_marks,
            num_questions=num_questions,
            breakdown_spec=breakdown_spec,
            title_instruction=title_instruction,
            units_spec=f"Units {request.units}" if request.units else "All Units",
            cos_spec=f"{request.cos}" if request.cos else "Target COs",
            bloom_spec=f"{request.bloom_levels}" if request.bloom_levels else "Progressive (Understand to Apply/Analyze)",
            difficulty=request.difficulty,
            retrieved_context=context_str,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="ASSIGNMENT_GENERATION",
            model_used="gemini-2.5-flash",
            input_params=request.model_dump(),
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            batch_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=AssignmentGenerationSchema,
                system_prompt=ASSIGNMENT_GENERATION_SYSTEM_PROMPT,
            )

            # Determine title chosen by LLM or fallback
            generated_title = (batch_result.title or "").strip()
            if not generated_title or generated_title.lower() in ["assignment", "untitled", "assignment 1"]:
                if request.title and request.title.strip():
                    final_title = request.title.strip()
                else:
                    unit_str = f" (Units {', '.join(str(u) for u in request.units)})" if request.units else ""
                    final_title = f"{subject.name} Assignment{unit_str}"
            else:
                final_title = generated_title

            final_desc = batch_result.description or request.description or (
                f"Assignment for {subject.name} covering Units {request.units} ({total_marks} Marks)"
                if request.units else f"Assignment for {subject.name} ({total_marks} Marks)"
            )

            # Create Assignment record
            assignment = Assignment(
                subject_id=subject_id,
                generation_run_id=gen_run.id,
                title=final_title,
                description=final_desc,
                total_marks=total_marks,
                config=request.model_dump(),
                status="DRAFT",
                version=1,
            )
            self.db.add(assignment)
            await self.db.flush()
            await self.db.refresh(assignment)

            # Store questions & link to assignment
            total_actual_marks = 0
            for idx, item in enumerate(batch_result.questions, 1):
                bloom_res = await self.bloom_classifier.classify(item.question_text)
                q_marks = item.marks or (total_marks // max(1, num_questions))
                total_actual_marks += q_marks

                q_obj = Question(
                    subject_id=subject_id,
                    generation_run_id=gen_run.id,
                    question_text=item.question_text,
                    question_type=item.question_type or "DESCRIPTIVE",
                    marks=q_marks,
                    difficulty=item.difficulty or request.difficulty,
                    bloom_level=bloom_res.level,
                    bloom_confidence=bloom_res.confidence,
                    co_code=item.co_code,
                    unit_number=item.unit_number or (request.units[0] if request.units else 1),
                    topic=item.topic,
                    reference_answer=item.reference_answer,
                    marking_scheme=item.marking_scheme,
                    status="DRAFT",
                )
                self.db.add(q_obj)
                await self.db.flush()
                await self.db.refresh(q_obj)

                # Link
                aq = AssignmentQuestion(
                    assignment_id=assignment.id,
                    question_id=q_obj.id,
                    sequence_order=idx,
                    marks=q_marks,
                )
                self.db.add(aq)

            # Check mark validation
            val_report = {
                "total_marks_expected": total_marks,
                "total_marks_actual": total_actual_marks,
                "marks_balanced": total_actual_marks == total_marks,
                "question_count": len(batch_result.questions),
                "title_generated_by_llm": bool(generated_title),
            }
            assignment.validation_report = val_report

            gen_run.status = "COMPLETED"
            gen_run.validation_result = val_report
            await self.db.commit()
            return assignment

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"Assignment generation failed: {e}")
            raise LLMError(f"Failed to generate assignment: {str(e)}")
