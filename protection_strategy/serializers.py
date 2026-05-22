from rest_framework import serializers

from .models import ModelProtectionStrategy, ProtectionPolicySource, ProtectionPolicyVersion


class ProtectionPolicySourceSerializer(serializers.ModelSerializer):
    trace_id = serializers.CharField(source="trace.trace_id", read_only=True)
    risk_code = serializers.CharField(source="risk.risk_code", read_only=True)
    recommendation_title = serializers.CharField(source="recommendation.title", read_only=True)

    class Meta:
        model = ProtectionPolicySource
        fields = [
            "id",
            "policy_version",
            "source_type",
            "run",
            "trace",
            "trace_id",
            "risk",
            "risk_code",
            "recommendation",
            "recommendation_title",
            "regression_case",
            "weight",
            "metadata",
            "created_at",
        ]


class ProtectionPolicyVersionSerializer(serializers.ModelSerializer):
    sources = ProtectionPolicySourceSerializer(many=True, read_only=True)

    class Meta:
        model = ProtectionPolicyVersion
        fields = [
            "id",
            "strategy",
            "version",
            "status",
            "risk_profile",
            "guard_prompt",
            "guard_policy",
            "rag_guard_rules",
            "agent_tool_policy",
            "output_guard_rules",
            "regression_cases",
            "metrics",
            "source_summary",
            "sources",
            "created_by",
            "created_at",
            "activated_at",
        ]


class ModelProtectionStrategySerializer(serializers.ModelSerializer):
    active_version_detail = ProtectionPolicyVersionSerializer(source="active_version", read_only=True)

    class Meta:
        model = ModelProtectionStrategy
        fields = [
            "id",
            "project",
            "target_model_name",
            "name",
            "status",
            "active_version",
            "active_version_detail",
            "risk_profile",
            "metadata",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ModelProtectionStrategyDetailSerializer(ModelProtectionStrategySerializer):
    versions = ProtectionPolicyVersionSerializer(many=True, read_only=True)

    class Meta(ModelProtectionStrategySerializer.Meta):
        fields = ModelProtectionStrategySerializer.Meta.fields + ["versions"]
