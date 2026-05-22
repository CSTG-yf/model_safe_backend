from django.urls import path

from .views import (
    DocumentAPIView,
    KnowledgeBaseAPIView,
    RagEvalRunAPIView,
    RagEvalRunDetailAPIView,
    SeedDemoDocumentsAPIView,
    SyncChromaAPIView,
)


urlpatterns = [
    path("knowledge-bases/", KnowledgeBaseAPIView.as_view(), name="rag-knowledge-bases"),
    path("documents/", DocumentAPIView.as_view(), name="rag-documents"),
    path("seed-demo-documents/", SeedDemoDocumentsAPIView.as_view(), name="rag-seed-demo-documents"),
    path("knowledge-bases/<int:knowledge_base_id>/sync-chroma/", SyncChromaAPIView.as_view(), name="rag-sync-chroma"),
    path("eval-runs/", RagEvalRunAPIView.as_view(), name="rag-eval-runs"),
    path("eval-runs/<int:run_id>/", RagEvalRunDetailAPIView.as_view(), name="rag-eval-run-detail"),
]

