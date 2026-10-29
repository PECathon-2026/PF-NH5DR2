"""Sanitization pipeline: detect() -> replace spans with placeholders.

Pipeline:
  1. Load raw input (DOM / form / page)  -> detection (src.detection)
  2. Sanitize: replace each span with [REDACTED:{TYPE}]
  3. Leak check: no detected raw value may survive in the output
  4. (later) Local LLM reasoning + action validation over the sanitized view

Fail-closed: if detection or the leak check fails, SanitizationError is raised
and the caller must block the action instead of passing raw data on.

Run:
    python -m src.pipeline.sanitize "My card is 4532015112830366"
"""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import List

from src.detection import DetectionResult, detect

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class SanitizationError(RuntimeError):
    """Raised when input cannot be safely sanitized (fail-closed)."""


@dataclass
class SanitizeResult:
    original: str
    sanitized: str
    detections: List[DetectionResult] = field(default_factory=list)
    leaked: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "sanitized": self.sanitized,
            "detections": [asdict(d) for d in self.detections],
            "leaked": self.leaked,
            "latency_ms": round(self.latency_ms, 2),
        }


def placeholder(label: str, typed: bool = True) -> str:
    return f"[REDACTED:{label}]" if typed else "[REDACTED]"


def sanitize_text(text: str, detections: List[DetectionResult], typed: bool = True) -> str:
    """Replace detected spans with placeholders; preserve everything else."""
    out: list[str] = []
    cursor = 0
    for d in sorted(detections, key=lambda r: r.start):
        if d.start < cursor:  # overlapping span already covered
            continue
        out.append(text[cursor:d.start])
        out.append(placeholder(d.label, typed))
        cursor = d.end
    out.append(text[cursor:])
    return "".join(out)


def count_leaks(sanitized: str, detections: List[DetectionResult]) -> int:
    """Number of detected raw values that still appear in the sanitized text."""
    return sum(1 for d in detections if d.text and d.text in sanitized)


def sanitize(text: str, typed: bool = True) -> SanitizeResult:
    """Detect and redact sensitive spans in *text*. Fail-closed on any error."""
    t0 = time.perf_counter()
    try:
        detections = detect(text)
    except Exception as exc:  # noqa: BLE001 - fail closed on anything
        raise SanitizationError(f"detection failed: {exc}") from exc
    sanitized = sanitize_text(text, detections, typed)
    leaked = count_leaks(sanitized, detections)
    if leaked:
        raise SanitizationError(f"{leaked} detected value(s) survived sanitization")
    return SanitizeResult(text, sanitized, detections, leaked,
                          (time.perf_counter() - t0) * 1000)


def validate_action(action: dict, sanitized: str) -> bool:
    """Reject invalid/unsafe actions before execution."""
    # TODO: action validation logic for the reasoning step
    return True


def main() -> None:
    text = " ".join(sys.argv[1:]) or (
        "Hi, I'm paying with 4532 0151 1283 0366. Call +91 98765 43210 or "
        "mail test@example.com. OTP is 126225."
    )
    result = sanitize(text)
    print("Input:    ", result.original)
    print("Sanitized:", result.sanitized)
    for d in result.detections:
        print(f"  [{d.label:6s}] {d.text!r} {d.start}-{d.end}")
    print(f"Leaked: {result.leaked}  ({result.latency_ms:.2f} ms)")


if __name__ == "__main__":
    sys.exit(main())
