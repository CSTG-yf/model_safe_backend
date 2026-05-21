from django.shortcuts import get_object_or_404
from rest_framework import status

from core.responses import error_response
from members.models import ProjectMember
from projects.models import Project


def user_has_project_role(user, project_id, roles=None):
    if not user or not user.is_authenticated:
        return False
    queryset = ProjectMember.objects.filter(project_id=project_id, user=user)
    if roles:
        queryset = queryset.filter(role__in=roles)
    return queryset.exists()


def require_project_member(user, project_id):
    if user_has_project_role(user, project_id):
        return None
    return error_response(
        message="You do not have permission to access this project.",
        code="permission_denied",
        status_code=status.HTTP_403_FORBIDDEN,
    )


def require_project_owner(user, project_id):
    if user_has_project_role(user, project_id, roles=["owner"]):
        return None
    return error_response(
        message="Only project owners can perform this action.",
        code="permission_denied",
        status_code=status.HTTP_403_FORBIDDEN,
    )


def get_project_for_member(user, project_id):
    project = get_object_or_404(Project, id=project_id)
    permission_error = require_project_member(user, project.id)
    if permission_error:
        return None, permission_error
    return project, None
