"""Embedding service using OpenAI API (for evaluation agent)."""
from typing import List, Optional
import hashlib
from api.config.settings import settings

# In-memory embedding cache (cost optimization): max 500 entries
_embedding_cache: dict = {}
_embedding_cache_max = 500


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OpenAIEmbeddingService:
    """Service for generating embeddings using OpenAI API (with optional cache for cost)."""

    def __init__(self, api_key: str = None, use_cache: bool = True):
        self.api_key = api_key or getattr(settings, "openai_api_key", None)
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY.")
        self.model = getattr(settings, "openai_embedding_model", "text-embedding-3-small")
        self._client = None
        self._use_cache = use_cache

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text (cached when use_cache=True)."""
        global _embedding_cache
        if self._use_cache:
            key = _cache_key(text)
            if key in _embedding_cache:
                try:
                    from rag.answer.cost_report import cost_report_tracker
                    cost_report_tracker.add_cache_hit()
                except Exception:
                    pass
                return _embedding_cache[key][:]
            try:
                from rag.answer.cost_report import cost_report_tracker
                cost_report_tracker.add_cache_miss()
            except Exception:
                pass
        try:
            r = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            try:
                from rag.answer.cost_report import cost_report_tracker
                cost_report_tracker.add_embedding_calls(1)
            except Exception:
                pass
            emb = list(r.data[0].embedding)
            if self._use_cache and len(_embedding_cache) < _embedding_cache_max:
                _embedding_cache[_cache_key(text)] = emb
            return emb
        except Exception as e:
            raise Exception(f"Error generating OpenAI embedding: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (OpenAI supports batch; cache not used for batch)."""
        if not texts:
            return []
        try:
            r = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            try:
                from rag.answer.cost_report import cost_report_tracker
                cost_report_tracker.add_embedding_calls(1)
            except Exception:
                pass
            by_idx = {d.index: list(d.embedding) for d in r.data}
            return [by_idx[i] for i in range(len(texts))]
        except Exception as e:
            raise Exception(f"Error generating OpenAI embeddings: {str(e)}")
