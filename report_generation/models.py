from django.db import models
from django.utils import timezone
from projects.models import Project


class Report(models.Model):
    report_name = models.CharField(blank=True, null=True,max_length=255, verbose_name="报告名称")
    description = models.TextField(blank=True, null=True,verbose_name="描述")
    project = models.ForeignKey(Project, on_delete=models.CASCADE,related_name="reports",verbose_name="关联项目",)
    report_detail = models.TextField(blank=True, null=True,verbose_name="报告内容（Markdown/HTML）")
    pdf_file = models.FileField(
        upload_to="reports/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name="PDF 文件地址",
    )
    created_time = models.DateTimeField(
        default=timezone.now, verbose_name="创建时间"
    )

    class Meta:
        verbose_name = "AI 生成报告"
        verbose_name_plural = "AI 生成报告"
        ordering = ["-created_time"]

    def __str__(self):
        return f"{self.report_name} (项目: {self.project.id})"
