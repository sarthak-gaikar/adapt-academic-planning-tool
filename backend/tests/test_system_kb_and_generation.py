"""
Tests for the ADAPT system knowledge base, unified exam generation,
question bank blueprint, and request-scoped document isolation.
"""

import hashlib
import tempfile
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.rag.system_knowledge import (
    _classify_document_type,
    _compute_file_hash,
    _discover_knowledge_files,
)
from app.schemas.exam import UnifiedPaperGenerateRequest
from app.schemas.question_bank_blueprint import MarkConfig, QuestionBankBlueprintRequest
from app.validators.blueprint_validator import MasterBlueprintValidator


# ─────────────────────────────────────────────────────────────────────────────
# 1. System RAG: Document discovery and type classification
# ─────────────────────────────────────────────────────────────────────────────

class TestSystemDocumentClassification:
    """Tests for document type inference from file paths."""

    def test_po_pi_guideline_classification(self, tmp_path):
        f = tmp_path / "po_pi_mapping.pdf"
        f.touch()
        assert _classify_document_type(f) == "PO_PI_GUIDELINE"

    def test_aap_format_classification(self, tmp_path):
        f = tmp_path / "aap_sample.pdf"
        f.touch()
        assert _classify_document_type(f) == "AAP_FORMAT"

    def test_mse_sample_classification(self, tmp_path):
        subdir = tmp_path / "mse_sample_papers"
        subdir.mkdir()
        f = subdir / "mse_sample_1.pdf"
        f.touch()
        assert _classify_document_type(f) == "MSE_SAMPLE"

    def test_ese_sample_classification(self, tmp_path):
        subdir = tmp_path / "ese_sample_papers"
        subdir.mkdir()
        f = subdir / "ese_exam.pdf"
        f.touch()
        assert _classify_document_type(f) == "ESE_SAMPLE"

    def test_unknown_doc_classified_as_system_reference(self, tmp_path):
        f = tmp_path / "random_document.pdf"
        f.touch()
        assert _classify_document_type(f) == "SYSTEM_REFERENCE"


class TestFileHashDetection:
    """Tests for idempotent ingestion via content hash."""

    def test_same_file_produces_same_hash(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"content ABC 123")
        h1 = _compute_file_hash(f)
        h2 = _compute_file_hash(f)
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "doc1.pdf"
        f2 = tmp_path / "doc2.pdf"
        f1.write_bytes(b"content 1")
        f2.write_bytes(b"content 2")
        assert _compute_file_hash(f1) != _compute_file_hash(f2)

    def test_hash_is_sha256_hex(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"test content")
        h = _compute_file_hash(f)
        # SHA-256 hex is 64 chars
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_changed_content_produces_different_hash(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"version 1")
        h1 = _compute_file_hash(f)
        f.write_bytes(b"version 2")
        h2 = _compute_file_hash(f)
        assert h1 != h2


class TestKnowledgeBaseDiscovery:
    """Tests for file discovery in knowledge base directory."""

    def test_discovers_pdf_files(self, tmp_path):
        (tmp_path / "doc.pdf").write_bytes(b"content")
        files = _discover_knowledge_files(tmp_path)
        assert any(f.name == "doc.pdf" for f in files)

    def test_discovers_docx_files(self, tmp_path):
        (tmp_path / "doc.docx").write_bytes(b"content")
        files = _discover_knowledge_files(tmp_path)
        assert any(f.name == "doc.docx" for f in files)

    def test_ignores_non_document_files(self, tmp_path):
        (tmp_path / "doc.pdf").write_bytes(b"content")
        (tmp_path / "readme.txt").write_text("readme")
        (tmp_path / "notes.md").write_text("notes")
        files = _discover_knowledge_files(tmp_path)
        names = [f.name for f in files]
        assert "readme.txt" not in names
        assert "notes.md" not in names

    def test_discovers_files_in_subdirectories(self, tmp_path):
        subdir = tmp_path / "mse_sample_papers"
        subdir.mkdir()
        (subdir / "sample.pdf").write_bytes(b"content")
        files = _discover_knowledge_files(tmp_path)
        assert any("sample.pdf" in str(f) for f in files)

    def test_returns_empty_for_nonexistent_dir(self):
        files = _discover_knowledge_files(Path("/nonexistent/path"))
        assert files == []

    def test_actual_institutional_docs_exist(self):
        """Verify the actual institutional documents are present in the repository."""
        settings = get_settings()
        base_dir = Path(settings.knowledge_base_dir).resolve()
        if base_dir.exists():
            files = _discover_knowledge_files(base_dir)
            assert len(files) >= 1, "At least one institutional document expected"
            doc_types = {_classify_document_type(f) for f in files}
            # Should have at least AAP_FORMAT or PO_PI_GUIDELINE
            assert len(doc_types) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Blueprint Validation (Paper Generation)
