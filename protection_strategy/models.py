from django.db import models
from django.utils import timezone

from mitigation.models import MitigationRecommendation, RegressionCase
from model_evaluation.models import EvaluationRun
from projects.models import Project
from trace_analysis.models import AppTrace, TraceRisk


class ModelProtectionStrategy(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="protection_strategies")
    target_model_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    active_version = models.ForeignKey(
        "ProtectionPolicyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    risk_profile = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_protection_strategies",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "model_protection_strategy"
        unique_together = ("project", "target_model_name", "name")
        indexes = [
            models.Index(fields=["project", "target_model_name", "status"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.target_model_name}:{self.name}"


class ProtectionPolicyVersion(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("superseded", "Superseded"),
        ("archived", "Archived"),
    ]

    strategy = models.ForeignKey(ModelProtectionStrategy, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    risk_profile = models.JSONField(default=dict, blank=True)
    guard_prompt = models.TextField(blank=True, default="")
    guard_policy = models.JSONField(default=dict, blank=True)
    rag_guard_rules = models.JSONField(default=dict, blank=True)
    agent_tool_policy = models.JSONField(default=dict, blank=True)
    output_guard_rules = models.JSONField(default=dict, blank=True)
    regression_cases = models.JSONField(default=list, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    source_summary = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_protection_policy_versions",
    )
    created_at = models.DateTimeField(default=timezone.now)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "protection_policy_version"
        unique_together = ("strategy", "version")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["strategy", "status"]),
            models.Index(fields=["strategy", "version"]),
        ]

    def __str__(self):
        return f"{self.strategy_id}:v{self.version}:{self.status}"


class ProtectionPolicySource(models.Model):
    SOURCE_TYPES = [
        ("run", "Evaluation run"),
        ("trace", "Trace"),
        ("risk", "Trace risk"),
        ("recommendation", "Mitigation recommendation"),
        ("regression_case", "Regression case"),
        ("manual", "Manual"),
    ]

    policy_version = models.ForeignKey(ProtectionPolicyVersion, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=64, choices=SOURCE_TYPES)
    run = models.ForeignKey(EvaluationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="policy_sources")
    trace = models.ForeignKey(AppTrace, on_delete=models.SET_NULL, null=True, blank=True, related_name="policy_sources")
    risk = models.ForeignKey(TraceRisk, on_delete=models.SET_NULL, null=True, blank=True, related_name="policy_sources")
    recommendation = models.ForeignKey(
        MitigationRecommendation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="policy_sources",
    )
    regression_case = models.ForeignKey(
        RegressionCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="policy_sources",
    )
    weight = models.FloatField(default=1.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "protection_policy_source"
        indexes = [
            models.Index(fields=["policy_version", "source_type"]),
            models.Index(fields=["run"]),
            models.Index(fields=["trace"]),
            models.Index(fields=["risk"]),
        ]

    def __str__(self):
        return f"{self.policy_version_id}:{self.source_type}:{self.weight}"
