"""Detection layer: pattern-based PII/PCI detection.

Usage:
    from src.detection import detect
"""
from .main import detect, DetectionResult

__all__ = ["detect", "DetectionResult"]
