"""Facts about the pipeline for the demo's "How it works" view.

Everything here is read from the repo or measured at runtime, never typed in:
  - training_info():  model/training config parsed from src/model/train.py and
                      src/model/corpus/build_corpus.py (AST, no torch import),
                      plus metrics from a real Trainer run if one exists locally.
  - evaluate_patterns(): precision/recall of the pattern layer on a seeded
                      synthetic benchmark generated here (positives + negatives).
  - canary_audit():   Athrav's canary values pushed through sanitize().

Run:
    python -m src.pipeline.insights
"""
from __future__ import annotations

import ast
import json
import random
import re
import string
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from src.detection import DETECTORS, detect
from src.detection import ner

ROOT = Path(__file__).resolve().parents[2]
TRAIN_PY = ROOT / "src" / "model" / "train.py"
CORPUS_PY = ROOT / "src" / "model" / "corpus" / "build_corpus.py"
CORPUS_FILE = ROOT / "data" / "corpus" / "train.jsonl"
MODEL_DIR = ROOT / "models" / "pii_classifier"


# --- training pipeline (read from source) -----------------------------------

def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:  # noqa: BLE001
        return None


def _parse_train() -> dict:
    src = TRAIN_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    info: dict = {"base_model": None, "labels": [], "args": {}, "max_length": None}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "MODEL_NAME":
                info["base_model"] = _literal(node.value)
            elif name == "LABEL2ID":
                info["labels"] = list((_literal(node.value) or {}).keys())
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "TrainingArguments":
            info["args"] = {k.arg: _literal(k.value) for k in node.keywords if _literal(k.value) is not None}
        elif isinstance(node, ast.FunctionDef) and node.name == "tokenize_and_align_labels":
            for arg, default in zip(node.args.args[-len(node.args.defaults):], node.args.defaults):
                if arg.arg == "max_length":
                    info["max_length"] = _literal(default)
    m = re.search(r"int\(\s*([\d.]+)\s*\*\s*len", src)
    info["train_split"] = float(m.group(1)) if m else None
    m = re.search(r"random\.seed\((\d+)\)", src)
    info["seed"] = int(m.group(1)) if m else None
    return info


def _parse_corpus_builder() -> dict:
    tree = ast.parse(CORPUS_PY.read_text(encoding="utf-8"))
    templates, loops, generators = [], None, []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("make_"):
            generators.append(node.name[5:].upper())
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "records":
            templates = [t[0] for t in (_literal(node.value) or [])]
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Call)
                and getattr(node.iter.func, "id", None) == "range" and loops is None):
            loops = _literal(node.iter.args[0])
    return {"templates": templates, "rounds": loops, "generators": generators,
            "planned_sentences": len(templates) * loops if loops else None}


def _trainer_runs() -> dict | None:
    """Metrics from the newest HF Trainer state under models/pii_classifier."""
    states = sorted(MODEL_DIR.glob("**/trainer_state.json"),
                    key=lambda p: json.loads(p.read_text()).get("global_step", 0))
    if not states:
        return None
    state = json.loads(states[-1].read_text())
    hist = state.get("log_history", [])
    train = [{"step": h["step"], "loss": h["loss"]} for h in hist if "loss" in h]
    evals = [{k: h[k] for k in h if k == "step" or k.startswith("eval_")} for h in hist if "eval_loss" in h]
    return {"global_step": state.get("global_step"), "epochs": state.get("epoch"),
            "train_loss": train, "eval": evals, "final_eval": evals[-1] if evals else None,
            "source": str(states[-1].relative_to(ROOT)).replace("\\", "/")}


def training_info() -> dict:
    corpus_lines = None
    if CORPUS_FILE.exists():
        with CORPUS_FILE.open(encoding="utf-8") as f:
            corpus_lines = sum(1 for _ in f)
    return {
        "train": _parse_train(),
        "corpus": {**_parse_corpus_builder(), "generated_lines": corpus_lines},
        "model_dir_present": (MODEL_DIR / "config.json").exists(),
        "run": _trainer_runs(),
        "ner": ner.status(),
    }


# --- pattern-layer benchmark --------------------------------------------------

