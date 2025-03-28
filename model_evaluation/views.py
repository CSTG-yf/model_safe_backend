from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Sum
from .models import EvaluationBatch, ModelEvalMetrics, EvaluationRecord, OverallResult
from .serializers import OverallResultBasicSerializer, SimpleEvaluationBatchSerializer, OverallResultSerializer,EvaluationDetailSerializer,EvaluationRecordSerializer
from .utils import Evaluator
from projects.models import Project
from question_bank.models import EvalQuestions
from django.http import Http404



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
            EvalQuestions.objects.get(question_bank_id=question_bank_id)
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

class EvaluationDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, evaluation_id):
        """
        获取评测详情
        :param request: 包含评测ID
        :return: 评测详情
        """
        try:
            evaluation = EvaluationBatch.objects.get(id=evaluation_id)
            serializer = EvaluationDetailSerializer(evaluation)
            return Response(
                {
                    "message": "评测详情获取成功",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except EvaluationBatch.DoesNotExist:
            return Response(
                {"error": f"评测ID {evaluation_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request, evaluation_id):
        """更新评测名称和描述"""
        try:
            evaluation = EvaluationBatch.objects.get(id=evaluation_id)

            # 只允许更新 name 和 description 字段
            name = request.data.get('name')
            description = request.data.get('description')

            if name is not None:
                evaluation.name = name
            if description is not None:
                evaluation.description = description

            evaluation.save()

            return Response(
                {
                    "message": "评测信息更新成功",
                    "data": {
                        "id": evaluation.id,
                        "name": evaluation.name,
                        "description": evaluation.description
                    }
                },
                status=status.HTTP_200_OK,
            )
        except EvaluationBatch.DoesNotExist:
            return Response(
                {"error": f"评测ID {evaluation_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, evaluation_id):
        """删除评测"""
        try:
            evaluation = EvaluationBatch.objects.get(id=evaluation_id)

            # 先删除关联的评估记录
            EvaluationRecord.objects.filter(evaluation=evaluation).delete()

            # 再删除评测本身
            evaluation.delete()

            return Response(
                {
                    "message": "评测删除成功",
                    "deleted_id": evaluation_id
                },
                status=status.HTTP_200_OK,
            )
        except EvaluationBatch.DoesNotExist:
            return Response(
                {"error": f"评测ID {evaluation_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )


class EvaluationReviewView(APIView):
    """
    评测审核接口
    - PUT: 将评测标记为已审核
    """
    permission_classes = [permissions.AllowAny]

    def put(self, request, evaluation_id):
        """
        将评测标记为已审核
        :param evaluation_id: 要审核的评测ID
        """
        try:
            evaluation = EvaluationBatch.objects.get(id=evaluation_id)

            # 如果已经审核过，直接返回
            if evaluation.is_reviewed:
                return Response(
                    {
                        "message": "该评测已被审核过",
                        "evaluation_id": evaluation.id,
                        "is_reviewed": True
                    },
                    status=status.HTTP_200_OK,
                )

            # 更新审核状态
            evaluation.is_reviewed = True
            evaluation.save()

            return Response(
                {
                    "message": "评测审核成功",
                    "evaluation_id": evaluation.id,
                    "is_reviewed": evaluation.is_reviewed
                },
                status=status.HTTP_200_OK,
            )

        except EvaluationBatch.DoesNotExist:
            return Response(
                {"error": f"评测ID {evaluation_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )


class EvaluationRecordDetailView(APIView):
    """
    题目详情操作接口
    - GET: 获取题目详情
    - PUT: 更新题目分数
    - DELETE: 删除题目
    """
    permission_classes = [permissions.AllowAny]  # 根据需求调整权限

    def get_object(self, record_id):
        try:
            return EvaluationRecord.objects.get(record_id=record_id)
        except EvaluationRecord.DoesNotExist:
            raise Http404

    def get(self, request, record_id):
        """
        获取题目详情
        """
        record = self.get_object(record_id)
        serializer = EvaluationRecordSerializer(record)
        return Response(serializer.data)

    def put(self, request, record_id):
        """
        更新题目分数
        """
        record = self.get_object(record_id)

        # 只允许更新score字段
        if 'score' not in request.data:
            return Response(
                {"error": "必须提供score字段"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 验证分数范围 (假设分数范围是0-5)
        new_score = request.data['score']
        if not (0 <= float(new_score) <= 5):
            return Response(
                {"error": "分数必须在0到5之间"},
                status=status.HTTP_400_BAD_REQUEST
            )

        record.score = new_score
        record.save()

        # 更新关联评测批次的平均分
        self.update_batch_average(record.evaluation)

        serializer = EvaluationRecordSerializer(record)
        return Response(serializer.data)

    def delete(self, request, record_id):
        """
        删除题目
        """
        record = self.get_object(record_id)
        evaluation_batch = record.evaluation  # 保存关联的评测批次

        record.delete()

        # 更新关联评测批次的统计信息
        self.update_batch_stats(evaluation_batch)

        return Response(
            {"message": "题目删除成功"},
            status=status.HTTP_204_NO_CONTENT
        )

    def update_batch_average(self, evaluation_batch):
        """
        更新关联评测批次的平均分
        """
        avg_score = EvaluationRecord.objects.filter(
            evaluation=evaluation_batch
        ).aggregate(Avg('score'))['score__avg'] or 0

        evaluation_batch.average_score = avg_score
        evaluation_batch.save()

    def update_batch_stats(self, evaluation_batch):
        """
        更新关联评测批次的统计信息
        """
        stats = EvaluationRecord.objects.filter(
            evaluation=evaluation_batch
        ).aggregate(
            total_samples=Count('id'),
            total_tokens=Sum('tokens'),
            avg_score=Avg('score')
        )

        evaluation_batch.total_samples = stats['total_samples']
        evaluation_batch.total_tokens = stats['total_tokens'] or 0
        evaluation_batch.average_score = stats['avg_score'] or 0
        evaluation_batch.save()


class OverallResultView(APIView):
    """
    评估结果资源端点 (支持POST/PUT/GET)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """创建新的模型评估"""
        project_id = request.data.get("project_id")
        batch_ids = request.data.get("batch_ids", [])

        if not project_id or not batch_ids:
            return Response(
                {"error": "必须提供project_id和batch_ids"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)
            evaluations = EvaluationBatch.objects.filter(
                project=project,
                id__in=batch_ids
            ).select_related('project')

            if not evaluations.exists():
                raise EvaluationBatch.DoesNotExist

        except (Project.DoesNotExist, EvaluationBatch.DoesNotExist) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        # 聚合计算
        aggregation = evaluations.aggregate(
            total_samples=Sum('total_samples'),
            total_tokens=Sum('total_tokens')
        )

        # 检查模型一致性
        model_names = evaluations.values_list('model_name', flat=True).distinct()
        if len(model_names) != 1:
            return Response(
                {"error": "批次中包含不同模型"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取模型指标
        try:
            metrics = ModelEvalMetrics.objects.get(model_name=model_names[0])
        except ModelEvalMetrics.DoesNotExist:
            return Response(
                {"error": f"模型 {model_names[0]} 未配置指标"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 计算各内容类型平均分
        records = EvaluationRecord.objects.filter(
            evaluation__in=evaluations
        ).values('content_type').annotate(
            avg_score=Avg('score')
        )

        # 将记录转换为JSON格式
        project_score = {record['content_type']: record['avg_score'] for record in records}

        # 创建评估结果
        result = OverallResult.objects.create(
            project=project,
            total_tokens=aggregation['total_tokens'] or 0,
            hallucination_accuracy=metrics.hallucination_accuracy,
            toxicity_accuracy=metrics.toxicity_accuracy,
            total_samples=aggregation['total_samples'] or 0,
            name=f"{project.name}的评估结果",
            project_score=project_score  # 保存JSON数据
        )

        return Response(
            {
                "id": result.id,
                "name": result.name,
                "project": project_id,
                "created_at": result.created_at
            },
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk=None):
        """更新评估结果名称和描述（字段可选）"""
        if not pk:
            return Response(
                {"error": "需要提供结果ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = OverallResult.objects.get(id=pk)

            # 可选更新 name 和 description
            if 'name' in request.data:
                result.name = request.data['name']
            if 'description' in request.data:
                result.description = request.data['description']

            result.save()
            return Response(
                OverallResultBasicSerializer(result).data,
                status=status.HTTP_200_OK
            )
        except OverallResult.DoesNotExist:
            return Response(
                {"error": "评估结果不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk=None):
        """获取单个评估结果详情"""
        if not pk:
            return Response(
                {"error": "必须提供结果ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = OverallResult.objects.get(id=pk)
            serializer = OverallResultSerializer(result)
            return Response(serializer.data)
        except OverallResult.DoesNotExist:
            return Response(
                {"error": "评估结果不存在"},
                status=status.HTTP_404_NOT_FOUND
            )


class OverallResultListView(APIView):
    """
    获取项目评估结果列表
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取项目评估结果列表"""
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"error": "必须提供project_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": f"项目ID {project_id} 不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        overall_results = OverallResult.objects.filter(project=project).order_by("-created_at")
        serializer = OverallResultSerializer(overall_results, many=True)

        return Response(
            {
                "project_id": project_id,
                "count": overall_results.count(),
                "results": serializer.data
            },
            status=status.HTTP_200_OK
        )



    






        
    