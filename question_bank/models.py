from django.db import models
from projects.models import Project

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

    def __str__(self):
        return self.question[:20]  # 返回前20个字符

class EvalQuestions(models.Model):
    """
    观测题库模型
    """
    question_bank_id = models.AutoField(primary_key=True)  # 自动递增主键
    exam_title = models.CharField(max_length=255)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间，默认当前时间
    questions = models.JSONField()  # 题目内容，使用 JSON 字段
# questions 示例：
# [
#     {
#         "question_id": 1  
#         "source": "security-bank",
#         "content_type": "",
#         "question_type": "",
#         "question": "问题"
#         "options": ["选项A", "选项B"],
#         "answer": "正确答案",
#         "scoring_criteria": "评分标准"
#     },
#     {
#         "question_id": 2
#         "source": "llm",
#         "content_type": "",
#         "question_type": "",
#         "question": "问题"
#         "options": ["选项A", "选项B"],
#         "answer": "正确答案",
#         "scoring_criteria": "评分标准"
#     }
# ]
    def __str__(self):
        return f"Exam ID: {self.question_bank_id}, Project ID: {self.project_id}"