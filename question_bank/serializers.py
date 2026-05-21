from rest_framework import serializers
from .models import (
    EvalQuestions,
    Question,
    QuestionBank,
    QuestionOption,
    QuestionQualityCheck,
    QuestionRiskTag,
    SecurityQuestions,
)


class SecurityQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestions
        fields = '__all__'

class EvalQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalQuestions
        fields = ["question_bank_id", "exam_title", "description", "created_at", "questions", "project_id"]
        read_only_fields = ["project_id", "questions", "created_at"]

    def validate_exam_title(self, value):
        if value.strip() == "":
            raise serializers.ValidationError("题库名称不能为空")
        return value


class BasicEvalQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalQuestions
        fields = ["question_bank_id", "exam_title", "description"]


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "label", "content", "is_correct", "position"]


class QuestionRiskTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionRiskTag
        fields = ["id", "risk_code", "risk_name", "regulation_ref", "weight", "metadata"]


class QuestionQualityCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionQualityCheck
        fields = ["id", "check_type", "passed", "score", "message", "details", "checked_at"]


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    risk_tags = QuestionRiskTagSerializer(many=True, read_only=True)
    quality_checks = QuestionQualityCheckSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_id",
            "bank",
            "source",
            "domain",
            "subdomain",
            "question_type",
            "prompt",
            "standard_answer",
            "explanation",
            "scoring_criteria",
            "metadata",
            "position",
            "review_status",
            "options",
            "risk_tags",
            "quality_checks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["question_id", "created_at", "updated_at"]


class QuestionBankSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = QuestionBank
        fields = [
            "id",
            "legacy_bank",
            "project",
            "title",
            "description",
            "version",
            "status",
            "source",
            "created_by",
            "question_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

