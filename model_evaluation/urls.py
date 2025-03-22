# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 评估任务相关
    path('tasks/', views.EvaluationTaskView.as_view(), name='evaluation_tasks'),
    path('tasks/<str:task_id>/', views.EvaluationTaskView.as_view(), name='evaluation_task_detail'),
    
    # 评估记录相关
    path('records/<str:record_id>/', views.EvaluationRecordView.as_view(), name='evaluation_record'),
    
    # 模型配置相关
    path('models/', views.ModelAPIView.as_view(), name='model_api_list'),
    path('models/<str:model_name>/', views.ModelAPIView.as_view(), name='model_api_detail'),
    
    # 模型评估结果相关
    path('models/<str:model_name>/results/', views.get_evaluation_halucination_toxicity, name='get_model_evaluation'),
    path('models/<str:model_name>/evaluate/', views.trigger_evaluation_halucination_toxicity, name='trigger_evaluation'),
]