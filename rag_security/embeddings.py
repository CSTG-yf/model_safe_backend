import logging
from typing import Iterable

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    """Small Ollama embedding client using the HTTP API."""

    def __init__(self, base_url="", model=""):
        self.base_url = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_EMBEDDING_MODEL", "bge-m3")
        self.timeout = int(getattr(settings, "OLLAMA_EMBEDDING_TIMEOUT", 120))

    def embed_documents(self, texts: Iterable[str]):
        texts = list(texts)
        if not texts:
            return []
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload.get("embeddings")
            if embeddings:
                return embeddings
        except Exception:
            logger.exception("Ollama /api/embed failed; falling back to /api/embeddings.")

        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str):
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding")
        if not embedding:
            raise ValueError("Ollama embedding response does not contain embedding.")
        return embedding

