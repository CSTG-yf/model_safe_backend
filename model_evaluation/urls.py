# urls.py
from django.urls import path
from .views import EvaluationTaskView, get_evaluation_halucination_toxicity, trigger_evaluation_halucination_toxicity, ModelAPIView

urlpatterns = [
    path('api/evaluation/task/', EvaluationTaskView.as_view(), name='evaluation_task'),
    path('api/model/<str:model_name>/', get_evaluation_halucination_toxicity, name='get_model_evaluation'),
    path('api/model/<str:model_name>/evaluate/', trigger_evaluation_halucination_toxicity, name='trigger_evaluation'),
    path('api/model-config/', ModelAPIView.as_view(), name='model_api_list'),
    path('api/model-config/<str:model_name>/', ModelAPIView.as_view(), name='model_api_detail'),
]