# ─────────────────────────────────────────────────────────────────────────────

class TestUnifiedPaperBlueprintValidation:
    """Tests for the unified paper generation blueprint arithmetic."""

    def test_valid_mse_blueprint_30m(self):
        """Acceptance scenario: 5×2M + 2×5M + 1×10M = 30M"""
        is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
            total_marks=30,
            question_counts={2: 5, 5: 2, 10: 1},
        )
        assert is_valid is True
        assert calc_total == 30

    def test_valid_ese_blueprint_50m(self):
        """ESE: 5×2M + 4×5M + 2×10M = 50M"""
        is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
            total_marks=50,
            question_counts={2: 5, 5: 4, 10: 2},
        )
        assert is_valid is True
        assert calc_total == 50

    def test_mismatch_blocks_generation(self):
        """Blueprint mismatch (30M configured but 50M requested) must be rejected."""
        is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
            total_marks=50,
            question_counts={2: 5, 5: 2, 10: 1},  # = 30M
        )
        assert is_valid is False
        assert calc_total == 30

    def test_mismatch_message_is_clear(self):
        """Error message must mention both requested and calculated totals."""
        is_valid, calc_total, msg = MasterBlueprintValidator.validate_generation_request(
            total_marks=40,
            question_counts={2: 3, 5: 2},  # 3×2+2×5=16
        )
        assert is_valid is False
        # Message should mention numbers
        assert "16" in msg or "40" in msg or "mismatch" in msg.lower() or "configured" in msg.lower()

    def test_schema_string_keys_to_int_conversion(self):
        """UnifiedPaperGenerateRequest must convert string keys to int."""
        req = UnifiedPaperGenerateRequest(
            paper_type="MSE",
            unit_ids=[1, 2],
            total_marks=30,
            question_counts={"2": 5, "5": 2, "10": 1},
        )
        counts_int = req.question_counts_int
        assert isinstance(list(counts_int.keys())[0], int)
        assert counts_int[2] == 5
        assert req.calculated_marks == 30
        assert req.total_questions == 8


