"""Decision policy: six Decider signals -> one of approve | partial | deny | escalate.

Plain code, so every step is explainable and testable. Money only moves when Decider is confident
a concrete problem exists and nothing contradicts it. Amounts are computed here, never by a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .questions import ARGS_GROUNDED, CONCRETE_PROBLEM, CONTRADICTED, NON_EVIDENCE, OVER_ASK, UNCERTAIN

Outcome = Literal["approve", "partial", "deny", "escalate"]
OUTCOMES: tuple[Outcome, ...] = ("approve", "partial", "deny", "escalate")


@dataclass(frozen=True)
class Thresholds:
    """Tuned on our refund dev set; re-tune on a labelled sample of your own cases."""

    args_grounded: float = 0.50  # below this, the tool arguments are treated as invented
    contradicted: float = 0.60
    non_evidence: float = 0.60
    uncertain: float = 0.60
    concrete_problem: float = 0.70
    over_ask: float = 0.60


@dataclass(frozen=True)
class Verdict:
    """The guard's answer for one tool call. `step` names the rule that decided it (see STEPS)."""

    outcome: Outcome
    step: str
    amount: float = 0.0
    signals: dict[str, float] | None = field(default=None)
    latency_ms: float | None = None

    @property
    def decided_by(self) -> str:
        return self.step.split(":", 1)[0]  # precheck | decider | policy | fallback


STEPS: dict[str, str] = {
    "decider:args_ungrounded": "Tool arguments not supported by what the person said",
    "decider:contradicted": "The records contradict the claim",
    "decider:pressure_with_problem": "Real problem, but pressure or instructions too: a human checks",
    "decider:non_evidence": "Authority, threats or instructions instead of evidence",
    "decider:uncertain": "The person is unsure, or it is a matter of taste",
    "decider:partial": "Concrete problem, amount capped at the affected items",
    "decider:approve": "Concrete problem, nothing contradicts it",
    "policy:no_items_identified": "Problem described, but no affected item identified",
    "policy:no_concrete_problem": "No concrete problem established",
}


def fallback(reason: str) -> Verdict:
    """Every error path ends here: fail closed to a human."""
    return Verdict(outcome="escalate", step=f"fallback:{reason}")


def apply_policy(
    signals: dict[str, float], *, requested: float, cap: float | None, t: Thresholds | None = None
) -> Verdict:
    """`requested`: amount the tool call asks for. `cap`: value of the items the claim is about (None = unknown)."""
    t = t or Thresholds()
    p = signals

    def done(outcome: Outcome, step: str, amount: float = 0.0) -> Verdict:
        return Verdict(outcome=outcome, step=step, amount=amount, signals=dict(signals))

    # 1: tool arguments not supported by what the person actually said
    if p[ARGS_GROUNDED] < t.args_grounded:
        return done("deny", "decider:args_ungrounded")
    # 2: the records contradict the claim
    if p[CONTRADICTED] >= t.contradicted:
        return done("deny", "decider:contradicted")
    # 3: authority / threats / instructions instead of evidence
    if p[NON_EVIDENCE] >= t.non_evidence:
        if p[CONCRETE_PROBLEM] >= t.concrete_problem:
            return done("escalate", "decider:pressure_with_problem")
        return done("deny", "decider:non_evidence")
    # 4: unsure, or a matter of taste
    if p[UNCERTAIN] >= t.uncertain:
        return done("escalate", "decider:uncertain")
    # 5: a concrete problem -> pay, capped by code at the value of the affected items
    if p[CONCRETE_PROBLEM] >= t.concrete_problem:
        if cap is None:
            return done("escalate", "policy:no_items_identified")
        capped = round(min(requested, cap), 2)
        if p[OVER_ASK] >= t.over_ask or capped + 0.01 < requested:
            return done("partial", "decider:partial", amount=capped)
        return done("approve", "decider:approve", amount=round(requested, 2))
    # 6: no concrete problem established
    return done("escalate", "policy:no_concrete_problem")
