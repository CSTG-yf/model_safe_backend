from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/question_generation/(?P<project_id>\w+)/$', consumers.QuestionBankConsumer.as_asgi()),
]