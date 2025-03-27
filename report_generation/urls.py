from django.urls import path
from .views import ReportGenerationAPIView, ReportDetailAPIView

urlpatterns = [
    # 项目报告集合操作
    path(
        'report-generation/reports/',
        ReportGenerationAPIView.as_view(),
        name='report-generation-list'
    ),
    # 单个报告操作
    path(
        'report-generation/report/<int:report_id>/',
        ReportDetailAPIView.as_view(),
        name='report-generation-detail'
    ),
]
