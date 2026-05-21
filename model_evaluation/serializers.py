
# model_evaluation/serializers.py

from rest_framework import serializers
from .models import (
    EvaluationArtifact,
    EvaluationBatch,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationMetric,
    EvaluationRecord,
    EvaluationRun,
    MetricDefinition,
    MetricValue,
    ModelEvalMetrics,
    OverallResult,
)

class EvaluationDetailSerializer(serializers.ModelSerializer):
    hallucination_accuracy = serializers.SerializerMethodField()
    toxicity_accuracy = serializers.SerializerMethodField()
    records = serializers.SerializerMethodField()

    class Meta:
        model = EvaluationBatch
        fields = [
            'total_samples',    # 测试用例总数
            'average_score',    # 平均分
            'hallucination_accuracy',  # 幻觉检测准确率
            'toxicity_accuracy',       # 有害内容检测准确率
            'records'          # 所有题目记录
        ]

    def get_hallucination_accuracy(self, obj):
        try:
            metrics = ModelEvalMetrics.objects.get(model_name=obj.model_name)
            return metrics.hallucination_accuracy
        except ModelEvalMetrics.DoesNotExist:
            return None

    def get_toxicity_accuracy(self, obj):
        try:
            metrics = ModelEvalMetrics.objects.get(model_name=obj.model_name)
            return metrics.toxicity_accuracy
        except ModelEvalMetrics.DoesNotExist:
            return None

    def get_records(self, obj):
        records = EvaluationRecord.objects.filter(evaluation=obj)
        return [{
            'record_id': record.record_id,
            'input_text': {
                'question': record.input_text.get('question', ''),
                'question_type': record.input_text.get('question_type', '')
            },
            'score': record.score
        } for record in records]




class SimpleEvaluationBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationBatch
        fields = [
            'id',
            'name',
            'description',
            'is_reviewed',
            'created_at'
        ]

class EvaluationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationRecord
        fields = [
            'record_id',
            'input_text',
            'output_text',
            'content_type',
            'score',
            'tokens',
            'created_at'
        ]
        read_only_fields = ['record_id', 'created_at']  # 这些字段不允许修改


class OverallResultSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source='project.id')

    class Meta:
        model = OverallResult
        fields = [
            'id',
            'name',
            'description',
            'project_id',
            'project_score',
            'total_tokens',
            'hallucination_accuracy',
            'toxicity_accuracy',
            'total_samples',
            'jailbreak_evaluation',
            'created_at',
            'updated_at'
        ]
class OverallResultBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverallResult
        fields = ['id', 'name', 'description','created_at']  # 仅包含基本字段


class EvaluationCaseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCaseResult
        fields = [
            "id",
            "output_text",
            "judge_output",
            "score",
            "risk_level",
            "evidence",
            "tokens",
            "latency_ms",
            "error_message",
            "created_at",
            "updated_at",
        ]


class EvaluationCaseSerializer(serializers.ModelSerializer):
    result = EvaluationCaseResultSerializer(read_only=True)

    class Meta:
        model = EvaluationCase
        fields = [
            "id",
            "run",
            "question",
            "case_id",
            "input_payload",
            "expected_output",
            "scoring_criteria",
            "risk_tags",
            "position",
            "result",
            "created_at",
        ]


class EvaluationMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationMetric
        fields = ["id", "name", "value", "unit", "scope", "metadata", "created_at"]


class EvaluationArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationArtifact
        fields = ["id", "artifact_type", "name", "file", "content", "created_at"]


class EvaluationRunSerializer(serializers.ModelSerializer):
    metrics = EvaluationMetricSerializer(many=True, read_only=True)
    artifacts = EvaluationArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = EvaluationRun
        fields = [
            "id",
            "legacy_batch",
            "project",
            "question_bank",
            "name",
            "description",
            "run_type",
            "status",
            "task_id",
            "model_name",
            "evaluator_model_name",
            "model_config",
            "prompt_version",
            "question_bank_version",
            "total_cases",
            "completed_cases",
            "failed_cases",
            "average_score",
            "total_tokens",
            "progress",
            "error_message",
            "created_by",
            "started_at",
            "finished_at",
            "metrics",
            "artifacts",
            "created_at",
            "updated_at",
        ]


class MetricDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricDefinition
        fields = [
            "id",
            "code",
            "name",
            "category",
            "description",
            "unit",
            "direction",
            "default_threshold",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
        ]


class MetricValueSerializer(serializers.ModelSerializer):
    definition_code = serializers.CharField(source="definition.code", read_only=True)

    class Meta:
        model = MetricValue
        fields = [
            "id",
            "definition",
            "definition_code",
            "project",
            "run",
            "model_name",
            "risk_code",
            "value",
            "unit",
            "dimensions",
            "measured_at",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "task_id",
            "completed_cases",
            "failed_cases",
            "average_score",
            "total_tokens",
            "progress",
            "error_message",
            "created_by",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
