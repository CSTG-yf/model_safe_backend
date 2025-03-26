from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Sum
from django.utils import timezone
from .models import EvaluationBatch, ModelEvalMetrics, EvaluationRecord, OverallResult
from .serializers import EvaluationBatchSerializer, SimpleEvaluationBatchSerializer, OverallResultSerializer
from .utils import Evaluator
from projects.models import Project
from question_bank.models import EvalQuestions


class EvaluationCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data

        # 校验必要参数
        project_id = data.get("project_id")
        question_bank_id = data.get("question_bank_id")
        if not all([project_id, question_bank_id]):
            return Response(
                {"error": "缺少必要参数：project_id 或 question_bank_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 校验题库是否存在（但不保存到评测记录）
        try:
            EvalQuestions.objects.get(id=question_bank_id)
        except EvalQuestions.DoesNotExist:
            return Response(
                {"error": "题库不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 获取项目实例
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": "项目不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 创建评测记录
        evaluation_batch = EvaluationBatch.objects.create(
            project=project,
            model_name=data.get("model_name", project.ai_model_name),
            evaluator_model_name=data.get("evaluation_model_name", "deepseek-chat"),
            name=data.get("evaluation_name", "未命名评估"),
            description=data.get("evaluation_description", ""),
        )

        return Response(
            {
                "message": "评测记录创建成功",
                "evaluation_id": evaluation_batch.id,
            },
            status=status.HTTP_201_CREATED,
        )



class EvaluationRunView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, evaluation_id):
        data = request.data

        # 校验必要参数
        question_bank_id = data.get("question_bank_id")
        if not question_bank_id:
            return Response(
                {"error": "缺少必要参数：question_bank_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 获取评测记录实例
        evaluation_batch = get_object_or_404(EvaluationBatch, id=evaluation_id)

        # 获取题库实例
        try:
            question_bank = EvalQuestions.objects.get(question_bank_id=question_bank_id)
        except EvalQuestions.DoesNotExist:
            return Response(
                {"error": "题库不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 固定API配置
        DEFAULT_API_KEY = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
        DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"

        try:
            # 初始化评估器
            evaluator = Evaluator(
                api_key=DEFAULT_API_KEY,
                base_url=DEFAULT_BASE_URL,
                model_name=evaluation_batch.model_name,
                project_id=evaluation_batch.project.id,
                question_bank_id=question_bank.question_bank_id,  # 使用传入的题库ID
                eval_model_name=evaluation_batch.evaluator_model_name,
            )

            # Step 1: 执行基础指标评估（幻觉和毒性检测）
            evaluator.run_full_evaluation(
                api_key=DEFAULT_API_KEY,
                base_url=DEFAULT_BASE_URL,
                model_name=evaluation_batch.model_name,
                sample_size=int(data.get("sample_size", 100)),
            )

            # Step 2: 执行题库评估
            evaluator.evaluate_multiple(evaluation_batch)

            return Response(
                {"message": "评测任务执行成功"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"评测任务执行失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )





class EvaluationListView(APIView):
    """
    获取评测记录列表接口
    - GET: 根据项目ID获取评测记录列表
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        获取评测记录列表
        :param request: 包含项目ID的查询参数
        :return: 评测记录列表
        """
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"error": "缺少必要参数：project_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 获取项目实例
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": f"项目ID {project_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 获取评测记录列表
        evaluations = EvaluationBatch.objects.filter(project=project).order_by(
            "-created_at"
        )
        serializer = SimpleEvaluationBatchSerializer(evaluations, many=True)

        return Response(
            {
                "message": "评测记录列表获取成功",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class OverallResultRunView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        开始模型评估
        :param request: 包含项目ID和测试ID的数组的查询参数
        :return: 评估的ID
        """
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"error": "缺少必要参数：project_id"}, 
                status=status.HTTP_400_BAD_REQUEST
                )

        batch_ids = request.query_params.getlist("batch_ids")
        if not batch_ids:
            return Response(
                {"error": "缺少必要的参数: batch_ids"}, 
                status=status.HTTP_400_BAD_REQUEST
                )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": f"项目ID {project_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # 获得查询的评估批次
        evaluations = EvaluationBatch.objects.filter(project=project, id__in=batch_ids).order_by(
            "-created_at"
        )

        total_samples_sum = evaluations.aggregate(total_samples=Sum('total_samples'))['total_samples'] or 0
        total_tokens_sum = evaluations.aggregate(total_tokens=Sum('total_tokens'))['total_tokens'] or 0
        

        model_names = set(evaluation.model_name for evaluation in evaluations)

        # 检查是否只有一个唯一的model_name
        if len(model_names) != 1:
            return Response(
                {"error": "存在多个不同的 model_name"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        model_name = model_names.pop()

        try:
            metrics = ModelEvalMetrics.objects.get(model_name=model_name)
            hallucination_accuracy = metrics.hallucination_accuracy
            toxicity_accuracy = metrics.toxicity_accuracy
        except ModelEvalMetrics.DoesNotExist:
            return Response(
                {"error": f"未找到模型 {model_name} 的评估指标"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # 获得评估批次中的记录
        evaluation_records = EvaluationRecord.objects.filter(evaluation__in=evaluations)
        
        content_type_avg_scores = evaluation_records.values('content_type').annotate(avg_score=Avg('score'))

        project_score = {record['content_type']: record['avg_score'] for record in content_type_avg_scores}
        if not project_score:
            project_score = {}

        overall_result = OverallResult.objects.create(
            name=f"评估结果_{project.name}",
            description=f"{project.name}的评估结果细节",
            project_score=project_score,
            total_tokens=total_tokens_sum,
            hallucination_accuracy=hallucination_accuracy,
            toxicity_accuracy=toxicity_accuracy,
            total_samples=total_samples_sum,
        )

        return Response(
            {
                "message": "模型评估成功",
                "data": overall_result.id,
            },
            status=status.HTTP_200_OK,
        )
    
    def post(self, request):
        """
        设置评估模型结果的名称
        :param request: JSON，包含 overall_result_id 和新的 name
        :return: 操作结果
        """
        overall_result_id = request.data.get("overall_result_id")
        new_name = request.data.get("name")

        if not overall_result_id or not new_name:
            return Response(
                {"error": "缺少必要参数：overall_result_id 或 name"},
                status=status.HTTP_400_BAD_REQUEST
                )

        try:
            overall_result = OverallResult.objects.get(id=overall_result_id)
        except OverallResult.DoesNotExist:
            return Response(
                {"error": f"评估结果 ID {overall_result_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND
                )

        overall_result.name = new_name
        overall_result.save()

        return Response(
            {"message": "评估名称更新成功", "data": overall_result.id},
            status=status.HTTP_200_OK
            )
    

class OverallResultListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        获取评估结果列表
        :param request: 包含 project_id
        :return: 模型评估结果列表
        """
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"error": "缺少必要参数：project_id"}, 
                status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": f"项目ID {project_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        overall_results = OverallResult.objects.filter(project=project,).order_by(
            "-created_at"
        )

        serializer = OverallResultSerializer(overall_results, many=True)

        return Response(
            {
                "message": "项目评估模型列表获取成功",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class OverallResultRecordView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        获取评估结果记录
        :param request: 包含 overall_result_id
        :return: 模型评估结果记录
        """
        overall_result_id = request.query_params.get("overall_result_id")
        if not overall_result_id:
            return Response(
                {"error": "缺少必要参数：overall_result_id"}, 
                status=status.HTTP_400_BAD_REQUEST
                )
        
        overall_result = OverallResult.objects.filter(id=overall_result_id)

        serializer = OverallResultSerializer(overall_result)

        return Response(
            {
                "message": "评估模型记录获取成功",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



    






        
    