from django.db.models import Count
from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response

from .models import AppTrace
from .serializers import AppTraceListSerializer, AppTraceSerializer, TraceRiskSerializer


class TraceListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=status.HTTP_400_BAD_REQUEST)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error

        queryset = (
            AppTrace.objects.filter(project=project)
            .annotate(risk_count=Count("risks", distinct=True), step_count=Count("steps", distinct=True))
            .order_by("-created_at")
        )
        scenario_type = request.query_params.get("scenario_type")
        risk_level = request.query_params.get("risk_level")
        run_id = request.query_params.get("run_id")
        if scenario_type:
            queryset = queryset.filter(scenario_type=scenario_type)
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        if run_id:
            queryset = queryset.filter(run_id=run_id)

        serializer = AppTraceListSerializer(queryset[:200], many=True)
        return success_response({"project_id": int(project_id), "traces": serializer.data})


class TraceDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, trace_id):
        trace = AppTrace.objects.select_related("project", "run").filter(trace_id=trace_id).first()
        if not trace:
            return error_response("Trace not found.", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
        if not user_has_project_role(request.user, trace.project_id):
            return error_response("You do not have permission to access this trace.", code="permission_denied", status_code=403)
        return success_response(AppTraceSerializer(trace).data)


class TraceRiskListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, trace_id):
        trace = AppTrace.objects.filter(trace_id=trace_id).first()
        if not trace:
            return error_response("Trace not found.", code="not_found", status_code=status.HTTP_404_NOT_FOUND)
        if not user_has_project_role(request.user, trace.project_id):
            return error_response("You do not have permission to access this trace.", code="permission_denied", status_code=403)
        serializer = TraceRiskSerializer(trace.risks.select_related("step").all(), many=True)
        return success_response({"trace_id": trace_id, "risks": serializer.data})

