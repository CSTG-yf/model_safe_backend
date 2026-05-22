from django.urls import path

from .views import (
    AttackStrategyListAPIView,
    RedTeamAttemptListAPIView,
    RedTeamRunAPIView,
    RedTeamRunDetailAPIView,
    StrategyStatListAPIView,
)


urlpatterns = [
    path("runs/", RedTeamRunAPIView.as_view(), name="redteam-runs"),
    path("runs/<int:run_id>/", RedTeamRunDetailAPIView.as_view(), name="redteam-run-detail"),
    path("runs/<int:run_id>/attempts/", RedTeamAttemptListAPIView.as_view(), name="redteam-attempts"),
    path("strategies/", AttackStrategyListAPIView.as_view(), name="redteam-strategies"),
    path("strategy-stats/", StrategyStatListAPIView.as_view(), name="redteam-strategy-stats"),
]

