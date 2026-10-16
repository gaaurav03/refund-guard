"""Decider 2B client for the app: the pattern package's client, returning the app's typed DeciderResult."""

from __future__ import annotations

from typing import Any

from claim_vs_evidence import client as _c
from claim_vs_evidence.client import (
    GENUINE_SIGNALS,
    DeciderClient,
    DeciderError,
    FakeDeciderClient,
    HttpDeciderClient,
    fake_payload,
)

from ..models import DeciderResult
from .questions import SIGNALS

__all__ = [
    "GENUINE_SIGNALS",
    "DeciderClient",
    "DeciderError",
    "FakeDeciderClient",
    "HttpDeciderClient",
    "ask_decider",
    "fake_payload",
    "parse_answers",
]


def parse_answers(payload: dict[str, Any], *, wall_ms: float | None = None) -> DeciderResult:
    """Normalise a /v1/systemone payload. Raises DeciderError on anything missing or out of range."""
    a = _c.parse_answers(payload, signals=SIGNALS, wall_ms=wall_ms)
    return DeciderResult(signals=a.signals, latency_ms=a.latency_ms)


def ask_decider(client: DeciderClient, state: Any, questions: dict[str, dict[str, Any]]) -> DeciderResult:
    a = _c.ask(client, state, questions)
    return DeciderResult(signals=a.signals, latency_ms=a.latency_ms)
