from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from app.guard.decider_client import DeciderError, FakeDeciderClient, fake_payload, parse_answers
from app.guard.engine import decide
from app.guard.policy import Thresholds
from app.guard.questions import SIGNALS

from tests.conftest import make_state

# Captured from the real strands-decider server (CPU) for the S1 state, 2026-10-16.
REAL = json.loads((Path(__file__).parents[1] / "fixtures" / "systemone_real_v2_s1.json").read_text())


def test_parses_real_server_response() -> None:
    r = parse_answers(REAL)
    assert set(r.signals) == set(SIGNALS)
    assert r.signals["concrete_problem"] == pytest.approx(0.8814)
    assert r.signals["contradicted"] == pytest.approx(0.2485)


def test_real_s1_answer_approves() -> None:
    d = decide(client=FakeDeciderClient(lambda s, q: REAL), thresholds=Thresholds(), high_value_escalate_inr=10000.0,
               order_found=True, order_customer_id="CUST-007", session_customer_id="CUST-007",
               state=make_state(), refunded_on_order=0.0)
    assert (d.outcome, d.approved_amount) == ("approve", 450.0)


def test_fake_payload_matches_real_shape() -> None:
    fake = fake_payload()
    assert set(fake) == set(REAL)
    assert set(fake["answers"]) == set(REAL["answers"])
    for name, ans in REAL["answers"].items():
        assert set(fake["answers"][name]) == set(ans)


@pytest.mark.parametrize("mutate", [
    lambda p: p["answers"].pop("contradicted"),
    lambda p: p["answers"]["uncertain"].pop("noul"),
    lambda p: p["answers"]["over_ask"].__setitem__("noul", 1.7),
    lambda p: p["answers"]["non_evidence"].__setitem__("noul", "lots"),
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


def test_engine_sends_all_questions_and_key_facts() -> None:
    client = FakeDeciderClient(lambda s, q: fake_payload())
    decide(client=client, thresholds=Thresholds(), high_value_escalate_inr=10000.0, order_found=True,
           order_customer_id="CUST-007", session_customer_id="CUST-007", state=make_state(), refunded_on_order=0.0)
    state, questions = client.calls[0]
    assert set(questions) == set(SIGNALS)
    assert "KEY FACTS (from store records)" in state


def test_prechecks_skip_decider() -> None:
    client = FakeDeciderClient(lambda s, q: pytest.fail("decider must not be called"))
    d = decide(client=client, thresholds=Thresholds(), high_value_escalate_inr=10000.0, order_found=True,
               order_customer_id="CUST-007", session_customer_id="CUST-007",
               state=make_state(requested_amount=50000.0), refunded_on_order=0.0)
    assert (d.rule_id, client.calls) == ("PC-03", [])
