import time
import threading
from typing import Dict, Optional

class RateLimitExceeded(Exception):
    pass

class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.tokens = calls
        self.last_update = time.time()
        self.lock = threading.Lock()

    def _replace_tokens(self):
        now = time.time()
        elapsed = now - self.last_update
        if elapsed > self.period:
            self.tokens = self.calls
            self.last_update = now

    def acquire(self):
        with self.lock:
            self._replace_tokens()
            if self.tokens > 0:
                self.tokens -= 1
                return True
            else:
                raise RateLimitExceeded("Rate limit exceeded. Please try again later.")

# Global limiter instance
from .config import settings
limiter = RateLimiter(calls=settings.RATE_LIMIT_CALLS, period=settings.RATE_LIMIT_PERIOD)
