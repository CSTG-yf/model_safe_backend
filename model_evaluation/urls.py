from django.urls import path
from .views import EvaluationCreateView, EvaluationRunView, EvaluationListView, OverallResultView, OverallResultListView

urlpatterns = [
    # 创建评测记录
    path("create/",EvaluationCreateView.as_view(),name="evaluation-create",),

    # 执行评测任务
    path("<int:evaluation_id>/run/",EvaluationRunView.as_view(),name="evaluation-run",),

    # 获取评测记录列表
    path("list/",EvaluationListView.as_view(),name="evaluation-list",),

    # 获取项目评估结果列表 (GET /overall-results/?project_id=<project_id>)
    path("overall-results/", OverallResultListView.as_view(), name="overall-result-list"),

    # 创建新的模型评估 (POST /overall-result/)
    path("overall-result/", OverallResultView.as_view(), name="overall-result-create"),

    # 获取单个评估结果详情 (GET /overall-result/<pk>/)
    # 更新评估结果名称 (PUT /overall-result/<pk>/)
    path("overall-result/<int:pk>/", OverallResultView.as_view(), name="overall-result-detail"),

]
