"""
ASGI config for ai_evaluation project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import jailbreak_evaluation.routing

import sys
print(sys.path)  # 检查是否有重复路径

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_evaluation.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            jailbreak_evaluation.routing.websocket_urlpatterns
        )
    ),
})
