from django.urls import path

from .views import (
    RecommendationAcceptAPIView,
    RecommendationListAPIView,
    RegressionCompareAPIView,
    RegressionRunAPIView,
    RegressionSetAPIView,
)


urlpatterns = [
    path("recommendations/", RecommendationListAPIView.as_view(), name="mitigation-recommendations"),
    path("recommendations/<int:recommendation_id>/accept/", RecommendationAcceptAPIView.as_view(), name="mitigation-accept"),
    path("regression/sets/", RegressionSetAPIView.as_view(), name="regression-sets"),
    path("regression/runs/", RegressionRunAPIView.as_view(), name="regression-runs"),
    path("regression/runs/<int:run_id>/compare/", RegressionCompareAPIView.as_view(), name="regression-compare"),
]

