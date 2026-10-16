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
    # Free-plan CPU host (m7i-flex.large) takes ~27-31 s per decision; past this the guard fails closed to a human
    decider_timeout_ms: int = 90_000

    # decision policy thresholds (docs/decision.md section 5)
    args_grounded_threshold: float = 0.50
    contradicted_threshold: float = 0.60
    non_evidence_threshold: float = 0.60
    uncertain_threshold: float = 0.60
    concrete_problem_threshold: float = 0.70
    over_ask_threshold: float = 0.60
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
