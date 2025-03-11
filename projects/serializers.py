from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "ai_model_name", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]
