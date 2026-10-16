from __future__ import annotations

from typing import Any

import pytest
from app.models import RefundClaimState


def make_state(**overrides: Any) -> RefundClaimState:
    """S1-style genuine claim: 1 cracked mug out of a 2-line order. Override any field."""
    base: dict[str, Any] = {
        "order_id": "ORD-1042",
        "customer_id": "CUST-007",
        "items": [
            {"sku": "MUG-BLU", "name": "Blue ceramic mug", "qty": 1, "unit_price": 450.0},
            {"sku": "TEA-ASM", "name": "Assam tea 250g", "qty": 2, "unit_price": 300.0},
        ],
        "order_amount": 1050.0,
        "currency": "INR",
        "order_date": "2026-10-02",
        "delivery_status": "delivered",
        "delivered_at": "2026-10-06T14:12:00+05:30",
        "proof_of_delivery": True,
        "return_window_days": 30,
        "return_window_status": "open",
        "account_age_days": 412,
        "past_refund_count": 0,
        "past_refund_total": 0.0,
        "claimed_reason": "damaged",
        "claimed_skus": ["MUG-BLU"],
        "customer_quotes": ["The mug arrived cracked down the side, I have a photo."],
        "requested_amount": 450.0,
        "tool_reason": "Item arrived damaged (cracked mug)",
        "recent_customer_messages": ["The mug arrived cracked down the side, I have a photo."],
    }
    base.update(overrides)
    return RefundClaimState.model_validate(base)


@pytest.fixture
def state() -> RefundClaimState:
    return make_state()