def _luhn_complete(prefix: str, length: int, rng: random.Random) -> str:
    body = prefix + "".join(rng.choices(string.digits, k=length - len(prefix) - 1))
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return body + str((10 - total % 10) % 10)


def _gen_value(label: str, rng: random.Random) -> str:
    if label == "CARD":
        prefix, length = rng.choice([("4", 16), ("51", 16), ("55", 16), ("6011", 16), ("34", 15), ("37", 15)])
        num = _luhn_complete(prefix, length, rng)
        sep = rng.choice(["", " ", "-"])
        if not sep:
            return num
        groups = [num[:4], num[4:10], num[10:]] if length == 15 else [num[i:i + 4] for i in range(0, 16, 4)]
        return sep.join(groups)
    if label == "PHONE":
        n = str(rng.randint(6, 9)) + "".join(rng.choices(string.digits, k=9))
        return rng.choice([n, f"+91 {n[:5]} {n[5:]}", f"+91-{n}", f"0{n}", f"{n[:5]} {n[5:]}",
                           f"+1 {rng.randint(200, 999)} 555 {rng.randint(1000, 9999)}",
                           f"+44 20 {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"])
    if label == "EMAIL":
        user = rng.choice(["priya.s", "rahul_92", "a.k.verma", "dev+alerts", "support", "neha.gupta"])
        dom = rng.choice(["example.com", "mail.co.in", "corp.example.org", "uni.ac.in"])
        return f"{user}{rng.randint(1, 99)}@{dom}"
    if label == "PAN":
        return ("".join(rng.choices(string.ascii_uppercase, k=5)) +
                "".join(rng.choices(string.digits, k=4)) + rng.choice(string.ascii_uppercase))
    if label == "IP":
        return ".".join(str(rng.randint(0, 255)) for _ in range(4))
    if label == "URL":
        return rng.choice([f"https://bank.example.com/login?id={rng.randint(100, 999)}",
                           f"http://portal.example.in/u/{rng.randint(1000, 9999)}",
                           f"www.example.org/reset/{rng.randint(10, 99)}"])
    if label == "OTP":
        return "".join(rng.choices(string.digits, k=rng.choice([4, 6, 6, 8])))
    raise ValueError(label)


TEMPLATES = {
    "CARD": ["Card number: {v}", "please charge {v} for the order", "My card is {v}, expiry 09/28"],
    "PHONE": ["Call me on {v}", "Phone: {v}", "whatsapp {v} after 6pm"],
    "EMAIL": ["Email: {v}", "send the invoice to {v} today", "contact {v}."],
    "PAN": ["PAN: {v}", "my pan card no. is {v}", "Tax ID {v} verified"],
    "IP": ["Login from IP {v}", "server {v} is down", "blocked {v}."],
    "URL": ["visit {v}", "reset link: {v}.", "Open ({v}) to continue"],
    # The last two phrasings are realistic but have no keyword before the code.
    "OTP": ["Your OTP is {v}", "verification code: {v}", "PIN {v} for ATM",
            "use code {v} to log in", "{v} is your one-time password"],
}

NEGATIVES = [
    "Order #{n13} shipped yesterday",
    "Invoice total Rs {amt} due on 12/05/2026",
    "Card ending 4242 was declined",
    "Rejected card {badcard}",
    "Running version 1.2.3.4.5 of the app",
    "Employee id {n6} joined team 42",
    "Meeting at 10:30 in room 204",
    "Address 999.300.1.1 is not an IP",
]


def _negative(rng: random.Random) -> str:
    good = _luhn_complete("4", 16, rng)
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    return rng.choice(NEGATIVES).format(
        n13="".join(rng.choices(string.digits, k=13)), amt=f"{rng.randint(1, 99)},{rng.randint(100, 999)}",
        badcard=bad, n6="".join(rng.choices(string.digits, k=6)))


