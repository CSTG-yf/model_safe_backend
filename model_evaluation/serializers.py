# model_evaluation/serializers.py

from rest_framework import serializers
from .models import EvaluationBatch, ModelEvalMetrics, OverallResult

class EvaluationBatchSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source='project.id')

    class Meta:
        model = EvaluationBatch
        fields = [
            'id',
            'name',
            'description',
            'is_reviewed',
            'project_id',
            'model_name',
            'evaluator_model_name',
            'total_samples',
            'total_tokens',
            'average_score',
            'created_at'
        ]

class SimpleEvaluationBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationBatch
        fields = [
            'name',
            'description',
            'is_reviewed',
            'created_at'
        ]

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
            'created_at'
        ]
class OverallResultBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverallResult
        fields = ['id', 'name', 'description','created_at']  # 仅包含基本字段