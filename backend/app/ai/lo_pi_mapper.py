"""
ADAPT — LO-PI Mapping Engine

AI-suggested LO-PI mapping with automatic PO derivation.
Each PI belongs to a PO, so mapping LO→PI automatically establishes LO→PI→PO chain.

The institutional PO-PI Mapping Guidelines are retrieved from the system RAG
knowledge base and used as authoritative grounding for all mappings.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_llm_provider
from app.core.exceptions import LLMError, NotFoundError
from app.core.logging import get_logger
from app.models.learning_outcome import LearningOutcome
from app.models.lo_pi_mapping import LOPIMapping
from app.models.performance_indicator import PerformanceIndicator
from app.models.program_outcome import ProgramOutcome
from app.models.generation_run import GenerationRun
from app.models.subject import Subject
from app.rag.context_assembler import ContextAssembler
from app.rag.retriever import VectorRetriever
from app.schemas.lo_pi import LOPIMappingResponseSchema

logger = get_logger("ai.lo_pi_mapper")

LO_PI_MAPPING_SYSTEM_PROMPT = """You are an OBE curriculum mapping expert.
Map Learning Outcomes (LOs) to Performance Indicators (PIs).
Each PI belongs to a Program Outcome (PO).
For each LO, identify which PI(s) it helps students achieve.
Assign mapping_level: 0=No alignment, 1=Low, 2=Medium, 3=High.
Only include mappings with level >= 1.
Base mappings on:
- The institutional PO-PI Mapping Guidelines provided below (authoritative)
- Content alignment between LO and PI statements
- Bloom level coherence
- Domain relevance (e.g., LOs about design map to PO3 PIs)
For each mapping, include the po_code of the PI's parent PO.
Follow the institutional guidelines strictly — do not override them with generic assumptions.
"""

LO_PI_MAPPING_USER_PROMPT = """Map these Learning Outcomes to Performance Indicators:

Subject: {subject_name}

=== INSTITUTIONAL PO-PI MAPPING GUIDELINES (Authoritative) ===
{po_pi_guidelines}
=== END GUIDELINES ===

Learning Outcomes:
{los_text}

Performance Indicators (grouped by PO):
{pis_text}

