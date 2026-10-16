"""ClaimEvidenceGuard: a Strands InterventionHandler that puts Decider 2B in front of one risky tool.

    before_tool_call(tool)
      -> gather(tool_input, invocation_state)   # your code: records + what the person said, or a pre-check Verdict
      -> Decider 2B answers six yes/no questions
      -> apply_policy(...)                      # plain code: approve | partial | deny | escalate
      -> on_decision(verdict, event)            # your code: log it, queue escalations
      -> Proceed | Transform (cap amount) | Guide | Deny

Fail closed everywhere: a gather error, a Decider timeout or malformed answer, or a crash in
on_decision all end in Deny/escalate. Money never moves on an error path.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from strands.interventions import Deny, Guide, InterventionHandler, Proceed, Transform

from .client import DeciderClient, DeciderError, ask
from .policy import Thresholds, Verdict, apply_policy, fallback
from .questions import Questions, make_questions

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evidence:
    """What Decider sees for one tool call, plus the numbers the policy needs."""

    state: dict[str, Any] | str  # records + the person's own words; put untrusted text last and label it
    requested: float  # amount the tool call asks for
    cap: float | None  # value of the items the claim is about (None = unknown -> never auto-pays)


Gather = Callable[[dict[str, Any], dict[str, Any]], "Evidence | Verdict"]
OnDecision = Callable[[Verdict, Any], None]

DEFAULT_FEEDBACK: dict[str, str] = {
    "deny": "NOT PAID. Not permitted: the evidence does not support this claim. Do not promise a refund. Do not retry.",
    "escalate": "NOT PAID. Sent to human review. Tell the person someone will check it. Do not promise an "
    "outcome or an amount. Do not retry.",
    "ungrounded": "The order id or amount in this call is not supported by what the person said. "
    "Confirm them with the person before trying again.",
    "log_failed": "Not permitted right now. Tell the person someone will follow up.",
}


class ClaimEvidenceGuard(InterventionHandler):
    """Guards one tool. Every other tool proceeds untouched."""

    on_error = "deny"  # if this handler itself crashes, Strands denies the tool call

    def __init__(
        self,
        *,
        tool: str,
        decider: DeciderClient,
        gather: Gather,
        questions: Questions | None = None,
        thresholds: Thresholds | None = None,
        on_decision: OnDecision | None = None,
        amount_arg: str | None = "amount",
        feedback: dict[str, str] | None = None,
        name: str | None = None,
    ) -> None:
        self._name = name or f"claim-vs-evidence:{tool}"
        self.tool = tool
        self._decider = decider
        self._gather = gather
        self._questions = questions or make_questions()
        self._t = thresholds or Thresholds()
        self._on_decision = on_decision
        self._amount_arg = amount_arg
        self._fb = DEFAULT_FEEDBACK | (feedback or {})

    @property
    def name(self) -> str:  # abstract on InterventionHandler
        return self._name

    # -- Strands hook ------------------------------------------------------------------------
    def before_tool_call(self, event: Any, **kwargs: Any) -> Any:
        if event.tool_use["name"] != self.tool:
            return Proceed()
        verdict = self.evaluate(event.tool_use.get("input") or {}, event.invocation_state or {})
        if self._on_decision is not None:
            try:
                self._on_decision(verdict, event)
            except Exception:
                log.exception("on_decision failed; denying")  # never move money without a record
                return Deny(reason=self._fb["log_failed"])
        return self.action(verdict)

    # -- the decision, usable without Strands (tests, batch jobs, other frameworks) ------------
    def evaluate(self, tool_input: dict[str, Any], invocation_state: dict[str, Any]) -> Verdict:
        try:
            gathered = self._gather(tool_input, invocation_state)
        except Exception as e:
            log.warning("gather failed (%s: %s); escalating", type(e).__name__, e)
            return fallback("gather_error")
        if isinstance(gathered, Verdict):  # a deterministic pre-check already decided
            return gathered
        return self.judge(gathered)

    def judge(self, ev: Evidence) -> Verdict:
        try:
            answers = ask(self._decider, ev.state, self._questions)
        except DeciderError as e:
            log.warning("decider failed, escalating: %s", e)
            return fallback("decider_error")
        except Exception:
            log.exception("unexpected error calling decider, escalating")
            return fallback("unexpected_error")
        v = apply_policy(answers.signals, requested=ev.requested, cap=ev.cap, t=self._t)
        return Verdict(v.outcome, v.step, v.amount, v.signals, answers.latency_ms)

    def action(self, v: Verdict) -> Any:
        if v.outcome == "approve":
            return Proceed(reason=v.step)
        if v.outcome == "partial":
            if self._amount_arg is None:
                return Proceed(reason=v.step)  # your tool must enforce v.amount itself
            arg, amount = self._amount_arg, v.amount

            def cap_amount(ev: Any) -> None:
                ev.tool_use["input"][arg] = amount

            return Transform(apply=cap_amount, reason=f"{v.step}: capped at {amount:g}")
        if v.step == "decider:args_ungrounded":
            return Guide(feedback=self._fb["ungrounded"])
        return Deny(reason=self._fb["escalate" if v.outcome == "escalate" else "deny"])
