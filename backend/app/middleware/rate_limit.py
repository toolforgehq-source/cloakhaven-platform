"""In-memory token bucket rate limiting middleware."""

import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status

logger = logging.getLogger("cloakhaven.ratelimit")


class TokenBucket:
    """Simple token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens: dict[str, float] = defaultdict(lambda: float(capacity))
        self.last_time: dict[str, float] = defaultdict(time.monotonic)

    def consume(self, key: str) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_time[key]
        self.last_time[key] = now

        # Refill tokens
        self.tokens[key] = min(
            self.capacity, self.tokens[key] + elapsed * self.rate
        )

        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        return False

    def cleanup(self, max_age: float = 3600):
        """Remove stale entries older than max_age seconds."""
        now = time.monotonic()
        stale = [k for k, t in self.last_time.items() if now - t > max_age]
        for k in stale:
            del self.tokens[k]
            del self.last_time[k]


# Global rate limiters
# Public endpoints: 60 requests per minute per IP
public_limiter = TokenBucket(rate=60 / 60, capacity=60)

# Authenticated endpoints: 120 requests per minute per user
auth_limiter = TokenBucket(rate=120 / 60, capacity=120)

# Partner API: configurable per key, default 100/min
partner_limiter = TokenBucket(rate=100 / 60, capacity=100)

# Audit endpoint: 5 per hour per user (expensive operation)
audit_limiter = TokenBucket(rate=5 / 3600, capacity=5)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(
    key: str,
    bucket: TokenBucket,
    error_msg: str = "Rate limit exceeded. Please try again later.",
) -> None:
    """Check rate limit and raise 429 if exceeded."""
    if not bucket.consume(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg,
            headers={"Retry-After": "60"},
        )
