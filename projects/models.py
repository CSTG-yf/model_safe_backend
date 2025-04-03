from django.db import models
from users.models import User

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    ai_model_name = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects",null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects"
        unique_together = ("name", "created_by")

    def __str__(self):
        return f"{self.name} - {self.ai_model_name}"

