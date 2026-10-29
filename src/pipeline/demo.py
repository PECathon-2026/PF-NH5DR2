"""Demo server: serves the single-page demo and the local sanitize API.

Endpoints:
  GET  /               -> demo/index.html (live demo)
  GET  /pipeline, /training, /evaluation -> demo/<page>.html
  GET  /static/*       -> demo/static (shared CSS/JS)
  POST /api/sanitize   -> {"text": "..."} -> original, sanitized, detections, leaked
  GET  /api/health     -> {"ok": true}

Run (from repo root):
    python -m src.pipeline.demo            # http://localhost:8000
    PORT=9000 python -m src.pipeline.demo
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.pipeline import insights
from src.pipeline.sanitize import SanitizationError, sanitize

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo"
PAGES = {"pipeline", "training", "evaluation"}
MAX_CHARS = 20_000

app = FastAPI(title="PrivacyLens demo", docs_url=None, redoc_url=None)


class SanitizeRequest(BaseModel):
    text: str = Field(default="", max_length=MAX_CHARS)
    typed: bool = True


app.mount("/static", StaticFiles(directory=DEMO / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(DEMO / "index.html", media_type="text/html")


@app.get("/{page}")
def subpage(page: str) -> FileResponse:
    if page not in PAGES:
        raise HTTPException(status_code=404)
    return FileResponse(DEMO / f"{page}.html", media_type="text/html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/pipeline")
def api_pipeline() -> dict:
    """Training config, measured benchmark and canary audit for the 'How it works' view."""
    return {
        "detectors": insights.detectors_info(),
        "training": insights.training_info(),
        "evaluation": insights.evaluate_patterns(),
        "canary": insights.canary_audit(),
    }


@app.post("/api/sanitize")
def api_sanitize(req: SanitizeRequest) -> dict:
    try:
        return sanitize(req.text, typed=req.typed).to_dict()
    except SanitizationError as exc:
        # Fail closed: never echo raw input back when sanitization failed.
        logger.error("sanitization blocked: %s", exc)
        raise HTTPException(status_code=422, detail="Blocked: input could not be safely sanitized.")


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("PrivacyLens demo on http://localhost:%d", port)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
