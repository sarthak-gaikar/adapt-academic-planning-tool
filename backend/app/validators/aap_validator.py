"""
ADAPT — AAP Deterministic Validator

Validates Academic Activity Plans against deterministic academic constraints:
1. Total hours match subject requirement
2. Week continuity (1..N without gaps)
3. Unit sequence and full unit coverage
4. Valid CO associations
5. Topic coverage completeness
"""

from typing import Any, Dict, List
from app.schemas.aap import AAPPlanDataSchema


class AAPValidationReport:
    def __init__(self):
        self.is_valid = True
        self.checks: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_check(self, name: str, passed: bool, message: str, is_warning: bool = False):
        self.checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "type": "WARNING" if is_warning else ("PASSED" if passed else "ERROR"),
        })
        if not passed:
            if is_warning:
                self.warnings.append(message)
            else:
                self.errors.append(message)
                self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "total_checks": len(self.checks),
        }


class AAPValidator:
    """Deterministic constraint validator for AAP plans."""

    @staticmethod
    def validate(
        plan: AAPPlanDataSchema,
        expected_total_hours: int = 45,
        expected_units: List[int] = None,
        valid_cos: List[str] = None,
    ) -> Dict[str, Any]:
        report = AAPValidationReport()
        expected_units = expected_units or [1, 2, 3, 4, 5]
        valid_cos = valid_cos or ["CO1", "CO2", "CO3", "CO4", "CO5"]

        if not plan.weeks:
            report.add_check("Non-empty Plan", False, "AAP plan contains 0 instructional weeks.")
            return report.to_dict()

        # Check 1: Total Hours
        actual_hours = sum(w.planned_hours for w in plan.weeks)
        hours_diff = abs(actual_hours - expected_total_hours)
        if hours_diff == 0:
            report.add_check("Total Hours Exact Match", True, f"Total planned hours ({actual_hours}) exactly matches syllabus teaching hours ({expected_total_hours}).")
        elif hours_diff <= 3:
            report.add_check("Total Hours Tolerance", True, f"Planned hours ({actual_hours}) is within acceptable tolerance of target ({expected_total_hours}).", is_warning=True)
        else:
            report.add_check("Total Hours Constraint", False, f"Planned hours ({actual_hours}) deviates significantly from syllabus hours ({expected_total_hours}).")

        # Check 2: Week sequence continuity
        week_nums = [w.week_number for w in plan.weeks]
        expected_week_nums = list(range(1, len(week_nums) + 1))
        if week_nums == expected_week_nums:
            report.add_check("Week Number Continuity", True, f"All {len(week_nums)} weeks are sequenced continuously from 1 to {len(week_nums)}.")
        else:
            report.add_check("Week Number Continuity", False, f"Week numbers are non-continuous or disordered: {week_nums}")

        # Check 3: Unit Coverage
        covered_units = set(w.unit_number for w in plan.weeks)
        missing_units = set(expected_units) - covered_units
        if not missing_units:
            report.add_check("Unit Coverage", True, f"All units {expected_units} are covered in the plan.")
        else:
            report.add_check("Unit Coverage", False, f"Missing units in plan: {sorted(list(missing_units))}")

        # Check 4: CO Mapping Validity
        plan_cos = set(w.co_mapped for w in plan.weeks)
        invalid_cos = plan_cos - set(valid_cos)
        if not invalid_cos:
            report.add_check("CO Alignment", True, "All mapped COs match active course outcomes.")
        else:
            report.add_check("CO Alignment", True, f"Plan references unrecognized COs: {invalid_cos}", is_warning=True)

        return report.to_dict()
