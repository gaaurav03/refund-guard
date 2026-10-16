"""Decision ledger keyed by toolUseId (ADR-04).

issue_refund executes only if the guard recorded approve/partial for that exact call and the
amount does not exceed the approved amount. This protects against direct calls or misconfiguration
even though the handler already returns Deny.
"""

from __future__ import annotations

import threading

from ..models import Decision


class Ledger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_tool_use: dict[str, Decision] = {}

    def record(self, tool_use_id: str, decision: Decision) -> None:
        with self._lock:
            self._by_tool_use[tool_use_id] = decision

    def authorize(self, tool_use_id: str, amount: float) -> float | None:
        """Return the amount this call may pay out (never above the approved amount), else None.

        One use per call: a second issue_refund with the same toolUseId gets nothing.
        """
        with self._lock:
            d = self._by_tool_use.pop(tool_use_id, None)
        if d is None or d.outcome not in ("approve", "partial") or amount <= 0 or d.approved_amount <= 0:
            return None
        return round(min(amount, d.approved_amount), 2)
