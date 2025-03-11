from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer
from members.models import ProjectMember
from django.db import models

from django.db import IntegrityError

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
        """ 获取项目详情 """
        project = get_object_or_404(Project, id=project_id)
        if project.created_by != request.user and not ProjectMember.objects.filter(project=project, user=request.user).exists():
            return Response({"result": "error", "message": "你没有权限查看该项目"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectSerializer(project)
        return Response({"result": "success", "message": "获取项目成功", "project": serializer.data})

    def put(self, request, project_id):
        """ 更新项目 """
        project = get_object_or_404(Project, id=project_id)

        # 仅创建者 & 项目成员可以修改
        if project.created_by != request.user and not ProjectMember.objects.filter(project=project, user=request.user).exists():
            return Response({"result": "error", "message": "你没有权限修改该项目"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"result": "success", "message": "项目更新成功", "project": serializer.data})
        return Response({"result": "error", "message": "更新失败", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, project_id):
        """ 仅创建者可以删除项目 """
        project = get_object_or_404(Project, id=project_id, created_by=request.user)
        project.delete()
        return Response({"result": "success", "message": "项目已删除"}, status=status.HTTP_204_NO_CONTENT)
