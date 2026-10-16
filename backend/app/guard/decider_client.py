"""Client for a strands-decider server (POST /v1/systemone).

Request/response shapes follow strands_decider/schema.py (v0.1.0). `FakeDeciderClient` exists only
for automated tests: it can return scripted answers or misbehave on demand (timeouts, garbage),
which the real model cannot be made to do.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from ..models import OUTCOMES, DeciderResult
from .questions import ARGS_GROUNDED, MANIPULATION, REFUND_GROUNDED


class DeciderError(RuntimeError):
    """Server down, timeout, or an answer we cannot trust. Callers must fail closed."""


class DeciderClient(Protocol):
    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]: ...


class HttpDeciderClient:
    def __init__(self, url: str, timeout_ms: int) -> None:
        self._url = url.rstrip("/")
        self._timeout = timeout_ms / 1000

    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        try:
            r = httpx.post(
                f"{self._url}/v1/systemone",
                json={"state": state, "questions": questions},
                timeout=self._timeout,
            )
            r.raise_for_status()
            payload: dict[str, Any] = r.json()
            return payload
        except (httpx.HTTPError, ValueError) as e:
            raise DeciderError(f"{type(e).__name__}: {e}") from e

    def health(self) -> dict[str, Any]:
        try:
            r = httpx.get(f"{self._url}/health", timeout=self._timeout)
            r.raise_for_status()
            payload: dict[str, Any] = r.json()
            return payload
        except (httpx.HTTPError, ValueError) as e:
            raise DeciderError(f"{type(e).__name__}: {e}") from e


class FakeDeciderClient:
    """Test double. `respond` returns a payload, or raises to simulate failures."""

    def __init__(self, respond: Callable[[Any, dict[str, dict[str, Any]]], dict[str, Any]]) -> None:
        self._respond = respond
        self.calls: list[tuple[Any, dict[str, dict[str, Any]]]] = []

    def ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        self.calls.append((state, questions))
        return self._respond(state, questions)


def fake_payload(
    probs: dict[str, float],
    *,
    args_grounded: float = 0.9,
    manipulation: float = 0.1,
    latency_ms: float = 5.0,
) -> dict[str, Any]:
    """Build a response in the exact shape the real server returns (see scripts/out/)."""
    choice = max(probs, key=lambda k: probs[k])
    n = len(probs)
    confidence = max(0.0, min(1.0, (n * probs[choice] - 1) / (n - 1)))
    return {
        "model": "fake",
        "answers": {
            ARGS_GROUNDED: {"type": "noul", "noul": args_grounded},
            REFUND_GROUNDED: {
                "type": "choice",
                "choice": choice,
                "probabilities": probs,
                "confidence": round(confidence, 4),
            },
            MANIPULATION: {"type": "noul", "noul": manipulation},
        },
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "latency_ms": latency_ms,
    }


def parse_answers(payload: dict[str, Any], *, wall_ms: float | None = None) -> DeciderResult:
    """Normalise a /v1/systemone payload. Raises DeciderError on anything unexpected."""
    try:
        answers = payload["answers"]
        rg = answers[REFUND_GROUNDED]
        probs = {k: float(v) for k, v in rg["probabilities"].items()}
        option = rg["choice"]
        confidence = float(rg["confidence"])
    except (KeyError, TypeError, ValueError) as e:
        raise DeciderError(f"malformed answer: {e!r}") from e

    if set(probs) != set(OUTCOMES) or option not in OUTCOMES:
        raise DeciderError(f"unexpected options: choice={option!r} probs={sorted(probs)}")
    if any(not 0.0 <= p <= 1.0 for p in probs.values()):
        raise DeciderError(f"probability out of range: {probs}")

    def noul(name: str) -> float | None:
        a = answers.get(name)
        if a is None:
            return None
        try:
            v = float(a["noul"])
        except (KeyError, TypeError, ValueError) as e:
            raise DeciderError(f"malformed {name} answer: {e!r}") from e
        if not 0.0 <= v <= 1.0:
            raise DeciderError(f"{name} out of range: {v}")
        return v

    return DeciderResult(
        option=option,
        probs=probs,
        confidence=confidence,
        args_grounded_p=noul(ARGS_GROUNDED),
        manipulation_p=noul(MANIPULATION),
        latency_ms=float(payload.get("latency_ms", wall_ms or 0.0)),
    )


def ask_decider(client: DeciderClient, state: Any, questions: dict[str, dict[str, Any]]) -> DeciderResult:
    t0 = time.perf_counter()
    payload = client.ask(state, questions)
    return parse_answers(payload, wall_ms=(time.perf_counter() - t0) * 1000)
