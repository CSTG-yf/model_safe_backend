from django.urls import include, path

urlpatterns = [
    path('question-bank/', include('question_bank.urls')),  # 题库管理 API
    path('model-evaluation/', include('model_evaluation.urls')),
    path('jailbreak-evaluation/', include('jailbreak_evaluation.urls')),
    path('report-generation/', include('report_generation.urls')),
    path("users/", include("users.urls")),
    path('projects/', include('projects.urls')),

]
