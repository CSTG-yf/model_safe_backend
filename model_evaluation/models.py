from django.db import models
from django.utils import timezone
from projects.models import Project
from question_bank.models import Question, QuestionBank


# class ModelAPI(models.Model):
#     """
#     存储模型API的相关信息
#     """
#     name = models.CharField(max_length=100, unique=True, help_text="模型名称")
#     api_key = models.CharField(max_length=255, help_text="API密钥")
#     base_url = models.URLField(help_text="API基础URL")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.name} API Configuration"

#     class Meta:
#         verbose_name = "模型API配置"
#         verbose_name_plural = "模型API配置"
#         db_table = "model_api"


class ModelEvalMetrics(models.Model):
    """
    存储模型评估指标
    """
    model_name = models.CharField(max_length=255, help_text="评估时的模型名称")
    hallucination_accuracy = models.FloatField(null=True, blank=True, help_text="幻觉检测准确率")
    toxicity_accuracy = models.FloatField(null=True, blank=True, help_text="有害内容检测准确率")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} 评估指标"

    class Meta:
        verbose_name = "模型评估指标"
        verbose_name_plural = "模型评估指标"
        db_table = "model_eval_metrics"


class EvaluationBatch(models.Model):
    """
    记录一次模型评估任务的结果
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default="未命名评估", help_text="评估任务名称")
    description = models.TextField(blank=True, null=True, help_text="评估任务说明")
    is_reviewed = models.BooleanField(default=False, help_text="是否已人工审核")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='model_evaluations')
    model_name = models.CharField(max_length=255, help_text="被评估的模型名称（项目的AI模型）")
    evaluator_model_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="执行评估的模型名称（可选）"
    )
    total_samples = models.IntegerField(default=0, help_text="评估样本总数")
    average_score = models.FloatField(default=0.0, help_text="平均评分")
    total_tokens = models.IntegerField(default=0, help_text="总token数")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        evaluator_info = f"(由 {self.evaluator_model_name} 评估)" if self.evaluator_model_name else ""
        return f"评估 {self.id}: {self.project.name} - {self.model_name} {evaluator_info}"

    def save(self, *args, **kwargs):
        # 新建记录且未手动设置模型名时，默认使用项目的模型名
        if not self.pk and (not self.model_name or self.model_name.strip() == ''):
            if self.project and self.project.ai_model_name:
                self.model_name = self.project.ai_model_name
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "模型评估"
        verbose_name_plural = "模型评估"
        db_table = "evaluation_batch"


class EvaluationRecord(models.Model):
    """
    记录每一次评估结果
    """
    evaluation = models.ForeignKey(EvaluationBatch, on_delete=models.CASCADE, related_name='records')
    record_id = models.CharField(max_length=255, unique=True, help_text="记录ID")
    input_text = models.JSONField()
    output_text = models.TextField(help_text="输出文本")
    content_type  = models.TextField(help_text="题目类型",default='')
    score = models.FloatField(help_text="评分")
    tokens = models.IntegerField(help_text="token数量")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "评估记录"
        verbose_name_plural = "评估记录"
        db_table = "evaluation_record"
        indexes = [
            models.Index(fields=['record_id']),
            models.Index(fields=['score']),
        ]

    def __str__(self):
        return f"记录 {self.record_id} (评分: {self.score})"

class OverallResult(models.Model):
    """
    记录最终的评估结果
    """
    name = models.CharField(max_length=255,blank=True,null=True, help_text="模型评估结果名称")
    description = models.TextField(blank=True, null=True, help_text="模型评估结果说明")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='overall_results')
    project_score = models.JSONField(help_text="模型评估结果的记录")
    total_tokens = models.IntegerField(default=0, help_text="总token数")
    hallucination_accuracy = models.FloatField(null=True, blank=True, help_text="幻觉检测准确率")
    toxicity_accuracy = models.FloatField(null=True, blank=True, help_text="有害内容检测准确率")
    total_samples = models.IntegerField(default=0, help_text="总样本数")
    jailbreak_evaluation = models.JSONField(null=True, blank=True,default=list,help_text="模型评估结果的记录"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "模型评估结果"
        verbose_name_plural = "模型评估结果"
        db_table = "overall_result"


    def __str__(self):
        return f"记录 {self.id} (模型评估结果: {self.project_score})"


class EvaluationRun(models.Model):
    """Unified evaluation task covering normal, jailbreak, RAG, Agent, and regression runs."""

    RUN_TYPES = [
        ("normal_eval", "Normal evaluation"),
        ("jailbreak", "Jailbreak evaluation"),
        ("rag", "RAG evaluation"),
        ("agent", "Agent evaluation"),
        ("regression", "Regression evaluation"),
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
    legacy_batch = models.OneToOneField(
        EvaluationBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unified_run",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evaluation_runs")
    question_bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluation_runs",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    run_type = models.CharField(max_length=32, choices=RUN_TYPES, default="normal_eval")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    task_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    model_name = models.CharField(max_length=255, blank=True, default="")
    evaluator_model_name = models.CharField(max_length=255, blank=True, default="")
    model_config = models.JSONField(default=dict, blank=True)
    prompt_version = models.CharField(max_length=128, blank=True, default="")
    question_bank_version = models.PositiveIntegerField(null=True, blank=True)
    total_cases = models.PositiveIntegerField(default=0)
    completed_cases = models.PositiveIntegerField(default=0)
    failed_cases = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(default=0)
    progress = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_evaluation_runs",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluation_run"
        indexes = [
            models.Index(fields=["project", "run_type", "status"]),
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["task_id"]),
        ]

    def mark_running(self, task_id=""):
        self.status = "running"
        if task_id:
            self.task_id = task_id
        if not self.started_at:
            self.started_at = timezone.now()
        self.save(update_fields=["status", "task_id", "started_at", "updated_at"])

    def mark_finished(self, status="completed", error_message=""):
        self.status = status
        self.error_message = error_message
        self.finished_at = timezone.now()
        if status == "completed":
            self.progress = 100
        self.save(update_fields=["status", "error_message", "finished_at", "progress", "updated_at"])

    def __str__(self):
        return f"{self.name} ({self.run_type}/{self.status})"


class EvaluationCase(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="cases")
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluation_cases",
    )
    case_id = models.CharField(max_length=128, db_index=True)
    input_payload = models.JSONField(default=dict, blank=True)
    expected_output = models.TextField(blank=True, default="")
    scoring_criteria = models.JSONField(default=dict, blank=True)
    risk_tags = models.JSONField(default=list, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation_case"
        unique_together = ("run", "case_id")
        ordering = ["run_id", "position", "id"]
        indexes = [
            models.Index(fields=["run", "case_id"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.case_id}"


class EvaluationCaseResult(models.Model):
    case = models.OneToOneField(EvaluationCase, on_delete=models.CASCADE, related_name="result")
    output_text = models.TextField(blank=True, default="")
    judge_output = models.JSONField(default=dict, blank=True)
    score = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=32, blank=True, default="")
    evidence = models.JSONField(default=list, blank=True)
    tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluation_case_result"
        indexes = [
            models.Index(fields=["score"]),
            models.Index(fields=["risk_level"]),
        ]

    def __str__(self):
        return f"{self.case.case_id}: {self.score}"


class EvaluationMetric(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="metrics")
    name = models.CharField(max_length=128)
    value = models.FloatField()
    unit = models.CharField(max_length=64, blank=True, default="")
    scope = models.CharField(max_length=128, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation_metric"
        unique_together = ("run", "name", "scope")
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["run", "name"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.name}={self.value}"


class EvaluationArtifact(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="evaluation_artifacts/%Y/%m/%d/", blank=True, null=True)
    content = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evaluation_artifact"
        indexes = [
            models.Index(fields=["run", "artifact_type"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.artifact_type}:{self.name}"


class MetricDefinition(models.Model):
    """Reusable metric definition for dashboards, reports, and experiments."""

    DIRECTION_CHOICES = [
        ("higher_better", "Higher is better"),
        ("lower_better", "Lower is better"),
        ("neutral", "Neutral"),
    ]

    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="")
    unit = models.CharField(max_length=64, blank=True, default="")
    direction = models.CharField(max_length=32, choices=DIRECTION_CHOICES, default="neutral")
    default_threshold = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metric_definition"
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"


class MetricValue(models.Model):
    """Metric value scoped to a project, model, run, risk type, or time window."""

    definition = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="values")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="metric_values")
    run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metric_values",
    )
    model_name = models.CharField(max_length=255, blank=True, default="")
    risk_code = models.CharField(max_length=128, blank=True, default="")
    value = models.FloatField()
    unit = models.CharField(max_length=64, blank=True, default="")
    dimensions = models.JSONField(default=dict, blank=True)
    measured_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "metric_value"
        indexes = [
            models.Index(fields=["project", "measured_at"]),
            models.Index(fields=["definition", "model_name"]),
            models.Index(fields=["risk_code"]),
        ]

    def __str__(self):
        return f"{self.definition.code}={self.value}"
