from model_evaluation.models import MetricDefinition, MetricValue


DEFAULT_METRICS = [
    {
        "code": "jailbreak_success_rate",
        "name": "Jailbreak success rate",
        "category": "red_team",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of red-team attempts that reached the configured success threshold.",
    },
    {
        "code": "privacy_leakage_rate",
        "name": "Privacy leakage rate",
        "category": "safety",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of cases where private or sensitive information was exposed.",
    },
    {
        "code": "harmful_content_rate",
        "name": "Harmful content generation rate",
        "category": "safety",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of cases where harmful, illegal, or non-compliant content was generated.",
    },
    {
        "code": "hallucination_rate",
        "name": "Hallucination rate",
        "category": "quality",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of answers judged as unsupported or factually incorrect.",
    },
    {
        "code": "toxicity_score",
        "name": "Toxicity score",
        "category": "safety",
        "unit": "score",
        "direction": "lower_better",
        "description": "Aggregate toxicity indicator from safety evaluation.",
    },
    {
        "code": "dangerous_tool_call_rate",
        "name": "Dangerous tool call rate",
        "category": "agent",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of Agent traces that attempted dangerous or unauthorized tool calls.",
    },
    {
        "code": "rag_pollution_hit_rate",
        "name": "RAG pollution hit rate",
        "category": "rag",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of RAG tests where polluted or injected documents affected the answer.",
    },
    {
        "code": "regression_pass_rate",
        "name": "Regression pass rate",
        "category": "regression",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of previously failing or high-risk cases that pass after mitigation.",
    },
    {
        "code": "question_field_completeness",
        "name": "Question field completeness",
        "category": "question_bank",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Completeness ratio of required generated-question fields.",
    },
    {
        "code": "json_parse_success_rate",
        "name": "JSON parse success rate",
        "category": "question_bank",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of model generations that produced parseable structured JSON.",
    },
]


class MetricRegistry:
    @staticmethod
    def seed_defaults():
        created = []
        for item in DEFAULT_METRICS:
            definition, _ = MetricDefinition.objects.update_or_create(
                code=item["code"],
                defaults=item,
            )
            created.append(definition)
        return created

    @staticmethod
    def record(project, code, value, run=None, model_name="", risk_code="", dimensions=None, measured_at=None):
        definition = MetricDefinition.objects.get(code=code)
        payload = {
            "definition": definition,
            "project": project,
            "run": run,
            "model_name": model_name,
            "risk_code": risk_code,
            "value": value,
            "unit": definition.unit,
            "dimensions": dimensions or {},
        }
        if measured_at is not None:
            payload["measured_at"] = measured_at
        return MetricValue.objects.create(**payload)
