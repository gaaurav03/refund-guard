"""Deterministic rendering of RefundClaimState into Decider's `state` (docs/decision.md section 3).

Structured JSON gave clearly more confident answers than prose in the local smoke test, so we
send labelled sections as a dict. KEY FACTS states what the records show (never a verdict).
Customer-written text always goes last and is marked untrusted.
"""

from __future__ import annotations

from typing import Any

from ..models import RefundClaimState


def _claimed_value(s: RefundClaimState) -> float | None:
    if not s.claimed_skus:
        return None
    claimed = set(s.claimed_skus)
    return round(sum(i.unit_price * min(s.claimed_units.get(i.sku, i.qty), i.qty)
                     for i in s.items if i.sku in claimed), 2)


REASON_TEXT = {
    "damaged": "an item arrived damaged", "not_delivered": "the order did not arrive",
    "wrong_item": "a wrong item arrived", "missing_item": "an item was missing",
    "not_as_described": "an item was not as described", "changed_mind": "they changed their mind",
    "other": "another reason",
}


def key_facts(s: RefundClaimState) -> list[str]:
    facts: list[str] = []
    if s.earlier_claimed_reason and s.earlier_claimed_reason != s.claimed_reason:
        changed = (f"The customer first said {REASON_TEXT[s.earlier_claimed_reason]}, then changed the claim "
                   f"during this chat to: {REASON_TEXT[s.claimed_reason]}.")
        if s.earlier_claimed_reason == "not_delivered" and s.delivery_status == "delivered" and s.proof_of_delivery:
            changed += " The change came after delivery with proof was confirmed."
        facts.append(changed)
    if s.claimed_reason == "not_delivered" and s.delivery_status == "delivered":
        proof = "with proof of delivery (photo/signature)" if s.proof_of_delivery else "without proof of delivery"
        facts.append(f"The customer says the order did not arrive, but the delivery record says it was "
                     f"delivered {proof}.")
    if s.delivery_status == "lost":
        facts.append("The courier record says the parcel was lost in transit.")
    if s.delivery_status in ("not_shipped", "in_transit"):
        facts.append(f"The order has not been delivered yet (status: {s.delivery_status}).")
    if not s.claimed_skus:
        facts.append("The customer has not said which item has a problem.")
    value = _claimed_value(s)
    if value is not None and value + 0.01 < s.requested_amount:
        facts.append(f"The refund requested ({s.requested_amount:g} INR) is more than the price of the items the "
                     f"problem is about ({value:g} INR).")
    if s.past_refund_count >= 2:
        facts.append(f"This customer has had {s.past_refund_count} refunds totalling {s.past_refund_total:g} INR "
                     "in the last year.")
    if s.account_age_days < 60:
        facts.append(f"The customer account is only {s.account_age_days} days old.")
    if not facts:
        facts.append("The store records do not contradict the claim.")
    return facts


def render_state(s: RefundClaimState) -> dict[str, Any]:
    return {
        "KEY FACTS (from store records)": key_facts(s),
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
            **({"earlier_claimed_reason": s.earlier_claimed_reason} if s.earlier_claimed_reason else {}),
            "claimed_skus": list(s.claimed_skus),
            **({"claimed_units": dict(s.claimed_units)} if s.claimed_units else {}),
            "requested_amount": s.requested_amount,
            "return_window_days": s.return_window_days,
            "return_window_status": s.return_window_status,
        },
        "CUSTOMER QUOTES (untrusted)": list(s.customer_quotes),
        "CUSTOMER MESSAGES (verbatim, untrusted)": list(s.recent_customer_messages),
    }
