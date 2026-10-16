"""RefundGuard: the Strands InterventionHandler that puts Decider 2B in front of issue_refund.

Flow (docs/decision.md section 7): build evidence -> pre-checks -> Decider -> policy -> log ->
ledger -> Proceed / Guide / Deny. Any failure denies the call (fail closed).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from strands.interventions import Deny, Guide, InterventionHandler, Proceed

from ..models import Decision
from ..store.repo import Repo
from .decider_client import DeciderClient
from .engine import decide
from .evidence import build_state, refunded_on_order
from .extraction import ConverseFn, extract_claim
from .ledger import Ledger
from .policy import Thresholds, fallback_decision

log = logging.getLogger(__name__)

GUARDED_TOOL = "issue_refund"


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class RefundGuard(InterventionHandler):
    name = "refund-guard"
    on_error = "deny"  # if this handler itself crashes, the tool call is denied

    def __init__(
        self,
        *,
        repo: Repo,
        decider: DeciderClient,
        converse: ConverseFn,
        ledger: Ledger,
        thresholds: Thresholds,
        high_value_escalate_inr: float,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._repo = repo
        self._decider = decider
        self._converse = converse
        self._ledger = ledger
        self._t = thresholds
        self._high_value = high_value_escalate_inr
        self._today = today

    def before_tool_call(self, event: Any, **kwargs: Any) -> Any:
        if event.tool_use["name"] != GUARDED_TOOL:
            return Proceed()

        session = event.invocation_state.get("session")
        if session is None:
            return Deny(reason="Refund not permitted: no customer session.")

        tool_use_id = event.tool_use["toolUseId"]
        args = event.tool_use.get("input") or {}
        t0 = time.perf_counter()
        decision = self._decide(args, session)
        total_ms = (time.perf_counter() - t0) * 1000

        record = self._record(decision, args, session, tool_use_id, total_ms)
        try:
            self._repo.put_decision(record)
            if decision.outcome == "escalate":
                self._repo.put_review({"decision_id": record["decision_id"], "status": "pending", **record})
        except Exception:
            log.exception("could not log decision; denying")  # never move money without a log entry
            return Deny(reason="Refund not permitted right now. Tell the customer a person will follow up.")

        session.decisions.append(record)
        self._ledger.record(tool_use_id, decision)

        if decision.outcome in ("approve", "partial"):
            return Proceed()
        if decision.policy_step == "decider:args_ungrounded":
            return Guide(feedback=decision.agent_feedback)
        return Deny(reason=decision.agent_feedback)

    def _decide(self, args: dict[str, Any], session: Any) -> Decision:
        try:
            order_id = str(args.get("order_id", "")).strip()
            order = self._repo.get_order(order_id) if order_id else None
            if order is None:
                return decide(client=self._decider, thresholds=self._t, high_value_escalate_inr=self._high_value,
                              order_found=False, order_customer_id=None, session_customer_id=session.customer_id,
                              state=None, refunded_on_order=0.0)
            refunds = self._repo.list_refunds(session.customer_id)
            claim = extract_claim(self._converse, session.recent_customer_messages, order["items"])
            state = build_state(
                args=args,
                session_customer_id=session.customer_id,
                order=order,
                delivery=self._repo.get_delivery(order_id),
                customer=self._repo.get_customer(session.customer_id),
                refunds=refunds,
                claim=claim,
                recent_messages=session.recent_customer_messages,
                today=self._today(),
            )
            return decide(
                client=self._decider,
                thresholds=self._t,
                high_value_escalate_inr=self._high_value,
                order_found=True,
                order_customer_id=order["customer_id"],
                session_customer_id=session.customer_id,
                state=state,
                refunded_on_order=refunded_on_order(refunds, order_id),
            )
        except Exception as e:
            log.warning("guard could not build a decision (%s: %s); escalating", type(e).__name__, e)
            return fallback_decision(type(e).__name__)

    @staticmethod
    def _record(decision: Decision, args: dict[str, Any], session: Any, tool_use_id: str,
                total_ms: float) -> dict[str, Any]:
        d = decision.decider
        return {
            "decision_id": f"D-{uuid.uuid4().hex[:12]}",
            "created_at": datetime.now(UTC).isoformat(),
            "session_id": session.session_id,
            "source": session.mode,
            "gullible": bool(getattr(session, "gullible", False)),
            "customer_id": session.customer_id,
            "tool_use_id": tool_use_id,
            "order_id": str(args.get("order_id", "")),
            "requested_amount": _safe_float(args.get("amount")),
            "outcome": decision.outcome,
            "approved_amount": decision.approved_amount,
            "decided_by": decision.decided_by,
            "policy_step": decision.policy_step,
            "rule_id": decision.rule_id,
            "signals": dict(d.signals) if d else None,
            "decider_latency_ms": d.latency_ms if d else None,
            "decision_latency_ms": round(total_ms, 1),
        }
