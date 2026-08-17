"""
ADAPT — Unit Tests for Deterministic Validators
"""

import pytest
from app.schemas.aap import AAPPlanDataSchema, AAPRowSchema
from app.validators.aap_validator import AAPValidator
from app.validators.blueprint_validator import (
    BloomDistributionValidator,
    CoverageValidator,
    MarksValidator,
    MasterBlueprintValidator,
)
from app.validators.duplicate_detector import DuplicateDetector


def test_marks_validator_exact_match():
    questions = [
        {"marks": 10, "is_compulsory": True},
        {"marks": 10, "is_compulsory": True},
        {"marks": 10, "is_compulsory": True},
    ]
    checks = MarksValidator.validate(questions, expected_total_marks=30)
    assert len(checks) == 1
    assert checks[0][1] is True  # Passed


def test_marks_validator_mismatch():
    questions = [
        {"marks": 10, "is_compulsory": True},
        {"marks": 10, "is_compulsory": True},
    ]
    checks = MarksValidator.validate(questions, expected_total_marks=30)
    assert len(checks) == 1
    assert checks[0][1] is False  # Failed


def test_coverage_validator_all_units():
    questions = [
        {"unit_number": 1, "co_code": "CO1"},
        {"unit_number": 2, "co_code": "CO2"},
        {"unit_number": 3, "co_code": "CO3"},
    ]
    checks = CoverageValidator.validate(questions, expected_units=[1, 2, 3])
    assert any(name == "Unit Coverage" and passed for name, passed, _, _ in checks)


def test_coverage_validator_missing_unit():
    questions = [
        {"unit_number": 1, "co_code": "CO1"},
        {"unit_number": 2, "co_code": "CO2"},
    ]
    checks = CoverageValidator.validate(questions, expected_units=[1, 2, 3])
    assert any(name == "Unit Coverage" and not passed for name, passed, _, _ in checks)


def test_aap_validator():
    plan = AAPPlanDataSchema(
        total_weeks=3,
        total_hours=9,
        weeks=[
            AAPRowSchema(week_number=1, unit_number=1, planned_hours=3, teaching_method="PPT", co_mapped="CO1"),
            AAPRowSchema(week_number=2, unit_number=2, planned_hours=3, teaching_method="Chalk", co_mapped="CO2"),
            AAPRowSchema(week_number=3, unit_number=3, planned_hours=3, teaching_method="Lab", co_mapped="CO3"),
        ],
    )
    report = AAPValidator.validate(plan, expected_total_hours=9, expected_units=[1, 2, 3])
    assert report["is_valid"] is True
    assert len(report["errors"]) == 0
