"""Minimal client for a strands-decider server (POST /v1/systemone).

Request/response shapes follow strands_decider/schema.py (v0.1.0):
  request  {"state": <str|dict>, "questions": {name: {"type": "noul", "instructions": str}}}
  response {"answers": {name: {"type": "noul", "noul": P(yes)}}, "latency_ms": float, ...}

Anything we cannot trust raises DeciderError, and callers must fail closed.
`FakeDeciderClient` is for tests only: it can misbehave on demand, which a real model cannot.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .questions import ARGS_GROUNDED, CONCRETE_PROBLEM, CONTRADICTED, NON_EVIDENCE, OVER_ASK, SIGNALS, UNCERTAIN


class DeciderError(RuntimeError):
    """Server down, timeout, or an answer we cannot trust."""


class DeciderClient(Protocol):
    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]: ...


class HttpDeciderClient:
    def __init__(self, url: str = "http://127.0.0.1:8099", timeout_ms: int = 2500) -> None:
        self._url = url.rstrip("/")
        self._timeout = timeout_ms / 1000

    def _call(self, method: str, path: str, **kw: Any) -> dict[str, Any]:
        try:
            r = httpx.request(method, f"{self._url}{path}", timeout=self._timeout, **kw)
            r.raise_for_status()
            payload: dict[str, Any] = r.json()
            return payload
        except (httpx.HTTPError, ValueError) as e:
            raise DeciderError(f"{type(e).__name__}: {e}") from e

    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return self._call("POST", "/v1/systemone", json={"state": state, "questions": questions})

    def health(self) -> dict[str, Any]:
        return self._call("GET", "/health")


class FakeDeciderClient:
    """Test double. `respond(state, questions)` returns a payload, or raises to simulate a failure."""

    def __init__(self, respond: Callable[[Any, dict[str, dict[str, Any]]], dict[str, Any]]) -> None:
        self._respond = respond
        self.calls: list[tuple[Any, dict[str, dict[str, Any]]]] = []

    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        self.calls.append((state, questions))
        return self._respond(state, questions)


# A clearly genuine claim: concrete problem, nothing contradicts it, nothing suspicious.
GENUINE_SIGNALS: dict[str, float] = {
    ARGS_GROUNDED: 0.9, CONTRADICTED: 0.1, CONCRETE_PROBLEM: 0.9, NON_EVIDENCE: 0.1, OVER_ASK: 0.1, UNCERTAIN: 0.1,
}


def fake_payload(latency_ms: float = 5.0, **overrides: float) -> dict[str, Any]:
    """A response in the exact shape the real server returns. Unspecified signals look genuine."""
    signals = GENUINE_SIGNALS | overrides
    return {
        "model": "fake",
        "answers": {name: {"type": "noul", "noul": p} for name, p in signals.items()},
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "latency_ms": latency_ms,
    }


@dataclass(frozen=True)
class Answers:
    signals: dict[str, float]  # P(yes) per question
    latency_ms: float


def parse_answers(
    payload: dict[str, Any], *, signals: tuple[str, ...] = SIGNALS, wall_ms: float | None = None
) -> Answers:
    """Normalise a /v1/systemone payload. Raises DeciderError on anything missing or out of range."""
    try:
        answers = payload["answers"]
        out = {name: float(answers[name]["noul"]) for name in signals}
    except (KeyError, TypeError, ValueError) as e:
        raise DeciderError(f"malformed answer: {e!r}") from e
    bad = {k: v for k, v in out.items() if not 0.0 <= v <= 1.0}
    if bad:
        raise DeciderError(f"probability out of range: {bad}")
    return Answers(signals=out, latency_ms=float(payload.get("latency_ms", wall_ms or 0.0)))


def ask(client: DeciderClient, state: Any, questions: dict[str, dict[str, Any]]) -> Answers:
    t0 = time.perf_counter()
    payload = client.ask(state, questions)
    return parse_answers(payload, signals=tuple(questions), wall_ms=(time.perf_counter() - t0) * 1000)
