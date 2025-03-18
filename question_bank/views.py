from rest_framework import viewsets
from rest_framework.decorators import action
from .models import EvalQuestions, SecurityQuestions
from .serializers import EvalQuestionsSerializer, SecurityQuestionsSerializer
from .services import (
    generated_questions_and_add_to_database,
    get_question_detail, get_security_question_detail,
)

class EvaluationQuestionsViewSet(viewsets.ModelViewSet):
    queryset = EvalQuestions.objects.all()
    serializer_class = EvalQuestionsSerializer

    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/generate-questions')
    def generated_questions(self, request,project_id=None):
        return generated_questions_and_add_to_database(request,project_id)

    @action(detail=False, methods=['get'], url_path='security-questions-details')
    def security_questions_detail(self, request):
        return get_security_question_detail()

    @action(detail=False, methods=['post'], url_path='questions-details')
    def get_question_detail(self, request):
        #根据题库id获取题库详情
       return get_question_detail(request)