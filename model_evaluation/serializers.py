from rest_framework import serializers

from .models import EvaluationBatch, EvaluationRecord, ModelAPI


class ModelAPISerializer(serializers.ModelSerializer):
    """
    模型API配置的序列化器
    """
    class Meta:
        model = ModelAPI
        fields = ['id', 'name', 'api_key', 'base_url', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        """创建时必须提供 api_key"""
        if 'api_key' not in validated_data:
            raise serializers.ValidationError({'api_key': 'API key is required when creating a model configuration'})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新时 api_key 是可选的"""
        return super().update(instance, validated_data)


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