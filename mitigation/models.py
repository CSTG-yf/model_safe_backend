from django.db import models

from model_evaluation.models import EvaluationRun
from projects.models import Project
from trace_analysis.models import AppTrace, TraceRisk


class MitigationTemplate(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    risk_code = models.CharField(max_length=128)
    scenario_type = models.CharField(max_length=32, blank=True, default="")
    step_type = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=255)
    description = models.TextField()
    steps = models.JSONField(default=list, blank=True)
    verification_method = models.TextField(blank=True, default="")
    priority = models.CharField(max_length=32, choices=PRIORITY_CHOICES, default="medium")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mitigation_template"
        unique_together = ("risk_code", "scenario_type", "step_type", "title")
        indexes = [
            models.Index(fields=["risk_code", "scenario_type"]),
            models.Index(fields=["enabled", "priority"]),
        ]

    def __str__(self):
        return f"{self.risk_code}:{self.title}"


class MitigationRecommendation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("verified", "Verified"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="mitigation_recommendations")
    trace = models.ForeignKey(AppTrace, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    risk = models.ForeignKey(TraceRisk, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    run = models.ForeignKey(EvaluationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    template = models.ForeignKey(
        MitigationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    risk_code = models.CharField(max_length=128)
    title = models.CharField(max_length=255)
    reason = models.TextField(blank=True, default="")
    steps = models.JSONField(default=list, blank=True)
    verification_cases = models.JSONField(default=list, blank=True)
    priority = models.CharField(max_length=32, default="medium")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mitigation_recommendation"
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["risk_code", "priority"]),
            models.Index(fields=["run"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.risk_code}:{self.title}"


class RegressionSet(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="regression_sets")
    source_run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_regression_sets",
    )
    name = models.CharField(max_length=255)
    risk_codes = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "regression_set"
        indexes = [
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.name}"


class RegressionCase(models.Model):
    regression_set = models.ForeignKey(RegressionSet, on_delete=models.CASCADE, related_name="cases")
    source_case_id = models.CharField(max_length=128, blank=True, default="")
    source_attempt_id = models.CharField(max_length=128, blank=True, default="")
    input_payload = models.JSONField(default=dict, blank=True)
    expected_safe_behavior = models.TextField(blank=True, default="")
    risk_code = models.CharField(max_length=128)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "regression_case"
        indexes = [
            models.Index(fields=["regression_set", "risk_code"]),
            models.Index(fields=["source_case_id"]),
        ]

    def __str__(self):
        return f"{self.regression_set_id}:{self.risk_code}:{self.source_case_id}"

