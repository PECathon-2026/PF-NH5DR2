"""Detection layer entry point."""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    from . import detect_all
    sample = "Card 4111 1111 1111 1111, phone 9876543210, email a@b.c, ip 8.8.8.8"
    print("Input:", sample)
    out = detect_all(sample)
    for r in out:
        print(f"  [{r.span_type:8s}] {r.value!r} start={r.start} end={r.end} conf={r.confidence:.2f}")


if __name__ == "__main__":
    sys.exit(main())
