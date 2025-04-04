from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import EvalQuestions, SecurityQuestions
from .serializers import  SecurityQuestionsSerializer,BasicEvalQuestionsSerializer
from members.models import ProjectMember
from .services import generated_questions_and_add_to_database
from django.utils import timezone
from projects.models import Project
import logging

logger = logging.getLogger(__name__)



def check_project_membership(user, project_id):
    """检查用户是否是项目成员"""
    is_member = ProjectMember.objects.filter(project_id=project_id, user=user).exists()
    if not is_member:
        return Response({
            "result": "error",
            "message": "你不是该项目的成员，无权访问此内容"
        }, status=403)
    return None



class SearchQuestionBankView(views.APIView):
    """ 搜索或列出当前 `project_id` 下的题库 """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        """
        - 传入 `exam_title`：模糊搜索题库
        - 未传 `exam_title`：返回该项目下全部题库
        """
        permission_check = check_project_membership(request.user, project_id)
        if permission_check:
            return permission_check

        exam_title = request.data.get("exam_title", "").strip()

        if exam_title:
            queryset = EvalQuestions.objects.filter(project_id=project_id, exam_title__icontains=exam_title)
            if not queryset.exists():
                return Response({"result": "error", "message": "未找到匹配的题库"}, status=status.HTTP_404_NOT_FOUND)

            serializer = BasicEvalQuestionsSerializer(queryset, many=True)
            return Response({
                "result": "success",
                "message": "搜索成功",
                "question_banks": serializer.data
            }, status=status.HTTP_200_OK)

        else:
            # 未传 exam_title，返回全部题库
            queryset = EvalQuestions.objects.filter(project_id=project_id)
            serializer = BasicEvalQuestionsSerializer(queryset, many=True)
            return Response({
                "result": "success",
                "message": "已返回全部题库",
                "question_banks": serializer.data
            }, status=status.HTTP_200_OK)




class QuestionBankUpdateDeleteView(views.APIView):
    """ 修改和删除题库 """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, question_bank_id):
        """ 获取 `EvalQuestions` 实例，确保用户是项目成员 """
        question_bank = get_object_or_404(EvalQuestions, question_bank_id=question_bank_id)

        permission_check = check_project_membership(self.request.user, question_bank.project_id)
        if permission_check:
            return permission_check

        return question_bank

    def put(self, request, question_bank_id):
        """ 修改题库（只允许 `exam_title` 和 `description`） """
        instance = self.get_object(question_bank_id)
        if isinstance(instance, Response):  # 如果 `get_object` 返回 `Response`，说明用户无权限
            return instance

        data = request.data.copy()
        allowed_fields = ["exam_title", "description"]
        filtered_data = {key: data[key] for key in allowed_fields if key in data}

        if "exam_title" in filtered_data and not filtered_data["exam_title"].strip():
            return Response({
                "result": "error",
                "message": "题库名称不能为空"
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = BasicEvalQuestionsSerializer(instance, data=filtered_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "result": "success",
                "message": "题库修改成功",
                "question_bank": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "result": "error",
            "message": "修改失败",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, question_bank_id):
        """  删除题库 """
        instance = self.get_object(question_bank_id)
        if isinstance(instance, Response):  # 检查是否返回权限错误
            return instance

        instance.delete()
        return Response({
            "result": "success",
            "message": "题库已成功删除"
        }, status=status.HTTP_200_OK)


class SecurityQuestionListView(generics.ListAPIView):
    """ 获取所有安全题库的内容 """
    serializer_class = SecurityQuestionsSerializer
    permission_classes = [permissions.AllowAny]
    queryset = SecurityQuestions.objects.all()

    def list(self, request, *args, **kwargs):
        """ 返回格式调整，包含 `result` """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "result": "success",
            "message": "获取安全题库成功",
            "security_questions": serializer.data
        }, status=status.HTTP_200_OK)


class SingleQuestionBankView(views.APIView):
    """ 获取单个观测题库的题目 """
    permission_classes = [permissions.AllowAny]

    def get(self, request, question_bank_id):
        """ 获取某个题库的 `questions` 字段 """
        question_bank = get_object_or_404(EvalQuestions, question_bank_id=question_bank_id)

        return Response({
            "result": "success",
            "message": "获取题目列表成功",
            "questions": question_bank.questions  # 只返回 `questions` 字段
        }, status=status.HTTP_200_OK)


class GenerateObservationQuestionBankView(views.APIView):
    """ 生成观测题库（调用 AI + 安全题库）"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, project_id):
        """ 获取预生成题库id """
        try:
            project = get_object_or_404(Project, id=project_id)
            # 创建 EvalQuestions 实例
            eval_question = EvalQuestions.objects.create(
                exam_title=None,
                project_id=project,
                created_at=timezone.now(),
                questions=None,
            )
            return Response({
                'message': 'success',
                'question_bank_id': eval_question.question_bank_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"创建 EvalQuestions 失败: {str(e)}")  # 记录详细错误日志
            return Response({
                "message": "error",
                'question_bank_id': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request,project_id):
        """ 直接调用 `services.py` 生成题库 """
        return generated_questions_and_add_to_database(request,project_id)


class QuestionDetailView(views.APIView):

    permission_classes = [permissions.AllowAny]

    """
    处理单个题目的查看、修改和删除操作
    """

    def get_object(self, question_bank_id, question_id):
        try:
            # 获取对应题库的题目
            question_bank = EvalQuestions.objects.get(question_bank_id=question_bank_id)
            # 查找题目
            question = next((q for q in question_bank.questions if q['question_id'] == question_id), None)
            return question
        except EvalQuestions.DoesNotExist:
            return None

    def get(self, request, question_bank_id, question_id):
        """
        获取单个题目的详细信息
        """
        question = self.get_object(question_bank_id, question_id)
        if question:
            return Response({
                "result": "success",
                "message": "获取成功",
                "question": question
            })
        return Response({
            "result": "failure",
            "message": "Question not found",
        }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, question_bank_id, question_id):
        """
        修改单个题目的信息（部分更新）
        """
        try:
            # 获取题库对象
            question_bank = EvalQuestions.objects.get(question_bank_id=question_bank_id)
            # 获取要修改的题目
            question = self.get_object(question_bank_id, question_id)

            if not question:
                return Response({
                    "result": "failure",
                    "message": "题目不存在",
                }, status=status.HTTP_404_NOT_FOUND)

            # 创建题目副本用于修改
            updated_question = question.copy()

            # 只更新请求体中传递的字段
            for field, value in request.data.items():
                if field in updated_question:
                    updated_question[field] = value

            # 更新题库中的题目数组
            updated_questions = []
            for q in question_bank.questions:
                if q['question_id'] == question_id:
                    updated_questions.append(updated_question)
                else:
                    updated_questions.append(q)

            # 保存更新后的题库
            question_bank.questions = updated_questions
            question_bank.save()

            return Response({
                "result": "success",
                "message": "题目更新成功",
                "question": updated_question
            })

        except EvalQuestions.DoesNotExist:
            return Response({
                "result": "failure",
                "message": "题库不存在",
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, question_bank_id, question_id):
        """
        删除单个题目
        """
        question = self.get_object(question_bank_id, question_id)
        if question:
            question_bank = EvalQuestions.objects.get(question_bank_id=question_bank_id)
            # 从题库中移除对应的题目
            question_bank.questions = [q for q in question_bank.questions if q['question_id'] != question_id]
            question_bank.save()
            return Response({
                "result": "success",
                "message": "Question deleted successfully",
            })
        return Response({
            "result": "failure",
            "message": "Question not found",
        }, status=status.HTTP_404_NOT_FOUND)
