from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from jailbreak_evaluation.utils import JailbreakService
from model_evaluation.models import OverallResult
from model_evaluation.serializers import OverallResultSerializer
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
    # GET /api/report-generation/reports/evaluation-info/?project_id=<project_id>
    def get_evaluation_info(self, request):
        """获取项目的所有评估内容"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            raise ValidationError({'project_id': 'This parameter is required'})

        project = self._get_project(request.user, project_id)

        # 获取模型评估信息
        overall_results = OverallResult.objects.filter(project=project).order_by("-created_at")
        serializer = OverallResultSerializer(overall_results, many=True)
        model_evaluation_overall_results = serializer.data
        # 获取越狱评估信息
        jailbreak_evaluation_overall_result = JailbreakService.get_all_session_by_project_id(project_id)

        # 处理task_ids
        task_ids_info = []

        # 添加模型评估的task_ids
        for result in model_evaluation_overall_results:
            if 'id' in result:
                task_ids_info.append({
                    'task_id': result['task_id'],
                    'name': result['name'],
                    'source': 'model_evaluation',
                })

        # 添加越狱评估的task_ids
        for result in jailbreak_evaluation_overall_result:
            task_ids_info.append({
                'task_id': result['task_id'],
                'name': result['task_id'],
                'source': 'jailbreak_evaluation'
            })

        return Response({
            'project_id': project_id,
            'result': task_ids_info,
        },status=status.HTTP_200_OK)

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
        """创建新报告（通过JSON body传project_id和overall_id）"""
        project_id = request.data.get('project_id')
        overall_id = request.data.get('overall_id')  # 新增字段
        focus_metrics = request.data.get('focus_metrics')

        # 参数校验
        if not project_id:
            raise ValidationError({'project_id': 'This field is required'})
        if not overall_id:
            raise ValidationError({'overall_id': 'This field is required'})

        report_generator = ReportGenerator()
        pdf_path, report_detail = report_generator.generate_report(project_id, overall_id, focus_metrics)

        return Response({
            "result":"success",
            "pdf_url": pdf_path,
            "report_detail": report_detail,
            "message": "报告生成成功"
        }, status=status.HTTP_200_OK)


class ReportDetailAPIView(APIView):
    """报告详情操作接口"""
    permission_classes = [permissions.IsAuthenticated]

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
