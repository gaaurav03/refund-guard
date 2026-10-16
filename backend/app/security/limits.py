"""Public-demo protections (docs/security.md section 4): rate limits, session caps, daily spend cap.

In-memory, which is fine for one EC2 instance. IPs are only kept as salted hashes.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime


def ip_hash(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


class Limits:
    def __init__(self, *, per_min_ip: int, sessions_per_ip_day: int, daily_budget_usd: float,
                 clock: object = time.time) -> None:
        self._per_min = per_min_ip
        self._sessions_per_day = sessions_per_ip_day
        self._budget = daily_budget_usd
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._sessions: dict[tuple[str, str], int] = defaultdict(int)
        self._spend: dict[str, float] = defaultdict(float)

    def _now(self) -> float:
        return float(self._clock())  # type: ignore[operator]

    def _day(self) -> str:
        return datetime.fromtimestamp(self._now(), UTC).strftime("%Y-%m-%d")

    def allow_request(self, ip_key: str) -> bool:
        now = self._now()
        with self._lock:
            q = self._hits[ip_key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self._per_min:
                return False
            q.append(now)
            return True

    def allow_new_session(self, ip_key: str) -> bool:
        with self._lock:
            key = (ip_key, self._day())
            if self._sessions[key] >= self._sessions_per_day:
                return False
            self._sessions[key] += 1
            return True

    def add_spend(self, usd: float) -> None:
        with self._lock:
            self._spend[self._day()] += usd

    def spend_today(self) -> float:
        with self._lock:
            return round(self._spend[self._day()], 4)

    def budget_exhausted(self) -> bool:
        return self.spend_today() >= self._budget
