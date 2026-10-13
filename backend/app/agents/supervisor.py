"""
ADAPT — Supervisor Agent

Receives natural language faculty commands, reasons on required toolchain,
executes the specialized academic tools, and coordinates state.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.aap_generator import AAPGenerator
from app.ai.assignment_generator import AssignmentGenerator
from app.ai.co_generator import COGenerator
from app.ai.co_lo_mapper import COLOMapper
from app.ai.co_po_mapper import COPOMapper
from app.ai.factory import get_llm_provider
from app.ai.lo_generator import LOGenerator
from app.ai.lo_pi_mapper import LOPIMapper
from app.ai.mse_generator import MSEGenerator
from app.ai.question_generator import QuestionGenerator
from app.core.exceptions import ADAPTError, LLMError
from app.core.logging import get_logger
from app.schemas.aap import AAPGenerationRequest
from app.schemas.assignment import AssignmentGenerateRequest
from app.schemas.course_outcome import COGenerationRequest
from app.schemas.learning_outcome import LOGenerationRequest
from app.schemas.question import QuestionGenerateRequest

logger = get_logger("agents.supervisor")


class AgentPlanStep(BaseModel):
    tool_name: str = Field(..., description="generate_cos | generate_los | generate_co_lo | generate_lo_pi | generate_co_po | generate_aap | generate_questions | generate_assignment | generate_mse | get_obe_matrix")
    params: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class AgentExecutionPlan(BaseModel):
    intent_summary: str
    steps: List[AgentPlanStep] = Field(default_factory=list)


SUPERVISOR_PLANNING_PROMPT = """You are the ADAPT Supervisor Agent managing an academic planning platform for a university subject.
The faculty user has submitted a natural language request: "{user_request}"

Analyze the request and determine the exact tool sequence and parameters required:
Available tools:
1. 'generate_cos': Generate Course Outcomes. Parameters: num_cos (int), guidelines (str)
2. 'generate_los': Generate Learning Outcomes. Parameters: unit_numbers (list of int, optional), num_los_per_unit (int)
3. 'generate_co_lo': Generate CO-LO mapping. Parameters: none
4. 'generate_lo_pi': Generate LO-PI mapping. Parameters: none
5. 'generate_co_po': Generate CO-PO mapping. Parameters: none
6. 'generate_aap': Generate Academic Activity Plan. Parameters: total_weeks (int), hours_per_week (int)
7. 'generate_questions': Generate questions. Parameters: unit_number (int), topic (str), difficulty (str: EASY|MEDIUM|HARD), count (int), marks (int), bloom_level (str)
8. 'generate_assignment': Generate assignment. Parameters: title (str), total_marks (int), num_questions (int), units (list of int), difficulty (str)
9. 'generate_mse': Generate MSE paper. Parameters: custom_title (str)
10. 'get_obe_matrix': View the full CO→LO→PI→PO traceability matrix. Parameters: none

Produce a valid execution plan matching the schema.
"""


class SupervisorAgent:
    """Orchestrates natural language faculty requests across specialized tools."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_provider()

    async def execute_faculty_request(
        self,
        subject_id: UUID,
        user_id: UUID,
        user_request: str,
    ) -> Dict[str, Any]:
        logger.info(f"Supervisor received request: '{user_request}' for subject {subject_id}")

        # 1. Plan execution steps
        prompt = SUPERVISOR_PLANNING_PROMPT.format(user_request=user_request)
        try:
            plan = await self.llm.generate_structured(
                prompt=prompt,
                schema=AgentExecutionPlan,
                system_prompt="You are an autonomous orchestrator for academic course planning.",
            )
        except Exception as e:
            logger.error(f"Supervisor planning failed: {e}")
            raise LLMError(f"Supervisor could not parse intent: {str(e)}")

        results: List[Dict[str, Any]] = []

        # 2. Execute toolchain
        for step in plan.steps:
            tool = step.tool_name
            params = step.params or {}

            if tool == "generate_cos":
                gen = COGenerator(self.db)
                cos = await gen.generate_cos(
                    subject_id, user_id, COGenerationRequest(**params)
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(cos)} Course Outcomes."})

            elif tool == "generate_los":
                gen = LOGenerator(self.db)
                los = await gen.generate_los(
                    subject_id, user_id, LOGenerationRequest(**params)
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(los)} Learning Outcomes."})

            elif tool == "generate_co_lo":
                mapper = COLOMapper(self.db)
                mappings = await mapper.generate_mappings(subject_id, user_id)
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(mappings)} CO-LO mappings."})

            elif tool == "generate_lo_pi":
                mapper = LOPIMapper(self.db)
                mappings = await mapper.generate_mappings(subject_id, user_id)
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(mappings)} LO-PI mappings."})

            elif tool == "generate_co_po":
                mapper = COPOMapper(self.db)
                mappings = await mapper.generate_mappings(subject_id, user_id)
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(mappings)} CO-PO correlations."})

            elif tool == "generate_aap":
                aap_gen = AAPGenerator(self.db)
                plan_obj = await aap_gen.generate_aap(
                    subject_id, user_id, AAPGenerationRequest(**params)
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated AAP for {plan_obj.total_weeks} weeks ({plan_obj.total_hours} hours)."})

            elif tool == "generate_questions":
                q_gen = QuestionGenerator(self.db)
                questions = await q_gen.generate_questions(
                    subject_id, user_id, QuestionGenerateRequest(**params)
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated {len(questions)} questions in question bank."})

            elif tool == "generate_assignment":
                asg_gen = AssignmentGenerator(self.db)
                assignment = await asg_gen.generate_assignment(
                    subject_id, user_id, AssignmentGenerateRequest(**params)
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated assignment '{assignment.title}' ({assignment.total_marks} marks)."})

            elif tool == "generate_mse":
                # Find blueprint
                from app.models.exam import ExamBlueprint
                from sqlalchemy import select
                bp_res = await self.db.execute(
                    select(ExamBlueprint).where(ExamBlueprint.subject_id == subject_id, ExamBlueprint.exam_type == "MSE").limit(1)
                )
                bp = bp_res.scalar_one_or_none()
                if not bp:
                    bp = ExamBlueprint(
                        subject_id=subject_id,
                        created_by=user_id,
                        exam_type="MSE",
                        total_marks=30,
                        units_covered=[1, 2, 3],
                        status="APPROVED",
                    )
                    self.db.add(bp)
                    await self.db.flush()

                mse_gen = MSEGenerator(self.db)
                paper = await mse_gen.generate_mse(
                    subject_id, bp.id, user_id, custom_title=params.get("custom_title")
                )
                results.append({"tool": tool, "status": "SUCCESS", "message": f"Generated MSE paper '{paper.title}' ({paper.total_marks} marks)."})

            elif tool == "get_obe_matrix":
                results.append({"tool": tool, "status": "SUCCESS", "message": "OBE Matrix retrieved. View it in the CO-LO-PI-PO Matrix tab."})

        return {
            "intent": plan.intent_summary,
            "steps_executed": len(results),
            "results": results,
        }
