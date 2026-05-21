from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from question_bank.schemas import GeneratedQuestion


@dataclass
class QuestionQualityResult:
    passed: bool
    completeness: float
    checks: list[dict[str, Any]]
    errors: list[str]


class QuestionQualityService:
    REQUIRED_FIELDS = ["question_type", "question"]

    @classmethod
    def validate_payload(cls, payload: dict[str, Any]) -> tuple[GeneratedQuestion | None, QuestionQualityResult]:
        checks = []
        errors = []

        for field in cls.REQUIRED_FIELDS:
            present = bool(payload.get(field))
            checks.append({"check_type": f"required:{field}", "passed": present})
            if not present:
                errors.append(f"Missing required field: {field}")

        scoring_criteria = payload.get("scoring_criteria") or {}
        criteria_complete = isinstance(scoring_criteria, dict) and bool(scoring_criteria)
        checks.append({"check_type": "scoring_criteria_complete", "passed": criteria_complete})

        answer_present = bool(payload.get("answer")) or bool(payload.get("risk_tags"))
        checks.append({"check_type": "answer_or_risk_tag_present", "passed": answer_present})

        try:
            question = GeneratedQuestion.model_validate(payload)
        except ValidationError as exc:
            question = None
            errors.extend([err["msg"] for err in exc.errors()])

        passed_count = sum(1 for item in checks if item["passed"])
        completeness = passed_count / len(checks) if checks else 0.0
        passed = question is not None and not errors

        return question, QuestionQualityResult(
            passed=passed,
            completeness=round(completeness, 4),
            checks=checks,
            errors=errors,
        )
