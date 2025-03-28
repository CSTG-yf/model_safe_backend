from .models import *
from rest_framework import serializers

class ScoreRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreRecord
        fields = '__all__'

# class IterationRecordSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = IterationRecord
#         fields = '__all__'