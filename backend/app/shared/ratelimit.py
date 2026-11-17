"""Small in-process sliding-window rate limiter (prototype; use Redis for multi-instance)."""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.exceptions import TooManyRequests


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                raise TooManyRequests("Too many requests. Please try again later.")
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


login_limiter = RateLimiter(limit=20, window_seconds=60)
