from django.db import models
from django.core.serializers.json import DjangoJSONEncoder


class JailbreakQuestion(models.Model):
    category_index = models.IntegerField(primary_key=True)
    title_index = models.IntegerField()
    prompt_num = models.IntegerField()
    category = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    prompt = models.TextField()
    starting_string = models.TextField()

    class Meta:
        db_table = 'new_jailbreak'
        unique_together = ('category_index', 'title_index', 'prompt_num')
        managed = False


class ScoreRecord(models.Model):
    session_id = models.CharField(max_length=255,primary_key=True)  # 会话ID(由模型名称+时间戳组成)
    ev_id = models.CharField(max_length=255)  # 评估结果ID
    project_id = models.IntegerField()
    session_name = models.TextField()
    category_index = models.IntegerField()
    title_index = models.IntegerField()
    content_index = models.IntegerField()
    avg_score = models.FloatField()
    history = models.JSONField(encoder=DjangoJSONEncoder)

    class Meta:
        db_table = 'new_content_avg_score'
        unique_together = ('session_id', 'ev_id','project_id')


# class IterationRecord(models.Model):
#     category_index = models.IntegerField(primary_key=True)
#     title_index = models.IntegerField()
#     prompt_num = models.IntegerField()
#     cycle_num = models.IntegerField()
#     score_info = models.JSONField(encoder=DjangoJSONEncoder)
#
#     class Meta:
#         db_table = 'iterate_stream'
#         unique_together = ('category_index', 'title_index', 'prompt_num', 'cycle_num')
