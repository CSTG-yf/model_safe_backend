from django.urls import path
from .views import EvaluationCreateView, EvaluationRunView, EvaluationListView

urlpatterns = [
    # 创建评测记录
    path("create/",EvaluationCreateView.as_view(),name="evaluation-create",),

    # 执行评测任务
    path("<int:evaluation_id>/run/",EvaluationRunView.as_view(),name="evaluation-run",),

    # 获取评测记录列表
    path("list/",EvaluationListView.as_view(),name="evaluation-list",),
]
