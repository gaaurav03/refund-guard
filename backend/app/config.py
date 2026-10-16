"""All runtime settings, read from environment variables (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "ap-southeast-2"

    bedrock_model_id: str = ""
    bedrock_fallback_model_id: str = ""

    strands_decider_url: str = "http://127.0.0.1:8099"
    decider_model: str = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"
    decider_timeout_ms: int = 3000

    approve_threshold: float = 0.85
    deny_threshold: float = 0.85
    partial_threshold: float = 0.80
    manipulation_threshold: float = 0.50
    args_grounded_threshold: float = 0.50
    high_value_escalate_inr: float = 10000.0

    ddb_table_prefix: str = "rg_"

    rate_limit_per_min_ip: int = 30
    max_messages_per_session: int = 20
    max_sessions_per_ip_day: int = 10
    daily_bedrock_budget_usd: float = 3.00

    reviewer_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
