"""
ADAPT — Bloom Ordering Tests

Tests for CO and LO Bloom taxonomy ordering validation and reordering.
"""

import pytest
from app.validators.bloom_order_validator import (
    BloomOrderValidator,
    bloom_to_order,
    order_to_bloom,
    BLOOM_HIERARCHY,
)


class TestBloomHelpers:
    def test_bloom_to_order_standard(self):
        assert bloom_to_order("Remember") == 1
        assert bloom_to_order("Understand") == 2
        assert bloom_to_order("Apply") == 3
        assert bloom_to_order("Analyze") == 4
        assert bloom_to_order("Evaluate") == 5
        assert bloom_to_order("Create") == 6

    def test_bloom_to_order_aliases(self):
        assert bloom_to_order("Recall") == 1
        assert bloom_to_order("Analyse") == 4  # British spelling
        assert bloom_to_order("Design") == 6

    def test_bloom_to_order_none_or_unknown(self):
        assert bloom_to_order(None) == 2
        assert bloom_to_order("") == 2
        assert bloom_to_order("FakeLevel") == 2

    def test_order_to_bloom(self):
        assert order_to_bloom(1) == "Remember"
        assert order_to_bloom(6) == "Create"
        assert order_to_bloom(99) == "Understand"


class TestBloomOrderValidation:
    def test_valid_ordering(self):
        cos = [
            {"co_code": "CO1", "bloom_level": "Remember"},
            {"co_code": "CO2", "bloom_level": "Understand"},
            {"co_code": "CO3", "bloom_level": "Apply"},
            {"co_code": "CO4", "bloom_level": "Analyze"},
            {"co_code": "CO5", "bloom_level": "Create"},
        ]
        result = BloomOrderValidator.validate_cos(cos)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_same_level_adjacent(self):
        cos = [
            {"co_code": "CO1", "bloom_level": "Understand"},
            {"co_code": "CO2", "bloom_level": "Understand"},
            {"co_code": "CO3", "bloom_level": "Apply"},
        ]
        result = BloomOrderValidator.validate_cos(cos)
        assert result.is_valid is True

    def test_invalid_ordering_detected(self):
        cos = [
            {"co_code": "CO1", "bloom_level": "Analyze"},
            {"co_code": "CO2", "bloom_level": "Remember"},
            {"co_code": "CO3", "bloom_level": "Create"},
        ]
        result = BloomOrderValidator.validate_cos(cos)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_empty_list_valid(self):
        result = BloomOrderValidator.validate_cos([])
        assert result.is_valid is True


class TestBloomReordering:
    def test_reorder_fixes_invalid(self):
        cos = [
            {"co_code": "CO1", "bloom_level": "Analyze"},
            {"co_code": "CO2", "bloom_level": "Remember"},
            {"co_code": "CO3", "bloom_level": "Apply"},
        ]
        sorted_cos, result = BloomOrderValidator.reorder_cos(cos)
        assert result.was_reordered is True
        assert result.is_valid is True
        # After reorder: Remember, Apply, Analyze
        assert sorted_cos[0]["bloom_level"] == "Remember"
        assert sorted_cos[0]["co_code"] == "CO1"
        assert sorted_cos[1]["bloom_level"] == "Apply"
        assert sorted_cos[1]["co_code"] == "CO2"
        assert sorted_cos[2]["bloom_level"] == "Analyze"
        assert sorted_cos[2]["co_code"] == "CO3"

    def test_reorder_no_change_if_valid(self):
        cos = [
            {"co_code": "CO1", "bloom_level": "Remember"},
            {"co_code": "CO2", "bloom_level": "Apply"},
        ]
        sorted_cos, result = BloomOrderValidator.reorder_cos(cos)
        assert result.was_reordered is False

    def test_reorder_renumbers_codes(self):
        cos = [
            {"co_code": "CO3", "bloom_level": "Create"},
            {"co_code": "CO1", "bloom_level": "Remember"},
        ]
        sorted_cos, result = BloomOrderValidator.reorder_cos(cos)
        assert sorted_cos[0]["co_code"] == "CO1"
        assert sorted_cos[1]["co_code"] == "CO2"


class TestLOBloomOrdering:
    def test_validate_per_unit(self):
        los_by_unit = {
            1: [
                {"lo_code": "LO1.1", "bloom_level": "Remember"},
                {"lo_code": "LO1.2", "bloom_level": "Apply"},
            ],
            2: [
                {"lo_code": "LO2.1", "bloom_level": "Evaluate"},
                {"lo_code": "LO2.2", "bloom_level": "Understand"},
            ],
        }
        results = BloomOrderValidator.validate_los_per_unit(los_by_unit)
        assert results[1].is_valid is True
        assert results[2].is_valid is False

    def test_reorder_per_unit(self):
        los_by_unit = {
            1: [
                {"lo_code": "LO1.1", "bloom_level": "Analyze"},
                {"lo_code": "LO1.2", "bloom_level": "Remember"},
            ],
        }
        results = BloomOrderValidator.reorder_los_per_unit(los_by_unit)
        sorted_los, val = results[1]
        assert sorted_los[0]["bloom_level"] == "Remember"
        assert sorted_los[0]["lo_code"] == "LO1.1"
        assert sorted_los[1]["bloom_level"] == "Analyze"
        assert sorted_los[1]["lo_code"] == "LO1.2"
