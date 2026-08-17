"""
ADAPT — Syllabus, SyllabusUnit, and Topic Models

Structured syllabus representation extracted from uploaded documents.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Syllabus(Base):
    __tablename__ = "syllabi"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    structured_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT"
    )  # DRAFT | CONFIRMED | ARCHIVED
    confirmed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subject = relationship("Subject", back_populates="syllabi")
    document = relationship("Document", back_populates="syllabus")
    units = relationship(
        "SyllabusUnit",
        back_populates="syllabus",
        lazy="selectin",
        order_by="SyllabusUnit.unit_number",
    )

    def __repr__(self) -> str:
        return f"<Syllabus v{self.version} for subject={self.subject_id}>"


class SyllabusUnit(Base):
    __tablename__ = "syllabus_units"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    syllabus_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("syllabi.id"), nullable=False, index=True
    )
    unit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hours: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    syllabus = relationship("Syllabus", back_populates="units")
    topics = relationship(
        "Topic",
        back_populates="unit",
        lazy="selectin",
        order_by="Topic.sequence_order",
    )

    def __repr__(self) -> str:
        return f"<SyllabusUnit {self.unit_number}: {self.title}>"


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("syllabus_units.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subtopics: Mapped[dict] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    unit = relationship("SyllabusUnit", back_populates="topics")

    def __repr__(self) -> str:
        return f"<Topic {self.name}>"
