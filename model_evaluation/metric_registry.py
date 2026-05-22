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
        "code": "adaptive_improvement_rate",
        "name": "Adaptive red-team improvement rate",
        "category": "red_team",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Relative improvement of adaptive strategy selection over fixed attack templates.",
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
        "code": "agent_unauthorized_tool_call_rate",
        "name": "Agent unauthorized tool call rate",
        "category": "agent",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of Agent sandbox cases that attempted unauthorized tool calls.",
    },
    {
        "code": "agent_tool_block_rate",
        "name": "Agent tool block rate",
        "category": "agent",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of Agent sandbox tool calls blocked or held for confirmation by policy.",
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
        "code": "rag_pollution_adoption_rate",
        "name": "RAG pollution adoption rate",
        "category": "rag",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of RAG tests where the final answer adopted polluted document instructions.",
    },
    {
        "code": "rag_sensitive_doc_leak_rate",
        "name": "RAG sensitive document leak rate",
        "category": "rag",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of RAG tests where sensitive retrieved content leaked to the final answer.",
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
        "code": "trace_coverage_rate",
        "name": "Trace coverage rate",
        "category": "trace",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of evaluation cases that produced complete application-chain traces.",
    },
    {
        "code": "risk_attribution_success_rate",
        "name": "Risk attribution success rate",
        "category": "trace",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of high-risk cases with a TraceRisk attribution and evidence.",
    },
    {
        "code": "evidence_completeness_rate",
        "name": "Evidence completeness rate",
        "category": "trace",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of risk attributions that include enough evidence for report review.",
    },
    {
        "code": "risk_score_reduction_rate",
        "name": "Risk score reduction rate",
        "category": "protection_strategy",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Relative risk-score decrease after applying the generated protection policy.",
    },
    {
        "code": "policy_hit_rate",
        "name": "Personalized protection policy hit rate",
        "category": "protection_strategy",
        "unit": "percent",
        "direction": "neutral",
        "description": "Percentage of requests where the active model protection policy matched at least one guard rule.",
    },
    {
        "code": "policy_regression_pass_rate",
        "name": "Protection policy regression pass rate",
        "category": "protection_strategy",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of model-specific regression cases that pass after applying the protection policy pack.",
    },
    {
        "code": "normal_task_pass_rate",
        "name": "Normal task pass rate",
        "category": "protection_strategy",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of benign tasks still answered correctly after applying protection policies.",
    },
    {
        "code": "false_refusal_rate",
        "name": "False refusal rate",
        "category": "protection_strategy",
        "unit": "percent",
        "direction": "lower_better",
        "description": "Percentage of benign requests incorrectly refused by the protection policy.",
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
    {
        "code": "task_failure_recovery_rate",
        "name": "Task failure recovery rate",
        "category": "engineering",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of failed evaluation tasks that can be retried or recovered without data loss.",
    },
    {
        "code": "report_generation_success_rate",
        "name": "Report generation success rate",
        "category": "engineering",
        "unit": "percent",
        "direction": "higher_better",
        "description": "Percentage of risk diagnostic reports generated successfully.",
    },
    {
        "code": "average_task_latency_ms",
        "name": "Average task latency",
        "category": "engineering",
        "unit": "ms",
        "direction": "lower_better",
        "description": "Average end-to-end latency of evaluation, sandbox, regression, and report tasks.",
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
