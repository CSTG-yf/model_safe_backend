from django.db import models
from users.models import User
from projects.models import Project

class ProjectMember(models.Model):
    """ 项目成员表 """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_projects")
    role = models.CharField(max_length=50, choices=[("owner", "Owner"), ("member", "Member")], default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")  # 不能重复加入
        db_table = "project_members"

    def __str__(self):
        return f"{self.user.email} - {self.project.name}"
