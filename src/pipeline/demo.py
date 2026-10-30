"""Demo server: serves the single-page demo and the local sanitize API.

Endpoints:
  GET  /               -> demo/index.html (live demo)
  GET  /pipeline, /training, /evaluation -> demo/<page>.html
  GET  /static/*       -> demo/static (shared CSS/JS)
  POST /api/sanitize   -> {"text": "..."} -> original, sanitized, detections, leaked
  POST /api/document   -> multipart PDF -> per-page sanitize results (+ indexed for RAG)
  GET  /api/rag        -> this visitor's documents + local LLM status (scoped by X-PL-Session)
  POST /api/rag/ask    -> {"question": "..."} -> sanitized question, retrieved chunks, answer
  POST /api/rag/text   -> {"name", "text"} -> index a message
  DELETE /api/rag/docs[/{id}] -> remove one / all documents
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

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.pipeline import insights, rag
from src.pipeline.documents import MAX_BYTES, DocumentError, process_pdf
from src.pipeline.sanitize import SanitizationError, sanitize

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "demo"
PAGES = {"ask", "pipeline", "training", "evaluation"}
MAX_CHARS = 20_000

app = FastAPI(title="PrivacyLens demo", docs_url=None, redoc_url=None)


@app.middleware("http")
async def no_stale_pages(request, call_next):
    # Pages and assets change on every deploy; make browsers revalidate.
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


class SanitizeRequest(BaseModel):
    text: str = Field(default="", max_length=MAX_CHARS)
    typed: bool = True


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    k: int = Field(default=4, ge=1, le=8)


class TextDoc(BaseModel):
    name: str = Field(default="Message", max_length=120)
    text: str = Field(min_length=1, max_length=MAX_CHARS)


app.mount("/static", StaticFiles(directory=DEMO / "static"), name="static")
app.mount("/samples", StaticFiles(directory=DEMO / "samples"), name="samples")


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
        "model_evaluation": insights.model_evaluation(),
        "canary": insights.canary_audit(),
    }


@app.on_event("startup")
def _warm_up() -> None:
    insights.warm_up()


@app.post("/api/sanitize")
def api_sanitize(req: SanitizeRequest) -> dict:
    try:
        return sanitize(req.text, typed=req.typed).to_dict()
    except SanitizationError as exc:
        # Fail closed: never echo raw input back when sanitization failed.
        logger.error("sanitization blocked: %s", exc)
        raise HTTPException(status_code=422, detail="Blocked: input could not be safely sanitized.")


BLOCKED = "Blocked: the document could not be safely sanitized."


SessionId = Header(default="", alias="X-PL-Session", description="Random per-browser id; scopes the RAG index")


@app.post("/api/document")
def api_document(file: UploadFile = File(...), index: bool = Form(True), sid: str = SessionId) -> dict:
    """Sanitize a PDF page by page; optionally add the sanitized pages to this visitor's RAG index."""
    data = file.file.read(MAX_BYTES + 1)
    try:
        doc = process_pdf(data)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SanitizationError as exc:
        logger.error("document sanitization blocked: %s", exc)
        raise HTTPException(status_code=422, detail=BLOCKED)
    name = os.path.basename(file.filename or "document.pdf")[:120]
    doc["name"] = name
    if index:
        try:
            doc["indexed"] = rag.ingest_pages(name, [p["sanitized"] for p in doc["pages"]], doc["detections"], sid=sid)
        except rag.TooManyDocuments as exc:
            doc["index_error"] = str(exc)
    return doc


@app.get("/api/rag")
def api_rag(sid: str = SessionId) -> dict:
    idx = rag.index_for(sid)
    return {"docs": sorted(idx.docs.values(), key=lambda d: d["added"]),
            "chunks": len(idx.chunks), "llm": rag.llm_status(), "private": True}


@app.post("/api/rag/ask")
def api_rag_ask(req: AskRequest, sid: str = SessionId) -> dict:
    try:
        return rag.ask(req.question, req.k, sid=sid)
    except SanitizationError as exc:
        logger.error("rag blocked: %s", exc)
        raise HTTPException(status_code=422, detail="Blocked: the question or answer could not be safely sanitized.")


@app.post("/api/rag/text")
def api_rag_text(req: TextDoc, sid: str = SessionId) -> dict:
    try:
        return rag.ingest_text(req.name, req.text, sid=sid)
    except SanitizationError:
        raise HTTPException(status_code=422, detail=BLOCKED)
    except rag.TooManyDocuments as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/rag/docs/{doc_id}")
def api_rag_delete(doc_id: str, sid: str = SessionId) -> dict:
    if not rag.index_for(sid).remove(doc_id):
        raise HTTPException(status_code=404, detail="No such document.")
    return {"ok": True}


@app.delete("/api/rag/docs")
def api_rag_clear(sid: str = SessionId) -> dict:
    rag.index_for(sid).clear()
    return {"ok": True}


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("PrivacyLens demo on http://localhost:%d", port)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
