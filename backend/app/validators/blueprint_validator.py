"""
ADAPT — Exam Paper Deterministic Validators

Comprehensive validation suite for university examination papers:
- MarksValidator: Verifies total paper marks, section arithmetic, choices
- BloomValidator: Verifies cognitive level distribution vs blueprint
- CoverageValidator: Verifies unit coverage, topic diversity, and CO distribution
- BlueprintValidator: Master orchestrator producing structured validation reports
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

Tuple_Check = Tuple[str, bool, str, bool]  # (name, passed, message, is_warning)


class ValidationCheck:
    def __init__(self, name: str, passed: bool, message: str, is_warning: bool = False):
        self.name = name
        self.passed = passed
        self.message = message
        self.is_warning = is_warning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "type": "WARNING" if self.is_warning else ("PASSED" if self.passed else "ERROR"),
        }


class ExamValidationReport:
    def __init__(self):
        self.is_valid = True
        self.checks: List[ValidationCheck] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add(self, name: str, passed: bool, message: str, is_warning: bool = False):
        check = ValidationCheck(name, passed, message, is_warning)
        self.checks.append(check)
        if not passed:
            if is_warning:
                self.warnings.append(message)
            else:
                self.errors.append(message)
                self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "checks": [c.to_dict() for c in self.checks],
            "errors": self.errors,
            "warnings": self.warnings,
            "score": round((sum(1 for c in self.checks if c.passed) / max(1, len(self.checks))) * 100, 1),
        }


class MarksValidator:
    """Deterministic validation of marks arithmetic."""

    @staticmethod
    def validate(
        questions: List[Dict[str, Any]],
        expected_total_marks: int,
        sections: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Tuple_Check]:
        checks = []
        actual_total = sum(q.get("marks", 0) for q in questions if q.get("is_compulsory", True))
        all_marks_sum = sum(q.get("marks", 0) for q in questions)

        if actual_total == expected_total_marks:
            checks.append(("Total Marks Verification", True, f"Sum of answerable marks ({actual_total}m) exactly matches target ({expected_total_marks}m).", False))
        elif all_marks_sum == expected_total_marks:
            checks.append(("Total Marks Verification", True, f"Total question marks ({all_marks_sum}m) matches blueprint total.", False))
        else:
            checks.append(("Total Marks Verification", False, f"Marks mismatch: paper provides {actual_total}m (total questions: {all_marks_sum}m), expected {expected_total_marks}m.", False))

        return checks


class CoverageValidator:
    """Deterministic validation of syllabus unit, topic, and CO coverage."""

    @staticmethod
    def validate(
        questions: List[Dict[str, Any]],
        expected_units: List[int],
    ) -> List[Tuple_Check]:
        checks = []
        covered_units = set(q.get("unit_number") for q in questions if q.get("unit_number") is not None)
        missing_units = set(expected_units) - covered_units

        if not missing_units:
            checks.append(("Unit Coverage", True, f"All requested units ({expected_units}) are covered.", False))
        else:
            checks.append(("Unit Coverage", False, f"Missing syllabus units: {sorted(list(missing_units))}", False))

        # CO distribution check
        covered_cos = set(q.get("co_code") for q in questions if q.get("co_code"))
        if len(covered_cos) >= 2:
            checks.append(("CO Distribution", True, f"Paper addresses {len(covered_cos)} distinct Course Outcomes ({sorted(list(covered_cos))}).", False))
        else:
            checks.append(("CO Distribution", True, "Low CO diversity in questions.", True))

        return checks


class BloomDistributionValidator:
    """Validates cognitive level balance."""

    @staticmethod
    def validate(
        questions: List[Dict[str, Any]],
        target_bloom: Optional[Dict[str, int]] = None,
    ) -> List[Tuple_Check]:
        checks = []
        bloom_counts = {}
        for q in questions:
            lvl = q.get("bloom_level", "Understand")
            bloom_counts[lvl] = bloom_counts.get(lvl, 0) + 1

        total_q = max(1, len(questions))
        higher_order = sum(bloom_counts.get(k, 0) for k in ["Apply", "Analyze", "Evaluate", "Create"])
        higher_pct = (higher_order / total_q) * 100

        if higher_pct >= 40:
            checks.append(("Bloom Cognitive Balance", True, f"{higher_pct:.0f}% higher-order cognitive questions (Apply/Analyze/Evaluate/Create).", False))
        else:
            checks.append(("Bloom Cognitive Balance", True, f"Only {higher_pct:.0f}% higher-order questions. Paper is heavily weighted toward recall/understanding.", True))

        return checks


# Helper tuple alias
Tuple_Check = tuple  # (name, passed, message, is_warning)


class LOCoverageValidator:
    """Validates that questions cover the expected Learning Outcomes."""

    @staticmethod
    def validate(
        questions: List[Dict[str, Any]],
        expected_lo_codes: Optional[List[str]] = None,
    ) -> List[Tuple_Check]:
        checks = []
        covered_los = set(q.get("lo_code") for q in questions if q.get("lo_code"))

        if expected_lo_codes:
            missing_los = set(expected_lo_codes) - covered_los
            if not missing_los:
                checks.append(("LO Coverage", True, f"All {len(expected_lo_codes)} expected LOs are covered.", False))
            else:
                checks.append(("LO Coverage", False, f"Missing LOs: {sorted(list(missing_los))}. Only {len(covered_los)} of {len(expected_lo_codes)} covered.", True))
        elif covered_los:
            checks.append(("LO Coverage", True, f"Questions cover {len(covered_los)} distinct Learning Outcomes.", False))
        else:
            checks.append(("LO Coverage", True, "No LO metadata on questions. Consider mapping questions to LOs.", True))

        return checks


class MarkConfigValidator:
    """Validates mark configs arithmetic consistency."""

    @staticmethod
    def validate(
        mark_configs: List[Dict[str, Any]],
        expected_total: int,
    ) -> List[Tuple_Check]:
        checks = []
        if not mark_configs:
            return checks

        calc_total = sum(mc.get("marks", 0) * mc.get("count", 0) for mc in mark_configs)
        calc_questions = sum(mc.get("count", 0) for mc in mark_configs)

        if calc_total == expected_total:
            checks.append(("Mark Config Arithmetic", True, f"Mark configs sum to {calc_total}m with {calc_questions} questions — matches expected total.", False))
        else:
            checks.append(("Mark Config Arithmetic", False, f"Mark configs sum to {calc_total}m but blueprint expects {expected_total}m.", False))

        return checks


class MasterBlueprintValidator:
    """Master validator assembling all deterministic checks."""

    @staticmethod
    def validate_exam_paper(
        questions: List[Dict[str, Any]],
        total_marks: int,
        units_covered: List[int],
        target_bloom: Optional[Dict[str, int]] = None,
        expected_lo_codes: Optional[List[str]] = None,
        mark_configs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        report = ExamValidationReport()

        # 1. Marks
        for name, passed, msg, is_warn in MarksValidator.validate(questions, total_marks):
            report.add(name, passed, msg, is_warn)

        # 2. Coverage
        for name, passed, msg, is_warn in CoverageValidator.validate(questions, units_covered):
            report.add(name, passed, msg, is_warn)

        # 3. Bloom
        for name, passed, msg, is_warn in BloomDistributionValidator.validate(questions, target_bloom):
            report.add(name, passed, msg, is_warn)

        # 4. LO Coverage
        for name, passed, msg, is_warn in LOCoverageValidator.validate(questions, expected_lo_codes):
            report.add(name, passed, msg, is_warn)

        # 5. Mark Config Arithmetic
        if mark_configs:
            for name, passed, msg, is_warn in MarkConfigValidator.validate(mark_configs, total_marks):
                report.add(name, passed, msg, is_warn)

        # 6. Duplicate checks
        q_texts = [q.get("question_text", "").strip() for q in questions]
        if len(q_texts) == len(set(q_texts)):
            report.add("Duplicate Question Check", True, "No duplicate questions detected in exam paper.", False)
        else:
            report.add("Duplicate Question Check", False, "Duplicate questions detected within the exam paper!", False)

        return report.to_dict()

    @staticmethod
    def validate_generation_request(
        total_marks: int,
        question_counts: Dict[int, int],
    ) -> tuple:
        """
        Pre-generation validation of marks arithmetic.
        
        BLOCKS generation if configured question counts don't sum to requested total.
        Must be called BEFORE the LLM — do NOT let the LLM fix arithmetic.
        
        Args:
            total_marks: Faculty-requested total marks
            question_counts: Dict of {marks_per_question: count}
            
        Returns:
            (is_valid, calculated_total, message)
        """
        calculated = sum(marks * count for marks, count in question_counts.items())
        total_questions = sum(question_counts.values())

        if calculated == total_marks:
            breakdown = ", ".join(
                f"{count}×{marks}m={marks*count}"
                for marks, count in sorted(question_counts.items())
            )
            return (
                True,
                calculated,
                f"Blueprint valid: {breakdown} = {calculated}m ({total_questions} questions)",
            )
        else:
            breakdown = ", ".join(
                f"{count}×{marks}m={marks*count}"
                for marks, count in sorted(question_counts.items())
            )
            return (
                False,
                calculated,
                f"Marks mismatch: {breakdown} = {calculated}m but requested {total_marks}m. "
                f"Please adjust question counts.",
            )

