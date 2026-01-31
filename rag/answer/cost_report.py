"""Full cost report for evaluation: tokens (input/output), embedding calls, caching metrics."""
from typing import Dict, Any
import threading
from rag.answer.token_usage import get_usage as get_token_usage

_embedding_calls: int = 0
_cache_hits: int = 0
_cache_misses: int = 0
_llm_cache_hits: int = 0
_lock = threading.Lock()


def add_embedding_calls(count: int = 1) -> None:
    """Record embedding API calls (e.g. 1 per embed() or 1 per embed_batch())."""
    with _lock:
        global _embedding_calls
        _embedding_calls += count


def add_cache_hit() -> None:
    """Record a cache hit (if caching is implemented)."""
    with _lock:
        global _cache_hits
        _cache_hits += 1


def add_cache_miss() -> None:
    """Record a cache miss (if caching is implemented)."""
    with _lock:
        global _cache_misses
        _cache_misses += 1


def add_llm_cache_hit() -> None:
    """Record an LLM answer cache hit (repeated question + context)."""
    with _lock:
        global _llm_cache_hits
        _llm_cache_hits += 1


def get_full_report() -> Dict[str, Any]:
    """Return full cost report: token usage (input/output), embedding calls, caching metrics."""
    with _lock:
        token_usage = get_token_usage()
        return {
            "token_usage": {
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0),
            },
            "embedding_calls": _embedding_calls,
            "caching": {
                "enabled": _cache_hits > 0 or _cache_misses > 0 or _llm_cache_hits > 0,
                "cache_hits": _cache_hits,
                "cache_misses": _cache_misses,
                "llm_cache_hits": _llm_cache_hits,
            },
        }


def reset_report() -> None:
    """Reset all cost metrics (for a fresh evaluation run)."""
    with _lock:
        global _embedding_calls, _cache_hits, _cache_misses, _llm_cache_hits
        _embedding_calls = 0
        _cache_hits = 0
        _cache_misses = 0
        _llm_cache_hits = 0
    from rag.answer.token_usage import reset_usage
    reset_usage()


class CostReportTracker:
    add_embedding_calls = staticmethod(add_embedding_calls)
    add_cache_hit = staticmethod(add_cache_hit)
    add_cache_miss = staticmethod(add_cache_miss)
    add_llm_cache_hit = staticmethod(add_llm_cache_hit)
    get_full_report = staticmethod(get_full_report)
    reset = staticmethod(reset_report)


cost_report_tracker = CostReportTracker()
