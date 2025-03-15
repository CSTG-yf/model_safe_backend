from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EvaluationQuestionsViewSet

router = DefaultRouter()
router.register(r'eval_questions', EvaluationQuestionsViewSet, basename='master-questions')


urlpatterns = [
    path('', include(router.urls)),
]
