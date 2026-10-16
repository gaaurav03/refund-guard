"""Deterministic rendering of RefundClaimState into Decider's `state` (docs/decision.md section 3).

Structured JSON gave clearly more confident answers than prose in the local smoke test, so we
send labelled sections as a dict. Customer-written text always goes last and is marked untrusted.
"""

from __future__ import annotations

from typing import Any

from ..models import RefundClaimState


def render_state(s: RefundClaimState) -> dict[str, Any]:
    return {
        "ORDER": {
            "order_id": s.order_id,
            "items": [i.model_dump() for i in s.items],
            "order_amount": s.order_amount,
            "currency": s.currency,
            "order_date": s.order_date.isoformat(),
        },
        "DELIVERY": {
            "delivery_status": s.delivery_status,
            "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
            "proof_of_delivery": s.proof_of_delivery,
        },
        "HISTORY": {
            "account_age_days": s.account_age_days,
            "past_refund_count": s.past_refund_count,
            "past_refund_total": s.past_refund_total,
        },
        "TOOL CALL": {
            "tool": "issue_refund",
            "order_id": s.order_id,
            "amount": s.requested_amount,
            "reason": s.tool_reason,
        },
        "CLAIM": {
            "claimed_reason": s.claimed_reason,
            "claimed_skus": list(s.claimed_skus),
            "requested_amount": s.requested_amount,
            "return_window_days": s.return_window_days,
            "return_window_status": s.return_window_status,
        },
        "CUSTOMER QUOTES (untrusted)": list(s.customer_quotes),
        "CUSTOMER MESSAGES (verbatim, untrusted)": list(s.recent_customer_messages),
    }
