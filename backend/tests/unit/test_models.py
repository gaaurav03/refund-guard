from __future__ import annotations

import pytest
from app.guard.state_render import render_state
from app.models import RefundClaimState
from pydantic import ValidationError

from tests.conftest import make_state


@pytest.mark.parametrize("override", [
    {"claimed_reason": "because"},
    {"delivery_status": "teleported"},
    {"order_amount": -5},
    {"customer_quotes": ["q"] * 6},
    {"customer_quotes": ["x" * 301]},
    {"recent_customer_messages": ["x" * 501]},
    {"unexpected_field": 1},
])
def test_state_rejects_invalid(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make_state(**override)


def test_state_json_round_trip() -> None:
    s = make_state()
    assert RefundClaimState.model_validate_json(s.model_dump_json()) == s


def test_render_is_deterministic_and_untrusted_text_last() -> None:
    s = make_state()
    a, b = render_state(s), render_state(s)
    assert a == b
    keys = list(a)
    assert keys[-2:] == ["CUSTOMER QUOTES (untrusted)", "CUSTOMER MESSAGES (verbatim, untrusted)"]
    assert a["TOOL CALL"]["amount"] == s.requested_amount
