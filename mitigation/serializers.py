from rest_framework import serializers

from .models import (
    MitigationRecommendation,
    MitigationTemplate,
    RegressionCase,
    RegressionSet,
)


class MitigationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MitigationTemplate
        fields = "__all__"


class MitigationRecommendationSerializer(serializers.ModelSerializer):
    trace_id = serializers.CharField(source="trace.trace_id", read_only=True)

    class Meta:
        model = MitigationRecommendation
        fields = [
            "id",
            "project",
            "trace",
            "trace_id",
            "risk",
            "run",
            "template",
            "risk_code",
            "title",
            "reason",
            "steps",
            "verification_cases",
            "priority",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        ]


class RegressionCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegressionCase
        fields = [
            "id",
            "regression_set",
            "source_case_id",
            "source_attempt_id",
            "input_payload",
            "expected_safe_behavior",
            "risk_code",
            "metadata",
            "created_at",
        ]


class RegressionSetSerializer(serializers.ModelSerializer):
    cases = RegressionCaseSerializer(many=True, read_only=True)

    class Meta:
        model = RegressionSet
        fields = [
            "id",
            "project",
            "source_run",
            "name",
            "risk_codes",
            "description",
            "cases",
            "created_at",
            "updated_at",
        ]

