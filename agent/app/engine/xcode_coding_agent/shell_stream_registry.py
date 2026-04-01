"""
Per-graph thread_id registry for live shell stdout/stderr chunks.

The queue is not stored in LangGraph checkpoint config (non-serializable).
"""

from __future__ import annotations

import queue
import threading
from typing import Optional

_lock = threading.Lock()
_queues: dict[str, queue.Queue] = {}


def register_shell_stream_queue(thread_id: str, max_chunks: int) -> Optional[queue.Queue]:
    """Create and register a bounded queue for this graph thread. Returns None if max_chunks <= 0."""
    if max_chunks <= 0:
        return None
    q: queue.Queue = queue.Queue(maxsize=max_chunks)
    with _lock:
        _queues[thread_id] = q
    return q


def get_shell_stream_queue_for_thread(thread_id: str) -> Optional[queue.Queue]:
    with _lock:
        return _queues.get(thread_id)


def unregister_shell_stream_queue(thread_id: str) -> None:
    with _lock:
        _queues.pop(thread_id, None)


def clear_shell_stream_registry() -> None:
    """Test helper: drop all registered queues."""
    with _lock:
        _queues.clear()
