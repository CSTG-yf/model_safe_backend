import math
import re

from django.conf import settings

from .chroma_client import ChromaHttpClient
from .models import RagDocument


TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokenize(text):
    return TOKEN_PATTERN.findall((text or "").lower())


class SimpleKeywordRetriever:
    """DB-backed fallback retriever for demos and tests."""

    def retrieve(self, knowledge_base, question, top_k=5, include_sensitive=False, min_trust_level=""):
        docs = RagDocument.objects.filter(knowledge_base=knowledge_base)
        if not include_sensitive:
            docs = docs.exclude(document_type="sensitive")
        if min_trust_level == "trusted":
            docs = docs.filter(trust_level="trusted")
        query_tokens = tokenize(question)
        scored = []
        for doc in docs:
            score = self._score(query_tokens, doc)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            scored = [(0.01, doc) for doc in docs.order_by("-is_poisoned", "id")[:top_k]]
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "document_type": doc.document_type,
                "trust_level": doc.trust_level,
                "is_poisoned": doc.is_poisoned,
                "contains_injection": doc.contains_injection,
                "poison_goal": doc.poison_goal,
                "score": round(score, 4),
                "source": "keyword",
            }
            for score, doc in scored[:top_k]
        ]

    @staticmethod
    def _score(query_tokens, doc):
        doc_tokens = tokenize(f"{doc.title} {doc.content}")
        if not query_tokens or not doc_tokens:
            return 0
        overlap = len(set(query_tokens) & set(doc_tokens))
        poison_boost = 0.1 if doc.is_poisoned else 0
        return overlap / math.sqrt(len(set(doc_tokens)) + 1) + poison_boost


class HybridRagRetriever:
    def __init__(self):
        self.keyword = SimpleKeywordRetriever()
        self.chroma = ChromaHttpClient()

    def retrieve(self, knowledge_base, question, top_k=5, include_sensitive=False, use_chroma=False, min_trust_level=""):
        if not use_chroma:
            return self.keyword.retrieve(knowledge_base, question, top_k, include_sensitive, min_trust_level)
        try:
            payload = self.chroma.query(question, n_results=top_k)
            return self._from_chroma_payload(payload, include_sensitive)
        except Exception:
            if getattr(settings, "RAG_FAIL_OPEN_TO_KEYWORD", True):
                return self.keyword.retrieve(knowledge_base, question, top_k, include_sensitive, min_trust_level)
            raise

    @staticmethod
    def _from_chroma_payload(payload, include_sensitive):
        docs = []
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        for content, metadata, distance in zip(documents, metadatas, distances):
            if metadata.get("document_type") == "sensitive" and not include_sensitive:
                continue
            docs.append({
                "id": metadata.get("document_id"),
                "title": metadata.get("title", ""),
                "content": content,
                "document_type": metadata.get("document_type", "normal"),
                "trust_level": metadata.get("trust_level", "normal"),
                "is_poisoned": bool(metadata.get("is_poisoned", False)),
                "contains_injection": bool(metadata.get("contains_injection", False)),
                "poison_goal": metadata.get("poison_goal", ""),
                "score": 1 - float(distance or 0),
                "source": "chroma",
            })
        return docs

