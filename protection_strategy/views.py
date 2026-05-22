from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response
from core.utils import parse_bool
from projects.models import Project

from .models import ModelProtectionStrategy, ProtectionPolicyVersion
from .serializers import ModelProtectionStrategyDetailSerializer, ModelProtectionStrategySerializer
from .services import ProtectionPolicyCompiler, ProtectionPolicyGenerator


class ProtectionStrategyListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        queryset = ModelProtectionStrategy.objects.filter(project=project).select_related("active_version")
        target_model_name = request.query_params.get("target_model_name")
        if target_model_name:
            queryset = queryset.filter(target_model_name=target_model_name)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return success_response({
            "project_id": project.id,
            "strategies": ModelProtectionStrategySerializer(queryset.order_by("-updated_at")[:100], many=True).data,
        })


class ProtectionStrategyGenerateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        target_model_name = request.data.get("target_model_name") or project.ai_model_name
        if not target_model_name:
            return error_response("target_model_name is required.", code="invalid_params", status_code=400)
        try:
            strategy, version = ProtectionPolicyGenerator.generate(
                project=project,
                target_model_name=target_model_name,
                name=request.data.get("name") or "",
                created_by=request.user,
                activate=parse_bool(request.data.get("activate"), True),
            )
        except ValueError as exc:
            return error_response(str(exc), code="invalid_params", status_code=400)
        return success_response({
            "strategy": ModelProtectionStrategyDetailSerializer(strategy).data,
            "generated_version_id": version.id,
        }, status_code=status.HTTP_201_CREATED)


class ProtectionStrategyDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, strategy_id):
        strategy = (
            ModelProtectionStrategy.objects.select_related("project", "active_version")
            .prefetch_related("versions__sources")
            .filter(id=strategy_id)
            .first()
        )
        if not strategy:
            return error_response("Protection strategy not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, strategy.project_id):
            return error_response("You do not have permission to access this strategy.", code="permission_denied", status_code=403)
        return success_response(ModelProtectionStrategyDetailSerializer(strategy).data)


class ProtectionStrategyActivateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, strategy_id):
        strategy = ModelProtectionStrategy.objects.select_related("project").filter(id=strategy_id).first()
        if not strategy:
            return error_response("Protection strategy not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, strategy.project_id):
            return error_response("You do not have permission to update this strategy.", code="permission_denied", status_code=403)
        version_id = request.data.get("version_id")
        version = ProtectionPolicyVersion.objects.filter(id=version_id, strategy=strategy).first() if version_id else strategy.versions.order_by("-version").first()
        if not version:
            return error_response("Protection policy version not found.", code="not_found", status_code=404)
        ProtectionPolicyGenerator.activate_version(strategy, version)
        return success_response(ModelProtectionStrategyDetailSerializer(strategy).data)


class ProtectionStrategyCompileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project = Project.objects.filter(id=project_id).first()
        if not project:
            return error_response("Project not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, project.id):
            return error_response("You do not have permission to compile this strategy.", code="permission_denied", status_code=403)
        compiled = ProtectionPolicyCompiler.compile(
            project=project,
            target_model_name=request.data.get("target_model_name") or project.ai_model_name or "",
            scenario_type=request.data.get("scenario_type") or "normal",
            user_input=request.data.get("user_input") or "",
            base_prompt=request.data.get("base_prompt") or "",
        )
        return success_response(compiled)


class ProtectionStrategyExportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, strategy_id):
        strategy = ModelProtectionStrategy.objects.select_related("project", "active_version").filter(id=strategy_id).first()
        if not strategy:
            return error_response("Protection strategy not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, strategy.project_id):
            return error_response("You do not have permission to export this strategy.", code="permission_denied", status_code=403)
        version = strategy.active_version or strategy.versions.order_by("-version").first()
        if not version:
            return error_response("Protection policy version not found.", code="not_found", status_code=404)
        markdown = ProtectionPolicyCompiler.export_markdown(version)
        if request.query_params.get("raw") == "1":
            return HttpResponse(markdown, content_type="text/markdown; charset=utf-8")
        return success_response({
            "strategy_id": strategy.id,
            "version_id": version.id,
            "format": "markdown",
            "content": markdown,
        })
