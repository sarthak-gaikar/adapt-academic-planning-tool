"""
ADAPT — Subject Model
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    course_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=True)
    teaching_hours: Mapped[int] = mapped_column(Integer, nullable=True)
    semester: Mapped[str] = mapped_column(String(50), nullable=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=True)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    prerequisites: Mapped[dict] = mapped_column(JSON, nullable=True, default=list)
    course_objectives: Mapped[dict] = mapped_column(JSON, nullable=True, default=list)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )  # ACTIVE | ARCHIVED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    creator = relationship("User", back_populates="subjects", lazy="selectin")
    documents = relationship("Document", back_populates="subject", lazy="selectin")
    syllabi = relationship("Syllabus", back_populates="subject", lazy="selectin")
    course_outcomes = relationship(
        "CourseOutcome", back_populates="subject", lazy="selectin"
    )
    learning_outcomes = relationship(
        "LearningOutcome", back_populates="subject", lazy="selectin"
    )
    co_po_mappings = relationship(
        "COPOMapping", back_populates="subject", lazy="selectin"
    )
    aap_plans = relationship("AAPPlan", back_populates="subject", lazy="selectin")
    questions = relationship("Question", back_populates="subject", lazy="selectin")
    assignments = relationship("Assignment", back_populates="subject", lazy="selectin")
    exam_blueprints = relationship(
        "ExamBlueprint", back_populates="subject", lazy="selectin"
    )
    exam_papers = relationship("ExamPaper", back_populates="subject", lazy="selectin")
    generation_runs = relationship(
        "GenerationRun", back_populates="subject", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Subject {self.course_code}: {self.name}>"
