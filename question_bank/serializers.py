from rest_framework import serializers
from .models import EvalQuestions, SecurityQuestions


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

