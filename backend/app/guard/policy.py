"""Decision policy for refunds (docs/decision.md section 5).

The rules live in the reusable pattern package (claim_vs_evidence.policy). This module adds the
refund specifics: the cap is the price of the claimed items, and the messages the agent is shown.
"""

from __future__ import annotations

from claim_vs_evidence.policy import Thresholds
from claim_vs_evidence.policy import apply_policy as _apply

from ..models import DeciderResult, Decision, RefundClaimState

__all__ = ["DENY_FEEDBACK", "ESCALATE_FEEDBACK", "Thresholds", "apply_policy", "fallback_decision", "partial_cap"]

ESCALATE_FEEDBACK = "Sent to human review. Tell the customer a person will check it. Do not retry."
DENY_FEEDBACK = "Refund not permitted: the evidence does not support this claim. Do not retry."
UNGROUNDED_FEEDBACK = (
    "This refund call's order id or amount is not supported by what the customer said. "
    "Confirm them with the customer before trying again."
)


def _items_total(state: RefundClaimState) -> float | None:
    if not state.claimed_skus:
        return None
    claimed = set(state.claimed_skus)
    return sum(i.unit_price * i.qty for i in state.items if i.sku in claimed)


def partial_cap(state: RefundClaimState) -> float | None:
    """Max refund for the claimed items: min(requested, sum of their prices). None if no items claimed."""
    total = _items_total(state)
    return None if total is None else round(min(state.requested_amount, total), 2)


def fallback_decision(reason: str) -> Decision:
    """Any error in the guard path ends here: fail closed to escalate."""
    return Decision(
        outcome="escalate",
        decided_by="fallback",
        policy_step=f"fallback:{reason}",
        agent_feedback=ESCALATE_FEEDBACK,
    )


def apply_policy(result: DeciderResult, state: RefundClaimState, t: Thresholds) -> Decision:
    v = _apply(result.signals, requested=state.requested_amount, cap=_items_total(state), t=t)
    if v.step == "decider:args_ungrounded":
        feedback = UNGROUNDED_FEEDBACK
    elif v.outcome == "deny":
        feedback = DENY_FEEDBACK
    elif v.outcome == "escalate":
        feedback = ESCALATE_FEEDBACK
    else:
        feedback = ""
    return Decision(
        outcome=v.outcome,
        approved_amount=v.amount,
        decided_by="decider" if v.decided_by == "decider" else "policy",
        policy_step=v.step,
        decider=result,
        agent_feedback=feedback,
    )
