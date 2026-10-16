"""The typed Decider questions (docs/decision.md section 2).

Defined once in the reusable pattern package (decision-patterns/claim-vs-evidence). The refund app
uses its default wording, which is word for word what the benchmark measured (locked by a test).
"""

from __future__ import annotations

from claim_vs_evidence.questions import (
    ARGS_GROUNDED,
    CONCRETE_PROBLEM,
    CONTRADICTED,
    NON_EVIDENCE,
    OVER_ASK,
    SIGNALS,
    UNCERTAIN,
    make_questions,
)

QUESTIONS = make_questions()  # refund wording (the package defaults)

__all__ = [
    "ARGS_GROUNDED",
    "CONCRETE_PROBLEM",
    "CONTRADICTED",
    "NON_EVIDENCE",
    "OVER_ASK",
    "QUESTIONS",
    "SIGNALS",
    "UNCERTAIN",
]
