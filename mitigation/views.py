from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response
from core.utils import parse_bool
from model_evaluation.models import EvaluationRun
from model_evaluation.serializers import EvaluationRunSerializer

from .models import MitigationRecommendation, RegressionCase, RegressionSet
from .serializers import MitigationRecommendationSerializer, RegressionSetSerializer
from .services import MitigationTemplateService, RecommendationService, RegressionService


class RecommendationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        if request.query_params.get("seed") == "1":
            MitigationTemplateService.seed_defaults()
        queryset = MitigationRecommendation.objects.filter(project=project).select_related("trace", "risk", "run")
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return success_response({
            "project_id": int(project_id),
            "recommendations": MitigationRecommendationSerializer(queryset.order_by("-created_at")[:200], many=True).data,
        })


class RecommendationAcceptAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, recommendation_id):
        recommendation = MitigationRecommendation.objects.select_related("project").filter(id=recommendation_id).first()
        if not recommendation:
            return error_response("Recommendation not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, recommendation.project_id):
            return error_response("You do not have permission to update this recommendation.", code="permission_denied", status_code=403)
        RecommendationService.accept(recommendation)
        return success_response(MitigationRecommendationSerializer(recommendation).data)


class RegressionSetAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        regression_set = RegressionSet.objects.create(
            project=project,
            source_run_id=request.data.get("source_run"),
            name=request.data.get("name") or "手动安全回归集",
            risk_codes=request.data.get("risk_codes") or [],
            description=request.data.get("description") or "",
        )
        for item in request.data.get("cases") or []:
            RegressionCase.objects.create(
                regression_set=regression_set,
                source_case_id=item.get("source_case_id", ""),
                source_attempt_id=item.get("source_attempt_id", ""),
                input_payload=item.get("input_payload") or {},
                expected_safe_behavior=item.get("expected_safe_behavior") or "",
                risk_code=item.get("risk_code") or "jailbreak_success",
                metadata=item.get("metadata") or {},
            )
        return success_response(RegressionSetSerializer(regression_set).data, status_code=status.HTTP_201_CREATED)

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        sets = RegressionSet.objects.filter(project=project).order_by("-created_at")[:100]
        return success_response({"project_id": int(project_id), "regression_sets": RegressionSetSerializer(sets, many=True).data})


class RegressionRunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        regression_set_id = request.data.get("regression_set_id")
        if not regression_set_id:
            return error_response("regression_set_id is required.", code="invalid_params", status_code=400)
        regression_set = RegressionSet.objects.select_related("project").filter(id=regression_set_id).first()
        if not regression_set:
            return error_response("Regression set not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, regression_set.project_id):
            return error_response("You do not have permission to run this regression set.", code="permission_denied", status_code=403)
        run = RegressionService.create_run(
            regression_set,
            created_by=request.user,
            simulate=parse_bool(request.data.get("simulate"), True),
        )
        return success_response(EvaluationRunSerializer(run).data, status_code=status.HTTP_201_CREATED)


class RegressionCompareAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="regression").first()
        if not run:
            return error_response("Regression run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
        return success_response(RegressionService.compare(run))
