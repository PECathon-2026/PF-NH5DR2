"""Detection layer: pattern + DOM structural + optional local NER.

Usage:
    python -m src.detection.main
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Iterable, List

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    span_type: str
    start: int
    end: int
    value: str
    confidence: float = 1.0
    source: str = "pattern"  # "pattern" or "model"

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("end must be > start")


CARD_PATTERNS: list[tuple[re.Pattern, str]] = []
PHONE_PATTERN = re.compile(r"^[\+]?[0-9\s\-()]{7,}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[0-9]{2}[0-9]{3}[A-Z]{1}$")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
URL_PATTERN = re.compile(r"https?://[^\s\"']+")

EXPECTED_TYPES = {
    "CARD", "PHONE", "PAN", "EMAIL", "IP", "URL", "OTP", "PERSON", "ENTITY"
}


def card_luhn_valid(value: str) -> bool:
    """Return True if the digit string passes the Luhn checksum."""
    digits = [int(ch) for ch in value if ch.isdigit()]
    if not digits:
        return False
    total = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
        if d > 9:
            d -= 9
        total += d
    return total % 10 == 0


def build_card_patterns() -> list[tuple[re.Pattern, str]]:
    """Compile Luhn-valid card regexes for common brands."""
    def card_rx(prefix: str, length: int) -> re.Pattern:
        p = prefix.rstrip("*")
        return re.compile(
            rf"(?<!\d)(?:{p})[0-9]{{{length}}}(?!\d)", re.VERBOSE
        )
    return [
        (card_rx("4", 13), "CARD_VISA"),           # 13 or 16
        (card_rx("5[1-5]", 16), "CARD_MASTERCARD"),
        (card_rx("3[47]", 14), "CARD_AMEX"),
        (card_rx("6(?:011|5[0-9]{2})", 16), "CARD_DISCOVER"),
    ]


def detect_patterns(text: str) -> list[DetectionResult]:
    """Run pattern-based detection over *text*."""
    found: list[DetectionResult] = []
    for rx, stype in CARD_PATTERNS:
        for m in rx.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if card_luhn_valid(digits):
                found.append(DetectionResult(stype, m.start(), m.end(), m.group(0), 0.9, "pattern"))
    for m in PHONE_PATTERN.finditer(text):
        found.append(DetectionResult("PHONE", m.start(), m.end(), m.group(0), 0.8, "pattern"))
    for m in PAN_PATTERN.finditer(text):
        found.append(DetectionResult("PAN", m.start(), m.end(), m.group(0), 0.85, "pattern"))
    for m in EMAIL_PATTERN.finditer(text):
        found.append(DetectionResult("EMAIL", m.start(), m.end(), m.group(0), 0.9, "pattern"))
    for m in IP_PATTERN.finditer(text):
        # skip private/reserved
        ip = m.group(0)
        a, b, c, d = (int(x) for x in ip.split("."))
        if not (a == 10 or a == 172 and 16 <= b <= 31 or a == 192 and b == 168):
            found.append(DetectionResult("IP", m.start(), m.end(), ip, 0.9, "pattern"))
    for m in URL_PATTERN.finditer(text):
        found.append(DetectionResult("URL", m.start(), m.end(), m.group(0), 0.85, "pattern"))
    return found


def detect_all(text: str, model_results: Iterable[DetectionResult] | None = None) -> list[DetectionResult]:
    """Merge pattern detection with optional model results."""
    results = detect_patterns(text)
    for mr in (model_results or []):
        results.append(mr)
    return results
