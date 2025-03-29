# model_evaluation/serializers.py

from rest_framework import serializers
from .models import EvaluationBatch, ModelEvalMetrics, OverallResult,EvaluationRecord

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