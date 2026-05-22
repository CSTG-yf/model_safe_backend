from django.db import models
from django.utils import timezone

from model_evaluation.models import EvaluationRun
from projects.models import Project


class AppTrace(models.Model):
    """Application-chain trace for one model, RAG, Agent, or red-team execution."""

    SCENARIO_TYPES = [
        ("normal", "Normal evaluation"),
        ("jailbreak", "Jailbreak"),
        ("rag", "RAG"),
        ("agent", "Agent"),
        ("regression", "Regression"),
    ]
    RISK_LEVELS = [
        ("none", "None"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="app_traces")
    run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traces",
    )
    trace_id = models.CharField(max_length=128, unique=True, db_index=True)
    scenario_type = models.CharField(max_length=32, choices=SCENARIO_TYPES, default="normal")
    input_text = models.TextField(blank=True, default="")
    final_output = models.TextField(blank=True, default="")
    risk_level = models.CharField(max_length=32, choices=RISK_LEVELS, default="none")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_trace"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "scenario_type", "created_at"]),
            models.Index(fields=["run", "risk_level"]),
        ]

    def __str__(self):
        return f"{self.trace_id} ({self.scenario_type}/{self.risk_level})"


class TraceStep(models.Model):
    """One observable step inside an application trace."""

    STEP_TYPES = [
        ("user_input", "User input"),
        ("attack_prompt", "Attack prompt"),
        ("retrieval", "Retrieval"),
        ("context_build", "Context build"),
        ("model_output", "Model output"),
        ("target_response", "Target response"),
        ("tool_call", "Tool call"),
        ("judge_result", "Judge result"),
        ("post_check", "Post check"),
        ("mitigation", "Mitigation"),
        ("regression", "Regression"),
    ]

    trace = models.ForeignKey(AppTrace, on_delete=models.CASCADE, related_name="steps")
    step_type = models.CharField(max_length=64, choices=STEP_TYPES)
    name = models.CharField(max_length=255)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trace_step"
        ordering = ["trace_id", "position", "id"]
        indexes = [
            models.Index(fields=["trace", "step_type"]),
            models.Index(fields=["trace", "position"]),
        ]

    def __str__(self):
        return f"{self.trace.trace_id}:{self.position}:{self.step_type}"


class TraceRisk(models.Model):
    """Risk attribution result with evidence and mitigation hint."""

    trace = models.ForeignKey(AppTrace, on_delete=models.CASCADE, related_name="risks")
    step = models.ForeignKey(
        TraceStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks",
    )
    risk_code = models.CharField(max_length=128, db_index=True)
    risk_name = models.CharField(max_length=255)
    risk_level = models.CharField(max_length=32, choices=AppTrace.RISK_LEVELS, default="low")
    evidence = models.JSONField(default=list, blank=True)
    reason = models.TextField(blank=True, default="")
    mitigation_hint = models.TextField(blank=True, default="")
    confidence = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trace_risk"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["trace", "risk_level"]),
            models.Index(fields=["risk_code"]),
        ]

    def __str__(self):
        return f"{self.trace.trace_id}:{self.risk_code}:{self.risk_level}"

