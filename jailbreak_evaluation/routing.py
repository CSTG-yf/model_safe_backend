from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/jailbreak_evaluation/(?P<task_id>\w+)/$', consumers.ProgressConsumer.as_asgi()),
]