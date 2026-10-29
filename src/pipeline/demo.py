"""Demo UI entry point (Person C) - browser capture -> detect -> redact -> reason.

Features:
  - Capture a URL or paste a page
  - Run detection (pattern + local model)
  - Redact sensitive spans with [REDACTED:{TYPE}]
  - Local LLM reasoning over sanitized view
  - Action validation + user approval hook
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Demo UI ready (Person C)")


if __name__ == "__main__":
    sys.exit(main())
