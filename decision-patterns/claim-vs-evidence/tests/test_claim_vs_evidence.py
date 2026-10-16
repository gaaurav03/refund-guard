"""Tests for the reusable pattern. No Decider server or AWS needed: FakeDeciderClient stands in."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from claim_vs_evidence import (
    SIGNALS,
    ClaimEvidenceGuard,
    DeciderError,
    Evidence,
    FakeDeciderClient,
    Thresholds,
    Verdict,
    Wording,
    apply_policy,
    fake_payload,
    make_questions,
    parse_answers,
)
from strands.interventions import Deny, Guide, Proceed, Transform

GENUINE = {"args_grounded": 0.9, "contradicted": 0.1, "concrete_problem": 0.9,
           "non_evidence": 0.1, "over_ask": 0.1, "uncertain": 0.1}


# -- questions --------------------------------------------------------------------------------
def test_six_noul_questions_with_custom_wording():
    q = make_questions(Wording(tool="apply_store_credit", action="credit", actor="shopper"))
    assert list(q) == list(SIGNALS)
    assert all(v["type"] == "noul" for v in q.values())
    assert "apply_store_credit" in q["args_grounded"]["instructions"]
    assert q["over_ask"]["instructions"].startswith("Is the credit amount requested")
    assert "shopper" in q["uncertain"]["instructions"]


# -- policy ------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("override", "outcome", "step"),
    [
        ({}, "approve", "decider:approve"),
        ({"args_grounded": 0.2}, "deny", "decider:args_ungrounded"),
        ({"contradicted": 0.7}, "deny", "decider:contradicted"),
        ({"non_evidence": 0.7, "concrete_problem": 0.2}, "deny", "decider:non_evidence"),
        ({"non_evidence": 0.7}, "escalate", "decider:pressure_with_problem"),
        ({"uncertain": 0.7}, "escalate", "decider:uncertain"),
        ({"concrete_problem": 0.3}, "escalate", "policy:no_concrete_problem"),
    ],
)
def test_policy_steps(override: dict[str, float], outcome: str, step: str):
    v = apply_policy(GENUINE | override, requested=500, cap=500)
    assert (v.outcome, v.step) == (outcome, step)
    assert v.amount == (500 if outcome == "approve" else 0)


def test_partial_is_capped_by_code_not_by_the_model():
    v = apply_policy(GENUINE, requested=1500, cap=600)
    assert (v.outcome, v.amount) == ("partial", 600)


def test_unknown_cap_never_auto_pays():
    assert apply_policy(GENUINE, requested=500, cap=None).outcome == "escalate"


def test_thresholds_are_configurable():
    strict = Thresholds(concrete_problem=0.95)
    assert apply_policy(GENUINE, requested=500, cap=500, t=strict).outcome == "escalate"


def test_parse_rejects_missing_and_out_of_range():
    with pytest.raises(DeciderError):
        parse_answers({"answers": {}})
    bad = fake_payload(contradicted=1.7)
    with pytest.raises(DeciderError):
        parse_answers(bad)


# -- guard -------------------------------------------------------------------------------------
def event(tool: str = "apply_store_credit", **inp: Any) -> Any:
    return SimpleNamespace(
        tool_use={"name": tool, "toolUseId": "t1", "input": {"account": "A-1", "amount": 1500, **inp}},
        invocation_state={"user": "A-1"},
    )


def evidence(_inp: dict[str, Any], _state: dict[str, Any]) -> Evidence:
    return Evidence(state={"RECORDS": ["coupon SAVE10 failed at checkout"]}, requested=1500, cap=600)


def make_guard(respond: Any = None, **kw: Any) -> tuple[ClaimEvidenceGuard, list[Verdict]]:
    logged: list[Verdict] = []
    guard = ClaimEvidenceGuard(
        tool="apply_store_credit",
        decider=FakeDeciderClient(respond or (lambda s, q: fake_payload())),
        gather=kw.pop("gather", evidence),
        on_decision=kw.pop("on_decision", lambda v, e: logged.append(v)),
        **kw,
    )
    return guard, logged


def test_other_tools_pass_untouched():
    guard, logged = make_guard()
    assert isinstance(guard.before_tool_call(event(tool="lookup_order")), Proceed)
    assert logged == []


def test_partial_rewrites_the_amount_before_the_tool_runs():
    guard, logged = make_guard()
    ev = event()
    action = guard.before_tool_call(ev)
    assert isinstance(action, Transform)
    action.apply(ev)
    assert ev.tool_use["input"]["amount"] == 600
    assert logged[0].outcome == "partial"


def test_contradicted_is_denied():
    guard, _ = make_guard(lambda s, q: fake_payload(contradicted=0.8))
    assert isinstance(guard.before_tool_call(event()), Deny)


def test_invented_arguments_get_guidance_not_a_silent_block():
    guard, _ = make_guard(lambda s, q: fake_payload(args_grounded=0.1))
    assert isinstance(guard.before_tool_call(event()), Guide)


def test_precheck_verdict_skips_decider():
    calls: list[Any] = []
    guard, _ = make_guard(
        lambda s, q: calls.append(1) or fake_payload(),
        gather=lambda i, s: Verdict(outcome="deny", step="precheck:amount_over_order"),
    )
    assert isinstance(guard.before_tool_call(event()), Deny)
    assert calls == []


@pytest.mark.parametrize(
    "respond",
    [
        lambda s, q: (_ for _ in ()).throw(DeciderError("timeout")),
        lambda s, q: {"answers": {"contradicted": {"noul": "garbage"}}},
        lambda s, q: (_ for _ in ()).throw(RuntimeError("boom")),
    ],
)
def test_decider_failures_fail_closed(respond: Any):
    guard, logged = make_guard(respond)
    assert isinstance(guard.before_tool_call(event()), Deny)
    assert logged[0].outcome == "escalate" and logged[0].step.startswith("fallback:")


def test_gather_crash_fails_closed():
    guard, logged = make_guard(gather=lambda i, s: 1 / 0)
    assert isinstance(guard.before_tool_call(event()), Deny)
    assert logged[0].step == "fallback:gather_error"


def test_no_record_no_money():
    def broken_log(v: Verdict, e: Any) -> None:
        raise OSError("database down")

    guard, _ = make_guard(on_decision=broken_log)  # Decider would approve/partial
    assert isinstance(guard.before_tool_call(event()), Deny)


def test_decider_sees_state_and_questions():
    fake = FakeDeciderClient(lambda s, q: fake_payload())
    guard = ClaimEvidenceGuard(tool="apply_store_credit", decider=fake, gather=evidence)
    guard.before_tool_call(event())
    state, questions = fake.calls[0]
    assert state == {"RECORDS": ["coupon SAVE10 failed at checkout"]}
    assert list(questions) == list(SIGNALS)
