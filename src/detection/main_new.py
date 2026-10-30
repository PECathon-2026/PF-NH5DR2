"""
Improved regex patterns that handle:
- Card numbers with spaces/dashes (with Luhn validation)
- 9-digit numbers (PAN, SSN, etc.)
- Better context-aware detection
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional


@dataclass
class DetectionResult:
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = "pattern"

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("end must be > start")


# --- Validators --------------------------------------------------------------

def luhn_valid(value: str) -> bool:
    """Luhn algorithm for credit card validation."""
    digits = [int(ch) for ch in value if ch.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def ip_valid(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 4 and all(p.isdigit() and int(p) <= 255 for p in parts)


# --- Patterns ----------------------------------------------------------------

# Card: 13-19 digits, optionally grouped by spaces/dashes
# Must pass Luhn check
CARD_RX = re.compile(
    r"(?<![\d-])\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,7}(?![\d-])"
)

# Phone: Indian 10-digit (6-9 start) with optional +91/0 prefix
# Also handles 9-digit numbers
PHONE_RX = re.compile(
    r"(?<!\d)(?:\+91[\s\-]?|0)?[6-9]\d{4}[\s\-]?\d{5}(?!\d)"
)

# 9-DIGIT numbers: PAN, SSN, or other IDs
# Context-aware: only flag near keywords
NINE_DIGIT_RX = re.compile(r"(?<!\d)\d{9}(?!\d)")

# OTP: 4-8 digits near keywords
OTP_RX = re.compile(
    r"\b(?:otp|one[\s\-]?time[\s\-]?(?:password|passcode|code)|verification\s+code|"
    r"security\s+code|passcode|auth(?:entication)?\s+code|pin)\b[^\d\n]{0,20}?(?<!\d)(\d{4,8})(?!\d)",
    re.IGNORECASE,
)

EMAIL_RX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PAN_RX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
IP_RX = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
URL_RX = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)

URL_TRAILING = ".,;:!?)]}'\""


# --- Detectors --------------------------------------------------------------

def _simple(rx: re.Pattern, label: str, conf: float,
            check: Optional[Callable[[str], bool]] = None):
    def run(text: str) -> Iterable[DetectionResult]:
        for m in rx.finditer(text):
            if check is None or check(m.group(0)):
                yield DetectionResult(m.group(0), label, m.start(), m.end(), conf)
    return run


def _urls(text: str) -> Iterable[DetectionResult]:
    for m in URL_RX.finditer(text):
        value = m.group(0).rstrip(URL_TRAILING)
        yield DetectionResult(value, "URL", m.start(), m.start() + len(value), 0.9)


def _otps(text: str) -> Iterable[DetectionResult]:
    for m in OTP_RX.finditer(text):
        yield DetectionResult(m.group(1), "OTP", m.start(1), m.end(1), 0.85)


def _nine_digit(text: str) -> Iterable[DetectionResult]:
    """Detect 9-digit numbers with context awareness."""
    # Keywords that suggest a 9-digit number is sensitive
    keywords = ['pan', 'ssn', 'social security', 'tax', 'id', 'number', 'aadhaar', 'aadhar']
    text_lower = text.lower()
    
    for m in NINE_DIGIT_RX.finditer(text):
        # Check if near a keyword (within 50 chars before or after)
        start = max(0, m.start() - 50)
        end = min(len(text), m.end() + 50)
        context = text_lower[start:end]
        
        if any(kw in context for kw in keywords):
            yield DetectionResult(m.group(0), "NINE_DIGIT", m.start(), m.end(), 0.7)


# Order: patterns run in this order, earlier patterns win on overlap
DETECTORS: list[Callable[[str], Iterable[DetectionResult]]] = [
    _urls,
    _simple(EMAIL_RX, "EMAIL", 0.95),
    _simple(CARD_RX, "CARD", 0.95, luhn_valid),  # Only valid Luhn cards
    _simple(PAN_RX, "PAN", 0.9),
    _simple(IP_RX, "IP", 0.9, ip_valid),
    _simple(PHONE_RX, "PHONE", 0.85),
    _nine_digit,  # 9-digit numbers with context
    _otps,
]


def _overlaps(a: DetectionResult, b: DetectionResult) -> bool:
    return a.start < b.end and b.start < a.end


def detect(text: str, model_results: Iterable[DetectionResult] | None = None) -> List[DetectionResult]:
    """Detect sensitive spans in text.
    
    Returns non-overlapping results sorted by start offset.
    Optional model_results are merged after pattern detectors.
    """
    accepted: list[DetectionResult] = []
    candidates = [r for det in DETECTORS for r in det(text)]
    candidates.extend(model_results or [])
    
    for cand in candidates:
        if not any(_overlaps(cand, a) for a in accepted):
            accepted.append(cand)
    
    return sorted(accepted, key=lambda r: r.start)


def main() -> None:
    # Test with the exact input from the screenshot
    sample = (
        "Card 4532 0151 1283 0367, phone +91 98765 43210, "
        "OTP is 126225, email priya.sharma@example.com, "
        "PAN ABCDE1234F, IP 192.168.1.1, see https://example.com/x."
    )
    print("Input:", sample)
    results = detect(sample)
    print(f"\nDetected {len(results)} entities:")
    for r in results:
        print(f"  [{r.label:12s}] {r.text!r:30s} conf={r.confidence:.2f}")
    
    # Test 9-digit number
    sample2 = "My SSN is 123456789 and PAN is ABCDE1234F"
    print(f"\nInput: {sample2}")
    results2 = detect(sample2)
    print(f"Detected {len(results2)} entities:")
    for r in results2:
        print(f"  [{r.label:12s}] {r.text!r:30s} conf={r.confidence:.2f}")


if __name__ == "__main__":
    main()
