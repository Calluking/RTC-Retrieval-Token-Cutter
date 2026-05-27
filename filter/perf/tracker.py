"""Token savings tracker — records Filter compression metrics."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class FilterSnapshot:
    commands_processed: int = 0
    original_tokens: int = 0
    transformed_tokens: int = 0
    tokens_saved: int = 0
    save_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "commands_processed": self.commands_processed,
            "original_tokens": self.original_tokens,
            "transformed_tokens": self.transformed_tokens,
            "tokens_saved": self.tokens_saved,
            "save_rate_pct": round(self.save_rate * 100, 2),
        }


class FilterTracker:
    """Thread-safe tracker for Filter token savings.

    Records: commands processed, original size, transformed size,
    and cumulative tokens saved.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processed = 0
        self._original = 0
        self._transformed = 0

    def record(
        self,
        original_text: str,
        transformed_text: str,
    ) -> None:
        """Record a transformation event."""
        with self._lock:
            self._processed += 1
            self._original += self._estimate_tokens(original_text)
            self._transformed += self._estimate_tokens(transformed_text)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token for English."""
        return max(1, len(text) // 4)

    def snapshot(self) -> FilterSnapshot:
        with self._lock:
            saved = self._original - self._transformed
            rate = saved / self._original if self._original else 0.0
            return FilterSnapshot(
                commands_processed=self._processed,
                original_tokens=self._original,
                transformed_tokens=self._transformed,
                tokens_saved=max(0, saved),
                save_rate=rate,
            )

    def snapshot_and_reset(self) -> FilterSnapshot:
        with self._lock:
            snap = self.snapshot()
            self._reset_unlocked()
            return snap

    def reset(self) -> None:
        with self._lock:
            self._reset_unlocked()

    def _reset_unlocked(self) -> None:
        self._processed = 0
        self._original = 0
        self._transformed = 0


# Global singleton
_global_tracker: FilterTracker | None = None
_tracker_lock = threading.Lock()


def get_tracker() -> FilterTracker:
    global _global_tracker
    with _tracker_lock:
        if _global_tracker is None:
            _global_tracker = FilterTracker()
        return _global_tracker