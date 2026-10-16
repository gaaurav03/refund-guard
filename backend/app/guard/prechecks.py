"""Deterministic pre-checks PC-01..PC-10 (docs/decision.md section 4).

Cheap rules that run before Decider. The first match wins and ends the decision.
"""

from __future__ import annotations

from claim_vs_evidence.checks import args_mismatch

from ..models import Decision, Outcome, RefundClaimState


def _hit(rule_id: str, outcome: Outcome, feedback: str) -> Decision:
    return Decision(
        outcome=outcome,
        decided_by="precheck",
        policy_step=f"precheck:{rule_id}",
        rule_id=rule_id,
        agent_feedback=feedback,
    )


def run_prechecks(
    *,
    order_found: bool,
    order_customer_id: str | None,
    session_customer_id: str,
    state: RefundClaimState | None,
    refunded_on_order: float,
    high_value_escalate_inr: float,
) -> Decision | None:
    """Return a final Decision if a rule matches, else None (go to Decider)."""
    if not order_found or state is None:
        return _hit("PC-01", "deny", "Refund not permitted: order not found. Do not retry.")

    if order_customer_id != session_customer_id:
        return _hit("PC-02", "deny", "Refund not permitted: this order does not belong to this customer.")

    amount = state.requested_amount
    if amount <= 0 or amount > state.order_amount:
        return _hit(
            "PC-03",
            "deny",
            f"Refund not permitted: requested amount {amount:g} is not between 0 and the order "
            f"amount {state.order_amount:g}. Do not retry with a different amount unless the customer asks.",
        )

    if refunded_on_order + amount > state.order_amount:
        return _hit("PC-04", "deny", "Refund not permitted: this order has already been refunded.")

    order_skus = {item.sku for item in state.items}
    unknown = [s for s in state.claimed_skus if s not in order_skus]
    if unknown:
        return _hit("PC-05", "deny", f"Refund not permitted: items {unknown} are not part of this order.")

    if state.return_window_status == "closed":
        if state.claimed_reason == "changed_mind":
            return _hit("PC-06", "deny", "Refund not permitted: the return window has closed.")
        return _hit("PC-07", "escalate", "Sent to human review: the return window has closed. Do not retry.")

    if amount > high_value_escalate_inr:
        return _hit("PC-08", "escalate", "Sent to human review: high-value refund. Do not retry.")

    if state.delivery_status in ("not_shipped", "in_transit") and state.claimed_reason == "not_delivered":
        return _hit(
            "PC-09",
            "escalate",
            "Sent to human review: the order is still on its way. Tell the customer the current status.",
        )

    # PC-10: the customer typed an amount or order id and this call does not match it (plain code;
    # Decider was unreliable at exact matching). The agent is guided to confirm, not blocked for good.
    mismatch = args_mismatch(state.recent_customer_messages, amount=amount, order_id=state.order_id)
    if mismatch:
        return _hit(
            "PC-10",
            "deny",
            f"NOT PAID. This refund call does not match what the customer asked: {mismatch}. "
            "Confirm the order and amount with the customer before trying again.",
        )

    return None
