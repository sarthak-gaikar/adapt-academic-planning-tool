"""
ADAPT — SQLAlchemy Models Package

All ORM models re-exported for convenient imports and Alembic discovery.
"""

from app.models.user import User
from app.models.subject import Subject
from app.models.document import Document
from app.models.syllabus import Syllabus, SyllabusUnit, Topic
from app.models.course_outcome import CourseOutcome
from app.models.program_outcome import ProgramOutcome
from app.models.co_po_mapping import COPOMapping
from app.models.learning_outcome import LearningOutcome
from app.models.performance_indicator import PerformanceIndicator
from app.models.lo_co_mapping import LOCOMapping
from app.models.lo_pi_mapping import LOPIMapping
from app.models.aap import AAPPlan
from app.models.question import Question
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.exam import ExamBlueprint, ExamPaper, ExamQuestion
from app.models.answer_key import AnswerKey
from app.models.generation_run import GenerationRun
from app.models.document_export import DocumentExport
from app.models.vector_chunk import VectorChunk
from app.models.institution_config import InstitutionConfig
from app.models.system_document import SystemDocument

__all__ = [
    "User",
    "Subject",
    "Document",
    "Syllabus",
    "SyllabusUnit",
    "Topic",
    "CourseOutcome",
    "ProgramOutcome",
    "COPOMapping",
    "LearningOutcome",
    "PerformanceIndicator",
    "LOCOMapping",
    "LOPIMapping",
    "AAPPlan",
    "Question",
    "Assignment",
    "AssignmentQuestion",
    "ExamBlueprint",
    "ExamPaper",
    "ExamQuestion",
    "AnswerKey",
    "GenerationRun",
    "DocumentExport",
    "VectorChunk",
    "InstitutionConfig",
    "SystemDocument",
]
