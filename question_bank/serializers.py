from rest_framework import serializers
from .models import EvalQuestions, SecurityQuestions


class SecurityQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestions
        fields = '__all__'

class EvalQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalQuestions
        fields = '__all__'