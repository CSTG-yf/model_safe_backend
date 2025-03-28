from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'score-records', views.ScoreHistoryViewSet, basename='score-records')
# router.register(r'iteration-records', views.IterationRecordViewSet, basename='iteration-records')

urlpatterns = [
    path('', include(router.urls)),
    # 启动工作流
    path('workflow-start/', views.StartWorkflowAPI.as_view(), name='start_workflow'),
]

