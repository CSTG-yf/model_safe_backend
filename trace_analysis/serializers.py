from rest_framework import serializers

from .models import AppTrace, TraceRisk, TraceStep


class TraceRiskSerializer(serializers.ModelSerializer):
    step_position = serializers.IntegerField(source="step.position", read_only=True)
    step_type = serializers.CharField(source="step.step_type", read_only=True)

    class Meta:
        model = TraceRisk
        fields = [
            "id",
            "trace",
            "step",
            "step_position",
            "step_type",
            "risk_code",
            "risk_name",
            "risk_level",
            "evidence",
            "reason",
            "mitigation_hint",
            "confidence",
            "metadata",
            "created_at",
        ]


class TraceStepSerializer(serializers.ModelSerializer):
    risks = TraceRiskSerializer(many=True, read_only=True)

    class Meta:
        model = TraceStep
        fields = [
            "id",
            "trace",
            "step_type",
            "name",
            "input_payload",
            "output_payload",
            "metadata",
            "position",
            "risks",
            "created_at",
        ]


class AppTraceSerializer(serializers.ModelSerializer):
    steps = TraceStepSerializer(many=True, read_only=True)
    risks = TraceRiskSerializer(many=True, read_only=True)

    class Meta:
        model = AppTrace
        fields = [
            "id",
            "project",
            "run",
            "trace_id",
            "scenario_type",
            "input_text",
            "final_output",
            "risk_level",
            "metadata",
            "steps",
            "risks",
            "created_at",
            "updated_at",
        ]


class AppTraceListSerializer(serializers.ModelSerializer):
    risk_count = serializers.IntegerField(read_only=True)
    step_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AppTrace
        fields = [
            "id",
            "project",
            "run",
            "trace_id",
            "scenario_type",
            "input_text",
            "final_output",
            "risk_level",
            "risk_count",
            "step_count",
            "created_at",
            "updated_at",
        ]

