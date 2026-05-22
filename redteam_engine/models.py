from django.db import models

from model_evaluation.models import EvaluationCase, EvaluationRun


class AttackStrategy(models.Model):
    """Configurable red-team prompt transformation strategy."""

    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=64)
    description = models.TextField(blank=True, default="")
    prompt_template = models.TextField()
    applicable_risks = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attack_strategy"
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["category", "enabled"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"


class RedTeamAttempt(models.Model):
    """One round of adaptive red-team testing."""

    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="redteam_attempts")
    case = models.ForeignKey(
        EvaluationCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redteam_attempts",
    )
    strategy = models.ForeignKey(AttackStrategy, on_delete=models.SET_NULL, null=True, blank=True)
    parent_attempt = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    trace_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    target_risk_code = models.CharField(max_length=128)
    objective = models.TextField(blank=True, default="")
    prompt = models.TextField()
    response = models.TextField(blank=True, default="")
    score = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=32, blank=True, default="")
    judge_output = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=False)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    selection_reason = models.TextField(blank=True, default="")
    token_usage = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "redteam_attempt"
        ordering = ["run_id", "id"]
        indexes = [
            models.Index(fields=["run", "target_risk_code"]),
            models.Index(fields=["strategy", "success"]),
            models.Index(fields=["trace_id"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.strategy_id}:{self.score}"


class StrategyStat(models.Model):
    strategy = models.ForeignKey(AttackStrategy, on_delete=models.CASCADE, related_name="stats")
    risk_code = models.CharField(max_length=128, blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)
    successes = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0)
    average_latency_ms = models.FloatField(default=0)
    novelty_score = models.FloatField(default=1.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "strategy_stat"
        unique_together = ("strategy", "risk_code")
        indexes = [
            models.Index(fields=["risk_code"]),
            models.Index(fields=["strategy", "risk_code"]),
        ]

    @property
    def success_rate(self):
        return self.successes / self.attempts if self.attempts else 0

    def __str__(self):
        return f"{self.strategy.code}:{self.risk_code}"

