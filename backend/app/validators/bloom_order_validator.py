"""
ADAPT — Bloom's Taxonomy Order Validator

Deterministic validator ensuring Course Outcomes and Learning Outcomes
are ordered by increasing Bloom cognitive complexity:
  1. Remember  2. Understand  3. Apply  4. Analyze  5. Evaluate  6. Create

Used after LLM generation to guarantee ordering—does not rely on the LLM alone.
"""

from typing import Any, Dict, List, Optional, Tuple


# Canonical Bloom hierarchy mapping
BLOOM_HIERARCHY: Dict[str, int] = {
    "Remember": 1,
    "Recall": 1,
    "Understand": 2,
    "Apply": 3,
    "Analyze": 4,
    "Analyse": 4,  # British spelling alias
    "Evaluate": 5,
    "Create": 6,
    "Design": 6,
}

BLOOM_LEVEL_NAMES: Dict[int, str] = {
    1: "Remember",
    2: "Understand",
    3: "Apply",
    4: "Analyze",
    5: "Evaluate",
    6: "Create",
}


def bloom_to_order(level: Optional[str]) -> int:
    """Convert a Bloom level name to its numeric order (1-6). Defaults to 2 if unknown."""
    if not level:
        return 2
    return BLOOM_HIERARCHY.get(level.strip().capitalize(), 2)


def order_to_bloom(order: int) -> str:
    """Convert a numeric Bloom order to the canonical level name."""
    return BLOOM_LEVEL_NAMES.get(order, "Understand")


class BloomOrderValidationResult:
    """Result of a Bloom ordering validation check."""

    def __init__(self):
        self.is_valid: bool = True
        self.original_order: List[str] = []
        self.corrected_order: List[str] = []
        self.errors: List[str] = []
        self.was_reordered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "original_order": self.original_order,
            "corrected_order": self.corrected_order,
            "errors": self.errors,
            "was_reordered": self.was_reordered,
        }


class BloomOrderValidator:
    """Deterministic Bloom's Taxonomy ordering validator for COs and LOs."""

    @staticmethod
    def validate_ordering(items: List[Dict[str, Any]], bloom_key: str = "bloom_level") -> BloomOrderValidationResult:
        """
        Validates that items are in non-decreasing Bloom order.
        Each item dict must have the bloom_key field.

        Returns a validation result with is_valid=True if ordering is correct,
        or is_valid=False with error details if not.
        """
        result = BloomOrderValidationResult()
        if not items:
            return result

        orders = [bloom_to_order(item.get(bloom_key)) for item in items]
        result.original_order = [item.get(bloom_key, "Unknown") for item in items]

        for i in range(1, len(orders)):
            if orders[i] < orders[i - 1]:
                result.is_valid = False
                result.errors.append(
                    f"Item {i} ({result.original_order[i]}, order={orders[i]}) "
                    f"has lower Bloom level than item {i-1} "
                    f"({result.original_order[i-1]}, order={orders[i-1]})"
                )

        return result

    @staticmethod
    def reorder_items(
        items: List[Dict[str, Any]],
        bloom_key: str = "bloom_level",
        code_key: str = "co_code",
        code_prefix: str = "CO",
    ) -> Tuple[List[Dict[str, Any]], BloomOrderValidationResult]:
        """
        Sorts items by Bloom order (ascending) and renumbers their codes.
        Returns (sorted_items, validation_result).
        
        Example:
            Input:  [CO1:Analyze, CO2:Remember, CO3:Apply]
            Output: [CO1:Remember, CO2:Apply, CO3:Analyze]
        """
        result = BloomOrderValidationResult()
        if not items:
            return items, result

        result.original_order = [item.get(bloom_key, "Unknown") for item in items]

        # Sort by Bloom hierarchy order (stable sort preserves relative order of same-level items)
        sorted_items = sorted(
            items,
            key=lambda x: bloom_to_order(x.get(bloom_key)),
        )

        # Check if reordering was needed
        original_blooms = [bloom_to_order(item.get(bloom_key)) for item in items]
        sorted_blooms = [bloom_to_order(item.get(bloom_key)) for item in sorted_items]
        result.was_reordered = original_blooms != sorted_blooms

        # Renumber codes
        for idx, item in enumerate(sorted_items, 1):
            item[code_key] = f"{code_prefix}{idx}"

        result.corrected_order = [item.get(bloom_key, "Unknown") for item in sorted_items]
        result.is_valid = True  # After reordering, it's valid by construction
        return sorted_items, result

    @staticmethod
    def validate_cos(cos: List[Dict[str, Any]]) -> BloomOrderValidationResult:
        """Validate Course Outcomes are in increasing Bloom order."""
        return BloomOrderValidator.validate_ordering(cos, bloom_key="bloom_level")

    @staticmethod
    def reorder_cos(cos: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], BloomOrderValidationResult]:
        """Reorder Course Outcomes by Bloom level and renumber CO1, CO2, ..."""
        return BloomOrderValidator.reorder_items(
            cos, bloom_key="bloom_level", code_key="co_code", code_prefix="CO"
        )

    @staticmethod
    def validate_los_per_unit(
        los_by_unit: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[int, BloomOrderValidationResult]:
        """
        Validates Learning Outcomes are in increasing Bloom order WITHIN each unit.
        Returns a dict of unit_number → validation result.
        """
        results = {}
        for unit_num, unit_los in los_by_unit.items():
            results[unit_num] = BloomOrderValidator.validate_ordering(
                unit_los, bloom_key="bloom_level"
            )
        return results

    @staticmethod
    def reorder_los_per_unit(
        los_by_unit: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[int, Tuple[List[Dict[str, Any]], BloomOrderValidationResult]]:
        """
        Reorders LOs within each unit by Bloom level.
        Renumbers LO codes as LO{unit}.1, LO{unit}.2, ...
        """
        results = {}
        for unit_num, unit_los in los_by_unit.items():
            sorted_los, val_result = BloomOrderValidator.reorder_items(
                unit_los,
                bloom_key="bloom_level",
                code_key="lo_code",
                code_prefix=f"LO{unit_num}.",
            )
            results[unit_num] = (sorted_los, val_result)
        return results
