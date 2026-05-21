from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionSource = Literal["llm", "security_seed", "manual", "regression", "imported"]


class GeneratedQuestionOption(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)
    is_correct: bool = False


class GeneratedRiskTag(BaseModel):
    risk_code: str = Field(min_length=1, max_length=128)
    risk_name: str = Field(min_length=1, max_length=255)
    regulation_ref: str = ""
    weight: float = Field(default=1.0, ge=0)


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: QuestionSource = "llm"
    domain: str = ""
    subdomain: str = ""
    content_type: str = ""
    question_type: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: list[GeneratedQuestionOption] = Field(default_factory=list)
    answer: str = ""
    explanation: str = ""
    scoring_criteria: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[GeneratedRiskTag] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("domain", mode="before")
    @classmethod
    def fill_domain_from_content_type(cls, value, info):
        if value:
            return value
        return info.data.get("content_type", "")

    @model_validator(mode="after")
    def validate_question_shape(self):
        normalized_type = self.question_type.lower()
        if ("choice" in normalized_type or "选择" in self.question_type) and not self.options:
            raise ValueError("Choice questions must include options.")
        if not self.answer and not self.risk_tags:
            raise ValueError("Question must include an answer or risk tags.")
        return self


class GeneratedQuestionBatch(BaseModel):
    questions: list[GeneratedQuestion] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_single_or_list_payload(cls, value):
        if isinstance(value, list):
            return {"questions": value}
        if isinstance(value, dict) and "questions" not in value:
            if "question" in value:
                return {"questions": [value]}
        return value
