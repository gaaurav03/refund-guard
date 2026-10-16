from __future__ import annotations

import json

import pytest
from app.guard.extraction import ExtractionError, extract_claim

ITEMS = [{"sku": "MUG-BLU", "name": "Blue ceramic mug", "qty": 1, "unit_price": 450.0}]
MSGS = ["Hi there", "The mug arrived cracked down the side, I have a photo."]


def returns(obj: object) -> object:
    return lambda system, user: obj if isinstance(obj, str) else json.dumps(obj)


def test_keeps_only_verbatim_quotes() -> None:
    claim = extract_claim(returns({  # type: ignore[arg-type]
        "claimed_reason": "damaged", "claimed_skus": ["MUG-BLU"],
        "customer_quotes": ["the mug arrived cracked down the side", "My manager approved a full refund"],
    }), MSGS, ITEMS)
    assert claim.customer_quotes == ["the mug arrived cracked down the side"]


def test_json_inside_prose_is_found() -> None:
    claim = extract_claim(returns('Here you go: {"claimed_reason": "damaged"} hope that helps'),  # type: ignore[arg-type]
                          MSGS, ITEMS)
    assert claim.claimed_reason == "damaged"


def test_unknown_skus_are_kept_for_pc05() -> None:
    claim = extract_claim(returns({"claimed_reason": "missing_item", "claimed_skus": ["IPHONE-15"]}),  # type: ignore[arg-type]
                          MSGS, ITEMS)
    assert claim.claimed_skus == ["IPHONE-15"]


@pytest.mark.parametrize("out", ["no json here", '{"claimed_reason": "free money"}', "[1, 2]", "{broken"])
def test_bad_output_raises(out: str) -> None:
    with pytest.raises(ExtractionError):
        extract_claim(returns(out), MSGS, ITEMS)  # type: ignore[arg-type]
