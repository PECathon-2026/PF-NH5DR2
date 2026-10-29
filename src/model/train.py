"""Fine-tune a local PII classifier and evaluate it.

Pipeline (Person B):
  1. Build corpus       (src/model/corpus/build_corpus.py)
  2. Fine-tune a small model on the corpus
  3. Quantize to ONNX/GGUF
  4. Evaluate recall / precision / latency on held-out set

Sizing (12GB VRAM hard cap): <= 600M params or a quantized 1-4B model.
"""
from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_corpus(corpus_dir: str) -> str:
    # TODO(Person B): point to real corpus dir
    return corpus_dir


def train(corpus_dir: str, out_dir: str) -> str:
    # TODO(Person B): load model, fine-tune, quantize, save to out_dir
    logger.info("Saving model to %s", out_dir)
    return out_dir


def evaluate(model_dir: str) -> None:
    # TODO(Person B): load model, run eval on held-out corpus,
    # report recall / precision / latency, canary leakage == 0
    pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="F:/Hackthon/data/corpus")
    ap.add_argument("--out", default="F:/Hackthon/models/pii_classifier")
    args = ap.parse_args()

    corpus = build_corpus(args.corpus)
    model_dir = train(corpus, args.out)
    evaluate(model_dir)
    logger.info("Done: model at %s", model_dir)


if __name__ == "__main__":
    sys.exit(main())
