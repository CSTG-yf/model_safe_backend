from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response
from core.utils import parse_bool
from model_evaluation.models import EvaluationRun
from model_evaluation.serializers import EvaluationRunSerializer

from .models import AgentTool, AgentToolCall
from .serializers import AgentToolCallSerializer, AgentToolSerializer
from .services import AgentSandbox, AgentToolRegistry, ToolPolicyEngine
from .tool_templates import DEFAULT_AGENT_ATTACK_CASES


class AgentToolAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        if request.query_params.get("seed") == "1":
            AgentToolRegistry.seed_defaults(project)
        queryset = AgentTool.objects.filter(project=project).order_by("risk_level", "name")
        enabled = request.query_params.get("enabled")
        if enabled is not None:
            queryset = queryset.filter(enabled=parse_bool(enabled, True))
        return success_response({
            "project_id": project.id,
            "tools": AgentToolSerializer(queryset, many=True).data,
        })

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        payload = dict(request.data)
        payload["project"] = project.id
        serializer = AgentToolSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        tool = serializer.save()
        return success_response(AgentToolSerializer(tool).data, status_code=status.HTTP_201_CREATED)


class SeedAgentToolsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        stats = AgentToolRegistry.seed_defaults(project)
        tools = AgentTool.objects.filter(project=project).order_by("name")
        return success_response({
            "seed_stats": stats,
            "tools": AgentToolSerializer(tools, many=True).data,
        }, status_code=status.HTTP_201_CREATED)


class ToolPolicyCheckAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        tool_name = request.data.get("tool_name")
        if not project_id or not tool_name:
            return error_response("project_id and tool_name are required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        tool = AgentTool.objects.filter(project=project, name=tool_name).first()
        decision = ToolPolicyEngine.evaluate(
            tool,
            arguments=request.data.get("arguments") or {},
            user_role=request.data.get("user_role") or "member",
            confirmed=parse_bool(request.data.get("confirmed"), False),
        )
        return success_response({
            "project_id": project.id,
            "tool_name": tool_name,
            "decision": decision,
        })


class AgentEvalRunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        runs = EvaluationRun.objects.filter(project=project, run_type="agent").order_by("-created_at")[:100]
        return success_response({
            "project_id": project.id,
            "runs": EvaluationRunSerializer(runs, many=True).data,
        })

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        cases = request.data.get("cases") or DEFAULT_AGENT_ATTACK_CASES
        sandbox = AgentSandbox(
            project=project,
            target_model_name=request.data.get("target_model_name") or request.data.get("model_name") or "",
            created_by=request.user,
            simulate=parse_bool(request.data.get("simulate"), True),
        )
        run = sandbox.create_run(name=request.data.get("name") or "", cases=cases)
        if parse_bool(request.data.get("execute"), True):
            sandbox.run(run, cases=cases)
            run.refresh_from_db()
        return success_response(EvaluationRunSerializer(run).data, status_code=status.HTTP_201_CREATED)


class AgentEvalRunDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="agent").first()
        if not run:
            return error_response("Agent run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
        calls = AgentToolCall.objects.filter(run=run).select_related("tool").order_by("id")
        return success_response({
            "run": EvaluationRunSerializer(run).data,
            "tool_calls": AgentToolCallSerializer(calls, many=True).data,
        })


class AgentToolCallAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        trace_id = request.query_params.get("trace_id")
        run_id = request.query_params.get("run_id")
        if not project_id and not trace_id and not run_id:
            return error_response("project_id, run_id, or trace_id is required.", code="invalid_params", status_code=400)
        queryset = AgentToolCall.objects.select_related("project", "tool", "run").order_by("-created_at")
        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)
            first = queryset.first()
            if not first:
                return success_response({"tool_calls": []})
            if not user_has_project_role(request.user, first.project_id):
                return error_response("You do not have permission to access this trace.", code="permission_denied", status_code=403)
        elif run_id:
            run = EvaluationRun.objects.filter(id=run_id, run_type="agent").first()
            if not run:
                return error_response("Agent run not found.", code="not_found", status_code=404)
            if not user_has_project_role(request.user, run.project_id):
                return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
            queryset = queryset.filter(run=run)
        else:
            project, permission_error = get_project_for_member(request.user, project_id)
            if permission_error:
                return permission_error
            queryset = queryset.filter(project=project)
        return success_response({"tool_calls": AgentToolCallSerializer(queryset[:200], many=True).data})
