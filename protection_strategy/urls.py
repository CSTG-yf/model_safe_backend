from django.urls import path

from .views import (
    ProtectionStrategyActivateAPIView,
    ProtectionStrategyCompileAPIView,
    ProtectionStrategyDetailAPIView,
    ProtectionStrategyExportAPIView,
    ProtectionStrategyGenerateAPIView,
    ProtectionStrategyListAPIView,
)

urlpatterns = [
    path("", ProtectionStrategyListAPIView.as_view(), name="protection-strategy-list"),
    path("generate/", ProtectionStrategyGenerateAPIView.as_view(), name="protection-strategy-generate"),
    path("compile/", ProtectionStrategyCompileAPIView.as_view(), name="protection-strategy-compile"),
    path("<int:strategy_id>/", ProtectionStrategyDetailAPIView.as_view(), name="protection-strategy-detail"),
    path("<int:strategy_id>/activate/", ProtectionStrategyActivateAPIView.as_view(), name="protection-strategy-activate"),
    path("<int:strategy_id>/export/", ProtectionStrategyExportAPIView.as_view(), name="protection-strategy-export"),
]
