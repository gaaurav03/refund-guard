"""Builds RefundClaimState from records + tool arguments + the extracted claim (docs/decision.md section 3).

Identity always comes from the session, never from the LLM. Customer messages are the raw
turns recorded by the session, never text rewritten by a model.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from ..models import MAX_MESSAGE_CHARS, MAX_RECENT_MESSAGES, RefundClaimState
from .extraction import ClaimExtraction

RETURN_WINDOW_DAYS = 30
HISTORY_DAYS = 365


def return_window_status(delivered_at: str | None, today: date, days: int = RETURN_WINDOW_DAYS) -> str:
    if not delivered_at:
        return "open"  # not delivered yet: the window has not started
    delivered = datetime.fromisoformat(delivered_at).date()
    return "open" if today <= delivered + timedelta(days=days) else "closed"


def refund_history(refunds: list[dict[str, Any]], today: date) -> tuple[int, float]:
    cutoff = today - timedelta(days=HISTORY_DAYS)
    recent = [r for r in refunds if datetime.fromisoformat(r["created_at"]).date() >= cutoff]
    return len(recent), round(sum(r["amount"] for r in recent), 2)


def refunded_on_order(refunds: list[dict[str, Any]], order_id: str) -> float:
    return round(float(sum(r["amount"] for r in refunds if r.get("order_id") == order_id)), 2)


def build_state(
    *,
    args: dict[str, Any],
    session_customer_id: str,
    order: dict[str, Any],
    delivery: dict[str, Any] | None,
    customer: dict[str, Any] | None,
    refunds: list[dict[str, Any]],
    claim: ClaimExtraction,
    recent_messages: list[str],
    today: date,
) -> RefundClaimState:
    """Raises ValueError/ValidationError on bad input; the caller fails closed."""
    delivery = delivery or {"delivery_status": "not_shipped", "delivered_at": None, "proof_of_delivery": False}
    count, total = refund_history(refunds, today)
    return RefundClaimState(
        order_id=order["order_id"],
        customer_id=session_customer_id,
        items=order["items"],
        order_amount=order["order_amount"],
        currency="INR",
        order_date=order["order_date"],
        delivery_status=delivery["delivery_status"],
        delivered_at=delivery.get("delivered_at"),
        proof_of_delivery=bool(delivery.get("proof_of_delivery", False)),
        return_window_days=RETURN_WINDOW_DAYS,
        return_window_status=return_window_status(delivery.get("delivered_at"), today),  # type: ignore[arg-type]
        account_age_days=int((customer or {}).get("account_age_days", 0)),
        past_refund_count=count,
        past_refund_total=total,
        claimed_reason=claim.claimed_reason,
        claimed_skus=claim.claimed_skus,
        claimed_units=claim.claimed_units,
        customer_quotes=claim.customer_quotes,
        requested_amount=float(args["amount"]),
        tool_reason=str(args.get("reason", ""))[:300],
        recent_customer_messages=[m[:MAX_MESSAGE_CHARS] for m in recent_messages[-MAX_RECENT_MESSAGES:]],
    )
