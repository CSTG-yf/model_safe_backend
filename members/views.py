from rest_framework import status, views, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ProjectMember
from users.models import User
from projects.models import Project
from .serializers import ProjectMemberSerializer


class ProjectMemberView(views.APIView):
    """ 处理成员管理（邀请、获取、删除成员） """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id):
        """ 获取项目所有成员 """
        project = get_object_or_404(Project, id=project_id)

        if not ProjectMember.objects.filter(project=project, user=request.user).exists():
            return Response({"result": "error", "message": "你没有权限查看该项目成员"},
                            status=status.HTTP_403_FORBIDDEN)

        members = ProjectMember.objects.filter(project=project).order_by("joined_at")
        serializer = ProjectMemberSerializer(members, many=True)
        return Response({"result": "success", "message": "获取成员成功", "members": serializer.data})

    def post(self, request, project_id):
        """ 邀请单个成员（仅 owner 可操作） """
        project = get_object_or_404(Project, id=project_id)

        if not ProjectMember.objects.filter(project=project, user=request.user, role="owner").exists():
            return Response({"result": "error", "message": "只有 owner 可以邀请成员"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"result": "error", "message": "请提供 user_id"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)

        if ProjectMember.objects.filter(project=project, user=user).exists():
            return Response({"result": "error", "message": "该用户已经是成员"}, status=status.HTTP_400_BAD_REQUEST)

        ProjectMember.objects.create(project=project, user=user, role="member")

        return Response({
            "result": "success",
            "message": f"{user.username} 已加入项目"
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, project_id, user_id):
        """ 移除成员（仅 owner 可以操作，不能移除 owner） """
        project = get_object_or_404(Project, id=project_id)

        if not ProjectMember.objects.filter(project=project, user=request.user, role="owner").exists():
            return Response({"result": "error", "message": "只有 owner 可以移除成员"}, status=status.HTTP_403_FORBIDDEN)

        member = get_object_or_404(ProjectMember, project=project, user_id=user_id)

        # 不能移除 owner
        if member.role == "owner":
            return Response({"result": "error", "message": "不能移除项目 owner"}, status=status.HTTP_400_BAD_REQUEST)

        member.delete()
        return Response({"result": "success", "message": "成员已移除"}, status=status.HTTP_204_NO_CONTENT)
