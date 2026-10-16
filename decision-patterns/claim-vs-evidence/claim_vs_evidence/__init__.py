"""claim-vs-evidence: a reusable Strands Decider 2B guardrail for risky tools.

Before a tool like issue_refund, apply_credit or cancel_order runs, Decider 2B answers six yes/no
questions comparing what the person claims with the evidence you hold. Plain code turns the answers
into approve | partial | deny | escalate. See README.md.
"""

from .client import (
    Answers,
    DeciderClient,
    DeciderError,
    FakeDeciderClient,
    HttpDeciderClient,
    ask,
    fake_payload,
    parse_answers,
)
from .policy import OUTCOMES, STEPS, Outcome, Thresholds, Verdict, apply_policy, fallback
from .questions import SIGNALS, Questions, Wording, make_questions

__all__ = [
    "OUTCOMES",
    "SIGNALS",
    "STEPS",
    "Answers",
    "ClaimEvidenceGuard",
    "DeciderClient",
    "DeciderError",
    "Evidence",
    "FakeDeciderClient",
    "HttpDeciderClient",
    "Outcome",
    "Questions",
    "Thresholds",
    "Verdict",
    "Wording",
    "apply_policy",
    "ask",
    "fake_payload",
    "fallback",
    "make_questions",
    "parse_answers",
]


def __getattr__(name: str) -> object:
    # The guard needs strands-agents; import it lazily so the questions/policy work without it.
    if name in ("ClaimEvidenceGuard", "Evidence"):
        from . import guard

        return getattr(guard, name)
    raise AttributeError(name)
