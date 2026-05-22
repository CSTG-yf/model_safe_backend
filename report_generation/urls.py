from django.urls import path
from .views import CompetitionPackageAPIView, ReportDiagnosticDataAPIView, ReportGenerationAPIView, ReportDetailAPIView

urlpatterns = [
    # 项目报告集合操作
    path(
        'reports/',
        ReportGenerationAPIView.as_view(),
        name='report-generation-list'
    ),
    # 单个报告操作
    path(
        'report/<int:report_id>/',
        ReportDetailAPIView.as_view(),
        name='report-generation-detail'
    ),
    path(
        'diagnostic-data/',
        ReportDiagnosticDataAPIView.as_view(),
        name='report-diagnostic-data'
    ),
    path(
        'competition-package/',
        CompetitionPackageAPIView.as_view(),
        name='report-competition-package'
    ),
]
