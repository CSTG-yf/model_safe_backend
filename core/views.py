import logging
import os

from django.conf import settings
from openai import OpenAI
from rest_framework import permissions, status, views
from rest_framework.response import Response


logger = logging.getLogger(__name__)


class EvaluableModelListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        models = list(getattr(settings, "EVALUABLE_MODEL_NAMES", []))
        return Response(
            {
                "result": "success",
                "models": models,
                "provider": {
                    "name": "dashscope",
                    "base_url": getattr(settings, "DASHSCOPE_BASE_URL", ""),
                    "api_key_env": getattr(settings, "DASHSCOPE_API_KEY_ENV", "DASHSCOPE_API_KEY"),
                    "fallback_api_key_env": getattr(settings, "DASHSCOPE_FALLBACK_API_KEY_ENV", "ONE_API_KEY"),
                },
                "add_model_hint": "Edit ai_evaluation/settings.py:EVALUABLE_MODEL_NAMES to explicitly add testable models.",
            }
        )


class ModelPingView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        model_name = (request.data.get("model_name") or "").strip()
        allowed_models = set(getattr(settings, "EVALUABLE_MODEL_NAMES", []))
        if not model_name:
            return Response({"result": "error", "message": "model_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if model_name not in allowed_models:
            return Response(
                {"result": "error", "message": f"Model '{model_name}' is not in EVALUABLE_MODEL_NAMES."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key_env = getattr(settings, "DASHSCOPE_API_KEY_ENV", "DASHSCOPE_API_KEY")
        fallback_api_key_env = getattr(settings, "DASHSCOPE_FALLBACK_API_KEY_ENV", "ONE_API_KEY")
        api_key = os.getenv(api_key_env, "") or os.getenv(fallback_api_key_env, "")
        if not api_key:
            return Response(
                {"result": "error", "message": f"{api_key_env} or {fallback_api_key_env} is not configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_url = getattr(settings, "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        prompt = request.data.get("prompt") or "请用一句中文回复：模型连通性测试成功。"

        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是用于连通性测试的助手，只需简短回答。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=80,
            )
            message = completion.choices[0].message.content
            usage = getattr(completion, "usage", None)
            usage_payload = usage.model_dump() if hasattr(usage, "model_dump") else getattr(usage, "__dict__", None)
            return Response(
                {
                    "result": "success",
                    "model_name": model_name,
                    "response": message,
                    "usage": usage_payload,
                    "provider": {"name": "dashscope", "base_url": base_url, "api_key_env": api_key_env},
                }
            )
        except Exception as exc:
            logger.exception("Model ping failed model=%s", model_name)
            return Response(
                {"result": "error", "message": str(exc), "model_name": model_name},
                status=status.HTTP_502_BAD_GATEWAY,
            )
