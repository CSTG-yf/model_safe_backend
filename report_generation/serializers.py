from rest_framework import serializers
from .models import Report
from projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "ai_model_name"]


class ReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "report_name", "created_at", "pdf_file"]


class ReportDetailSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Report
        fields = "__all__"


class ReportCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["report_name", "report_detail"]
        extra_kwargs = {
            "report_name": {"required": True},
            "report_detail": {"required": False}
        }
