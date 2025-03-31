from django.db import models
from django.utils import timezone
from projects.models import Project


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