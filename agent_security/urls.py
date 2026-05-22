from django.urls import path

from .views import (
    AgentEvalRunAPIView,
    AgentEvalRunDetailAPIView,
    AgentToolAPIView,
    AgentToolCallAPIView,
    SeedAgentToolsAPIView,
    ToolPolicyCheckAPIView,
)

urlpatterns = [
    path("tools/", AgentToolAPIView.as_view(), name="agent-tools"),
    path("tools/seed-defaults/", SeedAgentToolsAPIView.as_view(), name="agent-tools-seed"),
    path("policy-check/", ToolPolicyCheckAPIView.as_view(), name="agent-policy-check"),
    path("eval-runs/", AgentEvalRunAPIView.as_view(), name="agent-eval-runs"),
    path("eval-runs/<int:run_id>/", AgentEvalRunDetailAPIView.as_view(), name="agent-eval-run-detail"),
    path("tool-calls/", AgentToolCallAPIView.as_view(), name="agent-tool-calls"),
]
