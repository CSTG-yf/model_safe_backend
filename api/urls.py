from django.urls import include, path

urlpatterns = [
    path('question-bank/', include('question_bank.urls')),  # 题库管理 API
    # path('model-testing/', include('model_testing.urls')),  # AI 测试 API
    # path('model-evaluation/', include('model_evaluation.urls')),  # 评估 API（预留）
    path('jailbreak-evaluation/', include('jailbreak_evaluation.urls')),
    # path('report-generation/', include('report_generation.urls')),  # 报告 API（预留）
    path("users/", include("users.urls")),
    path('projects/', include('projects.urls')),

]
