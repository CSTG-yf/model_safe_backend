from django.urls import path
from .views import EvaluationCreateView, EvaluationRunView, EvaluationListView, OverallResultView, \
    OverallResultListView, EvaluationDetailView, EvaluationReviewView, EvaluationRecordDetailView,EvaluationProgressView

urlpatterns = [
    # 创建评测记录
    path("create/",EvaluationCreateView.as_view(),name="evaluation-create",),

    # 执行评测任务
    path("<int:evaluation_id>/run/",EvaluationRunView.as_view(),name="evaluation-run",),

    # 获取评测记录列表
    path("list/",EvaluationListView.as_view(),name="evaluation-list",),

    # 获取评测记录详情/修改/删除
    path("<int:evaluation_id>/detail/", EvaluationDetailView.as_view(), name="evaluation-detail"),

    # 评测审核接口
    path("<int:evaluation_id>/review/", EvaluationReviewView.as_view(), name="evaluation-review"),

    # 题目操作接口
    path("records/<str:record_id>/", EvaluationRecordDetailView.as_view(), name="evaluation-record-detail"),

    # 获取项目评估结果列表 (GET /overall-results/?project_id=<project_id>)
    path("overall-results/", OverallResultListView.as_view(), name="overall-result-list"),

    # 创建新的模型评估 (POST /overall-result/)
    path("overall-result/", OverallResultView.as_view(), name="overall-result-create"),
    # 获取单个评估结果详情 (GET /overall-result/<pk>/)
    # 更新评估结果名称 (PUT /overall-result/<pk>/)
    path("overall-result/<int:pk>/", OverallResultView.as_view(), name="overall-result-detail"),

    path('<int:project_id>/progress/', EvaluationProgressView.as_view(), name='evaluation_progress'),
]
