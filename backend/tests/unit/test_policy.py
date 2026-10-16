from __future__ import annotations

import pytest
from app.guard.decider_client import GENUINE_SIGNALS
from app.guard.policy import Thresholds, apply_policy, partial_cap
from app.models import DeciderResult

from tests.conftest import make_state

T = Thresholds()


def result(**overrides: float) -> DeciderResult:
    return DeciderResult(signals=GENUINE_SIGNALS | overrides)


def test_genuine_concrete_problem_approves_requested_amount() -> None:
    d = apply_policy(result(), make_state(), T)
    assert (d.outcome, d.approved_amount, d.decided_by, d.policy_step) == ("approve", 450.0, "decider",
                                                                          "decider:approve")


def test_concrete_problem_just_below_threshold_escalates() -> None:
    d = apply_policy(result(concrete_problem=0.699), make_state(), T)
    assert (d.outcome, d.approved_amount, d.policy_step) == ("escalate", 0.0, "policy:no_concrete_problem")


def test_ungrounded_args_deny_this_call() -> None:
    d = apply_policy(result(args_grounded=0.49), make_state(), T)
    assert (d.outcome, d.policy_step, d.approved_amount) == ("deny", "decider:args_ungrounded", 0.0)
    assert "Confirm" in d.agent_feedback


def test_args_at_threshold_continue() -> None:
    assert apply_policy(result(args_grounded=0.50), make_state(), T).outcome == "approve"


def test_contradicted_denies_even_with_concrete_problem() -> None:
    d = apply_policy(result(contradicted=0.6, concrete_problem=0.95), make_state(), T)
    assert (d.outcome, d.policy_step) == ("deny", "decider:contradicted")


def test_pressure_without_problem_denies() -> None:
    d = apply_policy(result(non_evidence=0.7, concrete_problem=0.2), make_state(), T)
    assert (d.outcome, d.policy_step) == ("deny", "decider:non_evidence")


def test_pressure_with_real_problem_escalates() -> None:
    d = apply_policy(result(non_evidence=0.7, concrete_problem=0.9), make_state(), T)
    assert (d.outcome, d.policy_step) == ("escalate", "decider:pressure_with_problem")


def test_uncertain_customer_escalates() -> None:
    d = apply_policy(result(uncertain=0.65), make_state(), T)
    assert (d.outcome, d.policy_step) == ("escalate", "decider:uncertain")


def test_over_ask_pays_only_affected_items() -> None:
    s = make_state(requested_amount=1050.0)  # asks for everything, only the mug is claimed
    d = apply_policy(result(over_ask=0.9), s, T)
    assert (d.outcome, d.approved_amount) == ("partial", 450.0)


def test_code_caps_amount_even_if_decider_misses_over_ask() -> None:
    s = make_state(requested_amount=1050.0)
    d = apply_policy(result(over_ask=0.1), s, T)
    assert (d.outcome, d.approved_amount) == ("partial", 450.0)


def test_concrete_problem_without_items_escalates() -> None:
    d = apply_policy(result(), make_state(claimed_skus=[]), T)
    assert (d.outcome, d.policy_step) == ("escalate", "policy:no_items_identified")


@pytest.mark.parametrize("signals", [
    {"concrete_problem": 0.5},
    {"contradicted": 0.9},
    {"non_evidence": 0.8, "concrete_problem": 0.3},
    {"uncertain": 0.9},
    {"args_grounded": 0.2},
])
def test_no_money_without_a_confident_concrete_problem(signals: dict[str, float]) -> None:
    assert apply_policy(result(**signals), make_state(), T).approved_amount == 0.0


def test_payout_never_exceeds_request_or_order() -> None:
    for requested in (100.0, 450.0, 1050.0):
        s = make_state(requested_amount=requested)
        d = apply_policy(result(), s, T)
        assert d.approved_amount <= requested
        assert d.approved_amount <= s.order_amount


def test_partial_cap_counts_quantity() -> None:
    s = make_state(claimed_skus=["TEA-ASM"], requested_amount=1000.0)
    assert partial_cap(s) == 600.0


def test_partial_cap_never_exceeds_request() -> None:
    s = make_state(claimed_skus=["MUG-BLU", "TEA-ASM"], requested_amount=500.0)
    assert partial_cap(s) == 500.0


def test_partial_cap_counts_damaged_units_not_the_whole_line() -> None:
    # "one of the two tea packs is torn": 1 x 300, not the 600 line
    s = make_state(claimed_skus=["TEA-ASM"], claimed_units={"TEA-ASM": 1}, requested_amount=600.0)
    assert partial_cap(s) == 300.0
    d = apply_policy(result(), s, T)
    assert (d.outcome, d.approved_amount) == ("partial", 300.0)


def test_without_units_the_cap_is_the_whole_line_as_before() -> None:
    s = make_state(claimed_skus=["TEA-ASM"], requested_amount=600.0)
    assert partial_cap(s) == 600.0
