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
from pathlib import Path

import model_evaluation.routing
import question_bank.routing

BASE_DIR = Path(__file__).resolve().parent
sys.path = [
    str(BASE_DIR),
    *[p for p in sys.path if Path(p).resolve() != BASE_DIR and p not in ('.', '.\\')]
]

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_evaluation.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            jailbreak_evaluation.routing.websocket_urlpatterns +
            question_bank.routing.websocket_urlpatterns +
            model_evaluation.routing.websocket_urlpatterns
        )
    ),
})
