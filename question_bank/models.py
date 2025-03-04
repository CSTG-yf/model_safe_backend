from django.db import models


class MasterQuestion(models.Model):
    """
    总题库的题目
    """
    content = models.TextField()  # 题干
    answer = models.TextField(null=True, blank=True)  # 答案（可选）
    tags = models.CharField(max_length=255, blank=True)  # 题目标签（逗号分隔，如 "1,2,3"）
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content[:20]  # 返回前20个字符


class EvaluationQuestionBank(models.Model):
    """
    评测题库
    """
    title = models.CharField(max_length=255)  # 题库名称
    created_by = models.CharField(max_length=255, blank=True)  # 记录创建者（如果有用户系统可关联 User）
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EvaluationQuestion(models.Model):
    """
    评测题库的题目（既可以是 AI 生成，也可以是从总题库选取）
    """
    evaluation_bank = models.ForeignKey(EvaluationQuestionBank, on_delete=models.CASCADE, related_name='questions')

    content = models.TextField()  # 题干
    answer = models.TextField(null=True, blank=True)  # 参考答案（可选）

    # 题目来源：
    master_question = models.ForeignKey("MasterQuestion", on_delete=models.SET_NULL, null=True,
                                        blank=True)  # 如果是从总题库选的，记录来源

    created_at = models.DateTimeField(auto_now_add=True)
