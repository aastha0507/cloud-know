"""Token usage tracking for evaluation reporting."""
from typing import Dict, Any
import threading

_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
_lock = threading.Lock()


def add_usage(prompt_tokens: int, completion_tokens: int) -> None:
    with _lock:
        _usage["prompt_tokens"] += prompt_tokens
        _usage["completion_tokens"] += completion_tokens
        _usage["total_tokens"] += prompt_tokens + completion_tokens


def get_usage() -> Dict[str, int]:
    with _lock:
        return dict(_usage)


def reset_usage() -> None:
    with _lock:
        _usage["prompt_tokens"] = 0
        _usage["completion_tokens"] = 0
        _usage["total_tokens"] = 0


class TokenUsageTracker:
    add = staticmethod(add_usage)
    get = staticmethod(get_usage)
    reset = staticmethod(reset_usage)


token_usage_tracker = TokenUsageTracker()