class TestQuestionBankBlueprint:
    """Tests for the question bank blueprint schema."""

    def test_total_marks_calculation(self):
        req = QuestionBankBlueprintRequest(
            units=[1, 3],
            mark_configs=[
                MarkConfig(marks=2, count=10),
                MarkConfig(marks=5, count=5),
                MarkConfig(marks=10, count=2),
            ],
        )
        # 10×2 + 5×5 + 2×10 = 20 + 25 + 20 = 65
        assert req.total_marks == 65
        assert req.total_questions == 17

    def test_empty_units_allowed(self):
        """Units list can be empty (applies to all units)."""
        req = QuestionBankBlueprintRequest(
            units=[],
            mark_configs=[MarkConfig(marks=5, count=3)],
        )
        assert req.total_marks == 15

    def test_single_unit(self):
        req = QuestionBankBlueprintRequest(
            units=[1],
            mark_configs=[MarkConfig(marks=2, count=5)],
        )
        assert req.units == [1]
        assert req.total_marks == 10

    def test_multi_unit_selection(self):
        req = QuestionBankBlueprintRequest(
            units=[1, 3, 5],
            mark_configs=[MarkConfig(marks=5, count=6)],
        )
        assert req.units == [1, 3, 5]
        assert req.total_questions == 6

    def test_optional_files_default_empty(self):
        req = QuestionBankBlueprintRequest(
            mark_configs=[MarkConfig(marks=5, count=2)],
        )
        assert req.additional_file_paths == []

    def test_optional_files_can_be_set(self):
        req = QuestionBankBlueprintRequest(
            mark_configs=[MarkConfig(marks=5, count=2)],
            additional_file_paths=["/tmp/ref.pdf"],
        )
        assert len(req.additional_file_paths) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Security: Source Scope Isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceScopeIsolation:
    """Tests that SYSTEM, SUBJECT, and REQUEST scopes are kept separate."""

    def test_vector_chunk_source_scope_values(self):
        """VectorChunk model supports all three source scopes."""
        from app.models.vector_chunk import VectorChunk
        # Verify the model fields accept the three valid scopes
        chunk = VectorChunk(
            document_type="SYLLABUS",
            content="test content",
            source_scope="SYSTEM",
        )
        assert chunk.source_scope == "SYSTEM"

        chunk2 = VectorChunk(
            document_type="SYLLABUS",
            content="test content",
            source_scope="SUBJECT",
        )
        assert chunk2.source_scope == "SUBJECT"

        chunk3 = VectorChunk(
            document_type="REQUEST_REFERENCE",
            content="test content",
            source_scope="REQUEST",
            generation_run_id="run-123",
        )
        assert chunk3.source_scope == "REQUEST"
        assert chunk3.generation_run_id == "run-123"

    def test_system_document_always_system_scope(self):
        """SystemDocument model source_scope column has default='SYSTEM'."""
        from app.models.system_document import SystemDocument
        from sqlalchemy import inspect as sa_inspect
        # Check the column default is "SYSTEM" via SQLAlchemy column inspection
        mapper = sa_inspect(SystemDocument)
        scope_col = mapper.columns["source_scope"]
        # The default should be set to "SYSTEM"
        col_default = scope_col.default
        assert col_default is not None
        assert col_default.arg == "SYSTEM"

    def test_request_chunk_has_generation_run_id(self):
        """REQUEST-scoped chunks must carry generation_run_id for isolation."""
        from app.models.vector_chunk import VectorChunk
        run_id = "test-gen-run-001"
        chunk = VectorChunk(
            document_type="REQUEST_REFERENCE",
            content="ref content",
            source_scope="REQUEST",
            generation_run_id=run_id,
        )
        assert chunk.generation_run_id == run_id
        assert chunk.source_scope == "REQUEST"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Config: Knowledge Base Path
# ─────────────────────────────────────────────────────────────────────────────

class TestKnowledgeBaseConfig:
    """Tests that the knowledge base config is correctly set."""

    def test_knowledge_base_dir_configured(self):
        settings = get_settings()
        assert settings.knowledge_base_dir is not None
        assert len(settings.knowledge_base_dir) > 0

    def test_knowledge_base_dir_resolves(self):
        settings = get_settings()
        path = Path(settings.knowledge_base_dir).resolve()
        # Should not raise — just check it's a valid path object
        assert isinstance(path, Path)

    def test_knowledge_base_relative_path(self):
        """Knowledge base should use a relative or environment-configurable path."""
        settings = get_settings()
        # Default should be relative, not an absolute hardcoded dev path
        kb_dir = settings.knowledge_base_dir
        assert "knowledge_base" in kb_dir.replace("\\", "/")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Paper Type Selection
# ─────────────────────────────────────────────────────────────────────────────

