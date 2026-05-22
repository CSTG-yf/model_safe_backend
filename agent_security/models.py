from django.db import models
from django.utils import timezone

from model_evaluation.models import EvaluationRun
from projects.models import Project


class AgentTool(models.Model):
    TOOL_TYPES = [
        ("read", "Read"),
        ("write", "Write"),
        ("external", "External"),
        ("destructive", "Destructive"),
        ("payment", "Payment"),
        ("admin", "Admin"),
    ]
    RISK_LEVELS = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="agent_tools")
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    tool_type = models.CharField(max_length=32, choices=TOOL_TYPES, default="read")
    risk_level = models.CharField(max_length=32, choices=RISK_LEVELS, default="low")
    allowed_roles = models.JSONField(default=list, blank=True)
    parameter_schema = models.JSONField(default=dict, blank=True)
    requires_confirmation = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    policy = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_tool"
        unique_together = ("project", "name")
        indexes = [
            models.Index(fields=["project", "enabled"]),
            models.Index(fields=["project", "risk_level"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.name}:{self.risk_level}"


class AgentToolCall(models.Model):
    DECISIONS = [
        ("allowed", "Allowed"),
        ("blocked", "Blocked"),
        ("requires_confirmation", "Requires confirmation"),
        ("error", "Error"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="agent_tool_calls")
    run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_tool_calls",
    )
    tool = models.ForeignKey(
        AgentTool,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls",
    )
    trace_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    case_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    prompt = models.TextField(blank=True, default="")
    planned_tool_name = models.CharField(max_length=128)
    arguments = models.JSONField(default=dict, blank=True)
    user_role = models.CharField(max_length=64, default="member")
    decision = models.CharField(max_length=32, choices=DECISIONS, default="blocked")
    blocked_reason = models.CharField(max_length=255, blank=True, default="")
    risk_code = models.CharField(max_length=128, blank=True, default="")
    risk_level = models.CharField(max_length=32, blank=True, default="")
    simulated_result = models.JSONField(default=dict, blank=True)
    policy_snapshot = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "agent_tool_call"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["project", "decision"]),
            models.Index(fields=["run", "decision"]),
            models.Index(fields=["risk_code"]),
            models.Index(fields=["trace_id"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.planned_tool_name}:{self.decision}"
