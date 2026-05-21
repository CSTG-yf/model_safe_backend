import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from openai import OpenAI

from core.models import ModelProvider


logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    content: str | None
    usage: dict[str, Any] | None = None
    model: str = ""
    provider: str = ""
    latency_ms: int | None = None
    raw: Any | None = None


@dataclass
class ChatRequest:
    model: str
    system_prompt: str
    user_prompt: str
    provider_name: str = "default"
    temperature: float = 0.3
    response_format: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ModelGateway:
    """Unified OpenAI-compatible model caller.

    The gateway is intentionally thin in this stage: it centralizes provider
    resolution, timeout/retry hooks, usage capture, and latency logging while
    keeping existing OneAPI-compatible behavior.
    """

    def __init__(self, provider_name="default"):
        self.provider = self.resolve_provider(provider_name)
        api_key = self._resolve_api_key(self.provider)
        if not api_key:
            raise ValueError(f"API key is not configured for provider '{self.provider.name}'.")
        self.client = OpenAI(api_key=api_key, base_url=self.provider.base_url)

    @classmethod
    def resolve_provider(cls, provider_name="default"):
        try:
            if provider_name != "default":
                provider = ModelProvider.objects.filter(name=provider_name, is_active=True).first()
                if provider:
                    return provider
                raise ValueError(f"Model provider '{provider_name}' is not configured.")

            provider = ModelProvider.objects.filter(name="default", is_active=True).first()
            if provider:
                return provider
        except (OperationalError, ProgrammingError):
            logger.warning("ModelProvider table is not ready; falling back to environment configuration.")

        return ModelProvider(
            name="default",
            provider_type="one_api",
            base_url=os.environ.get("ONE_API_BASE_URL", "http://127.0.0.1:3000/v1"),
            api_key_env="ONE_API_KEY",
            default_model=getattr(settings, "DEFAULT_MODEL_NAME", ""),
        )

    @staticmethod
    def _resolve_api_key(provider):
        if provider.api_key_env:
            return os.environ.get(provider.api_key_env, "")
        return os.environ.get("ONE_API_KEY", "")

    def chat(self, request: ChatRequest) -> ChatResult:
        params = {
            "model": request.model or self.provider.default_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            **request.extra,
        }
        if request.response_format:
            params["response_format"] = request.response_format

        started = time.monotonic()
        try:
            completion = self.client.chat.completions.create(**params)
            latency_ms = int((time.monotonic() - started) * 1000)
            usage = self._usage_to_dict(getattr(completion, "usage", None))
            content = completion.choices[0].message.content
            logger.info(
                "Model call completed provider=%s model=%s latency_ms=%s tokens=%s",
                self.provider.name,
                params["model"],
                latency_ms,
                usage.get("total_tokens") if usage else None,
            )
            return ChatResult(
                content=content,
                usage=usage,
                model=params["model"],
                provider=self.provider.name,
                latency_ms=latency_ms,
                raw=completion,
            )
        except Exception:
            logger.exception("Model call failed provider=%s model=%s", self.provider.name, params["model"])
            raise

    @staticmethod
    def _usage_to_dict(usage):
        if usage is None:
            return None
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if hasattr(usage, "__dict__"):
            return dict(usage.__dict__)
        return None


def chat_completion(
    model,
    system_prompt,
    user_prompt,
    provider_name="default",
    temperature=0.3,
    response_format=None,
    **extra,
):
    gateway = ModelGateway(provider_name=provider_name)
    return gateway.chat(
        ChatRequest(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            provider_name=provider_name,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
        )
    )
