from django.urls import path

from .views import TraceDetailAPIView, TraceListAPIView, TraceRiskListAPIView


urlpatterns = [
    path("", TraceListAPIView.as_view(), name="trace-list"),
    path("<str:trace_id>/", TraceDetailAPIView.as_view(), name="trace-detail"),
    path("<str:trace_id>/risks/", TraceRiskListAPIView.as_view(), name="trace-risks"),
]

