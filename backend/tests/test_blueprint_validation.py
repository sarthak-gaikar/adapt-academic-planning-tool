"""
ADAPT — OBE Mapping Tests

Tests for blueprint validation with mark configs.
"""

import pytest
from app.schemas.question_bank_blueprint import (
    MarkConfig,
    QuestionBankBlueprintRequest,
)


class TestMarkConfig:
    def test_total_marks_calculation(self):
        req = QuestionBankBlueprintRequest(
            units=[1, 2, 3],
            mark_configs=[
                MarkConfig(marks=2, count=10),
                MarkConfig(marks=5, count=5),
                MarkConfig(marks=10, count=2),
            ],
        )
        assert req.total_marks == 65  # 20 + 25 + 20
        assert req.total_questions == 17  # 10 + 5 + 2

    def test_single_config(self):
        req = QuestionBankBlueprintRequest(
            units=[1],
            mark_configs=[MarkConfig(marks=5, count=4)],
        )
        assert req.total_marks == 20
        assert req.total_questions == 4

    def test_mark_config_validation(self):
        with pytest.raises(Exception):
            MarkConfig(marks=0, count=1)  # marks must be >= 1

        with pytest.raises(Exception):
            MarkConfig(marks=5, count=0)  # count must be >= 1

    def test_empty_mark_configs_rejected(self):
        with pytest.raises(Exception):
            QuestionBankBlueprintRequest(
                units=[1],
                mark_configs=[],  # min_length=1
            )
