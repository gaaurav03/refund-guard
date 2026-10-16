"""Per-conversation state. Passed to the agent as invocation_state["session"]."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from ..models import MAX_MESSAGE_CHARS, MAX_RECENT_MESSAGES


@dataclass
class Session:
    customer_id: str  # from login / persona picker, never from the LLM
    mode: Literal["chat", "challenge", "bench"] = "chat"
    session_id: str = field(default_factory=lambda: f"S-{uuid.uuid4().hex[:12]}")
    recent_customer_messages: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)

    def add_customer_message(self, text: str) -> None:
        self.recent_customer_messages.append(text[:MAX_MESSAGE_CHARS])
        del self.recent_customer_messages[:-MAX_RECENT_MESSAGES]
