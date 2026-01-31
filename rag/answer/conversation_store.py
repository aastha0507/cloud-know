"""In-memory conversation store for follow-up context."""
from typing import List, Dict, Any
import threading

_store: Dict[str, List[Dict[str, str]]] = {}
_lock = threading.Lock()
MAX_MESSAGES_PER_CONVERSATION = 20


def get_messages(conversation_id: str) -> List[Dict[str, str]]:
    with _lock:
        return list(_store.get(conversation_id, []))


def append_message(conversation_id: str, role: str, content: str) -> None:
    with _lock:
        if conversation_id not in _store:
            _store[conversation_id] = []
        _store[conversation_id].append({"role": role, "content": content})
        _store[conversation_id] = _store[conversation_id][-MAX_MESSAGES_PER_CONVERSATION:]


def clear_conversation(conversation_id: str) -> None:
    with _lock:
        _store.pop(conversation_id, None)


class ConversationStore:
    """Thin wrapper for conversation_store functions."""
    get_messages = staticmethod(get_messages)
    append_message = staticmethod(append_message)
    clear = staticmethod(clear_conversation)


conversation_store = ConversationStore()
