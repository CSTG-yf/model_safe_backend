from django.urls import include, path

urlpatterns = [
    path('models/', include('core.urls')),
    path('question-bank/', include('question_bank.urls')),  # 棰樺簱绠＄悊 API
    path('model-evaluation/', include('model_evaluation.urls')),
    path('jailbreak-evaluation/', include('jailbreak_evaluation.urls')),
    path('report-generation/', include('report_generation.urls')),
    path('traces/', include('trace_analysis.urls')),
    path('redteam/', include('redteam_engine.urls')),
    path('mitigation/', include('mitigation.urls')),
    path('rag-security/', include('rag_security.urls')),
    path('protection-strategies/', include('protection_strategy.urls')),
    path('agent-security/', include('agent_security.urls')),
    path("users/", include("users.urls")),
    path('projects/', include('projects.urls')),

]

