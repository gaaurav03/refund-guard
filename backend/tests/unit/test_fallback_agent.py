from __future__ import annotations

from typing import Any

import pytest
from app.agent.build import FallbackAgent
from strands.types.exceptions import ModelThrottledException


class FakeAgent:
    def __init__(self, model_id: str, messages: list[Any] | None, fail: bool) -> None:
        self.model_id = model_id
        self.messages: list[Any] = list(messages or [])
        self.fail = fail

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        self.messages.append({"role": "user", "content": prompt})
        if self.fail:
            raise ModelThrottledException("throttled")
        self.messages.append({"role": "assistant", "content": f"{self.model_id} ok"})
        return f"{self.model_id} ok"


def test_switches_to_fallback_and_keeps_history() -> None:
    made: list[FakeAgent] = []

    def make(model_id: str, messages: list[Any] | None) -> Any:
        a = FakeAgent(model_id, messages, fail=False)
        made.append(a)
        return a

    agent = FallbackAgent(make, "primary", "backup")
    assert agent("hi") == "primary ok"
    made[0].fail = True
    assert agent("second") == "backup ok"
    assert agent.model_id == "backup"
    # history from the primary is kept, the failed half-turn is dropped
    assert made[1].messages[:2] == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "primary ok"}]
    assert made[1].messages[2] == {"role": "user", "content": "second"}


def test_without_fallback_the_error_propagates() -> None:
    agent = FallbackAgent(lambda m, msgs: FakeAgent(m, msgs, fail=True), "primary", None)
    with pytest.raises(ModelThrottledException):
        agent("hi")
