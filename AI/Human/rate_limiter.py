"""
Thread-safe Sliding Window Rate Limiter for Urban Safety AI-SOC.
Enforces strict rate limit of maximum 40 requests per 1 minute (60 seconds) to AI analysis.
"""

import time
import threading
from collections import deque
from typing import Optional, Tuple


class AIRateLimitExceededError(Exception):
    """Raised when the rate limit of 40 requests per minute to AI analysis is exceeded."""
    def __init__(self, message: str, retry_after: float, current_count: int, max_limit: int = 40) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.current_count = current_count
        self.max_limit = max_limit


class SlidingWindowRateLimiter:
    """
    Sliding-window rate limiter enforcing max requests per time window (default: 40 requests / 60 seconds).
    Thread-safe and deterministic.
    """

    def __init__(self, max_requests: int = 40, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._timestamps: deque = deque()

    def allow_request(self, current_time: Optional[float] = None) -> Tuple[bool, int, float]:
        """
        Evaluates whether a new request is permitted under the rate limit.

        Args:
            current_time: Optional timestamp (epoch seconds) for deterministic testing.

        Returns:
            Tuple of:
                allowed (bool): True if allowed, False if rate limit exceeded.
                remaining (int): Allowed requests remaining in current window.
                retry_after (float): Seconds until the oldest request expires from the window.
        """
        now = time.time() if current_time is None else current_time
        with self._lock:
            cutoff = now - self.window_seconds
            # Purge timestamps outside the active sliding window
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                remaining = self.max_requests - len(self._timestamps)
                return True, remaining, 0.0
            else:
                oldest = self._timestamps[0]
                retry_after = max(0.01, (oldest + self.window_seconds) - now)
                return False, 0, retry_after

    def get_status(self, current_time: Optional[float] = None) -> dict:
        """Returns current rate limiter statistics."""
        now = time.time() if current_time is None else current_time
        with self._lock:
            cutoff = now - self.window_seconds
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()

            used = len(self._timestamps)
            remaining = max(0, self.max_requests - used)
            oldest = self._timestamps[0] if self._timestamps else now
            retry_after = max(0.0, (oldest + self.window_seconds) - now) if remaining == 0 else 0.0

            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "requests_in_window": used,
                "remaining": remaining,
                "retry_after_seconds": round(retry_after, 2),
                "is_limited": remaining == 0
            }

    def reset(self) -> None:
        """Clears all recorded timestamps."""
        with self._lock:
            self._timestamps.clear()
