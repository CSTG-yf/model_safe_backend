from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response
from core.utils import parse_bool
from model_evaluation.models import EvaluationRun
from model_evaluation.serializers import EvaluationRunSerializer

from .models import AttackStrategy, RedTeamAttempt, StrategyStat
from .serializers import AttackStrategySerializer, RedTeamAttemptSerializer, StrategyStatSerializer
from .services import RedTeamOrchestrator, StrategySeedService


class RedTeamRunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=status.HTTP_400_BAD_REQUEST)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error

        StrategySeedService.seed_defaults()
        objectives = request.data.get("objectives") or []
        if not objectives:
            seed_prompt = request.data.get("seed_prompt") or request.data.get("objective")
            if not seed_prompt:
                return error_response("objectives or seed_prompt is required.", code="invalid_params", status_code=400)
            objectives = [{
                "objective": request.data.get("objective") or seed_prompt,
                "seed_prompt": seed_prompt,
                "risk_code": request.data.get("risk_code") or "jailbreak_success",
            }]

        try:
            orchestrator = RedTeamOrchestrator(
                project=project,
                target_model_name=request.data.get("target_model_name") or request.data.get("model_name") or "",
                judge_model_name=request.data.get("judge_model_name") or request.data.get("evaluator_model_name") or "",
                attack_model_name=request.data.get("attack_model_name") or "",
                max_rounds=request.data.get("max_rounds") or 3,
                simulate=parse_bool(request.data.get("simulate"), True),
                created_by=request.user,
            )
        except ValueError as exc:
            return error_response(str(exc), code="invalid_params", status_code=status.HTTP_400_BAD_REQUEST)
        run = orchestrator.create_run(
            name=request.data.get("name") or "自适应红队任务",
            description=request.data.get("description") or "",
            objectives=objectives,
        )
        if parse_bool(request.data.get("execute"), False):
            orchestrator.run(run, objectives)
            run.refresh_from_db()
        return success_response(EvaluationRunSerializer(run).data, status_code=status.HTTP_201_CREATED)

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=status.HTTP_400_BAD_REQUEST)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        runs = EvaluationRun.objects.filter(project=project, run_type="jailbreak").order_by("-created_at")[:100]
        return success_response({"project_id": int(project_id), "runs": EvaluationRunSerializer(runs, many=True).data})


class RedTeamRunDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="jailbreak").first()
        if not run:
            return error_response("Run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
        return success_response(EvaluationRunSerializer(run).data)

    def post(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="jailbreak").select_related("project").first()
        if not run:
            return error_response("Run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to execute this run.", code="permission_denied", status_code=403)
        if run.status == "running":
            return error_response("Run is already running.", code="run_already_running", status_code=409)
        if run.redteam_attempts.exists() and not parse_bool(request.data.get("force"), False):
            return error_response(
                "Run already has attempts. Create a new run or pass force=true to append another execution.",
                code="run_already_executed",
                status_code=409,
            )
        objectives = request.data.get("objectives") or run.model_config.get("objectives") or [{
            "objective": request.data.get("objective") or "安全边界测试",
            "seed_prompt": request.data.get("seed_prompt") or "请进行安全边界测试",
            "risk_code": request.data.get("risk_code") or "jailbreak_success",
        }]
        orchestrator = RedTeamOrchestrator(
            project=run.project,
            target_model_name=run.model_config.get("target_model_name") or run.model_name,
            judge_model_name=(run.model_config.get("internal_models") or {}).get("judge_model_name") or run.evaluator_model_name,
            attack_model_name=(run.model_config.get("internal_models") or {}).get("attack_model_name") or "",
            max_rounds=run.model_config.get("max_rounds", 3),
            simulate=parse_bool(run.model_config.get("simulate"), True),
            created_by=request.user,
        )
        orchestrator.run(run, objectives)
        run.refresh_from_db()
        return success_response(EvaluationRunSerializer(run).data)


class RedTeamAttemptListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="jailbreak").first()
        if not run:
            return error_response("Run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
        attempts = RedTeamAttempt.objects.filter(run=run).select_related("strategy", "case")
        return success_response({"run_id": run.id, "attempts": RedTeamAttemptSerializer(attempts, many=True).data})


class AttackStrategyListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.query_params.get("seed") == "1":
            StrategySeedService.seed_defaults()
        strategies = AttackStrategy.objects.all().order_by("category", "name")
        return success_response({"strategies": AttackStrategySerializer(strategies, many=True).data})

    def post(self, request):
        serializer = AttackStrategySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        strategy = serializer.save()
        return success_response(AttackStrategySerializer(strategy).data, status_code=status.HTTP_201_CREATED)


class StrategyStatListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats = StrategyStat.objects.select_related("strategy").all().order_by("-successes", "-average_score")
        risk_code = request.query_params.get("risk_code")
        if risk_code:
            stats = stats.filter(risk_code=risk_code)
        return success_response({"strategy_stats": StrategyStatSerializer(stats, many=True).data})
