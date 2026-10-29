"""Compile the training corpus for the local PII classifier.

Builds a combined corpus from:
  - dlptest sample rows (download to data/dlptest/)
  - Faker-generated phone / OTP / card / email / name PII text

Output: data/corpus/train.jsonl  (IOB2 label format)
         data/corpus/test.jsonl   (held-out eval)

Label types (IOB2):
  CARD, PHONE, PAN, EMAIL, IP, URL, OTP, PERSON, ENTITY
"""
from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


LABEL_TYPES = ["CARD", "PHONE", "PAN", "EMAIL", "IP", "URL", "OTP", "PERSON", "ENTITY"]


def iob2(tags: list[str]) -> bool:
    """Check IOB2 compliance."""
    for i, t in enumerate(tags):
        if t.startswith("B-"):
            continue
        if t == "O":
            continue
        if t.startswith("I-") and i == 0:
            return False
        if t.startswith("I-") and i > 0 and not tags[i - 1].startswith("I-") and tags[i - 1] != "O":
            return False
    return True


def build_corpus(out_dir: str, size: int = 400) -> Path:
    """Compile the training corpus (placeholder)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    train = out / "train.jsonl"
    test = out / "test.jsonl"
    # TODO(Person B): fill with dlptest rows + Faker generation
    for i in range(size):
        record = {"text": f"synthetic line {i}", "labels": ["O"] * 5}
        train.write_text(json.dumps(record) + "\n")
        if i % 10 == 0:
            test.write_text(json.dumps(record) + "\n")
    logger.info("Wrote %s (%d rows)", train, size)
    return train


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="F:/Hackthon/data/corpus")
    ap.add_argument("--size", type=int, default=400)
    args = ap.parse_args()
    build_corpus(args.out, args.size)


if __name__ == "__main__":
    main()