@lru_cache(maxsize=1)
def evaluate_patterns(per_label: int = 60, negatives: int = 120, seed: int = 7) -> dict:
    """Exact-span precision / recall / F1 of the pattern layer on a synthetic benchmark."""
    rng = random.Random(seed)
    cases = []  # (text, [(label, start, end)])
    for label, templates in TEMPLATES.items():
        for _ in range(per_label):
            tpl, v = rng.choice(templates), _gen_value(label, rng)
            text = tpl.format(v=v)
            start = text.index(v)
            cases.append((text, [(label, start, start + len(v))], tpl))
    for _ in range(negatives):
        cases.append((_negative(rng), [], None))

    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    misses, false_alarms = defaultdict(list), []
    t0 = time.perf_counter()
    for text, gold, _ in cases:
        pred = {(d.label, d.start, d.end) for d in detect(text)}
        gold_set = set(gold)
        for g in gold_set:
            if g in pred:
                tp[g[0]] += 1
            else:
                fn[g[0]] += 1
                if len(misses[g[0]]) < 2:
                    misses[g[0]].append(text)
        for p in pred - gold_set:
            fp[p[0]] += 1
            if not gold and len(false_alarms) < 3:
                false_alarms.append({"text": text, "label": p[0]})
    elapsed = (time.perf_counter() - t0) * 1000

    def prf(t, f_p, f_n):
        p = t / (t + f_p) if t + f_p else 1.0
        r = t / (t + f_n) if t + f_n else 1.0
        return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
                "tp": t, "fp": f_p, "fn": f_n}

    per = {lab: {**prf(tp[lab], fp[lab], fn[lab]), "misses": misses[lab]} for lab in TEMPLATES}
    neg_flagged = sum(1 for text, gold, _ in cases if not gold and detect(text))
    return {
        "per_label": per,
        "overall": prf(sum(tp.values()), sum(fp.values()), sum(fn.values())),
        "negatives": {"total": negatives, "flagged": neg_flagged, "examples": false_alarms},
        "cases": len(cases), "seed": seed, "ms_total": elapsed, "ms_per_case": elapsed / len(cases),
    }


# --- canary audit -------------------------------------------------------------

CANARY_SENTENCES = {
    "card": "Customer paid with {v} at checkout.",
    "phone": "Reach the customer on {v}.",
    "otp": "Your OTP is {v}.",
    "email": "Receipt sent to {v}.",
    "ip": "Request came from {v}.",
    "url": "Callback was {v}",
}


@lru_cache(maxsize=1)
def canary_audit() -> dict:
    """Push the canary values from src/eval/canary.py through sanitize(); count leaks."""
    from src.eval.canary import CANARY_MARKERS
    from src.pipeline.sanitize import SanitizationError, sanitize

    rows = []
    for marker in CANARY_MARKERS:
        _, kind, value = marker.split("_", 2)
        text = CANARY_SENTENCES.get(kind, "{v}").format(v=value)
        try:
            out = sanitize(text).sanitized
            leaked = value in out
        except SanitizationError:
            out, leaked = "(blocked: fail-closed)", False
        rows.append({"kind": kind.upper(), "input": text, "output": out, "leaked": leaked})
    return {"markers": len(rows), "leaked": sum(r["leaked"] for r in rows), "rows": rows}


def detectors_info() -> list[dict]:
    return [{"name": n, "label": lab, "method": m, "priority": i + 1}
            for i, (n, lab, m, _) in enumerate(DETECTORS)]


def main() -> None:
    ev = evaluate_patterns()
    print(f"Pattern benchmark: {ev['cases']} cases, {ev['ms_per_case']:.3f} ms/case")
    for lab, m in ev["per_label"].items():
        print(f"  {lab:6s} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}  misses={m['misses']}")
    o = ev["overall"]
    print(f"  ALL    P={o['precision']:.2f} R={o['recall']:.2f} F1={o['f1']:.2f}")
    print(f"  negatives flagged: {ev['negatives']['flagged']}/{ev['negatives']['total']} {ev['negatives']['examples']}")
    ca = canary_audit()
    print(f"Canary: {ca['leaked']}/{ca['markers']} leaked")
    for r in ca["rows"]:
        print(f"  {r['kind']:5s} {r['output']}")
    print(json.dumps(training_info(), indent=1)[:1500])


if __name__ == "__main__":
    main()
