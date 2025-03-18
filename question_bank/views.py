from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import EvalQuestions, SecurityQuestions
from .serializers import EvalQuestionsSerializer, SecurityQuestionsSerializer,BasicEvalQuestionsSerializer
from members.models import ProjectMember
import random
from django.utils.timezone import now
from .services import generated_questions_and_add_to_database


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
    """ 仅搜索当前 `project_id` 下的题库 """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        """ 通过 `exam_title` 搜索 `project_id` 题库 """
        permission_check = check_project_membership(request.user, project_id)
        if permission_check:
            return permission_check

        exam_title = request.data.get("exam_title", "").strip()
        if not exam_title:
            return Response({"result": "error", "message": "请提供搜索关键词"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = EvalQuestions.objects.filter(project_id=project_id, exam_title__icontains=exam_title)
        if not queryset.exists():
            return Response({"result": "error", "message": "未找到匹配的题库"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BasicEvalQuestionsSerializer(queryset, many=True)
        return Response({
            "result": "success",
            "message": "搜索成功",
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
    permission_classes = [permissions.IsAuthenticated]
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
    """ 获取单个观测题库的具体内容 """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, question_bank_id):
        """ 获取某个题库的详细内容 """
        question_bank = get_object_or_404(EvalQuestions, question_bank_id=question_bank_id)
        serializer = EvalQuestionsSerializer(question_bank)
        return Response({
            "result": "success",
            "message": "获取题库详情成功",
            "question_bank": serializer.data
        }, status=status.HTTP_200_OK)


class GenerateObservationQuestionBankView(views.APIView):
    """ 生成观测题库（调用 AI + 安全题库）"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """ 直接调用 `services.py` 生成题库 """
        return generated_questions_and_add_to_database(request)
