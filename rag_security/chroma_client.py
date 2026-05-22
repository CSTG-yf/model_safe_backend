import logging

import requests
from django.conf import settings

from .embeddings import OllamaEmbeddingClient


logger = logging.getLogger(__name__)


class ChromaHttpClient:
    """Chroma HTTP adapter.

    This client intentionally uses requests instead of the chromadb SDK so the
    backend remains lightweight. If Chroma changes its HTTP API, failures are
    isolated to this adapter and RAG can still fall back to DB keyword search.
    """

    def __init__(self, base_url="", collection_name="", embedder=None):
        self.base_url = (base_url or getattr(settings, "CHROMA_BASE_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.collection_name = collection_name or getattr(settings, "CHROMA_COLLECTION_NAME", "ai_evaluation_rag")
        self.timeout = int(getattr(settings, "CHROMA_TIMEOUT", 30))
        self.embedder = embedder or OllamaEmbeddingClient()
        self._collection_id = None

    def add_documents(self, documents):
        if not documents:
            return {"indexed": 0, "collection": self.collection_name}
        collection_id = self._get_or_create_collection_id()
        texts = [doc["content"] for doc in documents]
        embeddings = self.embedder.embed_documents(texts)
        payload = {
            "ids": [doc["id"] for doc in documents],
            "documents": texts,
            "embeddings": embeddings,
            "metadatas": [doc.get("metadata", {}) for doc in documents],
        }
        response = requests.post(f"{self.base_url}/api/v1/collections/{collection_id}/add", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return {"indexed": len(documents), "collection": self.collection_name, "collection_id": collection_id}

    def query(self, query_text, n_results=5):
        collection_id = self._get_or_create_collection_id()
        query_embedding = self.embedder.embed_query(query_text)
        payload = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        response = requests.post(f"{self.base_url}/api/v1/collections/{collection_id}/query", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get_or_create_collection_id(self):
        if self._collection_id:
            return self._collection_id
        collection = self._get_collection()
        if collection is None:
            collection = self._create_collection()
        self._collection_id = collection.get("id") or collection.get("uuid") or self.collection_name
        return self._collection_id

    def _get_collection(self):
        response = requests.get(f"{self.base_url}/api/v1/collections/{self.collection_name}", timeout=self.timeout)
        if response.status_code == 200:
            return response.json()
        response = requests.get(f"{self.base_url}/api/v1/collections", timeout=self.timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        collections = payload.get("collections", payload) if isinstance(payload, dict) else payload
        for item in collections:
            if item.get("name") == self.collection_name:
                return item
        return None

    def _create_collection(self):
        response = requests.post(
            f"{self.base_url}/api/v1/collections",
            json={"name": self.collection_name, "metadata": {"hnsw:space": "cosine"}},
            timeout=self.timeout,
        )
        if response.status_code in {200, 201}:
            return response.json()
        if response.status_code == 409:
            collection = self._get_collection()
            if collection:
                return collection
            response.raise_for_status()
        response.raise_for_status()
        return response.json()
