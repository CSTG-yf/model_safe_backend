from django.db import models
from django.utils import timezone


class AsyncTaskRecord(models.Model):
    """Unified task progress record for long-running backend jobs."""

    TASK_TYPES = [
        ("question_generation", "Question generation"),
        ("model_evaluation", "Model evaluation"),
        ("jailbreak_evaluation", "Jailbreak evaluation"),
        ("report_generation", "Report generation"),
        ("regression", "Regression"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("cancelling", "Cancelling"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
        ("completed", "Completed"),
    ]

    id = models.BigAutoField(primary_key=True)
    task_id = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=64, choices=TASK_TYPES, default="other")
    project_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    progress = models.PositiveIntegerField(default=0)
    message = models.CharField(max_length=500, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    cancel_requested = models.BooleanField(default=False)
    celery_task_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    created_by_id = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "async_task_record"
        indexes = [
            models.Index(fields=["project_id", "task_type", "status"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def mark_running(self, celery_task_id=""):
        self.status = "running"
        if celery_task_id:
            self.celery_task_id = celery_task_id
        if not self.started_at:
            self.started_at = timezone.now()
        self.save(update_fields=["status", "celery_task_id", "started_at", "updated_at"])

    def mark_finished(self, status="completed", result=None, error_message=""):
        self.status = status
        self.result = result or self.result
        self.error_message = error_message
        self.finished_at = timezone.now()
        if status == "completed":
            self.progress = 100
        self.save(update_fields=["status", "result", "error_message", "finished_at", "progress", "updated_at"])


class ModelProvider(models.Model):
    """Configurable model provider used by ModelGateway."""

    PROVIDER_TYPES = [
        ("one_api", "OneAPI"),
        ("openai_compatible", "OpenAI compatible"),
        ("local", "Local OpenAI-compatible"),
    ]

    name = models.CharField(max_length=128, unique=True)
    provider_type = models.CharField(max_length=64, choices=PROVIDER_TYPES, default="one_api")
    base_url = models.URLField(blank=True, default="")
    api_key_env = models.CharField(max_length=128, blank=True, default="")
    default_model = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "model_provider"
        indexes = [
            models.Index(fields=["provider_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"
