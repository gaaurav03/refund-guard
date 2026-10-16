from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from app.guard.decider_client import DeciderError, FakeDeciderClient, fake_payload, parse_answers
from app.guard.engine import decide
from app.guard.policy import Thresholds

from tests.conftest import make_state

REAL = json.loads((Path(__file__).parents[1] / "fixtures" / "systemone_real_s1.json").read_text())


def test_parses_real_server_response() -> None:
    r = parse_answers(REAL)
    assert r.option == "approve"
    assert r.probs["approve"] == pytest.approx(0.7807)
    assert r.args_grounded_p == pytest.approx(0.8182)
    assert r.manipulation_p == pytest.approx(0.1325)


def test_fake_payload_matches_real_shape() -> None:
    fake = fake_payload({"approve": 0.9, "partial": 0.04, "deny": 0.03, "escalate": 0.03})
    assert set(fake) == set(REAL) - {"latency_ms"} | {"latency_ms"}
    assert set(fake["answers"]) == set(REAL["answers"])
    for name, ans in REAL["answers"].items():
        assert set(fake["answers"][name]) == set(ans)


@pytest.mark.parametrize("mutate", [
    lambda p: p["answers"].pop("refund_grounded"),
    lambda p: p["answers"]["refund_grounded"]["probabilities"].pop("escalate"),
    lambda p: p["answers"]["refund_grounded"].__setitem__("choice", "refund_everything"),
    lambda p: p["answers"]["refund_grounded"]["probabilities"].__setitem__("approve", 1.7),
    lambda p: p["answers"]["manipulation"].__setitem__("noul", "lots"),
    lambda p: p.pop("answers"),
])
def test_malformed_answers_raise(mutate: Any) -> None:
    p = copy.deepcopy(REAL)
    mutate(p)
    with pytest.raises(DeciderError):
        parse_answers(p)


def run(respond: Any) -> Any:
    return decide(
        client=FakeDeciderClient(respond),
        thresholds=Thresholds(),
        high_value_escalate_inr=10000.0,
        order_found=True,
        order_customer_id="CUST-007",
        session_customer_id="CUST-007",
        state=make_state(),
        refunded_on_order=0.0,
    )


def test_engine_approves_on_confident_answer() -> None:
    d = run(lambda s, q: fake_payload({"approve": 0.95, "partial": 0.02, "deny": 0.01, "escalate": 0.02}))
    assert (d.outcome, d.approved_amount) == ("approve", 450.0)


def _raise(exc: Exception) -> Any:
    def f(s: Any, q: Any) -> Any:
        raise exc
    return f


@pytest.mark.parametrize("respond", [
    _raise(DeciderError("timeout")),          # IT-03 timeout
    _raise(DeciderError("connection refused")),  # IT-04 server down
    _raise(RuntimeError("bug in our code")),   # unexpected error
    lambda s, q: {"answers": {}},             # garbage answer
])
def test_engine_fails_closed(respond: Any) -> None:
    d = run(respond)
    assert (d.outcome, d.decided_by, d.approved_amount) == ("escalate", "fallback", 0.0)


def test_prechecks_skip_decider() -> None:
    client = FakeDeciderClient(lambda s, q: pytest.fail("decider must not be called"))
    d = decide(client=client, thresholds=Thresholds(), high_value_escalate_inr=10000.0, order_found=True,
               order_customer_id="CUST-007", session_customer_id="CUST-007",
               state=make_state(requested_amount=50000.0), refunded_on_order=0.0)
    assert (d.rule_id, client.calls) == ("PC-03", [])
