from rest_framework import serializers

from .models import EvaluationBatch, EvaluationRecord, ModelAPI


class ModelAPISerializer(serializers.ModelSerializer):
    """
    模型API配置的序列化器
    """
    class Meta:
        model = ModelAPI
        fields = ['id', 'name', 'base_url', 'created_at']
        read_only_fields = ['created_at']


class EvaluationBatchSerializer(serializers.ModelSerializer):
    """
    评估批次的序列化器
    """
    class Meta:
        model = EvaluationBatch
        fields = '__all__'

class EvaluationRecordSerializer(serializers.ModelSerializer):
    """
    评估记录的详细序列化器
    """
    class Meta:
        model = EvaluationRecord
        fields = '__all__'