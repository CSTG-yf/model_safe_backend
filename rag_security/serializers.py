from rest_framework import serializers

from .models import RagDocument, RagEvalCase, RagKnowledgeBase


class RagDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RagDocument
        fields = [
            "id",
            "knowledge_base",
            "title",
            "content",
            "document_type",
            "trust_level",
            "access_scope",
            "is_poisoned",
            "contains_injection",
            "injection_type",
            "poison_goal",
            "metadata",
            "vector_id",
            "embedding_model",
            "index_status",
            "indexed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["vector_id", "embedding_model", "index_status", "indexed_at", "created_at", "updated_at"]


class RagKnowledgeBaseSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RagKnowledgeBase
        fields = [
            "id",
            "project",
            "name",
            "description",
            "metadata",
            "document_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class RagEvalCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RagEvalCase
        fields = [
            "id",
            "run",
            "knowledge_base",
            "question",
            "expected_answer",
            "target_poison_goal",
            "retrieved_docs",
            "final_answer",
            "judge_output",
            "pollution_hit",
            "pollution_adopted",
            "sensitive_doc_hit",
            "sensitive_leak",
            "trace_id",
            "metadata",
            "created_at",
            "updated_at",
        ]

