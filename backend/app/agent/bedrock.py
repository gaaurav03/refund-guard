"""Thin Bedrock Converse helper for one-shot calls (claim extraction, LLM-judge baseline)."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

from ..guard.extraction import ConverseFn


def make_converse(model_id: str, region: str, *, max_tokens: int = 400, timeout_s: int = 30) -> ConverseFn:
    client: Any = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(read_timeout=timeout_s, retries={"max_attempts": 2, "mode": "standard"}),
    )

    def converse(system: str, user: str) -> str:
        resp = client.converse(
            modelId=model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
        )
        blocks = resp["output"]["message"]["content"]
        return "".join(b["text"] for b in blocks if "text" in b)

    return converse
