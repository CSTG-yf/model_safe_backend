from django.db import models
from django.utils import timezone


class ModelAPI(models.Model):
    """
    存储模型API的相关信息
    """
    name = models.CharField(max_length=100, unique=True, help_text="模型名称")
    api_key = models.CharField(max_length=255, help_text="API密钥")
    base_url = models.URLField(help_text="API基础URL")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} API Configuration"

    class Meta:
        verbose_name = "Model API Configuration"
        verbose_name_plural = "Model API Configurations"


class ModelEvaluationHALUCINATION_TOXICITY(models.Model):
    model_name = models.CharField(max_length=100, help_text="Name of the evaluated model")
    hallucination_accuracy = models.FloatField(null=True, blank=True,
                                               help_text="Accuracy score for hallucination detection")
    toxicity_accuracy = models.FloatField(null=True, blank=True, help_text="Accuracy score for toxicity detection")

    def __str__(self):
        return f"{self.model_name} evaluation"

    class Meta:
        verbose_name = "Model Evaluation Result"
        verbose_name_plural = "Model Evaluation Results"



class EvaluationBatch(models.Model):
    """
    记录一个批次的最终评估结果
    """
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=255, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    total_tokens = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Batch {self.id}: {self.name or 'Unnamed'} ({self.created_at.strftime('%Y-%m-%d')})"

class EvaluationRecord(models.Model):
    """
    记录每一次评估结果
    """
    batch = models.ForeignKey(EvaluationBatch, on_delete=models.CASCADE, related_name='records')
    record_id = models.CharField(max_length=255)
    input = models.TextField()
    output = models.TextField()
    score = models.FloatField()
    tokens = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['record_id']),
            models.Index(fields=['score']),
        ]

    def __str__(self):
        return f"Record {self.record_id} (Score: {self.score})"