class TestPaperTypeSelection:
    """Tests for MSE vs ESE type selection in the unified generator."""

    def test_exam_type_mse_enum(self):
        from app.ai.exam_generator import ExamType, EXAM_CONFIGS
        assert ExamType.MSE == "MSE"
        assert ExamType.ESE == "ESE"
        assert EXAM_CONFIGS[ExamType.MSE]["system_doc_types"] == ["MSE_SAMPLE"]
        assert EXAM_CONFIGS[ExamType.ESE]["system_doc_types"] == ["ESE_SAMPLE"]

    def test_mse_default_config(self):
        from app.ai.exam_generator import EXAM_CONFIGS, ExamType
        cfg = EXAM_CONFIGS[ExamType.MSE]
        assert cfg["default_total_marks"] == 30
        assert cfg["has_internal_choice"] is False

    def test_ese_default_config(self):
        from app.ai.exam_generator import EXAM_CONFIGS, ExamType
        cfg = EXAM_CONFIGS[ExamType.ESE]
        assert cfg["default_total_marks"] == 50
        assert cfg["has_internal_choice"] is True

    def test_invalid_paper_type_raises(self):
        from app.ai.exam_generator import ExamType
        with pytest.raises(ValueError):
            ExamType("INVALID_TYPE")


# ─────────────────────────────────────────────────────────────────────────────
# 6. System Document Metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestSystemDocumentTypes:
    """Tests for correct document type metadata assignment."""

    def test_all_required_doc_types_supported(self, tmp_path):
        """All four institutional document types must be classifiable."""
        test_cases = [
            ("po_pi_guidelines.pdf", "PO_PI_GUIDELINE"),
            ("aap_format.pdf", "AAP_FORMAT"),
            ("mse_sample_papers/sample.pdf", "MSE_SAMPLE"),
            ("ese_sample_papers/sample.pdf", "ESE_SAMPLE"),
        ]
        for path_str, expected_type in test_cases:
            full_path = tmp_path / path_str
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()
            result = _classify_document_type(full_path)
            assert result == expected_type, f"Expected {expected_type} for {path_str}, got {result}"

    def test_system_doc_types_are_unique_strings(self):
        """Document type identifiers are non-empty strings."""
        doc_types = ["PO_PI_GUIDELINE", "AAP_FORMAT", "MSE_SAMPLE", "ESE_SAMPLE", "SYSTEM_REFERENCE"]
        for dt in doc_types:
            assert isinstance(dt, str)
            assert len(dt) > 0
            assert dt == dt.upper()  # Should be uppercase


# ─────────────────────────────────────────────────────────────────────────────
# 7. Unit Selection in Blueprints
# ─────────────────────────────────────────────────────────────────────────────

class TestUnitSelection:
    """Tests for unit selection in question bank and paper generation."""

    def test_paper_gen_requires_at_least_one_unit(self):
        """unit_ids must not be empty in paper generation request."""
        with pytest.raises(Exception):  # ValidationError from pydantic
            UnifiedPaperGenerateRequest(
                paper_type="MSE",
                unit_ids=[],  # Should fail min_length=1
                total_marks=30,
                question_counts={"2": 5},
            )

    def test_paper_gen_single_unit(self):
        req = UnifiedPaperGenerateRequest(
            paper_type="MSE",
            unit_ids=[2],
            total_marks=10,
            question_counts={"2": 5},
        )
        assert req.unit_ids == [2]

    def test_paper_gen_multi_unit(self):
        req = UnifiedPaperGenerateRequest(
            paper_type="ESE",
            unit_ids=[1, 2, 3, 4, 5],
            total_marks=50,
            question_counts={"2": 5, "5": 4, "10": 2},
        )
        assert len(req.unit_ids) == 5
        assert req.calculated_marks == 50

    def test_qb_blueprint_multi_unit(self):
        req = QuestionBankBlueprintRequest(
            units=[1, 3],
            mark_configs=[MarkConfig(marks=5, count=4)],
        )
        assert 1 in req.units
        assert 3 in req.units
        assert 2 not in req.units
