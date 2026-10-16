"""Decision policy: turns Decider's evidence signals into approve | partial | deny | escalate
(docs/decision.md section 5).

Plain code, so every step is explainable. Money only moves when Decider is confident a concrete
problem exists and nothing contradicts it. Amounts are computed here, never by a model.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import DeciderResult, Decision, Outcome, RefundClaimState
from .questions import ARGS_GROUNDED, CONCRETE_PROBLEM, CONTRADICTED, NON_EVIDENCE, OVER_ASK, UNCERTAIN


@dataclass(frozen=True)
class Thresholds:
    args_grounded: float = 0.50  # below this, the tool arguments are treated as invented
    contradicted: float = 0.60
    non_evidence: float = 0.60
    uncertain: float = 0.60
    concrete_problem: float = 0.70
    over_ask: float = 0.60


ESCALATE_FEEDBACK = "Sent to human review. Tell the customer a person will check it. Do not retry."
DENY_FEEDBACK = "Refund not permitted: the evidence does not support this claim. Do not retry."


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
    p = result.signals

    def done(outcome: Outcome, step: str, amount: float = 0.0, feedback: str = "") -> Decision:
        return Decision(
            outcome=outcome,
            approved_amount=amount,
            decided_by="decider" if step.startswith("decider") else "policy",
            policy_step=step,
            decider=result,
            agent_feedback=feedback,
        )

    # 1: tool arguments not supported by what the customer actually said
    if p[ARGS_GROUNDED] < t.args_grounded:
        return done(
            "deny",
            "decider:args_ungrounded",
            feedback="This refund call's order id or amount is not supported by what the customer said. "
            "Confirm them with the customer before trying again.",
        )

    # 2: the records contradict the claim
    if p[CONTRADICTED] >= t.contradicted:
        return done("deny", "decider:contradicted", feedback=DENY_FEEDBACK)

    # 3: authority / threats / instructions instead of evidence
    if p[NON_EVIDENCE] >= t.non_evidence:
        if p[CONCRETE_PROBLEM] >= t.concrete_problem:
            return done("escalate", "decider:pressure_with_problem", feedback=ESCALATE_FEEDBACK)
        return done("deny", "decider:non_evidence", feedback=DENY_FEEDBACK)

    # 4: the customer is unsure, or it is a matter of taste
    if p[UNCERTAIN] >= t.uncertain:
        return done("escalate", "decider:uncertain", feedback=ESCALATE_FEEDBACK)

    # 5: a concrete problem -> pay, capped by code at the value of the affected items
    if p[CONCRETE_PROBLEM] >= t.concrete_problem:
        cap = partial_cap(state)
        if cap is None:
            return done("escalate", "policy:no_items_identified", feedback=ESCALATE_FEEDBACK)
        if p[OVER_ASK] >= t.over_ask or cap + 0.01 < state.requested_amount:
            return done("partial", "decider:partial", amount=cap)
        return done("approve", "decider:approve", amount=round(state.requested_amount, 2))

    # 6: no concrete problem established
    return done("escalate", "policy:no_concrete_problem", feedback=ESCALATE_FEEDBACK)
