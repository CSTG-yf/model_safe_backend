from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/evaluation/(?P<evaluation_batch>\w+)/$', consumers.EvaluationConsumer.as_asgi()),
]