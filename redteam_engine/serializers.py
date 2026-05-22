from rest_framework import serializers

from .models import AttackStrategy, RedTeamAttempt, StrategyStat


class AttackStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttackStrategy
        fields = [
            "id",
            "code",
            "name",
            "category",
            "description",
            "prompt_template",
            "applicable_risks",
            "enabled",
            "metadata",
            "created_at",
            "updated_at",
        ]


class RedTeamAttemptSerializer(serializers.ModelSerializer):
    strategy_code = serializers.CharField(source="strategy.code", read_only=True)
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)

    class Meta:
        model = RedTeamAttempt
        fields = [
            "id",
            "run",
            "case",
            "strategy",
            "strategy_code",
            "strategy_name",
            "parent_attempt",
            "trace_id",
            "target_risk_code",
            "objective",
            "prompt",
            "response",
            "score",
            "risk_level",
            "judge_output",
            "success",
            "latency_ms",
            "selection_reason",
            "token_usage",
            "created_at",
        ]


class StrategyStatSerializer(serializers.ModelSerializer):
    strategy_code = serializers.CharField(source="strategy.code", read_only=True)
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    success_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = StrategyStat
        fields = [
            "id",
            "strategy",
            "strategy_code",
            "strategy_name",
            "risk_code",
            "attempts",
            "successes",
            "success_rate",
            "average_score",
            "average_latency_ms",
            "novelty_score",
            "updated_at",
        ]

