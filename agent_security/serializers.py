from rest_framework import serializers

from .models import AgentTool, AgentToolCall


class AgentToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTool
        fields = [
            "id",
            "project",
            "name",
            "display_name",
            "description",
            "tool_type",
            "risk_level",
            "allowed_roles",
            "parameter_schema",
            "requires_confirmation",
            "enabled",
            "policy",
            "metadata",
            "created_at",
            "updated_at",
        ]


class AgentToolCallSerializer(serializers.ModelSerializer):
    tool_display_name = serializers.CharField(source="tool.display_name", read_only=True)

    class Meta:
        model = AgentToolCall
        fields = [
            "id",
            "project",
            "run",
            "tool",
            "tool_display_name",
            "trace_id",
            "case_id",
            "prompt",
            "planned_tool_name",
            "arguments",
            "user_role",
            "decision",
            "blocked_reason",
            "risk_code",
            "risk_level",
            "simulated_result",
            "policy_snapshot",
            "metadata",
            "created_at",
        ]
