"""Production entry point: uvicorn app.main:app --app-dir backend

Wires the real Bedrock model, Decider server and DynamoDB tables into the FastAPI app.
Serves the built frontend from frontend/dist when it exists (fallback when CloudFront is not used).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent.bedrock import make_converse
from .agent.build import FallbackAgent, build_agent
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


def agent_factory(session: Session) -> FallbackAgent:
    def make(model_id: str, messages: list[object] | None):  # type: ignore[no-untyped-def]
        return build_agent(settings=settings, repo=repo, decider=decider, converse=converse, ledger=ledger,
                           model_id=model_id, gullible=session.gullible, messages=messages)

    return FallbackAgent(make, settings.bedrock_model_id, settings.bedrock_fallback_model_id)


app = create_app(settings=settings, repo=repo, agent_factory=agent_factory, decider_health=decider.health)

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Serve real files from dist; every other non-API route gets index.html (client-side routing)."""
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (DIST / path).resolve()
        if path and file.is_file() and DIST.resolve() in file.parents:
            return FileResponse(file)
        # Always revalidate the page shell, so a new deploy is picked up on the next load instead of
        # the browser reusing a stale index.html that points at old JavaScript.
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
