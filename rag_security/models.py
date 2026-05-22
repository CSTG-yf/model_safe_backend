from django.db import models

from model_evaluation.models import EvaluationRun
from projects.models import Project


class RagKnowledgeBase(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="rag_knowledge_bases")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_knowledge_base"
        unique_together = ("project", "name")
        indexes = [
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        return f"{self.project_id}:{self.name}"


class RagDocument(models.Model):
    DOCUMENT_TYPES = [
        ("normal", "Normal"),
        ("poisoned", "Poisoned"),
        ("sensitive", "Sensitive"),
    ]
    TRUST_LEVELS = [
        ("trusted", "Trusted"),
        ("normal", "Normal"),
        ("untrusted", "Untrusted"),
        ("blocked", "Blocked"),
    ]
    INDEX_STATUS = [
        ("not_indexed", "Not indexed"),
        ("indexed", "Indexed"),
        ("failed", "Failed"),
    ]

    knowledge_base = models.ForeignKey(RagKnowledgeBase, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    content = models.TextField()
    document_type = models.CharField(max_length=32, choices=DOCUMENT_TYPES, default="normal")
    trust_level = models.CharField(max_length=32, choices=TRUST_LEVELS, default="normal")
    access_scope = models.CharField(max_length=128, blank=True, default="")
    is_poisoned = models.BooleanField(default=False)
    contains_injection = models.BooleanField(default=False)
    injection_type = models.CharField(max_length=64, blank=True, default="")
    poison_goal = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    vector_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    embedding_model = models.CharField(max_length=255, blank=True, default="")
    index_status = models.CharField(max_length=32, choices=INDEX_STATUS, default="not_indexed")
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_document"
        indexes = [
            models.Index(fields=["knowledge_base", "document_type"]),
            models.Index(fields=["knowledge_base", "trust_level"]),
            models.Index(fields=["is_poisoned", "contains_injection"]),
        ]

    def __str__(self):
        return f"{self.knowledge_base_id}:{self.title}"


class RagEvalCase(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="rag_eval_cases")
    knowledge_base = models.ForeignKey(RagKnowledgeBase, on_delete=models.CASCADE, related_name="eval_cases")
    question = models.TextField()
    expected_answer = models.TextField(blank=True, default="")
    target_poison_goal = models.TextField(blank=True, default="")
    retrieved_docs = models.JSONField(default=list, blank=True)
    final_answer = models.TextField(blank=True, default="")
    judge_output = models.JSONField(default=dict, blank=True)
    pollution_hit = models.BooleanField(default=False)
    pollution_adopted = models.BooleanField(default=False)
    sensitive_doc_hit = models.BooleanField(default=False)
    sensitive_leak = models.BooleanField(default=False)
    trace_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rag_eval_case"
        indexes = [
            models.Index(fields=["run", "pollution_adopted"]),
            models.Index(fields=["knowledge_base", "created_at"]),
            models.Index(fields=["trace_id"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.question[:50]}"

