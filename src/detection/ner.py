"""Optional local NER layer: Samanyu's fine-tuned classifier (models/pii_classifier).

Loaded lazily and only if the model directory and transformers/torch are
present; otherwise the pattern layer serves alone and status() says why.
Set PRIVACYLENS_NER=0 to disable.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

from .main import DetectionResult

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "pii_classifier"
MIN_SCORE = 0.6

_lock = threading.Lock()
_pipe = None
_status = {"state": "unloaded", "detail": "", "load_ms": None}


def _load() -> None:
    global _pipe
    if os.environ.get("PRIVACYLENS_NER", "1") == "0":
        _status.update(state="disabled", detail="PRIVACYLENS_NER=0")
        return
    if not (MODEL_DIR / "config.json").exists():
        _status.update(state="missing",
                       detail="No trained model at models/pii_classifier (run src/model/train.py)")
        return
    try:
        from transformers import pipeline  # heavy import, only when a model exists
    except Exception as exc:  # noqa: BLE001
        _status.update(state="missing", detail=f"transformers not installed: {exc}")
        return
    t0 = time.perf_counter()
    try:
        _pipe = pipeline("token-classification", model=str(MODEL_DIR),
                         tokenizer=str(MODEL_DIR), aggregation_strategy="simple", device=-1)
    except Exception as exc:  # noqa: BLE001
        _status.update(state="error", detail=str(exc)[:200])
        return
    _status.update(state="loaded", detail=str(MODEL_DIR.name),
                   load_ms=(time.perf_counter() - t0) * 1000)
    logger.info("NER model loaded from %s", MODEL_DIR)


def status() -> dict:
    with _lock:
        if _status["state"] == "unloaded":
            _load()
    return dict(_status)


def predict(text: str) -> Optional[List[DetectionResult]]:
    """Model detections for *text*, or None when the model isn't available."""
    if status()["state"] != "loaded" or not text.strip():
        return None
    out = []
    for ent in _pipe(text):
        if ent["score"] < MIN_SCORE or ent["end"] <= ent["start"]:
            continue
        out.append(DetectionResult(text[ent["start"]:ent["end"]], ent["entity_group"],
                                   ent["start"], ent["end"], float(ent["score"]), "model"))
    return out
