from rest_framework import serializers
from .models import MasterQuestion, EvaluationQuestionBank, EvaluationQuestion

class MasterQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterQuestion
        fields = '__all__'

class EvaluationQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationQuestion
        fields = '__all__'

class EvaluationQuestionBankSerializer(serializers.ModelSerializer):
    # 嵌套返回题库里的问题
    questions = EvaluationQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = EvaluationQuestionBank
        fields = '__all__'
