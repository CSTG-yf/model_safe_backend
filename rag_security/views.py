from django.db.models import Count
from rest_framework import permissions, status
from rest_framework.views import APIView

from core.permissions import get_project_for_member, user_has_project_role
from core.responses import error_response, success_response
from core.utils import parse_bool
from model_evaluation.models import EvaluationRun
from model_evaluation.serializers import EvaluationRunSerializer

from .models import RagDocument, RagEvalCase, RagKnowledgeBase
from .serializers import RagDocumentSerializer, RagEvalCaseSerializer, RagKnowledgeBaseSerializer
from .services import RagDemoDataService, RagIndexService, RagSecurityEvaluator


class KnowledgeBaseAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        queryset = RagKnowledgeBase.objects.filter(project=project).annotate(document_count=Count("documents")).order_by("-created_at")
        return success_response({"project_id": int(project_id), "knowledge_bases": RagKnowledgeBaseSerializer(queryset, many=True).data})

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        serializer = RagKnowledgeBaseSerializer(data={
            "project": project.id,
            "name": request.data.get("name") or "RAG 安全知识库",
            "description": request.data.get("description") or "",
            "metadata": request.data.get("metadata") or {},
        })
        serializer.is_valid(raise_exception=True)
        kb = serializer.save()
        return success_response(RagKnowledgeBaseSerializer(kb).data, status_code=status.HTTP_201_CREATED)


class DocumentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        knowledge_base_id = request.query_params.get("knowledge_base_id")
        if not knowledge_base_id:
            return error_response("knowledge_base_id is required.", code="invalid_params", status_code=400)
        kb = RagKnowledgeBase.objects.filter(id=knowledge_base_id).first()
        if not kb:
            return error_response("Knowledge base not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, kb.project_id):
            return error_response("You do not have permission to access this knowledge base.", code="permission_denied", status_code=403)
        docs = RagDocument.objects.filter(knowledge_base=kb).order_by("document_type", "id")
        document_type = request.query_params.get("document_type")
        if document_type:
            docs = docs.filter(document_type=document_type)
        return success_response({"knowledge_base_id": kb.id, "documents": RagDocumentSerializer(docs, many=True).data})

    def post(self, request):
        knowledge_base_id = request.data.get("knowledge_base_id")
        if not knowledge_base_id:
            return error_response("knowledge_base_id is required.", code="invalid_params", status_code=400)
        kb = RagKnowledgeBase.objects.filter(id=knowledge_base_id).first()
        if not kb:
            return error_response("Knowledge base not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, kb.project_id):
            return error_response("You do not have permission to update this knowledge base.", code="permission_denied", status_code=403)
        payload = dict(request.data)
        payload["knowledge_base"] = kb.id
        document_type = payload.get("document_type", "normal")
        payload["is_poisoned"] = parse_bool(payload.get("is_poisoned"), document_type == "poisoned")
        payload["contains_injection"] = parse_bool(payload.get("contains_injection"), document_type == "poisoned")
        serializer = RagDocumentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        return success_response(RagDocumentSerializer(doc).data, status_code=status.HTTP_201_CREATED)


class SeedDemoDocumentsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        kb, stats = RagDemoDataService.seed(project, name=request.data.get("name") or "RAG 安全评测演示知识库")
        serializer = RagKnowledgeBaseSerializer(RagKnowledgeBase.objects.annotate(document_count=Count("documents")).get(id=kb.id))
        return success_response({"knowledge_base": serializer.data, "seed_stats": stats}, status_code=status.HTTP_201_CREATED)


class SyncChromaAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, knowledge_base_id):
        kb = RagKnowledgeBase.objects.filter(id=knowledge_base_id).first()
        if not kb:
            return error_response("Knowledge base not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, kb.project_id):
            return error_response("You do not have permission to sync this knowledge base.", code="permission_denied", status_code=403)
        try:
            result = RagIndexService.sync_to_chroma(kb)
        except Exception as exc:
            return error_response(f"Chroma sync failed: {exc}", code="chroma_sync_failed", status_code=502)
        return success_response(result)


class RagEvalRunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        knowledge_base_id = request.data.get("knowledge_base_id")
        if not knowledge_base_id:
            return error_response("knowledge_base_id is required.", code="invalid_params", status_code=400)
        kb = RagKnowledgeBase.objects.select_related("project").filter(id=knowledge_base_id).first()
        if not kb:
            return error_response("Knowledge base not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, kb.project_id):
            return error_response("You do not have permission to run this knowledge base.", code="permission_denied", status_code=403)
        questions = request.data.get("questions") or []
        if not questions:
            question = request.data.get("question")
            if not question:
                return error_response("questions or question is required.", code="invalid_params", status_code=400)
            questions = [{
                "question": question,
                "expected_answer": request.data.get("expected_answer", ""),
                "target_poison_goal": request.data.get("target_poison_goal", ""),
            }]
        try:
            evaluator = RagSecurityEvaluator(
                project=kb.project,
                knowledge_base=kb,
                target_model_name=request.data.get("target_model_name") or request.data.get("model_name") or "",
                judge_model_name=request.data.get("judge_model_name") or request.data.get("evaluator_model_name") or "",
                simulate=parse_bool(request.data.get("simulate"), True),
                simulate_vulnerable=parse_bool(request.data.get("simulate_vulnerable"), True),
                created_by=request.user,
            )
        except ValueError as exc:
            return error_response(str(exc), code="invalid_params", status_code=400)
        run = evaluator.create_run(request.data.get("name") or "RAG 安全评测任务", questions)
        if parse_bool(request.data.get("execute"), True):
            evaluator.run(
                run,
                questions,
                top_k=int(request.data.get("top_k", 5)),
                include_sensitive=parse_bool(request.data.get("include_sensitive"), False),
                use_chroma=parse_bool(request.data.get("use_chroma"), False),
            )
            run.refresh_from_db()
        return success_response(EvaluationRunSerializer(run).data, status_code=status.HTTP_201_CREATED)

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error_response("project_id is required.", code="invalid_params", status_code=400)
        project, permission_error = get_project_for_member(request.user, project_id)
        if permission_error:
            return permission_error
        runs = EvaluationRun.objects.filter(project=project, run_type="rag").order_by("-created_at")[:100]
        return success_response({"project_id": int(project_id), "runs": EvaluationRunSerializer(runs, many=True).data})


class RagEvalRunDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = EvaluationRun.objects.filter(id=run_id, run_type="rag").first()
        if not run:
            return error_response("RAG run not found.", code="not_found", status_code=404)
        if not user_has_project_role(request.user, run.project_id):
            return error_response("You do not have permission to access this run.", code="permission_denied", status_code=403)
        cases = RagEvalCase.objects.filter(run=run).order_by("id")
        return success_response({
            "run": EvaluationRunSerializer(run).data,
            "cases": RagEvalCaseSerializer(cases, many=True).data,
        })

