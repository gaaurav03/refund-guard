"""Production entry point: uvicorn app.main:app --app-dir backend

Wires the real Bedrock model, Decider server and DynamoDB tables into the FastAPI app.
Serves the built frontend from frontend/dist when it exists (fallback when CloudFront is not used).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from .agent.bedrock import make_converse
from .agent.build import build_agent
from .agent.session import Session
from .api import create_app
from .config import get_settings
from .guard.decider_client import HttpDeciderClient
from .guard.ledger import Ledger
from .store.repo import DynamoRepo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()
if not settings.bedrock_model_id:
    raise RuntimeError("BEDROCK_MODEL_ID is not set (see .env.example)")

repo = DynamoRepo(region=settings.aws_region, prefix=settings.ddb_table_prefix)
decider = HttpDeciderClient(settings.strands_decider_url, settings.decider_timeout_ms)
converse = make_converse(settings.bedrock_model_id, settings.aws_region)
ledger = Ledger()


def agent_factory(session: Session):  # type: ignore[no-untyped-def]
    return build_agent(settings=settings, repo=repo, decider=decider, converse=converse, ledger=ledger,
                       gullible=session.gullible)


app = create_app(settings=settings, repo=repo, agent_factory=agent_factory, decider_health=decider.health)

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
