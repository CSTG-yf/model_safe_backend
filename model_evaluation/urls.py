from django.urls import path
from .views import EvaluationCreateView, EvaluationRunView, EvaluationListView, OverallResultRunView, OverallResultListView, OverallResultRecordView

urlpatterns = [
    # 创建评测记录
    path("create/",EvaluationCreateView.as_view(),name="evaluation-create",),

    # 执行评测任务
    path("<int:evaluation_id>/run/",EvaluationRunView.as_view(),name="evaluation-run",),

    # 获取评测记录列表
    path("list/",EvaluationListView.as_view(),name="evaluation-list",),

    # 模型评估（GET: 触发评估, POST: 修改评估名称）
    path("overall-result/run/", OverallResultRunView.as_view(), name="overall-result-run"),

    # 获取项目模型评估结果列表
    path('overall-results/', OverallResultListView.as_view(), name='overall-result-list'),

    # 获取模型评估结果记录
    path('overall-result/<int:overall_result_id>/', OverallResultRecordView.as_view(), name='overall-result-record'),
]
