"""Canary leakage audit (Person D).

Injects low-drama fake values (canary markers) into test inputs and asserts that
NOTHING sensitive leaves the machine. Requires leakage_count == 0 to pass.

Run:
    python -m src.eval.canary
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


CANARY_MARKERS = [
    "fake_card_4111111111111111",
    "fake_phone_9876543210",
    "fake_otp_123456",
    "fake_email_x@y.z",
    "fake_ip_8.8.8.8",
    "fake_url_https://example.com/pass=secret",
]


def load_canary_corpus(corpus_dir: str) -> list[dict]:
    rows = []
    p = Path(corpus_dir)
    for f in p.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def audit(leak_checker, markers: list[str] | None = None) -> int:
    """Run a leak check; return count of leaked markers. 0 == pass."""
    markers = markers or CANARY_MARKERS
    count = 0
    for m in markers:
        # TODO(Person D): wire to pipeline leak inspection
        if "fake" in m:
            count += 1  # placeholder - replace with real check
    return count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="F:/Hackthon/data/corpus")
    args = ap.parse_args()

    corpus = load_canary_corpus(args.corpus)
    leak = audit(None, CANARY_MARKERS)
    if leak == 0:
        logger.info("PASS: canary leakage == 0")
    else:
        logger.error("FAIL: %d markers leaked", leak)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
