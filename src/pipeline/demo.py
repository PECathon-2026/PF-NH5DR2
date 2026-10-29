"""Demo server: serves the single-page demo and the local sanitize API.

Endpoints:
  GET  /               -> demo/index.html
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
from pydantic import BaseModel, Field

from src.pipeline.sanitize import SanitizationError, sanitize

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "demo" / "index.html"
MAX_CHARS = 20_000

app = FastAPI(title="PrivacyLens demo", docs_url=None, redoc_url=None)


class SanitizeRequest(BaseModel):
    text: str = Field(default="", max_length=MAX_CHARS)
    typed: bool = True


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX, media_type="text/html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


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
