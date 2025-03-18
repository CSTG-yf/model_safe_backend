from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions,generics
from rest_framework.response import Response
from .models import Project
from question_bank.serializers import BasicEvalQuestionsSerializer
from question_bank.models import EvalQuestions
from .serializers import ProjectSerializer
from members.models import ProjectMember
from django.db import models

from django.db import IntegrityError

def check_project_permission(user, project_id, allow_owner=True):
    project = get_object_or_404(Project, id=project_id)

    is_member = ProjectMember.objects.filter(project=project, user=user).exists()
    is_owner = project.created_by == user

    if not (is_member or (allow_owner and is_owner)):
        return Response({"result": "error", "message": "你没有权限访问此项目"}, status=status.HTTP_403_FORBIDDEN)

    return None

class ProjectListCreateView(views.APIView):
    """ 获取用户的所有项目 & 创建新项目 """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """ 获取当前用户创建或加入的项目 """
        projects = Project.objects.filter(
            models.Q(created_by=request.user) |
            models.Q(members__user=request.user)
        ).distinct()
        serializer = ProjectSerializer(projects, many=True)
        return Response({
            "result": "success",
            "message": "获取项目列表成功",
            "projects": serializer.data
        })

    def post(self, request):
        """ 创建新项目 """
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            try:
                project = serializer.save(created_by=request.user)
                ProjectMember.objects.create(project=project, user=request.user, role="owner")
                return Response({
                    "result": "success",
                    "message": "项目创建成功",
                    "project": serializer.data
                }, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({
                    "result": "error",
                    "message": "你已经创建过同名的项目"
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "result": "error",
            "message": "创建失败",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProjectDetailView(views.APIView):
    """ 获取 / 更新 / 删除 单个项目 """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        """ 获取项目详情（仅成员可见） """
        permission_check = check_project_permission(request.user, project_id)
        if permission_check:
            return permission_check

        project = get_object_or_404(Project, id=project_id)
        serializer = ProjectSerializer(project)
        return Response({"result": "success", "message": "获取项目成功", "project": serializer.data})

    def put(self, request, project_id):
        """ 更新项目（仅成员可修改） """
        permission_check = check_project_permission(request.user, project_id)
        if permission_check:
            return permission_check

        project = get_object_or_404(Project, id=project_id)
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"result": "success", "message": "项目更新成功", "project": serializer.data})
        return Response({"result": "error", "message": "更新失败", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, project_id):
        """ 删除项目（仅创建者可删除） """
        permission_check = check_project_permission(request.user, project_id, allow_owner=True)
        if permission_check:
            return permission_check

        project = get_object_or_404(Project, id=project_id, created_by=request.user)
        project.delete()
        return Response({"result": "success", "message": "项目已删除"}, status=status.HTTP_204_NO_CONTENT)


class ProjectQuestionBankListView(generics.ListAPIView):
    """ 获取某个项目下的所有观测题库（不包含 questions） """
    serializer_class = BasicEvalQuestionsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """ 只获取当前项目的题库 """
        project_id = self.kwargs['project_id']
        return EvalQuestions.objects.filter(project_id=project_id)

    def list(self, request, *args, **kwargs):
        """ 在返回数据前检查用户是否是项目成员 """
        project_id = self.kwargs['project_id']
        permission_check = check_project_permission(request.user, project_id)
        if permission_check:
            return permission_check

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "result": "success",
            "message": "获取题库成功",
            "question_banks": serializer.data
        }, status=status.HTTP_200_OK)
