import uuid

from django.db import models
from projects.models import Project


def generate_question_id():
    return uuid.uuid4().hex


class SecurityQuestions(models.Model):
    """
    安全问题模型
    """
    content_type = models.CharField(max_length=255)  # 题目内容类型
    question_type = models.CharField(max_length=255)  # 题型
    question = models.TextField()  # 题目内容
    options = models.TextField(null=True, blank=True)  # 选项（可选）
    answer = models.TextField()  # 答案
    scoring_criteria = models.TextField()  # 评分标准

    class Meta:
        db_table = "security_questions"

    def __str__(self):
        return self.question[:20]  # 返回前20个字符

class EvalQuestions(models.Model):
    """
    观测题库模型
    """
    question_bank_id = models.AutoField(primary_key=True)  # 自动递增主键
    exam_title = models.CharField(max_length=255, null=True, blank=True) #题库名称
    description = models.TextField(blank=True, null=True) #题库描述
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间，默认当前时间
    questions = models.JSONField(default=list,null=True, blank=True)  # 题目内容，使用 JSON 字段

    class Meta:
        db_table = "eval_questions"
    def __str__(self):
        return f"Exam ID: {self.question_bank_id}, Project ID: {self.project_id}"

    # questions 示例：
    # [
    #     {
    #         "question_id": 1,
    #         "source": "SecurityQuestions",
    #         "content_type": "",
    #         "question_type": "",
    #         "question": "问题"
    #         "options": ["选项A", "选项B"],
    #         "answer": "正确答案",
    #         "scoring_criteria": "评分标准"
    #     },
    #     {
    #         "question_id": 2,
    #         "source": "llm",
    #         "content_type": "",
    #         "question_type": "",
    #         "question": "问题"
    #         "options": ["选项A", "选项B"],
    #         "answer": "正确答案",
    #         "scoring_criteria": "评分标准"
    #     }
    # ]


class QuestionBank(models.Model):
    """Structured question bank used by the refactored evaluation pipeline."""

    id = models.BigAutoField(primary_key=True)
    legacy_bank = models.OneToOneField(
        EvalQuestions,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="structured_bank",
        help_text="Optional compatibility link to the legacy JSON question bank.",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="structured_question_banks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=32,
        choices=[
            ("draft", "Draft"),
            ("generating", "Generating"),
            ("ready", "Ready"),
            ("archived", "Archived"),
        ],
        default="draft",
    )
    source = models.CharField(
        max_length=32,
        choices=[
            ("manual", "Manual"),
            ("llm", "LLM"),
            ("security_seed", "Security Seed"),
            ("mixed", "Mixed"),
            ("regression", "Regression"),
        ],
        default="mixed",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_question_banks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "question_bank"
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} v{self.version}"


class Question(models.Model):
    """Single normalized question record."""

    id = models.BigAutoField(primary_key=True)
    question_id = models.CharField(max_length=64, unique=True, default=generate_question_id)
    bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name="questions")
    source = models.CharField(
        max_length=32,
        choices=[
            ("llm", "LLM"),
            ("security_seed", "Security Seed"),
            ("manual", "Manual"),
            ("regression", "Regression"),
            ("imported", "Imported"),
        ],
        default="llm",
    )
    domain = models.CharField(max_length=255, blank=True, default="")
    subdomain = models.CharField(max_length=255, blank=True, default="")
    question_type = models.CharField(max_length=64)
    prompt = models.TextField()
    standard_answer = models.TextField(blank=True, default="")
    explanation = models.TextField(blank=True, default="")
    scoring_criteria = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveIntegerField(default=0)
    review_status = models.CharField(
        max_length=32,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("needs_revision", "Needs revision"),
        ],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "question"
        ordering = ["bank_id", "position", "id"]
        indexes = [
            models.Index(fields=["bank", "question_type"]),
            models.Index(fields=["bank", "domain"]),
            models.Index(fields=["review_status"]),
        ]

    def __str__(self):
        return f"{self.question_id}: {self.prompt[:40]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=32)
    content = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "question_option"
        ordering = ["question_id", "position", "id"]
        unique_together = ("question", "label")

    def __str__(self):
        return f"{self.question.question_id} {self.label}"


class QuestionRiskTag(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="risk_tags")
    risk_code = models.CharField(max_length=128)
    risk_name = models.CharField(max_length=255)
    regulation_ref = models.CharField(max_length=255, blank=True, default="")
    weight = models.FloatField(default=1.0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "question_risk_tag"
        unique_together = ("question", "risk_code")
        indexes = [
            models.Index(fields=["risk_code"]),
            models.Index(fields=["risk_name"]),
        ]

    def __str__(self):
        return f"{self.question.question_id} -> {self.risk_code}"


class QuestionQualityCheck(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="quality_checks")
    check_type = models.CharField(max_length=64)
    passed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)
    message = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "question_quality_check"
        indexes = [
            models.Index(fields=["question", "check_type"]),
            models.Index(fields=["passed"]),
        ]

    def __str__(self):
        return f"{self.question.question_id} {self.check_type}: {self.passed}"
