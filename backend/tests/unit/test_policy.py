from __future__ import annotations

import pytest
from app.guard.policy import Thresholds, apply_policy, partial_cap
from app.models import DeciderResult

from tests.conftest import make_state

T = Thresholds()


def result(approve: float = 0.0, partial: float = 0.0, deny: float = 0.0, escalate: float = 0.0,
           args: float | None = 0.9, manip: float | None = 0.1) -> DeciderResult:
    probs = {"approve": approve, "partial": partial, "deny": deny, "escalate": escalate}
    top = max(probs, key=lambda k: probs[k])
    return DeciderResult(option=top, probs=probs, confidence=0.5,  # type: ignore[arg-type]
                         args_grounded_p=args, manipulation_p=manip)


def test_approve_at_threshold() -> None:
    d = apply_policy(result(approve=0.85, escalate=0.15), make_state(), T)
    assert (d.outcome, d.approved_amount, d.decided_by) == ("approve", 450.0, "decider")


def test_approve_just_below_threshold_escalates() -> None:
    d = apply_policy(result(approve=0.849, escalate=0.151), make_state(), T)
    assert (d.outcome, d.approved_amount, d.policy_step) == ("escalate", 0.0, "policy:below_threshold")


def test_real_s1_answer_078_escalates_under_default_thresholds() -> None:
    # Measured locally on 2026-10-15: genuine claim scored approve 0.78. Tuning happens on the dev split.
    d = apply_policy(result(approve=0.7807, partial=0.1, deny=0.0275, escalate=0.0918), make_state(), T)
    assert d.outcome == "escalate"


def test_deny_at_threshold() -> None:
    d = apply_policy(result(deny=0.85, escalate=0.15), make_state(), T)
    assert (d.outcome, d.approved_amount) == ("deny", 0.0)


def test_partial_is_capped_by_code() -> None:
    s = make_state(requested_amount=1050.0)  # asks for everything, only the mug is claimed
    d = apply_policy(result(partial=0.80, escalate=0.2), s, T)
    assert (d.outcome, d.approved_amount) == ("partial", 450.0)


def test_partial_without_claimed_items_escalates() -> None:
    d = apply_policy(result(partial=0.9, escalate=0.1), make_state(claimed_skus=[]), T)
    assert (d.outcome, d.policy_step) == ("escalate", "policy:partial_without_items")


def test_confident_escalate_escalates() -> None:
    assert apply_policy(result(escalate=0.97, approve=0.03), make_state(), T).outcome == "escalate"


def test_manipulation_downgrades_approve() -> None:
    d = apply_policy(result(approve=0.95, escalate=0.05, manip=0.5), make_state(), T)
    assert (d.outcome, d.policy_step) == ("escalate", "policy:manipulation")


def test_manipulation_never_upgrades_deny() -> None:
    d = apply_policy(result(deny=0.95, escalate=0.05, manip=0.99), make_state(), T)
    assert d.outcome == "deny"


def test_ungrounded_args_deny_this_call() -> None:
    d = apply_policy(result(approve=0.99, args=0.49), make_state(), T)
    assert (d.outcome, d.policy_step, d.approved_amount) == ("deny", "policy:args_ungrounded", 0.0)
    assert "Confirm" in d.agent_feedback


def test_args_at_threshold_continue() -> None:
    assert apply_policy(result(approve=0.99, args=0.50), make_state(), T).outcome == "approve"


@pytest.mark.parametrize("probs", [
    {"approve": 0.84, "deny": 0.16}, {"partial": 0.79, "escalate": 0.21}, {"deny": 0.84, "approve": 0.16},
])
def test_never_moves_money_below_threshold(probs: dict[str, float]) -> None:
    d = apply_policy(result(**probs), make_state(), T)  # type: ignore[arg-type]
    assert d.approved_amount == 0.0


def test_partial_cap_counts_quantity() -> None:
    s = make_state(claimed_skus=["TEA-ASM"], requested_amount=1000.0)
    assert partial_cap(s) == 600.0


def test_partial_cap_never_exceeds_request() -> None:
    s = make_state(claimed_skus=["MUG-BLU", "TEA-ASM"], requested_amount=500.0)
    assert partial_cap(s) == 500.0
