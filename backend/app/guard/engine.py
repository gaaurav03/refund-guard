"""Pre-checks -> Decider -> confidence policy. Every error path fails closed to `escalate`."""

from __future__ import annotations

import logging

from ..models import Decision, RefundClaimState
from .decider_client import DeciderClient, DeciderError, ask_decider
from .policy import Thresholds, apply_policy, fallback_decision
from .prechecks import run_prechecks
from .questions import QUESTIONS
from .state_render import render_state

log = logging.getLogger(__name__)


def decide(
    *,
    client: DeciderClient,
    thresholds: Thresholds,
    high_value_escalate_inr: float,
    order_found: bool,
    order_customer_id: str | None,
    session_customer_id: str,
    state: RefundClaimState | None,
    refunded_on_order: float,
) -> Decision:
    pre = run_prechecks(
        order_found=order_found,
        order_customer_id=order_customer_id,
        session_customer_id=session_customer_id,
        state=state,
        refunded_on_order=refunded_on_order,
        high_value_escalate_inr=high_value_escalate_inr,
    )
    if pre is not None:
        return pre
    assert state is not None  # run_prechecks returns PC-01 when state is None

    try:
        result = ask_decider(client, render_state(state), QUESTIONS)
    except DeciderError as e:
        log.warning("decider failed, escalating: %s", e)
        return fallback_decision("decider_error")
    except Exception:  # never let an unexpected error approve a refund
        log.exception("unexpected error calling decider, escalating")
        return fallback_decision("unexpected_error")

    return apply_policy(result, state, thresholds)
