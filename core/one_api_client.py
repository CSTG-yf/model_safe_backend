import logging
import os
from typing import Any, Tuple

from openai import OpenAI


logger = logging.getLogger(__name__)


def get_available_models() -> list[str]:
    logger.info("Fetching available models from OneAPI")
    try:
        client = OpenAI(
            api_key=OneAPIClient.API_KEY,
            base_url=OneAPIClient.API_BASE_URL,
        )
        models_response = client.models.list()
        return [model.id for model in models_response.data]
    except Exception:
        logger.exception("Failed to fetch model list from OneAPI")
        return []


class OneAPIClient:
    API_BASE_URL = os.environ.get("ONE_API_BASE_URL", "http://127.0.0.1:3000/v1")
    API_KEY = os.environ.get("ONE_API_KEY", "")

    def __init__(self, model: str):
        self.model = model
        if not self.API_KEY:
            raise ValueError("ONE_API_KEY is not configured.")

        self.client = OpenAI(
            api_key=self.API_KEY,
            base_url=self.API_BASE_URL,
        )
        logger.info("OneAPI client initialized model=%s", self.model)

    def get_chat_response(self, system_prompt: str, prompt: str, **kwargs) -> str:
        params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        }
        try:
            completion = self.client.chat.completions.create(**params)
            return completion.choices[0].message.content
        except Exception:
            logger.exception("Model call failed model=%s", self.model)
            raise

    def get_chat_response_with_usage(self, system_prompt: str, prompt: str, **kwargs) -> Tuple[str | None, Any | None]:
        params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        }
        try:
            completion = self.client.chat.completions.create(**params)
            return completion.choices[0].message.content, completion.usage
        except Exception:
            logger.exception("Model call with usage failed model=%s", self.model)
            return None, None
