from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import EvalQuestions, SecurityQuestions
from .serializers import EvalQuestionsSerializer, SecurityQuestionsSerializer,BasicEvalQuestionsSerializer
from members.models import ProjectMember
import random
from django.utils.timezone import now


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
    """ 生成观测题库（模拟数据） """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        """ 在数据库中创建一个模拟的观测题库 """
        exam_title = request.data.get("exam_title", f"观测题库_{random.randint(1000, 9999)}")
        description = request.data.get("description", "自动生成的模拟观测题库")

        # 获取随机安全题库题目
        security_questions = list(SecurityQuestions.objects.all())
        num_security_questions = min(len(security_questions), 3)  # 随机选取最多 3 道安全题
        selected_security_questions = random.sample(security_questions, num_security_questions) if security_questions else []

        # 构造 JSON 格式的 `questions`
        questions = [
            {
                "question_id": q.id,
                "source": "SecurityQuestions",
                "content_type": q.content_type,
                "question_type": q.question_type,
                "question": q.question,
                "options": q.options,
                "answer": q.answer,
                "scoring_criteria": q.scoring_criteria
            }
            for q in selected_security_questions
        ]

        # 额外生成 2 道 AI 题目（模拟）
        ai_generated_questions = [
            {
                "question_id": random.randint(10000, 99999),
                "source": "AI",
                "content_type": "text",
                "question_type": "选择题",
                "question": f"这是 AI 生成的问题 {i+1}?",
                "options": ["选项 A", "选项 B", "选项 C"],
                "answer": "选项 A",
                "scoring_criteria": "回答 A 正确，其他错误"
            }
            for i in range(2)
        ]

        # 合并安全题目和 AI 生成的题目
        questions.extend(ai_generated_questions)

        # 创建数据库记录
        question_bank = EvalQuestions.objects.create(
            exam_title=exam_title,
            description=description,
            project_id_id=project_id,  # 直接传 `project_id`
            created_at=now(),
            questions=questions
        )

        serializer = EvalQuestionsSerializer(question_bank)

        return Response({
            "result": "success",
            "message": "观测题库生成成功",
            "question_bank": serializer.data
        }, status=status.HTTP_201_CREATED)

