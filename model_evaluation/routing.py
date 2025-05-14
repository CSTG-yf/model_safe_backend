from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/evaluation/(?P<project_id>\w+)/$', consumers.EvaluationConsumer.as_asgi()),
]