Use the institutional guidelines above as primary authority for mapping decisions.
"""


class LOPIMapper:
    """Generates AI-suggested LO-PI mappings with PO derivation.
    
    Uses the institutional PO-PI Mapping Guidelines from the system RAG knowledge
    base as authoritative grounding. Faculty can still edit/approve the final mappings.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()
        self.retriever = VectorRetriever(db)

    async def generate_mappings(
        self,
        subject_id: UUID,
        user_id: UUID,
    ) -> List[LOPIMapping]:
        # 1. Fetch Subject
        s_res = await self.db.execute(select(Subject).where(Subject.id == subject_id))
        subject = s_res.scalar_one_or_none()
        if not subject:
            raise NotFoundError("Subject", str(subject_id))

        # 2. Fetch LOs
        lo_res = await self.db.execute(
            select(LearningOutcome)
            .where(LearningOutcome.subject_id == subject_id, LearningOutcome.status.in_(["DRAFT", "APPROVED"]))
            .order_by(LearningOutcome.lo_code)
        )
        los = lo_res.scalars().all()
        if not los:
            raise NotFoundError("Learning Outcomes", f"for subject {subject.name}")
        lo_dict = {lo.lo_code: lo for lo in los}

        # 3. Fetch all PIs grouped by PO
        po_res = await self.db.execute(
            select(ProgramOutcome).where(ProgramOutcome.is_active == True).order_by(ProgramOutcome.po_code)
        )
        pos = po_res.scalars().all()
        po_dict = {po.po_code: po for po in pos}

        pi_res = await self.db.execute(
            select(PerformanceIndicator).where(PerformanceIndicator.is_active == True).order_by(PerformanceIndicator.pi_code)
        )
        pis = pi_res.scalars().all()
        pi_dict = {pi.pi_code: pi for pi in pis}

        # 4. Retrieve PO-PI Mapping Guidelines from system RAG (institutional authority)
        po_pi_guideline_context = "No institutional PO-PI guidelines available in knowledge base."
        try:
            query = f"PO PI mapping guidelines performance indicators program outcomes {subject.name}"
            guideline_chunks = await self.retriever.retrieve_system(
                query=query,
                document_types=["PO_PI_GUIDELINE"],
                top_k=5,
                min_score=0.0,
            )
            if guideline_chunks:
                po_pi_guideline_context = ContextAssembler.assemble_context(
                    guideline_chunks, max_characters=4000
                )
                logger.info(
                    f"LO-PI mapper: Retrieved {len(guideline_chunks)} PO-PI guideline chunks "
                    f"(max score: {max(c.score for c in guideline_chunks):.3f})"
                )
            else:
                logger.warning("LO-PI mapper: No PO-PI guideline chunks found in system KB")
        except Exception as e:
            logger.warning(f"LO-PI mapper: Could not retrieve PO-PI guidelines: {e}")

        # Build text for prompt
        los_text = "\n".join([f"- {lo.lo_code}: {lo.statement} (Bloom: {lo.bloom_level})" for lo in los])
        pis_by_po = {}
        for pi in pis:
            po_code = pi.program_outcome.po_code if pi.program_outcome else "Unknown"
            pis_by_po.setdefault(po_code, []).append(pi)
        pis_text_lines = []
        for po_code in sorted(pis_by_po.keys()):
            po_pis = pis_by_po[po_code]
            pis_text_lines.append(f"\n{po_code}:")
            for pi in po_pis:
                pis_text_lines.append(f"  - {pi.pi_code}: {pi.statement}")
        pis_text = "\n".join(pis_text_lines)

        prompt = LO_PI_MAPPING_USER_PROMPT.format(
            subject_name=subject.name,
            po_pi_guidelines=po_pi_guideline_context,
            los_text=los_text,
            pis_text=pis_text,
        )

        gen_run = GenerationRun(
            subject_id=subject_id,
            triggered_by=user_id,
            operation="LO_PI_MAPPING",
            model_used="gemini-2.5-flash",
            input_params={
                "lo_count": len(los),
                "pi_count": len(pis),
                "guideline_chunks_retrieved": len(guideline_chunks) if isinstance(guideline_chunks, list) else 0,
            },
            status="RUNNING",
        )
        self.db.add(gen_run)
        await self.db.flush()

        try:
            structured_res = await self.llm.generate_structured(
                prompt=prompt,
                schema=LOPIMappingResponseSchema,
                system_prompt=LO_PI_MAPPING_SYSTEM_PROMPT,
            )

            # Clear existing draft mappings
            for lo in los:
                existing = await self.db.execute(
                    select(LOPIMapping).where(
                        LOPIMapping.lo_id == lo.id,
                        LOPIMapping.status == "DRAFT",
                    )
                )
                for old_m in existing.scalars().all():
                    await self.db.delete(old_m)
            await self.db.flush()

            created_mappings = []
            for cell in structured_res.mappings:
                lo_obj = lo_dict.get(cell.lo_code)
                pi_obj = pi_dict.get(cell.pi_code)
                po_obj = po_dict.get(cell.po_code)
                if lo_obj and pi_obj and po_obj and cell.mapping_level > 0:
                    mapping = LOPIMapping(
                        lo_id=lo_obj.id,
                        pi_id=pi_obj.id,
                        po_id=po_obj.id,
                        mapping_level=cell.mapping_level,
                        rationale=cell.rationale,
                        status="DRAFT",
                    )
                    self.db.add(mapping)
                    created_mappings.append(mapping)

            gen_run.status = "COMPLETED"
            gen_run.retrieved_documents = [str(c.chunk_id) for c in (guideline_chunks if isinstance(guideline_chunks, list) else [])]
            await self.db.commit()
            return created_mappings

        except Exception as e:
            gen_run.status = "FAILED"
            gen_run.error_message = str(e)
            await self.db.commit()
            logger.error(f"LO-PI mapping generation failed: {e}")
            raise LLMError(f"Failed to generate LO-PI mapping: {str(e)}")
