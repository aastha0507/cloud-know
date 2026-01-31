"""Answer generation service: retrieval + OpenAI chat with citations and no hallucination."""
import hashlib
from typing import List, Dict, Any, Optional
from api.config.settings import settings
from rag.answer.conversation_store import get_messages, append_message
from rag.answer.token_usage import token_usage_tracker

# In-memory LLM answer cache (question + context + history) -> {answer, sources}; max 200 entries
_llm_answer_cache: Dict[str, Dict[str, Any]] = {}
_llm_answer_cache_keys: List[str] = []
_LLM_ANSWER_CACHE_MAX = 200


def _llm_cache_key(question: str, context: str, history: List[Dict[str, str]]) -> str:
    """Stable cache key for (question, context, recent history)."""
    hist = "|".join(f"{m.get('role','')}:{m.get('content','')}" for m in history)
    raw = f"{question.strip().lower()}|{context}|{hist}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

SYSTEM_PROMPT = """Answer using only the context below. Cite sources as [Source: title]. If not in context, say: "I don't have enough information in the knowledge base to answer that question." Be concise."""


class AnswerService:
    """Generate accurate, cited answers from the knowledge base using OpenAI."""

    def __init__(self):
        from rag.embedding.openai_embedding_service import OpenAIEmbeddingService
        from rag.vectorstore.vector_store import VectorStore
        from cloudknow_tools.tools.mongodb_tool import MongoDBAtlasTool
        from rag.retrieval.retrieval_service import RetrievalService
        from cloudknow_tools.tools import SpannerTool

        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the answer agent.")
        self._embedding = OpenAIEmbeddingService(api_key=api_key)
        collection_openai = getattr(settings, "mongodb_collection_openai", "documents")
        dims = getattr(settings, "openai_embedding_dimensions", 1536)
        mongodb_tool = MongoDBAtlasTool(
            collection_name=collection_openai,
            embedding_dimensions=dims,
        )
        self._vector_store = VectorStore(mongodb_tool=mongodb_tool)
        self._retrieval = RetrievalService(
            embedding_service=self._embedding,
            vector_store=self._vector_store,
            spanner_tool=SpannerTool(),
        )
        self._client = None
        self._model = getattr(settings, "openai_chat_model", "gpt-4o-mini")

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def answer(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        limit: int = 6,
        min_score: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks, generate an answer grounded in sources, cite documents,
        and handle no-info gracefully. Supports follow-up via conversation_id.
        """
        # Use OpenAI collection for retrieval (same embedding model as ingestion for that collection)
        try:
            results = self._retrieval.retrieve(
                query=question,
                limit=limit,
                source_filter=None,
                min_score=min_score,
            )
        except Exception as e:
            return {
                "answer": "I encountered an error searching the knowledge base. Please try again.",
                "sources": [],
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "answered_from_context": False,
                "error": str(e),
            }

        # No relevant documents — do not call LLM; avoid hallucination
        if not results:
            return {
                "answer": "I don't have enough information in the knowledge base to answer that question. Please try rephrasing or ensure the relevant documents have been ingested.",
                "sources": [],
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "answered_from_context": False,
            }

        # Build context with clear source labels; cap per-chunk size (enough to contain answers, not cut them off)
        max_chunk_chars = 450
        context_parts = []
        seen_titles = set()
        for i, r in enumerate(results, 1):
            title = "Unknown document"
            if r.get("document") and r["document"].get("title"):
                title = r["document"]["title"]
            elif r.get("chunk_metadata", {}).get("file_name"):
                title = r["chunk_metadata"]["file_name"]
            content = r.get("content", r.get("content_preview", ""))
            if len(content) > max_chunk_chars:
                content = content[:max_chunk_chars] + "..."
            context_parts.append(f"[Source: {title}]\n{content}")
            seen_titles.add(title)
        context = "\n\n---\n\n".join(context_parts)

        # Conversation history for follow-ups
        history = []
        if conversation_id:
            history = get_messages(conversation_id)
        history_tail = history[-4:]  # last 4 turns

        # LLM answer cache: same (question + context + history) -> reuse answer, skip token usage
        cache_key = _llm_cache_key(question, context, history_tail)
        if cache_key in _llm_answer_cache:
            try:
                from rag.answer.cost_report import cost_report_tracker
                cost_report_tracker.add_llm_cache_hit()
            except Exception:
                pass
            cached = _llm_answer_cache[cache_key]
            return {
                "answer": cached["answer"],
                "sources": cached["sources"],
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "answered_from_context": True,
            }

        # Build messages for OpenAI: system (with context) + history + current question
        system_content = f"{SYSTEM_PROMPT}\n\nContext:\n{context}"
        messages = [{"role": "system", "content": system_content}]
        for m in history_tail:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
        except Exception as e:
            return {
                "answer": "I encountered an error generating an answer. Please try again.",
                "sources": [],
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "answered_from_context": False,
                "error": str(e),
            }

        choice = response.choices[0] if response.choices else None
        answer_text = choice.message.content if choice else ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        token_usage_tracker.add(prompt_tokens, completion_tokens)

        if conversation_id:
            append_message(conversation_id, "user", question)
            append_message(conversation_id, "assistant", answer_text)

        # Store in LLM answer cache (evict oldest if over max)
        if len(_llm_answer_cache) >= _LLM_ANSWER_CACHE_MAX and cache_key not in _llm_answer_cache:
            while _llm_answer_cache_keys and len(_llm_answer_cache) >= _LLM_ANSWER_CACHE_MAX:
                old_key = _llm_answer_cache_keys.pop(0)
                _llm_answer_cache.pop(old_key, None)
        if cache_key not in _llm_answer_cache:
            _llm_answer_cache_keys.append(cache_key)
        _llm_answer_cache[cache_key] = {"answer": answer_text, "sources": list(seen_titles)}

        return {
            "answer": answer_text,
            "sources": list(seen_titles),
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "answered_from_context": True,
        }
