"""Token bucket rate limiting with SQLite persistence.

Buckets survive restarts and work correctly on single-instance deploys.
Falls back to in-memory if the DB write fails (e.g. during tests).
"""

import time
import logging
import sqlite3
import os
from collections import defaultdict
from fastapi import Request, HTTPException, status

logger = logging.getLogger("cloakhaven.ratelimit")

# Persistent storage path — same DB file used by the app
_DB_PATH = "/data/app.db" if os.path.isdir("/data") else "./cloakhaven.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table():
    """Create the rate_limit_buckets table if it doesn't exist."""
    try:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_buckets (
                bucket_name TEXT NOT NULL,
                key TEXT NOT NULL,
                tokens REAL NOT NULL,
                last_time REAL NOT NULL,
                PRIMARY KEY (bucket_name, key)
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Could not create rate_limit_buckets table: %s", e)


# Create table on module load
_ensure_table()


class TokenBucket:
    """Token bucket with SQLite persistence and in-memory fallback."""

    def __init__(self, name: str, rate: float, capacity: int):
        self.name = name
        self.rate = rate  # tokens per second
        self.capacity = capacity
        # In-memory fallback
        self._mem_tokens: dict[str, float] = defaultdict(lambda: float(capacity))
        self._mem_last_time: dict[str, float] = defaultdict(time.monotonic)

    def consume(self, key: str) -> bool:
        try:
            return self._consume_persistent(key)
        except Exception:
            return self._consume_memory(key)

    def _consume_persistent(self, key: str) -> bool:
        now = time.time()
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT tokens, last_time FROM rate_limit_buckets WHERE bucket_name=? AND key=?",
                (self.name, key),
            ).fetchone()

            if row:
                tokens, last_time = row
                elapsed = now - last_time
                tokens = min(self.capacity, tokens + elapsed * self.rate)
            else:
                tokens = float(self.capacity)

            if tokens >= 1:
                tokens -= 1
                conn.execute(
                    """INSERT INTO rate_limit_buckets (bucket_name, key, tokens, last_time)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(bucket_name, key) DO UPDATE
                       SET tokens=excluded.tokens, last_time=excluded.last_time""",
                    (self.name, key, tokens, now),
                )
                conn.commit()
                return True
            else:
                conn.execute(
                    """INSERT INTO rate_limit_buckets (bucket_name, key, tokens, last_time)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(bucket_name, key) DO UPDATE
                       SET tokens=excluded.tokens, last_time=excluded.last_time""",
                    (self.name, key, tokens, now),
                )
                conn.commit()
                return False
        finally:
            conn.close()

    def _consume_memory(self, key: str) -> bool:
        """Fallback to in-memory if persistent storage fails."""
        now = time.monotonic()
        elapsed = now - self._mem_last_time[key]
        self._mem_last_time[key] = now
        self._mem_tokens[key] = min(
            self.capacity, self._mem_tokens[key] + elapsed * self.rate
        )
        if self._mem_tokens[key] >= 1:
            self._mem_tokens[key] -= 1
            return True
        return False

    def cleanup(self, max_age: float = 3600):
        """Remove stale entries older than max_age seconds."""
        try:
            conn = _get_conn()
            cutoff = time.time() - max_age
            conn.execute(
                "DELETE FROM rate_limit_buckets WHERE bucket_name=? AND last_time<?",
                (self.name, cutoff),
            )
            conn.commit()
            conn.close()
        except Exception:
            now = time.monotonic()
            stale = [k for k, t in self._mem_last_time.items() if now - t > max_age]
            for k in stale:
                del self._mem_tokens[k]
                del self._mem_last_time[k]


# Global rate limiters
# Public endpoints: 60 requests per minute per IP
public_limiter = TokenBucket(name="public", rate=60 / 60, capacity=60)

# Authenticated endpoints: 120 requests per minute per user
auth_limiter = TokenBucket(name="auth", rate=120 / 60, capacity=120)

# Partner API: configurable per key, default 100/min
partner_limiter = TokenBucket(name="partner", rate=100 / 60, capacity=100)

# Audit endpoint: 5 per hour per user (expensive operation)
audit_limiter = TokenBucket(name="audit", rate=5 / 3600, capacity=5)

# Scan endpoints: 10 scans per hour per IP (expensive, triggers external API calls)
scan_limiter = TokenBucket(name="scan", rate=10 / 3600, capacity=10)


# ── Daily scan cap ──
# Limits the number of *unique names* an IP can scan per calendar day.
# Prevents bulk enumeration even if per-hour limits are not exceeded.
_DAILY_SCAN_CAP = 20  # max unique names per IP per day


def _ensure_daily_cap_table():
    """Create the daily_scan_log table if it doesn't exist."""
    try:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_scan_log (
                ip TEXT NOT NULL,
                scanned_name TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (ip, scanned_name, scan_date)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_scan_ip_date
            ON daily_scan_log (ip, scan_date)
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Could not create daily_scan_log table: %s", e)


_ensure_daily_cap_table()


def check_daily_scan_cap(ip: str, name: str) -> None:
    """Check if this IP has exceeded its daily unique-name scan cap.

    Raises 429 if the IP has already scanned _DAILY_SCAN_CAP distinct names today.
    If the name was already scanned today by this IP, it doesn't count again
    (re-checking the same person is free).
    """
    import datetime as _dt
    today = _dt.date.today().isoformat()
    try:
        conn = _get_conn()
        # Check if this exact (ip, name, date) already exists — free re-check
        existing = conn.execute(
            "SELECT 1 FROM daily_scan_log WHERE ip=? AND scanned_name=? AND scan_date=?",
            (ip, name.lower().strip(), today),
        ).fetchone()
        if existing:
            conn.close()
            return  # Already scanned today — no additional cost

        # Count unique names scanned today by this IP
        count_row = conn.execute(
            "SELECT COUNT(*) FROM daily_scan_log WHERE ip=? AND scan_date=?",
            (ip, today),
        ).fetchone()
        count = count_row[0] if count_row else 0

        if count >= _DAILY_SCAN_CAP:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily scan limit reached ({_DAILY_SCAN_CAP} unique people per day). "
                       f"Please try again tomorrow or create an account for higher limits.",
                headers={"Retry-After": "3600"},
            )

        # Log this scan
        conn.execute(
            "INSERT OR IGNORE INTO daily_scan_log (ip, scanned_name, scan_date, created_at) VALUES (?, ?, ?, ?)",
            (ip, name.lower().strip(), today, time.time()),
        )
        conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Daily scan cap check failed (allowing request): %s", e)


def cleanup_daily_scan_log(days_to_keep: int = 2) -> None:
    """Remove old daily scan log entries."""
    import datetime as _dt
    cutoff = (_dt.date.today() - _dt.timedelta(days=days_to_keep)).isoformat()
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM daily_scan_log WHERE scan_date < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Daily scan log cleanup failed: %s", e)


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
