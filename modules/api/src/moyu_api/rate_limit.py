"""In-memory login rate limiter."""

import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    def __init__(self, max_attempts=5, window_seconds=300):
        self.max_attempts = int(max_attempts)
        self.window_seconds = int(window_seconds)
        self._attempts = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key, now):
        window = self._attempts[key]
        while window and now - window[0] >= self.window_seconds:
            window.popleft()

    def allow(self, key):
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            return len(self._attempts[key]) < self.max_attempts

    def failure(self, key):
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._attempts[key].append(now)

    def success(self, key):
        with self._lock:
            self._attempts.pop(key, None)
