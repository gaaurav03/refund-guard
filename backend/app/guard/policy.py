"""Confidence policy: turns Decider probabilities into a final action (docs/decision.md section 5).

Never auto-approves under threshold. Amounts are computed here, never by a model.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import DeciderResult, Decision, Outcome, RefundClaimState


@dataclass(frozen=True)
class Thresholds:
    approve: float = 0.85
    deny: float = 0.85
    partial: float = 0.80
    manipulation: float = 0.50
    args_grounded: float = 0.50


ESCALATE_FEEDBACK = "Sent to human review. Tell the customer a person will check it. Do not retry."


def partial_cap(state: RefundClaimState) -> float | None:
    """Max refund for the claimed items: min(requested, sum of their prices). None if no items claimed."""
    if not state.claimed_skus:
        return None
    claimed = set(state.claimed_skus)
    items_total = sum(i.unit_price * i.qty for i in state.items if i.sku in claimed)
    return round(min(state.requested_amount, items_total), 2)


def fallback_decision(reason: str) -> Decision:
    """Any error in the guard path ends here: fail closed to escalate."""
    return Decision(
        outcome="escalate",
        decided_by="fallback",
        policy_step=f"fallback:{reason}",
        agent_feedback=ESCALATE_FEEDBACK,
    )


def apply_policy(result: DeciderResult, state: RefundClaimState, t: Thresholds) -> Decision:
    def done(outcome: Outcome, step: str, amount: float = 0.0, feedback: str = "") -> Decision:
        return Decision(
            outcome=outcome,
            approved_amount=amount,
            decided_by="decider" if step.startswith("decider") else "policy",
            policy_step=step,
            decider=result,
            agent_feedback=feedback,
        )

    # 1b: tool arguments not supported by what the customer actually said
    if result.args_grounded_p is not None and result.args_grounded_p < t.args_grounded:
        return done(
            "deny",
            "policy:args_ungrounded",
            feedback="This refund call's order id or amount is not supported by what the customer said. "
            "Confirm them with the customer before trying again.",
        )

    p = result.probs
    top = result.option

    # 2: manipulation can only downgrade approve/partial, never upgrade
    if (
        result.manipulation_p is not None
        and result.manipulation_p >= t.manipulation
        and top in ("approve", "partial")
    ):
        return done("escalate", "policy:manipulation", feedback=ESCALATE_FEEDBACK)

    # 3: approve
    if p.get("approve", 0.0) >= t.approve:
        return done("approve", "decider:approve", amount=round(state.requested_amount, 2))

    # 4: deny
    if p.get("deny", 0.0) >= t.deny:
        return done(
            "deny",
            "decider:deny",
            feedback="Refund not permitted: the evidence does not support this claim. Do not retry.",
        )

    # 5: partial, amount capped by code
    if p.get("partial", 0.0) >= t.partial:
        cap = partial_cap(state)
        if cap is None or cap <= 0:
            return done("escalate", "policy:partial_without_items", feedback=ESCALATE_FEEDBACK)
        return done("partial", "decider:partial", amount=cap)

    # 6: everything else, including a confident "escalate"
    return done("escalate", "policy:below_threshold", feedback=ESCALATE_FEEDBACK)
