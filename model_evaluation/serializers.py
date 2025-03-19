from django.core import serializers

from .models import EvaluationBatch, EvaluationRecord

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