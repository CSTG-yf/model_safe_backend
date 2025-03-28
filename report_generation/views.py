from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .models import Report
from projects.models import Project
from .serializers import (
    ReportListSerializer,
    ReportDetailSerializer,
    ReportCreateUpdateSerializer
)
from .utils import ReportGenerator


class ReportGenerationAPIView(APIView):
    """报告生成主接口 (支持query和body传project_id)"""
    permission_classes = [permissions.AllowAny]

    def _get_project(self, user, project_id):
        """获取项目并验证权限"""
        return get_object_or_404(
            Project,
            id=project_id,
            created_by=user
        )

    # GET /api/report-generation/reports/?project_id=<project_id>
    def get(self, request):
        """获取项目报告列表（通过query参数传project_id）"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            raise ValidationError({'project_id': 'This parameter is required'})

        project = self._get_project(request.user, project_id)
        reports = Report.objects.filter(project=project)
        serializer = ReportListSerializer(reports, many=True)
        return Response({
            'project_id': project_id,
            'reports': serializer.data
        })

    # POST /api/report-generation/reports/
    def post(self, request):
        """创建新报告（通过JSON body传project_id）"""
        project_id = request.data.get('project_id')
        task_ids =request.data.get('task_ids')
        focus_metrics = request.data.get('focus_metrics')
        #
        if not project_id:
            raise ValidationError({'project_id': 'This field is required'})

        project = self._get_project(request.user, project_id)
        report_generator = ReportGenerator()
        report = report_generator.generate_report(project_id, task_ids,focus_metrics)

        return Response({"result":report,"message":"报告生成成功"}, status=status.HTTP_200_OK)


class ReportDetailAPIView(APIView):
    """报告详情操作接口"""
    permission_classes = [permissions.AllowAny]

    def _get_report(self, user, report_id):
        return get_object_or_404(
            Report,
            id=report_id,
            project__created_by=user
        )

    # GET /api/report-generation/report/<report_id>/
    def get(self, request, report_id):
        """获取报告详情"""
        report = self._get_report(request.user, report_id)
        serializer = ReportDetailSerializer(report)
        return Response(serializer.data)

    # PUT /api/report-generation/report/<report_id>/
    def put(self, request, report_id):
        """更新报告（全量/部分更新）"""
        report = self._get_report(request.user, report_id)

        # 允许部分更新
        serializer = ReportCreateUpdateSerializer(
            report,
            data=request.data,
            partial=True  # 关键修改：允许部分更新
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ReportDetailSerializer(report).data)

    # DELETE /api/report-generation/report/<report_id>/
    def delete(self, request, report_id):
        """删除报告"""
        report = self._get_report(request.user, report_id)
        report.delete()
        return Response(
            {"detail": "Report deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
