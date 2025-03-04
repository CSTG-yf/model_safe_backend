from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MasterQuestionViewSet, EvaluationQuestionBankViewSet

router = DefaultRouter()
router.register(r'master-questions', MasterQuestionViewSet, basename='master-questions')
router.register(r'evaluation-banks', EvaluationQuestionBankViewSet, basename='evaluation-banks')

urlpatterns = [
    path('', include(router.urls)),
]
