"""
A simple async sliding-window rate limiter.

Used to keep Gemini API calls under whatever requests-per-minute quota the
configured API key/plan allows (e.g. 15/min on the free tier). This is
proactive pacing, not reactive retry-after-failure: every caller awaits
`acquire()` before making a request, and the limiter makes them wait if
that would exceed the allowed rate -- so pages stop hitting 429 in the
first place instead of failing and retrying into the same wall.

This complements (does not replace) the retry/backoff logic in
gemini_service.py, which still handles genuinely transient errors
(server hiccups, network blips) that pacing alone can't prevent.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until it's safe to make another call without exceeding the quota."""
        async with self._lock:
            while True:
                now = time.monotonic()

                # Drop timestamps that have aged out of the window.
                while self._timestamps and now - self._timestamps[0] >= self.period_seconds:
                    self._timestamps.popleft()

                if len(self._timestamps) < self.max_calls:
                    self._timestamps.append(now)
                    return

                # Wait until the oldest call in the window expires, plus a
                # small safety margin to avoid boundary-timing races.
                wait_seconds = self.period_seconds - (now - self._timestamps[0]) + 0.1
                await asyncio.sleep(max(wait_seconds, 0.05))