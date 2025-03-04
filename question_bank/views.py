from rest_framework import viewsets
from rest_framework.decorators import action
from .models import MasterQuestion, EvaluationQuestionBank
from .serializers import MasterQuestionSerializer, EvaluationQuestionBankSerializer
from .services import (
    preview_generated_questions,
    add_generated_questions,
    add_master_questions,
    generate_from_master
)

class MasterQuestionViewSet(viewsets.ModelViewSet):
    queryset = MasterQuestion.objects.all()
    serializer_class = MasterQuestionSerializer


class EvaluationQuestionBankViewSet(viewsets.ModelViewSet):
    queryset = EvaluationQuestionBank.objects.all()
    serializer_class = EvaluationQuestionBankSerializer

    @action(detail=True, methods=['post'], url_path='preview-generated-questions')
    def preview_questions(self, request, pk=None):
        return preview_generated_questions(request, self.get_object())

    @action(detail=True, methods=['post'], url_path='add-generated-questions')
    def add_ai_questions(self, request, pk=None):
        return add_generated_questions(request, self.get_object())

    @action(detail=True, methods=['post'], url_path='add-master-questions')
    def add_questions_from_master(self, request, pk=None):
        return add_master_questions(request, self.get_object())

    @action(detail=True, methods=['post'], url_path='generate-from-master')
    def generate_questions(self, request, pk=None):
        return generate_from_master(request, self.get_object())
