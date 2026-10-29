import os
import sys

# Allow `python src/detection/test.py` from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from detection import detect

tests = [
    ("My card is 4532015112830366", ["CARD"]),
    ("Phone: 9876543210", ["PHONE"]),
    ("OTP is 126225", ["OTP"]),
    ("Email me at test@example.com", ["EMAIL"]),
    ("PAN: ABCDE1234F", ["PAN"]),
    ("IP: 192.168.1.1", ["IP"]),
    ("Visit https://example.com", ["URL"]),
]

for text, expected in tests:
    results = detect(text)
    labels = [r.label for r in results]
    status = "✓" if all(e in labels for e in expected) else "✗"
    print(f"{status} {text[:40]:40s} -> {labels}")
